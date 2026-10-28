"""Lab-Bewertung: Kategorien, Least-Privilege-Pruefung, gestufte Hinweise und Lab-Modi.

Die Bewertung liest nur den gemeinsamen Zustand (Store + Engine) und nutzt fuer Verkehr dieselbe
Connectivity-Engine wie der Traffic Inspector (trace.run). Sie veraendert nie die Konfiguration.
"""
from .engine import port_val

CATEGORIES = ('functional', 'security', 'understanding', 'diagnosis')
CATEGORY_LABEL = {'functional': 'Funktion', 'security': 'Sicherheit', 'understanding': 'Verständnis', 'diagnosis': 'Diagnose'}
MODES = ('guided', 'exam')


def category(check):
    """Explizite Kategorie oder Ableitung: Negativtests und Least Privilege zaehlen zur Sicherheit."""
    c = check.get('category')
    if c in CATEGORIES:
        return c
    if check['type'] == 'policy_scope':
        return 'security'
    if check['type'] == 'traffic' and check.get('expect', True) is False:
        return 'security'
    return 'functional'


def _parse_allow(specs):
    """['tcp/443', 'tcp/8000-8010', 'icmp'] -> {'tcp': [(443, 443), ...], 'icmp': True}"""
    out = {}
    for sp in specs or []:
        sp = sp.strip().lower()
        if sp in ('icmp', 'arp'):
            out[sp] = True
            continue
        proto, _, ports = sp.partition('/')
        lo, _, hi = ports.partition('-')
        lo_v = port_val(lo)
        hi_v = port_val(hi) if hi else lo_v
        if proto not in ('tcp', 'udp') or lo_v is None or hi_v is None:
            raise ValueError('ungueltige Freigabe %r (erwartet z. B. tcp/443, udp/53, icmp)' % sp)
        out.setdefault(proto, []).append((lo_v, hi_v))
    return out


def _entry_ok(a, allow):
    """Ist ein Filter-Eintrag hoechstens so breit wie die erlaubten Dienste? -> (ok, Begruendung)"""
    eth = a.get('etherT', 'unspecified')
    if eth == 'unspecified':
        return False, 'EtherType unspecified (passt auf jeden Verkehr)'
    if eth == 'arp':
        return ('arp' in allow), 'ARP'
    if eth not in ('ip', 'ipv4'):
        return False, 'EtherType %s' % eth
    prot = a.get('prot', 'unspecified')
    if prot == 'unspecified':
        return False, 'IP-Protokoll unspecified (alle Protokolle)'
    if prot == 'icmp':
        return ('icmp' in allow), 'ICMP'
    if prot not in ('tcp', 'udp'):
        return False, 'IP-Protokoll %s' % prot
    lo, hi = port_val(a.get('dFromPort', 'unspecified')), port_val(a.get('dToPort', 'unspecified'))
    if lo is None and hi is None:
        return False, '%s ohne Ziel-Port (alle Ports)' % prot
    lo = lo if lo is not None else hi
    hi = hi if hi is not None else lo
    ranges = allow.get(prot, [])
    if any(r_lo <= lo and hi <= r_hi for r_lo, r_hi in ranges):
        return True, '%s/%s' % (prot, lo if lo == hi else '%d-%d' % (lo, hi))
    return False, '%s/%s' % (prot, lo if lo == hi else '%d-%d' % (lo, hi))


def policy_scope(eng, check):
    """Least Privilege zwischen den EPGs zweier Hosts: alles, was Verkehr erlaubt, darf nicht breiter sein als 'allow'."""
    allow = _parse_allow(check.get('allow'))
    ends = []
    for key in ('src', 'dst'):
        hs = eng.hosts.get(check[key]) or {}
        if not hs.get('learned'):
            return False, '%s ist nicht gelernt - keine EPG-Zuordnung' % check[key]
        ends.append(eng.cls[hs.get('esg') or hs['epg']])
    items = eng.permit_scope(ends[0], ends[1])
    too_wide, fine = [], []
    for it in items:
        if it['kind'] == 'blanket':
            too_wide.append('pauschal: %s' % it['text'])
            continue
        ok, why = _entry_ok(it['attrs'], allow)
        (fine if ok else too_wide).append('%s (%s)' % (it['text'], why))
    if too_wide:
        return False, 'Zu breit: ' + '; '.join(too_wide)
    if not fine:
        return True, 'Keine Freigabe zwischen den EPGs'
    return True, 'Nur erlaubt: ' + '; '.join(fine)


def summarize(results):
    """Ergebnis je Kategorie: {'functional': {'passed': n, 'total': m, 'label': ...}, ...}"""
    out = {}
    for r in results:
        c = out.setdefault(r['category'], {'passed': 0, 'total': 0, 'label': CATEGORY_LABEL[r['category']]})
        c['total'] += 1
        c['passed'] += 1 if r['ok'] else 0
    return out


def hints_of(lab):
    """Gestufte Hinweise eines Labs, sortiert nach Stufe (1 Konzept ... 4 Loesung)."""
    return sorted(lab.get('hints') or [], key=lambda x: x['level'])


def lab_view(lab, mode, shown):
    """Was die Oberflaeche vom Lab sehen darf. Im Pruefungsmodus keine Tipps, Hinweise und Loesung."""
    if not lab:
        return None
    exam = mode == 'exam'
    hints = hints_of(lab)
    return {'id': lab['id'], 'title': lab['title'], 'intro': lab.get('intro'), 'goals': lab.get('goals'),
            'tasks': [{k: v for k, v in t.items() if not (exam and k == 'hint')} for t in lab.get('tasks', [])],
            'solution': None if exam else lab.get('solution'), 'mode': mode,
            'limits': lab.get('limits'), 'hintsTotal': len(hints),
            'hints': [] if exam else [h for h in hints if h['level'] <= shown]}
