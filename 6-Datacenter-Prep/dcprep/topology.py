"""Physische Standard-Topologie und Grundkonfiguration eines frischen APIC."""
from .model import create_obj, now_ts

LEAF_MODEL = 'N9K-C93180YC-FX'
SPINE_MODEL = 'N9K-C9332C'


def default_topology():
    """1 APIC, 2 Spines, 4 Leafs. Uplinks: eth1/49 -> spine201, eth1/50 -> spine202.
    Der APIC haengt an leaf101 und leaf102 jeweils auf eth1/48."""
    nodes = [
        {'serial': 'SAL1931LA01', 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf101'},
        {'serial': 'SAL1931LA02', 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf102'},
        {'serial': 'SAL1931LA03', 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf103'},
        {'serial': 'SAL1931LA04', 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf104'},
        {'serial': 'FDO2219SP01', 'model': SPINE_MODEL, 'role': 'spine', 'ports': 32, 'hint': 'spine201'},
        {'serial': 'FDO2219SP02', 'model': SPINE_MODEL, 'role': 'spine', 'ports': 32, 'hint': 'spine202'},
    ]
    links = []
    for i, leaf in enumerate(['SAL1931LA01', 'SAL1931LA02', 'SAL1931LA03', 'SAL1931LA04']):
        links.append([leaf, 'eth1/49', 'FDO2219SP01', 'eth1/%d' % (i + 1)])
        links.append([leaf, 'eth1/50', 'FDO2219SP02', 'eth1/%d' % (i + 1)])
    links.append(['APIC1', 'eth2-1', 'SAL1931LA01', 'eth1/48'])
    links.append(['APIC1', 'eth2-2', 'SAL1931LA02', 'eth1/48'])
    return {'pod': 1, 'apic': {'serial': 'APIC1', 'name': 'apic1', 'id': 1, 'model': 'APIC-SERVER-M3'},
            'nodes': nodes, 'links': links}


def multipod_topology():
    """Zwei Pods ueber ein IPN plus ein Remote Leaf hinter einem WAN-Router.
    Pod 2: spine203/204 (eth1/1-2 zu leaf105/106), IPN an Spine-Port eth1/32.
    Remote Leaf leaf301 haengt mit eth1/54 am WAN-Router wan-rl."""
    t = default_topology()
    t['nodes'] += [
        {'serial': 'SAL1931LA05', 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf105', 'pod': 2},
        {'serial': 'SAL1931LA06', 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf106', 'pod': 2},
        {'serial': 'FDO2219SP03', 'model': SPINE_MODEL, 'role': 'spine', 'ports': 32, 'hint': 'spine203', 'pod': 2},
        {'serial': 'FDO2219SP04', 'model': SPINE_MODEL, 'role': 'spine', 'ports': 32, 'hint': 'spine204', 'pod': 2},
        {'serial': 'SAL1931RL01', 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf301', 'pod': 1, 'remote': True},
    ]
    for i, leaf in enumerate(['SAL1931LA05', 'SAL1931LA06']):
        t['links'].append([leaf, 'eth1/49', 'FDO2219SP03', 'eth1/%d' % (i + 1)])
        t['links'].append([leaf, 'eth1/50', 'FDO2219SP04', 'eth1/%d' % (i + 1)])
    t['ipnlinks'] = [['FDO2219SP01', 'eth1/32', 'ipn1', 'Eth1/1'], ['FDO2219SP02', 'eth1/32', 'ipn1', 'Eth1/2'],
                     ['FDO2219SP03', 'eth1/32', 'ipn2', 'Eth1/1'], ['FDO2219SP04', 'eth1/32', 'ipn2', 'Eth1/2'],
                     ['SAL1931RL01', 'eth1/54', 'wan-rl', 'Gi0/1']]
    t['kind'] = 'multipod'
    return t


def default_ipn():
    """Startkonfiguration der IPN- und WAN-Router (Simulation > IPN & WAN)."""
    return {'routers': [
        {'name': 'ipn1', 'pod': 1, 'kind': 'ipn', 'mtu': 9150, 'area': '0.0.0.0', 'pim': True, 'rp': '192.168.100.1', 'relay': [],
         'down': False, 'ifs': [{'serial': 'FDO2219SP01', 'port': 'eth1/32', 'vlan': 4, 'ip': '192.168.1.2/30'},
                                {'serial': 'FDO2219SP02', 'port': 'eth1/32', 'vlan': 4, 'ip': '192.168.1.6/30'}]},
        {'name': 'ipn2', 'pod': 2, 'kind': 'ipn', 'mtu': 9150, 'area': '0.0.0.0', 'pim': True, 'rp': '192.168.100.1', 'relay': [],
         'down': False, 'ifs': [{'serial': 'FDO2219SP03', 'port': 'eth1/32', 'vlan': 4, 'ip': '192.168.2.2/30'},
                                {'serial': 'FDO2219SP04', 'port': 'eth1/32', 'vlan': 4, 'ip': '192.168.2.6/30'}]},
        {'name': 'wan-rl', 'pod': 1, 'kind': 'wan', 'mtu': 9150, 'area': '0.0.0.0', 'pim': False, 'rp': '', 'relay': [],
         'down': False, 'ifs': [{'serial': 'SAL1931RL01', 'port': 'eth1/54', 'vlan': 4, 'ip': '192.168.3.2/30'}]}]}


SPINE_MODEL_64 = 'N9K-C9364C'
LIMITS = {'pods': 4, 'spines': 6, 'leafs': 40, 'remote': 8}


def node_ids(pod, role, i):
    """Vorgeschlagene Node-IDs: Pod 1 leaf101.., spine201..; Pod p: p*1000+100+i bzw. +200+i; Remote Leafs 3901.."""
    if role == 'remote':
        return 3900 + i
    base = 0 if pod == 1 else (pod - 1) * 1000
    return base + (100 if role == 'leaf' else 200) + i


def build_topology(spec):
    """Topologie aus einer Beschreibung: {'pods': [{'spines': 2, 'leafs': 4}, ...], 'remote': 0}."""
    pods = spec.get('pods') or [{'spines': 2, 'leafs': 4}]
    if not 1 <= len(pods) <= LIMITS['pods']:
        raise ValueError('1 bis %d Pods' % LIMITS['pods'])
    remote = int(spec.get('remote') or 0)
    if not 0 <= remote <= LIMITS['remote']:
        raise ValueError('0 bis %d Remote Leafs' % LIMITS['remote'])
    nodes, links, ipnlinks = [], [], []
    multi = len(pods) > 1 or remote > 0
    for pi, pd in enumerate(pods):
        pod = pi + 1
        ns, nl = int(pd.get('spines') or 0), int(pd.get('leafs') or 0)
        if not 1 <= ns <= LIMITS['spines'] or not 1 <= nl <= LIMITS['leafs']:
            raise ValueError('Pod %d: 1 bis %d Spines und 1 bis %d Leafs' % (pod, LIMITS['spines'], LIMITS['leafs']))
        big = nl > 31
        sports = 64 if big else 32
        lser = [('SAL1931LA%02d' if pod == 1 else 'SAL193%dLA%%02d' % pod) % (i + 1) for i in range(nl)]
        sser = [('FDO2219SP%02d' if pod == 1 else 'FDO222%dSP%%02d' % pod) % (i + 1) for i in range(ns)]
        for i, s_ in enumerate(lser):
            nid = node_ids(pod, 'leaf', i + 1)
            nodes.append({'serial': s_, 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf%d' % nid, 'nid': nid, 'pod': pod})
        for i, s_ in enumerate(sser):
            nid = node_ids(pod, 'spine', i + 1)
            nodes.append({'serial': s_, 'model': SPINE_MODEL_64 if big else SPINE_MODEL, 'role': 'spine', 'ports': sports, 'hint': 'spine%d' % nid,
                          'nid': nid, 'pod': pod})
        for li, l in enumerate(lser):
            for si, sp in enumerate(sser):
                links.append([l, 'eth1/%d' % (49 + si), sp, 'eth1/%d' % (li + 1)])
        if multi:
            for si, sp in enumerate(sser):
                ipnlinks.append([sp, 'eth1/%d' % sports, 'ipn%d' % pod, 'Eth1/%d' % (si + 1)])
    for i in range(remote):
        s_ = 'SAL1939RL%02d' % (i + 1)
        nid = node_ids(1, 'remote', i + 1)
        nodes.append({'serial': s_, 'model': LEAF_MODEL, 'role': 'leaf', 'ports': 54, 'hint': 'leaf%d' % nid, 'nid': nid, 'pod': 1, 'remote': True})
        ipnlinks.append([s_, 'eth1/54', 'wan-rl', 'Gi0/%d' % (i + 1)])
    p1 = [n['serial'] for n in nodes if n['pod'] == 1 and n['role'] == 'leaf' and not n.get('remote')]
    for k, l in enumerate(p1[:2]):
        links.append(['APIC1', 'eth2-%d' % (k + 1), l, 'eth1/48'])
    t = {'pod': 1, 'apic': {'serial': 'APIC1', 'name': 'apic1', 'id': 1, 'model': 'APIC-SERVER-M3'}, 'nodes': nodes, 'links': links,
         'kind': 'custom', 'spec': {'pods': [{'spines': int(p_['spines']), 'leafs': int(p_['leafs'])} for p_ in pods], 'remote': remote}}
    if ipnlinks:
        t['ipnlinks'] = ipnlinks
    return t


def build_ipn(topo, relay=()):
    """IPN-Router je Pod und WAN-Router fuer Remote Leafs passend zu ipnlinks."""
    routers = {}
    for s_, p_, rname, rport in topo.get('ipnlinks', []):
        n = next(x for x in topo['nodes'] if x['serial'] == s_)
        r = routers.setdefault(rname, {'name': rname, 'pod': n['pod'], 'kind': 'wan' if rname == 'wan-rl' else 'ipn', 'mtu': 9150,
                                       'area': '0.0.0.0', 'pim': rname != 'wan-rl', 'rp': '' if rname == 'wan-rl' else '192.168.250.1',
                                       'relay': list(relay), 'down': False, 'ifs': []})
        k = len(r['ifs'])
        net = 100 if rname == 'wan-rl' else n['pod']
        r['ifs'].append({'serial': s_, 'port': p_, 'vlan': 4, 'ip': '192.168.%d.%d/30' % (net, 4 * k + 2)})
    return {'routers': list(routers.values())}


def infra_config(topo):
    """Multi-Pod/Remote-Leaf-Grundkonfiguration passend zu build_topology/build_ipn (APIC-JSON, Liste von (url, body))."""
    out = []
    pods = sorted({n['pod'] for n in topo['nodes']})
    for p_ in pods:
        if p_ > 1:
            out.append(('uni/controller/setuppol', {'fabricSetupPol': {'attributes': {}, 'children': [
                {'fabricSetupP': {'attributes': {'podId': str(p_), 'tepPool': '10.%d.0.0/16' % (p_ - 1)}}}]}}))
    rls = [n for n in topo['nodes'] if n.get('remote')]
    if rls:
        out.append(('uni/controller/setuppol/setupp-1', {'fabricSetupP': {'attributes': {}, 'children': [
            {'fabricExtSetupP': {'attributes': {'remoteId': '11', 'tepPool': '10.11.0.0/20'}}}]}}))
    ipn = build_ipn(topo)
    nodes_kids, lifs = [], []
    for r in ipn['routers']:
        for i in r['ifs']:
            n = next(x for x in topo['nodes'] if x['serial'] == i['serial'])
            nid = n['nid']
            ip = i['ip'].rsplit('.', 1)
            mine = '%s.%d/30' % (ip[0], int(ip[1].split('/')[0]) - 1)
            nodes_kids.append({'l3extRsNodeL3OutAtt': {'attributes': {'tDn': 'topology/pod-%d/node-%d' % (n['pod'], nid),
                                                                       'rtrId': '%d.%d.%d.%d' % (n['pod'], nid // 256, nid % 256, 1)}}})
            lifs.append({'l3extLIfP': {'attributes': {'name': 'ipn-%d' % nid}, 'children': [
                {'ospfIfP': {'attributes': {}}},
                {'l3extRsPathL3OutAtt': {'attributes': {'tDn': 'topology/pod-%d/paths-%d/pathep-[%s]' % (n['pod'], nid, i['port']),
                                                        'ifInstT': 'sub-interface', 'encap': 'vlan-4', 'addr': mine}}}]}})
    if not nodes_kids:
        return out
    conn = [{'fabricPeeringP': {'attributes': {'type': 'automatic_with_full_mesh'}}}]
    for p_ in pods:
        kids = [{'fabricIp': {'attributes': {'addr': '172.16.%d.1/32' % p_}}}]
        if p_ == 1 and rls:
            kids.append({'fabricExtRoutablePodSubnet': {'attributes': {'pool': '172.16.10.0/24'}}})
        conn.append({'fabricPodConnP': {'attributes': {'id': str(p_)}, 'children': kids}})
    out.append(('uni/tn-infra', {'fvTenant': {'attributes': {}, 'children': [
        {'l3extOut': {'attributes': {'name': 'multipod'}, 'children': [
            {'l3extRsEctx': {'attributes': {'tnFvCtxName': 'overlay-1'}}}, {'ospfExtP': {'attributes': {'areaId': '0.0.0.0'}}},
            {'bgpExtP': {'attributes': {}}}, {'l3extLNodeP': {'attributes': {'name': 'infra-nodes'}, 'children': nodes_kids + lifs}}]}},
        {'fabricExtConnP': {'attributes': {'id': '1', 'name': 'Multipod'}, 'children': conn}}]}}))
    return out


def discovered_members(topo=None):
    """fabricNodeIdentP-Eintraege fuer eine fertig registrierte Fabric."""
    if topo and topo.get('kind') == 'custom':
        out = []
        for n in topo['nodes']:
            a = {'serial': n['serial'], 'nodeId': str(n['nid']), 'name': n['hint'], 'podId': str(n['pod'])}
            if n.get('remote'):
                a.update(nodeType='remote-leaf-wan', extPoolId='11')
            out.append({'fabricNodeIdentP': {'attributes': a}})
        return out
    ids = {'SAL1931LA01': (101, 'leaf101'), 'SAL1931LA02': (102, 'leaf102'),
           'SAL1931LA03': (103, 'leaf103'), 'SAL1931LA04': (104, 'leaf104'),
           'FDO2219SP01': (201, 'spine201'), 'FDO2219SP02': (202, 'spine202')}
    return [{'fabricNodeIdentP': {'attributes': {'serial': s, 'nodeId': str(i), 'name': n, 'podId': '1'}}}
            for s, (i, n) in ids.items()]


def base_config(store, admin_pwd):
    ts = now_ts()
    store.objs.clear(); store.kids.clear(); store.idx.clear()
    store.counters.update({'vnid': 0, 'seg': 0, 'pctag': 0})
    store.add('', 'topRoot', {})
    for dn, cls in [('uni', 'polUni'), ('uni/infra', 'infraInfra'), ('uni/infra/funcprof', 'infraFuncP'),
                    ('uni/fabric', 'fabricInst'), ('uni/fabric/protpol', 'fabricProtPol'),
                    ('uni/controller', 'ctrlrInst'), ('uni/controller/nodeidentpol', 'fabricNodeIdentPol'),
                    ('uni/userext', 'aaaUserEp')]:
        create_obj(store, dn, cls, {}, ts)
    create_obj(store, 'uni/userext/user-admin', 'aaaUser', {'name': 'admin', 'pwd': admin_pwd}, ts)

    for t in ('common', 'infra', 'mgmt'):
        create_obj(store, 'uni/tn-%s' % t, 'fvTenant', {'name': t}, ts)
    c = 'uni/tn-common'
    create_obj(store, c + '/ctx-default', 'fvCtx', {'name': 'default'}, ts)
    create_obj(store, c + '/BD-default', 'fvBD', {'name': 'default'}, ts)
    for name, entry in [('default', {'etherT': 'unspecified'}),
                        ('arp', {'etherT': 'arp', 'arpOpc': 'unspecified'}),
                        ('icmp', {'etherT': 'ip', 'prot': 'icmp'}),
                        ('est', {'etherT': 'ip', 'prot': 'tcp', 'tcpRules': 'est'})]:
        create_obj(store, c + '/flt-' + name, 'vzFilter', {'name': name}, ts)
        e = {'name': name}
        e.update(entry)
        create_obj(store, c + '/flt-%s/e-%s' % (name, name), 'vzEntry', e, ts)
    create_obj(store, c + '/brc-default', 'vzBrCP', {'name': 'default'}, ts)
    create_obj(store, c + '/brc-default/subj-default', 'vzSubj', {'name': 'default'}, ts)
    create_obj(store, c + '/brc-default/subj-default/rssubjFiltAtt-default', 'vzRsSubjFiltAtt',
               {'tnVzFilterName': 'default'}, ts)
    create_obj(store, c + '/ospfIfPol-default', 'ospfIfPol', {'name': 'default'}, ts)
    create_obj(store, c + '/eigrpIfPol-default', 'eigrpIfPol', {'name': 'default'}, ts)
    create_obj(store, c + '/bfdIfPol-default', 'bfdIfPol', {'name': 'default'}, ts)
    create_obj(store, c + '/bgpCtxP-default', 'bgpCtxPol', {'name': 'default'}, ts)
    create_obj(store, 'uni/tn-mgmt/ctx-oob', 'fvCtx', {'name': 'oob'}, ts)
    create_obj(store, 'uni/tn-mgmt/ctx-inb', 'fvCtx', {'name': 'inb'}, ts)
    create_obj(store, 'uni/tn-infra/ctx-overlay-1', 'fvCtx', {'name': 'overlay-1'}, ts)

    i = 'uni/infra'
    create_obj(store, i + '/cdpIfP-default', 'cdpIfPol', {'name': 'default', 'adminSt': 'disabled'}, ts)
    create_obj(store, i + '/lldpIfP-default', 'lldpIfPol', {'name': 'default'}, ts)
    create_obj(store, i + '/lacplagp-default', 'lacpLagPol', {'name': 'default'}, ts)
    create_obj(store, i + '/hintfpol-default', 'fabricHIfPol', {'name': 'default'}, ts)
    create_obj(store, 'uni/fabric/bgpInstP-default', 'bgpInstPol', {'name': 'default'}, ts)
    create_obj(store, 'uni/fabric/bgpInstP-default/rr', 'bgpRRP', {}, ts)
    f = 'uni/fabric'
    create_obj(store, f + '/outofsvc', 'fabricOOServicePol', {}, ts)
    create_obj(store, f + '/funcprof', 'fabricFuncP', {}, ts)
    create_obj(store, f + '/time-default', 'datetimePol', {'name': 'default'}, ts)
    create_obj(store, f + '/podprof-default', 'fabricPodP', {'name': 'default'}, ts)
    create_obj(store, f + '/podprof-default/pods-default-typ-ALL', 'fabricPodS', {'name': 'default', 'type': 'ALL'}, ts)
    create_obj(store, f + '/podprof-default/pods-default-typ-ALL/rspodPGrp', 'fabricRsPodPGrp', {'tDn': ''}, ts)
    create_obj(store, 'uni/vmmp-VMware', 'vmmProvP', {'vendor': 'VMware'}, ts)
    create_obj(store, 'uni/tn-mgmt/mgmtp-default', 'mgmtMgmtP', {'name': 'default'}, ts)
    create_obj(store, 'uni/tn-mgmt/mgmtp-default/oob-default', 'mgmtOoB', {'name': 'default'}, ts)
    _aaa_base(store, ts)


AAA_BASE = [
    ('uni/userext/tacacsext', 'aaaTacacsPlusEp', {}),
    ('uni/userext/radiusext', 'aaaRadiusEp', {}),
    ('uni/userext/ldapext', 'aaaLdapEp', {}),
    ('uni/userext/authrealm', 'aaaAuthRealm', {}),
    ('uni/userext/authrealm/defaultauth', 'aaaDefaultAuth', {'realm': 'local'}),
    ('uni/userext/authrealm/consoleauth', 'aaaConsoleAuth', {'realm': 'local'}),
    ('uni/userext/logindomain-fallback', 'aaaLoginDomain', {'name': 'fallback'}),
    ('uni/userext/logindomain-fallback/domainauth', 'aaaDomainAuth', {'realm': 'local'}),
    ('uni/userext/domain-all', 'aaaDomain', {'name': 'all'}),
    ('uni/userext/domain-common', 'aaaDomain', {'name': 'common'}),
    ('uni/userext/domain-mgmt', 'aaaDomain', {'name': 'mgmt'}),
    ('uni/userext/user-admin/userdomain-all', 'aaaUserDomain', {'name': 'all'}),
    ('uni/userext/user-admin/userdomain-all/role-admin', 'aaaUserRole', {'name': 'admin', 'privType': 'writePriv'}),
    ('uni/tn-mgmt/BD-inb', 'fvBD', {'name': 'inb'}),
    ('uni/tn-mgmt/BD-inb/rsctx', 'fvRsCtx', {'tnFvCtxName': 'inb'}),
]


OPS_BASE = [
    ('uni/controller/setuppol', 'fabricSetupPol', {}),
    ('uni/controller/setuppol/setupp-1', 'fabricSetupP', {'podId': '1', 'tepPool': '10.0.0.0/16'}),
    ('uni/fabric/fwrepop', 'firmwareRepoP', {}),
    ('uni/controller/ctrlrfwpol', 'firmwareCtrlrFwP', {}),
    ('uni/controller/ctrlrmaintpol', 'maintCtrlrMaintP', {}),
    ('uni/exportcryptkey', 'pkiExportEncryptionKey', {}),
    ('uni/fabric/moncommon', 'monCommonPol', {}),
    ('uni/infra/qosinst-default', 'qosInstPol', {'name': 'default'}),
] + [x for i in range(1, 7) for x in (
    ('uni/infra/qosinst-default/class-level%d' % i, 'qosClass', {'prio': 'level%d' % i}),
    ('uni/infra/qosinst-default/class-level%d/sched' % i, 'qosSched', {'bw': '20' if i <= 3 else '0'}))] + [
    ('uni/infra/mcpInstP-default', 'mcpInstPol', {'name': 'default'}),
    ('uni/infra/mcpIfP-default', 'mcpIfPol', {'name': 'default'}),
    ('uni/infra/epLoopProtectP-default', 'epLoopProtectP', {'name': 'default'}),
]


def _aaa_base(store, ts):
    for dn, cls, attrs in AAA_BASE + OPS_BASE:
        if dn not in store.objs and parent_ok(store, dn):
            create_obj(store, dn, cls, attrs, ts)


def ensure_base(store):
    """Ergaenzt Systemobjekte, die in aelteren gespeicherten Zustaenden fehlen."""
    ts = now_ts()
    for dn, cls, attrs in [
            ('uni/vmmp-VMware', 'vmmProvP', {'vendor': 'VMware'}),
            ('uni/tn-common/eigrpIfPol-default', 'eigrpIfPol', {'name': 'default'}),
            ('uni/tn-common/bfdIfPol-default', 'bfdIfPol', {'name': 'default'}),
            ('uni/tn-common/bgpCtxP-default', 'bgpCtxPol', {'name': 'default'}),
            ('uni/fabric/outofsvc', 'fabricOOServicePol', {}),
            ('uni/fabric/funcprof', 'fabricFuncP', {}),
            ('uni/fabric/time-default', 'datetimePol', {'name': 'default'}),
            ('uni/fabric/podprof-default', 'fabricPodP', {'name': 'default'}),
            ('uni/fabric/podprof-default/pods-default-typ-ALL', 'fabricPodS', {'name': 'default', 'type': 'ALL'}),
            ('uni/fabric/podprof-default/pods-default-typ-ALL/rspodPGrp', 'fabricRsPodPGrp', {'tDn': ''}),
            ('uni/tn-mgmt/mgmtp-default', 'mgmtMgmtP', {'name': 'default'}),
            ('uni/tn-mgmt/mgmtp-default/oob-default', 'mgmtOoB', {'name': 'default'})]:
        if dn not in store.objs and parent_ok(store, dn):
            create_obj(store, dn, cls, attrs, ts)
    _aaa_base(store, ts)


def parent_ok(store, dn):
    from .model import parent_dn
    return parent_dn(dn) in store.objs
