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
                res.append((vid, '%s:%s:%s' % (p[1][3:], p[2][3:], p[3][4:]), 'vlan-%d' % d['vlan'], ports, bd, d))
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
        if m:
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
            return '% VRF %s ist auf diesem Switch nicht deployed' % vname
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
        for _, lines in sorted(entries, key=lambda x: (int(x[0].network_address), x[0].prefixlen)):
            out.extend(lines)
        return '\n'.join(out)

    def zoning(self, nid, scope):
        e = self.e
        rows = []
        fid = {}
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
                if not cons or not prov:
                    continue
                for subj in e.kids(brc, 'vzSubj'):
                    for rf in e.kids(subj, 'vzRsSubjFiltAtt'):
                        rfa = e.A(rf)
                        if rfa['state'] != 'formed':
                            continue
                        f = fid.setdefault(rfa['tDn'], 4 + len(fid) + 1)
                        for cpt in cons:
                            for ppt in prov:
                                if cpt == ppt:
                                    continue
                                pr = 'fully_qual(7)' if cpt != '0' and ppt != '0' else 'any_dest_filter(14)'
                                rows.append((rid, cpt, ppt, f, 'bi-dir', 'enabled', vn, e.A(brc)['name'],
                                             rfa['action'], pr)); rid += 1
                                rows.append((rid, ppt, cpt, f, 'uni-dir-ignore', 'enabled', vn, e.A(brc)['name'],
                                             rfa['action'], pr)); rid += 1
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
