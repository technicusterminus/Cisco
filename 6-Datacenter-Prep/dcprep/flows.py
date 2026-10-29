"""Testmatrix und Erwartungen: viele Verkehrsfluesse auf einmal pruefen, wie ein Regressionstest fuer das Design."""
import re
import time

from . import trace
from .model import AciError, now_ts

MAX_CELLS = 4000


def _members(S, x):
    """'EPG:Tenant/AP/EPG' -> Hosts, die in dieser EPG gelernt sind (inklusive uSeg-Basis); sonst der Name selbst."""
    x = (x or '').strip()
    m = re.match(r'^epg:([^/]+)/([^/]+)/(.+)$', x, re.I)
    if not m:
        return [x]
    dn = 'uni/tn-%s/ap-%s/epg-%s' % m.groups()
    e = S.engine
    out = [n for n, hs in e.hosts.items() if dn in (hs.get('epg'), hs.get('base'), hs.get('esg'))]
    return sorted(out)


def _cell(S, src, dst, proto, port):
    r = trace.run(S.engine, S.sim, src, dst, proto, port)
    bad = next((s for s in r['steps'] if s['ok'] is False), None)
    return {'ok': bool(r['ok']), 'why': ('%s: %s' % (bad['title'], bad['detail'])) if bad else (r.get('summary') if not r['ok'] else '')}


def matrix(S, srcs, dsts, proto='icmp', port=0):
    e = S.engine
    hosts = sorted(e.hosts)
    srcs = [m for x in (srcs or hosts) for m in _members(S, x)] or hosts
    dsts = [m for x in (dsts or hosts) for m in _members(S, x)] or hosts
    if len(srcs) * len(dsts) > MAX_CELLS:
        raise AciError(400, 'Matrix zu gross (%d x %d) - hoechstens %d Zellen, Quellen oder Ziele einschraenken' % (len(srcs), len(dsts), MAX_CELLS))
    t0 = time.time()
    rows = []
    for s in srcs:
        rows.append({'src': s, 'cells': [None if s == d else _cell(S, s, d, proto, port) for d in dsts]})
    return {'srcs': srcs, 'dsts': dsts, 'proto': proto, 'port': port, 'rows': rows, 'ms': int((time.time() - t0) * 1000)}


def _clean(x):
    proto = x.get('proto') or 'icmp'
    if proto not in ('icmp', 'tcp', 'udp'):
        raise AciError(400, 'Protokoll icmp, tcp oder udp')
    port = int(x.get('port') or 0)
    if proto != 'icmp' and not 1 <= port <= 65535:
        raise AciError(400, 'Fuer %s einen Port 1-65535 angeben' % proto)
    exp = x.get('expect')
    exp = exp if isinstance(exp, bool) else str(exp).lower() in ('allow', 'permit', 'true', 'yes', 'ja', '1', 'erlaubt')
    if not x.get('src') or not x.get('dst'):
        raise AciError(400, 'Quelle und Ziel angeben')
    return {'src': x['src'].strip(), 'dst': x['dst'].strip(), 'proto': proto, 'port': port if proto != 'icmp' else 0, 'expect': exp,
            'note': (x.get('note') or '').strip()}


def expect_op(S, b):
    lst = S.sim.setdefault('expect', [])
    op = b.get('op')
    if op == 'add':
        x = _clean(b.get('item') or {})
        x['id'] = max([i['id'] for i in lst] + [0]) + 1
        lst.append(x)
    elif op == 'update':
        x = _clean(b.get('item') or {})
        for i, y in enumerate(lst):
            if y['id'] == b.get('id'):
                x['id'] = y['id']
                lst[i] = x
    elif op == 'delete':
        S.sim['expect'] = [y for y in lst if y['id'] not in (b.get('ids') or [b.get('id')])]
    elif op == 'clear':
        S.sim['expect'] = []
    elif op == 'csv':
        new, errs = [], []
        for n, line in enumerate(str(b.get('csv') or '').splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#') or line.lower().startswith('src,'):
                continue
            c = [v.strip() for v in line.split(',')]
            try:
                new.append(_clean({'src': c[0], 'dst': c[1] if len(c) > 1 else '', 'proto': c[2] if len(c) > 2 else 'icmp',
                                   'port': c[3] if len(c) > 3 else 0, 'expect': c[4] if len(c) > 4 else 'allow',
                                   'note': ','.join(c[5:]) if len(c) > 5 else ''}))
            except (AciError, ValueError) as ex:
                errs.append('Zeile %d: %s' % (n, getattr(ex, 'text', ex)))
        if errs:
            raise AciError(400, 'Nichts uebernommen: ' + ' | '.join(errs[:8]))
        nid = max([i['id'] for i in lst] + [0])
        for x in new:
            nid += 1
            x['id'] = nid
        if b.get('replace'):
            S.sim['expect'] = new
        else:
            lst.extend(new)
    elif op == 'baseline':
        m = b.get('matrix') or {}
        nid = max([i['id'] for i in lst] + [0])
        have = {(y['src'], y['dst'], y['proto'], y['port']) for y in lst}
        for r in m.get('rows', []):
            for d, c in zip(m.get('dsts', []), r['cells']):
                if c is None or (r['src'], d, m.get('proto'), int(m.get('port') or 0)) in have:
                    continue
                nid += 1
                lst.append({'id': nid, 'src': r['src'], 'dst': d, 'proto': m.get('proto') or 'icmp', 'port': int(m.get('port') or 0),
                            'expect': bool(c['ok']), 'note': 'Baseline ' + now_ts()[:16]})
    elif op != 'run':
        raise AciError(400, 'Unbekannte Aktion')
    return run(S) if op in ('run', 'csv', 'baseline', 'add', 'update') else None


def run(S):
    """Alle Erwartungen pruefen; EPG-Angaben werden auf ihre Hosts aufgeloest, jedes Paar muss passen."""
    res, t0 = [], time.time()
    for x in S.sim.get('expect', []):
        srcs, dsts = _members(S, x['src']), _members(S, x['dst'])
        pairs = [(s, d) for s in srcs for d in dsts if s != d]
        if not pairs:
            res.append({'id': x['id'], 'pass': False, 'pairs': 0, 'why': 'Keine Hosts zu %s bzw. %s gefunden (EPG ohne gelernte Hosts?)' % (x['src'], x['dst'])})
            continue
        fails = []
        for s, d in pairs[:400]:
            c = _cell(S, s, d, x['proto'], x['port'])
            if c['ok'] != x['expect']:
                fails.append('%s -> %s: %s' % (s, d, c['why'] if not c['ok'] else 'erreichbar, sollte blockiert sein'))
        res.append({'id': x['id'], 'pass': not fails, 'pairs': len(pairs), 'why': '; '.join(fails[:3]) + (' (+%d)' % (len(fails) - 3) if len(fails) > 3 else '')})
    out = {'ts': now_ts(), 'results': res, 'passed': sum(1 for r in res if r['pass']), 'total': len(res), 'ms': int((time.time() - t0) * 1000)}
    S.sim['expect_last'] = out
    return out


def policy_matrix(S, vrf=None):
    """EPG x EPG je VRF: welche typischen Dienste die Policy fuer eine neue Verbindung erlaubt.
    Rechnet direkt mit Engine.packet (dieselbe Entscheidung wie Traffic-Test und Lab-Bewertung), ohne Endpoints.
    Antwortrichtung und Pfad (Endpoint, Routing) gehoeren nicht dazu."""
    from .engine import EPHEMERAL
    e = S.engine
    vrfs = sorted({c['vrf'] for c in e.cls.values() if c.get('vrf')})
    vrf = vrf if vrf in vrfs else (vrfs[0] if vrfs else None)
    probes = list(S.EXPOSURE_PROBES) + ['tcp/1', 'udp/65000']
    classes = sorted((c for c in e.cls.values() if c.get('vrf') == vrf and c['kind'] in ('epg', 'esg', 'ext')),
                     key=lambda c: (c['kind'] != 'epg', c['dn']))
    cells = {}
    for s in classes:
        row = cells.setdefault(s['dn'], {})
        for d in classes:
            open_, rules, codes = [], set(), set()
            for pr in probes:
                proto, _, port = pr.partition('/')
                port = int(port or 0)
                act, why = e.packet(s, d, proto, EPHEMERAL if port else None, port or None, 'syn')
                codes.add(e.last_code)
                if act == 'permit':
                    open_.append(pr)
                    if e.last_rule and e.last_rule.get('contract'):
                        rules.add(e.short(e.last_rule['contract']))
            row[d['dn']] = {'open': open_, 'all': len(open_) == len(probes), 'rules': sorted(rules),
                            'codes': sorted(c for c in codes if c)}
    return {'vrfs': vrfs, 'vrf': vrf, 'probes': probes,
            'classes': [{'dn': c['dn'], 'name': e.short(c['dn']), 'kind': c['kind']} for c in classes], 'cells': cells}
