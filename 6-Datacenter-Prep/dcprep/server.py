"""HTTP-Server: APIC-REST-API, Simulator-API, Weboberflaeche."""
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

from . import model
from .model import AciError, CLASSES, rn_of, Store, post as mit_post, delete as mit_delete, now_ts
from .query import run_query
from .engine import Engine, ip_of
from . import setup as apic_setup
from .topology import default_topology, discovered_members, base_config, ensure_base
from .cli import Cli
from . import trace

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
                'settings': {'discoverySeconds': self.default_discovery}, 'lab': None,
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
        for k in ('settings', 'audit', 'events', 'seq'):
            if k in old:
                self.sim[k] = old[k]
        if keep_sim:
            for k in ('hosts', 'routers', 'vcenters'):
                if k in old:
                    self.sim[k] = old[k]
        if mode == 'factory':
            self.sim['setup'] = None
            self.sim['audit'], self.sim['events'] = [], []
            self.tokens.clear()
        self.engine = Engine(self.store, self.sim)
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

    def _event(self, affected, descr, sev='info', cause='transition', code='E4205125'):
        ev = self.sim.setdefault('events', [])
        ev.append({'id': self._next_id(), 'affected': affected, 'descr': descr, 'severity': sev, 'cause': cause,
                   'code': code, 'created': now_ts(), 'ind': 'state-transition', 'trig': 'oper', 'user': 'internal',
                   'changeSet': ''})
        del ev[:-2000]

    def rebuild(self):
        before = self._snap()
        self.engine.rebuild()
        after = self._snap()
        if not before:
            return
        n0 = len(self.sim.get('events', []))
        for nid, (name, state) in after['nodes'].items():
            if before['nodes'].get(nid, (None, None))[1] != state:
                self._event('topology/pod-%d/node-%d' % (self.engine.pod, nid), 'Node %s (%d) changed state to %s' % (name, nid, state),
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
                self._event(d.rsplit('/fault-', 1)[0], 'Fault %s raised: %s' % (code, descr), sev=sev, cause='fault-raised',
                            code='E4204886')
        for d, (code, sev, descr) in before['faults'].items():
            if d not in after['faults']:
                self._event(d.rsplit('/fault-', 1)[0], 'Fault %s cleared: %s' % (code, descr), cause='fault-cleared',
                            code='E4204887')
        if len(self.sim.get('events', [])) != n0:
            self.engine._history()

    def audit(self, user, changes):
        log = self.sim.setdefault('audit', [])
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
        u = self.store.attrs('uni/userext/user-%s' % name)
        if not u or u.get('pwd') != pwd or u.get('accountStatus') == 'inactive':
            return None
        tok = secrets.token_urlsafe(48)
        self.tokens[tok] = (name, time.time() + 3600, now_ts())
        return tok

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

    def load_lab(self, lid):
        lab = self.lab(lid)
        if not lab:
            raise AciError(404, 'Lab %s nicht gefunden' % lid)
        self.reset(lab.get('fabric', 'discovered'))
        for tree in lab.get('config', []):
            mit_post(self.store, 'uni', tree)
        self.sim['hosts'] = json.loads(json.dumps(lab.get('hosts', [])))
        self.sim['routers'] = json.loads(json.dumps(lab.get('routers', [])))
        self.sim['vcenters'] = json.loads(json.dumps(lab.get('vcenters', [])))
        self.sim['lab'] = lid
        self.changed()
        return lab

    def check_lab(self):
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
                    bad = next((s for s in r['steps'] if s['ok'] is False), None)
                    info = 'Ergebnis: %s%s' % ('erreichbar' if r['ok'] else 'blockiert',
                                               ' - ' + bad['title'] if bad else '')
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
                elif t == 'learned':
                    rs = e.routers.get(c['router'], {})
                    has = c['prefix'] in rs.get('learned', [])
                    ok = has == c.get('expect', True)
                    info = '%s kennt von der ACI: %s' % (c['router'], ', '.join(rs.get('learned', [])) or 'nichts')
                elif t == 'route':
                    v = 'uni/tn-%s/ctx-%s' % tuple(c['vrf'].split(':'))
                    has = any(r['prefix'] == c['prefix'] for r in e.routes.get((v, c['node']), []))
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
                    ok = rs.get('adj') == c.get('adj', 'FULL')
                    info = 'Zustand: %s' % rs.get('adj')
            except (KeyError, ValueError) as ex:
                info = 'Pruefung fehlerhaft: %s' % ex
            res.append({'desc': c['desc'], 'ok': bool(ok), 'info': info})
        return {'id': lab['id'], 'title': lab['title'], 'checks': res,
                'passed': sum(1 for r in res if r['ok']), 'total': len(res)}

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
                used[(r['serial'], r['port'])] = 'Router ' + r['name']
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
        names = {x['name'] for x in self.sim['hosts'] + self.sim['routers'] if x['name'] != (old or h['name'])}
        if h['name'] in names:
            raise AciError(400, 'Name %s ist bereits vergeben' % h['name'])
        if not MAC_RE.match(h.get('mac', '')):
            raise AciError(400, 'MAC-Adresse ungueltig (Format 00:50:56:00:00:01)')
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
        self.sim['woken'] = [n for n in self.sim.get('woken', []) if n != clean['name']]
        self.sim['hosts'] = [x for x in self.sim['hosts'] if x['name'] != (old or h['name'])] + [clean]

    def set_router(self, r, old=None):
        if not NAME_RE.match(r.get('name', '')):
            raise AciError(400, 'Name: 1-32 Zeichen, Buchstaben/Ziffern/._-')
        names = {x['name'] for x in self.sim['hosts'] + self.sim['routers'] if x['name'] != (old or r['name'])}
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
        self._check_port(r.get('serial'), r.get('port'), used)
        if r.get('protocol') not in ('static', 'ospf', 'bgp'):
            raise AciError(400, 'Protokoll static, ospf oder bgp')
        clean = {k: r.get(k) for k in ('name', 'serial', 'port', 'ip', 'protocol', 'routerId', 'descr')}
        clean['vlan'] = int(r.get('vlan') or 0)
        clean['mtu'] = int(r.get('mtu') or 1500)
        for k in ('networks', 'advertise', 'staticBack'):
            clean[k] = [str(x) for x in r.get(k, [])]
        o = r.get('ospf') or {}
        clean['ospf'] = {'area': o.get('area', '0.0.0.0'), 'areaType': o.get('areaType', 'regular'),
                         'hello': int(o.get('hello', 10)), 'dead': int(o.get('dead', 40)),
                         'nwT': o.get('nwT', 'bcast'), 'mtuIgnore': bool(o.get('mtuIgnore'))}
        b = r.get('bgp') or {}
        clean['bgp'] = {'asn': str(b.get('asn', '65100')), 'peerAs': str(b.get('peerAs', '65001'))}
        self.sim['routers'] = [x for x in self.sim['routers'] if x['name'] != (old or r['name'])] + [clean]

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
                          'since': info.get('since')})
        hosts = []
        for h in self.sim['hosts']:
            hs = e.hosts.get(h['name'], {})
            hosts.append(dict(h, status={'learned': hs.get('learned', False), 'ipLearned': hs.get('ipLearned'), 'quiet': hs.get('quiet', False),
                                         'epg': hs.get('epg'), 'reasons': hs.get('reasons', []),
                                         'path': hs.get('path'), 'encap': hs.get('encap')}))
        routers = []
        for r in self.sim['routers']:
            rs = e.routers.get(r['name'], {})
            routers.append(dict(r, status={'link': rs.get('link'), 'adj': rs.get('adj'),
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
                'pending': e.pending, 'hosts': hosts, 'routers': routers, 'settings': self.sim['settings'],
                'faults': sev, 'vpc': e.vpc_groups, 'mpbgp': e.mpbgp_ok,
                'vcenters': [dict(v, pwd='***') for v in self.sim.get('vcenters', [])], 'vmm': vmm, 'vms': vms,
                'lab': {k: lab.get(k) for k in ('id', 'title', 'intro', 'tasks', 'goals', 'solution')} if lab else None,
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

def make_handler(S):
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
                if path.startswith('/api/'):
                    return self.api(method, path[5:], q)
                if path.startswith('/sim/'):
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
                if not tok:
                    raise AciError(401, 'Username or password is incorrect - FAILED local authentication', 401)
                return self.send(200, self._login_resp(tok, a['name']),
                                 headers={'Set-Cookie': 'APIC-cookie=%s; path=/; HttpOnly' % tok})
            if rest == 'aaaRefresh':
                user, tok = self.auth()
                with S.lock:
                    if tok:
                        S.tokens[tok] = (user, time.time() + 3600, S.tokens[tok][2])
                return self.send(200, self._login_resp(tok or '', user),
                                 headers={'Set-Cookie': 'APIC-cookie=%s; path=/; HttpOnly' % tok} if tok else None)
            if rest == 'aaaLogout':
                c = self.cookies().get('APIC-cookie')
                with S.lock:
                    S.tokens.pop(c, None)
                return self.send(200, {'totalCount': '0', 'imdata': []})
            user, _ = self.auth()
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
                    return self.send(200, {'totalCount': str(total), 'imdata': res})
                if kind != 'mo':
                    raise AciError(400, 'POST/DELETE only on /api/mo')
                if method == 'POST':
                    b = self.body()
                    S.audit(user, mit_post(S.store, target, b))
                    S.changed()
                    return self.send(200, {'totalCount': '0', 'imdata': []})
                if method == 'DELETE':
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
            self.auth()
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
                    if b.get('op') == 'delete':
                        S.sim['hosts'] = [h for h in S.sim['hosts'] if h['name'] != b.get('name')]
                    else:
                        S.set_host(b.get('host') or {}, b.get('old'))
                    S.changed()
                    return self.send(200, {'ok': True})
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
                    v = float(b.get('discoverySeconds', 20))
                    S.sim['settings']['discoverySeconds'] = max(0.0, min(v, 600.0))
                    S.changed()
                    return self.send(200, {'ok': True})
                if rest == 'labs':
                    return self.send(200, [{k: l.get(k) for k in ('id', 'title', 'level', 'duration', 'goals',
                                                                  'topic', 'fabric')} for l in S.labs()])
                if rest == 'labs/load':
                    lab = S.load_lab(b.get('id'))
                    return self.send(200, {'ok': True, 'title': lab['title']})
                if rest == 'labs/check':
                    return self.send(200, S.check_lab() or {'checks': []})
                if rest == 'reset':
                    S.reset(b.get('mode', 'discovered'))
                    S.save()
                    return self.send(200, {'ok': True})
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
    S = Sim(data_dir, admin_pwd, discovery)
    httpd = ThreadingHTTPServer((host, port), make_handler(S))
    httpd.daemon_threads = True
    if https:
        crt, key = ensure_cert(data_dir)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(crt, key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    return S, httpd
