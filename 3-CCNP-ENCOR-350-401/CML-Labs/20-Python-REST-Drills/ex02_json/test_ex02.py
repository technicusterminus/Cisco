import json, unittest
import xml.etree.ElementTree as ET
import ex02_json_build as m

IPINT = """Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     10.0.0.1        YES manual up                    up
GigabitEthernet0/1     unassigned      YES unset  administratively down down
Loopback0              1.1.1.1         YES manual up                    up
GigabitEthernet0/2     10.0.2.1        YES manual up                    down"""

class T(unittest.TestCase):
    def test_restconf_body(self):
        b = m.restconf_interface_body("GigabitEthernet2", "Uplink", "10.0.0.1", "255.255.255.0")
        i = b["ietf-interfaces:interface"]
        self.assertEqual(i["name"], "GigabitEthernet2"); self.assertEqual(i["description"], "Uplink")
        self.assertEqual(i["type"], "iana-if-type:ethernetCsmacd"); self.assertIs(i["enabled"], True)
        self.assertEqual(i["ietf-ip:ipv4"]["address"], [{"ip": "10.0.0.1", "netmask": "255.255.255.0"}])
    def test_restconf_disabled(self):
        b = m.restconf_interface_body("Gi1", "x", "1.1.1.1", "255.255.255.255", enabled=False)
        self.assertIs(b["ietf-interfaces:interface"]["enabled"], False)
        json.dumps(b)
    def test_netconf_xml(self):
        x = m.netconf_edit_config_xml("GigabitEthernet2", "R&D <Labor>")
        root = ET.fromstring(x)
        ns = "{urn:ietf:params:xml:ns:yang:ietf-interfaces}"
        ifaces = root.find(ns + "interfaces") if root.tag != ns + "interfaces" else root
        self.assertIsNotNone(ifaces)
        self.assertEqual(ifaces.find(f"{ns}interface/{ns}name").text, "GigabitEthernet2")
        self.assertEqual(ifaces.find(f"{ns}interface/{ns}description").text, "R&D <Labor>")
    def test_users_json(self):
        s = m.users_to_json([("operator", 5), ("admin", 15)])
        d = json.loads(s)
        self.assertEqual(d, {"users": [{"name": "admin", "privilege": 15}, {"name": "operator", "privilege": 5}]})
    def test_parse(self):
        r = m.parse_ip_int_brief(IPINT)
        self.assertEqual(len(r), 4)
        self.assertEqual(r[0], {"name": "GigabitEthernet0/0", "ip": "10.0.0.1", "up": True})
        self.assertEqual(r[1], {"name": "GigabitEthernet0/1", "ip": None, "up": False})
        self.assertFalse(r[3]["up"])
if __name__ == "__main__": unittest.main()
