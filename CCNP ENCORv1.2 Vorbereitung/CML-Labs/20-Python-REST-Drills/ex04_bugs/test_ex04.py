import unittest
import ex04_bugs as m

class T(unittest.TestCase):
    def test_range(self): self.assertEqual(m.vlans_in_range(10, 13), [10, 11, 12, 13])
    def test_mask(self):
        self.assertEqual(m.mask_to_prefix("255.255.255.0"), 24)
        self.assertEqual(m.mask_to_prefix("255.255.254.0"), 23)
        self.assertEqual(m.mask_to_prefix("255.255.255.252"), 30)
        self.assertEqual(m.mask_to_prefix("0.0.0.0"), 0)
    def test_add_vlan(self):
        self.assertEqual(m.add_vlan(10), [10]); self.assertEqual(m.add_vlan(20), [20])
        base = [1]; self.assertEqual(m.add_vlan(2, base), [1, 2]); self.assertEqual(base, [1])
    def test_safe_get(self):
        d = {"a": {"b": 5}}
        self.assertEqual(m.safe_get(d, "a.b"), 5)
        self.assertIsNone(m.safe_get(d, "a.c")); self.assertIsNone(m.safe_get(d, "x.y.z")); self.assertIsNone(m.safe_get({"a": 3}, "a.b"))
    def test_valid(self):
        for v in (1, 4094, "10", 100): self.assertTrue(m.is_valid_vlan(v), v)
        for v in (0, 4095, "abc", None, -5, "", 10.5): self.assertFalse(m.is_valid_vlan(v), v)
if __name__ == "__main__": unittest.main()
