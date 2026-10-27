"""Multi-Pod und Remote Leaf: IPN, Infra-L3Out, Discovery ueber DHCP Relay und Datenpfad zwischen den Pods.

Ohne IPN-Verkabelung in der Topologie (Standard: ein Pod) bleibt alles wie bisher.
"""
import ipaddress
import re

INFRA_MTU = 9150      # MTU der Spine-Sub-Interfaces im Infra-L3Out bei "inherit"
VXLAN_MIN_MTU = 9150  # Mindest-MTU im IPN, damit Jumbo-Frames mit VXLAN-Header durchpassen
WAN_MIN_MTU = 1550    # Remote Leaf: 1500 Byte Payload plus VXLAN-Overhead


def _vlan(encap):
    m = re.match(r'^vlan-(\d+)$', encap or '')
    return int(m.group(1)) if m else None


def _area(a):
    a = str(a or '').strip()
    if a in ('', 'backbone'):
        return '0.0.0.0'
    if a.isdigit():
        return str(ipaddress.ip_address(int(a)))
    return a


def _iface(ipmask):
    try:
        return ipaddress.ip_interface(ipmask)
    except ValueError:
        return None


class PodMixin:
    # ------------------------------------------------------------------ Pools
    def _pod_pools(self):
        pools, remote = {}, {}
        for d in self.store.by_class('fabricSetupP'):
            a = self.A(d)
            pools[int(a['podId'])] = a['tepPool']
            for r in self.kids(d, 'fabricExtSetupP'):
                ra = self.A(r)
                remote[int(ra['remoteId'])] = {'pool': ra['tepPool'], 'pod': int(a['podId'])}
        pools[self.pod] = self.tep_pool
        return pools, remote

    def pdn(self, nid):
        return 'topology/pod-%d' % self.pod_of.get(nid, self.pod)

    # ------------------------------------------------------------------ Infra-L3Out
    def _infra_ifaces(self):
        """Interfaces der Infra-L3Outs (Tenant infra, VRF overlay-1) auf Spines und Remote Leafs."""
        out = []
        self.infra_bgp = False
        for o in self.store.by_class('l3extOut'):
            if not o.startswith('uni/tn-infra/'):
                continue
            vrf = (self.A(o + '/rsectx') or {}).get('tnFvCtxName', '')
            ospf = self.A(o + '/ospfExtP')
            if self.has(o + '/bgpExtP'):
                self.infra_bgp = True
            for np in self.kids(o, 'l3extLNodeP'):
                nodes = {}
                for rn in self.kids(np, 'l3extRsNodeL3OutAtt'):
                    m = re.search(r'/node-(\d+)$', self.A(rn)['tDn'])
                    if m:
                        nodes[int(m.group(1))] = self.A(rn)
                for lif in self.kids(np, 'l3extLIfP'):
                    pol = self._ospf_pol(lif)
                    for rp in self.kids(lif, 'l3extRsPathL3OutAtt'):
                        a = self.A(rp)
                        m = re.search(r'/paths-(\d+)/pathep-\[(eth\d+/\d+)\]$', a['tDn'])
                        if not m:
                            continue
                        nid = int(m.group(1))
                        out.append({'dn': rp, 'out': o, 'nid': nid, 'port': m.group(2), 'vrf': vrf, 'node': nodes.get(nid),
                                    'ifInstT': a['ifInstT'], 'vlan': _vlan(a['encap']), 'ip': _iface(a['addr']) if a['addr'] != '0.0.0.0' else None,
                                    'mtu': INFRA_MTU if a['mtu'] == 'inherit' else int(a['mtu']), 'ospf': bool(ospf) and self.has(lif + '/ospfIfP'),
                                    'area': (ospf or {}).get('areaId', ''), 'mtuIgnore': 'mtu-ignore' in (pol.get('ctrl') or '')})
        return out

    # ------------------------------------------------------------------ Auswertung
    def _mp_eval(self, nodes, valid, ident):
        """Vor der Discovery: welche Switches erreichen den APIC ueber IPN/WAN, welche Adjacencies sind FULL."""
        topo = self.sim['topology']
        self.pod_of_serial = {n['serial']: n.get('pod', self.pod) for n in topo['nodes']}
        self.remote_serial = {n['serial'] for n in topo['nodes'] if n.get('remote')}
        self.mp = {'active': bool(topo.get('ipnlinks')), 'adj': [], 'reasons': {}, 'ipn_ok': {}, 'edges': set(), 'up': set(),
                   'pools': {}, 'remote': {}}
        self.mp['pools'], self.mp['remote'] = self._pod_pools()
        if not self.mp['active']:
            return
        cfg = self.sim.get('ipn') or {'routers': []}
        routers = {r['name']: r for r in cfg.get('routers', [])}
        infra = self._infra_ifaces()
        self.mp['infra'] = infra
        nid_of = dict(valid)
        for s, p, rname, rport in topo['ipnlinks']:
            r = routers.get(rname)
            nid = nid_of.get(s)
            ri = next((x for x in (r or {}).get('ifs', []) if x['serial'] == s and x['port'] == p), None)
            sw = next((x for x in infra if x['nid'] == nid and x['port'] == p), None) if nid else None
            adj = {'serial': s, 'port': p, 'router': rname, 'rport': rport, 'nid': nid, 'state': 'down', 'why': None,
                   'kind': (r or {}).get('kind', 'ipn'), 'pod': self.pod_of_serial.get(s, 1), 'dn': sw['dn'] if sw else None}
            self.mp['adj'].append(adj)
            if not r or r.get('down'):
                adj['why'] = 'Router %s ist ausgefallen' % rname if r else 'Router %s fehlt' % rname
            elif not ri or not _iface(ri.get('ip', '')):
                adj['why'] = '%s %s hat keine IP-Adresse' % (rname, rport)
            elif nid is None:
                adj['why'] = 'Switch ist nicht registriert'
            elif not sw:
                adj['why'] = 'Kein Interface im Infra-L3Out (Tenant infra) fuer Node %d %s' % (nid, p)
            elif sw['vrf'] != 'overlay-1':
                adj['why'] = 'Das Infra-L3Out muss im VRF overlay-1 liegen'
            elif sw['ifInstT'] != 'sub-interface' or sw['vlan'] != int(ri.get('vlan') or 0):
                adj['why'] = 'Encap passt nicht: Switch %s vlan-%s, %s erwartet ein Sub-Interface mit vlan-%s' % (
                    sw['ifInstT'], sw['vlan'], rname, ri.get('vlan'))
            elif not sw['ip'] or _iface(ri['ip']).network != sw['ip'].network or _iface(ri['ip']).ip == sw['ip'].ip:
                adj['why'] = 'IP %s passt nicht zum Router %s (%s)' % (sw['ip'] or 'fehlt', rname, ri['ip'])
            elif not sw['node'] or not sw['node'].get('rtrId'):
                adj['why'] = 'Node %d fehlt im Node Profile des Infra-L3Outs oder hat keine Router ID' % nid
            elif not sw['ospf']:
                adj['why'] = 'OSPF fehlt (OSPF am Infra-L3Out und OSPF Interface Profile)'
            elif _area(sw['area']) != _area(r.get('area')):
                adj['why'] = 'OSPF Area %s, %s ist in Area %s' % (sw['area'], rname, r.get('area'))
            elif sw['mtu'] != int(r.get('mtu') or 1500) and not sw['mtuIgnore']:
                adj.update(state='EXSTART', why='MTU-Mismatch: Switch %d, %s %d - OSPF bleibt in EXSTART' % (sw['mtu'], rname, int(r.get('mtu') or 1500)))
            else:
                adj['state'] = 'FULL'
            if adj['state'] == 'FULL':
                self.mp['up'].add(s)
        # Pod 1 ist ueber seine Spines am IPN angebunden?
        for pod in sorted({self.pod_of_serial.get(n['serial'], 1) for n in topo['nodes']}):
            self.mp['ipn_ok'][pod] = any(a['state'] == 'FULL' and a['kind'] == 'ipn' and a['pod'] == pod for a in self.mp['adj'])
        apic_tep = self.apic_tep
        for adj in self.mp['adj']:
            s = adj['serial']
            r = routers.get(adj['router'])
            ri = next((x for x in (r or {}).get('ifs', []) if x['serial'] == s and x['port'] == adj['port']), None)
            pod = adj['pod']
            if pod == self.pod and s not in self.remote_serial:
                continue
            why = None
            if not self.mp['ipn_ok'].get(self.pod):
                why = 'Die Spines von Pod %d haben keine OSPF-Nachbarschaft zum IPN - der APIC erreicht das IPN nicht' % self.pod
            elif not r or r.get('down') or any(x.get('down') for x in routers.values() if x['kind'] == 'ipn'):
                why = 'IPN-Router ausgefallen'
            elif not ri or int(ri.get('vlan') or 0) != 4:
                why = 'Auf %s fehlt das Sub-Interface vlan-4 zum Switch (Discovery laeuft ueber vlan-4)' % adj['router']
            elif apic_tep not in (r.get('relay') or []):
                why = 'Auf %s %s fehlt das DHCP Relay zum APIC (%s) - der DHCP Discover des Switches kommt nicht an' % (
                    adj['router'], adj['rport'], apic_tep)
            elif s in self.remote_serial:
                if not self.mp['remote']:
                    why = 'Kein Remote Pool in der Pod Fabric Setup Policy'
                elif not self._ext_tep(pod):
                    why = 'In der Fabric External Connection Policy fehlt fuer Pod %d der External TEP Pool (Routable Subnet)' % pod
            elif pod not in self.mp['pools']:
                why = 'Der APIC kennt Pod %d nicht: TEP Pool in der Pod Fabric Setup Policy fehlt' % pod
            if why:
                self.mp['reasons'][s] = why
            else:
                self.mp['edges'].add(s)

    def _ext_tep(self, pod):
        for c in self.store.by_class('fabricPodConnP'):
            if c.startswith('uni/tn-infra/') and self.A(c)['id'] == str(pod) and self.kids(c, 'fabricExtRoutablePodSubnet'):
                return True
        return False

    def _dp_tep(self, pod):
        for c in self.store.by_class('fabricPodConnP'):
            if c.startswith('uni/tn-infra/') and self.A(c)['id'] == str(pod) and self.kids(c, 'fabricIp'):
                return True
        return False

    def mp_adj_filter(self, adj, apic_serial):
        """Kanten fuer die Discovery: APIC <-> per IPN/WAN erreichbare Switches; Pod-2-Leafs nur ueber Spines mit IPN-Anbindung."""
        if not self.mp['active']:
            return adj
        for s in self.mp['edges']:
            adj.setdefault(apic_serial, set()).add(s)
            adj.setdefault(s, set()).add(apic_serial)
        for n in self.sim['topology']['nodes']:
            s = n['serial']
            if n['role'] == 'leaf' and self.pod_of_serial.get(s, 1) != self.pod:
                bad = {x for x in adj.get(s, set()) if x not in self.mp['up'] and x != apic_serial}
                if bad:
                    adj[s] = adj[s] - bad
                    for x in bad:
                        adj[x] = adj.get(x, set()) - {s}
                    if not adj[s]:
                        self.mp['reasons'][s] = 'Die Spines von Pod %d haben keine OSPF-Nachbarschaft zum IPN - der TEP Pool von Pod %d ist ' \
                                                'vom APIC aus nicht erreichbar' % (self.pod_of_serial[s], self.pod_of_serial[s])
        return adj

    def mp_gate(self, s):
        """Remote Leaf: erst aktiv, wenn die OSPF-Nachbarschaft zum WAN-Router steht."""
        if s in getattr(self, 'remote_serial', set()) and s not in self.mp['up']:
            a = next((x for x in self.mp['adj'] if x['serial'] == s), None)
            self.mp['reasons'][s] = 'Remote Leaf ist registriert, aber ohne OSPF zum WAN-Router (%s)' % ((a or {}).get('why') or 'Infra-L3Out')
            return False
        return True

    # ------------------------------------------------------------------ Datenpfad
    def interpod(self, pa, pb, flood=False):
        """Pruefung des VXLAN-Pfads zwischen zwei Pods. Rueckgabe Fehlertext oder None."""
        if pa == pb:
            return None
        if not self.mp.get('active'):
            return 'Kein IPN zwischen Pod %d und Pod %d' % (pa, pb)
        routers = [r for r in (self.sim.get('ipn') or {}).get('routers', []) if r['kind'] == 'ipn']
        for p in (pa, pb):
            if not self.mp['ipn_ok'].get(p):
                return 'Pod %d hat keine OSPF-Nachbarschaft zum IPN' % p
            if not any(n['role'] == 'spine' and n['state'] == 'active' and self.pod_of.get(i) == p for i, n in self.nodes.items()):
                return 'In Pod %d ist kein Spine aktiv' % p
            if not self._dp_tep(p):
                return 'Fabric External Connection Policy: fuer Pod %d fehlt der Data Plane TEP - die Spines tauschen keine Endpoints aus' % p
        if not self.infra_bgp:
            return 'Im Infra-L3Out fehlt BGP: ohne MP-BGP EVPN zwischen den Spines kennt Pod %d die Endpoints von Pod %d nicht' % (pa, pb)
        small = [r for r in routers if int(r.get('mtu') or 1500) < VXLAN_MIN_MTU]
        if small:
            return 'IPN-MTU zu klein: %s - VXLAN-Pakete (bis 9150 Byte) werden verworfen' % ', '.join('%s %s' % (r['name'], r['mtu']) for r in small)
        if flood and not all(r.get('pim') and r.get('rp') for r in routers):
            return 'Im IPN fehlt PIM Bidir mit RP fuer den GIPo-Bereich - BUM-Verkehr (ARP Flooding) erreicht den anderen Pod nicht'
        return None

    def remote_path(self, s):
        """Remote Leaf <-> Pod: WAN-MTU und IPN."""
        r = next((x for x in (self.sim.get('ipn') or {}).get('routers', []) if x['kind'] == 'wan'
                  and any(i['serial'] == s for i in x.get('ifs', []))), None)
        if r and int(r.get('mtu') or 1500) < WAN_MIN_MTU:
            return 'WAN-MTU %s zum Remote Leaf zu klein (mindestens %d fuer VXLAN)' % (r['mtu'], WAN_MIN_MTU)
        return None
