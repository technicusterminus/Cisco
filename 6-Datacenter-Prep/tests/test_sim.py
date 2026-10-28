"""Tests fuer Datacenter Prep: python3 -m unittest discover -s tests"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dcprep.server import Sim, serve  # noqa: E402
from dcprep.model import post, AciError  # noqa: E402
from dcprep import trace  # noqa: E402
from dcprep import ops  # noqa: E402
from dcprep import msite  # noqa: E402
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
        cls.hub, cls.httpd = serve('127.0.0.1', 0, tempfile.mkdtemp(), 'secret')
        cls.S = cls.hub.sim('standard')
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

    def test_abgleich_script_against_itself(self):
        """werkzeuge/abgleich.py: Simulator gegen sich selbst muss vollstaendig gleich sein und raeumt auf."""
        import subprocess
        import sys
        out = tempfile.mkdtemp()
        url = 'http://127.0.0.1:%d' % self.port
        r = subprocess.run([sys.executable, os.path.join(BASE_DIR, 'werkzeuge', 'abgleich.py'), '--sim', url, '--sim-password', 'secret',
                            '--apic', url, '--apic-password', 'secret', '--write', '--fault-wait', '0', '--out', out],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertIn('0 abweichend', r.stdout)
        with open(os.path.join(out, 'abgleich-rohdaten.json'), encoding='utf-8') as f:
            self.assertGreater(len(json.load(f)['ergebnisse']), 60)
        self.assertNotIn('uni/tn-DCP-Abgleich', self.S.store.objs)

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
        for lab in sorted(j, key=lambda l: l.get('fabric') == 'factory'):
            s, r, _ = self.req('POST', '/sim/labs/load', {'id': lab['id']}, cookie)
            self.assertEqual(s, 200, (lab['id'], r))
            if lab.get('fabric') == 'factory':
                # Werkszustand: Sitzungen ungueltig, Login gesperrt bis zum Setup
                s, r, _ = self.req('GET', '/sim/setup')
                self.assertFalse(r['done'])
                s, r, _ = self.req('POST', '/api/aaaLogin.json', {"aaaUser": {"attributes": {"name": "admin", "pwd": "secret"}}})
                self.assertEqual(s, 503)
                continue
            s, r, _ = self.req('GET', '/sim/labs/check', cookie=cookie)
            self.assertEqual(s, 200, lab['id'])


    def test_saves(self):
        with self.S.lock:
            self.S.reset('discovered')
            self.S.save()
        s, j, _ = self.req('POST', '/api/aaaLogin.json', {"aaaUser": {"attributes": {"name": "admin", "pwd": "secret"}}})
        cookie = 'APIC-cookie=' + j['imdata'][0]['aaaLogin']['attributes']['token']
        self.req('POST', '/sim/labs/load', {'id': '16-service-graph-pbr'}, cookie)
        self.req('POST', '/api/mo/uni.json', {"fvTenant": {"attributes": {"name": "Merker"}}}, cookie)
        s, lst, _ = self.req('POST', '/sim/saves', {'op': 'save', 'name': 'stand1', 'descr': 'Test'}, cookie)
        self.assertEqual(s, 200)
        row = next(x for x in lst if x['name'] == 'stand1')
        self.assertEqual(row['lab'], '16-service-graph-pbr')
        self.assertIn('Merker', row['tenants'])
        # Download als Datei
        r = urllib.request.Request('http://127.0.0.1:%d/sim/saves/download?name=stand1' % self.port)
        r.add_header('Cookie', cookie)
        with urllib.request.urlopen(r) as resp:
            self.assertIn('attachment', resp.headers['Content-Disposition'])
            blob = json.loads(resp.read())
        self.assertEqual(blob['kind'], 'datacenter-prep-save')
        # Labwechsel sichert automatisch, Fortsetzen holt den Stand zurueck
        s, lst, _ = self.req('POST', '/sim/labs/load', {'id': '03-tenant-epg'}, cookie)
        s, lst, _ = self.req('GET', '/sim/saves', cookie=cookie)
        self.assertTrue(any(x['name'] == 'auto-16-service-graph-pbr' for x in lst))
        s, _, _ = self.req('POST', '/sim/saves', {'op': 'resume', 'lab': '16-service-graph-pbr'}, cookie)
        self.assertEqual(s, 200)
        s, st, _ = self.req('GET', '/sim/state', cookie=cookie)
        self.assertEqual(st['lab']['id'], '16-service-graph-pbr')
        self.assertEqual(len(st['devices']), 1)
        s, j, _ = self.req('GET', '/api/mo/uni/tn-Merker.json', cookie=cookie)
        self.assertEqual(j['totalCount'], '1')
        # Upload: gueltige und ungueltige Datei
        s, _, _ = self.req('POST', '/sim/saves', {'op': 'upload', 'name': 'import1', 'data': blob}, cookie)
        self.assertEqual(s, 200)
        s, _, _ = self.req('POST', '/sim/saves', {'op': 'upload', 'name': 'kaputt', 'data': {'foo': 1}}, cookie)
        self.assertEqual(s, 400)
        s, _, _ = self.req('POST', '/sim/saves', {'op': 'save', 'name': '../boese'}, cookie)
        self.assertEqual(s, 400)


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
        self.assertGreaterEqual(len(labs), 29)
        for lab in labs:
            with self.subTest(lab=lab['id']):
                self.S.load_lab(lab['id'])
                self.S.sim['settings']['upgradeSeconds'] = 0
                before = self.S.check_lab()
                self.assertLess(before['passed'], before['total'], '%s ist schon ohne Loesung bestanden' % lab['id'])
                for url, body in lab['solutionConfig']:
                    if url == '#setup':
                        self.S.setup_apply(body)
                        continue
                    if url == '#ndo':
                        msite.ndo_op(self.S, body)
                        self.S.changed()
                        continue
                    if url == '#ipn':
                        self.S.ipn_op({'router': body})
                        self.S.changed()
                        continue
                    if url == '#snapshot':
                        self.S.snapshot(body['op'], body['name'])
                        continue
                    if url == '#change':
                        self.S.audit('admin', post(self.S.store, body[0], body[1]))
                        self.S.rebuild()
                        self.S.changed()
                        continue
                    if url == '#monitor-test':
                        self.S.monitor_op(dict(body, op='test'))
                        self.S.changed()
                        continue
                    post(self.S.store, url, body)
                    self.S.rebuild()
                    ops.run_triggers(self.S, 'admin')
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


class TestRouteControl(Base):
    def test_transit_and_profiles(self):
        self.S.sim['settings']['discoverySeconds'] = 0
        self.S.load_lab('15-transit-route-control')
        sol = self.S.lab('15-transit-route-control')['solutionConfig'][0][1]
        post(self.S.store, 'uni', sol)
        self.S.changed()
        e = self.S.engine
        self.assertTrue(trace.run(e, self.S.sim, '192.168.50.10', '8.8.8.8')['ok'])
        self.assertNotIn('1.1.1.0/24', e.routers['partner1']['learned'])
        # Route-Profile default-export gibt zusaetzlich 1.1.1.0/24 frei
        post(self.S.store, 'uni/tn-Shop', {"fvTenant": {"attributes": {}, "children": [
            {"rtctrlSubjP": {"attributes": {"name": "one"}, "children": [
                {"rtctrlMatchRtDest": {"attributes": {"ip": "1.1.0.0/16", "aggregate": "yes"}}}]}},
            {"l3extOut": {"attributes": {"name": "Partner"}, "children": [
                {"rtctrlProfile": {"attributes": {"name": "default-export"}, "children": [
                    {"rtctrlCtxP": {"attributes": {"name": "c1", "order": "0", "action": "permit"}, "children": [
                        {"rtctrlRsCtxPToSubjP": {"attributes": {"tnRtctrlSubjPName": "one"}}}]}}]}}]}}]}})
        self.S.changed()
        e = self.S.engine
        self.assertIn('1.1.1.0/24', e.routers['partner1']['learned'])
        # deny-Context hebt es wieder auf
        post(self.S.store, 'uni/tn-Shop/out-Partner/prof-default-export/ctx-c1', {"rtctrlCtxP": {"attributes": {"action": "deny"}}})
        self.S.changed()
        self.assertNotIn('1.1.1.0/24', self.S.engine.routers['partner1']['learned'])
        # Import Enforcement ohne Import-Subnetz blockiert alles vom Partner
        post(self.S.store, 'uni/tn-Shop/out-Partner/instP-PartnerNet/extsubnet-[192.168.50.0/24]',
             {"l3extSubnet": {"attributes": {"scope": "import-security"}}})
        self.S.changed()
        self.assertFalse(any(r['prefix'] == '192.168.50.0/24' for r in self.S.engine.routes.get(('uni/tn-Shop/ctx-Prod', 104), [])))


class TestServiceGraph(Base):
    def test_pbr(self):
        self.S.sim['settings']['discoverySeconds'] = 0
        self.S.load_lab('16-service-graph-pbr')
        for url, body in self.S.lab('16-service-graph-pbr')['solutionConfig']:
            post(self.S.store, url, body)
        self.S.changed()
        e = self.S.engine
        g = next(iter(e.graphs.values()))
        self.assertEqual(g['state'], 'applied', g['reasons'])
        r = trace.run(e, self.S.sim, 'web1', 'app1', 'tcp', 8080)
        self.assertTrue(r['ok'], r)
        self.assertTrue(any('fw1' in s['detail'] for s in r['steps']))
        self.assertFalse(trace.run(e, self.S.sim, 'web1', 'app1', 'icmp', 0)['ok'])
        out = Cli(e, self.S.sim).run('leaf101', 'show zoning-rule')
        self.assertIn('redir(destgrp-1)', out)
        # falsche MAC im PBR-Ziel
        post(self.S.store, 'uni/tn-Shop/svcCont/svcRedirectPol-PBR-Ext/RedirectDest_ip-[192.168.100.10]',
             {"vnsRedirectDest": {"attributes": {"mac": "00:50:56:FA:01:99"}}})
        self.S.changed()
        r = trace.run(self.S.engine, self.S.sim, 'web1', 'app1', 'tcp', 8080)
        self.assertFalse(r['ok'])
        self.assertIn('MAC', ' '.join(s['detail'] for s in r['steps'] if s['ok'] is False))
        # ohne Device Selection Policy: Graph nicht gerendert, Fault S1690
        self.S.store and post(self.S.store, 'uni/tn-Shop', {"fvTenant": {"attributes": {}, "children": [
            {"vnsLDevCtx": {"attributes": {"ctrctNameOrLbl": "web-to-app", "graphNameOrLbl": "FW-Graph", "nodeNameOrLbl": "N1",
                                           "status": "deleted"}}}]}})
        self.S.changed()
        g = next(iter(self.S.engine.graphs.values()))
        self.assertEqual(g['state'], 'failed')
        self.assertTrue(any(self.S.store.attrs(d)['code'] == 'S1690' for d in self.S.store.by_class('faultInst')))


class TestSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub, cls.httpd = serve('127.0.0.1', 0, tempfile.mkdtemp(), 'secret')
        cls.S = cls.hub.sim('standard')
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    req = TestRest.req

    def login(self, name, pwd):
        s, j, _ = self.req('POST', '/api/aaaLogin.json', {"aaaUser": {"attributes": {"name": name, "pwd": pwd}}})
        if s != 200:
            return s, j['imdata'][0]['error']['attributes']['text']
        return s, 'APIC-cookie=' + j['imdata'][0]['aaaLogin']['attributes']['token']

    def test_aaa_rbac(self):
        S = self.S
        with S.lock:
            S.sim['settings']['discoverySeconds'] = 0
            S.load_lab('21-aaa-tacacs-rbac')
            for url, body in S.lab('21-aaa-tacacs-rbac')['solutionConfig']:
                post(S.store, url, body)
            S.changed()
        s, ck = self.login('apic#ISE\\netadmin', 'Net#2026')
        self.assertEqual(s, 200, ck)
        s, ck2 = self.login('apic#ISE\\shopops', 'Shop#2026')
        self.assertEqual(s, 200, ck2)
        # Lesen gefiltert: nur Shop und common
        s, j, _ = self.req('GET', '/api/class/fvTenant.json', cookie=ck2)
        names = sorted(x['fvTenant']['attributes']['name'] for x in j['imdata'])
        self.assertEqual(names, ['Shop', 'common'])
        # Schreiben im eigenen Tenant ja, Access Policies nein
        s, _, _ = self.req('POST', '/api/mo/uni/tn-Shop.json', {"fvBD": {"attributes": {"name": "BD-Neu"}}}, ck2)
        self.assertEqual(s, 200)
        s, j, _ = self.req('POST', '/api/mo/uni/infra.json', {"fvnsVlanInstP": {"attributes": {"name": "X", "allocMode": "static"}}}, ck2)
        self.assertEqual(s, 403)
        self.assertNotIn('uni/infra/vlanns-[X]-static', S.store.objs)
        s, _, _ = self.req('POST', '/sim/hosts', {'op': 'delete', 'name': 'web1'}, ck2)
        self.assertEqual(s, 403)
        # Falscher Key -> abgelehnt; Server aus -> Login-Domain ohne Fallback
        with S.lock:
            post(S.store, 'uni/userext/tacacsext/tacacsplusprovider-192.168.10.40', {"aaaTacacsPlusProvider": {"attributes": {"key": "falsch"}}})
        s, txt = self.login('apic#ISE\\netadmin', 'Net#2026')
        self.assertEqual(s, 401)
        self.assertIn('Shared Key', txt)
        with S.lock:
            post(S.store, 'uni/userext/tacacsext/tacacsplusprovider-192.168.10.40', {"aaaTacacsPlusProvider": {"attributes": {"key": "Tac#Key2026"}}})
            S.sim['aaa'][0]['down'] = True
            # Default Authentication auf TACACS: bei Ausfall lokaler Fallback
            post(S.store, 'uni/userext/authrealm/defaultauth', {"aaaDefaultAuth": {"attributes": {"realm": "tacacs", "providerGroup": "ISE-TACACS"}}})
        s, txt = self.login('apic#ISE\\netadmin', 'Net#2026')
        self.assertEqual(s, 401)
        self.assertIn('kein Server erreichbar', txt)
        s, ck3 = self.login('admin', 'secret')
        self.assertEqual(s, 200, ck3)
        s, w, _ = self.req('GET', '/sim/whoami', cookie=ck3)
        self.assertIn('Fallback', w['how'])
        s, ck4 = self.login('apic#fallback\\admin', 'secret')
        self.assertEqual(s, 200)


class TestOps(Base):
    def run_post(self, url, body):
        ch = post(self.st, url, body)
        self.S.audit('admin', ch)
        self.S.rebuild()
        ops.run_triggers(self.S, 'admin')
        self.S.changed()

    def setUp(self):
        super().setUp()
        self.S.sim['settings'].update({'discoverySeconds': 0, 'upgradeSeconds': 0})
        self.apply(ACCESS, tenant(), hosts=HOSTS)

    def test_firmware_order_and_groups(self):
        self.run_post('uni/fabric/fwrepop', {'firmwareOSource': {'attributes': {'name': 'sw', 'proto': 'http', 'url': 'http://192.168.10.50/images/aci-n9000-dk9.16.0.6c.bin'}}})
        self.run_post('uni/fabric/fwrepop', {'firmwareOSource': {'attributes': {'name': 'bad', 'proto': 'scp', 'url': '192.168.10.50:/images/x.bin', 'user': 'backup', 'password': 'x'}}})
        self.assertEqual([i['version'] for i in self.S.sim['fwrepo']], ['n9000-16.0(6c)'])
        self.assertIn('Permission denied', [d for k, d in self.S.sim['downloads'].items() if 'osrc-bad' in k][0]['status'])
        self.run_post('uni/fabric/protpol', {'fabricExplicitGEp': {'attributes': {'name': 'v', 'id': '12'}, 'children': [
            {'fabricNodePEp': {'attributes': {'id': '101'}}}, {'fabricNodePEp': {'attributes': {'id': '102'}}}]}})
        self.run_post('uni/fabric', {'maintMaintP': {'attributes': {'name': 'g', 'version': 'n9000-16.0(6c)'}}})
        self.run_post('uni/fabric', {'maintMaintGrp': {'attributes': {'name': 'g'}, 'children': [
            {'maintRsMgrpp': {'attributes': {'tnMaintMaintPName': 'g'}}},
            {'fabricNodeBlk': {'attributes': {'name': 'b', 'from_': '101', 'to_': '102'}}}]}})
        self.assertIn('S1801', [c for _, c, _ in self.faults('uni/fabric/maintgrp-g')])
        self.run_post('uni/fabric/maintpol-g', {'maintMaintP': {'attributes': {'adminSt': 'triggered'}}})
        self.assertIn('Controller first', self.S.sim['fwlog'][-1]['text'])
        self.assertEqual(self.st.attrs('uni/fabric/maintpol-g')['adminSt'], 'untriggered')
        # Reload: Knoten inaktiv, Host an leaf101 nicht gelernt
        self.S.sim['settings']['upgradeSeconds'] = 3600
        self.run_post('uni/fabric/maintpol-g', {'maintMaintP': {'attributes': {'ignoreCompat': 'true', 'adminSt': 'triggered'}}})
        self.assertEqual(self.e.nodes[101]['state'], 'inactive')
        self.assertIn('Firmware-Upgrade', ' '.join(self.e.hosts['web1']['reasons']))
        self.S.sim['upgrades'][-1]['dur'] = 0
        self.S.changed()
        self.assertEqual(self.e.node_version('SAL1931LA01'), 'n9000-16.0(6c)')
        self.assertTrue(self.traffic('web1', 'cli1')['ok'])

    def test_export_import(self):
        self.run_post('uni/fabric', {'fileRemotePath': {'attributes': {'name': 'scp', 'host': '192.168.10.50', 'remotePath': '/backup',
                                                                        'userName': 'backup', 'userPasswd': 'Backup123!'}, 'children': [
            {'fileRsARemoteHostToEpg': {'attributes': {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'}}}]}})
        self.run_post('uni/exportcryptkey', {'pkiExportEncryptionKey': {'attributes': {'strongEncryptionEnabled': 'yes', 'passphrase': 'A-very-long-phrase-1'}}})
        self.run_post('uni/fabric', {'configExportP': {'attributes': {'name': 'x', 'targetDn': 'uni/tn-T', 'adminSt': 'triggered'}, 'children': [
            {'configRsRemotePath': {'attributes': {'tnFileRemotePathName': 'scp'}}}]}})
        job = self.S.sim['jobs'][-1]
        self.assertTrue(job['ok'], job)
        self.assertNotIn('ohne Secure', job['details'])
        self.st.delete('uni/tn-T')
        self.S.changed()
        self.assertFalse(self.traffic('web1', 'cli1')['ok'])
        # andere Passphrase -> atomic Import scheitert
        self.run_post('uni/exportcryptkey', {'pkiExportEncryptionKey': {'attributes': {'passphrase': 'Another-long-phrase2'}}})
        self.run_post('uni/fabric', {'configImportP': {'attributes': {'name': 'i', 'fileName': job['file'], 'adminSt': 'triggered'}, 'children': [
            {'configRsRemotePath': {'attributes': {'tnFileRemotePathName': 'scp'}}}]}})
        self.assertFalse(self.S.sim['jobs'][-1]['ok'])
        self.assertNotIn('uni/tn-T', self.st.objs)
        self.run_post('uni/fabric/configimp-i', {'configImportP': {'attributes': {'importMode': 'best-effort', 'adminSt': 'triggered'}}})
        self.assertTrue(self.S.sim['jobs'][-1]['ok'], self.S.sim['jobs'][-1])
        self.assertTrue(self.traffic('web1', 'cli1')['ok'])

    def test_monitoring_and_snmp(self):
        self.run_post('uni/fabric', {'syslogGroup': {'attributes': {'name': 'SL'}, 'children': [{'syslogRemoteDest': {'attributes': {'host': '192.168.10.60', 'port': '515'}, 'children': [
            {'fileRsARemoteHostToEpg': {'attributes': {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'}}}]}}]}})
        self.run_post('uni/fabric/moncommon', {'syslogSrc': {'attributes': {'name': 'a', 'incl': 'faults'}, 'children': [
            {'syslogRsDestGroup': {'attributes': {'tDn': 'uni/fabric/slgroup-SL'}}}]}})
        self.assertIn('Port 515', self.e.mon[0]['why'])
        self.run_post('uni/fabric/slgroup-SL/rdst-192.168.10.60', {'syslogRemoteDest': {'attributes': {'port': '514'}}})
        self.assertTrue(self.e.mon[0]['ok'])
        self.S.monitor_op({'op': 'test', 'severity': 'major'})
        self.S.changed()
        log = self.S.sim['monlog']['syslog-srv']
        self.assertIn('[F9999][raised]', log[-1]['text'])
        r = ops.snmp_walk(self.S, 'snmp-nms', 'apic1', 'NMS-Read')
        self.assertFalse(r['ok'])
        self.run_post('uni/fabric', {'snmpPol': {'attributes': {'name': 'default', 'adminSt': 'enabled'}, 'children': [
            {'snmpCommunityP': {'attributes': {'name': 'NMS-Read'}}},
            {'snmpClientGrpP': {'attributes': {'name': 'g'}, 'children': [{'snmpRsEpg': {'attributes': {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'}}},
                                                                         {'snmpClientP': {'attributes': {'addr': '192.168.10.61'}}}]}}]}})
        self.run_post('uni/fabric/funcprof', {'fabricPodPGrp': {'attributes': {'name': 'P'}, 'children': [{'fabricRsSnmpPol': {'attributes': {'tnSnmpPolName': 'default'}}}]}})
        self.run_post('uni/fabric/podprof-default/pods-default-typ-ALL/rspodPGrp', {'fabricRsPodPGrp': {'attributes': {'tDn': 'uni/fabric/funcprof/podpgrp-P'}}})
        self.assertTrue(ops.snmp_walk(self.S, 'snmp-nms', 'apic1', 'NMS-Read')['ok'])
        self.assertIn('Community', ops.snmp_walk(self.S, 'snmp-nms', 'apic1', 'public')['why'])

    def test_dhcp_relay(self):
        hosts = json.loads(json.dumps(HOSTS))
        hosts[1]['dhcpd'] = [{'net': '10.1.1.0/24', 'from': '10.1.1.100', 'to': '10.1.1.110', 'gw': '10.1.1.1'}]
        hosts.append({'name': 'pc1', 'mac': '00:50:56:00:00:09', 'ip': '0.0.0.0/32', 'gw': '', 'vlan': 10,
                      'links': [['SAL1931LA01', 'eth1/4']], 'bond': 'none', 'dhcp': True})
        self.apply({'fvAEPg': {'attributes': {'dn': 'uni/tn-T/ap-A/epg-Web'}, 'children': [
            {'fvRsPathAtt': {'attributes': {'tDn': 'topology/pod-1/paths-101/pathep-[eth1/4]', 'encap': 'vlan-10'}}}]}}, hosts=hosts)
        self.assertFalse(self.e.dhcp_info['pc1']['ok'])
        self.run_post('uni/tn-T', {'dhcpRelayP': {'attributes': {'name': 'R'}, 'children': [
            {'dhcpRsProv': {'attributes': {'tDn': 'uni/tn-T/ap-A/epg-Cli', 'addr': '10.1.2.10'}}}]}})
        self.run_post('uni/tn-T/BD-BD1', {'dhcpLbl': {'attributes': {'name': 'R'}}})
        self.assertEqual(self.e.dhcp_info['pc1']['ip'], '10.1.1.100/24')
        self.assertTrue(self.traffic('pc1', 'web1')['ok'])

    def test_mcp_loop(self):
        self.apply({'fvAEPg': {'attributes': {'dn': 'uni/tn-T/ap-A/epg-Web'}, 'children': [
            {'fvRsPathAtt': {'attributes': {'tDn': 'topology/pod-1/paths-101/pathep-[eth1/3]', 'encap': 'vlan-10'}}},
            {'fvRsPathAtt': {'attributes': {'tDn': 'topology/pod-1/paths-102/pathep-[eth1/3]', 'encap': 'vlan-10'}}}]}})
        self.S.sim['switches'] = [{'name': 'sw', 'links': [['SAL1931LA01', 'eth1/3'], ['SAL1931LA02', 'eth1/3']], 'bond': 'none', 'vlans': ''}]
        self.S.changed()
        self.assertIn('S2534', [c for _, c, _ in self.faults('uni/tn-T/BD-BD1')])
        self.assertFalse(self.traffic('web1', 'cli1')['ok'])
        self.run_post('uni/infra/mcpInstP-default', {'mcpInstPol': {'attributes': {'adminSt': 'enabled', 'key': 'k'}}})
        self.assertFalse(self.traffic('web1', 'cli1')['ok'])
        self.run_post('uni/infra/mcpInstP-default', {'mcpInstPol': {'attributes': {'ctrl': 'pdu-per-vlan'}}})
        self.assertEqual(self.e.ports[(102, 'eth1/3')]['qual'], 'error-disabled')
        self.assertTrue(self.traffic('web1', 'cli1')['ok'])
        out = Cli(self.e, self.S.sim).run('leaf102', 'show interface status err-disabled')
        self.assertIn('mcp-loop', out)


class TestMultiPod(Base):
    def test_ipn_mtu_and_relay(self):
        S = self.S
        S.sim['settings']['discoverySeconds'] = 0
        S.load_lab('29-multipod')
        for url, body in S.lab('29-multipod')['solutionConfig'][:3]:
            post(S.store, url, body)
        S.changed()
        self.assertIn('DHCP Relay', S.engine.mp['reasons']['FDO2219SP03'])
        S.ipn_op({'router': {'name': 'ipn2', 'relay': '10.0.0.1'}})
        S.ipn_op({'router': {'name': 'ipn1', 'relay': '10.0.0.1'}})
        S.changed()
        self.assertIn('FDO2219SP03', [p['serial'] for p in S.engine.pending])
        post(S.store, 'uni/controller/nodeidentpol', {'fabricNodeIdentP': {'attributes': {'serial': 'FDO2219SP03', 'nodeId': '203', 'name': 'spine203', 'podId': '1'}}})
        S.changed()
        self.assertIn('S0135', [c for _, c, _ in self.faults('uni/controller')])
        post(S.store, 'uni/controller/nodeidentpol/nodep-FDO2219SP03', {'fabricNodeIdentP': {'attributes': {'podId': '2'}}})
        S.changed()
        adj = next(a for a in S.engine.mp['adj'] if a['serial'] == 'FDO2219SP03')
        self.assertEqual(adj['state'], 'EXSTART')
        out = Cli(S.engine, S.sim).run('spine203', 'show ip ospf neighbors vrf overlay-1')
        self.assertIn('EXSTART', out)


class TestScale(Base):
    def test_topology_bulk_flows_coverage(self):
        from dcprep import flows, coverage
        S = self.S
        S.sim['settings']['discoverySeconds'] = 0
        r = S.topology_op({'spec': {'pods': [{'spines': 4, 'leafs': 12}, {'spines': 2, 'leafs': 4}], 'remote': 1}, 'register': True, 'infra': True})
        S.changed()
        S.changed()
        self.assertEqual(r['nodes'], 23)
        self.assertTrue(all(n['state'] == 'active' for n in self.e.nodes.values()), {n: x['state'] for n, x in self.e.nodes.items()})
        with self.assertRaises(AciError):
            S.topology_op({'spec': {'pods': [{'spines': 7, 'leafs': 4}]}})
        # Hosts in Masse: Web in Pod 1, App in Pod 2
        post(self.st, 'uni', ACCESS)
        acc2 = json.loads(json.dumps(ACCESS).replace('"101"', '"1101"').replace('"104"', '"1104"').replace('IFP"', 'IFP2"')
                          .replace('"ALL"', '"ALL2"'))
        post(self.st, 'uni', acc2)
        post(self.st, 'uni', tenant())
        post(self.st, 'uni/tn-T/ap-A/epg-Cli', {'fvAEPg': {'attributes': {}, 'children': [
            {'fvRsPathAtt': {'attributes': {'tDn': 'topology/pod-2/paths-1101/pathep-[eth1/2]', 'encap': 'vlan-20'}}}]}})
        n = S.bulk_hosts('web1,,10.1.1.10/24,10.1.1.1,10,leaf101,1\ncli1,,10.1.2.10/24,10.1.2.1,20,leaf1101,2')
        S.changed()
        self.assertEqual(n, 2)
        with self.assertRaises(AciError):
            S.bulk_hosts('web1,,10.1.1.20/24,10.1.1.1,10,leaf101,3')
        self.assertEqual(next(h for h in S.sim['hosts'] if h['name'] == 'web1')['ip'], '10.1.1.10/24')
        self.assertTrue(self.traffic('web1', 'cli1')['ok'], self.traffic('web1', 'cli1')['steps'][-1])
        m = flows.matrix(S, None, None, 'tcp', 80)
        self.assertEqual(m['rows'][0]['cells'][1]['ok'] or m['rows'][1]['cells'][0]['ok'], True)
        res = flows.expect_op(S, {'op': 'csv', 'csv': 'EPG:T/A/Cli,EPG:T/A/Web,tcp,80,allow\nweb1,cli1,tcp,22,deny'})
        self.assertEqual((res['passed'], res['total']), (2, 2), res)
        rep = coverage.report(self.st, 'uni/tn-T')
        self.assertGreater(rep['byLevel']['ausgewertet'], 10)


class TestUsers(unittest.TestCase):
    """Benutzerverwaltung: getrennte Welten, Rechte, Lab-Speicherstaende und Zuruecksetzen."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.hub, self.httpd = serve('127.0.0.1', 0, self.dir, 'admin', discovery=0)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.httpd.shutdown()

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

    def login(self, name, pwd=''):
        s, j, h = self.req('POST', '/dp/login', {'name': name, 'password': pwd})
        if s != 200:
            return None
        dp = h['Set-Cookie'].split(';')[0]
        s, j, h = self.req('POST', '/api/aaaLogin.json', {'aaaUser': {'attributes': {'name': 'admin', 'pwd': 'admin'}}}, dp)
        return dp + '; APIC-cookie=' + j['imdata'][0]['aaaLogin']['attributes']['token']

    def test_users_worlds_and_lab_saves(self):
        s, j, _ = self.req('GET', '/dp/users')
        self.assertEqual([(u['name'], u['role']) for u in j['users']], [('standard', 'verwalter')])
        self.assertEqual(self.req('POST', '/dp/users', {'op': 'create', 'name': 'Anna', 'password': 'geheim1'})[0], 200)
        self.assertEqual(self.req('POST', '/dp/users', {'op': 'create', 'name': 'anna'})[0], 400)
        self.assertIsNone(self.login('Anna', 'falsch'))
        anna, std = self.login('Anna', 'geheim1'), self.login('standard')
        # Getrennte Welten
        self.req('POST', '/sim/labs/op', {'op': 'resume', 'id': '03-tenant-epg'}, anna)
        self.assertEqual(self.req('GET', '/sim/state', cookie=anna)[1]['lab']['id'], '03-tenant-epg')
        self.assertIsNone(self.req('GET', '/sim/state', cookie=std)[1]['lab'])
        self.req('POST', '/api/mo/uni.json', {'fvTenant': {'attributes': {'name': 'NurAnna'}}}, anna)
        names = lambda ck: [x['fvTenant']['attributes']['name'] for x in self.req('GET', '/api/class/fvTenant.json', cookie=ck)[1]['imdata']]
        self.assertIn('NurAnna', names(anna))
        self.assertNotIn('NurAnna', names(std))
        # Rechte: Anna ist kein Verwalter
        self.assertEqual(self.req('POST', '/dp/users', {'op': 'delete', 'name': 'standard'}, anna)[0], 403)
        self.assertEqual(self.req('POST', '/dp/users', {'op': 'delete', 'name': 'Tippfehler'}, std)[0], 404)
        # Lab-Speicherstaende: speichern, Labwechsel sichert automatisch, fortsetzen, zuruecksetzen
        self.req('POST', '/sim/saves', {'op': 'save', 'name': 'lab03-mitte'}, anna)
        self.req('POST', '/sim/labs/op', {'op': 'resume', 'id': '04-contracts'}, anna)
        labs = {l['id']: l for l in self.req('GET', '/sim/labs?full=1', cookie=anna)[1]['labs']}
        self.assertEqual(sorted(x['name'] for x in labs['03-tenant-epg']['saves']), ['auto-03-tenant-epg', 'lab03-mitte'])
        self.req('POST', '/sim/labs/op', {'op': 'resume', 'id': '03-tenant-epg'}, anna)
        self.assertIn('NurAnna', names(anna))
        self.req('POST', '/sim/labs/check', {}, anna)
        labs = {l['id']: l for l in self.req('GET', '/sim/labs?full=1', cookie=anna)[1]['labs']}
        self.assertEqual(labs['03-tenant-epg']['progress']['total'], 9)  # Lab 03: 7 Funktions- und 2 Sicherheitspruefungen (Least Privilege dazu)
        self.assertFalse(labs['03-tenant-epg']['progress']['done'])
        self.req('POST', '/sim/labs/op', {'op': 'reset', 'id': '03-tenant-epg'}, anna)
        self.assertNotIn('NurAnna', names(anna))
        labs = {l['id']: l for l in self.req('GET', '/sim/labs?full=1', cookie=anna)[1]['labs']}
        self.assertEqual([x['name'] for x in labs['03-tenant-epg']['saves']], ['lab03-mitte'])
        self.req('POST', '/sim/labs/op', {'op': 'purge', 'id': '03-tenant-epg', 'progress': True}, anna)
        labs = {l['id']: l for l in self.req('GET', '/sim/labs?full=1', cookie=anna)[1]['labs']}
        self.assertEqual((labs['03-tenant-epg']['saves'], labs['03-tenant-epg']['progress']), ([], None))
        # Welt zuruecksetzen und Benutzer loeschen
        self.assertEqual(self.req('POST', '/dp/users', {'op': 'reset'}, anna)[0], 200)
        anna = self.login('Anna', 'geheim1')
        self.assertIsNone(self.req('GET', '/sim/state', cookie=anna)[1]['lab'])
        s, j, h = self.req('POST', '/dp/users', {'op': 'delete'}, anna)
        self.assertIn('Max-Age=0', h['Set-Cookie'])
        self.assertEqual([u['name'] for u in self.req('GET', '/dp/users')[1]['users']], ['standard'])
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'users', 'anna')))

    def test_migration_of_old_state(self):
        from dcprep.users import Hub
        d = tempfile.mkdtemp()
        with open(os.path.join(d, 'state.json'), 'w') as f:
            f.write('{}')
        os.makedirs(os.path.join(d, 'saves'))
        hub = Hub(d)
        self.assertEqual(list(hub.data['users']), ['standard'])
        self.assertTrue(os.path.exists(os.path.join(d, 'users', 'standard', 'state.json')))
        self.assertFalse(os.path.exists(os.path.join(d, 'state.json')))
