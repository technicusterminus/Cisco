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


class TestRequirementLabs(unittest.TestCase):
    """Alle Labs im Anforderungsformat: Aufbau, keine Loesung im Aufgabentext, Abkuerzungen scheitern."""

    LEAKS = {
        '02-access-policies': ['AAEP', 'Attachable', 'Policy Group', 'Switch Profile', 'Interface Profile', 'VLAN Pool'],
        '03-tenant-epg': ['Static Port', 'fvRsPathAtt', 'Domain-Zuordnung'],
        '04-contracts': ['vzAny', 'EPG Collection', 'Consumer', 'Provider', 'Reverse', 'konsumiert'],
        '07-troubleshooting': ['8080', 'Unicast Routing', 'BD-Bakup', 'Reverse', '149', 'Port Block'],
        '32-https-least-privilege': ['Consumer', 'Provider', 'web-to-app-https', 'Reverse'],
        '33-same-epg': ['Static Port', 'fvRsPathAtt'],
        '34-two-epgs-same-bd': ['Consumer', 'Provider', 'admin-to-web'],
        '35-port-and-direction': ['8443', 'Consumer', 'Provider', 'vertauscht', 'konsumiert'],
        '36-endpoint-move': ['eth1/7', 'eth1/6', 'pc-x', 'Static Port', 'Bindung'],
        '37-link-or-policy': ['Disabled', 'deaktiviert', 'Kabel', 'LINK_DOWN', 'Contract', 'eth1/2 ist'],
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


if __name__ == '__main__':
    unittest.main()
