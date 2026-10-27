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


def discovered_members():
    """fabricNodeIdentP-Eintraege fuer eine fertig registrierte Fabric."""
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
