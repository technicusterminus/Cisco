"""Policy-Engine: macht aus der Konfiguration den operativen Zustand.

Nach jeder Änderung baut die Engine alles Operative neu auf: Fabric-Discovery,
Ports und Pfade, Auflösung der Relationen, EPG-Deployment auf den Leafs,
Endpoint-Learning der simulierten Hosts, L3Out-Nachbarschaften, Routing,
Zoning-Rules und Faults. Daraus entstehen auch die Antworten der CLI und
des Traffic-Tests.
"""
import ipaddress
import re
import time

from .model import CLASSES, split_dn, parent_dn, rn_of, tenant_of, now_ts

SEV_PEN = {'critical': 40, 'major': 15, 'minor': 5, 'warning': 1}
EPHEMERAL = 49152
PORT_NAMES = {'ftpData': 20, 'smtp': 25, 'dns': 53, 'http': 80, 'pop3': 110, 'https': 443, 'rtsp': 554}


def vlan_num(encap):
    m = re.match(r'^vlan-(\d+)$', encap or '')
    return int(m.group(1)) if m else None


def pnum(p):
    m = re.match(r'^eth1/(\d+)$', p)
    return int(m.group(1)) if m else None


def net_of(ipmask):
    try:
        return ipaddress.ip_interface(ipmask).network
    except ValueError:
        return None


def ip_of(ipmask):
    try:
        return ipaddress.ip_interface(ipmask).ip
    except ValueError:
        return None


def in_net(ip, net):
    try:
        return ipaddress.ip_address(str(ip)) in ipaddress.ip_network(str(net), strict=False)
    except ValueError:
        return False


def norm_area(a):
    a = str(a or '').strip()
    if a in ('backbone', ''):
        return '0.0.0.0'
    if a.isdigit():
        return str(ipaddress.ip_address(int(a)))
    return a


def port_val(v):
    if v in (None, '', 'unspecified'):
        return None
    if v in PORT_NAMES:
        return PORT_NAMES[v]
    return int(v) if str(v).isdigit() else None


class Engine:
    def __init__(self, store, sim):
        self.store = store
        self.sim = sim
        self.fault_first = {}
        self.next_event = None
        self.health = {}

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
        now = time.time() if now is None else now
        self.now = now
        self.store.clear_oper()
        self.faults = {}
        self._fabric(now)
        self._access()
        self._resolve()
        self._classes()
        self._epgs()
        self._endpoints()
        self._l3outs()
        self._emit_ports()
        self._emit_faults()
        self._health()

    # ------------------------------------------------------------------
    # Fabric: Discovery, Knoten, Links
    # ------------------------------------------------------------------
    def _fabric(self, now):
        st, topo = self.store, self.sim['topology']
        pod = topo.get('pod', 1)
        self.pod = pod
        self.poddn = 'topology/pod-%d' % pod
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
        speed = float(self.sim.get('settings', {}).get('discoverySeconds', 20))
        inf = float('inf')
        act = {apic['serial']: 0.0}
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
        self.next_event = min([t for t in act.values() if t > now], default=None)

        self.nodes = {}            # nid -> info
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
            info = {'id': nid, 'serial': s, 'name': a['name'] or 'node-%d' % nid, 'role': n['role'],
                    'model': n['model'], 'state': state, 'ports': n['ports'],
                    'tep': '10.0.%d.%d' % (pod * 16 + nid // 250, nid % 250 + 32),
                    'since': act.get(s), 'regdn': dn}
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
                self.pending.append({'serial': s, 'model': n['model'], 'role': n['role']})

        # APIC
        version = '6.0(5h)-sim'
        adn = self.poddn + '/node-1'
        st.add(adn, 'fabricNode', {'id': '1', 'name': apic['name'], 'role': 'controller',
                                   'serial': apic['serial'], 'model': apic['model'], 'fabricSt': 'unknown',
                                   'address': '10.0.0.1', 'version': '6.0(5h)', 'adSt': 'on',
                                   'nodeType': 'unspecified', 'vendor': 'Cisco Systems, Inc',
                                   'lastStateModTs': now_ts()}, True)
        st.add(adn + '/sys', 'topSystem', {'address': '10.0.0.1', 'id': '1', 'name': apic['name'],
                                           'role': 'controller', 'serial': apic['serial'], 'state': 'in-service',
                                           'podId': str(pod), 'oobMgmtAddr': '192.168.10.1',
                                           'inbMgmtAddr': '0.0.0.0', 'version': '6.0(5h)',
                                           'systemUpTime': '01:00:00:00.000',
                                           'fabricMAC': '00:00:00:00:00:00', 'tepPool': '10.0.0.0/16'}, True)
        for p in self.pending:
            st.add(adn + '/sys/client-[%s]' % p['serial'], 'dhcpClient',
                   {'id': p['serial'], 'model': p['model'], 'nodeRole': p['role'], 'podId': str(pod),
                    'fabricId': '1', 'clientEvent': 'pending', 'nodeId': '0', 'name': '',
                    'ip': '0.0.0.0', 'supported': 'yes', 'decomissioned': 'no'}, True)

        for nid, n in self.nodes.items():
            ndn = '%s/node-%d' % (self.poddn, nid)
            st.add(ndn, 'fabricNode', {'id': str(nid), 'name': n['name'], 'role': n['role'],
                                       'serial': n['serial'], 'model': n['model'],
                                       'fabricSt': n['state'], 'address': n['tep'] if n['state'] == 'active' else '0.0.0.0',
                                       'version': 'n9000-16.0(5h)' if n['state'] == 'active' else '',
                                       'adSt': 'on', 'nodeType': 'unspecified',
                                       'vendor': 'Cisco Systems, Inc', 'lastStateModTs': now_ts(n['since'])
                                       if n['since'] and n['since'] != inf else 'never'}, True)
            if n['state'] != 'active':
                continue
            up = int(now - n['since'])
            st.add(ndn + '/sys', 'topSystem', {
                'address': n['tep'], 'id': str(nid), 'name': n['name'], 'role': n['role'],
                'serial': n['serial'], 'state': 'in-service', 'podId': str(pod),
                'oobMgmtAddr': '192.168.10.%d' % (nid % 250), 'inbMgmtAddr': '0.0.0.0',
                'version': 'n9000-16.0(5h)', 'fabricMAC': '00:22:BD:F8:19:FF', 'tepPool': '10.0.0.0/16',
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
                    cdn = '%s/lnkcnt-%d' % (self.poddn, yid)
                    st.add(cdn, 'fabricLinkCont', {'id': str(yid)}, True)
                    st.add(cdn + '/lnk-%d-1-%s-to-%d-1-%s' % (xid, xp.split('/')[-1], yid, yp.split('/')[-1]),
                           'fabricLink', {'n1': str(xid), 's1': '1', 'p1': xp.split('/')[-1],
                                          'n2': str(yid), 's2': '1', 'p2': yp.split('/')[-1],
                                          'linkState': 'ok', 'wiringIssues': ''}, True)
        # Hosts/Router verkabeln
        self.cabled = {}
        for h in self.sim.get('hosts', []):
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

    # ------------------------------------------------------------------
    # Access Policies: Switch-/Interface-Profile, Policy-Gruppen, Pfade
    # ------------------------------------------------------------------
    def _pg_info(self, pg):
        if pg in self._pgcache:
            return self._pgcache[pg]
        a = self.A(pg)
        info = {'dn': pg, 'cls': self.store.objs[pg][0], 'name': a['name'],
                'lagT': a.get('lagT', 'not-aggregated'), 'aaep': None, 'domains': [],
                'lacp': 'off', 'cdp': 'disabled', 'lldp': True}
        rs = pg + '/rsattEntP'
        if self.has(rs) and self.has(self.A(rs)['tDn']):
            info['aaep'] = self.A(rs)['tDn']
            for d in self.kids(info['aaep'], 'infraRsDomP'):
                t = self.A(d)['tDn']
                if self.has(t):
                    info['domains'].append(t)

        def pol(rn, attr, prefix):
            r = pg + '/' + rn
            name = (self.A(r) or {}).get(attr) or 'default'
            return self.A('uni/infra/%s-%s' % (prefix, name))
        lacp = pol('rslacpPol', 'tnLacpLagPolName', 'lacplagp')
        if lacp:
            info['lacp'] = lacp['mode']
        cdp = pol('rscdpIfPol', 'tnCdpIfPolName', 'cdpIfP')
        if cdp:
            info['cdp'] = cdp['adminSt']
        lldp = pol('rslldpIfPol', 'tnLldpIfPolName', 'lldpIfP')
        if lldp:
            info['lldp'] = lldp['adminRxSt'] == 'enabled' and lldp['adminTxSt'] == 'enabled'
        self._pgcache[pg] = info
        return info

    def _access(self):
        st = self.store
        self._pgcache = {}
        self.portmap = {}   # (nid, port) -> pg dn
        for np in st.by_class('infraNodeP'):
            sel = set()
            for ls in self.kids(np, 'infraLeafS'):
                if self.A(ls)['type'] == 'ALL':
                    sel |= self.leaf_ids
                for nb in self.kids(ls, 'infraNodeBlk'):
                    a = self.A(nb)
                    f, t = int(a['from_'] or 0), int(a['to_'] or 0)
                    sel |= {n for n in self.leaf_ids if f <= n <= t}
            for rs in self.kids(np, 'infraRsAccPortP'):
                ip = self.A(rs)['tDn']
                if not self.has(ip):
                    continue
                for hs in self.kids(ip, 'infraHPortS'):
                    rsg = hs + '/rsaccBaseGrp'
                    pg = self.A(rsg)['tDn'] if self.has(rsg) else ''
                    pg = pg if self.has(pg) else None
                    ports = set()
                    if self.A(hs)['type'] == 'ALL':
                        ports = set(range(1, 49))
                    for b in self.kids(hs, 'infraPortBlk'):
                        a = self.A(b)
                        if a['fromCard'] != '1':
                            continue
                        ports |= set(range(int(a['fromPort']), int(a['toPort']) + 1))
                    for nid in sel:
                        for p in ports:
                            key = (nid, 'eth1/%d' % p)
                            old = self.portmap.get(key)
                            if old and old[0] != pg:
                                self.fault(hs, 'S0841', 'minor',
                                           'Port eth1/%d on node %d is selected by multiple interface selectors '
                                           'with different policy groups (%s)' % (p, nid, old[1]),
                                           'port-config-conflict', domain='access')
                                continue
                            self.portmap[key] = (pg, hs)
        for key, (pg, hs) in self.portmap.items():
            if key in self.ports and pg:
                self.ports[key]['pg'] = pg

        # vPC-Paare
        self.vpc_peer, self.vpc_groups = {}, []
        for g in self.kids('uni/fabric/protpol', 'fabricExplicitGEp'):
            ids = sorted(int(self.A(n)['id']) for n in self.kids(g, 'fabricNodePEp'))
            if len(ids) != 2:
                if ids:
                    self.fault(g, 'S0475', 'minor', 'vPC protection group needs exactly two nodes',
                               'vpc-config-incomplete', domain='infra')
                continue
            if any(i in self.vpc_peer for i in ids):
                self.fault(g, 'S0476', 'major', 'Node already belongs to another vPC protection group',
                           'vpc-config-conflict', domain='infra')
                continue
            self.vpc_peer[ids[0]], self.vpc_peer[ids[1]] = ids[1], ids[0]
            up = all(self.nodes.get(i, {}).get('state') == 'active' for i in ids)
            self.vpc_groups.append({'dn': g, 'name': self.A(g)['name'], 'id': self.A(g)['id'],
                                    'nodes': ids, 'up': up})

        # Pfade
        self.paths = {}
        for (nid, port), pi in self.ports.items():
            if pi['fabric'] or self.nodes[nid]['role'] != 'leaf':
                continue
            dn = '%s/paths-%d/pathep-[%s]' % (self.poddn, nid, port)
            self.paths[dn] = {'type': 'port', 'legs': [(nid, port)], 'pg': pi['pg'], 'nodes': [nid],
                              'name': port}
        bundles = {}
        for (nid, port), pi in self.ports.items():
            if pi['pg'] and self.store.objs[pi['pg']][0] == 'infraAccBndlGrp' and not pi['fabric']:
                bundles.setdefault(pi['pg'], {}).setdefault(nid, []).append(port)
        for pg, bynode in bundles.items():
            info = self._pg_info(pg)
            legs_all = [(n, p) for n, ps in bynode.items() for p in sorted(ps, key=pnum)]
            if info['lagT'] == 'link':
                for nid, ps in bynode.items():
                    dn = '%s/paths-%d/pathep-[%s]' % (self.poddn, nid, info['name'])
                    self.paths[dn] = {'type': 'pc', 'legs': [(nid, p) for p in ps], 'pg': pg,
                                      'nodes': [nid], 'name': info['name']}
            else:
                ns = sorted(bynode)
                done, alone = set(), []
                for n in ns:
                    if n in done:
                        continue
                    peer = self.vpc_peer.get(n)
                    if peer is None:
                        alone.append(n)
                        continue
                    a, b = sorted([n, peer])
                    done |= {a, b}
                    legs = [(x, p) for x in (a, b) for p in sorted(bynode.get(x, []), key=pnum)]
                    dn = '%s/protpaths-%d-%d/pathep-[%s]' % (self.poddn, a, b, info['name'])
                    self.paths[dn] = {'type': 'vpc', 'legs': legs, 'pg': pg, 'nodes': [a, b], 'name': info['name']}
                if alone:
                    self.fault(pg, 'S0477', 'minor',
                               'vPC interface policy group is deployed on node(s) %s without vPC peer '
                               '(no explicit vPC protection group)' % ','.join(map(str, alone)),
                               'vpc-domain-missing', domain='access')
            for leg in legs_all:
                pdn = '%s/paths-%d/pathep-[%s]' % (self.poddn, leg[0], leg[1])
                if pdn in self.paths:
                    self.paths[pdn]['member_of'] = info['name']
        for dn, p in self.paths.items():
            parts = split_dn(dn)
            cdn = '/'.join(parts[:3])
            if not self.has(cdn):
                if p['type'] == 'vpc':
                    a, b = p['nodes']
                    self.store.add(cdn, 'fabricProtPathEpCont', {'nodeAId': str(a), 'nodeBId': str(b)}, True)
                else:
                    self.store.add(cdn, 'fabricPathEpCont', {'nodeId': str(p['nodes'][0])}, True)
            self.store.add(dn, 'fabricPathEp', {'name': p['name'], 'pathT': 'leaf',
                                                'lagT': {'port': 'not-aggregated', 'pc': 'link',
                                                         'vpc': 'node'}[p['type']]}, True)

    def vlan_in_domain(self, dom, vlan, static=True):
        rs = dom + '/rsvlanNs'
        if not self.has(rs):
            return False
        pool = self.A(rs)['tDn']
        if not self.has(pool):
            return False
        pmode = self.A(pool)['allocMode']
        for b in self.kids(pool, 'fvnsEncapBlk'):
            a = self.A(b)
            f, t = vlan_num(a['from']), vlan_num(a['to'])
            if f is None or t is None:
                continue
            mode = pmode if a['allocMode'] == 'inherit' else a['allocMode']
            if f <= vlan <= t and (not static or mode == 'static'):
                return True
        return False

    # ------------------------------------------------------------------
    # Relationen auflösen
    # ------------------------------------------------------------------
    def _resolve(self):
        st = self.store
        for dn, (cls, a, oper) in list(st.objs.items()):
            meta = CLASSES[cls]
            if not meta.rel or oper:
                continue
            rel = meta.rel
            if rel[0] == 'name':
                attr, tcls, scope = rel[1], rel[2], rel[3]
                name = a.get(attr) or 'default'
                rn = CLASSES[tcls].rn.format(name=name)
                if scope == 'tenant':
                    tn = tenant_of(dn)
                    cands = [tn + '/' + rn, 'uni/tn-common/' + rn] if tn else []
                else:
                    cands = ['uni/infra/' + rn]
                tgt = next((c for c in cands if c in st.objs and st.objs[c][0] == tcls), '')
                a['tDn'] = tgt
                a['tCl'] = tcls
                a['state'] = 'formed' if tgt else 'missing-target'
                a['stateQual'] = ('default-target' if not a.get(attr) else 'none') if tgt else 'target-not-found'
                if not tgt and cls not in ('fvRsBd', 'fvRsCtx', 'l3extRsEctx'):
                    self.fault(dn, 'S1123', 'warning',
                               'Failed to form relation to MO %s of class %s' % (cands[0] if cands else name, tcls),
                               'resolution-failed')
            else:
                t = a.get('tDn', '')
                o = st.objs.get(t)
                ok = o is not None and o[0] in rel[2]
                a['tCl'] = o[0] if o else rel[2][0]
                a['state'] = 'formed' if ok else 'missing-target'
                a['stateQual'] = 'none' if ok else 'target-not-found'
                if not ok and cls not in ('fvRsPathAtt', 'l3extRsPathL3OutAtt'):
                    self.fault(dn, 'S1123', 'warning',
                               'Failed to form relation to MO %s of class %s' % (t or '(leer)', rel[2][0]),
                               'resolution-failed', domain='tenant' if tenant_of(dn) else 'access')

    # ------------------------------------------------------------------
    # EPGs, External EPGs und Contracts als "Klassen" (pcTags)
    # ------------------------------------------------------------------
    def _rs_targets(self, dn, cls):
        return [self.A(r)['tDn'] for r in self.kids(dn, cls) if self.A(r)['state'] == 'formed']

    def _classes(self):
        self.cls = {}
        for dn in self.store.by_class('fvAEPg'):
            a = self.A(dn)
            bd = self.A(dn + '/rsbd')['tDn'] if self.has(dn + '/rsbd') else ''
            vrf = self.A(bd + '/rsctx')['tDn'] if bd and self.has(bd + '/rsctx') else ''
            a['scope'] = self.A(vrf)['scope'] if vrf else ''
            self.cls[dn] = {'dn': dn, 'kind': 'epg', 'name': a['name'], 'tenant': tenant_of(dn),
                            'ap': parent_dn(dn), 'bd': bd, 'vrf': vrf, 'pcTag': a['pcTag'],
                            'prov': self._rs_targets(dn, 'fvRsProv'),
                            'cons': self._rs_targets(dn, 'fvRsCons'),
                            'pref': a['prefGrMemb'] == 'include',
                            'isolation': a['pcEnfPref'] == 'enforced'}
        for dn in self.store.by_class('l3extInstP'):
            a = self.A(dn)
            out = parent_dn(dn)
            vrf = self.A(out + '/rsectx')['tDn'] if self.has(out + '/rsectx') else ''
            a['scope'] = self.A(vrf)['scope'] if vrf else ''
            self.cls[dn] = {'dn': dn, 'kind': 'ext', 'name': a['name'], 'tenant': tenant_of(dn),
                            'ap': None, 'bd': None, 'vrf': vrf, 'pcTag': a['pcTag'], 'out': out,
                            'prov': self._rs_targets(dn, 'fvRsProv'),
                            'cons': self._rs_targets(dn, 'fvRsCons'),
                            'pref': a['prefGrMemb'] == 'include', 'isolation': False}
        for dn in self.store.by_class('fvBD'):
            vrf = self.A(dn + '/rsctx')['tDn'] if self.has(dn + '/rsctx') else ''
            self.A(dn)['scope'] = self.A(vrf)['scope'] if vrf else ''
        self.contracts = {}
        for dn, c in self.cls.items():
            for k in ('prov', 'cons'):
                for brc in c[k]:
                    self.contracts.setdefault(brc, {'prov': set(), 'cons': set(), 'prov_any': set(),
                                                    'cons_any': set()})[k].add(dn)
        for vrf in self.store.by_class('fvCtx'):
            anyd = vrf + '/any'
            if not self.has(anyd):
                continue
            for brc in self._rs_targets(anyd, 'vzRsAnyToProv'):
                self.contracts.setdefault(brc, {'prov': set(), 'cons': set(), 'prov_any': set(),
                                                'cons_any': set()})['prov_any'].add(vrf)
            for brc in self._rs_targets(anyd, 'vzRsAnyToCons'):
                self.contracts.setdefault(brc, {'prov': set(), 'cons': set(), 'prov_any': set(),
                                                'cons_any': set()})['cons_any'].add(vrf)

    # ------------------------------------------------------------------
    # EPG-Deployment (Static Ports)
    # ------------------------------------------------------------------
    def _epgs(self):
        self.deploys = []
        self.leaf_vlans = {}      # nid -> {vlan: epg}
        self.dep_bd = {}          # nid -> set(bd)
        self.dep_vrf = {}         # nid -> set(vrf)
        binds = []
        for dn, c in self.cls.items():
            if c['kind'] != 'epg':
                continue
            a = self.A(dn)
            if not c['bd'] or self.A(dn + '/rsbd')['state'] != 'formed':
                self.fault(dn, 'S0523', 'minor',
                           'Configuration failed for EPG %s due to Bridge Domain not present, debug message: '
                           'bd-not-present: BD %s not found' % (a['name'], (self.A(dn + '/rsbd') or {}).get('tnFvBDName', '')),
                           'bd-not-present')
            elif not c['vrf']:
                self.fault(c['bd'], 'S0956', 'minor',
                           'Bridge Domain %s is not associated with a valid VRF (ctx-not-present)'
                           % self.A(c['bd'])['name'], 'ctx-not-present')
            doms = self._rs_targets(dn, 'fvRsDomAtt')
            for rs in self.kids(dn, 'fvRsPathAtt'):
                binds.append((self.A(rs).get('modTs', ''), rs, dn, c, doms))
        binds.sort(key=lambda x: (x[0], x[1]))
        for _, rs, dn, c, doms in binds:
            self._bind(rs, dn, c, doms)

    def _epg_fault(self, dn, reason, text):
        name = self.A(dn)['name']
        titles = {'invalid-vlan': 'Invalid VLAN Configuration', 'invalid-path': 'Invalid Path Configuration',
                  'encap-already-in-use': 'Encap Already Used in Another EPG'}
        self.fault(dn, 'F0467', 'minor', 'Configuration failed for EPG %s due to %s, debug message: %s: %s'
                   % (name, titles[reason], reason, text), 'configuration-failed', rule='fv-nw-issues-config-failed')

    def _bind(self, rs, dn, c, doms):
        ra = self.A(rs)
        tdn, vlan, mode = ra['tDn'], vlan_num(ra['encap']), ra['mode']
        path = self.paths.get(tdn)
        if self.A(dn)['shutdown'] == 'yes':
            return
        if path is None:
            self._epg_fault(dn, 'invalid-path', '%s :: Path is not present in the fabric' % tdn)
            return
        if path.get('member_of'):
            self._epg_fault(dn, 'invalid-path', '%s :: Port is a member of port-channel/vPC %s'
                            % (tdn, path['member_of']))
            return
        if vlan is None:
            self._epg_fault(dn, 'invalid-vlan', '%s :: Encap is missing' % tdn)
            return
        dom_vlan = [d for d in doms if self.vlan_in_domain(d, vlan)]
        if not dom_vlan:
            self._epg_fault(dn, 'invalid-vlan', 'vlan-%d :: Either the EpG is not associated with a domain or '
                            'the domain does not have this vlan assigned to it' % vlan)
            return
        pgdoms = self._pg_info(path['pg'])['domains'] if path['pg'] else []
        if not [d for d in dom_vlan if d in pgdoms]:
            self._epg_fault(dn, 'invalid-path', 'vlan-%d :: Either the EpG/L3Out is not associated with a domain '
                            'or the domain does not have this interface assigned to it' % vlan)
            return
        for nid in path['nodes']:
            other = self.leaf_vlans.get(nid, {}).get(vlan)
            if other and other != dn:
                parts = split_dn(other)
                self._epg_fault(dn, 'encap-already-in-use', 'Encap (vlan-%d) is already in use by %s:%s:%s'
                                % (vlan, parts[1][3:], parts[2][3:], parts[3][4:]))
                return
        if not c['bd'] or not c['vrf']:
            return
        dep = {'epg': dn, 'bd': c['bd'], 'vrf': c['vrf'], 'path': tdn, 'legs': path['legs'],
               'nodes': path['nodes'], 'vlan': vlan, 'mode': mode, 'type': path['type']}
        self.deploys.append(dep)
        for nid in path['nodes']:
            self.leaf_vlans.setdefault(nid, {})[vlan] = dn
            self.dep_bd.setdefault(nid, set()).add(c['bd'])
            self.dep_vrf.setdefault(nid, set()).add(c['vrf'])
        for leg in path['legs']:
            if leg in self.ports:
                self.ports[leg]['usage'].add('epg')
                self.ports[leg]['vlans'].add(vlan)

    # ------------------------------------------------------------------
    # Hosts: Port-Channel/LACP, Endpoint-Learning
    # ------------------------------------------------------------------
    def bd_subnets(self, bd):
        out = []
        for s in self.kids(bd, 'fvSubnet'):
            a = self.A(s)
            n = net_of(a['ip'])
            if n:
                out.append({'ip': a['ip'], 'gw': str(ip_of(a['ip'])), 'net': n, 'scope': a['scope'], 'dn': s})
        return out

    def epg_subnets(self, epg):
        return self.bd_subnets(epg)

    def _endpoints(self):
        self.hosts = {}
        for h in self.sim.get('hosts', []):
            hs = {'name': h['name'], 'learned': False, 'ipLearned': False, 'reasons': [], 'legs': [],
                  'path': None, 'epg': None, 'bd': None, 'vrf': None, 'nodes': [], 'linkdown': []}
            self.hosts[h['name']] = hs
            legs = []
            for s, p in h.get('links', []):
                nid = self.serial_active.get(s)
                if nid is None:
                    hs['reasons'].append('Switch %s ist nicht aktiv (nicht registriert oder noch in Discovery)'
                                         % self.node_label(s))
                    continue
                legs.append((nid, p))
            hs['legs'] = legs
            if not legs:
                continue
            bond = h.get('bond', 'none')
            pgs = {self.ports[l]['pg'] for l in legs if l in self.ports}
            pg = pgs.pop() if len(pgs) == 1 else None
            info = self._pg_info(pg) if pg else None
            path, down_reason = None, None
            if info and info['cls'] == 'infraAccBndlGrp':
                cand = [d for d, p in self.paths.items() if p['pg'] == pg and p['type'] in ('pc', 'vpc')
                        and set(legs) <= set(p['legs'])]
                aci = info['lacp']
                aci_lacp = aci in ('active', 'passive')
                if bond in ('lacp-active', 'lacp-passive'):
                    if not aci_lacp:
                        down_reason = ('suspended', 'LACP: Host sendet LACP-PDUs, die Port-Channel-Policy der ACI '
                                       'steht auf mode %s (statisch) - Host suspendiert seine Links' % aci)
                    elif bond == 'lacp-passive' and aci == 'passive':
                        down_reason = ('suspended', 'LACP: beide Seiten passive - kein Bundle')
                elif aci_lacp:
                    down_reason = ('suspended-due-to-no-lacp-pdus',
                                   'LACP: ACI erwartet LACP-PDUs (mode %s), der Host sendet keine' % aci)
                if cand:
                    path = cand[0]
                elif len(legs) > 1:
                    hs['reasons'].append('Die Host-Links liegen nicht im selben Port-Channel/vPC-Pfad')
            else:
                if bond in ('lacp-active', 'lacp-passive'):
                    down_reason = ('suspended', 'LACP: Host erwartet einen Port-Channel, die ACI-Ports haben aber '
                                   'keine PC/vPC-Policy-Gruppe')
                path = '%s/paths-%d/pathep-[%s]' % (self.poddn, legs[0][0], legs[0][1])
            if down_reason:
                for l in legs:
                    if l in self.ports:
                        self.ports[l]['oper'] = 'down' if down_reason[0] == 'suspended' else 'up'
                        self.ports[l]['qual'] = down_reason[0]
                        hs['linkdown'].append(l)
                hs['reasons'].append(down_reason[1])
                continue
            hs['path'] = path
            if path is None:
                continue
            p = self.paths.get(path, {})
            if p.get('type') in ('pc', 'vpc'):
                for l in legs:
                    self.ports[l]['usage'].add('epg' if self.ports[l]['usage'] else 'discovery')
            vlan = int(h.get('vlan') or 0)
            cands = [d for d in self.deploys if d['path'] == path]
            match = None
            for d in cands:
                if vlan == 0 and d['mode'] in ('untagged', 'native'):
                    match = d
                elif vlan and d['vlan'] == vlan and d['mode'] in ('regular', 'native'):
                    match = d
                if match:
                    break
            if not match:
                if cands:
                    have = ', '.join('vlan-%d (%s)' % (d['vlan'], {'regular': 'Trunk', 'native': 'Access 802.1P',
                                                                    'untagged': 'Access untagged'}[d['mode']])
                                     for d in cands)
                    hs['reasons'].append('Auf %s ist %s deployed, der Host sendet %s'
                                         % (self.path_label(path), have, 'vlan-%d' % vlan if vlan else 'untagged'))
                else:
                    hs['reasons'].append('Auf %s ist keine EPG deployed (Static Port fehlt oder ist fehlerhaft - '
                                         'Faults pruefen)' % self.path_label(path))
                continue
            bd = match['bd']
            bda = self.A(bd)
            ip = ip_of(h['ip'])
            subs = self.bd_subnets(bd) + self.bd_subnets(match['epg'])
            in_sub = any(ip in s['net'] for s in subs)
            ip_learn = bda['unicastRoute'] == 'yes' and (in_sub or bda['limitIpLearnToSubnets'] == 'no')
            hs.update({'learned': True, 'ipLearned': ip_learn, 'epg': match['epg'], 'bd': bd,
                       'vrf': match['vrf'], 'nodes': match['nodes'], 'encap': 'vlan-%d' % match['vlan'],
                       'dep': match})
            if not ip_learn:
                hs['reasons'].append('IP %s wird nicht gelernt (%s)' % (
                    ip, 'Unicast Routing im BD aus' if bda['unicastRoute'] != 'yes'
                    else 'IP liegt in keinem BD-Subnetz und "Limit IP Learning to Subnet" ist aktiv'))
            mac = h['mac'].upper()
            cep = match['epg'] + '/cep-' + mac
            self.store.add(cep, 'fvCEp', {'mac': mac, 'name': mac, 'ip': str(ip) if ip_learn else '0.0.0.0',
                                          'encap': 'vlan-%d' % match['vlan'], 'lcC': 'learned',
                                          'fabricPathDn': path, 'id': '0', 'mcastAddr': 'not-applicable',
                                          'contName': '', 'baseEpgDn': ''}, True)
            if ip_learn:
                self.store.add(cep + '/ip-[%s]' % ip, 'fvIp', {'addr': str(ip), 'createTs': now_ts()}, True)
            self.store.add(cep + '/rscEpToPathEp-[%s]' % path, 'fvRsCEpToPathEp',
                           {'tDn': path, 'state': 'formed', 'lcC': 'learned'}, True)

    # ------------------------------------------------------------------
    # L3Out: Interfaces, Nachbarn, Routen
    # ------------------------------------------------------------------
    def fabric_asn(self):
        a = self.A('uni/fabric/bgpInstP-default/as')
        return a['asn'] if a and a.get('asn') else None

    def mpbgp(self):
        asn = self.fabric_asn()
        rr = [int(self.A(n)['id']) for n in self.kids('uni/fabric/bgpInstP-default/rr', 'bgpRRNodePEp')]
        rr_ok = [i for i in rr if self.nodes.get(i, {}).get('state') == 'active'
                 and self.nodes[i]['role'] == 'spine']
        return bool(asn and rr_ok), asn, rr

    def _ospf_pol(self, lif):
        rs = lif + '/ospfIfP/rsIfPol'
        t = self.A(rs)['tDn'] if self.has(rs) else 'uni/tn-common/ospfIfPol-default'
        return self.A(t) or self.A('uni/tn-common/ospfIfPol-default') or {}

    def _l3outs(self):
        self.l3if, self.outs = [], {}
        self.routes = {}       # (vrf, nid) -> [route]
        self.ext_class = {}    # vrf -> [(net, instP)]
        self.routers = {}
        for out in self.store.by_class('l3extOut'):
            a = self.A(out)
            vrf = self.A(out + '/rsectx')['tDn'] if self.has(out + '/rsectx') else ''
            drs = out + '/rsl3DomAtt'
            dom = self.A(drs)['tDn'] if self.has(drs) and self.A(drs)['state'] == 'formed' else ''
            if not vrf:
                self.fault(out, 'S0956', 'minor', 'L3Out %s is not associated with a valid VRF' % a['name'],
                           'ctx-not-present')
            o = {'dn': out, 'name': a['name'], 'vrf': vrf, 'dom': dom, 'ospf': self.A(out + '/ospfExtP'),
                 'bgp': self.has(out + '/bgpExtP'), 'nodes': {}, 'ifs': []}
            self.outs[out] = o
            for np in self.kids(out, 'l3extLNodeP'):
                for rn in self.kids(np, 'l3extRsNodeL3OutAtt'):
                    ra = self.A(rn)
                    m = re.search(r'/node-(\d+)$', ra['tDn'])
                    if not m:
                        continue
                    nid = int(m.group(1))
                    if not ra['rtrId']:
                        self.fault(rn, 'S3089', 'warning', 'Router ID is not configured for node %d' % nid,
                                   'rtrid-missing')
                    statics = []
                    for rt in self.kids(rn, 'ipRouteP'):
                        statics.append({'prefix': self.A(rt)['ip'],
                                        'nhs': [self.A(n)['nhAddr'] for n in self.kids(rt, 'ipNexthopP')]})
                    o['nodes'][nid] = {'dn': rn, 'rtrId': ra['rtrId'], 'statics': statics,
                                       'peers': [self.A(p)['addr'] for p in self.kids(np, 'bgpPeerP')],
                                       'np': np}
                for lif in self.kids(np, 'l3extLIfP'):
                    ospf_if = self.has(lif + '/ospfIfP')
                    pol = self._ospf_pol(lif)
                    for ri in self.kids(lif, 'l3extRsPathL3OutAtt'):
                        self._l3if(o, np, lif, ri, ospf_if, pol)
            for ip in self.kids(out, 'l3extInstP'):
                for s in self.kids(ip, 'l3extSubnet'):
                    sa = self.A(s)
                    if 'import-security' in sa['scope'].split(',') and vrf:
                        n = net_of(sa['ip'])
                        if n:
                            self.ext_class.setdefault(vrf, []).append((n, ip))
        for r in self.sim.get('routers', []):
            self._router(r)
        # Verteilung der externen Routen per MP-BGP
        ok, asn, rr = self.mpbgp()
        self.mpbgp_ok = ok
        border = {}
        for (vrf, nid), rts in list(self.routes.items()):
            for rt in rts:
                if rt['proto'] in ('ospf', 'bgp', 'static', 'direct'):
                    border.setdefault(vrf, []).append((nid, rt))
        if ok:
            for vrf, items in border.items():
                for leaf in self.leaf_ids:
                    if self.nodes.get(leaf, {}).get('state') != 'active':
                        continue
                    if vrf not in self.dep_vrf.get(leaf, set()):
                        continue
                    for nid, rt in items:
                        if nid == leaf:
                            continue
                        self.routes.setdefault((vrf, leaf), []).append(
                            {'prefix': rt['prefix'], 'nh': self.nodes[nid]['tep'], 'proto': 'bgp',
                             'via': 'overlay-1', 'border': nid, 'router': rt.get('router'), 'pref': 200})

    def _l3if(self, o, np, lif, ri, ospf_if, pol):
        ia = self.A(ri)
        name = o['name']
        path = self.paths.get(ia['tDn'])
        if path is None:
            self.fault(o['dn'], 'F0467', 'minor', 'Configuration failed for L3Out %s due to Invalid Path '
                       'Configuration, debug message: invalid-path: %s :: Path is not present' % (name, ia['tDn']),
                       'configuration-failed')
            return
        nid = path['nodes'][0]
        vlan = vlan_num(ia['encap'])
        typ = ia['ifInstT']
        err = None
        if nid not in o['nodes']:
            err = ('S', 'Node %d of interface %s is not part of the logical node profile' % (nid, path['name']))
        elif not o['dom']:
            err = ('invalid-path', 'Either the EpG/L3Out is not associated with a domain or the domain does not '
                   'have this interface assigned to it')
        elif o['dom'] not in (self._pg_info(path['pg'])['domains'] if path['pg'] else []):
            err = ('invalid-path', 'Either the EpG/L3Out is not associated with a domain or the domain does not '
                   'have this interface assigned to it')
        elif typ != 'l3-port' and vlan is None:
            err = ('invalid-vlan', 'Encap is missing for %s' % typ)
        elif typ != 'l3-port' and not self.vlan_in_domain(o['dom'], vlan):
            err = ('invalid-vlan', 'vlan-%d :: Either the EpG/L3Out is not associated with a domain or the domain '
                   'does not have this vlan assigned to it' % vlan)
        elif ia['addr'] in ('', '0.0.0.0'):
            err = ('S', 'No IP address configured on %s' % path['name'])
        if err:
            if err[0] == 'S':
                self.fault(ri, 'S0468', 'minor', err[1], 'l3if-config-failed')
            else:
                self.fault(o['dn'], 'F0467', 'minor', 'Configuration failed for L3Out %s due to Invalid %s '
                           'Configuration, debug message: %s: %s' % (
                               name, 'Path' if err[0] == 'invalid-path' else 'VLAN', err[0], err[1]),
                           'configuration-failed')
            return
        mtu = 9000 if ia['mtu'] == 'inherit' else int(ia['mtu'])
        peers = []
        for p in self.kids(ri, 'bgpPeerP'):
            pa = self.A(p)
            asp = self.A(p + '/as')
            lasp = self.A(p + '/localasn')
            peers.append({'addr': pa['addr'], 'remoteAs': asp['asn'] if asp else '',
                          'localAs': lasp['localAsn'] if lasp and lasp.get('localAsn') else None, 'dn': p})
        iface = {'out': o['dn'], 'vrf': o['vrf'], 'nid': nid, 'legs': path['legs'], 'path': ia['tDn'],
                 'type': typ, 'vlan': vlan, 'addr': ia['addr'], 'net': net_of(ia['addr']), 'mtu': mtu,
                 'ospf': bool(o['ospf']) and ospf_if, 'pol': pol, 'peers': peers, 'dn': ri, 'lif': lif}
        o['ifs'].append(iface)
        self.l3if.append(iface)
        for l in path['legs']:
            if l in self.ports:
                self.ports[l]['usage'].add('epg')
                if typ == 'l3-port':
                    self.ports[l]['layer'] = 'Layer3'
        if o['vrf']:
            self.dep_vrf.setdefault(nid, set()).add(o['vrf'])
            self.routes.setdefault((o['vrf'], nid), []).append(
                {'prefix': str(iface['net']), 'nh': str(ip_of(ia['addr'])), 'proto': 'direct',
                 'via': self.if_name(iface), 'pref': 0})

    def if_name(self, iface):
        port = iface['legs'][0][1] if iface['legs'] else '?'
        if iface['type'] == 'sub-interface':
            return '%s.%s' % (port, iface['vlan'])
        if iface['type'] == 'ext-svi':
            return 'vlan%d' % iface['vlan']
        return port

    def exported_subnets(self, out, nid):
        """BD-Subnetze, die die ACI über dieses L3Out ankündigt."""
        o = self.outs[out]
        res = []
        for bd in self.store.by_class('fvBD'):
            if (self.A(bd + '/rsctx') or {}).get('tDn') != o['vrf']:
                continue
            outs = self._rs_targets(bd, 'fvRsBDToOut')
            if out not in outs:
                continue
            subs = [s for s in self.bd_subnets(bd) if 'public' in s['scope'].split(',')]
            if not subs:
                continue
            if not self.bd_on_border(bd, out, nid):
                continue
            res.extend(str(s['net']) for s in subs)
        return res

    def bd_on_border(self, bd, out, nid):
        if bd in self.dep_bd.get(nid, set()):
            return True
        exts = [d for d, c in self.cls.items() if c['kind'] == 'ext' and c.get('out') == out]
        epgs = [d for d, c in self.cls.items() if c['kind'] == 'epg' and c['bd'] == bd]
        for brc, rel in self.contracts.items():
            e = any(x in rel['prov'] or x in rel['cons'] for x in exts)
            g = any(x in rel['prov'] or x in rel['cons'] for x in epgs)
            if e and g:
                return True
        return False

    def _router(self, r):
        rs = {'name': r['name'], 'link': False, 'state': 'down', 'reasons': [], 'iface': None,
              'learned': [], 'proto': r.get('protocol', 'static'), 'adj': '-'}
        self.routers[r['name']] = rs
        nid = self.serial_active.get(r.get('serial'))
        if nid is None:
            rs['reasons'].append('Switch %s ist nicht aktiv' % self.node_label(r.get('serial')))
            return
        vlan = int(r.get('vlan') or 0)
        cand = [i for i in self.l3if if (nid, r['port']) in i['legs']]
        iface = None
        for i in cand:
            if (vlan == 0 and i['type'] == 'l3-port') or (vlan and i['vlan'] == vlan and i['type'] != 'l3-port'):
                iface = i
                break
        if iface is None:
            if cand:
                rs['reasons'].append('L3Out-Interface auf %s passt nicht zum Router (Typ/VLAN: ACI %s, Router %s)'
                                     % (r['port'], ', '.join('%s%s' % (i['type'], ' vlan-%s' % i['vlan'] if i['vlan']
                                                                       else '') for i in cand),
                                        'vlan-%d' % vlan if vlan else 'untagged/routed'))
            else:
                rs['reasons'].append('Kein funktionierendes L3Out-Interface auf %s %s (Konfiguration/Faults pruefen)'
                                     % (self.nodes[nid]['name'], r['port']))
            return
        rs['iface'] = iface
        rip = ip_of(r['ip'])
        if iface['net'] is None or rip not in iface['net'] or rip == ip_of(iface['addr']):
            rs['reasons'].append('IP-Subnetz passt nicht: ACI %s, Router %s' % (iface['addr'], r['ip']))
            return
        rs['link'] = True
        rs['state'] = 'up'
        o = self.outs[iface['out']]
        vrf, nid = o['vrf'], iface['nid']
        installed = []
        proto = r.get('protocol', 'static')
        if proto == 'ospf':
            st_, why = self._ospf_state(r, iface, o)
            rs['adj'] = st_
            if why:
                rs['reasons'].append(why)
            if st_ == 'FULL' and not why:
                installed = [(p, 'ospf') for p in r.get('advertise', [])]
                rs['learned'] = self.exported_subnets(o['dn'], nid)
                if not rs['learned']:
                    rs['reasons'].append('ACI kuendigt dem Router keine BD-Subnetze an')
        elif proto == 'bgp':
            st_, why = self._bgp_state(r, iface, o)
            rs['adj'] = st_
            if why:
                rs['reasons'].append(why)
            if st_ == 'Established':
                installed = [(p, 'bgp') for p in r.get('advertise', [])]
                rs['learned'] = self.exported_subnets(o['dn'], nid)
                if not rs['learned']:
                    rs['reasons'].append('ACI kuendigt dem Router keine BD-Subnetze an')
        else:
            rs['adj'] = 'static'
        for p in r.get('staticBack', []):
            if p not in rs['learned']:
                rs['learned'].append(p)
        node = o['nodes'].get(nid, {})
        for s in node.get('statics', []):
            if str(rip) in s['nhs']:
                installed.append((s['prefix'], 'static'))
        if vrf:
            for p, pr in installed:
                self.routes.setdefault((vrf, nid), []).append(
                    {'prefix': p, 'nh': str(rip), 'proto': pr, 'via': self.if_name(iface), 'router': r['name'],
                     'pref': {'static': 1, 'ospf': 110, 'bgp': 20}[pr]})

    def _ospf_state(self, r, iface, o):
        if not o['ospf']:
            return 'DOWN', 'OSPF ist im L3Out nicht aktiviert'
        if not iface['ospf']:
            return 'DOWN', 'Am Logical Interface Profile fehlt das OSPF Interface Profile'
        ro = r.get('ospf', {})
        if norm_area(o['ospf']['areaId']) != norm_area(ro.get('area', '0.0.0.0')):
            return 'DOWN', None
        if o['ospf']['areaType'] != ro.get('areaType', 'regular'):
            return 'DOWN', None
        pol = iface['pol']
        if str(pol.get('helloIntvl', '10')) != str(ro.get('hello', 10)) or \
                str(pol.get('deadIntvl', '40')) != str(ro.get('dead', 40)):
            return 'DOWN', None
        aci_nw = 'p2p' if pol.get('nwT') == 'p2p' else 'bcast'
        mtu_ign = 'mtu-ignore' in (pol.get('ctrl') or '').split(',') or ro.get('mtuIgnore')
        if iface['mtu'] != int(r.get('mtu', 1500)) and not mtu_ign:
            return 'EXSTART', None
        if aci_nw != ro.get('nwT', 'bcast'):
            return 'FULL', 'OSPF-Netzwerktyp unterschiedlich: Nachbarschaft FULL, aber Routen werden nicht installiert'
        return 'FULL', None

    def _bgp_state(self, r, iface, o):
        if not o['bgp']:
            return 'Idle', 'BGP ist im L3Out nicht aktiviert'
        rip = str(ip_of(r['ip']))
        peer = next((p for p in iface['peers'] if p['addr'] == rip), None)
        if peer is None:
            for n in o['nodes'].values():
                if rip in n['peers']:
                    return 'Idle', 'BGP-Peer ist am Node-Profil (Loopback) statt am Interface konfiguriert'
            return 'Idle', None
        fasn = self.fabric_asn()
        if not fasn:
            return 'Idle', None
        rb = r.get('bgp', {})
        local = peer['localAs'] or fasn
        if str(peer['remoteAs']) != str(rb.get('asn')):
            return 'Idle', None
        if str(rb.get('peerAs')) != str(local):
            return 'Idle', None
        return 'Established', None

    # ------------------------------------------------------------------
    # Ports ausgeben
    # ------------------------------------------------------------------
    def _emit_ports(self):
        for (nid, port), pi in sorted(self.ports.items(), key=lambda x: (x[0][0], pnum(x[0][1]) or 0)):
            n = self.nodes[nid]
            base = '%s/node-%d/sys/phys-[%s]' % (self.poddn, nid, port)
            usage = ','.join(sorted(pi['usage'])) or 'discovery'
            self.store.add(base, 'l1PhysIf', {'id': port, 'adminSt': 'up', 'usage': usage, 'mtu': '9000',
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
        seen = set()
        for dn, codes in self.faults.items():
            if dn not in self.store.objs:
                continue
            for code, f in codes.items():
                fdn = dn + '/fault-' + code
                key = (fdn, f['descr'])
                seen.add(fdn)
                first = self.fault_first.get(fdn)
                if not first or first[1] != f['descr']:
                    first = (now_ts(self.now), f['descr'])
                    self.fault_first[fdn] = first
                self.store.add(fdn, 'faultInst', {
                    'ack': 'no', 'cause': f['cause'], 'changeSet': '', 'code': code, 'created': first[0],
                    'descr': f['descr'], 'domain': f['domain'], 'highestSeverity': f['severity'],
                    'lastTransition': first[0], 'lc': 'raised', 'occur': '1', 'origSeverity': f['severity'],
                    'prevSeverity': f['severity'], 'rule': f['rule'] or f['cause'], 'severity': f['severity'],
                    'subject': CLASSES[self.store.objs[dn][0]].label, 'type': f['type']}, True)
                _ = key
        for k in list(self.fault_first):
            if k not in seen:
                del self.fault_first[k]

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
            out.append(re.sub(r'^(tn|ap|epg|BD|ctx|out|instP|brc|flt)-', '', p))
        return ':'.join(out)

    # ------------------------------------------------------------------
    # Contracts: Paketentscheidung
    # ------------------------------------------------------------------
    @staticmethod
    def _rng(p, f, t):
        fv, tv = port_val(f), port_val(t)
        if fv is None and tv is None:
            return True
        if p is None:
            return False
        fv = fv if fv is not None else tv
        tv = tv if tv is not None else fv
        return fv <= p <= tv

    def _entry_match(self, e, proto, sport, dport, flags, rev):
        if e['etherT'] not in ('unspecified', 'ip', 'ipv4'):
            return False
        if e['prot'] not in ('unspecified', proto):
            return False
        if proto in ('tcp', 'udp') and e['prot'] == proto:
            d = (e['dFromPort'], e['dToPort'])
            s = (e['sFromPort'], e['sToPort'])
            if rev:
                d, s = s, d
            if not self._rng(dport, *d) or not self._rng(sport, *s):
                return False
        if 'est' in (e.get('tcpRules') or '').split(',') and proto == 'tcp' and flags != 'ack':
            return False
        if 'est' in (e.get('tcpRules') or '').split(',') and proto != 'tcp':
            return False
        return True

    def packet(self, s, d, proto, sport, dport, flags):
        """Entscheidet ein einzelnes Paket von Klasse s nach Klasse d."""
        vrf = s['vrf']
        va = self.A(vrf) or {}
        if va.get('pcEnfPref') == 'unenforced':
            return 'permit', 'VRF %s steht auf "unenforced" - keine Policy-Pruefung' % self.short(vrf)
        if s['dn'] == d['dn']:
            if s.get('isolation'):
                return 'deny', 'Intra-EPG-Isolation ist aktiv'
            return 'permit', 'Quelle und Ziel in derselben EPG - kein Contract noetig'
        anya = self.A(vrf + '/any') or {}
        if anya.get('prefGrMemb') == 'enabled' and s['pref'] and d['pref']:
            return 'permit', 'Beide sind Mitglied der Preferred Group'
        hits = []
        for brc, rel in self.contracts.items():
            s_cons = s['dn'] in rel['cons'] or vrf in rel['cons_any']
            s_prov = s['dn'] in rel['prov'] or vrf in rel['prov_any']
            d_cons = d['dn'] in rel['cons'] or d['vrf'] in rel['cons_any']
            d_prov = d['dn'] in rel['prov'] or d['vrf'] in rel['prov_any']
            fwd, rev = s_cons and d_prov, s_prov and d_cons
            if not (fwd or rev):
                continue
            ca = self.A(brc)
            if ca['scope'] == 'application-profile' and (s['ap'] is None or s['ap'] != d['ap']):
                continue
            if ca['scope'] == 'context' and s['vrf'] != d['vrf']:
                continue
            if ca['scope'] == 'tenant' and s['tenant'] != d['tenant']:
                continue
            for subj in self.kids(brc, 'vzSubj'):
                sa = self.A(subj)
                for rf in self.kids(subj, 'vzRsSubjFiltAtt'):
                    rfa = self.A(rf)
                    if rfa['state'] != 'formed':
                        continue
                    for e in self.kids(rfa['tDn'], 'vzEntry'):
                        ea = self.A(e)
                        where = '%s / %s / %s / %s' % (self.short(brc), sa['name'], self.A(rfa['tDn'])['name'],
                                                       ea['name'])
                        if fwd and self._entry_match(ea, proto, sport, dport, flags, False):
                            hits.append((rfa['action'], where + ' (Consumer -> Provider)'))
                        if rev and self._entry_match(ea, proto, sport, dport, flags, sa['revFltPorts'] == 'yes'):
                            hits.append((rfa['action'], where + ' (Provider -> Consumer%s)'
                                         % (', Ports getauscht' if sa['revFltPorts'] == 'yes' else '')))
        deny = [h for h in hits if h[0] == 'deny']
        if deny:
            return 'deny', 'Deny-Filter: ' + deny[0][1]
        if hits:
            return 'permit', 'Contract: ' + hits[0][1]
        return 'deny', 'Implicit Deny: kein Contract mit passendem Filter zwischen %s und %s' % (
            self.short(s['dn']), self.short(d['dn']))
