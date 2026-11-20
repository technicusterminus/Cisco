"""Lab-Engine: Labs als JSON (aus Labs-Quelle/build_labs.py), Bewertung ueber das Verhalten der Welt.

Wie im Datacenter Prep: Eine Lab-Sitzung veraendert nie die Konfiguration. Die Pruefungen lesen denselben Zustand wie die
Oberflaeche und die CLI; es gibt keine zweite Logik. Verstaendnisfragen zaehlen nicht zum Bestehen.
"""
import json
import os

LABS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'labs')
MODES = ('guided', 'exam')
HIDDEN = ('cause', 'solution', 'solutionCommands', 'startCommands', 'worldClients', 'worldRadius', 'worldMobility', 'worldUnderlay', 'checks', 'hints', 'questions')


class LabError(Exception):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.status = status


def load_all(directory=LABS_DIR):
    out = {}
    if os.path.isdir(directory):
        for f in sorted(os.listdir(directory)):
            if f.endswith('.json'):
                with open(os.path.join(directory, f), encoding='utf-8') as fh:
                    lab = json.load(fh)
                out[lab['id']] = lab
    return out


def run_check(chk, st):
    """Eine Pruefung gegen den Zustand (Wlc.state()). Rueckgabe (ok, Detail)."""
    t = chk['type']
    if t == 'client':
        c = next((x for x in st['clients'] if x['mac'] == chk['mac']), None)
        if c is None:
            return False, 'Client %s unbekannt' % chk['mac']
        ok = (c['state'] == chk['state'] and (chk.get('vlan') is None or str(c['vlan']) == str(chk['vlan']))
              and (chk.get('switching') is None or c.get('switching') == chk['switching'])
              and (chk.get('roam') is None or c.get('roam') == chk['roam'])
              and all(chk.get(k) is None or c.get(k) == chk[k] for k in ('dscpDown', 'dscpUp', 'mcast')))
        return ok, 'Zustand %s%s%s%s' % (c['state'], ', VLAN %s' % c['vlan'] if c['vlan'] else '',
                                         ', %s geschaltet' % c['switching'] if c['state'] == 'Run' and c.get('switching') else '',
                                         ', DSCP runter %s, rauf %s' % (c['dscpDown'], c['dscpUp']) if c.get('dscpDown') is not None else '')
    if t == 'wlan':
        w = next((x for x in st['wlans'] if x['profile'] == chk['profile']), None)
        if w is None:
            return False, 'WLAN-Profil %s fehlt' % chk['profile']
        bad = {k: w.get(k) for k, v in chk['attrs'].items() if w.get(k) != v}
        return not bad, 'passt' if not bad else 'abweichend: ' + ', '.join('%s=%s' % kv for kv in sorted(bad.items()))
    if t == 'policy':
        p = next((x for x in st['policies'] if x['name'] == chk['name']), None)
        if p is None:
            return False, 'Policy Profile %s fehlt' % chk['name']
        bad = {k: p.get(k) for k, v in chk['attrs'].items() if p.get(k) != v}
        return not bad, 'passt' if not bad else 'abweichend: ' + ', '.join('%s=%s' % kv for kv in sorted(bad.items()))
    if t == 'aptag':
        a = next((x for x in st['aps'] if x['name'] == chk['ap']), None)
        return (a is not None and a['policyTag'] == chk['tag']), 'Policy Tag %s' % (a['policyTag'] if a else '?')
    if t == 'apmode':
        a = next((x for x in st['aps'] if x['name'] == chk['ap']), None)
        return (a is not None and a['mode'] == chk['mode']), 'Modus %s' % (a['mode'] if a else '?')
    if t == 'mcastcfg':
        m = st['multicast']
        ok = m['enabled'] and m['group'].startswith(chk['prefix']) and not m['groupInUse']
        return ok, 'Multicast %s, Gruppe %s%s' % ('an' if m['enabled'] else 'aus', m['group'] or '-', ' (im Netz schon verwendet)' if m['groupInUse'] else '')
    if t == 'aprf':
        a = next((x for x in st['aps'] if x['name'] == chk['ap']), None)
        r = a['rf'][chk['band']] if a else None
        ok = r is not None and all(r.get(k) == v for k, v in chk['attrs'].items())
        return ok, 'nicht gefunden' if r is None else 'Profil %s, max. Sendeleistung %s, Funk %s' % (r['profile'] or '-', r['txMax'] if r['txMax'] is not None else 'automatisch', r['radio'])
    if t == 'mobilitypeer':
        pr = next((x for x in st['mobilityPeers'] if x['ip'] == chk['ip']), None)
        return (pr is not None and pr['control'] == 'Up' and pr['data'] == 'Up'), 'Peer %s: %s' % (
            chk['ip'], 'nicht konfiguriert' if pr is None else 'Control %s, Data %s' % (pr['control'], pr['data']))
    if t == 'wlanservers':
        got = st['_wlan_servers'].get(chk['profile']) or []
        return all(ip in got for ip in chk['servers']), 'Server in der Kette: %s' % (', '.join(got) if got else 'keine')
    if t == 'tagmap':
        tg = next((x for x in st['policyTags'] if x['name'] == chk['tag']), None)
        got = {m['wlan']: m['policy'] for m in tg['maps']} if tg else None
        return got == chk['maps'], 'Zuordnung %s' % (got if got is not None else 'Tag fehlt')
    if t == 'absent':
        key = {'wlan': ('wlans', 'profile'), 'policy': ('policies', 'name'), 'tag': ('policyTags', 'name')}[chk['kind']]
        there = any(x[key[1]] == chk['name'] for x in st[key[0]])
        return not there, 'vorhanden' if there else 'entfernt'
    raise ValueError('Pruefungstyp unbekannt: %s' % t)


class LabEngine:
    def __init__(self, sim, directory=LABS_DIR):
        self.sim = sim
        self.labs = load_all(directory)
        self.session = None   # {id, mode, hints, answers, checks}
        self.progress = {}    # lab-id -> Zaehler und Bestanden-Merker (ohne Zeitstempel, deterministisch)

    # ------------------------------------------------------------------ Liste, Start
    def _prog(self, lab_id):
        return self.progress.setdefault(lab_id, {'starts': 0, 'checks': 0, 'passed': False, 'guidedPassed': False,
                                                 'examPassed': False, 'bestHints': None, 'questionsRight': 0})

    def list(self):
        out = []
        for lab in self.labs.values():
            d = {k: lab[k] for k in ('id', 'title', 'topic', 'level', 'duration', 'kind', 'modes')}
            d['track'] = lab.get('track')
            d['progress'] = dict(self.progress.get(lab['id']) or {'starts': 0, 'checks': 0, 'passed': False, 'guidedPassed': False,
                                                                'examPassed': False, 'bestHints': None, 'questionsRight': 0})
            out.append(d)
        return out

    def reset_progress(self):
        self.progress = {}

    def start(self, lab_id, mode='guided'):
        lab = self.labs.get(lab_id)
        if lab is None:
            raise LabError('Lab %s gibt es nicht' % lab_id, 404)
        if mode not in lab['modes']:
            raise LabError('Modus %s ist fuer dieses Lab nicht vorgesehen' % mode)
        self.sim.reset_world(lab.get('worldClients'), lab.get('worldRadius'), lab.get('worldMobility'), lab.get('worldUnderlay'))
        ok, _, err = self.sim.apply(lab.get('startCommands', []))
        if not ok:
            raise LabError('Startkonfiguration von %s fehlerhaft: %s' % (lab_id, err['message']), 500)
        self.session = {'id': lab_id, 'mode': mode, 'hints': 0, 'answers': {}, 'checks': 0}
        self._prog(lab_id)['starts'] += 1
        return self.public()

    def reset(self):
        s = self._need()
        return self.start(s['id'], s['mode'])

    def stop(self):
        self.session = None

    def restore_session(self, d):
        """Lab-Sitzung aus einem gespeicherten Stand uebernehmen; unbekannte oder ungueltige Sitzungen werden verworfen."""
        self.session = None
        if not isinstance(d, dict) or d.get('id') not in self.labs or d.get('mode') not in MODES:
            return
        lab = self.labs[d['id']]
        hints = d.get('hints') if isinstance(d.get('hints'), int) else 0
        answers = d.get('answers') if isinstance(d.get('answers'), dict) else {}
        qids = {q['id']: len(q['options']) for q in lab.get('questions', [])}
        self.session = {'id': d['id'], 'mode': d['mode'], 'hints': max(0, min(hints, len(lab['hints']))),
                        'answers': {k: v for k, v in answers.items() if k in qids and isinstance(v, int) and 0 <= v < qids[k]},
                        'checks': d.get('checks') if isinstance(d.get('checks'), int) else 0}

    def _need(self):
        if self.session is None:
            raise LabError('Es laeuft kein Lab', 409)
        return self.session

    # ------------------------------------------------------------------ Ansicht, Hinweise, Fragen
    def public(self):
        if self.session is None:
            return None
        s, lab = self.session, self.labs[self.session['id']]
        out = {k: v for k, v in lab.items() if k not in HIDDEN}
        exam = s['mode'] == 'exam'
        out.update(mode=s['mode'], hintsTotal=0 if exam else len(lab['hints']), hintsUsed=s['hints'],
                   hints=[] if exam else lab['hints'][:s['hints']], checksRun=s['checks'],
                   questions=[{k: v for k, v in q.items() if k not in ('answer', 'explain')} for q in lab.get('questions', [])],
                   answers={q: a for q, a in s['answers'].items()})
        return out

    def hint(self):
        s = self._need()
        lab = self.labs[s['id']]
        if s['mode'] == 'exam':
            raise LabError('Im Prüfungsmodus gibt es keine Hinweise', 403)
        if s['hints'] >= len(lab['hints']):
            raise LabError('Alle Hinweise sind bereits freigeschaltet', 409)
        s['hints'] += 1
        return self.public()

    def solution(self):
        s = self._need()
        if s['mode'] == 'exam':
            raise LabError('Im Prüfungsmodus gibt es keine Lösung', 403)
        return {'solution': self.labs[s['id']]['solution']}

    def answer(self, qid, idx):
        s = self._need()
        q = next((x for x in self.labs[s['id']].get('questions', []) if x['id'] == qid), None)
        if q is None or not isinstance(idx, int) or not 0 <= idx < len(q['options']):
            raise LabError('Frage oder Antwort ungueltig')
        s['answers'][qid] = idx
        ok = idx == q['answer']
        return {'correct': ok, 'explain': None if s['mode'] == 'exam' else q['explain']}

    # ------------------------------------------------------------------ Bewertung
    def check(self):
        s = self._need()
        lab = self.labs[s['id']]
        s['checks'] += 1
        st = self.sim.wlc.state()
        st['_wlan_servers'] = {n: self.sim.wlc.wlan_servers(w) for n, w in self.sim.wlc.wlans.items()}
        exam = s['mode'] == 'exam'
        res = []
        for c in lab['checks']:
            ok, detail = run_check(c, st)
            r = {'desc': c['desc'], 'ok': ok, 'category': c.get('category', 'function')}
            if not exam:
                r['detail'] = detail
            res.append(r)
        cats = {}
        for r in res:
            cats.setdefault(r['category'], [0, 0])
            cats[r['category']][1] += 1
            cats[r['category']][0] += r['ok']
        qs = lab.get('questions', [])
        right = sum(1 for q in qs if s['answers'].get(q['id']) == q['answer'])
        passed = all(r['ok'] for r in res)
        p = self._prog(s['id'])
        p['checks'] += 1
        p['questionsRight'] = max(p['questionsRight'], right)
        if passed:
            p['passed'] = True
            p['examPassed' if exam else 'guidedPassed'] = True
            if not exam:
                p['bestHints'] = s['hints'] if p['bestHints'] is None else min(p['bestHints'], s['hints'])
        return {'passed': passed, 'checks': res, 'categories': {k: {'ok': v[0], 'total': v[1]} for k, v in cats.items()},
                'questions': {'right': right, 'total': len(qs)}, 'hintsUsed': s['hints'], 'mode': s['mode']}
