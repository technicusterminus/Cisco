"""Abnahmefall der Lernplattform: HTTPS von WEB zu APP mit Least Privilege (Lab 32).

Prueft die ganze Kette: Ausgangszustand -> Drop mit Policy-Ursache -> Loesung -> ALLOW fuer HTTPS,
Drop fuer alles andere -> Lab-Bewertung nach Zustand -> Permit-any faellt durch -> Reset.
Dazu die Connectivity-Regeln, die das Lab braucht, und GUI/REST/CLI auf demselben Zustand.

Aufruf: python3 -m unittest discover -s tests
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

from dcprep.server import Sim, serve  # noqa: E402
from dcprep.model import post  # noqa: E402
from dcprep.cli import Cli  # noqa: E402
from dcprep import trace  # noqa: E402

LAB = '32-least-privilege-https'
EPG = 'uni/tn-Portal/ap-Portal/epg-'


def mo(cls, attrs=None, *children):
    body = {'attributes': attrs or {}}
    if children:
        body['children'] = list(children)
    return {cls: body}


def tenant(*kids):
    return mo('fvTenant', {'name': 'Portal'}, *kids)


def entry(name, **a):
    return mo('vzEntry', dict({'name': name, 'etherT': 'ip'}, **a))


def flt(name, *entries):
    return mo('vzFilter', {'name': name}, *entries)


def contract(name, filters, rev='yes', scope='context'):
    return mo('vzBrCP', {'name': name, 'scope': scope},
              mo('vzSubj', {'name': 's', 'revFltPorts': rev}, *[mo('vzRsSubjFiltAtt', {'tnVzFilterName': f}) for f in filters]))


def rel(epg, cls, name):
    return mo('fvAp', {'name': 'Portal'}, mo('fvAEPg', {'name': epg}, mo(cls, {'tnVzBrCPName': name})))


HTTPS = flt('https', entry('tcp-443', prot='tcp', dFromPort='443', dToPort='443'))


def solution(cname='web-to-app-https', filters=('https',), extra=(), rev='yes', cons='WEB', prov='APP'):
    return tenant(HTTPS, *extra, contract(cname, list(filters), rev=rev), rel(cons, 'fvRsCons', cname), rel(prov, 'fvRsProv', cname))


class LabBase(unittest.TestCase):
    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.S.sim['settings']['discoverySeconds'] = 0
        self.S.load_lab(LAB)

    def apply(self, tree, url='uni'):
        post(self.S.store, url, tree)
        self.S.changed()

    def t(self, src, dst, proto='tcp', port=443):
        return trace.run(self.S.engine, self.S.sim, src, dst, proto, port)

    def grade(self):
        return self.S.check_lab()

    def failed(self, chk, category=None):
        return [c['desc'] for c in chk['checks'] if not c['ok'] and (category is None or c['category'] == category)]


class TestAcceptance(LabBase):
    """Abschnitt 14 des Auftrags, Schritt fuer Schritt."""

    def test_start_state(self):
        # 1.-4. Hosts gelernt, verschiedene EPGs, Anbindung und Routing da, keine Policy
        for h, epg in (('web1', 'WEB'), ('app1', 'APP'), ('mon1', 'MON')):
            hs = self.S.engine.hosts[h]
            self.assertTrue(hs['learned'], h)
            self.assertEqual(hs['epg'], EPG + epg)
        self.assertEqual(self.S.engine.contracts, {})
        # 5./6. HTTPS faellt, und zwar an der Policy - nicht pauschal
        r = self.t('web1', 'app1')
        self.assertEqual(r['verdict'], 'DROP')
        self.assertEqual(r['reason'], 'POLICY_IMPLICIT_DENY')
        self.assertEqual(r['failedAt']['layer'], 'policy')
        self.assertIn(EPG + 'WEB', r['refs'])
        self.assertIn(EPG + 'APP', r['refs'])
        self.assertTrue(any('Gateway' in s['title'] and s['ok'] for s in r['steps']), 'Routing-Grundlage muss vor der Policy ok sein')
        self.assertTrue(r['hint'])
        # Ausgangszustand besteht nicht versehentlich
        chk = self.grade()
        self.assertIn('web1 → app1 HTTPS (TCP 443) erreichbar', self.failed(chk, 'functional'))
        self.assertLess(chk['passed'], chk['total'])

    def test_solution_passes(self):
        # 7.-8. Filter, Contract, Consumer/Provider
        self.apply(solution())
        r = self.t('web1', 'app1')
        # 9. HTTPS gemaess Richtungsmodell: Anfrage Consumer->Provider, Antwort mit getauschten Ports
        self.assertEqual(r['verdict'], 'ALLOW', r['explanation'])
        phases = {p['phase']: p for p in r['policy']}
        self.assertEqual(phases['Anfrage']['direction'], 'c2p')
        self.assertEqual(phases['Antwort']['direction'], 'p2c')
        self.assertEqual(phases['Anfrage']['contract'], 'uni/tn-Portal/brc-web-to-app-https')
        # 10. SSH bleibt blockiert - an der Policy, obwohl app1 auf 22 lauscht
        r = self.t('web1', 'app1', 'tcp', 22)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_IMPLICIT_DENY'))
        # 11. Bewertung nach Zustand
        chk = self.grade()
        self.assertEqual(self.failed(chk), [])
        self.assertEqual(chk['categories']['functional']['passed'], 1)
        self.assertEqual(chk['categories']['security']['passed'], chk['categories']['security']['total'])

    def test_permit_any_fails_security(self):
        # 12. Permit-any: Funktion ja, Least Privilege nein
        self.apply(solution(filters=('default',)))  # Filter "default" aus Tenant common = alles
        chk = self.grade()
        self.assertEqual(self.failed(chk, 'functional'), [])
        sec = self.failed(chk, 'security')
        self.assertIn('Least Privilege: zwischen WEB und APP ist nur TCP 443 freigegeben', sec)
        self.assertIn('web1 → app1 SSH (TCP 22) bleibt blockiert', sec)
        self.assertIn('web1 → app1 Ping bleibt blockiert (ICMP ist kein HTTPS)', sec)
        info = next(c['info'] for c in chk['checks'] if c['desc'].startswith('Least'))
        self.assertIn('Zu breit', info)

    def test_reset_restores_start(self):
        # 13. Reset stellt den definierten Ausgangszustand wieder her
        fresh = Sim(tempfile.mkdtemp(), 'admin')
        fresh.load_lab(LAB)
        self.apply(solution())
        self.assertNotEqual(config(self.S), config(fresh))
        self.S.lab_op({'op': 'reset', 'id': LAB})
        self.assertEqual(config(self.S), config(fresh))
        self.assertEqual(self.S.engine.contracts, {})
        self.assertEqual(self.t('web1', 'app1')['reason'], 'POLICY_IMPLICIT_DENY')
        self.assertEqual(self.S.sim['hosts'], fresh.sim['hosts'])


def config(S):
    """Konfiguration ohne Zeitstempel (modTs haengt an der Uhr, nicht am Inhalt)."""
    rows = []
    for dn, cls, attrs in S.store.dump_config():
        rows.append(json.dumps([dn, cls, {k: v for k, v in attrs.items() if k != 'modTs'}], sort_keys=True))
    return sorted(rows)


class TestEquivalentSolutions(LabBase):
    def test_other_names_and_named_port(self):
        f = flt('tls', entry('e1', prot='tcp', dFromPort='https', dToPort='https'))
        self.apply(tenant(f, contract('c1', ['tls']), rel('WEB', 'fvRsCons', 'c1'), rel('APP', 'fvRsProv', 'c1')))
        self.assertEqual(self.failed(self.grade()), [])

    def test_two_contracts_each_minimal(self):
        # zwei Contracts mit demselben schmalen Filter sind gleichwertig
        self.apply(tenant(HTTPS, contract('a', ['https']), contract('b', ['https']),
                          rel('WEB', 'fvRsCons', 'a'), rel('APP', 'fvRsProv', 'a'), rel('WEB', 'fvRsCons', 'b'), rel('APP', 'fvRsProv', 'b')))
        self.assertEqual(self.failed(self.grade()), [])

    def test_vzany_provider_is_too_wide(self):
        self.apply(tenant(HTTPS, contract('c', ['https']), rel('WEB', 'fvRsCons', 'c')))
        self.apply(mo('vzAny', {}, mo('vzRsAnyToProv', {'tnVzBrCPName': 'c'})), 'uni/tn-Portal/ctx-Prod/any')
        chk = self.grade()
        self.assertEqual(self.failed(chk, 'functional'), [])
        self.assertIn('web1 → mon1 HTTPS blockiert (WEB erreicht nur APP)', self.failed(chk, 'security'))

    def test_vzany_consumer_is_too_wide(self):
        self.apply(tenant(HTTPS, contract('c', ['https']), rel('APP', 'fvRsProv', 'c')))
        self.apply(mo('vzAny', {}, mo('vzRsAnyToCons', {'tnVzBrCPName': 'c'})), 'uni/tn-Portal/ctx-Prod/any')
        chk = self.grade()
        self.assertEqual(self.failed(chk, 'functional'), [])
        self.assertIn('mon1 → app1 HTTPS blockiert (keine neue Freigabe für MON)', self.failed(chk, 'security'))

    def test_port_range_too_wide(self):
        wide = flt('web', entry('r', prot='tcp', dFromPort='1', dToPort='1024'))
        self.apply(tenant(wide, contract('c', ['web']), rel('WEB', 'fvRsCons', 'c'), rel('APP', 'fvRsProv', 'c')))
        chk = self.grade()
        self.assertEqual(self.failed(chk, 'functional'), [])
        self.assertIn('Least Privilege: zwischen WEB und APP ist nur TCP 443 freigegeben', self.failed(chk, 'security'))

    def test_unenforced_vrf_is_too_wide(self):
        self.apply(tenant(mo('fvCtx', {'name': 'Prod', 'pcEnfPref': 'unenforced'})))
        chk = self.grade()
        self.assertEqual(self.failed(chk, 'functional'), [])
        self.assertTrue(len(self.failed(chk, 'security')) >= 3)


class TestConnectivityRules(LabBase):
    def test_icmp_not_permitted_by_tcp_filter(self):
        self.apply(solution())
        r = self.t('web1', 'app1', 'icmp', 0)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_IMPLICIT_DENY'))

    def test_wrong_port(self):
        self.apply(tenant(flt('alt', entry('e', prot='tcp', dFromPort='8443', dToPort='8443')), contract('c', ['alt']),
                          rel('WEB', 'fvRsCons', 'c'), rel('APP', 'fvRsProv', 'c')))
        self.assertEqual(self.t('web1', 'app1')['reason'], 'POLICY_IMPLICIT_DENY')

    def test_wrong_protocol(self):
        self.apply(tenant(flt('u', entry('e', prot='udp', dFromPort='443', dToPort='443')), contract('c', ['u']),
                          rel('WEB', 'fvRsCons', 'c'), rel('APP', 'fvRsProv', 'c')))
        # TCP 443 passt nicht auf einen UDP-Filter
        self.assertEqual(self.t('web1', 'app1')['reason'], 'POLICY_IMPLICIT_DENY')
        # UDP 443 laesst die Fabric durch, aber app1 hat dort keinen Dienst
        self.assertEqual(self.t('web1', 'app1', 'udp', 443)['reason'], 'SERVICE_UNAVAILABLE')

    def test_swapped_consumer_provider(self):
        self.apply(solution(cons='APP', prov='WEB'))
        r = self.t('web1', 'app1')
        self.assertEqual(r['verdict'], 'DROP')
        self.assertEqual(r['reason'], 'POLICY_IMPLICIT_DENY')
        # Gegenrichtung funktioniert dann, weil web1 auf 443 lauscht - genau das, was die Anforderung nicht will
        self.assertEqual(self.t('app1', 'web1')['verdict'], 'ALLOW')
        self.assertIn('app1 → web1 HTTPS blockiert (APP baut keine Verbindung zu WEB auf)', self.failed(self.grade(), 'security'))

    def test_reply_needs_reverse_ports(self):
        self.apply(solution(rev='no'))
        r = self.t('web1', 'app1')
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_REPLY_DENY'))
        self.assertTrue(any(s['title'].startswith('Policy Anfrage') and s['ok'] for s in r['steps']))

    def test_provider_cannot_initiate(self):
        self.apply(solution())
        r = self.t('app1', 'web1')
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_IMPLICIT_DENY'))

    def test_permit_does_not_create_service(self):
        # Freigabe ersetzt keinen Dienst: tcp/8443 erlaubt, app1 lauscht dort nicht
        self.apply(tenant(flt('alt', entry('e', prot='tcp', dFromPort='8443', dToPort='8443')), contract('c', ['alt']),
                          rel('WEB', 'fvRsCons', 'c'), rel('APP', 'fvRsProv', 'c')))
        r = self.t('web1', 'app1', 'tcp', 8443)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'SERVICE_UNAVAILABLE'))
        self.assertEqual(r['failedAt']['layer'], 'service')

    def test_same_epg_and_isolation(self):
        self.S.sim['hosts'].append({'name': 'web2', 'mac': '00:50:56:32:10:12', 'ip': '10.32.10.12/24', 'gw': '10.32.10.1', 'vlan': 110,
                                    'links': [['SAL1931LA02', 'eth1/1']], 'bond': 'none', 'services': ['tcp/443']})
        self.apply(tenant(mo('fvAp', {'name': 'Portal'}, mo('fvAEPg', {'name': 'WEB'}, mo('fvRsPathAtt', {
            'tDn': 'topology/pod-1/paths-102/pathep-[eth1/1]', 'encap': 'vlan-110', 'mode': 'regular'})))))
        r = self.t('web1', 'web2')
        self.assertEqual(r['verdict'], 'ALLOW', r['explanation'])
        self.assertEqual(r['policy'][0]['kind'], 'same-epg')
        self.apply(tenant(mo('fvAp', {'name': 'Portal'}, mo('fvAEPg', {'name': 'WEB', 'pcEnfPref': 'enforced'}))))
        r = self.t('web1', 'web2')
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_INTRA_EPG_ISOLATION'))

    def test_missing_access_path(self):
        # Ein Contract ersetzt keine physische Anbindung: Static Path weg -> Endpoint nicht gelernt
        self.apply(solution())
        self.S.store.delete(EPG + 'APP/rspathAtt-[topology/pod-1/paths-102/pathep-[eth1/2]]')
        self.S.changed()
        r = self.t('web1', 'app1')
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'EP_NOT_LEARNED'))
        self.assertEqual(r['failedAt']['layer'], 'endpoint')

    def test_missing_gateway(self):
        self.apply(solution())
        self.S.store.delete('uni/tn-Portal/BD-BD-App/subnet-[10.32.20.1/24]')
        self.S.changed()
        r = self.t('web1', 'app1')
        self.assertEqual(r['verdict'], 'DROP')
        self.assertIn(r['reason'], ('IP_NOT_LEARNED', 'GATEWAY', 'NO_ROUTE'))
        self.assertEqual(r['failedAt']['layer'], 'l3')

    def test_preferred_group(self):
        self.apply(tenant(mo('fvCtx', {'name': 'Prod'}, mo('vzAny', {'prefGrMemb': 'enabled'})),
                          mo('fvAp', {'name': 'Portal'}, mo('fvAEPg', {'name': 'WEB', 'prefGrMemb': 'include'}),
                             mo('fvAEPg', {'name': 'APP', 'prefGrMemb': 'include'}))))
        r = self.t('web1', 'app1', 'tcp', 22)
        self.assertEqual(r['verdict'], 'ALLOW')
        self.assertEqual(r['policy'][0]['kind'], 'preferred-group')
        # MON ist nicht Mitglied: weiter Implicit Deny
        self.assertEqual(self.t('mon1', 'app1')['reason'], 'POLICY_IMPLICIT_DENY')

    def test_deny_filter_wins(self):
        deny = mo('vzBrCP', {'name': 'c'}, mo('vzSubj', {'name': 'allow'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'https'})),
                  mo('vzSubj', {'name': 'block'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'https', 'action': 'deny'})))
        self.apply(tenant(HTTPS, deny, rel('WEB', 'fvRsCons', 'c'), rel('APP', 'fvRsProv', 'c')))
        self.assertEqual(self.t('web1', 'app1')['reason'], 'POLICY_DENY_FILTER')

    def test_unsupported_unidirectional_subject(self):
        self.apply(tenant(HTTPS, mo('vzBrCP', {'name': 'uni'}, mo('vzSubj', {'name': 's'}, mo('vzInTerm', {}), mo('vzOutTerm', {}))),
                          rel('WEB', 'fvRsCons', 'uni'), rel('APP', 'fvRsProv', 'uni')))
        r = self.t('web1', 'app1')
        self.assertEqual((r['verdict'], r['reason']), ('UNRESOLVED', 'POLICY_UNSUPPORTED'))
        self.assertFalse(r['ok'])

    def test_invalid_input_is_unresolved(self):
        self.assertEqual(self.t('gibtsnicht', 'app1')['verdict'], 'UNRESOLVED')
        self.assertEqual(self.t('web1', 'app1', 'tcp', 0)['reason'], 'INPUT_PORT_MISSING')

    def test_deterministic(self):
        self.apply(solution())
        a = [self.t('web1', 'app1', p, n) for p, n in (('tcp', 443), ('tcp', 22), ('icmp', 0))]
        b = [self.t('web1', 'app1', p, n) for p, n in (('tcp', 443), ('tcp', 22), ('icmp', 0))]
        self.assertEqual(a, b)


class TestLabEngine(LabBase):
    def test_hints_staged_and_side_effect_free(self):
        before = copy.deepcopy(self.S.store.dump_config())
        r1 = self.S.lab_hint()
        self.assertEqual([h['level'] for h in r1['hints']], [1])
        r2 = self.S.lab_hint()
        self.assertEqual([h['level'] for h in r2['hints']], [1, 2])
        self.assertEqual(self.S.lab_hint(4)['level'], 4)
        self.assertEqual(self.S.lab_hint(1)['level'], 4, 'Hinweise lassen sich nicht zurueckdrehen')
        self.assertEqual(self.S.store.dump_config(), before)
        self.assertEqual(self.grade()['hintsUsed'], 4)

    def test_solution_not_in_task_text(self):
        lab = self.S.lab(LAB)
        text = json.dumps([lab['intro'], lab['tasks']], ensure_ascii=False)
        for word in ('web-to-app-https', 'Provider', 'Consumer', 'revFltPorts', 'dFromPort'):
            self.assertNotIn(word, text)

    def test_exam_mode_hides_help(self):
        self.S.set_lab_mode('exam')
        view = self.S.state()['lab']
        self.assertIsNone(view['solution'])
        self.assertEqual(view['hints'], [])
        self.assertTrue(all('hint' not in t for t in view['tasks']))
        with self.assertRaises(Exception):
            self.S.lab_hint()
        self.S.set_lab_mode('guided')
        self.assertTrue(self.S.state()['lab']['solution'])

    def test_grader_and_inspector_share_engine(self):
        self.apply(solution())
        chk = self.grade()
        row = next(c for c in chk['checks'] if c['desc'].startswith('web1 → app1 HTTPS'))
        r = self.t('web1', 'app1')
        self.assertEqual((row['verdict'], row['reason']), (r['verdict'], r['reason']))

    def test_cli_sees_same_state(self):
        cli = Cli(self.S.engine, self.S.sim)
        before = cli.run('leaf102', 'show zoning-rule')
        self.apply(solution())
        cli = Cli(self.S.engine, self.S.sim)
        after = cli.run('leaf102', 'show zoning-rule')
        self.assertNotEqual(before, after)
        self.assertIn('permit', after)

    def test_progress_survives_reload(self):
        self.apply(solution())
        self.assertTrue(self.grade()['passed'])
        again = Sim(self.S.data_dir, 'admin')
        self.assertEqual(again.sim['lab'], LAB)
        self.assertTrue(again.progress()[LAB]['done'])
        self.assertEqual(again.engine.contracts.keys(), self.S.engine.contracts.keys())


class TestEndToEndRest(unittest.TestCase):
    """Ueber HTTP wie Browser und Automatisierung: Lab laden, pruefen, per REST loesen, pruefen, zuruecksetzen."""

    def setUp(self):
        self.hub, self.httpd = serve('127.0.0.1', 0, tempfile.mkdtemp(), 'admin', discovery=0)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def req(self, method, path, body=None, cookie=None):
        r = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), method=method,
                                   data=json.dumps(body).encode() if body is not None else None)
        if cookie:
            r.add_header('Cookie', cookie)
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, json.loads(resp.read() or b'null'), resp.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b'null'), e.headers

    def login(self):
        s, j, h = self.req('POST', '/dp/login', {'name': 'standard', 'password': ''})
        dp = h['Set-Cookie'].split(';')[0]
        s, j, h = self.req('POST', '/api/aaaLogin.json', {'aaaUser': {'attributes': {'name': 'admin', 'pwd': 'admin'}}}, dp)
        return dp + '; APIC-cookie=' + j['imdata'][0]['aaaLogin']['attributes']['token']

    def test_full_lab_over_http(self):
        ck = self.login()
        self.assertEqual(self.req('POST', '/sim/labs/op', {'op': 'resume', 'id': LAB}, ck)[0], 200)
        s, r, _ = self.req('POST', '/sim/traffic', {'src': 'web1', 'dst': 'app1', 'proto': 'tcp', 'port': 443}, ck)
        self.assertEqual((r['verdict'], r['reason']), ('DROP', 'POLICY_IMPLICIT_DENY'))
        s, chk, _ = self.req('GET', '/sim/labs/check', cookie=ck)
        self.assertLess(chk['passed'], chk['total'])
        s, j, _ = self.req('POST', '/api/mo/uni.json', solution(), ck)
        self.assertEqual(s, 200, j)
        s, r, _ = self.req('POST', '/sim/traffic', {'src': 'web1', 'dst': 'app1', 'proto': 'tcp', 'port': 443}, ck)
        self.assertEqual(r['verdict'], 'ALLOW')
        s, r, _ = self.req('POST', '/sim/traffic', {'src': 'web1', 'dst': 'app1', 'proto': 'tcp', 'port': 22}, ck)
        self.assertEqual(r['verdict'], 'DROP')
        s, chk, _ = self.req('GET', '/sim/labs/check', cookie=ck)
        self.assertEqual(chk['passed'], chk['total'], [c for c in chk['checks'] if not c['ok']])
        s, h1, _ = self.req('POST', '/sim/labs/hint', {}, ck)
        self.assertEqual(h1['level'], 1)
        self.assertEqual(self.req('POST', '/sim/labs/mode', {'mode': 'exam'}, ck)[0], 200)
        self.assertEqual(self.req('POST', '/sim/labs/hint', {}, ck)[0], 403)
        s, st, _ = self.req('GET', '/sim/state', cookie=ck)
        self.assertIsNone(st['lab']['solution'])
        self.req('POST', '/sim/labs/op', {'op': 'reset', 'id': LAB}, ck)
        s, r, _ = self.req('POST', '/sim/traffic', {'src': 'web1', 'dst': 'app1', 'proto': 'tcp', 'port': 443}, ck)
        self.assertEqual(r['reason'], 'POLICY_IMPLICIT_DENY')
        s, labs, _ = self.req('GET', '/sim/labs', cookie=ck)
        self.assertTrue(next(l for l in labs if l['id'] == LAB)['progress']['done'], 'bestanden bleibt nach Reset stehen')


if __name__ == '__main__':
    unittest.main()
