#!/usr/bin/env python3
"""Abgleich Datacenter Prep <-> echter APIC.

Fuehrt dieselben REST-Pruefungen gegen den Simulator und gegen einen echten APIC
(z. B. die Cisco DevNet Sandbox) aus und listet jede Abweichung auf: Defaults,
Attribute, Fehlercodes, automatisch angelegte Objekte, Relationen, Faults und
Abfrage-Verhalten. Nur Standardbibliothek.

Beispiele:
  # nur lesen (aendert nichts am APIC):
  python3 werkzeuge/abgleich.py --apic https://sandboxapicdc.cisco.com --apic-user admin --insecure

  # zusaetzlich einen Test-Tenant DCP-Abgleich anlegen, pruefen und wieder loeschen:
  python3 werkzeuge/abgleich.py --apic https://apic.lab --apic-user admin --insecure --write

Das Passwort wird abgefragt (oder --apic-password / Umgebungsvariable APIC_PASSWORD).
Ergebnis: Tabelle auf der Konsole, dazu abgleich-bericht.md und abgleich-rohdaten.json.
--write nur gegen einen Lab- oder Sandbox-APIC verwenden, nie gegen eine produktive Fabric.
"""
import argparse
import getpass
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

TENANT = 'DCP-Abgleich'
VOLATILE = {'modTs', 'uid', 'userdom', 'lcOwn', 'childAction', 'status', 'monPolDn', 'extMngdBy', 'dn', 'rn',
            'configIssues', 'pcTag', 'seg', 'bcastP', 'mac', 'rd', 'nameAlias', 'descr', 'ownerKey', 'ownerTag',
            'annotation', 'forceResolve', 'rType', 'tType', 'stateQual', 'tContextDn', 'tRn', 'tCl', 'tDn', 'state', 'triggerSt',
            'exceptionTag', 'txId', 'creator', 'lcC'}


def keep(k, v):
    """Attribut vergleichen? Interne Kennungen (z. B. VRF-scope als Zahl) unterscheiden sich zwischen Fabrics immer."""
    return k not in VOLATILE and not (k == 'scope' and str(v).isdigit())

# Klassen, die auf jedem APIC (auch der Sandbox) existieren und gelesen werden
READ_CLASSES = ['topSystem', 'fabricNode', 'fvTenant', 'fvCtx', 'fvBD', 'fvAEPg', 'fvAp', 'vzBrCP', 'vzFilter', 'vzEntry',
                'l3extOut', 'infraAccPortP', 'infraNodeP', 'fvnsVlanInstP', 'physDomP', 'infraAttEntityP', 'l1PhysIf',
                'ethpmPhysIf', 'fvCEp', 'faultInst', 'firmwareRunning', 'aaaUser', 'fabricPod', 'infraAccPortGrp', 'infraAccBndlGrp',
                'lldpAdjEp', 'isisAdjEp', 'bgpPeerEntry', 'ospfAdjEp', 'actrlRule', 'eqptCh', 'fabricHealthTotal']


def mo(cls, attrs, *children):
    return {cls: {'attributes': attrs, 'children': list(children)}}


class Client:
    def __init__(self, label, base, user, pwd, insecure, timeout=30):
        self.label, self.base, self.user, self.pwd, self.timeout = label, base.rstrip('/'), user, pwd, timeout
        ctx = ssl.create_default_context()
        if insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()), urllib.request.HTTPSHandler(context=ctx))
        self.login_resp = None

    def login(self):
        st, j = self._raw('POST', '/api/aaaLogin.json', {'aaaUser': {'attributes': {'name': self.user, 'pwd': self.pwd}}})
        if st != 200:
            raise SystemExit('%s: Login fehlgeschlagen (%s %s)' % (self.label, st, err_of(j)))
        self.login_resp = j

    def _raw(self, method, path, body=None):
        req = urllib.request.Request(self.base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={'Content-Type': 'application/json'})
        try:
            with self.op.open(req, timeout=self.timeout) as r:
                return r.status, json.loads(r.read() or b'null')
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b'null')
            except ValueError:
                return e.code, None
        except (urllib.error.URLError, OSError) as e:
            raise SystemExit('%s: keine Verbindung zu %s (%s)' % (self.label, self.base, e))

    def req(self, method, path, body=None):
        st, j = self._raw(method, path, body)
        if st == 403 and 'aaaLogin' not in path:
            self.login()
            st, j = self._raw(method, path, body)
        return st, j

    def get(self, path):
        return self.req('GET', path)

    def post(self, path, body):
        return self.req('POST', path, body)


def err_of(j):
    try:
        a = j['imdata'][0]['error']['attributes']
        return {'code': str(a.get('code')), 'text': a.get('text', '')}
    except (TypeError, KeyError, IndexError):
        return None


def attrs_of(j):
    try:
        return next(iter(j['imdata'][0].values()))['attributes']
    except (TypeError, KeyError, IndexError, StopIteration):
        return None


# ---------------------------------------------------------------------------------------------- Pruefungen
# Jede Pruefung liefert pro Ziel eine Beobachtung (JSON-faehig). Verglichen wird die Beobachtung.
# kind: 'equal' = muss gleich sein, 'keys' = Attributnamen (fehlende sind kritisch, zusaetzliche Hinweis)

def p_login(c):
    a = attrs_of(c.login_resp) or {}
    return {'keys': sorted(k for k in a if k not in VOLATILE)}


def p_class(cls):
    def run(c):
        st, j = c.get('/api/class/%s.json?page-size=1' % cls)
        out = {'status': st, 'error': (err_of(j) or {}).get('code')}
        a = attrs_of(j) if st == 200 else None
        out['keys'] = sorted(k for k in a if k not in VOLATILE) if a else None
        return out
    return run


def p_err(path, method='GET', body=None):
    def run(c):
        st, j = c.req(method, path, body)
        e = err_of(j)
        return {'status': st, 'code': e['code'] if e else None, 'count': (j or {}).get('totalCount') if not e and isinstance(j, dict) else None}
    return run


def p_query(path, shape):
    def run(c):
        st, j = c.get(path)
        if st != 200:
            return {'status': st, 'code': (err_of(j) or {}).get('code')}
        return dict({'status': st}, **shape(j))
    return run


def classes_in(j):
    return sorted({next(iter(x)) for x in (j or {}).get('imdata', [])})


def tenant_tree():
    return mo('fvTenant', {'name': TENANT, 'descr': 'Abgleich Datacenter Prep - wird automatisch geloescht'},
              mo('fvCtx', {'name': 'VRF1'}),
              mo('fvBD', {'name': 'BD1'}, mo('fvRsCtx', {'tnFvCtxName': 'VRF1'}), mo('fvSubnet', {'ip': '10.99.1.1/24'})),
              mo('fvBD', {'name': 'BD-ohne-VRF'}),
              mo('vzFilter', {'name': 'tcp-80'}, mo('vzEntry', {'name': 'e1', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '80', 'dToPort': '80'})),
              mo('vzBrCP', {'name': 'web'}, mo('vzSubj', {'name': 's1'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'tcp-80'}))),
              mo('fvAp', {'name': 'AP1'},
                 mo('fvAEPg', {'name': 'EPG1'}, mo('fvRsBd', {'tnFvBDName': 'BD1'}), mo('fvRsProv', {'tnVzBrCPName': 'web'})),
                 mo('fvAEPg', {'name': 'EPG-falscheBD'}, mo('fvRsBd', {'tnFvBDName': 'gibt-es-nicht'})),
                 mo('fvAEPg', {'name': 'EPG-ohneDomain'}, mo('fvRsBd', {'tnFvBDName': 'BD1'}),
                    mo('fvRsPathAtt', {'tDn': 'topology/pod-1/paths-101/pathep-[eth1/33]', 'encap': 'vlan-3999'}))))


TDN = 'uni/tn-' + TENANT


def p_defaults(dn):
    def run(c):
        st, j = c.get('/api/mo/%s.json' % dn)
        a = attrs_of(j) if st == 200 else None
        if not a:
            return {'status': st, 'code': (err_of(j) or {}).get('code')}
        return {'values': {k: v for k, v in sorted(a.items()) if keep(k, v)}}
    return run


def p_children(dn):
    def run(c):
        st, j = c.get('/api/mo/%s.json?query-target=children' % dn)
        return {'status': st, 'classes': classes_in(j) if st == 200 else None}
    return run


def p_rel(dn):
    def run(c):
        st, j = c.get('/api/mo/%s.json' % dn)
        a = attrs_of(j) if st == 200 else None
        return {'status': st, 'state': a.get('state') if a else None, 'tCl': a.get('tCl') if a else None,
                'tDn': (a.get('tDn') or '') if a else None}
    return run


def p_faults(dn, wait):
    def run(c):
        end = time.time() + wait
        while True:
            st, j = c.get('/api/mo/%s.json?rsp-subtree-include=faults,no-scoped&query-target=subtree' % dn)
            codes = sorted({x['faultInst']['attributes']['code'] for x in (j or {}).get('imdata', []) if 'faultInst' in x
                            and not x['faultInst']['attributes']['code'].startswith('S')})  # S-Codes gibt es nur im Simulator
            if codes or time.time() > end:
                return {'status': st, 'codes': codes}
            time.sleep(2)
    return run


def read_probes():
    P = [('Login', 'Antwortfelder von aaaLogin', 'keys', p_login)]
    for cls in READ_CLASSES:
        P.append(('Klasse', cls, 'class', p_class(cls)))
    P += [
        ('Fehler', 'GET unbekannte Klasse fvGibtsNicht', 'equal', p_err('/api/class/fvGibtsNicht.json')),
        ('Fehler', 'GET DN, den es nicht gibt', 'equal', p_err('/api/mo/uni/tn-gibt-es-nicht-4711.json')),
        ('Fehler', 'Filter mit Syntaxfehler', 'equal', p_err('/api/class/fvTenant.json?query-target-filter=eq(fvTenant.name,"a"')),
        ('Fehler', 'Filter auf unbekanntes Attribut', 'equal', p_err('/api/class/fvTenant.json?query-target-filter=eq(fvTenant.gibtsnicht,"a")')),
        ('Fehler', 'query-target mit falschem Wert', 'equal', p_err('/api/mo/uni/tn-common.json?query-target=irgendwas')),
        ('Fehler', 'Ohne Login (neue Sitzung)', 'noauth', None),
        ('Abfrage', 'tn-common children, nur fvBD', 'equal', p_query('/api/mo/uni/tn-common.json?query-target=children&target-subtree-class=fvBD',
                                                                     lambda j: {'classes': classes_in(j)})),
        ('Abfrage', 'Filter eq auf Namen', 'equal', p_query('/api/class/fvTenant.json?query-target-filter=eq(fvTenant.name,"common")',
                                                          lambda j: {'count': j.get('totalCount'), 'type': type(j.get('totalCount')).__name__})),
        ('Abfrage', 'Filter wcard', 'equal', p_query('/api/class/fvTenant.json?query-target-filter=wcard(fvTenant.name,"^comm")',
                                                   lambda j: {'count': j.get('totalCount')})),
        ('Abfrage', 'rsp-subtree-include=count', 'equal', p_query('/api/class/fvTenant.json?query-target-filter=eq(fvTenant.name,"common")&rsp-subtree-include=count',
                                                                lambda j: {'classes': classes_in(j)})),
        ('Abfrage', 'rsp-subtree=children liefert Kinder', 'equal', p_query('/api/mo/uni/tn-common.json?rsp-subtree=children&rsp-subtree-class=fvCtx',
                                                                          lambda j: {'childClasses': sorted({next(iter(ch)) for x in j.get('imdata', []) for ch in next(iter(x.values())).get('children', [])})})),
        ('Abfrage', 'page-size=1: totalCount = Gesamtzahl?', 'equal', p_query('/api/class/fvTenant.json?page-size=1&page=0',
                                                                            lambda j: {'rows': len(j.get('imdata', [])), 'totalIsAll': int(j.get('totalCount', 0)) > 1})),
        ('Abfrage', 'order-by absteigend', 'equal', p_query('/api/class/fvTenant.json?order-by=fvTenant.name|desc&page-size=3',
                                                          lambda j: {'sorted_desc': [x['fvTenant']['attributes']['name'] for x in j.get('imdata', [])]
                                                                     == sorted([x['fvTenant']['attributes']['name'] for x in j.get('imdata', [])], reverse=True)})),
        ('Abfrage', 'Kinder von tn-common', 'equal', p_children('uni/tn-common')),
    ]
    return P


def write_probes(wait):
    T = TDN
    P = [('Schreiben', 'Tenant-Baum anlegen (atomarer POST)', 'equal', p_err('/api/mo/uni.json', 'POST', tenant_tree()))]
    for name, dn in [('Defaults fvTenant', T), ('Defaults fvCtx', T + '/ctx-VRF1'), ('Defaults fvBD', T + '/BD-BD1'),
                     ('Defaults fvSubnet', T + '/BD-BD1/subnet-[10.99.1.1/24]'), ('Defaults fvAp', T + '/ap-AP1'),
                     ('Defaults fvAEPg', T + '/ap-AP1/epg-EPG1'), ('Defaults vzFilter', T + '/flt-tcp-80'),
                     ('Defaults vzEntry', T + '/flt-tcp-80/e-e1'), ('Defaults vzBrCP', T + '/brc-web'), ('Defaults vzSubj', T + '/brc-web/subj-s1'),
                     ('Defaults fvRsPathAtt', T + '/ap-AP1/epg-EPG-ohneDomain/rspathAtt-[topology/pod-1/paths-101/pathep-[eth1/33]]')]:
        P.append(('Defaults', name, 'values', p_defaults(dn)))
    for name, dn in [('automatische Kinder fvTenant', T), ('automatische Kinder fvCtx', T + '/ctx-VRF1'), ('automatische Kinder fvBD', T + '/BD-BD1'),
                     ('automatische Kinder BD ohne VRF', T + '/BD-BD-ohne-VRF'), ('automatische Kinder fvAEPg', T + '/ap-AP1/epg-EPG1')]:
        P.append(('Auto-Objekte', name, 'equal', p_children(dn)))
    P += [
        ('Relation', 'fvRsBd auf vorhandene BD', 'equal', p_rel(T + '/ap-AP1/epg-EPG1/rsbd')),
        ('Relation', 'fvRsBd auf fehlende BD', 'equal', p_rel(T + '/ap-AP1/epg-EPG-falscheBD/rsbd')),
        ('Relation', 'BD ohne fvRsCtx', 'equal', p_rel(T + '/BD-BD-ohne-VRF/rsctx')),
        ('Relation', 'fvRsProv auf Contract', 'equal', p_rel(T + '/ap-AP1/epg-EPG1/rsprov-web')),
        ('Faults', 'Faults im Test-Tenant (Static Port ohne Domain, fehlende BD …)', 'equal', p_faults(T, wait)),
        ('Fehler', 'ungültiger Enum-Wert (fvBD arpFlood=vielleicht)', 'equal',
         p_err('/api/mo/%s/BD-BD1.json' % T, 'POST', mo('fvBD', {'name': 'BD1', 'arpFlood': 'vielleicht'}))),
        ('Fehler', 'ungültige IP im fvSubnet', 'equal', p_err('/api/mo/%s/BD-BD1.json' % T, 'POST', mo('fvBD', {'name': 'BD1'}, mo('fvSubnet', {'ip': '10.99.300.1/24'})))),
        ('Fehler', 'unbekannte Klasse im POST', 'equal', p_err('/api/mo/%s.json' % T, 'POST', mo('fvGibtsNicht', {'name': 'x'}))),
        ('Fehler', 'unbekanntes Attribut', 'equal', p_err('/api/mo/%s.json' % T, 'POST', mo('fvTenant', {'name': TENANT, 'gibtsNicht': 'x'}))),
        ('Fehler', 'Kind unter falschem Eltern-Objekt (fvBD unter fvAp)', 'equal',
         p_err('/api/mo/%s/ap-AP1.json' % T, 'POST', mo('fvAp', {'name': 'AP1'}, mo('fvBD', {'name': 'X'})))),
        ('Fehler', 'Name mit Leerzeichen', 'equal', p_err('/api/mo/%s.json' % T, 'POST', mo('fvTenant', {'name': TENANT}, mo('fvCtx', {'name': 'a b'})))),
        ('Fehler', 'Name passt nicht zum DN', 'equal', p_err('/api/mo/%s/ctx-VRF1.json' % T, 'POST', mo('fvCtx', {'name': 'VRF2'}))),
        ('Fehler', 'Eltern fehlen', 'equal', p_err('/api/mo/uni/tn-gibt-es-nicht-4711/ctx-x.json', 'POST', mo('fvCtx', {'name': 'x'}))),
        ('Fehler', 'atomar: Fehler im Baum verwirft alles', 'equal', None),
        ('Schreiben', 'DELETE auf nicht vorhandenes Objekt', 'equal', p_err('/api/mo/%s/ctx-gibtsnicht.json' % T, 'DELETE')),
    ]
    return P


def p_atomic(c):
    st, j = c.post('/api/mo/%s.json' % TDN, mo('fvTenant', {'name': TENANT}, mo('fvCtx', {'name': 'atomar-ok'}), mo('fvBD', {'name': 'atomar', 'arpFlood': 'kaputt'})))
    st2, j2 = c.get('/api/mo/%s/ctx-atomar-ok.json' % TDN)
    return {'status': st, 'code': (err_of(j) or {}).get('code'), 'ctxAngelegt': bool((j2 or {}).get('imdata'))}


def p_noauth(c):
    fresh = Client(c.label, c.base, c.user, c.pwd, True, c.timeout)
    st, j = fresh._raw('GET', '/api/class/fvTenant.json')
    return {'status': st, 'code': (err_of(j) or {}).get('code')}


# ---------------------------------------------------------------------------------------------- Vergleich
def compare(kind, a, b):
    """-> (Ergebnis, Detail). a = Simulator, b = APIC."""
    if kind in ('keys', 'class', 'values'):
        if kind == 'class' and (a.get('status') != b.get('status') or a.get('error') != b.get('error')):
            return 'abweichend', 'Status Sim %s/%s, APIC %s/%s' % (a.get('status'), a.get('error'), b.get('status'), b.get('error'))
        if kind == 'values':
            if 'values' not in a or 'values' not in b:
                return ('gleich', '') if a == b else ('abweichend', 'Sim %s, APIC %s' % (a, b))
            va, vb = a['values'], b['values']
            missing = sorted(set(vb) - set(va))
            extra = sorted(set(va) - set(vb))
            diff = ['%s: Sim %r, APIC %r' % (k, va[k], vb[k]) for k in sorted(set(va) & set(vb)) if va[k] != vb[k]]
            parts = []
            if diff:
                parts.append('andere Werte: ' + '; '.join(diff))
            if missing:
                parts.append('fehlt im Sim: ' + ', '.join(missing))
            if extra:
                parts.append('nur im Sim: ' + ', '.join(extra))
            return ('abweichend' if diff else 'unvollständig' if missing else 'gleich'), ' | '.join(parts)
        ka, kb = set(a.get('keys') or []), set(b.get('keys') or [])
        if not kb or not ka:
            return 'gleich', 'keine Instanz zum Vergleichen' if not kb else 'im Sim keine Instanz'
        missing, extra = sorted(kb - ka), sorted(ka - kb)
        det = ('fehlt im Sim: ' + ', '.join(missing) if missing else '') + (' | nur im Sim: ' + ', '.join(extra) if extra else '')
        return ('unvollständig' if missing else 'gleich'), det.strip(' |')
    if a == b:
        return 'gleich', ''
    return 'abweichend', 'Sim %s | APIC %s' % (json.dumps(a, ensure_ascii=False), json.dumps(b, ensure_ascii=False))


def cleanup(c):
    c.post('/api/mo/uni.json', mo('fvTenant', {'name': TENANT, 'status': 'deleted'}))


def main():
    ap = argparse.ArgumentParser(description='Datacenter Prep mit einem echten APIC abgleichen')
    ap.add_argument('--sim', default='http://localhost:8080', help='Datacenter Prep (Standard http://localhost:8080)')
    ap.add_argument('--sim-user', default='admin')
    ap.add_argument('--sim-password', default=os.environ.get('SIM_PASSWORD', 'admin'))
    ap.add_argument('--apic', required=True, help='echter APIC, z. B. https://sandboxapicdc.cisco.com')
    ap.add_argument('--apic-user', default='admin')
    ap.add_argument('--apic-password', default=os.environ.get('APIC_PASSWORD'))
    ap.add_argument('--insecure', action='store_true', help='Zertifikat des APIC nicht pruefen (Lab mit selbstsigniertem Zertifikat)')
    ap.add_argument('--write', action='store_true', help='Test-Tenant %s anlegen, pruefen und loeschen' % TENANT)
    ap.add_argument('--fault-wait', type=float, default=20, help='Sekunden, die auf Faults gewartet wird (Standard 20)')
    ap.add_argument('--out', default='.', help='Ordner fuer abgleich-bericht.md und abgleich-rohdaten.json')
    a = ap.parse_args()
    pwd = a.apic_password or getpass.getpass('Passwort fuer %s@%s: ' % (a.apic_user, a.apic))
    sim = Client('Simulator', a.sim, a.sim_user, a.sim_password, True)
    apic = Client('APIC', a.apic, a.apic_user, pwd, a.insecure)
    sim.login()
    apic.login()
    probes = read_probes()
    if a.write:
        for c in (sim, apic):
            cleanup(c)
        probes += write_probes(a.fault_wait)
    rows, raw = [], []
    try:
        for area, name, kind, fn in probes:
            fn = fn or (p_noauth if kind == 'noauth' else p_atomic)
            kind = 'equal' if kind == 'noauth' else kind
            ra, rb = fn(sim), fn(apic)
            res, det = compare(kind, ra, rb)
            rows.append((area, name, res, det))
            raw.append({'bereich': area, 'pruefung': name, 'sim': ra, 'apic': rb, 'ergebnis': res})
            print('%-13s %-12s %-55s %s' % (res, area, name[:55], det[:160]))
    finally:
        if a.write:
            for c in (sim, apic):
                cleanup(c)
    n = {k: sum(1 for r in rows if r[2] == k) for k in ('gleich', 'unvollständig', 'abweichend')}
    print('\n%d Prüfungen: %d gleich, %d unvollständig (Attribute fehlen im Sim), %d abweichend' % (len(rows), n['gleich'], n['unvollständig'], n['abweichend']))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'abgleich-rohdaten.json'), 'w', encoding='utf-8') as f:
        json.dump({'sim': a.sim, 'apic': a.apic, 'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'write': a.write, 'ergebnisse': raw}, f, indent=1, ensure_ascii=False)
    with open(os.path.join(a.out, 'abgleich-bericht.md'), 'w', encoding='utf-8') as f:
        f.write('# Abgleich Datacenter Prep mit %s\n\n%s · %d Prüfungen: **%d gleich**, %d unvollständig, **%d abweichend**%s\n\n'
                % (a.apic, time.strftime('%d.%m.%Y %H:%M'), len(rows), n['gleich'], n['unvollständig'], n['abweichend'],
                   '' if a.write else ' (nur lesend, mit --write kommen Defaults, Fehlercodes, Relationen und Faults dazu)'))
        for res in ('abweichend', 'unvollständig', 'gleich'):
            sel = [r for r in rows if r[2] == res]
            if not sel:
                continue
            f.write('## %s (%d)\n\n| Bereich | Prüfung | Detail |\n|---|---|---|\n' % (res.capitalize(), len(sel)))
            for area, name, _, det in sel:
                f.write('| %s | %s | %s |\n' % (area, name, det.replace('|', '\\|') or '—'))
            f.write('\n')
    print('Bericht: %s' % os.path.join(a.out, 'abgleich-bericht.md'))
    return 1 if n['abweichend'] else 0


if __name__ == '__main__':
    sys.exit(main())
