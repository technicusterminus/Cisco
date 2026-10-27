/* Formular- und Baum-Spezifikationen je ACI-Klasse */
'use strict';

const NAME = { k: 'name', l: 'Name', create: true, req: true, ph: 'z. B. Web' };
const DESCR = { k: 'descr', l: 'Description', ph: 'optional' };
const IMM = [['lazy', 'On Demand'], ['immediate', 'Immediate']];
const RES_IMM = [['lazy', 'On Demand'], ['immediate', 'Immediate'], ['pre-provision', 'Pre-provision']];
const PORTS = ['unspecified', 'http', 'https', 'dns', 'smtp', 'ftpData', 'pop3', 'rtsp', '22', '443', '8080', '3306'];

const relName = (rel, k, l, target, extra) => Object.assign({ rel, k, l, t: 'tname', target }, extra || {});
const relDn = (rel, l, target, extra) => Object.assign({ rel, k: 'tDn', l, t: 'tdn', target: [].concat(target) }, extra || {});
const relState = (row) => stateBadge(row.state);
const col = (l, f) => ({ l, f });
const ac = k => col({ name: 'Name', descr: 'Description' }[k] || k, r => r[k]);

function relOf(dn, rel, k) { const a = MIT.a(dn + '/' + makeRn(rel, {})); return a ? a[k] : ''; }
function nameOfDn(dn) { if (!dn) return ''; const rn = rnOf(dn); return rn.replace(/^[a-zA-Z]+-\[?/, '').replace(/\]?$/, '').replace(/-(static|dynamic)$/, ''); }

function parsePorts(text) {
  const out = [];
  String(text || '').split(',').map(s => s.trim()).filter(Boolean).forEach(p => {
    const m = /^(?:1\/)?(\d+)(?:\s*-\s*(?:1\/)?(\d+))?$/.exec(p);
    if (!m) throw new ApiError('Eingabe', 'Ports im Format 1-10 oder 1,3,5-7 angeben');
    out.push([Number(m[1]), Number(m[2] || m[1])]);
  });
  if (!out.length) throw new ApiError('Eingabe', 'Mindestens einen Port angeben');
  return out;
}

const SPEC = {
  /* ---------------- Tenant ---------------- */
  fvTenant: { fields: [NAME, DESCR], cols: [ac('name'), ac('descr')] },
  fvCtx: {
    fields: [NAME,
      { k: 'pcEnfPref', l: 'Policy Control Enforcement Preference', t: 'radio', o: [['enforced', 'Enforced'], ['unenforced', 'Unenforced']] },
      { k: 'pcEnfDir', l: 'Policy Control Enforcement Direction', t: 'radio', o: [['ingress', 'Ingress'], ['egress', 'Egress']] },
      { k: 'ipDataPlaneLearning', l: 'IP Data-plane Learning', t: 'select', o: [['enabled', 'Enabled'], ['disabled', 'Disabled']] },
      DESCR],
    cols: [ac('name'), col('Enforcement', r => r.pcEnfPref), col('VNID (Scope)', r => r.scope), col('pcTag', r => r.pcTag)],
    info: r => [['VNID (Segment)', r.scope], ['pcTag', r.pcTag]],
  },
  vzAny: { fields: [{ k: 'prefGrMemb', l: 'Preferred Group Member', t: 'ed', cl: 'Preferred Group in diesem VRF aktivieren' }], cols: [] },
  vzRsAnyToProv: { fields: [relNameSelf('tnVzBrCPName', 'Contract', 'vzBrCP')], cols: [col('Provided Contract', r => r.tnVzBrCPName), col('State', relState)] },
  vzRsAnyToCons: { fields: [relNameSelf('tnVzBrCPName', 'Contract', 'vzBrCP')], cols: [col('Consumed Contract', r => r.tnVzBrCPName), col('State', relState)] },
  fvBD: {
    fields: [NAME,
      relName('fvRsCtx', 'tnFvCtxName', 'VRF', 'fvCtx', { req: true }),
      { k: 'unkMacUcastAct', l: 'L2 Unknown Unicast', t: 'radio', o: [['proxy', 'Hardware Proxy'], ['flood', 'Flood']] },
      { k: 'arpFlood', l: 'ARP Flooding', t: 'yesno' },
      { k: 'unicastRoute', l: 'Unicast Routing', t: 'yesno' },
      { k: 'limitIpLearnToSubnets', l: 'Limit IP Learning To Subnet', t: 'yesno' },
      { k: 'ipLearning', l: 'Endpoint Data-plane Learning', t: 'yesno' },
      { k: 'multiDstPktAct', l: 'Multi Destination Flooding', t: 'select', o: [['bd-flood', 'Flood in BD'], ['encap-flood', 'Flood in Encapsulation'], ['drop', 'Drop']] },
      DESCR],
    createExtra: [
      { k: '_subnet', l: 'Subnetz (Gateway-IP)', virtual: true, ph: '10.1.1.1/24', help: 'optional, weitere Subnetze später im BD' },
      { k: '_scope', l: 'Subnet Scope', virtual: true, t: 'checks', o: [['private', 'Private to VRF'], ['public', 'Advertised Externally'], ['shared', 'Shared between VRFs']], def: 'private' },
    ],
    build: v => {
      const b = bodyFromForm('fvBD', SPEC.fvBD.fields, v, 'create');
      if (v._subnet) (b.fvBD.children = b.fvBD.children || []).push({ fvSubnet: { attributes: { ip: v._subnet, scope: v._scope || 'private' } } });
      return b;
    },
    cols: [ac('name'), col('VRF', r => relOf(r.dn, 'fvRsCtx', 'tnFvCtxName') || '(default)'), col('Unicast Routing', r => r.unicastRoute),
      col('L2 Unk. Unicast', r => r.unkMacUcastAct), col('ARP Flood', r => r.arpFlood), col('Segment', r => r.seg)],
    info: r => [['Segment (VNID)', r.seg], ['pcTag', r.pcTag], ['VRF (aufgelöst)', relOf(r.dn, 'fvRsCtx', 'tDn')], ['Custom MAC', r.mac]],
  },
  fvSubnet: {
    fields: [{ k: 'ip', l: 'Gateway IP', create: true, req: true, ph: '10.1.1.1/24', help: 'Adresse des Gateways mit Maske' },
      { k: 'scope', l: 'Scope', t: 'checks', o: [['private', 'Private to VRF'], ['public', 'Advertised Externally'], ['shared', 'Shared between VRFs']] },
      { k: 'preferred', l: 'Make this IP address primary', t: 'yesno' },
      { k: 'virtual', l: 'Treat as virtual IP address', t: 'yesno' }, DESCR],
    cols: [col('Gateway Address', r => r.ip), col('Scope', r => r.scope), col('Primary', r => r.preferred)],
  },
  fvRsBDToOut: { fields: [relNameSelf('tnL3extOutName', 'L3 Out', 'l3extOut')], cols: [col('L3 Out', r => r.tnL3extOutName), col('State', relState)] },
  fvAp: { fields: [NAME, DESCR], cols: [ac('name'), ac('descr')] },
  fvAEPg: {
    fields: [NAME,
      relName('fvRsBd', 'tnFvBDName', 'Bridge Domain', 'fvBD', { req: true }),
      { k: 'pcEnfPref', l: 'Intra EPG Isolation', t: 'radio', o: [['unenforced', 'Unenforced'], ['enforced', 'Enforced']] },
      { k: 'prefGrMemb', l: 'Preferred Group Member', t: 'radio', o: [['exclude', 'Exclude'], ['include', 'Include']] },
      { k: 'shutdown', l: 'Shutdown EPG', t: 'yesno' },
      DESCR],
    createExtra: [{ k: '_dom', l: 'Physical Domain', virtual: true, t: 'tdn', target: ['physDomP'], empty: '— keine (später unter Domains) —' }],
    build: v => {
      const b = bodyFromForm('fvAEPg', SPEC.fvAEPg.fields, v, 'create');
      if (v._dom) (b.fvAEPg.children = b.fvAEPg.children || []).push({ fvRsDomAtt: { attributes: { tDn: v._dom } } });
      return b;
    },
    cols: [ac('name'), col('Bridge Domain', r => relOf(r.dn, 'fvRsBd', 'tnFvBDName') || '(default)'), col('pcTag', r => r.pcTag), col('Pref. Group', r => r.prefGrMemb)],
    info: r => [['pcTag (sclass)', r.pcTag], ['VRF-Scope', r.scope], ['BD (aufgelöst)', relOf(r.dn, 'fvRsBd', 'tDn')]],
    oper: 'fvCEp',
  },
  fvRsDomAtt: {
    fields: [{ k: 'tDn', l: 'Domain', t: 'tdn', target: ['physDomP', 'l3extDomP'], create: true, req: true },
      { k: 'resImedcy', l: 'Resolution Immediacy', t: 'select', o: RES_IMM },
      { k: 'instrImedcy', l: 'Deployment Immediacy', t: 'select', o: IMM }],
    cols: [col('Domain', r => r.tDn), col('Resolution', r => r.resImedcy), col('Deployment', r => r.instrImedcy), col('State', relState)],
  },
  fvRsPathAtt: {
    fields: [{ k: 'tDn', l: 'Path', t: 'path', create: true, req: true },
      { k: 'encap', l: 'Port Encap (VLAN)', req: true, ph: 'vlan-10' },
      { k: 'mode', l: 'Mode', t: 'radio', o: [['regular', 'Trunk'], ['native', 'Access (802.1P)'], ['untagged', 'Access (Untagged)']] },
      { k: 'instrImedcy', l: 'Deployment Immediacy', t: 'select', o: IMM }],
    cols: [col('Path', r => pathLabel(r.tDn)), col('Encap', r => r.encap), col('Mode', r => ({ regular: 'Trunk', native: 'Access (802.1P)', untagged: 'Access (Untagged)' }[r.mode])),
      col('Immediacy', r => r.instrImedcy), col('State', relState)],
    normalize: v => { if (/^\d+$/.test(v.encap || '')) v.encap = 'vlan-' + v.encap; return v; },
  },
  fvRsProv: { label: 'Provided Contract', fields: [relNameSelf('tnVzBrCPName', 'Contract', 'vzBrCP')], cols: [col('Contract', r => r.tnVzBrCPName), col('Typ', () => 'Provided'), col('State', relState)] },
  fvRsCons: { label: 'Consumed Contract', fields: [relNameSelf('tnVzBrCPName', 'Contract', 'vzBrCP')], cols: [col('Contract', r => r.tnVzBrCPName), col('Typ', () => 'Consumed'), col('State', relState)] },
  fvCEp: { fields: [], cols: [col('MAC', r => r.mac), col('IP', r => r.ip), col('Encap', r => r.encap), col('Path', r => pathLabel(r.fabricPathDn)), col('Learning', r => r.lcC)] },

  vzBrCP: {
    fields: [NAME, { k: 'scope', l: 'Scope', t: 'select', o: [['context', 'VRF'], ['application-profile', 'Application Profile'], ['tenant', 'Tenant'], ['global', 'Global']] }, DESCR],
    createExtra: [
      { k: '_subj', l: 'Subject', virtual: true, def: 'subj', help: 'Der Contract bekommt ein Subject mit diesem Namen' },
      { k: '_rev', l: 'Reverse Filter Ports', virtual: true, t: 'yesno', def: 'yes', cl: 'Apply Both Directions + Reverse Filter Ports' },
      { k: '_filters', l: 'Filter', virtual: true, t: 'tdnmulti', target: ['vzFilter'], tenantScope: true, none: 'Noch keine Filter – zuerst unter Contracts > Filters anlegen' },
    ],
    build: v => {
      const b = bodyFromForm('vzBrCP', SPEC.vzBrCP.fields, v, 'create');
      if (v._subj) {
        const kids = (v._filters || []).map(dn => ({ vzRsSubjFiltAtt: { attributes: { tnVzFilterName: MIT.a(dn) ? MIT.a(dn).name : nameOfDn(dn) } } }));
        b.vzBrCP.children = [{ vzSubj: { attributes: { name: v._subj, revFltPorts: v._rev }, children: kids } }];
      }
      return b;
    },
    cols: [ac('name'), col('Scope', r => r.scope), ac('descr')],
  },
  vzSubj: {
    fields: [NAME, { k: 'revFltPorts', l: 'Reverse Filter Ports', t: 'yesno', cl: 'Ports der Gegenrichtung tauschen' }, DESCR],
    cols: [ac('name'), col('Reverse Filter Ports', r => r.revFltPorts)],
  },
  vzRsSubjFiltAtt: {
    fields: [relNameSelf('tnVzFilterName', 'Filter', 'vzFilter'), { k: 'action', l: 'Action', t: 'radio', o: [['permit', 'Permit'], ['deny', 'Deny']] }],
    cols: [col('Filter', r => r.tnVzFilterName), col('Action', r => r.action), col('State', relState)],
  },
  vzFilter: {
    fields: [NAME, DESCR],
    createExtra: [
      { k: '_e', l: 'Entry Name', virtual: true, ph: 'z. B. http', help: 'leer lassen = Filter ohne Entry anlegen' },
      { k: '_et', l: 'EtherType', virtual: true, t: 'select', o: [['ip', 'IP'], ['unspecified', 'Unspecified'], ['arp', 'ARP']], def: 'ip' },
      { k: '_p', l: 'IP Protocol', virtual: true, t: 'select', o: [['tcp', 'tcp'], ['udp', 'udp'], ['icmp', 'icmp'], ['unspecified', 'unspecified']], def: 'tcp' },
      { k: '_df', l: 'Destination Port From', virtual: true, list: PORTS, def: 'unspecified' },
      { k: '_dt', l: 'Destination Port To', virtual: true, list: PORTS, def: 'unspecified' },
    ],
    build: v => {
      const b = bodyFromForm('vzFilter', SPEC.vzFilter.fields, v, 'create');
      if (v._e) {
        const e = { name: v._e, etherT: v._et, prot: v._et === 'ip' ? v._p : 'unspecified' };
        if (['tcp', 'udp'].includes(e.prot)) { e.dFromPort = v._df || 'unspecified'; e.dToPort = v._dt || v._df || 'unspecified'; }
        b.vzFilter.children = [{ vzEntry: { attributes: e } }];
      }
      return b;
    },
    cols: [ac('name'), col('Entries', r => MIT.kids(r.dn, ['vzEntry']).map(d => MIT.a(d).name).join(', ')), ac('descr')],
  },
  vzEntry: {
    fields: [NAME,
      { k: 'etherT', l: 'EtherType', t: 'select', o: [['unspecified', 'Unspecified'], ['ip', 'IP'], ['arp', 'ARP'], ['ipv4', 'IPv4'], ['ipv6', 'IPv6']] },
      { k: 'prot', l: 'IP Protocol', t: 'select', o: [['unspecified', 'unspecified'], ['tcp', 'tcp'], ['udp', 'udp'], ['icmp', 'icmp'], ['ospfigp', 'ospf'], ['eigrp', 'eigrp'], ['pim', 'pim']], show: v => ['ip', 'ipv4', 'ipv6'].includes(v.etherT) },
      { k: 'sFromPort', l: 'Source Port From', list: PORTS, show: v => ['tcp', 'udp'].includes(v.prot) },
      { k: 'sToPort', l: 'Source Port To', list: PORTS, show: v => ['tcp', 'udp'].includes(v.prot) },
      { k: 'dFromPort', l: 'Destination Port From', list: PORTS, show: v => ['tcp', 'udp'].includes(v.prot) },
      { k: 'dToPort', l: 'Destination Port To', list: PORTS, show: v => ['tcp', 'udp'].includes(v.prot) },
      { k: 'tcpRules', l: 'TCP Session Rules', t: 'select', o: [['', 'Unspecified'], ['est', 'Established']], show: v => v.prot === 'tcp' },
      { k: 'stateful', l: 'Stateful', t: 'yesno', show: v => v.prot === 'tcp' }],
    normalize: v => { if (v.dFromPort && v.dFromPort !== 'unspecified' && (!v.dToPort || v.dToPort === 'unspecified')) v.dToPort = v.dFromPort; if (v.sFromPort && v.sFromPort !== 'unspecified' && (!v.sToPort || v.sToPort === 'unspecified')) v.sToPort = v.sFromPort; return v; },
    cols: [ac('name'), col('EtherType', r => r.etherT), col('Protocol', r => r.prot), col('Src Port', r => r.sFromPort === r.sToPort ? r.sFromPort : r.sFromPort + '-' + r.sToPort),
      col('Dst Port', r => r.dFromPort === r.dToPort ? r.dFromPort : r.dFromPort + '-' + r.dToPort), col('TCP Rules', r => r.tcpRules)],
  },

  /* ---------------- L3Out ---------------- */
  l3extOut: {
    fields: [NAME, relName('l3extRsEctx', 'tnFvCtxName', 'VRF', 'fvCtx', { req: true }),
      relDn('l3extRsL3DomAtt', 'L3 Domain', 'l3extDomP', { req: true }), DESCR],
    createExtra: [
      { k: '_proto', l: 'Routing-Protokoll', virtual: true, t: 'radio', o: [['', 'keins / Static'], ['ospf', 'OSPF'], ['bgp', 'BGP']], def: '' },
      { k: '_area', l: 'OSPF Area ID', virtual: true, ph: '0.0.0.1 oder backbone', def: 'backbone', show: v => v._proto === 'ospf' },
      { k: '_atype', l: 'OSPF Area Type', virtual: true, t: 'select', o: [['regular', 'Regular area'], ['nssa', 'NSSA area'], ['stub', 'Stub area']], show: v => v._proto === 'ospf' },
    ],
    build: v => {
      const b = bodyFromForm('l3extOut', SPEC.l3extOut.fields, v, 'create');
      const k = b.l3extOut.children = b.l3extOut.children || [];
      if (v._proto === 'ospf') k.push({ ospfExtP: { attributes: { areaId: v._area || 'backbone', areaType: v._atype } } });
      if (v._proto === 'bgp') k.push({ bgpExtP: { attributes: {} } });
      return b;
    },
    cols: [ac('name'), col('VRF', r => relOf(r.dn, 'l3extRsEctx', 'tnFvCtxName')), col('L3 Domain', r => nameOfDn(relOf(r.dn, 'l3extRsL3DomAtt', 'tDn'))),
      col('Protokolle', r => [MIT.get(r.dn + '/ospfExtP') ? 'OSPF' : '', MIT.get(r.dn + '/bgpExtP') ? 'BGP' : ''].filter(Boolean).join(', '))],
  },
  ospfExtP: {
    label: 'OSPF',
    fields: [{ k: 'areaId', l: 'Area ID', ph: 'backbone, 0.0.0.1 oder 1' },
      { k: 'areaType', l: 'Area Type', t: 'select', o: [['regular', 'Regular area'], ['nssa', 'NSSA area'], ['stub', 'Stub area']] },
      { k: 'areaCost', l: 'Area Cost' }, { k: 'areaCtrl', l: 'Area Control', t: 'checks', o: [['redistribute', 'Send redistributed LSAs into NSSA area'], ['summary', 'Originate summary LSA']] }],
    cols: [col('Protokoll', () => 'OSPF'), col('Area', r => r.areaId), col('Area Type', r => r.areaType)],
  },
  bgpExtP: { label: 'BGP', fields: [], cols: [col('Protokoll', () => 'BGP')] },
  l3extLNodeP: { fields: [NAME, DESCR], cols: [ac('name'), col('Nodes', r => MIT.kids(r.dn, ['l3extRsNodeL3OutAtt']).map(d => pathLabel(MIT.a(d).tDn)).join(', '))] },
  l3extRsNodeL3OutAtt: {
    label: 'Node',
    fields: [{ k: 'tDn', l: 'Node', t: 'node', create: true, req: true }, { k: 'rtrId', l: 'Router ID', ph: '1.1.1.103', req: true },
      { k: 'rtrIdLoopBack', l: 'Use Router ID as Loopback Address', t: 'yesno' }],
    cols: [col('Node', r => pathLabel(r.tDn)), col('Router ID', r => r.rtrId), col('Static Routes', r => MIT.kids(r.dn, ['ipRouteP']).map(d => MIT.a(d).ip).join(', '))],
  },
  ipRouteP: {
    label: 'Static Route',
    fields: [{ k: 'ip', l: 'Prefix', create: true, req: true, ph: '0.0.0.0/0' }, { k: 'pref', l: 'Preference' }],
    createExtra: [{ k: '_nh', l: 'Next Hop Address', virtual: true, ph: '172.16.1.2' }],
    build: v => {
      const b = bodyFromForm('ipRouteP', SPEC.ipRouteP.fields, v, 'create');
      if (v._nh) b.ipRouteP.children = [{ ipNexthopP: { attributes: { nhAddr: v._nh } } }];
      return b;
    },
    cols: [col('Prefix', r => r.ip), col('Next Hops', r => MIT.kids(r.dn, ['ipNexthopP']).map(d => MIT.a(d).nhAddr).join(', ')), col('Pref', r => r.pref)],
  },
  ipNexthopP: { label: 'Next Hop', fields: [{ k: 'nhAddr', l: 'Next Hop Address', create: true, req: true, ph: '172.16.1.2' }], cols: [col('Next Hop', r => r.nhAddr)] },
  l3extLIfP: { fields: [NAME, DESCR], cols: [ac('name'), col('Interfaces', r => MIT.kids(r.dn, ['l3extRsPathL3OutAtt']).length)] },
  l3extRsPathL3OutAtt: {
    label: 'Interface',
    fields: [{ k: 'ifInstT', l: 'Interface Type', t: 'radio', o: [['l3-port', 'Routed Interface'], ['sub-interface', 'Routed Sub-Interface'], ['ext-svi', 'SVI']] },
      { k: 'tDn', l: 'Path', t: 'path', create: true, req: true },
      { k: 'addr', l: 'IPv4 Address', req: true, ph: '172.16.1.1/30' },
      { k: 'encap', l: 'Encap (VLAN)', ph: 'vlan-100', show: v => v.ifInstT !== 'l3-port' },
      { k: 'mtu', l: 'MTU (bytes)', ph: 'inherit' }],
    normalize: v => { if (/^\d+$/.test(v.encap || '')) v.encap = 'vlan-' + v.encap; if (v.ifInstT === 'l3-port') delete v.encap; return v; },
    cols: [col('Path', r => pathLabel(r.tDn)), col('Typ', r => r.ifInstT), col('IP', r => r.addr), col('Encap', r => r.encap), col('MTU', r => r.mtu), col('State', relState)],
  },
  ospfIfP: {
    label: 'OSPF Interface Profile',
    fields: [relName('ospfRsIfPol', 'tnOspfIfPolName', 'OSPF Policy', 'ospfIfPol', { empty: 'default (common)', keepEmpty: true }),
      { k: 'authType', l: 'Authentication Type', t: 'select', o: [['none', 'No authentication'], ['simple', 'Simple'], ['md5', 'MD5']] }],
    cols: [col('OSPF Policy', r => relOf(r.dn, 'ospfRsIfPol', 'tnOspfIfPolName') || 'default'), col('Auth', r => r.authType)],
  },
  ospfIfPol: {
    fields: [NAME, { k: 'nwT', l: 'Network Type', t: 'radio', o: [['unspecified', 'Unspecified'], ['bcast', 'Broadcast'], ['p2p', 'Point-to-point']] },
      { k: 'ctrl', l: 'Interface Controls', t: 'checks', o: [['advert-subnet', 'Advertise subnet'], ['bfd', 'BFD'], ['mtu-ignore', 'MTU ignore'], ['passive', 'Passive participation']] },
      { k: 'helloIntvl', l: 'Hello Interval (sec)' }, { k: 'deadIntvl', l: 'Dead Interval (sec)' }, { k: 'cost', l: 'Cost of Interface' }, { k: 'prio', l: 'Priority' }],
    cols: [ac('name'), col('Network Type', r => r.nwT), col('Controls', r => r.ctrl), col('Hello/Dead', r => r.helloIntvl + '/' + r.deadIntvl)],
  },
  bgpPeerP: {
    label: 'BGP Peer',
    fields: [{ k: 'addr', l: 'Peer Address', create: true, req: true, ph: '172.16.1.2' },
      { rel: 'bgpAsP', k: 'asn', l: 'Remote Autonomous System Number', req: true, ph: '65100' },
      { rel: 'bgpLocalAsnP', k: 'localAsn', l: 'Local-AS Number', ph: 'optional' },
      { k: 'ttl', l: 'eBGP Multihop TTL' }],
    cols: [col('Peer', r => r.addr), col('Remote AS', r => relOf(r.dn, 'bgpAsP', 'asn')), col('TTL', r => r.ttl)],
  },
  bgpAsP: { label: 'Remote AS', fields: [{ k: 'asn', l: 'ASN' }], cols: [col('ASN', r => r.asn)] },
  l3extInstP: {
    fields: [NAME, { k: 'prefGrMemb', l: 'Preferred Group Member', t: 'radio', o: [['exclude', 'Exclude'], ['include', 'Include']] }, DESCR],
    createExtra: [{ k: '_sub', l: 'Subnet', virtual: true, ph: '0.0.0.0/0', help: 'wird als "External Subnets for External EPG" angelegt' }],
    build: v => {
      const b = bodyFromForm('l3extInstP', SPEC.l3extInstP.fields, v, 'create');
      if (v._sub) b.l3extInstP.children = [{ l3extSubnet: { attributes: { ip: v._sub, scope: 'import-security' } } }];
      return b;
    },
    cols: [ac('name'), col('Subnets', r => MIT.kids(r.dn, ['l3extSubnet']).map(d => MIT.a(d).ip).join(', ')), col('pcTag', r => r.pcTag)],
    info: r => [['pcTag', r.pcTag]],
  },
  l3extSubnet: {
    fields: [{ k: 'ip', l: 'IP Address', create: true, req: true, ph: '0.0.0.0/0' },
      { k: 'scope', l: 'Scope', t: 'checks', o: [['export-rtctrl', 'Export Route Control Subnet'], ['import-rtctrl', 'Import Route Control Subnet'], ['import-security', 'External Subnets for External EPG'], ['shared-rtctrl', 'Shared Route Control Subnet'], ['shared-security', 'Shared Security Import Subnet']] }],
    cols: [col('IP', r => r.ip), col('Scope', r => r.scope)],
  },

  /* ---------------- Access Policies ---------------- */
  fvnsVlanInstP: {
    fields: [NAME, { k: 'allocMode', l: 'Allocation Mode', t: 'radio', o: [['static', 'Static Allocation'], ['dynamic', 'Dynamic Allocation']], create: true, def: 'static' }, DESCR],
    createExtra: [{ k: '_from', l: 'Encap Block von VLAN', virtual: true, ph: '100' }, { k: '_to', l: 'bis VLAN', virtual: true, ph: '199' }],
    build: v => {
      const b = bodyFromForm('fvnsVlanInstP', SPEC.fvnsVlanInstP.fields, v, 'create');
      if (v._from) b.fvnsVlanInstP.children = [{ fvnsEncapBlk: { attributes: { from: 'vlan-' + v._from.replace(/^vlan-/, ''), to: 'vlan-' + (v._to || v._from).replace(/^vlan-/, '') } } }];
      return b;
    },
    cols: [ac('name'), col('Allocation', r => r.allocMode), col('Encap Blocks', r => MIT.kids(r.dn, ['fvnsEncapBlk']).map(d => MIT.a(d).from.replace('vlan-', '') + '-' + MIT.a(d).to.replace('vlan-', '')).join(', ')), ac('descr')],
  },
  fvnsEncapBlk: {
    label: 'Encap Block',
    fields: [{ k: 'from', l: 'From', create: true, req: true, ph: 'vlan-100' }, { k: 'to', l: 'To', create: true, req: true, ph: 'vlan-199' },
      { k: 'allocMode', l: 'Allocation Mode', t: 'select', o: [['inherit', 'Inherit allocMode from parent'], ['static', 'Static Allocation'], ['dynamic', 'Dynamic Allocation']] },
      { k: 'role', l: 'Role', t: 'select', o: [['external', 'External or On the wire encapsulations'], ['internal', 'Internal']] }],
    normalize: v => { ['from', 'to'].forEach(k => { if (/^\d+$/.test(v[k] || '')) v[k] = 'vlan-' + v[k]; }); return v; },
    cols: [col('From', r => r.from), col('To', r => r.to), col('Allocation Mode', r => r.allocMode), col('Role', r => r.role)],
  },
  physDomP: {
    fields: [NAME, relDn('infraRsVlanNs', 'VLAN Pool', 'fvnsVlanInstP')],
    cols: [ac('name'), col('VLAN Pool', r => nameOfDn(relOf(r.dn, 'infraRsVlanNs', 'tDn')))],
  },
  l3extDomP: {
    fields: [NAME, relDn('infraRsVlanNs', 'VLAN Pool', 'fvnsVlanInstP')],
    cols: [ac('name'), col('VLAN Pool', r => nameOfDn(relOf(r.dn, 'infraRsVlanNs', 'tDn')))],
  },
  infraAttEntityP: {
    fields: [NAME, DESCR],
    createExtra: [{ k: '_doms', l: 'Domains', virtual: true, t: 'tdnmulti', target: ['physDomP', 'l3extDomP'], none: 'Noch keine Domains angelegt' }],
    build: v => {
      const b = bodyFromForm('infraAttEntityP', SPEC.infraAttEntityP.fields, v, 'create');
      if ((v._doms || []).length) b.infraAttEntityP.children = v._doms.map(d => ({ infraRsDomP: { attributes: { tDn: d } } }));
      return b;
    },
    cols: [ac('name'), col('Domains', r => MIT.kids(r.dn, ['infraRsDomP']).map(d => nameOfDn(MIT.a(d).tDn)).join(', ')), ac('descr')],
  },
  infraRsDomP: { label: 'Domain', fields: [{ k: 'tDn', l: 'Domain', t: 'tdn', target: ['physDomP', 'l3extDomP'], create: true, req: true }], cols: [col('Domain', r => r.tDn), col('State', relState)] },
  infraAccPortGrp: {
    fields: [NAME, relDn('infraRsAttEntP', 'Attached Entity Profile', 'infraAttEntityP'),
      relName('infraRsLldpIfPol', 'tnLldpIfPolName', 'LLDP Policy', 'lldpIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsCdpIfPol', 'tnCdpIfPolName', 'CDP Policy', 'cdpIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsHIfPol', 'tnFabricHIfPolName', 'Link Level Policy', 'fabricHIfPol', { scope: 'infra', empty: 'default' }), DESCR],
    cols: [ac('name'), col('AAEP', r => nameOfDn(relOf(r.dn, 'infraRsAttEntP', 'tDn'))), col('LLDP', r => relOf(r.dn, 'infraRsLldpIfPol', 'tnLldpIfPolName') || 'default'), col('CDP', r => relOf(r.dn, 'infraRsCdpIfPol', 'tnCdpIfPolName') || 'default')],
  },
  infraAccBndlGrp: {
    fields: [NAME, { k: 'lagT', l: 'Link Aggregation Type', t: 'radio', o: [['link', 'Port Channel'], ['node', 'Virtual Port Channel']], create: true },
      relDn('infraRsAttEntP', 'Attached Entity Profile', 'infraAttEntityP'),
      relName('infraRsLacpPol', 'tnLacpLagPolName', 'Port Channel Policy', 'lacpLagPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsLldpIfPol', 'tnLldpIfPolName', 'LLDP Policy', 'lldpIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsCdpIfPol', 'tnCdpIfPolName', 'CDP Policy', 'cdpIfPol', { scope: 'infra', empty: 'default' }), DESCR],
    cols: [ac('name'), col('Typ', r => r.lagT === 'node' ? 'vPC' : 'PC'), col('AAEP', r => nameOfDn(relOf(r.dn, 'infraRsAttEntP', 'tDn'))), col('Port Channel Policy', r => relOf(r.dn, 'infraRsLacpPol', 'tnLacpLagPolName') || 'default')],
  },
  infraAccPortP: {
    fields: [NAME, DESCR],
    createExtra: [
      { k: '_sel', l: 'Interface Selector', virtual: true, ph: 'z. B. Server-1-10', help: 'leer = Profil ohne Selector' },
      { k: '_ports', l: 'Interface IDs', virtual: true, ph: '1/1-10 oder 1,3,5-7' },
      { k: '_pg', l: 'Interface Policy Group', virtual: true, t: 'tdn', target: ['infraAccPortGrp', 'infraAccBndlGrp'], empty: '— keine —' },
    ],
    build: v => {
      const b = bodyFromForm('infraAccPortP', SPEC.infraAccPortP.fields, v, 'create');
      if (v._sel) b.infraAccPortP.children = [hportsBody(v._sel, v._ports, v._pg)];
      return b;
    },
    cols: [ac('name'), col('Selectors', r => MIT.kids(r.dn, ['infraHPortS']).map(d => MIT.a(d).name).join(', ')), ac('descr')],
  },
  infraHPortS: {
    label: 'Access Port Selector',
    fields: [NAME, relDn('infraRsAccBaseGrp', 'Interface Policy Group', ['infraAccPortGrp', 'infraAccBndlGrp'])],
    createFields: [NAME, { k: '_ports', l: 'Interface IDs', virtual: true, req: true, ph: '1/1-10 oder 1,3,5-7' },
      { k: '_pg', l: 'Interface Policy Group', virtual: true, t: 'tdn', target: ['infraAccPortGrp', 'infraAccBndlGrp'], empty: '— keine —' }],
    build: v => hportsBody(v.name, v._ports, v._pg),
    cols: [ac('name'), col('Ports', r => MIT.kids(r.dn, ['infraPortBlk']).map(d => { const a = MIT.a(d); return '1/' + a.fromPort + (a.toPort !== a.fromPort ? '-' + a.toPort : ''); }).join(', ')),
      col('Policy Group', r => nameOfDn(relOf(r.dn, 'infraRsAccBaseGrp', 'tDn')))],
  },
  infraPortBlk: {
    label: 'Port Block',
    fields: [NAME, { k: 'fromCard', l: 'From Card' }, { k: 'fromPort', l: 'From Port' }, { k: 'toCard', l: 'To Card' }, { k: 'toPort', l: 'To Port' }],
    cols: [ac('name'), col('From', r => r.fromCard + '/' + r.fromPort), col('To', r => r.toCard + '/' + r.toPort)],
  },
  infraNodeP: {
    fields: [NAME, DESCR],
    createExtra: [
      { k: '_sel', l: 'Leaf Selector', virtual: true, ph: 'z. B. Leaf101', help: 'leer = Profil ohne Selector' },
      { k: '_from', l: 'Von Node-ID', virtual: true, ph: '101' }, { k: '_to', l: 'Bis Node-ID', virtual: true, ph: '101' },
      { k: '_ifp', l: 'Interface Selector Profiles', virtual: true, t: 'tdnmulti', target: ['infraAccPortP'], none: 'Noch keine Leaf Interface Profiles' },
    ],
    build: v => {
      const b = bodyFromForm('infraNodeP', SPEC.infraNodeP.fields, v, 'create');
      const k = [];
      if (v._sel) k.push(leafSelBody(v._sel, v._from, v._to));
      (v._ifp || []).forEach(d => k.push({ infraRsAccPortP: { attributes: { tDn: d } } }));
      if (k.length) b.infraNodeP.children = k;
      return b;
    },
    cols: [ac('name'), col('Leaf Selectors', r => MIT.kids(r.dn, ['infraLeafS']).map(d => MIT.a(d).name + ' (' + MIT.kids(d, ['infraNodeBlk']).map(n => MIT.a(n).from_ + '-' + MIT.a(n).to_).join(',') + ')').join(', ')),
      col('Interface Profiles', r => MIT.kids(r.dn, ['infraRsAccPortP']).map(d => nameOfDn(MIT.a(d).tDn)).join(', '))],
  },
  infraLeafS: {
    label: 'Leaf Selector',
    fields: [NAME],
    createFields: [NAME, { k: '_from', l: 'Von Node-ID', virtual: true, req: true, ph: '101' }, { k: '_to', l: 'Bis Node-ID', virtual: true, ph: '101' }],
    build: v => leafSelBody(v.name, v._from, v._to),
    cols: [ac('name'), col('Blocks', r => MIT.kids(r.dn, ['infraNodeBlk']).map(n => MIT.a(n).from_ + '-' + MIT.a(n).to_).join(', '))],
  },
  infraNodeBlk: { label: 'Node Block', fields: [NAME, { k: 'from_', l: 'From' }, { k: 'to_', l: 'To' }], cols: [ac('name'), col('From', r => r.from_), col('To', r => r.to_)] },
  infraRsAccPortP: { label: 'Interface Selector Profile', fields: [{ k: 'tDn', l: 'Interface Profile', t: 'tdn', target: ['infraAccPortP'], create: true, req: true }], cols: [col('Interface Profile', r => nameOfDn(r.tDn)), col('State', relState)] },
  cdpIfPol: { fields: [NAME, { k: 'adminSt', l: 'Admin State', t: 'radio', o: [['enabled', 'Enabled'], ['disabled', 'Disabled']] }, DESCR], cols: [ac('name'), col('Admin State', r => r.adminSt)] },
  lldpIfPol: { fields: [NAME, { k: 'adminRxSt', l: 'Receive State', t: 'radio', o: [['enabled', 'Enabled'], ['disabled', 'Disabled']] }, { k: 'adminTxSt', l: 'Transmit State', t: 'radio', o: [['enabled', 'Enabled'], ['disabled', 'Disabled']] }, DESCR], cols: [ac('name'), col('RX', r => r.adminRxSt), col('TX', r => r.adminTxSt)] },
  lacpLagPol: {
    fields: [NAME, { k: 'mode', l: 'Mode', t: 'select', o: [['off', 'Static Channel - Mode On'], ['active', 'LACP Active'], ['passive', 'LACP Passive'], ['mac-pin', 'MAC Pinning'], ['mac-pin-nicload', 'MAC Pinning-Physical-NIC-load'], ['explicit-failover', 'Use Explicit Failover Order']] },
      { k: 'minLinks', l: 'Minimum Number of Links' }, { k: 'maxLinks', l: 'Maximum Number of Links' }, DESCR],
    cols: [ac('name'), col('Mode', r => r.mode)],
  },
  fabricHIfPol: { fields: [NAME, { k: 'speed', l: 'Speed', t: 'select', o: ['inherit', '1G', '10G', '25G', '40G', '100G'].map(x => [x, x]) }, { k: 'autoNeg', l: 'Auto Negotiation', t: 'select', o: [['on', 'on'], ['off', 'off']] }, DESCR], cols: [ac('name'), col('Speed', r => r.speed), col('AutoNeg', r => r.autoNeg)] },
  fabricProtPol: { label: 'Virtual Port Channel default', fields: [{ k: 'pairT', l: 'Pairing Type', ro: true }], cols: [] },
  fabricExplicitGEp: {
    label: 'Explicit vPC Protection Group',
    fields: [NAME, { k: 'id', l: 'ID (vPC Domain)', create: true, req: true, ph: '10' }],
    createExtra: [{ k: '_a', l: 'Switch 1', virtual: true, t: 'node', ids: true, req: true }, { k: '_b', l: 'Switch 2', virtual: true, t: 'node', ids: true, req: true }],
    build: v => {
      const b = bodyFromForm('fabricExplicitGEp', SPEC.fabricExplicitGEp.fields, v, 'create');
      b.fabricExplicitGEp.children = [v._a, v._b].filter(Boolean).map(id => ({ fabricNodePEp: { attributes: { id } } }));
      return b;
    },
    cols: [ac('name'), col('Domain ID', r => r.id), col('Switches', r => MIT.kids(r.dn, ['fabricNodePEp']).map(d => MIT.a(d).id).join(', '))],
  },
  fabricNodePEp: { label: 'vPC Node', fields: [{ k: 'id', l: 'Node ID', create: true, req: true }], cols: [col('Node ID', r => r.id)] },
  fabricNodeIdentP: {
    label: 'Fabric Node Member',
    fields: [{ k: 'serial', l: 'Serial Number', create: true, req: true }, { k: 'podId', l: 'Pod ID' }, { k: 'nodeId', l: 'Node ID', create: true, req: true, ph: '101' },
      { k: 'name', l: 'Node Name', req: true, ph: 'leaf101' }],
    cols: [col('Serial', r => r.serial), col('Node ID', r => r.nodeId), col('Name', r => r.name), col('Pod', r => r.podId)],
  },
  bgpRRNodePEp: { label: 'Route Reflector Node', fields: [{ k: 'id', l: 'Spine Node ID', t: 'node', role: 'spine', ids: true, create: true, req: true }], cols: [col('Node ID', r => r.id), col('Pod', r => r.podId)] },
  aaaUser: {
    label: 'Local User',
    fields: [{ k: 'name', l: 'Login ID', create: true, req: true }, { k: 'pwd', l: 'Password', t: 'password', help: 'leer lassen = unverändert' },
      { k: 'firstName', l: 'First Name' }, { k: 'lastName', l: 'Last Name' }, { k: 'email', l: 'Email' },
      { k: 'accountStatus', l: 'Account Status', t: 'radio', o: [['active', 'Active'], ['inactive', 'Inactive']] }],
    cols: [col('Login ID', r => r.name), col('Name', r => (r.firstName + ' ' + r.lastName).trim()), col('Status', r => r.accountStatus)],
  },
};

function relNameSelf(k, l, target) { return { k, l, t: 'tname', target, create: true, req: true }; }

function hportsBody(name, ports, pg) {
  const kids = parsePorts(ports).map(([a, b], i) => ({ infraPortBlk: { attributes: { name: 'block' + (i + 2), fromCard: '1', toCard: '1', fromPort: String(a), toPort: String(b) } } }));
  if (pg) kids.push({ infraRsAccBaseGrp: { attributes: { tDn: pg } } });
  return { infraHPortS: { attributes: { name, type: 'range' }, children: kids } };
}

function leafSelBody(name, from, to) {
  if (!/^\d+$/.test(from || '')) throw new ApiError('Eingabe', 'Node-ID (z. B. 101) angeben');
  return { infraLeafS: { attributes: { name, type: 'range' }, children: [{ infraNodeBlk: { attributes: { name: 'blk' + from + '-' + (to || from), from_: String(from), to_: String(to || from) } } }] } };
}

/* Navigationsbaum: je Klasse die Unterordner (cls) */
const TREE = {
  fvTenant: [
    { l: 'Application Profiles', cls: ['fvAp'] },
    { l: 'Networking', sub: [{ l: 'Bridge Domains', cls: ['fvBD'] }, { l: 'VRFs', cls: ['fvCtx'] }, { l: 'L3Outs', cls: ['l3extOut'] }] },
    { l: 'Contracts', sub: [{ l: 'Standard', cls: ['vzBrCP'] }, { l: 'Filters', cls: ['vzFilter'] }] },
    { l: 'Policies', sub: [{ l: 'Protocol', sub: [{ l: 'OSPF Interface', cls: ['ospfIfPol'] }] }] },
  ],
  fvAp: [{ l: 'Application EPGs', cls: ['fvAEPg'] }],
  fvAEPg: [{ l: 'Domains (VMs and Bare-Metals)', cls: ['fvRsDomAtt'], flat: 1 }, { l: 'Static Ports', cls: ['fvRsPathAtt'], flat: 1 },
    { l: 'Contracts', cls: ['fvRsProv', 'fvRsCons'], flat: 1 }, { l: 'Subnets', cls: ['fvSubnet'], flat: 1 }],
  fvBD: [{ l: 'Subnets', cls: ['fvSubnet'], flat: 1 }, { l: 'Associated L3 Outs', cls: ['fvRsBDToOut'], flat: 1 }],
  fvCtx: [{ l: 'EPG Collection for VRF', rn: 'any' }],
  vzAny: [{ l: 'Contracts', cls: ['vzRsAnyToProv', 'vzRsAnyToCons'], flat: 1 }],
  vzBrCP: [{ l: 'Subjects', cls: ['vzSubj'] }],
  vzSubj: [{ l: 'Filters', cls: ['vzRsSubjFiltAtt'], flat: 1 }],
  vzFilter: [{ l: 'Entries', cls: ['vzEntry'], flat: 1 }],
  l3extOut: [{ l: 'Routing Protocols', cls: ['ospfExtP', 'bgpExtP'], flat: 1, max: 1 }, { l: 'Logical Node Profiles', cls: ['l3extLNodeP'] }, { l: 'External EPGs', cls: ['l3extInstP'] }],
  l3extLNodeP: [{ l: 'Configured Nodes', cls: ['l3extRsNodeL3OutAtt'] }, { l: 'Logical Interface Profiles', cls: ['l3extLIfP'] }],
  l3extRsNodeL3OutAtt: [{ l: 'Static Routes', cls: ['ipRouteP'] }],
  ipRouteP: [{ l: 'Next Hops', cls: ['ipNexthopP'], flat: 1 }],
  l3extLIfP: [{ l: 'Interfaces', cls: ['l3extRsPathL3OutAtt'] }, { l: 'OSPF Interface Profile', cls: ['ospfIfP'], flat: 1, max: 1 }],
  l3extRsPathL3OutAtt: [{ l: 'BGP Peers', cls: ['bgpPeerP'], flat: 1 }],
  l3extInstP: [{ l: 'Subnets', cls: ['l3extSubnet'], flat: 1 }, { l: 'Contracts', cls: ['fvRsProv', 'fvRsCons'], flat: 1 }],
  fvnsVlanInstP: [{ l: 'Encap Blocks', cls: ['fvnsEncapBlk'], flat: 1 }],
  infraAttEntityP: [{ l: 'Domains', cls: ['infraRsDomP'], flat: 1 }],
  infraNodeP: [{ l: 'Leaf Selectors', cls: ['infraLeafS'] }, { l: 'Interface Selector Profiles', cls: ['infraRsAccPortP'], flat: 1 }],
  infraLeafS: [{ l: 'Node Blocks', cls: ['infraNodeBlk'], flat: 1 }],
  infraAccPortP: [{ l: 'Access Port Selectors', cls: ['infraHPortS'] }],
  infraHPortS: [{ l: 'Port Blocks', cls: ['infraPortBlk'], flat: 1 }],
  fabricProtPol: [{ l: 'Explicit vPC Protection Groups', cls: ['fabricExplicitGEp'] }],
  fabricExplicitGEp: [{ l: 'Nodes', cls: ['fabricNodePEp'], flat: 1 }],
};

const ACCESS_TREE = [
  { l: 'Switches', sub: [{ l: 'Leaf Switches', sub: [{ l: 'Profiles', cls: ['infraNodeP'], parent: 'uni/infra' }] }] },
  { l: 'Interfaces', sub: [{ l: 'Leaf Interfaces', sub: [{ l: 'Profiles', cls: ['infraAccPortP'], parent: 'uni/infra' },
    { l: 'Policy Groups', sub: [{ l: 'Leaf Access Port', cls: ['infraAccPortGrp'], parent: 'uni/infra/funcprof' }, { l: 'PC/VPC Interface', cls: ['infraAccBndlGrp'], parent: 'uni/infra/funcprof' }] }] }] },
  { l: 'Policies', sub: [
    { l: 'Switch', sub: [{ l: 'Virtual Port Channel default', mo: 'uni/fabric/protpol' }] },
    { l: 'Interface', sub: [{ l: 'Link Level', cls: ['fabricHIfPol'], parent: 'uni/infra' }, { l: 'CDP Interface', cls: ['cdpIfPol'], parent: 'uni/infra' },
      { l: 'LLDP Interface', cls: ['lldpIfPol'], parent: 'uni/infra' }, { l: 'Port Channel', cls: ['lacpLagPol'], parent: 'uni/infra' }] },
    { l: 'Global', sub: [{ l: 'Attachable Access Entity Profiles', cls: ['infraAttEntityP'], parent: 'uni/infra' }] }] },
  { l: 'Physical and External Domains', sub: [{ l: 'Physical Domains', cls: ['physDomP'], parent: 'uni' }, { l: 'L3 Domains', cls: ['l3extDomP'], parent: 'uni' }] },
  { l: 'Pools', sub: [{ l: 'VLAN', cls: ['fvnsVlanInstP'], parent: 'uni/infra' }] },
];

const ICON = {
  fvTenant: 'TN', fvAp: 'AP', fvAEPg: 'EPG', fvBD: 'BD', fvCtx: 'VRF', l3extOut: 'L3', vzBrCP: 'C', vzFilter: 'F', vzSubj: 'S',
  l3extLNodeP: 'NP', l3extLIfP: 'IP', l3extInstP: 'EX', l3extRsNodeL3OutAtt: 'N', l3extRsPathL3OutAtt: 'IF', ipRouteP: 'R', vzAny: '*',
  infraNodeP: 'SW', infraAccPortP: 'IF', infraAccPortGrp: 'PG', infraAccBndlGrp: 'PC', infraAttEntityP: 'AE', physDomP: 'PD',
  l3extDomP: 'L3D', fvnsVlanInstP: 'VL', infraHPortS: 'S', infraLeafS: 'S', fabricExplicitGEp: 'vPC', ospfIfPol: 'O',
  cdpIfPol: 'P', lldpIfPol: 'P', lacpLagPol: 'P', fabricHIfPol: 'P', fabricProtPol: 'vPC',
};
