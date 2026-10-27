"""Tenant per REST-API mit Python anlegen und Faults auslesen.

Aufruf: python3 python-tenant.py [http://localhost:8080]
Nur Standardbibliothek, laeuft gegen Simulator und echten APIC
(beim echten APIC https:// und ggf. Zertifikatspruefung beachten).
"""
import json
import sys
import urllib.request
from http.cookiejar import CookieJar

APIC = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8080'
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def call(method, path, body=None):
    req = urllib.request.Request(APIC + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with opener.open(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())['imdata'][0]['error']['attributes']
        raise SystemExit('Fehler %s: %s' % (err['code'], err['text']))


call('POST', '/api/aaaLogin.json', {'aaaUser': {'attributes': {'name': 'admin', 'pwd': 'admin'}}})


def mo(cls, attrs, *children):
    return {cls: {'attributes': attrs, 'children': list(children)}}


tenant = mo('fvTenant', {'name': 'PyTenant'},
            mo('fvCtx', {'name': 'v1'}),
            mo('fvBD', {'name': 'bd1'}, mo('fvRsCtx', {'tnFvCtxName': 'v1'}), mo('fvSubnet', {'ip': '172.20.1.1/24'})),
            mo('fvAp', {'name': 'app'},
               mo('fvAEPg', {'name': 'epg1'}, mo('fvRsBd', {'tnFvBDName': 'bd1'}),
                  # absichtlich ohne Domain: der Static Port erzeugt Fault F0467
                  mo('fvRsPathAtt', {'tDn': 'topology/pod-1/paths-101/pathep-[eth1/40]', 'encap': 'vlan-400'}))))
call('POST', '/api/mo/uni.json', tenant)
print('Tenant PyTenant angelegt.')

res = call('GET', '/api/mo/uni/tn-PyTenant.json?rsp-subtree-include=faults,no-scoped')
for f in res['imdata']:
    a = f['faultInst']['attributes']
    print('%s %s: %s' % (a['severity'], a['code'], a['descr']))

eps = call('GET', '/api/class/fvCEp.json')
print('%s Endpoints in der Fabric gelernt.' % eps['totalCount'])
