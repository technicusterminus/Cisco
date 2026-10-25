import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mock_api"))
import server
import ex03_rest_client as c

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.make_server(0); cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()
    def setUp(self): server.reset()
    def tok(self, u="admin", p="Lab#2026!"): return c.get_token(self.base, u, p)
    def test_token(self):
        self.assertEqual(len(self.tok()), 32)
    def test_token_bad(self):
        with self.assertRaises(PermissionError): c.get_token(self.base, "admin", "falsch")
    def test_pagination(self):
        devs = c.get_all_devices(self.base, self.tok())
        self.assertEqual(len(devs), 25)
        self.assertEqual(devs[0]["id"], "dev-001"); self.assertEqual(devs[-1]["id"], "dev-025")
        self.assertEqual(len({d["id"] for d in devs}), 25)
    def test_get_device(self):
        t = self.tok()
        self.assertEqual(c.get_device(self.base, t, "dev-007")["hostname"], "sw07.lab.local")
        self.assertIsNone(c.get_device(self.base, t, "dev-999"))
    def test_set_description(self):
        t = self.tok()
        task = c.set_description(self.base, t, "dev-003", "Core Musterstadt")
        self.assertEqual(len(task), 32)
        self.assertEqual(c.get_device(self.base, t, "dev-003")["description"], "Core Musterstadt")
    def test_set_description_errors(self):
        v = self.tok("viewer", "View#2026!")
        with self.assertRaises(PermissionError): c.set_description(self.base, v, "dev-001", "x")
        a = self.tok()
        with self.assertRaises(LookupError): c.set_description(self.base, a, "dev-999", "x")
    def test_retry_503(self):
        self.assertEqual(c.get_with_retry(self.base + "/api/v1/flaky")["response"], "ok nach 3 Versuchen")
    def test_retry_429(self):
        self.assertEqual(c.get_with_retry(self.base + "/api/v1/limited")["response"], "ok")
    def test_retry_gives_up(self):
        with self.assertRaises(RuntimeError): c.get_with_retry(self.base + "/api/v1/flaky", retries=2)
if __name__ == "__main__": unittest.main()
