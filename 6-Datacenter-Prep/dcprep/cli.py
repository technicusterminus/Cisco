"""CLI-Emulation: APIC (moquery, acidiag) und Leaf/Spine (show-Befehle)."""
import ipaddress
import re
import shlex

from .model import CLASSES, split_dn
from .engine import ip_of, net_of, pnum, vlan_num
from .query import parse_filter, eval_filter, out_attrs

APIC_HELP = """Verfuegbare Befehle auf dem APIC:
  acidiag fnvread                     Fabric-Knoten und ihr Zustand
  moquery -c <Klasse> [-f '<filter>'] Objekte einer Klasse, z. B. moquery -c fvBD
  moquery -d <dn>                     ein Objekt, z. B. moquery -d uni/tn-common
  show switch | show controller       Knotenuebersicht
  show tenant                         Tenants
  show version
  show fabric membership              registrierte Switches
  acidiag avread                      Zustand des APIC-Clusters
  cat /data/data_admin/sam_exported.config   Werte aus dem Setup-Dialog
  acidiag touch clean | acidiag reboot       Konfiguration loeschen und neu starten (Werkszustand)
  show faults [detail]                aktive Faults der Fabric
  show endpoints [ip <a.b.c.d>]       Endpoints der ganzen Fabric
  show bridge-domain | show epg       BDs und EPGs mit Zustand
  show vmware domain name <Domain>    VMM Domain mit vCenter, Port Groups, Hosts
  ssh <leaf>                          zur Leaf-/Spine-CLI wechseln (z. B. ssh leaf101)
  Filter-Beispiel: moquery -c fvAEPg -f 'fv.AEPg.name=="Web"'"""

LEAF_HELP = """Verfuegbare Befehle auf Leaf/Spine:
  show version
  show lldp neighbors
  show interface status
  show vlan extended
  show endpoint [vrf <Tenant:VRF>] [ip <a.b.c.d>]
  show vrf
  show ip route vrf <Tenant:VRF>
  show zoning-rule [scope <VNID>]
  show ip ospf neighbors vrf <Tenant:VRF>
  show bgp ipv4 unicast summary vrf <Tenant:VRF>
  show vpc brief
  show port-channel summary
  show ntp peer-status | show clock
  show interface eth1/<n>             Details eines Ports (Status, Grund, VLANs, Policy Group)
  show cdp neighbors
  show mac address-table [vlan <id>]
  show ip interface brief vrf <Tenant:VRF | overlay-1>
  show ip arp vrf <Tenant:VRF>
  show system internal epm endpoint ip <a.b.c.d> | mac <mac>
  show zoning-filter [filter <id>]
  contract_parser.py [--vrf <Tenant:VRF>]
  show bgp ipv4 unicast vrf <Tenant:VRF>
  show ip ospf interface brief vrf <Tenant:VRF>
  show service redir info                  PBR Destination Groups
  iping -V <Tenant:VRF> <a.b.c.d>          Ping vom Leaf (Quelle: BD-Gateway)
  Underlay: show ip route vrf overlay-1 | show isis adjacency vrf overlay-1
            show bgp vpnv4 unicast summary vrf overlay-1 | show coop internal info ip-db (Spine)
  exit                                zurueck zum APIC"""


def _pkg(cls):
    m = re.match(r'^([a-z0-9]+)([A-Z].*)$', cls)
    return '%s.%s' % (m.group(1), m.group(2)) if m else cls


def _cls_from_pkg(s):
    return s.replace('.', '')


def _table(headers, rows):
    w = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            w[i] = max(w[i], len(str(c)))
    line = '+' + '+'.join('-' * (x + 2) for x in w) + '+'
    out = [line, '|' + '|'.join(' %s ' % h.center(w[i]) for i, h in enumerate(headers)) + '|', line]
    for r in rows:
        out.append('|' + '|'.join(' %s ' % str(c).center(w[i]) for i, c in enumerate(r)) + '|')
    out.append(line)
    return '\n'.join(out)


def _mac(m):
    h = m.replace(':', '').lower()
    return '%s.%s.%s' % (h[0:4], h[4:8], h[8:12])


class Cli:
    def __init__(self, eng, sim):
        self.e = eng
        self.sim = sim
        self.request = None

    def run(self, node, cmd):
        cmd = cmd.strip()
        if not cmd:
            return ''
        if node in ('apic1', 'apic', '1', ''):
            return self.apic(cmd)
        n = self._node(node)
        if n is None:
            return '%% Knoten %s ist nicht erreichbar (nicht registriert/aktiv)' % node
        return self.switch(n, cmd)

    def _node(self, name):
        for nid, n in self.e.nodes.items():
            if (n['name'] == name or str(nid) == str(name)) and n['state'] == 'active':
                return n
        return None

    # ------------------------------------------------------------------ APIC
    def apic(self, cmd):
        e = self.e
        if cmd in ('help', '?'):
            return APIC_HELP
        if cmd == 'acidiag fnvread':
            rows = []
            for nid in sorted(e.nodes):
                n = e.nodes[nid]
                rows.append('%8d %8d %18s %15s %20s/%-5s %8s %10s %s' % (
                    nid, e.pod, n['name'], n['serial'], n['tep'] if n['state'] == 'active' else '0.0.0.0', '32',
                    n['role'], '0', n['state']))
            return ('      ID   Pod ID                 Name    Serial Number         IP Address    Role        '
                    'State   LastUpdMsgId\n' + '-' * 100 + '\n' + '\n'.join(rows) +
                    '\n\nTotal %d nodes' % len(rows))
        if cmd.startswith('moquery'):
            return self.moquery(cmd)
        su = e.setup or {}
        oob = str(ip_of(e.oob[1])) if e.oob.get(1) else '0.0.0.0'
        if cmd == 'show controller':
            return ('Fabric Name            : %s\n'
                    'Operational Size       : 1\n'
                    'Cluster Size           : %s\n'
                    'Time Difference        : 0\n'
                    'Fabric Security Mode   : PERMISSIVE\n\n'
                    ' ID   Pod  Address          In-Band IPv4  OOB IPv4         Version  Flags  Serial Number  Health\n'
                    ' ---- ---- ---------------- ------------- ---------------- -------- ------ -------------- ----------\n'
                    ' 1*   %-4s %-16s 0.0.0.0       %-16s 6.0(5h)  crva   %-14s %s'
                    % (e.fabric_name, su.get('ctrlCount', '1'), e.pod, e.apic_tep, oob, self.sim['topology']['apic']['serial'],
                       'fully-fit' if su.get('ctrlCount', '1') == '1' else 'not-fully-fit'))
        if cmd in ('show switch', 'show fabric membership'):
            out = [' ID    Pod  Address          In-Band IPv4  OOB IPv4         Version          Flags  Serial Number  Name',
                   ' ----- ---- ---------------- ------------- ---------------- ---------------- ------ -------------- ----------']
            for nid in sorted(e.nodes):
                n = e.nodes[nid]
                if cmd == 'show switch' and n['state'] != 'active':
                    continue
                out.append(' %-5d %-4d %-16s %-13s %-16s %-16s %-6s %-14s %s' % (
                    nid, e.pod, n['tep'] if n['state'] == 'active' else '0.0.0.0', '0.0.0.0',
                    str(ip_of(e.oob[nid])) if e.oob.get(nid) else '0.0.0.0',
                    'n9000-16.0(5h)' if n['state'] == 'active' else '', 'aliv' if n['state'] == 'active' else '-',
                    n['serial'], n['name']))
            if cmd == 'show fabric membership':
                out.append('')
                out.append(' Nodes pending registration: %d' % len(e.pending))
                for p_ in e.pending:
                    out.append('   %s  %s  %s' % (p_['serial'], p_['role'], p_['model']))
            return '\n'.join(out)
        if cmd == 'acidiag avread':
            return ('Local appliance ID=1 ADDRESS=%s TEP ADDRESS=%s CHASSIS_ID=%s\n'
                    'Cluster of %s lm(t):1(zeroTime) appliance vector(s):\n'
                    '  appliance id=1 address=%s lm(t):1 tep address=%s oob address=%s/%s version=6.0(5h) '
                    'chassisId=%s capabilities=0X7EEFFFFFFFFF--0X2020--0X7F cntrlSbst=(APPROVED, %s) commissioned=YES '
                    'registered=YES standby=NO DRR=NO apicX=NO virtual=NO active=YES(zeroTime) health=(applnc:255 '
                    'svc\'s)\n  ---------------------------------------------\n  clusterTime=<diff=0 common=zeroTime local=zeroTime '
                    'pF=<displForm=0 offsSt=0 offsVlu=0 lm(t):1(zeroTime)>>\n  ---------------------------------------------'
                    % (e.apic_tep, self.e.tep_pool, self.sim['topology']['apic']['serial'], su.get('ctrlCount', '1'),
                       e.apic_tep, self.e.tep_pool, oob, (su.get('oobIp') or '/24').split('/')[-1],
                       self.sim['topology']['apic']['serial'], self.sim['topology']['apic']['serial']))
        if cmd in ('cat /data/data_admin/sam_exported.config', 'cat /data/data_admin/sam_exported.config | grep -v pwd'):
            return '\n'.join([
                'Setup for Active and Standby APIC', 'fabricDomain = %s' % e.fabric_name, 'fabricID = %s' % su.get('fabricId'),
                'systemName =%s' % self.sim['topology']['apic']['name'], 'controllerID = %s' % su.get('ctrlId'),
                'tepPool = %s' % su.get('tepPool'), 'infraVlan = %s' % su.get('infraVlan'),
                'GIPo = %s' % su.get('gipo'), 'clusterSize = %s' % su.get('ctrlCount'), 'standbyApic = %s' % su.get('standby'),
                'enableIPv4 = Y', 'enableIPv6 = N', 'firmwareVersion = 6.0(5h)', 'ifcIpAddr = %s' % e.apic_tep,
                'apicX = NO', 'podId = %s' % su.get('podId'),
                'oobIpAddr = %s' % su.get('oobIp'), 'oobGateway = %s' % su.get('oobGw'), 'oobSpeed = %s' % su.get('speed')])
        if cmd == 'acidiag touch clean':
            self.sim['touch_clean'] = True
            return ('This command will wipe out this device. Proceed? [y/N] y\n'
                    'Done. Die Konfiguration wird beim naechsten "acidiag reboot" geloescht.')
        if cmd in ('acidiag reboot', 'reboot'):
            if self.sim.get('touch_clean'):
                self.request = 'factory'
                return ('This command will restart this device, Proceed? [y/N] y\n'
                        'Rebooting ... Die Konfiguration ist geloescht. Der APIC startet mit dem Setup-Dialog.')
            return ('This command will restart this device, Proceed? [y/N] y\n'
                    'Rebooting ... Der APIC ist wieder da (Konfiguration unveraendert).')
        r = self.apic_extra(cmd)
        if r is not None:
            return r
        if cmd == 'show tenant':
            rows = [e.A(d)['name'] for d in e.store.by_class('fvTenant')]
            return ' Tenant\n ' + '-' * 30 + '\n' + '\n'.join(' ' + r for r in sorted(rows))
        if cmd == 'show version':
            return ' Role        Pod  Node  Name      Version\n ----------  ---  ----  --------  --------\n' \
                   ' controller  1    1     apic1     6.0(5h) (Datacenter Prep)'
        return '%% Unbekannter Befehl. "help" zeigt die verfuegbaren Befehle.'

    def moquery(self, cmd):
        try:
            args = shlex.split(cmd)[1:]
        except ValueError as ex:
            return 'Error: %s' % ex
        cls = dn = flt = None
        i = 0
        while i < len(args):
            if args[i] == '-c' and i + 1 < len(args):
                cls = _cls_from_pkg(args[i + 1]); i += 2
            elif args[i] == '-d' and i + 1 < len(args):
                dn = args[i + 1]; i += 2
            elif args[i] == '-f' and i + 1 < len(args):
                flt = args[i + 1]; i += 2
            else:
                i += 1
        st = self.e.store
        if dn:
            dns = [dn] if dn in st.objs else []
        elif cls:
            if cls not in CLASSES:
                return 'Error: unknown class %s' % cls
            dns = sorted(st.by_class(cls))
        else:
            return 'usage: moquery -c <class> [-f <filter>] | -d <dn>'
        if flt:
            m = re.match(r'^\s*([\w.]+)\s*(==|!=|=~)\s*"(.*)"\s*$', flt)
            if not m:
                return 'Error: filter format: <pkg.Class.attr>=="value"'
            path, op, val = m.groups()
            parts = path.split('.')
            attr = parts[-1]
            f = {'==': 'eq', '!=': 'ne', '=~': 'wcard'}[op]
            tree = (f, [('prop', attr), ('str', val)])
            dns = [d for d in dns if eval_filter(tree, st.objs[d][0], st.objs[d][1])]
        out = ['Total Objects shown: %d' % len(dns), '']
        for d in dns:
            c = st.objs[d][0]
            a = out_attrs(st, d)
            out.append('# ' + _pkg(c))
            w = max(len(k) for k in a)
            for k in sorted(a, key=lambda k: (k not in CLASSES[c].naming, k)):
                out.append('%s : %s' % (k.ljust(w), a[k]))
            out.append('')
        return '\n'.join(out)

    # ------------------------------------------------------------------ Switch
    def _vrf_by_name(self, name):
        if not name:
            return None
        if ':' in name:
            tn, v = name.split(':', 1)
            dn = 'uni/tn-%s/ctx-%s' % (tn, v)
            return dn if dn in self.e.store.objs else None
        return None

    def _vname(self, dn):
        p = split_dn(dn)
        return '%s:%s' % (p[1][3:], p[2][4:])

    def _pivlans(self, nid):
        e = self.e
        res = []
        vid = 12
        bds = sorted(e.dep_bd.get(nid, set()))
        for bd in bds:
            vid += 1
            ports = sorted({l[1] for d in e.deploys if d['bd'] == bd and nid in d['nodes'] for l in d['legs']
                            if l[0] == nid}, key=pnum)
            res.append((vid, '%s:%s' % (split_dn(bd)[1][3:], split_dn(bd)[2][3:]),
                        'vxlan-%s' % e.A(bd)['seg'], ports, bd, None))
            for d in sorted([d for d in e.deploys if d['bd'] == bd and nid in d['nodes']], key=lambda x: x['vlan']):
                vid += 1
                p = split_dn(d['epg'])
                ports = sorted({l[1] for l in d['legs'] if l[0] == nid}, key=pnum)
                c = e.cls.get(d['epg'], {})
                name = c.get('vname') or ('%s:%s:%s' % (p[1][3:], p[2].split('-', 1)[-1], p[3].split('-', 1)[-1]))
                res.append((vid, name, 'vlan-%d' % d['vlan'], ports, bd, d))
        return res

    def _po_ids(self, nid):
        e = self.e
        ids = {}
        n = 0
        for dn, p in sorted(e.paths.items()):
            if p['type'] in ('pc', 'vpc') and nid in p['nodes'] and any(l[0] == nid for l in p['legs']):
                n += 1
                ids[dn] = n
        return ids

    def switch(self, n, cmd):
        e = self.e
        nid = n['id']
        c = re.sub(r'\s+', ' ', cmd.strip())
        words = c.split(' ')
        if c in ('help', '?'):
            return LEAF_HELP
        if c == 'show version':
            return ('Cisco Nexus Operating System (NX-OS) Software (Datacenter Prep)\n'
                    ' NXOS: version 16.0(5h)\n hardware: cisco %s\n %s Serial Number: %s\n Device name: %s\n'
                    % (n['model'], n['role'], n['serial'], n['name']))
        if c in ('show lldp neighbors', 'show lldp neighbor'):
            out = ['Capability codes:', '  (R) Router, (B) Bridge, (T) Telephone, (C) DOCSIS Cable Device',
                   '  (W) WLAN Access Point, (P) Repeater, (S) Station, (O) Other',
                   'Device ID            Local Intf      Hold-time  Capability  Port ID']
            rows = list(e.lldp.get(nid, []))
            for (k, port), peer in e.cabled.items():
                if k == nid:
                    pg = e.ports[(k, port)]['pg']
                    if pg and not e._pg_info(pg)['lldp']:
                        continue
                    rows.append((port, peer[1], 'eth0' if peer[0] == 'host' else 'Gi0/0',
                                 'S' if peer[0] == 'host' else 'R', None))
            for lp, dev, rp, cap, _ in sorted(rows, key=lambda r: pnum(r[0]) or 0):
                out.append('%-20s %-15s %-10s %-11s %s' % (dev[:20], lp.capitalize(), '120', cap, rp))
            out.append('Total entries displayed: %d' % len(rows))
            return '\n'.join(out)
        if c in ('show interface status', 'show int status', 'show interface brief'):
            out = ['-' * 80, '%-12s %-18s %-10s %-9s %-7s %-7s %s' % ('Port', 'Name', 'Status', 'Vlan', 'Duplex',
                                                                       'Speed', 'Type'), '-' * 80]
            for (k, port), pi in sorted(e.ports.items(), key=lambda x: (pnum(x[0][1]) or 0)):
                if k != nid:
                    continue
                status = {'up': 'connected', 'down': 'notconnect'}[pi['oper']]
                if pi['qual'] == 'suspended':
                    status = 'suspnd'
                elif pi['qual'].startswith('suspended'):
                    status = 'suspnd'
                vl = 'routed' if pi['layer'] == 'Layer3' else ('trunk' if pi['vlans'] else '--')
                out.append('%-12s %-18s %-10s %-9s %-7s %-7s %s' % (
                    port.capitalize(), '--', status, vl, 'full', pi['speed'] if pi['oper'] == 'up' else 'auto',
                    '25Gbase-SR' if (pnum(port) or 0) <= 48 else '100Gbase-SR4'))
            return '\n'.join(out)
        if c == 'show vlan extended':
            out = [' VLAN Name                             Encap            Ports',
                   ' ---- -------------------------------- ---------------- ------------------------']
            ctl = sorted([p_ for (k, p_), pi in e.ports.items() if k == nid and (pi.get('peer') or ('',))[0] == 'controller'],
                         key=pnum)
            if ctl:
                out.append(' %-4d %-32s %-16s %s' % (8, 'infra:default', 'vxlan-16777209, vlan-%d' % e.infra_vlan,
                                                     ', '.join(p_.capitalize() for p_ in ctl)))
            for vid, name, encap, ports, _, _ in self._pivlans(nid):
                out.append(' %-4d %-32s %-16s %s' % (vid, name[:32], encap, ', '.join(p.capitalize() for p in ports)))
            return '\n'.join(out)
        if words[:2] == ['show', 'endpoint']:
            return self.endpoints(nid, words[2:])
        if c == 'show vrf':
            out = [' VRF-Name                           VRF-ID State   Reason',
                   ' black-hole                              3 Up      --',
                   ' overlay-1                               4 Up      --']
            for i, v in enumerate(sorted(e.dep_vrf.get(nid, set()))):
                out.append(' %-34s %6d Up      --' % (self._vname(v), 5 + i))
            return '\n'.join(out)
        m = re.match(r'^show ip route vrf (\S+)$', c)
        if m and m.group(1) != 'overlay-1':
            return self.route(nid, m.group(1))
        m = re.match(r'^show zoning-rule(?: scope (\d+))?$', c)
        if m:
            return self.zoning(nid, m.group(1))
        m = re.match(r'^show ip ospf neighbors? vrf (\S+)$', c)
        if m:
            return self.ospf(nid, m.group(1))
        m = re.match(r'^show bgp ipv4 unicast summary vrf (\S+)$', c)
        if m:
            return self.bgp(nid, m.group(1))
        if c in ('show ntp peer-status', 'show ntp peers'):
            why = e.ntp['nodes'].get(nid)
            provs = e.ntp['provs']
            out = ['Total peers : %d' % len(provs), '* - selected for sync, + -  peer mode(active),',
                   '- - peer mode(passive), = - polled in client mode', '    remote                                 local'
                   '                 st   poll   reach delay   vrf', '-' * 100]
            oob = str(ip_of(e.oob[nid])) if e.oob.get(nid) else '0.0.0.0'
            for p in provs:
                out.append('%s%-38s %-21s %-4s %-6s %-7s %-7s management' % (
                    '=' if why else '*', p, oob, '16' if why else '2', '64', '0' if why else '377', '0.000'))
            return '\n'.join(out)
        if c == 'show clock':
            import time as _t
            return _t.strftime('%H:%M:%S.000 UTC %a %b %d %Y', _t.gmtime()) + '\nTime source is %s' % (
                'NTP' if not e.ntp['nodes'].get(nid) else 'Hardware Calendar')
        if c in ('show vpc', 'show vpc brief'):
            return self.vpc(nid)
        if c in ('show port-channel summary', 'show port-channel sum'):
            return self.pc(nid)
        extra = dispatch_extra(self, nid, c)
        if extra is not None:
            return extra
        if c.startswith('show ip route') or c.startswith('show ip ospf') or c.startswith('show bgp'):
            return '% Bitte VRF angeben, z. B. "show ip route vrf Tenant:VRF"'
        return '% Invalid command. "help" zeigt die verfuegbaren Befehle.'

    def endpoints(self, nid, args):
        e = self.e
        vrf_f = ip_f = None
        if 'vrf' in args and args.index('vrf') + 1 < len(args):
            vrf_f = self._vrf_by_name(args[args.index('vrf') + 1])
        if 'ip' in args and args.index('ip') + 1 < len(args):
            ip_f = args[args.index('ip') + 1]
        out = ['Legend:',
               ' S - static           s - arp              L - local            O - peer-attached',
               ' V - vpc-attached     a - local-aged       p - peer-aged        M - span',
               ' B - bounce           H - vtep             R - peer-attached-rl D - bounce-to-proxy',
               ' E - shared-service   m - svc-mgr',
               '+-----------------------------------+---------------+-----------------+--------------+-------------+',
               '      VLAN/                           Encap           MAC Address       MAC Info/       Interface',
               '      Domain                          VLAN            IP Address        IP Info',
               '+-----------------------------------+---------------+-----------------+--------------+-------------+']
        piv = {(d['epg'], d['vlan']): vid for vid, _, _, _, _, d in self._pivlans(nid) if d}
        po = self._po_ids(nid)
        for h in e.all_hosts():
            hs = e.hosts.get(h['name'])
            if not hs or not hs['learned'] or nid not in hs['nodes']:
                continue
            if vrf_f and hs['vrf'] != vrf_f:
                continue
            if ip_f and str(ip_of(h['ip'])) != ip_f:
                continue
            p = e.paths[hs['path']]
            if p['type'] == 'port':
                intf = p['name']
            else:
                intf = 'po%d' % po.get(hs['path'], 1)
            flag = 'L' + (' V' if p['type'] == 'vpc' else '')
            vid = piv.get((hs['epg'], vlan_num(hs['encap'])), '?')
            out.append('%-36s %15s %17s %-14s %13s' % (vid, hs['encap'], _mac(h['mac']), flag, intf))
            if hs['ipLearned']:
                out.append('%-36s %15s %17s %-14s %13s' % (self._vname(hs['vrf']), hs['encap'], str(ip_of(h['ip'])),
                                                          flag, intf))
        return '\n'.join(out)

    def route(self, nid, vname):
        e = self.e
        vrf = self._vrf_by_name(vname)
        if not vrf or vrf not in e.dep_vrf.get(nid, set()):
            return '%% VRF %s ist auf diesem Switch nicht deployed' % vname
        out = ['IP Route Table for VRF "%s"' % vname, "'*' denotes best ucast next-hop",
               "'**' denotes best mcast next-hop", "'[x/y]' denotes [preference/metric]",
               "'%<string>' in via output denotes VRF <string>", '']
        entries = []
        for bd in e.dep_bd.get(nid, set()):
            if (e.A(bd + '/rsctx') or {}).get('tDn') != vrf or e.A(bd)['unicastRoute'] != 'yes':
                continue
            for s in e.bd_subnets(bd):
                entries.append((s['net'], ['%s, ubest/mbest: 1/0, attached, direct, pervasive' % s['net'],
                                           '    *via 10.0.0.66%overlay-1, [1/0], 01:02:03, static, tag 4294967294']))
                entries.append((ipaddress.ip_network(s['gw'] + '/32'),
                                ['%s/32, ubest/mbest: 1/0, attached, pervasive' % s['gw'],
                                 '    *via %s, vlan%s, [0/0], 01:02:03, local, local' % (s['gw'], 13)]))
        for rt in e.routes.get((vrf, nid), []):
            n = ipaddress.ip_network(rt['prefix'], strict=False)
            if rt['proto'] == 'direct':
                entries.append((n, ['%s, ubest/mbest: 1/0, attached, direct' % n,
                                    '    *via %s, %s, [0/0], 01:02:03, direct' % (rt['nh'], rt['via'])]))
                entries.append((ipaddress.ip_network(rt['nh'] + '/32'),
                                ['%s/32, ubest/mbest: 1/0, attached' % rt['nh'],
                                 '    *via %s, %s, [0/0], 01:02:03, local, local' % (rt['nh'], rt['via'])]))
            elif rt['proto'] == 'bgp' and rt.get('border'):
                entries.append((n, ['%s, ubest/mbest: 1/0' % n,
                                    '    *via %s%%overlay-1, [200/0], 00:05:11, bgp-65001, internal, tag 65001'
                                    % rt['nh']]))
            else:
                tag = {'static': 'static', 'ospf': 'ospf-default, intra', 'bgp': 'bgp-%s, external, tag %s' % (
                    e.fabric_asn() or '0', next((r.get('bgp', {}).get('asn') for r in self.sim.get('routers', [])
                                                 if r['name'] == rt.get('router')), ''))}[rt['proto']]
                entries.append((n, ['%s, ubest/mbest: 1/0' % n,
                                    '    *via %s, %s, [%d/0], 00:05:11, %s' % (rt['nh'], rt['via'], rt['pref'], tag)]))
        for net, svrf, obj in e.leaked_routes().get(vrf, []):
            entries.append((net, ['%s, ubest/mbest: 1/0, attached, direct, pervasive' % net,
                                  '    *via 10.0.0.66%%overlay-1, [1/0], 00:02:11, static, tag 4294967294, rwVnid: vxlan-%s'
                                  % e.A(svrf)['scope'],
                                  '         recursive next hop: 10.0.0.66/32%%overlay-1 (geleakt aus VRF %s, %s)'
                                  % (self._vname(svrf), e.short(obj))]))
        for _, lines in sorted(entries, key=lambda x: (int(x[0].network_address), x[0].prefixlen)):
            out.extend(lines)
        return '\n'.join(out)

    def zoning(self, nid, scope):
        e = self.e
        rows = []
        fid = self._filters()
        rid = 4096
        for vrf in sorted(e.dep_vrf.get(nid, set())):
            va = e.A(vrf)
            vn = va['scope']
            if scope and scope != vn:
                continue
            enforced = va['pcEnfPref'] == 'enforced'
            rows.append((rid, 0, 0, 'implicit', 'uni-dir', 'enabled', vn, '',
                         'deny,log' if enforced else 'permit', 'any_any_any(21)')); rid += 1
            rows.append((rid, 0, 0, 'implarp', 'uni-dir', 'enabled', vn, '', 'permit', 'any_any_filter(17)')); rid += 1
            rows.append((rid, 0, 15, 'implicit', 'uni-dir', 'enabled', vn, '', 'deny,log', 'any_vrf_any_deny(22)')); rid += 1
            for brc, rel in sorted(e.contracts.items()):
                members = lambda k: [e.cls[d]['pcTag'] for d in rel[k] if d in e.cls and e.cls[d]['vrf'] == vrf] + \
                    (['0'] if vrf in rel[k + '_any'] else [])
                cons, prov = members('cons'), members('prov')
                if prov and e.A(brc)['scope'] in ('tenant', 'global'):
                    # Shared Services: Regeln liegen im VRF des Providers
                    cons += [e.cls[d]['pcTag'] for d in rel['cons'] if d in e.cls and e.cls[d]['vrf'] and e.cls[d]['vrf'] != vrf]
                if not cons or not prov:
                    continue
                for subj in e.kids(brc, 'vzSubj'):
                    g = getattr(e, 'graphs', {}).get(subj)
                    g = g if g and g['state'] == 'applied' and g['redirect'] else None
                    for rf in e.kids(subj, 'vzRsSubjFiltAtt'):
                        rfa = e.A(rf)
                        if rfa['state'] != 'formed':
                            continue
                        f = fid[rfa['tDn']]
                        a1 = a2 = rfa['action']
                        if g:
                            a1 = 'redir(destgrp-%d)' % self._destgrp(g, 'consumer')
                            a2 = 'redir(destgrp-%d)' % self._destgrp(g, 'provider')
                        for cpt in cons:
                            for ppt in prov:
                                if cpt == ppt:
                                    continue
                                pr = 'fully_qual(7)' if cpt != '0' and ppt != '0' else 'any_dest_filter(14)'
                                rows.append((rid, cpt, ppt, f, 'bi-dir', 'enabled', vn, e.A(brc)['name'],
                                             a1, pr)); rid += 1
                                rows.append((rid, ppt, cpt, f, 'uni-dir-ignore', 'enabled', vn, e.A(brc)['name'],
                                             a2, pr)); rid += 1
                                if g:
                                    sc_, sp_ = g['conns']['consumer']['pcTag'], g['conns']['provider']['pcTag']
                                    rows.append((rid, sp_, ppt, f, 'bi-dir', 'enabled', vn, e.A(brc)['name'], 'permit', pr)); rid += 1
                                    rows.append((rid, sc_, cpt, f, 'uni-dir-ignore', 'enabled', vn, e.A(brc)['name'], 'permit', pr)); rid += 1
        if not rows:
            return 'Keine Zoning-Rules (kein VRF auf diesem Switch deployed).'
        return _table(['Rule ID', 'SrcEPG', 'DstEPG', 'FilterID', 'Dir', 'operSt', 'Scope', 'Name', 'Action',
                       'Priority'], rows)

    def ospf(self, nid, vname):
        e = self.e
        vrf = self._vrf_by_name(vname)
        out = [' OSPF Process ID default VRF %s' % vname]
        rows = []
        for r in self.sim.get('routers', []):
            rs = e.routers.get(r['name'], {})
            i = rs.get('iface')
            if not i or i['nid'] != nid or e.outs[i['out']]['vrf'] != vrf or r.get('protocol') != 'ospf':
                continue
            if rs.get('adj') in (None, 'DOWN', '-'):
                continue
            state = rs['adj'] + ('/DR' if rs['adj'] == 'FULL' and r.get('ospf', {}).get('nwT', 'bcast') == 'bcast'
                                 else '/ -' if rs['adj'] == 'FULL' else '')
            rows.append(' %-15s %3d %-16s %8s %-15s %s' % (r.get('routerId') or str(ip_of(r['ip'])), 1, state,
                                                           '00:10:23', str(ip_of(r['ip'])),
                                                           e.if_name(i).capitalize()))
        out.append(' Total number of neighbors: %d' % len(rows))
        out.append(' Neighbor ID     Pri State            Up Time  Address         Interface')
        return '\n'.join(out + rows)

    def bgp(self, nid, vname):
        e = self.e
        vrf = self._vrf_by_name(vname)
        asn = e.fabric_asn()
        if not asn:
            return '% BGP ist nicht aktiv (kein Fabric-AS in der BGP Route Reflector Policy)'
        out = ['BGP summary information for VRF %s, address family IPv4 Unicast' % vname,
               'BGP router identifier %s, local AS number %s' % (
                   next((o['nodes'].get(nid, {}).get('rtrId') for o in e.outs.values()
                         if o['vrf'] == vrf and nid in o['nodes']), '0.0.0.0') or '0.0.0.0', asn), '',
               'Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd']
        for o in e.outs.values():
            if o['vrf'] != vrf:
                continue
            for i in o['ifs']:
                if i['nid'] != nid:
                    continue
                for p in i['peers']:
                    r = next((r for r in self.sim.get('routers', []) if str(ip_of(r['ip'])) == p['addr']), None)
                    rs = e.routers.get(r['name'], {}) if r else {}
                    if rs.get('adj') == 'Established':
                        st = str(len(r.get('advertise', [])))
                    else:
                        st = 'Idle' if not rs.get('link') else 'Active'
                    out.append('%-15s 4 %5s %7d %7d %8d %4d %4d %8s %s' % (
                        p['addr'], p['remoteAs'] or '?', 42, 40, 12, 0, 0, '00:12:01', st))
        return '\n'.join(out)

    def vpc(self, nid):
        e = self.e
        g = next((g for g in e.vpc_groups if nid in g['nodes']), None)
        if not g:
            return 'vPC ist auf diesem Switch nicht konfiguriert (keine Explicit vPC Protection Group).'
        peer = [x for x in g['nodes'] if x != nid][0]
        peer_ok = e.nodes.get(peer, {}).get('state') == 'active'
        out = ['Legend:', '                (*) - local vPC is down, forwarding via vPC peer-link', '',
               'vPC domain id                     : %s' % g['id'],
               'Peer status                       : %s' % ('peer adjacency formed ok' if peer_ok else 'peer link is down'),
               'vPC keep-alive status             : Disabled', 'Configuration consistency status  : success',
               'Per-vlan consistency status       : success', 'Type-2 consistency status         : success',
               'vPC role                          : %s' % ('primary' if nid == min(g['nodes']) else 'secondary'),
               'Number of vPCs configured         : %d' % len([p for p in e.paths.values()
                                                             if p['type'] == 'vpc' and nid in p['nodes']]),
               'Peer Gateway                      : Disabled', 'Dual-active excluded VLANs        : -', '',
               'vPC Peer-link status', '-' * 69, 'id   Port   Status Active vlans', '--   ----   ------ ' + '-' * 50,
               '1           %s     -' % ('up' if peer_ok else 'down'), '',
               'vPC status', '-' * 70, 'Id   Port   Status Consistency Reason                     Active vlans',
               '--   ----   ------ ----------- ------                     ------------']
        po = self._po_ids(nid)
        for dn, p in sorted(e.paths.items()):
            if p['type'] != 'vpc' or nid not in p['nodes']:
                continue
            legs = [l for l in p['legs'] if l[0] == nid]
            up = any(e.ports.get(l, {}).get('oper') == 'up' and e.ports[l]['qual'] == 'link-up' for l in legs)
            vl = sorted({d['vlan'] for d in e.deploys if d['path'] == dn})
            out.append('%-4d Po%-4d %-6s %-11s %-26s %s' % (
                680 + po.get(dn, 0), po.get(dn, 0), 'up' if up else 'down', 'success', 'success',
                ','.join(map(str, vl)) or '-'))
        return '\n'.join(out)

    def pc(self, nid):
        e = self.e
        out = ['Flags:  D - Down        P - Up in port-channel (members)',
               '        I - Individual  H - Hot-standby (LACP only)',
               '        s - Suspended   r - Module-removed', '        S - Switched    R - Routed',
               '        U - Up (port-channel)', '        M - Not in use. Min-links not met', '',
               '-' * 80, 'Group Port-       Type     Protocol  Member Ports', '      Channel', '-' * 80]
        for dn, idx in sorted(self._po_ids(nid).items(), key=lambda x: x[1]):
            p = e.paths[dn]
            info = e._pg_info(p['pg'])
            legs = [l for l in p['legs'] if l[0] == nid]
            mem = []
            anyup = False
            for l in legs:
                pi = e.ports.get(l, {})
                if pi.get('qual') == 'link-up':
                    f = 'P'
                    anyup = True
                elif pi.get('qual', '').startswith('suspended'):
                    f = 's'
                else:
                    f = 'D'
                mem.append('%s(%s)' % (l[1].capitalize(), f))
            proto = 'LACP' if info['lacp'] in ('active', 'passive') else 'NONE'
            out.append('%-5d %-11s %-8s %-9s %s' % (idx, 'Po%d(%s)' % (idx, 'SU' if anyup else 'SD'), 'Eth', proto,
                                                    ' '.join(mem)))
        return '\n'.join(out)


# ----------------------------------------------------------------------------
# Verification-Befehle (Leaf, Spine, APIC)
# ----------------------------------------------------------------------------
BD_MAC = '0022.bdf8.19ff'


def _verify_methods():
    """Erweitert Cli um weitere show-Befehle (siehe dispatch_extra)."""

    def bd_svis(self, nid, vrf=None):
        """[(vlanId, bd, gw/len, vrf)] der BD-SVIs auf einem Leaf."""
        e = self.e
        res = []
        for vid, name, encap, ports, bd, d in self._pivlans(nid):
            if d is not None:
                continue
            bvrf = (e.A(bd + '/rsctx') or {}).get('tDn')
            if vrf and bvrf != vrf:
                continue
            if e.A(bd)['unicastRoute'] != 'yes':
                res.append((vid, bd, None, bvrf))
                continue
            subs = e.bd_subnets(bd) + [x for d2 in e.deploys if d2['bd'] == bd for x in e.epg_subnets(d2['epg'])]
            if not subs:
                res.append((vid, bd, None, bvrf))
            for x in subs:
                res.append((vid, bd, x['ip'], bvrf))
        return res

    def ip_int_brief(self, nid, vname):
        e = self.e
        vrf = self._vrf_by_name(vname)
        if vname == 'overlay-1':
            n = e.nodes[nid]
            out = ['IP Interface Status for VRF "overlay-1"(4)', 'Interface            Address              Interface Status']
            for lp, dev, rp, cap, ser in sorted(e.lldp.get(nid, []), key=lambda r: pnum(r[0]) or 0):
                if cap == 'BR':
                    out.append('%-20s %-20s %s' % ('eth%s.%d' % (lp[3:], 7 + (pnum(lp) or 0) % 50), 'unnumbered', 'protocol-up/link-up/admin-up'))
            out.append('%-20s %-20s %s' % ('lo0', n['tep'] + '/32', 'protocol-up/link-up/admin-up'))
            out.append('%-20s %-20s %s' % ('lo1023', e.apic_tep.rsplit('.', 1)[0] + '.32/32', 'protocol-up/link-up/admin-up'))
            return '\n'.join(out)
        if not vrf or vrf not in e.dep_vrf.get(nid, set()):
            return '%% VRF %s ist auf diesem Switch nicht deployed' % vname
        out = ['IP Interface Status for VRF "%s"(%s)' % (vname, 5), 'Interface            Address              Interface Status']
        for vid, bd, gw, _ in self.bd_svis(nid, vrf):
            out.append('%-20s %-20s %s' % ('vlan%d' % vid, gw or 'unassigned', 'protocol-up/link-up/admin-up'))
        for i in e.l3if:
            if i['nid'] == nid and i['vrf'] == vrf:
                out.append('%-20s %-20s %s' % (e.if_name(i), i['addr'], 'protocol-up/link-up/admin-up'))
        for o in e.outs.values():
            if o['vrf'] == vrf and nid in o['nodes'] and o['nodes'][nid]['rtrId']:
                ra = e.A(o['nodes'][nid]['dn'])
                if ra.get('rtrIdLoopBack', 'yes') == 'yes':
                    out.append('%-20s %-20s %s' % ('lo%d' % (3 + list(e.outs).index(o['dn'])), ra['rtrId'] + '/32',
                                                   'protocol-up/link-up/admin-up'))
        return '\n'.join(out)

    def arp(self, nid, vname):
        e = self.e
        vrf = self._vrf_by_name(vname)
        if not vrf or vrf not in e.dep_vrf.get(nid, set()):
            return '%% VRF %s ist auf diesem Switch nicht deployed' % vname
        piv = {d['epg']: vid for vid, _, _, _, _, d in self._pivlans(nid) if d}
        bdv = {bd: vid for vid, _, _, _, bd, d in self._pivlans(nid) if d is None}
        rows = []
        for h in e.all_hosts():
            hs = e.hosts.get(h['name'])
            if hs and hs['learned'] and hs['ipLearned'] and hs['vrf'] == vrf and nid in hs['nodes']:
                p = e.paths[hs['path']]
                intf = p['name'] if p['type'] == 'port' else 'po%d' % self._po_ids(nid).get(hs['path'], 1)
                rows.append((str(ip_of(h['ip'])), '00:01:12', _mac(h['mac']), 'vlan%s' % bdv.get(hs['bd'], '?'), intf))
        for r in self.sim.get('routers', []):
            rs = e.routers.get(r['name'], {})
            i = rs.get('iface')
            if rs.get('link') and i and i['nid'] == nid and i['vrf'] == vrf:
                rows.append((str(ip_of(r['ip'])), '00:03:41', _mac(r.get('mac') or '00:00:5e:00:53:%02x' % (len(rows) + 1)),
                             e.if_name(i), e.if_name(i)))
        out = ['Flags: * - Adjacencies learnt on non-active FHRP router', '       + - Adjacencies synced via CFSoE',
               '       # - Adjacencies Throttled for Glean', '       D - Static Adjacencies attached to down interface', '',
               'IP ARP Table for context %s' % vname, 'Total number of entries: %d' % len(rows),
               'Address         Age       MAC Address     Interface       Physical Interface']
        for r in rows:
            out.append('%-15s %-9s %-15s %-15s %s' % r)
        return '\n'.join(out)

    def mac_table(self, nid, vlan=None):
        e = self.e
        piv = {(d['epg'], d['vlan']): vid for vid, _, _, _, _, d in self._pivlans(nid) if d}
        out = ['Legend:', '        * - primary entry, G - Gateway MAC, (R) - Routed MAC, O - Overlay MAC',
               '        age - seconds since last seen,+ - primary entry using vPC Peer-Link,',
               '        (T) - True, (F) - False, C - ControlPlane MAC', '   VLAN     MAC Address      Type      age     Secure NTFY Ports',
               '---------+-----------------+--------+---------+------+----+------------------']
        n = 0
        for h in e.all_hosts():
            hs = e.hosts.get(h['name'])
            if not hs or not hs['learned'] or nid not in hs['nodes']:
                continue
            vid = piv.get((hs['epg'], vlan_num(hs['encap'])), '?')
            if vlan and str(vid) != str(vlan):
                continue
            p = e.paths[hs['path']]
            intf = p['name'].capitalize() if p['type'] == 'port' else 'Po%d' % self._po_ids(nid).get(hs['path'], 1)
            out.append('* %-7s %-16s %-8s %-9s %-6s %-4s %s' % (vid, _mac(h['mac']), 'dynamic', '-', 'F', 'F', intf))
            n += 1
        for vid, bd, gw, _ in self.bd_svis(nid):
            if gw and (not vlan or str(vlan) == str(vid)):
                out.append('G %-7s %-16s %-8s %-9s %-6s %-4s %s' % (vid, BD_MAC, 'static', '-', 'F', 'F', 'sup-eth1(R)'))
        return '\n'.join(out)

    def epm(self, nid, kind, val):
        e = self.e
        for h in e.all_hosts():
            hs = e.hosts.get(h['name'])
            if not hs or not hs['learned']:
                continue
            if kind == 'ip' and (not hs['ipLearned'] or str(ip_of(h['ip'])) != val):
                continue
            if kind == 'mac' and _mac(h['mac']) != _mac(val.replace('.', '').replace(':', '')
                                                          if len(val.replace('.', '').replace(':', '')) == 12 else val):
                continue
            local = nid in hs['nodes']
            p = e.paths[hs['path']]
            intf = p['name'] if p['type'] == 'port' else 'po%d' % self._po_ids(nid).get(hs['path'], 1)
            other = [x for x in hs['nodes'] if x != nid]
            tunnel = 'tunnel%d' % (10 + (other[0] if other else hs['nodes'][0]) % 90)
            ep = e.cls.get(hs['epg'], {})
            out = ['MAC : %s ::: Num IPs : %d' % (_mac(h['mac']), 1 if hs['ipLearned'] else 0),
                   'IP# 0 : %s ::: IP# 0 flags : %s' % (str(ip_of(h['ip'])) if hs['ipLearned'] else '-',
                                                        'local' if local else ''),
                   'Vlan id : %s ::: Vlan vnid : %s ::: VRF name : %s' % (
                       vlan_num(hs['encap']) if local else 0, 8192 + (vlan_num(hs['encap']) or 0), self._vname(hs['vrf'])),
                   'BD vnid : %s ::: VRF vnid : %s' % (e.A(hs['bd'])['seg'], e.A(hs['vrf'])['scope']),
                   'Phy If : %s ::: Tunnel If : %s' % (intf if local else '0', '0' if local else tunnel),
                   'Interface : %s' % (intf.capitalize() if local else tunnel.capitalize()),
                   'Flags : 0x80004c04 ::: sclass : %s ::: Ref count : 5' % ep.get('pcTag', ''),
                   'EP Create Timestamp : 10/27/2026 09:12:01.123456',
                   'EP Update Timestamp : 10/27/2026 09:12:01.123456',
                   'EP Flags : %s' % ('local|IP|MAC|sclass|timer|' if local else 'IP|MAC|sclass|timer|'),
                   '::::']
            if not local and not e.mpbgp_ok and False:
                pass
            return '\n'.join(out)
        return 'Keinen Endpoint zu %s %s gefunden.' % (kind, val)

    def show_interface(self, nid, port):
        e = self.e
        port = port.lower().replace('ethernet', 'eth')
        if not port.startswith('eth'):
            port = 'eth' + port
        pi = e.ports.get((nid, port))
        if not pi:
            return '%% Invalid interface %s' % port
        n = e.nodes[nid]
        up = pi['oper'] == 'up'
        qual = pi['qual']
        reason = {'link-up': 'none', 'link-not-connected': 'Link not connected', 'admin-down': 'Administratively down',
                  'suspended': 'suspended(no LACP PDUs)', 'suspended-due-to-no-lacp-pdus': 'suspended(no LACP PDUs)'}.get(qual, qual)
        mtu = 9216 if pi['fabric'] or pi['layer'] == 'Layer3' else 9000
        peer = pi.get('peer')
        out = ['%s is %s' % (port.capitalize(), 'up' if up else ('down (%s)' % reason)),
               'admin state is %s, Dedicated Interface' % ('down' if qual == 'admin-down' else 'up'),
               '  Hardware: 1000/10000/25000/auto Ethernet, address: 00de.fb%02x.%04x (bia 00de.fb%02x.%04x)' % (
                   nid % 100, pnum(port) or 0, nid % 100, pnum(port) or 0),
               '  Description: %s' % ('%s %s' % (peer[1], peer[2]) if peer else ''),
               '  MTU %d bytes, BW %s Kbit, DLY 1 usec' % (mtu, '100000000' if pi['speed'] == '100G' else '25000000'),
               '  reliability 255/255, txload 1/255, rxload 1/255',
               '  Encapsulation ARPA, medium is broadcast',
               '  Port mode is %s' % ('routed' if pi['layer'] == 'Layer3' else 'trunk'),
               '  full-duplex, %s' % (pi['speed'].replace('G', ' Gb/s') if up else 'auto-speed'),
               '  Usage: %s' % (', '.join(sorted(pi['usage'])) or 'discovery'),
               '  Allowed VLANs (encap): %s' % (', '.join('vlan-%d' % v for v in sorted(pi['vlans'])) or 'none'),
               '  Last link flapped 01:02:03',
               '  %s' % ('Policy Group: %s' % pi['pg'].split('/')[-1] if pi.get('pg') else 'Keine Access Policy (kein Interface Selector)')]
        return '\n'.join(out)

    def cdp(self, nid):
        e = self.e
        out = ['Capability Codes: R - Router, T - Trans-Bridge, B - Source-Route-Bridge',
               '                  S - Switch, H - Host, I - IGMP, r - Repeater,', '                  V - VoIP-Phone, D - Remotely-Managed-Device,',
               '                  s - Supports-STP-Dispute', '', 'Device-ID          Local Intrfce  Hldtme Capability  Platform      Port ID']
        n = 0
        for (k, port), peer in sorted(e.cabled.items(), key=lambda x: pnum(x[0][1]) or 0):
            if k != nid:
                continue
            pg = e.ports[(k, port)]['pg']
            if not pg or e._pg_info(pg)['cdp'] != 'enabled':
                continue
            out.append('%-18s %-14s %-6s %-11s %-13s %s' % (peer[1][:18], port.capitalize(), '163',
                                                            'H' if peer[0] == 'host' else 'R S I', 'Linux' if peer[0] == 'host' else 'ISR4331', 'eth0' if peer[0] == 'host' else 'Gig0/0/0'))
            n += 1
        for vc in self.sim.get('vcenters', []):
            for esx in vc.get('hosts', []):
                for s_, p_ in esx.get('links', []):
                    if e.serial_active.get(s_) == nid:
                        pg = e.ports.get((nid, p_), {}).get('pg')
                        if pg and e._pg_info(pg)['cdp'] == 'enabled':
                            out.append('%-18s %-14s %-6s %-11s %-13s %s' % (esx['name'], p_.capitalize(), '163', 'S', 'VMware ESXi', 'vmnic%d' % esx['links'].index([s_, p_])))
                            n += 1
        out.append('')
        out.append('Total entries displayed: %d' % n)
        return '\n'.join(out)

    def _filters(self):
        """Filter-IDs wie in show zoning-rule (gleiche Nummerierung)."""
        e = self.e
        fid = {}
        for brc, rel in sorted(e.contracts.items()):
            for subj in e.kids(brc, 'vzSubj'):
                for rf in e.kids(subj, 'vzRsSubjFiltAtt'):
                    rfa = e.A(rf)
                    if rfa['state'] == 'formed':
                        fid.setdefault(rfa['tDn'], 4 + len(fid) + 1)
        return fid

    def zoning_filter(self, nid, which):
        e = self.e
        rows = [(2, 'implarp', 'arp', 'unspecified', 'unspecified', 'unspecified', 'unspecified', 'no'),
                (4, 'implicit', 'unspecified', 'unspecified', 'unspecified', 'unspecified', 'unspecified', 'no')]
        for flt, i in sorted(self._filters().items(), key=lambda x: x[1]):
            for en in e.kids(flt, 'vzEntry'):
                a = e.A(en)
                rows.append((i, '%s_%s' % (i, a['name']), a['etherT'], a.get('prot', 'unspecified'),
                             '%s-%s' % (a.get('sFromPort', 'unspecified'), a.get('sToPort', 'unspecified')),
                             '%s-%s' % (a.get('dFromPort', 'unspecified'), a.get('dToPort', 'unspecified')),
                             a.get('tcpRules') or 'unspecified', a.get('stateful', 'no')))
        if which:
            rows = [r for r in rows if str(r[0]) == which]
        return _table(['FilterId', 'Name', 'EtherT', 'Prot', 'SFromPort-SToPort', 'DFromPort-DToPort', 'TcpRules', 'Stateful'], rows)

    def contract_parser(self, nid, vname):
        e = self.e
        vrf = self._vrf_by_name(vname) if vname else None
        names = {c['pcTag']: (c['dn'], c) for c in e.cls.values()}
        fnames = {i: f for f, i in self._filters().items()}
        out = []
        z = self.zoning(nid, e.A(vrf)['scope'] if vrf else None)
        if z.startswith('Keine'):
            return z
        for line in z.split('\n')[3:-1]:
            cells = [c.strip() for c in line.strip('|').split('|')]
            rid, src, dst, fid, dirn, _, scope, name, action, prio = cells
            if fid in ('implicit', 'implarp'):
                continue
            def label(tag):
                if tag == '0':
                    return 'any'
                dn, c = names.get(tag, (None, None))
                if c and c.get('vname'):
                    return 'epg:%s' % c['vname']
                return ('epg:%s' % e.short(dn)) if dn else tag
            flt = fnames.get(int(fid)) if fid.isdigit() else None
            desc = []
            for en in e.kids(flt, 'vzEntry') if flt else []:
                a = e.A(en)
                port = a.get('dFromPort', 'unspecified')
                if dirn == 'uni-dir-ignore':
                    port = a.get('dFromPort', 'unspecified')
                    desc.append('%s %s%s' % (a['etherT'], a.get('prot', ''), '' if port == 'unspecified' else ' sport %s' % port))
                else:
                    desc.append('%s %s%s' % (a['etherT'], a.get('prot', ''), '' if port == 'unspecified' else ' eq %s' % port))
            vrfname = next((self._vname(v) for v in e.dep_vrf.get(nid, set()) if e.A(v)['scope'] == scope), scope)
            out.append('[%s:%s] [vrf:%s] %s %s %s %s [contract:%s] [hit=0]' % (
                rid, prio.split('(')[-1].rstrip(')'), vrfname, action, ', '.join(desc) or 'ip', label(src), label(dst),
                name or '-'))
        return '\n'.join(out) if out else 'Keine Contract-Regeln auf diesem Switch.'

    def bgp_table(self, nid, vname):
        e = self.e
        vrf = self._vrf_by_name(vname)
        if not e.fabric_asn():
            return '% BGP ist nicht aktiv (kein Fabric-AS in der BGP Route Reflector Policy)'
        if not vrf or vrf not in e.dep_vrf.get(nid, set()):
            return '%% VRF %s ist auf diesem Switch nicht deployed' % vname
        out = ['BGP routing table information for VRF %s, address family IPv4 Unicast' % vname,
               'BGP table version is 42, Local Router ID is %s' % next((o['nodes'][nid]['rtrId'] for o in e.outs.values()
                                                                        if o['vrf'] == vrf and nid in o['nodes']), e.nodes[nid]['tep']),
               'Status: s-suppressed, x-deleted, S-stale, d-dampened, h-history, *-valid, >-best',
               'Path type: i-internal, e-external, c-confed, l-local, a-aggregate, r-redist, I-injected',
               'Origin codes: i - IGP, e - EGP, ? - incomplete, | - multipath, & - backup', '',
               '   Network            Next Hop            Metric     LocPrf     Weight Path']
        for rt in sorted(e.routes.get((vrf, nid), []), key=lambda r: ipaddress.ip_network(r['prefix'], strict=False)):
            if rt['proto'] == 'bgp' and rt.get('border'):
                out.append('*>i%-18s %-19s %-10s %-10s %-6s %s' % (rt['prefix'], rt['nh'], '0', '100', '0', '?'))
            elif rt['proto'] in ('bgp', 'ospf', 'static'):
                asn = next((r.get('bgp', {}).get('asn') for r in self.sim.get('routers', []) if r['name'] == rt.get('router')), '')
                out.append('*>%s%-18s %-19s %-10s %-10s %-6s %s' % ('e' if rt['proto'] == 'bgp' else 'r', rt['prefix'], rt['nh'], '0', '100',
                                                                    '0', ('%s i' % asn) if rt['proto'] == 'bgp' else '?'))
        for o in e.outs.values():
            if o['vrf'] == vrf and nid in o['nodes']:
                for net in e.exported_subnets(o['dn'], nid):
                    out.append('*>r%-18s %-19s %-10s %-10s %-6s %s' % (net, '0.0.0.0', '0', '100', '32768', '?'))
        return '\n'.join(out)

    def ospf_if(self, nid, vname):
        e = self.e
        vrf = self._vrf_by_name(vname)
        out = [' OSPF Process ID default VRF %s' % vname, ' Total number of interface: %d' % sum(
            1 for i in e.l3if if i['nid'] == nid and i['vrf'] == vrf and i['ospf']),
               ' Interface               ID     Area            Cost   State    Neighbors Status']
        for k, i in enumerate([i for i in e.l3if if i['nid'] == nid and i['vrf'] == vrf and i['ospf']]):
            o = e.outs[i['out']]
            area = (o['ospf'] or {}).get('areaId', 'backbone')
            area = '0.0.0.0' if area in ('backbone', '0') else area
            nb = sum(1 for r in self.sim.get('routers', []) if (e.routers.get(r['name'], {}).get('iface') or {}).get('dn') == i['dn']
                     and e.routers[r['name']].get('adj') == 'FULL')
            nwt = (i['pol'] or {}).get('nwT', 'bcast')
            out.append(' %-23s %-6d %-15s %-6d %-8s %-9d %s' % (e.if_name(i), k + 7, area, 4, 'P2P' if nwt == 'p2p' else 'BDR',
                                                               nb, 'up'))
        return '\n'.join(out)

    def iping(self, nid, vname, dst):
        from . import trace
        e = self.e
        vrf = self._vrf_by_name(vname)
        if not vrf or vrf not in e.dep_vrf.get(nid, set()):
            return '%% VRF %s ist auf diesem Switch nicht deployed' % vname
        try:
            dip = ipaddress.ip_address(dst)
        except ValueError:
            return '% Invalid IP address'
        svis = [x for x in self.bd_svis(nid, vrf) if x[2]]
        src = next((x for x in svis if dip in ipaddress.ip_interface(x[2]).network), svis[0] if svis else None)
        ok = False
        why = 'Request timed out'
        if any(str(ip_of(x[2])) == dst for x in svis):
            ok = True
        else:
            host = next((h for h in e.all_hosts() if str(ip_of(h['ip'])) == dst), None)
            if host:
                hs = e.hosts.get(host['name'], {})
                if hs.get('vrf') == vrf or (hs.get('quiet') and hs.get('dep') and hs['dep']['vrf'] == vrf):
                    bd = hs.get('bd') or (hs.get('dep') or {}).get('bd')
                    if hs.get('learned'):
                        ok = True
                    elif hs.get('quiet') and bd and e.A(bd)['unicastRoute'] == 'yes' and any(
                            dip in x['net'] for x in e.bd_subnets(bd)):
                        ok = True
                        self.sim.setdefault('woken', []).append(host['name'])
                        self.request = self.request or 'changed'
                        why = None
                    else:
                        why = 'Ziel nicht gelernt (%s)' % '; '.join(hs.get('reasons', [])[:1])
                else:
                    why = 'Ziel liegt nicht in VRF %s' % vname
            else:
                rts = [r for r in e.routes.get((vrf, nid), []) if dip in ipaddress.ip_network(r['prefix'], strict=False)]
                if not rts:
                    why = 'Keine Route zu %s in VRF %s' % (dst, vname)
                else:
                    if not src:
                        li = next((i for i in e.l3if if i['nid'] == nid and i['vrf'] == vrf), None)
                        src = (0, None, li['addr'], vrf) if li else None
                    sip = ipaddress.ip_address(src[2].split('/')[0]) if src else None
                    rtr = next((r for r in self.sim.get('routers', []) if (e.routers.get(r['name'], {}).get('iface') or {}).get('vrf') == vrf
                                and (str(ip_of(r['ip'])) == dst or any(dip in ipaddress.ip_network(n, strict=False) for n in r.get('networks', [])))), None)
                    if not rtr:
                        why = 'Request timed out (der externe Router kennt %s nicht)' % dst
                    else:
                        rs = e.routers[rtr['name']]
                        back = sip and (ipaddress.ip_network(rtr['ip'], strict=False).overlaps(ipaddress.ip_network(str(sip) + '/32'))
                                        or any(sip in ipaddress.ip_network(n, strict=False) for n in rs.get('learned', []) + rtr.get('staticBack', [])))
                        ok = bool(back)
                        if not ok:
                            why = 'Request timed out (Router %s hat keine Route zurueck zu %s)' % (rtr['name'], sip)
        lines = ['PING %s (%s) from %s: 56 data bytes' % (dst, dst, src[2].split('/')[0] if src else '0.0.0.0')]
        for i in range(5):
            lines.append('64 bytes from %s: icmp_seq=%d ttl=63 time=%.3f ms' % (dst, i, 0.3 + i * 0.05) if ok else 'Request %d timed out' % i)
        lines += ['', '--- %s ping statistics ---' % dst,
                  '5 packets transmitted, %d packets received, %s packet loss' % (5 if ok else 0, '0.00%' if ok else '100.00%')]
        if ok:
            lines.append('round-trip min/avg/max = 0.300/0.400/0.500 ms')
        elif why and why != 'Request timed out':
            if why.startswith('Request timed out ('):
                why = why[len('Request timed out ('):-1]
            lines.append('Hinweis (Datacenter Prep): %s' % why)
        return '\n'.join(lines)

    def overlay_routes(self, nid):
        e = self.e
        out = ['IP Route Table for VRF "overlay-1"', "'*' denotes best ucast next-hop", '']
        me = e.nodes[nid]
        uplinks = [lp for lp, dev, rp, cap, ser in e.lldp.get(nid, []) if cap == 'BR']
        tgts = [(me['tep'], None)] + [(n['tep'], n) for k, n in sorted(e.nodes.items()) if k != nid and n['state'] == 'active']
        for tep, n in sorted(tgts, key=lambda x: ipaddress.ip_address(x[0])):
            if n is None:
                out += ['%s/32, ubest/mbest: 2/0, attached' % tep, '    *via %s, lo0, [0/0], 01:02:03, local, local' % tep]
                continue
            out.append('%s/32, ubest/mbest: %d/0' % (tep, max(1, len(uplinks) if n['role'] == 'leaf' and me['role'] == 'leaf' else 1)))
            via = uplinks if n['role'] == 'leaf' and me['role'] == 'leaf' else \
                [lp for lp, dev, rp, cap, ser in e.lldp.get(nid, []) if dev == n['name']]
            for lp in via or uplinks[:1]:
                out.append('    *via 10.0.0.%d, eth%s.%d, [115/%d], 01:02:03, isis-isis_infra, isis-l1-int' % (
                    30 + (pnum(lp) or 0), lp[3:], 7 + (pnum(lp) or 0) % 50, 3 if me['role'] == n['role'] else 2))
        return '\n'.join(out)

    def isis(self, nid):
        e = self.e
        out = ['IS-IS process: isis_infra VRF:overlay-1', 'IS-IS adjacency database:',
               'System ID               SNPA            Level  State  Hold Time  Interface']
        for lp, dev, rp, cap, ser in sorted(e.lldp.get(nid, []), key=lambda r: pnum(r[0]) or 0):
            if cap != 'BR':
                continue
            pid = e.serial_active.get(ser)
            if pid is None:
                continue
            out.append('%-23s %-15s %-6s %-6s %-10s %s' % ('%s' % e.nodes[pid]['tep'], 'N/A', '1', 'UP', '00:01:04',
                                                          'Ethernet%s.%d' % (lp[3:], 7 + (pnum(lp) or 0) % 50)))
        return '\n'.join(out)

    def vpnv4(self, nid):
        e = self.e
        ok, asn, rr = e.mpbgp()
        me = e.nodes[nid]
        if not asn:
            return '% BGP ist nicht aktiv: In der BGP Route Reflector Policy fehlt das Fabric-AS.'
        out = ['BGP summary information for VRF overlay-1, address family VPNv4 Unicast',
               'BGP router identifier %s, local AS number %s' % (me['tep'], asn), '',
               'Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd']
        rr_ids = [int(x) for x in (rr or [])]
        if me['role'] == 'spine':
            if nid not in rr_ids:
                return '% Dieser Spine ist kein Route Reflector (System > System Settings > BGP Route Reflector)'
            peers = [n for k, n in sorted(e.nodes.items()) if n['role'] == 'leaf' and n['state'] == 'active']
        else:
            peers = [e.nodes[k] for k in rr_ids if k in e.nodes and e.nodes[k]['state'] == 'active']
        if not peers:
            out.append('(keine Peers - kein aktiver Spine als Route Reflector)')
        for n in peers:
            pfx = sum(1 for (v, x), rts in e.routes.items() if x == n['id'] for r in rts if r['proto'] in ('ospf', 'bgp', 'static') and not r.get('border'))
            out.append('%-15s 4 %5s %7d %7d %8d %4d %4d %8s %s' % (n['tep'], asn, 120, 118, 33, 0, 0, '01:02:03', pfx))
        return '\n'.join(out)

    def coop(self, nid):
        e = self.e
        if e.nodes[nid]['role'] != 'spine':
            return '% COOP-Datenbank gibt es nur auf Spines'
        out = ['IP DB entries:']
        n = 0
        for h in e.all_hosts():
            hs = e.hosts.get(h['name'])
            if not hs or not hs['learned'] or not hs['ipLearned']:
                continue
            n += 1
            pub = e.nodes[hs['nodes'][0]]
            out += ['', 'Global epoc: 0', 'VRF vnid: %s' % e.A(hs['vrf'])['scope'], 'IP: %s' % ip_of(h['ip']),
                    'MAC: %s' % h['mac'].upper(), 'BD vnid: %s' % e.A(hs['bd'])['seg'],
                    'Publisher Id: %s' % pub['tep'], 'Record timestamp: 10 27 2026 09:12:01 123456789',
                    'Tunnel nh: %s' % (pub['tep'] if len(hs['nodes']) == 1 else '10.0.%d.%d (vPC Anycast)' % (64, hs['nodes'][0] % 250)),
                    'Num of repositories: %d' % len(hs['nodes'])]
        out.insert(1, 'Total entries: %d' % n)
        return '\n'.join(out)

    for f in (bd_svis, ip_int_brief, arp, mac_table, epm, show_interface, cdp, _filters, zoning_filter, contract_parser,
              bgp_table, ospf_if, iping, overlay_routes, isis, vpnv4, coop):
        setattr(Cli, f.__name__, f)


_verify_methods()


def _destgrp(self, g, conn):
    """Fortlaufende Destination-Group-Nummer je PBR Policy (wie in show service redir info)."""
    pols = []
    for gg in sorted(getattr(self.e, 'graphs', {}).values(), key=lambda x: x['dn']):
        for c_ in ('consumer', 'provider'):
            p_ = gg['conns'].get(c_, {}).get('pol')
            if p_ and p_ not in pols:
                pols.append(p_)
    pol = g['conns'][conn]['pol']
    return pols.index(pol) + 1 if pol in pols else 0


def redir_info(self, nid):
    e = self.e
    groups = []
    for g in sorted(getattr(e, 'graphs', {}).values(), key=lambda x: x['dn']):
        if g['state'] != 'applied' or g['vrf'] not in e.dep_vrf.get(nid, set()):
            continue
        for conn in ('consumer', 'provider'):
            c_ = g['conns'][conn]
            n = self._destgrp(g, conn)
            if n and n not in [x[0] for x in groups]:
                groups.append((n, c_, g['vrf']))
    out = ['=' * 100, 'LEGEND', 'TL: Threshold(Low)  | TH: Threshold(High) | HP: HashProfile | HG: HealthGrp | BAC: Backup-Dest',
           '=' * 100, 'List of Dest Groups',
           'GrpID Name                destination                                    HG-name       BAC  operSt   operStQual   HP',
           '===== ====                ===========                                    =======       ===  ======   ==========   ==']
    dests = []
    for n, c_, vrf in sorted(groups, key=lambda x: x[0]):
        vn = e.A(vrf)['scope']
        for d in c_['dests']:
            name = 'dest-[%s]-[vxlan-%s]' % (d['ip'], vn)
            out.append('%-5d %-19s %-46s %-13s %-4s %-8s %-12s %s' % (n, 'destgrp-%d' % n, name, 'Not attached', 'N', 'enabled',
                                                                     'no-oper-grp', 'sym'))
            dests.append((name, 'vxlan-%s' % e.A(c_['bd'])['seg'], d['mac'] or '00:00:00:00:00:00', self._vname(vrf)))
    out += ['', 'List of destinations', 'Name                                      bdVnid          vMac                vrf                  operSt   HG-name',
            '====                                      ======          ====                ===                  ======   =======']
    for name, bdv, mac, vrfn in dests:
        out.append('%-41s %-15s %-19s %-20s %-8s %s' % (name, bdv, mac, vrfn, 'enabled', 'Not attached'))
    if not groups:
        out.append('(keine PBR-Ziele auf diesem Switch - kein angewendeter Service Graph mit Redirect im VRF)')
    return '\n'.join(out)


Cli._destgrp = _destgrp
Cli.redir_info = redir_info


def dispatch_extra(self, nid, c):
    """Weitere Leaf-/Spine-Befehle. Rueckgabe None = unbekannt."""
    if c in ('show service redir info', 'show service redir info group'):
        return self.redir_info(nid)
    m = re.match(r'^show ip int(?:erface)? br(?:ief)? vrf (\S+)$', c)
    if m:
        return self.ip_int_brief(nid, m.group(1))
    m = re.match(r'^show ip arp vrf (\S+)$', c)
    if m:
        return self.arp(nid, m.group(1))
    m = re.match(r'^show mac address-table(?: vlan (\d+))?$', c)
    if m:
        return self.mac_table(nid, m.group(1))
    m = re.match(r'^show system internal epm endpoint (ip|mac) (\S+)$', c)
    if m:
        return self.epm(nid, m.group(1), m.group(2))
    m = re.match(r'^show int(?:erface)? (e(?:th(?:ernet)?)?\s?\d+/\d+)$', c)
    if m:
        return self.show_interface(nid, re.sub(r'^e(?:th(?:ernet)?)?\s?', 'eth', m.group(1)))
    if c in ('show cdp neighbors', 'show cdp neighbor', 'show cdp nei'):
        return self.cdp(nid)
    m = re.match(r'^show zoning-filter(?: filter (\d+))?$', c)
    if m:
        return self.zoning_filter(nid, m.group(1))
    m = re.match(r'^contract_parser(?:\.py)?(?: --vrf (\S+))?$', c)
    if m:
        return self.contract_parser(nid, m.group(1))
    m = re.match(r'^show bgp ipv4 unicast vrf (\S+)$', c)
    if m:
        return self.bgp_table(nid, m.group(1))
    m = re.match(r'^show ip ospf int(?:erface)? br(?:ief)? vrf (\S+)$', c)
    if m:
        return self.ospf_if(nid, m.group(1))
    m = re.match(r'^iping (?:-V|vrf) (\S+) (\S+)$', c)
    if m:
        return self.iping(nid, m.group(1), m.group(2))
    if c == 'show ip route vrf overlay-1':
        return self.overlay_routes(nid)
    if re.match(r'^show isis adjacency(?: detail)? vrf overlay-1$', c):
        return self.isis(nid)
    if re.match(r'^show bgp vpnv4 unicast summary vrf overlay-1$', c):
        return self.vpnv4(nid)
    if c in ('show coop internal info ip-db', 'show coop internal info repo ep'):
        return self.coop(nid)
    if c in ('show vlan', 'show vlan brief'):
        return self.switch(self.e.nodes[nid], 'show vlan extended')
    return None


def apic_extra(self, cmd):
    e = self.e
    c = re.sub(r'\s+', ' ', cmd.strip())
    m = re.match(r'^show faults?( detail)?$', c)
    if m:
        st = e.store
        rows = sorted((st.attrs(d) for d in st.by_class('faultInst')),
                      key=lambda a: (['critical', 'major', 'minor', 'warning'].index(a['severity'])
                                     if a['severity'] in ('critical', 'major', 'minor', 'warning') else 9, a['code']))
        if not rows:
            return 'Keine aktiven Faults.'
        out = []
        if m.group(1):
            for a in rows:
                out += [' Code         : %s' % a['code'], ' Severity     : %s' % a['severity'], ' Cause        : %s' % a['cause'],
                        ' Affected     : %s' % a['dn'].rsplit('/fault-', 1)[0], ' Description  : %s' % a['descr'],
                        ' Created      : %s' % a.get('created', ''), '']
            return '\n'.join(out)
        out = [' Code   Severity Affected Object' + ' ' * 41 + 'Cause', ' ------ -------- ' + '-' * 56 + ' ' + '-' * 24]
        for a in rows:
            out.append(' %-6s %-8s %-56s %s' % (a['code'], a['severity'], a['dn'].rsplit('/fault-', 1)[0][:56], a['cause']))
        out.append('\n Total: %d' % len(rows))
        return '\n'.join(out)
    m = re.match(r'^show endpoints?(?: ip (\S+))?$', c)
    if m:
        out = [' Dynamic Endpoints:', ' Tenant      : Application : AEPg  MAC                IP               Node        Interface          Encap',
               ' ' + '-' * 112]
        for h in e.all_hosts():
            hs = e.hosts.get(h['name'])
            if not hs or not hs['learned']:
                continue
            ip = str(ip_of(h['ip'])) if hs['ipLearned'] else '---'
            if m.group(1) and ip != m.group(1):
                continue
            p = split_dn(hs['epg'])
            p_ = e.paths[hs['path']]
            out.append(' %-38s %-18s %-16s %-11s %-18s %s' % (
                ':'.join(x.split('-', 1)[1] for x in p[1:4]), h['mac'].upper(), ip,
                ','.join(str(n) for n in hs['nodes']), p_['name'] if p_['type'] == 'port' else p_['name'], hs['encap']))
        out.append('\n Total Dynamic Endpoints: %d' % (len(out) - 3))
        return '\n'.join(out)
    if c in ('show bridge-domain', 'show bd'):
        out = [' Tenant           Bridge Domain          VRF                Unicast  ARP Flood  L2 Unk Ucast  Subnets',
               ' ' + '-' * 106]
        for bd in sorted(e.store.by_class('fvBD')):
            a = e.A(bd)
            vrf = (e.A(bd + '/rsctx') or {}).get('tDn', '')
            out.append(' %-16s %-22s %-18s %-8s %-10s %-13s %s' % (split_dn(bd)[1][3:], a['name'], vrf.split('ctx-')[-1] if vrf else '-',
                                                                    a['unicastRoute'], a['arpFlood'], a['unkMacUcastAct'],
                                                                    ', '.join(x['ip'] for x in e.bd_subnets(bd)) or '-'))
        return '\n'.join(out)
    if c == 'show epg':
        out = [' Tenant           AP               EPG              BD               pcTag  Endpoints  Health',
               ' ' + '-' * 96]
        for d, cl in sorted(e.cls.items()):
            if cl['kind'] != 'epg':
                continue
            p = split_dn(d)
            n = sum(1 for hs in e.hosts.values() if hs.get('learned') and hs.get('epg') == d)
            out.append(' %-16s %-16s %-16s %-16s %-6s %-10d %s' % (p[1][3:], p[2][3:], p[3][4:], e.A(cl['bd'])['name'] if cl['bd'] else '-',
                                                                cl['pcTag'], n, e.score(d)))
        return '\n'.join(out)
    m = re.match(r'^show vmware domain(?: name (\S+))?$', c)
    if m:
        doms = [v for v in getattr(e, 'vmm', {}).values() if not m.group(1) or v['name'] == m.group(1)]
        if not doms:
            return '%% VMM Domain %s nicht gefunden' % (m.group(1) or '')
        out = []
        for v in doms:
            vc = next((x for x in self.sim.get('vcenters', []) if x['name'] == v['vc']), None)
            ctrl = e.kids(v['dn'], 'vmmCtrlrP')
            ca = e.A(ctrl[0]) if ctrl else {}
            out += ['Domain Name                    : %s' % v['name'], 'Virtual Switch Mode            : VMware Distributed Switch',
                    'Vlan Domain                    : %s' % ((e.A(v['dn'] + '/rsvlanNs') or {}).get('tDn', '-').split('[')[-1].split(']')[0]),
                    'Physical Interfaces            : %s' % ', '.join(sorted({'%s %s' % (e.nodes[l[0]]['name'], l[1]) for x in v['hosts'] for l in x['legs']})),
                    'Number of EPGs                 : %d' % len(v['pgs']), 'Faults by Severity             : 0, 0, 0, 0',
                    'LLDP override                  : %s' % ('LLDP' if v['discovery'] == 'lldp' else 'no'),
                    'CDP override                   : %s' % ('CDP' if v['discovery'] == 'cdp' else 'no'),
                    '', 'vCenters:', 'Faults: Grouped by severity (Critical, Major, Minor, Warning)',
                    'vCenter                Type        Datacenter   Status    ESXs  VMs   Faults',
                    '---------------------  ----------  -----------  --------  ----  ----  -------',
                    '%-22s %-11s %-12s %-9s %-5s %-5s %s' % (ca.get('hostOrIp', '-'), 'vCenter', ca.get('rootContName', '-'),
                                                             v['state'], len(v['hosts']),
                                                             sum(len(x.get('vms', [])) for x in (vc or {}).get('hosts', [])
                                                                 if v['name'] in x.get('dvs', [])), '0,%d,0,0' % (1 if v['state'] != 'online' else 0))]
            if v['reasons']:
                out.append('Grund: %s' % '; '.join(v['reasons']))
            out += ['', 'Hypervisor          Uplinks                     Status', '------------------  --------------------------  ------']
            for x in v['hosts']:
                out.append('%-19s %-27s %s' % (x['name'], ', '.join('%s %s' % (e.nodes[l[0]]['name'], l[1]) for l in x['legs']),
                                               'up' if x['ok'] else 'down: ' + '; '.join(x['reasons'])))
            out += ['', 'DVS Port Group                       VLAN       EPG', '-----------------------------------  ---------  ---------------------']
            for epg, g in sorted(v['pgs'].items()):
                out.append('%-36s %-10s %s' % (g['name'], 'vlan-%d' % g['vlan'], e.short(epg)))
            out.append('')
        return '\n'.join(out)
    return None


Cli.apic_extra = apic_extra
