"""Die simulierte Welt: Controller, Access Points und WLAN-Clients. Deterministisch, ohne Zufall."""
import copy
import uuid

NAMESPACE = uuid.UUID('6f0a2c1e-5a7d-4b7e-9d0e-1c0a5e5e0001')


def default_world():
    return {
        'wlc': {'hostname': 'wlc1', 'platformId': 'C9800-CL-K9', 'ip': '10.10.0.10', 'mac': 'aabb.cc00.0100',
                'serial': 'SIM9800CL001', 'version': '17.9.4a', 'location': 'Rechenzentrum', 'uptimeSeconds': 864000},
        'aps': [
            {'name': 'ap-lobby', 'model': '9130AXI', 'ethMac': 'a4b2.32aa.0001', 'radioMac': '2c57.41aa.0001',
             'ip': '10.10.20.11', 'location': 'default location', 'country': 'DE', 'serial': 'SIMAP0000001', 'joined': True},
            {'name': 'ap-lager', 'model': '9130AXI', 'ethMac': 'a4b2.32aa.0002', 'radioMac': '2c57.41aa.0002',
             'ip': '10.10.20.12', 'location': 'default location', 'country': 'DE', 'serial': 'SIMAP0000002', 'joined': True},
        ],
        'clients': [
            {'mac': '58bf.eaaa.0001', 'ssid': 'Corp', 'psk': 'Sommer2026', 'ap': 'ap-lobby', 'protocol': '11ac'},
            {'mac': '58bf.eaaa.0002', 'ssid': 'Corp', 'psk': 'falsch', 'ap': 'ap-lobby', 'protocol': '11ax'},
        ],
    }


def new_world():
    return copy.deepcopy(default_world())


def norm_mac(m):
    h = ''.join(c for c in m.lower() if c in '0123456789abcdef')
    if len(h) != 12:
        raise ValueError('MAC-Adresse ungueltig: %s' % m)
    return '%s.%s.%s' % (h[0:4], h[4:8], h[8:12])


def det_uuid(kind, name):
    return str(uuid.uuid5(NAMESPACE, '%s:%s' % (kind, name)))
