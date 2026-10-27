"""Ersteinrichtung des APIC (Setup-Dialog an der Konsole) wie beim echten APIC."""
import ipaddress
import re

DEFAULTS = {'fabricName': 'ACI Fabric1', 'fabricId': '1', 'ctrlCount': '1', 'podId': '1', 'standby': 'NO',
            'ctrlId': '1', 'ctrlName': 'apic1', 'tepPool': '10.0.0.0/16', 'infraVlan': '3967',
            'gipo': '225.0.0.0/15', 'oobIp': '192.168.10.1/24', 'oobGw': '192.168.10.254',
            'speed': 'auto', 'strong': 'Y', 'pwd': 'admin'}

# (Schluessel, Abschnitt, Frage, Vorschlag im Dialog; None = keine Vorgabe)
QUESTIONS = [
    ('fabricName', 'Cluster configuration ...', 'Enter the fabric name', 'ACI Fabric1'),
    ('fabricId', None, 'Enter the fabric ID (1-128)', '1'),
    ('ctrlCount', None, 'Enter the number of active controllers in the fabric (1-9)', '3'),
    ('podId', None, 'Enter the POD ID (1-254)', '1'),
    ('standby', None, 'Is this a standby controller?', 'NO'),
    ('ctrlId', None, 'Enter the controller ID (1-3)', '1'),
    ('ctrlName', None, 'Enter the controller name', 'apic1'),
    ('tepPool', None, 'Enter address pool for TEP addresses', '10.0.0.0/16'),
    ('infraVlan', None, 'Enter the VLAN ID for infra network (2-4094)', None),
    ('gipo', None, 'Enter address pool for BD multicast addresses (GIPO)', '225.0.0.0/15'),
    ('oobIp', 'Out-of-band management configuration ...', 'Enter the IPv4 address', '192.168.10.1/24'),
    ('oobGw', None, 'Enter the IPv4 address of the default gateway', None),
    ('speed', None, 'Enter the interface speed/duplex mode', 'auto'),
    ('strong', 'admin user configuration ...', 'Enable strong passwords?', 'Y'),
    ('pwd', None, 'Enter the password for admin', None),
]

NOTES = {'infraVlan': 'Note: The infra VLAN ID should not be used elsewhere in your environment\n'
                      '      and should not overlap with any other reserved VLANs on other platforms.',
         'tepPool': 'Note: The TEP pool must not overlap with any other subnet used in the fabric\n'
                    '      (OOB, in-band, tenant subnets). It cannot be changed without wiping the fabric.'}

NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 _.-]{0,62}$')


def validate(key, val, ans):
    """Prueft eine Antwort. Rueckgabe: Fehlertext oder None."""
    v = (val or '').strip()
    if not v and key != 'pwd':
        return 'Error: a value is required'
    if key == 'fabricName':
        return None if NAME_RE.match(v) else 'Error: invalid fabric name (1-63 characters: letters, digits, space, _ . -)'
    if key in ('fabricId', 'ctrlCount', 'podId', 'ctrlId'):
        lim = {'fabricId': (1, 128), 'ctrlCount': (1, 9), 'podId': (1, 254), 'ctrlId': (1, 9)}[key]
        if not v.isdigit() or not lim[0] <= int(v) <= lim[1]:
            return 'Error: value must be between %d and %d' % lim
        if key == 'ctrlId' and int(v) > int(ans.get('ctrlCount', 1)):
            return 'Error: controller ID must not exceed the number of active controllers (%s)' % ans.get('ctrlCount')
        return None
    if key == 'standby':
        return None if v.upper() in ('NO', 'N', 'YES', 'Y') else 'Error: answer YES or NO'
    if key == 'ctrlName':
        return None if re.match(r'^[A-Za-z][A-Za-z0-9-]{0,63}$', v) else 'Error: invalid controller name'
    if key == 'tepPool':
        try:
            n = ipaddress.ip_network(v, strict=True)
        except ValueError:
            return 'Error: invalid address pool, use network/mask, e.g. 10.0.0.0/16'
        if n.version != 4 or not 16 <= n.prefixlen <= 22:
            return 'Error: TEP pool must be an IPv4 network with a prefix length between /16 and /22'
        if not n.is_private:
            return 'Error: TEP pool should be a private (RFC 1918) range'
        if n.overlaps(ipaddress.ip_network('172.17.0.0/16')):
            return 'Error: 172.17.0.0/16 is reserved for internal Docker networking on the APIC'
        return None
    if key == 'infraVlan':
        if not v.isdigit() or not 2 <= int(v) <= 4094:
            return 'Error: VLAN ID must be between 2 and 4094'
        if 3915 <= int(v) <= 4042 and int(v) != 3967:
            return 'Error: VLAN %s is in a reserved range (3915-4042) - use e.g. 3967' % v
        return None
    if key == 'gipo':
        try:
            n = ipaddress.ip_network(v, strict=True)
        except ValueError:
            return 'Error: invalid multicast pool'
        if not n.is_multicast or n.prefixlen != 15:
            return 'Error: GIPo pool must be a /15 multicast range, e.g. 225.0.0.0/15'
        return None
    if key == 'oobIp':
        try:
            i = ipaddress.ip_interface(v)
            assert '/' in v and i.version == 4 and i.network.prefixlen < 31
        except (ValueError, AssertionError):
            return 'Error: enter IPv4 address with mask, e.g. 192.168.10.1/24'
        tep = ans.get('tepPool')
        if tep and ipaddress.ip_network(tep).overlaps(i.network):
            return 'Error: OOB subnet overlaps with the TEP pool %s' % tep
        return None
    if key == 'oobGw':
        try:
            g = ipaddress.ip_address(v)
        except ValueError:
            return 'Error: invalid gateway address'
        oob = ipaddress.ip_interface(ans.get('oobIp', '192.168.10.1/24'))
        if g not in oob.network or g == oob.ip:
            return 'Error: gateway must be in the OOB subnet %s and differ from the APIC address' % oob.network
        return None
    if key == 'speed':
        return None if v in ('auto', '10baseT/Half', '10baseT/Full', '100baseT/Half', '100baseT/Full', '1000baseT/Full') \
            else 'Error: auto, 100baseT/Full or 1000baseT/Full'
    if key == 'strong':
        return None if v.upper() in ('Y', 'N', 'YES', 'NO') else 'Error: answer Y or N'
    if key == 'pwd':
        if str(ans.get('strong', 'Y')).upper().startswith('Y'):
            classes = sum(bool(re.search(p, v)) for p in (r'[a-z]', r'[A-Z]', r'[0-9]', r'[^A-Za-z0-9]'))
            if len(v) < 8 or classes < 3:
                return ('Error: strong password required: at least 8 characters with at least three of: '
                        'lower case, upper case, digit, special character')
            if 'admin' in v.lower() or 'cisco' in v.lower():
                return 'Error: password must not contain the user name or "cisco"'
        elif not v:
            return 'Error: password must not be empty'
        return None
    return 'Error: unknown parameter'


def normalize(ans):
    out = dict(DEFAULTS)
    out.update({k: str(v).strip() for k, v in ans.items() if k in DEFAULTS and v is not None and str(v).strip() != ''})
    out['standby'] = 'YES' if out['standby'].upper().startswith('Y') else 'NO'
    out['strong'] = 'Y' if out['strong'].upper().startswith('Y') else 'N'
    return out


def validate_all(ans):
    a = normalize(ans)
    for key, *_ in QUESTIONS:
        err = validate(key, a[key], a)
        if err:
            return key, err
    return None, None


def tep_of(pool, pod, nid):
    """TEP-Adresse eines Switches aus dem TEP-Pool (APIC = .1, Switches dahinter)."""
    n = ipaddress.ip_network(pool or '10.0.0.0/16')
    base = int(n.network_address)
    if n.prefixlen <= 19:
        off = (pod * 16 + nid // 250) * 256 + nid % 250 + 32
    else:
        off = (nid // 250) * 256 + nid % 250 + 32
    return str(ipaddress.ip_address(base + off))


def apic_tep(pool):
    return str(ipaddress.ip_network(pool or '10.0.0.0/16').network_address + 1)


def summary(a):
    return '\n'.join([
        '  Cluster configuration ...',
        '    Fabric name: %s' % a['fabricName'],
        '    Fabric ID: %s' % a['fabricId'],
        '    Number of controllers: %s' % a['ctrlCount'],
        '    Controller name: %s' % a['ctrlName'],
        '    POD ID: %s' % a['podId'],
        '    Controller ID: %s' % a['ctrlId'],
        '    TEP address pool: %s' % a['tepPool'],
        '    Infra VLAN ID: %s' % a['infraVlan'],
        '    Multicast address pool: %s' % a['gipo'],
        '',
        '  Out-of-band management configuration ...',
        '    Management IP address: %s' % a['oobIp'],
        '    Default gateway: %s' % a['oobGw'],
        '    Interface speed/duplex mode: %s' % a['speed'],
        '',
        '  admin user configuration ...',
        '    Strong Passwords: %s' % a['strong'],
        '    User name: admin',
        '    Password: ********'])
