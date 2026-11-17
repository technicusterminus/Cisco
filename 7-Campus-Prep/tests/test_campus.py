import base64
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from campusprep.catc import CatalystCenter  # noqa: E402
from campusprep.server import serve, Sim  # noqa: E402

BASIC = 'Basic ' + base64.b64encode(b'admin:admin').decode()
CORP = ['configure terminal', 'wlan Corp_Profile 1 Corp', 'security wpa akm psk',
        'security wpa psk set-key ascii 0 Sommer2026', 'no shutdown', 'exit',
        'wireless profile policy PP_Corp', 'vlan 20', 'no shutdown', 'exit',
        'wireless tag policy PT_Corp', 'wlan Corp_Profile policy PP_Corp', 'exit', 'end']


def configured(extra=()):
    s = Sim()
    for line in list(CORP) + list(extra):
        s.cli.run(line)
    return s


def tag_lobby(s):
    for line in ('configure terminal', 'ap a4b2.32aa.0001', 'policy-tag PT_Corp', 'end'):
        s.cli.run(line)


class TestShowFormats(unittest.TestCase):
    """Kopfzeilen wie in den genieparser-Parsern (Muster dort: show_wlan.py, show_ap.py, show_wireless.py)."""

    def test_wlan_summary(self):
        out = configured().cli.run('show wlan summary').split('\n')
        self.assertRegex(out[0], r'^Number\s+of\s+WLANs:\s+1$')
        self.assertRegex(out[2], r'^ID\s+Profile\s+Name\s+SSID\s+Status\s+Security$')
        self.assertRegex(out[4], r'^1\s+Corp_Profile\s+Corp\s+UP\s+\[WPA2\]\[PSK\]\[AES\]$')

    def test_ap_summary(self):
        out = Sim().cli.run('show ap summary').split('\n')
        self.assertRegex(out[0], r'^Number\s+of\s+APs:\s+2$')
        self.assertRegex(out[2], r'^AP Name\s+Slots\s+AP Model\s+Ethernet MAC\s+Radio MAC\s+Location\s+Country\s+IP Address\s+State$')
        self.assertRegex(out[4], r'^ap-lobby\s+2\s+9130AXI\s+a4b2\.32aa\.0001\s+2c57\.41aa\.0001\s+default location\s+DE\s+10\.10\.20\.11\s+Registered$')

    def test_client_summary_and_tag_summary(self):
        s = configured()
        tag_lobby(s)
        out = s.cli.run('show wireless client summary').split('\n')
        self.assertRegex(out[0], r'^Number of Clients:\s+1$')
        self.assertRegex(out[2], r'^MAC Address\s+AP Name\s+Type\s+ID\s+State\s+Protocol\s+Method\s+Role$')
        self.assertRegex(out[4], r'^58bf\.eaaa\.0001\s+ap-lobby\s+WLAN\s+1\s+Run\s+11ac\s+PSK\s+Local$')
        tags = s.cli.run('show ap tag summary')
        self.assertRegex(tags.split('\n')[2], r'^AP Name\s+AP Mac\s+Site Tag Name\s+Policy Tag Name\s+RF Tag Name\s+Misconfigured\s+Tag Source$')
        self.assertRegex(tags, r'ap-lobby\s+a4b2\.32aa\.0001\s+default-site-tag\s+PT_Corp\s+default-rf-tag\s+No\s+Static')
        self.assertRegex(tags, r'ap-lager\s+a4b2\.32aa\.0002\s+default-site-tag\s+default-policy-tag')

    def test_policy_summary(self):
        out = configured().cli.run('show wireless profile policy summary').split('\n')
        self.assertRegex(out[0], r'^Number of Policy Profiles:\s+1$')
        self.assertRegex(out[2], r'^Policy Profile Name\s+Description\s+Status$')
        self.assertRegex(out[4], r'^PP_Corp\s+Not required\s+ENABLED$')

    def test_unknown_show_is_refused_not_invented(self):
        r = Sim().cli.run('show wireless stats ap join summary')
        self.assertTrue(r.startswith('% '), r)
        self.assertIn('nicht belegt', r)


class TestWlcDecision(unittest.TestCase):
    def reasons(self, s, mac='58bf.eaaa.0001'):
        c = next(x for x in s.wlc.clients() if x['mac'] == mac)
        return c['state'], ' '.join(c['reasons'])

    def test_default_policy_tag_hides_the_ssid(self):
        s = configured()
        state, why = self.reasons(s)
        self.assertEqual(state, 'Not Associated')
        self.assertIn('default-policy-tag', why)
        self.assertIn('nicht ausgestrahlt', why)
        tag_lobby(s)
        self.assertEqual(self.reasons(s)[0], 'Run')

    def test_wlan_and_policy_are_down_by_default(self):
        s = Sim()
        for line in ['configure terminal', 'wlan Corp_Profile 1 Corp', 'security wpa akm psk',
                     'security wpa psk set-key ascii 0 Sommer2026', 'exit', 'wireless profile policy PP_Corp', 'exit',
                     'wireless tag policy PT_Corp', 'wlan Corp_Profile policy PP_Corp', 'exit',
                     'ap a4b2.32aa.0001', 'policy-tag PT_Corp', 'end']:
            s.cli.run(line)
        self.assertIn('WLAN-Profil Corp_Profile ist administrativ down', self.reasons(s)[1])
        for line in ['configure terminal', 'wlan Corp_Profile 1 Corp', 'no shutdown', 'end']:
            s.cli.run(line)
        self.assertIn('Policy Profile PP_Corp ist administrativ down', self.reasons(s)[1])
        for line in ['configure terminal', 'wireless profile policy PP_Corp', 'no shutdown', 'end']:
            s.cli.run(line)
        self.assertEqual(self.reasons(s)[0], 'Run')

    def test_wrong_psk_and_other_ap(self):
        s = configured()
        tag_lobby(s)
        state, why = self.reasons(s, '58bf.eaaa.0002')
        self.assertEqual(state, 'Not Associated')
        self.assertIn('Pre-Shared Key', why)
        s.world['clients'][0]['ap'] = 'ap-lager'
        self.assertIn('default-policy-tag', self.reasons(s)[1])

    def test_unregistered_ap(self):
        s = configured()
        tag_lobby(s)
        s.world['aps'][0]['joined'] = False
        self.assertIn('nicht am Controller registriert', self.reasons(s)[1])

    def test_cli_modes_and_errors(self):
        s = Sim()
        self.assertEqual(s.cli.prompt, 'wlc1#')
        self.assertTrue(s.cli.run('wlan x 1 y').startswith('% '))
        s.cli.run('configure terminal')
        s.cli.run('wlan Corp_Profile 1 Corp')
        self.assertEqual(s.cli.prompt, 'wlc1(config-wlan)#')
        self.assertTrue(s.cli.run('bogus').startswith('% '))
        self.assertTrue(s.cli.run('wlan Other 1 Foo').startswith('% '))
        s.cli.run('end')
        self.assertEqual(s.cli.prompt, 'wlc1#')
        s.cli.run('configure terminal')
        self.assertTrue(s.cli.run('wlan Other 1 Foo').startswith('% '), 'WLAN-ID doppelt')
        self.assertTrue(s.cli.run('ap nicht-eine-mac').startswith('% '))


class TestCatalystCenter(unittest.TestCase):
    def setUp(self):
        self.s = Sim()
        self.c = self.s.catc
        st, body = self.c.handle('POST', '/dna/system/api/v1/auth/token', headers={'Authorization': BASIC})
        self.assertEqual(st, 200)
        self.h = {'X-Auth-Token': body['Token']}

    def test_auth(self):
        c = CatalystCenter(self.s.world)
        self.assertEqual(c.handle('POST', '/dna/system/api/v1/auth/token')[0], 401)
        bad = 'Basic ' + base64.b64encode(b'admin:x').decode()
        self.assertEqual(c.handle('POST', '/dna/system/api/v1/auth/token', headers={'authorization': bad})[0], 401)
        self.assertEqual(c.handle('GET', '/dna/intent/api/v1/network-device')[0], 401)
        self.assertEqual(c.handle('GET', '/dna/intent/api/v1/network-device', headers={'X-Auth-Token': 'x'})[0], 401)

    def test_device_list_fields_and_envelope(self):
        st, body = self.c.handle('GET', '/dna/intent/api/v1/network-device', headers=self.h)
        self.assertEqual(st, 200)
        self.assertEqual(set(body), {'response', 'version'})
        self.assertEqual(len(body['response']), 3)
        wlc = next(d for d in body['response'] if d['family'] == 'Wireless Controller')
        # Feldnamen laut cisco.dnac network_device_info
        for f in ('hostname', 'managementIpAddress', 'macAddress', 'serialNumber', 'platformId', 'softwareType',
                  'softwareVersion', 'family', 'type', 'role', 'reachabilityStatus', 'managementState', 'upTime',
                  'uptimeSeconds', 'associatedWlcIp', 'apManagerInterfaceIp', 'id', 'instanceUuid'):
            self.assertIn(f, wlc)
        self.assertEqual((wlc['hostname'], wlc['managementIpAddress']), ('wlc1', '10.10.0.10'))
        ap = next(d for d in body['response'] if d['hostname'] == 'ap-lobby')
        self.assertEqual((ap['family'], ap['associatedWlcIp']), ('Unified AP', '10.10.0.10'))

    def test_count_filter_paging_and_by_id(self):
        g = lambda path, q=None: self.c.handle('GET', path, q, self.h)
        self.assertEqual(g('/dna/intent/api/v1/network-device/count')[1], {'response': 3, 'version': '1.0'})
        self.assertEqual(g('/dna/intent/api/v1/network-device/count', {'family': ['Unified AP']})[1]['response'], 2)
        st, body = g('/dna/intent/api/v1/network-device', {'hostname': ['ap-lager']})
        self.assertEqual([d['hostname'] for d in body['response']], ['ap-lager'])
        st, body = g('/dna/intent/api/v1/network-device', {'offset': ['2'], 'limit': ['1']})
        self.assertEqual(len(body['response']), 1)
        one = body['response'][0]
        st, b2 = g('/dna/intent/api/v1/network-device/' + one['id'])
        self.assertEqual((st, b2['response']['hostname']), (200, one['hostname']))
        self.assertEqual(g('/dna/intent/api/v1/network-device/unbekannt')[0], 404)

    def test_unimplemented_endpoint_says_so(self):
        st, body = self.c.handle('GET', '/dna/intent/api/v1/site', headers=self.h)
        self.assertEqual(st, 404)
        self.assertIn('nicht umgesetzt', body['error'])

    def test_one_truth_wlc_world_drives_inventory(self):
        self.s.world['aps'][0]['joined'] = False
        self.assertEqual(self.c.handle('GET', '/dna/intent/api/v1/network-device/count', headers=self.h)[1]['response'], 2)
        self.assertEqual(self.s.cli.run('show ap summary').split('\n')[0], 'Number of APs: 1')


class TestDeterminismAndHttp(unittest.TestCase):
    def test_deterministic(self):
        a, b = configured(), configured()
        tag_lobby(a)
        tag_lobby(b)
        for cmd in ('show wlan summary', 'show ap tag summary', 'show wireless client summary'):
            self.assertEqual(a.cli.run(cmd), b.cli.run(cmd))
        self.assertEqual([d['id'] for d in a.catc.devices()], [d['id'] for d in b.catc.devices()])

    def test_http_end_to_end(self):
        srv, sim = serve(0)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        base = 'http://127.0.0.1:%d' % port
        try:
            def call(path, method='GET', headers=None, data=None):
                req = urllib.request.Request(base + path, method=method, headers=headers or {},
                                             data=json.dumps(data).encode() if data is not None else None)
                try:
                    with urllib.request.urlopen(req) as r:
                        return r.status, json.loads(r.read())
                except urllib.error.HTTPError as e:
                    return e.code, json.loads(e.read())
            self.assertEqual(call('/dna/intent/api/v1/network-device')[0], 401)
            st, body = call('/dna/system/api/v1/auth/token', 'POST', {'Authorization': BASIC})
            self.assertEqual(st, 200)
            st, body = call('/dna/intent/api/v1/network-device/count', headers={'X-Auth-Token': body['Token']})
            self.assertEqual((st, body['response']), (200, 3))
            for line in CORP:
                call('/wlc/cli', 'POST', data={'command': line})
            st, out = call('/wlc/cli', 'POST', data={'command': 'show wlan summary'})
            self.assertIn('Corp_Profile', out['output'])
            self.assertEqual(out['prompt'], 'wlc1#')
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == '__main__':
    unittest.main()


class TestWebApi(unittest.TestCase):
    """Zustands- und Apply-Endpunkt der Oberflaeche sowie das Ausliefern der statischen Dateien."""

    def setUp(self):
        self.srv, self.sim = serve(0)
        self.base = 'http://127.0.0.1:%d' % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def call(self, path, method='GET', data=None, raw=False):
        req = urllib.request.Request(self.base + path, method=method, data=json.dumps(data).encode() if data is not None else None)
        try:
            with urllib.request.urlopen(req) as r:
                body = r.read()
                return r.status, (body if raw else json.loads(body)), r.headers
        except urllib.error.HTTPError as e:
            body = e.read()
            return e.code, (body if raw else json.loads(body)), e.headers

    def test_static_and_path_traversal(self):
        st, body, hd = self.call('/', raw=True)
        self.assertEqual(st, 200)
        self.assertIn(b'Campus Prep', body)
        self.assertIn('text/html', hd['Content-Type'])
        st, body, hd = self.call('/static/app.js', raw=True)
        self.assertEqual(st, 200)
        self.assertIn('javascript', hd['Content-Type'])
        for bad in ('/static/../campusprep/wlc.py', '/static/%2e%2e/start.py', '/static/nix.js'):
            self.assertEqual(self.call(bad, raw=True)[0], 404, bad)

    def test_state_hides_the_key(self):
        self.call('/wlc/api/apply', 'POST', {'commands': ['wlan P 1 Corp', 'security wpa akm psk', 'security wpa psk set-key ascii 0 GeheimGeheim']})
        st, state, _ = self.call('/wlc/api/state')
        self.assertEqual(st, 200)
        self.assertEqual(state['wlans'][0]['pskSet'], True)
        self.assertNotIn('GeheimGeheim', json.dumps(state))

    def test_apply_is_atomic(self):
        st, body, _ = self.call('/wlc/api/apply', 'POST', {'commands': ['wlan P 1 Corp', 'no shutdown', 'bogus']})
        self.assertEqual(st, 400)
        self.assertFalse(body['ok'])
        self.assertEqual(body['error']['command'], 'bogus')
        self.assertEqual(self.call('/wlc/api/state')[1]['wlans'], [])
        st, body, _ = self.call('/wlc/api/apply', 'POST', {'commands': ['wlan P 1 Corp', 'no shutdown']})
        self.assertEqual((st, body['ok']), (200, True))
        self.assertEqual(self.call('/wlc/api/state')[1]['wlans'][0]['status'], 'UP')

    def test_apply_input_validation(self):
        self.assertEqual(self.call('/wlc/api/apply', 'POST', {'commands': 'x'})[0], 400)
        self.assertEqual(self.call('/wlc/api/apply', 'POST', {})[0], 400)

    def test_gui_and_cli_share_one_truth(self):
        for line in ('configure terminal', 'wlan P 1 Corp', 'end'):
            self.call('/wlc/cli', 'POST', {'command': line})
        self.assertEqual(self.call('/wlc/api/state')[1]['wlans'][0]['profile'], 'P')
        self.call('/wlc/api/apply', 'POST', {'commands': ['wlan Q 2 Gast']})
        self.assertIn('Q', self.call('/wlc/cli', 'POST', {'command': 'show wlan summary'})[1]['output'])


class TestDeleteAndTagCommands(unittest.TestCase):
    def test_delete_refuses_referenced_objects(self):
        s = configured()
        tag_lobby(s)
        for cmd, word in (('no wlan Corp_Profile', 'PT_Corp'), ('no wireless profile policy PP_Corp', 'PT_Corp'),
                          ('no wireless tag policy PT_Corp', 'ap-lobby'), ('no wireless tag policy default-policy-tag', 'vordefiniert')):
            s.cli.run('configure terminal')
            r = s.cli.run(cmd)
            s.cli.run('end')
            self.assertTrue(r.startswith('% '), cmd)
            self.assertIn(word, r)
        self.assertEqual(len(s.wlc.wlans), 1)

    def test_delete_in_the_right_order_and_unassign_ap(self):
        s = configured()
        tag_lobby(s)
        for line in ('configure terminal', 'ap a4b2.32aa.0001', 'no policy-tag', 'exit', 'no wireless tag policy PT_Corp',
                     'no wlan Corp_Profile', 'no wireless profile policy PP_Corp', 'end'):
            out = s.cli.run(line)
            self.assertFalse(out.startswith('% '), '%s -> %s' % (line, out))
        self.assertEqual((s.wlc.wlans, s.wlc.policies, list(s.wlc.policy_tags)), ({}, {}, ['default-policy-tag']))
        self.assertEqual(s.wlc.policy_tag_of(s.world['aps'][0]), 'default-policy-tag')
