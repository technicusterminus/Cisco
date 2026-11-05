"""Access Policies, Pfade, EPG-Deployment auf Ports und Leafs (Static Port, Static Leaf, L2Out)."""
import re

from .model import split_dn

from .engine_util import (vlan_num, pnum)


class AccessMixin:
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
            dn = '%s/paths-%d/pathep-[%s]' % (self.pdn(nid), nid, port)
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
                    dn = '%s/paths-%d/pathep-[%s]' % (self.pdn(nid), nid, info['name'])
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
                    dn = '%s/protpaths-%d-%d/pathep-[%s]' % (self.pdn(a), a, b, info['name'])
                    self.paths[dn] = {'type': 'vpc', 'legs': legs, 'pg': pg, 'nodes': [a, b], 'name': info['name']}
                if alone:
                    self.fault(pg, 'S0477', 'minor',
                               'vPC interface policy group is deployed on node(s) %s without vPC peer '
                               '(no explicit vPC protection group)' % ','.join(map(str, alone)),
                               'vpc-domain-missing', domain='access')
            for leg in legs_all:
                pdn = '%s/paths-%d/pathep-[%s]' % (self.pdn(leg[0]), leg[0], leg[1])
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

    def _ipn_paths(self):
        """Pfade der Spine- und Remote-Leaf-Ports zum IPN/WAN (fuer das Infra-L3Out)."""
        for s_, p_, _, _ in self.sim['topology'].get('ipnlinks', []):
            nid = self.serial_active.get(s_)
            if nid is None:
                continue
            cdn = '%s/paths-%d' % (self.pdn(nid), nid)
            self.store.add(cdn, 'fabricPathEpCont', {'nodeId': str(nid)}, True)
            self.store.add(cdn + '/pathep-[%s]' % p_, 'fabricPathEp', {'name': p_, 'pathT': 'leaf', 'lagT': 'not-aggregated'}, True)

    def _oos(self):
        self.oos = set()
        for r in self.kids('uni/fabric/outofsvc', 'fabricRsOosPath'):
            t = self.A(r)['tDn']
            p = self.paths.get(t)
            if not p:
                continue
            self.oos.add(t)
            for l in p['legs']:
                if l in self.ports:
                    self.ports[l].update({'admin': 'down', 'oper': 'down', 'qual': 'admin-down'})

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
        for dn, c in self.cls.items():
            if c['kind'] == 'epg':
                doms = self._rs_targets(dn, 'fvRsDomAtt')
                for rs in self.kids(dn, 'fvRsNodeAtt'):
                    self._node_bind(rs, dn, c, doms)
        for out in self.store.by_class('l2extOut'):
            self._l2out(out)

    def _l2out(self, out):
        name = self.A(out)['name']
        insts = self.kids(out, 'l2extInstP')
        rs = self.A(out + '/rseBd') or {}
        vlan = vlan_num(rs.get('encap'))
        drs = self.A(out + '/rsl2DomAtt') or {}
        dom = drs.get('tDn') if drs.get('state') == 'formed' else ''

        def flt(reason, text):
            self.fault(out, 'F0467', 'minor', 'Configuration failed for L2Out %s due to %s, debug message: %s: %s'
                       % (name, 'Invalid VLAN Configuration' if reason == 'invalid-vlan' else 'Invalid Path Configuration',
                          reason, text), 'configuration-failed')
        if not insts:
            return
        c = self.cls[insts[0]]
        if not c['bd']:
            self.fault(out, 'S0523', 'minor', 'L2Out %s has no valid Bridge Domain' % name, 'bd-not-present')
            return
        if vlan is None:
            flt('invalid-vlan', 'Encap is missing on the Bridge Domain association')
            return
        if not dom or not self.vlan_in_domain(dom, vlan):
            flt('invalid-vlan', 'vlan-%d :: Either the L2Out is not associated with a domain or the domain does not have '
                'this vlan assigned to it' % vlan)
            return
        for np in self.kids(out, 'l2extLNodeP'):
            for lif in self.kids(np, 'l2extLIfP'):
                for ri in self.kids(lif, 'l2extRsPathL2OutAtt'):
                    tdn = self.A(ri)['tDn']
                    path = self.paths.get(tdn)
                    if path is None or path.get('member_of'):
                        flt('invalid-path', '%s :: Path is not present' % tdn)
                        continue
                    if dom not in (self._pg_info(path['pg'])['domains'] if path['pg'] else []):
                        flt('invalid-path', 'Either the EpG/L2Out is not associated with a domain or the domain does not '
                            'have this interface assigned to it')
                        continue
                    other = [self.leaf_vlans.get(n, {}).get(vlan) for n in path['nodes']]
                    if any(o and o != c['dn'] for o in other):
                        flt('invalid-vlan', 'Encap (vlan-%d) is already in use' % vlan)
                        continue
                    self._deploy(c['dn'], c, tdn, path, vlan, 'regular')

    def _node_bind(self, rs, dn, c, doms):
        """Static Leaf: EPG auf allen Ports des Leafs, deren Access Policy die Domain enthaelt."""
        ra = self.A(rs)
        m = re.search(r'/node-(\d+)$', ra['tDn'])
        vlan = vlan_num(ra['encap'])
        if not m or self.A(dn)['shutdown'] == 'yes':
            return
        nid = int(m.group(1))
        if self.nodes.get(nid, {}).get('state') != 'active':
            return
        if vlan is None:
            self._epg_fault(dn, 'invalid-vlan', '%s :: Encap is missing' % ra['tDn'], 'node %d' % nid)
            return
        dom_vlan = [d for d in doms if self.vlan_in_domain(d, vlan)]
        if not dom_vlan:
            self._epg_fault(dn, 'invalid-vlan', 'vlan-%d :Either the EpG is not associated with a domain or the domain does not have this vlan assigned to it' % vlan, 'node %d' % nid)
            return
        other = self.leaf_vlans.get(nid, {}).get(vlan)
        if other and other != dn:
            parts = split_dn(other)
            self._epg_fault(dn, 'encap-already-in-use', 'Encap (vlan-%d) is already in use by %s:%s:%s'
                            % (vlan, parts[1][3:], parts[2][3:], parts[3][4:]), 'node %d' % nid)
            return
        done = {d['path'] for d in self.deploys if d['epg'] == dn}
        for pdn, p in sorted(self.paths.items()):
            if p['nodes'] != [nid] or p.get('member_of') or not p['pg'] or pdn in done:
                continue
            if not set(dom_vlan) & set(self._pg_info(p['pg'])['domains']):
                continue
            self._deploy(dn, c, pdn, p, vlan, ra['mode'])

    def _epg_fault(self, dn, reason, text, loc=''):
        """F0467 an der EPG. Format nach Cisco TechNote 220876 ("Troubleshoot Address ACI Fault Code F0467"):
        'Configuration failed for <EPG-DN> node <id> <port> due to <Titel>, debug message: <cause>: <Text>;'.
        Belegt sind die Texte fuer invalid-vlan, invalid-path und encap-already-in-use; andere Texte sind simulator-spezifisch."""
        titles = {'invalid-vlan': 'Invalid VLAN Configuration', 'invalid-path': 'Invalid Path Configuration',
                  'encap-already-in-use': 'Encap Already Used in Another EPG'}
        self.fault(dn, 'F0467', 'minor', 'Configuration failed for %s%s due to %s, debug message: %s: %s;'
                   % (dn, ' ' + loc if loc else '', titles[reason], reason, text), 'configuration-failed',
                   rule='fv-nw-issues-config-failed')

    def _bind(self, rs, dn, c, doms):
        ra = self.A(rs)
        tdn, vlan, mode = ra['tDn'], vlan_num(ra['encap']), ra['mode']
        path = self.paths.get(tdn)
        if self.A(dn)['shutdown'] == 'yes':
            return
        if path is None:
            self._epg_fault(dn, 'invalid-path', '%s :: Path is not present in the fabric' % tdn)
            return
        loc = 'node %s %s' % ('-'.join(str(n) for n in path['nodes']), path['name'])
        if path.get('member_of'):
            self._epg_fault(dn, 'invalid-path', '%s :: Port is a member of port-channel/vPC %s'
                            % (tdn, path['member_of']), loc)
            return
        if vlan is None:
            self._epg_fault(dn, 'invalid-vlan', '%s :: Encap is missing' % tdn, loc)
            return
        dom_vlan = [d for d in doms if self.vlan_in_domain(d, vlan)]
        if not dom_vlan:
            self._epg_fault(dn, 'invalid-vlan', 'vlan-%d :Either the EpG is not associated with a domain or the domain does not have this vlan assigned to it' % vlan, loc)
            return
        pgdoms = self._pg_info(path['pg'])['domains'] if path['pg'] else []
        if not [d for d in dom_vlan if d in pgdoms]:
            self._epg_fault(dn, 'invalid-path', 'Either the EpG/L3Out is not associated with a domain or the domain does not have this interface assigned to it', loc)
            return
        for nid in path['nodes']:
            other = self.leaf_vlans.get(nid, {}).get(vlan)
            if other and other != dn:
                parts = split_dn(other)
                self._epg_fault(dn, 'encap-already-in-use', 'Encap (vlan-%d) is already in use by %s:%s:%s'
                                % (vlan, parts[1][3:], parts[2][3:], parts[3][4:]), loc)
                return
        self._deploy(dn, c, tdn, path, vlan, mode)

    def _deploy(self, dn, c, tdn, path, vlan, mode):
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
