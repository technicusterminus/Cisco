"""Abnahmefall: HTTPS von WEB zu APP mit Least Privilege (Lab 32).

Prueft die ganze Kette: Ausgangszustand -> Traffic-Test mit Ursache -> Konfiguration per REST ->
Bewertung nach Zustand (Funktion und Sicherheit getrennt) -> Abkuerzungen scheitern -> Reset,
Persistenz, Hinweise, Pruefungsmodus. Alle Wege (REST, Traffic-Test, CLI, Lab-Bewertung)
laufen ueber denselben Zustand und dieselbe Engine.
"""
import copy
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dcprep import trace  # noqa: E402
from dcprep.cli import Cli  # noqa: E402
from dcprep.model import post  # noqa: E402
from dcprep.server import Sim, serve  # noqa: E402

LAB = '32-https-least-privilege'


def mo(cls, attrs=None, *children):
    body = {'attributes': attrs or {}}
    if children:
        body['children'] = list(children)
    return {cls: body}


def solution(filter_entry=None, scope='context', rev='yes', web_rel='fvRsCons', app_rel='fvRsProv', filter_tenant='Shop'):
    """Baut eine Loesung; Varianten fuer gleichwertige und falsche Loesungen."""
    entry = filter_entry or {'name': 'https', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '443', 'dToPort': '443'}
    flt = mo('vzFilter', {'name': 'f-https'}, mo('vzEntry', entry))
    trees = []
    if filter_tenant != 'Shop':
        trees.append(('uni', mo('fvTenant', {'name': filter_tenant}, flt)))
    kids = [flt] if filter_tenant == 'Shop' else []
    kids += [mo('vzBrCP', {'name': 'c-https', 'scope': scope},
                mo('vzSubj', {'name': 's', 'revFltPorts': rev}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'f-https'}))),
             mo('fvAp', {'name': 'Webshop'},
                mo('fvAEPg', {'name': 'Web'}, mo(web_rel, {'tnVzBrCPName': 'c-https'})),
                mo('fvAEPg', {'name': 'App'}, mo(app_rel, {'tnVzBrCPName': 'c-https'})))]
    trees.append(('uni', mo('fvTenant', {'name': 'Shop'}, *kids)))
    return trees


def config_without_ts(store):
    rows = copy.deepcopy(store.dump_config())
    for r in rows:
        for x in r[1:]:
            if isinstance(x, dict):
                x.pop('modTs', None)
    return rows


class LabBase(unittest.TestCase):
    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0
        self.S.load_lab(LAB)

    def apply(self, trees):
        for dn, t in trees:
            post(self.S.store, dn, t)
        self.S.changed()

    def tr(self, src, dst, proto, port=0):
        return trace.run(self.S.engine, self.S.sim, src, dst, proto, port)

    def check(self):
        r = self.S.check_lab()
        return r, {c['desc']: c for c in r['checks']}


class TestStartState(LabBase):
    def test_https_fails_with_policy_reason_not_network(self):
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual(r['verdict'], 'DROP')
        self.assertEqual(r['reason'], 'POLICY_IMPLICIT_DENY')
        self.assertTrue(r['location'].startswith('Policy Anfrage'))
        self.assertIn('Implicit Deny', r['explain'])
        self.assertTrue(r['hint'])
        # alles vor der Policy ist gruen: Endpoints, Gateway, Routing
        before = r['steps'][:[s['title'] for s in r['steps']].index(r['location'])]
        self.assertTrue(before and all(s['ok'] is not False for s in before))
        titles = ' '.join(s['title'] for s in before)
        for part in ('web1 gelernt', 'app1 gelernt', 'Gateway', 'Routing in VRF'):
            self.assertIn(part, titles)
        self.assertEqual([(p['direction'], p['action'], p['code']) for p in r['policy']], [('request', 'deny', 'POLICY_IMPLICIT_DENY')])

    def test_start_state_fails_lab_and_is_reproducible(self):
        r, by = self.check()
        self.assertEqual(r['categories']['function']['passed'], 1)  # nur das Gateway
        self.assertLess(r['passed'], r['total'])
        a = (config_without_ts(self.S.store), json.dumps(self.S.sim['hosts'], sort_keys=True), json.dumps(self.tr('web1', 'app1', 'tcp', 443)['steps']))
        other = Sim(tempfile.mkdtemp(), 'admin')
        other.sim['settings']['discoverySeconds'] = 0
        other.load_lab(LAB)
        b = (config_without_ts(other.store), json.dumps(other.sim['hosts'], sort_keys=True),
             json.dumps(trace.run(other.engine, other.sim, 'web1', 'app1', 'tcp', 443)['steps']))
        self.assertEqual(a, b)

    def test_unresolved_for_unknown_endpoint(self):
        r = self.tr('web1', 'gibtsnicht', 'tcp', 443)
        self.assertEqual(r['verdict'], 'UNRESOLVED')
        self.assertEqual(r['reason'], 'INPUT_INVALID')


class TestSolutions(LabBase):
    def test_reference_solution_passes_everything(self):
        self.apply(solution())
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual(r['verdict'], 'ALLOW')
        req, rep = r['policy']
        self.assertEqual((req['action'], req['code'], req['rule']['contract'], req['rule']['direction']),
                         ('permit', 'POLICY_CONTRACT_PERMIT', 'uni/tn-Shop/brc-c-https', 'c2p'))
        self.assertEqual((rep['action'], rep['rule']['direction'], rep['sport']), ('permit', 'p2c', 443))
        ssh = self.tr('web1', 'app1', 'tcp', 22)
        self.assertEqual((ssh['verdict'], ssh['reason']), ('DROP', 'POLICY_IMPLICIT_DENY'))
        ping = self.tr('web1', 'app1', 'icmp')
        self.assertEqual(ping['reason'], 'POLICY_IMPLICIT_DENY', 'Ein TCP-Filter darf ICMP nicht freigeben')
        res, by = self.check()
        self.assertEqual([c['desc'] for c in res['checks'] if not c['ok']], [])
        self.assertEqual(res['categories'], {'function': {'passed': 2, 'total': 2}, 'security': {'passed': 5, 'total': 5}})

    def test_lab_file_solution_passes(self):
        for dn, body in self.S.lab(LAB)['solutionConfig']:
            post(self.S.store, dn, body)
        self.S.changed()
        res, _ = self.check()
        self.assertEqual(res['passed'], res['total'])

    def test_equivalent_solutions_pass(self):
        variants = {
            'Scope tenant': solution(scope='tenant'),
            'Filter im Tenant common': solution(filter_tenant='common'),
            'Stateful-Entry': solution({'name': 'https', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '443', 'dToPort': '443', 'stateful': 'yes'}),
            'EtherType ipv4': solution({'name': 'https', 'etherT': 'ipv4', 'prot': 'tcp', 'dFromPort': 'https', 'dToPort': 'https'}),
        }
        for name, trees in variants.items():
            with self.subTest(variant=name):
                self.S.load_lab(LAB)
                self.apply(trees)
                res, _ = self.check()
                self.assertEqual([(c['desc'], c['info']) for c in res['checks'] if not c['ok']], [], name)

    def test_permit_any_shortcut_fails_least_privilege(self):
        self.apply(solution({'name': 'any', 'etherT': 'unspecified'}))
        res, by = self.check()
        self.assertEqual(res['categories']['function'], {'passed': 2, 'total': 2}, 'funktional erfuellt')
        self.assertLess(res['categories']['security']['passed'], res['categories']['security']['total'])
        lp = by['Least Privilege Web → App: nur tcp/443 offen']
        self.assertFalse(lp['ok'])
        self.assertIn('tcp/22', lp['info'])
        self.assertFalse(by['web1 → app1 SSH (TCP 22) ist durch die Policy blockiert']['ok'])
        self.assertLess(res['passed'], res['total'])

    def test_wide_port_range_fails_least_privilege(self):
        self.apply(solution({'name': 'tcp-all', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '1', 'dToPort': '65535'}))
        res, by = self.check()
        self.assertFalse(by['Least Privilege Web → App: nur tcp/443 offen']['ok'])
        self.assertTrue(by['web1 → app1 Ping ist durch die Policy blockiert']['ok'])

    def test_swapped_roles_fail_function(self):
        self.apply(solution(web_rel='fvRsProv', app_rel='fvRsCons'))
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_IMPLICIT_DENY'))
        res, by = self.check()
        self.assertFalse(by['web1 → app1 HTTPS (TCP 443) funktioniert']['ok'])

    def test_without_reverse_filter_ports_reply_is_dropped(self):
        self.apply(solution(rev='no'))
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_REPLY_DENIED'))
        self.assertEqual([p['action'] for p in r['policy']], ['permit', 'deny'])
        self.assertTrue(r['location'].startswith('Policy Antwort'))

    def test_provider_cannot_initiate(self):
        self.apply(solution())
        r = self.tr('app1', 'web1', 'tcp', 443)
        self.assertEqual(r['verdict'], 'DROP')
        self.assertTrue(r['reason'].startswith('POLICY_'))

    def test_stateful_entry_blocks_provider_syn_from_service_port(self):
        """Ohne Stateful darf der Provider mit Quell-Port 443 beliebige Ports beim Consumer ansprechen (zustandslos),
        mit Stateful nur noch TCP mit ACK."""
        e = lambda: self.S.engine
        web, app = 'uni/tn-Shop/ap-Webshop/epg-Web', 'uni/tn-Shop/ap-Webshop/epg-App'
        self.apply(solution())
        self.assertEqual(e().packet(e().cls[app], e().cls[web], 'tcp', 443, 3389, 'syn')[0], 'permit')
        self.S.load_lab(LAB)
        self.apply(solution({'name': 'https', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '443', 'dToPort': '443', 'stateful': 'yes'}))
        self.assertEqual(e().packet(e().cls[app], e().cls[web], 'tcp', 443, 3389, 'syn')[0], 'deny')
        self.assertEqual(e().packet(e().cls[app], e().cls[web], 'tcp', 443, 49152, 'ack')[0], 'permit')
        self.assertEqual(self.tr('web1', 'app1', 'tcp', 443)['verdict'], 'ALLOW')

    def test_subject_without_apply_both_directions_uses_own_filter_per_direction(self):
        """B-06: Ohne Apply Both Directions gelten vzInTerm (Consumer -> Provider) und vzOutTerm (Provider -> Consumer)
        getrennt, ohne Port-Tausch. Fehlt der Rueckrichtungs-Filter, scheitert die Antwort."""
        e = lambda: self.S.engine
        web, app = 'uni/tn-Shop/ap-Webshop/epg-Web', 'uni/tn-Shop/ap-Webshop/epg-App'

        def tree(with_out):
            terms = [mo('vzInTerm', {}, mo('vzRsFiltAtt', {'tnVzFilterName': 'to-443'}))]
            if with_out:
                terms.append(mo('vzOutTerm', {}, mo('vzRsFiltAtt', {'tnVzFilterName': 'from-443'})))
            return [('uni', mo('fvTenant', {'name': 'Shop'},
                               mo('vzFilter', {'name': 'to-443'}, mo('vzEntry', {'name': 'e', 'etherT': 'ip', 'prot': 'tcp',
                                                                                'dFromPort': '443', 'dToPort': '443'})),
                               mo('vzFilter', {'name': 'from-443'}, mo('vzEntry', {'name': 'e', 'etherT': 'ip', 'prot': 'tcp',
                                                                                  'sFromPort': '443', 'sToPort': '443'})),
                               mo('vzBrCP', {'name': 'c-https'}, mo('vzSubj', {'name': 's'}, *terms)),
                               mo('fvAp', {'name': 'Webshop'},
                                  mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'c-https'})),
                                  mo('fvAEPg', {'name': 'App'}, mo('fvRsProv', {'tnVzBrCPName': 'c-https'})))))]
        self.apply(tree(False))
        self.assertTrue(self.S.store.get('uni/tn-Shop/brc-c-https/subj-s/intmnl/rsfiltAtt-to-443'))
        self.assertEqual(e().packet(e().cls[web], e().cls[app], 'tcp', 50000, 443, 'syn')[0], 'permit')
        self.assertEqual(e().packet(e().cls[app], e().cls[web], 'tcp', 443, 50000, 'ack')[0], 'deny',
                         'ohne vzOutTerm gibt es keine Rueckrichtung, auch kein automatischer Port-Tausch')
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_REPLY_DENIED'))
        self.S.load_lab(LAB)
        self.apply(tree(True))
        self.assertEqual(e().packet(e().cls[app], e().cls[web], 'tcp', 443, 50000, 'ack')[0], 'permit')
        self.assertEqual(e().packet(e().cls[app], e().cls[web], 'tcp', 50000, 443, 'syn')[0], 'deny',
                         'der Rueckrichtungs-Filter gilt nur wie definiert (Quell-Port 443)')
        self.assertEqual(self.tr('web1', 'app1', 'tcp', 443)['verdict'], 'ALLOW')
        z = Cli(self.S.engine, self.S.sim).run('leaf101', 'show zoning-rule')
        rules = [ln for ln in z.split('\n') if 'c-https' in ln]
        self.assertEqual(len(rules), 2, z)
        self.assertTrue(all('| uni-dir ' in ln for ln in rules), z)
        self.assertNotIn('bi-dir', '\n'.join(rules))

    def test_service_model_is_separate_from_policy(self):
        self.apply(solution())
        self.S.sim['hosts'] = [dict(h, services=['tcp/22']) if h['name'] == 'app1' else h for h in self.S.sim['hosts']]
        self.S.changed()
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'SERVICE_NOT_LISTENING'))
        self.assertEqual(r['policy'][0]['action'], 'permit', 'Policy hat erlaubt, nur der Dienst fehlt')
        res, by = self.check()
        self.assertFalse(by['web1 → app1 HTTPS (TCP 443) funktioniert']['ok'])
        self.assertTrue(by['Least Privilege Web → App: nur tcp/443 offen']['ok'])

    def test_broken_access_does_not_count_as_policy_block(self):
        """Ein kaputter Pfad blockiert SSH auch - zaehlt aber nicht als Sicherheits-Erfuellung."""
        self.apply(solution())
        post(self.S.store, 'uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {}, mo('fvRsDomAtt', {'tDn': 'uni/phys-PhysDom-Server', 'status': 'deleted'})))
        self.S.changed()
        r = self.tr('web1', 'app1', 'tcp', 22)
        self.assertEqual(r['reason'], 'EP_NOT_LEARNED')
        res, by = self.check()
        self.assertFalse(by['web1 → app1 SSH (TCP 22) ist durch die Policy blockiert']['ok'])
        self.assertFalse(by['web1 → app1 HTTPS (TCP 443) funktioniert']['ok'])


    def test_f0467_texts_follow_technote(self):
        """Cisco TechNote 220876: Format und Texte von F0467 (invalid-vlan, encap-already-in-use) und
        show vlan encap-id <n> extended (leer, wenn das Encap nicht deployed ist)."""
        self.apply(solution())
        app = 'uni/tn-Shop/ap-Webshop/epg-App'
        cli = Cli(self.S.engine, self.S.sim)
        self.assertIn('vlan-120', cli.run('leaf102', 'show vlan encap-id 120 extended'))
        post(self.S.store, app + '/rspathAtt-[topology/pod-1/paths-102/pathep-[eth1/2]]', mo('fvRsPathAtt', {'encap': 'vlan-250'}))
        self.S.changed()
        d = self.S.engine.faults[app]['F0467']['descr']
        self.assertEqual(d, 'Configuration failed for %s node 102 eth1/2 due to Invalid VLAN Configuration, debug message: '
                            'invalid-vlan: vlan-250 :Either the EpG is not associated with a domain or the domain does not '
                            'have this vlan assigned to it;' % app)
        self.assertEqual(Cli(self.S.engine, self.S.sim).run('leaf102', 'show vlan encap-id 250 extended'), '')
        post(self.S.store, app + '/rspathAtt-[topology/pod-1/paths-102/pathep-[eth1/2]]', mo('fvRsPathAtt', {'encap': 'vlan-120'}))
        post(self.S.store, 'uni/tn-Shop/ap-Webshop/epg-Web', mo('fvAEPg', {}, mo('fvRsPathAtt', {
            'tDn': 'topology/pod-1/paths-102/pathep-[eth1/3]', 'encap': 'vlan-120'})))
        self.S.changed()
        f = {dn: x['F0467']['descr'] for dn, x in self.S.engine.faults.items() if 'F0467' in x}
        self.assertEqual(len(f), 1, f)
        (dn, descr), = f.items()
        other = 'Shop:Webshop:Web' if dn == app else 'Shop:Webshop:App'
        self.assertIn('due to Encap Already Used in Another EPG, debug message: encap-already-in-use: Encap (vlan-120) is '
                      'already in use by %s;' % other, descr)


class TestContractPriorities(LabBase):
    """B-16: Prioritaeten nach Cisco ACI Contract Guide (Table 8 Zoning-Rule-Prioritaet, Table 23 Filter-Prioritaet).
    Spezifischere EPG-Paare gewinnen ueber vzAny; Deny gewinnt nur bei gleicher Zoning-Rule-Prioritaet."""

    WEB, APP = 'uni/tn-Shop/ap-Webshop/epg-Web', 'uni/tn-Shop/ap-Webshop/epg-App'
    SSH = {'name': 'ssh', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '22', 'dToPort': '22'}

    def build(self, any_action='permit', epg_action='deny', any_entry=None, epg_entry=None, pref=None):
        e = self.S.engine
        vrf = e.cls[self.WEB]['vrf']
        flt = lambda n, en: mo('vzFilter', {'name': n}, mo('vzEntry', dict(en, name='e')))
        subj = lambda f, act: mo('vzSubj', {'name': 's', 'revFltPorts': 'yes'},
                                 mo('vzRsSubjFiltAtt', {'tnVzFilterName': f, 'action': act}))
        kids = [flt('f-any', any_entry or self.SSH), flt('f-epg', epg_entry or self.SSH),
                mo('vzBrCP', {'name': 'c-any'}, subj('f-any', any_action)),
                mo('vzBrCP', {'name': 'c-epg'}, subj('f-epg', epg_action)),
                mo('fvAp', {'name': 'Webshop'},
                   mo('fvAEPg', {'name': 'Web', **({'prefGrMemb': pref[0]} if pref else {})},
                      mo('fvRsCons', {'tnVzBrCPName': 'c-epg'})),
                   mo('fvAEPg', {'name': 'App', **({'prefGrMemb': pref[1]} if pref else {})},
                      mo('fvRsProv', {'tnVzBrCPName': 'c-epg'})))]
        self.apply([('uni', mo('fvTenant', {'name': 'Shop'}, *kids)),
                    (vrf + '/any', mo('vzAny', {'prefGrMemb': 'enabled' if pref else 'disabled'},
                                      mo('vzRsAnyToCons', {'tnVzBrCPName': 'c-any'}),
                                      mo('vzRsAnyToProv', {'tnVzBrCPName': 'c-any'})))])

    def pkt(self, src, dst, port=22):
        e = self.S.engine
        return e.packet(e.cls[src], e.cls[dst], 'tcp', 50000, port, 'syn')

    def test_epg_deny_beats_vzany_permit(self):
        """Figure 134: vzAny-to-vzAny permit SSH (17), EPG-to-EPG deny SSH (7) -> Web -> App SSH verworfen."""
        self.build('permit', 'deny')
        act, why = self.pkt(self.WEB, self.APP)
        self.assertEqual((act, self.S.engine.last_code), ('deny', 'POLICY_DENY_RULE'))
        self.assertIn('fully_qual(7)', why)

    def test_epg_permit_beats_vzany_deny(self):
        """Hoehere Zoning-Rule-Prioritaet gewinnt vor der Aktion: EPG-to-EPG permit (7) vor vzAny-to-vzAny deny (17)."""
        self.build('deny', 'permit')
        act, why = self.pkt(self.WEB, self.APP)
        self.assertEqual(act, 'permit', why)
        self.assertIn('fully_qual(7)', why)

    def test_same_priority_deny_wins_over_more_specific_permit(self):
        """Figure 135: gleiche Prioritaet (EPG-to-EPG), Deny any-IP gewinnt gegen spezifischeren Permit SSH."""
        self.build('permit', 'deny', epg_entry={'etherT': 'ip'})
        self.apply([('uni/tn-Shop', mo('fvTenant', {}, mo('vzBrCP', {'name': 'c-epg2'}, mo('vzSubj', {'name': 's'},
                    mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'f-any'}))))),
                    (self.WEB, mo('fvAEPg', {}, mo('fvRsCons', {'tnVzBrCPName': 'c-epg2'}))),
                    (self.APP, mo('fvAEPg', {}, mo('fvRsProv', {'tnVzBrCPName': 'c-epg2'})))])
        self.assertEqual(self.pkt(self.WEB, self.APP)[0], 'deny')

    def test_any_filter_has_lower_priority_than_specific_filter(self):
        """EPG-to-EPG mit default-Filter ist src_dst_any(9), mit spezifischem Filter fully_qual(7)."""
        self.build('deny', 'permit', epg_entry={'etherT': 'unspecified'}, any_entry={'etherT': 'unspecified'})
        act, why = self.pkt(self.WEB, self.APP, 443)
        self.assertEqual(act, 'permit', 'EPG-to-EPG (9) vor vzAny-to-vzAny (21)')
        self.assertIn('src_dst_any(9)', why)

    def test_preferred_group_loses_to_contract_deny(self):
        """Preferred Group permit ist grp_any_any_any_permit(20): ein Deny-Contract (7) zwischen Mitgliedern gewinnt."""
        self.build('permit', 'deny', pref=('include', 'include'))
        self.assertEqual(self.pkt(self.WEB, self.APP)[0], 'deny')
        self.assertEqual(self.pkt(self.WEB, self.APP, 443)[0], 'permit', 'anderer Verkehr ueber die Preferred Group')
        self.assertEqual(self.S.engine.last_code, 'POLICY_PREFERRED_GROUP')

    def test_preferred_group_non_member_denies_vzany_any_filter(self):
        """Nicht-Mitglied: grp-Denies (18/19) liegen vor vzAny-to-vzAny mit any-Filter (21), aber hinter 17."""
        self.build('permit', 'permit', any_entry={'etherT': 'unspecified'}, epg_entry=self.SSH, pref=('include', 'exclude'))
        self.assertEqual(self.pkt(self.WEB, self.APP, 443)[0], 'deny')
        self.assertEqual(self.pkt(self.WEB, self.APP)[0], 'permit', 'EPG-to-EPG SSH (7)')

    def test_dhcp_is_implicitly_permitted(self):
        """Contract Guide, FAQ: DHCPv4 ist ohne Contract erlaubt, auch ein Deny-Contract greift nicht."""
        pol = lambda port: [(p['direction'], p['action'], p['code']) for p in self.tr('web1', 'app1', 'udp', port)['policy']]
        self.assertEqual(pol(67)[0], ('request', 'permit', 'POLICY_IMPLICIT_PROTOCOL'),
                         'Policy erlaubt; ob ein DHCP-Dienst laeuft, entscheidet das Dienstmodell')
        e = self.S.engine
        self.assertEqual(e.packet(e.cls[self.APP], e.cls[self.WEB], 'udp', 67, 68, 'ack')[0], 'permit', 'Server -> Client')
        self.build('deny', 'deny', any_entry={'etherT': 'ip'}, epg_entry={'etherT': 'ip'})
        self.assertEqual(pol(67)[0][1:], ('permit', 'POLICY_IMPLICIT_PROTOCOL'))
        self.assertEqual(pol(69)[0][1], 'deny', 'nur DHCP, kein beliebiges UDP')

    def test_log_directive_in_zoning_rule_and_decision(self):
        """Contract Guide: Aktion "deny,log" / "log,permit"; bei gleichem Filter gewinnt Deny+Log vor Deny."""
        self.build('permit', 'deny')
        self.apply([(self.S.engine.contracts and 'uni/tn-Shop/brc-c-epg/subj-s/rssubjFiltAtt-f-epg',
                     mo('vzRsSubjFiltAtt', {'directives': 'log'}))])
        act, why = self.pkt(self.WEB, self.APP)
        self.assertEqual(act, 'deny')
        self.assertIn('(log)', why)
        z = Cli(self.S.engine, self.S.sim).run('leaf101', 'show zoning-rule')
        self.assertTrue(all('deny,log' in ln for ln in z.split('\n') if '| c-epg ' in ln), z)
        self.assertTrue(all(' permit ' in ln and 'log' not in ln.split('|')[9] for ln in z.split('\n') if '| c-any ' in ln), z)

    def test_zoning_tables_follow_contract_guide(self):
        """Contract Guide: Gegenrichtung mit eigener Filter-ID (vertauschte Ports, Prio sport), implizite Regel zum BD,
        unenforced nur eine Regel, Preferred Group mit grp_*-Regeln, Intra-EPG class-eq-deny(2)."""
        self.build('permit', 'permit')
        cli = Cli(self.S.engine, self.S.sim)
        rows = [[c.strip() for c in ln.strip('|').split('|')] for ln in cli.run('leaf102', 'show zoning-rule').split('\n')
                if ln.startswith('|') and 'Rule ID' not in ln]
        epg = [r for r in rows if r[7] == 'c-epg']
        self.assertEqual([r[4] for r in epg], ['bi-dir', 'uni-dir-ignore'])
        self.assertNotEqual(epg[0][3], epg[1][3], 'eigene Filter-ID fuer die Gegenrichtung')
        flt = cli.run('leaf102', 'show zoning-filter filter %s' % epg[1][3])
        self.assertIn('sport', flt)
        bd = self.S.engine.A('uni/tn-Shop/BD-BD-App')['pcTag']
        self.assertIn(['0', bd, 'implicit', 'any_dest_any(16)'], [[r[1], r[2], r[3], r[9]] for r in rows])
        self.assertIn('\n[7:', '\n' + cli.run('leaf102', 'contract_parser.py'), 'Format [Prio:RuleId]')
        self.apply([(self.APP, mo('fvAEPg', {'pcEnfPref': 'enforced'}))])
        z = cli.run('leaf102', 'show zoning-rule')
        tag = self.S.engine.cls[self.APP]['pcTag']
        self.assertTrue(any('| %s ' % tag in ln and 'class-eq-deny(2)' in ln for ln in z.split('\n')), z)
        vrf = self.S.engine.cls[self.WEB]['vrf']
        self.apply([(vrf + '/any', mo('vzAny', {'prefGrMemb': 'enabled'})),
                    (self.WEB, mo('fvAEPg', {'prefGrMemb': 'include'}))])
        z = cli.run('leaf102', 'show zoning-rule')
        self.assertIn('grp_any_any_any_permit(20)', z)
        self.assertIn('grp_src_any_any_deny(18)', z, 'App ist kein Mitglied')
        self.assertNotIn('any_any_any(21)', z)
        self.apply([(vrf, mo('fvCtx', {'pcEnfPref': 'unenforced'}))])
        z = [ln for ln in cli.run('leaf102', 'show zoning-rule').split('\n') if ln.startswith('|') and 'Rule ID' not in ln]
        self.assertEqual(len(z), 1)
        self.assertIn('permit', z[0])

    def test_zoning_rule_shows_guide_priorities(self):
        self.build('permit', 'deny')
        z = Cli(self.S.engine, self.S.sim).run('leaf101', 'show zoning-rule')
        any_rows = [ln for ln in z.split('\n') if 'c-any' in ln]
        self.assertTrue(any_rows and all('any_any_filter(17)' in ln for ln in any_rows), z)
        self.assertTrue(all('fully_qual(7)' in ln for ln in z.split('\n') if '| c-epg ' in ln), z)


class TestConnectivityCases(LabBase):
    """Grundfaelle der Connectivity-Engine auf dem Lab-Ausgangszustand."""

    def add_web2(self):
        self.S.sim['hosts'].append({'name': 'web2', 'mac': '00:50:56:10:10:12', 'ip': '10.10.10.12/24', 'gw': '10.10.10.1', 'vlan': 110,
                                    'links': [[self.S.sim['hosts'][0]['links'][0][0], 'eth1/3']], 'bond': 'none', 'descr': ''})
        post(self.S.store, 'uni/tn-Shop/ap-Webshop/epg-Web', mo('fvAEPg', {}, mo('fvRsPathAtt', {
            'tDn': 'topology/pod-1/paths-101/pathep-[eth1/3]', 'encap': 'vlan-110'})))
        self.S.changed()

    def test_same_epg_allowed_without_contract(self):
        self.add_web2()
        r = self.tr('web1', 'web2', 'tcp', 22)
        self.assertEqual(r['verdict'], 'ALLOW')
        self.assertEqual(r['policy'][0]['code'], 'POLICY_SAME_EPG')

    def test_intra_epg_isolation(self):
        self.add_web2()
        post(self.S.store, 'uni/tn-Shop/ap-Webshop/epg-Web', mo('fvAEPg', {'pcEnfPref': 'enforced'}))
        self.S.changed()
        r = self.tr('web1', 'web2', 'tcp', 22)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_INTRA_EPG_ISOLATION'))

    def test_routing_off_is_not_a_policy_problem(self):
        self.apply(solution())
        post(self.S.store, 'uni/tn-Shop/BD-BD-Web', mo('fvBD', {'unicastRoute': 'no'}))
        self.S.changed()
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'GATEWAY_INVALID'))
        self.assertEqual(r['policy'], [], 'die Policy wird gar nicht erst erreicht')

    def test_unenforced_vrf_allows_everything(self):
        post(self.S.store, 'uni/tn-Shop/ctx-Prod', mo('fvCtx', {'pcEnfPref': 'unenforced'}))
        self.S.changed()
        r = self.tr('web1', 'app1', 'tcp', 22)
        self.assertEqual((r['verdict'], r['policy'][0]['code']), ('ALLOW', 'POLICY_VRF_UNENFORCED'))
        res, by = self.check()
        self.assertFalse(by['Least Privilege Web → App: nur tcp/443 offen']['ok'])


class TestLabSession(LabBase):
    def test_hints_are_staged_and_do_not_change_config(self):
        before = config_without_ts(self.S.store)
        h1 = self.S.lab_hint(1)
        self.assertEqual((h1['used'], len(h1['hints']), h1['count']), (1, 1, 4))
        self.assertNotIn('web-to-app-https', h1['hints'][0], 'Stufe 1 verraet die Loesung nicht')
        h4 = self.S.lab_hint(4)
        self.assertIn('web-to-app-https', h4['hints'][3])
        self.assertEqual(config_without_ts(self.S.store), before)
        self.assertEqual(self.S.check_lab()['hintsUsed'], 4)

    def test_description_does_not_contain_solution(self):
        lab = self.S.lab_public(self.S.lab(LAB))
        text = lab['intro'] + ' '.join(lab['requirements'])
        for word in ('Consumer', 'Provider', 'web-to-app-https', 'vzFilter', 'Reverse'):
            self.assertNotIn(word, text)
        self.assertEqual(lab['hints'], [])

    def test_exam_mode_hides_hints_solution_and_details(self):
        self.S.load_lab(LAB, mode='exam')
        pub = self.S.lab_public(self.S.lab(LAB))
        self.assertEqual((pub['mode'], pub['solution'], pub['hintCount']), ('exam', None, 0))
        with self.assertRaises(Exception):
            self.S.lab_hint(1)
        res = self.S.check_lab()
        self.assertTrue(all(c['info'] == '' for c in res['checks']))
        self.assertEqual(res['mode'], 'exam')

    def test_understanding_is_scored_separately(self):
        self.S.lab_answer('q1', 1)
        self.S.lab_answer('q2', 0)
        res = self.S.check_lab()
        self.assertEqual(res['understanding'], {'correct': 1, 'answered': 2, 'total': 3})
        self.apply(solution())
        self.assertEqual(self.S.check_lab()['passed'], 7, 'Fragen beeinflussen das Bestehen nicht')

    def test_reset_restores_start_state(self):
        start_cfg, start_hosts = config_without_ts(self.S.store), json.dumps(self.S.sim['hosts'], sort_keys=True)
        self.apply(solution())
        self.S.lab_hint(2)
        self.assertEqual(self.S.check_lab()['passed'], 7)
        self.S.lab_op({'op': 'reset', 'id': LAB})
        self.assertEqual(config_without_ts(self.S.store), start_cfg)
        self.assertEqual(json.dumps(self.S.sim['hosts'], sort_keys=True), start_hosts)
        self.assertEqual(self.S.lab_session()['hints'], 0)
        self.assertEqual(self.tr('web1', 'app1', 'tcp', 443)['reason'], 'POLICY_IMPLICIT_DENY')

    def test_reset_keeps_exam_mode(self):
        self.S.load_lab(LAB, mode='exam')
        self.S.lab_op({'op': 'reset', 'id': LAB})
        self.assertEqual(self.S.lab_session()['mode'], 'exam')

    def test_progress_and_state_survive_restart_and_export_roundtrip(self):
        self.apply(solution())
        self.assertEqual(self.S.check_lab()['passed'], 7)
        self.S.save()
        again = Sim(self.S.data_dir, 'admin')
        self.assertEqual(again.progress()[LAB]['done'], True)
        self.assertEqual(again.check_lab()['passed'], 7)
        blob = json.loads(json.dumps(self.S.save_blob('roundtrip')))
        self.S.load_lab(LAB)
        self.assertLess(self.S.check_lab()['passed'], 7)
        self.S.load_blob(blob)
        self.assertEqual(self.S.check_lab()['passed'], 7)

    def test_import_is_validated(self):
        with self.assertRaises(Exception):
            self.S.load_blob({'kind': 'etwas-anderes'})
        with self.assertRaises(Exception):
            self.S.load_blob({'kind': 'datacenter-prep-save', 'version': 999, 'config': [], 'sim': {}})

    def test_cli_sees_same_state_as_rest_and_trace(self):
        self.apply(solution())
        import re
        cli = Cli(self.S.engine, self.S.sim)
        out = cli.run('leaf102', 'show zoning-rule')
        row = next(l for l in out.splitlines() if 'c-https' in l and 'bi-dir' in l)
        self.assertIn('permit', row)
        fid = re.split(r'\s*\|\s*', row.strip('| '))[3]
        self.assertIn('443', cli.run('leaf102', 'show zoning-filter filter %s' % fid))


class TestOverHttp(unittest.TestCase):
    """Wie ein Benutzer: Lab per REST starten, testen, konfigurieren, bewerten, zuruecksetzen."""

    @classmethod
    def setUpClass(cls):
        cls.hub, cls.httpd = serve('127.0.0.1', 0, tempfile.mkdtemp(), 'admin', discovery=0)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def req(self, method, path, body=None):
        r = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), method=method,
                                   data=json.dumps(body).encode() if body is not None else None)
        try:
            with self.opener.open(r) as resp:
                return resp.status, json.loads(resp.read() or b'null')
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b'null')

    def test_full_chain(self):
        self.assertEqual(self.req('POST', '/api/aaaLogin.json', {'aaaUser': {'attributes': {'name': 'admin', 'pwd': 'admin'}}})[0], 200)
        self.assertEqual(self.req('POST', '/sim/labs/load', {'id': LAB, 'mode': 'guided'})[0], 200)
        st, r = self.req('POST', '/sim/traffic', {'src': 'web1', 'dst': 'app1', 'proto': 'tcp', 'port': 443})
        self.assertEqual((st, r['verdict'], r['reason']), (200, 'DROP', 'POLICY_IMPLICIT_DENY'))
        for dn, body in solution():
            self.assertEqual(self.req('POST', '/api/mo/%s.json' % dn, body)[0], 200)
        st, r = self.req('POST', '/sim/traffic', {'src': 'web1', 'dst': 'app1', 'proto': 'tcp', 'port': 443})
        self.assertEqual(r['verdict'], 'ALLOW')
        st, r = self.req('POST', '/sim/traffic', {'src': 'web1', 'dst': 'app1', 'proto': 'tcp', 'port': 22})
        self.assertEqual(r['verdict'], 'DROP')
        st, chk = self.req('POST', '/sim/labs/check', {})
        self.assertEqual((chk['passed'], chk['total']), (7, 7))
        st, h = self.req('POST', '/sim/labs/hint', {'level': 1})
        self.assertEqual((st, h['used']), (200, 1))
        self.assertEqual(self.req('POST', '/sim/labs/op', {'op': 'reset', 'id': LAB})[0], 200)
        st, chk = self.req('POST', '/sim/labs/check', {})
        self.assertLess(chk['passed'], chk['total'])
        st, labs = self.req('GET', '/sim/labs')
        row = next(l for l in labs if l['id'] == LAB)
        self.assertTrue(row['progress']['done'], 'bestanden bleibt nach dem Reset sichtbar')
        self.assertEqual(row['modes'], ['guided', 'exam'])


    def test_change_history_source_and_rollback_diff(self):
        """B-12: Herkunft je Aenderung (GUI/REST/Rollback), Rollback als Diff, aaaModLR ohne erfundenes Attribut."""
        self.assertEqual(self.req('POST', '/api/aaaLogin.json', {'aaaUser': {'attributes': {'name': 'admin', 'pwd': 'admin'}}})[0], 200)
        self.assertEqual(self.req('POST', '/sim/labs/load', {'id': LAB, 'mode': 'guided'})[0], 200)
        self.assertEqual(self.req('POST', '/sim/snapshots', {'op': 'create', 'name': 'vor-test'})[0], 200)
        self.req('POST', '/api/mo/uni.json', {'fvTenant': {'attributes': {'name': 'ChgRest'}}})
        r = urllib.request.Request('http://127.0.0.1:%d/api/mo/uni.json' % self.port, method='POST',
                                   data=json.dumps({'fvTenant': {'attributes': {'name': 'ChgGui', 'descr': 'x'}}}).encode(),
                                   headers={'X-DCPrep-Client': 'gui'})
        with self.opener.open(r) as resp:
            self.assertEqual(resp.status, 200)
        self.assertEqual(self.req('POST', '/sim/snapshots', {'op': 'rollback', 'name': 'vor-test'})[0], 200)
        st, ch = self.req('GET', '/sim/changes')
        by_src = {}
        for t in ch:
            by_src.setdefault(t['source'], []).append(t)
        self.assertIn('uni/tn-ChgRest', [i['affected'] for t in by_src['REST'] for i in t['items']])
        self.assertIn('uni/tn-ChgGui', [i['affected'] for t in by_src['GUI'] for i in t['items']])
        rb = by_src['Rollback'][0]
        self.assertEqual(ch[0]['source'], 'Rollback', 'neueste zuerst')
        self.assertTrue({i['affected'] for i in rb['items'] if i['ind'] == 'deletion'} >= {'uni/tn-ChgRest', 'uni/tn-ChgGui'})
        st, mods = self.req('GET', '/api/class/aaaModLR.json')
        self.assertTrue(mods['imdata'])
        self.assertNotIn('source', mods['imdata'][0]['aaaModLR']['attributes'], 'Herkunft ist simulator-spezifisch')

    def test_diagnosis_log_records_without_grading_or_changes(self):
        """B-13: Traffic-Tests, CLI und Pruefungen landen im Protokoll der Lab-Sitzung, auch im Pruefungsmodus, ohne Bewertung."""
        self.assertEqual(self.req('POST', '/api/aaaLogin.json', {'aaaUser': {'attributes': {'name': 'admin', 'pwd': 'admin'}}})[0], 200)
        self.assertEqual(self.req('POST', '/sim/labs/load', {'id': LAB, 'mode': 'exam'})[0], 200)
        self.assertEqual(self.req('GET', '/sim/labs/log')[1], [])
        self.req('POST', '/sim/traffic', {'src': 'web1', 'dst': 'app1', 'proto': 'tcp', 'port': 443})
        self.req('POST', '/sim/cli', {'node': 'leaf101', 'cmd': 'show zoning-rule'})
        self.req('POST', '/sim/cli', {'node': 'apic1', 'cmd': 'show running-config'})
        st, chk = self.req('POST', '/sim/labs/check', {})
        st, log = self.req('GET', '/sim/labs/log')
        self.assertEqual([x['kind'] for x in log], ['traffic', 'cli', 'cli', 'check'])
        self.assertEqual(log[0]['what'], 'web1 → app1 tcp/443')
        self.assertEqual(log[0]['result'], 'DROP POLICY_IMPLICIT_DENY')
        self.assertEqual([log[1]['result'], log[2]['result']], ['device', 'unsupported'])
        self.assertEqual(log[3]['result'], '%d von %d' % (chk['passed'], chk['total']))
        self.assertNotIn('log', json.dumps(chk['checks']), 'Das Protokoll fliesst nicht in die Bewertung ein')
        self.assertEqual(self.req('POST', '/sim/labs/op', {'op': 'reset', 'id': LAB})[0], 200)
        self.assertEqual(self.req('GET', '/sim/labs/log')[1], [], 'Neue Sitzung, leeres Protokoll')


class TestRequirementLabs(unittest.TestCase):
    """Alle Labs im Anforderungsformat: Aufbau, keine Loesung im Aufgabentext, Abkuerzungen scheitern."""

    LEAKS = {
        '02-access-policies': ['AAEP', 'Attachable', 'Policy Group', 'Switch Profile', 'Interface Profile', 'VLAN Pool'],
        '03-tenant-epg': ['Static Port', 'fvRsPathAtt', 'Domain-Zuordnung'],
        '04-contracts': ['vzAny', 'EPG Collection', 'Consumer', 'Provider', 'Reverse', 'konsumiert'],
        '00-day0-apic-setup': ['number of active', 'Vorschlag ist 3', 'acidiag touch'],
        '08-rest-api': ['aaaDomainRef', 'Security Domain', 'Auto-Dom', 'writePriv', 'children'],
        '01-fabric-discovery': ['Route Reflector', 'MP-BGP', 'Pending', 'nodeidentpol'],
        '05-vpc-lacp': ['Protection Group', 'fabricExplicitGEp', 'IPG-vPC', 'Port Channel Policy', 'lacpLagPol', 'protpaths', 'Policy Group'],
        '06-l3out-ospf': ['Route Reflector', 'MP-BGP', 'MTU ignore', 'Advertised', 'EXSTART', 'web-to-internet', '9000'],
        '09-l3out-bgp': ['Route Reflector', 'Remote AS', 'bgpPeerP', 'web-to-isp', 'Advertised', 'VLAN Pool'],
        '10-mgmt-ntp': ['Pod Policy Group', 'Pod Profile', 'Date and Time', 'PodPol', 'fabricRsPodPGrp'],
        '12-vmm-vcenter': ['Dynamic', 'dynamisch', 'Resolution', 'VLAN-Pool-VMM', 'vmmDomP', 'Immediate'],
        '14-l2out-migration': ['ARP Flooding', 'arpFlood', 'External Bridged', 'l2extOut', 'Glean', 'LegacyNet'],
        '11-static-leaf-taboo': ['Static Leaf', 'Taboo', 'fvRsNodeAtt', 'vzTaboo', 'no-ping'],
        '13-shared-services': ['Global', 'Export', 'vzCPIf', 'Shared between', 'Imported', 'fvRsConsIf', 'Consumer', 'Provider'],
        '07-troubleshooting': ['8080', 'Unicast Routing', 'BD-Bakup', 'Reverse', '149', 'Port Block'],
        '15-transit-route-control': ['Export Route Control', 'Import Route Control', 'export-rtctrl', 'Aggregate', 'enforceRtctrl'],
        '16-service-graph-pbr': ['vlan-400', 'Encap Block', 'Redirect', 'vnsLDevVip', 'Device Selection', 'PBR'],
        '17-l3out-vpc-svi-bfd': ['OSPF-BFD', 'Interface Control', 'Side A', 'Secondary IP', 'ext-svi'],
        '18-ebgp-loopback-md5-summary': ['Multihop', 'TTL', 'Static Route', 'Node Profile', 'Summarization Policy', 'bgpRtSummPol'],
        '19-eigrp-static-track': ['IP SLA', 'Track List', 'ipRsRouteTrack', 'EIGRP-Branch', 'icmp-5s'],
        '20-floating-svi': ['Floating SVI', 'Floating IP', 'Anchor', 'l3extVirtualLIfP', 'Path Attribute'],
        '22-inband-management': ['S0211', 'VLAN Pool', 'AAEP', 'In-Band EPG', 'Provider Group', 'IPG-APIC'],
        '21-aaa-tacacs-rbac': ['Provider Group', 'aaaLoginDomain', 'aaaDomainRef', 'readPriv', 'ISE-TACACS', 'Security Domain'],
        '23-esg-useg': ['fvIpAttr', 'IP-Attribut', 'isAttrBasedEPg', 'EPG Selector', 'frontend-to-backend', 'Consumer', 'Provider'],
        '24-firmware-upgrade': ['Odd', 'Even', 'Upgrade Group', 'maintMaintGrp'],
        '25-config-export-import': ['Merge', 'Replace', 'AES', 'Remote Location', 'configImportP'],
        '26-monitoring-snmp-syslog': ['Client Group', 'Pod Policy Group', 'Destination Group', 'snmpClientGrpP'],
        '27-dhcp-relay': ['Relay Label', 'dhcpLbl', 'Relay Policy', 'Filter default'],
        '28-mcp-loop-qos': ['MCP', 'PDU per VLAN', 'Endpoint Loop Protection', 'mcpInstPol', 'Port Disable'],
        '29-multipod': ['DHCP Relay', '9150', 'External Connection', 'MTU'],
        '30-remote-leaf': ['DHCP Relay', 'Routable', 'Direct Traffic', 'MTU'],
        '31-multisite-ndo': ['9150', 'Template', 'Annotation', 'Shop-Stretched'],
        '32-https-least-privilege': ['Consumer', 'Provider', 'web-to-app-https', 'Reverse'],
        '33-same-epg': ['Static Port', 'fvRsPathAtt'],
        '34-two-epgs-same-bd': ['Consumer', 'Provider', 'admin-to-web'],
        '35-port-and-direction': ['8443', 'Consumer', 'Provider', 'vertauscht', 'konsumiert'],
        '36-endpoint-move': ['eth1/7', 'eth1/6', 'pc-x', 'Static Port', 'Bindung'],
        '37-link-or-policy': ['Disabled', 'deaktiviert', 'Kabel', 'LINK_DOWN', 'Contract', 'eth1/2 ist'],
        '38-intra-epg': ['Isolation', 'Intra-EPG', 'Intra EPG', 'fvRsIntraEpg', 'Contract'],
        '39-preferred-group': ['Preferred', 'vzAny', 'EPG Collection', 'prefGrMemb', 'Include'],
        '40-it-ot-segmentation': ['Consumer', 'Provider', 'Isolation', 'Intra', 'vzBrCP', 'scada-to-plc'],
        '41-route-or-contract': ['Route Reflector', 'MP-BGP', 'BGP', 'konsumiert', 'fvRsCons'],
        '42-return-path': ['Advertised', 'public', 'fvRsBDToOut', 'Associated', 'Rückweg'],
        '43-change-snapshot': ['Config Rollbacks', 'Port 8443'],
        '44-access-diagnosis': ['fvRsDomAtt', 'Encap Block', 'vlan-111', 'VLAN 111', 'ohne Domain', 'Pool'],
        '45-two-bds-one-vrf': ['10.10.21', 'VRF Test liegt', 'fvRsCtx', 'Subnetz ersetzen'],
        '46-contract-priorities': ['web-to-db-deny', 'fully_qual', 'Priorität 7', 'Aktion deny', 'Web konsumiert'],
    }

    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0

    def load(self, lid):
        self.S.load_lab(lid)
        return self.S.lab(lid)

    def apply(self, *items):
        for dn, body in items:
            post(self.S.store, dn, body)
        self.S.changed()

    def result(self):
        r = self.S.check_lab()
        return r, {c['desc']: c['ok'] for c in r['checks']}

    def test_structure_and_no_solution_in_text(self):
        labs = [l for l in self.S.labs() if l.get('kind') in ('requirements', 'troubleshooting')]
        self.assertEqual(sorted(l['id'] for l in labs), sorted(self.LEAKS))
        for lab in labs:
            with self.subTest(lab=lab['id']):
                self.assertEqual(len(lab['hints']), 4)
                self.assertEqual(lab['modes'], ['guided', 'exam'])
                self.assertEqual(lab['tasks'], [])
                self.assertTrue(lab['requirements'] and lab['goals'] and lab['limits'] and lab['cause'])
                self.assertTrue(any(c.get('category') == 'security' for c in lab['checks']), 'Sicherheitspruefung fehlt')
                for q in lab.get('questions', []):
                    self.assertLess(q['answer'], len(q['options']))
                # sichtbar ab Start: Szenario, Anforderungen und die Beschreibungen der Pruefungen
                text = lab['intro'] + ' ' + ' '.join(lab['requirements']) + ' ' + ' '.join(c['desc'] for c in lab['checks'])
                for word in self.LEAKS[lab['id']]:
                    self.assertNotIn(word, text, '%s verraet die Loesung' % word)

    def test_lab33_new_epg_plus_contract_is_not_the_solution(self):
        self.load('33-same-epg')
        self.apply(('uni', mo('fvTenant', {'name': 'Shop'},
                              mo('vzFilter', {'name': 'any'}, mo('vzEntry', {'name': 'any'})),
                              mo('vzBrCP', {'name': 'all'}, mo('vzSubj', {'name': 's'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'any'}))),
                              mo('fvAp', {'name': 'Webshop'},
                                 mo('fvAEPg', {'name': 'Web2'}, mo('fvRsBd', {'tnFvBDName': 'BD-Web'}), mo('fvRsDomAtt', {'tDn': 'uni/phys-PhysDom-Server'}),
                                    mo('fvRsPathAtt', {'tDn': 'topology/pod-1/paths-102/pathep-[eth1/3]', 'encap': 'vlan-110'}),
                                    mo('fvRsCons', {'tnVzBrCPName': 'all'})),
                                 mo('fvAEPg', {'name': 'Web'}, mo('fvRsProv', {'tnVzBrCPName': 'all'}))))))
        r, by = self.result()
        self.assertTrue(by['web1 → web2 SSH (TCP 22)'], 'funktioniert ...')
        self.assertFalse(by['web2 in EPG Web gelernt'], '... aber web2 ist nicht in der EPG Web')
        self.assertFalse(by['Kein Contract im Tenant Shop'])

    def test_lab34_bridging_ok_policy_denies_then_shortcuts_fail(self):
        self.load('34-two-epgs-same-bd')
        t = trace.run(self.S.engine, self.S.sim, 'adm1', 'web1', 'icmp')
        self.assertEqual((t['verdict'], t['reason']), ('DROP', 'POLICY_IMPLICIT_DENY'))
        titles = ' '.join(s['title'] for s in t['steps'] if s['ok'])
        self.assertIn('ARP aufgeloest', titles)
        self.assertIn('Layer-2-Forwarding', titles)
        anyc = mo('fvTenant', {'name': 'Shop'}, mo('vzFilter', {'name': 'any'}, mo('vzEntry', {'name': 'any'})),
                  mo('vzBrCP', {'name': 'all'}, mo('vzSubj', {'name': 's'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'any'}))),
                  mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Admin'}, mo('fvRsCons', {'tnVzBrCPName': 'all'})),
                     mo('fvAEPg', {'name': 'Web'}, mo('fvRsProv', {'tnVzBrCPName': 'all'}))))
        self.apply(('uni', anyc))
        r, by = self.result()
        self.assertEqual(r['categories']['function']['passed'], r['categories']['function']['total'])
        self.assertFalse(by['Least Privilege Admin → Web: nur SSH und Ping'])
        self.load('34-two-epgs-same-bd')
        sol = json.loads(json.dumps(self.S.lab('34-two-epgs-same-bd')['solutionConfig'][0][1]))
        ap = next(c for c in sol['fvTenant']['children'] if 'fvAp' in c)['fvAp']['children']
        for e in ap:
            k = e['fvAEPg']['children'][0]
            rel = next(iter(k))
            e['fvAEPg']['children'][0] = {('fvRsProv' if rel == 'fvRsCons' else 'fvRsCons'): k[rel]}
        self.apply(('uni', sol))
        r, by = self.result()
        self.assertFalse(by['adm1 → web1 SSH'], 'vertauschte Rollen')

    def test_lab35_two_independent_faults(self):
        lab = self.load('35-port-and-direction')
        t = trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'tcp', 443)
        self.assertEqual(t['reason'], 'POLICY_IMPLICIT_DENY')
        port_fix, roles_web, roles_app = lab['solutionConfig']
        self.apply(port_fix)
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'tcp', 443)['verdict'], 'DROP', 'nur Port behoben')
        self.load('35-port-and-direction')
        self.apply(roles_web, roles_app)
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'tcp', 443)['verdict'], 'DROP', 'nur Rollen behoben')
        self.apply(port_fix)
        r, by = self.result()
        self.assertEqual(r['passed'], r['total'])

    def test_lab35_extra_permit_any_contract_fails(self):
        self.load('35-port-and-direction')
        self.apply(('uni', mo('fvTenant', {'name': 'Shop'}, mo('vzFilter', {'name': 'any'}, mo('vzEntry', {'name': 'any'})),
                              mo('vzBrCP', {'name': 'quickfix'}, mo('vzSubj', {'name': 's'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'any'}))),
                              mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'quickfix'})),
                                 mo('fvAEPg', {'name': 'App'}, mo('fvRsProv', {'tnVzBrCPName': 'quickfix'}))))))
        r, by = self.result()
        self.assertTrue(by['web1 → app1 HTTPS (TCP 443) funktioniert'])
        self.assertFalse(by['Kein zusätzlicher Contract (höchstens einer im Tenant)'])
        self.assertFalse(by['Least Privilege Web → App: nur tcp/443'])

    def test_lab07_permit_any_for_ticket3_fails_security(self):
        lab = self.load('07-troubleshooting')
        for dn, body in lab['solutionConfig']:
            if 'flt-http' in dn:
                body = mo('vzEntry', {'etherT': 'unspecified', 'prot': 'unspecified', 'dFromPort': 'unspecified', 'dToPort': 'unspecified'})
            self.apply((dn, body))
        r, by = self.result()
        self.assertTrue(by['Ticket 3+6: web1 → app1 TCP 80'])
        self.assertFalse(by['Least Privilege Web → App: nur TCP 80 und Ping'])

    def test_lab04_per_epg_provider_is_accepted(self):
        lab = self.load('04-contracts')
        base, vzany_contract = lab['solutionConfig'][0], lab['solutionConfig'][1]
        self.apply(base, vzany_contract, ('uni/tn-Shop/ap-Webshop', mo('fvAp', {},
            mo('fvAEPg', {'name': 'Web'}, mo('fvRsProv', {'tnVzBrCPName': 'mgmt-ssh'})),
            mo('fvAEPg', {'name': 'App'}, mo('fvRsProv', {'tnVzBrCPName': 'mgmt-ssh'})),
            mo('fvAEPg', {'name': 'Mgmt'}, mo('fvRsCons', {'tnVzBrCPName': 'mgmt-ssh'})))))
        r, by = self.result()
        self.assertEqual([k for k, v in by.items() if not v], [])

    def test_lab02_binding_a_free_port_fails_security(self):
        lab = self.load('02-access-policies')
        self.apply(*[(dn, body) for dn, body in lab['solutionConfig']],
                   ('uni/tn-Lab02/ap-AP1/epg-Server', mo('fvAEPg', {}, mo('fvRsPathAtt', {
                       'tDn': 'topology/pod-1/paths-101/pathep-[eth1/5]', 'encap': 'vlan-100'}))))
        r, by = self.result()
        self.assertTrue(by['Ping h1 → h2'])
        self.assertFalse(by['Fremdgerät h9 an leaf101 eth1/5 (ohne EPG-Bindung) bekommt keinen Zugang'])


class TestEventsAndPhysical(unittest.TestCase):
    """Endpoint Move, Link-Ausfall und deaktivierter Port: eigene Reason Codes, Ereignisse und Endpoint-Verlauf."""

    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0
        self.S.load_lab(LAB)
        self.leaf102 = self.S.sim['hosts'][1]['links'][0][0]

    def tr(self, *a):
        return trace.run(self.S.engine, self.S.sim, *a)

    def codes(self):
        return [e['code'] for e in self.S.sim['events']]

    def test_lab_load_writes_no_history(self):
        self.assertEqual(self.S.sim['ephist'], {})

    def test_link_down_is_physical_not_policy(self):
        self.S.host_event({'op': 'link', 'name': 'app1', 'up': False})
        self.S.changed()
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual((r['verdict'], r['reason'], r['layer']), ('DROP', 'LINK_DOWN', 'physical'))
        self.assertEqual(r['policy'], [])
        self.assertIn('S9102', self.codes())
        self.S.host_event({'op': 'link', 'name': 'app1', 'up': True})
        self.S.changed()
        self.assertIn('S9103', self.codes())
        self.assertEqual([x['event'] for x in self.S.sim['ephist']['app1']], ['lost', 'linkdown', 'learned', 'linkup'])

    def test_disabled_interface(self):
        post(self.S.store, 'uni/fabric/outofsvc', mo('fabricOOServicePol', {}, mo('fabricRsOosPath', {'tDn': 'topology/pod-1/paths-102/pathep-[eth1/2]'})))
        self.S.changed()
        self.assertEqual(self.tr('web1', 'app1', 'tcp', 443)['reason'], 'PORT_ADMIN_DOWN')

    def test_move_to_bound_port_is_a_move_event(self):
        post(self.S.store, 'uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {}, mo('fvRsPathAtt', {
            'tDn': 'topology/pod-1/paths-102/pathep-[eth1/8]', 'encap': 'vlan-120'})))
        self.S.changed()
        self.S.host_event({'op': 'move', 'name': 'app1', 'links': [[self.leaf102, 'eth1/8']]})
        self.S.changed()
        self.assertIn('S9101', self.codes())
        last = self.S.sim['ephist']['app1'][-1]
        self.assertEqual((last['event'], last['where'], last['detail']), ('moved', 'leaf102 eth1/8', 'vorher leaf102 eth1/2'))

    def test_move_to_unbound_port_is_not_learned(self):
        self.S.host_event({'op': 'move', 'name': 'app1', 'links': [[self.leaf102, 'eth1/9']]})
        self.S.changed()
        r = self.tr('web1', 'app1', 'tcp', 443)
        self.assertEqual(r['reason'], 'EP_NOT_LEARNED')
        self.assertEqual(self.S.sim['ephist']['app1'][-1]['event'], 'lost')

    def test_history_over_http_api_shape(self):
        self.S.host_event({'op': 'link', 'name': 'app1', 'up': False})
        self.S.changed()
        self.S.save()
        again = Sim(self.S.data_dir, 'admin')
        self.assertEqual(again.sim['ephist']['app1'][-1]['event'], 'linkdown', 'Verlauf bleibt nach Neustart erhalten')


class TestTroubleshootingLabs(unittest.TestCase):
    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0

    def apply(self, *items):
        for dn, body in items:
            post(self.S.store, dn, body)
        self.S.changed()

    def by(self):
        return {c['desc']: c['ok'] for c in self.S.check_lab()['checks']}

    def test_lab36_start_shows_risk_and_history(self):
        self.S.load_lab('36-endpoint-move')
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'app2', 'tcp', 8080)['reason'], 'EP_NOT_LEARNED')
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'pc-x', 'app1', 'icmp')['verdict'], 'ALLOW', 'Fremdgeraet ist in der EPG App')
        self.assertEqual(self.S.sim['ephist']['app2'][0]['where'], 'leaf101 eth1/6')

    def test_lab36_new_binding_without_cleanup_fails_security(self):
        lab = self.S.load_lab('36-endpoint-move')
        self.apply(('uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {}, mo('fvRsPathAtt', {
            'tDn': 'topology/pod-1/paths-102/pathep-[eth1/7]', 'encap': 'vlan-120'}))))
        by = self.by()
        self.assertTrue(by['web1 → app2 TCP 8080'])
        self.assertFalse(by['Am alten Anschluss kommt niemand mehr in die EPG App'])
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.assertEqual(self.S.sim['ephist']['app2'][-1]['event'], 'learned')

    def test_lab37_three_different_causes(self):
        self.S.load_lab('37-link-or-policy')
        got = {k: trace.run(self.S.engine, self.S.sim, *a)['reason'] for k, a in
               {'t1': ('web1', 'app1', 'tcp', 8080), 't2': ('jump1', 'web1', 'tcp', 22), 't3': ('web1', 'web3', 'icmp')}.items()}
        self.assertEqual(got, {'t1': 'PORT_ADMIN_DOWN', 't2': 'POLICY_IMPLICIT_DENY', 't3': 'LINK_DOWN'})

    def test_lab37_permit_any_for_ticket2_fails(self):
        lab = self.S.load_lab('37-link-or-policy')
        self.apply(lab['solutionConfig'][0], ('uni', mo('fvTenant', {'name': 'Shop'},
            mo('vzFilter', {'name': 'any'}, mo('vzEntry', {'name': 'any'})),
            mo('vzBrCP', {'name': 'all'}, mo('vzSubj', {'name': 's'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'any'}))),
            mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsProv', {'tnVzBrCPName': 'all'})),
               mo('fvAEPg', {'name': 'Mgmt'}, mo('fvRsCons', {'tnVzBrCPName': 'all'}))))))
        by = self.by()
        self.assertTrue(by['Ticket 1: web1 → app1 TCP 8080'] and by['Ticket 2: jump1 → web1 SSH'])
        self.assertFalse(by['Least Privilege jump1 → Web: nur SSH'])
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'web3', 'icmp')['reason'], 'LINK_DOWN', 'Ticket 3 bleibt physisch')


    def test_lab44_three_access_causes_and_faults(self):
        self.S.load_lab('44-access-diagnosis')
        e = self.S.engine
        for src, dst, port in (('web1', 'app1', 8080), ('web2', 'app1', 8080), ('app1', 'db1', 5432)):
            self.assertEqual(trace.run(e, self.S.sim, src, dst, 'tcp', port)['reason'], 'EP_NOT_LEARNED', (src, dst))
        self.assertIn('vlan-111', ' '.join(e.hosts['web2']['reasons']))
        faults = sorted(self.S.store.attrs(f)['descr'] for f in self.S.store.by_class('faultInst') if '/tn-Shop/' in f)
        self.assertEqual(len(faults), 2, 'App ohne Domain und DB mit VLAN ausserhalb des Pools, web2 ohne Fault')
        self.assertTrue(all('F0467' == self.S.store.attrs(f)['code'] for f in self.S.store.by_class('faultInst') if '/tn-Shop/' in f))

    def test_lab44_static_leaf_shortcut_learns_foreign_device(self):
        lab = self.S.load_lab('44-access-diagnosis')
        self.apply(lab['solutionConfig'][0], lab['solutionConfig'][2],
                   ('uni/tn-Shop/ap-Webshop/epg-Web', mo('fvAEPg', {}, mo('fvRsNodeAtt', {'tDn': 'topology/pod-1/node-101', 'encap': 'vlan-110'}),
                                                       mo('fvRsNodeAtt', {'tDn': 'topology/pod-1/node-102', 'encap': 'vlan-110'}))))
        by = self.by()
        self.assertTrue(by['Ticket 1: web1 → app1 TCP 8080'] and by['Ticket 3: app1 → db1 TCP 5432'])
        self.assertFalse(by['Unbekanntes Gerät an leaf101 eth1/9 wird nicht gelernt'])

    def test_lab44_changing_the_db_vlan_is_not_a_fix(self):
        lab = self.S.load_lab('44-access-diagnosis')
        self.apply(lab['solutionConfig'][0], lab['solutionConfig'][1],
                   ('uni/tn-Shop/ap-Webshop/epg-DB', mo('fvAEPg', {}, mo('fvRsPathAtt', {
                       'tDn': 'topology/pod-1/paths-102/pathep-[eth1/8]', 'encap': 'vlan-130'}))))
        by = self.by()
        self.assertTrue(by['Keine Konfigurationsfehler (F0467) im Tenant Shop'], 'gueltige Konfiguration ...')
        self.assertFalse(by['Ticket 3: app1 → db1 TCP 5432'], '... passt aber nicht zum Server (sendet VLAN 250)')

    def test_lab45_routing_not_policy_and_leak_shortcut_fails(self):
        lab = self.S.load_lab('45-two-bds-one-vrf')
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'tcp', 8080)['reason'], 'INTERVRF_LEAK_MISSING')
        # Abkuerzung: Gateway korrigieren, BD in VRF Test lassen, Contract auf Scope Tenant mit Shared-Subnetzen
        self.apply(('uni', mo('fvTenant', {'name': 'Shop'},
                              mo('fvBD', {'name': 'BD-App'}, mo('fvSubnet', {'ip': '10.10.21.1/24', 'status': 'deleted'})),
                              mo('vzBrCP', {'name': 'web-to-app', 'scope': 'tenant'}))))
        self.apply(('uni/tn-Shop/BD-BD-App', mo('fvBD', {}, mo('fvSubnet', {'ip': '10.10.20.1/24', 'scope': 'private,shared'}))),
                   ('uni/tn-Shop/BD-BD-Web', mo('fvBD', {}, mo('fvSubnet', {'ip': '10.10.10.1/24', 'scope': 'private,shared'}))))
        by = self.by()
        self.assertFalse(by['Web und App liegen in derselben VRF wie geplant (Prod)'])
        self.assertTrue(by['test1 → app1 bleibt getrennt'], 'Die Trennung allein erkennt die Abkuerzung nicht ...')
        self.S.load_lab('45-two-bds-one-vrf')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()), '... die Musterloesung besteht')


    def test_lab46_vzany_deny_shortcut_blocks_everything(self):
        """Lab 46: Start offen (vzAny 17); Deny in vrf-open sperrt alles; EPG-Deny (7) trifft nur Web <-> DB."""
        lab = self.S.load_lab('46-contract-priorities')
        r = trace.run(self.S.engine, self.S.sim, 'web1', 'db1', 'tcp', 1433)
        self.assertEqual(r['verdict'], 'ALLOW')
        self.assertIn('any_any_filter(17)', r['policy'][0]['text'])
        self.apply(('uni/tn-Shop/brc-vrf-open/subj-subj/rssubjFiltAtt-any-ip', mo('vzRsSubjFiltAtt', {'action': 'deny'})))
        by = self.by()
        self.assertTrue(by['web1 → db1 TCP 1433 ist durch die Policy blockiert'])
        self.assertFalse(by['app1 → db1 TCP 1433 funktioniert weiter'], 'Deny auf vzAny-Ebene trifft alle EPGs')
        self.S.load_lab('46-contract-priorities')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        r = trace.run(self.S.engine, self.S.sim, 'web1', 'db1', 'tcp', 1433)
        self.assertEqual(r['policy'][0]['code'], 'POLICY_DENY_RULE')
        self.assertIn('fully_qual(7)', r['policy'][0]['text'])


class TestSegmentationLabs(unittest.TestCase):
    """Labs 38 (Intra-EPG), 39 (Preferred Group), 40 (IT/OT): Loesung besteht, Abkuerzungen scheitern."""

    ANY = mo('vzFilter', {'name': 'any'}, mo('vzEntry', {'name': 'any'}))
    ANYC = mo('vzBrCP', {'name': 'all'}, mo('vzSubj', {'name': 's'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'any'})))

    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0

    def apply(self, *items):
        for dn, body in items:
            post(self.S.store, dn, body)
        self.S.changed()

    def by(self):
        r = self.S.check_lab()
        return r, {c['desc']: c['ok'] for c in r['checks']}

    def test_lab38_isolation_alone_breaks_sync(self):
        self.S.load_lab('38-intra-epg')
        self.apply(('uni/tn-Shop/ap-Webshop/epg-Web', mo('fvAEPg', {'pcEnfPref': 'enforced'})))
        r, by = self.by()
        self.assertFalse(by['web1 → web2 TCP 9100'])
        self.assertTrue(by['web1 → web2 SSH durch die Policy blockiert'])
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'web2', 'tcp', 9100)['reason'], 'POLICY_INTRA_EPG_ISOLATION')

    def test_lab38_intra_contract_permit_any_fails(self):
        self.S.load_lab('38-intra-epg')
        self.apply(('uni', mo('fvTenant', {'name': 'Shop'}, self.ANY, self.ANYC, mo('fvAp', {'name': 'Webshop'},
                    mo('fvAEPg', {'name': 'Web'}, mo('fvRsIntraEpg', {'tnVzBrCPName': 'all'}))))))
        r, by = self.by()
        self.assertTrue(by['web1 → web2 TCP 9100'])
        self.assertFalse(by['Least Privilege web1 → web2: nur TCP 9100'])

    def test_lab38_solution_reason_codes(self):
        lab = self.S.load_lab('38-intra-epg')
        self.apply(*lab['solutionConfig'])
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'web2', 'tcp', 22)['reason'], 'POLICY_INTRA_EPG_CONTRACT_DENY')
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'web2', 'tcp', 9100)['policy'][0]['code'], 'POLICY_INTRA_EPG_CONTRACT')

    def test_lab39_shortcuts(self):
        self.S.load_lab('39-preferred-group')
        self.apply(('uni/tn-Shop/ctx-Prod', mo('fvCtx', {'pcEnfPref': 'unenforced'})))
        r, by = self.by()
        self.assertTrue(by['web1 → app1 TCP 1433'])
        self.assertFalse(by['Policy im VRF Prod bleibt eingeschaltet'])
        self.assertFalse(by['web1 → jump1 durch die Policy blockiert'])
        self.S.load_lab('39-preferred-group')
        self.apply(('uni', mo('fvTenant', {'name': 'Shop'}, self.ANY, self.ANYC, mo('fvAp', {'name': 'Webshop'},
                    mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'all'}), mo('fvRsProv', {'tnVzBrCPName': 'all'})),
                    mo('fvAEPg', {'name': 'App'}, mo('fvRsCons', {'tnVzBrCPName': 'all'}), mo('fvRsProv', {'tnVzBrCPName': 'all'}))))))
        r, by = self.by()
        self.assertTrue(by['web1 → app1 TCP 1433'])
        self.assertFalse(by['Ohne Contracts gelöst'])

    def test_lab39_mgmt_in_group_fails_and_vrf_only_is_not_enough(self):
        lab = self.S.load_lab('39-preferred-group')
        self.apply(('uni/tn-Shop/ctx-Prod/any', mo('vzAny', {'prefGrMemb': 'enabled'})))
        r, by = self.by()
        self.assertFalse(by['web1 → app1 TCP 1433'], 'nur am VRF reicht nicht')
        self.apply(*lab['solutionConfig'], ('uni/tn-Shop/ap-Webshop/epg-Mgmt', mo('fvAEPg', {'prefGrMemb': 'include'})))
        r, by = self.by()
        self.assertFalse(by['Least Privilege jump1 → App: nichts'])

    def test_lab40_permit_any_works_but_is_not_least_privilege(self):
        self.S.load_lab('40-it-ot-segmentation')
        self.apply(('uni', mo('fvTenant', {'name': 'Werk'}, self.ANY, self.ANYC,
                              mo('fvCtx', {'name': 'OT'}, mo('vzAny', {}, mo('vzRsAnyToCons', {'tnVzBrCPName': 'all'}),
                                                              mo('vzRsAnyToProv', {'tnVzBrCPName': 'all'}))))))
        r, by = self.by()
        self.assertEqual(r['categories']['function']['passed'], r['categories']['function']['total'], 'alles funktioniert ...')
        self.assertLessEqual(r['categories']['security']['passed'], 1, '... aber fast nichts ist Least Privilege')

    def test_lab40_without_plc_isolation_lateral_fails(self):
        lab = self.S.load_lab('40-it-ot-segmentation')
        sol = json.loads(json.dumps(lab['solutionConfig'][0][1]))
        ap = next(c for c in sol['fvTenant']['children'] if 'fvAp' in c)['fvAp']['children']
        next(e for e in ap if e['fvAEPg']['attributes']['name'] == 'PLC')['fvAEPg']['attributes'].pop('pcEnfPref')
        self.apply(('uni', sol))
        r, by = self.by()
        self.assertFalse(by['Keine laterale Kommunikation plc1 → plc2'])
        self.assertEqual(r['passed'], r['total'] - 1)

    def test_lab40_monitoring_with_admin_rights_fails(self):
        lab = self.S.load_lab('40-it-ot-segmentation')
        self.apply(*lab['solutionConfig'], ('uni/tn-Werk/ap-Linie1/epg-MON', mo('fvAEPg', {}, mo('fvRsCons', {'tnVzBrCPName': 'admin-ssh'}))))
        r, by = self.by()
        self.assertFalse(by['MON → SCADA: nur SNMP und Ping (kein SSH)'])

    def test_lab40_start_shows_lateral_risk(self):
        self.S.load_lab('40-it-ot-segmentation')
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'plc1', 'plc2', 'tcp', 502)['verdict'], 'ALLOW')
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'scada1', 'plc1', 'tcp', 502)['reason'], 'POLICY_IMPLICIT_DENY')


class TestConvertedLabs(unittest.TestCase):
    """B-01: alte Labs im Anforderungsformat. Die Musterloesung besteht (TestLabs), typische Abkuerzungen nicht."""

    ANY = mo('vzFilter', {'name': 'any'}, mo('vzEntry', {'name': 'any'}))

    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0

    def apply(self, *items):
        for dn, body in items:
            post(self.S.store, dn, body)
        self.S.changed()

    def by(self):
        return {c['desc']: c['ok'] for c in self.S.check_lab()['checks']}

    def test_lab01_logical_config_waits_for_physical_fabric(self):
        lab = self.S.load_lab('01-fabric-discovery')
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'tcp', 8080)['reason'], 'SWITCH_INACTIVE')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        cli = Cli(self.S.engine, self.S.sim)
        self.assertIn('Shop:Prod', cli.run('leaf101', 'show vrf'))
        self.assertNotIn('Shop:Prod', cli.run('leaf103', 'show vrf'), 'VRF nur dort, wo Endpoints ihrer EPGs haengen (Frage q2)')

    def test_lab05_static_channel_suspends_lacp_server(self):
        lab = self.S.load_lab('05-vpc-lacp')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/infra/lacplagp-LACP-Active', mo('lacpLagPol', {'mode': 'off'})))
        by = self.by()
        self.assertFalse(by['db1 gelernt in EPG DB'], 'Mode On: der LACP-Server suspendiert seine Links')
        self.assertIn('LACP', ' '.join(self.S.engine.hosts['db1']['reasons']))

    def test_lab05_permit_any_to_db_fails_security(self):
        lab = self.S.load_lab('05-vpc-lacp')
        sol = copy.deepcopy(lab['solutionConfig'])
        self.apply(*sol)
        self.apply(('uni/tn-Shop', mo('fvTenant', {}, self.ANY, mo('vzBrCP', {'name': 'all'}, mo('vzSubj', {'name': 's', 'revFltPorts': 'yes'},
                    mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'any'}))),
                    mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'DB'}, mo('fvRsProv', {'tnVzBrCPName': 'all'})),
                       mo('fvAEPg', {'name': 'App'}, mo('fvRsCons', {'tnVzBrCPName': 'all'}))))))
        by = self.by()
        self.assertTrue(by['app1 → db1 TCP 3306'])
        self.assertFalse(by['Least Privilege App → DB: nur TCP 3306'])

    def test_lab06_advertising_app_net_fails_security(self):
        lab = self.S.load_lab('06-l3out-ospf')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/tn-Shop/BD-BD-App', mo('fvBD', {}, mo('fvSubnet', {'ip': '10.10.20.1/24', 'scope': 'public'}),
                                                  mo('fvRsBDToOut', {'tnL3extOutName': 'WAN'}))),
                   ('uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-internet'}))))
        by = self.by()
        self.assertFalse(by['10.10.20.0/24 wird nicht angekündigt'])
        self.assertFalse(by['app1 → 8.8.8.8 blockiert'])

    def test_lab11_removing_icmp_from_contract_is_not_a_taboo(self):
        self.S.load_lab('11-static-leaf-taboo')
        self.apply(('uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {}, mo('fvRsNodeAtt', {'tDn': 'topology/pod-1/node-102', 'encap': 'vlan-120'}))),
                   ('uni/tn-Shop/brc-web-to-app/subj-subj', mo('vzSubj', {}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'icmp', 'status': 'deleted'}))))
        r = trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'icmp')
        self.assertEqual(r['reason'], 'POLICY_IMPLICIT_DENY')
        by = self.by()
        self.assertTrue(by['app2 gelernt in EPG App'])
        self.assertFalse(by['Ping zu app1 verboten, unabhängig von Contracts'], 'ohne Taboo erlaubt der naechste ICMP-Contract wieder')

    def test_lab11_static_port_for_app2_is_not_the_ask(self):
        self.S.load_lab('11-static-leaf-taboo')
        self.apply(('uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {}, mo('fvRsPathAtt', {
            'tDn': 'topology/pod-1/paths-102/pathep-[eth1/3]', 'encap': 'vlan-120'}))))
        by = self.by()
        self.assertTrue(by['app2 gelernt in EPG App'])
        self.assertFalse(by['Keine eigene Port-Bindung für app2'])

    def test_lab13_global_permit_any_fails_least_privilege(self):
        lab = self.S.load_lab('13-shared-services')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/tn-Shared/brc-dns/subj-subj', mo('vzSubj', {}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'default'}))))
        by = self.by()
        self.assertTrue(by['web1 → dns1 UDP 53'])
        self.assertFalse(by['Least Privilege Web → DNS: nur UDP 53'])


    def test_lab13_zoning_rules_in_consumer_vrf(self):
        """Contract Guide, Consumer VRF enforcement: Contract-Regeln und shsrc_any_any_deny(12) im Consumer-VRF,
        im Provider-VRF nur provider -> 14 permit_override src_dst_any(9)."""
        lab = self.S.load_lab('13-shared-services')
        self.apply(*lab['solutionConfig'])
        e = self.S.engine
        cli = Cli(e, self.S.sim)
        rows = [[c.strip() for c in ln.strip('|').split('|')] for ln in cli.run('leaf102', 'show zoning-rule').split('\n')
                if ln.startswith('|') and 'Rule ID' not in ln]
        dns = next(c for c in e.cls.values() if c['name'] == 'DNS')
        cons_scope = e.A(e.cls['uni/tn-Shop/ap-Webshop/epg-Web']['vrf'])['scope']
        prov_scope = e.A(dns['vrf'])['scope']
        self.assertIn([dns['pcTag'], '14', 'permit_override', 'src_dst_any(9)', prov_scope], [[r[1], r[2], r[8], r[9], r[6]] for r in rows])
        self.assertIn([dns['pcTag'], '0', 'shsrc_any_any_deny(12)', cons_scope], [[r[1], r[2], r[9], r[6]] for r in rows])
        self.assertFalse([r for r in rows if r[7] == 'dns' and r[6] == prov_scope], 'keine Contract-Regeln im Provider-VRF')
        self.assertTrue([r for r in rows if r[7] == 'dns' and r[6] == cons_scope])

    def test_lab09_default_route_external_epg_uses_special_class_ids(self):
        """Contract Guide, L3Out EPG with 0.0.0.0/0: EPG -> 15 und VRF-Class-ID -> EPG, beide uni-dir."""
        lab = self.S.load_lab('09-l3out-bgp')
        self.apply(*lab['solutionConfig'])
        e = self.S.engine
        rows = [[c.strip() for c in ln.strip('|').split('|')] for ln in Cli(e, self.S.sim).run('leaf101', 'show zoning-rule').split('\n')
                if ln.startswith('|') and 'web-to-isp' in ln]
        web = e.cls['uni/tn-Shop/ap-Webshop/epg-Web']['pcTag']
        vrf_tag = e.A(e.cls['uni/tn-Shop/ap-Webshop/epg-Web']['vrf'])['pcTag']
        got = {(r[1], r[2], r[4]) for r in rows}
        self.assertTrue({(web, '15', 'uni-dir'), (vrf_tag, web, 'uni-dir')} <= got, rows)
        # Musterloesung nimmt das Transfernetz ins External EPG auf (Contract Guide): zusaetzlich Regeln mit eigenem pcTag
        ext = e.cls['uni/tn-Shop/out-ISP/instP-Internet']['pcTag']
        self.assertTrue({(web, ext, 'bi-dir'), (ext, web, 'uni-dir-ignore')} <= got, rows)

    def test_lab13_vzany_cannot_provide_inter_vrf_contract(self):
        """Contract Guide: vzAny kann bei Inter-VRF-Contracts nur Consumer sein, nicht Provider."""
        lab = self.S.load_lab('13-shared-services')
        self.apply(*lab['solutionConfig'])
        dns = next(c for c in self.S.engine.cls.values() if c['name'] == 'DNS')
        self.apply((dns['vrf'] + '/any', mo('vzAny', {}, mo('vzRsAnyToProv', {'tnVzBrCPName': 'dns'}))),
                   (dns['dn'] + '/rsprov-dns', mo('fvRsProv', {'status': 'deleted'})))
        r = trace.run(self.S.engine, self.S.sim, 'web1', 'dns1', 'udp', 53)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'INTERVRF_LEAK_MISSING'))
        self.assertIn('vzAny kann bei Inter-VRF-Contracts nur Consumer sein', ' '.join(s['detail'] for s in r['steps']))

    def test_lab09_transfer_subnet_is_class1_without_explicit_subnet(self):
        """Contract Guide, Figures 127-132: Hat das External EPG nur 0.0.0.0/0, gilt die Interface-Adresse des Routers als
        Class-ID 1 und darf ohne Contract zu web1 (Anfrage). Mit dem Transfernetz im External EPG greift der Contract."""
        lab = self.S.load_lab('09-l3out-bgp')
        self.apply(*lab['solutionConfig'])
        self.apply(('uni/tn-Shop/out-ISP/instP-Internet/extsubnet-[172.16.1.0/30]', mo('l3extSubnet', {'status': 'deleted'})))
        r = trace.run(self.S.engine, self.S.sim, 'isp1', 'web1', 'tcp', 22)
        self.assertEqual(r['policy'][0]['code'], 'POLICY_IMPLICIT_CLASS1')
        self.assertEqual(r['policy'][0]['action'], 'permit')
        self.assertEqual(r['reason'], 'POLICY_REPLY_DENIED', 'web1 liegt nicht am Border Leaf: Antwort an Class-ID 15 ohne Contract')
        self.assertFalse(self.by()['Least Privilege Provider → Web: nur Ping'])
        self.S.load_lab('09-l3out-bgp')
        self.apply(*lab['solutionConfig'])
        r = trace.run(self.S.engine, self.S.sim, 'isp1', 'web1', 'tcp', 22)
        self.assertEqual((r['policy'][0]['action'], r['policy'][0]['code']), ('deny', 'POLICY_IMPLICIT_DENY'))
        self.assertTrue(all(self.by().values()))

    def test_lab13_vzany_consumes_inter_vrf_contract(self):
        """Contract Guide, Appendix (Inter-VRF contract with vzAny as the consumer): vzAny im Consumer-VRF konsumiert einen
        globalen Contract, den DNS bereitstellt. Route Leaking und Verkehr funktionieren; im Consumer-VRF stehen 0 <-> Provider
        (globaler pcTag, Prioritaet 10), im Provider-VRF nur Provider -> 14."""
        lab = self.S.load_lab('13-shared-services')
        self.apply(*lab['solutionConfig'])
        self.apply(('uni/tn-common', mo('fvTenant', {}, mo('vzFilter', {'name': 'dns53'}, mo('vzEntry', {
                        'name': 'd', 'etherT': 'ip', 'prot': 'udp', 'dFromPort': '53', 'dToPort': '53'})),
                        mo('vzBrCP', {'name': 'dns-common', 'scope': 'global'}, mo('vzSubj', {'name': 's'},
                           mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'dns53'}))))),
                   ('uni/tn-Shop/ap-Webshop/epg-Web/rsconsIf-dns', mo('fvRsConsIf', {'status': 'deleted'})),
                   ('uni/tn-Shared/ap-Infra/epg-DNS/rsprov-dns', mo('fvRsProv', {'status': 'deleted'})),
                   ('uni/tn-Shared/ap-Infra/epg-DNS', mo('fvAEPg', {}, mo('fvRsProv', {'tnVzBrCPName': 'dns-common'}))),
                   ('uni/tn-Shop/ctx-Prod/any', mo('vzAny', {}, mo('vzRsAnyToCons', {'tnVzBrCPName': 'dns-common'}))))
        e = self.S.engine
        self.assertEqual(trace.run(e, self.S.sim, 'web1', 'dns1', 'udp', 53)['verdict'], 'ALLOW')
        self.assertEqual(trace.run(e, self.S.sim, 'web1', 'dns1', 'udp', 54)['reason'], 'POLICY_IMPLICIT_DENY')
        dns = e.cls['uni/tn-Shared/ap-Infra/epg-DNS']['pcTag']
        self.assertLess(int(dns), 16384, 'Provider bekommt einen globalen pcTag')
        rows = [[c.strip() for c in ln.strip('|').split('|')] for ln in Cli(e, self.S.sim).run('leaf102', 'show zoning-rule').split('\n')
                if ln.startswith('|') and 'Rule ID' not in ln]
        got = {(r[1], r[2], r[9]) for r in rows if r[7] == 'dns-common'}
        self.assertEqual(got, {('0', dns, 'shsrc_any_filt_perm(10)'), (dns, '0', 'shsrc_any_filt_perm(10)')})
        self.assertIn((dns, '14', 'permit_override'), {(r[1], r[2], r[8]) for r in rows})

    def test_lab09_permit_any_to_internet_fails(self):
        lab = self.S.load_lab('09-l3out-bgp')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/tn-Shop/brc-web-to-isp/subj-subj', mo('vzSubj', {}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'default'}))))
        by = self.by()
        self.assertTrue(by['web1 → 1.1.1.1 Ping'])
        self.assertFalse(by['Least Privilege Web → Internet: nur Ping'])
        self.assertFalse(by['Least Privilege Provider → Web: nur Ping'])

    def test_lab10_second_time_source_fails_security(self):
        lab = self.S.load_lab('10-mgmt-ntp')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/fabric/time-default', mo('datetimePol', {}, mo('datetimeNtpProv', {'name': 'pool.ntp.org'}))))
        self.assertFalse(self.by()['Nur die freigegebene Zeitquelle ist eingetragen'])

    def test_lab12_vmm_vms_follow_the_same_policy(self):
        lab = self.S.load_lab('12-vmm-vcenter')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        r = trace.run(self.S.engine, self.S.sim, 'web-vm1', 'app-vm1', 'tcp', 22)
        self.assertEqual(r['reason'], 'POLICY_IMPLICIT_DENY')

    def test_lab14_gateway_in_aci_breaks_guardrail(self):
        lab = self.S.load_lab('14-l2out-migration')
        self.assertIn(trace.run(self.S.engine, self.S.sim, 'web2', 'old-srv', 'icmp')['reason'], ('EP_NOT_LEARNED', 'ARP_UNRESOLVED'))
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        # Abkuerzung: Gateway in die ACI holen (Unicast Routing + Subnetz) statt ARP Flooding -> doppeltes Gateway
        self.apply(('uni/tn-Shop/BD-BD-Migration', mo('fvBD', {'unicastRoute': 'yes'}, mo('fvSubnet', {'ip': '10.10.50.1/24'}))))
        by = self.by()
        self.assertFalse(by['Kein Gateway für 10.10.50.0/24 in der ACI'])
        self.assertFalse(by['Unicast Routing im BD-Migration bleibt aus'])


    def test_lab21_write_role_for_reader_fails_security(self):
        lab = self.S.load_lab('21-aaa-tacacs-rbac')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/userext/user-shopro/userdomain-Shop-Dom/role-tenant-admin', mo('aaaUserRole', {'privType': 'writePriv'})))
        by = self.by()
        self.assertTrue(by['shopro kann sich anmelden'])
        self.assertFalse(by['shopro darf Shop nur lesen'])

    def test_lab23_esg_vzany_rules_use_priority_10(self):
        """Contract Guide, Table 8: Contract zwischen ESG und vzAny -> shsrc_any_filt_perm(10) statt 13/14."""
        lab = self.S.load_lab('23-esg-useg')
        self.apply(*lab['solutionConfig'])
        self.apply(('uni/tn-Shop', mo('fvTenant', {}, mo('vzBrCP', {'name': 'any-to-backend'}, mo('vzSubj', {'name': 's'},
                    mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'icmp'}))))),
                   ('uni/tn-Shop/ctx-Prod/any', mo('vzAny', {}, mo('vzRsAnyToCons', {'tnVzBrCPName': 'any-to-backend'}))),
                   ('uni/tn-Shop/ap-Webshop/esg-Backend', mo('fvESg', {}, mo('fvRsProv', {'tnVzBrCPName': 'any-to-backend'}))))
        e = self.S.engine
        z = Cli(e, self.S.sim).run('leaf101', 'show zoning-rule')
        rows = [ln for ln in z.split('\n') if 'any-to-backend' in ln]
        self.assertTrue(rows and all('shsrc_any_filt_perm(10)' in ln for ln in rows), z)
        esg = e.cls['uni/tn-Shop/ap-Webshop/esg-Backend']
        self.assertEqual(e.packet(e.cls['uni/tn-Shop/ap-Webshop/esg-Frontend'], esg, 'icmp', None, None, 'syn')[0], 'permit')

    def test_lab23_epg_contract_instead_of_esg_and_permit_any(self):
        lab = self.S.load_lab('23-esg-useg')
        # Abkuerzung 1: klassischer EPG-Contract statt ESGs
        self.apply(('uni', mo('fvTenant', {'name': 'Shop'},
                              mo('vzFilter', {'name': 'tcp-8080'}, mo('vzEntry', {'name': 'e', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '8080', 'dToPort': '8080'})),
                              mo('vzBrCP', {'name': 'w2a'}, mo('vzSubj', {'name': 's', 'revFltPorts': 'yes'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'tcp-8080'}))),
                              mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'w2a'})),
                                 mo('fvAEPg', {'name': 'App'}, mo('fvRsProv', {'tnVzBrCPName': 'w2a'}))))))
        by = self.by()
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'tcp', 8080)['verdict'], 'ALLOW')
        self.assertFalse(by['web1 → app1 TCP 8080 über ESGs'], 'funktioniert, aber nicht ueber ESGs')
        # Musterloesung, dann permit any zwischen den ESGs
        self.S.load_lab('23-esg-useg')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/tn-Shop/brc-frontend-to-backend/subj-subj', mo('vzSubj', {}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'default'}))))
        self.assertFalse(self.by()['Least Privilege Web → App: nur TCP 8080'])


    def test_lab15_aggregate_export_leaks_routes(self):
        lab = self.S.load_lab('15-transit-route-control')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/tn-Shop/out-Partner/instP-PartnerNet', mo('l3extInstP', {}, mo('l3extSubnet', {
            'ip': '0.0.0.0/0', 'scope': 'export-rtctrl', 'aggregate': 'export-rtctrl'}))))
        self.assertFalse(self.by()['partner1 lernt 1.1.1.0/24 nicht'])

    def test_lab16_firewall_decides_not_the_contract(self):
        lab = self.S.load_lab('16-service-graph-pbr')
        self.apply(*lab['solutionConfig'])
        self.assertEqual(trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'icmp')['reason'], 'FIREWALL_DENY')
        self.assertTrue(all(self.by().values()))

    def test_lab17_permit_any_to_campus_fails(self):
        lab = self.S.load_lab('17-l3out-vpc-svi-bfd')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/tn-Shop/brc-web-to-campus/subj-subj', mo('vzSubj', {}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'default'}))))
        self.assertFalse(self.by()['Least Privilege Web → Campus: nur Ping'])

    def test_lab18_without_summary_partner_sees_more_specifics(self):
        lab = self.S.load_lab('18-ebgp-loopback-md5-summary')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/tn-Shop/out-Partner/instP-PartnerNet/extsubnet-[10.10.0.0/16]/rsSubnetToRtSumm', mo('l3extRsSubnetToRtSumm', {'status': 'deleted'})))
        by = self.by()
        self.assertFalse(by['partner1 lernt 10.10.10.0/24 nicht einzeln'] and by['partner1 lernt 10.10.20.0/24 nicht einzeln'])


    def test_lab19_track_removes_default_route_on_failure(self):
        lab = self.S.load_lab('19-eigrp-static-track')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        next(r for r in self.S.sim['routers'] if r['name'] == 'inet1')['down'] = True
        self.S.changed()
        self.assertFalse(self.by()['Default Route auf leaf104 aktiv'], 'Mit Track verschwindet die Route bei Ausfall')

    def test_lab20_floating_svi_without_floating_ip_fails(self):
        lab = self.S.load_lab('20-floating-svi')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        dn = next(d for d in self.S.store.by_class('l3extRsDynPathAtt'))
        self.apply((dn, mo('l3extRsDynPathAtt', {'floatingAddr': '0.0.0.0'})))
        self.assertFalse(self.by()['Andere Leafs antworten unter 172.16.10.100/24'])

    def test_lab22_inb_domain_on_server_aaep_fails_security(self):
        lab = self.S.load_lab('22-inband-management')
        self.apply(*lab['solutionConfig'])
        self.assertTrue(all(self.by().values()))
        self.apply(('uni/infra/attentp-AAEP-Server', mo('infraAttEntityP', {}, mo('infraRsDomP', {'tDn': 'uni/phys-PhysDom-INB'}))))
        self.assertFalse(self.by()['vlan-90 kommt nicht auf die Server-Ports'])


    def test_lab27_relay_without_tightening_contract_fails(self):
        lab = self.S.load_lab('27-dhcp-relay')
        self.apply(lab['solutionConfig'][0])
        by = self.by()
        self.assertTrue(by['pc1 hat ein DHCP-Lease'])
        self.assertFalse(by['Least Privilege Clients → Services: nur Ping (und DHCP)'], 'der Contract erlaubt noch alles')


class TestOperationsLabs(unittest.TestCase):
    """Labs 41 (Routing vs. Contract), 42 (Rueckweg), 43 (Change mit Snapshot)."""

    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0

    def apply(self, *items, audit=False):
        for dn, body in items:
            ch = post(self.S.store, dn, body)
            if audit:
                self.S.audit('admin', ch)
        self.S.changed()

    def by(self):
        r = self.S.check_lab()
        return r, {c['desc']: c['ok'] for c in r['checks']}

    def tr(self, *a):
        return trace.run(self.S.engine, self.S.sim, *a)

    def test_lab41_faults_appear_in_order(self):
        lab = self.S.load_lab('41-route-or-contract')
        self.assertEqual(self.tr('web1', '8.8.8.8', 'icmp')['reason'], 'ROUTE_MISSING')
        self.apply(lab['solutionConfig'][0])
        self.assertEqual(self.tr('web1', '8.8.8.8', 'icmp')['reason'], 'POLICY_IMPLICIT_DENY')
        self.apply(lab['solutionConfig'][1])
        self.assertEqual(self.tr('web1', '8.8.8.8', 'icmp')['verdict'], 'ALLOW')

    def test_lab41_app_without_route_reflector_does_not_count_as_policy_block(self):
        self.S.load_lab('41-route-or-contract')
        r, by = self.by()
        self.assertFalse(by['app1 → 8.8.8.8 durch die Policy blockiert'], 'blockiert durch fehlende Route, nicht durch Policy')

    def test_lab41_permit_any_to_internet_fails(self):
        lab = self.S.load_lab('41-route-or-contract')
        self.apply(lab['solutionConfig'][0], ('uni', mo('fvTenant', {'name': 'Shop'},
            mo('vzFilter', {'name': 'any'}, mo('vzEntry', {'name': 'any'})),
            mo('vzBrCP', {'name': 'all'}, mo('vzSubj', {'name': 's'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'any'}))),
            mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'all'}))),
            mo('l3extOut', {'name': 'WAN'}, mo('l3extInstP', {'name': 'Internet'}, mo('fvRsProv', {'tnVzBrCPName': 'all'}))))))
        r, by = self.by()
        self.assertTrue(by['web1 → 8.8.8.8 HTTPS'])
        self.assertFalse(by['Least Privilege web1 → Internet: nur Ping und HTTPS'])

    def test_lab42_announcing_app_subnet_fails(self):
        lab = self.S.load_lab('42-return-path')
        self.assertEqual(self.tr('web1', '8.8.8.8', 'icmp')['reason'], 'RETURN_ROUTE_MISSING')
        bd_app = ('uni/tn-Shop/BD-BD-App', mo('fvBD', {}, mo('fvSubnet', {'ip': '10.10.20.1/24', 'scope': 'public'}),
                                                  mo('fvRsBDToOut', {'tnL3extOutName': 'WAN'})))
        self.apply(*lab['solutionConfig'], bd_app)
        r, by = self.by()
        self.assertTrue(by['10.10.20.0/24 wird nicht angekündigt'], 'BD-App ist ohne Contract zum External EPG nicht auf dem Border Leaf aktiv')
        self.apply(('uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-internet'}))))
        r, by = self.by()
        self.assertTrue(by['wan1 kennt 10.10.10.0/24'])
        self.assertFalse(by['10.10.20.0/24 wird nicht angekündigt'])

    def change(self):
        return self.S.lab('43-change-snapshot')['solutionConfig'][1][1]

    def test_lab43_full_process(self):
        self.S.load_lab('43-change-snapshot')
        self.S.snapshot('create', 'vor-CHG4711-a')
        self.apply(self.change(), audit=True)
        self.assertEqual(self.tr('web1', 'app1', 'tcp', 443)['reason'], 'POLICY_IMPLICIT_DENY')
        self.S.snapshot('rollback', 'vor-CHG4711-a')
        r, by = self.by()
        self.assertEqual([k for k, v in by.items() if not v], [])

    def test_lab43_without_snapshot_or_without_change_fails(self):
        self.S.load_lab('43-change-snapshot')
        r, by = self.by()
        self.assertFalse(by['Sicherungspunkt vor-CHG4711 in diesem Lab angelegt'])
        self.assertFalse(by['Change CHG-4711 wurde eingespielt (Audit-Log)'], 'nichts tun ist keine Loesung')

    def test_lab43_old_snapshot_from_before_lab_start_does_not_count(self):
        self.S.snapshot('create', 'vor-CHG4711-alt')
        import time
        time.sleep(1.1)
        self.S.load_lab('43-change-snapshot')
        r, by = self.by()
        self.assertFalse(by['Sicherungspunkt vor-CHG4711 in diesem Lab angelegt'])

    def test_lab43_hand_fix_instead_of_rollback_fails(self):
        self.S.load_lab('43-change-snapshot')
        self.S.snapshot('create', 'vor-CHG4711')
        self.apply(self.change(), audit=True)
        self.apply(('uni/tn-Shop/flt-https/e-https', mo('vzEntry', {'dFromPort': '443', 'dToPort': '443'})), audit=True)
        r, by = self.by()
        self.assertTrue(by['web1 → app1 HTTPS funktioniert'])
        self.assertFalse(by['Change vollständig zurückgerollt (keine EPG Api)'])


class TestPolicyMatrix(unittest.TestCase):
    def test_matrix_matches_trace_and_lab40_design(self):
        from dcprep import flows
        S = Sim(tempfile.mkdtemp(), 'admin')
        S.sim['settings']['discoverySeconds'] = 0
        lab = S.load_lab('40-it-ot-segmentation')
        for dn, body in lab['solutionConfig']:
            post(S.store, dn, body)
        S.changed()
        m = flows.policy_matrix(S)
        self.assertEqual(m['vrf'], 'uni/tn-Werk/ctx-OT')
        z = lambda n: 'uni/tn-Werk/ap-Linie1/epg-' + n
        cell = lambda a, b: m['cells'][z(a)][z(b)]
        self.assertEqual(cell('SCADA', 'PLC')['open'], ['tcp/502'])
        self.assertEqual(cell('SCADA', 'PLC')['rules'], ['Werk:scada-to-plc'])
        self.assertEqual(cell('ENG', 'PLC')['open'], ['tcp/44818'])
        self.assertEqual(sorted(cell('MON', 'SCADA')['open']), ['icmp', 'udp/161'])
        self.assertEqual(cell('PLC', 'PLC')['open'], [], 'Isolation in der Zone PLC')
        self.assertTrue(cell('ENG', 'ENG')['all'], 'ohne Isolation ist innerhalb der EPG alles offen')
        self.assertEqual(cell('PLC', 'SCADA')['open'], [])
        # gleiche Entscheidung wie der Traffic-Test
        self.assertEqual(trace.run(S.engine, S.sim, 'scada1', 'plc1', 'tcp', 502)['verdict'], 'ALLOW')
        self.assertEqual(trace.run(S.engine, S.sim, 'scada1', 'plc1', 'tcp', 22)['verdict'], 'DROP')


if __name__ == '__main__':
    unittest.main()


class TestOverlay(unittest.TestCase):
    """B-08: Overlay je EPG/BD/VRF aus der Engine (Deployment auf Leafs, gelernte Hosts)."""

    def test_overlay_follows_deployment_and_learning(self):
        S = Sim(tempfile.mkdtemp(), 'admin')
        S.sim['settings']['discoverySeconds'] = 0
        S.load_lab('37-link-or-policy')
        ov = {o['dn']: o for o in S.engine.overlay()}
        app = ov['uni/tn-Shop/ap-Webshop/epg-App']
        self.assertEqual((app['kind'], app['leafs'], app['hosts']), ('EPG', ['leaf102'], []), 'deployed, aber app1 ist nicht gelernt')
        self.assertEqual(ov['uni/tn-Shop/ctx-Prod']['leafs'], ['leaf101', 'leaf102'])
        self.assertIn('web1', ov['uni/tn-Shop/BD-BD-Web']['hosts'])


class TestSimClock(unittest.TestCase):
    """B-07: simulierte Uhr - Discovery laeuft nach Sekunden-Einstellung, Vorspulen ersetzt das Warten."""

    def test_discovery_waits_for_clock_and_advance_completes_it(self):
        S = Sim(tempfile.mkdtemp(), 'admin')
        S.sim['settings']['discoverySeconds'] = 120
        S.reset('empty')
        post(S.store, 'uni/controller/nodeidentpol', mo('fabricNodeIdentP', {'serial': 'SAL1931LA01', 'nodeId': '101', 'name': 'leaf101'}))
        S.changed()
        state = lambda: next(n['state'] for n in S.engine.nodes.values() if n['serial'] == 'SAL1931LA01')
        self.assertNotEqual(state(), 'active', 'ohne Vorspulen dauert die Discovery')
        self.assertIsNotNone(S.engine.next_event)
        for _ in range(5):
            if state() == 'active':
                break
            r = S.advance_clock(to_next=True)
            self.assertGreater(r['advanced'], 0)
        self.assertEqual(state(), 'active', 'nach dem Vorspulen ist leaf101 aktiv')
        self.assertGreater(S.sim['clockOffset'], 100)

    def test_fault_lifecycle_on_sim_clock(self):
        """B-07: soaking -> raised, behoben -> retaining (cleared) -> weg; Bewertung zaehlt cleared nicht."""
        S = Sim(tempfile.mkdtemp(), 'admin')
        S.sim['settings'].update({'discoverySeconds': 0, 'faultSoakSeconds': 120, 'faultRetainSeconds': 300})
        S.load_lab('44-access-diagnosis')
        S.sim['settings'].update({'faultSoakSeconds': 120, 'faultRetainSeconds': 300})
        S.changed()
        app = 'uni/tn-Shop/ap-Webshop/epg-App/fault-F0467'
        lc = lambda: S.store.attrs(app)['lc'] if app in S.store.objs else None
        self.assertEqual(lc(), 'soaking')
        S.advance_clock(to_next=True)
        self.assertEqual(lc(), 'raised')
        post(S.store, 'uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {}, mo('fvRsDomAtt', {'tDn': 'uni/phys-PhysDom-Server'})))
        S.changed()
        self.assertEqual((lc(), S.store.attrs(app)['severity']), ('retaining', 'cleared'))
        nof = [c for c in S.check_lab(count=False)['checks'] if c['desc'].startswith('Keine Konfigurationsfehler')][0]
        self.assertIn('1 Fault', nof['info'], 'der DB-Fault ist noch aktiv, der behobene zaehlt nicht')
        for _ in range(4):
            if lc() is None:
                break
            S.advance_clock(to_next=True)
        self.assertIsNone(lc(), 'nach der Retention ist der Fault weg')

    def test_fault_lifecycle_off_by_default(self):
        S = Sim(tempfile.mkdtemp(), 'admin')
        S.sim['settings']['discoverySeconds'] = 0
        S.load_lab('44-access-diagnosis')
        self.assertEqual(S.store.attrs('uni/tn-Shop/ap-Webshop/epg-App/fault-F0467')['lc'], 'raised')

    def test_advance_is_bounded_and_noop_without_event(self):
        S = Sim(tempfile.mkdtemp(), 'admin')
        S.sim['settings']['discoverySeconds'] = 0
        S.changed()
        self.assertEqual(S.advance_clock(to_next=True)['advanced'], 0.0)
        self.assertEqual(S.advance_clock(10 ** 9)['advanced'], 86400.0)


class TestCliHonesty(unittest.TestCase):
    """B-14: Das Terminal sagt, was echt ist, was simulator-spezifisch ist und was es nicht kann."""

    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0
        self.S.load_lab(LAB)
        self.cli = Cli(self.S.engine, self.S.sim)

    def run_(self, node, cmd):
        return self.cli.run(node, cmd), self.cli.kind

    def test_known_commands_are_marked_by_origin(self):
        self.assertEqual(self.run_('apic1', 'show tenant')[1], 'device')
        self.assertEqual(self.run_('leaf101', 'show zoning-rule')[1], 'device')
        self.assertEqual(self.run_('apic1', 'show snmp')[1], 'sim')
        self.assertIn('[S]', self.run_('apic1', 'help')[0])

    def test_unsupported_commands_name_a_supported_path(self):
        cases = {('apic1', 'show running-config tenant Shop'): 'moquery',
                 ('leaf101', 'show running-config'): 'moquery',
                 ('apic1', 'show ip route vrf Shop:Prod'): 'ssh leaf101',
                 ('leaf101', 'moquery -c fvBD'): 'exit',
                 ('leaf101', 'ping 10.10.20.11'): 'Traffic Inspector',
                 ('apic1', 'configure terminal'): 'REST-API',
                 ('apic1', 'frobnicate'): 'help'}
        for (node, cmd), hint in cases.items():
            with self.subTest(cmd=cmd):
                out, kind = self.run_(node, cmd)
                self.assertEqual(kind, 'unsupported')
                self.assertIn('In der Simulation nicht unterstuetzt', out)
                self.assertIn('Stattdessen' if hint != 'help' else '"help"', out)
                self.assertIn(hint, out)

    def test_no_shell_and_no_config_change(self):
        before = json.dumps(self.S.store.dump_config(), sort_keys=True, default=str)
        for cmd in ('ls; rm -rf /', '$(id)', 'bash', 'python3 -c "print(1)"', 'conf t'):
            out, kind = self.run_('apic1', cmd)
            self.assertEqual(kind, 'unsupported', cmd)
        self.assertEqual(json.dumps(self.S.store.dump_config(), sort_keys=True, default=str), before)
