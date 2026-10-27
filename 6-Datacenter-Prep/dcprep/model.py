"""Management Information Tree (MIT): Klassenmodell, DN-Logik und Objektspeicher.

Jedes Objekt hat einen Distinguished Name (DN) wie im echten APIC, z. B.
``uni/tn-Firma/BD-Web``. Die Klassen tragen die echten APIC-Namen (fvTenant,
fvBD, fvAEPg, ...), damit Ansible, Terraform, Postman und eigene Skripte
gegen den Simulator genauso arbeiten wie gegen einen APIC.
"""
import ipaddress
import re
import time


class AciError(Exception):
    def __init__(self, code, text, status=400):
        super().__init__(text)
        self.code = str(code)
        self.text = text
        self.status = status


# --------------------------------------------------------------------------
# DN-Hilfen
# --------------------------------------------------------------------------

def split_dn(dn):
    """Zerlegt einen DN in RNs; '/' innerhalb von [...] trennt nicht."""
    parts, buf, depth = [], [], 0
    for ch in dn:
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        if ch == '/' and depth == 0:
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append(''.join(buf))
    return parts


def parent_dn(dn):
    return '/'.join(split_dn(dn)[:-1])


def rn_of(dn):
    p = split_dn(dn)
    return p[-1] if p else ''


def tenant_of(dn):
    p = split_dn(dn)
    if len(p) >= 2 and p[0] == 'uni' and p[1].startswith('tn-'):
        return 'uni/' + p[1]
    return None


# --------------------------------------------------------------------------
# Klassen-Metadaten
# --------------------------------------------------------------------------

COMMON_RW = {'descr', 'nameAlias', 'annotation', 'ownerKey', 'ownerTag', 'userdom'}
COMMON_RO = {'childAction', 'lcOwn', 'modTs', 'uid', 'extMngdBy', 'monPolDn',
             'configIssues', 'configSt', 'status', 'dn', 'rn'}
NAME_RE = re.compile(r'^[a-zA-Z0-9_.:-]{1,64}$')
YN = ('yes', 'no')
ED = ('enabled', 'disabled')
IMMED = ('immediate', 'lazy')


class Meta:
    def __init__(self, name, rn, parents, attrs=None, enums=None, sets=None,
                 ro=(), label=None, config=True, auto=(), rel=None, fixed=False,
                 checks=None):
        self.name = name
        self.rn = rn
        self.parents = tuple(parents)
        self.attrs = dict(attrs or {})
        self.enums = enums or {}
        self.sets = sets or {}
        self.ro = set(ro)
        self.label = label or name
        self.config = config
        self.auto = auto
        self.rel = rel
        self.fixed = fixed
        self.checks = checks or {}
        self.naming = re.findall(r'\{(\w+)\}', rn)
        for n in self.naming:
            self.attrs.setdefault(n, '')
        pat, pos = '', 0
        for m in re.finditer(r'\{(\w+)\}', rn):
            pat += re.escape(rn[pos:m.start()]) + '(?P<%s>.+?)' % m.group(1)
            pos = m.end()
        pat += re.escape(rn[pos:])
        self.rn_re = re.compile('^' + pat + '$')
        if rel:
            for a in ('tDn', 'state', 'stateQual', 'tCl', 'tType', 'forceResolve'):
                if a != 'tDn' or rel[0] == 'name':
                    self.ro.add(a)
                self.attrs.setdefault(a, {'state': 'unformed', 'stateQual': 'none',
                                          'forceResolve': 'yes', 'tType': rel[0]}.get(a, ''))

    def make_rn(self, attrs):
        try:
            return self.rn.format(**{n: attrs[n] for n in self.naming})
        except KeyError:
            return None

    def parse_rn(self, rn):
        m = self.rn_re.match(rn)
        return m.groupdict() if m else None

    def writable(self):
        return (set(self.attrs) - self.ro) | COMMON_RW


CLASSES = {}


def mo(name, rn, parents, attrs=None, **kw):
    CLASSES[name] = Meta(name, rn, parents, attrs, **kw)


def _vlan(v):
    if v in ('unknown', ''):
        return True
    m = re.match(r'^vlan-(\d+)$', v)
    return bool(m) and 1 <= int(m.group(1)) <= 4094


def _ipmask(v):
    try:
        ipaddress.ip_interface(v)
        return '/' in v
    except ValueError:
        return False


def _ip(v):
    if v in ('', '0.0.0.0'):
        return True
    try:
        ipaddress.ip_address(v)
        return True
    except ValueError:
        return False


PORT_NAMES = {'unspecified': None, 'ftpData': 20, 'smtp': 25, 'dns': 53, 'http': 80,
              'pop3': 110, 'https': 443, 'rtsp': 554}


def _port(v):
    return v in PORT_NAMES or (v.isdigit() and 0 <= int(v) <= 65535)


def _num(v):
    return v.isdigit()


def _rtrid(v):
    return v == '' or _ip(v)


# ---------------------------- System/Container ----------------------------
mo('topRoot', '', (), config=False, fixed=True)
mo('polUni', 'uni', ('topRoot',), fixed=True, label='Policy Universe')
mo('infraInfra', 'infra', ('polUni',), fixed=True, label='Access Policies')
mo('infraFuncP', 'funcprof', ('infraInfra',), fixed=True)
mo('fabricInst', 'fabric', ('polUni',), fixed=True)
mo('fabricProtPol', 'protpol', ('fabricInst',), {'pairT': 'explicit'}, fixed=True,
   label='VPC Protection Policy')
mo('ctrlrInst', 'controller', ('polUni',), fixed=True)
mo('fabricNodeIdentPol', 'nodeidentpol', ('ctrlrInst',), fixed=True)
mo('aaaUserEp', 'userext', ('polUni',), fixed=True)
mo('aaaUser', 'user-{name}', ('aaaUserEp',),
   {'pwd': '', 'firstName': '', 'lastName': '', 'email': '', 'accountStatus': 'active'},
   enums={'accountStatus': ('active', 'inactive')}, label='Local User')

# ---------------------------- Tenant ---------------------------------------
mo('fvTenant', 'tn-{name}', ('polUni',), label='Tenant')
mo('fvCtx', 'ctx-{name}', ('fvTenant',),
   {'pcEnfPref': 'enforced', 'pcEnfDir': 'ingress', 'knwMcastAct': 'permit',
    'ipDataPlaneLearning': 'enabled', 'bdEnforcedEnable': 'no',
    'scope': '', 'pcTag': '', 'seg': ''},
   enums={'pcEnfPref': ('enforced', 'unenforced'), 'pcEnfDir': ('ingress', 'egress'),
          'knwMcastAct': ('permit', 'deny'), 'ipDataPlaneLearning': ED,
          'bdEnforcedEnable': YN},
   ro=('scope', 'pcTag', 'seg'), label='VRF', auto=(('vzAny', {}),))
mo('vzAny', 'any', ('fvCtx',), {'matchT': 'AtleastOne', 'prefGrMemb': 'disabled'},
   enums={'prefGrMemb': ED, 'matchT': ('All', 'AtleastOne', 'AtmostOne', 'None')},
   label='EPG Collection for VRF')
mo('vzRsAnyToProv', 'rsanyToProv-{tnVzBrCPName}', ('vzAny',), {'prio': 'unspecified', 'matchT': 'AtleastOne'},
   rel=('name', 'tnVzBrCPName', 'vzBrCP', 'tenant'), label='Provided Contract')
mo('vzRsAnyToCons', 'rsanyToCons-{tnVzBrCPName}', ('vzAny',), {'prio': 'unspecified'},
   rel=('name', 'tnVzBrCPName', 'vzBrCP', 'tenant'), label='Consumed Contract')
mo('fvBD', 'BD-{name}', ('fvTenant',),
   {'arpFlood': 'no', 'unicastRoute': 'yes', 'unkMacUcastAct': 'proxy',
    'unkMcastAct': 'flood', 'multiDstPktAct': 'bd-flood', 'limitIpLearnToSubnets': 'yes',
    'ipLearning': 'yes', 'epMoveDetectMode': '', 'mac': '00:22:BD:F8:19:FF',
    'type': 'regular', 'seg': '', 'pcTag': '', 'scope': ''},
   enums={'arpFlood': YN, 'unicastRoute': YN, 'unkMacUcastAct': ('proxy', 'flood'),
          'unkMcastAct': ('flood', 'opt-flood'),
          'multiDstPktAct': ('bd-flood', 'encap-flood', 'drop'),
          'limitIpLearnToSubnets': YN, 'ipLearning': YN, 'type': ('regular', 'fc')},
   ro=('seg', 'pcTag', 'scope'), label='Bridge Domain',
   auto=(('fvRsCtx', {'tnFvCtxName': ''}),))
mo('fvRsCtx', 'rsctx', ('fvBD',), {'tnFvCtxName': ''},
   rel=('name', 'tnFvCtxName', 'fvCtx', 'tenant'), label='VRF Association')
mo('fvSubnet', 'subnet-[{ip}]', ('fvBD', 'fvAEPg'),
   {'scope': 'private', 'preferred': 'no', 'virtual': 'no', 'ctrl': 'nd'},
   enums={'preferred': YN, 'virtual': YN},
   sets={'scope': ('private', 'public', 'shared'),
         'ctrl': ('nd', 'no-default-gateway', 'querier', 'unspecified')},
   checks={'ip': _ipmask}, label='Subnet')
mo('fvRsBDToOut', 'rsBDToOut-{tnL3extOutName}', ('fvBD',), {},
   rel=('name', 'tnL3extOutName', 'l3extOut', 'tenant'), label='Associated L3Out')
mo('fvAp', 'ap-{name}', ('fvTenant',), {'prio': 'unspecified'}, label='Application Profile')
mo('fvAEPg', 'epg-{name}', ('fvAp',),
   {'pcEnfPref': 'unenforced', 'prefGrMemb': 'exclude', 'floodOnEncap': 'disabled',
    'isAttrBasedEPg': 'no', 'prio': 'unspecified', 'shutdown': 'no',
    'pcTag': '', 'scope': ''},
   enums={'pcEnfPref': ('enforced', 'unenforced'), 'prefGrMemb': ('include', 'exclude'),
          'floodOnEncap': ED, 'shutdown': YN, 'isAttrBasedEPg': YN},
   ro=('pcTag', 'scope'), label='Application EPG',
   auto=(('fvRsBd', {'tnFvBDName': ''}),))
mo('fvRsBd', 'rsbd', ('fvAEPg',), {'tnFvBDName': ''},
   rel=('name', 'tnFvBDName', 'fvBD', 'tenant'), label='Bridge Domain Association')
mo('fvRsDomAtt', 'rsdomAtt-[{tDn}]', ('fvAEPg',),
   {'instrImedcy': 'lazy', 'resImedcy': 'lazy', 'encap': 'unknown', 'primaryEncap': 'unknown',
    'classPref': 'encap'},
   enums={'instrImedcy': IMMED, 'resImedcy': ('immediate', 'lazy', 'pre-provision')},
   rel=('dn', 'tDn', ('physDomP', 'l3extDomP', 'vmmDomP')), label='Domain Association')
mo('fvRsPathAtt', 'rspathAtt-[{tDn}]', ('fvAEPg',),
   {'encap': '', 'mode': 'regular', 'instrImedcy': 'lazy', 'primaryEncap': 'unknown'},
   enums={'mode': ('regular', 'native', 'untagged'), 'instrImedcy': IMMED},
   checks={'encap': _vlan}, rel=('dn', 'tDn', ('fabricPathEp',)), label='Static Port')
mo('fvRsProv', 'rsprov-{tnVzBrCPName}', ('fvAEPg', 'l3extInstP', 'l2extInstP'),
   {'prio': 'unspecified', 'matchT': 'AtleastOne'},
   rel=('name', 'tnVzBrCPName', 'vzBrCP', 'tenant'), label='Provided Contract')
mo('fvRsCons', 'rscons-{tnVzBrCPName}', ('fvAEPg', 'l3extInstP', 'l2extInstP'), {'prio': 'unspecified'},
   rel=('name', 'tnVzBrCPName', 'vzBrCP', 'tenant'), label='Consumed Contract')

# Operative Endpunkte (vom Simulator gelernt)
mo('fvCEp', 'cep-{mac}', ('fvAEPg', 'l3extInstP', 'l2extInstP', 'vnsEPpInfo'),
   {'ip': '0.0.0.0', 'encap': '', 'lcC': 'learned', 'fabricPathDn': '', 'id': '0',
    'name': '', 'mcastAddr': 'not-applicable', 'contName': '', 'baseEpgDn': ''},
   config=False, label='Client Endpoint')
mo('fvIp', 'ip-[{addr}]', ('fvCEp',), {'createTs': ''}, config=False)
mo('fvRsCEpToPathEp', 'rscEpToPathEp-[{tDn}]', ('fvCEp',), {'state': 'formed', 'lcC': 'learned'},
   config=False)

# ---------------------------- Contracts -----------------------------------
mo('vzBrCP', 'brc-{name}', ('fvTenant',),
   {'scope': 'context', 'prio': 'unspecified', 'targetDscp': 'unspecified'},
   enums={'scope': ('context', 'application-profile', 'tenant', 'global')}, label='Contract')
mo('vzSubj', 'subj-{name}', ('vzBrCP',),
   {'revFltPorts': 'yes', 'consMatchT': 'AtleastOne', 'provMatchT': 'AtleastOne',
    'prio': 'unspecified', 'targetDscp': 'unspecified'},
   enums={'revFltPorts': YN}, label='Contract Subject')
mo('vzRsSubjFiltAtt', 'rssubjFiltAtt-{tnVzFilterName}', ('vzSubj',),
   {'action': 'permit', 'directives': '', 'priorityOverride': 'default'},
   enums={'action': ('permit', 'deny')},
   rel=('name', 'tnVzFilterName', 'vzFilter', 'tenant'), label='Filter')
mo('vzFilter', 'flt-{name}', ('fvTenant',), {}, label='Filter')
mo('vzEntry', 'e-{name}', ('vzFilter',),
   {'etherT': 'unspecified', 'prot': 'unspecified', 'dFromPort': 'unspecified',
    'dToPort': 'unspecified', 'sFromPort': 'unspecified', 'sToPort': 'unspecified',
    'stateful': 'no', 'applyToFrag': 'no', 'arpOpc': 'unspecified',
    'icmpv4T': 'unspecified', 'tcpRules': ''},
   enums={'etherT': ('unspecified', 'ip', 'ipv4', 'ipv6', 'arp', 'mpls_ucast', 'fcoe', 'trill'),
          'prot': ('unspecified', 'icmp', 'igmp', 'tcp', 'egp', 'igp', 'udp', 'icmpv6',
                   'eigrp', 'ospfigp', 'pim', 'l2tp'),
          'stateful': YN, 'applyToFrag': YN},
   sets={'tcpRules': ('', 'est', 'syn', 'ack', 'fin', 'rst', 'unspecified')},
   checks={'dFromPort': _port, 'dToPort': _port, 'sFromPort': _port, 'sToPort': _port},
   label='Filter Entry')

# ---------------------------- L3Out ---------------------------------------
mo('l3extOut', 'out-{name}', ('fvTenant',), {'enforceRtctrl': 'export', 'targetDscp': 'unspecified'},
   sets={'enforceRtctrl': ('export', 'import')}, label='L3Out',
   auto=(('l3extRsEctx', {'tnFvCtxName': ''}),))
mo('l3extRsEctx', 'rsectx', ('l3extOut',), {'tnFvCtxName': ''},
   rel=('name', 'tnFvCtxName', 'fvCtx', 'tenant'), label='VRF')
mo('l3extRsL3DomAtt', 'rsl3DomAtt', ('l3extOut',), {'tDn': ''},
   rel=('dn', 'tDn', ('l3extDomP',)), label='L3 Domain')
mo('ospfExtP', 'ospfExtP', ('l3extOut',),
   {'areaId': 'backbone', 'areaType': 'regular', 'areaCost': '1', 'areaCtrl': 'redistribute,summary'},
   enums={'areaType': ('regular', 'stub', 'nssa')},
   sets={'areaCtrl': ('redistribute', 'summary', 'suppress-fa', 'unspecified')},
   label='OSPF')
mo('bgpExtP', 'bgpExtP', ('l3extOut',), {}, label='BGP')
mo('l3extLNodeP', 'lnodep-{name}', ('l3extOut',), {'tag': 'yellow-green', 'targetDscp': 'unspecified'},
   label='Logical Node Profile')
mo('l3extRsNodeL3OutAtt', 'rsnodeL3OutAtt-[{tDn}]', ('l3extLNodeP',),
   {'rtrId': '', 'rtrIdLoopBack': 'yes', 'configIssues': ''},
   enums={'rtrIdLoopBack': YN}, checks={'rtrId': _rtrid},
   rel=('dn', 'tDn', ('fabricNode',)), label='Configured Node')
mo('ipRouteP', 'rt-[{ip}]', ('l3extRsNodeL3OutAtt',), {'pref': '1', 'aggregate': 'no', 'rtCtrl': ''},
   sets={'rtCtrl': ('', 'bfd')},
   checks={'ip': _ipmask}, label='Static Route')
mo('ipNexthopP', 'nh-[{nhAddr}]', ('ipRouteP',), {'pref': 'unspecified', 'type': 'prefix'},
   checks={'nhAddr': _ip}, label='Next Hop')
mo('l3extLIfP', 'lifp-{name}', ('l3extLNodeP',), {'tag': 'yellow-green'},
   label='Logical Interface Profile')
mo('l3extRsPathL3OutAtt', 'rspathL3OutAtt-[{tDn}]', ('l3extLIfP',),
   {'ifInstT': 'l3-port', 'addr': '0.0.0.0', 'encap': 'unknown', 'mtu': 'inherit',
    'mode': 'regular', 'mac': '00:22:BD:F8:19:FF', 'encapScope': 'local'},
   enums={'ifInstT': ('l3-port', 'sub-interface', 'ext-svi'),
          'mode': ('regular', 'native', 'untagged')},
   checks={'encap': _vlan, 'addr': lambda v: v == '0.0.0.0' or _ipmask(v),
           'mtu': lambda v: v == 'inherit' or (v.isdigit() and 576 <= int(v) <= 9216)},
   rel=('dn', 'tDn', ('fabricPathEp',)), label='Interface')
mo('ospfIfP', 'ospfIfP', ('l3extLIfP',), {'authType': 'none', 'authKeyId': '1'},
   enums={'authType': ('none', 'simple', 'md5')}, label='OSPF Interface Profile')
mo('ospfRsIfPol', 'rsIfPol', ('ospfIfP',), {'tnOspfIfPolName': ''},
   rel=('name', 'tnOspfIfPolName', 'ospfIfPol', 'tenant'), label='OSPF Policy')
mo('ospfIfPol', 'ospfIfPol-{name}', ('fvTenant',),
   {'nwT': 'unspecified', 'ctrl': '', 'helloIntvl': '10', 'deadIntvl': '40',
    'cost': 'unspecified', 'prio': '1', 'rexmitIntvl': '5', 'xmitDelay': '1'},
   enums={'nwT': ('unspecified', 'bcast', 'p2p')},
   sets={'ctrl': ('', 'advert-subnet', 'bfd', 'mtu-ignore', 'passive')},
   checks={'helloIntvl': _num, 'deadIntvl': _num}, label='OSPF Interface Policy')
mo('bgpPeerP', 'peerP-[{addr}]', ('l3extRsPathL3OutAtt', 'l3extLNodeP'),
   {'ctrl': '', 'ttl': '1', 'peerCtrl': '', 'weight': '0', 'allowedSelfAsCnt': '3', 'password': '', 'addrTCtrl': 'af-ucast'},
   sets={'peerCtrl': ('', 'bfd', 'dis-conn-check')},
   checks={'addr': _ip, 'ttl': lambda v: v.isdigit() and 1 <= int(v) <= 255}, label='BGP Peer')
mo('bgpAsP', 'as', ('bgpPeerP', 'bgpInstPol'), {'asn': ''},
   checks={'asn': lambda v: v.isdigit() and 1 <= int(v) <= 4294967295}, label='Autonomous System')
mo('bgpLocalAsnP', 'localasn', ('bgpPeerP',), {'localAsn': '', 'asnPropagate': 'none'},
   label='Local AS')
mo('l3extInstP', 'instP-{name}', ('l3extOut',),
   {'prefGrMemb': 'exclude', 'prio': 'unspecified', 'pcTag': '', 'scope': '', 'floodOnEncap': 'disabled'},
   enums={'prefGrMemb': ('include', 'exclude')}, ro=('pcTag', 'scope'),
   label='External EPG')
mo('l3extSubnet', 'extsubnet-[{ip}]', ('l3extInstP',), {'scope': 'import-security', 'aggregate': ''},
   sets={'scope': ('import-rtctrl', 'export-rtctrl', 'import-security', 'shared-security',
                   'shared-rtctrl'),
         'aggregate': ('', 'export-rtctrl', 'import-rtctrl', 'shared-rtctrl')},
   checks={'ip': _ipmask}, label='External Subnet')

# ---------------------------- Access Policies ------------------------------
mo('fvnsVlanInstP', 'vlanns-[{name}]-{allocMode}', ('infraInfra',), {},
   enums={'allocMode': ('static', 'dynamic')}, label='VLAN Pool')
mo('fvnsEncapBlk', 'from-[{from}]-to-[{to}]', ('fvnsVlanInstP',),
   {'allocMode': 'inherit', 'role': 'external'},
   enums={'allocMode': ('static', 'dynamic', 'inherit'), 'role': ('external', 'internal')},
   checks={'from': _vlan, 'to': _vlan}, label='Encap Block')
mo('physDomP', 'phys-{name}', ('polUni',), {}, label='Physical Domain')
mo('l3extDomP', 'l3dom-{name}', ('polUni',), {}, label='L3 Domain')
mo('infraRsVlanNs', 'rsvlanNs', ('physDomP', 'l3extDomP', 'vmmDomP', 'l2extDomP'), {'tDn': ''},
   rel=('dn', 'tDn', ('fvnsVlanInstP',)), label='VLAN Pool')
mo('infraAttEntityP', 'attentp-{name}', ('infraInfra',), {}, label='Attachable Access Entity Profile')
mo('infraRsDomP', 'rsdomP-[{tDn}]', ('infraAttEntityP',), {},
   rel=('dn', 'tDn', ('physDomP', 'l3extDomP', 'vmmDomP', 'l2extDomP')), label='Domain')
mo('infraAccPortGrp', 'accportgrp-{name}', ('infraFuncP',), {}, label='Leaf Access Port Policy Group')
mo('infraAccBndlGrp', 'accbundle-{name}', ('infraFuncP',), {'lagT': 'link'},
   enums={'lagT': ('link', 'node')}, label='PC/VPC Interface Policy Group')
mo('infraRsAttEntP', 'rsattEntP', ('infraAccPortGrp', 'infraAccBndlGrp'), {'tDn': ''},
   rel=('dn', 'tDn', ('infraAttEntityP',)), label='AAEP')
mo('infraRsCdpIfPol', 'rscdpIfPol', ('infraAccPortGrp', 'infraAccBndlGrp'), {'tnCdpIfPolName': ''},
   rel=('name', 'tnCdpIfPolName', 'cdpIfPol', 'infra'), label='CDP Policy')
mo('infraRsLldpIfPol', 'rslldpIfPol', ('infraAccPortGrp', 'infraAccBndlGrp'), {'tnLldpIfPolName': ''},
   rel=('name', 'tnLldpIfPolName', 'lldpIfPol', 'infra'), label='LLDP Policy')
mo('infraRsHIfPol', 'rshIfPol', ('infraAccPortGrp', 'infraAccBndlGrp'), {'tnFabricHIfPolName': ''},
   rel=('name', 'tnFabricHIfPolName', 'fabricHIfPol', 'infra'), label='Link Level Policy')
mo('infraRsLacpPol', 'rslacpPol', ('infraAccBndlGrp',), {'tnLacpLagPolName': ''},
   rel=('name', 'tnLacpLagPolName', 'lacpLagPol', 'infra'), label='Port Channel Policy')
mo('infraAccPortP', 'accportprof-{name}', ('infraInfra',), {}, label='Leaf Interface Profile')
mo('infraHPortS', 'hports-{name}-typ-{type}', ('infraAccPortP',), {},
   enums={'type': ('range', 'ALL')}, label='Access Port Selector')
mo('infraPortBlk', 'portblk-{name}', ('infraHPortS',),
   {'fromCard': '1', 'toCard': '1', 'fromPort': '1', 'toPort': '1'},
   checks={'fromCard': _num, 'toCard': _num, 'fromPort': _num, 'toPort': _num},
   label='Port Block')
mo('infraRsAccBaseGrp', 'rsaccBaseGrp', ('infraHPortS',), {'tDn': '', 'fexId': '101'},
   rel=('dn', 'tDn', ('infraAccPortGrp', 'infraAccBndlGrp')), label='Interface Policy Group')
mo('infraNodeP', 'nprof-{name}', ('infraInfra',), {}, label='Leaf Profile')
mo('infraLeafS', 'leaves-{name}-typ-{type}', ('infraNodeP',), {},
   enums={'type': ('range', 'ALL')}, label='Leaf Selector')
mo('infraNodeBlk', 'nodeblk-{name}', ('infraLeafS',), {'from_': '0', 'to_': '0'},
   checks={'from_': _num, 'to_': _num}, label='Node Block')
mo('infraRsAccPortP', 'rsaccPortP-[{tDn}]', ('infraNodeP',), {},
   rel=('dn', 'tDn', ('infraAccPortP',)), label='Interface Selector Profile')
mo('cdpIfPol', 'cdpIfP-{name}', ('infraInfra',), {'adminSt': 'enabled'},
   enums={'adminSt': ED}, label='CDP Interface Policy')
mo('lldpIfPol', 'lldpIfP-{name}', ('infraInfra',), {'adminRxSt': 'enabled', 'adminTxSt': 'enabled'},
   enums={'adminRxSt': ED, 'adminTxSt': ED}, label='LLDP Interface Policy')
mo('lacpLagPol', 'lacplagp-{name}', ('infraInfra',),
   {'mode': 'off', 'ctrl': 'fast-sel-hot-stdby,graceful-conv,susp-individual',
    'minLinks': '1', 'maxLinks': '16'},
   enums={'mode': ('off', 'active', 'passive', 'mac-pin', 'mac-pin-nicload', 'explicit-failover')},
   label='Port Channel Policy')
mo('fabricHIfPol', 'hintfpol-{name}', ('infraInfra',), {'speed': 'inherit', 'autoNeg': 'on', 'fecMode': 'inherit'},
   enums={'autoNeg': ('on', 'off'),
          'speed': ('inherit', '100M', '1G', '10G', '25G', '40G', '100G')},
   label='Link Level Policy')

# ---------------------------- Fabric-Policies ------------------------------
mo('fabricExplicitGEp', 'expgep-{name}', ('fabricProtPol',), {'id': ''},
   checks={'id': lambda v: v.isdigit() and 1 <= int(v) <= 1000}, label='VPC Explicit Protection Group')
mo('fabricNodePEp', 'nodepep-{id}', ('fabricExplicitGEp',), {'podId': '1'},
   checks={'id': _num}, label='VPC Node')
mo('bgpInstPol', 'bgpInstP-{name}', ('fabricInst',), {}, label='BGP Route Reflector Policy')
mo('bgpRRP', 'rr', ('bgpInstPol',), {}, label='Route Reflector Nodes')
mo('bgpRRNodePEp', 'node-{id}', ('bgpRRP',), {'podId': '1'}, checks={'id': _num},
   label='Route Reflector Node')
mo('fabricNodeIdentP', 'nodep-{serial}', ('fabricNodeIdentPol',),
   {'nodeId': '0', 'name': '', 'podId': '1', 'role': 'unspecified', 'nodeType': 'unspecified',
    'extPoolId': '0'},
   enums={'role': ('unspecified', 'leaf', 'spine'),
          'nodeType': ('unspecified', 'remote-leaf-wan', 'virtual', 'tier-2-leaf')},
   checks={'nodeId': lambda v: v.isdigit() and 101 <= int(v) <= 4000,
           'name': lambda v: bool(NAME_RE.match(v))},
   label='Fabric Node Member')

# ---------------------------- Operative Klassen ----------------------------
mo('fabricTopology', 'topology', ('topRoot',), config=False, fixed=True)
mo('fabricPod', 'pod-{id}', ('fabricTopology',), {'podType': 'physical'}, config=False)
mo('fabricNode', 'node-{id}', ('fabricPod',),
   {'name': '', 'role': '', 'serial': '', 'model': '', 'fabricSt': '', 'address': '',
    'version': '', 'adSt': 'on', 'nodeType': 'unspecified', 'vendor': 'Cisco Systems, Inc',
    'lastStateModTs': ''},
   config=False, label='Fabric Node')
mo('topSystem', 'sys', ('fabricNode',),
   {'address': '', 'id': '', 'name': '', 'role': '', 'serial': '', 'state': '', 'podId': '1',
    'oobMgmtAddr': '', 'inbMgmtAddr': '0.0.0.0', 'version': '', 'systemUpTime': '',
    'fabricMAC': '', 'tepPool': '10.0.0.0/16', 'fabricDomain': ''}, config=False)
mo('l1PhysIf', 'phys-[{id}]', ('topSystem',),
   {'adminSt': 'up', 'usage': 'discovery', 'mtu': '9000', 'speed': 'inherit', 'layer': 'Layer2',
    'portT': 'leaf', 'mode': 'trunk', 'descr': '', 'autoNeg': 'on'}, config=False,
   label='Physical Interface')
mo('ethpmPhysIf', 'phys', ('l1PhysIf',),
   {'operSt': 'down', 'operStQual': 'link-not-connected', 'operSpeed': 'inherit',
    'operMode': 'trunk', 'bundleIndex': 'unspecified', 'operVlans': '', 'allowedVlans': ''},
   config=False)
mo('fabricPathEpCont', 'paths-{nodeId}', ('fabricPod',), {}, config=False)
mo('fabricProtPathEpCont', 'protpaths-{nodeAId}-{nodeBId}', ('fabricPod',), {}, config=False)
mo('fabricPathEp', 'pathep-[{name}]', ('fabricPathEpCont', 'fabricProtPathEpCont'),
   {'pathT': 'leaf', 'lagT': 'not-aggregated'}, config=False, label='Path Endpoint')
mo('fabricLinkCont', 'lnkcnt-{id}', ('fabricPod',), {}, config=False)
mo('fabricLink', 'lnk-{n1}-{s1}-{p1}-to-{n2}-{s2}-{p2}', ('fabricLinkCont',),
   {'linkState': 'ok', 'wiringIssues': ''}, config=False)
mo('dhcpClient', 'client-[{id}]', ('topSystem',),
   {'model': '', 'nodeRole': '', 'podId': '1', 'fabricId': '1', 'clientEvent': 'pending',
    'nodeId': '0', 'name': '', 'ip': '0.0.0.0', 'supported': 'yes', 'decomissioned': 'no'},
   config=False, label='Node Pending Registration')
mo('faultInst', 'fault-{code}', [],
   {'ack': 'no', 'cause': '', 'changeSet': '', 'created': '', 'descr': '', 'domain': '',
    'highestSeverity': '', 'lastTransition': '', 'lc': 'raised', 'occur': '1',
    'origSeverity': '', 'prevSeverity': '', 'rule': '', 'severity': '', 'subject': '',
    'type': 'config'}, config=False, label='Fault')
mo('healthInst', 'health', [], {'cur': '100', 'maxSev': 'cleared', 'twScore': '100'}, config=False)


# Passive Klassen: echte APIC-Klassen, die Ansible/Terraform mitsenden, die der
# Simulator aber nicht auswertet (QoS, Monitoring, STP, ...). Sie werden
# gespeichert und abgefragt, beliebige Attribute sind erlaubt.
PASSIVE = [
    ('fvTenant', ['fvRsTenantMonPol:rsTenantMonPol']),
    ('fvCtx', ['fvRsCtxToEpRet:rsctxToEpRet', 'fvRsBgpCtxPol:rsbgpCtxPol', 'fvRsOspfCtxPol:rsospfCtxPol',
               'fvRsCtxToExtRouteTagPol:rsctxToExtRouteTagPol', 'fvRsCtxMonPol:rsCtxMonPol',
               'fvRsVrfValidationPol:rsvrfValidationPol', 'fvRsCtxToEigrpCtxAfPol:rsctxToEigrpCtxAfPol-{af}',
               'fvRsCtxToBgpCtxAfPol:rsctxToBgpCtxAfPol-[{tnBgpCtxAfPolName}]-{af}', 'fvRsCtxToOspfCtxPol:rsctxToOspfCtxPol-{af}',
               'fvRsCtxToSDWanVpnAtt:rsctxToSDWanVpnAtt', 'fvRsCtxToExtRouteTagPol:rsctxToExtRouteTagPol']),
    ('fvBD', ['fvRsIgmpsn:rsigmpsn', 'fvRsBdToEpRet:rsbdToEpRet', 'fvRsBDToNdP:rsBDToNdP', 'fvRsBDToProfile:rsBDToProfile',
              'fvRsMldsn:rsmldsn', 'fvRsABDPolMonPol:rsABDPolMonPol', 'fvRsBDToRelayP:rsBDToRelayP',
              'fvRsBDToFhs:rsBDToFhs', 'fvRsBDToNetflowMonitorPol:rsBDToNetflowMonitorPol-[{tnNetflowMonitorPolName}]-{fltType}',
              'fvRsBdFloodTo:rsbdFloodTo-[{tDn}]', 'fvRsBDSubnetToProfile:rsBDSubnetToProfile']),
    ('fvSubnet', ['fvRsBDSubnetToProfile:rsBDSubnetToProfile', 'fvRsNdPfxPol:rsNdPfxPol', 'fvRsBDSubnetToOut:rsBDSubnetToOut-{tnL3extOutName}']),
    ('fvAEPg', ['fvRsCustQosPol:rscustQosPol', 'fvRsAEPgMonPol:rsAEPgMonPol', 'fvRsDppPol:rsdppPol', 'fvRsTrustCtrl:rstrustCtrl',
                'fvRsIntraEpg:rsintraEpg-{tnVzBrCPName}', 
                'fvRsSecInherited:rssecInherited-[{tDn}]', 'fvRsFcPathAtt:rsfcPathAtt-[{tDn}]',
                'fvCrtrn:crtrn', 'fvRsEPgToCollectionStatsPol:rsEPgToCollectionStatsPol']),
    ('fvAp', ['fvRsApMonPol:rsApMonPol']),
    ('vzBrCP', ['vzRsGraphAtt:rsGraphAtt']),
    ('vzSubj', ['vzInTerm:intmnl', 'vzOutTerm:outtmnl', 'vzRsSdwanPol:rssdwanPol']),
    ('vnsAbsGraph', ['vnsAbsTermNodeCon:AbsTermNodeCon-{name}', 'vnsAbsTermNodeProv:AbsTermNodeProv-{name}',
                     'vnsAbsConnection:AbsConnection-{name}']),
    ('vnsAbsNode', ['vnsAbsFuncConn:AbsFConn-{name}', 'vnsRsNodeToAbsFuncProf:rsNodeToAbsFuncProf']),
    ('vnsAbsTermNodeCon', ['vnsAbsTermConn:AbsTConn', 'vnsInTerm:intmnl', 'vnsOutTerm:outtmnl']),
    ('vnsAbsTermNodeProv', ['vnsAbsTermConn:AbsTConn', 'vnsInTerm:intmnl', 'vnsOutTerm:outtmnl']),
    ('vnsAbsConnection', ['vnsRsAbsConnectionConns:rsabsConnectionConns-[{tDn}]']),
    ('vnsSvcRedirectPol', ['vnsRsIPSLAMonitoringPol:rsIPSLAMonitoringPol']),
    ('vnsLDevVip', ['vnsRsALDevToDomP:rsALDevToDomP']),
    ('l3extOut', ['l3extRsInterleakPol:rsinterleakPol', 'l3extRsDampeningPol:rsdampeningPol-[{tnRtctrlProfileName}]-{af}',
                  'l3extRsOutToBDPublicSubnetHolder:rsoutToBDPublicSubnetHolder-[{tDn}]', 'pimExtP:pimextp',
                  'l3extRsRedistributePol:rsredistributePol-[{tnRtctrlProfileName}]-{src}']),
    ('l3extInstP', ['fvRsCustQosPol:rscustQosPol', 'l3extRsInstPToProfile:rsinstPToProfile-[{tnRtctrlProfileName}]-{direction}',
                    'fvRsIntraEpg:rsintraEpg-{tnVzBrCPName}', 'fvRsProtBy:rsprotBy-{tnVzTabooName}',
                    'l3extRsInstPToNatMappingEPg:rsinstPToNatMappingEPg']),
    ('l3extSubnet', ['l3extRsSubnetToProfile:rssubnetToProfile-[{tnRtctrlProfileName}]-{direction}', 'l3extRsSubnetToRtSumm:rsSubnetToRtSumm']),
    ('l3extLNodeP', ['l3extRsNodeL3OutAtt', 'l3extRsLNodePMonPol:rsLNodePMonPol']),
    ('l3extLIfP', ['l3extRsNdIfPol:rsNdIfPol', 'l3extRsIngressQosDppPol:rsIngressQosDppPol', 'l3extRsEgressQosDppPol:rsEgressQosDppPol',
                   'l3extRsLIfPCustQosPol:rslIfPCustQosPol', 'l3extRsArpIfPol:rsArpIfPol', 'l3extRsLIfPToNetflowMonitorPol:rsLIfPToNetflowMonitorPol-[{tnNetflowMonitorPolName}]-{fltType}',
                   'bfdIfP:bfdIfP']),
    ('l3extRsPathL3OutAtt', ['l3extIp:addr-[{addr}]', 'l3extMember:mem-{side}']),
    ('l3extRsNodeL3OutAtt', ['l3extLoopBackIfP:lbp-[{addr}]', 'l3extInfraNodeP:infranodep']),
    ('ospfIfP', ['ospfAuthKey:ospfauthkey']),
    ('infraAttEntityP', ['infraGeneric:gen-{name}', 'infraProvAcc:provacc', 'infraRsOverrideCdpIfPol:rsoverrideCdpIfPol']),
    ('infraLeafS', ['infraRsAccNodePGrp:rsaccNodePGrp']),
    ('infraHPortS', ['infraSubPortBlk:subportblk-{name}']),
]
_PG_RS = ['infraRsMcpIfPol:rsmcpIfPol', 'infraRsStpIfPol:rsstpIfPol', 'infraRsL2IfPol:rsl2IfPol',
          'infraRsStormctrlIfPol:rsstormctrlIfPol', 'infraRsMonIfInfraPol:rsmonIfInfraPol',
          'infraRsQosIngressDppIfPol:rsQosIngressDppIfPol', 'infraRsQosEgressDppIfPol:rsQosEgressDppIfPol',
          'infraRsQosPfcIfPol:rsqosPfcIfPol', 'infraRsQosSdIfPol:rsqosSdIfPol', 'infraRsFcIfPol:rsfcIfPol',
          'infraRsCoppIfPol:rscoppIfPol', 'infraRsL2PortSecurityPol:rsl2PortSecurityPol',
          'infraRsL2PortAuthPol:rsl2PortAuthPol', 'infraRsDwdmIfPol:rsdwdmIfPol', 'infraRsPoeIfPol:rspoeIfPol',
          'infraRsLinkFlapPol:rslinkFlapPol', 'infraRsMacsecIfPol:rsmacsecIfPol', 'infraRsL2InstPol:rsl2InstPol',
          'infraRsQosLlfcIfPol:rsqosLlfcIfPol', 'infraRsSynceEthIfPol:rssynceEthIfPol', 'infraRsCdpIfPol',
          'infraRsSpanVSrcGrp:rsspanVSrcGrp-{tnSpanVSrcGrpName}', 'infraRsSpanVDestGrp:rsspanVDestGrp-{tnSpanVDestGrpName}',
          'infraRsNetflowMonitorPol:rsnetflowMonitorPol-[{tnNetflowMonitorPolName}]-{fltType}']
PASSIVE += [('infraAccPortGrp', _PG_RS), ('infraAccBndlGrp', _PG_RS)]
PASSIVE += [('infraInfra', ['mcpIfPol:mcpIfP-{name}', 'stpIfPol:ifPol-{name}', 'l2IfPol:l2IfP-{name}',
                            'stormctrlIfPol:stormctrlifp-{name}', 'infraAccNodePGrp:funcprof/accnodepgrp-{name}']),
            ('infraFuncP', ['infraAccNodePGrp:accnodepgrp-{name}', 'infraAccBndlPolGrp:accbundlepolgrp-{name}'])]


def _passive():
    for parent, items in PASSIVE:
        for it in items:
            if ':' not in it:
                continue
            cls, rn = it.split(':', 1)
            if '/' in rn:
                continue
            if cls in CLASSES:
                m = CLASSES[cls]
                if parent not in m.parents:
                    m.parents = m.parents + (parent,)
                continue
            CLASSES[cls] = Meta(cls, rn, (parent,), {}, label=cls)
            CLASSES[cls].passive = True


_passive()
STRICT = False


# ---------------------------- Weitere APIC-Funktionen ----------------------
mo('vzTaboo', 'taboo-{name}', ('fvTenant',), {'scope': 'context'}, label='Taboo Contract')
mo('vzTSubj', 'tsubj-{name}', ('vzTaboo',), {}, label='Taboo Subject')
mo('vzRsDenyRule', 'rsdenyRule-{tnVzFilterName}', ('vzTSubj',), {'directives': ''},
   rel=('name', 'tnVzFilterName', 'vzFilter', 'tenant'), label='Deny Filter')
mo('fvRsProtBy', 'rsprotBy-{tnVzTabooName}', ('fvAEPg', 'l3extInstP', 'l2extInstP'), {},
   rel=('name', 'tnVzTabooName', 'vzTaboo', 'tenant'), label='Taboo Contract')
mo('fvRsNodeAtt', 'rsnodeAtt-[{tDn}]', ('fvAEPg',),
   {'encap': '', 'mode': 'regular', 'instrImedcy': 'lazy', 'descr': ''},
   enums={'mode': ('regular', 'native', 'untagged'), 'instrImedcy': IMMED},
   checks={'encap': _vlan}, rel=('dn', 'tDn', ('fabricNode',)), label='Static Leaf')
mo('fabricOOServicePol', 'outofsvc', ('fabricInst',), {}, fixed=True, label='Out of Service Policy')
mo('fabricRsOosPath', 'rsoosPath-[{tDn}]', ('fabricOOServicePol',), {'lc': 'blacklist'},
   rel=('dn', 'tDn', ('fabricPathEp',)), label='Disabled Interface')
mo('mgmtMgmtP', 'mgmtp-{name}', ('fvTenant',), {}, label='Management Profile')
mo('mgmtOoB', 'oob-{name}', ('mgmtMgmtP',), {}, label='Out-of-Band EPG')
mo('mgmtRsOoBStNode', 'rsooBStNode-[{tDn}]', ('mgmtOoB',), {'addr': '', 'gw': '', 'v6Addr': '::', 'v6Gw': '::'},
   checks={'addr': lambda v: v == '' or _ipmask(v), 'gw': _ip},
   rel=('dn', 'tDn', ('fabricNode',)), label='Static Node Management Address')
mo('datetimePol', 'time-{name}', ('fabricInst',), {'adminSt': 'enabled', 'authSt': 'disabled', 'serverState': 'disabled',
                                                  'masterMode': 'disabled', 'StratumValue': '8'},
   enums={'adminSt': ED, 'authSt': ED, 'serverState': ED, 'masterMode': ED}, label='Date and Time Policy')
mo('datetimeNtpProv', 'ntpprov-{name}', ('datetimePol',), {'preferred': 'no', 'minPoll': '4', 'maxPoll': '6',
                                                           'keyId': '0', 'trueChimer': 'disabled'},
   enums={'preferred': YN}, label='NTP Server')
mo('datetimeRsNtpProvToEpg', 'rsNtpProvToEpg', ('datetimeNtpProv',), {'tDn': ''},
   rel=('dn', 'tDn', ('mgmtOoB',)), label='Management EPG')
mo('fabricFuncP', 'funcprof', ('fabricInst',), {}, fixed=True)
mo('fabricPodPGrp', 'podpgrp-{name}', ('fabricFuncP',), {}, label='Pod Policy Group')
mo('fabricRsTimePol', 'rsTimePol', ('fabricPodPGrp',), {'tnDatetimePolName': ''},
   rel=('name', 'tnDatetimePolName', 'datetimePol', 'fabric'), label='Date Time Policy')
mo('fabricPodP', 'podprof-{name}', ('fabricInst',), {}, label='Pod Profile')
mo('fabricPodS', 'pods-{name}-typ-{type}', ('fabricPodP',), {}, enums={'type': ('ALL', 'range')}, label='Pod Selector')
mo('fabricRsPodPGrp', 'rspodPGrp', ('fabricPodS',), {'tDn': ''},
   rel=('dn', 'tDn', ('fabricPodPGrp',)), label='Pod Policy Group')
mo('aaaModLR', 'mod-{id}', [], {'affected': '', 'cause': 'transition', 'changeSet': '', 'code': 'E4206326',
                                'created': '', 'descr': '', 'ind': '', 'severity': 'info', 'trig': 'config',
                                'txId': '', 'user': ''}, config=False, label='Audit Log')
mo('eventRecord', 'rec-{id}', [], {'affected': '', 'cause': '', 'changeSet': '', 'code': '', 'created': '',
                                   'descr': '', 'ind': 'state-transition', 'severity': 'info', 'trig': 'oper',
                                   'user': 'internal'}, config=False, label='Event')


# ---------------------------- VMM ------------------------------------------
mo('vmmProvP', 'vmmp-{vendor}', ('polUni',), {}, fixed=True, label='VMM Provider')
mo('vmmDomP', 'dom-{name}', ('vmmProvP',), {'mode': 'default', 'enfPref': 'hw', 'encapMode': 'auto',
                                           'mcastAddr': '0.0.0.0', 'delimiter': '', 'configInfraPg': 'no'},
   enums={'mode': ('default', 'n1kv', 'unknown', 'ovs', 'k8s', 'rhev', 'cf', 'openshift'), 'enfPref': ('hw', 'sw', 'unknown'),
          'encapMode': ('auto', 'vlan', 'vxlan', 'unknown')}, label='VMM Domain')
mo('vmmCtrlrP', 'ctrlr-{name}', ('vmmDomP',), {'hostOrIp': '', 'rootContName': '', 'mode': 'default',
                                              'dvsVersion': 'unmanaged', 'port': '0', 'statsMode': 'disabled'},
   enums={'statsMode': ED}, label='vCenter Controller')
mo('vmmRsAcc', 'rsacc', ('vmmCtrlrP',), {'tDn': ''}, rel=('dn', 'tDn', ('vmmUsrAccP',)), label='Credentials')
mo('vmmUsrAccP', 'usracc-{name}', ('vmmDomP',), {'usr': '', 'pwd': ''}, label='vCenter Credential')
mo('vmmVSwitchPolicyCont', 'vswitchpolcont', ('vmmDomP',), {}, label='vSwitch Policy')
mo('vmmRsVswitchOverrideLldpIfPol', 'rsvswitchOverrideLldpIfPol', ('vmmVSwitchPolicyCont',), {'tDn': ''},
   rel=('dn', 'tDn', ('lldpIfPol',)), label='LLDP Policy')
mo('vmmRsVswitchOverrideCdpIfPol', 'rsvswitchOverrideCdpIfPol', ('vmmVSwitchPolicyCont',), {'tDn': ''},
   rel=('dn', 'tDn', ('cdpIfPol',)), label='CDP Policy')
mo('vmmRsVswitchOverrideLacpPol', 'rsvswitchOverrideLacpPol', ('vmmVSwitchPolicyCont',), {'tDn': ''},
   rel=('dn', 'tDn', ('lacpLagPol',)), label='Port Channel Policy')

# ---------------------------- Route Control --------------------------------
mo('rtctrlProfile', 'prof-{name}', ('l3extOut', 'fvTenant'), {'type': 'combinable'},
   enums={'type': ('combinable', 'global')}, label='Route Map for Import and Export Route Control')
mo('rtctrlCtxP', 'ctx-{name}', ('rtctrlProfile',), {'order': '0', 'action': 'permit'},
   enums={'action': ('permit', 'deny')}, label='Context')
mo('rtctrlRsCtxPToSubjP', 'rsctxPToSubjP-{tnRtctrlSubjPName}', ('rtctrlCtxP',), {},
   rel=('name', 'tnRtctrlSubjPName', 'rtctrlSubjP', 'tenant'), label='Associated Matched Rule')
mo('rtctrlSubjP', 'subj-{name}', ('fvTenant',), {}, label='Match Rule')
mo('rtctrlMatchRtDest', 'dest-[{ip}]', ('rtctrlSubjP',), {'aggregate': 'no', 'fromPfxLen': '0', 'toPfxLen': '0'},
   enums={'aggregate': ('yes', 'no')}, label='Match Prefix')

# ---------------------------- L3Out-Varianten ------------------------------
mo('l3extMember', 'mem-{side}', ('l3extRsPathL3OutAtt',), {'addr': '0.0.0.0', 'ipv6Dad': 'enabled', 'llAddr': '::'},
   enums={'side': ('A', 'B')}, checks={'addr': lambda v: v == '0.0.0.0' or _ipmask(v)}, label='vPC Member (Side A/B)')
mo('l3extIp', 'addr-[{addr}]', ('l3extRsPathL3OutAtt', 'l3extMember', 'l3extVirtualLIfP'), {'ipv6Dad': 'enabled'},
   checks={'addr': _ipmask}, label='Secondary IP')
mo('l3extVirtualLIfP', 'vlifp-[{nodeDn}]-[{encap}]', ('l3extLIfP',),
   {'addr': '0.0.0.0', 'ifInstT': 'ext-svi', 'mtu': 'inherit', 'encapScope': 'local', 'mode': 'regular', 'mac': '00:22:BD:F8:19:FF'},
   checks={'encap': _vlan, 'addr': lambda v: v == '0.0.0.0' or _ipmask(v)}, label='Floating SVI')
mo('l3extRsDynPathAtt', 'rsdynPathAtt-[{tDn}]', ('l3extVirtualLIfP',), {'floatingAddr': '0.0.0.0', 'encap': 'unknown'},
   rel=('dn', 'tDn', ('physDomP', 'vmmDomP')), label='Floating Path (Domain)')
mo('bfdIfP', 'bfdIfP', ('l3extLIfP',), {'type': 'none', 'keyId': '1'}, enums={'type': ('none', 'sha1')}, label='BFD Interface Profile')
mo('bfdRsIfPol', 'rsIfPol', ('bfdIfP',), {'tnBfdIfPolName': ''}, rel=('name', 'tnBfdIfPolName', 'bfdIfPol', 'tenant'), label='BFD Policy')
mo('bfdIfPol', 'bfdIfPol-{name}', ('fvTenant',), {'adminSt': 'enabled', 'minTxIntvl': '50', 'minRxIntvl': '50', 'detectMult': '3', 'ctrl': ''},
   enums={'adminSt': ('enabled', 'disabled')}, label='BFD Interface Policy')
mo('eigrpExtP', 'eigrpExtP', ('l3extOut',), {'asn': '1'}, checks={'asn': lambda v: v.isdigit() and 1 <= int(v) <= 65535}, label='EIGRP')
mo('eigrpIfP', 'eigrpIfP', ('l3extLIfP',), {}, label='EIGRP Interface Profile')
mo('eigrpRsIfPol', 'rsIfPol', ('eigrpIfP',), {'tnEigrpIfPolName': ''}, rel=('name', 'tnEigrpIfPolName', 'eigrpIfPol', 'tenant'), label='EIGRP Policy')
mo('eigrpIfPol', 'eigrpIfPol-{name}', ('fvTenant',), {'helloIntvl': '5', 'holdIntvl': '15', 'bw': '0', 'delay': '0', 'ctrl': 'nh-self,split-horizon'},
   checks={'helloIntvl': _num, 'holdIntvl': _num}, label='EIGRP Interface Policy')
mo('ospfRtSummPol', 'ospfrtsumm-{name}', ('fvTenant',), {'cost': 'unspecified', 'interAreaEnabled': 'no', 'tag': '0'}, label='OSPF Route Summarization Policy')
mo('bgpRtSummPol', 'bgprtsum-{name}', ('fvTenant',), {'ctrl': '', 'attrmap': ''}, sets={'ctrl': ('', 'as-set', 'summary-only')},
   label='BGP Route Summarization Policy')
mo('eigrpRtSummPol', 'eigrprtsum-{name}', ('fvTenant',), {}, label='EIGRP Route Summarization Policy')
mo('l3extRsSubnetToRtSumm', 'rsSubnetToRtSumm', ('l3extSubnet',), {'tDn': ''},
   rel=('dn', 'tDn', ('ospfRtSummPol', 'bgpRtSummPol', 'eigrpRtSummPol')), label='Route Summarization Policy')
mo('fvIPSLAMonitoringPol', 'ipslaMonitoringPol-{name}', ('fvTenant',), {'slaType': 'icmp', 'slaFrequency': '60', 'slaPort': '0'},
   enums={'slaType': ('icmp', 'tcp', 'l2ping', 'http')}, label='IP SLA Monitoring Policy')
mo('fvTrackMember', 'trackmember-{name}', ('fvTenant',), {'dstIpAddr': '', 'scopeDn': ''}, checks={'dstIpAddr': _ip}, label='Track Member')
mo('fvRsIpslaMonPol', 'rsIpslaMonPol', ('fvTrackMember',), {'tDn': ''}, rel=('dn', 'tDn', ('fvIPSLAMonitoringPol',)), label='IP SLA Policy')
mo('fvTrackList', 'tracklist-{name}', ('fvTenant',), {'type': 'percentage', 'percentageUp': '1', 'percentageDown': '0', 'weightUp': '1', 'weightDown': '0'},
   enums={'type': ('percentage', 'weight')}, label='Track List')
mo('fvRsOtmListMember', 'rsotmListMember-[{tDn}]', ('fvTrackList',), {'weight': '10'}, rel=('dn', 'tDn', ('fvTrackMember',)), label='Track Member')
mo('ipRsRouteTrack', 'rsRouteTrack', ('ipRouteP',), {'tDn': ''}, rel=('dn', 'tDn', ('fvTrackList',)), label='Track Policy')
mo('ipRsNexthopRouteTrack', 'rsNexthopRouteTrack', ('ipNexthopP',), {'tDn': ''}, rel=('dn', 'tDn', ('fvTrackList',)), label='Track Policy')
mo('bgpCtxPol', 'bgpCtxP-{name}', ('fvTenant',), {'holdIntvl': '180', 'kaIntvl': '60', 'staleIntvl': '300', 'grCtrl': 'helper', 'maxAsLimit': '0'},
   checks={'holdIntvl': _num, 'kaIntvl': _num}, label='BGP Timers Policy')
mo('fvRsBgpCtxPol', 'rsbgpCtxPol', ('fvCtx',), {'tnBgpCtxPolName': ''}, rel=('name', 'tnBgpCtxPolName', 'bgpCtxPol', 'tenant'), label='BGP Timers')

# ---------------------------- L4-L7 Service Graph / PBR ----------------------
mo('vnsLDevVip', 'lDevVip-{name}', ('fvTenant',), {'devtype': 'PHYSICAL', 'funcType': 'GoTo', 'managed': 'no', 'svcType': 'FW',
                                                 'isCopy': 'no', 'contextAware': 'single-Context', 'trunking': 'no', 'mode': 'legacy-Mode'},
   enums={'devtype': ('PHYSICAL', 'VIRTUAL', 'CLOUD'), 'funcType': ('GoTo', 'GoThrough', 'L1', 'L2', 'None'),
          'svcType': ('FW', 'ADC', 'OTHERS', 'COPY', 'NATIVELB')}, label='L4-L7 Device')
mo('vnsRsALDevToPhysDomP', 'rsALDevToPhysDomP', ('vnsLDevVip',), {'tDn': ''}, rel=('dn', 'tDn', ('physDomP',)), label='Physical Domain')
mo('vnsCDev', 'cDev-{name}', ('vnsLDevVip',), {}, label='Concrete Device')
mo('vnsCIf', 'cIf-[{name}]', ('vnsCDev',), {}, label='Concrete Interface')
mo('vnsRsCIfPathAtt', 'rsCIfPathAtt', ('vnsCIf',), {'tDn': ''}, rel=('dn', 'tDn', ('fabricPathEp',)), label='Path')
mo('vnsLIf', 'lIf-{name}', ('vnsLDevVip',), {'encap': 'unknown'}, checks={'encap': _vlan}, label='Cluster Interface')
mo('vnsRsCIfAttN', 'rscIfAttN-[{tDn}]', ('vnsLIf',), {}, rel=('dn', 'tDn', ('vnsCIf',)), label='Concrete Interface')
mo('vnsAbsGraph', 'AbsGraph-{name}', ('fvTenant',), {'type': 'legacy', 'uiTemplateType': 'UNSPECIFIED'}, label='L4-L7 Service Graph Template')
mo('vnsAbsNode', 'AbsNode-{name}', ('vnsAbsGraph',), {'funcTemplateType': 'FW_ROUTED', 'funcType': 'GoTo', 'routingMode': 'Redirect',
                                                     'managed': 'no', 'sequenceNumber': '0', 'isCopy': 'no', 'shareEncap': 'no'},
   enums={'routingMode': ('Redirect', 'unspecified'), 'funcType': ('GoTo', 'GoThrough', 'L1', 'L2', 'None')}, label='Function Node')
mo('vnsRsNodeToLDev', 'rsNodeToLDev', ('vnsAbsNode',), {'tDn': ''}, rel=('dn', 'tDn', ('vnsLDevVip',)), label='L4-L7 Device')
mo('vzRsSubjGraphAtt', 'rsSubjGraphAtt', ('vzSubj',), {'directives': ''},
   rel=('name', 'tnVnsAbsGraphName', 'vnsAbsGraph', 'tenant'), label='L4-L7 Service Graph')
mo('vnsLDevCtx', 'ldevCtx-c-{ctrctNameOrLbl}-g-{graphNameOrLbl}-n-{nodeNameOrLbl}', ('fvTenant',), {'context': ''},
   label='Device Selection Policy')
mo('vnsRsLDevCtxToLDev', 'rsLDevCtxToLDev', ('vnsLDevCtx',), {'tDn': ''}, rel=('dn', 'tDn', ('vnsLDevVip',)), label='L4-L7 Device')
mo('vnsLIfCtx', 'lIfCtx-c-{connNameOrLbl}', ('vnsLDevCtx',), {'l3Dest': 'yes', 'permitLog': 'no'}, label='Logical Interface Context')
mo('vnsRsLIfCtxToBD', 'rsLIfCtxToBD', ('vnsLIfCtx',), {'tDn': ''}, rel=('dn', 'tDn', ('fvBD',)), label='Bridge Domain')
mo('vnsRsLIfCtxToLIf', 'rsLIfCtxToLIf', ('vnsLIfCtx',), {'tDn': ''}, rel=('dn', 'tDn', ('vnsLIf',)), label='Cluster Interface')
mo('vnsRsLIfCtxToSvcRedirectPol', 'rsLIfCtxToSvcRedirectPol', ('vnsLIfCtx',), {'tDn': ''},
   rel=('dn', 'tDn', ('vnsSvcRedirectPol',)), label='L4-L7 Policy-Based Redirect')
mo('vnsSvcCont', 'svcCont', ('fvTenant',), {}, label='Service Container')
mo('vnsSvcRedirectPol', 'svcRedirectPol-{name}', ('vnsSvcCont',), {'hashingAlgorithm': 'sip-dip-prototype', 'thresholdEnable': 'no',
                                                                  'destType': 'L3', 'anycastEnabled': 'no'},
   label='L4-L7 Policy-Based Redirect')
mo('vnsRedirectDest', 'RedirectDest_ip-[{ip}]', ('vnsSvcRedirectPol',), {'mac': '', 'destName': ''}, label='Redirect Destination')
mo('vnsGraphInst', 'GraphInst_C-[{ctrctDn}]-G-[{graphDn}]-S-[{scopeDn}]', ('fvTenant',),
   {'configSt': 'applied', 'descr': ''}, config=False, label='Deployed Graph Instance')
mo('vnsEPpInfo', 'EPpInfo-{name}', ('vnsGraphInst',), {'pcTag': '', 'bdDn': '', 'encap': ''}, config=False, label='Service EPG (Shadow EPG)')

# ---------------------------- Imported Contracts ---------------------------
mo('vzCPIf', 'cif-{name}', ('fvTenant',), {}, label='Imported Contract')
mo('vzRsIf', 'rsif', ('vzCPIf',), {'tDn': '', 'prio': 'unspecified'}, rel=('dn', 'tDn', ('vzBrCP',)), label='Exported Contract')
mo('fvRsConsIf', 'rsconsIf-{tnVzCPIfName}', ('fvAEPg', 'l3extInstP', 'l2extInstP'), {'prio': 'unspecified'},
   rel=('name', 'tnVzCPIfName', 'vzCPIf', 'tenant'), label='Consumed Contract Interface')

# ---------------------------- L2Out ----------------------------------------
mo('l2extDomP', 'l2dom-{name}', ('polUni',), {}, label='External Bridged Domain')
mo('l2extOut', 'l2out-{name}', ('fvTenant',), {'targetDscp': 'unspecified'}, label='L2Out')
mo('l2extRsEBd', 'rseBd', ('l2extOut',), {'tnFvBDName': '', 'encap': 'unknown'}, checks={'encap': _vlan},
   rel=('name', 'tnFvBDName', 'fvBD', 'tenant'), label='Bridge Domain')
mo('l2extRsL2DomAtt', 'rsl2DomAtt', ('l2extOut',), {'tDn': ''}, rel=('dn', 'tDn', ('l2extDomP',)), label='External Bridged Domain')
mo('l2extLNodeP', 'lnodep-{name}', ('l2extOut',), {}, label='Node Profile')
mo('l2extLIfP', 'lifp-{name}', ('l2extLNodeP',), {}, label='Interface Profile')
mo('l2extRsPathL2OutAtt', 'rspathL2OutAtt-[{tDn}]', ('l2extLIfP',), {'targetDscp': 'unspecified'},
   rel=('dn', 'tDn', ('fabricPathEp',)), label='Path')
mo('l2extInstP', 'instP-{name}', ('l2extOut',), {'prefGrMemb': 'exclude', 'pcTag': '', 'scope': ''},
   enums={'prefGrMemb': ('include', 'exclude')}, ro=('pcTag', 'scope'), label='External Network (L2)')

def check_attr(meta, k, v, dn):
    if not isinstance(v, str):
        raise AciError(801, "property %s of %s failed validation for value '%s'" % (k, dn, v))
    if k in meta.enums and v not in meta.enums[k]:
        raise AciError(801, "property %s of %s failed validation for value '%s'" % (k, dn, v))
    if k in meta.sets:
        for part in v.split(','):
            if part not in meta.sets[k]:
                raise AciError(801, "property %s of %s failed validation for value '%s'" % (k, dn, v))
    if k in meta.checks and not meta.checks[k](v):
        raise AciError(801, "property %s of %s failed validation for value '%s'" % (k, dn, v))
    if k == 'name' and 'name' in meta.naming and not NAME_RE.match(v):
        raise AciError(801, "property name of %s failed validation for value '%s'" % (dn, v))


# --------------------------------------------------------------------------
# Objektspeicher
# --------------------------------------------------------------------------

class Store:
    """Hält alle Objekte. Konfigurationsobjekte werden gespeichert,
    operative Objekte (oper=True) erzeugt die Engine bei jedem Neuaufbau."""

    def __init__(self):
        self.objs = {}      # dn -> [cls, attrs, oper]
        self.kids = {}      # dn -> {child_dn: None}
        self.idx = {}       # cls -> {dn: None}
        self.counters = {'vnid': 0, 'seg': 0, 'pctag': 0}

    def get(self, dn):
        return self.objs.get(dn)

    def attrs(self, dn):
        o = self.objs.get(dn)
        return o[1] if o else None

    def add(self, dn, cls, attrs, oper=False):
        if dn not in self.objs and dn != '':
            self.kids.setdefault(parent_dn(dn), {})[dn] = None
        old = self.objs.get(dn)
        if old and old[0] != cls:
            self.idx.get(old[0], {}).pop(dn, None)
        self.objs[dn] = [cls, attrs, oper]
        self.idx.setdefault(cls, {})[dn] = None

    def delete(self, dn):
        for c in list(self.kids.get(dn, {})):
            self.delete(c)
        self.kids.pop(dn, None)
        o = self.objs.pop(dn, None)
        if o:
            self.idx.get(o[0], {}).pop(dn, None)
            self.kids.get(parent_dn(dn), {}).pop(dn, None)

    def children(self, dn, cls=None):
        out = list(self.kids.get(dn, {}))
        if cls:
            if isinstance(cls, str):
                cls = (cls,)
            out = [c for c in out if self.objs[c][0] in cls]
        return out

    def child(self, dn, rn):
        d = dn + '/' + rn
        return d if d in self.objs else None

    def by_class(self, cls):
        return list(self.idx.get(cls, {}))

    def subtree(self, dn):
        out = [dn]
        for c in self.kids.get(dn, {}):
            out.extend(self.subtree(c))
        return out

    def clear_oper(self):
        for dn in [d for d, o in self.objs.items() if o[2]]:
            if dn in self.objs:
                self.delete(dn)

    def backup(self):
        return ({d: [o[0], dict(o[1]), o[2]] for d, o in self.objs.items()},
                {k: dict(v) for k, v in self.kids.items()},
                {k: dict(v) for k, v in self.idx.items()}, dict(self.counters))

    def restore(self, b):
        self.objs, self.kids, self.idx, self.counters = b[0], b[1], b[2], b[3]

    def dump_config(self):
        return [[d, o[0], o[1]] for d, o in self.objs.items() if not o[2]]

    def load_config(self, rows, counters=None):
        self.objs, self.kids, self.idx = {}, {}, {}
        rows = sorted(rows, key=lambda r: len(split_dn(r[0])))
        for dn, cls, attrs in rows:
            if cls in CLASSES:
                self.add(dn, cls, attrs)
        if counters:
            self.counters.update(counters)


def now_ts(t=None):
    t = time.time() if t is None else t
    lt = time.localtime(t)
    off = -time.altzone if lt.tm_isdst > 0 else -time.timezone
    return time.strftime('%Y-%m-%dT%H:%M:%S', lt) + '.%03d' % int((t % 1) * 1000) + \
        '%+03d:%02d' % (off // 3600, abs(off) % 3600 // 60)


# --------------------------------------------------------------------------
# Schreiben (POST/DELETE) - atomar wie beim APIC
# --------------------------------------------------------------------------

def _alloc(store, meta, attrs):
    c = store.counters
    if meta.name == 'fvCtx':
        c['vnid'] += 1
        attrs['scope'] = str(2097152 + 32768 * c['vnid'])
        attrs['seg'] = attrs['scope']
    if meta.name == 'fvBD':
        c['seg'] += 1
        attrs['seg'] = str(15990000 + 4099 * c['seg'])
    if meta.name in ('fvCtx', 'fvBD', 'fvAEPg', 'l3extInstP'):
        c['pctag'] += 1
        attrs['pcTag'] = str(16385 + c['pctag'] if meta.name == 'fvCtx' else 32769 + c['pctag'])


def create_obj(store, dn, cls, attrs, ts):
    meta = CLASSES[cls]
    a = dict(meta.attrs)
    a.update(attrs)
    a['modTs'] = ts
    _alloc(store, meta, a)
    store.add(dn, cls, a)
    for acls, aattrs in meta.auto:
        am = CLASSES[acls]
        adn = dn + '/' + am.make_rn(aattrs)
        if adn not in store.objs:
            create_obj(store, adn, acls, dict(aattrs), ts)


def post(store, url_dn, body, ts=None):
    """Verarbeitet einen POST wie der APIC. Gibt die Liste geänderter DNs zurück."""
    ts = ts or now_ts()
    if not isinstance(body, dict) or len(body) != 1:
        raise AciError(107, 'Malformed request: body must contain exactly one root object')
    backup = store.backup()
    changed = []
    try:
        _post_node(store, body, None, url_dn, ts, changed)
    except AciError:
        store.restore(backup)
        raise
    except Exception as e:  # noqa
        store.restore(backup)
        raise AciError(107, 'Malformed request: %s' % e)
    return changed


def _post_node(store, node, parent, url_dn, ts, changed):
    if not isinstance(node, dict) or len(node) != 1:
        raise AciError(107, 'Malformed request: each element must contain exactly one class')
    cls, content = next(iter(node.items()))
    meta = CLASSES.get(cls)
    if meta is None:
        raise AciError(122, 'unknown managed object class %s' % cls)
    content = content or {}
    attrs = dict(content.get('attributes') or {})
    children = content.get('children') or []
    status = attrs.pop('status', '') or ''
    dn = attrs.pop('dn', None)
    attrs.pop('rn', None)

    if dn is None:
        if all(attrs.get(n) not in (None, '') for n in meta.naming):
            rn = meta.make_rn(attrs)
            if parent is not None:
                dn = parent + '/' + rn
            elif url_dn is not None:
                dn = url_dn if (url_dn == rn or url_dn.endswith('/' + rn)) else (
                    url_dn + '/' + rn if url_dn else rn)
        elif parent is None and url_dn is not None and meta.parse_rn(rn_of(url_dn)) is not None:
            dn = url_dn
        if dn is None:
            raise AciError(103, 'Naming property missing for class %s (%s)' % (
                cls, ', '.join(meta.naming)))
    if parent is not None and parent_dn(dn) != parent:
        raise AciError(103, 'dn %s is not a child of %s' % (dn, parent))

    if dn in ('', 'uni') or meta.fixed:
        if dn not in store.objs:
            raise AciError(102, 'configured object (%s) not found' % dn)
        if 'deleted' in status:
            raise AciError(105, 'Cannot delete system object %s' % dn)
        for k, v in attrs.items():
            if k in meta.writable():
                store.objs[dn][1][k] = v
        for ch in children:
            _post_node(store, ch, dn, None, ts, changed)
        return

    parsed = meta.parse_rn(rn_of(dn))
    if parsed is None:
        raise AciError(103, 'Invalid rn %s for class %s' % (rn_of(dn), cls))
    for k, v in parsed.items():
        if attrs.get(k) not in (None, '') and attrs[k] != v:
            raise AciError(103, 'Naming property %s=%s does not match dn %s' % (k, attrs[k], dn))
        attrs[k] = v

    if 'deleted' in status:
        if dn in store.objs:
            if store.objs[dn][2]:
                raise AciError(106, 'Object %s is not configurable' % dn)
            store.delete(dn)
            changed.append({'dn': dn, 'cls': cls, 'ind': 'deletion', 'changes': {}})
        return
    if not meta.config:
        raise AciError(106, 'Class %s is not configurable' % cls)

    pdn = parent_dn(dn)
    pobj = store.objs.get(pdn)
    if pobj is None:
        raise AciError(102, 'configured object ((%s)) not found' % pdn)
    if meta.parents and pobj[0] not in meta.parents:
        raise AciError(103, 'Class %s cannot be contained in %s (%s)' % (cls, pobj[0], pdn))

    allowed = meta.writable()
    clean = {}
    for k, v in attrs.items():
        if k in COMMON_RO or k in meta.ro:
            continue
        if k not in allowed:
            if (STRICT and not getattr(meta, 'passive', False)) or not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', k):
                raise AciError(121, "unknown attribute '%s' in element '%s'" % (k, cls))
        v = '' if v is None else str(v)
        check_attr(meta, k, v, dn)
        clean[k] = v

    exists = dn in store.objs
    if exists and status == 'created':
        raise AciError(103, 'Cannot create %s; object already exists.' % dn)
    if not exists and status == 'modified':
        raise AciError(102, 'configured object (%s) not found' % dn)
    if exists:
        if store.objs[dn][2]:
            raise AciError(106, 'Object %s is not configurable' % dn)
        cur = store.objs[dn][1]
        diff = {k: (cur.get(k, ''), v) for k, v in clean.items() if cur.get(k, '') != v}
        cur.update(clean)
        if diff:
            cur['modTs'] = ts
            changed.append({'dn': dn, 'cls': cls, 'ind': 'modification', 'changes': diff})
    else:
        create_obj(store, dn, cls, clean, ts)
        changed.append({'dn': dn, 'cls': cls, 'ind': 'creation',
                        'changes': {k: ('', v) for k, v in clean.items()}})
    for ch in children:
        _post_node(store, ch, dn, None, ts, changed)


def delete(store, dn):
    o = store.objs.get(dn)
    if o is None:
        return []
    meta = CLASSES[o[0]]
    if meta.fixed or dn in ('', 'uni') or o[2]:
        raise AciError(105, 'Cannot delete object %s' % dn)
    store.delete(dn)
    return [{'dn': dn, 'cls': o[0], 'ind': 'deletion', 'changes': {}}]
