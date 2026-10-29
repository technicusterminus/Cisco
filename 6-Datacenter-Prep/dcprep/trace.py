"""Traffic-Test: verfolgt ein Paket (und die Antwort) durch die simulierte Fabric."""
import ipaddress

from .engine import ip_of, net_of, EPHEMERAL


# Reason Codes: maschinenlesbare Ursache eines DROP. Die Codes sind simulator-spezifisch (keine Cisco-Codes),
# die Reihenfolge der Pruefschritte ist ein didaktisches Diagnosemodell, keine Hardware-Pipeline.
# (Praefix des Schritt-Titels, Code, Ebene, naechster Diagnoseschritt)
STEP_CODES = [
    ('Policy Anfrage', None, 'policy', None),
    ('Policy Antwort', 'POLICY_REPLY_DENIED', 'policy',
     'Rueckweg: Subject-Option "Reverse Filter Ports" und die Filter-Ports pruefen; ohne Reverse passt die Antwort (Quell-Port = Dienst-Port) nicht.'),
    ('Zieldienst', 'SERVICE_NOT_LISTENING', 'service', 'Auf dem Ziel-Host laeuft kein Dienst auf diesem Port (Simulation > Topologie & Hosts, Feld Dienste).'),
    ('Endpoint nicht gelernt', 'EP_NOT_LEARNED', 'endpoint',
     'Access-Kette pruefen: Static Port, VLAN-Encap im Pool, Domain an der EPG, AAEP, Interface Policy Group, Interface-/Switch-Profil, Link.'),
    ('Layer-2-Schleife', 'L2_LOOP', 'endpoint', 'MCP und Legacy-Switches pruefen (Fabric > Access Policies > MCP Instance Policy).'),
    ('Route Leaking', 'INTERVRF_LEAK_MISSING', 'routing', 'Shared-Subnetze am Provider und Consumer sowie den Contract-Scope pruefen.'),
    ('Gateway', 'GATEWAY_INVALID', 'routing', 'BD: Unicast Routing, Subnetz/Gateway-IP und das Default Gateway des Hosts vergleichen.'),
    ('IP-Learning', 'EP_IP_NOT_LEARNED', 'endpoint', 'BD-Option "Limit IP Learning to Subnet" und das BD-Subnetz pruefen.'),
    ('Service Graph', 'SERVICE_GRAPH_NOT_APPLIED', 'policy', 'Operations > Service Graph: Rendering-Zustand und Fehlermeldungen pruefen.'),
    ('PBR', 'PBR_DEST_INVALID', 'policy', 'PBR Policy: Ziel-IP und MAC des Firewall-Interfaces pruefen.'),
    ('Firewall', 'FIREWALL_DENY', 'service', 'Regelwerk und Interfaces der simulierten Firewall pruefen.'),
    ('Rueckweg per PBR', 'PBR_RETURN_INVALID', 'policy', 'PBR Policy am Provider-Connector pruefen.'),
    ('Remote Leaf', 'FABRIC_PATH_DOWN', 'fabric', 'Fabric > Inventory: Zustand der Switches und Links pruefen.'),
    ('Fabric', 'FABRIC_PATH_DOWN', 'fabric', 'Fabric > Inventory: Spines und Fabric-Links pruefen.'),
    ('Multi-Pod', 'FABRIC_PATH_DOWN', 'fabric', 'IPN-Adjacencies und Spine-Uplinks pruefen.'),
    ('Layer 2', 'L2_DIFFERENT_BD', 'forwarding', 'Subnetzmaske des Hosts und BD-Zuordnung der EPGs vergleichen.'),
    ('ARP', 'ARP_UNRESOLVED', 'forwarding', 'BD-Optionen ARP Flooding und Unicast Routing pruefen, ist das Ziel ein stiller Host?'),
    ('Routing', 'ROUTE_MISSING', 'routing', 'Routing-Tabelle des Leafs (CLI: show ip route vrf ...) und L3Out-Nachbarschaft pruefen.'),
    ('Route auf Border Leaf', 'ROUTE_MISSING', 'routing', 'Routen auf dem Border Leaf und die L3Out-Nachbarschaft pruefen.'),
    ('Klassifizierung', 'EXT_EPG_NO_MATCH', 'policy', 'External EPG: Subnetz mit "External Subnets for the External EPG" pruefen.'),
    ('Rueckweg', 'RETURN_ROUTE_MISSING', 'routing',
     'BD-Subnetz "Advertised Externally", BD mit L3Out verknuepft, Export-Route-Control und Route des externen Routers pruefen.'),
    ('Externer Router', 'EXTERNAL_UNREACHABLE', 'external', 'Netze des simulierten externen Routers pruefen.'),
    ('Router', 'EXTERNAL_UNREACHABLE', 'external', 'Link, Nachbarschaft und Routen des externen Routers pruefen.'),
    ('VRF', 'VRF_MISMATCH', 'routing', 'VRF des BD und des L3Out vergleichen.'),
    ('Policy', 'POLICY_TRANSIT_DENIED', 'policy', 'Fuer Transit Routing braucht jedes L3Out ein eigenes External EPG mit Contract.'),
    ('Ziel', 'DEST_INVALID', 'input', None),
]

# Codes der Policy-Entscheidung (engine.packet) mit naechstem Diagnoseschritt
POLICY_HINTS = {
    'POLICY_IMPLICIT_DENY': 'Zwischen den beiden EPGs gibt es keinen Contract mit passendem Filter. Contract, Subject, Filter-Entry '
                            '(Protokoll, Ports) und die Rollen Consumer/Provider pruefen; CLI: show zoning-rule.',
    'POLICY_DENY_RULE': 'Ein Filter mit Aktion Deny passt. Subjects und Filter-Aktionen im Contract pruefen.',
    'POLICY_TABOO': 'Ein Taboo Contract an der Ziel-EPG verbietet diesen Verkehr.',
    'POLICY_INTRA_EPG_ISOLATION': 'An der EPG ist Intra EPG Isolation "enforced" - Endpoints derselben EPG duerfen nicht miteinander sprechen.',
    'POLICY_INTRA_EPG_CONTRACT_DENY': 'An der EPG haengt ein Intra-EPG-Contract: Innerhalb der EPG gilt nur noch, was seine Filter erlauben.',
    'POLICY_ESG_EPG_MIX': 'Contracts zwischen ESG und EPG gibt es nicht; beide Seiten muessen ESGs sein.',
}


# Physische Ursachen, wenn kein Link eines Hosts nutzbar ist
PHYS_HINTS = {
    'LINK_DOWN': 'Kein Link am Leaf-Port: Kabel, Transceiver oder NIC des Hosts pruefen. Das ist kein Konfigurationsfehler der ACI '
                 '(CLI: show interface ethX/Y, Fabric > Inventory > Interfaces).',
    'PORT_ADMIN_DOWN': 'Der Port ist in der ACI deaktiviert (Fabric > Inventory > Disabled Interfaces, fabricRsOosPath). Wieder aktivieren.',
    'PORT_ERR_DISABLED': 'Der Port ist error-disabled (z. B. durch MCP). Ursache beseitigen, dann den Port wieder aktivieren.',
    'SWITCH_INACTIVE': 'Der Leaf ist nicht aktiv (Discovery, Upgrade oder nicht registriert). Fabric > Inventory pruefen.',
}


class Trace:
    def __init__(self):
        self.steps = []
        self.ok = True
        self.woken = []
        self.policy = []
        self.path = None

    def step(self, ok, title, detail='', code=None, refs=None, hint=None):
        st = {'ok': ok, 'title': title, 'detail': detail}
        if ok is False:
            self.ok = False
            for pre, c, layer, h in STEP_CODES:
                if title.startswith(pre) or (' ' + pre) in title:
                    code, st['layer'], hint = code or c, layer, hint or h
                    break
            st['code'] = code or 'CHECK_FAILED'
            if hint:
                st['hint'] = hint
        elif code:
            st['code'] = code
        if refs:
            st['refs'] = [r for r in refs if r]
        self.steps.append(st)
        return ok is not False

    def result(self, summary=None):
        if summary is None:
            summary = 'Erfolgreich: Anfrage und Antwort kommen an.' if self.ok else \
                'Fehlgeschlagen: siehe ersten roten Schritt.'
        out = {'ok': self.ok, 'summary': summary, 'steps': self.steps, 'woken': self.woken if self.ok else [],
               'policy': self.policy, 'path': self.path}
        return finish(out)


def finish(r):
    """Ergebnis vereinheitlichen: verdict ALLOW / DROP / UNRESOLVED, reason (Code), location, hint."""
    if 'verdict' in r:
        return r
    bad = next((s for s in r.get('steps', []) if s['ok'] is False), None)
    if r.get('ok'):
        r.update(verdict='ALLOW', reason='ALLOWED', location=None, hint=None)
    elif bad:
        r.update(verdict='DROP', reason=bad.get('code', 'CHECK_FAILED'), location=bad['title'], layer=bad.get('layer'),
                 explain=bad['detail'], hint=bad.get('hint'))
        if bad.get('code') == 'DEST_INVALID':
            r['verdict'] = 'UNRESOLVED'
    else:
        r.update(verdict='UNRESOLVED', reason='INPUT_INVALID', location=None, explain=r.get('summary'), hint=None)
    r.setdefault('steps', [])
    r.setdefault('policy', [])
    return r


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
        codes = (hs or {}).get('codes') or []
        if codes and not hs.get('legs'):
            # kein einziger Link nutzbar: physische Ursache statt Access-/EPG-Problem
            c = codes[0]
            t.step(False, '%s %s: Link nicht nutzbar' % (role, h['name']), '; '.join(reasons), code=c,
                   hint=PHYS_HINTS.get(c))
            t.steps[-1]['layer'] = 'physical'
        else:
            t.step(False, '%s %s: Endpoint nicht gelernt' % (role, h['name']), '; '.join(reasons))
        return None
    if hs.get('storm'):
        t.step(False, '%s %s: Layer-2-Schleife im BD %s' % (role, h['name'], eng.short(hs['bd'])), hs['storm'])
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
                                              eng.short(hs['bd']), eng.short(hs['vrf'])))
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


def _policy(eng, t, s, d, proto, port, label_s, label_d, dst_host=None):
    dport = port if proto in ('tcp', 'udp') else None
    act, why = eng.packet(s, d, proto, EPHEMERAL if dport else None, dport, 'syn')
    code, rule = getattr(eng, 'last_code', None), getattr(eng, 'last_rule', None)
    if act == 'permit':
        eng.count(s['dn'], 'txPkts')
        eng.count(d['dn'], 'rxPkts')
    else:
        eng.count(s['dn'], 'txPkts')
        eng.count(d['dn'], 'dropPkts')
    flow = '%s%s' % (proto, '/%d' % port if dport else '')
    t.policy.append({'direction': 'request', 'from': s['dn'], 'to': d['dn'], 'flow': flow, 'sport': EPHEMERAL if dport else None,
                     'dport': dport, 'action': act, 'code': code, 'rule': rule, 'text': why})
    t.step(act == 'permit', 'Policy Anfrage %s -> %s (%s)' % (label_s, label_d, flow), why,
           code=code, refs=[s['dn'], d['dn'], (rule or {}).get('contract')], hint=POLICY_HINTS.get(code))
    if act != 'permit':
        return False
    hit = getattr(eng, 'last_hit', None)
    g = getattr(eng, 'graphs', {}).get(hit[0]) if hit else None
    if g is not None and not _service(eng, t, g, hit[1], proto, port):
        return False
    if dst_host is not None and dport and dst_host.get('services') is not None:
        svc = '%s/%d' % (proto, port)
        if svc not in [x.strip().lower() for x in dst_host['services']]:
            t.step(False, 'Zieldienst auf %s' % dst_host['name'],
                   'Netz und Policy lassen das Paket durch, aber auf %s laeuft kein Dienst %s (laufende Dienste: %s). '
                   'Ein echter Host antwortet mit TCP RST bzw. ICMP Port Unreachable - simulator-spezifisches Dienstmodell.'
                   % (dst_host['name'], svc, ', '.join(dst_host['services']) or 'keine'), refs=[d['dn']])
            return False
        t.step(True, 'Zieldienst %s auf %s' % (svc, dst_host['name']), 'Dienst laeuft (simulator-spezifisches Dienstmodell)')
    act, why = eng.packet(d, s, proto, dport, EPHEMERAL if dport else None, 'ack')
    code, rule = getattr(eng, 'last_code', None), getattr(eng, 'last_rule', None)
    eng.count(d['dn'], 'txPkts')
    eng.count(s['dn'], 'rxPkts' if act == 'permit' else 'dropPkts')
    t.policy.append({'direction': 'reply', 'from': d['dn'], 'to': s['dn'], 'flow': flow, 'sport': dport, 'dport': EPHEMERAL if dport else None,
                     'action': act, 'code': code, 'rule': rule, 'text': why})
    t.step(act == 'permit', 'Policy Antwort %s -> %s' % (label_d, label_s), why,
           code='POLICY_REPLY_DENIED' if act != 'permit' else code, refs=[d['dn'], s['dn'], (rule or {}).get('contract')],
           hint=None if act == 'permit' else 'Die Anfrage war erlaubt, die Antwort nicht. ' + STEP_CODES[1][3])
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
    """Traffic-Test von src nach dst. Ergebnis mit verdict, reason, location, steps, policy (siehe finish)."""
    return finish(_run(eng, sim, src, dst, proto, port))


def _run(eng, sim, src, dst, proto='icmp', port=0):
    t = Trace()
    proto = proto if proto in ('icmp', 'tcp', 'udp') else 'icmp'
    port = int(port or 0)
    if proto in ('tcp', 'udp') and not port:
        return {'ok': False, 'summary': 'Fuer TCP/UDP bitte einen Ziel-Port angeben.', 'steps': []}
    S = _resolve(eng, sim, src)
    D = _resolve(eng, sim, dst)
    if S is not None and S['kind'] == 'ext':
        r_ = next((x for x in sim.get('routers', []) if any(S['ip'] in ipaddress.ip_network(n, strict=False)
                                                             for n in x.get('networks', []))), None)
        if r_:
            S = {'kind': 'router', 'r': r_, 'ip': S['ip']}
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
    leafs = lambda hs: [eng.nodes[n]['name'] for n in hs.get('nodes', []) if n in eng.nodes]
    t.path = {'src': sh['name'], 'srcLeafs': leafs(shs), 'srcEpg': shs['epg']}

    if D['kind'] == 'host':
        t.path['dst'] = D['h']['name']
        r = _host_checks(eng, t, D, 'Ziel')
        if not r:
            return t.result()
        dhs, dc = r
        dh = D['h']
        t.path.update(dst=dh['name'], dstLeafs=leafs(dhs), dstEpg=dhs['epg'])
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
    if not _policy(eng, t, sc, dc, proto, port, r['name'], dh['name'], dst_host=dh):
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
