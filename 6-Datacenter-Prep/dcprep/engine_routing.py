"""L3Outs, Nachbarschaften externer Router, Routen, Route Control und Leaking."""
import ipaddress
import re

from .engine_util import (vlan_num, net_of, ip_of, norm_area)


class RoutingMixin:
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
            if out.startswith('uni/tn-infra/'):
                continue
            a = self.A(out)
            vrf = self.A(out + '/rsectx')['tDn'] if self.has(out + '/rsectx') else ''
            drs = out + '/rsl3DomAtt'
            dom = self.A(drs)['tDn'] if self.has(drs) and self.A(drs)['state'] == 'formed' else ''
            if not vrf:
                self.fault(out, 'S0956', 'minor', 'L3Out %s is not associated with a valid VRF' % a['name'],
                           'ctx-not-present')
            o = {'dn': out, 'name': a['name'], 'vrf': vrf, 'dom': dom, 'ospf': self.A(out + '/ospfExtP'),
                 'bgp': self.has(out + '/bgpExtP'), 'nodes': {}, 'ifs': [], 'eigrp': self.A(out + '/eigrpExtP'),
                 'enforce': set((a.get('enforceRtctrl') or 'export').split(',')) | {'export'}}
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
                        rta = self.A(rt)
                        trk = (self.A(rt + '/rsRouteTrack') or {})
                        nhs = []
                        for n in self.kids(rt, 'ipNexthopP'):
                            na = self.A(n)
                            ntrk = (self.A(n + '/rsNexthopRouteTrack') or {})
                            nhs.append({'addr': na['nhAddr'], 'pref': int(na['pref']) if str(na['pref']).isdigit() else int(rta['pref'] or 1),
                                        'track': ntrk.get('tDn') if ntrk.get('state') == 'formed' else None})
                        statics.append({'prefix': rta['ip'], 'pref': int(rta['pref'] or 1), 'nhs': nhs, 'dn': rt,
                                        'track': trk.get('tDn') if trk.get('state') == 'formed' else None,
                                        'bfd': 'bfd' in (rta.get('rtCtrl') or '').split(',')})
                    o['nodes'][nid] = {'dn': rn, 'rtrId': ra['rtrId'], 'statics': statics,
                                       'peers': [self._peer(p) for p in self.kids(np, 'bgpPeerP')],
                                       'np': np}
                for lif in self.kids(np, 'l3extLIfP'):
                    ospf_if = self.has(lif + '/ospfIfP')
                    pol = self._ospf_pol(lif)
                    for ri in self.kids(lif, 'l3extRsPathL3OutAtt'):
                        self._l3if(o, np, lif, ri, ospf_if, pol)
                    for vi in self.kids(lif, 'l3extVirtualLIfP'):
                        self._float_if(o, lif, vi, ospf_if, pol)
            for ip in self.kids(out, 'l3extInstP'):
                for s in self.kids(ip, 'l3extSubnet'):
                    sa = self.A(s)
                    if 'import-security' in sa['scope'].split(',') and vrf:
                        n = net_of(sa['ip'])
                        if n:
                            self.ext_class.setdefault(vrf, []).append((n, ip))
        for r in self.sim.get('routers', []):
            self._router(r)
        self._statics()
        # Verteilung der externen Routen per MP-BGP
        ok, asn, rr = self.mpbgp()
        self.mpbgp_ok = ok
        border = {}
        for (vrf, nid), rts in list(self.routes.items()):
            for rt in rts:
                if rt['proto'] in ('ospf', 'bgp', 'static', 'direct', 'eigrp'):
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
        self._exports()

    # ------------------------------------------------------------------
    # Route Control: Import/Export Route Control Subnets und Route-Profile
    # ------------------------------------------------------------------
    @staticmethod
    def _pfx_in(prefix, net, agg, lo=None, hi=None):
        try:
            p = ipaddress.ip_network(prefix, strict=False)
        except ValueError:
            return False
        if not agg:
            return p == net
        if p.version != net.version or not p.subnet_of(net):
            return False
        lo = lo if lo else net.prefixlen
        hi = hi if hi else 32
        return lo <= p.prefixlen <= hi

    def rt_permit(self, o, direction, prefix):
        """(erlaubt, Begruendung) fuer eine Route und Richtung import/export am L3Out o."""
        key = direction + '-rtctrl'
        for inst in self.kids(o['dn'], 'l3extInstP'):
            for sub in self.kids(inst, 'l3extSubnet'):
                a = self.A(sub)
                n = net_of(a['ip'])
                if n and key in a['scope'].split(',') and self._pfx_in(prefix, n, key in (a.get('aggregate') or '').split(',')):
                    return True, '%s Route Control Subnet %s am External EPG %s' % (
                        direction.capitalize(), a['ip'], self.A(inst)['name'])
        prof = o['dn'] + '/prof-default-' + direction
        if self.has(prof):
            for ctx in sorted(self.kids(prof, 'rtctrlCtxP'), key=lambda c: int(self.A(c)['order'] or 0)):
                ca = self.A(ctx)
                for rs_ in self.kids(ctx, 'rtctrlRsCtxPToSubjP'):
                    ra = self.A(rs_)
                    if ra.get('state') != 'formed':
                        continue
                    for d in self.kids(ra['tDn'], 'rtctrlMatchRtDest'):
                        da = self.A(d)
                        n = net_of(da['ip'])
                        lo, hi = int(da.get('fromPfxLen') or 0), int(da.get('toPfxLen') or 0)
                        if n and self._pfx_in(prefix, n, da['aggregate'] == 'yes', lo, hi):
                            return ca['action'] == 'permit', 'Route-Profile default-%s, Context %s (%s), Match Rule %s' % (
                                direction, ca['name'], ca['action'], self.A(ra['tDn'])['name'])
        return False, None

    def _import(self, o, rs, routes):
        if 'import' not in o['enforce']:
            return routes
        ok = []
        for p, pr in routes:
            if self.rt_permit(o, 'import', p)[0]:
                ok.append((p, pr))
            else:
                rs.setdefault('rejected', []).append(p)
        if rs.get('rejected'):
            rs['reasons'].append('Import Route Control (enforced) blockiert: %s' % ', '.join(rs['rejected']))
        return ok

    def _summaries(self, o):
        """Route Summarization: (Netz, Policy-DN, summary-only) aus Export-Subnetzen mit Summarization Policy."""
        out = []
        for inst in self.kids(o['dn'], 'l3extInstP'):
            for sub in self.kids(inst, 'l3extSubnet'):
                a = self.A(sub)
                rs_ = self.A(sub + '/rsSubnetToRtSumm') or {}
                n = net_of(a['ip'])
                if n and rs_.get('state') == 'formed' and 'export-rtctrl' in a['scope'].split(','):
                    pol = rs_['tDn']
                    only = True
                    if self.store.objs[pol][0] == 'bgpRtSummPol':
                        only = 'summary-only' in (self.A(pol)['ctrl'] or '').split(',')
                    out.append((n, pol, only))
        return out

    def _exports(self):
        """Was die ACI jedem dynamischen Nachbarn ankuendigt (BD-Subnetze, Transit-Routen, Summaries)."""
        for r in self.sim.get('routers', []):
            rs = self.routers.get(r['name'], {})
            if not rs.get('_exp'):
                continue
            learned, transit = [], []
            for out, nid in rs.pop('_exp'):
                o = self.outs[out]
                for p_ in self.exported_subnets(out, nid):
                    if p_ not in learned:
                        learned.append(p_)
                cands = []
                for rt in self.routes.get((o['vrf'], nid), []):
                    if rt['proto'] not in ('ospf', 'bgp', 'static', 'eigrp') or rt.get('router') == r['name']:
                        continue
                    cands.append(rt['prefix'])
                    if rt['prefix'] in learned or rt['prefix'] in transit:
                        continue
                    if self.rt_permit(o, 'export', rt['prefix'])[0]:
                        transit.append(rt['prefix'])
                # BD-Subnetze, die nur ein default-export Route-Profile freigibt
                bdsubs = []
                for bd in self.store.by_class('fvBD'):
                    if (self.A(bd + '/rsctx') or {}).get('tDn') != o['vrf']:
                        continue
                    for x in self.bd_subnets(bd):
                        p_ = str(x['net'])
                        if 'public' in x['scope'].split(','):
                            bdsubs.append(p_)
                        if p_ not in learned and 'public' in x['scope'].split(',') and self.has(out + '/prof-default-export') \
                                and self.rt_permit(o, 'export', p_)[0]:
                            learned.append(p_)
                for net, pol, only in self._summaries(o):
                    inner = [p_ for p_ in learned + transit + cands + bdsubs
                             if ipaddress.ip_network(p_, strict=False).subnet_of(net) and ipaddress.ip_network(p_, strict=False) != net]
                    if not inner:
                        continue
                    if only:
                        learned = [p_ for p_ in learned if p_ not in inner]
                        transit = [p_ for p_ in transit if p_ not in inner]
                    if str(net) not in transit:
                        transit.append(str(net))
                    rs.setdefault('summaries', []).append({'net': str(net), 'pol': pol, 'only': only, 'covers': sorted(set(inner))})
            rs['learned'] = learned + transit
            rs['transit'] = transit
            for p_ in r.get('staticBack', []):
                if p_ not in rs['learned']:
                    rs['learned'].append(p_)
            if not learned and not transit:
                rs['reasons'].append('ACI kuendigt dem Router nichts an (keine BD-Subnetze, keine Transit-Routen)')

    def _peer(self, p):
        pa = self.A(p)
        asp = self.A(p + '/as')
        lasp = self.A(p + '/localasn')
        return {'addr': pa['addr'], 'remoteAs': asp['asn'] if asp else '', 'dn': p, 'ttl': int(pa.get('ttl') or 1),
                'localAs': lasp['localAsn'] if lasp and lasp.get('localAsn') else None,
                'password': pa.get('password', ''), 'bfd': 'bfd' in (pa.get('peerCtrl') or '').split(',')}

    def _l3err(self, o, ri, err):
        if err[0] == 'S':
            self.fault(ri, 'S0468', 'minor', err[1], 'l3if-config-failed')
        else:
            self.fault(o['dn'], 'F0467', 'minor', 'Configuration failed for L3Out %s due to Invalid %s '
                       'Configuration, debug message: %s: %s' % (
                           o['name'], 'Path' if err[0] == 'invalid-path' else 'VLAN', err[0], err[1]),
                       'configuration-failed')

    def _if_common(self, o, lif, ospf_if, pol):
        eig = self.A(lif + '/eigrpIfP/rsIfPol') or {}
        eigpol = self.A(eig['tDn']) if eig.get('state') == 'formed' else {'helloIntvl': '5', 'holdIntvl': '15', 'ctrl': ''}
        bfdrs = self.A(lif + '/bfdIfP/rsIfPol') or {}
        bfdpol = self.A(bfdrs['tDn']) if bfdrs.get('state') == 'formed' else {'minTxIntvl': '50', 'minRxIntvl': '50', 'detectMult': '3', 'adminSt': 'enabled'}
        return {'ospf': bool(o['ospf']) and ospf_if, 'pol': pol, 'lif': lif,
                'eigrp': bool(o['eigrp']) and self.has(lif + '/eigrpIfP'), 'eigrp_pol': eigpol,
                'bfd_if': self.has(lif + '/bfdIfP'), 'bfd_pol': bfdpol}

    def _add_if(self, o, iface):
        o['ifs'].append(iface)
        self.l3if.append(iface)
        for l in iface['legs']:
            if l in self.ports:
                self.ports[l]['usage'].add('epg')
                if iface['type'] == 'l3-port':
                    self.ports[l]['layer'] = 'Layer3'
        if o['vrf']:
            nid = iface['nid']
            self.dep_vrf.setdefault(nid, set()).add(o['vrf'])
            self.routes.setdefault((o['vrf'], nid), []).append(
                {'prefix': str(iface['net']), 'nh': str(ip_of(iface['addr'])), 'proto': 'direct',
                 'via': self.if_name(iface), 'pref': 0})

    def _l3if(self, o, np, lif, ri, ospf_if, pol):
        ia = self.A(ri)
        name = o['name']
        path = self.paths.get(ia['tDn'])
        if path is None:
            self.fault(o['dn'], 'F0467', 'minor', 'Configuration failed for L3Out %s due to Invalid Path '
                       'Configuration, debug message: invalid-path: %s :: Path is not present' % (name, ia['tDn']),
                       'configuration-failed')
            return
        vlan = vlan_num(ia['encap'])
        typ = ia['ifInstT']
        err = None
        missing = [n for n in path['nodes'] if n not in o['nodes']]
        if missing:
            err = ('S', 'Node %s of interface %s is not part of the logical node profile' % (
                ', '.join(map(str, missing)), path['name']))
        elif not o['dom']:
            err = ('invalid-path', 'Either the EpG/L3Out is not associated with a domain or the domain does not '
                   'have this interface assigned to it')
        elif o['dom'] not in (self._pg_info(path['pg'])['domains'] if path['pg'] else []):
            err = ('invalid-path', 'Either the EpG/L3Out is not associated with a domain or the domain does not '
                   'have this interface assigned to it')
        elif path['type'] == 'vpc' and typ != 'ext-svi':
            err = ('invalid-path', '%s :: Auf einem vPC-Pfad ist nur ein SVI moeglich (Routed/Sub-Interface nicht erlaubt)' % path['name'])
        elif typ != 'l3-port' and vlan is None:
            err = ('invalid-vlan', 'Encap is missing for %s' % typ)
        elif typ != 'l3-port' and not self.vlan_in_domain(o['dom'], vlan):
            err = ('invalid-vlan', 'vlan-%d :: Either the EpG/L3Out is not associated with a domain or the domain '
                   'does not have this vlan assigned to it' % vlan)
        elif path['type'] != 'vpc' and ia['addr'] in ('', '0.0.0.0'):
            err = ('S', 'No IP address configured on %s' % path['name'])
        if err:
            return self._l3err(o, ri, err)
        mtu = 9000 if ia['mtu'] == 'inherit' else int(ia['mtu'])
        peers = [self._peer(p) for p in self.kids(ri, 'bgpPeerP')]
        sec = [self.A(x)['addr'] for x in self.kids(ri, 'l3extIp')]
        common = self._if_common(o, lif, ospf_if, pol)
        if path['type'] == 'vpc':
            mem = {self.A(m)['side']: m for m in self.kids(ri, 'l3extMember')}
            if set(mem) != {'A', 'B'} or any(self.A(m)['addr'] in ('', '0.0.0.0') for m in mem.values()):
                return self._l3err(o, ri, ('S', 'vPC-SVI %s braucht Side A und Side B mit je einer IP-Adresse' % path['name']))
            nets = {net_of(self.A(m)['addr']) for m in mem.values()}
            if len(nets) != 1 or any(net_of(x) not in nets for x in sec):
                return self._l3err(o, ri, ('S', 'vPC-SVI %s: Side A, Side B und Secondary IP muessen im selben Subnetz liegen' % path['name']))
            for side, nid in zip(('A', 'B'), sorted(path['nodes'])):
                m = mem[side]
                msec = sec + [self.A(x)['addr'] for x in self.kids(m, 'l3extIp')]
                iface = dict(common, out=o['dn'], vrf=o['vrf'], nid=nid, legs=[l for l in path['legs'] if l[0] == nid],
                             path=ia['tDn'], type=typ, vlan=vlan, addr=self.A(m)['addr'], net=net_of(self.A(m)['addr']),
                             mtu=mtu, peers=peers, dn=ri, side=side, secondary=msec, ptype='vpc')
                self._add_if(o, iface)
            return
        nid = path['nodes'][0]
        iface = dict(common, out=o['dn'], vrf=o['vrf'], nid=nid, legs=path['legs'], path=ia['tDn'], type=typ, vlan=vlan,
                     addr=ia['addr'], net=net_of(ia['addr']), mtu=mtu, peers=peers, dn=ri, secondary=sec, ptype=path['type'])
        self._add_if(o, iface)

    def _float_if(self, o, lif, vi, ospf_if, pol):
        va = self.A(vi)
        m = re.search(r'/node-(\d+)$', va['nodeDn'])
        vlan = vlan_num(va['encap'])
        if not m or int(m.group(1)) not in o['nodes']:
            return self._l3err(o, vi, ('S', 'Floating SVI: Anchor Node %s ist nicht im Logical Node Profile' % va['nodeDn']))
        if va['addr'] in ('', '0.0.0.0') or vlan is None:
            return self._l3err(o, vi, ('S', 'Floating SVI: Primary IP oder Encap fehlt'))
        doms = []
        for d in self.kids(vi, 'l3extRsDynPathAtt'):
            da = self.A(d)
            if da['state'] != 'formed':
                continue
            if self.A(da['tDn']) and self.store.objs[da['tDn']][0] == 'physDomP' and not self.vlan_in_domain(da['tDn'], vlan):
                self._l3err(o, vi, ('invalid-vlan', 'vlan-%d :: not in domain %s' % (vlan, self.short(da['tDn']))))
                continue
            doms.append({'dom': da['tDn'], 'float': da['floatingAddr'] if da['floatingAddr'] not in ('', '0.0.0.0') else None})
        if not doms:
            return self._l3err(o, vi, ('S', 'Floating SVI ohne Domain (Floating Path)'))
        sec = [self.A(x)['addr'] for x in self.kids(vi, 'l3extIp')]
        mtu = 9000 if va['mtu'] == 'inherit' else int(va['mtu'])
        iface = dict(self._if_common(o, lif, ospf_if, pol), out=o['dn'], vrf=o['vrf'], nid=int(m.group(1)), legs=[], path=vi,
                     type='floating', vlan=vlan, addr=va['addr'], net=net_of(va['addr']), mtu=mtu, peers=[], dn=vi,
                     secondary=sec, doms=doms, ptype='floating')
        self._add_if(o, iface)

    def _float_reach(self, iface, legs):
        """Kann ein Router an diesen Ports die Floating SVI erreichen? (Ports mit der Domain)"""
        for nid, port in legs:
            pg = self.ports.get((nid, port), {}).get('pg')
            pdoms = self._pg_info(pg)['domains'] if pg else []
            for d in iface['doms']:
                if d['dom'] in pdoms or d['dom'].startswith('uni/vmmp-'):
                    if nid == iface['nid'] or d['float']:
                        return True, None
                    return False, 'Leaf %s ist kein Anchor Node und die Floating IP fehlt' % self.nodes[nid]['name']
        return False, 'Port ohne Access Policy fuer die Domain der Floating SVI'

    def _alive(self, ip):
        """Fuer IP SLA: antwortet diese Adresse?"""
        ip = ip_of(ip) if '/' in str(ip) else ipaddress.ip_address(ip)
        for r in self.sim.get('routers', []):
            rs = self.routers.get(r['name'], {})
            if not rs.get('link'):
                continue
            if ip_of(r['ip']) == ip or any(ip in ipaddress.ip_network(n, strict=False) for n in r.get('networks', [])):
                return True
        return any(hs.get('learned') and ip_of(h['ip']) == ip for h in self.all_hosts() for hs in [self.hosts.get(h['name'], {})])

    def track_state(self, tl):
        if not tl or not self.has(tl):
            return True, []
        mem = []
        for r in self.kids(tl, 'rtctrlDummy') + self.kids(tl, 'fvRsOtmListMember'):
            ra = self.A(r)
            if ra.get('state') != 'formed':
                continue
            dst = self.A(ra['tDn'])['dstIpAddr']
            mem.append((self.A(ra['tDn'])['name'], dst, bool(dst) and self._alive(dst)))
        if not mem:
            return True, mem
        a = self.A(tl)
        pct = 100.0 * sum(1 for m in mem if m[2]) / len(mem)
        up = pct >= max(1, int(a.get('percentageUp') or 1)) if a.get('type', 'percentage') == 'percentage' else pct > 0
        return up, mem

    def _statics(self):
        for o in self.outs.values():
            if not o['vrf']:
                continue
            for nid, node in o['nodes'].items():
                for st in node['statics']:
                    tok, _ = self.track_state(st['track'])
                    st['trackUp'] = tok
                    if not tok:
                        continue
                    cands = []
                    for nh in st['nhs']:
                        if nh['track'] and not self.track_state(nh['track'])[0]:
                            continue
                        r = next((x for x in self.sim.get('routers', []) if str(ip_of(x['ip'])) == nh['addr']), None)
                        rs = self.routers.get(r['name'], {}) if r else {}
                        ifc = next((i for i in rs.get('ifaces', []) if i['nid'] == nid and i['out'] == o['dn']), None)
                        if ifc:
                            cands.append((nh['pref'], nh, r, ifc))
                    if not cands:
                        continue
                    best = min(c[0] for c in cands)
                    for pref, nh, r, ifc in cands:
                        if pref == best:
                            self.routes.setdefault((o['vrf'], nid), []).append(
                                {'prefix': st['prefix'], 'nh': nh['addr'], 'proto': 'static', 'via': self.if_name(ifc),
                                 'router': r['name'], 'pref': pref, 'track': st['track'] or nh['track'], 'bfd': st['bfd']})

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
        exts = [d for d, c in self.cls.items() if c['kind'] == 'ext' and c.get('out') == out]
        for bd in self.store.by_class('fvBD'):
            bvrf = (self.A(bd + '/rsctx') or {}).get('tDn')
            if bvrf != o['vrf']:
                # Shared L3Out: BD-Subnetz public+shared und Contract zum External EPG
                epgs = [d for d, c in self.cls.items() if c['kind'] == 'epg' and c['bd'] == bd]
                if any(self._related(e, x) for e in epgs for x in exts):
                    res.extend(str(s_['net']) for s_ in self.bd_subnets(bd)
                               if {'public', 'shared'} <= set(s_['scope'].split(',')))
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

    def leaked_routes(self):
        """Shared Services: geleakte Subnetze je VRF -> [(Netz, Quell-VRF, Objekt)]."""
        out = {}
        for brc, rel in self.contracts.items():
            sc = (self.A(brc) or {}).get('scope')
            if sc not in ('tenant', 'global'):
                continue
            for p in rel['prov']:
                for c in rel['cons']:
                    pc, cc = self.cls.get(p), self.cls.get(c)
                    if not pc or not cc or not pc['vrf'] or not cc['vrf'] or pc['vrf'] == cc['vrf']:
                        continue
                    if sc == 'tenant' and pc['tenant'] != cc['tenant']:
                        continue
                    if pc['kind'] == 'epg':
                        for x in self.epg_subnets(p):
                            if 'shared' in x['scope'].split(','):
                                out.setdefault(cc['vrf'], []).append((x['net'], pc['vrf'], p))
                    if cc['kind'] == 'epg':
                        for x in self.bd_subnets(cc['bd']) + self.epg_subnets(c):
                            if 'shared' in x['scope'].split(','):
                                out.setdefault(pc['vrf'], []).append((x['net'], cc['vrf'], c))
        for v in out:
            seen, uniq = set(), []
            for r in out[v]:
                if r[0] not in seen:
                    seen.add(r[0])
                    uniq.append(r)
            out[v] = uniq
        return out

    def _related(self, a, b):
        for brc, rel in self.contracts.items():
            if (a in rel['prov'] and b in rel['cons']) or (a in rel['cons'] and b in rel['prov']):
                return True
        return False

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
        rs = {'name': r['name'], 'link': False, 'state': 'down', 'reasons': [], 'iface': None, 'ifaces': [], 'adjs': [],
              'learned': [], 'proto': r.get('protocol', 'static'), 'adj': '-', 'bfd': []}
        self.routers[r['name']] = rs
        if r.get('down'):
            rs['reasons'].append('Router ist ausgeschaltet (Simulation)')
            return
        links = r.get('links') or [[r.get('serial'), r.get('port')]]
        legs = []
        for s_, p_ in links:
            nid = self.serial_active.get(s_)
            if nid is None:
                rs['reasons'].append('Switch %s ist nicht aktiv' % self.node_label(s_))
                continue
            if self.ports.get((nid, p_), {}).get('qual') == 'admin-down':
                rs['reasons'].append('%s %s ist deaktiviert (Disabled Interface)' % (self.nodes[nid]['name'], p_))
                continue
            legs.append((nid, p_))
        if not legs:
            return
        vlan = int(r.get('vlan') or 0)
        cand, why_float = [], None
        for i in self.l3if:
            if i['type'] == 'floating':
                if vlan and i['vlan'] == vlan:
                    ok_, why_float = self._float_reach(i, legs)
                    if ok_:
                        cand.append(i)
            elif set(i['legs']) & set(legs):
                cand.append(i)
        match = [i for i in cand if (vlan == 0 and i['type'] == 'l3-port') or (vlan and i['vlan'] == vlan and i['type'] != 'l3-port')]
        if not match:
            if why_float:
                rs['reasons'].append('Floating SVI: %s' % why_float)
            elif cand:
                rs['reasons'].append('L3Out-Interface passt nicht zum Router (Typ/VLAN: ACI %s, Router %s)'
                                     % (', '.join('%s%s' % (i['type'], ' vlan-%s' % i['vlan'] if i['vlan'] else '') for i in cand),
                                        'vlan-%d' % vlan if vlan else 'untagged/routed'))
            else:
                rs['reasons'].append('Kein funktionierendes L3Out-Interface auf %s (Konfiguration/Faults pruefen)'
                                     % ', '.join('%s %s' % (self.nodes[n]['name'], p_) for n, p_ in legs))
            return
        # Port-Channel/vPC zum Router: Bonding muss zur Port-Channel-Policy passen
        bond = r.get('bond', 'none')
        for i in match:
            if i.get('ptype') in ('pc', 'vpc') and i['legs']:
                pg = self.ports.get(i['legs'][0], {}).get('pg')
                lacp = self._pg_info(pg)['lacp'] if pg else 'off'
                if lacp in ('active', 'passive') and bond not in ('lacp-active', 'lacp-passive'):
                    rs['reasons'].append('LACP: ACI erwartet LACP-PDUs (mode %s), der Router bildet keinen Port-Channel' % lacp)
                    return
                if lacp not in ('active', 'passive') and bond in ('lacp-active', 'lacp-passive'):
                    rs['reasons'].append('LACP: Router sendet LACP, die Port-Channel-Policy der ACI steht auf %s' % lacp)
                    return
        rip = ip_of(r['ip'])
        ok = []
        for i in match:
            if i['net'] is None or rip not in i['net'] or rip == ip_of(i['addr']) or any(rip == ip_of(x) for x in i['secondary']):
                rs['reasons'].append('IP-Subnetz passt nicht: ACI %s, Router %s' % (i['addr'], r['ip']))
                continue
            ok.append(i)
        if not ok:
            return
        rs['link'] = True
        rs['state'] = 'up'
        rs['ifaces'] = ok
        rs['iface'] = ok[0]
        proto = r.get('protocol', 'static')
        exp = []
        prio = {'FULL': 4, 'Established': 4, 'UP': 4, 'static': 3, 'EXSTART': 2, 'Active': 1}
        for i in ok:
            o = self.outs[i['out']]
            if proto == 'ospf':
                st_, why = self._ospf_state(r, i, o)
            elif proto == 'bgp':
                st_, why = self._bgp_state(r, i, o, rs)
            elif proto == 'eigrp':
                st_, why = self._eigrp_state(r, i, o)
            else:
                st_, why = 'static', None
            rs['adjs'].append({'nid': i['nid'], 'iface': i, 'state': st_, 'why': why})
            if why and why not in rs['reasons']:
                rs['reasons'].append(why)
            aci_bfd = (proto == 'ospf' and 'bfd' in (i['pol'].get('ctrl') or '').split(',')) or \
                (proto == 'eigrp' and 'bfd' in (i['eigrp_pol'].get('ctrl') or '').split(',')) or \
                (proto == 'bgp' and any(p['bfd'] for p in i['peers'] + o['nodes'].get(i['nid'], {}).get('peers', []))) or \
                (proto == 'static' and any(st['bfd'] for st in o['nodes'].get(i['nid'], {}).get('statics', [])))
            if aci_bfd or r.get('bfd'):
                bst = 'Up' if aci_bfd and r.get('bfd') and st_ in ('FULL', 'Established', 'UP', 'static') else 'Down'
                rs['bfd'].append({'nid': i['nid'], 'iface': i, 'state': bst, 'aci': aci_bfd, 'router': bool(r.get('bfd'))})
            if st_ in ('FULL', 'Established', 'UP') and not why and o['vrf']:
                pr = {'ospf': 'ospf', 'bgp': 'bgp', 'eigrp': 'eigrp'}[proto]
                for p, pr2 in self._import(o, rs, [(x, pr) for x in r.get('advertise', [])]):
                    self.routes.setdefault((o['vrf'], i['nid']), []).append(
                        {'prefix': p, 'nh': str(rip), 'proto': pr2, 'via': self.if_name(i), 'router': r['name'],
                         'pref': {'ospf': 110, 'bgp': 20, 'eigrp': 90}[pr2]})
                exp.append((o['dn'], i['nid']))
        if exp:
            rs['_exp'] = exp
        rs['adj'] = max((a['state'] for a in rs['adjs']), key=lambda x: prio.get(x, 0)) if rs['adjs'] else '-'
        if proto == 'static':
            rs['learned'] = list(r.get('staticBack', []))

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

    def _bgp_state(self, r, iface, o, rs=None):
        if not o['bgp']:
            return 'Idle', 'BGP ist im L3Out nicht aktiviert'
        rb = r.get('bgp', {})
        src = rb.get('updateSource') or str(ip_of(r['ip']))
        peer = next((p for p in iface['peers'] if p['addr'] == src), None)
        multihop = False
        if peer is None:
            node = o['nodes'].get(iface['nid'], {})
            peer = next((p for p in node.get('peers', []) if p['addr'] == src), None)
            if peer is None:
                return 'Idle', None
            multihop = True
        fasn = self.fabric_asn()
        if not fasn:
            return 'Idle', None
        local = peer['localAs'] or fasn
        if str(peer['remoteAs']) != str(rb.get('asn')):
            return 'Idle', None
        if str(rb.get('peerAs')) != str(local):
            return 'Idle', None
        node = o['nodes'].get(iface['nid'], {})
        aci_src = node.get('rtrId') if multihop else str(ip_of(iface['addr']))
        want = rb.get('peerAddr') or (str(ip_of(iface['addr'])) if not multihop else None)
        if multihop:
            if peer['ttl'] < 2:
                return 'Idle', 'eBGP ueber Loopbacks braucht eBGP Multihop: TTL am BGP Peer ist %d' % peer['ttl']
            if not any(ip_of(src + '/32') in ipaddress.ip_network(st['prefix'], strict=False) and
                       any(n['addr'] == str(ip_of(r['ip'])) for n in st['nhs']) for st in node.get('statics', [])):
                return 'Active', 'Die ACI hat keine Static Route zur Loopback %s des Routers' % src
            if not any(ipaddress.ip_address(aci_src) in ipaddress.ip_network(n, strict=False) for n in r.get('staticBack', [])):
                return 'Active', 'Der Router hat keine Route zur ACI-Loopback %s (Router ID)' % aci_src
            if want and want != aci_src:
                return 'Active', 'Router baut die Session zu %s auf, die ACI spricht von %s' % (want, aci_src)
        elif want and want not in [str(ip_of(iface['addr']))] + [str(ip_of(x)) for x in iface['secondary']]:
            return 'Active', None
        if (peer.get('password') or '') != (rb.get('password') or ''):
            return 'Active', 'BGP-Session baut sich nicht auf: TCP-MD5-Authentifizierung schlaegt fehl (Passwort unterschiedlich)'
        vrs = self.A(o['vrf'] + '/rsbgpCtxPol') or {}
        pol = self.A(vrs['tDn']) if vrs.get('state') == 'formed' else {'holdIntvl': '180', 'kaIntvl': '60'}
        hold = min(int(pol['holdIntvl']), int(rb.get('hold') or 180))
        if rs is not None:
            rs.setdefault('timers', {})[iface['nid']] = {'hold': hold, 'keepalive': min(int(pol['kaIntvl']), int(rb.get('keepalive') or 60)),
                                                       'aciHold': int(pol['holdIntvl']), 'aciKa': int(pol['kaIntvl']),
                                                       'multihop': multihop, 'peer': peer['addr'], 'local': aci_src,
                                                       'password': bool(peer.get('password'))}
        return 'Established', None

    def _eigrp_state(self, r, iface, o):
        if not o['eigrp']:
            return 'DOWN', 'EIGRP ist im L3Out nicht aktiviert'
        if not iface['eigrp']:
            return 'DOWN', 'Am Logical Interface Profile fehlt das EIGRP Interface Profile'
        re_ = r.get('eigrp', {})
        if str(o['eigrp']['asn']) != str(re_.get('asn', '1')):
            return 'DOWN', None
        if iface['mtu'] != int(r.get('mtu', 1500)):
            return 'UP', None
        return 'UP', None
