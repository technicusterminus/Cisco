"""HTTP-Server: APIC-REST-API, Simulator-API, Weboberflaeche."""
import hashlib
import json
import mimetypes
import os
import re
import secrets
import ssl
import subprocess
import threading
import time
import ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

from .model import AciError, CLASSES, rn_of, Store, post as mit_post, delete as mit_delete, now_ts
from .query import run_query
from .engine import Engine, ip_of
from . import setup as apic_setup
from . import aaa
from .topology import default_topology, multipod_topology, default_ipn, discovered_members, base_config, ensure_base, build_topology, build_ipn, infra_config, LIMITS
from .cli import Cli
from . import trace
from . import ops
from . import msite
from . import flows
from . import coverage
from .users import Hub, SimProxy, COOKIE as DP_COOKIE, SESSION_DAYS

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(BASE, 'static')
LABS = os.path.join(BASE, 'labs')
MAC_RE = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$')
NAME_RE = re.compile(r'^[A-Za-z0-9_.-]{1,32}$')


class Sim:
    """Gesamtzustand: MIT, Simulationsdaten, Engine, Persistenz."""

    def __init__(self, data_dir, admin_pwd='admin', discovery=20):
        self.lock = threading.RLock()
        self.data_dir = data_dir
        os.makedirs(os.path.join(data_dir, 'snapshots'), exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'saves'), exist_ok=True)
        self.state_file = os.path.join(data_dir, 'state.json')
        self.admin_pwd = admin_pwd
        self.store = Store()
        self.sim = {}
        self.tokens = {}
        self.default_discovery = discovery
        if not self._load():
            self.reset('discovered')
        self.rebuild()

    # -------------------------------------------------------------- Persistenz
    def _new_sim(self):
        return {'topology': default_topology(), 'registered': {}, 'hosts': [], 'routers': [],
                'settings': {'discoverySeconds': self.default_discovery, 'upgradeSeconds': 60}, 'lab': None,
                'fileserver': ops.default_fileserver(), 'monitors': ops.default_monitors(), 'switches': [],
                'setup': {k: v for k, v in apic_setup.DEFAULTS.items() if k != 'pwd'}}

    def _load(self):
        if not os.path.exists(self.state_file):
            return False
        try:
            with open(self.state_file, encoding='utf-8') as f:
                d = json.load(f)
            self.store.load_config(d['config'], d.get('counters'))
            ensure_base(self.store)
            self.sim = d['sim']
            self.engine = Engine(self.store, self.sim)
            return True
        except (OSError, ValueError, KeyError) as ex:
            print('Zustand konnte nicht geladen werden (%s) - starte neu.' % ex)
            return False

    def save(self):
        tmp = self.state_file + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'version': 1, 'config': self.store.dump_config(), 'counters': self.store.counters,
                       'sim': self.sim}, f)
        os.replace(tmp, self.state_file)

    def reset(self, mode='discovered', keep_sim=False):
        base_config(self.store, self.admin_pwd)
        old = self.sim or {}
        self.sim = self._new_sim()
        for k in ('settings', 'audit', 'events', 'seq', 'fileserver', 'monitors', 'monlog'):
            if k in old:
                self.sim[k] = old[k]
        if keep_sim:
            for k in ('hosts', 'routers', 'vcenters', 'devices', 'aaa', 'switches'):
                if k in old:
                    self.sim[k] = old[k]
        if mode == 'factory':
            self.sim['setup'] = None
            self.sim['audit'], self.sim['events'] = [], []
            self.tokens.clear()
        self.sim['pristine'] = True
        self.engine = Engine(self.store, self.sim)
        if mode != 'factory':
            su = self.sim['setup']
            mit_post(self.store, 'uni/controller/setuppol', {'fabricSetupPol': {'attributes': {}, 'children': [
                {'fabricSetupP': {'attributes': {'podId': str(int(su['podId'])), 'tepPool': su['tepPool']}}}]}})
            mit_post(self.store, 'uni/tn-mgmt/mgmtp-default/oob-default', {'mgmtOoB': {'attributes': {}, 'children': [
                {'mgmtRsOoBStNode': {'attributes': {'tDn': 'topology/pod-%d/node-1' % int(su['podId']), 'addr': su['oobIp'],
                                                    'gw': su['oobGw']}}}]}})
        if mode == 'discovered':
            for m in discovered_members():
                mit_post(self.store, 'uni/controller/nodeidentpol', m)
            for n in self.sim['topology']['nodes']:
                self.sim['registered'][n['serial']] = 0.0
        self.rebuild()

    def changed(self):
        self.rebuild()
        self.save()

    def tick(self):
        ne = self.engine.next_event
        if ne is not None and time.time() >= ne:
            self.rebuild()
            self.save()

    # -------------------------------------------------------------- Historie
    def _next_id(self):
        self.sim['seq'] = self.sim.get('seq', 4294967296) + 1
        return self.sim['seq']

    def _snap(self):
        e = self.engine
        if not hasattr(e, 'nodes'):
            return None
        st = self.store
        return {'nodes': {nid: (n['name'], n['state']) for nid, n in e.nodes.items()},
                'hosts': {k: (v['learned'], v.get('epg'), v.get('path')) for k, v in e.hosts.items()},
                'routers': {k: (v.get('adj'), (v.get('iface') or {}).get('dn')) for k, v in e.routers.items()},
                'faults': {d: (st.attrs(d)['code'], st.attrs(d)['severity'], st.attrs(d)['descr'])
                           for d in st.by_class('faultInst')}}

    def _event(self, affected, descr, sev='info', cause='transition', code='E4205125', rec=None):
        self.outbox.append(rec or {'kind': 'event', 'severity': sev, 'code': code, 'dn': affected, 'descr': descr, 'cause': cause})
        ev = self.sim.setdefault('events', [])
        ev.append({'id': self._next_id(), 'affected': affected, 'descr': descr, 'severity': sev, 'cause': cause,
                   'code': code, 'created': now_ts(), 'ind': 'state-transition', 'trig': 'oper', 'user': 'internal',
                   'changeSet': ''})
        del ev[:-2000]

    def rebuild(self):
        if not hasattr(self, 'outbox'):
            self.outbox = []
        before = self._snap()
        self.engine.rebuild()
        after = self._snap()
        if not before:
            return
        n0 = len(self.sim.get('events', []))
        for nid, (name, state) in after['nodes'].items():
            if before['nodes'].get(nid, (None, None))[1] != state:
                self._event('%s/node-%d' % (self.engine.pdn(nid), nid), 'Node %s (%d) changed state to %s' % (name, nid, state),
                            code='E4204979')
        for name, (learned, epg, path) in after['hosts'].items():
            ob = before['hosts'].get(name, (False, None, None))
            if learned and (not ob[0] or ob[1] != epg):
                h = next((x for x in self.engine.all_hosts() if x['name'] == name), {})
                self._event(epg, 'Endpoint %s (%s) learned on %s' % (h.get('mac', ''), name, path), code='E4209232')
            if ob[0] and not learned:
                self._event(ob[1], 'Endpoint of host %s aged out / no longer learned' % name, code='E4209233')
        for name, (adj, idn) in after['routers'].items():
            if before['routers'].get(name, (None,))[0] != adj and idn:
                self._event(idn, 'Routing adjacency to %s changed to %s' % (name, adj),
                            sev='info' if adj in ('FULL', 'Established') else 'warning', code='E4212468')
        for d, (code, sev, descr) in after['faults'].items():
            if d not in before['faults']:
                aff = d.rsplit('/fault-', 1)[0]
                self._event(aff, 'Fault %s raised: %s' % (code, descr), sev=sev, cause='fault-raised', code='E4204886',
                            rec={'kind': 'fault', 'severity': sev, 'orig': sev, 'code': code, 'dn': aff, 'descr': descr,
                                 'lc': 'raised', 'cause': self.store.attrs(d).get('cause', '')})
        for d, (code, sev, descr) in before['faults'].items():
            if d not in after['faults']:
                aff = d.rsplit('/fault-', 1)[0]
                self._event(aff, 'Fault %s cleared: %s' % (code, descr), cause='fault-cleared', code='E4204887',
                            rec={'kind': 'fault', 'severity': 'cleared', 'orig': sev, 'code': code, 'dn': aff, 'descr': descr,
                                 'lc': 'cleared', 'cause': 'cleared'})
        if len(self.sim.get('events', [])) != n0:
            self.engine._history()
        box, self.outbox = self.outbox, []
        ops.deliver(self, box)

    def audit(self, user, changes):
        if changes:
            self.sim.pop('pristine', None)
        log = self.sim.setdefault('audit', [])
        if not hasattr(self, 'outbox'):
            self.outbox = []
        tx = self._next_id()
        for c in changes:
            name = rn_of(c['dn'])
            verb = {'creation': 'created', 'modification': 'modified', 'deletion': 'deleted'}[c['ind']]
            cs = ', '.join('%s (Old: %s, New: %s)' % (k, o, n) if c['ind'] == 'modification' else '%s:%s' % (k, n)
                           for k, (o, n) in sorted(c['changes'].items()) if k != 'pwd')
            log.append({'id': self._next_id(), 'affected': c['dn'], 'ind': c['ind'], 'user': user, 'created': now_ts(),
                        'descr': '%s %s %s' % (CLASSES[c['cls']].label, name, verb), 'changeSet': cs,
                        'code': {'creation': 'E4206326', 'modification': 'E4206327', 'deletion': 'E4206328'}[c['ind']],
                        'cause': 'transition', 'severity': 'info', 'trig': 'config', 'txId': str(tx)})
            self.outbox.append({'kind': 'audit', 'severity': 'info', 'code': log[-1]['code'], 'dn': c['dn'],
                                'descr': '%s by %s: %s' % (log[-1]['descr'], user, cs), 'lc': c['ind'], 'cause': 'transition'})
        del log[:-3000]

    # -------------------------------------------------------------- Auth
    def setup_apply(self, answers):
        if self.sim.get('setup') is not None:
            raise AciError(400, 'Der APIC ist bereits eingerichtet. Zuruecksetzen mit "acidiag touch clean" und "acidiag reboot".')
        key, err = apic_setup.validate_all(answers)
        if err:
            raise AciError(400, '%s: %s' % (key, err))
        a = apic_setup.normalize(answers)
        ts = now_ts()
        mit_post(self.store, 'uni/userext/user-admin', {'aaaUser': {'attributes': {'pwd': a['pwd']}}})
        self.sim['setup'] = {k: v for k, v in a.items() if k != 'pwd'}
        self.sim['topology']['pod'] = int(a['podId'])
        self.sim['topology']['apic']['name'] = a['ctrlName']
        pod = int(a['podId'])
        mit_post(self.store, 'uni/tn-mgmt/mgmtp-default/oob-default', {'mgmtOoB': {'attributes': {}, 'children': [
            {'mgmtRsOoBStNode': {'attributes': {'tDn': 'topology/pod-%d/node-1' % pod, 'addr': a['oobIp'],
                                                'gw': a['oobGw']}}}]}})
        self.changed()
        return ts

    def login(self, name, pwd):
        if self.sim.get('setup', 0) is None:
            raise AciError(503, 'Der APIC ist noch nicht eingerichtet - zuerst den Setup-Dialog an der Konsole abschliessen.', 503)
        user, roles, how = aaa.authenticate(self, name, pwd)
        tok = secrets.token_urlsafe(48)
        self.tokens[tok] = (user, time.time() + 3600, now_ts(), roles, how)
        self.sim.setdefault('logins', []).append({'ts': now_ts(), 'user': user, 'how': how, 'roles': aaa.describe(roles)})
        del self.sim['logins'][:-200]
        return tok

    def roles_of(self, user, tok):
        if tok and tok in self.tokens and len(self.tokens[tok]) > 3:
            return self.tokens[tok][3]
        return aaa.local_roles(self.store, user)

    def check(self, cookies, headers):
        tok = cookies.get('APIC-cookie') or headers.get('APIC-challenge')
        if tok and tok in self.tokens:
            user, exp = self.tokens[tok][:2]
            if exp > time.time():
                return user, tok
            del self.tokens[tok]
        dn = cookies.get('APIC-Certificate-DN')
        if dn and cookies.get('APIC-Request-Signature'):
            m = re.match(r'^uni/userext/user-([^/]+)/', dn)
            if m and self.store.attrs('uni/userext/user-%s' % m.group(1)):
                return m.group(1), None
        return None, None

    # -------------------------------------------------------------- Labs
    def labs(self):
        out = []
        if os.path.isdir(LABS):
            for fn in sorted(os.listdir(LABS)):
                if fn.endswith('.json'):
                    try:
                        with open(os.path.join(LABS, fn), encoding='utf-8') as f:
                            d = json.load(f)
                        out.append(d)
                    except (OSError, ValueError) as ex:
                        print('Lab %s fehlerhaft: %s' % (fn, ex))
        return out

    def lab(self, lid):
        return next((l for l in self.labs() if l['id'] == lid), None)

    def load_lab(self, lid, autosave=True, mode=None):
        lab = self.lab(lid)
        if not lab:
            raise AciError(404, 'Lab %s nicht gefunden' % lid)
        modes = lab.get('modes') or ['guided']
        mode = mode or modes[0]
        if mode not in modes:
            raise AciError(400, 'Modus %s gibt es fuer dieses Lab nicht (moeglich: %s)' % (mode, ', '.join(modes)))
        if autosave:
            self.autosave_lab()
        self.reset(lab.get('fabric', 'discovered'))
        if lab.get('topology') == 'multipod':
            self.sim['topology'] = multipod_topology()
            self.sim['ipn'] = json.loads(json.dumps(lab.get('ipn') or default_ipn()))
        if lab.get('topology') == 'multisite':
            self.sim['topology'] = msite.multisite_topology()
            self.sim['ipn'] = json.loads(json.dumps(lab.get('ipn') or msite.default_isn()))
            self.sim['ndo'] = msite.default_ndo()
        for tree in lab.get('config', []):
            mit_post(self.store, 'uni', tree)
        self.sim['hosts'] = json.loads(json.dumps(lab.get('hosts', [])))
        self.sim['routers'] = json.loads(json.dumps(lab.get('routers', [])))
        self.sim['vcenters'] = json.loads(json.dumps(lab.get('vcenters', [])))
        self.sim['devices'] = json.loads(json.dumps(lab.get('devices', [])))
        self.sim['aaa'] = json.loads(json.dumps(lab.get('aaa', [])))
        self.sim['switches'] = json.loads(json.dumps(lab.get('switches', [])))
        self.sim['monitors'] = json.loads(json.dumps(lab.get('monitors') or ops.default_monitors()))
        self.sim['fileserver'] = ops.default_fileserver()
        self.sim['fileserver'].update(json.loads(json.dumps(lab.get('fileserver', {}))))
        self.sim['monlog'] = {}
        for k, v in lab.get('sim', {}).items():
            self.sim[k] = json.loads(json.dumps(v))
        self.sim['settings'].update(lab.get('settings', {}))
        self.sim['lab'] = lid
        # Lab-Sitzung: Modus und erfasste Aktionen (Hinweise, Antworten) - aendern die Konfiguration nicht
        self.sim['labSession'] = {'mode': mode, 'hints': 0, 'answers': {}, 'checks': 0}
        self.changed()
        return lab

    def lab_session(self):
        return self.sim.get('labSession') or {'mode': 'guided', 'hints': 0, 'answers': {}, 'checks': 0}

    def lab_public(self, lab):
        """Lab fuer die Oberflaeche: im Pruefungsmodus ohne Hinweise und Loesung, Fragen ohne Antwort."""
        if not lab:
            return None
        ses = self.lab_session()
        exam = ses['mode'] == 'exam'
        out = {k: lab.get(k) for k in ('id', 'title', 'intro', 'goals', 'level', 'topic', 'prerequisites', 'tools', 'limits', 'requirements')}
        out['mode'] = ses['mode']
        out['modes'] = lab.get('modes') or ['guided']
        out['tasks'] = [{k: v for k, v in t.items() if not (exam and k == 'hint')} for t in lab.get('tasks', [])]
        hints = lab.get('hints') or []
        out['hintCount'] = 0 if exam else len(hints)
        out['hints'] = [] if exam else hints[:ses['hints']]
        out['solution'] = None if exam else lab.get('solution')
        out['questions'] = [{k: q[k] for k in ('id', 'q', 'options')} for q in lab.get('questions', [])]
        out['answers'] = {k: {'choice': v, 'ok': v == next((q['answer'] for q in lab.get('questions', []) if q['id'] == k), None),
                              'explain': None if exam else next((q.get('explain') for q in lab.get('questions', []) if q['id'] == k), None)}
                          for k, v in ses['answers'].items()}
        return out

    def lab_hint(self, level):
        lab = self.lab(self.sim.get('lab'))
        if not lab:
            raise AciError(400, 'Kein Lab aktiv')
        ses = self.lab_session()
        if ses['mode'] == 'exam':
            raise AciError(403, 'Im Pruefungsmodus gibt es keine Hinweise', 403)
        hints = lab.get('hints') or []
        ses['hints'] = max(ses['hints'], min(int(level), len(hints)))
        self.sim['labSession'] = ses
        return {'hints': hints[:ses['hints']], 'used': ses['hints'], 'count': len(hints)}

    def lab_answer(self, qid, choice):
        lab = self.lab(self.sim.get('lab'))
        q = next((x for x in (lab or {}).get('questions', []) if x['id'] == qid), None)
        if not q:
            raise AciError(404, 'Frage %s gibt es nicht' % qid, 404)
        ses = self.lab_session()
        ses['answers'][qid] = int(choice)
        self.sim['labSession'] = ses
        return self.lab_public(lab)['answers'][qid]

    def check_lab(self, count=True):
        lab = self.lab(self.sim.get('lab'))
        if not lab:
            return None
        e = self.engine
        res = []
        for c in lab.get('checks', []):
            ok, info = False, ''
            t = c['type']
            try:
                if t == 'node':
                    nid = e.serial_node.get(c['serial'])
                    n = e.nodes.get(nid)
                    ok = bool(n) and n['state'] == 'active' and (not c.get('id') or nid == c['id']) and \
                        (not c.get('name') or n['name'] == c['name'])
                    info = '%s: %s' % (c['serial'], ('ID %s, %s, %s' % (nid, n['name'], n['state'])) if n
                                       else 'nicht registriert')
                elif t == 'exists':
                    a = self.store.attrs(c['dn'])
                    ok = a is not None and all(a.get(k) == v for k, v in c.get('attrs', {}).items())
                elif t == 'class':
                    dns = self.store.by_class(c['cls'])
                    ok = any(all(self.store.attrs(d).get(k) == v for k, v in c.get('attrs', {}).items())
                             and d.startswith(c.get('under', '')) for d in dns)
                elif t == 'traffic':
                    r = trace.run(e, self.sim, c['src'], c['dst'], c.get('proto', 'icmp'), c.get('port', 0))
                    ok = r['ok'] == c.get('expect', True)
                    if ok and c.get('via'):
                        ok = any(c['via'] in (s_['title'] + ' ' + s_['detail']) for s_ in r['steps'])
                    if ok and c.get('reason') and not r['ok']:
                        # Blockiert, aber aus dem geforderten Grund? (z. B. 'POLICY_' = durch Policy, nicht durch einen kaputten Pfad)
                        ok = r['reason'].startswith(c['reason'])
                    bad = next((s for s in r['steps'] if s['ok'] is False), None)
                    info = 'Ergebnis: %s (%s)%s' % (r['verdict'], r['reason'], ' - ' + bad['title'] if bad else '')
                elif t == 'exposure':
                    ok, info = self.exposure_check(c)
                elif t == 'endpoint':
                    hs = e.hosts.get(c['host'], {})
                    ok = hs.get('learned') and (not c.get('epg') or hs.get('epg') == c['epg'])
                    info = 'gelernt in %s' % e.short(hs.get('epg')) if hs.get('learned') else 'nicht gelernt'
                elif t == 'nofaults':
                    fl = [d for d in self.store.by_class('faultInst') if d.startswith(c.get('under', ''))
                          and (not c.get('code') or self.store.attrs(d)['code'] == c['code'])]
                    ok = not fl
                    info = '%d Fault(s)' % len(fl)
                elif t == 'ntp':
                    bad = {e.nodes[n]['name']: why for n, why in e.ntp['nodes'].items() if why}
                    ok = not bad and len(e.ntp['nodes']) >= c.get('min', 1)
                    info = '; '.join('%s: %s' % kv for kv in sorted(bad.items())) or '%d Switches synchron' % len(e.ntp['nodes'])
                elif t == 'graph':
                    g = next((g for g in getattr(e, 'graphs', {}).values() if g['brc'] == c['contract']), None)
                    ok = bool(g) and g['state'] == 'applied'
                    info = ('Zustand: %s%s' % (g['state'], ' - ' + '; '.join(g['reasons']) if g['reasons'] else '')) if g else 'kein Service Graph am Contract'
                elif t in ('login', 'rbac'):
                    try:
                        u_, roles_, how_ = aaa.authenticate(self, c['user'], c['pwd'])
                        logged = True
                    except AciError as ex:
                        logged, roles_, how_ = False, [], ex.text
                    if t == 'login':
                        ok = logged == c.get('expect', True) and (not c.get('role') or any(r['role'] == c['role'] for r in roles_))
                        info = ('angemeldet: %s - %s' % (how_, aaa.describe(roles_))) if logged else 'abgelehnt: %s' % how_
                    else:
                        can = logged and aaa.can_write(self.store, roles_, c['dn'])
                        ok = can == c.get('expect', True)
                        info = '%s darf %s %s schreiben' % (c['user'], '' if can else 'NICHT', c['dn'])
                elif t == 'firmware':
                    sw = {n['name']: ops.plain(e.node_version(n['serial'])) for n in e.nodes.values()}
                    bad = {k: v for k, v in sw.items() if v != ops.plain(c['switch'])}
                    ok = not bad and (not c.get('apic') or e.apic_version == ops.plain(c['apic'])) and not any(
                        not u.get('done') for u in self.sim.get('upgrades', []))
                    info = 'APIC %s; %s' % (e.apic_version, ', '.join('%s %s' % kv for kv in sorted(bad.items())) or 'alle Switches auf ' + ops.plain(c['switch']))
                elif t == 'fwgroups':
                    member = [n for g in e.fw_groups for n in g['nodes']]
                    miss = sorted(set(e.nodes) - set(member))
                    warn = [w for g in e.fw_groups for w in g['warn']]
                    multi = sorted({n for n in member if member.count(n) > 1})
                    ok = not miss and not warn and not multi and len(e.fw_groups) >= c.get('min', 2)
                    info = '; '.join(filter(None, ['ohne Gruppe: %s' % miss if miss else '', '; '.join(warn), 'mehrfach: %s' % multi if multi else ''])) \
                        or '%d Upgrade Groups' % len(e.fw_groups)
                elif t == 'job':
                    js = [j for j in self.sim.get('jobs', []) if j['kind'] == c['kind'] and j['ok']]
                    if c.get('secure'):
                        js = [j for j in js if 'ohne Secure' not in j['details']]
                    ok = bool(js)
                    last = (self.sim.get('jobs') or [{}])[-1]
                    info = js[-1]['details'] if js else ('letzter Job: %s' % last.get('details', 'keiner'))
                elif t == 'mon':
                    ds = [d for d in getattr(e, 'mon', []) if d['kind'] == c['kind']]
                    ok = any(d['ok'] for d in ds)
                    info = '; '.join('%s: %s' % (d['host'] or '-', 'ok' if d['ok'] else d['why']) for d in ds) or 'kein Ziel konfiguriert'
                elif t == 'received':
                    log = [x for x in self.sim.get('monlog', {}).get(c['collector'], []) if not x.get('dropped')]
                    hit = [x for x in log if c.get('contains', '') in x['text']]
                    ok = bool(hit)
                    info = '%d Meldungen empfangen' % len(log)
                elif t == 'snmp':
                    r = ops.snmp_walk(self, c['manager'], c['node'], c['community'])
                    ok = r['ok']
                    info = 'Antwort von %s' % c['node'] if ok else r['why']
                elif t == 'dhcp':
                    d = getattr(e, 'dhcp_info', {}).get(c['host']) or {}
                    ok = bool(d.get('ok'))
                    info = ('%s von %s' % (d['ip'], d['server'])) if ok else (d.get('why') or 'kein DHCP-Client')
                elif t == 'loop':
                    l = next((x for x in getattr(e, 'loops', []) if x['name'] == c['switch']), {})
                    ok = bool(l) and (not l.get('loop') or l.get('action') == c.get('action', 'mcp'))
                    info = l.get('text', 'Switch nicht vorhanden')
                elif t == 'msite':
                    why = e.msite_state()
                    ok = why is None
                    info = why or 'Infra zwischen den Sites ok'
                elif t == 'ipnadj':
                    adj = [x for x in getattr(e, 'mp', {}).get('adj', []) if x['serial'] in c['serials']]
                    bad = [x for x in adj if x['state'] != 'FULL']
                    ok = len(adj) == len(c['serials']) and not bad
                    info = '; '.join('%s: %s' % (x['serial'], x['why'] or x['state']) for x in bad) or 'alle FULL'
                elif t == 'inb':
                    ok = all(n in getattr(e, 'inb', {}) for n in c['nodes'])
                    info = 'In-Band aktiv auf: %s' % (', '.join(str(n) for n in sorted(getattr(e, 'inb', {}))) or 'keinem Node')
                elif t == 'learned':
                    rs = e.routers.get(c['router'], {})
                    has = c['prefix'] in rs.get('learned', [])
                    ok = has == c.get('expect', True)
                    info = '%s kennt von der ACI: %s' % (c['router'], ', '.join(rs.get('learned', [])) or 'nichts')
                elif t == 'route':
                    v = 'uni/tn-%s/ctx-%s' % tuple(c['vrf'].split(':'))
                    has = any(r['prefix'] == c['prefix'] and (not c.get('proto') or r['proto'] == c['proto'])
                              for r in e.routes.get((v, c['node']), []))
                    ok = has == c.get('expect', True)
                    info = 'Route %s auf Node %s: %s' % (c['prefix'], c['node'], 'vorhanden' if has else 'nicht vorhanden')
                elif t == 'setup':
                    su = self.sim.get('setup') or {}
                    ok = bool(su) and all(su.get(k) == v for k, v in c.get('attrs', {}).items())
                    info = 'nicht eingerichtet' if not su else ', '.join('%s=%s' % (k, su.get(k)) for k in c.get('attrs', {}))
                elif t == 'vmm':
                    v = e.vmm.get(c['dn'], {})
                    ok = v.get('state') == 'online'
                    info = 'Zustand: %s%s' % (v.get('state', 'nicht vorhanden'), ' - ' + '; '.join(v['reasons']) if v.get('reasons') else '')
                elif t == 'router':
                    rs = e.routers.get(c['name'], {})
                    if c.get('nodes'):
                        st_ = {a['nid']: a['state'] for a in rs.get('adjs', [])}
                        ok = all(st_.get(n) == c.get('adj', 'FULL') for n in c['nodes'])
                        info = 'Nachbarschaften: %s' % (', '.join('%s %s' % (e.nodes[n]['name'], s_) for n, s_ in st_.items()) or 'keine')
                    else:
                        ok = rs.get('adj') == c.get('adj', 'FULL')
                        info = 'Zustand: %s' % rs.get('adj')
                elif t == 'bfd':
                    rs = e.routers.get(c['router'], {})
                    st_ = {b['nid']: b['state'] for b in rs.get('bfd', [])}
                    ok = bool(st_) and all(st_.get(n) == 'Up' for n in c.get('nodes', st_.keys()))
                    info = 'BFD: %s' % (', '.join('%s %s' % (e.nodes[n]['name'], s_) for n, s_ in st_.items()) or 'keine Session')
                elif t == 'bgptimer':
                    rs = e.routers.get(c['router'], {})
                    tm = next(iter((rs.get('timers') or {}).values()), {})
                    ok = tm.get('hold') == c['hold']
                    info = 'Hold Time: %s' % tm.get('hold')
            except (KeyError, ValueError) as ex:
                info = 'Pruefung fehlerhaft: %s' % ex
            res.append({'desc': c['desc'], 'ok': bool(ok), 'info': info, 'category': c.get('category', 'function')})
        ses = self.lab_session()
        ses['checks'] = ses.get('checks', 0) + (1 if count else 0)
        self.sim['labSession'] = ses
        cats = {}
        for r in res:
            k = cats.setdefault(r['category'], {'passed': 0, 'total': 0})
            k['total'] += 1
            k['passed'] += 1 if r['ok'] else 0
        qs = lab.get('questions', [])
        und = {'correct': sum(1 for q in qs if ses['answers'].get(q['id']) == q['answer']), 'answered': len(ses['answers']), 'total': len(qs)}
        if ses['mode'] == 'exam':
            for r in res:
                r['info'] = ''
        out = {'id': lab['id'], 'title': lab['title'], 'checks': res, 'categories': cats, 'understanding': und,
               'mode': ses['mode'], 'hintsUsed': ses['hints'], 'checkRuns': ses['checks'],
               'passed': sum(1 for r in res if r['ok']), 'total': len(res)}
        self.record_progress(out)
        return out

    # Standard-Proben fuer Least Privilege: typische Dienste, die zwischen zwei Zonen nicht offen sein sollten
    EXPOSURE_PROBES = ['icmp', 'tcp/20', 'tcp/21', 'tcp/22', 'tcp/23', 'tcp/25', 'tcp/53', 'tcp/80', 'tcp/135', 'tcp/139', 'tcp/443',
                       'tcp/445', 'tcp/502', 'tcp/1433', 'tcp/3306', 'tcp/3389', 'tcp/5900', 'tcp/8080', 'tcp/8443', 'tcp/44818',
                       'udp/53', 'udp/69', 'udp/123', 'udp/161', 'udp/443', 'udp/514', 'udp/47808']

    def exposure_check(self, c):
        """Least Privilege: von src nach dst darf eine neue Verbindung nur fuer die Fluesse in 'allow' durch die Policy kommen.
        Gewertet wird die Policy-Entscheidung fuer die Anfrage (dieselbe Engine wie der Traffic-Test), unabhaengig davon,
        ob auf dem Ziel ein Dienst laeuft."""
        allow = {x.lower() for x in c.get('allow', [])}
        probes = c.get('probes') or self.EXPOSURE_PROBES
        open_ = []
        for pr in probes:
            if pr.lower() in allow:
                continue
            proto, _, port = pr.partition('/')
            r = trace.run(self.engine, self.sim, c['src'], c['dst'], proto, int(port or 0))
            if any(p['direction'] == 'request' and p['action'] == 'permit' for p in r['policy']):
                open_.append(pr)
        if open_:
            return False, 'Zusaetzlich offen: %s (geprueft: %d typische Dienste)' % (', '.join(open_), len(probes))
        return True, 'Nur %s offen (geprueft: %d typische Dienste)' % (', '.join(sorted(allow)) or 'nichts', len(probes))

    # -------------------------------------------------------------- Fortschritt
    def progress(self):
        try:
            with open(os.path.join(self.data_dir, 'progress.json'), encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _write_progress(self, p):
        fp = os.path.join(self.data_dir, 'progress.json')
        with open(fp + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(p, f)
        os.replace(fp + '.tmp', fp)

    def record_progress(self, chk):
        """Letztes Pruefergebnis je Lab; 'done' bleibt stehen, sobald ein Lab einmal komplett bestanden war."""
        p = self.progress()
        old = p.get(chk['id'], {})
        done = old.get('done') or (chk['total'] > 0 and chk['passed'] == chk['total'])
        new = {'passed': chk['passed'], 'total': chk['total'], 'ts': now_ts(), 'done': bool(done),
               'doneTs': old.get('doneTs') or (now_ts() if done else None)}
        if {k: old.get(k) for k in ('passed', 'total', 'done')} != {k: new[k] for k in ('passed', 'total', 'done')}:
            p[chk['id']] = new
            self._write_progress(p)

    # -------------------------------------------------------------- Snapshots
    def snapshots(self):
        d = os.path.join(self.data_dir, 'snapshots')
        out = []
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.json'):
                try:
                    with open(os.path.join(d, fn), encoding='utf-8') as f:
                        s = json.load(f)
                    out.append({'name': fn[:-5], 'created': s.get('created'), 'descr': s.get('descr', ''),
                                'objects': len(s.get('config', []))})
                except (OSError, ValueError):
                    pass
        return out

    def snapshot(self, op, name, descr=''):
        if not NAME_RE.match(name or ''):
            raise AciError(400, 'Ungueltiger Snapshot-Name')
        fn = os.path.join(self.data_dir, 'snapshots', name + '.json')
        if op == 'create':
            with open(fn, 'w', encoding='utf-8') as f:
                json.dump({'created': now_ts(), 'descr': descr, 'config': self.store.dump_config(),
                           'counters': self.store.counters, 'hosts': self.sim.get('hosts', []),
                           'routers': self.sim.get('routers', [])}, f)
        elif op == 'rollback':
            with open(fn, encoding='utf-8') as f:
                s = json.load(f)
            self.store.load_config(s['config'], s.get('counters'))
            ensure_base(self.store)
            self.changed()
        elif op == 'delete':
            if os.path.exists(fn):
                os.remove(fn)


    # -------------------------------------------------------------- Spielstaende
    SAVE_VERSION = 1

    def _save_file(self, name):
        if not NAME_RE.match(name or ''):
            raise AciError(400, 'Name: 1-32 Zeichen, Buchstaben/Ziffern/._-')
        return os.path.join(self.data_dir, 'saves', name + '.json')

    def save_blob(self, descr=''):
        """Kompletter Zustand: Konfiguration, simulierte Welt, Setup, Lab und Fortschritt."""
        lab = self.lab(self.sim.get('lab')) if self.sim.get('lab') else None
        chk = self.check_lab(count=False) if lab else None
        return {'kind': 'datacenter-prep-save', 'version': self.SAVE_VERSION, 'created': now_ts(), 'descr': descr,
                'lab': lab['id'] if lab else None, 'labTitle': lab['title'] if lab else None,
                'progress': [chk['passed'], chk['total']] if chk else None,
                'fabricName': (self.sim.get('setup') or {}).get('fabricName'),
                'tenants': sorted(self.store.attrs(d)['name'] for d in self.store.by_class('fvTenant')),
                'config': self.store.dump_config(), 'counters': self.store.counters,
                'sim': json.loads(json.dumps(self.sim))}

    def _check_blob(self, b):
        if not isinstance(b, dict) or b.get('kind') != 'datacenter-prep-save' or 'config' not in b or 'sim' not in b:
            raise AciError(400, 'Keine gueltige Datacenter-Prep-Sicherung')
        if int(b.get('version', 0)) > self.SAVE_VERSION:
            raise AciError(400, 'Die Sicherung stammt aus einer neueren Version von Datacenter Prep')
        for k in ('topology', 'hosts', 'routers'):
            if k not in b['sim']:
                raise AciError(400, 'Sicherung unvollstaendig (%s fehlt)' % k)

    def saves(self):
        d = os.path.join(self.data_dir, 'saves')
        out = []
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.json'):
                try:
                    with open(os.path.join(d, fn), encoding='utf-8') as f:
                        s = json.load(f)
                    row = {k: s.get(k) for k in ('created', 'descr', 'lab', 'labTitle', 'progress', 'fabricName', 'tenants')}
                    row.update(name=fn[:-5], auto=fn.startswith('auto-'))
                    out.append(row)
                except (OSError, ValueError):
                    pass
        return sorted(out, key=lambda x: x.get('created') or '', reverse=True)

    def save_game(self, name, descr=''):
        fn = self._save_file(name)
        tmp = fn + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.save_blob(descr), f)
        os.replace(tmp, fn)

    def read_save(self, name):
        fn = self._save_file(name)
        if not os.path.exists(fn):
            raise AciError(404, 'Spielstand %s nicht gefunden' % name, 404)
        with open(fn, encoding='utf-8') as f:
            return json.load(f)

    def load_blob(self, b):
        self._check_blob(b)
        self.store.load_config(b['config'], b.get('counters'))
        ensure_base(self.store)
        sim = b['sim']
        sim.setdefault('settings', {'discoverySeconds': self.default_discovery})
        if 'setup' not in sim:
            sim['setup'] = {k: v for k, v in apic_setup.DEFAULTS.items() if k != 'pwd'}
        self.sim = sim
        self.engine = Engine(self.store, self.sim)
        self.changed()

    @staticmethod
    def auto_name(lid):
        return ('auto-' + (lid or 'frei'))[:32]

    def autosave_lab(self):
        """Vor dem Wechsel: das laufende Lab als auto-<lab> sichern (freies Ueben als auto-frei)."""
        lid = self.sim.get('lab')
        if self.sim.get('setup', 0) is None:
            return
        if not lid and self.sim.get('pristine') and not self.sim.get('hosts'):
            return
        self.save_game(self.auto_name(lid), 'Automatisch gesichert beim Wechsel' + ('' if lid else ' (freies Üben)'))

    def lab_saves(self, lid):
        """Speicherstaende eines Labs (lid None = freies Ueben), neueste zuerst; der automatische Stand ist markiert."""
        return [x for x in self.saves() if (x.get('lab') or None) == (lid or None)]

    def lab_op(self, b):
        """Labs: fortsetzen, auf Default zuruecksetzen, Staende loeschen, freies Ueben."""
        op, lid = b.get('op'), b.get('id') or None
        if lid and not self.lab(lid):
            raise AciError(404, 'Lab %s nicht gefunden' % lid, 404)
        if op == 'resume':
            saves = self.lab_saves(lid)
            auto = next((x for x in saves if x['name'] == self.auto_name(lid)), None)
            pick = next((x for x in saves if x['name'] == b.get('save')), None) if b.get('save') else (auto or (saves[0] if saves else None))
            if self.sim.get('lab') != lid or b.get('save'):
                self.autosave_lab()
            if pick:
                self.load_blob(self.read_save(pick['name']))
                return {'ok': True, 'loaded': pick['name']}
            if lid:
                self.load_lab(lid, autosave=False, mode=b.get('mode'))
            else:
                self.reset('discovered', keep_sim=False)
                self.save()
            return {'ok': True, 'loaded': None}
        if op == 'reset':
            mode = b.get('mode') or (self.lab_session()['mode'] if self.sim.get('lab') == lid else None)
            if self.sim.get('lab') != lid:
                self.autosave_lab()
            for x in self.lab_saves(lid):
                if x['name'] == self.auto_name(lid) or b.get('purge'):
                    os.remove(self._save_file(x['name']))
            if b.get('purge') and lid:
                p = self.progress()
                if p.pop(lid, None) is not None:
                    self._write_progress(p)
            if lid:
                self.load_lab(lid, autosave=False, mode=mode)
            else:
                self.reset('discovered')
                self.save()
            return {'ok': True}
        if op == 'purge':
            n = 0
            for x in self.lab_saves(lid):
                os.remove(self._save_file(x['name']))
                n += 1
            if lid and b.get('progress'):
                p = self.progress()
                if p.pop(lid, None) is not None:
                    self._write_progress(p)
            return {'ok': True, 'deleted': n}
        raise AciError(400, 'Unbekannte Aktion')

    # -------------------------------------------------------------- Sim-Objekte
    def used_ports(self, skip=None):
        used = {}
        for l in self.sim['topology']['links']:
            used[(l[0], l[1])] = 'Fabric-Link'
            used[(l[2], l[3])] = 'Fabric-Link'
        for h in self.sim['hosts']:
            if h['name'] != skip:
                for s, p in h['links']:
                    used[(s, p)] = 'Host ' + h['name']
        for r in self.sim['routers']:
            if r['name'] != skip:
                for s_, p_ in (r.get('links') or [[r['serial'], r['port']]]):
                    used[(s_, p_)] = 'Router ' + r['name']
        for d in self.sim.get('devices', []):
            if d['name'] != skip:
                for s_, p_ in d.get('links', []):
                    used[(s_, p_)] = 'L4-L7 ' + d['name']
        for sw in self.sim.get('switches', []):
            if sw['name'] != skip:
                for s_, p_ in sw.get('links', []):
                    used[(s_, p_)] = 'Switch ' + sw['name']
        for vc in self.sim.get('vcenters', []):
            for esx in vc.get('hosts', []):
                if esx['name'] != skip:
                    for s_, p_ in esx.get('links', []):
                        used[(s_, p_)] = 'ESXi ' + esx['name']
        return used

    def _check_port(self, serial, port, used):
        node = next((n for n in self.sim['topology']['nodes'] if n['serial'] == serial), None)
        if not node or node['role'] != 'leaf':
            raise AciError(400, 'Switch %s ist kein Leaf' % serial)
        m = re.match(r'^eth1/(\d+)$', port)
        if not m or not 1 <= int(m.group(1)) <= node['ports']:
            raise AciError(400, 'Ungueltiger Port %s' % port)
        if (serial, port) in used:
            raise AciError(400, '%s %s ist bereits belegt (%s)' % (serial, port, used[(serial, port)]))

    def set_host(self, h, old=None):
        if not NAME_RE.match(h.get('name', '')):
            raise AciError(400, 'Name: 1-32 Zeichen, Buchstaben/Ziffern/._-')
        names = {x['name'] for x in self.sim['hosts'] + self.sim['routers'] + self.sim.get('switches', []) if x['name'] != old}
        if h['name'] in names:
            raise AciError(400, 'Name %s ist bereits vergeben' % h['name'])
        if not MAC_RE.match(h.get('mac', '')):
            raise AciError(400, 'MAC-Adresse ungueltig (Format 00:50:56:00:00:01)')
        if h.get('dhcp'):
            h['ip'], h['gw'] = '0.0.0.0/32', ''
        scopes = []
        raw = h.get('dhcpd') or []
        if isinstance(raw, str):
            raw = raw.replace(';', '\n').splitlines()
        for line in raw:
            if isinstance(line, dict):
                scopes.append(line)
                continue
            m = re.match(r'^\s*(\S+)\s+(\S+)\s*-\s*(\S+)(?:\s+gw\s+(\S+))?\s*$', line)
            if not line.strip():
                continue
            try:
                assert m
                ipaddress.ip_network(m.group(1), strict=False)
                ipaddress.ip_address(m.group(2))
                ipaddress.ip_address(m.group(3))
            except (AssertionError, ValueError):
                raise AciError(400, 'DHCP-Scope ungueltig: "%s" (Format: 10.1.1.0/24 10.1.1.100-10.1.1.199 gw 10.1.1.1)' % line.strip())
            scopes.append({'net': m.group(1), 'from': m.group(2), 'to': m.group(3), 'gw': m.group(4) or ''})
        try:
            ipaddress.ip_interface(h['ip'])
            assert '/' in h['ip']
            if h.get('gw'):
                ipaddress.ip_address(h['gw'])
        except (ValueError, KeyError, AssertionError):
            raise AciError(400, 'IP (mit Maske, z. B. 10.1.1.10/24) oder Gateway ungueltig')
        v = int(h.get('vlan') or 0)
        if not 0 <= v <= 4094:
            raise AciError(400, 'VLAN 0 (untagged) oder 1-4094')
        links = h.get('links') or []
        if not 1 <= len(links) <= 4:
            raise AciError(400, 'Ein Host braucht 1 bis 4 Links')
        used = self.used_ports(skip=old or h['name'])
        seen = set()
        for s, p in links:
            if (s, p) in seen:
                raise AciError(400, 'Port doppelt angegeben')
            seen.add((s, p))
            self._check_port(s, p, used)
        if h.get('bond', 'none') not in ('none', 'static', 'lacp-active', 'lacp-passive'):
            raise AciError(400, 'Bonding ungueltig')
        clean = {'name': h['name'], 'mac': h['mac'].upper().replace('-', ':'), 'ip': h['ip'], 'gw': h.get('gw', ''),
                 'vlan': v, 'links': [[s, p] for s, p in links], 'bond': h.get('bond', 'none'),
                 'descr': h.get('descr', ''), 'silent': bool(h.get('silent'))}
        if h.get('dhcp'):
            clean['dhcp'] = True
        svc = h.get('services')
        if isinstance(svc, str):
            svc = [x for x in re.split(r'[\s,;]+', svc) if x]
        if svc:
            for x in svc:
                m = re.match(r'^(tcp|udp)/(\d{1,5})$', str(x).strip().lower())
                if not m or not 1 <= int(m.group(2)) <= 65535:
                    raise AciError(400, 'Dienst ungueltig: "%s" (Format tcp/443 oder udp/53)' % x)
            clean['services'] = sorted({str(x).strip().lower() for x in svc}, key=lambda x: (x.split('/')[0], int(x.split('/')[1])))
        if scopes:
            clean['dhcpd'] = scopes
        self.sim['woken'] = [n for n in self.sim.get('woken', []) if n != clean['name']]
        self.sim['hosts'] = [x for x in self.sim['hosts'] if x['name'] != (old or h['name'])] + [clean]

    def set_router(self, r, old=None):
        if not NAME_RE.match(r.get('name', '')):
            raise AciError(400, 'Name: 1-32 Zeichen, Buchstaben/Ziffern/._-')
        names = {x['name'] for x in self.sim['hosts'] + self.sim['routers'] if x['name'] != old}
        if r['name'] in names:
            raise AciError(400, 'Name %s ist bereits vergeben' % r['name'])
        try:
            ipaddress.ip_interface(r['ip'])
            assert '/' in r['ip']
            for n in r.get('networks', []) + r.get('advertise', []) + r.get('staticBack', []):
                ipaddress.ip_network(n, strict=False)
        except (ValueError, KeyError, AssertionError):
            raise AciError(400, 'IP/Netze ungueltig (Format 172.16.1.2/30, 8.8.8.0/24)')
        used = self.used_ports(skip=old or r['name'])
        links = [l for l in (r.get('links') or []) if l and l[0]]
        if not links:
            links = [[r.get('serial'), r.get('port')]]
        if len(links) > 2:
            raise AciError(400, 'Ein Router hat 1 oder 2 Links')
        for s_, p_ in links:
            self._check_port(s_, p_, used)
        r['serial'], r['port'] = links[0]
        if r.get('protocol') not in ('static', 'ospf', 'bgp', 'eigrp'):
            raise AciError(400, 'Protokoll static, ospf, bgp oder eigrp')
        clean = {k: r.get(k) for k in ('name', 'serial', 'port', 'ip', 'protocol', 'routerId', 'descr')}
        clean['links'] = [[s_, p_] for s_, p_ in links]
        clean['bond'] = r.get('bond') if r.get('bond') in ('none', 'lacp-active', 'lacp-passive', 'static') else 'none'
        clean['bfd'] = bool(r.get('bfd'))
        clean['down'] = bool(r.get('down'))
        e_ = r.get('eigrp') or {}
        clean['eigrp'] = {'asn': str(e_.get('asn', '1')), 'hello': int(e_.get('hello', 5)), 'hold': int(e_.get('hold', 15))}
        clean['vlan'] = int(r.get('vlan') or 0)
        clean['mtu'] = int(r.get('mtu') or 1500)
        for k in ('networks', 'advertise', 'staticBack'):
            clean[k] = [str(x) for x in r.get(k, [])]
        o = r.get('ospf') or {}
        clean['ospf'] = {'area': o.get('area', '0.0.0.0'), 'areaType': o.get('areaType', 'regular'),
                         'hello': int(o.get('hello', 10)), 'dead': int(o.get('dead', 40)),
                         'nwT': o.get('nwT', 'bcast'), 'mtuIgnore': bool(o.get('mtuIgnore'))}
        b = r.get('bgp') or {}
        clean['bgp'] = {'asn': str(b.get('asn', '65100')), 'peerAs': str(b.get('peerAs', '65001')),
                        'password': str(b.get('password') or ''), 'hold': int(b.get('hold') or 180),
                        'keepalive': int(b.get('keepalive') or 60), 'updateSource': str(b.get('updateSource') or ''),
                        'peerAddr': str(b.get('peerAddr') or '')}
        for k in ('updateSource', 'peerAddr'):
            if clean['bgp'][k]:
                try:
                    ipaddress.ip_address(clean['bgp'][k])
                except ValueError:
                    raise AciError(400, 'BGP %s: ungueltige IP' % k)
        self.sim['routers'] = [x for x in self.sim['routers'] if x['name'] != (old or r['name'])] + [clean]

    def aaa_server_op(self, b):
        """Simulierte AAA-Server (TACACS+, RADIUS, LDAP) im OOB-Netz."""
        lst = self.sim.setdefault('aaa', [])
        if b.get('op') == 'delete':
            self.sim['aaa'] = [x for x in lst if x['ip'] != b.get('ip')]
            return
        o = b.get('obj') or {}
        try:
            ipaddress.ip_address(o.get('ip', ''))
        except ValueError:
            raise AciError(400, 'IP-Adresse des Servers ungueltig')
        if o.get('type') not in ('tacacs', 'radius', 'ldap'):
            raise AciError(400, 'Typ tacacs, radius oder ldap')
        old = next((x for x in lst if x['ip'] == (b.get('old') or o['ip'])), None)
        key = old['key'] if old and o.get('key') in (None, '***') else o.get('key', '')
        users = []
        for u in o.get('users') or []:
            if not u.get('name'):
                continue
            ou = next((x for x in (old or {}).get('users', []) if x['name'] == u['name']), {})
            users.append({'name': u['name'], 'pwd': ou.get('pwd', '') if u.get('pwd') in (None, '***') else u.get('pwd', ''),
                          'avpair': u.get('avpair', '')})
        clean = {'name': o.get('name') or o['ip'], 'ip': o['ip'], 'type': o['type'], 'key': key, 'down': bool(o.get('down')), 'users': users}
        self.sim['aaa'] = [x for x in lst if x is not old] + [clean]

    def device_op(self, b):
        """Simulierte L4-L7-Geraete (Firewalls) verwalten."""
        devs = self.sim.setdefault('devices', [])
        if b.get('op') == 'delete':
            self.sim['devices'] = [d for d in devs if d['name'] != b.get('name')]
            return
        o = b.get('obj') or {}
        if not NAME_RE.match(o.get('name', '')):
            raise AciError(400, 'Name ungueltig')
        old = b.get('old') or o['name']
        links = o.get('links') or []
        if not 1 <= len(links) <= 2:
            raise AciError(400, 'Ein Geraet braucht 1 oder 2 Links')
        used = self.used_ports(skip=old)
        for s_, p_ in links:
            self._check_port(s_, p_, used)
        ifs = []
        for i in o.get('ifs') or []:
            if not NAME_RE.match(i.get('name', '')) or not MAC_RE.match(i.get('mac', '')):
                raise AciError(400, 'Interface: Name oder MAC ungueltig')
            try:
                ipaddress.ip_interface(i['ip'])
                assert '/' in i['ip']
                vlan = int(i.get('vlan') or 0)
                assert 0 <= vlan <= 4094
            except (ValueError, KeyError, AssertionError):
                raise AciError(400, 'Interface %s: IP mit Maske und VLAN 0-4094 angeben' % i.get('name'))
            ifs.append({'name': i['name'], 'vlan': vlan, 'ip': i['ip'], 'mac': i['mac'].upper().replace('-', ':')})
        allow = [a.strip().lower() for a in (o.get('allow') or ['any']) if a.strip()]
        clean = {'name': o['name'], 'links': [[s_, p_] for s_, p_ in links], 'ifs': ifs, 'allow': allow or ['any']}
        self.sim['devices'] = [d for d in devs if d['name'] != old] + [clean]

    def switch_op(self, b):
        """Legacy-Switches (z. B. ein alter Access-Switch), die an Leaf-Ports haengen."""
        sws = self.sim.setdefault('switches', [])
        if b.get('op') == 'delete':
            self.sim['switches'] = [x for x in sws if x['name'] != b.get('name')]
            return
        o = b.get('switch') or {}
        old = b.get('old')
        if not NAME_RE.match(o.get('name', '')):
            raise AciError(400, 'Name: 1-32 Zeichen, Buchstaben/Ziffern/._-')
        names = {x['name'] for x in self.sim['hosts'] + self.sim['routers'] + sws if x['name'] != (old or o['name'])}
        if o['name'] in names:
            raise AciError(400, 'Name %s ist bereits vergeben' % o['name'])
        links = o.get('links') or []
        if not 1 <= len(links) <= 4:
            raise AciError(400, 'Ein Legacy-Switch braucht 1 bis 4 Links')
        used = self.used_ports(skip=old or o['name'])
        for s_, p_ in links:
            self._check_port(s_, p_, used)
        if o.get('bond', 'none') not in ('none', 'lacp'):
            raise AciError(400, 'Bonding: none oder lacp')
        vl = str(o.get('vlans') or '').strip()
        if vl and not re.match(r'^\d+(\s*,\s*\d+)*$', vl):
            raise AciError(400, 'VLANs als Liste, z. B. 10,20 (leer = alle)')
        clean = {'name': o['name'], 'links': [[a, c] for a, c in links], 'bond': o.get('bond', 'none'), 'vlans': vl,
                 'descr': o.get('descr', '')}
        self.sim['switches'] = [x for x in sws if x['name'] != (old or o['name'])] + [clean]

    def bulk_hosts(self, text, replace=False):
        """CSV: name,mac,ip/maske,gateway,vlan,leaf,port[,leaf2,port2,bond]. Leaf als Name, Node-ID oder Serial; MAC leer = automatisch.
        Atomar: bei einem Fehler wird nichts uebernommen."""
        nodes = self.sim['topology']['nodes']
        nid_of = {}
        for d in self.store.by_class('fabricNodeIdentP'):
            a = self.store.attrs(d)
            nid_of[a['nodeId']] = a['serial']
            nid_of[a['name']] = a['serial']
        for n in nodes:
            nid_of[n['serial']] = n['serial']
            if n.get('hint'):
                nid_of.setdefault(n['hint'], n['serial'])
        backup = json.loads(json.dumps(self.sim['hosts']))
        if replace:
            self.sim['hosts'] = []
        errs, added = [], 0
        for i, line in enumerate(str(text or '').splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#') or line.lower().startswith('name,'):
                continue
            c = [x.strip() for x in line.split(',')]
            try:
                if len(c) < 7:
                    raise AciError(400, 'mindestens 7 Spalten: name,mac,ip,gw,vlan,leaf,port')
                links = [[nid_of.get(c[5], c[5]), c[6] if c[6].startswith('eth') else 'eth1/' + c[6]]]
                if len(c) >= 9 and c[7]:
                    links.append([nid_of.get(c[7], c[7]), c[8] if c[8].startswith('eth') else 'eth1/' + c[8]])
                hx = hashlib.md5(c[0].encode()).hexdigest().upper()
                mac = c[1] or '00:50:56:%s:%s:%s' % (hx[0:2], hx[2:4], hx[4:6])
                self.set_host({'name': c[0], 'mac': mac, 'ip': c[2], 'gw': c[3], 'vlan': int(c[4] or 0), 'links': links,
                               'bond': c[9] if len(c) > 9 and c[9] else ('lacp-active' if len(links) > 1 else 'none')})
                added += 1
            except (AciError, ValueError) as ex:
                errs.append('Zeile %d (%s): %s' % (i, c[0] if c else '', getattr(ex, 'text', str(ex))))
        if errs:
            self.sim['hosts'] = backup
            raise AciError(400, 'Nichts uebernommen - %d Fehler: %s' % (len(errs), ' | '.join(errs[:8]) + (' …' if len(errs) > 8 else '')))
        return added

    def topology_op(self, b):
        """Topologie neu aufbauen: Pods, Spines, Leafs, Remote Leafs. Die Konfiguration bleibt erhalten."""
        try:
            t = build_topology(b.get('spec') or {})
        except (ValueError, TypeError) as ex:
            raise AciError(400, 'Topologie ungueltig: %s' % ex)
        old = {n['serial'] for n in self.sim['topology']['nodes']}
        self.sim['topology'] = t
        if t.get('ipnlinks'):
            self.sim['ipn'] = build_ipn(t, relay=[self.engine.apic_tep] if b.get('infra') else [])
        else:
            self.sim.pop('ipn', None)
        reg = self.sim.setdefault('registered', {})
        if b.get('register'):
            for m in discovered_members(t):
                ser = m['fabricNodeIdentP']['attributes']['serial']
                if not any(self.store.attrs(d)['serial'] == ser for d in self.store.by_class('fabricNodeIdentP')):
                    mit_post(self.store, 'uni/controller/nodeidentpol', m)
                    reg[ser] = 0.0
        if b.get('infra'):
            for url, body in infra_config(t):
                mit_post(self.store, url, body)
        serials = {n['serial'] for n in t['nodes']}
        lost = [h['name'] for h in self.sim['hosts'] if any(l[0] not in serials for l in h['links'])]
        return {'nodes': len(t['nodes']), 'removed': sorted(old - serials), 'hostsWithoutSwitch': lost}

    def ipn_op(self, b):
        """IPN- und WAN-Router der Multi-Pod-Topologie bearbeiten."""
        cfg = self.sim.setdefault('ipn', default_ipn())
        o = b.get('router') or {}
        r = next((x for x in cfg['routers'] if x['name'] == o.get('name')), None)
        if not r:
            raise AciError(400, 'Router %s gibt es nicht' % o.get('name'))
        try:
            mtu = int(o.get('mtu', r['mtu']))
            assert 576 <= mtu <= 9216
            relay = [str(ipaddress.ip_address(x.strip())) for x in re.split(r'[,\s]+', str(o.get('relay', ''))) if x.strip()] \
                if isinstance(o.get('relay', ''), str) else [str(ipaddress.ip_address(x)) for x in o.get('relay', [])]
            if o.get('rp'):
                ipaddress.ip_address(o['rp'])
            ifs = []
            for i in o.get('ifs', r['ifs']):
                if i.get('ip'):
                    ipaddress.ip_interface(i['ip'])
                ifs.append({'serial': i['serial'], 'port': i['port'], 'vlan': int(i.get('vlan') or 0), 'ip': i.get('ip', '')})
        except (ValueError, AssertionError):
            raise AciError(400, 'Ungueltige Eingabe (MTU 576-9216, IP-Adressen mit Maske, Relay als IP-Liste)')
        r.update({'mtu': mtu, 'area': o.get('area', r['area']) or '0.0.0.0', 'pim': bool(o.get('pim', r['pim'])), 'rp': o.get('rp', r['rp']),
                  'relay': relay if 'relay' in o else r['relay'], 'down': bool(o.get('down', r['down'])), 'ifs': ifs})

    def monitor_op(self, b):
        mons = self.sim.setdefault('monitors', [])
        op = b.get('op')
        if op == 'delete':
            self.sim['monitors'] = [m for m in mons if m['name'] != b.get('name')]
            self.sim.get('monlog', {}).pop(b.get('name'), None)
            return None
        if op == 'clear':
            self.sim.setdefault('monlog', {})[b.get('name')] = []
            return None
        if op == 'walk':
            return ops.snmp_walk(self, b.get('name'), b.get('node', ''), b.get('community', ''))
        if op == 'test':
            self._event('uni/fabric/moncommon', 'Test notification from %s' % self.sim['topology']['apic']['name'], sev='info',
                        rec={'kind': 'fault', 'severity': b.get('severity', 'major'), 'orig': b.get('severity', 'major'), 'code': 'F9999',
                             'dn': 'topology/pod-1/node-1/sys', 'descr': 'Test fault raised by the simulator (Testmeldung)',
                             'lc': 'raised', 'cause': 'test'})
            return None
        o = b.get('monitor') or {}
        old = b.get('old')
        if not NAME_RE.match(o.get('name', '')):
            raise AciError(400, 'Name ungueltig')
        if o.get('type') not in ('syslog', 'snmp', 'smtp'):
            raise AciError(400, 'Typ: syslog, snmp oder smtp')
        try:
            ipaddress.ip_address(o.get('ip', ''))
            port = int(o.get('port') or {'syslog': 514, 'snmp': 162, 'smtp': 25}[o['type']])
        except ValueError:
            raise AciError(400, 'IP-Adresse oder Port ungueltig')
        clean = {'name': o['name'], 'type': o['type'], 'ip': o['ip'], 'port': port, 'down': bool(o.get('down'))}
        if o['type'] == 'snmp':
            clean['community'] = o.get('community', '')
        self.sim['monitors'] = [m for m in mons if m['name'] != (old or o['name'])] + [clean]
        return None

    def fileserver_op(self, b):
        fs = ops.fileserver(self)
        op = b.get('op')
        if op == 'delete':
            fs['files'].pop(b.get('path'), None)
        elif op == 'set':
            o = b.get('server') or {}
            try:
                ipaddress.ip_address(o.get('ip', fs['ip']))
            except ValueError:
                raise AciError(400, 'IP-Adresse ungueltig')
            for k in ('ip', 'user', 'pwd'):
                if o.get(k):
                    fs[k] = o[k]
            fs['down'] = bool(o.get('down'))
            if o.get('dirs'):
                fs['dirs'] = sorted({'/' + d.strip().strip('/') for d in str(o['dirs']).split(',') if d.strip()})
        elif op == 'reset':
            keep = {k: v for k, v in fs['files'].items() if v.get('export')}
            self.sim['fileserver'] = ops.default_fileserver()
            self.sim['fileserver']['files'].update(keep)

    def vcenter_op(self, b):
        """Verwaltung des simulierten vCenters: vCenter, ESXi-Hosts, VMs."""
        vcs = self.sim.setdefault('vcenters', [])
        op, kind = b.get('op'), b.get('kind')
        o = b.get('obj') or {}
        if kind == 'vcenter':
            if op == 'delete':
                self.sim['vcenters'] = [v for v in vcs if v['name'] != b.get('name')]
                return
            if not NAME_RE.match(o.get('name', '')):
                raise AciError(400, 'Name ungueltig')
            try:
                ipaddress.ip_address(o.get('ip', ''))
            except ValueError:
                raise AciError(400, 'IP-Adresse des vCenters ungueltig')
            old = next((v for v in vcs if v['name'] == (b.get('old') or o['name'])), None)
            pwd = old['pwd'] if old and o.get('pwd') in (None, '***') else o.get('pwd', '')
            clean = {'name': o['name'], 'ip': o['ip'], 'datacenter': o.get('datacenter') or 'DC1', 'user': o.get('user', ''),
                     'pwd': pwd, 'hosts': old['hosts'] if old else []}
            self.sim['vcenters'] = [v for v in vcs if v is not old] + [clean]
            return
        vc = next((v for v in vcs if v['name'] == b.get('vc')), None)
        if not vc:
            raise AciError(400, 'vCenter %s nicht gefunden' % b.get('vc'))
        if kind == 'esxi':
            if op == 'delete':
                vc['hosts'] = [h for h in vc['hosts'] if h['name'] != b.get('name')]
                return
            if not NAME_RE.match(o.get('name', '')):
                raise AciError(400, 'Name ungueltig')
            old = next((h for h in vc['hosts'] if h['name'] == (b.get('old') or o['name'])), None)
            links = o.get('links') or []
            if not 1 <= len(links) <= 2:
                raise AciError(400, 'Ein ESXi-Host braucht 1 oder 2 Uplinks')
            used = self.used_ports(skip=old['name'] if old else None)
            for s_, p_ in links:
                self._check_port(s_, p_, used)
            clean = {'name': o['name'], 'links': [[s_, p_] for s_, p_ in links], 'dvs': list(o.get('dvs') or []),
                     'vms': old['vms'] if old else []}
            vc['hosts'] = [h for h in vc['hosts'] if h is not old] + [clean]
            return
        if kind == 'vm':
            esx = next((h for h in vc['hosts'] if h['name'] == b.get('esxi')), None)
            if not esx:
                raise AciError(400, 'ESXi-Host %s nicht gefunden' % b.get('esxi'))
            for h in vc['hosts']:
                h['vms'] = [v for v in h['vms'] if v['name'] != (b.get('old') or b.get('name') or o.get('name'))]
            if op == 'delete':
                return
            if not NAME_RE.match(o.get('name', '')) or not MAC_RE.match(o.get('mac', '')):
                raise AciError(400, 'Name oder MAC ungueltig')
            try:
                ipaddress.ip_interface(o['ip'])
                assert '/' in o['ip']
            except (ValueError, KeyError, AssertionError):
                raise AciError(400, 'IP mit Maske angeben, z. B. 10.1.1.20/24')
            esx['vms'].append({'name': o['name'], 'mac': o['mac'].upper().replace('-', ':'), 'ip': o['ip'], 'gw': o.get('gw', ''),
                               'network': o.get('network', ''), 'silent': bool(o.get('silent'))})
            return
        raise AciError(400, 'Unbekannter Typ')

    def state(self):
        e = self.engine
        topo = self.sim['topology']
        nodes = []
        for n in topo['nodes']:
            nid = e.serial_node.get(n['serial'])
            info = e.nodes.get(nid, {})
            nodes.append({'serial': n['serial'], 'model': n['model'], 'role': n['role'], 'ports': n['ports'],
                          'id': nid, 'name': info.get('name'), 'tep': info.get('tep'),
                          'state': info.get('state') or ('pending' if any(p['serial'] == n['serial']
                                                                         for p in e.pending) else 'undiscovered'),
                          'since': info.get('since'), 'upgrading': bool(info.get('upgrading')),
                          'pod': n.get('pod', topo.get('pod', 1)), 'remote': bool(n.get('remote')),
                          'why': getattr(e, 'mp', {}).get('reasons', {}).get(n['serial']),
                          'version': ops.plain(e.node_version(n['serial']))})
        hosts = []
        for h in self.sim['hosts']:
            hs = e.hosts.get(h['name'], {})
            lease = self.sim.get('leases', {}).get(h['name']) if h.get('dhcp') else None
            hosts.append(dict(h, ip=lease['ip'] if lease else h['ip'], status={'learned': hs.get('learned', False), 'ipLearned': hs.get('ipLearned'), 'quiet': hs.get('quiet', False),
                                         'dhcp': getattr(e, 'dhcp_info', {}).get(h['name']), 'storm': hs.get('storm'),
                                         'epg': hs.get('epg'), 'reasons': hs.get('reasons', []),
                                         'path': hs.get('path'), 'encap': hs.get('encap')}))
        routers = []
        for r in self.sim['routers']:
            rs = e.routers.get(r['name'], {})
            routers.append(dict(r, status={'link': rs.get('link'), 'adj': rs.get('adj'),
                                           'adjs': [{'node': e.nodes[a['nid']]['name'], 'state': a['state']} for a in rs.get('adjs', [])],
                                           'bfd': [{'node': e.nodes[b['nid']]['name'], 'state': b['state']} for b in rs.get('bfd', [])],
                                           'reasons': rs.get('reasons', []), 'learned': rs.get('learned', []),
                                           'iface': rs.get('iface', {}).get('dn') if rs.get('iface') else None}))
        vmm = [{'dn': d, 'name': v['name'], 'state': v['state'], 'reasons': v['reasons'], 'vc': v['vc'],
                'discovery': v['discovery'], 'pgs': [dict(g, epg=k) for k, g in v['pgs'].items()],
                'hosts': v['hosts']} for d, v in getattr(e, 'vmm', {}).items()]
        vms = {h['name']: {'learned': e.hosts.get(h['name'], {}).get('learned', False),
                           'epg': e.hosts.get(h['name'], {}).get('epg'),
                           'reasons': e.hosts.get(h['name'], {}).get('reasons', [])} for h in getattr(e, 'vm_hosts', [])}
        sev = {}
        for d in self.store.by_class('faultInst'):
            s = self.store.attrs(d)['severity']
            sev[s] = sev.get(s, 0) + 1
        lab = self.lab(self.sim.get('lab')) if self.sim.get('lab') else None
        return {'now': time.time(), 'apic': topo['apic'], 'pod': topo.get('pod', 1), 'setup': self.sim.get('setup'), 'nodes': nodes, 'links': topo['links'],
                'ipnlinks': topo.get('ipnlinks', []), 'multipod': bool(topo.get('ipnlinks')),
                'pending': e.pending, 'hosts': hosts, 'routers': routers, 'settings': self.sim['settings'],
                'faults': sev, 'vpc': e.vpc_groups, 'mpbgp': e.mpbgp_ok,
                'vcenters': [dict(v, pwd='***') for v in self.sim.get('vcenters', [])], 'vmm': vmm, 'vms': vms,
                'devices': [dict(d, status={i['name']: {k: e.hosts.get('%s:%s' % (d['name'], i['name']), {}).get(k)
                                                        for k in ('learned', 'epg', 'reasons')} for i in d.get('ifs', [])})
                            for d in self.sim.get('devices', [])],
                'tracks': {d: e._alive(e.A(d)['dstIpAddr']) if e.A(d)['dstIpAddr'] else False
                           for d in self.store.by_class('fvTrackMember')},
                'switches': [dict(sw, status=next(({'loop': l['loop'], 'text': l['text'], 'action': l['action'], 'bds': l['bds'],
                                                     'tags': [str(t) for t in l['tags']],
                                                     'victim': '%s %s' % (e.nodes[l['victim'][0]]['name'], l['victim'][1]) if l.get('victim') else None}
                                                    for l in getattr(e, 'loops', []) if l['name'] == sw['name']), {}))
                             for sw in self.sim.get('switches', [])],
                'apicUpgrade': bool(getattr(e, 'apic_upgrade', None)), 'apicVersion': getattr(e, 'apic_version', ''),
                'downloads': self.sim.get('downloads', {}), 'jobs': self.sim.get('jobs', [])[-30:],
                'upgrading': any(not u.get('done') for u in self.sim.get('upgrades', [])),
                'graphs': [{k: g[k] for k in ('dn', 'brc', 'graph', 'state', 'reasons', 'node', 'dev')}
                           for g in getattr(e, 'graphs', {}).values()],
                'lab': self.lab_public(lab),
                'nextEvent': e.next_event}


def meta_json():
    out = {}
    for name, m in CLASSES.items():
        out[name] = {'rn': m.rn, 'naming': m.naming, 'label': m.label, 'parents': list(m.parents),
                     'attrs': {k: v for k, v in m.attrs.items() if k not in m.ro},
                     'ro': sorted(m.ro), 'enums': {k: list(v) for k, v in m.enums.items()},
                     'sets': {k: list(v) for k, v in m.sets.items()}, 'config': m.config,
                     'rel': list(m.rel) if m.rel else None}
    return out


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------

def make_handler(hub):
    S = SimProxy()

    class H(BaseHTTPRequestHandler):
        server_version = 'Datacenter Prep'
        protocol_version = 'HTTP/1.1'

        def log_message(self, fmt, *args):
            if os.environ.get('DCPREP_LOG'):
                super().log_message(fmt, *args)

        # ---------------------------------------------------------- Ausgabe
        def send(self, code, body, ctype='application/json', headers=None):
            data = body if isinstance(body, (bytes, bytearray)) else (
                json.dumps(body).encode() if ctype == 'application/json' else str(body).encode())
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)

        def err(self, e):
            self.send(e.status if isinstance(e.status, int) and e.status >= 400 else 400,
                      {'totalCount': '1', 'imdata': [{'error': {'attributes': {'code': e.code, 'text': e.text}}}]})

        def cookies(self):
            c = {}
            for part in (self.headers.get('Cookie') or '').split(';'):
                if '=' in part:
                    k, v = part.strip().split('=', 1)
                    c[k] = v
            return c

        def body(self):
            n = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(n) if n else b''
            if not raw:
                return {}
            try:
                return json.loads(raw.decode('utf-8'))
            except ValueError:
                if raw.strip().startswith(b'<'):
                    raise AciError(400, 'XML wird vom Simulator nicht unterstuetzt - bitte JSON verwenden')
                raise AciError(400, 'Malformed JSON body')

        # ---------------------------------------------------------- Routing
        def do_GET(self):
            self.route('GET')

        def do_POST(self):
            self.route('POST')

        def do_DELETE(self):
            self.route('DELETE')

        def do_HEAD(self):
            self.route('GET')

        def route(self, method):
            u = urlparse(self.path)
            path = unquote(u.path)
            q = parse_qs(u.query, keep_blank_values=True)
            try:
                if path.startswith('/dp/'):
                    return self.dp(method, path[4:])
                if path == '/sim/meta':
                    return self.send(200, meta_json())
                if path.startswith('/api/') or path.startswith('/sim/'):
                    self.dpuser = hub.resolve(self.cookies(), self.headers, self.client_address[0])
                    S.bind(hub.sim(self.dpuser))
                    if path.startswith('/api/'):
                        return self.api(method, path[5:], q)
                    return self.simapi(method, path[5:], q)
                return self.static(path)
            except AciError as e:
                return self.err(e)
            except (BrokenPipeError, ConnectionResetError):
                return None
            except Exception as e:  # noqa
                import traceback
                traceback.print_exc()
                return self.err(AciError(500, 'Interner Fehler: %s' % e, 500))

        def static(self, path):
            if path in ('/', ''):
                path = '/index.html'
            if path == '/visore.html':
                path = '/visore.html'
            fp = os.path.normpath(os.path.join(STATIC, path.lstrip('/')))
            if not fp.startswith(STATIC) or not os.path.isfile(fp):
                return self.send(404, 'Not found', 'text/plain')
            with open(fp, 'rb') as f:
                data = f.read()
            ctype = mimetypes.guess_type(fp)[0] or 'application/octet-stream'
            if ctype.startswith('text/') or ctype in ('application/javascript',):
                ctype += '; charset=utf-8'
            self.send(200, data, ctype)

        # ---------------------------------------------------------- Benutzer (Datacenter Prep)
        def dp(self, method, rest):
            ck = self.cookies()
            me = hub.session_user(ck.get(DP_COOKIE))
            b = self.body() if method == 'POST' else {}
            clear = '%s=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax' % DP_COOKIE
            if rest == 'users':
                if method == 'POST':
                    res = hub.op(me, b)
                    gone = b.get('op') == 'delete' and (b.get('name') or me) == me
                    return self.send(200, res, headers={'Set-Cookie': clear} if gone else None)
                return self.send(200, {'users': hub.listing(), 'me': me, 'admin': hub.is_admin(me),
                                       'openSignup': hub.data.get('openSignup', True)})
            if rest == 'login' and method == 'POST':
                tok, name = hub.login(b.get('name'), b.get('password'))
                return self.send(200, {'user': name}, headers={'Set-Cookie': '%s=%s; Path=/; Max-Age=%d; HttpOnly; SameSite=Lax'
                                                                            % (DP_COOKIE, tok, SESSION_DAYS * 86400)})
            if rest == 'logout' and method == 'POST':
                hub.logout(ck.get(DP_COOKIE))
                return self.send(200, {'ok': True}, headers={'Set-Cookie': clear})
            if rest == 'me':
                return self.send(200, {'user': me, 'admin': hub.is_admin(me)})
            raise AciError(404, 'Unbekannt: /dp/%s' % rest, 404)

        def auth(self):
            with S.lock:
                user, tok = S.check(self.cookies(), self.headers)
            if not user:
                raise AciError(403, 'Token was invalid (Error: Token timeout)', 403)
            return user, tok

        # ---------------------------------------------------------- APIC-API
        def api(self, method, rest, q):
            fmt = 'json'
            m = re.match(r'^(.*)\.(json|xml)$', rest)
            if m:
                rest, fmt = m.group(1), m.group(2)
            if fmt == 'xml':
                raise AciError(400, 'XML wird vom Simulator nicht unterstuetzt - bitte .json verwenden')
            if rest in ('aaaLogin', 'requestAppToken'):
                b = self.body()
                a = (b.get('aaaUser') or {}).get('attributes') or {}
                with S.lock:
                    tok = S.login(a.get('name', ''), a.get('pwd', ''))
                return self.send(200, self._login_resp(tok, S.tokens[tok][0]),
                                 headers={'Set-Cookie': 'APIC-cookie=%s; path=/; HttpOnly' % tok})
            if rest == 'aaaRefresh':
                user, tok = self.auth()
                with S.lock:
                    if tok:
                        S.tokens[tok] = (user, time.time() + 3600) + tuple(S.tokens[tok][2:])
                return self.send(200, self._login_resp(tok or '', user),
                                 headers={'Set-Cookie': 'APIC-cookie=%s; path=/; HttpOnly' % tok} if tok else None)
            if rest == 'aaaLogout':
                c = self.cookies().get('APIC-cookie')
                with S.lock:
                    S.tokens.pop(c, None)
                return self.send(200, {'totalCount': '0', 'imdata': []})
            user, tok_ = self.auth()
            roles = S.roles_of(user, tok_)
            rest = re.sub(r'^node/', '', rest)
            m = re.match(r'^(mo|class)/?(.*)$', rest)
            if not m:
                raise AciError(400, 'Request failed, unknown API %s' % rest)
            kind, target = m.group(1), m.group(2)
            if kind == 'mo' and target == '':
                target = ''
            with S.lock:
                S.tick()
                if method == 'GET':
                    res, total = run_query(S.store, kind, target, q, S.engine)
                    if 'rsp-prop-include' in q and q['rsp-prop-include'][0] == 'config-only':
                        res = [_strip_oper(S.store, r) for r in res]
                    if not aaa.is_admin(roles):
                        n0 = len(res)
                        res = [x for x in (_rbac_filter(S.store, roles, r) for r in res) if x is not None]
                        total = int(total) - (n0 - len(res))
                    return self.send(200, {'totalCount': str(total), 'imdata': res})
                if kind != 'mo':
                    raise AciError(400, 'POST/DELETE only on /api/mo')
                up = getattr(S.engine, 'apic_upgrade', None)
                if up:
                    pct = int((time.time() - up['start']) * 100 / max(up['dur'], 1))
                    raise AciError(503, 'APIC-Upgrade auf %s laeuft (%d%%) - der Controller nimmt bis zum Abschluss keine '
                                   'Konfiguration an' % (ops.plain(up['version']), min(pct, 99)), 503)
                if method == 'POST':
                    b = self.body()
                    backup = S.store.backup()
                    ch = mit_post(S.store, target, b)
                    bad = [c['dn'] for c in ch if not aaa.can_write(S.store, roles, c['dn'])]
                    if bad and not aaa.is_admin(roles):
                        S.store.restore(backup)
                        raise AciError(403, 'Access denied (RBAC): Benutzer %s hat kein Schreibrecht auf %s (Rollen: %s)'
                                       % (user, bad[0], aaa.describe(roles) or 'keine'), 403)
                    S.audit(user, ch)
                    S.rebuild()
                    ops.run_triggers(S, user)
                    S.changed()
                    return self.send(200, {'totalCount': '0', 'imdata': []})
                if method == 'DELETE':
                    if not aaa.can_write(S.store, roles, target):
                        raise AciError(403, 'Access denied (RBAC): Benutzer %s hat kein Schreibrecht auf %s' % (user, target), 403)
                    S.audit(user, mit_delete(S.store, target))
                    S.changed()
                    return self.send(200, {'totalCount': '0', 'imdata': []})
            raise AciError(400, 'Method not supported')

        def _login_resp(self, tok, user):
            return {'totalCount': '1', 'imdata': [{'aaaLogin': {'attributes': {
                'token': tok, 'siteFingerprint': 'simulator', 'refreshTimeoutSeconds': '600',
                'maximumLifetimeSeconds': '86400', 'guiIdleTimeoutSeconds': '1200',
                'restTimeoutSeconds': '90', 'creationTime': str(int(time.time())), 'firstLoginTime': str(int(time.time())),
                'userName': user, 'remoteUser': 'false', 'unixUserId': '15374', 'sessionId': tok[:20],
                'lastName': '', 'firstName': '', 'changePassword': 'no', 'version': '6.0(5h)',
                'buildTime': 'Simulator', 'node': 'topology/pod-1/node-1'},
                'children': [{'aaaUserDomain': {'attributes': {'name': 'all', 'rolesR': 'admin',
                                                               'rolesW': 'admin'}}}]}}]}

        # ---------------------------------------------------------- Sim-API
        def simapi(self, method, rest, q):
            if rest == 'meta':
                return self.send(200, meta_json())
            if rest == 'setup':
                with S.lock:
                    if method == 'GET':
                        return self.send(200, {'done': S.sim.get('setup', 0) is not None,
                                               'questions': apic_setup.QUESTIONS, 'notes': apic_setup.NOTES,
                                               'serial': S.sim['topology']['apic']['serial'],
                                               'lab': {k: (S.lab(S.sim['lab']) or {}).get(k) for k in ('title', 'intro')}
                                               if S.sim.get('lab') else None})
                    b = self.body()
                    if b.get('check'):
                        a = apic_setup.normalize(b.get('answers') or {})
                        v = b.get('value') or ''
                        return self.send(200, {'error': apic_setup.validate(b['check'], v, a)})
                    if b.get('summary'):
                        return self.send(200, {'text': apic_setup.summary(apic_setup.normalize(b.get('answers') or {}))})
                    S.setup_apply(b.get('answers') or {})
                    return self.send(200, {'ok': True})
            if rest == 'logindomains':
                with S.lock:
                    return self.send(200, sorted(S.store.attrs(d)['name'] for d in S.store.by_class('aaaLoginDomain')))
            user, tok_ = self.auth()
            if method == 'POST' and rest not in ('traffic', 'cli', 'labs/check', 'labs/hint', 'labs/answer'):
                with S.lock:
                    if not aaa.is_admin(S.roles_of(user, tok_)):
                        raise AciError(403, 'Access denied: Die Simulation darf nur ein Benutzer mit admin-Rolle in der Domain all aendern', 403)
            with S.lock:
                S.tick()
                b = self.body() if method == 'POST' else {}
                e = S.engine
                if rest == 'state':
                    return self.send(200, S.state())
                if rest == 'sessions':
                    return self.send(200, [{'user': v[0], 'since': v[2], 'expires': int(v[1] - time.time()),
                                            'id': k[:12]} for k, v in S.tokens.items() if v[1] > time.time()])
                if rest == 'stats':
                    return self.send(200, e.stats)
                if rest == 'oper':
                    return self.send(200, oper_info(S, (q.get('dn') or [''])[0]))
                if rest == 'capacity':
                    return self.send(200, capacity_info(S))
                if rest == 'nodeinfo':
                    return self.send(200, node_info(S, int((q.get('id') or ['0'])[0])))
                if rest == 'ntp':
                    return self.send(200, {'pgrp': e.ntp['pgrp'], 'pol': e.ntp['pol'], 'provs': e.ntp['provs'],
                                           'nodes': {str(k): v for k, v in e.ntp['nodes'].items()}})
                if rest == 'traffic':
                    r = trace.run(e, S.sim, b.get('src'), b.get('dst'), b.get('proto', 'icmp'), b.get('port', 0))
                    new = [n for n in r.pop('woken', []) if n not in S.sim.setdefault('woken', [])]
                    if new:
                        S.sim['woken'].extend(new)
                        S.changed()
                    return self.send(200, r)
                if rest == 'cli':
                    cli = Cli(e, S.sim)
                    out = cli.run(b.get('node', 'apic1'), b.get('cmd', ''))
                    if cli.request == 'factory':
                        S.reset('factory', keep_sim=True)
                        S.save()
                        return self.send(200, {'output': out, 'reboot': True})
                    if cli.request == 'changed':
                        S.changed()
                    elif S.sim.get('touch_clean'):
                        S.save()
                    return self.send(200, {'output': out})
                if rest == 'hosts':
                    if b.get('op') == 'bulk':
                        n = S.bulk_hosts(b.get('csv'), b.get('replace'))
                        S.changed()
                        return self.send(200, {'ok': True, 'added': n})
                    if b.get('op') == 'delete':
                        S.sim['hosts'] = [h for h in S.sim['hosts'] if h['name'] != b.get('name')]
                    else:
                        S.set_host(b.get('host') or {}, b.get('old'))
                    S.changed()
                    return self.send(200, {'ok': True})
                if rest == 'aaaservers':
                    if method == 'POST':
                        S.aaa_server_op(b)
                        S.changed()
                    return self.send(200, [dict(x, key='***' if x.get('key') else '', users=[dict(u, pwd='***') for u in x.get('users', [])])
                                           for x in S.sim.get('aaa', [])])
                if rest == 'logins':
                    return self.send(200, list(reversed(S.sim.get('logins', [])))[:100])
                if rest == 'whoami':
                    roles = S.roles_of(user, tok_)
                    return self.send(200, {'user': user, 'roles': roles, 'admin': aaa.is_admin(roles),
                                           'how': S.tokens[tok_][4] if tok_ and len(S.tokens.get(tok_, ())) > 4 else 'lokal'})
                if rest == 'devices':
                    S.device_op(b)
                    S.changed()
                    return self.send(200, {'ok': True})
                if rest == 'coverage':
                    return self.send(200, coverage.report(S.store, (q.get('dn') or [''])[0]))
                if rest == 'flows':
                    if method == 'POST':
                        if b.get('op') == 'matrix':
                            return self.send(200, flows.matrix(S, b.get('src'), b.get('dst'), b.get('proto', 'icmp'), b.get('port', 0)))
                        res = flows.expect_op(S, b)
                        S.save()
                        if res:
                            return self.send(200, dict(res, expect=S.sim.get('expect', [])))
                    return self.send(200, dict(S.sim.get('expect_last') or {'results': []}, expect=S.sim.get('expect', [])))
                if rest == 'topology':
                    out = None
                    if method == 'POST':
                        out = S.topology_op(b)
                        S.changed()
                    return self.send(200, {'spec': S.sim['topology'].get('spec') or {'pods': [{'spines': 2, 'leafs': 4}], 'remote': 0},
                                           'kind': S.sim['topology'].get('kind', 'default'), 'limits': LIMITS, 'result': out})
                if rest == 'ipn':
                    if method == 'POST':
                        S.ipn_op(b)
                        S.changed()
                    mp = getattr(e, 'mp', {})
                    return self.send(200, {'config': S.sim.get('ipn'), 'active': mp.get('active', False),
                                           'adj': [{k: v for k, v in a.items()} for a in mp.get('adj', [])],
                                           'reasons': mp.get('reasons', {}), 'ipnOk': {str(k): v for k, v in mp.get('ipn_ok', {}).items()},
                                           'pools': {str(k): v for k, v in mp.get('pools', {}).items()},
                                           'remote': {str(k): v for k, v in mp.get('remote', {}).items()},
                                           'apicTep': e.apic_tep, 'links': S.sim['topology'].get('ipnlinks', []),
                                           'interpod': e.interpod(1, 2) if mp.get('active') else None})
                if rest == 'ndo':
                    if method == 'POST':
                        try:
                            msite.ndo_op(S, b)
                        finally:
                            S.changed()
                    n = S.sim.get('ndo')
                    return self.send(200, {'ndo': n, 'state': e.msite_state() if n else None,
                                           'isn': [a for a in getattr(e, 'mp', {}).get('adj', []) if a['kind'] == 'isn']})
                if rest == 'switches':
                    S.switch_op(b)
                    S.changed()
                    return self.send(200, {'ok': True})
                if rest == 'monitors':
                    out = None
                    if method == 'POST':
                        out = S.monitor_op(b)
                        if b.get('op') == 'walk':
                            return self.send(200, out)
                        S.changed()
                    return self.send(200, {'monitors': S.sim.get('monitors', []), 'log': S.sim.get('monlog', {}),
                                           'dests': [{k: v for k, v in d.items() if k not in ('mgmt', 'incl')} for d in getattr(e, 'mon', [])],
                                           'snmpPol': e.snmp_pol})
                if rest == 'fileserver':
                    if method == 'POST':
                        S.fileserver_op(b)
                        S.changed()
                    fs = ops.fileserver(S)
                    return self.send(200, dict({k: v for k, v in fs.items() if k != 'files'}, pwd=fs['pwd'],
                                               files=[{'path': k, 'size': v.get('size'), 'image': bool(v.get('image')),
                                                       'export': bool(v.get('export')), 'created': (v.get('export') or {}).get('created'),
                                                       'secure': (v.get('export') or {}).get('secure'),
                                                       'target': (v.get('export') or {}).get('target'),
                                                       'objects': len((v.get('export') or {}).get('rows', []))}
                                                      for k, v in sorted(fs['files'].items())]))
                if rest == 'firmware':
                    now = time.time()
                    ups = [dict(u, pct=100 if u.get('done') else int(min(99, (now - u['start']) * 100 / max(u['dur'], 1))),
                                left=max(0, int(u['start'] + u['dur'] - now))) for u in S.sim.get('upgrades', [])[-20:]]
                    vers = [{'id': 1, 'name': S.sim['topology']['apic']['name'], 'role': 'controller', 'version': e.apic_version,
                             'state': 'upgrading' if e.apic_upgrade else 'active'}]
                    for nid, n in sorted(e.nodes.items()):
                        vers.append({'id': nid, 'name': n['name'], 'role': n['role'], 'version': ops.plain(e.node_version(n['serial'])),
                                     'state': 'upgrading' if n.get('upgrading') else n['state']})
                    return self.send(200, {'repo': S.sim.get('fwrepo', []), 'downloads': S.sim.get('downloads', {}),
                                           'log': list(reversed(S.sim.get('fwlog', [])))[:50], 'upgrades': list(reversed(ups)),
                                           'groups': getattr(e, 'fw_groups', []), 'nodes': vers})
                if rest == 'jobs':
                    return self.send(200, list(reversed(S.sim.get('jobs', []))))
                if rest == 'vcenters':
                    S.vcenter_op(b)
                    S.changed()
                    return self.send(200, {'ok': True})
                if rest == 'routers':
                    if b.get('op') == 'delete':
                        S.sim['routers'] = [r for r in S.sim['routers'] if r['name'] != b.get('name')]
                    else:
                        S.set_router(b.get('router') or {}, b.get('old'))
                    S.changed()
                    return self.send(200, {'ok': True})
                if rest == 'settings':
                    v = float(b.get('discoverySeconds', S.sim['settings'].get('discoverySeconds', 20)))
                    S.sim['settings']['discoverySeconds'] = max(0.0, min(v, 600.0))
                    u = float(b.get('upgradeSeconds', S.sim['settings'].get('upgradeSeconds', 60)))
                    S.sim['settings']['upgradeSeconds'] = max(5.0, min(u, 1800.0))
                    S.changed()
                    return self.send(200, {'ok': True})
                if rest == 'labs':
                    prog, saves = S.progress(), S.saves()
                    out = []
                    for l in S.labs():
                        row = {k: l.get(k) for k in ('id', 'title', 'level', 'duration', 'goals', 'topic', 'fabric', 'kind')}
                        row['modes'] = l.get('modes') or ['guided']
                        row['progress'] = prog.get(l['id'])
                        row['saves'] = [x for x in saves if x.get('lab') == l['id']]
                        row['auto'] = S.auto_name(l['id'])
                        out.append(row)
                    if q.get('full'):
                        return self.send(200, {'labs': out, 'current': S.sim.get('lab'), 'auto': S.auto_name(None),
                                               'free': [x for x in saves if not x.get('lab')]})
                    return self.send(200, out)
                if rest == 'labs/op':
                    return self.send(200, S.lab_op(b))
                if rest == 'labs/load':
                    lab = S.load_lab(b.get('id'), mode=b.get('mode'))
                    return self.send(200, {'ok': True, 'title': lab['title']})
                if rest == 'labs/check':
                    return self.send(200, S.check_lab() or {'checks': []})
                if rest == 'labs/hint':
                    return self.send(200, S.lab_hint(b.get('level', 1)))
                if rest == 'labs/answer':
                    return self.send(200, S.lab_answer(b.get('id'), b.get('choice')))
                if rest == 'reset':
                    S.reset(b.get('mode', 'discovered'))
                    S.save()
                    return self.send(200, {'ok': True})
                if rest == 'saves':
                    if method == 'POST':
                        op = b.get('op')
                        if op == 'save':
                            S.save_game(b.get('name'), b.get('descr', ''))
                        elif op == 'load':
                            S.load_blob(S.read_save(b.get('name')))
                        elif op == 'delete':
                            fn = S._save_file(b.get('name'))
                            if os.path.exists(fn):
                                os.remove(fn)
                        elif op == 'upload':
                            data = b.get('data')
                            S._check_blob(data)
                            fn = S._save_file(b.get('name'))
                            with open(fn, 'w', encoding='utf-8') as f:
                                json.dump(data, f)
                        elif op == 'resume':
                            lid = b.get('lab')
                            if S.sim.get('lab') != lid:
                                S.autosave_lab()
                            S.load_blob(S.read_save(('auto-' + lid)[:32]))
                        else:
                            raise AciError(400, 'Unbekannte Aktion')
                    return self.send(200, S.saves())
                if rest == 'saves/download':
                    name = (q.get('name') or [''])[0]
                    blob = S.save_blob('Aktueller Zustand') if name in ('', '_current') else S.read_save(name)
                    fname = 'datacenter-prep-%s.json' % (name if name not in ('', '_current') else
                                                         (blob.get('lab') or 'zustand') + '-' + time.strftime('%Y%m%d-%H%M'))
                    return self.send(200, json.dumps(blob).encode(), 'application/json',
                                     headers={'Content-Disposition': 'attachment; filename="%s"' % fname})
                if rest == 'snapshots':
                    if method == 'POST':
                        S.snapshot(b.get('op'), b.get('name'), b.get('descr', ''))
                    return self.send(200, S.snapshots())
            raise AciError(404, 'Unknown simulator API %s' % rest, 404)

    return H


def oper_info(S, dn):
    """Operative Daten fuer die Tabs Operational/Stats/Health eines Objekts."""
    e, st = S.engine, S.store
    o = st.objs.get(dn)
    if not o:
        raise AciError(404, 'Objekt %s nicht gefunden' % dn, 404)
    cls = o[0]
    res = {'health': e.score(dn), 'deployed': [], 'endpoints': [], 'contracts': [], 'neighbors': [], 'routes': [],
           'stats': {}}
    for d, v in e.stats.items():
        if d == dn or d.startswith(dn + '/'):
            for k, n in v.items():
                res['stats'][k] = res['stats'].get(k, 0) + n
    res['statsRows'] = [{'dn': d, **v} for d, v in sorted(e.stats.items()) if d == dn or d.startswith(dn + '/')]

    def ep_rows(epgs):
        out = []
        for h in e.all_hosts():
            hs = e.hosts.get(h['name'], {})
            if hs.get('learned') and hs.get('epg') in epgs:
                out.append({'name': h['name'], 'mac': h['mac'].upper(), 'ip': str(ip_of(h['ip'])) if hs.get('ipLearned') else '',
                            'encap': hs.get('encap'), 'path': hs.get('path'), 'epg': hs.get('epg'),
                            'src': 'learned,vmm' if h.get('vm') else 'learned',
                            'nodes': [e.nodes[n]['name'] for n in hs.get('nodes', [])]})
        return out
    if cls == 'fvAEPg':
        for d in e.deploys:
            if d['epg'] == dn:
                for n in d['nodes']:
                    res['deployed'].append({'node': e.nodes[n]['name'], 'id': n, 'path': d['path'], 'encap': 'vlan-%d' % d['vlan'],
                                            'mode': d['mode'], 'state': 'deployed'})
        res['endpoints'] = ep_rows({dn})
        c = e.cls.get(dn, {})
        for role, key in (('Provider', 'prov'), ('Consumer', 'cons')):
            for brc in c.get(key, []):
                res['contracts'].append({'role': role, 'contract': brc, 'scope': st.attrs(brc)['scope']})
        for t in e._rs_targets(dn, 'fvRsProtBy'):
            res['contracts'].append({'role': 'Taboo', 'contract': t, 'scope': '-'})
    elif cls == 'fvBD':
        res['deployed'] = [{'node': e.nodes[n]['name'], 'id': n, 'state': 'deployed'} for n in sorted(e.dep_bd) if dn in e.dep_bd[n]]
        res['endpoints'] = ep_rows({d for d, c in e.cls.items() if c.get('bd') == dn})
    elif cls == 'fvCtx':
        res['deployed'] = [{'node': e.nodes[n]['name'], 'id': n, 'state': 'deployed'} for n in sorted(e.dep_vrf) if dn in e.dep_vrf[n]]
        res['endpoints'] = ep_rows({d for d, c in e.cls.items() if c.get('vrf') == dn})
    elif cls == 'l3extOut':
        out = e.outs.get(dn)
        for r in S.sim.get('routers', []):
            rs = e.routers.get(r['name'], {})
            i = rs.get('iface')
            if i and i['out'] == dn:
                res['neighbors'].append({'name': r['name'], 'node': e.nodes[i['nid']]['name'], 'iface': e.if_name(i),
                                         'proto': r.get('protocol'), 'ip': str(ip_of(r['ip'])), 'state': rs.get('adj'),
                                         'learned': rs.get('learned', [])})
        if out:
            for nid in out['nodes']:
                for rt in e.routes.get((out['vrf'], nid), []):
                    res['routes'].append(dict(rt, node=e.nodes.get(nid, {}).get('name', nid)))
    elif cls == 'fvTenant':
        res['endpoints'] = ep_rows({d for d, c in e.cls.items() if c.get('tenant') == dn})
    elif cls == 'mgmtInB':
        info = next((i for i in getattr(e, 'inb_info', []) if i['dn'] == dn), {})
        res['inb'] = {'reasons': info.get('reasons', []), 'ports': info.get('ports', []),
                      'nodes': [{'node': e.nodes[n]['name'] if n in e.nodes else 'apic1' if n == 1 else str(n), 'why': w}
                                for n, w in sorted(info.get('nodes', {}).items())]}
    elif cls == 'fvESg':
        res['endpoints'] = [r for r in ep_rows(set(e.cls)) if e.hosts.get(r['name'], {}).get('esg') == dn]
        res['contracts'] = [{'contract': c, 'role': k, 'scope': (e.A(c) or {}).get('scope')} for k in ('prov', 'cons') for c in e.cls[dn][k]] if dn in e.cls else []
    elif cls == 'vmmDomP':
        v = e.vmm.get(dn, {})
        res['vmm'] = {'state': v.get('state'), 'reasons': v.get('reasons', []), 'vc': v.get('vc'), 'discovery': v.get('discovery'),
                      'pgs': [dict(g, epg=k) for k, g in v.get('pgs', {}).items()], 'hosts': v.get('hosts', [])}
        res['endpoints'] = ep_rows(set(v.get('pgs', {})))
        res['deployed'] = [{'node': e.nodes[n]['name'], 'id': n, 'path': d['path'], 'encap': 'vlan-%d' % d['vlan'],
                            'state': 'deployed', 'epg': d['epg']} for d in e.deploys if d['epg'] in v.get('pgs', {}) for n in d['nodes']]
    elif cls == 'l2extOut':
        insts = set(st.children(dn, 'l2extInstP'))
        res['endpoints'] = ep_rows(insts)
        res['deployed'] = [{'node': e.nodes[n]['name'], 'id': n, 'path': d['path'], 'encap': 'vlan-%d' % d['vlan'],
                            'state': 'deployed'} for d in e.deploys if d['epg'] in insts for n in d['nodes']]
    return res


def capacity_info(S):
    e = S.engine
    from .cli import Cli
    cli = Cli(e, S.sim)
    rows = []
    for nid in sorted(e.nodes):
        n = e.nodes[nid]
        if n['role'] != 'leaf' or n['state'] != 'active':
            continue
        eps = sum(1 for h in e.hosts.values() if h.get('learned') and nid in h.get('nodes', []))
        rules = cli.zoning(nid, None).count('\n|') - 1 if e.dep_vrf.get(nid) else 0
        routes = sum(len(r) for (v, x), r in e.routes.items() if x == nid) + \
            sum(len(e.bd_subnets(b)) for b in e.dep_bd.get(nid, set()))
        rows.append({'node': n['name'], 'id': nid, 'vlans': len(e.leaf_vlans.get(nid, {})) + len(e.dep_bd.get(nid, set())),
                     'vlansMax': 3960, 'endpoints': eps, 'endpointsMax': 24576, 'rules': max(0, rules), 'rulesMax': 65536,
                     'routes': routes, 'routesMax': 20000, 'vrfs': len(e.dep_vrf.get(nid, set())), 'vrfsMax': 800})
    st = S.store
    fabric = {k: len(st.by_class(c)) for k, c in (('tenants', 'fvTenant'), ('vrfs', 'fvCtx'), ('bds', 'fvBD'), ('epgs', 'fvAEPg'),
                                                   ('contracts', 'vzBrCP'), ('l3outs', 'l3extOut'), ('endpoints', 'fvCEp'))}
    return {'leafs': rows, 'fabric': fabric}


def node_info(S, nid):
    e = S.engine
    from .cli import Cli
    n = e.nodes.get(nid)
    if not n:
        raise AciError(404, 'Node %d nicht gefunden' % nid, 404)
    cli = Cli(e, S.sim)
    lldp = [{'local': lp, 'device': dev, 'port': rp, 'cap': cap} for lp, dev, rp, cap, _ in e.lldp.get(nid, [])]
    for (k, port), peer in e.cabled.items():
        if k == nid:
            lldp.append({'local': port, 'device': peer[1], 'port': 'eth0' if peer[0] == 'host' else 'Gi0/0',
                         'cap': 'S' if peer[0] == 'host' else 'R'})
    po = cli._po_ids(nid)
    pcs = []
    for dn, idx in sorted(po.items(), key=lambda x: x[1]):
        p = e.paths[dn]
        legs = [l for l in p['legs'] if l[0] == nid]
        pcs.append({'id': 'po%d' % idx, 'name': p['name'], 'type': p['type'], 'path': dn,
                    'members': [{'port': l[1], 'state': e.ports.get(l, {}).get('qual')} for l in legs],
                    'lacp': e._pg_info(p['pg'])['lacp']})
    nbrs = []
    for r in S.sim.get('routers', []):
        rs = e.routers.get(r['name'], {})
        i = rs.get('iface')
        if i and i['nid'] == nid:
            nbrs.append({'name': r['name'], 'proto': r.get('protocol'), 'ip': str(ip_of(r['ip'])), 'state': rs.get('adj'),
                         'iface': e.if_name(i), 'vrf': e.outs[i['out']]['vrf']})
    return {'node': {k: n[k] for k in ('id', 'name', 'role', 'model', 'serial', 'state', 'tep')},
            'oob': e.oob.get(nid, ''), 'ntp': e.ntp['nodes'].get(nid, 'n/a') if n['state'] == 'active' else 'n/a',
            'lldp': sorted(lldp, key=lambda x: (len(x['local']), x['local'])), 'pcs': pcs, 'neighbors': nbrs,
            'vpc': next((g for g in e.vpc_groups if nid in g['nodes']), None),
            'oos': sorted(t for t in e.oos if e.paths.get(t, {}).get('nodes') and nid in e.paths[t]['nodes'])}


def _rbac_filter(store, roles, node):
    cls = next(iter(node))
    body = node[cls]
    dn = (body.get('attributes') or {}).get('dn')
    if dn and dn not in ('uni', 'topology', '') and not aaa.can_read(store, roles, dn):
        return None
    if body.get('children'):
        body['children'] = [x for x in (_rbac_filter(store, roles, c) for c in body['children']) if x is not None]
    return node


def _strip_oper(store, node):
    cls = next(iter(node))
    body = node[cls]
    if 'children' in body:
        kids = []
        for ch in body['children']:
            c = next(iter(ch))
            dn = ch[c]['attributes'].get('dn')
            if c in ('faultInst', 'healthInst') or (dn in store.objs and store.objs[dn][2]):
                continue
            kids.append(_strip_oper(store, ch))
        body['children'] = kids
        if not kids:
            del body['children']
    return node


def ensure_cert(data_dir):
    crt, key = os.path.join(data_dir, 'dcprep.crt'), os.path.join(data_dir, 'dcprep.key')
    if not (os.path.exists(crt) and os.path.exists(key)):
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '3650',
                        '-subj', '/CN=dcprep', '-keyout', key, '-out', crt],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return crt, key


def serve(host, port, data_dir, admin_pwd, https=False, discovery=20):
    """Startet den Webserver. Rueckgabe (hub, httpd); hub verwaltet Benutzer und ihre Simulationen."""
    os.makedirs(data_dir, exist_ok=True)
    hub = Hub(data_dir, admin_pwd, discovery)
    httpd = ThreadingHTTPServer((host, port), make_handler(hub))
    httpd.daemon_threads = True
    if https:
        crt, key = ensure_cert(data_dir)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(crt, key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    return hub, httpd
