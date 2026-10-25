import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract as e
D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "interfaces.json")))

class T(unittest.TestCase):
    def test_hostname(self): self.assertEqual(e.hostname(D), "SW-LAB1")
    def test_enabled(self): self.assertEqual(e.enabled_interfaces(D), ["GigabitEthernet1/0/1", "GigabitEthernet1/0/2", "GigabitEthernet1/0/24", "Vlan10"])
    def test_trunk(self): self.assertEqual(e.trunk_vlans(D), [10, 20, 99])
    def test_ip(self):
        self.assertEqual(e.ip_of(D, "Vlan10"), "192.168.10.1")
        self.assertIsNone(e.ip_of(D, "GigabitEthernet1/0/1"))
        self.assertIsNone(e.ip_of(D, "Nope"))
    def test_access(self):
        self.assertEqual(e.access_ports_in_vlan(D, 10), ["GigabitEthernet1/0/1"])
        self.assertEqual(e.access_ports_in_vlan(D, 99), ["GigabitEthernet1/0/3"])
        self.assertEqual(e.access_ports_in_vlan(D, 5), [])
if __name__ == "__main__": unittest.main()
