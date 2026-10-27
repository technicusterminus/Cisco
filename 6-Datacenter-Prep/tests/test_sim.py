"""Tests fuer Datacenter Prep: python3 -m unittest discover -s tests"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dcprep.server import Sim, serve  # noqa: E402
from dcprep.model import post, AciError  # noqa: E402
from dcprep import trace  # noqa: E402
from dcprep.cli import Cli  # noqa: E402

ACCESS = {"polUni": {"attributes": {}, "children": [
    {"infraInfra": {"attributes": {}, "children": [
        {"fvnsVlanInstP": {"attributes": {"name": "VP", "allocMode": "static"}, "children": [
            {"fvnsEncapBlk": {"attributes": {"from": "vlan-10", "to": "vlan-99"}}}]}},
        {"fvnsVlanInstP": {"attributes": {"name": "VP-L3", "allocMode": "static"}, "children": [
            {"fvnsEncapBlk": {"attributes": {"from": "vlan-300", "to": "vlan-310"}}}]}},
        {"infraAttEntityP": {"attributes": {"name": "AAEP"}, "children": [
            {"infraRsDomP": {"attributes": {"tDn": "uni/phys-PD"}}},
            {"infraRsDomP": {"attributes": {"tDn": "uni/l3dom-L3D"}}}]}},
        {"lacpLagPol": {"attributes": {"name": "LACP-Active", "mode": "active"}}},
        {"infraFuncP": {"attributes": {}, "children": [
            {"infraAccPortGrp": {"attributes": {"name": "SRV"}, "children": [
                {"infraRsAttEntP": {"attributes": {"tDn": "uni/infra/attentp-AAEP"}}}]}},
            {"infraAccBndlGrp": {"attributes": {"name": "VPC-DB", "lagT": "node"}, "children": [
                {"infraRsAttEntP": {"attributes": {"tDn": "uni/infra/attentp-AAEP"}}},
                {"infraRsLacpPol": {"attributes": {"tnLacpLagPolName": "LACP-Active"}}}]}}]}},
        {"infraAccPortP": {"attributes": {"name": "IFP"}, "children": [
            {"infraHPortS": {"attributes": {"name": "srv", "type": "range"}, "children": [
                {"infraPortBlk": {"attributes": {"name": "b", "fromPort": "1", "toPort": "10"}}},
                {"infraRsAccBaseGrp": {"attributes": {"tDn": "uni/infra/funcprof/accportgrp-SRV"}}}]}},
            {"infraHPortS": {"attributes": {"name": "db", "type": "range"}, "children": [
                {"infraPortBlk": {"attributes": {"name": "b", "fromPort": "20", "toPort": "20"}}},
                {"infraRsAccBaseGrp": {"attributes": {"tDn": "uni/infra/funcprof/accbundle-VPC-DB"}}}]}},
            {"infraHPortS": {"attributes": {"name": "wan", "type": "range"}, "children": [
                {"infraPortBlk": {"attributes": {"name": "b", "fromPort": "47", "toPort": "47"}}},
                {"infraRsAccBaseGrp": {"attributes": {"tDn": "uni/infra/funcprof/accportgrp-SRV"}}}]}}]}},
        {"infraNodeP": {"attributes": {"name": "ALL"}, "children": [
            {"infraLeafS": {"attributes": {"name": "s", "type": "range"}, "children": [
                {"infraNodeBlk": {"attributes": {"name": "b", "from_": "101", "to_": "104"}}}]}},
            {"infraRsAccPortP": {"attributes": {"tDn": "uni/infra/accportprof-IFP"}}}]}}]}},
    {"physDomP": {"attributes": {"name": "PD"}, "children": [
        {"infraRsVlanNs": {"attributes": {"tDn": "uni/infra/vlanns-[VP]-static"}}}]}},
    {"l3extDomP": {"attributes": {"name": "L3D"}, "children": [
        {"infraRsVlanNs": {"attributes": {"tDn": "uni/infra/vlanns-[VP-L3]-static"}}}]}},
]}}


def tenant(extra_epg_children=None):
    web = [{"fvRsBd": {"attributes": {"tnFvBDName": "BD1"}}},
           {"fvRsDomAtt": {"attributes": {"tDn": "uni/phys-PD"}}},
           {"fvRsPathAtt": {"attributes": {"tDn": "topology/pod-1/paths-101/pathep-[eth1/1]", "encap": "vlan-10"}}},
           {"fvRsProv": {"attributes": {"tnVzBrCPName": "web"}}}]
    return {"fvTenant": {"attributes": {"name": "T"}, "children": [
        {"fvCtx": {"attributes": {"name": "V"}}},
        {"fvBD": {"attributes": {"name": "BD1"}, "children": [
            {"fvRsCtx": {"attributes": {"tnFvCtxName": "V"}}},
            {"fvSubnet": {"attributes": {"ip": "10.1.1.1/24", "scope": "public"}}},
            {"fvRsBDToOut": {"attributes": {"tnL3extOutName": "WAN"}}}]}},
        {"fvBD": {"attributes": {"name": "BD2"}, "children": [
            {"fvRsCtx": {"attributes": {"tnFvCtxName": "V"}}},
            {"fvSubnet": {"attributes": {"ip": "10.1.2.1/24"}}}]}},
        {"vzFilter": {"attributes": {"name": "http"}, "children": [
            {"vzEntry": {"attributes": {"name": "80", "etherT": "ip", "prot": "tcp", "dFromPort": "http",
                                        "dToPort": "http"}}}]}},
        {"vzBrCP": {"attributes": {"name": "web"}, "children": [
            {"vzSubj": {"attributes": {"name": "s"}, "children": [
                {"vzRsSubjFiltAtt": {"attributes": {"tnVzFilterName": "http"}}},
                {"vzRsSubjFiltAtt": {"attributes": {"tnVzFilterName": "icmp"}}}]}}]}},
        {"fvAp": {"attributes": {"name": "A"}, "children": [
            {"fvAEPg": {"attributes": {"name": "Web"}, "children": web + (extra_epg_children or [])}},
            {"fvAEPg": {"attributes": {"name": "Cli"}, "children": [
                {"fvRsBd": {"attributes": {"tnFvBDName": "BD2"}}},
                {"fvRsDomAtt": {"attributes": {"tDn": "uni/phys-PD"}}},
                {"fvRsPathAtt": {"attributes": {"tDn": "topology/pod-1/paths-102/pathep-[eth1/2]", "encap": "vlan-20"}}},
                {"fvRsCons": {"attributes": {"tnVzBrCPName": "web"}}}]}}]}}]}}


HOSTS = [
    {'name': 'web1', 'mac': '00:50:56:00:00:01', 'ip': '10.1.1.10/24', 'gw': '10.1.1.1', 'vlan': 10,
     'links': [['SAL1931LA01', 'eth1/1']], 'bond': 'none'},
    {'name': 'cli1', 'mac': '00:50:56:00:00:02', 'ip': '10.1.2.10/24', 'gw': '10.1.2.1', 'vlan': 20,
     'links': [['SAL1931LA02', 'eth1/2']], 'bond': 'none'},
]


class Base(unittest.TestCase):
    def setUp(self):
        self.S = Sim(tempfile.mkdtemp(), 'admin')
        self.st = self.S.store
        self.e = self.S.engine

    def apply(self, *trees, hosts=None, routers=None):
        for t in trees:
            post(self.st, 'uni', t)
        if hosts is not None:
            self.S.sim['hosts'] = json.loads(json.dumps(hosts))
        if routers is not None:
            self.S.sim['routers'] = json.loads(json.dumps(routers))
        self.S.changed()

    def faults(self, under=''):
        return [(d, self.st.attrs(d)['code'], self.st.attrs(d)['descr']) for d in self.st.by_class('faultInst')
                if d.startswith(under)]

    def traffic(self, src, dst, proto='icmp', port=0):
        return trace.run(self.e, self.S.sim, src, dst, proto, port)


class TestModel(Base):
    def test_naming_and_validation(self):
        with self.assertRaises(AciError) as c:
            post(self.st, 'uni', {"fvTenant": {"attributes": {"name": "bad name"}}})
        self.assertEqual(c.exception.code, '801')
        with self.assertRaises(AciError) as c:
            post(self.st, 'uni', {"fvFoo": {"attributes": {"name": "x"}}})
        self.assertEqual(c.exception.code, '122')
        from dcprep import model
        model.STRICT = True
        try:
            with self.assertRaises(AciError):
                post(self.st, 'uni', {"fvTenant": {"attributes": {"name": "x", "foo": "1"}}})
        finally:
            model.STRICT = False
        post(self.st, 'uni', {"fvTenant": {"attributes": {"name": "x", "foo": "1"}, "children": [
            {"fvRsTenantMonPol": {"attributes": {"tnMonEPGPolName": ""}}}]}})
        with self.assertRaises(AciError):  # Eltern fehlen
            post(self.st, 'uni/tn-nope', {"fvBD": {"attributes": {"name": "b"}}})
        post(self.st, 'uni/tn-X', {"fvTenant": {"attributes": {"name": "X"}}})
        self.assertIn('uni/tn-X', self.st.objs)

    def test_atomic(self):
        bad = {"fvTenant": {"attributes": {"name": "Y"}, "children": [
            {"fvCtx": {"attributes": {"name": "ok"}}}, {"fvBD": {"attributes": {"name": "b", "arpFlood": "maybe"}}}]}}
        with self.assertRaises(AciError):
            post(self.st, 'uni', bad)
        self.assertNotIn('uni/tn-Y', self.st.objs)

    def test_implicit_defaults(self):
        self.apply({"fvTenant": {"attributes": {"name": "Z"}, "children": [
            {"fvBD": {"attributes": {"name": "b"}}}]}})
        rs = self.st.attrs('uni/tn-Z/BD-b/rsctx')
        self.assertEqual(rs['tDn'], 'uni/tn-common/ctx-default')
        self.assertEqual(rs['state'], 'formed')


class TestDeploy(Base):
    def test_contract_and_endpoints(self):
        self.apply(ACCESS, tenant(), hosts=HOSTS)
        self.assertEqual([f for f in self.faults('uni/tn-T') if f[1] != 'S1123'], [])
        self.assertTrue(self.e.hosts['web1']['learned'])
        self.assertTrue(self.traffic('cli1', 'web1', 'tcp', 80)['ok'])
        self.assertTrue(self.traffic('cli1', 'web1', 'icmp')['ok'])
        self.assertFalse(self.traffic('cli1', 'web1', 'tcp', 22)['ok'])
        self.assertTrue(self.traffic('web1', '10.1.1.1')['ok'])

    def test_invalid_vlan_fault(self):
        t = tenant()
        t['fvTenant']['children'][-1]['fvAp']['children'][1]['fvAEPg']['children'][2] = \
            {"fvRsPathAtt": {"attributes": {"tDn": "topology/pod-1/paths-102/pathep-[eth1/2]", "encap": "vlan-200"}}}
        self.apply(ACCESS, t, hosts=HOSTS)
        codes = [f[1] for f in self.faults('uni/tn-T/ap-A/epg-Cli')]
        self.assertIn('F0467', codes)
        self.assertFalse(self.e.hosts['cli1']['learned'])

    def test_invalid_path_without_access_policy(self):
        t = tenant()
        t['fvTenant']['children'][-1]['fvAp']['children'][1]['fvAEPg']['children'][2] = \
            {"fvRsPathAtt": {"attributes": {"tDn": "topology/pod-1/paths-102/pathep-[eth1/30]", "encap": "vlan-20"}}}
        self.apply(ACCESS, t)
        descr = ' '.join(f[2] for f in self.faults('uni/tn-T/ap-A/epg-Cli'))
        self.assertIn('invalid-path', descr)

    def test_encap_in_use(self):
        t = tenant()
        t['fvTenant']['children'][-1]['fvAp']['children'][1]['fvAEPg']['children'].append(
            {"fvRsPathAtt": {"attributes": {"tDn": "topology/pod-1/paths-101/pathep-[eth1/3]", "encap": "vlan-10"}}})
        self.apply(ACCESS, t)
        descr = ' '.join(f[2] for f in self.faults('uni/tn-T/ap-A'))
        self.assertIn('encap-already-in-use', descr)

    def test_reverse_ports_off_breaks_reply(self):
        self.apply(ACCESS, tenant(), hosts=HOSTS)
        post(self.st, 'uni/tn-T/brc-web/subj-s', {"vzSubj": {"attributes": {"revFltPorts": "no"}}})
        self.S.changed()
        r = self.traffic('cli1', 'web1', 'tcp', 80)
        self.assertFalse(r['ok'])
        self.assertIn('Antwort', [s for s in r['steps'] if s['ok'] is False][0]['title'])

    def test_vzany_and_unenforced(self):
        self.apply(ACCESS, tenant(), hosts=HOSTS)
        self.assertFalse(self.traffic('cli1', 'web1', 'tcp', 22)['ok'])
        post(self.st, 'uni/tn-T/ctx-V', {"fvCtx": {"attributes": {"pcEnfPref": "unenforced"}}})
        self.S.changed()
        self.assertTrue(self.traffic('cli1', 'web1', 'tcp', 22)['ok'])

    def test_wrong_gateway_and_untagged(self):
        hosts = json.loads(json.dumps(HOSTS))
        hosts[0]['gw'] = '10.1.1.254'
        hosts[1]['vlan'] = 0
        self.apply(ACCESS, tenant(), hosts=hosts)
        self.assertFalse(self.e.hosts['cli1']['learned'])
        r = self.traffic('web1', 'cli1')
        self.assertFalse(r['ok'])

    def test_vpc_lacp(self):
        vpc = {"fabricInst": {"attributes": {"dn": "uni/fabric"}, "children": [{"fabricProtPol": {"attributes": {}, "children": [
            {"fabricExplicitGEp": {"attributes": {"name": "vpc101-102", "id": "10"}, "children": [
                {"fabricNodePEp": {"attributes": {"id": "101"}}}, {"fabricNodePEp": {"attributes": {"id": "102"}}}]}}]}}]}}
        t = tenant([{"fvRsPathAtt": {"attributes": {"tDn": "topology/pod-1/protpaths-101-102/pathep-[VPC-DB]",
                                                    "encap": "vlan-11"}}}])
        db = {'name': 'db1', 'mac': '00:50:56:00:00:09', 'ip': '10.1.1.20/24', 'gw': '10.1.1.1', 'vlan': 11,
              'links': [['SAL1931LA01', 'eth1/20'], ['SAL1931LA02', 'eth1/20']], 'bond': 'lacp-active'}
        self.apply(ACCESS, t, hosts=HOSTS + [db])
        self.assertFalse(self.e.hosts['db1']['learned'])  # ohne vPC-Domaene kein Pfad
        post(self.st, 'uni', vpc)
        self.S.changed()
        self.assertTrue(self.e.hosts['db1']['learned'], self.e.hosts['db1']['reasons'])
        post(self.st, 'uni/infra', {"lacpLagPol": {"attributes": {"name": "LACP-Active", "mode": "off"}}})
        self.S.changed()
        self.assertFalse(self.e.hosts['db1']['learned'])
        out = Cli(self.e, self.S.sim).run('leaf101', 'show port-channel summary')
        self.assertIn('Po1', out)


class TestL3Out(Base):
    def l3out(self, proto='ospf', mtu='inherit'):
        lif = [{"l3extRsPathL3OutAtt": {"attributes": {"tDn": "topology/pod-1/paths-103/pathep-[eth1/47]",
                                                       "ifInstT": "l3-port", "addr": "172.16.1.1/30", "mtu": mtu},
                                        "children": [{"bgpPeerP": {"attributes": {"addr": "172.16.1.2"}, "children": [
                                            {"bgpAsP": {"attributes": {"asn": "65100"}}}]}}] if proto == 'bgp' else []}}]
        if proto == 'ospf':
            lif.append({"ospfIfP": {"attributes": {}}})
        out = {"l3extOut": {"attributes": {"name": "WAN"}, "children": [
            {"l3extRsEctx": {"attributes": {"tnFvCtxName": "V"}}},
            {"l3extRsL3DomAtt": {"attributes": {"tDn": "uni/l3dom-L3D"}}},
            {"ospfExtP": {"attributes": {"areaId": "0.0.0.1"}}} if proto == 'ospf' else {"bgpExtP": {"attributes": {}}},
            {"l3extLNodeP": {"attributes": {"name": "np"}, "children": [
                {"l3extRsNodeL3OutAtt": {"attributes": {"tDn": "topology/pod-1/node-103", "rtrId": "1.1.1.103"}}},
                {"l3extLIfP": {"attributes": {"name": "ifp"}, "children": lif}}]}},
            {"l3extInstP": {"attributes": {"name": "all"}, "children": [
                {"l3extSubnet": {"attributes": {"ip": "0.0.0.0/0"}}},
                {"fvRsCons": {"attributes": {"tnVzBrCPName": "web"}}}]}}]}}
        return {"fvTenant": {"attributes": {"name": "T"}, "children": [out]}}

    def router(self, proto='ospf'):
        return [{'name': 'wan1', 'serial': 'SAL1931LA03', 'port': 'eth1/47', 'vlan': 0, 'ip': '172.16.1.2/30',
                 'mtu': 1500, 'protocol': proto, 'routerId': '9.9.9.9',
                 'ospf': {'area': '0.0.0.1', 'areaType': 'regular', 'hello': 10, 'dead': 40, 'nwT': 'bcast'},
                 'bgp': {'asn': '65100', 'peerAs': '65001'}, 'networks': ['8.8.8.0/24'], 'advertise': ['0.0.0.0/0'],
                 'staticBack': []}]

    def test_ospf_mtu_then_full(self):
        self.apply(ACCESS, tenant(), self.l3out(), hosts=HOSTS, routers=self.router())
        self.assertEqual(self.e.routers['wan1']['adj'], 'EXSTART')
        post(self.st, 'uni/tn-T/out-WAN/lnodep-np/lifp-ifp',
             {"l3extRsPathL3OutAtt": {"attributes": {"tDn": "topology/pod-1/paths-103/pathep-[eth1/47]", "mtu": "1500"}}})
        self.S.changed()
        self.assertEqual(self.e.routers['wan1']['adj'], 'FULL')
        # web1 haengt an leaf101: ohne MP-BGP keine Route
        r = self.traffic('web1', '8.8.8.8')
        self.assertFalse(r['ok'])
        self.assertIn('MP-BGP', ' '.join(s['detail'] for s in r['steps']))
        post(self.st, 'uni/fabric/bgpInstP-default', {"bgpInstPol": {"attributes": {}, "children": [
            {"bgpAsP": {"attributes": {"asn": "65001"}}},
            {"bgpRRP": {"attributes": {}, "children": [{"bgpRRNodePEp": {"attributes": {"id": "201"}}}]}}]}})
        self.S.changed()
        r = self.traffic('web1', '8.8.8.8')
        self.assertTrue(r['ok'], r)
        self.assertIn('10.1.1.0/24', self.e.routers['wan1']['learned'])
        out = Cli(self.e, self.S.sim).run('leaf103', 'show ip ospf neighbors vrf T:V')
        self.assertIn('FULL', out)

    def test_bgp(self):
        self.apply(ACCESS, tenant(), self.l3out('bgp'), hosts=HOSTS, routers=self.router('bgp'))
        self.assertEqual(self.e.routers['wan1']['adj'], 'Idle')  # Fabric-AS fehlt
        post(self.st, 'uni/fabric/bgpInstP-default', {"bgpInstPol": {"attributes": {}, "children": [
            {"bgpAsP": {"attributes": {"asn": "65001"}}},
            {"bgpRRP": {"attributes": {}, "children": [{"bgpRRNodePEp": {"attributes": {"id": "201"}}}]}}]}})
        self.S.changed()
        self.assertEqual(self.e.routers['wan1']['adj'], 'Established')
        self.assertTrue(self.traffic('web1', '8.8.8.8')['ok'])
        self.assertFalse(self.traffic('web1', '8.8.8.8', 'tcp', 22)['ok'])
        self.assertTrue(self.traffic('wan1', 'web1', 'tcp', 80)['ok'])


class TestRest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S, cls.httpd = serve('127.0.0.1', 0, tempfile.mkdtemp(), 'secret')
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def req(self, method, path, body=None, cookie=None):
        r = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), method=method,
                                   data=json.dumps(body).encode() if body is not None else None)
        if cookie:
            r.add_header('Cookie', cookie)
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, json.loads(resp.read() or b'null'), resp.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b'null'), e.headers

    def test_flow(self):
        s, j, _ = self.req('GET', '/api/class/fvTenant.json')
        self.assertEqual(s, 403)
        s, j, _ = self.req('POST', '/api/aaaLogin.json', {"aaaUser": {"attributes": {"name": "admin", "pwd": "bad"}}})
        self.assertEqual(s, 401)
        s, j, h = self.req('POST', '/api/aaaLogin.json', {"aaaUser": {"attributes": {"name": "admin", "pwd": "secret"}}})
        self.assertEqual(s, 200)
        cookie = 'APIC-cookie=' + j['imdata'][0]['aaaLogin']['attributes']['token']
        s, j, _ = self.req('POST', '/api/node/mo/uni/tn-R.json', {"fvTenant": {"attributes": {
            "dn": "uni/tn-R", "name": "R", "annotation": "orchestrator:terraform"}}}, cookie)
        self.assertEqual(s, 200, j)
        s, j, _ = self.req('GET', '/api/class/fvTenant.json?query-target-filter=eq(fvTenant.name,"R")', cookie=cookie)
        self.assertEqual(j['totalCount'], '1')
        s, j, _ = self.req('POST', '/api/mo/uni/tn-R.json', {"fvBD": {"attributes": {"name": "b", "arpFlood": "x"}}}, cookie)
        self.assertEqual(s, 400)
        self.assertEqual(j['imdata'][0]['error']['attributes']['code'], '801')
        s, j, _ = self.req('GET', '/api/mo/uni/tn-R.json?rsp-subtree=full&rsp-prop-include=config-only', cookie=cookie)
        self.assertEqual(j['imdata'][0]['fvTenant']['attributes']['name'], 'R')
        s, j, _ = self.req('DELETE', '/api/mo/uni/tn-R.json', cookie=cookie)
        self.assertEqual(s, 200)
        s, j, _ = self.req('GET', '/api/mo/uni/tn-R.json', cookie=cookie)
        self.assertEqual(j['totalCount'], '0')
        s, j, _ = self.req('GET', '/api/class/fabricNode.json?query-target-filter=eq(fabricNode.role,"spine")', cookie=cookie)
        self.assertEqual(j['totalCount'], '2')
        s, j, _ = self.req('GET', '/api/node/class/topology/pod-1/node-101/l1PhysIf.json', cookie=cookie)
        self.assertEqual(j['totalCount'], '54')
        s, j, _ = self.req('GET', '/sim/labs', cookie=cookie)
        self.assertTrue(len(j) >= 1)
        for lab in j:
            s, r, _ = self.req('POST', '/sim/labs/load', {'id': lab['id']}, cookie)
            self.assertEqual(s, 200, (lab['id'], r))
            s, r, _ = self.req('GET', '/sim/labs/check', cookie=cookie)
            self.assertEqual(s, 200)


class TestDiscovery(Base):
    def test_discovery_order(self):
        self.S.reset('empty')
        self.S.sim['settings']['discoverySeconds'] = 0
        self.S.changed()
        e = self.S.engine
        self.assertEqual(sorted(p['serial'] for p in e.pending), ['SAL1931LA01', 'SAL1931LA02'])
        post(self.S.store, 'uni/controller/nodeidentpol', {"fabricNodeIdentP": {"attributes": {
            "serial": "SAL1931LA01", "nodeId": "101", "name": "leaf101"}}})
        self.S.changed()
        self.assertEqual(e.nodes[101]['state'], 'active')
        self.assertIn('FDO2219SP01', [p['serial'] for p in e.pending])


if __name__ == '__main__':
    unittest.main()


class TestLabs(Base):
    def test_all_labs_solvable(self):
        self.S.sim['settings']['discoverySeconds'] = 0
        labs = self.S.labs()
        self.assertGreaterEqual(len(labs), 14)
        for lab in labs:
            with self.subTest(lab=lab['id']):
                self.S.load_lab(lab['id'])
                before = self.S.check_lab()
                self.assertLess(before['passed'], before['total'], '%s ist schon ohne Loesung bestanden' % lab['id'])
                for url, body in lab['solutionConfig']:
                    post(self.S.store, url, body)
                    self.S.changed()
                after = self.S.check_lab()
                failed = [(c['desc'], c['info']) for c in after['checks'] if not c['ok']]
                self.assertEqual(failed, [], lab['id'])


class TestApicFeatures(Base):
    def test_taboo_static_leaf_disable(self):
        app2 = {'name': 'app2', 'mac': '00:50:56:00:00:22', 'ip': '10.1.1.22/24', 'gw': '10.1.1.1', 'vlan': 10,
                'links': [['SAL1931LA01', 'eth1/4']], 'bond': 'none'}
        self.apply(ACCESS, tenant(), hosts=HOSTS + [app2])
        self.assertFalse(self.e.hosts['app2']['learned'])
        post(self.st, 'uni/tn-T/ap-A/epg-Web', {"fvAEPg": {"attributes": {}, "children": [
            {"fvRsNodeAtt": {"attributes": {"tDn": "topology/pod-1/node-101", "encap": "vlan-10"}}}]}})
        self.S.changed()
        self.assertTrue(self.e.hosts['app2']['learned'])
        self.assertTrue(self.traffic('cli1', 'web1')['ok'])
        post(self.st, 'uni/tn-T', {"fvTenant": {"attributes": {}, "children": [
            {"vzTaboo": {"attributes": {"name": "tb"}, "children": [{"vzTSubj": {"attributes": {"name": "s"}, "children": [
                {"vzRsDenyRule": {"attributes": {"tnVzFilterName": "icmp"}}}]}}]}},
            {"fvAp": {"attributes": {"name": "A"}, "children": [{"fvAEPg": {"attributes": {"name": "Web"}, "children": [
                {"fvRsProtBy": {"attributes": {"tnVzTabooName": "tb"}}}]}}]}}]}})
        self.S.changed()
        self.assertFalse(self.traffic('cli1', 'web1')['ok'])
        self.assertTrue(self.traffic('cli1', 'web1', 'tcp', 80)['ok'])
        post(self.st, 'uni/fabric/outofsvc', {"fabricRsOosPath": {"attributes": {
            "tDn": "topology/pod-1/paths-101/pathep-[eth1/1]", "lc": "blacklist"}}})
        self.S.changed()
        self.assertFalse(self.e.hosts['web1']['learned'])
        self.assertEqual(self.st.attrs('topology/pod-1/node-101/sys/phys-[eth1/1]')['adminSt'], 'down')

    def test_ntp_and_audit(self):
        self.apply()
        self.assertTrue(all(self.e.ntp['nodes'].values()))
        lab = self.S.lab('10-mgmt-ntp')
        for url, body in lab['solutionConfig']:
            self.S.audit('admin', post(self.st, url, body))
        self.S.changed()
        self.assertFalse(any(self.e.ntp['nodes'].values()), self.e.ntp['nodes'])
        self.assertIn('192.168.10.101', Cli(self.e, self.S.sim).run('leaf101', 'show ntp peer-status'))
        self.assertEqual(self.st.attrs('topology/pod-1/node-101/sys')['oobMgmtAddr'], '192.168.10.101')
        audit = self.st.by_class('aaaModLR')
        self.assertTrue(any('rsTimePol' in self.st.attrs(d)['affected'] for d in audit))
        events = [self.st.attrs(d)['descr'] for d in self.st.by_class('eventRecord')]
        self.assertTrue(events is not None)


VCENTER = [{'name': 'vc1', 'ip': '192.168.10.50', 'datacenter': 'DC1', 'user': 'administrator@vsphere.local', 'pwd': 'VMware1!',
            'hosts': [{'name': 'esx1', 'links': [['SAL1931LA01', 'eth1/9']], 'dvs': ['VDS1'],
                       'vms': [{'name': 'vm1', 'mac': '00:50:56:AA:00:01', 'ip': '10.1.1.50/24', 'gw': '10.1.1.1',
                                'network': 'T|A|Web'}]}]}]


class TestNewFeatures(Base):
    def vmm_tree(self, imm='immediate', pwd='VMware1!', mode='dynamic'):
        return {"polUni": {"attributes": {}, "children": [
            {"infraInfra": {"attributes": {}, "children": [
                {"fvnsVlanInstP": {"attributes": {"name": "VMM", "allocMode": mode}, "children": [
                    {"fvnsEncapBlk": {"attributes": {"from": "vlan-1000", "to": "vlan-1009"}}}]}},
                {"infraAttEntityP": {"attributes": {"name": "AAEP"}, "children": [
                    {"infraRsDomP": {"attributes": {"tDn": "uni/vmmp-VMware/dom-VDS1"}}}]}}]}},
            {"vmmProvP": {"attributes": {"vendor": "VMware"}, "children": [
                {"vmmDomP": {"attributes": {"name": "VDS1"}, "children": [
                    {"infraRsVlanNs": {"attributes": {"tDn": "uni/infra/vlanns-[VMM]-%s" % mode}}},
                    {"vmmUsrAccP": {"attributes": {"name": "cred", "usr": "administrator@vsphere.local", "pwd": pwd}}},
                    {"vmmCtrlrP": {"attributes": {"name": "vc1", "hostOrIp": "192.168.10.50", "rootContName": "DC1"}, "children": [
                        {"vmmRsAcc": {"attributes": {"tDn": "uni/vmmp-VMware/dom-VDS1/usracc-cred"}}}]}}]}}]}},
            {"fvTenant": {"attributes": {"name": "T"}, "children": [{"fvAp": {"attributes": {"name": "A"}, "children": [
                {"fvAEPg": {"attributes": {"name": "Web"}, "children": [
                    {"fvRsDomAtt": {"attributes": {"tDn": "uni/vmmp-VMware/dom-VDS1", "resImedcy": imm}}}]}}]}}]}}]}}

    def test_vmm(self):
        self.S.sim['vcenters'] = json.loads(json.dumps(VCENTER))
        self.apply(ACCESS, tenant(), self.vmm_tree(pwd='falsch'), hosts=HOSTS)
        self.assertEqual(self.e.vmm['uni/vmmp-VMware/dom-VDS1']['state'], 'offline')
        self.assertFalse(self.e.hosts['vm1']['learned'])
        post(self.st, 'uni', self.vmm_tree())
        self.S.changed()
        v = self.e.vmm['uni/vmmp-VMware/dom-VDS1']
        self.assertEqual(v['state'], 'online')
        self.assertEqual(v['pgs']['uni/tn-T/ap-A/epg-Web']['vlan'], 1000)
        self.assertTrue(self.e.hosts['vm1']['learned'], self.e.hosts['vm1']['reasons'])
        self.assertTrue(self.traffic('vm1', 'web1')['ok'])
        # Static-Pool: keine dynamischen VLANs
        post(self.st, 'uni', self.vmm_tree(mode='static'))
        post(self.st, 'uni/vmmp-VMware/dom-VDS1', {"vmmDomP": {"attributes": {}, "children": [
            {"infraRsVlanNs": {"attributes": {"tDn": "uni/infra/vlanns-[VMM]-static"}}}]}})
        self.S.changed()
        self.assertFalse(self.e.hosts['vm1']['learned'])

    def test_shared_services(self):
        t = tenant()
        t['fvTenant']['children'].insert(1, {"fvCtx": {"attributes": {"name": "V2"}}})
        # Cli in eigenen VRF
        t['fvTenant']['children'][3]['fvBD']['children'][0] = {"fvRsCtx": {"attributes": {"tnFvCtxName": "V2"}}}
        self.apply(ACCESS, t, hosts=HOSTS)
        r = self.traffic('cli1', 'web1', 'tcp', 80)
        self.assertFalse(r['ok'])
        post(self.st, 'uni/tn-T/brc-web', {"vzBrCP": {"attributes": {"scope": "tenant"}}})
        post(self.st, 'uni/tn-T/ap-A/epg-Web', {"fvSubnet": {"attributes": {"ip": "10.1.1.1/24", "scope": "private,shared"}}})
        post(self.st, 'uni/tn-T/BD-BD2', {"fvSubnet": {"attributes": {"ip": "10.1.2.1/24", "scope": "private,shared"}}})
        self.S.changed()
        r = self.traffic('cli1', 'web1', 'tcp', 80)
        self.assertTrue(r['ok'], r)
        self.assertFalse(self.traffic('cli1', 'web1', 'tcp', 22)['ok'])

    def test_l2out_silent(self):
        l2 = {"polUni": {"attributes": {}, "children": [
            {"infraInfra": {"attributes": {}, "children": [
                {"fvnsVlanInstP": {"attributes": {"name": "L2", "allocMode": "static"}, "children": [
                    {"fvnsEncapBlk": {"attributes": {"from": "vlan-300", "to": "vlan-300"}}}]}},
                {"infraAttEntityP": {"attributes": {"name": "AAEP"}, "children": [
                    {"infraRsDomP": {"attributes": {"tDn": "uni/l2dom-Legacy"}}}]}}]}},
            {"l2extDomP": {"attributes": {"name": "Legacy"}, "children": [
                {"infraRsVlanNs": {"attributes": {"tDn": "uni/infra/vlanns-[L2]-static"}}}]}},
            {"fvTenant": {"attributes": {"name": "T"}, "children": [
                {"l2extOut": {"attributes": {"name": "Legacy"}, "children": [
                    {"l2extRsEBd": {"attributes": {"tnFvBDName": "BD1", "encap": "vlan-300"}}},
                    {"l2extRsL2DomAtt": {"attributes": {"tDn": "uni/l2dom-Legacy"}}},
                    {"l2extLNodeP": {"attributes": {"name": "np"}, "children": [{"l2extLIfP": {"attributes": {"name": "ifp"}, "children": [
                        {"l2extRsPathL2OutAtt": {"attributes": {"tDn": "topology/pod-1/paths-101/pathep-[eth1/7]"}}}]}}]}},
                    {"l2extInstP": {"attributes": {"name": "LegacyNet"}, "children": [{"fvRsProv": {"attributes": {"tnVzBrCPName": "web"}}}]}}]}}]}}]}}
        legacy = {'name': 'old1', 'mac': '00:50:56:00:00:77', 'ip': '10.1.1.77/24', 'gw': '10.1.1.1', 'vlan': 300,
                  'links': [['SAL1931LA01', 'eth1/7']], 'bond': 'none', 'silent': True}
        self.apply(ACCESS, tenant(), l2, hosts=HOSTS + [legacy])
        self.assertEqual([f for f in self.faults('uni/tn-T/l2out') if f[1] == 'F0467'], [])
        self.assertTrue(self.e.hosts['old1'].get('quiet'))
        # web1 (EPG Web) -> old1 (L2Out, provider web) braucht Contract: web1 ist Provider, nicht Consumer
        self.assertFalse(self.traffic('web1', 'old1', 'tcp', 80)['ok'])
        post(self.st, 'uni/tn-T/ap-A/epg-Web', {"fvRsCons": {"attributes": {"tnVzBrCPName": "web"}}})
        post(self.st, 'uni/tn-T/BD-BD1', {"fvBD": {"attributes": {"unicastRoute": "no"}}})
        self.S.changed()
        r = self.traffic('web1', 'old1', 'tcp', 80)
        self.assertFalse(r['ok'])
        self.assertIn('flutet den ARP-Request nicht', ' '.join(s['detail'] for s in r['steps']))
        post(self.st, 'uni/tn-T/BD-BD1', {"fvBD": {"attributes": {"arpFlood": "yes"}}})
        self.S.changed()
        r = self.traffic('web1', 'old1', 'tcp', 80)
        self.assertTrue(r['ok'], r)
        self.assertIn('old1', r['woken'])
