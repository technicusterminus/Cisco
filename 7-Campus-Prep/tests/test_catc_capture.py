"""Das Aufnahme-Werkzeug fuer Catalyst-Center-Antworten: nur reine Funktionen, ohne Netz. Es verbindet sich in den Tests nie."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import catc_capture as cc  # noqa: E402


class TestAnonymizer(unittest.TestCase):
    def test_same_value_gets_the_same_placeholder_and_structure_stays(self):
        a = cc.Anonymizer()
        data = {'response': [{'hostname': 'wlc-zentrale', 'managementIpAddress': '10.1.2.3', 'macAddress': 'AA:BB:CC:00:01:02',
                              'serialNumber': 'FCW1234ABCD', 'id': '6f0a2c1e-5a7d-4b7e-9d0e-1c0a5e5e0001', 'neighbor': 'verbunden mit 10.1.2.3',
                              'count': 5, 'ok': True, 'family': 'Wireless Controller'}]}
        out = a.value(data)
        row = out['response'][0]
        self.assertEqual(row['managementIpAddress'], 'ip-1')
        self.assertEqual(row['neighbor'], 'verbunden mit ip-1', 'derselbe Wert, derselbe Platzhalter')
        self.assertEqual(row['hostname'], 'name-1')
        self.assertTrue(row['macAddress'].startswith('mac-') and row['serialNumber'].startswith('serial-') and row['id'].startswith('uuid-'))
        self.assertEqual((row['count'], row['ok'], row['family']), (5, True, 'Wireless Controller'))
        for secret in ('wlc-zentrale', '10.1.2.3', 'AA:BB:CC', 'FCW1234ABCD', '6f0a2c1e'):
            self.assertNotIn(secret, json.dumps(out))
        # stabil: derselbe Wert in einem anderen Feld bekommt denselben Platzhalter
        self.assertEqual(a.text('10.1.2.3'), a.text('10.1.2.3'))

    def test_secret_keys_are_blacked_out_whatever_the_value(self):
        out = cc.Anonymizer().value({'password': 'geheim', 'Token': 'abc', 'snmpAuthPassphrase': 'x', 'list': [{'secret': 'y'}]})
        self.assertEqual(out, {'password': '<geschwaerzt>', 'Token': '<geschwaerzt>', 'snmpAuthPassphrase': '<geschwaerzt>', 'list': [{'secret': '<geschwaerzt>'}]})

    def test_tool_never_contains_a_credential_or_writes_the_token(self):
        with open(os.path.join(os.path.dirname(cc.__file__), 'catc_capture.py'), encoding='utf-8') as fh:
            src = fh.read()
        self.assertNotIn("open(os.path.join(a.out, 'token", src)
        self.assertEqual(src.count("method='POST'"), 1, 'nur das Token wird per POST geholt')
        self.assertNotIn('verify=False', src)
        self.assertNotIn('CERT_NONE', src)


class TestPaths(unittest.TestCase):
    def test_all_paths_are_get_paths_below_dna_and_limit_handling(self):
        self.assertTrue(all(p.startswith('/dna/') for p in cc.PATHS))
        self.assertEqual(cc.with_limit('/dna/intent/api/v1/site', 5), '/dna/intent/api/v1/site?limit=5')
        self.assertEqual(cc.with_limit('/dna/intent/api/v1/site?offset=1', 5), '/dna/intent/api/v1/site?offset=1&limit=5')
        self.assertEqual(cc.with_limit('/dna/intent/api/v1/network-device/count', 5), '/dna/intent/api/v1/network-device/count')
        self.assertEqual(cc.with_limit('/dna/intent/api/v1/site?limit=2', 5), '/dna/intent/api/v1/site?limit=2')
        self.assertEqual(cc.with_limit('/dna/intent/api/v1/site', 0), '/dna/intent/api/v1/site')
        self.assertEqual(cc.file_name('/dna/intent/api/v1/network-device/count'), 'dna_intent_api_v1_network_device_count.json')

    def test_run_refuses_without_https_and_credentials(self):
        for env in ({}, {'CATC_URL': 'http://x', 'CATC_USER': 'u', 'CATC_PASS': 'p'}, {'CATC_URL': 'https://x', 'CATC_USER': 'u'}):
            old = {k: os.environ.pop(k, None) for k in ('CATC_URL', 'CATC_USER', 'CATC_PASS')}
            try:
                os.environ.update(env)
                with self.assertRaises(SystemExit):
                    cc.run(['--out', '/nonexistent-dir-for-test'])
            finally:
                for k in ('CATC_URL', 'CATC_USER', 'CATC_PASS'):
                    os.environ.pop(k, None)
                os.environ.update({k: v for k, v in old.items() if v is not None})
        self.assertFalse(os.path.exists('/nonexistent-dir-for-test'))


if __name__ == '__main__':
    unittest.main()
