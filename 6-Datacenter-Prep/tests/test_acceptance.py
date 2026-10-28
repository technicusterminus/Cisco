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


if __name__ == '__main__':
    unittest.main()
