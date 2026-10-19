import json
from xml.sax.saxutils import escape


def restconf_interface_body(name, description, ip, netmask, enabled=True):
    return {"ietf-interfaces:interface": {"name": name, "description": description,
            "type": "iana-if-type:ethernetCsmacd", "enabled": enabled,
            "ietf-ip:ipv4": {"address": [{"ip": ip, "netmask": netmask}]}}}


def netconf_edit_config_xml(name, description):
    return ('<config><interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">'
            f'<interface><name>{escape(name)}</name><description>{escape(description)}</description></interface>'
            '</interfaces></config>')


def users_to_json(users):
    return json.dumps({"users": [{"name": n, "privilege": int(p)} for n, p in sorted(users)]})


def parse_ip_int_brief(text):
    rows = []
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split()
        name, ip = parts[0], parts[1]
        status, proto = " ".join(parts[4:-1]), parts[-1]
        rows.append({"name": name, "ip": None if ip == "unassigned" else ip, "up": status == "up" and proto == "up"})
    return rows
