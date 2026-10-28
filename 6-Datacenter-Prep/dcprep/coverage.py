"""Abdeckungsbericht: welche Klassen und Attribute einer Konfiguration die Simulation auswertet."""
import os
import re

from .model import CLASSES, COMMON_RW

_SRC = None


def _sources():
    global _SRC
    if _SRC is None:
        base = os.path.dirname(os.path.abspath(__file__))
        _SRC = '\n'.join(open(os.path.join(base, f), encoding='utf-8').read()
                         for f in ('engine.py', 'ops.py', 'multipod.py', 'msite.py', 'trace.py', 'aaa.py'))
    return _SRC


_LEVEL = None


def _direct(cls):
    m = CLASSES[cls]
    src = _sources()
    if "'%s'" % cls in src:
        return True
    prefix = re.split(r'[{\[-]', m.rn)[0]
    return bool(prefix) and bool(re.search(r"['/]%s[-'\[/]" % re.escape(prefix), src))


def _levels():
    """Direkt im Code genutzte Klassen, dazu Ziele ihrer Relationen und ihre Elternklassen (Fixpunkt)."""
    global _LEVEL
    if _LEVEL is None:
        ev = {c for c, m in CLASSES.items() if not getattr(m, 'passive', False) and _direct(c)}
        changed = True
        while changed:
            changed = False
            for c in list(ev):
                m = CLASSES[c]
                add = set(m.parents)
                if m.rel:
                    add |= set([m.rel[2]] if isinstance(m.rel[2], str) else m.rel[2])
                for a in add:
                    if a in CLASSES and a not in ev and not getattr(CLASSES[a], 'passive', False):
                        ev.add(a)
                        changed = True
        _LEVEL = {c: ('gespeichert' if getattr(m, 'passive', False) else 'ausgewertet' if c in ev else 'modelliert') for c, m in CLASSES.items()}
    return _LEVEL


def level(cls):
    """'ausgewertet' (Verhalten simuliert), 'modelliert' (Attribute bekannt und geprueft) oder 'gespeichert' (nur abgelegt)."""
    return _levels()[cls]


def report(store, under=''):
    rows = {}
    for dn, (cls, attrs, oper) in store.objs.items():
        if oper or (under and dn != under and not dn.startswith(under + '/')):
            continue
        m = CLASSES[cls]
        r = rows.setdefault(cls, {'cls': cls, 'label': m.label, 'count': 0, 'level': level(cls), 'unknown': set(), 'example': dn})
        r['count'] += 1
        known = set(m.attrs) | COMMON_RW | set(m.ro) | {'modTs', 'status', 'childAction', 'lcOwn', 'uid', 'dn', 'rn', 'configIssues', 'configSt'}
        r['unknown'] |= {k for k in attrs if k not in known}
    out = sorted(rows.values(), key=lambda r: (['gespeichert', 'modelliert', 'ausgewertet'].index(r['level']), -r['count']))
    for r in out:
        r['unknown'] = sorted(r['unknown'])
    tot = sum(r['count'] for r in out)
    by = {lv: sum(r['count'] for r in out if r['level'] == lv) for lv in ('ausgewertet', 'modelliert', 'gespeichert')}
    return {'under': under or 'uni', 'objects': tot, 'byLevel': by, 'classes': out}
