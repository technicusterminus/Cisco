"""Multi-Site: vereinfachter Nexus Dashboard Orchestrator (NDO) mit einer simulierten zweiten Site.

Der NDO onboardet den lokalen APIC, konfiguriert die Infra (Site ID, ISN-Anbindung der
Spines, BGP EVPN, Overlay Unicast TEP) und deployt Templates. Die Objekte landen im
lokalen APIC mit annotation=orchestrator:msc; die zweite Site (DC-HAM) ist simuliert.
"""
import ipaddress
import re
import time

from .model import AciError, post as mit_post, delete as mit_delete, now_ts

ANNOT = 'orchestrator:msc'
ISN_MIN_MTU = 9150


def default_ndo():
    return {'sites': {'local': {'onboarded': False, 'siteId': '', 'user': '', 'error': ''},
                      'DC-HAM': {'onboarded': True, 'siteId': '2', 'down': False}},
            'infra': {'deployed': False, 'area': '0.0.0.0', 'ucastTep': '', 'peering': 'full-mesh', 'spines': [], 'error': ''},
            'remote': {'name': 'DC-HAM', 'apic': '10.20.0.1', 'ucastTep': '172.16.200.1/32', 'spines': ['ham-spine1', 'ham-spine2'],
                       'hosts': [{'name': 'ham-web1', 'mac': '00:50:56:20:10:51', 'ip': '10.10.10.51/24', 'tenant': 'Shop', 'ap': 'Webshop', 'epg': 'Web'},
                                 {'name': 'ham-app1', 'mac': '00:50:56:20:20:51', 'ip': '10.20.20.51/24', 'tenant': 'Shop', 'ap': 'Webshop', 'epg': 'App-HAM'}]},
            'templates': []}


def multisite_topology():
    from .topology import default_topology
    t = default_topology()
    t['ipnlinks'] = [['FDO2219SP01', 'eth1/31', 'isn1', 'Eth1/1'], ['FDO2219SP02', 'eth1/31', 'isn1', 'Eth1/2']]
    t['kind'] = 'multisite'
    return t


def default_isn():
    return {'routers': [{'name': 'isn1', 'pod': 1, 'kind': 'isn', 'mtu': 9150, 'area': '0.0.0.0', 'pim': False, 'rp': '', 'relay': [],
                         'down': False, 'ifs': [{'serial': 'FDO2219SP01', 'port': 'eth1/31', 'vlan': 4, 'ip': '10.255.1.2/30'},
                                                {'serial': 'FDO2219SP02', 'port': 'eth1/31', 'vlan': 4, 'ip': '10.255.1.6/30'}]}]}


def _filter_ok(spec, proto, port):
    for part in [p.strip() for p in (spec or 'any').split(',') if p.strip()]:
        if part in ('any', 'default'):
            return True
        if part == 'icmp' and proto == 'icmp':
            return True
        m = re.match(r'^(tcp|udp)/(\d+)$', part)
        if m and m.group(1) == proto and int(m.group(2)) == int(port or 0):
            return True
    return False


class SiteMixin:
    def ndo(self):
        return self.sim.get('ndo')

    def msite_state(self):
        """Infra-Zustand zwischen den Sites. Rueckgabe Fehlertext oder None."""
        n = self.ndo()
        if not n:
            return 'Kein Nexus Dashboard Orchestrator in dieser Umgebung (Lab 31 laden)'
        loc = n['sites']['local']
        if not loc['onboarded']:
            return 'Der lokale APIC ist im NDO nicht onboardet'
        if n['sites']['DC-HAM'].get('down'):
            return 'Site DC-HAM ist nicht erreichbar'
        if not n['infra']['deployed']:
            return 'Die Infra-Konfiguration (Site ID, ISN, BGP EVPN) ist im NDO noch nicht deployt'
        ext = [d for d in self.store.by_class('fabricExtConnP') if d.startswith('uni/tn-infra/')]
        if not ext or self.A(ext[0]).get('siteId') != loc['siteId']:
            return 'Im APIC fehlt die Site ID aus dem NDO (Fabric External Connection Policy) - Infra neu deployen'
        isn = [a for a in getattr(self, 'mp', {}).get('adj', []) if a['kind'] == 'isn']
        if not any(a['state'] == 'FULL' for a in isn):
            why = '; '.join('%s: %s' % (a['port'], a['why'] or a['state']) for a in isn) or 'keine ISN-Links'
            return 'Kein Spine hat OSPF FULL zum ISN (%s)' % why
        small = [r for r in (self.sim.get('ipn') or {}).get('routers', []) if r['kind'] == 'isn' and int(r.get('mtu') or 1500) < ISN_MIN_MTU]
        if small:
            return 'ISN-MTU %s zu klein - VXLAN zwischen den Sites braucht mindestens %d' % (small[0]['mtu'], ISN_MIN_MTU)
        if not all(s.get('evpnRid') for s in n['infra']['spines']) or not n['infra']['spines']:
            return 'Den Spines fehlt die BGP-EVPN Router-ID - keine EVPN-Sessions zu DC-HAM'
        if not n['infra'].get('ucastTep'):
            return 'Overlay Unicast TEP der lokalen Site fehlt'
        return None

    def site_template(self, tenant, ap, epg, site):
        for t in self.ndo().get('templates', []):
            if t['tenant'] != tenant or site not in t.get('sites', []) or not t.get('deployed', {}).get(site):
                continue
            for a in t.get('aps', []):
                if a['name'] == ap:
                    for e in a.get('epgs', []):
                        if e['name'] == epg:
                            return t, e
        return None, None

    def remote_host(self, name_or_ip):
        n = self.ndo()
        if not n:
            return None
        for h in n['remote']['hosts']:
            if h['name'] == name_or_ip or h['ip'].split('/')[0] == name_or_ip:
                return h
        return None

    def site_path(self, t, shs, sh, rh, proto, port):
        """Traffic-Test zu einem Host in DC-HAM."""
        why = self.msite_state()
        if why:
            t.step(False, 'Multi-Site', why)
            return False
        m = re.match(r'^uni/tn-([^/]+)/ap-([^/]+)/epg-(.+)$', shs['epg'] or '')
        if not m:
            t.step(False, 'Multi-Site', 'Die Quelle liegt in keiner Application EPG')
            return False
        tn, ap, epg = m.groups()
        if (self.A(shs['epg']) or {}).get('annotation') != ANNOT:
            t.step(False, 'Multi-Site', 'EPG %s wurde lokal angelegt, nicht vom NDO - sie ist nicht zwischen den Sites gestreckt' % self.short(shs['epg']))
            return False
        lt, le = self.site_template(tn, ap, epg, 'local')
        rt, re_ = self.site_template(rh['tenant'], rh['ap'], rh['epg'], 'DC-HAM')
        if not lt:
            t.step(False, 'Multi-Site', 'EPG %s steckt in keinem Template, das auf die lokale Site deployt ist' % epg)
            return False
        if not rt:
            t.step(False, 'Multi-Site: DC-HAM', 'In DC-HAM ist die EPG %s/%s nicht deployt - %s ist dort nicht gelernt' % (rh['ap'], rh['epg'], rh['name']))
            return False
        t.step(True, 'Ziel %s in Site DC-HAM' % rh['name'], 'EPG %s (Template %s), gelernt in DC-HAM' % (rh['epg'], rt['name']))
        bdl = next((b for b in lt.get('bds', []) if b['name'] == le['bd']), {})
        dst_ip = ipaddress.ip_interface(rh['ip']).ip
        same_subnet = dst_ip in ipaddress.ip_interface(sh['ip']).network
        if same_subnet:
            if not bdl.get('l2stretch'):
                t.step(False, 'Multi-Site: Layer 2', 'Gleiches Subnetz, aber BD %s ist nicht L2-gestreckt (L2 Stretch im Template)' % le['bd'])
                return False
            if self.A(shs['bd']).get('arpFlood') == 'yes' and not bdl.get('bum'):
                t.step(False, 'Multi-Site: BUM', 'ARP Flooding im BD, aber Intersite BUM Traffic ist aus - der ARP-Request erreicht DC-HAM nicht')
                return False
        if not (epg == rh['epg'] and ap == rh['ap']):
            allowed = None
            for c in lt.get('contracts', []) + [x for x in rt.get('contracts', []) if x not in lt.get('contracts', [])]:
                cons = c['name'] in le.get('cons', []) and c['name'] in re_.get('prov', [])
                prov = c['name'] in le.get('prov', []) and c['name'] in re_.get('cons', [])
                if (cons or prov) and _filter_ok(c.get('filter'), proto, port):
                    allowed = c
                    break
            if not allowed:
                t.step(False, 'Multi-Site: Policy', 'Kein Contract im Template zwischen %s und %s, der %s%s erlaubt' % (
                    epg, rh['epg'], proto, '/%s' % port if port else ''))
                return False
            t.step(True, 'Multi-Site: Policy', 'Contract %s aus dem Template (Shadow EPG %s in der lokalen Site, %s in DC-HAM)' % (
                allowed['name'], rh['epg'], epg))
        t.step(True, 'Multi-Site: VXLAN über das ISN', 'Spine (Overlay Unicast TEP %s) -> ISN -> DC-HAM (%s), VNID und pcTag werden auf den '
               'Spines übersetzt (Namespace Normalization)' % (self.ndo()['infra']['ucastTep'], self.ndo()['remote']['ucastTep']))
        return True


# ---------------------------------------------------------------------- NDO-Aktionen (Server)
def ndo_op(S, b):
    from . import aaa
    n = S.sim.get('ndo')
    if not n:
        raise AciError(400, 'Kein NDO in dieser Umgebung - Lab 31 laden')
    op = b.get('op')
    if op == 'onboard':
        loc = n['sites']['local']
        try:
            user, roles, _ = aaa.authenticate(S, b.get('user', ''), b.get('pwd', ''))
            if not aaa.is_admin(roles):
                raise AciError(401, 'Benutzer %s ist kein Admin in der Domain all' % user)
            sid = str(b.get('siteId') or '')
            if not sid.isdigit() or not 1 <= int(sid) <= 1000 or sid == n['sites']['DC-HAM']['siteId']:
                raise AciError(400, 'Site ID 1-1000, eindeutig (DC-HAM hat %s)' % n['sites']['DC-HAM']['siteId'])
            loc.update({'onboarded': True, 'user': user, 'siteId': sid, 'error': ''})
        except AciError as ex:
            loc.update({'onboarded': False, 'error': ex.text})
            raise
    elif op == 'infra':
        o = b.get('infra') or {}
        sp = []
        for x in o.get('spines', []):
            if not x.get('node'):
                continue
            try:
                ipaddress.ip_interface(x['ip'])
                if x.get('evpnRid'):
                    ipaddress.ip_address(x['evpnRid'])
            except (ValueError, KeyError):
                raise AciError(400, 'Spine %s: IP mit Maske und BGP-EVPN Router-ID als IP-Adresse angeben' % x.get('node'))
            sp.append({'node': int(x['node']), 'port': x.get('port') or 'eth1/31', 'ip': x['ip'], 'evpnRid': x.get('evpnRid', '')})
        n['infra'].update({'area': o.get('area') or '0.0.0.0', 'ucastTep': o.get('ucastTep', ''), 'peering': o.get('peering', 'full-mesh'),
                           'spines': sp, 'deployed': False})
    elif op == 'deployInfra':
        if not n['sites']['local']['onboarded']:
            raise AciError(400, 'Zuerst den lokalen APIC onboarden')
        inf = n['infra']
        if not inf['spines']:
            raise AciError(400, 'Keine Spines in der Infra-Konfiguration')
        body = {'fvTenant': {'attributes': {}, 'children': [
            {'l3extOut': {'attributes': {'name': 'intersite', 'annotation': ANNOT}, 'children': [
                {'l3extRsEctx': {'attributes': {'tnFvCtxName': 'overlay-1'}}}, {'ospfExtP': {'attributes': {'areaId': inf['area']}}},
                {'bgpExtP': {'attributes': {}}},
                {'l3extLNodeP': {'attributes': {'name': 'spines'}, 'children':
                    [{'l3extRsNodeL3OutAtt': {'attributes': {'tDn': 'topology/pod-1/node-%d' % x['node'], 'rtrId': x['evpnRid'] or '%d.%d.%d.%d' % ((x['node'],) * 4)}}}
                     for x in inf['spines']] +
                    [{'l3extLIfP': {'attributes': {'name': 'isn-%d' % x['node']}, 'children': [
                        {'ospfIfP': {'attributes': {}}},
                        {'l3extRsPathL3OutAtt': {'attributes': {'tDn': 'topology/pod-1/paths-%d/pathep-[%s]' % (x['node'], x['port']),
                                                                'ifInstT': 'sub-interface', 'encap': 'vlan-4', 'addr': x['ip']}}}]}} for x in inf['spines']]}}]}},
            {'fabricExtConnP': {'attributes': {'id': '1', 'siteId': n['sites']['local']['siteId'], 'name': 'Multisite', 'annotation': ANNOT}}}]}}
        mit_post(S.store, 'uni/tn-infra', body)
        inf['deployed'] = True
        S.audit('ndo', [{'dn': 'uni/tn-infra/out-intersite', 'cls': 'l3extOut', 'ind': 'modification', 'changes': {'deploy': ('', 'NDO Infra')}}])
    elif op == 'template':
        t = b.get('template') or {}
        if not re.match(r'^[A-Za-z0-9_.-]{1,64}$', t.get('name', '')) or not re.match(r'^[A-Za-z0-9_.-]{1,64}$', t.get('tenant', '')):
            raise AciError(400, 'Template und Tenant brauchen gueltige Namen')
        clean = {'name': t['name'], 'tenant': t['tenant'], 'sites': [s for s in t.get('sites', []) if s in ('local', 'DC-HAM')],
                 'vrfs': [v for v in t.get('vrfs', []) if v], 'bds': t.get('bds', []), 'aps': t.get('aps', []), 'contracts': t.get('contracts', []),
                 'deployed': {}}
        n['templates'] = [x for x in n['templates'] if x['name'] != (b.get('old') or t['name'])] + [clean]
    elif op == 'deleteTemplate':
        n['templates'] = [x for x in n['templates'] if x['name'] != b.get('name')]
    elif op == 'deploy':
        t = next((x for x in n['templates'] if x['name'] == b.get('name')), None)
        if not t:
            raise AciError(404, 'Template %s nicht gefunden' % b.get('name'))
        if 'local' in t['sites']:
            if not n['sites']['local']['onboarded']:
                raise AciError(400, 'Der lokale APIC ist nicht onboardet')
            mit_post(S.store, 'uni', _tenant_body(t))
            S.audit('ndo', [{'dn': 'uni/tn-' + t['tenant'], 'cls': 'fvTenant', 'ind': 'modification', 'changes': {'deploy': ('', 'NDO Template ' + t['name'])}}])
        t['deployed'] = {s: now_ts() for s in t['sites']}
    else:
        raise AciError(400, 'Unbekannte NDO-Aktion')


def _tenant_body(t):
    A = {'annotation': ANNOT}
    kids = [{'fvCtx': {'attributes': dict(A, name=v)}} for v in t['vrfs']]
    for bd in t['bds']:
        kids.append({'fvBD': {'attributes': dict(A, name=bd['name']), 'children': [
            {'fvRsCtx': {'attributes': {'tnFvCtxName': bd.get('vrf', '')}}}] + ([{'fvSubnet': {'attributes': {'ip': bd['subnet'], 'scope': 'private'}}}]
                                                                             if bd.get('subnet') else [])}})
    flts = set()
    for c in t['contracts']:
        subs = []
        for part in [p.strip() for p in (c.get('filter') or 'any').split(',') if p.strip()]:
            if part in ('any', 'default'):
                subs.append('default')
            elif part == 'icmp':
                subs.append('icmp')
            else:
                m = re.match(r'^(tcp|udp)/(\d+)$', part)
                if m:
                    fn = 'ndo-%s-%s' % m.groups()
                    flts.add((fn, m.group(1), m.group(2)))
                    subs.append(fn)
        kids.append({'vzBrCP': {'attributes': dict(A, name=c['name'], scope='context'), 'children': [
            {'vzSubj': {'attributes': {'name': 'subj', 'revFltPorts': 'yes'}, 'children': [
                {'vzRsSubjFiltAtt': {'attributes': {'tnVzFilterName': f}}} for f in subs]}}]}})
    for fn, pr, port in sorted(flts):
        kids.append({'vzFilter': {'attributes': dict(A, name=fn), 'children': [
            {'vzEntry': {'attributes': {'name': fn, 'etherT': 'ip', 'prot': pr, 'dFromPort': port, 'dToPort': port}}}]}})
    for ap in t['aps']:
        eps = []
        for e in ap.get('epgs', []):
            eps.append({'fvAEPg': {'attributes': dict(A, name=e['name']), 'children': [{'fvRsBd': {'attributes': {'tnFvBDName': e.get('bd', '')}}}] +
                       [{'fvRsCons': {'attributes': {'tnVzBrCPName': c}}} for c in e.get('cons', [])] +
                       [{'fvRsProv': {'attributes': {'tnVzBrCPName': c}}} for c in e.get('prov', [])]}})
        kids.append({'fvAp': {'attributes': dict(A, name=ap['name']), 'children': eps}})
    return {'fvTenant': {'attributes': dict(A, name=t['tenant']), 'children': kids}}
