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


FLEX = ['configure terminal', 'wireless profile flex FP1', 'native-vlan-id 1', 'vlan-name CORP_LOCAL', 'vlan-id 20', 'vlan-name GAST', 'vlan-id 99',
        'exit', 'exit', 'wireless tag site ST1', 'no local-site', 'flex-profile FP1', 'end']


class TestCliRobustness(unittest.TestCase):
    def test_a_lone_no_is_an_error_not_a_crash(self):
        s = Sim()
        s.cli.run('configure terminal')
        self.assertEqual(s.cli.run('no'), '% Invalid input detected: "no"')
        s.cli.run('wlan P 1 Corp')
        self.assertEqual(s.cli.run('no'), '% Invalid input detected: "no"')

    def test_object_deleted_under_an_open_cli_mode(self):
        s = Sim()
        for line in ('configure terminal', 'wlan P 1 Corp'):
            s.cli.run(line)
        self.assertEqual(s.cli.prompt, 'wlc1(config-wlan)#')
        ok, _, err = s.apply(['no wlan P'])        # z. B. ueber die Oberflaeche
        self.assertTrue(ok, err)
        self.assertEqual(s.cli.run('shutdown'), '% Das Objekt existiert nicht mehr')
        self.assertEqual(s.cli.prompt, 'wlc1(config)#')
        self.assertEqual(s.cli.run('wlan Q 2 Neu'), '')


class TestFlexConnect(unittest.TestCase):
    """Befehle und Regeln aus Cisco-Dokument 213945 (ueber Websuche zitiert); Formate der Show-Befehle aus genieparser."""

    def run_all(self, lines):
        s = Sim()
        for line in lines:
            out = s.cli.run(line)
            self.assertFalse(out.startswith('% '), '%s -> %s' % (line, out))
        return s

    def test_show_formats(self):
        s = self.run_all(FLEX)
        flex = s.cli.run('show wireless profile flex summary').split('\n')
        self.assertRegex(flex[0], r'^Number\s+of\s+Flex\s+Profiles:\s+2$')
        self.assertRegex(flex[2], r'^Flex\s+Profile\s+Name\s+Description$')
        self.assertRegex(flex[3], r'^-+$')
        self.assertEqual([x.strip() for x in flex[4:]], ['FP1', 'default-flex-profile'])
        site = s.cli.run('show wireless tag site summary').split('\n')
        self.assertRegex(site[0], r'^Number\s+of\s+Site\s+Tags:\s+2$')
        self.assertRegex(site[2], r'^Site\s+Tag\s+Name\s+Description$')
        self.assertEqual([x.strip() for x in site[4:]], ['ST1', 'default-site-tag'])

    def test_flex_profile_is_only_offered_without_local_site(self):
        s = self.run_all(['configure terminal', 'wireless profile flex FP1', 'exit', 'wireless tag site ST1'])
        r = s.cli.run('flex-profile FP1')
        self.assertTrue(r.startswith('% ') and 'Local Site' in r, r)
        self.assertEqual(s.cli.run('no local-site'), '')
        self.assertEqual(s.cli.run('flex-profile FP1'), '')
        self.assertTrue(s.cli.run('flex-profile gibtsnicht').startswith('% '))

    def test_prompts_and_vlan_submode_falls_back_to_the_parent_mode(self):
        s = self.run_all(['configure terminal', 'wireless profile flex FP1'])
        self.assertEqual(s.cli.prompt, 'wlc1(config-wireless-flex-profile)#')
        s.cli.run('vlan-name A')
        self.assertEqual(s.cli.prompt, 'wlc1(config-wireless-flex-profile-vlan)#')
        self.assertEqual(s.cli.run('vlan-name B'), '', 'weiterer vlan-name direkt im Untermodus (Beispiel im Cisco-Dokument)')
        s.cli.run('vlan-id 30')
        self.assertEqual(s.wlc.flex_profiles['FP1']['vlans'], {'A': None, 'B': 30})
        self.assertTrue(s.cli.run('vlan-id 5000').startswith('% '))
        s.cli.run('exit')
        self.assertEqual(s.cli.prompt, 'wlc1(config-wireless-flex-profile)#')
        self.assertTrue(s.cli.run('vlan-id 10').startswith('% '), 'vlan-id nur nach vlan-name')

    def test_site_tag_makes_the_ap_flexconnect_and_shows_in_the_tag_summary(self):
        s = self.run_all(FLEX + ['configure terminal', 'ap a4b2.32aa.0002', 'site-tag ST1', 'end'])
        st = s.wlc.state()
        self.assertEqual({a['name']: (a['mode'], a['siteTag']) for a in st['aps']},
                         {'ap-lobby': ('Local', 'default-site-tag'), 'ap-lager': ('FlexConnect', 'ST1')})
        self.assertRegex(s.cli.run('show ap tag summary'), r'ap-lager\s+a4b2\.32aa\.0002\s+ST1\s+default-policy-tag\s+default-rf-tag\s+No\s+Static')
        self.assertTrue(s.cli.run('configure terminal') and s.cli.run('ap a4b2.32aa.0002') == '')
        self.assertTrue(s.cli.run('site-tag gibtsnicht').startswith('% '))
        s.cli.run('no site-tag')
        self.assertEqual(s.wlc.ap_mode(s.world['aps'][1]), 'Local')

    def test_site_tag_without_flex_profile_uses_the_default_profile(self):
        s = self.run_all(['configure terminal', 'wireless tag site ST2', 'no local-site', 'exit', 'ap a4b2.32aa.0001', 'site-tag ST2'])
        self.assertEqual(s.wlc.flex_of(s.world['aps'][0]), 'default-flex-profile')

    def test_delete_rules_for_flex_profiles_and_site_tags(self):
        s = self.run_all(FLEX + ['configure terminal', 'ap a4b2.32aa.0002', 'site-tag ST1', 'exit'])
        for cmd, word in (('no wireless profile flex FP1', 'ST1'), ('no wireless tag site ST1', 'ap-lager'),
                          ('no wireless profile flex default-flex-profile', 'vordefiniert'), ('no wireless tag site default-site-tag', 'vordefiniert')):
            self.assertIn(word, s.cli.run(cmd), cmd)
        for line in ('ap a4b2.32aa.0002', 'no site-tag', 'exit', 'no wireless tag site ST1', 'no wireless profile flex FP1'):
            self.assertEqual(s.cli.run(line), '', line)
        self.assertEqual((list(s.wlc.flex_profiles), list(s.wlc.site_tags)), (['default-flex-profile'], ['default-site-tag']))

    def _client(self, lines):
        s = self.run_all(['configure terminal', 'wlan P 1 Corp', 'no shutdown', 'exit', 'wireless profile policy PP', 'vlan 20', 'no shutdown'] + lines)
        return s, s.wlc.clients()[0]

    def tags(self, site=True, vlan='CORP_LOCAL', central=False):
        pol = ['exit', 'wireless profile policy PP', 'vlan %s' % vlan, ('central switching' if central else 'no central switching')]
        out = pol + ['exit', 'wireless tag policy PT', 'wlan P policy PP', 'exit', 'wireless profile flex FP1', 'vlan-name CORP_LOCAL', 'vlan-id 20',
                     'exit', 'exit', 'wireless tag site ST1', 'no local-site', 'flex-profile FP1', 'exit', 'ap a4b2.32aa.0001', 'policy-tag PT']
        return out + (['site-tag ST1'] if site else [])

    def test_decision_central_local_and_the_failure_reasons(self):
        s, c = self._client(self.tags())
        self.assertEqual((c['state'], c['vlan'], c['switching'], c['mode']), ('Run', '20', 'local', 'FlexConnect'))
        s, c = self._client(self.tags(site=False))
        self.assertEqual(c['state'], 'Not Associated')
        self.assertIn('Local Mode', c['reasons'][0])
        s, c = self._client(self.tags(vlan='Corp_Local'))
        self.assertEqual(c['state'], 'Not Associated')
        self.assertIn('exakt', c['reasons'][0])
        s, c = self._client(self.tags(central=True))
        self.assertEqual(c['state'], 'Not Associated')
        self.assertIn('numerische', c['reasons'][0])
        s, c = self._client(self.tags(vlan='20', central=True))
        self.assertEqual((c['state'], c['vlan'], c['switching']), ('Run', '20', 'central'))

    def test_names_are_case_sensitive_and_numeric_ids_match_by_vlan_id(self):
        fp = {'native': 7, 'vlans': {'CORP_LOCAL': 20, 'leer': None}}
        f = Sim().wlc.flex_vlan
        self.assertEqual((f(fp, 'CORP_LOCAL'), f(fp, 'corp_local'), f(fp, 'leer'), f(fp, 'x')), (20, None, None, None))
        self.assertEqual((f(fp, '20'), f(fp, '7'), f(fp, '8'), f(None, '20')), (20, 7, None, None))


def aaa_world():
    """Welt fuer 802.1X-Tests: ein RADIUS-Server (Standard) und drei Endgeraete mit Zugangsdaten."""
    s = Sim()
    s.world['clients'] = [
        {'mac': '58bf.eaaa.0001', 'ssid': 'Corp1X', 'eap': {'user': 'anna', 'password': 'Passw0rt!'}, 'ap': 'ap-lobby', 'protocol': '11ac'},
        {'mac': '58bf.eaaa.0002', 'ssid': 'Corp1X', 'eap': {'user': 'bernd', 'password': 'Geheim#2'}, 'ap': 'ap-lobby', 'protocol': '11ac'},
        {'mac': '58bf.eaaa.0003', 'ssid': 'Corp1X', 'eap': {'user': 'carla', 'password': 'Sommer#3'}, 'ap': 'ap-lobby', 'protocol': '11ac'},
        {'mac': '58bf.eaaa.0004', 'ssid': 'Corp1X', 'eap': {'user': 'anna', 'password': 'falsch'}, 'ap': 'ap-lobby', 'protocol': '11ac'},
    ]
    return s


AAA = ['aaa new-model', 'radius server RS1', 'address ipv4 10.10.0.50 auth-port 1812 acct-port 1813', 'key RadiusKey1', 'exit',
       'aaa group server radius RG1', 'server name RS1', 'exit', 'aaa authentication dot1x L1 group RG1',
       'wlan W1 1 Corp1X', 'security wpa akm dot1x', 'security dot1x authentication-list L1', 'no shutdown', 'exit',
       'wireless profile policy PP', 'vlan 20', 'no shutdown', 'exit', 'wireless tag policy PT', 'wlan W1 policy PP', 'exit',
       'ap a4b2.32aa.0001', 'policy-tag PT', 'exit']


CORP_CFG = CORP[1:-1] + ['ap a4b2.32aa.0001', 'policy-tag PT_Corp', 'exit']


class TestMulticast(unittest.TestCase):
    """Multicast: wireless multicast <gruppe> und show wireless multicast nach Cisco-Dokument 225203; die Auswertung ist ein Simulator-Modell."""

    def world(self, extra=(), mcast=True, underlay=None):
        s = Sim()
        c = {'mac': '58bf.eaaa.0001', 'ssid': 'Corp', 'psk': 'Sommer2026', 'ap': 'ap-lobby', 'protocol': '11ac'}
        if mcast:
            c['mcast'] = True
        s.reset_world([c], underlay=underlay)
        ok, _, err = s.apply(list(CORP_CFG) + list(extra))
        self.assertTrue(ok, err)
        return s

    def client(self, s):
        return s.wlc.state()['clients'][0]

    def test_default_is_off_and_the_client_does_not_receive(self):
        s = self.world()
        self.assertEqual(s.wlc.state()['multicast'], {'enabled': False, 'group': '', 'mode': 'Unicast', 'groupInUse': False})
        self.assertEqual(self.client(s)['mcast'], 'Not received')
        self.assertIn('Multicast ist am Controller aus', ' '.join(self.client(s)['reasons']))
        self.assertEqual(s.cli.run('show wireless multicast'), 'Multicast : Disabled')

    def test_enabled_multicast_is_received_and_shown_in_the_documented_fields(self):
        s = self.world(['wireless multicast 239.1.1.10'])
        self.assertEqual(self.client(s)['mcast'], 'Received')
        self.assertEqual(s.cli.run('show wireless multicast').splitlines(),
                         ['Multicast : Enabled', 'AP Capwap Multicast : Multicast', 'AP Capwap IPv4 Multicast group Address : 239.1.1.10'])
        self.assertEqual(s.wlc.state()['multicast']['mode'], 'Multicast')

    def test_used_group_and_a_down_underlay_each_prevent_reception(self):
        s = self.world(['wireless multicast 239.1.1.10'], underlay={'multicastRouting': True, 'usedGroups': ['239.1.1.10']})
        self.assertEqual(self.client(s)['mcast'], 'Not received')
        self.assertTrue(s.wlc.state()['multicast']['groupInUse'])
        s = self.world(['wireless multicast 239.1.1.10'], underlay={'multicastRouting': False, 'usedGroups': []})
        self.assertIn('leitet Multicast nicht weiter', ' '.join(self.client(s)['reasons']))

    def test_clients_without_the_marker_or_not_connected_have_no_result(self):
        s = self.world(['wireless multicast 239.1.1.10'], mcast=False)
        self.assertEqual(self.client(s)['mcast'], None)
        s = self.world(['wireless multicast 239.1.1.10', 'wireless profile policy PP_Corp', 'shutdown'])
        self.assertEqual((self.client(s)['state'], self.client(s)['mcast']), ('Not Associated', None))

    def test_cli_forms_and_errors(self):
        s = self.world()
        cli = s.cli
        cli.run('configure terminal')
        for line in ('wireless multicast 239.1.1.10', 'wireless multicast 224.0.1.5', 'wireless multicast 239.255.255.255', 'no wireless multicast'):
            self.assertEqual(cli.run(line), '', line)
        for line in ('wireless multicast', 'wireless multicast 10.0.0.1', 'wireless multicast 240.0.0.1', 'wireless multicast 224.0.0.251', 'wireless multicast 300.1.1.1',
                     'wireless multicast 239.1.1.10 extra', 'wireless multicast x', 'no wireless multicast 239.1.1.10', 'wireless multicast mode unicast'):
            self.assertTrue(cli.run(line).startswith('% '), line)
        self.assertEqual(s.wlc.state()['multicast']['enabled'], False)

    def test_failed_apply_rolls_back_multicast(self):
        s = self.world(['wireless multicast 239.1.1.10'])
        before = s.wlc.state()
        ok, _, _ = s.apply(['wireless multicast 239.9.9.9', 'wireless multicast 10.0.0.1'])
        self.assertFalse(ok)
        self.assertEqual(s.wlc.state(), before)


class TestQos(unittest.TestCase):
    """QoS mit Metal-Profilen: service-policy und die hoechsten DSCP-Werte nach Cisco-Dokument 222241; Auswertung ist ein Simulator-Modell."""

    def world(self, extra=(), dscp=46):
        s = Sim()
        c = {'mac': '58bf.eaaa.0001', 'ssid': 'Corp', 'psk': 'Sommer2026', 'ap': 'ap-lobby', 'protocol': '11ac'}
        if dscp is not None:
            c['dscp'] = dscp
        s.reset_world([c])
        ok, _, err = s.apply(list(CORP_CFG) + list(extra))
        self.assertTrue(ok, err)
        return s

    def client(self, s):
        return s.wlc.state()['clients'][0]

    def test_each_metal_profile_caps_the_dscp_at_its_maximum(self):
        for name, cap in (('platinum', 46), ('gold', 34), ('silver', 0), ('bronze', 8)):
            s = self.world(['wireless profile policy PP_Corp', 'service-policy output ' + name, 'service-policy input %s-up' % name])
            c = self.client(s)
            self.assertEqual((c['state'], c['dscpDown'], c['dscpUp']), ('Run', min(46, cap), min(46, cap)), name)

    def test_lower_marking_is_not_raised_and_no_policy_means_no_cap(self):
        s = self.world(['wireless profile policy PP_Corp', 'service-policy output gold', 'service-policy input gold-up'], dscp=10)
        self.assertEqual((self.client(s)['dscpDown'], self.client(s)['dscpUp']), (10, 10))
        s = self.world()
        self.assertEqual((self.client(s)['dscpDown'], self.client(s)['dscpUp']), (46, 46))

    def test_directions_are_independent(self):
        s = self.world(['wireless profile policy PP_Corp', 'service-policy output bronze'])
        self.assertEqual((self.client(s)['dscpDown'], self.client(s)['dscpUp']), (8, 46))
        s = self.world(['wireless profile policy PP_Corp', 'service-policy input bronze-up'])
        self.assertEqual((self.client(s)['dscpDown'], self.client(s)['dscpUp']), (46, 8))

    def test_clients_without_marking_and_unconnected_clients_have_no_dscp_result(self):
        s = self.world(['wireless profile policy PP_Corp', 'service-policy output bronze'], dscp=None)
        self.assertEqual((self.client(s)['dscp'], self.client(s)['dscpDown'], self.client(s)['dscpUp']), (None, None, None))
        s = self.world(['wireless profile policy PP_Corp', 'shutdown'])
        self.assertEqual((self.client(s)['state'], self.client(s)['dscpDown']), ('Not Associated', None))

    def test_cli_forms_and_errors(self):
        s = self.world()
        cli = s.cli
        cli.run('configure terminal')
        cli.run('wireless profile policy PP_Corp')
        for line in ('service-policy output platinum', 'service-policy input gold-up', 'no service-policy output platinum', 'no service-policy input gold-up'):
            self.assertEqual(cli.run(line), '', line)
        self.assertEqual([(p['qosOutput'], p['qosInput']) for p in s.wlc.state()['policies']], [('', '')])
        for line in ('service-policy', 'service-policy output', 'service-policy output bogus', 'service-policy output platinum-up', 'service-policy input platinum',
                     'service-policy both gold', 'service-policy output gold extra', 'no service-policy output gold'):
            self.assertTrue(cli.run(line).startswith('% '), line)
        cli.run('service-policy output platinum')
        self.assertIn('nicht als service-policy output gesetzt', cli.run('no service-policy output gold'))
        self.assertEqual(cli.run('no service-policy output platinum'), '')
        cli.run('service-policy output gold')
        self.assertEqual(cli.run('no service-policy output'), '')
        self.assertEqual(s.wlc.state()['policies'][0]['qosOutput'], '')

    def test_failed_apply_rolls_back_qos(self):
        s = self.world(['wireless profile policy PP_Corp', 'service-policy output gold'])
        before = s.wlc.state()
        ok, _, _ = s.apply(['wireless profile policy PP_Corp', 'service-policy output platinum', 'service-policy input nix'])
        self.assertFalse(ok)
        self.assertEqual(s.wlc.state(), before)


class TestRf(unittest.TestCase):
    """RF-Profile und RF Tags: tx-power und 5ghz-rf-policy stammen aus einem Community-Beispiel (nicht offiziell); die Wirkung ist ein Simulator-Modell."""

    def sim(self, extra=()):
        s = Sim()
        ok, _, err = s.apply(list(extra))
        self.assertTrue(ok, err)
        return s

    def rf(self, s, i=0, band='5ghz'):
        return s.wlc.state()['aps'][i]['rf'][band]

    def test_defaults_and_effect_chain(self):
        s = self.sim()
        self.assertEqual(self.rf(s), {'profile': None, 'txMax': None, 'radio': 'on'})
        self.assertEqual(s.wlc.state()['rfTags'], [{'name': 'default-rf-tag', 'builtin': True, 'rf24': '', 'rf5': ''}])
        s = self.sim(['ap dot11 5ghz rf-profile P', 'tx-power max 12', 'tx-power min 6', 'no shutdown', 'exit', 'wireless tag rf T', '5ghz-rf-policy P', 'exit'])
        self.assertEqual(self.rf(s), {'profile': None, 'txMax': None, 'radio': 'on'}, 'ohne Zuweisung am AP wirkungslos')
        s.apply(['ap a4b2.32aa.0001', 'rf-tag T'])
        self.assertEqual(self.rf(s), {'profile': 'P', 'txMax': 12, 'radio': 'on'})
        self.assertEqual(self.rf(s, 1), {'profile': None, 'txMax': None, 'radio': 'on'})
        self.assertEqual(self.rf(s, 0, '24ghz'), {'profile': None, 'txMax': None, 'radio': 'on'})
        s.apply(['ap dot11 5ghz rf-profile P', 'shutdown'])
        self.assertEqual(self.rf(s), {'profile': 'P', 'txMax': None, 'radio': 'off'})

    def test_cli_forms_errors_and_prompts(self):
        s = Sim()
        cli = s.cli
        cli.run('configure terminal')
        self.assertEqual(cli.run('ap dot11 5ghz rf-profile P'), '')
        self.assertTrue(cli.prompt.endswith('(config-rf-profile)#'))
        for line in ('tx-power max 0', 'tx-power max 31', 'tx-power max x', 'tx-power', 'tx-power med 10', 'bogus', 'shutdown x', 'no bogus'):
            self.assertTrue(cli.run(line).startswith('% '), line)
        self.assertEqual(cli.run('tx-power max 10'), '')
        self.assertIn('nicht groesser', cli.run('tx-power min 11'))
        self.assertEqual(cli.run('tx-power min 10'), '')
        self.assertEqual(cli.run('no tx-power min'), '')
        cli.run('exit')
        self.assertTrue(cli.run('ap dot11 6ghz rf-profile X').startswith('% '))
        self.assertTrue(cli.run('ap dot11 5ghz rf-profile bad!name').startswith('% '))
        cli.run('wireless tag rf T')
        self.assertTrue(cli.prompt.endswith('(config-rf-tag)#'))
        self.assertIn('existiert fuer 5 GHz nicht', cli.run('5ghz-rf-policy NIX'))
        self.assertIn('existiert fuer 2,4 GHz nicht', cli.run('24ghz-rf-policy P'))
        self.assertEqual(cli.run('5ghz-rf-policy P'), '')
        self.assertEqual(cli.run('no 5ghz-rf-policy'), '')
        self.assertTrue(cli.run('6ghz-rf-policy P').startswith('% '))
        cli.run('exit')
        cli.run('ap a4b2.32aa.0001')
        self.assertIn('existiert nicht', cli.run('rf-tag NIX'))

    def test_same_name_in_both_bands_is_two_profiles(self):
        s = self.sim(['ap dot11 5ghz rf-profile P', 'tx-power max 10', 'exit', 'ap dot11 24ghz rf-profile P', 'tx-power max 20', 'exit'])
        self.assertEqual(sorted((p['band'], p['txMax']) for p in s.wlc.state()['rfProfiles']), [('24ghz', 20), ('5ghz', 10)])

    def test_dependencies_are_refused_and_the_default_tag_stays(self):
        s = self.sim(['ap dot11 5ghz rf-profile P', 'exit', 'wireless tag rf T', '5ghz-rf-policy P', 'exit', 'ap a4b2.32aa.0001', 'rf-tag T', 'exit'])
        cli = s.cli
        cli.run('configure terminal')
        self.assertIn('wird von RF Tags verwendet', cli.run('no ap dot11 5ghz rf-profile P'))
        self.assertIn('APs zugewiesen', cli.run('no wireless tag rf T'))
        self.assertIn('vordefiniert', cli.run('no wireless tag rf default-rf-tag'))
        self.assertIn('existiert nicht', cli.run('no wireless tag rf NIX'))
        self.assertIn('existiert fuer 5 GHz nicht', cli.run('no ap dot11 5ghz rf-profile NIX'))
        cli.run('ap a4b2.32aa.0001')
        self.assertEqual(cli.run('no rf-tag'), '')
        cli.run('exit')
        self.assertEqual(cli.run('no wireless tag rf T'), '')
        self.assertEqual(cli.run('no ap dot11 5ghz rf-profile P'), '')

    def test_deleted_rf_profile_in_an_open_submode_does_not_crash(self):
        s = Sim()
        s.cli.run('configure terminal')
        s.cli.run('ap dot11 5ghz rf-profile P')
        del s.wlc.rf_profiles['5ghz:P']
        self.assertEqual(s.cli.run('tx-power max 5'), '% Das Objekt existiert nicht mehr')

    def test_rf_tag_counts_as_a_static_tag_source(self):
        s = self.sim(['wireless tag rf T', 'exit', 'ap a4b2.32aa.0001', 'rf-tag T'])
        self.assertEqual([a['tagSource'] for a in s.wlc.state()['aps']], ['Static', 'Default'])
        self.assertIn('Static', next(x for x in s.cli.run('show ap tag summary').splitlines() if x.startswith('ap-lobby')))


class TestMobility(unittest.TestCase):
    """Mobility: Befehle und Felder nach Cisco-Dokument 213913; Tunnel- und Roaming-Entscheidung sind ein Simulator-Modell."""
    MEMBER = 'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus'

    def world(self, extra=(), roam=True):
        from campusprep.server import Sim
        s = Sim()
        c = {'mac': '58bf.eaaa.0001', 'ssid': 'Corp', 'psk': 'Sommer2026', 'ap': 'ap-lobby', 'protocol': '11ac'}
        if roam:
            c['roam'] = {'from': '10.10.0.20'}
        s.reset_world([c])
        ok, _, err = s.apply(list(CORP_CFG) + list(extra))
        self.assertTrue(ok, err)
        return s

    def client(self, s):
        return s.wlc.clients()[0]

    def test_matching_configuration_brings_the_tunnel_up_and_the_client_roams(self):
        s = self.world(['wireless mobility group name default', self.MEMBER])
        self.assertEqual(self.client(s)['roam'], 'Inter-Controller')
        p = s.wlc.state()['mobilityPeers'][0]
        self.assertEqual((p['ip'], p['control'], p['data'], p['reason']), ('10.10.0.20', 'Up', 'Up', ''))
        out = s.cli.run('show wireless mobility summary')
        for text in ('Mobility Group Name: default', 'Mobility MAC Address: aabb.cc00.0100', 'Wireless Management IP Address: 10.10.0.10',
                     'Mobility Keepalive Interval/Count: 10/3', '10.10.0.20', 'Up'):
            self.assertIn(text, out)

    def test_each_mismatch_keeps_the_tunnel_down_with_a_reason_and_the_client_connects_as_a_new_session(self):
        cases = [([], 'nicht konfiguriert'),
                 (['wireless mobility group member mac-address aabb.cc00.0201 ip 10.10.0.20 group Campus'], 'MAC-Adresse'),
                 (['wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Falsch'], 'Gruppenname Falsch'),
                 ([self.MEMBER, 'wireless mobility group name Anders'], 'erwartet diesen Controller in der Gruppe default'),
                 (['wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.21 group Campus'], 'nicht konfiguriert')]
        for extra, text in cases:
            s = self.world(extra)
            c = self.client(s)
            self.assertEqual((c['state'], c['roam']), ('Run', None), extra)
            self.assertIn(text, ' '.join(c['reasons']), extra)

    def test_a_different_security_on_the_other_controller_prevents_roaming(self):
        s = self.world([self.MEMBER, 'wlan Corp_Profile 1 Corp', 'no security wpa akm psk'])
        c = self.client(s)
        self.assertEqual((c['state'], c['roam']), ('Run', None))
        self.assertIn('Sicherheit der SSID Corp dort (psk)', ' '.join(c['reasons']))

    def test_a_client_that_does_not_roam_is_unaffected(self):
        s = self.world([self.MEMBER], roam=False)
        self.assertEqual((self.client(s)['state'], self.client(s)['roam'], self.client(s)['reasons']), ('Run', None, []))

    def test_cli_forms_and_errors(self):
        s = self.world()
        cli = s.cli
        cli.run('configure terminal')
        for line in ('wireless mobility group name Neu', 'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus',
                     'wireless mobility group member mac-address AA:BB:CC:00:02:00 ip 10.10.0.21 group G2'):
            self.assertEqual(cli.run(line), '', line)
        for line in ('wireless mobility group name', 'wireless mobility group name bad!name', 'wireless mobility group member mac-address zz ip 10.10.0.20 group G',
                     'wireless mobility group member mac-address aabb.cc00.0200 ip 300.1.1.1 group G', 'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.10 group G',
                     'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20', 'wireless mobility group member ip 10.10.0.20',
                     'no wireless mobility group member ip 10.9.9.9', 'no wireless mobility group name', 'wireless mobility group bogus'):
            self.assertTrue(cli.run(line).startswith('% '), line)
        self.assertEqual(sorted(p['ip'] for p in s.wlc.state()['mobilityPeers']), ['10.10.0.20', '10.10.0.21'])
        self.assertEqual(cli.run('no wireless mobility group member ip 10.10.0.21'), '')
        self.assertEqual([p['mac'] for p in s.wlc.state()['mobilityPeers']], ['aabb.cc00.0200'])

    def test_failed_apply_rolls_back_mobility(self):
        s = self.world([self.MEMBER])
        before = s.wlc.state()
        ok, _, _ = s.apply(['wireless mobility group name Neu', 'no wireless mobility group member ip 10.10.0.20', 'wireless mobility group name bad!'])
        self.assertFalse(ok)
        self.assertEqual(s.wlc.state(), before)


class TestWebAuth(unittest.TestCase):
    """Local Web Authentication: Befehlskette nach Cisco-Dokument 224922/217457; die Portal-Anmeldung ist ein Simulator-Modell."""
    CHAIN = ['username gast1 privilege 0 password 0 Gast#1', 'aaa authentication login WEBAUTH local', 'aaa authorization network default local',
             'wlan Guest 2 Gast', 'security web-auth', 'security web-auth authentication-list WEBAUTH', 'security web-auth parameter-map global',
             'no shutdown', 'exit', 'wireless profile policy PP_G', 'vlan 99', 'no shutdown', 'exit',
             'wireless tag policy PT_G', 'wlan Guest policy PP_G', 'exit', 'ap a4b2.32aa.0001', 'policy-tag PT_G', 'exit']

    def world(self, extra=(), clients=None):
        from campusprep.server import Sim
        s = Sim()
        s.reset_world(clients or [
            {'mac': '58bf.eaaa.0001', 'ssid': 'Gast', 'ap': 'ap-lobby', 'protocol': '11ac', 'web': {'user': 'gast1', 'password': 'Gast#1'}},
            {'mac': '58bf.eaaa.0002', 'ssid': 'Gast', 'ap': 'ap-lobby', 'protocol': '11ac', 'web': {'user': 'gast1', 'password': 'falsch'}},
            {'mac': '58bf.eaaa.0003', 'ssid': 'Gast', 'ap': 'ap-lobby', 'protocol': '11ac'}])
        ok, _, err = s.apply(list(self.CHAIN) + list(extra))
        self.assertTrue(ok, err)
        return s

    def states(self, s):
        return {c['mac'][-1]: c['state'] for c in s.wlc.clients()}

    def reasons(self, s, mac='1'):
        return ' '.join(next(c for c in s.wlc.clients() if c['mac'].endswith(mac))['reasons'])

    def test_complete_chain_authenticates_only_the_valid_login(self):
        s = self.world()
        self.assertEqual(self.states(s), {'1': 'Run', '2': 'Webauth Pending', '3': 'Webauth Pending'})
        self.assertIn('Benutzername oder Passwort falsch', self.reasons(s, '2'))
        self.assertIn('noch nicht am Web-Portal angemeldet', self.reasons(s, '3'))
        self.assertEqual(next(c for c in s.wlc.clients() if c['mac'].endswith('1'))['vlan'], '99')

    def test_each_missing_building_block_keeps_everyone_pending_with_a_reason(self):
        cases = [(['no aaa authorization network default local'], 'aaa authorization network default local'),
                 (['wlan Guest 2 Gast', 'no security web-auth authentication-list'], 'keine Web-Auth-Authentication-List'),
                 (['wlan Guest 2 Gast', 'no security web-auth parameter-map'], 'keine Parameter Map gesetzt'),
                 (['wlan Guest 2 Gast', 'security web-auth authentication-list GIBTSNICHT'], 'GIBTSNICHT ist nicht definiert'),
                 (['wlan Guest 2 Gast', 'security web-auth parameter-map GIBTSNICHT'], 'Parameter Map GIBTSNICHT ist nicht definiert')]
        for extra, text in cases:
            s = self.world(extra)
            self.assertEqual(self.states(s)['1'], 'Webauth Pending', extra)
            self.assertIn(text, self.reasons(s), extra)

    def test_wrong_or_removed_user_is_rejected(self):
        s = self.world(['no username gast1'])
        self.assertEqual(self.states(s)['1'], 'Webauth Pending')
        s = self.world(['username gast1 password Neu#Pw'])
        self.assertEqual(self.states(s)['1'], 'Webauth Pending')

    def test_open_wlan_without_web_auth_connects_everyone_and_the_summary_is_unchanged(self):
        s = self.world(['wlan Guest 2 Gast', 'no security web-auth'])
        self.assertEqual(set(self.states(s).values()), {'Run'})
        self.assertIn('[open]', s.cli.run('show wlan summary'))

    def test_web_auth_on_top_of_psk_requires_both(self):
        clients = [{'mac': '58bf.eaaa.0001', 'ssid': 'Gast', 'ap': 'ap-lobby', 'protocol': '11ac', 'psk': 'Sommer2026',
                    'web': {'user': 'gast1', 'password': 'Gast#1'}}]
        s = self.world(['wlan Guest 2 Gast', 'security wpa akm psk', 'security wpa psk set-key ascii 0 Sommer2026'], clients)
        self.assertEqual(self.states(s)['1'], 'Run')
        s = self.world(['wlan Guest 2 Gast', 'security wpa akm psk', 'security wpa psk set-key ascii 0 Falsch123'], clients)
        self.assertEqual(self.states(s)['1'], 'Not Associated')

    def test_cli_forms_and_prompts(self):
        s = self.world()
        cli = s.cli
        cli.run('configure terminal')
        self.assertEqual(cli.run('parameter-map type webauth PM1'), '')
        self.assertTrue(cli.prompt.endswith('(config-params-parameter-map)#'))
        self.assertEqual(cli.run('type webauth'), '')
        self.assertTrue(cli.run('virtual-ip ipv4 300.1.1.1').startswith('% '))
        self.assertTrue(cli.run('type consent').startswith('% '))
        self.assertEqual(cli.run('virtual-ip ipv4 192.0.2.7'), '')
        self.assertEqual([m['virtualIp'] for m in s.wlc.state()['webauthMaps']], ['192.0.2.7', '192.0.2.1'])   # sortiert nach Name: PM1 vor global
        cli.run('exit')
        for line in ('username a password 0 pw1', 'username b password pw2', 'username c privilege 0 password pw3', 'username d privilege 15 password 0 pw4'):
            self.assertEqual(cli.run(line), '', line)
        for line in ('username e', 'username e password', 'username e secret pw', 'username f privilege 99 password pw', 'aaa authentication login L2 group RG1',
                     'aaa authorization network default group RG1', 'parameter-map type consent PM9'):
            self.assertTrue(cli.run(line).startswith('% '), line)
        self.assertEqual(sorted(u['name'] for u in s.wlc.state()['localUsers']), ['a', 'b', 'c', 'd', 'gast1'])

    def test_dependencies_are_refused_and_the_builtin_map_stays(self):
        s = self.world()
        cli = s.cli
        cli.run('configure terminal')
        self.assertIn('wird von WLANs verwendet', cli.run('no aaa authentication login WEBAUTH'))
        self.assertIn('vordefiniert', cli.run('no parameter-map type webauth global'))
        cli.run('parameter-map type webauth PM2')
        cli.run('exit')
        cli.run('wlan Guest 2 Gast')
        cli.run('security web-auth parameter-map PM2')
        cli.run('exit')
        self.assertIn('wird von WLANs verwendet', cli.run('no parameter-map type webauth PM2'))
        cli.run('wlan Guest 2 Gast')
        cli.run('no security web-auth')
        cli.run('exit')
        self.assertEqual(cli.run('no parameter-map type webauth PM2'), '')
        self.assertEqual(cli.run('no aaa authentication login WEBAUTH'), '')
        self.assertTrue(cli.run('no aaa authentication login WEBAUTH').startswith('% '))

    def test_no_web_auth_clears_list_and_map(self):
        s = self.world(['wlan Guest 2 Gast', 'no security web-auth'])
        w = s.wlc.state()['wlans'][0]
        self.assertEqual((w['webAuth'], w['webAuthList'], w['webAuthMap']), (False, '', ''))

    def test_deleted_parameter_map_in_an_open_submode_does_not_crash(self):
        s = self.world()
        cli = s.cli
        cli.run('configure terminal')
        cli.run('parameter-map type webauth PM3')
        del s.wlc.webauth_maps['PM3']
        self.assertEqual(cli.run('virtual-ip ipv4 192.0.2.9'), '% Das Objekt existiert nicht mehr')

    def test_failed_apply_rolls_back_web_auth_objects(self):
        s = self.world()
        before = s.wlc.state()
        ok, _, _ = s.apply(['username neu password 0 pw', 'aaa authentication login X local', 'no aaa authorization network default local',
                            'parameter-map type webauth PMX', 'virtual-ip ipv4 999.1.1.1'])
        self.assertFalse(ok)
        self.assertEqual(s.wlc.state(), before)


class TestDot1xRadius(unittest.TestCase):
    """802.1X mit RADIUS: Befehlskette nach Cisco-Dokument 213919, Formate aus genieparser; Entscheidungen sind ein Simulator-Modell."""

    def setup(self, extra=()):
        s = aaa_world()
        ok, _, err = s.apply(list(AAA) + list(extra))
        self.assertTrue(ok, err)
        return s

    def by_user(self, s):
        return {c['eap']['user'] + ('!' if c['eap']['password'] == 'falsch' else ''): c for c in s.wlc.clients()}

    def test_full_chain_authenticates_and_shows_the_verified_formats(self):
        s = self.setup()
        c = self.by_user(s)
        self.assertEqual([(c[u]['state'], c[u]['method'], c[u]['vlan']) for u in ('anna', 'bernd', 'carla')], [('Run', 'Dot1x', '20')] * 3)
        self.assertEqual(c['anna!']['state'], 'Not Associated')
        self.assertIn('Access-Reject von RS1', ' '.join(c['anna!']['reasons']))
        self.assertRegex(s.cli.run('show wlan summary').split('\n')[4], r'^1\s+W1\s+Corp1X\s+UP\s+\[WPA2\]\[802\.1x\]\[AES\]$')
        self.assertRegex(s.cli.run('show wireless client summary').split('\n')[4], r'^58bf\.eaaa\.0001\s+ap-lobby\s+WLAN\s+1\s+Run\s+11ac\s+Dot1x\s+Local$')

    def test_show_aaa_servers_uses_the_verified_line_formats(self):
        s = self.setup()
        out = s.cli.run('show aaa servers').split('\n')
        self.assertRegex(out[0], r'^RADIUS:\s+id\s+1,\s+priority\s+1,\s+host\s+10\.10\.0\.50,\s+auth-port\s+1812,\s+acct-port\s+1813,\s*hostname\s+RS1$')
        self.assertRegex(out[1].strip(), r'^State:\s+current\s+UP,\s+duration\s+\S+,\s+previous\s+duration\s+\S+$')
        self.assertRegex(out[2].strip(), r'^Dead:\s+total\s+time\s+\S+,\s+count\s+\d+$')
        self.assertRegex(out[3].strip(), r'^Quarantined:\s+(No|Yes)$')
        s.world['radius']['servers'][0]['up'] = False
        self.assertIn('current DEAD', s.cli.run('show aaa servers'))
        self.assertEqual(Sim().cli.run('show aaa servers'), '')

    def test_every_break_in_the_chain_has_its_own_reason(self):
        cases = [
            ('Zugangsdaten', lambda s: s.world['clients'][0].pop('eap'), 'keine 802.1X-Zugangsdaten'),
            ('ohne Liste', lambda s: s.apply(['wlan W1 1 Corp1X', 'no security dot1x authentication-list']), 'keine 802.1X-Authentication-List'),
            ('Liste undefiniert', lambda s: s.apply(['wlan W1 1 Corp1X', 'security dot1x authentication-list TIPPFEHLER']), 'Authentication List TIPPFEHLER ist nicht definiert'),
            ('Group leer', lambda s: s.apply(['aaa group server radius RG1', 'no server name RS1']), 'Group RG1 enthaelt keinen RADIUS-Server'),
            ('Group undefiniert', lambda s: s.wlc.aaa_groups.pop('RG1'), 'Server Group RG1 der Authentication List L1 ist nicht definiert'),
            ('Server down', lambda s: s.world['radius']['servers'][0].update(up=False), 'RS1 (10.10.0.50) antwortet nicht'),
            ('falsche Adresse', lambda s: s.apply(['radius server RS1', 'address ipv4 10.10.0.99']), 'RS1 (10.10.0.99) antwortet nicht'),
            ('falscher Port', lambda s: s.apply(['radius server RS1', 'address ipv4 10.10.0.50 auth-port 1645 acct-port 1646']), 'Auth-Port 1645 stimmt nicht'),
            ('NAS unbekannt', lambda s: s.world['radius']['servers'][0].update(nas=[]), 'nicht als Client eingetragen'),
            ('Secret falsch', lambda s: s.apply(['radius server RS1', 'key Falsch']), 'Shared Secret stimmt nicht'),
            ('Adresse fehlt', lambda s: s.apply(['radius server RS1', 'address ipv4 0.0.0.0']), 'antwortet nicht'),
        ]
        for name, brk, word in cases:
            with self.subTest(name):
                s = self.setup()
                brk(s)
                anna = next(c for c in s.wlc.clients() if c['mac'] == '58bf.eaaa.0001')
                self.assertEqual(anna['state'], 'Not Associated', name)
                self.assertIn(word, ' '.join(anna['reasons']), name)

    def test_second_server_takes_over_but_a_reject_does_not_fail_over(self):
        s = self.setup(['radius server RS2', 'address ipv4 10.10.0.51', 'key RadiusKey1', 'exit', 'aaa group server radius RG1', 'server name RS2'])
        s.world['radius']['servers'][0]['up'] = False
        s.world['radius']['servers'].append(dict(s.world['radius']['servers'][0], ip='10.10.0.51', up=True))
        c = self.by_user(s)
        self.assertEqual(c['anna']['state'], 'Run', 'RS1 antwortet nicht, RS2 uebernimmt')
        self.assertEqual(c['anna!']['state'], 'Not Associated')
        self.assertIn('Access-Reject von RS2', ' '.join(c['anna!']['reasons']))
        self.assertEqual(s.wlc.wlan_servers(s.wlc.wlans['W1']), ['10.10.0.50', '10.10.0.51'])
        states = {r['name']: r['state'] for r in s.wlc.state()['radiusServers']}
        self.assertEqual(states, {'RS1': 'DEAD', 'RS2': 'UP'})

    def test_aaa_override_decides_whether_the_radius_vlan_applies(self):
        s = self.setup()
        self.assertEqual({u: v['vlan'] for u, v in self.by_user(s).items() if u != 'anna!'}, {'anna': '20', 'bernd': '20', 'carla': '20'})
        s.apply(['wireless profile policy PP', 'aaa-override'])
        c = self.by_user(s)
        self.assertEqual((c['anna']['vlan'], c['bernd']['vlan'], c['carla']['vlan']), ('30', '40', '20'), 'carla hat kein VLAN-Attribut')
        s.apply(['wireless profile policy PP', 'no aaa-override'])
        self.assertEqual(self.by_user(s)['anna']['vlan'], '20')
        self.assertTrue(s.wlc.state()['policies'][0]['aaaOverride'] is False)

    def test_aaa_override_with_local_switching_needs_the_vlan_in_the_flex_profile(self):
        """Annahme (docs/QUELLEN.md): Das per RADIUS gelieferte VLAN muss bei lokalem Switching im Flex Profile stehen."""
        flex = ['wireless profile policy PP', 'no central switching', 'aaa-override', 'vlan LOKAL', 'exit',
                'wireless profile flex FP', 'vlan-name LOKAL', 'vlan-id 20', 'exit', 'exit', 'wireless tag site ST', 'no local-site', 'flex-profile FP', 'exit',
                'ap a4b2.32aa.0001', 'site-tag ST']
        s = self.setup(flex)
        c = self.by_user(s)
        self.assertEqual(c['carla']['vlan'], '20')
        self.assertEqual(c['anna']['state'], 'Not Associated')
        self.assertIn('VLAN 30 ist im Flex Profile FP nicht definiert', ' '.join(c['anna']['reasons']))
        s.apply(['wireless profile flex FP', 'vlan-name V30', 'vlan-id 30', 'vlan-name V40', 'vlan-id 40'])
        c = self.by_user(s)
        self.assertEqual((c['anna']['vlan'], c['bernd']['vlan']), ('30', '40'))

    def test_a_dot1x_client_on_a_psk_wlan_and_the_reverse(self):
        s = self.setup(['wlan W1 1 Corp1X', 'security wpa akm psk', 'security wpa psk set-key ascii 0 Sommer2026'])
        self.assertIn('Pre-Shared Key', ' '.join(self.by_user(s)['anna']['reasons']))
        s2 = aaa_world()
        s2.world['clients'][0].pop('eap')
        s2.world['clients'][0]['psk'] = 'Sommer2026'
        s2.apply(list(AAA))
        self.assertIn('keine 802.1X-Zugangsdaten', ' '.join(s2.wlc.clients()[0]['reasons']))

    def test_cli_modes_validation_and_delete_order(self):
        s = Sim()
        s.cli.run('configure terminal')
        for line in ('aaa new-model', 'radius server RS1'):
            self.assertEqual(s.cli.run(line), '', line)
        self.assertEqual(s.cli.prompt, 'wlc1(config-radius-server)#')
        for bad in ('address ipv4 300.1.1.1', 'address ipv4 1.2.3', 'address ipv6 ::1', 'address ipv4 10.0.0.1 auth-port 0 acct-port 1813',
                    'address ipv4 10.0.0.1 auth-port x acct-port 1813', 'address ipv4 10.0.0.1 port 1812 acct-port 1813', 'key 7 abc', 'key',
                    'timeout 0', 'timeout 5000', 'retransmit 101', 'retransmit x', 'no key', 'bogus'):
            self.assertTrue(s.cli.run(bad).startswith('% '), bad)
        for ok in ('address ipv4 10.0.0.1', 'address ipv4 10.0.0.2 auth-port 1645 acct-port 1646', 'key 0 geheim', 'key anders', 'timeout 7', 'retransmit 0'):
            self.assertEqual(s.cli.run(ok), '', ok)
        self.assertEqual(s.wlc.radius_servers['RS1'], {'ip': '10.0.0.2', 'auth_port': 1645, 'acct_port': 1646, 'key': 'anders', 'timeout': 7, 'retransmit': 0})
        s.cli.run('exit')
        self.assertTrue(s.cli.run('radius server bad!name').startswith('% '))
        self.assertTrue(s.cli.run('aaa group server radius G').startswith('') and s.cli.prompt == 'wlc1(config-sg-radius)#')
        self.assertTrue(s.cli.run('server name NIX').startswith('% '))
        self.assertEqual(s.cli.run('server name RS1'), '')
        self.assertEqual(s.cli.run('server name RS1'), '', 'doppelt eintragen ist kein Fehler')
        self.assertEqual(s.wlc.aaa_groups['G']['servers'], ['RS1'])
        self.assertTrue(s.cli.run('no server name NIX').startswith('% '))
        s.cli.run('exit')
        self.assertTrue(s.cli.run('aaa authentication dot1x L group NIX').startswith('% '))
        self.assertTrue(s.cli.run('aaa authentication dot1x bad!name group G').startswith('% '))
        self.assertEqual(s.cli.run('aaa authentication dot1x L group G'), '')
        s.cli.run('wlan W 1 X')
        s.cli.run('security dot1x authentication-list L')
        s.cli.run('exit')
        for cmd, word in (('no radius server RS1', 'G'), ('no aaa group server radius G', 'L'), ('no aaa authentication dot1x L', 'W')):
            self.assertIn(word, s.cli.run(cmd), cmd)
        for line in ('wlan W 1 X', 'no security dot1x authentication-list', 'exit', 'no aaa authentication dot1x L', 'no aaa group server radius G',
                     'no radius server RS1', 'aaa group server radius G'):
            self.assertEqual(s.cli.run(line), '', line)
        self.assertTrue(s.cli.run('no radius server RS1').startswith('% '))
        self.assertTrue(s.cli.run('no aaa group server radius NIX').startswith('% '))
        self.assertTrue(s.cli.run('no aaa authentication dot1x NIX').startswith('% '))

    def test_state_exposes_no_secrets_and_the_user(self):
        s = self.setup()
        st = json.dumps(s.wlc.state())
        self.assertNotIn('RadiusKey1', st)
        self.assertNotIn('Passw0rt', st)
        self.assertTrue(s.wlc.state()['radiusServers'][0]['keySet'])
        self.assertEqual([c['user'] for c in s.wlc.state()['clients']], ['anna', 'bernd', 'carla', 'anna'])


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

    def test_cli_and_apply_reject_invalid_bodies_with_400(self):
        cases = {'/wlc/cli': ([], 'text', 5, None, {'command': 5}), '/wlc/api/apply': ([], 'text', 5, None, {'commands': 'x'}, {'commands': [1]})}
        for path, bodies in cases.items():
            for body in bodies:
                req = urllib.request.Request(self.base + path, method='POST', data=json.dumps(body).encode())
                try:
                    urllib.request.urlopen(req)
                    self.fail('%s %r hätte 400 liefern müssen' % (path, body))
                except urllib.error.HTTPError as e:
                    e.read()
                    self.assertEqual(e.code, 400, '%s %r' % (path, body))

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
