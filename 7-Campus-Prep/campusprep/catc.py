"""Simuliertes Catalyst Center (Intent API, Teilumfang).

Belegt: Pfade und Header (dnacentersdk), Feldnamen von network-device (cisco.dnac network_device_info).
Wissen/Festlegung: Token-Antwort {"Token": ...}, Werte wie family/softwareType, Fehlerantworten (docs/QUELLEN.md).
Das Catalyst Center hat keinen eigenen Bestand: Es liest den Controller und die APs aus der gemeinsamen Welt.
"""
import base64
import hashlib

from .world import det_uuid

AUTH = '/dna/system/api/v1/auth/token'
DEVICE = '/dna/intent/api/v1/network-device'
# Filter von get_device_list (REST-Namen in camelCase), soweit der Simulator sie auswertet
FILTERS = ('hostname', 'managementIpAddress', 'macAddress', 'family', 'platformId', 'role', 'reachabilityStatus',
           'softwareVersion', 'serialNumber', 'type', 'id', 'associatedWlcIp')


class CatalystCenter:
    def __init__(self, world, users=None):
        self.world = world
        self.users = users or {'admin': 'admin'}   # Uebungswerte, keine echten Zugangsdaten
        self.tokens = {}
        self._n = 0

    # ------------------------------------------------------------------ Inventar aus der Welt
    def devices(self):
        w = self.world['wlc']
        out = [{
            'id': det_uuid('device', w['hostname']), 'instanceUuid': det_uuid('device', w['hostname']),
            'hostname': w['hostname'], 'managementIpAddress': w['ip'], 'macAddress': w['mac'], 'serialNumber': w['serial'],
            'platformId': w['platformId'], 'softwareType': 'IOS-XE', 'softwareVersion': w['version'],
            'family': 'Wireless Controller', 'type': 'Cisco Catalyst 9800 Series Wireless Controller', 'role': 'ACCESS',
            'reachabilityStatus': 'Reachable', 'managementState': 'Managed', 'collectionStatus': 'Managed',
            'location': None, 'upTime': '10 days, 0:00:00.00', 'uptimeSeconds': w['uptimeSeconds'],
            'associatedWlcIp': '', 'apManagerInterfaceIp': '', 'vendor': 'Cisco', 'description': '',
        }]
        for a in self.world['aps']:
            if not a.get('joined'):
                continue
            out.append({
                'id': det_uuid('device', a['name']), 'instanceUuid': det_uuid('device', a['name']),
                'hostname': a['name'], 'managementIpAddress': a['ip'], 'macAddress': a['ethMac'], 'serialNumber': a['serial'],
                'platformId': 'C' + a['model'] + '-E', 'softwareType': 'Cisco Controller', 'softwareVersion': w['version'],
                'family': 'Unified AP', 'type': 'Cisco Catalyst %s Series Unified Access Point' % a['model'], 'role': 'ACCESS',
                'reachabilityStatus': 'Reachable', 'managementState': 'Managed', 'collectionStatus': 'Managed',
                'location': None, 'upTime': '1 day, 0:00:00.00', 'uptimeSeconds': 86400,
                'associatedWlcIp': w['ip'], 'apManagerInterfaceIp': w['ip'], 'vendor': 'Cisco', 'description': '',
            })
        return out

    # ------------------------------------------------------------------ Authentifizierung
    def _token(self, user):
        self._n += 1
        return hashlib.sha256(('%s:%d' % (user, self._n)).encode()).hexdigest()

    def login(self, authorization):
        try:
            kind, enc = (authorization or '').split(' ', 1)
            user, pw = base64.b64decode(enc).decode().split(':', 1)
            assert kind.lower() == 'basic'
        except Exception:
            return None
        if self.users.get(user) != pw:
            return None
        tok = self._token(user)
        self.tokens[tok] = user
        return tok

    # ------------------------------------------------------------------ Anfragen
    def handle(self, method, path, query=None, headers=None, body=None):
        """Rueckgabe (HTTP-Status, JSON-Objekt). query: dict name -> Liste/Text. headers: Kleinschreibung."""
        query = {k: (v[0] if isinstance(v, list) else v) for k, v in (query or {}).items()}
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        if path == AUTH:
            if method != 'POST':
                return 405, {'error': 'Methode nicht erlaubt'}
            tok = self.login(headers.get('authorization'))
            if tok is None:
                return 401, {'error': 'Authentifizierung fehlgeschlagen'}
            return 200, {'Token': tok}
        if headers.get('x-auth-token') not in self.tokens:
            return 401, {'error': 'X-Auth-Token fehlt oder ist ungueltig'}
        if method == 'GET' and path == DEVICE + '/count':
            return 200, {'response': len(self._filtered(query)), 'version': '1.0'}
        if method == 'GET' and path == DEVICE:
            devs = self._filtered(query)
            off = int(query.get('offset', 1) or 1)
            lim = int(query['limit']) if query.get('limit') else len(devs)
            return 200, {'response': devs[off - 1:off - 1 + lim], 'version': '1.0'}
        if method == 'GET' and path.startswith(DEVICE + '/'):
            d = next((x for x in self.devices() if x['id'] == path.rsplit('/', 1)[1]), None)
            if d is None:
                return 404, {'error': 'Geraet nicht gefunden'}
            return 200, {'response': d, 'version': '1.0'}
        return 404, {'error': 'Endpunkt im Simulator nicht umgesetzt: %s %s' % (method, path)}

    def _filtered(self, q):
        devs = self.devices()
        for k in FILTERS:
            if q.get(k):
                devs = [d for d in devs if str(d.get(k, '')).lower() == q[k].lower()]
        return devs
