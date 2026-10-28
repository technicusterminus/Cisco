"""Traffic-Test: verfolgt ein Paket (und die Antwort) durch die simulierte Fabric."""
import ipaddress

from .engine import ip_of, net_of, EPHEMERAL


# Reason Codes sind simulator-spezifisch (keine Cisco-Codes). Je Code: Diagnose-Ebene und naechster Pruefschritt.
REASONS = {
    'ALLOWED': ('ok', 'Anfrage und Antwort kommen an.'),
    'INPUT_INVALID': ('input', 'Quelle und Ziel als simulierten Host, Router oder IP-Adresse angeben.'),
    'INPUT_PORT_MISSING': ('input', 'Fuer TCP/UDP einen Ziel-Port angeben.'),
    'EP_NOT_LEARNED': ('endpoint', 'Access-Kette pruefen: Port, VLAN im Pool, Domain an EPG und AAEP, Static Path mit passender Encap '
                       '(Endpoint Explorer, Faults F0467).'),
    'L2_LOOP': ('l2', 'Schleife beseitigen: MCP und Endpoint Loop Protection pruefen.'),
    'L2_DIFFERENT_BD': ('l2', 'Gleiches Subnetz in verschiedenen BDs: Adressplan oder BD-Zuordnung der EPGs pruefen.'),
    'ARP_UNRESOLVED': ('l2', 'ARP Flooding oder Unicast Routing mit BD-Subnetz pruefen.'),
    'GATEWAY': ('l3', 'BD-Subnetz (Gateway-IP), Unicast Routing und Default Gateway des Hosts pruefen.'),
    'IP_NOT_LEARNED': ('l3', 'Liegt die Host-IP in einem BD-Subnetz? Ist Unicast Routing an?'),
    'ROUTE_LEAK_MISSING': ('l3', 'Shared Services: Contract-Scope, Provider-Subnetz an der EPG und Consumer-Subnetz "Shared between VRFs".'),
    'NO_ROUTE': ('l3', 'Ziel-Subnetz im BD bzw. Route ueber den L3Out pruefen (show ip route vrf ...).'),
    'FABRIC_PATH_DOWN': ('fabric', 'Spine-Zustand, Uplinks bzw. IPN/WAN pruefen (Fabric > Inventory).'),
    'POLICY_IMPLICIT_DENY': ('policy', 'Contract zwischen den EPGs anlegen: Consumer an der Quelle, Provider am Ziel, Filter fuer genau '
                             'diesen Dienst (show zoning-rule).'),
    'POLICY_DENY_FILTER': ('policy', 'Ein Deny-Filter im Contract trifft den Verkehr - Subject und Filter-Aktion pruefen.'),
    'POLICY_TABOO': ('policy', 'Ein Taboo Contract an der Ziel-EPG sperrt den Verkehr.'),
    'POLICY_INTRA_EPG_ISOLATION': ('policy', 'Intra-EPG-Isolation an der EPG ist aktiv.'),
    'POLICY_ESG_EPG': ('policy', 'ESG und EPG koennen keinen Contract miteinander haben.'),
    'POLICY_REPLY_DENY': ('policy', 'Die Antwort passt auf keine Regel: Reverse Filter Ports am Subject pruefen.'),
    'POLICY_UNSUPPORTED': ('policy', 'Die Konfiguration nutzt ein Feature, das der Simulator nicht auswertet (siehe Referenzprofil).'),
    'SERVICE_GRAPH': ('service-graph', 'Service Graph, PBR Policy und Firewall-Regelwerk pruefen.'),
    'SERVICE_UNAVAILABLE': ('service', 'Das Netz laesst den Verkehr durch, aber am Ziel laeuft kein Dienst auf diesem Port.'),
    'EXT_CLASSIFICATION': ('external', 'External EPG mit passendem Subnetz ("External Subnets for the External EPG") anlegen.'),
    'EXT_ROUTER': ('external', 'Externer Router: kennt er das Ziel-Netz?'),
    'EXT_NO_RETURN_ROUTE': ('external', 'Rueckweg: BD-Subnetz "Advertised Externally", BD mit L3Out verknuepfen, Route am Router pruefen.'),
    'REMOTE_SITE': ('fabric', 'Multi-Site/Remote-Pfad pruefen (ISN, Stretch, Contracts).'),
    'OTHER': ('other', 'Den ersten fehlgeschlagenen Schritt im Detail ansehen.'),
}
UNRESOLVED = {'INPUT_INVALID', 'INPUT_PORT_MISSING', 'POLICY_UNSUPPORTED'}
POLICY_CODES = {'implicit-deny': 'POLICY_IMPLICIT_DENY', 'contract-deny': 'POLICY_DENY_FILTER', 'taboo': 'POLICY_TABOO',
                'intra-epg-isolation': 'POLICY_INTRA_EPG_ISOLATION', 'esg-epg': 'POLICY_ESG_EPG', 'unsupported': 'POLICY_UNSUPPORTED'}
_PREFIX = [('Layer 2', 'L2_DIFFERENT_BD'), ('ARP', 'ARP_UNRESOLVED'), ('Gateway', 'GATEWAY'), ('IP-Learning', 'IP_NOT_LEARNED'),
           ('Route Leaking', 'ROUTE_LEAK_MISSING'), ('Routing', 'NO_ROUTE'), ('Route auf', 'NO_ROUTE'), ('Fabric', 'FABRIC_PATH_DOWN'),
           ('Multi-Pod', 'FABRIC_PATH_DOWN'), ('Remote Leaf', 'FABRIC_PATH_DOWN'), ('Service Graph', 'SERVICE_GRAPH'),
           ('PBR', 'SERVICE_GRAPH'), ('Firewall', 'SERVICE_GRAPH'), ('Rueckweg per PBR', 'SERVICE_GRAPH'),
           ('Klassifizierung', 'EXT_CLASSIFICATION'), ('Externer Router', 'EXT_ROUTER'), ('Rueckweg', 'EXT_NO_RETURN_ROUTE'),
           ('Ziel', 'EXT_ROUTER')]


def infer_code(title):
    for pre, code in _PREFIX:
        if title.startswith(pre):
            return code
    return 'OTHER'


class Trace:
    def __init__(self):
        self.steps = []
        self.ok = True
        self.woken = []
        self.refs = []
        self.policy = []

    def ref(self, *dns):
        for dn in dns:
            if dn and dn not in self.refs:
                self.refs.append(dn)

    def step(self, ok, title, detail='', code=None, refs=()):
        st = {'ok': ok, 'title': title, 'detail': detail}
        if ok is False:
            st['code'] = code or infer_code(title)
        if refs:
            st['refs'] = [r for r in refs if r]
            self.ref(*refs)
        self.steps.append(st)
        if ok is False:
            self.ok = False
        return ok is not False

    def result(self, summary=None):
        bad = next(((i, s) for i, s in enumerate(self.steps) if s['ok'] is False), None)
        code = bad[1]['code'] if bad else 'ALLOWED'
        verdict = 'UNRESOLVED' if code in UNRESOLVED else ('ALLOW' if self.ok else 'DROP')
        layer, hint = REASONS.get(code, REASONS['OTHER'])
        if summary is None:
            summary = {'ALLOW': 'Erfolgreich: Anfrage und Antwort kommen an.',
                       'DROP': 'Blockiert bei "%s".' % (bad[1]['title'] if bad else ''),
                       'UNRESOLVED': 'Nicht bewertbar: %s' % (bad[1]['detail'] if bad else '')}[verdict]
        return {'ok': self.ok and verdict == 'ALLOW', 'verdict': verdict, 'reason': code, 'summary': summary,
                'explanation': (bad[1]['title'] + (': ' + bad[1]['detail'] if bad[1]['detail'] else '')) if bad else summary,
                'failedAt': {'step': bad[0] + 1, 'title': bad[1]['title'], 'layer': layer} if bad else None,
                'hint': hint if bad else None, 'policy': self.policy, 'refs': self.refs,
                'steps': self.steps, 'woken': self.woken if self.ok else []}


def unresolved(code, text):
    t = Trace()
    t.step(False, 'Eingabe', text, code=code)
    return t.result(text)


def _hosts(eng, sim):
    return eng.all_hosts() if hasattr(eng, 'all_hosts') else sim.get('hosts', [])


def _host(eng, sim, name):
    return next((h for h in _hosts(eng, sim) if h['name'] == name), None)


def _router(sim, name):
    return next((r for r in sim.get('routers', []) if r['name'] == name), None)


def _resolve(eng, sim, x):
    x = (x or '').strip()
    h = _host(eng, sim, x)
    if h:
        return {'kind': 'host', 'h': h, 'ip': ip_of(h['ip'])}
    r = _router(sim, x)
    if r:
        return {'kind': 'router', 'r': r, 'ip': ip_of(r['ip'])}
    rh = eng.remote_host(x) if hasattr(eng, 'remote_host') else None
    if rh:
        return {'kind': 'site', 'rh': rh, 'ip': ip_of(rh['ip'])}
    try:
        ip = ipaddress.ip_address(x)
    except ValueError:
        return None
    for h in _hosts(eng, sim):
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
    if hs and hs.get('quiet'):
        if role == 'Quelle':
            t.woken.append(h['name'])
            t.step(None, 'Stiller Host %s sendet jetzt' % h['name'], 'Die Fabric lernt ihn mit dem ersten Paket')
        hs = dict(hs, learned=True, silent_dst=role != 'Quelle')
    if not hs or not hs['learned']:
        reasons = (hs or {}).get('reasons') or ['Host ist mit keinem aktiven Leaf verbunden']
        t.step(False, '%s %s: Endpoint nicht gelernt' % (role, h['name']), '; '.join(reasons), code='EP_NOT_LEARNED')
        return None
    if hs.get('storm'):
        t.step(False, '%s %s: Layer-2-Schleife im BD %s' % (role, h['name'], eng.short(hs['bd'])), hs['storm'], code='L2_LOOP')
        return None
    c = eng.cls[hs.get('esg') or hs['epg']]
    if hs.get('esg') or hs.get('base'):
        t.step(None, '%s %s: Klassifizierung' % (role, h['name']), ('uSeg EPG %s (Basis-EPG %s)' % (eng.short(hs['epg']), eng.short(hs['base']))
                                                                  if hs.get('base') else 'EPG %s' % eng.short(hs['epg'])) +
               (' -> ESG %s: fuer die Policy zaehlen jetzt die Contracts der ESG' % eng.short(hs['esg']) if hs.get('esg') else ''))
    if hs.get('silent_dst'):
        t.step(None, '%s %s ist ein stiller Host' % (role, h['name']), 'Noch nicht gelernt; erreichbar nur per ARP Flooding '
               'oder ARP Glean (Unicast Routing mit BD-Subnetz). Wartet in EPG %s, %s' % (eng.short(hs['epg']), eng.path_label(hs['path'])))
        return hs, c
    t.step(True, '%s %s gelernt in EPG %s' % (role, h['name'], eng.short(hs['epg'])),
           'MAC %s, %s, %s, BD %s, VRF %s' % (h['mac'].upper(), hs['encap'], eng.path_label(hs['path']),
                                              eng.short(hs['bd']), eng.short(hs['vrf'])),
           refs=(hs.get('esg') or hs['epg'], hs['bd'], hs['vrf']))
    return hs, c


def _shared_scope_ok(eng, brc, s, d):
    sc = eng.A(brc)['scope']
    return sc == 'global' or (sc == 'tenant' and s['tenant'] == d['tenant'])


def _contract_between(eng, s, d):
    """Contract zwischen zwei Klassen fuer Shared Services: (brc, provider, consumer) oder None."""
    for brc, rel in eng.contracts.items():
        if s['dn'] in rel['cons'] and d['dn'] in rel['prov']:
            return brc, d, s
        if s['dn'] in rel['prov'] and d['dn'] in rel['cons']:
            return brc, s, d
    return None


def _leak(eng, t, sc, dc, shs, dhs, sh, dh):
    r = _contract_between(eng, sc, dc)
    if not r:
        t.step(False, 'Route Leaking', 'Ziel liegt in VRF %s, Quelle in VRF %s. Zwischen VRFs leakt die ACI Routen nur mit '
               'einem Contract zwischen den EPGs (Scope Tenant oder Global)' % (eng.short(dhs['vrf']), eng.short(shs['vrf'])))
        return False
    brc, prov, cons = r
    if not _shared_scope_ok(eng, brc, sc, dc):
        t.step(False, 'Route Leaking', 'Contract %s hat Scope %s - fuer Verkehr zwischen VRFs braucht er Scope %s'
               % (eng.short(brc), eng.A(brc)['scope'], 'Tenant oder Global' if sc['tenant'] == dc['tenant'] else 'Global'))
        return False
    ph, phs = (dh, dhs) if prov is dc else (sh, shs)
    ch, chs = (sh, shs) if prov is dc else (dh, dhs)
    pip, cip = ip_of(ph['ip']), ip_of(ch['ip'])
    psub = [x for x in eng.epg_subnets(prov['dn']) if pip in x['net'] and 'shared' in x['scope'].split(',')]
    if not psub:
        t.step(False, 'Route Leaking', 'Am Provider (EPG %s) fehlt ein Subnetz mit Scope "Shared between VRFs" fuer %s. '
               'Bei Shared Services gehoert das Provider-Subnetz an die EPG.' % (eng.short(prov['dn']), pip))
        return False
    csub = [x for x in eng.bd_subnets(chs['bd']) + eng.epg_subnets(cons['dn']) if cip in x['net'] and 'shared' in x['scope'].split(',')]
    if not csub:
        t.step(False, 'Route Leaking', 'Am Consumer (BD %s) fehlt ein Subnetz mit Scope "Shared between VRFs" fuer %s'
               % (eng.short(chs['bd']), cip))
        return False
    t.step(True, 'Route Leaking', '%s wird in VRF %s und %s in VRF %s geleakt (Contract %s, Scope %s)' % (
        psub[0]['net'], eng.short(chs['vrf']), csub[0]['net'], eng.short(phs['vrf']), eng.short(brc), eng.A(brc)['scope']))
    return True


def _shared_l3out(eng, sc, ip):
    """Ziel hinter einem L3Out in einem anderen VRF (Shared L3Out)."""
    best = None
    for inst in eng.store.by_class('l3extInstP'):
        c = eng.cls.get(inst)
        if not c or c['vrf'] == sc['vrf'] or not c['vrf']:
            continue
        for sub in eng.kids(inst, 'l3extSubnet'):
            a = eng.A(sub)
            n = net_of(a['ip'])
            sco = a['scope'].split(',')
            if not n or ip not in n or 'shared-rtctrl' not in sco or 'shared-security' not in sco:
                continue
            r = _contract_between(eng, sc, c)
            if not r or not _shared_scope_ok(eng, r[0], sc, c):
                continue
            for (v, nid), rts in eng.routes.items():
                if v != c['vrf']:
                    continue
                rt = _lpm([x for x in rts if not x.get('border')], ip)
                if rt and (best is None or n.prefixlen > best['net'].prefixlen):
                    best = {'vrf': v, 'node': nid, 'route': rt, 'inst': inst, 'net': n}
    return best


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


def _decision(eng, t, phase):
    d = dict(getattr(eng, 'last_decision', None) or {})
    d['phase'] = phase
    t.policy.append(d)
    refs = [d.get(k) for k in ('contract', 'subject', 'filter', 'entry', 'taboo', 'epg', 'vrf')]
    return d, refs


def _service_available(t, host, proto, port, label):
    """Hoert am Ziel ein Dienst? Hosts ohne Dienstliste gelten als 'alle Ports offen' (dokumentierte Vereinfachung)."""
    if host is None:
        return True
    if proto == 'icmp':
        if host.get('icmp', True):
            return True
        t.step(False, 'Zieldienst auf %s' % label, 'Der Host beantwortet kein ICMP (Echo Reply abgeschaltet)', code='SERVICE_UNAVAILABLE')
        return False
    svc = host.get('services')
    if svc is None:
        t.step(None, 'Zieldienst auf %s nicht modelliert' % label, 'Host ohne Dienstliste: Der Simulator nimmt an, dass %s/%d offen ist'
               % (proto, port))
        return True
    if '%s/%d' % (proto, port) in [x.strip().lower() for x in svc]:
        t.step(True, 'Zieldienst %s/%d auf %s erreichbar' % (proto, port, label))
        return True
    t.step(False, 'Zieldienst auf %s' % label, 'Die Fabric laesst %s/%d durch, aber auf %s laeuft dort kein Dienst (offen: %s)'
           % (proto, port, label, ', '.join(svc) or 'keiner'), code='SERVICE_UNAVAILABLE')
    return False


def _policy(eng, t, s, d, proto, port, label_s, label_d, dst_host=None):
    dport = port if proto in ('tcp', 'udp') else None
    act, why = eng.packet(s, d, proto, EPHEMERAL if dport else None, dport, 'syn')
    dec, refs = _decision(eng, t, 'Anfrage')
    if act == 'permit':
        eng.count(s['dn'], 'txPkts')
        eng.count(d['dn'], 'rxPkts')
    else:
        eng.count(s['dn'], 'txPkts')
        eng.count(d['dn'], 'dropPkts')
    t.step(act == 'permit', 'Policy Anfrage %s -> %s (%s%s)' % (label_s, label_d, proto,
                                                            '/%d' % port if dport else ''), why,
           code=POLICY_CODES.get(dec.get('kind'), 'POLICY_IMPLICIT_DENY'), refs=refs)
    if act != 'permit':
        return False
    hit = getattr(eng, 'last_hit', None)
    g = getattr(eng, 'graphs', {}).get(hit[0]) if hit else None
    if g is not None and not _service(eng, t, g, hit[1], proto, port):
        return False
    if not _service_available(t, dst_host, proto, port, label_d):
        return False
    act, why = eng.packet(d, s, proto, dport, EPHEMERAL if dport else None, 'ack')
    dec, refs = _decision(eng, t, 'Antwort')
    eng.count(d['dn'], 'txPkts')
    eng.count(s['dn'], 'rxPkts' if act == 'permit' else 'dropPkts')
    t.step(act == 'permit', 'Policy Antwort %s -> %s' % (label_d, label_s), why,
           code='POLICY_UNSUPPORTED' if dec.get('kind') == 'unsupported' else 'POLICY_REPLY_DENY', refs=refs)
    return act == 'permit'


def _fw_allows(dev, proto, port):
    rules = [r.strip().lower() for r in dev.get('allow', ['any'])]
    if 'any' in rules:
        return True
    return proto in rules or ('%s/%s' % (proto, port)) in rules


def _service(eng, t, g, direction, proto, port):
    """Service Graph am Contract-Subject: Redirect zur Firewall und zurueck."""
    gname = eng.A(g['graph'])['name']
    if g['state'] != 'applied':
        t.step(False, 'Service Graph %s' % gname, 'Graph ist nicht gerendert: %s' % '; '.join(g['reasons']))
        return False
    if not g['redirect']:
        t.step(False, 'Service Graph %s' % gname, 'Function Node ohne Routing Mode "Redirect": Ohne PBR muessten die Hosts die '
               'Firewall als Gateway nutzen - Datacenter Prep simuliert Service Graphs mit PBR')
        return False
    legs = ('consumer', 'provider') if direction == 'c2p' else ('provider', 'consumer')
    first = g['conns'][legs[0]]
    dev = None
    for d in first['dests']:
        ep = next((h for h in eng.fw_hosts if str(ip_of(h['ip'])) == d['ip']), None)
        hs = eng.hosts.get(ep['name'], {}) if ep else {}
        if not ep:
            t.step(False, 'PBR %s' % eng.short(first['pol']), 'Redirect-Ziel %s gehoert zu keinem L4-L7-Geraet' % d['ip'])
            return False
        if not hs.get('learned') or hs.get('epg') != first['shadow']:
            t.step(False, 'PBR %s' % eng.short(first['pol']), 'Redirect-Ziel %s (%s) ist im Service-BD %s nicht gelernt: %s' % (
                d['ip'], ep['name'], eng.short(first['bd']), '; '.join(hs.get('reasons', [])) or 'Encap/Path des Cluster Interfaces pruefen'))
            return False
        if d['mac'] and d['mac'] != ep['mac'].upper():
            t.step(False, 'PBR %s' % eng.short(first['pol']), 'Redirect-Ziel %s: MAC in der PBR Policy (%s) passt nicht zur MAC der '
                   'Firewall (%s) - die ACI schreibt die falsche Ziel-MAC um, das Paket wird verworfen' % (d['ip'], d['mac'], ep['mac'].upper()))
            return False
        if not d['mac']:
            t.step(False, 'PBR %s' % eng.short(first['pol']), 'Redirect-Ziel %s hat keine MAC-Adresse (ohne IP-SLA-Tracking Pflicht)' % d['ip'])
            return False
        dev = next((x for x in eng.sim.get('devices', []) if x['name'] == ep['dev']), None)
        t.step(True, 'Redirect (%s -> %s)' % legs, 'PBR %s leitet zu %s (%s %s) um, Service-BD %s, vlan-%d' % (
            eng.short(first['pol']), ep['dev'], ep['devif'], d['ip'], eng.short(first['bd']), first['vlan']))
        break
    if dev is None:
        return False
    if not _fw_allows(dev, proto, port):
        t.step(False, 'Firewall %s' % dev['name'], 'Regelwerk der Firewall erlaubt %s%s nicht (erlaubt: %s)' % (
            proto, '/%s' % port if port else '', ', '.join(dev.get('allow', []))))
        return False
    t.step(True, 'Firewall %s' % dev['name'], 'Regel erlaubt %s%s, weiter ueber das %s-Interface' % (
        proto, '/%s' % port if port else '', legs[1]))
    second = g['conns'][legs[1]]
    out = next((h for h in eng.fw_hosts if h['dev'] == dev['name'] and eng.hosts.get(h['name'], {}).get('epg') == second['shadow']), None)
    if not out:
        t.step(False, 'Firewall %s' % dev['name'], 'Das %s-Interface der Firewall ist im Service-BD %s nicht gelernt' % (
            legs[1], eng.short(second['bd'])))
        return False
    back = next((d for d in second['dests'] if d['ip'] == str(ip_of(out['ip']))), None)
    if not back:
        t.step(False, 'Rueckweg per PBR', 'Die PBR Policy %s am %s-Connector zeigt nicht auf das %s-Interface der Firewall (%s) - '
               'die Antwort liefe an der Firewall vorbei (asymmetrisch) und wuerde verworfen' % (
                   eng.short(second['pol']), legs[1], legs[1], ip_of(out['ip'])))
        return False
    if back['mac'] != out['mac'].upper():
        t.step(False, 'Rueckweg per PBR', 'MAC in der PBR Policy %s (%s) passt nicht zur Firewall (%s)' % (
            eng.short(second['pol']), back['mac'] or '(leer)', out['mac'].upper()))
        return False
    t.step(True, 'Rueckweg per PBR', 'Antwort wird ueber %s (%s) zur Firewall umgeleitet - symmetrisch' % (
        eng.short(second['pol']), back['ip']))
    return True


def _spines(eng, t, a, b, flood=False):
    """Zwischen zwei Leafs braucht es einen aktiven Spine; zwischen Pods das IPN, zum Remote Leaf das WAN."""
    if set(a) & set(b):
        return True
    pods = lambda ns: {eng.pod_of.get(n, eng.pod) for n in ns}
    pa, pb = pods(a), pods(b)
    remote = [n for n in list(a) + list(b) if eng.nodes.get(n, {}).get('remote')]
    for n in remote:
        why = eng.remote_path(eng.nodes[n]['serial'])
        if why:
            t.step(False, 'Remote Leaf %s' % eng.nodes[n]['name'], why)
            return False
    if pa & pb:
        if any(n['role'] == 'spine' and n['state'] == 'active' and eng.pod_of.get(i, eng.pod) in pa & pb for i, n in eng.nodes.items()):
            if remote:
                t.step(True, 'Remote Leaf', 'VXLAN ueber das WAN zum Anycast-TEP der Spines in Pod %d' % sorted(pa & pb)[0])
            return True
        ups = [n['name'] for n in eng.nodes.values() if n['role'] == 'spine' and n.get('upgrading')]
        t.step(False, 'Fabric', 'Kein Spine ist aktiv%s - zwischen %s und %s gibt es keinen VXLAN-Pfad' % (
            ' (%s laden nach dem Firmware-Upgrade neu)' % ', '.join(ups) if ups else '',
            '/'.join(eng.nodes[n]['name'] for n in a), '/'.join(eng.nodes[n]['name'] for n in b)))
        return False
    p1, p2 = sorted(pa)[0], sorted(pb)[0]
    why = eng.interpod(p1, p2, flood)
    if why:
        t.step(False, 'Multi-Pod: Pod %d -> Pod %d' % (p1, p2), why)
        return False
    t.step(True, 'Multi-Pod: Pod %d -> Pod %d' % (p1, p2), 'VXLAN ueber das IPN (Spine -> IPN -> Spine), Endpoint per MP-BGP EVPN '
           'zwischen den Spines bekannt%s' % (', BUM ueber PIM Bidir' if flood else ''))
    return True


def run(eng, sim, src, dst, proto='icmp', port=0):
    t = Trace()
    proto = proto if proto in ('icmp', 'tcp', 'udp') else 'icmp'
    port = int(port or 0)
    if proto in ('tcp', 'udp') and not port:
        return unresolved('INPUT_PORT_MISSING', 'Fuer TCP/UDP bitte einen Ziel-Port angeben.')
    S = _resolve(eng, sim, src)
    D = _resolve(eng, sim, dst)
    if S is not None and S['kind'] == 'ext':
        r_ = next((x for x in sim.get('routers', []) if any(S['ip'] in ipaddress.ip_network(n, strict=False)
                                                             for n in x.get('networks', []))), None)
        if r_:
            S = {'kind': 'router', 'r': r_, 'ip': S['ip']}
    if S is None or S['kind'] not in ('host', 'router'):
        return unresolved('INPUT_INVALID', 'Quelle muss ein simulierter Host oder externer Router sein.')
    if D is None:
        return unresolved('INPUT_INVALID', 'Ziel unbekannt: Hostname, Routername oder IP-Adresse angeben.')

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
            if dhs.get('silent_dst'):
                glean = bd['unicastRoute'] == 'yes' and any(D['ip'] in x['net'] for x in eng.bd_subnets(dhs['bd']))
                if bd['arpFlood'] != 'yes' and not glean:
                    t.step(False, 'ARP', 'Das Ziel ist ein stiller Host: Die ACI kennt es nicht, ARP Flooding ist aus und '
                           'ohne Unicast Routing mit BD-Subnetz gibt es kein ARP Glean - der ARP-Request wird verworfen')
                    return t.result()
                t.step(True, 'ARP erreicht den stillen Host', 'ARP Flooding im BD' if bd['arpFlood'] == 'yes' else 'ARP Glean vom Pervasive Gateway')
                t.woken.append(dh['name'])
            elif not dhs['ipLearned'] and bd['arpFlood'] == 'no':
                t.step(False, 'ARP', 'Ziel-IP ist nicht gelernt und ARP Flooding ist aus')
                return t.result()
            t.step(True, 'ARP aufgeloest', 'ARP Flooding' if bd['arpFlood'] == 'yes' else
                   'ARP gezielt an den bekannten Endpoint (kein Flooding)')
            if not _spines(eng, t, shs['nodes'], dhs['nodes'], bd['arpFlood'] == 'yes'):
                return t.result()
            fwd = 'lokal auf %s' % '/'.join(eng.nodes[n]['name'] for n in shs['nodes']) \
                if set(shs['nodes']) & set(dhs['nodes']) else \
                'VXLAN von %s nach %s' % ('/'.join(eng.nodes[n]['name'] for n in shs['nodes']),
                                          '/'.join(eng.nodes[n]['name'] for n in dhs['nodes']))
            t.step(True, 'Layer-2-Forwarding in BD %s' % eng.short(shs['bd']), fwd)
        else:
            if not _gw_ok(eng, t, sh, shs, 'Quelle'):
                return t.result()
            if shs['vrf'] != dhs['vrf']:
                if not _leak(eng, t, sc, dc, shs, dhs, sh, dh):
                    return t.result()
            if not any(D['ip'] in s['net'] for s in eng.bd_subnets(dhs['bd']) + eng.bd_subnets(dhs['epg'])):
                t.step(False, 'Routing', 'Ziel-IP %s liegt in keinem Subnetz des BD %s' % (D['ip'], eng.short(dhs['bd'])))
                return t.result()
            if not _spines(eng, t, shs['nodes'], dhs['nodes']):
                return t.result()
            if dhs.get('silent_dst'):
                t.step(True, 'ARP Glean', 'Die ACI fragt den stillen Host per ARP vom Pervasive Gateway aus an')
                t.woken.append(dh['name'])
            t.step(True, 'Routing in VRF %s' % eng.short(shs['vrf']),
                   '%s -> %s (Pervasive Route, Ziel-Leaf %s)' % (snet, net_of(dh['ip']),
                                                              '/'.join(eng.nodes[n]['name'] for n in dhs['nodes'])))
            if not _gw_ok(eng, t, dh, dhs, 'Ziel (fuer die Antwort)'):
                return t.result()
        if not _policy(eng, t, sc, dc, proto, port, sh['name'], dh['name'], dst_host=dh):
            return t.result()
        return t.result()

    if D['kind'] == 'site':
        if D['ip'] not in snet and not _gw_ok(eng, t, sh, shs, 'Quelle'):
            return t.result()
        eng.site_path(t, shs, sh, D['rh'], proto, port)
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
    leaked = None
    if not best:
        leaked = _shared_l3out(eng, sc, D['ip'])
        if leaked:
            vrf = leaked['vrf']
            best = (leaked['node'], leaked['route'])
            t.step(True, 'Shared L3Out', 'Route %s aus VRF %s per Route Leaking in VRF %s (Shared Route Control Subnet am '
                   'External EPG %s)' % (leaked['route']['prefix'], eng.short(vrf), eng.short(shs['vrf']), eng.short(leaked['inst'])))
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
    if not _spines(eng, t, shs['nodes'], [bl]):
        return t.result()
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
    cl = _classify_ext(eng, vrf, D['ip']) if not leaked else (leaked['net'], leaked['inst'])
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
    if D['kind'] in ('router', 'ext'):
        return _transit(eng, sim, t, r, rs, iface, vrf, D, proto, port, S['ip'])
    if D['kind'] != 'host':
        t.step(False, 'Ziel', 'Vom externen Router aus kann ein Host, ein anderer Router oder ein Netz hinter einem Router getestet werden')
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


def _transit(eng, sim, t, r, rs, iface, vrf, D, proto, port, src_ip):
    """Transit Routing: externer Router -> ACI -> anderes L3Out."""
    dip = D['ip']
    known = [p for p in rs.get('learned', []) if dip in ipaddress.ip_network(p, strict=False)]
    if not known:
        t.step(False, 'Routing auf %s' % r['name'], 'Router %s hat keine Route zu %s. Fuer Transit Routing muss die ACI '
               'das Netz exportieren: Subnetz mit "Export Route Control Subnet" am External EPG des L3Outs %s'
               % (r['name'], dip, eng.short(iface['out'])))
        return t.result()
    t.step(True, 'Routing auf %s' % r['name'], '%s via ACI (Export Route Control)' % known[0])
    nid = iface['nid']
    rt = _lpm(eng.routes.get((vrf, nid), []), dip)
    if not rt or rt.get('router') == r['name']:
        t.step(False, 'Routing auf %s' % eng.nodes[nid]['name'], 'Keine Route zu %s in VRF %s' % (dip, eng.short(vrf)))
        return t.result()
    bl, brt = nid, rt
    if rt.get('border'):
        bl = rt['border']
        brt = _lpm([x for x in eng.routes.get((vrf, bl), []) if not x.get('border')], dip)
        t.step(True, 'Route auf %s' % eng.nodes[nid]['name'], '%s via Border Leaf %s (MP-BGP)' % (rt['prefix'], eng.nodes[bl]['name']))
    if not brt:
        t.step(False, 'Route auf Border Leaf', 'Border Leaf hat keine Route mehr')
        return t.result()
    rname = brt.get('router') or next((x['name'] for x in sim.get('routers', []) if ip_of(x['ip']) == dip), None)
    t.step(True, 'Route auf Border Leaf %s' % eng.nodes[bl]['name'], '%s via %s %s (%s)' % (brt['prefix'], brt['nh'], brt['via'], brt['proto']))
    s_out, d_rs = iface['out'], eng.routers.get(rname, {})
    d_out = (d_rs.get('iface') or {}).get('out')

    def classify(ip, prefer_out):
        cands = [(n, inst) for n, inst in eng.ext_class.get(vrf, []) if ip in n]
        if not cands:
            return None
        best = max(n.prefixlen for n, _ in cands)
        top = [(n, i) for n, i in cands if n.prefixlen == best]
        return next(((n, i) for n, i in top if eng.cls[i].get('out') == prefer_out), top[0])
    sc_ = classify(src_ip, s_out)
    dc_ = classify(dip, d_out)
    if not sc_:
        t.step(False, 'Klassifizierung', 'Quell-IP %s passt zu keinem External EPG Subnetz' % src_ip)
        return t.result()
    if not dc_:
        t.step(False, 'Klassifizierung', 'Ziel-IP %s passt zu keinem External EPG Subnetz ("External Subnets for the External EPG")' % dip)
        return t.result()
    t.step(True, 'Klassifizierung', 'Quelle %s -> External EPG %s, Ziel %s -> External EPG %s' % (
        src_ip, eng.short(sc_[1]), dip, eng.short(dc_[1])))
    if sc_[1] == dc_[1]:
        t.step(False, 'Policy', 'Quelle und Ziel landen im selben External EPG %s. Fuer Transit Routing braucht jedes L3Out '
               'eigene, spezifische External Subnets (nicht 0.0.0.0/0 auf beiden Seiten) und einen Contract dazwischen'
               % eng.short(sc_[1]))
        return t.result()
    if not _policy(eng, t, eng.cls[sc_[1]], eng.cls[dc_[1]], proto, port, r['name'], str(dip)):
        return t.result()
    dr = _router(sim, rname)
    if D['kind'] == 'ext' and not any(dip in ipaddress.ip_network(n, strict=False) for n in (dr or {}).get('networks', [])):
        t.step(False, 'Externer Router %s' % rname, 'Der Router kennt das Ziel %s nicht' % dip)
        return t.result()
    back = [p for p in d_rs.get('learned', []) if src_ip in ipaddress.ip_network(p, strict=False)]
    if not back:
        t.step(False, 'Rueckweg ueber %s' % rname, 'Router %s hat keine Route zurueck zu %s - die ACI exportiert sie ihm nicht '
               '(Export Route Control Subnet am External EPG von %s fehlt)' % (rname, src_ip, eng.short(d_out) if d_out else '?'))
        return t.result()
    t.step(True, 'Rueckweg ueber %s' % rname, 'Router kennt %s' % back[0])
    return t.result()
