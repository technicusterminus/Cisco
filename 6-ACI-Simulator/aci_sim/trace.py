"""Traffic-Test: verfolgt ein Paket (und die Antwort) durch die simulierte Fabric."""
import ipaddress

from .engine import ip_of, net_of, EPHEMERAL


class Trace:
    def __init__(self):
        self.steps = []
        self.ok = True

    def step(self, ok, title, detail=''):
        self.steps.append({'ok': ok, 'title': title, 'detail': detail})
        if ok is False:
            self.ok = False
        return ok is not False

    def result(self, summary=None):
        if summary is None:
            summary = 'Erfolgreich: Anfrage und Antwort kommen an.' if self.ok else \
                'Fehlgeschlagen: siehe ersten roten Schritt.'
        return {'ok': self.ok, 'summary': summary, 'steps': self.steps}


def _host(sim, name):
    return next((h for h in sim.get('hosts', []) if h['name'] == name), None)


def _router(sim, name):
    return next((r for r in sim.get('routers', []) if r['name'] == name), None)


def _resolve(eng, sim, x):
    x = (x or '').strip()
    h = _host(sim, x)
    if h:
        return {'kind': 'host', 'h': h, 'ip': ip_of(h['ip'])}
    r = _router(sim, x)
    if r:
        return {'kind': 'router', 'r': r, 'ip': ip_of(r['ip'])}
    try:
        ip = ipaddress.ip_address(x)
    except ValueError:
        return None
    for h in sim.get('hosts', []):
        if ip_of(h['ip']) == ip:
            return {'kind': 'host', 'h': h, 'ip': ip}
    for r in sim.get('routers', []):
        if ip_of(r['ip']) == ip:
            return {'kind': 'router', 'r': r, 'ip': ip}
    for bd in eng.store.by_class('fvBD'):
        for s in eng.bd_subnets(bd):
            if s['gw'] == str(ip):
                return {'kind': 'gw', 'bd': bd, 'ip': ip}
    return {'kind': 'ext', 'ip': ip}


def _lpm(routes, ip):
    best = None
    for rt in routes:
        try:
            n = ipaddress.ip_network(rt['prefix'], strict=False)
        except ValueError:
            continue
        if ip in n and (best is None or n.prefixlen > best[0].prefixlen or
                        (n.prefixlen == best[0].prefixlen and rt.get('pref', 0) < best[1].get('pref', 0))):
            best = (n, rt)
    return best[1] if best else None


def _classify_ext(eng, vrf, ip):
    best = None
    for n, inst in eng.ext_class.get(vrf, []):
        if ip in n and (best is None or n.prefixlen > best[0].prefixlen):
            best = (n, inst)
    return best


def _host_checks(eng, t, ep, role):
    h = ep['h']
    hs = eng.hosts.get(h['name'])
    if not hs or not hs['learned']:
        reasons = (hs or {}).get('reasons') or ['Host ist mit keinem aktiven Leaf verbunden']
        t.step(False, '%s %s: Endpoint nicht gelernt' % (role, h['name']), '; '.join(reasons))
        return None
    c = eng.cls[hs['epg']]
    t.step(True, '%s %s gelernt in EPG %s' % (role, h['name'], eng.short(hs['epg'])),
           'MAC %s, %s, %s, BD %s, VRF %s' % (h['mac'].upper(), hs['encap'], eng.path_label(hs['path']),
                                              eng.short(hs['bd']), eng.short(hs['vrf'])))
    return hs, c


def _gw_ok(eng, t, h, hs, who):
    bd = eng.A(hs['bd'])
    if bd['unicastRoute'] != 'yes':
        t.step(False, 'Gateway von %s' % who, 'Unicast Routing ist im BD %s ausgeschaltet - die ACI routet nicht'
               % eng.short(hs['bd']))
        return False
    gws = [s['gw'] for s in eng.bd_subnets(hs['bd']) + eng.bd_subnets(hs['epg'])]
    if not gws:
        t.step(False, 'Gateway von %s' % who, 'Im BD %s ist kein Subnetz (Gateway-IP) konfiguriert'
               % eng.short(hs['bd']))
        return False
    if h.get('gw') not in gws:
        t.step(False, 'Gateway von %s' % who, 'Host nutzt Gateway %s, die ACI bietet im BD %s: %s'
               % (h.get('gw') or '(keins)', eng.short(hs['bd']), ', '.join(gws)))
        return False
    if not hs['ipLearned']:
        t.step(False, 'IP-Learning fuer %s' % who, '; '.join(r for r in hs['reasons'] if 'IP' in r))
        return False
    t.step(True, 'Gateway %s (Pervasive Gateway im BD %s)' % (h['gw'], eng.short(hs['bd'])))
    return True


def _policy(eng, t, s, d, proto, port, label_s, label_d):
    dport = port if proto in ('tcp', 'udp') else None
    act, why = eng.packet(s, d, proto, EPHEMERAL if dport else None, dport, 'syn')
    t.step(act == 'permit', 'Policy Anfrage %s -> %s (%s%s)' % (label_s, label_d, proto,
                                                            '/%d' % port if dport else ''), why)
    if act != 'permit':
        return False
    act, why = eng.packet(d, s, proto, dport, EPHEMERAL if dport else None, 'ack')
    t.step(act == 'permit', 'Policy Antwort %s -> %s' % (label_d, label_s), why)
    return act == 'permit'


def run(eng, sim, src, dst, proto='icmp', port=0):
    t = Trace()
    proto = proto if proto in ('icmp', 'tcp', 'udp') else 'icmp'
    port = int(port or 0)
    if proto in ('tcp', 'udp') and not port:
        return {'ok': False, 'summary': 'Fuer TCP/UDP bitte einen Ziel-Port angeben.', 'steps': []}
    S = _resolve(eng, sim, src)
    D = _resolve(eng, sim, dst)
    if S is None or S['kind'] not in ('host', 'router'):
        return {'ok': False, 'summary': 'Quelle muss ein simulierter Host oder externer Router sein.', 'steps': []}
    if D is None:
        return {'ok': False, 'summary': 'Ziel unbekannt: Hostname, Routername oder IP-Adresse angeben.', 'steps': []}

    if S['kind'] == 'router':
        return _from_router(eng, sim, t, S, D, proto, port)

    r = _host_checks(eng, t, S, 'Quelle')
    if not r:
        return t.result()
    shs, sc = r
    sh = S['h']
    snet = net_of(sh['ip'])

    if D['kind'] == 'host':
        r = _host_checks(eng, t, D, 'Ziel')
        if not r:
            return t.result()
        dhs, dc = r
        dh = D['h']
        if D['ip'] in snet:
            if shs['bd'] != dhs['bd']:
                t.step(False, 'Layer 2', 'Ziel liegt im selben IP-Subnetz, aber in einer anderen Bridge Domain '
                       '(%s vs. %s) - ARP erreicht es nicht' % (eng.short(shs['bd']), eng.short(dhs['bd'])))
                return t.result()
            bd = eng.A(shs['bd'])
            if bd['unicastRoute'] == 'no' and bd['arpFlood'] == 'no':
                t.step(False, 'ARP', 'Unicast Routing und ARP Flooding sind im BD aus - die ACI kennt die Ziel-IP '
                       'nicht und flutet den ARP-Request nicht')
                return t.result()
            if not dhs['ipLearned'] and bd['arpFlood'] == 'no':
                t.step(False, 'ARP', 'Ziel-IP ist nicht gelernt und ARP Flooding ist aus')
                return t.result()
            t.step(True, 'ARP aufgeloest', 'ARP Flooding' if bd['arpFlood'] == 'yes' else
                   'ARP gezielt an den bekannten Endpoint (kein Flooding)')
            fwd = 'lokal auf %s' % '/'.join(eng.nodes[n]['name'] for n in shs['nodes']) \
                if set(shs['nodes']) & set(dhs['nodes']) else \
                'VXLAN von %s nach %s' % ('/'.join(eng.nodes[n]['name'] for n in shs['nodes']),
                                          '/'.join(eng.nodes[n]['name'] for n in dhs['nodes']))
            t.step(True, 'Layer-2-Forwarding in BD %s' % eng.short(shs['bd']), fwd)
        else:
            if not _gw_ok(eng, t, sh, shs, 'Quelle'):
                return t.result()
            if shs['vrf'] != dhs['vrf']:
                t.step(False, 'Routing', 'Ziel liegt in VRF %s, Quelle in VRF %s - Route Leaking (Shared Services) '
                       'simuliert dieses Tool nicht' % (eng.short(dhs['vrf']), eng.short(shs['vrf'])))
                return t.result()
            if not any(D['ip'] in s['net'] for s in eng.bd_subnets(dhs['bd']) + eng.bd_subnets(dhs['epg'])):
                t.step(False, 'Routing', 'Ziel-IP %s liegt in keinem Subnetz des BD %s' % (D['ip'], eng.short(dhs['bd'])))
                return t.result()
            t.step(True, 'Routing in VRF %s' % eng.short(shs['vrf']),
                   '%s -> %s (Pervasive Route, Ziel-Leaf %s)' % (snet, net_of(dh['ip']),
                                                              '/'.join(eng.nodes[n]['name'] for n in dhs['nodes'])))
            if not _gw_ok(eng, t, dh, dhs, 'Ziel (fuer die Antwort)'):
                return t.result()
        if not _policy(eng, t, sc, dc, proto, port, sh['name'], dh['name']):
            return t.result()
        return t.result()

    if D['kind'] == 'gw':
        if proto != 'icmp':
            t.step(False, 'Gateway', 'Das Pervasive Gateway beantwortet nur ICMP')
            return t.result()
        dvrf = (eng.A(D['bd'] + '/rsctx') or {}).get('tDn')
        if D['bd'] == shs['bd']:
            if eng.A(shs['bd'])['unicastRoute'] != 'yes':
                t.step(False, 'Gateway', 'Unicast Routing ist im BD %s aus' % eng.short(shs['bd']))
                return t.result()
        else:
            if not _gw_ok(eng, t, sh, shs, 'Quelle'):
                return t.result()
            if dvrf != shs['vrf']:
                t.step(False, 'Gateway', 'Gateway %s gehoert zu einem anderen VRF' % D['ip'])
                return t.result()
        t.step(True, 'Pervasive Gateway %s antwortet' % D['ip'], 'BD %s' % eng.short(D['bd']))
        return t.result()

    # Ziel extern (Router-IP oder Netz hinter einem Router)
    if not _gw_ok(eng, t, sh, shs, 'Quelle'):
        return t.result()
    vrf = shs['vrf']
    best = None
    for leaf in shs['nodes']:
        rt = _lpm(eng.routes.get((vrf, leaf), []), D['ip'])
        if rt:
            best = (leaf, rt)
            break
    if not best:
        hint = ''
        border = [n for (v, n), rts in eng.routes.items() if v == vrf and _lpm(rts, D['ip'])]
        if border and not eng.mpbgp_ok:
            hint = ' Der Border Leaf %s kennt die Route, aber ohne MP-BGP (BGP Route Reflector Policy mit ' \
                   'Fabric-AS und Spine als Route Reflector) wird sie nicht an andere Leafs verteilt.' % \
                   ', '.join(eng.nodes[n]['name'] for n in border)
        elif not border:
            hint = ' Auch kein Border Leaf hat eine Route (L3Out, Nachbarschaft und Static Routes pruefen).'
        t.step(False, 'Routing auf %s' % '/'.join(eng.nodes[n]['name'] for n in shs['nodes']),
               'Keine Route zu %s in VRF %s.%s' % (D['ip'], eng.short(vrf), hint))
        return t.result()
    leaf, rt = best
    if rt['proto'] == 'bgp' and rt.get('border'):
        t.step(True, 'Route auf %s' % eng.nodes[leaf]['name'],
               '%s via %s (Border Leaf %s, per MP-BGP gelernt)' % (rt['prefix'], rt['nh'],
                                                                 eng.nodes[rt['border']]['name']))
        bl = rt['border']
        brt = _lpm([x for x in eng.routes.get((vrf, bl), []) if not x.get('border')], D['ip'])
    else:
        bl, brt = leaf, rt
    if not brt:
        t.step(False, 'Route auf Border Leaf', 'Border Leaf hat keine Route mehr')
        return t.result()
    t.step(True, 'Route auf Border Leaf %s' % eng.nodes[bl]['name'],
           '%s via %s %s (%s)' % (brt['prefix'], brt['nh'], brt['via'], brt['proto']))
    rname = brt.get('router')
    if brt['proto'] == 'direct':
        rname = next((r['name'] for r in sim.get('routers', []) if ip_of(r['ip']) == D['ip']), None)
        if not rname:
            t.step(False, 'Ziel', '%s ist im Transfernetz, aber dort antwortet kein Router' % D['ip'])
            return t.result()
    cl = _classify_ext(eng, vrf, D['ip'])
    if not cl:
        t.step(False, 'Klassifizierung', 'Ziel-IP %s passt zu keinem External EPG Subnetz ("External Subnets for '
               'the External EPG") in VRF %s' % (D['ip'], eng.short(vrf)))
        return t.result()
    t.step(True, 'Klassifizierung', '%s gehoert zum External EPG %s (Subnetz %s)' % (D['ip'], eng.short(cl[1]), cl[0]))
    dc = eng.cls[cl[1]]
    if not _policy(eng, t, sc, dc, proto, port, sh['name'], str(D['ip'])):
        return t.result()
    r = _router(sim, rname)
    rs = eng.routers.get(rname, {})
    if D['kind'] != 'router' and not any(D['ip'] in ipaddress.ip_network(n, strict=False)
                                         for n in r.get('networks', [])):
        t.step(False, 'Externer Router %s' % rname, 'Der Router kennt das Ziel %s nicht' % D['ip'])
        return t.result()
    back = [p for p in rs.get('learned', []) if shs and ip_of(sh['ip']) in ipaddress.ip_network(p, strict=False)]
    if not back:
        t.step(False, 'Rueckweg ueber %s' % rname,
               'Der externe Router hat keine Route zurueck nach %s. Bei OSPF/BGP muss das BD-Subnetz "Advertised '
               'Externally" sein, der BD mit dem L3Out verknuepft und der BD auf dem Border Leaf aktiv sein '
               '(z. B. durch den Contract zum External EPG).' % snet)
        return t.result()
    t.step(True, 'Rueckweg ueber %s' % rname, 'Router kennt %s (%s)' % (back[0], rs.get('adj')))
    return t.result()


def _from_router(eng, sim, t, S, D, proto, port):
    r = S['r']
    rs = eng.routers.get(r['name'], {})
    if not rs.get('link'):
        t.step(False, 'Router %s' % r['name'], '; '.join(rs.get('reasons') or ['Link nicht aktiv']))
        return t.result()
    iface = rs['iface']
    vrf = eng.outs[iface['out']]['vrf']
    t.step(True, 'Router %s verbunden' % r['name'], '%s via %s, Nachbarschaft: %s' % (
        eng.nodes[iface['nid']]['name'], eng.if_name(iface), rs.get('adj')))
    if D['kind'] != 'host':
        t.step(False, 'Ziel', 'Vom externen Router aus kann nur ein simulierter Host getestet werden')
        return t.result()
    dhs_c = _host_checks(eng, t, D, 'Ziel')
    if not dhs_c:
        return t.result()
    dhs, dc = dhs_c
    dh = D['h']
    known = [p for p in rs.get('learned', []) if D['ip'] in ipaddress.ip_network(p, strict=False)]
    if not known:
        t.step(False, 'Routing auf %s' % r['name'], 'Router hat keine Route zu %s (BD-Subnetz wird nicht '
               'angekuendigt)' % net_of(dh['ip']))
        return t.result()
    t.step(True, 'Routing auf %s' % r['name'], '%s via ACI' % known[0])
    if dhs['vrf'] != vrf:
        t.step(False, 'VRF', 'Host liegt in VRF %s, das L3Out in VRF %s' % (eng.short(dhs['vrf']), eng.short(vrf)))
        return t.result()
    src_ip = S['ip']
    cl = _classify_ext(eng, vrf, src_ip)
    if not cl:
        t.step(False, 'Klassifizierung', 'Quell-IP %s passt zu keinem External EPG Subnetz' % src_ip)
        return t.result()
    t.step(True, 'Klassifizierung', 'Quelle %s gehoert zum External EPG %s' % (src_ip, eng.short(cl[1])))
    sc = eng.cls[cl[1]]
    if not _policy(eng, t, sc, dc, proto, port, r['name'], dh['name']):
        return t.result()
    if not _gw_ok(eng, t, dh, dhs, 'Ziel (fuer die Antwort)'):
        return t.result()
    leaf = dhs['nodes'][0]
    rt = _lpm(eng.routes.get((vrf, leaf), []), src_ip)
    if not rt:
        t.step(False, 'Rueckweg auf %s' % eng.nodes[leaf]['name'], 'Keine Route zurueck zu %s%s' % (
            src_ip, '' if eng.mpbgp_ok else ' (MP-BGP Route Reflector fehlt?)'))
        return t.result()
    t.step(True, 'Rueckweg auf %s' % eng.nodes[leaf]['name'], '%s via %s (%s)' % (rt['prefix'], rt['nh'], rt['proto']))
    return t.result()
