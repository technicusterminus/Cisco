"""Relationen, Klassen (pcTags), Contracts und Zoning Rules, Service Graphs und die Policy-Entscheidung je Paket."""

from .model import CLASSES, parent_dn, tenant_of

from .engine_util import (vlan_num, port_val, ip_of)


def has_log(rfa):
    """Directive "log" an der Filter-Relation (vzRsSubjFiltAtt/vzRsFiltAtt), kommagetrennt wie "log,no_stats"."""
    return 'log' in ((rfa or {}).get('directives') or '').split(',')


def entry_is_any(ea):
    """Filter Entry ohne EtherType ("unspecified") entspricht dem default-/any-Filter."""
    return ea.get('etherT', 'unspecified') == 'unspecified'


def is_global(c):
    """Klasse mit globalem pcTag (16-16384): ESG oder Provider-EPG eines Inter-VRF-Contracts (Contract Guide)."""
    tag = str(c.get('pcTag') or '')
    return c.get('kind') == 'esg' or (tag.isdigit() and 16 <= int(tag) <= 16384)


def rule_prio(src_specific, dst_specific, any_filter, esg=False):
    """Zoning-Rule-Prioritaet nach Cisco ACI Contract Guide, Table 8 (EPG-to-EPG, EPG-to-vzAny, vzAny-to-EPG,
    vzAny-to-vzAny; je mit spezifischem oder any-Filter). Kleinere Zahl = hoehere Prioritaet.
    esg: die spezifische Seite einer vzAny-Regel hat einen globalen pcTag (ESG, Inter-VRF-Provider) -> 10/11 statt 13-16
    (Contract Guide, Table 8: shsrc_any_filt_perm / shsrc_any_any_perm).
    Fuer vzAny -> globaler Provider-EPG (Inter-VRF) nennt Table 8 keine eigene Stufe; angenommen wie ESG (gleiche Begruendung)."""
    if esg and bool(src_specific) != bool(dst_specific):
        return (11, 'shsrc_any_any_perm(11)') if any_filter else (10, 'shsrc_any_filt_perm(10)')
    table = {(True, True): ((7, 'fully_qual'), (9, 'src_dst_any')),
             (True, False): ((13, 'src_any_filter'), (15, 'src_any_any')),
             (False, True): ((14, 'any_dest_filter'), (16, 'any_dest_any')),
             (False, False): ((17, 'any_any_filter'), (21, 'any_any_any'))}
    n, name = table[(bool(src_specific), bool(dst_specific))][1 if any_filter else 0]
    return n, '%s(%d)' % (name, n)


def filter_prio(ea):
    """Filter-Prioritaet nach Contract Guide, Table 23 (1 = am spezifischsten). Entscheidet nur zwischen Permit
    und Redirect gleicher Zoning-Rule-Prioritaet."""
    if entry_is_any(ea):
        return 7
    if ea.get('tcpRules'):
        return 1
    if ea.get('applyToFrag') == 'yes':
        return 6
    spec = lambda a, b: (ea.get(a, 'unspecified'), ea.get(b, 'unspecified')) != ('unspecified', 'unspecified')
    sp, dp = spec('sFromPort', 'sToPort'), spec('dFromPort', 'dToPort')
    return 2 if sp and dp else 3 if dp else 4 if sp else 5


class PolicyMixin:
    # ------------------------------------------------------------------
    # Relationen auflösen
    # ------------------------------------------------------------------
    def _resolve(self):
        st = self.store
        for dn, (cls, a, oper) in list(st.objs.items()):
            meta = CLASSES[cls]
            if not meta.rel or oper:
                continue
            rel = meta.rel
            if rel[0] == 'name':
                attr, tcls, scope = rel[1], rel[2], rel[3]
                name = a.get(attr) or 'default'
                rn = CLASSES[tcls].rn.format(name=name)
                if scope == 'tenant':
                    tn = tenant_of(dn)
                    cands = [tn + '/' + rn, 'uni/tn-common/' + rn] if tn else []
                elif scope == 'fabric':
                    cands = ['uni/fabric/' + rn]
                else:
                    cands = ['uni/infra/' + rn]
                tgt = next((c for c in cands if c in st.objs and st.objs[c][0] == tcls), '')
                a['tDn'] = tgt
                a['tCl'] = tcls
                a['state'] = 'formed' if tgt else 'missing-target'
                a['stateQual'] = ('default-target' if not a.get(attr) else 'none') if tgt else 'target-not-found'
                if not tgt and cls not in ('fvRsBd', 'fvRsCtx', 'l3extRsEctx'):
                    self.fault(dn, 'S1123', 'warning',
                               'Failed to form relation to MO %s of class %s' % (cands[0] if cands else name, tcls),
                               'resolution-failed')
            else:
                t = a.get('tDn', '')
                o = st.objs.get(t)
                ok = o is not None and o[0] in rel[2]
                a['tCl'] = o[0] if o else rel[2][0]
                a['state'] = 'formed' if ok else 'missing-target'
                a['stateQual'] = 'none' if ok else 'target-not-found'
                if not ok and t and cls not in ('fvRsPathAtt', 'l3extRsPathL3OutAtt'):
                    self.fault(dn, 'S1123', 'warning',
                               'Failed to form relation to MO %s of class %s' % (t or '(leer)', rel[2][0]),
                               'resolution-failed', domain='tenant' if tenant_of(dn) else 'access')

    # ------------------------------------------------------------------
    # EPGs, External EPGs und Contracts als "Klassen" (pcTags)
    # ------------------------------------------------------------------
    def _rs_targets(self, dn, cls):
        return [self.A(r)['tDn'] for r in self.kids(dn, cls) if self.A(r)['state'] == 'formed']

    def _classes(self):
        self.cls = {}
        for dn in self.store.by_class('fvAEPg'):
            a = self.A(dn)
            bd = self.A(dn + '/rsbd')['tDn'] if self.has(dn + '/rsbd') else ''
            vrf = self.A(bd + '/rsctx')['tDn'] if bd and self.has(bd + '/rsctx') else ''
            a['scope'] = self.A(vrf)['scope'] if vrf else ''
            self.cls[dn] = {'dn': dn, 'kind': 'epg', 'name': a['name'], 'tenant': tenant_of(dn),
                            'ap': parent_dn(dn), 'bd': bd, 'vrf': vrf, 'pcTag': a['pcTag'],
                            'prov': self._rs_targets(dn, 'fvRsProv'),
                            'cons': self._rs_targets(dn, 'fvRsCons'),
                            'pref': a['prefGrMemb'] == 'include',
                            'isolation': a['pcEnfPref'] == 'enforced',
                            'intra': self._rs_targets(dn, 'fvRsIntraEpg')}
        for dn in self.store.by_class('fvESg'):
            a = self.A(dn)
            vrs = self.A(dn + '/rsscope') or {}
            vrf = vrs.get('tDn') if vrs.get('state') == 'formed' else ''
            self.cls[dn] = {'dn': dn, 'kind': 'esg', 'name': a['name'], 'tenant': tenant_of(dn), 'ap': parent_dn(dn), 'bd': None,
                            'vrf': vrf, 'pcTag': a['pcTag'], 'prov': self._rs_targets(dn, 'fvRsProv'),
                            'cons': self._rs_targets(dn, 'fvRsCons'), 'pref': a['prefGrMemb'] == 'include',
                            'isolation': a['pcEnfPref'] == 'enforced'}
        for dn in self.store.by_class('l3extInstP'):
            a = self.A(dn)
            out = parent_dn(dn)
            vrf = self.A(out + '/rsectx')['tDn'] if self.has(out + '/rsectx') else ''
            a['scope'] = self.A(vrf)['scope'] if vrf else ''
            self.cls[dn] = {'dn': dn, 'kind': 'ext', 'name': a['name'], 'tenant': tenant_of(dn),
                            'ap': None, 'bd': None, 'vrf': vrf, 'pcTag': a['pcTag'], 'out': out,
                            'prov': self._rs_targets(dn, 'fvRsProv'),
                            'cons': self._rs_targets(dn, 'fvRsCons'),
                            'pref': a['prefGrMemb'] == 'include', 'isolation': False}
        for dn in self.store.by_class('l2extInstP'):
            a = self.A(dn)
            out = parent_dn(dn)
            rs = self.A(out + '/rseBd') or {}
            bd = rs.get('tDn', '') if rs.get('state') == 'formed' else ''
            vrf = self.A(bd + '/rsctx')['tDn'] if bd and self.has(bd + '/rsctx') else ''
            a['scope'] = self.A(vrf)['scope'] if vrf else ''
            self.cls[dn] = {'dn': dn, 'kind': 'l2ext', 'name': a['name'], 'tenant': tenant_of(dn),
                            'ap': None, 'bd': bd, 'vrf': vrf, 'pcTag': a['pcTag'], 'out': out,
                            'prov': self._rs_targets(dn, 'fvRsProv'),
                            'cons': self._rs_targets(dn, 'fvRsCons'),
                            'pref': a['prefGrMemb'] == 'include', 'isolation': False}
        for dn, c in self.cls.items():
            for cif in self._rs_targets(dn, 'fvRsConsIf'):
                t = (self.A(cif + '/rsif') or {})
                if t.get('state') == 'formed':
                    c['cons'].append(t['tDn'])
                    c.setdefault('imported', []).append((cif, t['tDn']))
        for dn in self.store.by_class('fvBD'):
            vrf = self.A(dn + '/rsctx')['tDn'] if self.has(dn + '/rsctx') else ''
            self.A(dn)['scope'] = self.A(vrf)['scope'] if vrf else ''
        self.contracts = {}
        for dn, c in self.cls.items():
            for k in ('prov', 'cons'):
                for brc in c[k]:
                    self.contracts.setdefault(brc, {'prov': set(), 'cons': set(), 'prov_any': set(),
                                                    'cons_any': set()})[k].add(dn)
        for vrf in self.store.by_class('fvCtx'):
            anyd = vrf + '/any'
            if not self.has(anyd):
                continue
            for brc in self._rs_targets(anyd, 'vzRsAnyToProv'):
                self.contracts.setdefault(brc, {'prov': set(), 'cons': set(), 'prov_any': set(),
                                                'cons_any': set()})['prov_any'].add(vrf)
            for brc in self._rs_targets(anyd, 'vzRsAnyToCons'):
                self.contracts.setdefault(brc, {'prov': set(), 'cons': set(), 'prov_any': set(),
                                                'cons_any': set()})['cons_any'].add(vrf)
        # Shared Services: Provider-EPG bekommt einen globalen pcTag (< 16384)
        for brc, rel in self.contracts.items():
            if (self.A(brc) or {}).get('scope') not in ('tenant', 'global'):
                continue
            for p in rel['prov']:
                pc = self.cls.get(p)
                if pc and pc['kind'] == 'epg' and pc['pcTag'].isdigit() and int(pc['pcTag']) >= 16384 and any(
                        self.cls.get(c, {}).get('vrf') not in (None, '', pc['vrf']) for c in rel['cons']) or any(
                        v != pc['vrf'] for v in rel['cons_any']):
                    pc['localTag'] = pc['pcTag']
                    pc['pcTag'] = str(10000 + int(pc['pcTag']) % 6000)

    # ------------------------------------------------------------------
    # L4-L7: Service Graph mit Policy-Based Redirect
    # ------------------------------------------------------------------
    def _services(self):
        self.graphs = {}
        self.fw_hosts = []
        for dev in self.sim.get('devices', []):
            for i in dev.get('ifs', []):
                self.fw_hosts.append({'name': '%s:%s' % (dev['name'], i['name']), 'mac': i['mac'], 'ip': i['ip'], 'gw': '',
                                      'vlan': int(i.get('vlan') or 0), 'links': dev.get('links', []), 'bond': 'none',
                                      'dev': dev['name'], 'devif': i['name']})
        tag = 49153
        for rs in sorted(self.store.by_class('vzRsSubjGraphAtt')):
            ra = self.A(rs)
            subj = parent_dn(rs)
            brc = parent_dn(subj)
            tn = tenant_of(brc)
            if ra['state'] != 'formed':
                continue
            graph = ra['tDn']
            rel = self.contracts.get(brc, {'prov': set(), 'cons': set()})
            cons = sorted(rel['cons'])
            prov = sorted(rel['prov'])
            vrf = next((self.cls[x]['vrf'] for x in cons + prov if x in self.cls and self.cls[x]['vrf']), '')
            gi = '%s/GraphInst_C-[%s]-G-[%s]-S-[%s]' % (tn, brc, graph, vrf)
            info = {'dn': gi, 'subj': subj, 'brc': brc, 'graph': graph, 'state': 'failed', 'reasons': [], 'conns': {},
                    'node': None, 'dev': None, 'redirect': False, 'vrf': vrf}
            self.graphs[subj] = info
            self.store.add(gi, 'vnsGraphInst', {'ctrctDn': brc, 'graphDn': graph, 'scopeDn': vrf, 'configSt': 'failed-to-apply'}, True)

            def fail(why, code='S1690'):
                info['reasons'].append(why)
                self.fault(gi, code, 'major', 'Graph %s for contract %s could not be rendered: %s' % (
                    self.A(graph)['name'], self.A(brc)['name'], why), 'graph-rendering-failure')
            if not cons or not prov:
                fail('Contract hat keinen Consumer oder keinen Provider')
                continue
            nodes = self.kids(graph, 'vnsAbsNode')
            if not nodes:
                fail('Service Graph Template enthaelt keinen Function Node')
                continue
            node = nodes[0]
            na = self.A(node)
            info['node'] = na['name']
            info['redirect'] = na['routingMode'] == 'Redirect'
            info['func'] = na.get('funcType', 'GoTo')
            cname, gname = self.A(brc)['name'], self.A(graph)['name']
            ctx = next((d for d in self.kids(tn, 'vnsLDevCtx')
                        if self.A(d)['ctrctNameOrLbl'] in (cname, 'any') and self.A(d)['graphNameOrLbl'] in (gname, 'any')
                        and self.A(d)['nodeNameOrLbl'] in (na['name'], 'any')), None)
            if not ctx:
                fail('Keine Device Selection Policy fuer Contract %s, Graph %s, Node %s (Apply L4-L7 Service Graph Template '
                     'ausfuehren)' % (cname, gname, na['name']))
                continue
            ldev = (self.A(ctx + '/rsLDevCtxToLDev') or {})
            if ldev.get('state') != 'formed':
                fail('Device Selection Policy verweist auf kein gueltiges L4-L7 Device')
                continue
            ldev = ldev['tDn']
            info['dev'] = ldev
            domrs = self.A(ldev + '/rsALDevToPhysDomP') or {}
            if domrs.get('state') != 'formed':
                fail('L4-L7 Device %s hat keine gueltige Physical Domain' % self.A(ldev)['name'])
                continue
            dom = domrs['tDn']
            ok = True
            for conn in ('consumer', 'provider'):
                lic = ctx + '/lIfCtx-c-' + conn
                if not self.has(lic):
                    fail('Logical Interface Context %s fehlt in der Device Selection Policy' % conn)
                    ok = False
                    break
                bdrs = self.A(lic + '/rsLIfCtxToBD') or {}
                lifrs = self.A(lic + '/rsLIfCtxToLIf') or {}
                pbrrs = self.A(lic + '/rsLIfCtxToSvcRedirectPol') or {}
                if bdrs.get('state') != 'formed':
                    fail('%s-Connector: keine gueltige Bridge Domain' % conn)
                    ok = False
                    break
                if lifrs.get('state') != 'formed':
                    fail('%s-Connector: kein gueltiges Cluster Interface' % conn)
                    ok = False
                    break
                bd = bdrs['tDn']
                bvrf = (self.A(bd + '/rsctx') or {}).get('tDn')
                if bvrf != vrf:
                    fail('%s-Connector: BD %s liegt in VRF %s, der Contract in VRF %s' % (conn, self.short(bd), self.short(bvrf), self.short(vrf)))
                    ok = False
                    break
                lif = lifrs['tDn']
                vlan = vlan_num(self.A(lif)['encap'])
                cifs = [self.A(r)['tDn'] for r in self.kids(lif, 'vnsRsCIfAttN') if self.A(r)['state'] == 'formed']
                if vlan is None or not cifs:
                    fail('Cluster Interface %s: Encap oder Concrete Interface fehlt' % self.A(lif)['name'])
                    ok = False
                    break
                prs = self.A(cifs[0] + '/rsCIfPathAtt') or {}
                path = self.paths.get(prs.get('tDn', ''))
                if not path:
                    fail('Concrete Interface %s: Path fehlt oder existiert nicht' % self.A(cifs[0])['name'], 'F0467')
                    ok = False
                    break
                if not self.vlan_in_domain(dom, vlan):
                    fail('vlan-%d des Cluster Interfaces %s ist nicht im VLAN Pool der Domain %s (invalid-vlan)'
                         % (vlan, self.A(lif)['name'], self.short(dom)), 'F0467')
                    ok = False
                    break
                pgdoms = self._pg_info(path['pg'])['domains'] if path['pg'] else []
                if dom not in pgdoms:
                    fail('%s: Die Access Policy des Ports enthaelt die Domain %s nicht (invalid-path)' % (path['name'], self.short(dom)), 'F0467')
                    ok = False
                    break
                pol = pbrrs.get('tDn') if pbrrs.get('state') == 'formed' else None
                if info['redirect'] and not pol:
                    fail('%s-Connector: Routing Mode Redirect braucht eine L4-L7 Policy-Based Redirect Policy' % conn)
                    ok = False
                    break
                if info['redirect']:
                    # White Paper "Service Graph Design with Cisco ACI", BD tuning fuer PBR: Am BD des L4-L7-Geraets muss
                    # IP Routing an sein; im Go-To-Modus braucht er ein Subnetz; GARP-based detection sollte an sein.
                    bda = self.A(bd) or {}
                    if bda.get('unicastRoute') != 'yes':
                        fail('%s-Connector: PBR braucht am BD %s IP Routing (Unicast Routing)' % (conn, self.short(bd)))
                        ok = False
                        break
                    if info.get('func') == 'GoTo' and not self.bd_subnets(bd):
                        fail('%s-Connector: Im Go-To-Modus braucht der BD %s des L4-L7-Geraets ein Subnetz' % (conn, self.short(bd)))
                        ok = False
                        break
                    if bda.get('epMoveDetectMode') != 'garp':
                        self.fault(bd, 'S1691', 'warning', 'BD %s connects an L4-L7 device with PBR: GARP based EP move detection '
                                   'should be enabled' % self.short(bd), 'pbr-bd-garp-recommended')
                dests = [{'ip': self.A(d)['ip'], 'mac': (self.A(d)['mac'] or '').upper(),
                          'hg': (self.A(d + '/rsRedirectHealthGroup') or {}).get('tDn', '')}
                         for d in self.kids(pol, 'vnsRedirectDest')] if pol else []
                # Tracking (Cisco APIC L4-L7 Services Deployment Guide): braucht IP SLA Monitoring Policy an der PBR Policy
                # UND eine Redirect Health Group an der Destination.
                sla = (self.A(pol + '/rsIPSLAMonitoringPol') or {}).get('tDn', '') if pol else ''
                sla_ok = bool(sla) and self.A(sla) is not None
                for d in dests:
                    d['tracked'] = sla_ok and bool(d['hg']) and self.A(d['hg']) is not None
                    dv = next((x for x in self.sim.get('devices', [])
                               if any(str(ip_of(i['ip'])) == d['ip'] for i in x.get('ifs', []))), None)
                    d['down'] = bool(dv and dv.get('down'))
                    if sla_ok and not d['tracked']:
                        self.fault(pol, 'S1693', 'warning', 'PBR policy %s: IP SLA monitoring policy is set, but destination %s has '
                                   'no redirect health group - tracking is not active' % (self.short(pol), d['ip']),
                                   'pbr-tracking-incomplete')
                    if d['tracked'] and d['down']:
                        self.fault(pol, 'S1694', 'major', 'PBR policy %s: destination %s is down (tracking), threshold down action %s'
                                   % (self.short(pol), d['ip'], (self.A(pol) or {}).get('thresholdDownAction', 'permit')),
                                   'pbr-destination-down')
                if pol and not dests:
                    fail('PBR Policy %s hat keine Destination' % self.short(pol))
                    ok = False
                    break
                sh = gi + '/EPpInfo-' + conn
                tag += 1
                c = {'dn': sh, 'kind': 'svc', 'name': '%s-%s' % (self.A(ldev)['name'], conn), 'tenant': tn, 'ap': None,
                     'vname': '%s:%sctx%s:%s' % (tn[7:], self.A(ldev)['name'], vrf.split('/ctx-')[-1], conn),
                     'bd': bd, 'vrf': vrf, 'pcTag': str(tag), 'prov': [], 'cons': [], 'pref': False, 'isolation': False}
                self.store.add(sh, 'vnsEPpInfo', {'name': conn, 'pcTag': str(tag), 'bdDn': bd, 'encap': 'vlan-%d' % vlan}, True)
                self.cls[sh] = c
                self._deploy(sh, c, prs['tDn'], path, vlan, 'regular')
                info['conns'][conn] = {'bd': bd, 'vlan': vlan, 'path': prs['tDn'], 'pol': pol, 'dests': dests,
                                       'lif': lif, 'shadow': sh, 'pcTag': str(tag)}
            if ok:
                info['state'] = 'applied'
                self.A(gi)['configSt'] = 'applied'

    # ------------------------------------------------------------------
    # Contracts: Paketentscheidung
    # ------------------------------------------------------------------
    @staticmethod
    def _rng(p, f, t):
        fv, tv = port_val(f), port_val(t)
        if fv is None and tv is None:
            return True
        if p is None:
            return False
        fv = fv if fv is not None else tv
        tv = tv if tv is not None else fv
        return fv <= p <= tv

    def _entry_match(self, e, proto, sport, dport, flags, rev):
        if e['etherT'] not in ('unspecified', 'ip', 'ipv4'):
            return False
        if e['prot'] not in ('unspecified', proto):
            return False
        if proto in ('tcp', 'udp') and e['prot'] == proto:
            d = (e['dFromPort'], e['dToPort'])
            s = (e['sFromPort'], e['sToPort'])
            if rev:
                d, s = s, d
            if not self._rng(dport, *d) or not self._rng(sport, *s):
                return False
        if 'est' in (e.get('tcpRules') or '').split(',') and proto == 'tcp' and flags != 'ack':
            return False
        if 'est' in (e.get('tcpRules') or '').split(',') and proto != 'tcp':
            return False
        return True

    def packet(self, s, d, proto, sport, dport, flags):
        """Entscheidet ein einzelnes Paket von Klasse s nach Klasse d -> (permit|deny, Begruendung).
        Danach stehen in last_code der Reason Code und in last_rule die angewandte Regel."""
        self._code, self.last_rule = None, None
        act, why = self._packet(s, d, proto, sport, dport, flags)
        self.last_code = self._code
        return act, why

    def _decide(self, code, act, why, rule=None):
        self._code = code
        self.last_rule = rule
        return act, why

    def _packet(self, s, d, proto, sport, dport, flags):
        self.last_hit = None
        vrf = s['vrf']
        va = self.A(vrf) or {}
        if va.get('pcEnfPref') == 'unenforced':
            return self._decide('POLICY_VRF_UNENFORCED', 'permit', 'VRF %s steht auf "unenforced" - keine Policy-Pruefung' % self.short(vrf))
        if proto == 'udp' and (sport, dport) in ((68, 67), (67, 68)):
            # Contract Guide, FAQ: DHCPv4 (sport 0x44/dport 0x43 und umgekehrt) ist implizit erlaubt; Contract-Aktionen
            # (Deny, Redirect, Taboo) greifen standardmaessig nicht. Das Abschalten der impliziten Regel ist nicht modelliert.
            return self._decide('POLICY_IMPLICIT_PROTOCOL', 'permit', 'DHCP (UDP %s -> %s) ist ohne Contract implizit erlaubt'
                                % (sport, dport))
        for tb in self._rs_targets(d['dn'], 'fvRsProtBy'):
            for ts in self.kids(tb, 'vzTSubj'):
                for rd in self.kids(ts, 'vzRsDenyRule'):
                    rda = self.A(rd)
                    if rda['state'] != 'formed':
                        continue
                    for e in self.kids(rda['tDn'], 'vzEntry'):
                        if self._entry_match(self.A(e), proto, sport, dport, flags, False):
                            return self._decide('POLICY_TABOO', 'deny', 'Taboo Contract %s (Filter %s) schuetzt %s' % (
                                self.short(tb), self.A(rda['tDn'])['name'], self.short(d['dn'])), {'contract': tb, 'filter': rda['tDn'], 'entry': e})
        if (s['kind'] == 'esg') != (d['kind'] == 'esg') and 'epg' in (s['kind'], d['kind']):
            return self._decide('POLICY_ESG_EPG_MIX', 'deny', 'Contracts zwischen einer ESG und einer EPG werden nicht unterstuetzt - beide Seiten '
                                'muessen ESGs sein (oder ein External EPG)')
        if s['dn'] == d['dn']:
            if s.get('intra'):
                # Intra-EPG-Contract: innerhalb der EPG gilt nur noch, was der Contract erlaubt (EPG ist Consumer und Provider)
                for brc in s['intra']:
                    for subj in self.kids(brc, 'vzSubj'):
                        sa = self.A(subj)
                        for rf, dirn in self.subj_filters(subj):
                            rfa = self.A(rf)
                            if rfa['state'] != 'formed':
                                continue
                            for e in self.kids(rfa['tDn'], 'vzEntry'):
                                ea = self.A(e)
                                # EPG ist Consumer und Provider: Richtungsfilter (vzInTerm/vzOutTerm) gelten wie definiert
                                hit = self._entry_match(ea, proto, sport, dport, flags, False) or \
                                    (dirn == 'both' and self._entry_match(ea, proto, sport, dport, flags, sa['revFltPorts'] == 'yes'))
                                if hit:
                                    return self._decide('POLICY_INTRA_EPG_CONTRACT', rfa['action'],
                                                        'Intra-EPG-Contract %s / %s / %s' % (self.short(brc), sa['name'], self.A(rfa['tDn'])['name']),
                                                        {'contract': brc, 'subject': subj, 'filter': rfa['tDn'], 'entry': e, 'direction': 'intra'})
                return self._decide('POLICY_INTRA_EPG_CONTRACT_DENY', 'deny', 'Intra-EPG-Contract an %s erlaubt diesen Verkehr nicht'
                                    % self.short(s['dn']), {'epg': s['dn']})
            if s.get('isolation'):
                return self._decide('POLICY_INTRA_EPG_ISOLATION', 'deny', 'Intra-EPG-Isolation ist aktiv', {'epg': s['dn']})
            return self._decide('POLICY_SAME_EPG', 'permit', 'Quelle und Ziel in derselben EPG - kein Contract noetig', {'epg': s['dn']})
        anya = self.A(vrf + '/any') or {}
        pref_on = anya.get('prefGrMemb') == 'enabled'
        hits = []
        for brc, rel in self.contracts.items():
            s_cons = s['dn'] in rel['cons'] or vrf in rel['cons_any']
            s_prov = s['dn'] in rel['prov'] or vrf in rel['prov_any']
            d_cons = d['dn'] in rel['cons'] or d['vrf'] in rel['cons_any']
            d_prov = d['dn'] in rel['prov'] or d['vrf'] in rel['prov_any']
            fwd, rev = s_cons and d_prov, s_prov and d_cons
            if not (fwd or rev):
                continue
            ca = self.A(brc)
            if ca['scope'] == 'application-profile' and (s['ap'] is None or s['ap'] != d['ap']):
                continue
            if ca['scope'] == 'context' and s['vrf'] != d['vrf']:
                continue
            if ca['scope'] == 'tenant' and s['tenant'] != d['tenant']:
                continue
            for subj in self.kids(brc, 'vzSubj'):
                sa = self.A(subj)
                for rf, dirn in self.subj_filters(subj):
                    rfa = self.A(rf)
                    if rfa['state'] != 'formed':
                        continue
                    swap = dirn == 'both' and sa['revFltPorts'] == 'yes'
                    for e in self.kids(rfa['tDn'], 'vzEntry'):
                        ea = self.A(e)
                        where = '%s / %s / %s / %s' % (self.short(brc), sa['name'], self.A(rfa['tDn'])['name'],
                                                       ea['name'])
                        if fwd and dirn != 'p2c' and self._entry_match(ea, proto, sport, dport, flags, False):
                            hits.append((rfa['action'], where + ' (Consumer -> Provider)', subj, 'c2p', brc, rfa['tDn'], e,
                                         rule_prio(s['dn'] in rel['cons'], d['dn'] in rel['prov'], entry_is_any(ea),
                                                   is_global(s) or is_global(d)), rf))
                        if not rev or dirn == 'c2p':
                            continue
                        # stateful: Provider -> Consumer nur TCP mit ACK (Antworten), kein Verbindungsaufbau vom Provider
                        if ea.get('stateful') == 'yes' and (proto != 'tcp' or flags != 'ack'):
                            continue
                        if self._entry_match(ea, proto, sport, dport, flags, swap):
                            hits.append((rfa['action'], where + ' (Provider -> Consumer%s)'
                                         % (', Ports getauscht' if swap else ', eigener Filter' if dirn == 'p2c' else ''),
                                         subj, 'p2c', brc, rfa['tDn'], e,
                                         rule_prio(s['dn'] in rel['prov'], d['dn'] in rel['cons'], entry_is_any(ea),
                                                   is_global(s) or is_global(d)), rf))
        # Zoning-Rule-Prioritaet (Contract Guide, Table 8): kleinere Zahl gewinnt. Preferred Group: Permit any-any (20);
        # ist eine Seite kein Mitglied, greifen die impliziten Denies src_any_any_deny(18) / any_dest_any_deny(19).
        if pref_on:
            if s['pref'] and d['pref']:
                hits = [h for h in hits if h[7][0] < 20]
                if not hits:
                    return self._decide('POLICY_PREFERRED_GROUP', 'permit', 'Beide sind Mitglied der Preferred Group '
                                        '(grp_any_any_any_permit(20))', {'vrf': vrf})
            else:
                hits = [h for h in hits if h[7][0] < 18]
                if not hits:
                    return self._decide('POLICY_IMPLICIT_DENY', 'deny', 'Preferred Group aktiv, %s ist kein Mitglied: '
                                        'implizites Deny (grp_src_any_any_deny(18) / grp_any_dest_any_deny(19))'
                                        % self.short((d if s['pref'] else s)['dn']), {'vrf': vrf})
        if hits:
            best = min(h[7][0] for h in hits)
            top = [h for h in hits if h[7][0] == best]
            prio = ' [%s]' % top[0][7][1]
            # gleicher Filter: Deny+Log vor Deny (Contract Guide, Priorities between actions) - beides verwirft
            deny = sorted([h for h in top if h[0] == 'deny'], key=lambda h: 0 if has_log(self.A(h[8])) else 1)
            if deny:
                # gleiche Zoning-Rule-Prioritaet: Deny gewinnt, auch gegen einen spezifischeren Permit-Filter
                return self._decide('POLICY_DENY_RULE', 'deny', 'Deny-Filter%s: %s%s' % (
                    ' (log)' if has_log(self.A(deny[0][8])) else '', deny[0][1], prio), self._rule(deny[0]))
            # Redirect gegen Permit: spezifischerer Filter gewinnt (Table 23), bei gleicher Filter-Prioritaet Redirect
            graphs = getattr(self, 'graphs', {})
            key = lambda h: (filter_prio(self.A(h[6])), 0 if (graphs.get(h[2]) or {}).get('state') == 'applied' else 1)
            h0 = min(top, key=key)
            self.last_hit = (h0[2], h0[3])
            return self._decide('POLICY_CONTRACT_PERMIT', 'permit', 'Contract: ' + h0[1] + prio, self._rule(h0))
        return self._decide('POLICY_IMPLICIT_DENY', 'deny', 'Implicit Deny: kein Contract mit passendem Filter zwischen %s und %s' % (
            self.short(s['dn']), self.short(d['dn'])))

    def subj_filters(self, subj):
        """Filter eines Subjects mit Richtung: 'both' (Apply Both Directions, vzRsSubjFiltAtt), 'c2p' (vzInTerm),
        'p2c' (vzOutTerm). Ohne Apply Both Directions gilt jede Richtung nur mit ihren eigenen Filtern, ohne Port-Tausch."""
        out = [(rf, 'both') for rf in self.kids(subj, 'vzRsSubjFiltAtt')]
        for term, dirn in (('/intmnl', 'c2p'), ('/outtmnl', 'p2c')):
            if self.has(subj + term):
                out += [(rf, dirn) for rf in self.kids(subj + term, 'vzRsFiltAtt')]
        return out

    def _rule(self, h):
        """Angewandte Regel als Objektreferenzen."""
        return {'contract': h[4], 'subject': h[2], 'filter': h[5], 'entry': h[6], 'direction': h[3]}
