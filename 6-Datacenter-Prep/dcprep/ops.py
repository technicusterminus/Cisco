"""Betriebsthemen: Firmware-Upgrade, Loop-Schutz (MCP), DHCP Relay, Monitoring und Config Export/Import.

Die Engine-Teile (OpsMixin) laufen bei jedem Neuaufbau mit. Die Funktionen
weiter unten (run_triggers, snmp_walk, deliver) arbeiten auf dem Sim-Objekt
des Servers, weil sie Konfiguration aendern oder Dateien schreiben.
"""
import hashlib
import ipaddress
import json
import re
import time

from .model import CLASSES, AciError, _alloc, now_ts, parent_dn, split_dn, tenant_of

APIC_BASE = '6.0(5h)'
SWITCH_BASE = 'n9000-16.0(5h)'
SECURE = {'pwd', 'password', 'key', 'userPasswd', 'passphrase'}
FAULT_SEV = ['info', 'warning', 'minor', 'major', 'critical']
SYSLOG_LVL = {'critical': 2, 'major': 3, 'minor': 4, 'warning': 4, 'info': 6, 'cleared': 5}
SYSLOG_SEV = ['emergencies', 'alerts', 'critical', 'errors', 'warnings', 'notifications', 'information', 'debugging']
IMAGES = [('aci-apic-dk9.6.0.6c.iso', 7.2), ('aci-n9000-dk9.16.0.6c.bin', 2.1),
          ('aci-apic-dk9.6.1.1e.iso', 7.4), ('aci-n9000-dk9.16.1.1e.bin', 2.2)]


def default_fileserver():
    return {'name': 'fileserver', 'ip': '192.168.10.50', 'user': 'backup', 'pwd': 'Backup123!',
            'protocols': ['scp', 'sftp', 'ftp', 'http'], 'dirs': ['/backup', '/images'], 'down': False,
            'files': {'/images/' + n: {'size': '%.1f GB' % s, 'image': True} for n, s in IMAGES}}


def default_monitors():
    return [{'name': 'syslog-srv', 'type': 'syslog', 'ip': '192.168.10.60', 'port': 514},
            {'name': 'snmp-nms', 'type': 'snmp', 'ip': '192.168.10.61', 'port': 162, 'community': 'NMS-Read'},
            {'name': 'mail-srv', 'type': 'smtp', 'ip': '192.168.10.62', 'port': 25}]


def image_info(fname):
    """'aci-n9000-dk9.16.0.6c.bin' -> (name, version, type)."""
    m = re.match(r'^(aci-(apic|n9000)-dk9\.(\d+)\.(\d+)\.(\w+))\.(iso|bin)$', fname)
    if not m:
        return None
    ver = '%s.%s(%s)' % (m.group(3), m.group(4), m.group(5))
    if m.group(2) == 'apic':
        return m.group(1), 'apic-' + ver, 'controller'
    return m.group(1), 'n9000-' + ver, 'switch'


def ver_key(v):
    """Vergleichsschluessel; Switch 16.x entspricht APIC 6.x."""
    m = re.search(r'(\d+)\.(\d+)\((\d+)(\w*)\)', v or '')
    if not m:
        return (0, 0, 0, '')
    major = int(m.group(1))
    if major >= 10:
        major -= 10
    return (major, int(m.group(2)), int(m.group(3)), m.group(4))


def plain(v):
    return re.sub(r'^(apic|n9000)-', '', v or '')


def keyhash(pp):
    return hashlib.sha256(('aci-export:' + pp).encode()).hexdigest()[:16] if pp else ''


class OpsMixin:
    # ------------------------------------------------------------------ Firmware
    def _fw_state(self, now):
        """Fortschritt der Upgrades; liefert {serial: upgrade} der Knoten im Reload."""
        fw = self.sim.setdefault('fw', {})
        reload, self.apic_upgrade = {}, None
        for up in self.sim.get('upgrades', []):
            end = up['start'] + up['dur']
            if up.get('done'):
                continue
            if now >= end:
                for s in up['serials']:
                    fw[s] = up['version']
                up['done'] = True
                continue
            if up['kind'] == 'ctrl':
                self.apic_upgrade = up
            for s in up['serials']:
                reload[s] = up
        self.apic_version = plain(fw.get('apic', 'apic-' + APIC_BASE))
        self.fw_reload = reload
        ends = [u['start'] + u['dur'] for u in self.sim.get('upgrades', []) if not u.get('done')]
        return min(ends) if ends else None

    def node_version(self, serial):
        return self.sim.get('fw', {}).get(serial, SWITCH_BASE)

    def _fw_groups(self):
        """Upgrade Groups auswerten: Mitglieder, Policy, Warnungen (vPC-Paar, alle Spines)."""
        self.fw_groups = []
        member = {}
        spines = {nid for nid, n in self.nodes.items() if n['role'] == 'spine'}
        for g in sorted(self.store.by_class('maintMaintGrp')):
            ids = set()
            for b in self.kids(g, 'fabricNodeBlk'):
                a = self.A(b)
                f, t = int(a['from_'] or 0), int(a['to_'] or a['from_'] or 0)
                ids |= {n for n in self.nodes if f <= n <= t}
            rs = self.A(g + '/rsmgrpp') or {}
            pol = rs.get('tDn') if rs.get('state') == 'formed' else None
            warn = []
            for a, b in {tuple(sorted((n, self.vpc_peer[n]))) for n in ids if n in self.vpc_peer}:
                if a in ids and b in ids:
                    warn.append('vPC-Paar %d/%d ist in derselben Upgrade Group - beide Switches laden gleichzeitig neu' % (a, b))
                    self.fault(g, 'S1801', 'warning', 'Both vPC peers (node %d and %d) are members of upgrade group %s - '
                               'they reload at the same time and dual-homed hosts lose connectivity' % (a, b, self.A(g)['name']),
                               'vpc-peers-in-same-upgrade-group', domain='infra')
            if spines and spines <= ids:
                warn.append('Alle Spines sind in derselben Upgrade Group - die Fabric verliert waehrend des Reloads jede Verbindung zwischen den Leafs')
                self.fault(g, 'S1802', 'major', 'All spine switches are members of upgrade group %s - the fabric is '
                           'partitioned while they reload' % self.A(g)['name'], 'all-spines-in-same-upgrade-group', domain='infra')
            for n in ids:
                if n in member:
                    self.fault(g, 'S1803', 'minor', 'Node %d is a member of more than one upgrade group (%s)' % (n, member[n]),
                               'node-in-multiple-upgrade-groups', domain='infra')
                member[n] = self.A(g)['name']
            self.fw_groups.append({'dn': g, 'name': self.A(g)['name'], 'nodes': sorted(ids), 'pol': pol, 'warn': warn})

    def _fw_emit(self):
        st = self.store
        st.add('fwrepo', 'firmwareRepo', {}, True)
        for img in self.sim.get('fwrepo', []):
            st.add('fwrepo/fw-' + img['name'], 'firmwareFirmware',
                   {'name': img['name'], 'fullVersion': img['version'], 'type': img['type'], 'size': img['size'],
                    'isoname': img['file'], 'checksum': hashlib.md5(img['name'].encode()).hexdigest(),
                    'downloadDate': img['date']}, True)
        jobs = {}
        for up in self.sim.get('upgrades', []):
            for s in up['serials']:
                jobs[s] = up
        for nid, n in list(self.nodes.items()) + [(1, {'serial': self.sim['topology']['apic']['serial'], 'state': 'active'})]:
            sysdn = '%s/node-%d/sys' % (self.pdn(nid), nid)
            s = n['serial']
            ver = ('apic-' + self.apic_version) if nid == 1 else self.node_version(s)
            if not self.has(sysdn):
                continue
            st.add(sysdn + '/fwstatuscont', 'firmwareFwStatusCont', {}, True)
            st.add(sysdn + '/fwstatuscont/running', 'firmwareRunning',
                   {'version': plain(ver), 'peVer': plain(ver), 'type': 'controller' if nid == 1 else 'switch'}, True)
            up = jobs.get(s)
            if up:
                pct = 100 if up.get('done') else int(min(99, (self.now - up['start']) * 100 / max(up['dur'], 1)))
                stt = 'completeok' if up.get('done') else 'inprogress'
                st.add(sysdn + '/fwstatuscont/upgjob', 'maintUpgJob',
                       {'upgradeStatus': stt, 'instlProgPct': str(pct), 'desiredVersion': up['version'], 'fwGrp': up.get('grp', ''),
                        'maintGrp': up.get('grp', ''), 'upgradeStatusStr': 'Upgrade completed' if up.get('done') else
                        'Installing firmware and reloading'}, True)

    # ------------------------------------------------------------------ Loops / MCP
    def _mcp_if(self, leg):
        pg = self.ports.get(leg, {}).get('pg')
        name = (self.A(pg + '/rsmcpIfPol') or {}).get('tnMcpIfPolName') if pg else ''
        pol = self.A('uni/infra/mcpIfP-%s' % (name or 'default'))
        return bool(pol) and pol['adminSt'] == 'enabled'

    def _loops(self):
        """Legacy-Switches, die an mehreren Ports haengen, bilden eine Schleife, wenn sie eine VLAN-Encap
        auf zwei Ports verbinden. MCP oder Endpoint Loop Protection koennen sie brechen."""
        self.loops, self.storm_bds, self.learn_off = [], {}, {}
        mcp = self.A('uni/infra/mcpInstP-default') or {}
        mcp_on = mcp.get('adminSt') == 'enabled' and bool(mcp.get('key'))
        per_vlan = 'pdu-per-vlan' in (mcp.get('ctrl') or '')
        eplp = self.A('uni/infra/epLoopProtectP-default') or {}
        for sw in self.sim.get('switches', []):
            legs = []
            for s, p in sw.get('links', []):
                nid = self.serial_active.get(s)
                if nid is not None and (nid, p) in self.ports and self.ports[(nid, p)].get('qual') != 'admin-down':
                    legs.append((nid, p))
            info = {'name': sw['name'], 'legs': legs, 'loop': False, 'tags': [], 'bds': [], 'action': None, 'text': ''}
            self.loops.append(info)
            for l in legs:
                self.ports[l].update({'oper': 'up', 'qual': 'link-up', 'peer': ('switch', sw['name'], 'Gi0/%d' % (legs.index(l) + 1))})
            if len(legs) < 2:
                continue
            if sw.get('bond', 'none') != 'none':
                paths = {d for d, p in self.paths.items() if p['type'] in ('pc', 'vpc') and set(legs) <= set(p['legs'])}
                if paths:
                    info['text'] = 'Die Links bilden einen Port-Channel - keine Schleife'
                    continue
            allowed = {int(v) for v in re.findall(r'\d+', str(sw.get('vlans') or ''))}
            tags = {}
            for d in self.deploys:
                for l in d['legs']:
                    if l in legs:
                        tag = 'untagged' if d['mode'] in ('untagged', 'native') else d['vlan']
                        if tag != 'untagged' and allowed and d['vlan'] not in allowed:
                            continue
                        tags.setdefault(tag, {}).setdefault(l, set()).add(d['bd'])
            loop_tags = {t: v for t, v in tags.items() if len(v) >= 2}
            if not loop_tags:
                info['text'] = 'Keine gemeinsame VLAN-Encap auf den Ports - keine Schleife'
                continue
            bds = sorted({bd for v in loop_tags.values() for s_ in v.values() for bd in s_})
            info.update({'loop': True, 'tags': sorted(loop_tags, key=str), 'bds': bds})
            looped = sorted({l for v in loop_tags.values() for l in v}, key=lambda x: (x[0], int(x[1].split('/')[-1])))
            mcp_tags = [t for t in loop_tags if per_vlan or t == 'untagged']
            mcp_legs = [l for l in looped if self._mcp_if(l)]
            names = ', '.join('%s %s' % (self.nodes[n]['name'], p) for n, p in looped)
            if mcp_on and mcp_tags and mcp_legs and mcp.get('loopProtectAct') == 'port-disable':
                victim = mcp_legs[-1]
                self._errdisable(victim, 'mcp-loop-err-disable')
                info.update({'action': 'mcp', 'victim': victim,
                             'text': 'MCP hat die Schleife erkannt (eigene MCP-PDU zurueck empfangen) und %s %s error-disabled'
                                     % (self.nodes[victim[0]]['name'], victim[1])})
                self.fault(self._pdn(victim), 'S2533', 'major', 'Loop detected by MCP on %s %s (legacy switch %s) - port error-disabled'
                           % (self.nodes[victim[0]]['name'], victim[1], sw['name']), 'mcp-loop-detected', domain='access')
                continue
            if mcp_on and mcp_tags and mcp_legs:
                info['text'] = 'MCP erkennt die Schleife, die Loop Protection Action ist aber nicht port-disable - die Schleife bleibt'
                self.fault(self._pdn(mcp_legs[-1]), 'S2533', 'major', 'Loop detected by MCP on %s %s (no action configured)'
                           % (self.nodes[mcp_legs[-1][0]]['name'], mcp_legs[-1][1]), 'mcp-loop-detected', domain='access')
            elif mcp_on and not mcp_tags:
                info['text'] = ('MCP ist aktiv, sendet seine PDUs aber nur untagged. Die Schleife laeuft ueber %s - '
                                'dafuer braucht es "Enable MCP PDU per VLAN"' % ', '.join('vlan-%s' % t for t in loop_tags))
            elif mcp_on:
                info['text'] = 'MCP ist auf den betroffenen Ports per MCP Interface Policy deaktiviert'
            else:
                info['text'] = 'MCP ist global nicht aktiv (MCP Instance Policy default: Admin State und Key)'
            if eplp.get('adminSt') == 'enabled':
                act = eplp.get('action') or ''
                if 'port-disable' in act:
                    victim = looped[-1]
                    self._errdisable(victim, 'ep-move-loop-err-disable')
                    info.update({'action': 'eplp', 'victim': victim,
                                 'text': info['text'] + '. Endpoint Loop Protection: die MACs springen zwischen %s - Port %s %s error-disabled'
                                 % (names, self.nodes[victim[0]]['name'], victim[1])})
                    self.fault(self._pdn(victim), 'S2535', 'major', 'Endpoint loop protection: endpoint moves between %s - '
                               'port %s %s disabled' % (names, self.nodes[victim[0]]['name'], victim[1]), 'ep-loop-detected', domain='access')
                    continue
                if 'bd-learn-disable' in act:
                    for bd in bds:
                        self.learn_off[bd] = 'Endpoint Loop Protection hat das Lernen im BD %s abgeschaltet (Schleife ueber %s)' % (self.short(bd), names)
                    info['action'] = 'bd-learn'
                    info['text'] += '. Endpoint Loop Protection hat das Endpoint Learning in %s abgeschaltet' % ', '.join(self.short(b) for b in bds)
            for bd in bds:
                self.storm_bds[bd] = ('Broadcast-Storm: Schleife ueber den Legacy-Switch %s (%s) - Frames kreisen, die MACs springen '
                                      'zwischen den Ports' % (sw['name'], names))
                self.fault(bd, 'S2534', 'critical', 'Layer 2 loop in bridge domain %s via %s (%s): endpoint flapping and broadcast storm'
                           % (self.short(bd), sw['name'], names), 'l2-loop', domain='tenant')

    def _pdn(self, leg):
        return '%s/paths-%d/pathep-[%s]' % (self.pdn(leg[0]), leg[0], leg[1])

    def _errdisable(self, leg, why):
        pi = self.ports[leg]
        pi.update({'oper': 'down', 'qual': 'error-disabled', 'errdis': why})

    # ------------------------------------------------------------------ DHCP Relay
    def _dhcp_hosts(self, hosts):
        leases = self.sim.get('leases', {})
        out = []
        for h in hosts:
            if h.get('dhcp'):
                l = leases.get(h['name'])
                h = dict(h, ip=l['ip'] if l else '0.0.0.0/32', gw=l['gw'] if l else '')
            out.append(h)
        return out

    def _relay_of(self, bd, lbl):
        a = self.A(lbl)
        if a['owner'] == 'infra':
            c = ['uni/infra/relayp-' + a['name']]
        else:
            c = [tenant_of(bd) + '/relayp-' + a['name'], 'uni/tn-common/relayp-' + a['name']]
        return next((x for x in c if self.has(x)), None), c[0]

    def _dhcp(self):
        """DHCP-Clients bekommen eine Adresse, wenn der BD ein Relay Label hat und der Server antwortet."""
        old = self.sim.get('leases', {})
        new, self.dhcp_info = {}, {}
        hosts = {h['name']: h for h in self.all_hosts()}
        for lbl in self.store.by_class('dhcpLbl'):
            bd = parent_dn(lbl)
            rel, want = self._relay_of(bd, lbl)
            if not rel:
                self.fault(lbl, 'S0721', 'minor', 'DHCP relay label %s: no DHCP relay policy %s found (owner %s)'
                           % (self.A(lbl)['name'], want, self.A(lbl)['owner']), 'dhcp-relay-policy-missing')
        for h in self.sim.get('hosts', []):
            if not h.get('dhcp'):
                continue
            hs = self.hosts.get(h['name'], {})
            info = {'ok': False, 'why': None, 'relay': None, 'server': None, 'ip': None}
            self.dhcp_info[h['name']] = info
            hs['reasons'] = [r for r in hs.get('reasons', []) if not r.startswith('IP 0.0.0.0')]
            if not hs.get('learned'):
                info['why'] = 'Der Client ist nicht im Fabric gelernt (DHCP Discover erreicht keine EPG)'
                continue
            res = self._dhcp_offer(h, hs, hosts, old.get(h['name']), new)
            if isinstance(res, str):
                info['why'] = res
                hs['reasons'].append('Kein DHCP-Lease: ' + res)
                continue
            info.update(res)
            info['ok'] = True
            new[h['name']] = {'ip': res['ip'], 'gw': res['gw'], 'server': res['server']}
        return new != old, new

    def _dhcp_offer(self, h, hs, hosts, prev, taken):
        bd = hs['bd']
        servers = [x for x in hosts.values() if x.get('dhcpd') and x['name'] != h['name']]
        subs = self.bd_subnets(bd)
        same = []
        for srv in servers:
            ss = self.hosts.get(srv['name'], {})
            if ss.get('learned') and ss.get('bd') == bd:
                same.append(srv)
        relay, why = None, None
        lbls = self.kids(bd, 'dhcpLbl')
        if not lbls and not same:
            return ('BD %s hat kein DHCP Relay Label - der DHCP Discover (Broadcast) bleibt im BD, dort antwortet kein '
                    'DHCP-Server' % self.short(bd))
        cands = []
        if same:
            giaddr = None
            cands = [(srv, None, 'direkt im BD (Broadcast)') for srv in same]
        else:
            if self.A(bd)['unicastRoute'] != 'yes':
                return 'Unicast Routing ist im BD %s aus - die ACI kann nicht als Relay Agent arbeiten' % self.short(bd)
            if not subs:
                return 'BD %s hat kein Subnetz - der Relay Agent braucht eine eigene Adresse (giaddr)' % self.short(bd)
            giaddr = subs[0]
            for lbl in lbls:
                rel, want = self._relay_of(bd, lbl)
                if not rel:
                    why = 'DHCP Relay Label %s: die Policy %s gibt es nicht (Owner %s)' % (self.A(lbl)['name'], want, self.A(lbl)['owner'])
                    continue
                relay = rel
                provs = self.kids(rel, 'dhcpRsProv')
                if not provs:
                    why = 'DHCP Relay Policy %s hat keinen Provider (EPG und Server-Adresse)' % self.short(rel)
                for p in provs:
                    pa = self.A(p)
                    srv = next((x for x in servers if str(ipaddress.ip_interface(x['ip']).ip) == pa['addr']), None)
                    if not srv:
                        why = 'Provider %s: unter %s antwortet kein DHCP-Server' % (self.short(pa['tDn']), pa['addr'])
                        continue
                    ss = self.hosts.get(srv['name'], {})
                    if not ss.get('learned'):
                        why = 'DHCP-Server %s ist nicht im Fabric gelernt (%s)' % (srv['name'], '; '.join(ss.get('reasons', [])[:1]))
                        continue
                    if ss.get('epg') != pa['tDn'] and ss.get('base') != pa['tDn']:
                        why = 'DHCP-Server %s liegt in EPG %s, der Provider der Relay Policy ist aber %s' % (
                            srv['name'], self.short(ss.get('epg')), self.short(pa['tDn']))
                        continue
                    if ss.get('vrf') != hs.get('vrf'):
                        why = 'DHCP-Server %s liegt in VRF %s, der Client in VRF %s' % (srv['name'], self.short(ss.get('vrf')), self.short(hs.get('vrf')))
                        continue
                    if not ss.get('ipLearned'):
                        why = 'Die IP des DHCP-Servers %s ist nicht gelernt' % srv['name']
                        continue
                    cands.append((srv, relay, 'Relay %s an %s' % (giaddr['gw'], pa['addr'])))
        for srv, relay, how in cands:
            scope = None
            for sc in srv.get('dhcpd') or []:
                try:
                    n = ipaddress.ip_network(sc['net'], strict=False)
                except (ValueError, KeyError):
                    continue
                if (giaddr and ipaddress.ip_address(giaddr['gw']) in n) or (not giaddr and any(s['net'] == n for s in subs)) \
                        or (not giaddr and not subs):
                    scope = (n, sc)
                    break
            if not scope:
                why = 'DHCP-Server %s hat keinen Scope fuer das Netz %s' % (
                    srv['name'], giaddr['net'] if giaddr else (subs[0]['net'] if subs else 'des BD'))
                continue
            n, sc = scope
            used = {str(ipaddress.ip_interface(x['ip']).ip) for x in hosts.values() if not x.get('dhcp')}
            used |= {v['ip'].split('/')[0] for v in taken.values()}
            try:
                lo, hi = ipaddress.ip_address(sc['from']), ipaddress.ip_address(sc['to'])
            except (ValueError, KeyError):
                why = 'Scope %s auf %s hat keinen gueltigen Adressbereich' % (n, srv['name'])
                continue
            ip = None
            if prev and prev.get('server') == srv['name']:
                p = ipaddress.ip_address(prev['ip'].split('/')[0])
                if lo <= p <= hi and str(p) not in used:
                    ip = p
            if ip is None:
                cur = lo
                while cur <= hi:
                    if str(cur) not in used:
                        ip = cur
                        break
                    cur += 1
            if ip is None:
                why = 'Scope %s auf %s ist voll' % (n, srv['name'])
                continue
            gw = sc.get('gw') or (giaddr['gw'] if giaddr else '')
            return {'ip': '%s/%d' % (ip, n.prefixlen), 'gw': gw, 'server': srv['name'], 'relay': relay, 'how': how}
        return why or 'Kein DHCP-Server antwortet'

    # ------------------------------------------------------------------ Monitoring
    def _monitoring(self):
        self.mon = []
        mons = self.sim.get('monitors', [])
        cdn = 'uni/fabric/moncommon'

        def mgmt_ok(epg, sender=1):
            if epg and '/inb-' in epg:
                return bool(getattr(self, 'inb', {}).get(sender))
            return bool(self.oob.get(sender))

        def collector(ip, kind):
            return next((m for m in mons if m['ip'] == ip and m['type'] == kind), None)

        for src_cls, grp_cls, kind in (('syslogSrc', 'syslogGroup', 'syslog'), ('snmpSrc', 'snmpGroup', 'snmp'),
                                       ('callhomeSrc', 'callhomeGroup', 'smtp')):
            for src in self.kids(cdn, src_cls):
                sa = self.A(src)
                rs = self.A(src + '/rsdestGroup') or {}
                grp = rs.get('tDn') if rs.get('state') == 'formed' else None
                base = {'src': src, 'kind': kind, 'minSev': sa['minSev'], 'incl': set((sa['incl'] or '').split(',')), 'group': grp}
                if not grp:
                    self.mon.append(dict(base, ok=False, why='Source %s ist mit keiner Destination Group verknuepft' % sa['name'],
                                         host='', collector=None))
                    continue
                if kind == 'syslog':
                    for d in self.kids(grp, 'syslogRemoteDest'):
                        a = self.A(d)
                        epg = (self.A(d + '/rsARemoteHostToEpg') or {}).get('tDn') or ''
                        c = collector(a['host'], 'syslog')
                        why = None
                        if a['adminState'] != 'enabled':
                            why = 'Destination ist deaktiviert'
                        elif not epg:
                            why = 'Kein Management EPG an der Destination (Management EPG: default (Out-of-Band))'
                        elif not c:
                            why = 'Unter %s laeuft kein Syslog-Server' % a['host']
                        elif c.get('down'):
                            why = 'Syslog-Server %s ist ausgefallen' % c['name']
                        elif int(a['port'] or 0) != int(c.get('port', 514)):
                            why = 'Port %s, der Server lauscht auf %s' % (a['port'], c.get('port', 514))
                        self.mon.append(dict(base, dn=d, host=a['host'], ok=why is None, why=why, collector=c and c['name'], epg=epg,
                                             sev=a['severity'], fac=a['forwardingFacility'], fmt=self.A(grp)['format']))
                elif kind == 'snmp':
                    for d in self.kids(grp, 'snmpTrapDest'):
                        a = self.A(d)
                        epg = (self.A(d + '/rsARemoteHostToEpg') or {}).get('tDn') or ''
                        c = collector(a['host'], 'snmp')
                        why = None
                        if not epg:
                            why = 'Kein Management EPG an der Trap Destination'
                        elif not c:
                            why = 'Unter %s laeuft kein SNMP-Manager' % a['host']
                        elif c.get('down'):
                            why = 'SNMP-Manager %s ist ausgefallen' % c['name']
                        elif int(a['port'] or 0) != int(c.get('port', 162)):
                            why = 'Port %s, der Manager empfaengt Traps auf %s' % (a['port'], c.get('port', 162))
                        elif a['ver'] == 'v3':
                            why = 'SNMPv3-Traps sind im Simulator nicht nachgebildet - v2c verwenden'
                        self.mon.append(dict(base, dn=d, host=a['host'], ok=why is None, why=why, collector=c and c['name'], epg=epg,
                                             community=a['secName'], ver=a['ver']))
                else:
                    prof = grp + '/prof'
                    pa = self.A(prof) or {}
                    smtp = (self.A(prof + '/smtp') or {}).get('host', '')
                    epg = (self.A(prof + '/smtp/rsARemoteHostToEpg') or {}).get('tDn') or ''
                    c = collector(smtp, 'smtp') if smtp else None
                    for d in self.kids(grp, 'callhomeDest'):
                        a = self.A(d)
                        why = None
                        if a['adminState'] != 'enabled':
                            why = 'Destination ist deaktiviert'
                        elif not pa:
                            why = 'Die Destination Group hat kein Profil (Kontakt, From-Adresse, SMTP-Server)'
                        elif not pa.get('from'):
                            why = 'Im Callhome-Profil fehlt die From-Adresse'
                        elif not smtp:
                            why = 'Im Callhome-Profil ist kein SMTP-Server eingetragen'
                        elif not epg:
                            why = 'Kein Management EPG am SMTP-Server'
                        elif not c:
                            why = 'Unter %s laeuft kein Mailserver' % smtp
                        elif c.get('down'):
                            why = 'Mailserver %s ist ausgefallen' % c['name']
                        elif int(pa.get('port') or 25) != int(c.get('port', 25)):
                            why = 'SMTP-Port %s, der Mailserver lauscht auf %s' % (pa.get('port'), c.get('port', 25))
                        self.mon.append(dict(base, dn=d, host=smtp, ok=why is None, why=why, collector=c and c['name'], epg=epg,
                                             to=a['email'], fmt=a['format'], frm=pa.get('from', '')))
        for d in self.mon:
            d['mgmt'] = mgmt_ok
        self.snmp_pol = None
        pg = (self.ntp or {}).get('pgrp')
        if pg:
            rs = self.A(pg + '/rssnmpPol') or {}
            if rs.get('state') == 'formed':
                self.snmp_pol = rs['tDn']


# ---------------------------------------------------------------------- Zustellung
def sender_of(dn):
    if not (dn or '').startswith('topology/'):
        return 1
    m = re.search(r'/(?:node|paths)-(\d+)', dn or '')
    if m:
        return int(m.group(1))
    m = re.search(r'/protpaths-(\d+)-', dn or '')
    return int(m.group(1)) if m else 1


def deliver(S, recs):
    """Neue Faults, Events und Audit-Eintraege an Syslog, SNMP-Manager und Mailserver zustellen."""
    e = S.engine
    dests = [d for d in getattr(e, 'mon', []) if d.get('ok')]
    if not dests:
        return
    log = S.sim.setdefault('monlog', {})
    for r in recs:
        kind = r['kind']
        for d in dests:
            inc = d['incl']
            if 'all' not in inc and kind + ('s' if kind != 'audit' else '') not in inc and kind not in inc:
                continue
            sev = r.get('severity', 'info')
            if kind == 'fault':
                base = r.get('orig', sev)
                if base in FAULT_SEV and d['minSev'] in FAULT_SEV and FAULT_SEV.index(base) < FAULT_SEV.index(d['minSev']):
                    continue
            lvl = SYSLOG_LVL.get(sev if kind == 'fault' else 'info', 6)
            snd = sender_of(r['dn'])
            if snd != 1 and snd not in e.nodes:
                snd = 1
            name = e.nodes[snd]['name'] if snd != 1 else S.sim['topology']['apic']['name']
            entry = {'ts': now_ts(), 'from': name}
            if not d['mgmt'](d.get('epg'), snd):
                entry.update({'dropped': True, 'text': '(nicht zugestellt: %s hat keine %s-Adresse) %s' % (
                    name, 'In-Band' if '/inb-' in (d.get('epg') or '') else 'Out-of-Band-Management', r['descr'])})
            elif d['kind'] == 'syslog':
                if lvl > SYSLOG_SEV.index(d['sev']):
                    continue
                fac = int(d['fac'].replace('local', '')) + 16
                tag = {'fault': 'SYSTEM_MSG', 'event': 'SYSTEM_MSG', 'audit': 'AUDIT_MSG'}[kind]
                entry['text'] = '<%d> %s %s %%LOG_%s-%d-%s [%s][%s][%s][%s][%s] %s' % (
                    fac * 8 + lvl, time.strftime('%b %d %H:%M:%S'), name, d['fac'].upper(), lvl, tag, r.get('code', ''),
                    r.get('lc', 'transition'), r.get('cause', ''), sev, r['dn'], r['descr'])
            elif d['kind'] == 'snmp':
                c = next((m for m in S.sim.get('monitors', []) if m['name'] == d['collector']), {})
                if c.get('community') and d['community'] != c.get('community'):
                    entry.update({'dropped': True, 'text': 'Trap von %s verworfen: unbekannte Community "%s" (erwartet: %s)'
                                  % (name, d['community'], c.get('community'))})
                else:
                    entry['text'] = 'SNMP%s-Trap von %s, Community %s: CISCO-APIC-MIB::%s code=%s severity=%s affected=%s descr="%s"' % (
                        d['ver'], name, d['community'], 'ciscoAciFaultNotification' if kind == 'fault' else 'ciscoAciEventNotification',
                        r.get('code', ''), sev, r['dn'], r['descr'])
            else:
                entry['text'] = 'Mail an %s (Absender %s, Format %s): [Callhome] %s %s - %s' % (
                    d['to'], d['frm'], d['fmt'], sev.upper(), r.get('code', ''), r['descr'])
            log.setdefault(d['collector'], []).append(entry)
            del log[d['collector']][:-300]


# ---------------------------------------------------------------------- SNMP-Abfrage
def snmp_walk(S, manager, target, community):
    e = S.engine
    mgr = next((m for m in S.sim.get('monitors', []) if m['name'] == manager and m['type'] == 'snmp'), None)
    if not mgr:
        raise AciError(400, 'SNMP-Manager %s gibt es nicht' % manager)
    nid = next((n for n, x in e.nodes.items() if x['name'] == target), 1 if target in ('', S.sim['topology']['apic']['name']) else None)
    if nid is None:
        raise AciError(400, 'Unbekannter Node %s' % target)
    addr = e.oob.get(nid)
    name = e.nodes[nid]['name'] if nid != 1 else S.sim['topology']['apic']['name']
    head = '$ snmpwalk -v2c -c %s %s system' % (community, addr.split('/')[0] if addr else name)
    fail = None
    pol = e.snmp_pol
    if nid != 1 and e.nodes[nid]['state'] != 'active':
        fail = '%s ist nicht aktiv' % name
    elif not addr:
        fail = '%s hat keine Out-of-Band-Adresse (Static Node Management Address)' % name
    elif not e.ntp.get('pgrp'):
        fail = 'Das Pod Profile hat keine Pod Policy Group - es gilt keine SNMP Policy'
    elif not pol:
        fail = 'Die Pod Policy Group hat keine SNMP Policy (SNMP Policy: default?)'
    elif e.A(pol)['adminSt'] != 'enabled':
        fail = 'Die SNMP Policy %s ist deaktiviert (Admin State)' % e.short(pol)
    elif not e.has(pol + '/community-' + community):
        fail = 'Community "%s" ist in der SNMP Policy nicht konfiguriert - der Switch verwirft die Anfrage' % community
    else:
        ok = False
        grps = e.kids(pol, 'snmpClientGrpP')
        for g in grps:
            epg = (e.A(g + '/rsepg') or {}).get('tDn', '')
            if '/inb-' in epg:
                continue
            if e.has(g + '/client-' + mgr['ip']):
                ok = bool(epg)
        if not grps:
            fail = 'Die SNMP Policy hat keine Client Group Policy - ohne Client-Eintrag nimmt die ACI keine SNMP-Anfragen an'
        elif not ok:
            fail = 'Die Adresse des Managers (%s) steht in keiner Client Group mit Management EPG Out-of-Band' % mgr['ip']
    if fail:
        return {'ok': False, 'output': head + '\nTimeout: No Response from %s.' % (addr.split('/')[0] if addr else name),
                'why': fail}
    pa = e.A(pol)
    ver = ('apic-' + e.apic_version) if nid == 1 else e.node_version(e.nodes[nid]['serial'])
    lines = [head,
             'SNMPv2-MIB::sysDescr.0 = STRING: %s' % ('APIC VERSION: %s' % plain(ver) if nid == 1 else
                                                     'Cisco NX-OS(tm) aci, Software (aci-n9000-system), Version %s' % plain(ver)),
             'SNMPv2-MIB::sysObjectID.0 = OID: SNMPv2-SMI::enterprises.9.12.3.1.3.1812',
             'DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (8640000) 1 day, 0:00:00.00',
             'SNMPv2-MIB::sysContact.0 = STRING: %s' % pa['contact'],
             'SNMPv2-MIB::sysName.0 = STRING: %s' % name,
             'SNMPv2-MIB::sysLocation.0 = STRING: %s' % pa['loc']]
    if nid != 1:
        up = sorted(p for (n, p), pi in e.ports.items() if n == nid and pi['oper'] == 'up')
        for i, p in enumerate(up[:8]):
            lines.append('IF-MIB::ifDescr.%d = STRING: %s' % (436207616 + i * 4096, p))
            lines.append('IF-MIB::ifOperStatus.%d = INTEGER: up(1)' % (436207616 + i * 4096))
    return {'ok': True, 'output': '\n'.join(lines)}


# ---------------------------------------------------------------------- Trigger
def run_triggers(S, user):
    """Ausloeser nach einer Konfigurationsaenderung: Firmware-Download, Upgrade, Export, Import."""
    st = S.store
    did = False
    for dn in st.by_class('firmwareOSource'):
        dl = S.sim.setdefault('downloads', {})
        a = st.attrs(dn)
        key = dn + '|' + a['url']
        if key in dl:
            continue
        dl[key] = _download(S, a)
        S._event(dn, 'Firmware download %s: %s' % (a['name'], dl[key]['status']), sev='info' if dl[key]['ok'] else 'warning')
        did = True
    for dn in st.by_class('maintCtrlrMaintP') + st.by_class('maintMaintP'):
        a = st.attrs(dn)
        if a['adminSt'] != 'triggered':
            continue
        a['adminSt'] = 'untriggered'
        _upgrade(S, dn, a, user)
        did = True
    for dn in st.by_class('configExportP'):
        a = st.attrs(dn)
        if a['adminSt'] == 'triggered':
            a['adminSt'] = 'untriggered'
            _job(S, dn, 'export', *_export(S, dn, a))
            did = True
    for dn in st.by_class('configImportP'):
        a = st.attrs(dn)
        if a['adminSt'] == 'triggered':
            a['adminSt'] = 'untriggered'
            _job(S, dn, 'import', *_import(S, dn, a, user))
            did = True
    return did


def _job(S, dn, kind, ok, details, fname=''):
    jobs = S.sim.setdefault('jobs', [])
    jobs.append({'policy': dn, 'kind': kind, 'ts': now_ts(), 'id': time.strftime('%Y-%m-%dT%H-%M-%S') + '-%d' % len(jobs),
                 'ok': ok, 'details': details, 'file': fname})
    del jobs[:-100]
    S._event(dn, 'Configuration %s %s: %s' % (kind, 'succeeded' if ok else 'failed', details),
             sev='info' if ok else 'major', code='E4210155' if ok else 'E4210156')


def fileserver(S):
    return S.sim.setdefault('fileserver', default_fileserver())


def _reach(S, host, proto, user, pwd, epg, port=None):
    """Ist der Fileserver vom APIC aus erreichbar und nimmt er die Anmeldung an? Rueckgabe Fehlertext oder None."""
    e = S.engine
    fs = fileserver(S)
    if '/inb-' in (epg or ''):
        if not getattr(e, 'inb', {}).get(1):
            return 'Management EPG ist In-Band, der APIC hat aber keine aktive In-Band-Adresse'
    elif not e.oob.get(1):
        return 'Der APIC hat keine Out-of-Band-Adresse'
    if host != fs['ip']:
        return 'Unter %s antwortet kein Server (Connection timed out)' % (host or '(kein Host)')
    if fs.get('down'):
        return 'Der Server %s ist ausgefallen (Connection timed out)' % host
    if proto not in fs['protocols']:
        return 'Der Server spricht kein %s (Connection refused)' % proto.upper()
    want = {'scp': 22, 'sftp': 22, 'ftp': 21, 'http': 80}.get(proto)
    if port and want and int(port) != want:
        return 'Port %s: dort lauscht kein %s-Dienst (Connection refused, %s nutzt Port %d)' % (port, proto.upper(), proto.upper(), want)
    if proto != 'http' and (user != fs['user'] or pwd != fs['pwd']):
        return 'Anmeldung am Server fehlgeschlagen: Benutzer oder Passwort falsch (Permission denied)'
    return None


def _download(S, a):
    fs = fileserver(S)
    url = a['url'].strip()
    if a['proto'] == 'http':
        m = re.match(r'^https?://([^/:]+)(/.*)$', url)
    else:
        m = re.match(r'^(?:[^@]+@)?([^:/]+):(/.*)$', url)
    if not m:
        return {'ok': False, 'status': 'failed: URL ungueltig (%s: %s)' % (a['proto'], 'http://host/pfad/datei' if a['proto'] == 'http'
                                                                          else 'host:/pfad/datei')}
    err = _reach(S, m.group(1), a['proto'], a['user'], a['password'], 'oob')
    if err:
        return {'ok': False, 'status': 'failed: ' + err}
    path = m.group(2)
    f = fs['files'].get(path)
    if not f or not f.get('image'):
        return {'ok': False, 'status': 'failed: Datei %s gibt es auf dem Server nicht' % path}
    info = image_info(path.rsplit('/', 1)[-1])
    if not info:
        return {'ok': False, 'status': 'failed: %s ist kein ACI-Firmware-Image' % path}
    repo = S.sim.setdefault('fwrepo', [])
    if not any(i['name'] == info[0] for i in repo):
        repo.append({'name': info[0], 'version': info[1], 'type': info[2], 'size': f['size'], 'file': path.rsplit('/', 1)[-1],
                     'date': now_ts()})
    return {'ok': True, 'status': 'downloaded %s (%s)' % (info[0], f['size'])}


def _upgrade(S, dn, a, user):
    e = S.engine
    repo = {i['version']: i for i in S.sim.get('fwrepo', [])}
    dur = float(S.sim['settings'].get('upgradeSeconds', 60))
    log = S.sim.setdefault('fwlog', [])

    def fail(text):
        log.append({'ts': now_ts(), 'policy': dn, 'ok': False, 'text': text})
        S._event(dn, 'Upgrade failed: ' + text, sev='major', code='E4214000')

    if any(not u.get('done') for u in S.sim.get('upgrades', [])) and CLASSES[S.store.objs[dn][0]].name == 'maintCtrlrMaintP':
        return fail('Es laeuft noch ein Upgrade - erst abschliessen lassen')
    if S.store.objs[dn][0] == 'maintCtrlrMaintP':
        ver = S.store.attrs('uni/controller/ctrlrfwpol')['version']
        if not ver:
            return fail('In der Controller Firmware Policy ist keine Zielversion gesetzt')
        if ver not in repo:
            return fail('Das Image %s ist nicht im Firmware Repository - zuerst herunterladen (Admin > Firmware > Images)' % ver)
        if ver_key(ver) <= ver_key(e.apic_version):
            return fail('Zielversion %s ist nicht neuer als die laufende Version %s' % (plain(ver), e.apic_version))
        S.sim.setdefault('upgrades', []).append({'kind': 'ctrl', 'grp': 'controller', 'version': ver, 'serials': ['apic'],
                                                 'start': time.time(), 'dur': dur, 'user': user})
        log.append({'ts': now_ts(), 'policy': dn, 'ok': True, 'text': 'APIC-Upgrade auf %s gestartet' % plain(ver)})
        return
    ver = a['version']
    grps = [g for g in getattr(e, 'fw_groups', []) if g['pol'] == dn]
    if not ver:
        return fail('In der Upgrade Policy %s ist keine Zielversion gesetzt' % a['name'])
    if ver not in repo:
        return fail('Das Image %s ist nicht im Firmware Repository' % ver)
    if not grps:
        return fail('Keine Upgrade Group verwendet die Policy %s' % a['name'])
    if a.get('ignoreCompat') != 'true' and ver_key(ver) > ver_key(e.apic_version):
        return fail('Kompatibilitaetspruefung: Die Switches sollen %s bekommen, der APIC laeuft noch mit %s. '
                    'Zuerst den APIC aktualisieren (Controller first)' % (plain(ver), e.apic_version))
    for g in grps:
        nodes = [n for n in g['nodes'] if e.nodes.get(n, {}).get('state') == 'active']
        if not nodes:
            fail('Upgrade Group %s enthaelt keine aktiven Nodes' % g['name'])
            continue
        todo = [e.nodes[n]['serial'] for n in nodes if e.node_version(e.nodes[n]['serial']) != ver]
        if not todo:
            log.append({'ts': now_ts(), 'policy': dn, 'ok': True, 'text': 'Upgrade Group %s laeuft bereits mit %s' % (g['name'], plain(ver))})
            continue
        S.sim.setdefault('upgrades', []).append({'kind': 'switch', 'grp': g['name'], 'version': ver, 'serials': todo,
                                                 'start': time.time(), 'dur': dur, 'user': user, 'warn': g['warn']})
        log.append({'ts': now_ts(), 'policy': dn, 'ok': True, 'text': 'Upgrade Group %s (Nodes %s) auf %s gestartet%s' % (
            g['name'], ', '.join(map(str, nodes)), plain(ver), (' - Warnung: ' + '; '.join(g['warn'])) if g['warn'] else '')})
    del log[:-100]


def _remote(S, pol_dn):
    rs = S.store.attrs(pol_dn + '/rsRemotePath') or {}
    t = rs.get('tDn')
    if not t or t not in S.store.objs:
        return None, 'Keine Remote Location gewaehlt (oder sie existiert nicht)'
    a = S.store.attrs(t)
    epg = (S.store.attrs(t + '/rsARemoteHostToEpg') or {}).get('tDn') or ''
    if not epg:
        return None, 'Die Remote Location %s hat kein Management EPG' % a['name']
    err = _reach(S, a['host'], a['protocol'], a['userName'], a['userPasswd'], epg, a['remotePort'])
    if err:
        return None, err
    fs = fileserver(S)
    path = (a['remotePath'] or '/').rstrip('/') or '/'
    if path not in fs['dirs'] and path != '/':
        return None, 'Das Verzeichnis %s gibt es auf dem Server nicht (vorhanden: %s)' % (path, ', '.join(fs['dirs']))
    return path, None


def _export(S, dn, a):
    st = S.store
    tgt = a['targetDn'].strip()
    if tgt and tgt not in st.objs:
        return False, 'Target DN %s existiert nicht' % tgt
    ck = st.attrs('uni/exportcryptkey')
    crypt = ck['strongEncryptionEnabled'] == 'yes' and bool(ck['passphrase'])
    secure = crypt and a['includeSecureFields'] == 'yes'
    rows = []
    for d, cls, at in st.dump_config():
        if tgt and d != tgt and not d.startswith(tgt + '/'):
            continue
        if not secure:
            at = {k: ('' if k in SECURE else v) for k, v in at.items()}
        rows.append([d, cls, at])
    stamp = time.strftime('%Y-%m-%dT%H-%M-%S')
    fname = 'ce2_%s-%s.tar.gz' % (a['name'], stamp)
    blob = {'kind': 'aci-config-export', 'created': now_ts(), 'target': tgt, 'secure': secure, 'key': keyhash(ck['passphrase']) if secure else '',
            'policy': a['name'], 'rows': rows, 'version': S.engine.apic_version, 'counters': dict(st.counters)}
    note = '' if secure else (' - ohne Secure Properties (Passwoerter, Keys): Global AES Encryption ist nicht aktiv' if not crypt
                              else ' - ohne Secure Properties (Include Secure Fields: no)')
    if a['snapshot'] == 'true':
        name = fname.replace('.tar.gz', '')[:60]
        snaps = S.sim.setdefault('ce_snaps', {})
        snaps[name] = blob
        S.snapshot('create', re.sub(r'[^A-Za-z0-9_.-]', '-', name)[:60], 'Snapshot der Export Policy %s%s' % (a['name'], ' (' + tgt + ')' if tgt else ''))
        return True, 'Snapshot %s erstellt (%d Objekte)%s' % (name, len(rows), note), name
    path, err = _remote(S, dn)
    if err:
        return False, err
    fs = fileserver(S)
    fs['files'][path.rstrip('/') + '/' + fname] = {'size': '%d KB' % max(1, len(json.dumps(rows)) // 1024), 'export': blob}
    exports = [k for k, v in fs['files'].items() if v.get('export')]
    for k in exports[:-12]:
        del fs['files'][k]
    return True, 'Export nach %s:%s/%s (%d Objekte)%s' % (fs['ip'], path.rstrip('/'), fname, len(rows), note), fname


def _import(S, dn, a, user):
    st = S.store
    path, err = _remote(S, dn)
    if err:
        return False, err
    fs = fileserver(S)
    fn = a['fileName'].strip()
    f = fs['files'].get(path.rstrip('/') + '/' + fn) if fn else None
    if not f or not f.get('export'):
        have = [k.rsplit('/', 1)[-1] for k, v in fs['files'].items() if v.get('export') and k.startswith(path.rstrip('/') + '/')]
        return False, 'Datei %s gibt es in %s nicht%s' % (fn or '(kein Name)', path, (' (vorhanden: %s)' % ', '.join(have)) if have else '')
    blob = f['export']
    ck = st.attrs('uni/exportcryptkey')
    cur = keyhash(ck['passphrase']) if ck['strongEncryptionEnabled'] == 'yes' else ''
    secure = blob['secure']
    warn = []
    if secure and blob['key'] != cur:
        if a['importMode'] == 'atomic':
            return False, ('Die Datei enthaelt verschluesselte Secure Properties, die AES-Passphrase stimmt aber nicht '
                           '(oder Global AES Encryption ist aus). Atomic Import abgebrochen')
        secure = False
        warn.append('Secure Properties uebersprungen (Passphrase passt nicht)')
    if a['snapshot'] == 'true':
        S.snapshot('create', ('pre-import-' + time.strftime('%Y%m%d-%H%M%S')), 'Snapshot vor Import %s' % fn)
    rows = [r for r in blob['rows'] if r[1] in CLASSES]
    bad = len(blob['rows']) - len(rows)
    if bad and a['importMode'] == 'atomic':
        return False, '%d Objekte haben unbekannte Klassen - Atomic Import abgebrochen' % bad
    tgt = blob['target']
    old = {d: dict(o[1]) for d, o in st.objs.items() if not o[2]}

    def keep_secret(d, at, cls=None):
        at = dict(at)
        if cls and d not in old:
            _alloc(st, CLASSES[cls], at)
        if not secure:
            for k in SECURE:
                if k in at:
                    at[k] = (old.get(d) or {}).get(k, '')
        return at

    if a['importType'] == 'replace':
        if tgt:
            if tgt in st.objs:
                st.delete(tgt)
        else:
            from .topology import ensure_base
            kept = [[d, o[0], o[1]] for d, o in st.objs.items() if not o[2] and CLASSES[o[0]].fixed]
            st.load_config(kept)
            for k, v in (blob.get('counters') or {}).items():
                st.counters[k] = max(st.counters.get(k, 0), v)
        for d, cls, at in sorted(rows, key=lambda r: len(split_dn(r[0]))):
            if parent_dn(d) in st.objs or d == 'uni':
                st.add(d, cls, keep_secret(d, at, cls if tgt else None))
            else:
                bad += 1
        if not tgt:
            from .topology import ensure_base
            ensure_base(st)
        if 'uni/userext/user-admin' not in st.objs:
            st.add('uni/userext/user-admin', 'aaaUser', old.get('uni/userext/user-admin', {'name': 'admin', 'pwd': S.admin_pwd}))
    else:
        for d, cls, at in sorted(rows, key=lambda r: len(split_dn(r[0]))):
            if d in st.objs:
                if st.objs[d][0] != cls:
                    bad += 1
                    continue
                for k, v in at.items():
                    if k in SECURE and not secure:
                        continue
                    st.objs[d][1][k] = v
            elif parent_dn(d) in st.objs:
                st.add(d, cls, keep_secret(d, at, cls))
            else:
                bad += 1
    S.audit(user, [{'dn': tgt or 'uni', 'cls': 'polUni' if not tgt else st.objs.get(tgt, ['fvTenant'])[0], 'ind': 'modification',
                    'changes': {'import': ('', '%s %s aus %s' % (a['importType'], a['importMode'], fn))}}])
    if bad:
        warn.append('%d Objekte uebersprungen' % bad)
    if not blob['secure']:
        warn.append('Die Datei enthaelt keine Secure Properties - bestehende Passwoerter bleiben, neue Objekte haben keine')
    return True, '%s-Import (%s) aus %s: %d Objekte%s' % (a['importType'].capitalize(), a['importMode'], fn, len(rows),
                                                          (' - ' + '; '.join(warn)) if warn else ''), fn
