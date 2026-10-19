import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mock_api"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server
import rest_client as c
RW, RO = "lab-key-123", "lab-ro-key"

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.make_server(0); cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()
    def setUp(self): server.reset()
    def test_list(self):
        self.assertEqual([v["id"] for v in c.list_vlans(self.base, RW)], [1, 10, 20])
    def test_list_unauthorized(self):
        with self.assertRaises(PermissionError): c.list_vlans(self.base, "falsch")
    def test_get(self):
        self.assertEqual(c.get_vlan(self.base, RW, 10), {"id": 10, "name": "USERS"})
        self.assertIsNone(c.get_vlan(self.base, RW, 999))
    def test_create(self):
        self.assertEqual(c.create_vlan(self.base, RW, 30, "VOICE"), {"id": 30, "name": "VOICE"})
        self.assertEqual(c.get_vlan(self.base, RW, 30)["name"], "VOICE")
    def test_create_errors(self):
        with self.assertRaises(FileExistsError): c.create_vlan(self.base, RW, 10, "DOPPELT")
        with self.assertRaises(PermissionError): c.create_vlan(self.base, RO, 40, "X")
        with self.assertRaises(ValueError): c.create_vlan(self.base, RW, 5000, "ZUGROSS")
    def test_replace_and_rename(self):
        self.assertEqual(c.replace_vlan(self.base, RW, 20, "SRV"), {"id": 20, "name": "SRV"})
        self.assertEqual(c.rename_vlan(self.base, RW, 20, "SERVERS")["name"], "SERVERS")
        with self.assertRaises(LookupError): c.replace_vlan(self.base, RW, 999, "X")
        with self.assertRaises(LookupError): c.rename_vlan(self.base, RW, 999, "X")
    def test_delete(self):
        self.assertTrue(c.delete_vlan(self.base, RW, 20))
        self.assertFalse(c.delete_vlan(self.base, RW, 20))
        self.assertEqual([v["id"] for v in c.list_vlans(self.base, RW)], [1, 10])
        with self.assertRaises(PermissionError): c.delete_vlan(self.base, RO, 10)
if __name__ == "__main__": unittest.main()
