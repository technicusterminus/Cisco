"""Aufgabe 2: JSON/XML-Bodies und Parser bauen (Ziel 6.2). Ersetze jeweils `raise NotImplementedError`.
Tests: python3 -m unittest -v test_ex02   (im Ordner ex02_json)"""


def restconf_interface_body(name, description, ip, netmask, enabled=True):
    """Body fuer RESTCONF ietf-interfaces (JSON-Struktur als dict).
    Erwartet: {"ietf-interfaces:interface": {"name": ..., "description": ..., "type": "iana-if-type:ethernetCsmacd",
               "enabled": ..., "ietf-ip:ipv4": {"address": [{"ip": ..., "netmask": ...}]}}}"""
    raise NotImplementedError


def netconf_edit_config_xml(name, description):
    """XML-Zeichenkette fuer <config> mit <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">,
    darin <interface><name>..</name><description>..</description></interface>.
    Der Namespace muss auf <interfaces> stehen. Sonderzeichen (&, <) im Text sind zu escapen."""
    raise NotImplementedError


def users_to_json(users):
    """users: Liste von Tupeln (name, privilege). Rueckgabe: JSON-Text (str) mit
    {"users": [{"name": ..., "privilege": ...}, ...]} nach Name sortiert, Privileg als Zahl."""
    raise NotImplementedError


def parse_ip_int_brief(text):
    """Parst die Ausgabe von 'show ip interface brief' in eine Liste von dicts:
    {"name": str, "ip": str oder None (bei 'unassigned'), "up": bool (Status UND Protokoll up)}.
    Die Kopfzeile wird ignoriert. Spalten: Interface IP-Address OK? Method Status Protocol"""
    raise NotImplementedError
