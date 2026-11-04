"""Gemeinsame Konstanten und Hilfsfunktionen der Engine (Adressen, Ports, VLANs)."""
import ipaddress
import re

SEV_PEN = {'critical': 40, 'major': 15, 'minor': 5, 'warning': 1}
EPHEMERAL = 49152
PORT_NAMES = {'ftpData': 20, 'smtp': 25, 'dns': 53, 'http': 80, 'pop3': 110, 'https': 443, 'rtsp': 554}


def vlan_num(encap):
    m = re.match(r'^vlan-(\d+)$', encap or '')
    return int(m.group(1)) if m else None


def pnum(p):
    m = re.match(r'^eth1/(\d+)$', p)
    return int(m.group(1)) if m else None


def net_of(ipmask):
    try:
        return ipaddress.ip_interface(ipmask).network
    except ValueError:
        return None


def ip_of(ipmask):
    try:
        return ipaddress.ip_interface(ipmask).ip
    except ValueError:
        return None


def in_net(ip, net):
    try:
        return ipaddress.ip_address(str(ip)) in ipaddress.ip_network(str(net), strict=False)
    except ValueError:
        return False


def norm_area(a):
    a = str(a or '').strip()
    if a in ('backbone', ''):
        return '0.0.0.0'
    if a.isdigit():
        return str(ipaddress.ip_address(int(a)))
    return a


def port_val(v):
    if v in (None, '', 'unspecified'):
        return None
    if v in PORT_NAMES:
        return PORT_NAMES[v]
    return int(v) if str(v).isdigit() else None
