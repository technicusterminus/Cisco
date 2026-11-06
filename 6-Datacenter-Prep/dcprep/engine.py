"""Policy-Engine: macht aus der Konfiguration den operativen Zustand.

Nach jeder Änderung baut die Engine alles Operative neu auf: Fabric-Discovery,
Ports und Pfade, Auflösung der Relationen, EPG-Deployment auf den Leafs,
Endpoint-Learning der simulierten Hosts, L3Out-Nachbarschaften, Routing,
Zoning-Rules und Faults. Daraus entstehen auch die Antworten der CLI und
des Traffic-Tests.

Aufteilung: Dieser Teil steuert den Ablauf (rebuild), Fabric, NTP, In-Band, Faults
und Health. Die Fachlogik liegt in Mixins: engine_access (Access Policies, Deployment),
engine_endpoints (Endpoint-Learning, VMM, uSeg/ESG), engine_routing (L3Outs, Routen),
engine_policy (Klassen, Contracts, Service Graphs, Paket-Entscheidung). Gemeinsame
Hilfsfunktionen stehen in engine_util.
"""
import re

from . import setup as apic_setup
import time

from .model import CLASSES, split_dn, now_ts
from .ops import OpsMixin
from .multipod import PodMixin
from .msite import SiteMixin

from .engine_util import (SEV_PEN, EPHEMERAL, PORT_NAMES, vlan_num, pnum, net_of, ip_of, in_net,  # noqa: F401 (Re-Export)
                          norm_area, port_val)
from .engine_access import AccessMixin
from .engine_endpoints import EndpointMixin
from .engine_routing import RoutingMixin
from .engine_policy import PolicyMixin


class Engine(AccessMixin, EndpointMixin, RoutingMixin, PolicyMixin, OpsMixin, PodMixin, SiteMixin):
    def __init__(self, store, sim):
        self.store = store
        self.sim = sim
        self.fault_first = {}
        self.fault_cleared = {}   # Fault-Lebenszyklus: behobene Faults in retaining (fdn -> (Zeit, Attribute))
        self.fault_attrs = {}     # letzte Attribute je aktivem Fault
        self.next_event = None
        self.health = {}
        self.stats = {}
        self.rule_hits = {}       # (src pcTag, dst pcTag, Filter-DN|'implicit') -> Pakete (show system internal policy-mgr stats)

    # ------------------------------------------------------------------
    def A(self, dn):
        return self.store.attrs(dn)

    def has(self, dn):
        return dn in self.store.objs

    def kids(self, dn, cls=None):
        return self.store.children(dn, cls)

    def fault(self, dn, code, sev, descr, cause, rule='', ftype='config', domain='tenant'):
        d = self.faults.setdefault(dn, {})
        if code in d:
            if descr not in d[code]['descr']:
                d[code]['descr'] += ' | ' + descr
            return
        d[code] = {'severity': sev, 'descr': descr, 'cause': cause, 'rule': rule,
                   'type': ftype, 'domain': domain}

    # ------------------------------------------------------------------
    def rebuild(self, now=None):
        # simulierte Uhr (B-07): Wanduhr plus Versatz aus 'Zeit vorspulen'
        now = time.time() + float(self.sim.get('clockOffset', 0)) if now is None else now
        self.now = now
        self.store.clear_oper()
        self.faults = {}
        self._fabric(now)
        self._access()
        self._ipn_paths()
        self._oos()
        self._resolve()
        self._fw_groups()
        self._classes()
        self._epgs()
        self._vmm()
        self._services()
        self._loops()
        self._endpoints()
        changed, leases = self._dhcp()
        if changed:
            self.sim['leases'] = leases
            for d in self.store.by_class('fvCEp'):
                if d in self.store.objs:
                    self.store.delete(d)
            self._endpoints()
            self._dhcp()
        self._l3outs()
        self._inband()
        self._ntp()
        self._monitoring()
        self._fw_emit()
        self._emit_ports()
        self._emit_faults()
        self._health()
        self._history()

    def count(self, dn, key, n=1):
        if dn:
            d = self.stats.setdefault(dn, {})
            d[key] = d.get(key, 0) + n

    def _history(self):
        for kind, cls, rn in (('audit', 'aaaModLR', 'mod'), ('events', 'eventRecord', 'rec')):
            for r in self.sim.get(kind, [])[-1500:]:
                a = dict(r)
                a.pop('source', None)  # simulator-spezifisch, kein Attribut von aaaModLR
                a['id'] = str(a['id'])
                self.store.add('subj-[%s]/%s-%s' % (a['affected'], rn, a['id']), cls, a, True)

    def _inband(self):
        """In-Band-Management: In-Band EPG (VLAN), BD inb und Access Policies an den APIC-Ports."""
        self.inb = {}
        self.inb_info = []
        for epg in self.store.by_class('mgmtInB'):
            a = self.A(epg)
            info = {'dn': epg, 'vlan': vlan_num(a['encap']), 'reasons': [], 'ports': [], 'nodes': {}}
            self.inb_info.append(info)
            vlan = info['vlan']
            bdrs = self.A(epg + '/rsmgmtBD') or {}
            bd = bdrs.get('tDn') if bdrs.get('state') == 'formed' else None
            if vlan is None:
                info['reasons'].append('Encap (VLAN) fehlt am In-Band EPG')
            if not bd:
                info['reasons'].append('In-Band EPG ist mit keiner gueltigen Bridge Domain verknuepft')
            gws = [x for x in self.bd_subnets(bd)] if bd else []
            if bd and not gws:
                info['reasons'].append('BD %s hat kein Subnetz (Gateway fuer In-Band)' % self.short(bd))
            ctl = sorted(l for l, pi in self.ports.items() if (pi.get('peer') or ('',))[0] == 'controller')
            if vlan is not None:
                for l in ctl:
                    pg = self.ports[l]['pg']
                    doms = self._pg_info(pg)['domains'] if pg else []
                    if any(self.vlan_in_domain(d, vlan) for d in doms):
                        info['ports'].append(l)
                if not info['ports']:
                    info['reasons'].append('Die APIC-Ports (%s) haben keine Access Policy mit einer Domain, deren VLAN Pool vlan-%d enthaelt' % (
                        ', '.join('%s %s' % (self.nodes[n]['name'], p) for n, p in ctl) or 'keine', vlan))
                    self.fault(epg, 'S0211', 'major', 'In-Band management VLAN vlan-%d cannot be deployed on the APIC-facing ports: '
                               'no domain with this VLAN on their access policy' % vlan, 'inb-vlan-not-deployable', domain='infra')
            for rs in self.kids(epg, 'mgmtRsInBStNode'):
                ra = self.A(rs)
                m = re.search(r'/node-(\d+)$', ra['tDn'])
                if not m or not ra['addr']:
                    continue
                nid = int(m.group(1))
                net = net_of(ra['addr'])
                why = None
                if info['reasons']:
                    why = info['reasons'][0]
                elif not any(net == x['net'] for x in gws):
                    why = 'Adresse %s liegt in keinem Subnetz des BD %s' % (ra['addr'], self.short(bd))
                elif not any(ra['gw'] == x['gw'] for x in gws):
                    why = 'Gateway %s ist nicht die Gateway-IP des BD %s' % (ra['gw'], self.short(bd))
                elif nid != 1 and self.nodes.get(nid, {}).get('state') != 'active':
                    why = 'Node %d ist nicht aktiv' % nid
                info['nodes'][nid] = why
                if not why:
                    self.inb[nid] = ra['addr']
                    sysdn = '%s/node-%d/sys' % (self.pdn(nid), nid)
                    if self.has(sysdn):
                        self.A(sysdn)['inbMgmtAddr'] = str(ip_of(ra['addr']))

    def _ntp(self):
        pgrp, pol = None, None
        for pp in self.store.by_class('fabricPodP'):
            for sel in self.kids(pp, 'fabricPodS'):
                t = (self.A(sel + '/rspodPGrp') or {}).get('tDn')
                if t and self.has(t):
                    pgrp = t
        if pgrp:
            t = (self.A(pgrp + '/rsTimePol') or {}).get('tDn') or ''
            pol = t if self.has(t) else None
        pa = self.A(pol) if pol else None
        provs = [self.A(p)['name'] for p in self.kids(pol, 'datetimeNtpProv')] if pol else []
        self.ntp = {'pgrp': pgrp, 'pol': pol, 'provs': provs, 'nodes': {}}
        for nid, n in self.nodes.items():
            if n['state'] != 'active':
                continue
            if not pgrp:
                why = 'Pod Profile default hat keine Pod Policy Group'
            elif not pa or pa['adminSt'] != 'enabled':
                why = 'Date and Time Policy fehlt oder ist deaktiviert'
            elif not provs:
                why = 'keine NTP-Server in der Date and Time Policy'
            else:
                epgs = [(self.A(p + '/rsNtpProvToEpg') or {}).get('tDn', '') for p in self.kids(pol, 'datetimeNtpProv')]
                inb_only = epgs and all('/inb-' in x for x in epgs)
                if inb_only and not getattr(self, 'inb', {}).get(nid):
                    why = 'NTP-Server ist ueber In-Band konfiguriert, der Switch hat keine aktive In-Band-Adresse'
                elif not inb_only and not self.oob.get(nid):
                    why = 'keine Management-Adresse (Static Node Management Address) - NTP-Server nicht erreichbar'
                else:
                    why = None
            self.ntp['nodes'][nid] = why

    # ------------------------------------------------------------------
    # Fabric: Discovery, Knoten, Links
    # ------------------------------------------------------------------
    def _fabric(self, now):
        st, topo = self.store, self.sim['topology']
        pod = topo.get('pod', 1)
        self.setup = self.sim.get('setup', 0)
        if self.setup == 0:
            self.setup = {k: v for k, v in apic_setup.DEFAULTS.items() if k != 'pwd'}
        self.apic_up = self.setup is not None
        su = self.setup or apic_setup.DEFAULTS
        self.tep_pool = su['tepPool']
        self.infra_vlan = int(su['infraVlan'])
        self.fabric_name = su['fabricName']
        self.pod = pod
        self.poddn = 'topology/pod-%d' % pod
        fw_next = self._fw_state(now)
        st.add('topology', 'fabricTopology', {}, True)
        st.add(self.poddn, 'fabricPod', {'id': str(pod), 'podType': 'physical'}, True)
        nodes = {n['serial']: n for n in topo['nodes']}
        apic = topo['apic']
        ident = {}
        for dn in st.by_class('fabricNodeIdentP'):
            a = st.attrs(dn)
            ident[a['serial']] = (dn, a)
        reg = self.sim.setdefault('registered', {})
        for s in list(reg):
            if s not in ident:
                del reg[s]
        for s in ident:
            if s in nodes and s not in reg:
                reg[s] = now
        valid, seen = {}, {}
        for s, (dn, a) in sorted(ident.items(), key=lambda x: x[1][1].get('modTs', '')):
            if s not in nodes:
                continue
            nid = int(a['nodeId'] or 0)
            npod = nodes[s].get('pod', pod)
            if int(a.get('podId') or 1) != npod:
                self.fault(dn, 'S0135', 'major', 'Node %s is registered with Pod ID %s but is connected in pod %d'
                           % (s, a.get('podId'), npod), 'pod-id-mismatch', domain='infra')
                continue
            if nodes[s].get('remote') and a.get('nodeType') != 'remote-leaf-wan':
                self.fault(dn, 'S0136', 'major', 'Node %s is a remote leaf and must be registered with node type '
                           'remote-leaf-wan and its Remote Pool ID' % s, 'remote-leaf-type-missing', domain='infra')
                continue
            if nid in seen:
                self.fault(dn, 'S0134', 'major', 'Node ID %d is already in use by node with serial %s'
                           % (nid, seen[nid]), 'node-id-conflict', domain='infra')
                continue
            seen[nid] = s
            valid[s] = nid
        adj = {}
        for l in topo['links']:
            adj.setdefault(l[0], set()).add(l[2])
            adj.setdefault(l[2], set()).add(l[0])
        self.apic_tep = apic_setup.apic_tep(self.tep_pool)
        self._mp_eval(nodes, valid, ident)
        adj = self.mp_adj_filter(adj, apic['serial'])
        speed = float(self.sim.get('settings', {}).get('discoverySeconds', 20))
        inf = float('inf')
        act = {apic['serial']: 0.0} if self.apic_up else {}
        changed = True
        while changed:
            changed = False
            for s in valid:
                nbt = min((act.get(n, inf) for n in adj.get(s, ())), default=inf)
                if nbt == inf:
                    continue
                t = max(reg[s], nbt) + speed
                if t < act.get(s, inf) - 1e-9:
                    act[s] = t
                    changed = True
        self.next_event = min([t for t in act.values() if t > now] + ([fw_next] if fw_next else []), default=None)

        self.nodes = {}            # nid -> info
        self.pod_of = {1: pod}
        self.serial_node = {}      # serial -> nid (registriert)
        self.serial_active = {}    # serial -> nid (aktiv)
        self.pending = []
        self.leaf_ids = set()
        for s, nid in valid.items():
            n = nodes[s]
            dn, a = ident[s]
            nbt = min((act.get(x, inf) for x in adj.get(s, ())), default=inf)
            if act.get(s, inf) <= now:
                state = 'active'
            elif nbt <= now:
                state = 'discovering'
            else:
                state = 'inactive'
            if s in self.fw_reload:
                state = 'inactive'
            if state == 'active' and not self.mp_gate(s):
                state = 'discovering'
            npod = n.get('pod', pod)
            if n.get('remote'):
                rp = self.mp['remote'].get(int(a.get('extPoolId') or 0)) or {}
                tep = apic_setup.tep_of(rp.get('pool') or self.tep_pool, npod, nid)
            else:
                tep = apic_setup.tep_of(self.mp['pools'].get(npod, self.tep_pool), npod, nid)
            self.pod_of[nid] = npod
            info = {'id': nid, 'serial': s, 'name': a['name'] or 'node-%d' % nid, 'role': n['role'],
                    'model': n['model'], 'state': state, 'ports': n['ports'],
                    'tep': tep, 'pod': npod, 'remote': bool(n.get('remote')),
                    'since': act.get(s), 'regdn': dn, 'upgrading': self.fw_reload.get(s)}
            self.nodes[nid] = info
            self.serial_node[s] = nid
            if state == 'active':
                self.serial_active[s] = nid
            if n['role'] == 'leaf':
                self.leaf_ids.add(nid)
        for s, n in nodes.items():
            if s in valid:
                continue
            nbt = min((act.get(x, inf) for x in adj.get(s, ())), default=inf)
            if nbt <= now:
                self.pending.append({'serial': s, 'model': n['model'], 'role': n['role'], 'pod': n.get('pod', pod),
                                     'remote': bool(n.get('remote'))})

        self.oob = {}
        for r in self.store.by_class('mgmtRsOoBStNode'):
            m = re.search(r'/node-(\d+)$', self.A(r)['tDn'])
            if m and self.A(r)['addr']:
                self.oob[int(m.group(1))] = self.A(r)['addr']
        # APIC
        atep = apic_setup.apic_tep(self.tep_pool)
        self.apic_tep = atep
        adn = self.poddn + '/node-1'
        st.add(adn, 'fabricNode', {'id': '1', 'name': apic['name'], 'role': 'controller',
                                   'serial': apic['serial'], 'model': apic['model'], 'fabricSt': 'unknown',
                                   'address': atep, 'version': self.apic_version, 'adSt': 'on',
                                   'nodeType': 'unspecified', 'vendor': 'Cisco Systems, Inc',
                                   'lastStateModTs': now_ts()}, True)
        st.add(adn + '/sys', 'topSystem', {'address': atep, 'id': '1', 'name': apic['name'], 'fabricDomain': self.fabric_name,
                                           'role': 'controller', 'serial': apic['serial'],
                                           'podId': str(pod), 'oobMgmtAddr': str(ip_of(self.oob[1])) if self.oob.get(1) else '0.0.0.0',
                                           'inbMgmtAddr': '0.0.0.0', 'version': self.apic_version,
                                           'systemUpTime': '01:00:00:00.000',
                                           'fabricMAC': '00:00:00:00:00:00', 'tepPool': self.tep_pool,
                                           'state': 'in-service' if self.apic_up else 'out-of-service'}, True)
        if self.apic_up and int(su['ctrlCount']) > 1:
            self.fault(adn + '/sys', 'S0101', 'major', 'Controller cluster is configured for %s controllers, but only 1 '
                       'controller is available - the cluster is not fully fit' % su['ctrlCount'], 'cluster-not-fully-fit',
                       domain='infra')
        for p in self.pending:
            st.add(adn + '/sys/client-[%s]' % p['serial'], 'dhcpClient',
                   {'id': p['serial'], 'model': p['model'], 'nodeRole': 'remote-leaf-wan' if p.get('remote') else p['role'], 'podId': str(p.get('pod', pod)),
                    'fabricId': '1', 'clientEvent': 'pending', 'nodeId': '0', 'name': '',
                    'ip': '0.0.0.0', 'supported': 'yes', 'decomissioned': 'no'}, True)

        for pd in sorted(set(self.pod_of.values())):
            st.add('topology/pod-%d' % pd, 'fabricPod', {'id': str(pd), 'podType': 'physical'}, True)
        for nid, n in self.nodes.items():
            ndn = '%s/node-%d' % (self.pdn(nid), nid)
            st.add(ndn, 'fabricNode', {'id': str(nid), 'name': n['name'], 'role': n['role'],
                                       'serial': n['serial'], 'model': n['model'],
                                       'fabricSt': n['state'], 'address': n['tep'] if n['state'] == 'active' else '0.0.0.0',
                                       'version': self.node_version(n['serial']) if n['state'] == 'active' else '',
                                       'adSt': 'on', 'nodeType': 'remote-leaf-wan' if n.get('remote') else 'unspecified',
                                       'vendor': 'Cisco Systems, Inc', 'lastStateModTs': now_ts(n['since'])
                                       if n['since'] and n['since'] != inf else 'never'}, True)
            if n['state'] != 'active':
                continue
            up = int(now - n['since'])
            st.add(ndn + '/sys', 'topSystem', {
                'address': n['tep'], 'id': str(nid), 'name': n['name'], 'role': n['role'],
                'serial': n['serial'], 'state': 'in-service', 'podId': str(n['pod']),
                'oobMgmtAddr': str(ip_of(self.oob[nid])) if self.oob.get(nid) else '0.0.0.0', 'inbMgmtAddr': '0.0.0.0',
                'version': self.node_version(n['serial']), 'fabricMAC': '00:22:BD:F8:19:FF', 'tepPool': self.tep_pool, 'fabricDomain': self.fabric_name,
                'systemUpTime': '%02d:%02d:%02d:%02d.000' % (up // 86400, up % 86400 // 3600, up % 3600 // 60, up % 60)}, True)

        # Ports
        self.ports = {}
        for nid, n in self.nodes.items():
            if n['state'] != 'active':
                continue
            for p in range(1, n['ports'] + 1):
                self.ports[(nid, 'eth1/%d' % p)] = {
                    'oper': 'down', 'qual': 'link-not-connected', 'usage': set(), 'peer': None,
                    'pg': None, 'vlans': set(), 'layer': 'Layer2', 'fabric': False,
                    'speed': '100G' if (n['role'] == 'spine' or p > 48) else '25G'}
        name_of = {apic['serial']: apic['name']}
        name_of.update({s: self.nodes[nid]['name'] for s, nid in self.serial_node.items()})
        id_of = {apic['serial']: 1}
        id_of.update(self.serial_node)
        self.lldp = {}
        lnk = set()
        for a_s, a_p, b_s, b_p in topo['links']:
            for (xs, xp, ys, yp) in ((a_s, a_p, b_s, b_p), (b_s, b_p, a_s, a_p)):
                xid = self.serial_active.get(xs)
                if xid is None:
                    continue
                pi = self.ports.get((xid, xp))
                if pi is None:
                    continue
                pi.update({'oper': 'up', 'qual': 'link-up', 'fabric': True,
                           'peer': ('controller' if ys == apic['serial'] else 'fabric', name_of.get(ys, ys), yp)})
                pi['usage'].add('controller' if ys == apic['serial'] else 'fabric')
                pi['layer'] = 'Layer3'
                self.lldp.setdefault(xid, []).append(
                    (xp, name_of.get(ys, 'switch'), yp, 'BR' if ys != apic['serial'] else 'S', ys))
                yid = id_of.get(ys)
                if ys in self.serial_active and xid != 1 and (xid, yid) not in lnk:
                    lnk.add((xid, yid))
                    cdn = '%s/lnkcnt-%d' % (self.pdn(xid), yid)
                    st.add(cdn, 'fabricLinkCont', {'id': str(yid)}, True)
                    st.add(cdn + '/lnk-%d-1-%s-to-%d-1-%s' % (xid, xp.split('/')[-1], yid, yp.split('/')[-1]),
                           'fabricLink', {'n1': str(xid), 's1': '1', 'p1': xp.split('/')[-1],
                                          'n2': str(yid), 's2': '1', 'p2': yp.split('/')[-1],
                                          'linkState': 'ok', 'wiringIssues': ''}, True)
        for s_, p_, rname, rport in topo.get('ipnlinks', []):
            xid = self.serial_active.get(s_)
            pi = self.ports.get((xid, p_)) if xid else None
            r = next((x for x in (self.sim.get('ipn') or {}).get('routers', []) if x['name'] == rname), None)
            if pi is not None and r and not r.get('down'):
                pi.update({'oper': 'up', 'qual': 'link-up', 'fabric': True, 'layer': 'Layer3', 'peer': ('ipn', rname, rport)})
                pi['usage'].add('infra')
                self.lldp.setdefault(xid, []).append((p_, rname, rport, 'R', rname))
        # Hosts/Router verkabeln
        self.cabled = {}
        for h in self.sim.get('hosts', []):
            if h.get('linkdown'):
                continue  # simulierter Kabel-/NIC-Ausfall am Host: Port bleibt ohne Link
            for s, p in h.get('links', []):
                nid = self.serial_active.get(s)
                if nid and (nid, p) in self.ports:
                    self.cabled[(nid, p)] = ('host', h['name'])
        for r in self.sim.get('routers', []):
            nid = self.serial_active.get(r.get('serial'))
            if nid and (nid, r.get('port')) in self.ports:
                self.cabled[(nid, r['port'])] = ('router', r['name'])
        for key, peer in self.cabled.items():
            pi = self.ports[key]
            pi.update({'oper': 'up', 'qual': 'link-up', 'peer': (peer[0], peer[1], 'eth0')})

    def _emit_ports(self):
        for (nid, port), pi in sorted(self.ports.items(), key=lambda x: (x[0][0], pnum(x[0][1]) or 0)):
            base = '%s/node-%d/sys/phys-[%s]' % (self.pdn(nid), nid, port)
            usage = ','.join(sorted(pi['usage'])) or 'discovery'
            self.store.add(base, 'l1PhysIf', {'id': port, 'adminSt': pi.get('admin', 'up'), 'usage': usage, 'mtu': '9000',
                                              'speed': 'inherit', 'layer': pi['layer'],
                                              'portT': 'fab' if pi['fabric'] else 'leaf',
                                              'mode': 'trunk', 'descr': '', 'autoNeg': 'on'}, True)
            self.store.add(base + '/phys', 'ethpmPhysIf', {
                'operSt': pi['oper'], 'operStQual': pi['qual'],
                'operSpeed': pi['speed'] if pi['oper'] == 'up' else 'unknown', 'operMode': 'trunk',
                'bundleIndex': 'unspecified',
                'operVlans': ','.join(str(v) for v in sorted(pi['vlans'])),
                'allowedVlans': ','.join(str(v) for v in sorted(pi['vlans']))}, True)

    # ------------------------------------------------------------------
    # Faults und Health
    # ------------------------------------------------------------------
    def _emit_faults(self):
        """Faults als faultInst. Lebenszyklus (B-07, vereinfacht): soaking -> raised, behoben -> retaining (severity cleared).
        Die Dauern stehen in settings.faultSoakSeconds / faultRetainSeconds; 0 (Standard) heisst sofort raised bzw. sofort weg."""
        st = self.sim.get('settings', {})
        soak, retain = float(st.get('faultSoakSeconds', 0) or 0), float(st.get('faultRetainSeconds', 0) or 0)
        seen, upcoming = set(), []
        for dn, codes in self.faults.items():
            if dn not in self.store.objs:
                continue
            for code, f in codes.items():
                fdn = dn + '/fault-' + code
                seen.add(fdn)
                self.fault_cleared.pop(fdn, None)
                first = self.fault_first.get(fdn)
                if not first or first[1] != f['descr']:
                    first = (now_ts(self.now), f['descr'], self.now)
                    self.fault_first[fdn] = first
                t0 = first[2] if len(first) > 2 else self.now
                soaking = soak > 0 and self.now < t0 + soak
                if soaking:
                    upcoming.append(t0 + soak)
                lc = 'soaking' if soaking else 'raised'
                last = first[0] if soaking or soak <= 0 else now_ts(t0 + soak)
                attrs = {
                    'ack': 'no', 'cause': f['cause'], 'changeSet': '', 'code': code, 'created': first[0],
                    'descr': f['descr'], 'domain': f['domain'], 'highestSeverity': f['severity'],
                    'lastTransition': last, 'lc': lc, 'occur': '1', 'origSeverity': f['severity'],
                    'prevSeverity': f['severity'], 'rule': f['rule'] or f['cause'], 'severity': f['severity'],
                    'subject': CLASSES[self.store.objs[dn][0]].label, 'type': f['type']}
                self.store.add(fdn, 'faultInst', attrs, True)
                self.fault_attrs[fdn] = attrs
        for k in list(self.fault_first):
            if k in seen:
                continue
            if retain > 0 and k in self.fault_attrs:
                # behoben: bleibt als retaining mit severity cleared sichtbar, bis die Retention abgelaufen ist
                self.fault_cleared[k] = (self.now, self.fault_attrs[k])
            del self.fault_first[k]
            self.fault_attrs.pop(k, None)
        for k, (t1, attrs) in list(self.fault_cleared.items()):
            parent = k.rsplit('/fault-', 1)[0]
            if retain <= 0 or self.now >= t1 + retain or parent not in self.store.objs:
                del self.fault_cleared[k]
                continue
            upcoming.append(t1 + retain)
            self.store.add(k, 'faultInst', dict(attrs, lc='retaining', severity='cleared', prevSeverity=attrs['severity'],
                                                 lastTransition=now_ts(t1)), True)
        if upcoming:
            nxt = min(upcoming)
            self.next_event = nxt if self.next_event is None else min(self.next_event, nxt)

    def _health(self):
        pen = {}
        for dn in self.store.by_class('faultInst'):
            a = self.A(dn)
            p = SEV_PEN.get(a['severity'], 0)
            parts = split_dn(dn)[:-1]
            for i in range(1, len(parts) + 1):
                d = '/'.join(parts[:i])
                pen[d] = pen.get(d, 0) + p
        self.health = {d: max(0, 100 - p) for d, p in pen.items()}

    def score(self, dn):
        return self.health.get(dn, 100)

    # ------------------------------------------------------------------
    # Anzeige-Helfer
    # ------------------------------------------------------------------
    def node_label(self, serial):
        nid = self.serial_node.get(serial)
        if nid:
            return '%s (%s)' % (self.nodes[nid]['name'], serial)
        return serial

    def overlay(self):
        """Topologie-Overlay (B-08): je EPG, BD und VRF die Leafs mit Deployment und die gelernten Hosts."""
        out = {}

        def ent(kind, dn):
            return out.setdefault(dn, {'kind': kind, 'dn': dn, 'name': self.short(dn), 'leafs': set(), 'hosts': set()})
        for d in self.deploys:
            for kind, dn in (('EPG', d['epg']), ('BD', d['bd']), ('VRF', d['vrf'])):
                ent(kind, dn)['leafs'].update(self.nodes[n]['name'] for n in d['nodes'] if n in self.nodes)
        for name, hs in self.hosts.items():
            if not hs.get('learned'):
                continue
            for kind, dn in (('EPG', hs.get('epg')), ('BD', hs.get('bd')), ('VRF', hs.get('vrf'))):
                if dn:
                    ent(kind, dn)['hosts'].add(name)
        order = {'VRF': 0, 'BD': 1, 'EPG': 2}
        return [dict(o, leafs=sorted(o['leafs']), hosts=sorted(o['hosts']))
                for o in sorted(out.values(), key=lambda o: (order[o['kind']], o['name']))]

    def path_label(self, path):
        p = self.paths.get(path)
        if not p:
            return path
        if p['type'] == 'port':
            return '%s %s' % (self.nodes[p['nodes'][0]]['name'], p['name'])
        if p['type'] == 'pc':
            return 'Port-Channel %s auf %s' % (p['name'], self.nodes[p['nodes'][0]]['name'])
        return 'vPC %s auf %s' % (p['name'], '/'.join(self.nodes[n]['name'] for n in p['nodes']))

    def short(self, dn):
        if not dn:
            return '-'
        parts = split_dn(dn)
        out = []
        for p in parts[1:]:
            out.append(re.sub(r'^(tn|ap|epg|BD|ctx|out|instP|brc|flt|taboo)-', '', p))
        return ':'.join(out)
