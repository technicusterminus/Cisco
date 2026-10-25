"""Aufgabe 1: Funktionen implementieren (Daten wie in interfaces.json)."""

def hostname(data):
    """Gibt den Hostnamen des Geraets zurueck."""
    raise NotImplementedError

def enabled_interfaces(data):
    """Liste der Namen aller Interfaces mit enabled == True."""
    raise NotImplementedError

def trunk_vlans(data):
    """Liste der auf Trunk-Interfaces erlaubten VLANs (ohne Duplikate, aufsteigend)."""
    raise NotImplementedError

def ip_of(data, name):
    """IPv4-Adresse des Interfaces name, oder None (auch bei ipv4 == null oder unbekanntem Namen)."""
    raise NotImplementedError

def access_ports_in_vlan(data, vlan):
    """Namen aller Access-Interfaces im angegebenen VLAN."""
    raise NotImplementedError
