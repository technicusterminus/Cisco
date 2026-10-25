def hostname(data): return data["device"]["hostname"]
def enabled_interfaces(data): return [i["name"] for i in data["interfaces"] if i["enabled"]]
def trunk_vlans(data): return sorted({v for i in data["interfaces"] if i.get("mode") == "trunk" for v in i.get("allowed_vlans", [])})
def ip_of(data, name):
    for i in data["interfaces"]:
        if i["name"] == name: return (i["ipv4"] or {}).get("address")
    return None
def access_ports_in_vlan(data, vlan): return [i["name"] for i in data["interfaces"] if i.get("mode") == "access" and i.get("vlan") == vlan]
