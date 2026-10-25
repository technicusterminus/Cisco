# Was gibt das aus? (json)
import json
raw = '{"interface": {"name": "Gi1", "enabled": true, "ipv4": {"address": [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}]}}}'
data = json.loads(raw)
print(type(data), data["interface"]["enabled"])
print([a["ip"] for a in data["interface"]["ipv4"]["address"]])
print(json.dumps({"vlan": 10, "name": "USERS"}, sort_keys=True))
