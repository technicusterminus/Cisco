"""Aufgabe 4: Fuenf typische Fehler in kleinen Netzwerk-Helfern (Ziel 6.1). Finde und behebe sie.
Tests: python3 -m unittest -v test_ex04   (im Ordner ex04_bugs). Die Tests schlagen am Anfang fehl."""


def vlans_in_range(start, end):
    """Alle VLAN-IDs von start bis einschliesslich end."""
    return list(range(start, end))


def mask_to_prefix(mask):
    """'255.255.255.0' -> 24, '255.255.254.0' -> 23."""
    return sum(1 for octet in mask.split(".") if octet == "255") * 8


def add_vlan(vlan, vlans=[]):
    """Gibt eine NEUE Liste mit dem VLAN zurueck, ohne Aufrufe untereinander zu beeinflussen."""
    vlans.append(vlan)
    return vlans


def safe_get(data, path):
    """safe_get({'a': {'b': 5}}, 'a.b') -> 5; fehlt irgendein Schluessel -> None (keine Exception)."""
    cur = data
    for key in path.split("."):
        cur = cur[key]
    return cur


def is_valid_vlan(value):
    """True fuer ganze Zahlen 1..4094 (int oder Zeichenkette aus Ziffern), sonst False. Auch 0, 4095, 'abc', None -> False."""
    return 1 <= value <= 4094
