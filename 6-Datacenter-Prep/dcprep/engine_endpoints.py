"""Endpoint-Learning der simulierten Hosts und VMs, uSeg und ESG-Zuordnung."""
import re

from .model import split_dn, now_ts
from .ops import plain

from .engine_util import (vlan_num, net_of, ip_of)


class EndpointMixin:
    # ------------------------------------------------------------------
    # VMM: simuliertes vCenter, VDS, Port Groups, dynamische VLANs
    # ------------------------------------------------------------------
    def _vmm(self):
        self.vmm = {}
        self.vm_hosts = []
        vcs = self.sim.get('vcenters', [])
        for dom in self.store.by_class('vmmDomP'):
            name = self.A(dom)['name']
            info = {'dn': dom, 'name': name, 'state': 'offline', 'reasons': [], 'vc': None, 'pgs': {},
                    'discovery': 'lldp', 'hosts': []}
            self.vmm[dom] = info
            ctrls = self.kids(dom, 'vmmCtrlrP')
            if not ctrls:
                info['reasons'].append('Kein vCenter Controller konfiguriert')
                continue
            ca = self.A(ctrls[0])
            vc = next((v for v in vcs if v.get('ip') == ca['hostOrIp'] or v.get('name') == ca['hostOrIp']), None)
            acc = self.A(ctrls[0] + '/rsacc') or {}
            cred = self.A(acc.get('tDn', '')) if acc.get('state') == 'formed' else None
            if vc is None:
                why = 'vCenter %s nicht erreichbar' % (ca['hostOrIp'] or '(keine Adresse)')
            elif not cred:
                why = 'Keine Credentials am Controller (Associated Credential)'
            elif cred['usr'] != vc.get('user') or cred.get('pwd') != vc.get('pwd'):
                why = 'Anmeldung am vCenter fehlgeschlagen (Benutzer oder Passwort falsch)'
            elif ca['rootContName'] != vc.get('datacenter'):
                why = 'Datacenter %s existiert im vCenter nicht' % (ca['rootContName'] or '(leer)')
            else:
                why = None
            if why:
                info['reasons'].append(why)
                self.fault(ctrls[0], 'S0606', 'major', 'Connection to VMM controller %s failed: %s' % (ca['hostOrIp'], why),
                           'connect-failed', domain='infra')
                continue
            info['state'] = 'online'
            info['vc'] = vc['name']
            sw = dom + '/vswitchpolcont'
            cdp = (self.A(sw + '/rsvswitchOverrideCdpIfPol') or {}).get('tDn')
            lldp = (self.A(sw + '/rsvswitchOverrideLldpIfPol') or {}).get('tDn')
            if lldp and self.has(lldp) and self.A(lldp)['adminRxSt'] == 'enabled':
                info['discovery'] = 'lldp'
            elif cdp and self.has(cdp) and self.A(cdp)['adminSt'] == 'enabled':
                info['discovery'] = 'cdp'
            elif lldp and self.has(lldp):
                info['discovery'] = 'none'
            pool = (self.A(dom + '/rsvlanNs') or {}).get('tDn', '')
            vlans = []
            if self.has(pool):
                pmode = self.A(pool)['allocMode']
                for b in self.kids(pool, 'fvnsEncapBlk'):
                    a = self.A(b)
                    mode = pmode if a['allocMode'] == 'inherit' else a['allocMode']
                    f, t = vlan_num(a['from']), vlan_num(a['to'])
                    if mode == 'dynamic' and f and t:
                        vlans.extend(range(f, t + 1))
            if not vlans:
                self.fault(dom, 'S0607', 'minor', 'VMM Domain %s has no dynamic VLAN range (VLAN Pool with dynamic '
                           'allocation)' % name, 'encap-pool-empty', domain='infra')
            epgs = sorted(d for d, c in self.cls.items() if c['kind'] == 'epg' and
                          any(self.A(r)['tDn'] == dom and self.A(r)['state'] == 'formed' for r in self.kids(d, 'fvRsDomAtt')))
            for epg in epgs:
                if not vlans:
                    break
                v = vlans.pop(0)
                p = split_dn(epg)
                pg = '%s|%s|%s' % (p[1][3:], p[2][3:], p[3][4:])
                imm = next(self.A(r)['resImedcy'] for r in self.kids(epg, 'fvRsDomAtt') if self.A(r)['tDn'] == dom)
                info['pgs'][epg] = {'name': pg, 'vlan': v, 'imm': imm}
            # ESXi-Hosts im DVS dieser Domain
            for esx in vc.get('hosts', []):
                if name not in esx.get('dvs', []):
                    continue
                legs = []
                for s_, port in esx.get('links', []):
                    nid = self.serial_active.get(s_)
                    if nid and (nid, port) in self.ports and self.ports[(nid, port)]['qual'] != 'admin-down':
                        legs.append((nid, port))
                hinfo = {'name': esx['name'], 'legs': legs, 'ok': [], 'reasons': []}
                for leg in legs:
                    pg_dn = self.ports[leg]['pg']
                    pgi = self._pg_info(pg_dn) if pg_dn else None
                    if not pgi or dom not in pgi['domains']:
                        hinfo['reasons'].append('%s %s: Access Policy enthaelt die VMM Domain nicht' % (self.nodes[leg[0]]['name'], leg[1]))
                        continue
                    disc = info['discovery']
                    if disc == 'none' or (disc == 'lldp' and not pgi['lldp']) or (disc == 'cdp' and pgi['cdp'] != 'enabled'):
                        hinfo['reasons'].append('%s %s: keine %s-Nachbarschaft zwischen ESXi und Leaf' % (
                            self.nodes[leg[0]]['name'], leg[1], disc.upper() if disc != 'none' else 'LLDP/CDP'))
                        hinfo['nodisc'] = True
                    hinfo['ok'].append(leg)
                info['hosts'].append(hinfo)
            # Deployment je Port Group nach Resolution Immediacy
            for epg, pgi in info['pgs'].items():
                c = self.cls[epg]
                targets = set()
                if pgi['imm'] == 'pre-provision':
                    for (nid, port), pi in self.ports.items():
                        if pi['pg'] and dom in self._pg_info(pi['pg'])['domains'] and not pi['fabric']:
                            targets.add((nid, port))
                else:
                    for hinfo in info['hosts']:
                        if hinfo.get('nodisc'):
                            continue
                        if pgi['imm'] == 'lazy':
                            esx = next(e for e in vc['hosts'] if e['name'] == hinfo['name'])
                            if not any(vm.get('network') == pgi['name'] for vm in esx.get('vms', [])):
                                continue
                        targets.update(hinfo['ok'])
                for leg in sorted(targets):
                    pdn = '%s/paths-%d/pathep-[%s]' % (self.pdn(leg[0]), leg[0], leg[1])
                    if pdn in self.paths:
                        self._deploy(epg, c, pdn, self.paths[pdn], pgi['vlan'], 'regular')
            # VMs als Endpoints
            for esx in vc.get('hosts', []):
                hinfo = next((x for x in info['hosts'] if x['name'] == esx['name']), None)
                for vm in esx.get('vms', []):
                    pg = next((g for g in info['pgs'].values() if g['name'] == vm.get('network')), None)
                    if not pg:
                        continue
                    h = {'name': vm['name'], 'mac': vm['mac'], 'ip': vm['ip'], 'gw': vm.get('gw', ''), 'vlan': pg['vlan'],
                         'links': [[s_, p_] for s_, p_ in esx.get('links', [])], 'bond': 'none', 'vm': True,
                         'esxi': esx['name'], 'network': vm.get('network'), 'silent': vm.get('silent', False)}
                    if hinfo is None:
                        h['vmreason'] = 'ESXi-Host %s ist nicht im DVS %s' % (esx['name'], name)
                    self.vm_hosts.append(h)
        # VMs ohne passende Port Group
        known = {h['name'] for h in self.vm_hosts}
        for vc in vcs:
            for esx in vc.get('hosts', []):
                for vm in esx.get('vms', []):
                    if vm['name'] not in known:
                        self.vm_hosts.append({'name': vm['name'], 'mac': vm['mac'], 'ip': vm['ip'], 'gw': vm.get('gw', ''),
                                              'vlan': 0, 'links': [], 'bond': 'none', 'vm': True, 'esxi': esx['name'],
                                              'network': vm.get('network'),
                                              'vmreason': 'Port Group %s gibt es im vCenter %s nicht' % (vm.get('network') or '(keine)', vc['name'])})

    def all_hosts(self):
        return self._dhcp_hosts(self.sim.get('hosts', [])) + list(getattr(self, 'vm_hosts', [])) + list(getattr(self, 'fw_hosts', []))

    # ------------------------------------------------------------------
    # Hosts: Port-Channel/LACP, Endpoint-Learning
    # ------------------------------------------------------------------
    def _useg(self, h, match):
        """uSeg EPG: gleiche BD, gemeinsame Domain, IP- oder MAC-Attribut passt."""
        base = match['epg']
        bdoms = set(self._rs_targets(base, 'fvRsDomAtt'))
        ip = ip_of(h['ip'])
        for d, c in self.cls.items():
            if c['kind'] != 'epg' or d == base or c['bd'] != match['bd'] or self.A(d).get('isAttrBasedEPg') != 'yes':
                continue
            if not bdoms & set(self._rs_targets(d, 'fvRsDomAtt')):
                continue
            for a in self.kids(d + '/crtrn', 'fvIpAttr'):
                n = net_of(self.A(a)['ip']) if '/' in self.A(a)['ip'] else None
                if (n and ip in n) or self.A(a)['ip'] == str(ip):
                    return d
            for a in self.kids(d + '/crtrn', 'fvMacAttr'):
                if self.A(a)['mac'].upper() == h['mac'].upper():
                    return d
        return None

    def _esg(self, h, hs):
        ip = ip_of(h['ip'])
        for d, c in self.cls.items():
            if c['kind'] != 'esg' or c['vrf'] != hs['vrf'] or self.A(d)['shutdown'] == 'yes':
                continue
            for sel in self.kids(d, 'fvEPgSelector'):
                if self.A(sel)['matchEpgDn'] == hs['epg']:
                    return d
            for sel in self.kids(d, 'fvEPSelector'):
                m = re.match(r'''^\s*ip\s*==\s*['"]([^'"]+)['"]\s*$''', self.A(sel)['matchExpression'])
                if m:
                    n = net_of(m.group(1)) if '/' in m.group(1) else None
                    if (n and ip in n) or m.group(1) == str(ip):
                        return d
        return None

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
        woken = set(self.sim.get('woken', []))
        for h in self.all_hosts():
            hs = {'name': h['name'], 'learned': False, 'ipLearned': False, 'reasons': [], 'codes': [], 'legs': [],
                  'path': None, 'epg': None, 'bd': None, 'vrf': None, 'nodes': [], 'linkdown': [],
                  'vm': h.get('vm', False), 'silent': bool(h.get('silent')) and h['name'] not in woken}
            self.hosts[h['name']] = hs
            if h.get('vmreason'):
                hs['reasons'].append(h['vmreason'])
                continue
            legs = []
            for s, p in h.get('links', []):
                nid = self.serial_active.get(s)
                if nid is None:
                    up = getattr(self, 'fw_reload', {}).get(s)
                    hs['reasons'].append('Switch %s laedt gerade neu (Firmware-Upgrade auf %s, Upgrade Group %s)'
                                         % (self.node_label(s), plain(up['version']), up.get('grp')) if up else
                                         'Switch %s ist nicht aktiv (%s)' % (self.node_label(s), self.mp['reasons'].get(s) or 'nicht registriert oder noch in Discovery'))
                    hs['codes'].append('SWITCH_INACTIVE')
                    continue
                if self.ports.get((nid, p), {}).get('qual') == 'error-disabled':
                    hs['reasons'].append('%s %s ist error-disabled (%s)' % (self.nodes[nid]['name'], p, self.ports[(nid, p)].get('errdis')))
                    hs['codes'].append('PORT_ERR_DISABLED')
                    continue
                if self.ports.get((nid, p), {}).get('qual') == 'admin-down':
                    hs['reasons'].append('%s %s ist deaktiviert (Disabled Interface)' % (self.nodes[nid]['name'], p))
                    hs['codes'].append('PORT_ADMIN_DOWN')
                    continue
                if h.get('linkdown') and (nid, p) in self.ports:
                    hs['reasons'].append('%s %s: kein Link (operSt down, link-not-connected) - Kabel oder NIC des Hosts '
                                         '(simulator-spezifisches Ereignis)' % (self.nodes[nid]['name'], p))
                    hs['codes'].append('LINK_DOWN')
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
                path = '%s/paths-%d/pathep-[%s]' % (self.pdn(legs[0][0]), legs[0][0], legs[0][1])
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
            if bd in self.learn_off:
                hs.update({'learned': False, 'ipLearned': False})
                hs['reasons'].append(self.learn_off[bd])
                continue
            if bd in self.storm_bds:
                hs['storm'] = self.storm_bds[bd]
                hs['reasons'].append(self.storm_bds[bd])
            if bd in getattr(self, 'rogue_bds', {}):
                hs['rogue'] = self.rogue_bds[bd]
                hs['reasons'].append(self.rogue_bds[bd])
            useg = self._useg(h, match)
            if useg:
                hs['base'], hs['epg'] = match['epg'], useg
            esg = self._esg(h, hs)
            if esg:
                hs['esg'] = esg
            if not ip_learn:
                hs['reasons'].append('IP %s wird nicht gelernt (%s)' % (
                    ip, 'Unicast Routing im BD aus' if bda['unicastRoute'] != 'yes'
                    else 'IP liegt in keinem BD-Subnetz und "Limit IP Learning to Subnet" ist aktiv'))
            if hs['silent']:
                hs['learned'] = False
                hs['quiet'] = True
                hs['reasons'].append('Stiller Host: sendet erst, wenn ihn jemand anspricht (ARP)')
                continue
            mac = h['mac'].upper()
            cep = hs['epg'] + '/cep-' + mac
            self.store.add(cep, 'fvCEp', {'mac': mac, 'name': mac, 'ip': str(ip) if ip_learn else '0.0.0.0',
                                          'encap': 'vlan-%d' % match['vlan'], 'lcC': 'learned,vmm' if h.get('vm') else 'learned',
                                          'fabricPathDn': path, 'id': '0', 'mcastAddr': 'not-applicable',
                                          'contName': '', 'baseEpgDn': ''}, True)
            if ip_learn:
                self.store.add(cep + '/ip-[%s]' % ip, 'fvIp', {'addr': str(ip), 'createTs': now_ts()}, True)
            self.store.add(cep + '/rscEpToPathEp-[%s]' % path, 'fvRsCEpToPathEp',
                           {'tDn': path, 'state': 'formed', 'lcC': 'learned'}, True)
            hs['cep'] = cep
        self._shared_ips()

    def _shared_ips(self):
        """White Paper Endpoint Learning, 'When to disable IP Data-plane Learning': Teilen sich Active und Standby
        eine IP (VIP) und sendet der Standby noch Pakete von dieser IP (z. B. TCP RST), lernt der Leaf die IP per
        Data Plane am Standby (Table 2). Mit IP Data-plane Learning aus (VRF) bzw. Endpoint Data-plane Learning aus
        (BD) lernt er lokale IPs nur per ARP/GARP (Control Plane), also nur vom Active. Der Simulator nimmt den
        unguenstigen Endzustand des Papers an: Das letzte Paket kam vom Standby."""
        self.ip_owner = {}
        groups = {}
        for h in self.all_hosts():
            hs = self.hosts[h['name']]
            if hs.get('learned') and hs.get('ipLearned') and hs.get('cep'):
                groups.setdefault((hs['vrf'], str(ip_of(h['ip']))), []).append(h)
        for (vrf, ip), hl in sorted(groups.items()):
            if len(hl) < 2:
                continue
            names = sorted(x['name'] for x in hl)
            act = sorted(x['name'] for x in hl if not x.get('standby'))
            sby = sorted(x['name'] for x in hl if x.get('standby'))
            if len(act) != 1:
                for n in names:
                    self.hosts[n]['reasons'].append('IP %s ist mehrfach konfiguriert (%s): doppelte IP ohne '
                                                    'Active/Standby-Rolle' % (ip, ', '.join(names)))
                continue
            dp_vrf = (self.A(vrf) or {}).get('ipDataPlaneLearning', 'enabled') == 'enabled'
            dp = [n for n in sby if dp_vrf and (self.A(self.hosts[n]['bd']) or {}).get('ipLearning', 'yes') == 'yes']
            owner = dp[0] if dp else act[0]
            self.ip_owner[(vrf, ip)] = owner
            for n in names:
                hs = self.hosts[n]
                if n == owner:
                    if dp:
                        hs['reasons'].append('VIP %s per Data Plane am Standby gelernt (z. B. TCP RST vom Standby) - '
                                             'geroutete Pakete an die VIP gehen an %s' % (ip, n))
                    continue
                self.store.delete(hs['cep'] + '/ip-[%s]' % ip)
                a = self.store.attrs(hs['cep'])
                if a is not None:
                    a['ip'] = '0.0.0.0'
                hs['reasons'].append('VIP %s: Die Fabric fuehrt die IP am %s %s; hier nur die MAC gelernt'
                                     % (ip, 'Standby' if dp else 'Active (ARP/GARP, IP Data-plane Learning aus)', owner))
            if dp:
                self.fault(self.hosts[owner]['bd'], 'S1692', 'warning',
                           'IP %s learned via data plane on standby device %s; consider disabling IP Data-plane Learning '
                           'in VRF %s' % (ip, owner, self.short(vrf)), 'ip-dataplane-learning-vip')
