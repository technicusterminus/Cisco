/* Formular-, Wizard- und Baum-Spezifikationen je ACI-Klasse */
'use strict';

const AAA_ROLES = ['admin', 'aaa', 'access-admin', 'fabric-admin', 'nw-svc-admin', 'nw-svc-params', 'ops', 'read-all', 'tenant-admin', 'tenant-ext-admin', 'vmm-admin'];
const NAME = { k: 'name', l: 'Name', create: true, req: true, ph: 'z. B. Web' };
const ALIAS = { k: 'nameAlias', l: 'Alias', ph: 'optional' };
const DESCR = { k: 'descr', l: 'Description', ph: 'optional' };
const IMM = [['lazy', 'On Demand'], ['immediate', 'Immediate']];
const RES_IMM = [['lazy', 'On Demand'], ['immediate', 'Immediate'], ['pre-provision', 'Pre-provision']];
const MODES = [['regular', 'Trunk'], ['native', 'Access (802.1P)'], ['untagged', 'Access (Untagged)']];
const PORTS = ['unspecified', 'http', 'https', 'dns', 'smtp', 'ftpData', 'pop3', 'rtsp', '22', '443', '8080', '3306'];
const ETHER = [['ip', 'IP'], ['unspecified', 'Unspecified'], ['arp', 'ARP'], ['ipv4', 'IPv4'], ['ipv6', 'IPv6']];
const PROTO = [['unspecified', 'unspecified'], ['tcp', 'tcp'], ['udp', 'udp'], ['icmp', 'icmp'], ['ospfigp', 'ospf'], ['eigrp', 'eigrp'], ['pim', 'pim']];
const SUBNET_SCOPE = [['private', 'Private to VRF'], ['public', 'Advertised Externally'], ['shared', 'Shared between VRFs']];

const relName = (rel, k, l, target, extra) => Object.assign({ rel, k, l, t: 'tname', target }, extra || {});
const relDn = (rel, l, target, extra) => Object.assign({ rel, k: 'tDn', l, t: 'tdn', target: [].concat(target) }, extra || {});
const relNameSelf = (k, l, target) => ({ k, l, t: 'tname', target, create: true, req: true });
const relState = row => stateBadge(row.state);
const col = (l, f) => ({ l, f });
const ac = k => col({ name: 'Name', descr: 'Description', nameAlias: 'Alias' }[k] || k, r => r[k]);
const vlanify = v => (/^\d+$/.test(v || '') ? 'vlan-' + v : v);

function relOf(dn, rel, k) { const a = MIT.a(dn + '/' + makeRn(rel, {})); return a ? a[k] : ''; }
function nameOfDn(dn) { if (!dn) return ''; const rn = rnOf(dn); return rn.replace(/^[a-zA-Z]+-\[?/, '').replace(/\]?$/, '').replace(/-(static|dynamic)$/, ''); }
function mo(cls, attrs, ...children) { const b = { [cls]: { attributes: attrs || {} } }; const k = children.flat().filter(Boolean); if (k.length) b[cls].children = k; return b; }

function parsePorts(text) {
  const out = [];
  String(text || '').split(',').map(s => s.trim()).filter(Boolean).forEach(p => {
    const m = /^(?:1\/)?(\d+)(?:\s*-\s*(?:1\/)?(\d+))?$/.exec(p);
    if (!m) throw new ApiError('Eingabe', 'Ports im Format 1/1-10 oder 1,3,5-7 angeben');
    out.push([Number(m[1]), Number(m[2] || m[1])]);
  });
  if (!out.length) throw new ApiError('Eingabe', 'Mindestens einen Port angeben');
  return out;
}

function hportsBody(name, ports, pg) {
  const kids = parsePorts(ports).map(([a, b], i) => mo('infraPortBlk', { name: 'block' + (i + 2), fromCard: '1', toCard: '1', fromPort: String(a), toPort: String(b) }));
  if (pg) kids.push(mo('infraRsAccBaseGrp', { tDn: pg }));
  return mo('infraHPortS', { name, type: 'range' }, kids);
}

function leafSelBody(name, from, to) {
  if (!/^\d+$/.test(from || '')) throw new ApiError('Eingabe', 'Node-ID (z. B. 101) angeben');
  return mo('infraLeafS', { name, type: 'range' }, mo('infraNodeBlk', { name: 'blk' + from + '-' + (to || from), from_: String(from), to_: String(to || from) }));
}

const SPEC = {
  /* ---------------- Tenant ---------------- */
  fvTenant: {
    fields: [NAME, ALIAS, DESCR], cols: [ac('name'), ac('nameAlias'), ac('descr')], summary: true,
    wizard: {
      title: 'Create Tenant',
      steps: [{ l: 'Tenant', fields: [NAME, ALIAS, DESCR, { k: '_doms', l: 'Security Domains', t: 'rows', cols: [{ k: 'name', l: 'Security Domain', t: 'tname', target: 'aaaDomain', scope: 'aaa' }] },
        { k: '_vrfs', l: 'VRF', t: 'rows', cols: [{ k: 'name', l: 'Name', ph: 'z. B. Prod' }] }] }],
      build: v => ({ url: 'uni', dn: 'uni/tn-' + v.name, body: mo('fvTenant', { name: v.name, nameAlias: v.nameAlias, descr: v.descr },
        (v._doms || []).filter(d => d.name).map(d => mo('aaaDomainRef', { name: d.name })), (v._vrfs || []).map(r => mo('fvCtx', { name: r.name }))) }),
    },
    actions: [['Add Security Domain', dn => createDialog(dn, 'aaaDomainRef', 'Add Security Domain')]],
  },
  fvCtx: {
    groups: [['general', 'General']],
    fields: [NAME, ALIAS,
      { k: 'pcEnfPref', l: 'Policy Control Enforcement Preference', t: 'radio', o: [['enforced', 'Enforced'], ['unenforced', 'Unenforced']] },
      { k: 'pcEnfDir', l: 'Policy Control Enforcement Direction', t: 'radio', o: [['ingress', 'Ingress'], ['egress', 'Egress']] },
      { k: 'ipDataPlaneLearning', l: 'IP Data-plane Learning', t: 'radio', o: [['enabled', 'Enabled'], ['disabled', 'Disabled']] },
      { k: 'bdEnforcedEnable', l: 'BD Enforcement Status', t: 'yesno' },
      relName('fvRsBgpCtxPol', 'tnBgpCtxPolName', 'BGP Timers', 'bgpCtxPol', { empty: 'default', keepEmpty: true }), DESCR],
    cols: [ac('name'), col('Enforcement', r => r.pcEnfPref), col('Segment', r => r.scope), col('pcTag', r => r.pcTag)],
    info: r => [['Segment (VNID)', r.scope], ['pcTag (Class ID)', r.pcTag]], summary: true, oper: ['deployed'],
    wizard: {
      title: 'Create VRF',
      steps: [
        { l: 'VRF', fields: [NAME, ALIAS, { k: 'pcEnfPref', l: 'Policy Control Enforcement Preference', t: 'radio', o: [['enforced', 'Enforced'], ['unenforced', 'Unenforced']], def: 'enforced' },
          { k: 'pcEnfDir', l: 'Policy Control Enforcement Direction', t: 'radio', o: [['ingress', 'Ingress'], ['egress', 'Egress']], def: 'ingress' }, DESCR,
          { k: '_mkbd', l: 'Create A Bridge Domain', t: 'yesno', def: 'no' }] },
        { l: 'Bridge Domain', show: v => v._mkbd === 'yes', fields: [{ k: '_bd', l: 'Name', req: true, ph: 'BD-Web' }, { k: '_sub', l: 'Subnet (Gateway IP)', ph: '10.1.1.1/24' }] },
      ],
      build: (v, parent) => {
        const ctx = mo('fvCtx', { name: v.name, nameAlias: v.nameAlias, descr: v.descr, pcEnfPref: v.pcEnfPref, pcEnfDir: v.pcEnfDir });
        if (v._mkbd !== 'yes') return { body: ctx, dn: parent + '/ctx-' + v.name };
        return { url: parent, dn: parent + '/ctx-' + v.name, body: mo('fvTenant', {}, ctx, mo('fvBD', { name: v._bd }, mo('fvRsCtx', { tnFvCtxName: v.name }), v._sub ? mo('fvSubnet', { ip: v._sub }) : null)) };
      },
    },
  },
  vzAny: { label: 'EPG Collection for VRF', fields: [{ k: 'prefGrMemb', l: 'Preferred Group Member', t: 'radio', o: [['disabled', 'Disabled'], ['enabled', 'Enabled']] }, { k: 'matchT', l: 'Match Type', t: 'select', o: [['AtleastOne', 'AtleastOne'], ['All', 'All'], ['AtmostOne', 'AtmostOne'], ['None', 'None']] }], cols: [] },
  vzRsAnyToProv: { label: 'Provided Contract', fields: [relNameSelf('tnVzBrCPName', 'Contract', 'vzBrCP')], cols: [col('Contract', r => r.tnVzBrCPName), col('Typ', () => 'Provided'), col('State', relState)] },
  vzRsAnyToCons: { label: 'Consumed Contract', fields: [relNameSelf('tnVzBrCPName', 'Contract', 'vzBrCP')], cols: [col('Contract', r => r.tnVzBrCPName), col('Typ', () => 'Consumed'), col('State', relState)] },
  fvBD: {
    groups: [['general', 'General'], ['l3', 'L3 Configurations'], ['adv', 'Advanced/Troubleshooting']],
    fields: [NAME, ALIAS,
      relName('fvRsCtx', 'tnFvCtxName', 'VRF', 'fvCtx', { req: true }),
      { k: 'type', l: 'Type', t: 'radio', o: [['regular', 'regular'], ['fc', 'fc']], ro: true },
      { k: 'unkMacUcastAct', l: 'L2 Unknown Unicast', t: 'radio', o: [['proxy', 'Hardware Proxy'], ['flood', 'Flood']] },
      { k: 'unkMcastAct', l: 'L3 Unknown Multicast Flooding', t: 'radio', o: [['flood', 'Flood'], ['opt-flood', 'Optimized Flood']] },
      { k: 'multiDstPktAct', l: 'Multi Destination Flooding', t: 'radio', o: [['bd-flood', 'Flood in BD'], ['encap-flood', 'Flood in Encapsulation'], ['drop', 'Drop']] },
      { k: 'arpFlood', l: 'ARP Flooding', t: 'yesno' }, DESCR,
      { k: 'unicastRoute', l: 'Unicast Routing', t: 'yesno', g: 'l3' },
      { k: 'mac', l: 'Custom MAC Address', g: 'l3' },
      { k: 'limitIpLearnToSubnets', l: 'Limit IP Learning To Subnet', t: 'yesno', g: 'l3' },
      { k: 'ipLearning', l: 'Endpoint Data-plane Learning', t: 'yesno', g: 'adv' },
      { k: 'epMoveDetectMode', l: 'Endpoint Move Detection Mode', t: 'select', o: [['', '—'], ['garp', 'GARP based detection']], g: 'adv' }],
    flatGroups: { fvSubnet: 'l3', fvRsBDToOut: 'l3' },
    cols: [ac('name'), col('VRF', r => relOf(r.dn, 'fvRsCtx', 'tnFvCtxName') || 'default'), col('Unicast Routing', r => r.unicastRoute),
      col('L2 Unknown Unicast', r => r.unkMacUcastAct), col('ARP Flooding', r => r.arpFlood), col('Segment', r => r.seg)],
    info: r => [['Segment (VNID)', r.seg], ['pcTag', r.pcTag], ['VRF (aufgelöst)', relOf(r.dn, 'fvRsCtx', 'tDn')]], summary: true, oper: ['endpoints', 'deployed'],
    wizard: {
      title: 'Create Bridge Domain',
      steps: [
        { l: 'Main', fields: [NAME, ALIAS, relName('fvRsCtx', 'tnFvCtxName', 'VRF', 'fvCtx', { req: true }),
          { k: 'unkMacUcastAct', l: 'L2 Unknown Unicast', t: 'radio', o: [['proxy', 'Hardware Proxy'], ['flood', 'Flood']], def: 'proxy' },
          { k: 'multiDstPktAct', l: 'Multi Destination Flooding', t: 'radio', o: [['bd-flood', 'Flood in BD'], ['encap-flood', 'Flood in Encapsulation'], ['drop', 'Drop']], def: 'bd-flood' },
          { k: 'arpFlood', l: 'ARP Flooding', t: 'yesno', def: 'no' }, DESCR] },
        { l: 'L3 Configurations', fields: [{ k: 'unicastRoute', l: 'Unicast Routing', t: 'yesno', def: 'yes' },
          { k: '_subnets', l: 'Subnets', t: 'rows', cols: [{ k: 'ip', l: 'Gateway IP', ph: '10.1.1.1/24', req: true },
            { k: 'scope', l: 'Scope', t: 'select', o: [['private', 'Private to VRF'], ['public', 'Advertised Externally'], ['shared', 'Shared between VRFs'], ['public,shared', 'Advertised Externally + Shared']], def: 'private' },
            { k: 'preferred', l: 'Primary', t: 'yesno', def: 'no' }] },
          { k: 'limitIpLearnToSubnets', l: 'Limit IP Learning To Subnet', t: 'yesno', def: 'yes' },
          { k: '_outs', l: 'Associated L3 Outs', t: 'rows', cols: [{ k: 'name', l: 'L3 Out', t: 'tname', target: 'l3extOut' }] }] },
        { l: 'Advanced/Troubleshooting', fields: [{ k: 'ipLearning', l: 'Endpoint Data-plane Learning', t: 'yesno', def: 'yes' },
          { k: 'epMoveDetectMode', l: 'Endpoint Move Detection Mode', t: 'select', o: [['', '—'], ['garp', 'GARP based detection']], def: '' }] },
      ],
      build: (v, parent) => {
        const a = { name: v.name };
        ['nameAlias', 'descr', 'unkMacUcastAct', 'multiDstPktAct', 'arpFlood', 'unicastRoute', 'limitIpLearnToSubnets', 'ipLearning', 'epMoveDetectMode'].forEach(k => { if (v[k] !== undefined && v[k] !== '') a[k] = v[k]; });
        return { dn: parent + '/BD-' + v.name, body: mo('fvBD', a, mo('fvRsCtx', { tnFvCtxName: v['fvRsCtx.tnFvCtxName'] }),
          (v._subnets || []).map(s => mo('fvSubnet', { ip: s.ip, scope: s.scope, preferred: s.preferred })),
          (v._outs || []).map(o => mo('fvRsBDToOut', { tnL3extOutName: o.name }))) };
      },
    },
  },
  fvSubnet: {
    label: 'Subnet',
    fields: [{ k: 'ip', l: 'Gateway IP', create: true, req: true, ph: '10.1.1.1/24', help: 'Adresse des Gateways mit Maske' },
      { k: 'scope', l: 'Scope', t: 'checks', o: SUBNET_SCOPE },
      { k: 'preferred', l: 'Make this IP address primary', t: 'yesno' },
      { k: 'virtual', l: 'Treat as virtual IP address', t: 'yesno' },
      { k: 'ctrl', l: 'Subnet Control', t: 'checks', o: [['nd', 'ND RA Prefix'], ['no-default-gateway', 'No Default SVI Gateway'], ['querier', 'Querier IP']] }, DESCR],
    cols: [col('Gateway Address', r => r.ip), col('Scope', r => r.scope), col('Primary IP Address', r => r.preferred), col('Virtual IP', r => r.virtual)],
  },
  fvRsBDToOut: { label: 'Associated L3 Out', fields: [relNameSelf('tnL3extOutName', 'L3 Out', 'l3extOut')], cols: [col('L3 Out', r => r.tnL3extOutName), col('State', relState)] },
  fvAp: {
    fields: [NAME, ALIAS, DESCR], cols: [ac('name'), ac('nameAlias'), ac('descr')], summary: true, topo: true,
  },
  fvAEPg: {
    groups: [['general', 'General']],
    fields: [NAME, ALIAS,
      relName('fvRsBd', 'tnFvBDName', 'Bridge Domain', 'fvBD', { req: true }),
      { k: 'pcEnfPref', l: 'Intra EPG Isolation', t: 'radio', o: [['unenforced', 'Unenforced'], ['enforced', 'Enforced']] },
      { k: 'prefGrMemb', l: 'Preferred Group Member', t: 'radio', o: [['exclude', 'Exclude'], ['include', 'Include']] },
      { k: 'floodOnEncap', l: 'Flood in Encapsulation', t: 'radio', o: [['disabled', 'Disabled'], ['enabled', 'Enabled']] },
      { k: 'shutdown', l: 'Shutdown EPG', t: 'yesno' }, DESCR],
    cols: [ac('name'), col('Bridge Domain', r => relOf(r.dn, 'fvRsBd', 'tnFvBDName') || 'default'), col('pcTag (sclass)', r => r.pcTag), col('Preferred Group', r => r.prefGrMemb)],
    info: r => [['pcTag (sclass)', r.pcTag], ['VRF-Segment', r.scope], ['BD (aufgelöst)', relOf(r.dn, 'fvRsBd', 'tDn')]],
    summary: true, oper: ['endpoints', 'deployed', 'contracts'],
    wizard: {
      title: 'Create Application EPG',
      steps: [
        { l: 'Identity', fields: [NAME, ALIAS, relName('fvRsBd', 'tnFvBDName', 'Bridge Domain', 'fvBD', { req: true }),
          { k: 'pcEnfPref', l: 'Intra EPG Isolation', t: 'radio', o: [['unenforced', 'Unenforced'], ['enforced', 'Enforced']], def: 'unenforced' },
          { k: 'prefGrMemb', l: 'Preferred Group Member', t: 'radio', o: [['exclude', 'Exclude'], ['include', 'Include']], def: 'exclude' }, DESCR,
          { k: '_doms', l: 'Associate to Domain Profiles', t: 'rows', cols: [{ k: 'tDn', l: 'Domain Profile', t: 'tdn', target: ['physDomP', 'vmmDomP'] }, { k: 'imm', l: 'Resolution Immediacy', t: 'select', o: RES_IMM, def: 'immediate' }] },
          { k: 'isAttrBasedEPg', l: 'uSeg EPG (attributbasiert)', t: 'yesno', def: 'no' },
          { k: '_uip', l: 'uSeg Attribut: IP oder Subnetz', ph: '10.10.10.50 oder 10.10.10.0/28', show: v => v.isAttrBasedEPg === 'yes' },
          { k: '_umac', l: 'uSeg Attribut: MAC', ph: '00:50:56:AA:BB:CC', show: v => v.isAttrBasedEPg === 'yes' },
          { k: '_static', l: 'Statically Link with Leaves/Paths', t: 'yesno', def: 'no', show: v => v.isAttrBasedEPg !== 'yes' }] },
        { l: 'Leaves/Paths', show: v => v._static === 'yes', fields: [
          { k: '_paths', l: 'Paths', t: 'rows', cols: [{ k: 'tDn', l: 'Path', t: 'path' }, { k: 'encap', l: 'Port Encap', ph: 'vlan-10', req: true, w: '90px' }, { k: 'mode', l: 'Mode', t: 'select', o: MODES, def: 'regular' }] },
          { k: '_leaves', l: 'Leaves', t: 'rows', cols: [{ k: 'tDn', l: 'Node', t: 'node' }, { k: 'encap', l: 'Encap', ph: 'vlan-10', req: true, w: '90px' }, { k: 'mode', l: 'Mode', t: 'select', o: MODES, def: 'regular' }] }] },
      ],
      build: (v, parent) => ({
        dn: parent + '/epg-' + v.name,
        body: mo('fvAEPg', { name: v.name, nameAlias: v.nameAlias, descr: v.descr, pcEnfPref: v.pcEnfPref, prefGrMemb: v.prefGrMemb, isAttrBasedEPg: v.isAttrBasedEPg || 'no' },
          mo('fvRsBd', { tnFvBDName: v['fvRsBd.tnFvBDName'] }),
          v.isAttrBasedEPg === 'yes' ? mo('fvCrtrn', { match: 'any' }, v._uip ? mo('fvIpAttr', { name: 'ip1', ip: v._uip }) : null, v._umac ? mo('fvMacAttr', { name: 'mac1', mac: v._umac.toUpperCase() }) : null) : null,
          (v._doms || []).filter(d => d.tDn).map(d => mo('fvRsDomAtt', { tDn: d.tDn, resImedcy: d.imm || 'immediate' })),
          (v._static === 'yes' ? v._paths || [] : []).map(p => mo('fvRsPathAtt', { tDn: p.tDn, encap: vlanify(p.encap), mode: p.mode })),
          (v._static === 'yes' ? v._leaves || [] : []).filter(l => l.tDn).map(l => mo('fvRsNodeAtt', { tDn: l.tDn, encap: vlanify(l.encap), mode: l.mode }))),
      }),
    },
    actions: [['Deploy Static EPG on PC, VPC, or Interface', dn => createDialog(dn, 'fvRsPathAtt', 'Deploy Static EPG on PC, VPC, or Interface')],
      ['Add Physical Domain Association', dn => createDialog(dn, 'fvRsDomAtt', 'Add Physical Domain Association')],
      ['Add VMM Domain Association', dn => createDialog(dn, 'fvRsDomAtt', 'Add VMM Domain Association', { resImedcy: 'immediate' })],
      ['Add Static Leaf', dn => createDialog(dn, 'fvRsNodeAtt')],
      ['Add Provided Contract', dn => createDialog(dn, 'fvRsProv', 'Add Provided Contract')],
      ['Add Consumed Contract', dn => createDialog(dn, 'fvRsCons', 'Add Consumed Contract')],
      ['Add Taboo Contract', dn => createDialog(dn, 'fvRsProtBy', 'Add Taboo Contract')],
      ['Add Consumed Contract Interface', dn => createDialog(dn, 'fvRsConsIf', 'Add Consumed Contract Interface')]],
  },
  fvRsDomAtt: {
    label: 'Domain',
    fields: [{ k: 'tDn', l: 'Domain', t: 'tdn', target: ['physDomP', 'vmmDomP', 'l3extDomP'], create: true, req: true },
      { k: 'resImedcy', l: 'Resolution Immediacy', t: 'select', o: RES_IMM },
      { k: 'instrImedcy', l: 'Deployment Immediacy', t: 'select', o: IMM },
      { k: 'primaryEncap', l: 'Primary VLAN for Micro-Seg', ph: 'unknown' }],
    cols: [col('Domain', r => r.tDn), col('Resolution Immediacy', r => r.resImedcy), col('Deployment Immediacy', r => r.instrImedcy), col('State', relState)],
  },
  fvRsPathAtt: {
    label: 'Static Port',
    fields: [{ k: 'tDn', l: 'Path', t: 'path', create: true, req: true },
      { k: 'encap', l: 'Port Encap (or Secondary VLAN for Micro-Seg)', req: true, ph: 'vlan-10' },
      { k: 'mode', l: 'Mode', t: 'radio', o: MODES },
      { k: 'instrImedcy', l: 'Deployment Immediacy', t: 'radio', o: IMM }, DESCR],
    cols: [col('Path', r => pathLabel(r.tDn)), col('Port Encap', r => r.encap), col('Mode', r => Object.fromEntries(MODES)[r.mode]),
      col('Deployment Immediacy', r => r.instrImedcy), col('State', relState)],
    normalize: v => { v.encap = vlanify(v.encap); return v; },
  },
  fvRsNodeAtt: {
    label: 'Static Leaf',
    fields: [{ k: 'tDn', l: 'Node', t: 'node', create: true, req: true }, { k: 'encap', l: 'Encap', req: true, ph: 'vlan-10' },
      { k: 'mode', l: 'Mode', t: 'radio', o: MODES }, { k: 'instrImedcy', l: 'Deployment Immediacy', t: 'radio', o: IMM }, DESCR],
    cols: [col('Node', r => pathLabel(r.tDn)), col('Encap', r => r.encap), col('Mode', r => Object.fromEntries(MODES)[r.mode]), col('State', relState)],
    normalize: v => { v.encap = vlanify(v.encap); return v; },
  },
  fvRsProv: { label: 'Provided Contract', fields: [relNameSelf('tnVzBrCPName', 'Contract', 'vzBrCP')], cols: [col('Contract', r => r.tnVzBrCPName), col('Typ', () => 'Provided'), col('State', relState)] },
  fvRsCons: { label: 'Consumed Contract', fields: [relNameSelf('tnVzBrCPName', 'Contract', 'vzBrCP')], cols: [col('Contract', r => r.tnVzBrCPName), col('Typ', () => 'Consumed'), col('State', relState)] },
  fvRsProtBy: { label: 'Taboo Contract', fields: [relNameSelf('tnVzTabooName', 'Taboo Contract', 'vzTaboo')], cols: [col('Contract', r => r.tnVzTabooName), col('Typ', () => 'Taboo'), col('State', relState)] },
  fvCEp: { fields: [], cols: [col('MAC', r => r.mac), col('IP', r => r.ip), col('Learning Source', r => r.lcC), col('Interface', r => pathLabel(r.fabricPathDn)), col('Encap', r => r.encap)] },

  /* ---------------- Contracts ---------------- */
  vzBrCP: {
    fields: [NAME, ALIAS, { k: 'scope', l: 'Scope', t: 'select', o: [['context', 'VRF'], ['application-profile', 'Application Profile'], ['tenant', 'Tenant'], ['global', 'Global']] },
      { k: 'prio', l: 'QoS Class', t: 'select', o: [['unspecified', 'Unspecified'], ['level1', 'Level1'], ['level2', 'Level2'], ['level3', 'Level3']] },
      { k: 'targetDscp', l: 'Target DSCP', t: 'select', o: [['unspecified', 'Unspecified']] }, DESCR],
    cols: [ac('name'), col('Scope', r => r.scope), col('Subjects', r => MIT.kids(r.dn, ['vzSubj']).map(d => MIT.a(d).name).join(', ')), ac('descr')],
    summary: true,
    wizard: {
      title: 'Create Contract',
      steps: [{ l: 'Contract', fields: [NAME, ALIAS, { k: 'scope', l: 'Scope', t: 'select', o: [['context', 'VRF'], ['application-profile', 'Application Profile'], ['tenant', 'Tenant'], ['global', 'Global']], def: 'context' }, DESCR,
        { k: '_subj', l: 'Subjects', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'subj', req: true }, { k: 'filters', l: 'Filters', t: 'tnamemulti', target: 'vzFilter', none: 'keine Filter' },
          { k: 'rev', l: 'Apply Both Directions + Reverse Filter Ports', t: 'yesno', def: 'yes' }] }] }],
      build: (v, parent) => ({
        dn: parent + '/brc-' + v.name,
        body: mo('vzBrCP', { name: v.name, nameAlias: v.nameAlias, descr: v.descr, scope: v.scope },
          (v._subj || []).map(s => mo('vzSubj', { name: s.name, revFltPorts: s.rev }, (s.filters || []).map(f => mo('vzRsSubjFiltAtt', { tnVzFilterName: f }))))),
      }),
    },
    actions: [['Create Contract Subject', dn => createDialog(dn, 'vzSubj')], ['Export Contract', dn => exportContract(dn)]],
  },
  vzSubj: {
    label: 'Contract Subject',
    fields: [NAME, ALIAS, { k: 'revFltPorts', l: 'Reverse Filter Ports', t: 'yesno', cl: 'Ports der Gegenrichtung tauschen' },
      { k: 'consMatchT', l: 'Consumer Match Type', t: 'select', o: [['AtleastOne', 'AtleastOne'], ['All', 'All'], ['AtmostOne', 'AtmostOne'], ['None', 'None']] },
      { k: 'provMatchT', l: 'Provider Match Type', t: 'select', o: [['AtleastOne', 'AtleastOne'], ['All', 'All'], ['AtmostOne', 'AtmostOne'], ['None', 'None']] }, DESCR],
    cols: [ac('name'), col('Reverse Filter Ports', r => r.revFltPorts), col('Filters', r => MIT.kids(r.dn, ['vzRsSubjFiltAtt']).map(d => MIT.a(d).tnVzFilterName).join(', '))],
    wizard: {
      title: 'Create Contract Subject',
      steps: [{ l: 'Subject', fields: [NAME, DESCR, { k: 'revFltPorts', l: 'Apply Both Directions + Reverse Filter Ports', t: 'yesno', def: 'yes' },
        { k: '_f', l: 'Filters', t: 'rows', start: true, cols: [{ k: 'name', l: 'Filter', t: 'tname', target: 'vzFilter' }, { k: 'action', l: 'Action', t: 'select', o: [['permit', 'Permit'], ['deny', 'Deny']], def: 'permit' }] }] }],
      build: (v, parent) => ({ dn: parent + '/subj-' + v.name, body: mo('vzSubj', { name: v.name, descr: v.descr, revFltPorts: v.revFltPorts }, (v._f || []).map(f => mo('vzRsSubjFiltAtt', { tnVzFilterName: f.name, action: f.action }))) }),
    },
  },
  vzRsSubjFiltAtt: {
    label: 'Filter',
    fields: [relNameSelf('tnVzFilterName', 'Filter', 'vzFilter'), { k: 'action', l: 'Action', t: 'radio', o: [['permit', 'Permit'], ['deny', 'Deny']] },
      { k: 'directives', l: 'Directives', t: 'checks', o: [['log', 'Log']] }],
    cols: [col('Name', r => r.tnVzFilterName), col('Action', r => r.action), col('Directives', r => r.directives), col('State', relState)],
  },
  vzTaboo: {
    label: 'Taboo Contract',
    fields: [NAME, ALIAS, DESCR],
    cols: [ac('name'), col('Subjects', r => MIT.kids(r.dn, ['vzTSubj']).map(d => MIT.a(d).name).join(', ')), ac('descr')],
    wizard: {
      title: 'Create Taboo Contract',
      steps: [{ l: 'Taboo Contract', fields: [NAME, DESCR, { k: '_subj', l: 'Subjects', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'deny', req: true }, { k: 'filters', l: 'Filters', t: 'tnamemulti', target: 'vzFilter' }] }] }],
      build: (v, parent) => ({ dn: parent + '/taboo-' + v.name, body: mo('vzTaboo', { name: v.name, descr: v.descr }, (v._subj || []).map(s => mo('vzTSubj', { name: s.name }, (s.filters || []).map(f => mo('vzRsDenyRule', { tnVzFilterName: f }))))) }),
    },
  },
  vzTSubj: { label: 'Taboo Contract Subject', fields: [NAME, DESCR], cols: [ac('name'), col('Filters', r => MIT.kids(r.dn, ['vzRsDenyRule']).map(d => MIT.a(d).tnVzFilterName).join(', '))] },
  vzRsDenyRule: { label: 'Filter', fields: [relNameSelf('tnVzFilterName', 'Filter', 'vzFilter'), { k: 'directives', l: 'Directives', t: 'checks', o: [['log', 'Log']] }], cols: [col('Filter', r => r.tnVzFilterName), col('State', relState)] },
  vzFilter: {
    fields: [NAME, ALIAS, DESCR],
    cols: [ac('name'), col('Entries', r => MIT.kids(r.dn, ['vzEntry']).map(d => MIT.a(d).name).join(', ')), ac('descr')],
    wizard: {
      title: 'Create Filter',
      steps: [{ l: 'Filter', fields: [NAME, ALIAS, DESCR, { k: '_e', l: 'Entries', t: 'rows', start: true, cols: [
        { k: 'name', l: 'Name', ph: 'http', req: true }, { k: 'etherT', l: 'EtherType', t: 'select', o: ETHER, def: 'ip' }, { k: 'prot', l: 'IP Protocol', t: 'select', o: PROTO, def: 'tcp' },
        { k: 'dFromPort', l: 'Dest. Port From', list: PORTS, ph: 'unspecified', w: '100px' }, { k: 'dToPort', l: 'Dest. Port To', list: PORTS, ph: 'unspecified', w: '100px' },
        { k: 'stateful', l: 'Stateful', t: 'yesno', def: 'no' }] }] }],
      build: (v, parent) => ({
        dn: parent + '/flt-' + v.name,
        body: mo('vzFilter', { name: v.name, nameAlias: v.nameAlias, descr: v.descr }, (v._e || []).map(e => {
          const a = { name: e.name, etherT: e.etherT, prot: ['ip', 'ipv4', 'ipv6'].includes(e.etherT) ? e.prot : 'unspecified', stateful: e.stateful };
          if (['tcp', 'udp'].includes(a.prot)) { a.dFromPort = e.dFromPort || 'unspecified'; a.dToPort = e.dToPort || e.dFromPort || 'unspecified'; }
          return mo('vzEntry', a);
        })),
      }),
    },
  },
  vzEntry: {
    label: 'Filter Entry',
    fields: [NAME, { k: 'etherT', l: 'EtherType', t: 'select', o: [['unspecified', 'Unspecified']].concat(ETHER.filter(e => e[0] !== 'unspecified')) },
      { k: 'arpOpc', l: 'ARP Flag', t: 'select', o: [['unspecified', 'Unspecified'], ['req', 'ARP Request'], ['reply', 'ARP Reply']], show: v => v.etherT === 'arp' },
      { k: 'prot', l: 'IP Protocol', t: 'select', o: PROTO, show: v => ['ip', 'ipv4', 'ipv6'].includes(v.etherT) },
      { k: 'applyToFrag', l: 'Match Only Fragments', t: 'yesno', show: v => ['ip', 'ipv4', 'ipv6'].includes(v.etherT) },
      { k: 'sFromPort', l: 'Source Port / Range From', list: PORTS, show: v => ['tcp', 'udp'].includes(v.prot) },
      { k: 'sToPort', l: 'Source Port / Range To', list: PORTS, show: v => ['tcp', 'udp'].includes(v.prot) },
      { k: 'dFromPort', l: 'Destination Port / Range From', list: PORTS, show: v => ['tcp', 'udp'].includes(v.prot) },
      { k: 'dToPort', l: 'Destination Port / Range To', list: PORTS, show: v => ['tcp', 'udp'].includes(v.prot) },
      { k: 'tcpRules', l: 'TCP Session Rules', t: 'select', o: [['', 'Unspecified'], ['est', 'Established']], show: v => v.prot === 'tcp' },
      { k: 'stateful', l: 'Stateful', t: 'yesno', show: v => v.prot === 'tcp' }],
    normalize: v => { if (v.dFromPort && v.dFromPort !== 'unspecified' && (!v.dToPort || v.dToPort === 'unspecified')) v.dToPort = v.dFromPort; if (v.sFromPort && v.sFromPort !== 'unspecified' && (!v.sToPort || v.sToPort === 'unspecified')) v.sToPort = v.sFromPort; return v; },
    cols: [ac('name'), col('EtherType', r => r.etherT), col('IP Protocol', r => r.prot), col('Source Port', r => r.sFromPort === r.sToPort ? r.sFromPort : r.sFromPort + '-' + r.sToPort),
      col('Destination Port', r => r.dFromPort === r.dToPort ? r.dFromPort : r.dFromPort + '-' + r.dToPort), col('TCP Session Rules', r => r.tcpRules), col('Stateful', r => r.stateful)],
  },

  /* ---------------- L3Out ---------------- */
  l3extOut: {
    fields: [NAME, ALIAS, relName('l3extRsEctx', 'tnFvCtxName', 'VRF', 'fvCtx', { req: true }),
      relDn('l3extRsL3DomAtt', 'L3 Domain', 'l3extDomP', { req: true }),
      { k: 'enforceRtctrl', l: 'Route Control Enforcement', t: 'checks', o: [['import', 'Import'], ['export', 'Export']] }, DESCR],
    cols: [ac('name'), col('VRF', r => relOf(r.dn, 'l3extRsEctx', 'tnFvCtxName')), col('L3 Domain', r => nameOfDn(relOf(r.dn, 'l3extRsL3DomAtt', 'tDn'))),
      col('Protocols', r => [MIT.get(r.dn + '/ospfExtP') ? 'OSPF' : '', MIT.get(r.dn + '/bgpExtP') ? 'BGP' : ''].filter(Boolean).join(', '))],
    summary: true, oper: ['neighbors', 'routes'],
    wizard: {
      title: 'Create L3Out',
      steps: [
        { l: 'Identity', fields: [NAME, relName('l3extRsEctx', 'tnFvCtxName', 'VRF', 'fvCtx', { req: true }), relDn('l3extRsL3DomAtt', 'L3 Domain', 'l3extDomP', { req: true }),
          { k: '_ospf', l: 'OSPF', t: 'yesno', def: 'no' }, { k: '_area', l: 'OSPF Area ID', ph: 'backbone oder 0.0.0.1', def: 'backbone', show: v => v._ospf === 'yes' },
          { k: '_atype', l: 'OSPF Area Type', t: 'radio', o: [['nssa', 'NSSA area'], ['regular', 'Regular area'], ['stub', 'Stub area']], def: 'regular', show: v => v._ospf === 'yes' },
          { k: '_bgp', l: 'BGP', t: 'yesno', def: 'no' },
          { k: '_eigrp', l: 'EIGRP', t: 'yesno', def: 'no' }, { k: '_easn', l: 'EIGRP Autonomous System', ph: '100', show: v => v._eigrp === 'yes' }] },
        { l: 'Nodes and Interfaces', fields: [
          { k: '_np', l: 'Node Profile Name', ph: 'leer = <L3Out>_nodeProfile' }, { k: '_ifp', l: 'Interface Profile Name', ph: 'leer = <L3Out>_interfaceProfile' },
          { k: '_l3', l: 'Interface Types: Layer 3', t: 'radio', o: [['l3-port', 'Routed'], ['sub-interface', 'Sub-Interface'], ['ext-svi', 'SVI']], def: 'l3-port' },
          { k: '_nodes', l: 'Nodes', t: 'rows', start: true, cols: [{ k: 'node', l: 'Node ID', t: 'node' }, { k: 'rtrId', l: 'Router ID', ph: '1.1.1.103', req: true }, { k: 'lb', l: 'Loopback = Router ID', t: 'yesno', def: 'yes' }] },
          { k: '_ifs', l: 'Interfaces', t: 'rows', start: true, cols: [{ k: 'tDn', l: 'Interface', t: 'path' }, { k: 'addr', l: 'IP Address', ph: '172.16.0.1/30', req: true, w: '120px' },
            { k: 'encap', l: 'Encap', ph: 'vlan-300', w: '90px' }, { k: 'mtu', l: 'MTU', def: 'inherit', w: '70px' }] }] },
        { l: 'Protocols', show: v => v._ospf === 'yes' || v._bgp === 'yes', fields: [
          { k: '_opol', l: 'OSPF Policy', t: 'tname', target: 'ospfIfPol', empty: 'default (common)', show: v => v._ospf === 'yes' },
          { k: '_peers', l: 'BGP Peer Connectivity', t: 'rows', show: v => v._bgp === 'yes', cols: [{ k: 'addr', l: 'Peer Address', ph: '172.16.1.2', req: true }, { k: 'asn', l: 'Remote ASN', ph: '65100', req: true }] }] },
        { l: 'External EPG', fields: [{ k: '_epg', l: 'Name', ph: 'Internet' }, { k: '_def', l: 'Default EPG for all external networks', t: 'yesno', def: 'yes' },
          { k: '_subs', l: 'Subnets', t: 'rows', show: v => v._def !== 'yes', cols: [{ k: 'ip', l: 'IP Address', ph: '8.8.8.0/24', req: true }] }] },
      ],
      build: (v, parent) => {
        const ifs = (v._ifs || []).map(i => {
          const peers = (v._peers || []).filter(p => { try { return ipInNet(p.addr, i.addr); } catch (e) { return false; } });
          const a = { tDn: i.tDn, ifInstT: v._l3, addr: i.addr, mtu: i.mtu || 'inherit' };
          if (v._l3 !== 'l3-port') a.encap = vlanify(i.encap);
          return mo('l3extRsPathL3OutAtt', a, peers.map(p => mo('bgpPeerP', { addr: p.addr }, mo('bgpAsP', { asn: p.asn }))));
        });
        const nodes = (v._nodes || []).filter(n => n.node).map(n => mo('l3extRsNodeL3OutAtt', { tDn: n.node, rtrId: n.rtrId, rtrIdLoopBack: n.lb }));
        const lif = mo('l3extLIfP', { name: v._ifp || v.name + '_interfaceProfile' }, v._ospf === 'yes' ? mo('ospfIfP', {}, mo('ospfRsIfPol', { tnOspfIfPolName: v._opol || '' })) : null,
          v._eigrp === 'yes' ? mo('eigrpIfP', {}, mo('eigrpRsIfPol', { tnEigrpIfPolName: '' })) : null, ifs);
        const ext = v._epg ? mo('l3extInstP', { name: v._epg }, (v._def === 'yes' ? [{ ip: '0.0.0.0/0' }] : v._subs || []).map(s => mo('l3extSubnet', { ip: s.ip, scope: 'import-security' }))) : null;
        return {
          dn: parent + '/out-' + v.name,
          body: mo('l3extOut', { name: v.name }, mo('l3extRsEctx', { tnFvCtxName: v['l3extRsEctx.tnFvCtxName'] }), mo('l3extRsL3DomAtt', { tDn: v['l3extRsL3DomAtt.tDn'] }),
            v._ospf === 'yes' ? mo('ospfExtP', { areaId: v._area || 'backbone', areaType: v._atype }) : null, v._bgp === 'yes' ? mo('bgpExtP', {}) : null,
            v._eigrp === 'yes' ? mo('eigrpExtP', { asn: v._easn || '100' }) : null,
            mo('l3extLNodeP', { name: v._np || v.name + '_nodeProfile' }, nodes, lif), ext),
        };
      },
    },
    actions: [['Create Node Profile', dn => createDialog(dn, 'l3extLNodeP')], ['Create External EPG', dn => createDialog(dn, 'l3extInstP')]],
  },
  ospfExtP: {
    label: 'OSPF',
    fields: [{ k: 'areaId', l: 'OSPF Area ID', ph: 'backbone, 0.0.0.1 oder 1' },
      { k: 'areaType', l: 'OSPF Area Type', t: 'radio', o: [['nssa', 'NSSA area'], ['regular', 'Regular area'], ['stub', 'Stub area']] },
      { k: 'areaCost', l: 'OSPF Area Cost' }, { k: 'areaCtrl', l: 'OSPF Area Control', t: 'checks', o: [['redistribute', 'Send redistributed LSAs into NSSA area'], ['summary', 'Originate summary LSA'], ['suppress-fa', 'Suppress forwarding address']] }],
    cols: [col('Protocol', () => 'OSPF'), col('Area ID', r => r.areaId), col('Area Type', r => r.areaType)],
  },
  bgpExtP: { label: 'BGP', fields: [], cols: [col('Protocol', () => 'BGP')] },
  l3extLNodeP: { label: 'Logical Node Profile', fields: [NAME, ALIAS, DESCR], cols: [ac('name'), col('Nodes', r => MIT.kids(r.dn, ['l3extRsNodeL3OutAtt']).map(d => pathLabel(MIT.a(d).tDn)).join(', '))],
    actions: [['Create Interface Profile', dn => createDialog(dn, 'l3extLIfP')]] },
  l3extRsNodeL3OutAtt: {
    label: 'Node',
    fields: [{ k: 'tDn', l: 'Node ID', t: 'node', create: true, req: true }, { k: 'rtrId', l: 'Router ID', ph: '1.1.1.103', req: true },
      { k: 'rtrIdLoopBack', l: 'Use Router ID as Loopback Address', t: 'yesno' }],
    cols: [col('Node ID', r => pathLabel(r.tDn)), col('Router ID', r => r.rtrId), col('Static Routes', r => MIT.kids(r.dn, ['ipRouteP']).map(d => MIT.a(d).ip).join(', '))],
  },
  ipRouteP: {
    label: 'Static Route',
    fields: [{ k: 'ip', l: 'Prefix', create: true, req: true, ph: '0.0.0.0/0' }, { k: 'pref', l: 'Fallback Preference' }, { k: 'aggregate', l: 'Aggregate', t: 'yesno' },
      { k: 'rtCtrl', l: 'Route Control', t: 'checks', o: [['bfd', 'BFD']] }, relDn('ipRsRouteTrack', 'Track Policy', 'fvTrackList', { tenantScope: true })],
    wizard: {
      title: 'Create Static Route',
      steps: [{ l: 'Static Route', fields: [{ k: 'ip', l: 'Prefix', req: true, ph: '0.0.0.0/0' }, { k: 'pref', l: 'Fallback Preference', def: '1' },
        { k: 'rtCtrl', l: 'Route Control', t: 'checks', o: [['bfd', 'BFD']] }, { k: '_trk', l: 'Track Policy', t: 'tdn', target: ['fvTrackList'], tenantScope: true },
        { k: '_nh', l: 'Next Hop Addresses', t: 'rows', start: true, cols: [{ k: 'nhAddr', l: 'Next Hop IP', ph: '172.16.0.2', req: true }, { k: 'pref', l: 'Preference', def: 'unspecified' },
          { k: 'trk', l: 'Track Policy', t: 'tdn', target: ['fvTrackList'], tenantScope: true }] }] }],
      build: (v, parent) => ({ dn: parent + '/rt-[' + v.ip + ']', body: mo('ipRouteP', { ip: v.ip, pref: v.pref, rtCtrl: v.rtCtrl || '' },
        v._trk ? mo('ipRsRouteTrack', { tDn: v._trk }) : null,
        (v._nh || []).map(n => mo('ipNexthopP', { nhAddr: n.nhAddr, pref: n.pref }, n.trk ? mo('ipRsNexthopRouteTrack', { tDn: n.trk }) : null))) }),
    },
    cols: [col('Prefix', r => r.ip), col('Next Hops', r => MIT.kids(r.dn, ['ipNexthopP']).map(d => MIT.a(d).nhAddr).join(', ')), col('Preference', r => r.pref)],
  },
  ipNexthopP: { label: 'Next Hop', fields: [{ k: 'nhAddr', l: 'Next Hop Address', create: true, req: true, ph: '172.16.1.2' }, { k: 'pref', l: 'Preference' },
    relDn('ipRsNexthopRouteTrack', 'Track Policy', 'fvTrackList', { tenantScope: true })], cols: [col('Next Hop IP', r => r.nhAddr), col('Preference', r => r.pref)] },
  l3extLIfP: { label: 'Logical Interface Profile', fields: [NAME, ALIAS, DESCR], cols: [ac('name'), col('Interfaces', r => MIT.kids(r.dn, ['l3extRsPathL3OutAtt']).map(d => pathLabel(MIT.a(d).tDn)).join(', '))] },
  l3extRsPathL3OutAtt: {
    label: 'Interface',
    fields: [{ k: 'ifInstT', l: 'Interface Type', t: 'radio', o: [['l3-port', 'Routed Interface'], ['sub-interface', 'Routed Sub-Interface'], ['ext-svi', 'SVI']] },
      { k: 'tDn', l: 'Path', t: 'path', create: true, req: true },
      { k: 'addr', l: 'IPv4 Primary / IPv6 Preferred Address', req: true, ph: '172.16.1.1/30' },
      { k: 'encap', l: 'Encap', ph: 'vlan-100', show: v => v.ifInstT !== 'l3-port' },
      { k: 'mode', l: 'Mode', t: 'radio', o: MODES, show: v => v.ifInstT === 'ext-svi' },
      { k: 'mtu', l: 'MTU (bytes)', ph: 'inherit' }, { k: 'mac', l: 'MAC Address' }],
    normalize: v => { v.encap = vlanify(v.encap); if (v.ifInstT === 'l3-port') delete v.encap; return v; },
    wizard: {
      title: 'Select Routed Interface / Sub-Interface / SVI',
      steps: [{ l: 'Interface', fields: [{ k: 'ifInstT', l: 'Interface Type', t: 'radio', o: [['l3-port', 'Routed Interface'], ['sub-interface', 'Routed Sub-Interface'], ['ext-svi', 'SVI']], def: 'l3-port' },
        { k: 'tDn', l: 'Path', t: 'path', req: true, help: 'Für SVI auf vPC als Pfadtyp "Virtual Port Channel" wählen' },
        { k: 'encap', l: 'Encap', ph: 'vlan-300', show: v => v.ifInstT !== 'l3-port' },
        { k: 'addr', l: 'IPv4 Primary Address', ph: '172.16.1.1/29', show: v => !/protpaths/.test(v.tDn || '') },
        { k: '_a', l: 'Side A IPv4 Primary', ph: '172.16.1.1/29', show: v => /protpaths/.test(v.tDn || '') },
        { k: '_b', l: 'Side B IPv4 Primary', ph: '172.16.1.2/29', show: v => /protpaths/.test(v.tDn || '') },
        { k: '_sec', l: 'IPv4 Secondary / Floating Address', ph: '172.16.1.3/29', show: v => v.ifInstT === 'ext-svi', help: 'Gemeinsame Adresse beider vPC-Leafs, z. B. als Next Hop für Static Routes des Routers' },
        { k: 'mtu', l: 'MTU (bytes)', def: 'inherit' }] }],
      build: (v, parent) => {
        const vpc = /protpaths/.test(v.tDn || '');
        const sec = v._sec ? [mo('l3extIp', { addr: v._sec })] : [];
        const a = { tDn: v.tDn, ifInstT: v.ifInstT, mtu: v.mtu || 'inherit' };
        if (v.ifInstT !== 'l3-port') a.encap = vlanify(v.encap);
        if (!vpc) a.addr = v.addr;
        return { dn: parent + '/rspathL3OutAtt-[' + v.tDn + ']', body: mo('l3extRsPathL3OutAtt', a,
          vpc ? [mo('l3extMember', { side: 'A', addr: v._a }, sec), mo('l3extMember', { side: 'B', addr: v._b }, sec)] : sec) };
      },
    },
    cols: [col('Path', r => pathLabel(r.tDn)), col('IP Address', r => r.addr), col('Interface Type', r => r.ifInstT), col('Encap', r => r.encap), col('MTU (bytes)', r => r.mtu), col('State', relState)],
  },
  l3extMember: { label: 'vPC Member', fields: [{ k: 'side', l: 'Side', t: 'select', o: [['A', 'A'], ['B', 'B']], create: true, req: true }, { k: 'addr', l: 'IPv4 Primary', req: true }],
    cols: [col('Side', r => r.side), col('IPv4 Primary', r => r.addr), col('Secondary', r => MIT.kids(r.dn, ['l3extIp']).map(d => MIT.a(d).addr).join(', '))] },
  l3extIp: { label: 'IPv4 Secondary Address', fields: [{ k: 'addr', l: 'IPv4 Address', create: true, req: true, ph: '172.16.1.3/29' }], cols: [col('Address', r => r.addr)] },
  l3extVirtualLIfP: {
    label: 'Floating SVI', menu: 'Create Floating SVI',
    fields: [{ k: 'addr', l: 'IPv4 Primary Address', req: true }, { k: 'mtu', l: 'MTU (bytes)' }],
    wizard: {
      title: 'Create Floating SVI',
      steps: [{ l: 'Floating SVI', fields: [{ k: '_node', l: 'Anchor Node', t: 'node', req: true }, { k: 'encap', l: 'Encap', ph: 'vlan-310', req: true },
        { k: 'addr', l: 'IPv4 Primary Address', ph: '172.16.10.11/24', req: true }, { k: '_sec', l: 'IPv4 Secondary Address', ph: 'optional' }, { k: 'mtu', l: 'MTU (bytes)', def: 'inherit' },
        { k: '_doms', l: 'Path Attributes (Domain + Floating IP)', t: 'rows', start: true, cols: [{ k: 'tDn', l: 'Domain', t: 'tdn', target: ['physDomP', 'vmmDomP'] },
          { k: 'floating', l: 'Floating IP Address', ph: '172.16.10.20/24' }] }] }],
      build: (v, parent) => ({ dn: parent + '/vlifp-[' + v._node + ']-[' + vlanify(v.encap) + ']', body: mo('l3extVirtualLIfP', { nodeDn: v._node, encap: vlanify(v.encap), addr: v.addr, ifInstT: 'ext-svi', mtu: v.mtu || 'inherit' },
        v._sec ? mo('l3extIp', { addr: v._sec }) : null, (v._doms || []).filter(d => d.tDn).map(d => mo('l3extRsDynPathAtt', { tDn: d.tDn, floatingAddr: d.floating || '0.0.0.0' }))) }),
    },
    cols: [col('Anchor Node', r => pathLabel(r.nodeDn)), col('Encap', r => r.encap), col('IP', r => r.addr),
      col('Floating', r => MIT.kids(r.dn, ['l3extRsDynPathAtt']).map(d => nameOfDn(MIT.a(d).tDn) + ' ' + MIT.a(d).floatingAddr).join(', '))],
  },
  l3extRsDynPathAtt: { label: 'Floating Path', fields: [{ k: 'tDn', l: 'Domain', t: 'tdn', target: ['physDomP', 'vmmDomP'], create: true, req: true }, { k: 'floatingAddr', l: 'Floating IP Address' }],
    cols: [col('Domain', r => nameOfDn(r.tDn)), col('Floating IP', r => r.floatingAddr), col('State', relState)] },
  eigrpExtP: { label: 'EIGRP', fields: [{ k: 'asn', l: 'Autonomous System Number', req: true, ph: '100' }], cols: [col('EIGRP AS', r => r.asn)] },
  eigrpIfP: { label: 'EIGRP Interface Profile', fields: [relName('eigrpRsIfPol', 'tnEigrpIfPolName', 'EIGRP Policy', 'eigrpIfPol', { empty: 'default (common)', keepEmpty: true })],
    cols: [col('EIGRP Policy', r => relOf(r.dn, 'eigrpRsIfPol', 'tnEigrpIfPolName') || 'default')] },
  eigrpIfPol: { label: 'EIGRP Interface Policy', fields: [NAME, { k: 'helloIntvl', l: 'Hello Interval (sec)' }, { k: 'holdIntvl', l: 'Hold Interval (sec)' },
    { k: 'ctrl', l: 'Control State', t: 'checks', o: [['bfd', 'BFD'], ['nh-self', 'Self Nexthop'], ['passive', 'Passive'], ['split-horizon', 'Split Horizon']] }],
    cols: [ac('name'), col('Hello / Hold', r => r.helloIntvl + ' / ' + r.holdIntvl), col('Control', r => r.ctrl)] },
  bfdIfP: { label: 'BFD Interface Profile', fields: [{ k: 'type', l: 'Authentication Type', t: 'select', o: [['none', 'No authentication'], ['sha1', 'Keyed SHA1']] },
    relName('bfdRsIfPol', 'tnBfdIfPolName', 'BFD Interface Policy', 'bfdIfPol', { empty: 'default', keepEmpty: true })],
    cols: [col('Policy', r => relOf(r.dn, 'bfdRsIfPol', 'tnBfdIfPolName') || 'default'), col('Auth', r => r.type)] },
  bfdIfPol: { label: 'BFD Interface Policy', fields: [NAME, { k: 'adminSt', l: 'Admin State', t: 'radio', o: [['enabled', 'Enabled'], ['disabled', 'Disabled']] },
    { k: 'minTxIntvl', l: 'Minimum Transmit Interval (msec)' }, { k: 'minRxIntvl', l: 'Minimum Receive Interval (msec)' }, { k: 'detectMult', l: 'Detection Multiplier' }],
    cols: [ac('name'), col('Tx/Rx', r => r.minTxIntvl + ' / ' + r.minRxIntvl), col('Multiplier', r => r.detectMult)] },
  bgpCtxPol: { label: 'BGP Timers Policy', fields: [NAME, { k: 'kaIntvl', l: 'Keepalive Interval (sec)' }, { k: 'holdIntvl', l: 'Hold Interval (sec)' }, { k: 'staleIntvl', l: 'Stale Interval (sec)' }],
    cols: [ac('name'), col('Keepalive / Hold', r => r.kaIntvl + ' / ' + r.holdIntvl)] },
  bgpRtSummPol: { label: 'BGP Route Summarization Policy', fields: [NAME, { k: 'ctrl', l: 'Control State', t: 'checks', o: [['as-set', 'Generate AS-SET information'], ['summary-only', 'Do not advertise more specifics']] }],
    cols: [ac('name'), col('Control', r => r.ctrl)] },
  ospfRtSummPol: { label: 'OSPF Route Summarization Policy', fields: [NAME, { k: 'cost', l: 'Cost' }, { k: 'interAreaEnabled', l: 'Inter-Area Enabled', t: 'yesno' }], cols: [ac('name'), col('Cost', r => r.cost)] },
  eigrpRtSummPol: { label: 'EIGRP Route Summarization Policy', fields: [NAME], cols: [ac('name')] },
  fvIPSLAMonitoringPol: { label: 'IP SLA Monitoring Policy', fields: [NAME, { k: 'slaType', l: 'SLA Type', t: 'select', o: [['icmp', 'ICMP'], ['tcp', 'TCP'], ['http', 'HTTP']] },
    { k: 'slaFrequency', l: 'SLA Frequency (sec)' }, { k: 'slaPort', l: 'Destination Port', show: v => v.slaType === 'tcp' }],
    cols: [ac('name'), col('Type', r => r.slaType), col('Frequency', r => r.slaFrequency)] },
  fvTrackMember: { label: 'Track Member', fields: [NAME, { k: 'dstIpAddr', l: 'Destination IP', req: true, ph: '172.16.0.2' },
    { k: 'scopeDn', l: 'Scope (L3Out oder BD)', t: 'tdn', target: ['l3extOut', 'fvBD'], tenantScope: true }, relDn('fvRsIpslaMonPol', 'IP SLA Policy', 'fvIPSLAMonitoringPol', { tenantScope: true })],
    cols: [ac('name'), col('Destination', r => r.dstIpAddr), col('Scope', r => nameOfDn(r.scopeDn)), col('State', r => { const t = ((App.state || {}).tracks || {})[r.dn]; return t === undefined ? '—' : stateBadge(t ? 'up' : 'down'); })] },
  fvTrackList: {
    label: 'Track List', fields: [NAME, { k: 'type', l: 'Type of Track List', t: 'radio', o: [['percentage', 'Threshold percentage'], ['weight', 'Threshold weight']] },
      { k: 'percentageUp', l: 'Percentage Up' }, { k: 'percentageDown', l: 'Percentage Down' }],
    wizard: {
      title: 'Create Track List',
      steps: [{ l: 'Track List', fields: [NAME, { k: 'percentageUp', l: 'Percentage Up', def: '1' }, { k: 'percentageDown', l: 'Percentage Down', def: '0' },
        { k: '_m', l: 'Track Members', t: 'rows', start: true, cols: [{ k: 'tDn', l: 'Track Member', t: 'tdn', target: ['fvTrackMember'], tenantScope: true }] }] }],
      build: (v, parent) => ({ dn: parent + '/tracklist-' + v.name, body: mo('fvTrackList', { name: v.name, type: 'percentage', percentageUp: v.percentageUp, percentageDown: v.percentageDown },
        (v._m || []).filter(m => m.tDn).map(m => mo('fvRsOtmListMember', { tDn: m.tDn }))) }),
    },
    cols: [ac('name'), col('Members', r => MIT.kids(r.dn, ['fvRsOtmListMember']).map(d => nameOfDn(MIT.a(d).tDn)).join(', ')), col('Up', r => r.percentageUp + '%')] },
  ospfIfP: {
    label: 'OSPF Interface Profile',
    fields: [relName('ospfRsIfPol', 'tnOspfIfPolName', 'OSPF Policy', 'ospfIfPol', { empty: 'default (common)', keepEmpty: true }),
      { k: 'authType', l: 'Authentication Type', t: 'select', o: [['none', 'No authentication'], ['simple', 'Simple'], ['md5', 'MD5 authentication']] }, { k: 'authKeyId', l: 'Authentication Key ID' }],
    cols: [col('OSPF Policy', r => relOf(r.dn, 'ospfRsIfPol', 'tnOspfIfPolName') || 'default'), col('Authentication Type', r => r.authType)],
  },
  ospfIfPol: {
    label: 'OSPF Interface Policy',
    fields: [NAME, { k: 'nwT', l: 'Network Type', t: 'radio', o: [['bcast', 'Broadcast'], ['p2p', 'Point-to-point'], ['unspecified', 'Unspecified']] },
      { k: 'prio', l: 'Priority' }, { k: 'cost', l: 'Cost of Interface' },
      { k: 'ctrl', l: 'Interface Controls', t: 'checks', o: [['advert-subnet', 'Advertise subnet'], ['bfd', 'BFD'], ['mtu-ignore', 'MTU ignore'], ['passive', 'Passive participation']] },
      { k: 'helloIntvl', l: 'Hello Interval (sec)' }, { k: 'deadIntvl', l: 'Dead Interval (sec)' }, { k: 'rexmitIntvl', l: 'Retransmit Interval (sec)' }, { k: 'xmitDelay', l: 'Transmit Delay (sec)' }],
    cols: [ac('name'), col('Network Type', r => r.nwT), col('Interface Controls', r => r.ctrl), col('Hello / Dead', r => r.helloIntvl + ' / ' + r.deadIntvl)],
  },
  bgpPeerP: {
    label: 'BGP Peer Connectivity Profile',
    fields: [{ k: 'addr', l: 'Peer Address', create: true, req: true, ph: '172.16.1.2' },
      { rel: 'bgpAsP', k: 'asn', l: 'Remote Autonomous System Number', req: true, ph: '65100' },
      { rel: 'bgpLocalAsnP', k: 'localAsn', l: 'Local-AS Number', ph: 'optional' },
      { k: 'ttl', l: 'EBGP Multihop TTL' }, { k: 'weight', l: 'Weight for routes from this neighbor' },
      { k: 'password', l: 'Password', t: 'password', help: 'leer lassen = unverändert' },
      { k: 'peerCtrl', l: 'Peer Controls', t: 'checks', o: [['bfd', 'Bidirectional Forwarding Detection'], ['dis-conn-check', 'Disable Connected Check']] },
      { k: 'ctrl', l: 'BGP Controls', t: 'checks', o: [['allow-self-as', 'Allow Self AS'], ['as-override', 'AS override'], ['dis-peer-as-check', 'Disable Peer AS Check'], ['nh-self', 'Next-hop Self'], ['send-com', 'Send Community']] }],
    cols: [col('Peer IP', r => r.addr), col('Remote AS', r => relOf(r.dn, 'bgpAsP', 'asn')), col('TTL', r => r.ttl)],
  },
  bgpAsP: { label: 'Autonomous System', fields: [{ k: 'asn', l: 'ASN' }], cols: [col('ASN', r => r.asn)] },
  l3extInstP: {
    label: 'External EPG',
    fields: [NAME, ALIAS, { k: 'prefGrMemb', l: 'Preferred Group Member', t: 'radio', o: [['exclude', 'Exclude'], ['include', 'Include']] }, DESCR],
    wizard: {
      title: 'Create External EPG',
      steps: [{ l: 'External EPG', fields: [NAME, DESCR, { k: '_s', l: 'Subnets', t: 'rows', start: true, cols: [{ k: 'ip', l: 'IP Address', ph: '0.0.0.0/0', req: true },
        { k: 'scope', l: 'Scope', t: 'select', o: [['import-security', 'External Subnets for External EPG'], ['import-security,export-rtctrl', 'External Subnets + Export Route Control'], ['export-rtctrl', 'Export Route Control Subnet'], ['shared-rtctrl,shared-security,import-security', 'Shared (Route Control + Security)']], def: 'import-security' }] }] }],
      build: (v, parent) => ({ dn: parent + '/instP-' + v.name, body: mo('l3extInstP', { name: v.name, descr: v.descr }, (v._s || []).map(s => mo('l3extSubnet', { ip: s.ip, scope: s.scope }))) }),
    },
    cols: [ac('name'), col('Subnets', r => MIT.kids(r.dn, ['l3extSubnet']).map(d => MIT.a(d).ip).join(', ')), col('pcTag', r => r.pcTag)],
    info: r => [['pcTag (sclass)', r.pcTag]], summary: true,
    actions: [['Add Provided Contract', dn => createDialog(dn, 'fvRsProv')], ['Add Consumed Contract', dn => createDialog(dn, 'fvRsCons')], ['Add Consumed Contract Interface', dn => createDialog(dn, 'fvRsConsIf')]],
  },
  l3extSubnet: {
    label: 'Subnet',
    fields: [{ k: 'ip', l: 'IP Address', create: true, req: true, ph: '0.0.0.0/0' },
      { k: 'scope', l: 'Scope', t: 'checks', o: [['export-rtctrl', 'Export Route Control Subnet'], ['import-rtctrl', 'Import Route Control Subnet'], ['import-security', 'External Subnets for External EPG'], ['shared-rtctrl', 'Shared Route Control Subnet'], ['shared-security', 'Shared Security Import Subnet']] },
      { k: 'aggregate', l: 'Aggregate', t: 'checks', o: [['export-rtctrl', 'Aggregate Export'], ['import-rtctrl', 'Aggregate Import'], ['shared-rtctrl', 'Aggregate Shared Routes']] },
      relDn('l3extRsSubnetToRtSumm', 'Route Summarization Policy', ['ospfRtSummPol', 'bgpRtSummPol', 'eigrpRtSummPol'], { tenantScope: true, help: 'nur zusammen mit Export Route Control Subnet' })],
    cols: [col('IP Address', r => r.ip), col('Scope', r => r.scope), col('Aggregate', r => r.aggregate)],
  },

  /* ---------------- mgmt ---------------- */
  mgmtOoB: { label: 'Out-of-Band EPG', fields: [NAME, DESCR], cols: [ac('name')] },
  mgmtRsOoBStNode: {
    label: 'Static Node Management Address',
    fields: [{ k: 'tDn', l: 'Node', t: 'node', role: ['leaf', 'spine', 'controller'], create: true, req: true }, { k: 'addr', l: 'IPv4 Address', ph: '192.168.10.101/24', req: true }, { k: 'gw', l: 'IPv4 Gateway', ph: '192.168.10.1' }],
    cols: [col('Node', r => pathLabel(r.tDn)), col('IPv4 Address', r => r.addr), col('IPv4 Gateway', r => r.gw), col('State', relState)],
  },

  /* ---------------- Access Policies ---------------- */
  fvnsVlanInstP: {
    label: 'VLAN Pool',
    fields: [NAME, ALIAS, { k: 'allocMode', l: 'Allocation Mode', t: 'radio', o: [['dynamic', 'Dynamic Allocation'], ['static', 'Static Allocation']], create: true, def: 'static' }, DESCR],
    wizard: {
      title: 'Create VLAN Pool',
      steps: [{ l: 'VLAN Pool', fields: [NAME, DESCR, { k: 'allocMode', l: 'Allocation Mode', t: 'radio', o: [['dynamic', 'Dynamic Allocation'], ['static', 'Static Allocation']], def: 'static' },
        { k: '_b', l: 'Encap Blocks', t: 'rows', start: true, cols: [{ k: 'from', l: 'From VLAN', ph: '100', req: true, w: '90px' }, { k: 'to', l: 'To VLAN', ph: '199', w: '90px' },
          { k: 'allocMode', l: 'Allocation Mode', t: 'select', o: [['inherit', 'Inherit allocMode from parent'], ['static', 'Static Allocation'], ['dynamic', 'Dynamic Allocation']], def: 'inherit' },
          { k: 'role', l: 'Role', t: 'select', o: [['external', 'External or On the wire encapsulations'], ['internal', 'Internal']], def: 'external' }] }] }],
      build: (v, parent) => ({
        dn: parent + '/vlanns-[' + v.name + ']-' + v.allocMode,
        body: mo('fvnsVlanInstP', { name: v.name, descr: v.descr, allocMode: v.allocMode }, (v._b || []).map(b => mo('fvnsEncapBlk', { from: vlanify(b.from.replace(/^vlan-/, '')), to: vlanify((b.to || b.from).replace(/^vlan-/, '')), allocMode: b.allocMode, role: b.role }))),
      }),
    },
    cols: [ac('name'), col('Allocation Mode', r => r.allocMode), col('Encap Blocks', r => MIT.kids(r.dn, ['fvnsEncapBlk']).map(d => '[' + MIT.a(d).from + '-' + MIT.a(d).to + ']').join(', ')), ac('descr')],
  },
  fvnsEncapBlk: {
    label: 'Encap Block',
    fields: [{ k: 'from', l: 'Range From', create: true, req: true, ph: 'vlan-100' }, { k: 'to', l: 'Range To', create: true, req: true, ph: 'vlan-199' },
      { k: 'allocMode', l: 'Allocation Mode', t: 'radio', o: [['dynamic', 'Dynamic Allocation'], ['inherit', 'Inherit allocMode from parent'], ['static', 'Static Allocation']] },
      { k: 'role', l: 'Role', t: 'radio', o: [['external', 'External or On the wire encapsulations'], ['internal', 'Internal']] }, DESCR],
    normalize: v => { ['from', 'to'].forEach(k => { v[k] = vlanify(v[k]); }); return v; },
    cols: [col('VLAN Range', r => '[' + r.from + '-' + r.to + ']'), col('Allocation Mode', r => r.allocMode), col('Role', r => r.role)],
  },
  physDomP: {
    label: 'Physical Domain',
    fields: [NAME, relDn('infraRsVlanNs', 'VLAN Pool', 'fvnsVlanInstP')],
    cols: [ac('name'), col('VLAN Pool', r => nameOfDn(relOf(r.dn, 'infraRsVlanNs', 'tDn')))],
  },
  l3extDomP: {
    label: 'L3 Domain',
    fields: [NAME, relDn('infraRsVlanNs', 'VLAN Pool', 'fvnsVlanInstP')],
    cols: [ac('name'), col('VLAN Pool', r => nameOfDn(relOf(r.dn, 'infraRsVlanNs', 'tDn')))],
  },
  infraAttEntityP: {
    label: 'Attachable Access Entity Profile',
    fields: [NAME, DESCR],
    wizard: {
      title: 'Create Attachable Access Entity Profile',
      steps: [{ l: 'Profile', fields: [NAME, DESCR, { k: '_d', l: 'Domains (VMM, Physical or External) To Be Associated To Interfaces', t: 'rows', start: true, cols: [{ k: 'tDn', l: 'Domain Profile', t: 'tdn', target: ['physDomP', 'vmmDomP', 'l2extDomP', 'l3extDomP'] }] }] }],
      build: (v, parent) => ({ dn: parent + '/attentp-' + v.name, body: mo('infraAttEntityP', { name: v.name, descr: v.descr }, (v._d || []).map(d => mo('infraRsDomP', { tDn: d.tDn }))) }),
    },
    cols: [ac('name'), col('Domains', r => MIT.kids(r.dn, ['infraRsDomP']).map(d => nameOfDn(MIT.a(d).tDn)).join(', ')), ac('descr')],
  },
  infraRsDomP: { label: 'Domain', fields: [{ k: 'tDn', l: 'Domain Profile', t: 'tdn', target: ['physDomP', 'vmmDomP', 'l2extDomP', 'l3extDomP'], create: true, req: true }], cols: [col('Domain Profile', r => r.tDn), col('State', relState)] },
  infraAccPortGrp: {
    label: 'Leaf Access Port Policy Group',
    fields: [NAME, DESCR,
      relName('infraRsHIfPol', 'tnFabricHIfPolName', 'Link Level Policy', 'fabricHIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsCdpIfPol', 'tnCdpIfPolName', 'CDP Policy', 'cdpIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsLldpIfPol', 'tnLldpIfPolName', 'LLDP Policy', 'lldpIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsMcpIfPol', 'tnMcpIfPolName', 'MCP Policy', 'mcpIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsStpIfPol', 'tnStpIfPolName', 'Spanning Tree Interface Policy', 'stpIfPol', { scope: 'infra', empty: 'default' }),
      relDn('infraRsAttEntP', 'Attached Entity Profile', 'infraAttEntityP')],
    cols: [ac('name'), col('AAEP', r => nameOfDn(relOf(r.dn, 'infraRsAttEntP', 'tDn'))), col('LLDP', r => relOf(r.dn, 'infraRsLldpIfPol', 'tnLldpIfPolName') || 'default'), col('CDP', r => relOf(r.dn, 'infraRsCdpIfPol', 'tnCdpIfPolName') || 'default')],
  },
  infraAccBndlGrp: {
    label: 'PC/VPC Interface Policy Group',
    fields: [NAME, DESCR, { k: 'lagT', l: 'Link Aggregation Type', t: 'radio', o: [['link', 'Port Channel'], ['node', 'Virtual Port Channel']], create: true },
      relName('infraRsHIfPol', 'tnFabricHIfPolName', 'Link Level Policy', 'fabricHIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsCdpIfPol', 'tnCdpIfPolName', 'CDP Policy', 'cdpIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsLldpIfPol', 'tnLldpIfPolName', 'LLDP Policy', 'lldpIfPol', { scope: 'infra', empty: 'default' }),
      relName('infraRsLacpPol', 'tnLacpLagPolName', 'Port Channel Policy', 'lacpLagPol', { scope: 'infra', empty: 'default' }),
      relDn('infraRsAttEntP', 'Attached Entity Profile', 'infraAttEntityP')],
    cols: [ac('name'), col('AAEP', r => nameOfDn(relOf(r.dn, 'infraRsAttEntP', 'tDn'))), col('Port Channel Policy', r => relOf(r.dn, 'infraRsLacpPol', 'tnLacpLagPolName') || 'default')],
  },
  infraAccPortP: {
    label: 'Leaf Interface Profile',
    fields: [NAME, DESCR],
    wizard: {
      title: 'Create Leaf Interface Profile',
      steps: [{ l: 'Profile', fields: [NAME, DESCR, { k: '_s', l: 'Interface Selectors', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'Server-1-10', req: true },
        { k: 'ports', l: 'Interface IDs', ph: '1/1-10', req: true, w: '110px' }, { k: 'pg', l: 'Interface Policy Group', t: 'tdn', target: ['infraAccPortGrp', 'infraAccBndlGrp'], empty: '— keine —' }] }] }],
      build: (v, parent) => ({ dn: parent + '/accportprof-' + v.name, body: mo('infraAccPortP', { name: v.name, descr: v.descr }, (v._s || []).map(s => hportsBody(s.name, s.ports, s.pg))) }),
    },
    cols: [ac('name'), col('Interface Selectors', r => MIT.kids(r.dn, ['infraHPortS']).map(d => MIT.a(d).name).join(', ')), ac('descr')],
  },
  infraHPortS: {
    label: 'Access Port Selector',
    fields: [NAME, DESCR, relDn('infraRsAccBaseGrp', 'Interface Policy Group', ['infraAccPortGrp', 'infraAccBndlGrp'])],
    wizard: {
      title: 'Create Access Port Selector',
      steps: [{ l: 'Selector', fields: [NAME, DESCR, { k: '_ports', l: 'Interface IDs', req: true, ph: '1/1-10 oder 1/1,1/3' },
        { k: '_pg', l: 'Interface Policy Group', t: 'tdn', target: ['infraAccPortGrp', 'infraAccBndlGrp'], empty: '— keine —' }] }],
      build: (v, parent) => ({ dn: parent + '/hports-' + v.name + '-typ-range', body: hportsBody(v.name, v._ports, v._pg) }),
    },
    cols: [ac('name'), col('Port Blocks', r => MIT.kids(r.dn, ['infraPortBlk']).map(d => { const a = MIT.a(d); return '1/' + a.fromPort + (a.toPort !== a.fromPort ? '-1/' + a.toPort : ''); }).join(', ')),
      col('Policy Group', r => nameOfDn(relOf(r.dn, 'infraRsAccBaseGrp', 'tDn')))],
  },
  infraPortBlk: {
    label: 'Port Block',
    fields: [NAME, { k: 'fromCard', l: 'From Card' }, { k: 'fromPort', l: 'From Port' }, { k: 'toCard', l: 'To Card' }, { k: 'toPort', l: 'To Port' }, DESCR],
    cols: [ac('name'), col('From', r => r.fromCard + '/' + r.fromPort), col('To', r => r.toCard + '/' + r.toPort)],
  },
  infraNodeP: {
    label: 'Leaf Profile',
    fields: [NAME, DESCR],
    wizard: {
      title: 'Create Leaf Profile',
      steps: [
        { l: 'Profile', fields: [NAME, DESCR, { k: '_sel', l: 'Leaf Selectors', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'Leaf101', req: true }, { k: 'from', l: 'From Node', ph: '101', req: true, w: '80px' }, { k: 'to', l: 'To Node', ph: '101', w: '80px' }] }] },
        { l: 'Associations', fields: [{ k: '_ifp', l: 'Interface Selector Profiles', t: 'tdnmulti', target: ['infraAccPortP'], none: 'Noch keine Leaf Interface Profiles' }] },
      ],
      build: (v, parent) => ({ dn: parent + '/nprof-' + v.name, body: mo('infraNodeP', { name: v.name, descr: v.descr }, (v._sel || []).map(s => leafSelBody(s.name, s.from, s.to)), (v._ifp || []).map(d => mo('infraRsAccPortP', { tDn: d }))) }),
    },
    cols: [ac('name'), col('Leaf Selectors', r => MIT.kids(r.dn, ['infraLeafS']).map(d => MIT.a(d).name + ' (' + MIT.kids(d, ['infraNodeBlk']).map(n => MIT.a(n).from_ + '-' + MIT.a(n).to_).join(',') + ')').join(', ')),
      col('Interface Profiles', r => MIT.kids(r.dn, ['infraRsAccPortP']).map(d => nameOfDn(MIT.a(d).tDn)).join(', '))],
  },
  infraLeafS: {
    label: 'Leaf Selector',
    fields: [NAME, DESCR],
    wizard: { title: 'Create Leaf Selector', steps: [{ l: 'Selector', fields: [NAME, { k: '_from', l: 'From Node', req: true, ph: '101' }, { k: '_to', l: 'To Node', ph: '101' }] }],
      build: (v, parent) => ({ dn: parent + '/leaves-' + v.name + '-typ-range', body: leafSelBody(v.name, v._from, v._to) }) },
    cols: [ac('name'), col('Node Blocks', r => MIT.kids(r.dn, ['infraNodeBlk']).map(n => MIT.a(n).from_ + '-' + MIT.a(n).to_).join(', '))],
  },
  infraNodeBlk: { label: 'Node Block', fields: [NAME, { k: 'from_', l: 'From' }, { k: 'to_', l: 'To' }], cols: [ac('name'), col('From', r => r.from_), col('To', r => r.to_)] },
  infraRsAccPortP: { label: 'Interface Selector Profile', fields: [{ k: 'tDn', l: 'Interface Profile', t: 'tdn', target: ['infraAccPortP'], create: true, req: true }], cols: [col('Interface Profile', r => nameOfDn(r.tDn)), col('State', relState)] },
  cdpIfPol: { label: 'CDP Interface Policy', fields: [NAME, DESCR, { k: 'adminSt', l: 'Admin State', t: 'radio', o: [['disabled', 'Disabled'], ['enabled', 'Enabled']] }], cols: [ac('name'), col('Admin State', r => r.adminSt)] },
  lldpIfPol: { label: 'LLDP Interface Policy', fields: [NAME, DESCR, { k: 'adminRxSt', l: 'Receive State', t: 'radio', o: [['disabled', 'Disabled'], ['enabled', 'Enabled']] }, { k: 'adminTxSt', l: 'Transmit State', t: 'radio', o: [['disabled', 'Disabled'], ['enabled', 'Enabled']] }], cols: [ac('name'), col('Receive State', r => r.adminRxSt), col('Transmit State', r => r.adminTxSt)] },
  lacpLagPol: {
    label: 'Port Channel Policy',
    fields: [NAME, DESCR, { k: 'mode', l: 'Mode', t: 'select', o: [['off', 'Static Channel - Mode On'], ['active', 'LACP Active'], ['passive', 'LACP Passive'], ['mac-pin', 'MAC Pinning'], ['mac-pin-nicload', 'MAC Pinning-Physical-NIC-load'], ['explicit-failover', 'Use Explicit Failover Order']] },
      { k: 'ctrl', l: 'Control', t: 'checks', o: [['fast-sel-hot-stdby', 'Fast Select Hot Standby Ports'], ['graceful-conv', 'Graceful Convergence'], ['susp-individual', 'Suspend Individual Port'], ['load-defer', 'Load Defer Member Ports'], ['symmetric-hash', 'Symmetric Hashing']] },
      { k: 'minLinks', l: 'Minimum Number of Links' }, { k: 'maxLinks', l: 'Maximum Number of Links' }],
    cols: [ac('name'), col('Mode', r => r.mode), col('Control', r => r.ctrl)],
  },
  fabricHIfPol: { label: 'Link Level Policy', fields: [NAME, DESCR, { k: 'autoNeg', l: 'Auto Negotiation', t: 'radio', o: [['off', 'off'], ['on', 'on']] }, { k: 'speed', l: 'Speed', t: 'select', o: ['inherit', '100M', '1G', '10G', '25G', '40G', '100G'].map(x => [x, x]) }, { k: 'fecMode', l: 'Forwarding Error Correction (FEC)', t: 'select', o: [['inherit', 'Inherit']] }], cols: [ac('name'), col('Speed', r => r.speed), col('Auto Negotiation', r => r.autoNeg)] },
  mcpIfPol: { label: 'MCP Interface Policy', fields: [NAME, DESCR, { k: 'adminSt', l: 'Admin State', t: 'radio', o: [['disabled', 'Disabled'], ['enabled', 'Enabled']], def: 'enabled' }], cols: [ac('name'), col('Admin State', r => r.adminSt)] },
  stpIfPol: { label: 'Spanning Tree Interface Policy', fields: [NAME, DESCR, { k: 'ctrl', l: 'Interface Controls', t: 'checks', o: [['bpdu-filter', 'BPDU filter enabled'], ['bpdu-guard', 'BPDU Guard enabled']] }], cols: [ac('name'), col('Interface Controls', r => r.ctrl)] },
  fabricProtPol: { label: 'VPC Explicit Protection Groups', fields: [{ k: 'pairT', l: 'Pairing Type', t: 'radio', o: [['explicit', 'Explicit']], ro: true }], cols: [] },
  fabricExplicitGEp: {
    label: 'VPC Explicit Protection Group',
    fields: [NAME, { k: 'id', l: 'ID', create: true, req: true, ph: '10' }],
    wizard: {
      title: 'Create VPC Explicit Protection Group',
      steps: [{ l: 'Protection Group', fields: [NAME, { k: 'id', l: 'ID', req: true, ph: '10' }, { k: '_a', l: 'Switch 1', t: 'node', ids: true, req: true }, { k: '_b', l: 'Switch 2', t: 'node', ids: true, req: true }] }],
      build: (v, parent) => ({ dn: parent + '/expgep-' + v.name, body: mo('fabricExplicitGEp', { name: v.name, id: v.id }, [v._a, v._b].filter(Boolean).map(id => mo('fabricNodePEp', { id }))) }),
    },
    cols: [ac('name'), col('ID', r => r.id), col('Switches', r => MIT.kids(r.dn, ['fabricNodePEp']).map(d => MIT.a(d).id).join(', '))],
  },
  fabricNodePEp: { label: 'vPC Node', fields: [{ k: 'id', l: 'Node ID', create: true, req: true }], cols: [col('Node ID', r => r.id)] },

  /* ---------------- Fabric Policies ---------------- */
  fabricPodPGrp: { label: 'Pod Policy Group', fields: [NAME, DESCR, relName('fabricRsTimePol', 'tnDatetimePolName', 'Date Time Policy', 'datetimePol', { scope: 'fabric', empty: 'default', keepEmpty: true })], cols: [ac('name'), col('Date Time Policy', r => relOf(r.dn, 'fabricRsTimePol', 'tnDatetimePolName') || 'default')] },
  fabricPodP: { label: 'Pod Profile', fields: [NAME, DESCR], cols: [ac('name')] },
  fabricPodS: { label: 'Pod Selector', fields: [NAME, { k: 'type', l: 'Type', t: 'radio', o: [['ALL', 'ALL'], ['range', 'Range']], create: true, def: 'ALL' }, relDn('fabricRsPodPGrp', 'Fabric Policy Group', 'fabricPodPGrp')], cols: [ac('name'), col('Type', r => r.type), col('Policy Group', r => nameOfDn(relOf(r.dn, 'fabricRsPodPGrp', 'tDn')))] },
  datetimePol: {
    label: 'Date and Time Policy',
    fields: [NAME, DESCR, { k: 'adminSt', l: 'Administrative State', t: 'radio', o: [['disabled', 'disabled'], ['enabled', 'enabled']] }, { k: 'authSt', l: 'Authentication State', t: 'radio', o: [['disabled', 'disabled'], ['enabled', 'enabled']] },
      { k: 'serverState', l: 'Server State', t: 'radio', o: [['disabled', 'Disabled'], ['enabled', 'Enabled']] }],
    cols: [ac('name'), col('Admin State', r => r.adminSt), col('NTP Servers', r => MIT.kids(r.dn, ['datetimeNtpProv']).map(d => MIT.a(d).name).join(', '))],
  },
  datetimeNtpProv: {
    label: 'NTP Server',
    fields: [{ k: 'name', l: 'Name (Hostname/IP)', create: true, req: true, ph: '192.168.10.250' }, DESCR, { k: 'preferred', l: 'Preferred', t: 'yesno' },
      { k: 'minPoll', l: 'Minimum Polling Interval' }, { k: 'maxPoll', l: 'Maximum Polling Interval' },
      relDn('datetimeRsNtpProvToEpg', 'Management EPG', 'mgmtOoB', { empty: '— keine —' })],
    cols: [col('Host Name/IP Address', r => r.name), col('Preferred', r => r.preferred), col('Min/Max Poll', r => r.minPoll + '/' + r.maxPoll), col('Management EPG', r => nameOfDn(relOf(r.dn, 'datetimeRsNtpProvToEpg', 'tDn')))],
  },
  bgpRRNodePEp: { label: 'Route Reflector Node', fields: [{ k: 'id', l: 'Spine Node', t: 'node', role: 'spine', ids: true, create: true, req: true }], cols: [col('Node ID', r => r.id), col('Pod ID', r => r.podId)] },
  fabricNodeIdentP: {
    label: 'Fabric Node Member',
    fields: [{ k: 'serial', l: 'Serial Number', create: true, req: true }, { k: 'podId', l: 'Pod ID' }, { k: 'nodeId', l: 'Node ID', create: true, req: true, ph: '101' },
      { k: 'name', l: 'Node Name', req: true, ph: 'leaf101' }],
    cols: [col('Serial', r => r.serial), col('Node ID', r => r.nodeId), col('Name', r => r.name), col('Pod', r => r.podId)],
  },
  aaaAuthRealm: { label: 'AAA Policy', fields: [{ k: 'defRolePolicy', l: 'Remote user login policy', t: 'radio', o: [['no-login', 'No Login'], ['assign-default-role', 'Assign Default Role']],
    help: 'Was passiert, wenn der AAA-Server kein gültiges Cisco AV-Pair liefert' }], cols: [col('Remote User Login Policy', r => r.defRolePolicy)] },
  aaaDefaultAuth: { label: 'Default Authentication', fields: [{ k: 'realm', l: 'Realm', t: 'select', o: [['local', 'Local'], ['tacacs', 'TACACS+'], ['radius', 'RADIUS'], ['ldap', 'LDAP']] },
    { k: 'providerGroup', l: 'Provider Group', show: v => v.realm !== 'local' },
    { k: 'fallbackCheck', l: 'Fallback Check', t: 'select', o: [['false', 'False (bei Ausfall lokal anmelden)'], ['true', 'True']], show: v => v.realm !== 'local' }],
    cols: [col('Realm', r => r.realm), col('Provider Group', r => r.providerGroup), col('Fallback Check', r => r.fallbackCheck)] },
  aaaConsoleAuth: { label: 'Console Authentication', fields: [{ k: 'realm', l: 'Realm', t: 'select', o: [['local', 'Local'], ['tacacs', 'TACACS+'], ['radius', 'RADIUS'], ['ldap', 'LDAP']] },
    { k: 'providerGroup', l: 'Provider Group', show: v => v.realm !== 'local' }], cols: [col('Realm', r => r.realm)] },
  aaaLoginDomain: {
    label: 'Login Domain', fields: [NAME, DESCR],
    wizard: { title: 'Create Login Domain', steps: [{ l: 'Login Domain', fields: [NAME, DESCR, { k: '_realm', l: 'Realm', t: 'select', o: [['local', 'Local'], ['tacacs', 'TACACS+'], ['radius', 'RADIUS'], ['ldap', 'LDAP']], def: 'tacacs' },
      { k: '_grp', l: 'Provider Group', ph: 'ISE', show: v => v._realm !== 'local' }] }],
      build: (v, parent) => ({ dn: parent + '/logindomain-' + v.name, body: mo('aaaLoginDomain', { name: v.name, descr: v.descr }, mo('aaaDomainAuth', { realm: v._realm, providerGroup: v._realm === 'local' ? '' : v._grp })) }) },
    cols: [ac('name'), col('Realm', r => (MIT.a(r.dn + '/domainauth') || {}).realm), col('Provider Group', r => (MIT.a(r.dn + '/domainauth') || {}).providerGroup), ac('descr')],
  },
  aaaDomainAuth: { label: 'Domain Authentication', fields: [{ k: 'realm', l: 'Realm', t: 'select', o: [['local', 'Local'], ['tacacs', 'TACACS+'], ['radius', 'RADIUS'], ['ldap', 'LDAP']] }, { k: 'providerGroup', l: 'Provider Group' }],
    cols: [col('Realm', r => r.realm), col('Provider Group', r => r.providerGroup)] },
  aaaDomain: { label: 'Security Domain', fields: [NAME, { k: 'restrictedRbacDomain', l: 'Restricted Domain', t: 'yesno' }, DESCR], cols: [ac('name'), ac('descr')] },
  aaaDomainRef: { label: 'Security Domain', fields: [{ k: 'name', l: 'Security Domain', t: 'tname', target: 'aaaDomain', scope: 'aaa', create: true, req: true }], cols: [col('Security Domain', r => r.name)] },
  aaaUserDomain: { label: 'User Security Domain', fields: [{ k: 'name', l: 'Security Domain', t: 'tname', target: 'aaaDomain', scope: 'aaa', create: true, req: true }],
    cols: [col('Domain', r => r.name), col('Roles', r => MIT.kids(r.dn, ['aaaUserRole']).map(d => MIT.a(d).name + (MIT.a(d).privType === 'writePriv' ? ' (write)' : ' (read)')).join(', '))] },
  aaaUserRole: { label: 'Role', fields: [{ k: 'name', l: 'Role', t: 'select', o: AAA_ROLES.map(r => [r, r]), create: true, req: true },
    { k: 'privType', l: 'Privilege Type', t: 'radio', o: [['readPriv', 'Read'], ['writePriv', 'Write']] }], cols: [col('Role', r => r.name), col('Privilege', r => r.privType)] },
  aaaTacacsPlusProvider: { label: 'TACACS+ Provider', fields: [{ k: 'name', l: 'Host Name (or IP Address)', create: true, req: true, ph: '192.168.10.40' },
    { k: 'key', l: 'Key', t: 'password', help: 'leer lassen = unverändert' }, { k: 'port', l: 'Port' }, { k: 'authProtocol', l: 'Authorization Protocol', t: 'select', o: [['pap', 'PAP'], ['chap', 'CHAP'], ['mschap', 'MS-CHAP']] },
    { k: 'timeout', l: 'Timeout (sec)' }, { k: 'retries', l: 'Retries' }, relDn('aaaRsSecProvToEpg', 'Management EPG', ['mgmtOoB', 'mgmtInB'], { empty: 'default (Out-of-Band)' })],
    cols: [ac('name'), col('Port', r => r.port), col('Protocol', r => r.authProtocol), col('Management EPG', r => nameOfDn(relOf(r.dn, 'aaaRsSecProvToEpg', 'tDn')) || 'default (OOB)')] },
  aaaRadiusProvider: { label: 'RADIUS Provider', fields: [{ k: 'name', l: 'Host Name (or IP Address)', create: true, req: true, ph: '192.168.10.41' },
    { k: 'key', l: 'Key', t: 'password', help: 'leer lassen = unverändert' }, { k: 'authPort', l: 'Authorization Port' }, { k: 'authProtocol', l: 'Authorization Protocol', t: 'select', o: [['pap', 'PAP'], ['chap', 'CHAP'], ['mschap', 'MS-CHAP']] },
    { k: 'timeout', l: 'Timeout (sec)' }, { k: 'retries', l: 'Retries' }, relDn('aaaRsSecProvToEpg', 'Management EPG', ['mgmtOoB', 'mgmtInB'], { empty: 'default (Out-of-Band)' })],
    cols: [ac('name'), col('Port', r => r.authPort), col('Management EPG', r => nameOfDn(relOf(r.dn, 'aaaRsSecProvToEpg', 'tDn')) || 'default (OOB)')] },
  aaaLdapProvider: { label: 'LDAP Provider', fields: [{ k: 'name', l: 'Host Name (or IP Address)', create: true, req: true, ph: '192.168.10.42' },
    { k: 'rootdn', l: 'Bind DN', ph: 'cn=apic,ou=svc,dc=lab,dc=local' }, { k: 'basedn', l: 'Base DN', ph: 'ou=users,dc=lab,dc=local' }, { k: 'key', l: 'Password', t: 'password', help: 'leer lassen = unverändert' },
    { k: 'port', l: 'Port' }, { k: 'attribute', l: 'Attribute', ph: 'CiscoAVPair' }, { k: 'filter', l: 'Filter', ph: 'cn=$userid' }, relDn('aaaRsSecProvToEpg', 'Management EPG', ['mgmtOoB', 'mgmtInB'], { empty: 'default (Out-of-Band)' })],
    cols: [ac('name'), col('Base DN', r => r.basedn), col('Attribute', r => r.attribute)] },
  aaaTacacsPlusProviderGroup: { label: 'TACACS+ Provider Group', fields: [NAME, DESCR], cols: [ac('name'), col('Providers', r => MIT.kids(r.dn, ['aaaProviderRef']).map(d => MIT.a(d).name).join(', '))] },
  aaaRadiusProviderGroup: { label: 'RADIUS Provider Group', fields: [NAME, DESCR], cols: [ac('name'), col('Providers', r => MIT.kids(r.dn, ['aaaProviderRef']).map(d => MIT.a(d).name).join(', '))] },
  aaaLdapProviderGroup: { label: 'LDAP Provider Group', fields: [NAME, DESCR], cols: [ac('name'), col('Providers', r => MIT.kids(r.dn, ['aaaProviderRef']).map(d => MIT.a(d).name).join(', '))] },
  aaaProviderRef: { label: 'Provider', fields: [{ k: 'name', l: 'Name (Provider)', create: true, req: true, ph: '192.168.10.40' }, { k: 'order', l: 'Priority' }], cols: [col('Provider', r => r.name), col('Priority', r => r.order)] },
  mgmtInB: {
    label: 'In-Band EPG', menu: 'Create In-Band Management EPG',
    fields: [NAME, { k: 'encap', l: 'Encap', ph: 'vlan-90', req: true }, relName('mgmtRsMgmtBD', 'tnFvBDName', 'Bridge Domain', 'fvBD', { req: true })],
    normalize: v => { v.encap = vlanify(v.encap); return v; },
    wizard: { title: 'Create In-Band Management EPG', steps: [{ l: 'In-Band EPG', fields: [NAME, { k: 'encap', l: 'Encap', ph: 'vlan-90', req: true },
      relName('mgmtRsMgmtBD', 'tnFvBDName', 'Bridge Domain', 'fvBD', { req: true, def: 'inb' }),
      { k: '_n', l: 'Static Node Addresses', t: 'rows', start: true, cols: [{ k: 'tDn', l: 'Node', t: 'node', role: ['leaf', 'spine', 'controller'] }, { k: 'addr', l: 'IPv4 Address', ph: '10.90.0.101/24' }, { k: 'gw', l: 'Gateway', ph: '10.90.0.1' }] }] }],
      build: (v, parent) => ({ dn: parent + '/inb-' + v.name, body: mo('mgmtInB', { name: v.name, encap: vlanify(v.encap) }, mo('mgmtRsMgmtBD', { tnFvBDName: v['mgmtRsMgmtBD.tnFvBDName'] }),
        (v._n || []).filter(n => n.tDn).map(n => mo('mgmtRsInBStNode', { tDn: n.tDn, addr: n.addr, gw: n.gw }))) }) },
    cols: [ac('name'), col('Encap', r => r.encap), col('BD', r => relOf(r.dn, 'mgmtRsMgmtBD', 'tnFvBDName'))], oper: ['inb'],
  },
  mgmtRsInBStNode: { label: 'Static In-Band Address', fields: [{ k: 'tDn', l: 'Node', t: 'node', role: ['leaf', 'spine', 'controller'], create: true, req: true },
    { k: 'addr', l: 'IPv4 Address', req: true }, { k: 'gw', l: 'IPv4 Gateway', req: true }],
    cols: [col('Node', r => pathLabel(r.tDn)), col('Address', r => r.addr), col('Gateway', r => r.gw)] },
  fvESg: {
    label: 'Endpoint Security Group', menu: 'Create Endpoint Security Group',
    fields: [NAME, relName('fvRsScope', 'tnFvCtxName', 'VRF', 'fvCtx', { req: true }), { k: 'pcEnfPref', l: 'Intra ESG Isolation', t: 'radio', o: [['unenforced', 'Unenforced'], ['enforced', 'Enforced']] },
      { k: 'shutdown', l: 'Shutdown', t: 'yesno' }, DESCR],
    wizard: { title: 'Create Endpoint Security Group', steps: [{ l: 'Identity', fields: [NAME, relName('fvRsScope', 'tnFvCtxName', 'VRF', 'fvCtx', { req: true }), DESCR] },
      { l: 'Selectors', fields: [{ k: '_epgs', l: 'EPG Selectors', t: 'rows', cols: [{ k: 'tDn', l: 'EPG', t: 'tdn', target: ['fvAEPg'], tenantScope: true }] },
        { k: '_ips', l: 'IP Subnet Selectors', t: 'rows', cols: [{ k: 'ip', l: 'IP oder Subnetz', ph: '10.10.10.0/28' }] }] }],
      build: (v, parent) => ({ dn: parent + '/esg-' + v.name, body: mo('fvESg', { name: v.name, descr: v.descr }, mo('fvRsScope', { tnFvCtxName: v['fvRsScope.tnFvCtxName'] }),
        (v._epgs || []).filter(e => e.tDn).map(e => mo('fvEPgSelector', { matchEpgDn: e.tDn })),
        (v._ips || []).filter(e => e.ip).map(e => mo('fvEPSelector', { matchExpression: "ip=='" + e.ip + "'" }))) }) },
    cols: [ac('name'), col('VRF', r => relOf(r.dn, 'fvRsScope', 'tnFvCtxName')), col('pcTag', r => r.pcTag),
      col('Selectors', r => MIT.kids(r.dn, ['fvEPgSelector']).map(d => nameOfDn(MIT.a(d).matchEpgDn)).concat(MIT.kids(r.dn, ['fvEPSelector']).map(d => MIT.a(d).matchExpression)).join(', '))],
    summary: true, oper: ['endpoints', 'contracts'],
    actions: [['Add Provided Contract', dn => createDialog(dn, 'fvRsProv')], ['Add Consumed Contract', dn => createDialog(dn, 'fvRsCons')]],
  },
  fvEPgSelector: { label: 'EPG Selector', fields: [{ k: 'matchEpgDn', l: 'EPG', t: 'tdn', target: ['fvAEPg'], tenantScope: true, create: true, req: true }, DESCR],
    cols: [col('EPG', r => r.matchEpgDn.replace(/^uni\//, ''))] },
  fvEPSelector: { label: 'IP Subnet Selector', fields: [{ k: 'matchExpression', l: 'Match Expression', create: true, req: true, ph: "ip=='10.10.10.0/28'" }, DESCR],
    cols: [col('Match Expression', r => r.matchExpression)] },
  fvCrtrn: { label: 'uSeg Attributes', fields: [{ k: 'match', l: 'Match', t: 'radio', o: [['any', 'Match Any'], ['all', 'Match All']] }], cols: [col('Match', r => r.match)] },
  fvIpAttr: { label: 'IP Attribute', fields: [NAME, { k: 'ip', l: 'IP Address oder Subnetz', req: true, ph: '10.10.10.50' }], cols: [ac('name'), col('IP', r => r.ip)] },
  fvMacAttr: { label: 'MAC Attribute', fields: [NAME, { k: 'mac', l: 'MAC Address', req: true }], cols: [ac('name'), col('MAC', r => r.mac)] },
  aaaUser: {
    label: 'Local User',
    fields: [{ k: 'name', l: 'Login ID', create: true, req: true }, { k: 'pwd', l: 'Password', t: 'password', help: 'leer lassen = unverändert' },
      { k: 'firstName', l: 'First Name' }, { k: 'lastName', l: 'Last Name' }, { k: 'email', l: 'Email' },
      { k: 'accountStatus', l: 'Account Status', t: 'radio', o: [['active', 'Active'], ['inactive', 'Inactive']] }],
    cols: [col('Login ID', r => r.name), col('First Name', r => r.firstName), col('Last Name', r => r.lastName), col('Account Status', r => r.accountStatus),
      col('Security Domains', r => MIT.kids(r.dn, ['aaaUserDomain']).map(d => MIT.a(d).name + ': ' + MIT.kids(d, ['aaaUserRole']).map(x => MIT.a(x).name + (MIT.a(x).privType === 'writePriv' ? '(w)' : '(r)')).join('/')).join(', '))],
    wizard: { title: 'Create Local User', steps: [
      { l: 'User Identity', fields: [{ k: 'name', l: 'Login ID', req: true }, { k: 'pwd', l: 'Password', t: 'password', req: true }, { k: 'firstName', l: 'First Name' }, { k: 'lastName', l: 'Last Name' },
        { k: 'email', l: 'Email' }, { k: 'accountStatus', l: 'Account Status', t: 'radio', o: [['active', 'Active'], ['inactive', 'Inactive']], def: 'active' }] },
      { l: 'Security', fields: [{ k: '_d', l: 'Security Domains und Rollen', t: 'rows', start: true, cols: [{ k: 'dom', l: 'Security Domain', t: 'tname', target: 'aaaDomain', scope: 'aaa', req: true },
        { k: 'role', l: 'Role', t: 'select', o: AAA_ROLES.map(r => [r, r]), def: 'read-all' }, { k: 'priv', l: 'Privilege', t: 'select', o: [['readPriv', 'Read'], ['writePriv', 'Write']], def: 'readPriv' }] }] }],
      build: (v, parent) => {
        const by = {};
        (v._d || []).filter(d => d.dom).forEach(d => { (by[d.dom] = by[d.dom] || []).push(mo('aaaUserRole', { name: d.role, privType: d.priv })); });
        return { dn: parent + '/user-' + v.name, body: mo('aaaUser', { name: v.name, pwd: v.pwd, firstName: v.firstName, lastName: v.lastName, email: v.email, accountStatus: v.accountStatus },
          Object.entries(by).map(([d, roles]) => mo('aaaUserDomain', { name: d }, roles))) };
      } },
  },
};

/* ---------------- VMM, Imported Contracts, L2Out ---------------- */
Object.assign(SPEC, {
  vmmDomP: {
    label: 'VMM Domain', menu: 'Create vCenter Domain',
    fields: [NAME, relDn('infraRsVlanNs', 'VLAN Pool', 'fvnsVlanInstP'),
      { k: 'enfPref', l: 'Endpoint Retention / Enforcement', t: 'select', o: [['hw', 'hw'], ['sw', 'sw'], ['unknown', 'unknown']] }],
    cols: [ac('name'), col('VLAN Pool', r => nameOfDn(relOf(r.dn, 'infraRsVlanNs', 'tDn'))),
      col('vCenter', r => MIT.kids(r.dn, ['vmmCtrlrP']).map(d => MIT.a(d).hostOrIp).join(', ')),
      col('State', r => { const v = ((App.state || {}).vmm || []).find(x => x.dn === r.dn); return stateBadge(v ? v.state : 'offline'); })],
    summary: true, oper: ['vmm', 'deployed', 'endpoints'],
    wizard: {
      title: 'Create vCenter Domain',
      steps: [{ l: 'Domain', fields: [
        { k: 'name', l: 'Virtual Switch Name', create: true, req: true, ph: 'z. B. VDS1', help: 'Name der VMM Domain = Name des Distributed Switch im vCenter' },
        { k: '_vs', l: 'Virtual Switch', t: 'radio', o: [['vds', 'VMware vSphere Distributed Switch']], def: 'vds' },
        relDn('infraRsVlanNs', 'VLAN Pool', 'fvnsVlanInstP', { help: 'Für Port Groups braucht die Domain einen Pool mit dynamischer Allocation' }),
        { k: '_aaep', l: 'Associated Attachable Entity Profile', t: 'tdn', target: ['infraAttEntityP'], help: 'Fügt die Domain gleich dem AAEP hinzu (optional)' },
        { k: '_creds', l: 'vCenter Credentials', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'vc-cred', req: true },
          { k: 'usr', l: 'Username', ph: 'administrator@vsphere.local', req: true }, { k: 'pwd', l: 'Password', t: 'password', req: true }] },
        { k: '_ctrls', l: 'vCenter', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'vcenter1', req: true },
          { k: 'ip', l: 'Host Name (or IP Address)', ph: '192.168.10.50', req: true }, { k: 'dc', l: 'Datacenter', ph: 'DC1', req: true },
          { k: 'cred', l: 'Associated Credential', ph: 'vc-cred', req: true }] },
        { k: '_lldp', l: 'vSwitch Policy: LLDP Policy', t: 'tdn', target: ['lldpIfPol'], under: 'uni/infra/' },
        { k: '_cdp', l: 'vSwitch Policy: CDP Policy', t: 'tdn', target: ['cdpIfPol'], under: 'uni/infra/' },
        { k: '_lacp', l: 'vSwitch Policy: Port Channel Policy', t: 'tdn', target: ['lacpLagPol'], under: 'uni/infra/' }] }],
      build: v => {
        const dn = 'uni/vmmp-VMware/dom-' + v.name;
        const sw = [v._lldp && mo('vmmRsVswitchOverrideLldpIfPol', { tDn: v._lldp }), v._cdp && mo('vmmRsVswitchOverrideCdpIfPol', { tDn: v._cdp }),
          v._lacp && mo('vmmRsVswitchOverrideLacpPol', { tDn: v._lacp })].filter(Boolean);
        const dom = mo('vmmDomP', { name: v.name, enfPref: 'hw' },
          v['infraRsVlanNs.tDn'] ? mo('infraRsVlanNs', { tDn: v['infraRsVlanNs.tDn'] }) : null,
          (v._creds || []).map(c => mo('vmmUsrAccP', { name: c.name, usr: c.usr, pwd: c.pwd })),
          (v._ctrls || []).map(c => mo('vmmCtrlrP', { name: c.name, hostOrIp: c.ip, rootContName: c.dc }, mo('vmmRsAcc', { tDn: dn + '/usracc-' + c.cred }))),
          sw.length ? mo('vmmVSwitchPolicyCont', {}, sw) : null);
        const kids = [mo('vmmProvP', { vendor: 'VMware' }, dom)];
        if (v._aaep) kids.push({ infraInfra: { attributes: {}, children: [mo('infraAttEntityP', { name: nameOfDn(v._aaep) }, mo('infraRsDomP', { tDn: dn }))] } });
        return { url: 'uni', dn, body: mo('polUni', {}, kids) };
      },
    },
    actions: [['Create vCenter Credential', dn => createDialog(dn, 'vmmUsrAccP')], ['Create vCenter Controller', dn => createDialog(dn, 'vmmCtrlrP')],
      ['vSwitch Policy', dn => createDialog(dn, 'vmmVSwitchPolicyCont', 'vSwitch Policy')]],
  },
  vmmUsrAccP: {
    label: 'vCenter Credential',
    fields: [NAME, { k: 'usr', l: 'Username', req: true, ph: 'administrator@vsphere.local' }, { k: 'pwd', l: 'Password', t: 'password', help: 'leer lassen = unverändert' }, DESCR],
    cols: [ac('name'), col('Username', r => r.usr), ac('descr')],
  },
  vmmCtrlrP: {
    label: 'vCenter Controller',
    fields: [NAME, { k: 'hostOrIp', l: 'Host Name (or IP Address)', req: true, ph: '192.168.10.50' },
      { k: 'rootContName', l: 'Datacenter', req: true, ph: 'DC1', help: 'Name des Datacenter-Objekts im vCenter (Groß-/Kleinschreibung beachten)' },
      relDn('vmmRsAcc', 'Associated Credential', 'vmmUsrAccP', { req: true })],
    cols: [ac('name'), col('Host or IP', r => r.hostOrIp), col('Datacenter', r => r.rootContName), col('Credential', r => nameOfDn(relOf(r.dn, 'vmmRsAcc', 'tDn'))),
      col('Connection', r => { const v = ((App.state || {}).vmm || []).find(x => r.dn.startsWith(x.dn + '/')); return stateBadge(v ? v.state : 'offline'); })],
  },
  vmmVSwitchPolicyCont: {
    label: 'vSwitch Policy',
    fields: [relDn('vmmRsVswitchOverrideLldpIfPol', 'LLDP Policy', 'lldpIfPol', { under: 'uni/infra/' }),
      relDn('vmmRsVswitchOverrideCdpIfPol', 'CDP Policy', 'cdpIfPol', { under: 'uni/infra/' }),
      relDn('vmmRsVswitchOverrideLacpPol', 'Port Channel Policy', 'lacpLagPol', { under: 'uni/infra/' })],
    cols: [col('LLDP', r => nameOfDn(relOf(r.dn, 'vmmRsVswitchOverrideLldpIfPol', 'tDn'))), col('CDP', r => nameOfDn(relOf(r.dn, 'vmmRsVswitchOverrideCdpIfPol', 'tDn')))],
  },
  vzCPIf: {
    label: 'Imported Contract',
    fields: [NAME, relDn('vzRsIf', 'Global Contract', 'vzBrCP', { req: true, help: 'Exportierter Contract aus einem anderen Tenant (Scope global)' }), DESCR],
    cols: [ac('name'), col('Contract', r => relOf(r.dn, 'vzRsIf', 'tDn')), col('State', r => relState(MIT.a(r.dn + '/rsif') || {}))],
  },
  fvRsConsIf: { label: 'Consumed Contract Interface', fields: [relNameSelf('tnVzCPIfName', 'Contract Interface', 'vzCPIf')],
    cols: [col('Contract', r => r.tnVzCPIfName), col('Typ', () => 'Consumed Contract Interface'), col('State', relState)] },
  l2extDomP: {
    label: 'External Bridged Domain',
    fields: [NAME, relDn('infraRsVlanNs', 'VLAN Pool', 'fvnsVlanInstP')],
    cols: [ac('name'), col('VLAN Pool', r => nameOfDn(relOf(r.dn, 'infraRsVlanNs', 'tDn')))],
  },
  l2extOut: {
    label: 'L2Out',
    fields: [NAME, ALIAS, relName('l2extRsEBd', 'tnFvBDName', 'Bridge Domain', 'fvBD', { req: true }),
      { rel: 'l2extRsEBd', k: 'encap', l: 'Encap', ph: 'vlan-300' },
      relDn('l2extRsL2DomAtt', 'External Bridged Domain', 'l2extDomP', { req: true }), DESCR],
    cols: [ac('name'), col('Bridge Domain', r => relOf(r.dn, 'l2extRsEBd', 'tnFvBDName')), col('Encap', r => relOf(r.dn, 'l2extRsEBd', 'encap')),
      col('Domain', r => nameOfDn(relOf(r.dn, 'l2extRsL2DomAtt', 'tDn')))],
    normalize: v => { if (v['l2extRsEBd.encap']) v['l2extRsEBd.encap'] = vlanify(v['l2extRsEBd.encap']); return v; },
    summary: true, oper: ['deployed', 'endpoints'],
    wizard: {
      title: 'Create L2Out',
      steps: [
        { l: 'Identity', fields: [NAME, relName('l2extRsEBd', 'tnFvBDName', 'Bridge Domain', 'fvBD', { req: true }),
          { k: '_encap', l: 'Encap', req: true, ph: 'vlan-300', help: 'VLAN auf dem Draht zum Legacy-Netz' },
          relDn('l2extRsL2DomAtt', 'External Bridged Domain', 'l2extDomP', { req: true }),
          { k: '_paths', l: 'Path', t: 'rows', start: true, cols: [{ k: 'tDn', l: 'Interface', t: 'path' }] }] },
        { l: 'External EPG', fields: [{ k: '_epg', l: 'External EPG Name', req: true, ph: 'LegacyNet' }] }],
      build: (v, parent) => ({
        dn: parent + '/l2out-' + v.name,
        body: mo('l2extOut', { name: v.name }, mo('l2extRsEBd', { tnFvBDName: v['l2extRsEBd.tnFvBDName'], encap: vlanify(v._encap) }),
          mo('l2extRsL2DomAtt', { tDn: v['l2extRsL2DomAtt.tDn'] }),
          mo('l2extLNodeP', { name: 'default' }, mo('l2extLIfP', { name: 'default' }, (v._paths || []).filter(p => p.tDn).map(p => mo('l2extRsPathL2OutAtt', { tDn: p.tDn })))),
          mo('l2extInstP', { name: v._epg })),
      }),
    },
    actions: [['Create Node Profile', dn => createDialog(dn, 'l2extLNodeP')], ['Create External EPG', dn => createDialog(dn, 'l2extInstP')]],
  },
  l2extLNodeP: { label: 'Node Profile', fields: [NAME, DESCR], cols: [ac('name'), ac('descr')], actions: [['Create Interface Profile', dn => createDialog(dn, 'l2extLIfP')]] },
  l2extLIfP: { label: 'Interface Profile', fields: [NAME, DESCR], cols: [ac('name'), ac('descr')], actions: [['Create Path', dn => createDialog(dn, 'l2extRsPathL2OutAtt')]] },
  l2extRsPathL2OutAtt: { label: 'L2Out Path', fields: [{ k: 'tDn', l: 'Path', t: 'path', create: true, req: true }, DESCR],
    cols: [col('Path', r => pathLabel(r.tDn)), col('State', relState)] },
  l2extInstP: {
    label: 'External EPG (L2)',
    fields: [NAME, { k: 'prefGrMemb', l: 'Preferred Group Member', t: 'radio', o: [['exclude', 'Exclude'], ['include', 'Include']] }, DESCR],
    cols: [ac('name'), col('pcTag (sclass)', r => r.pcTag), ac('descr')],
    summary: true, oper: ['endpoints', 'contracts'],
    actions: [['Add Provided Contract', dn => createDialog(dn, 'fvRsProv')], ['Add Consumed Contract', dn => createDialog(dn, 'fvRsCons')],
      ['Add Consumed Contract Interface', dn => createDialog(dn, 'fvRsConsIf')]],
  },
});

Object.assign(SPEC, {
  rtctrlProfile: {
    label: 'Route Map for Import and Export Route Control',
    fields: [{ k: 'name', l: 'Name', t: 'select', o: [['default-export', 'default-export'], ['default-import', 'default-import']], create: true, req: true,
      help: 'default-export steuert, was das L3Out ankündigt; default-import, was die ACI übernimmt (nur mit Enforcement Import)' },
    { k: 'type', l: 'Type', t: 'radio', o: [['combinable', 'Match Prefix AND Routing Policy'], ['global', 'Match Routing Policy Only']] }, DESCR],
    cols: [ac('name'), col('Type', r => r.type), col('Contexts', r => String(MIT.kids(r.dn, ['rtctrlCtxP']).length))],
  },
  rtctrlCtxP: {
    label: 'Context', menu: 'Create Route Control Context',
    fields: [NAME, { k: 'order', l: 'Order', ph: '0' }, { k: 'action', l: 'Action', t: 'radio', o: [['permit', 'Permit'], ['deny', 'Deny']] },
      DESCR],
    wizard: {
      title: 'Create Route Control Context',
      steps: [{ l: 'Context', fields: [NAME, { k: 'order', l: 'Order', def: '0' }, { k: 'action', l: 'Action', t: 'radio', o: [['permit', 'Permit'], ['deny', 'Deny']], def: 'permit' },
        { k: '_rule', l: 'Associated Matched Rule', t: 'tname', target: 'rtctrlSubjP' }, DESCR] }],
      build: (v, parent) => ({ dn: parent + '/ctx-' + v.name, body: mo('rtctrlCtxP', { name: v.name, order: v.order || '0', action: v.action, descr: v.descr },
        v._rule ? mo('rtctrlRsCtxPToSubjP', { tnRtctrlSubjPName: v._rule }) : null) }),
    },
    cols: [ac('name'), col('Order', r => r.order), col('Action', r => r.action),
      col('Match Rules', r => MIT.kids(r.dn, ['rtctrlRsCtxPToSubjP']).map(d => MIT.a(d).tnRtctrlSubjPName).join(', '))],
  },
  rtctrlRsCtxPToSubjP: { label: 'Associated Matched Rule', fields: [relNameSelf('tnRtctrlSubjPName', 'Match Rule', 'rtctrlSubjP')],
    cols: [col('Match Rule', r => r.tnRtctrlSubjPName), col('State', relState)] },
  rtctrlSubjP: {
    label: 'Match Rule', fields: [NAME, DESCR],
    wizard: {
      title: 'Create Match Rule',
      steps: [{ l: 'Match Rule', fields: [NAME, DESCR, { k: '_p', l: 'Match Prefix', t: 'rows', start: true, cols: [{ k: 'ip', l: 'IP', ph: '8.8.8.0/24', req: true },
        { k: 'aggregate', l: 'Aggregate', t: 'select', o: [['no', 'False'], ['yes', 'True']], def: 'no' }, { k: 'fromPfxLen', l: 'Greater Than Mask', ph: '0', w: '80px' }, { k: 'toPfxLen', l: 'Less Than Mask', ph: '0', w: '80px' }] }] }],
      build: (v, parent) => ({ dn: parent + '/subj-' + v.name, body: mo('rtctrlSubjP', { name: v.name, descr: v.descr },
        (v._p || []).filter(x => x.ip).map(x => mo('rtctrlMatchRtDest', { ip: x.ip, aggregate: x.aggregate || 'no', fromPfxLen: x.fromPfxLen || '0', toPfxLen: x.toPfxLen || '0' }))) }),
    },
    cols: [ac('name'), col('Prefixes', r => MIT.kids(r.dn, ['rtctrlMatchRtDest']).map(d => MIT.a(d).ip + (MIT.a(d).aggregate === 'yes' ? ' (agg)' : '')).join(', ')), ac('descr')],
  },
  rtctrlMatchRtDest: {
    label: 'Match Prefix',
    fields: [{ k: 'ip', l: 'IP', create: true, req: true, ph: '8.8.8.0/24' }, { k: 'aggregate', l: 'Aggregate', t: 'yesno' },
      { k: 'fromPfxLen', l: 'Greater Than Mask', ph: '0', show: v => v.aggregate === 'yes' }, { k: 'toPfxLen', l: 'Less Than Mask', ph: '0', show: v => v.aggregate === 'yes' }],
    cols: [col('IP', r => r.ip), col('Aggregate', r => r.aggregate), col('From', r => r.fromPfxLen), col('To', r => r.toPfxLen)],
  },
});

/* ---------------- L4-L7 Service Graph / PBR ---------------- */
function nestDn(dn, child) {
  const CLS = { 'tn-': 'fvTenant', 'ap-': 'fvAp', 'epg-': 'fvAEPg', 'out-': 'l3extOut', 'instP-': 'l3extInstP', 'l2out-': 'l2extOut' };
  const parts = splitDn(dn).slice(1);
  let body = child;
  for (let i = parts.length - 1; i >= 0; i--) {
    const rn = parts[i];
    const pre = Object.keys(CLS).find(k => rn.startsWith(k));
    body = mo(CLS[pre], { name: rn.slice(pre.length) }, body);
  }
  return body;
}

Object.assign(SPEC, {
  vnsLDevVip: {
    label: 'L4-L7 Device', menu: 'Create L4-L7 Devices',
    fields: [NAME, { k: 'svcType', l: 'Service Type', t: 'select', o: [['FW', 'Firewall'], ['ADC', 'ADC'], ['OTHERS', 'Other']] },
      { k: 'devtype', l: 'Device Type', t: 'radio', o: [['PHYSICAL', 'Physical'], ['VIRTUAL', 'Virtual']] },
      relDn('vnsRsALDevToPhysDomP', 'Physical Domain', 'physDomP'),
      { k: 'funcType', l: 'Function Type', t: 'radio', o: [['GoThrough', 'GoThrough'], ['GoTo', 'GoTo'], ['L1', 'L1'], ['L2', 'L2']] }, DESCR],
    cols: [ac('name'), col('Service Type', r => r.svcType), col('Function Type', r => r.funcType), col('Domain', r => nameOfDn(relOf(r.dn, 'vnsRsALDevToPhysDomP', 'tDn'))),
      col('Concrete Devices', r => MIT.kids(r.dn, ['vnsCDev']).map(d => MIT.a(d).name).join(', '))],
    wizard: {
      title: 'Create L4-L7 Devices',
      steps: [
        { l: 'General', fields: [NAME, { k: 'svcType', l: 'Service Type', t: 'select', o: [['FW', 'Firewall'], ['ADC', 'ADC'], ['OTHERS', 'Other']], def: 'FW' },
          { k: 'devtype', l: 'Device Type', t: 'radio', o: [['PHYSICAL', 'Physical'], ['VIRTUAL', 'Virtual']], def: 'PHYSICAL' },
          relDn('vnsRsALDevToPhysDomP', 'Physical Domain', 'physDomP', { req: true }),
          { k: 'funcType', l: 'Function Type', t: 'radio', o: [['GoThrough', 'GoThrough (transparent)'], ['GoTo', 'GoTo (routed)'], ['L1', 'L1'], ['L2', 'L2']], def: 'GoTo' }] },
        { l: 'Devices', fields: [{ k: '_cdev', l: 'Concrete Device Name', req: true, ph: 'fw1' },
          { k: '_cifs', l: 'Concrete Interfaces', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'outside', req: true }, { k: 'tDn', l: 'Path', t: 'path' }] }] },
        { l: 'Cluster Interfaces', fields: [{ k: '_lifs', l: 'Cluster Interfaces', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'consumer', req: true },
          { k: 'encap', l: 'Encap', ph: 'vlan-401', req: true, w: '100px' }, { k: 'cif', l: 'Concrete Interface', ph: 'outside', req: true }] }] }],
      build: (v, parent) => {
        const dn = parent + '/lDevVip-' + v.name;
        return { dn, body: mo('vnsLDevVip', { name: v.name, svcType: v.svcType, devtype: v.devtype, funcType: v.funcType, managed: 'no' },
          mo('vnsRsALDevToPhysDomP', { tDn: v['vnsRsALDevToPhysDomP.tDn'] }),
          mo('vnsCDev', { name: v._cdev }, (v._cifs || []).map(c => mo('vnsCIf', { name: c.name }, c.tDn ? mo('vnsRsCIfPathAtt', { tDn: c.tDn }) : null))),
          (v._lifs || []).map(l => mo('vnsLIf', { name: l.name, encap: vlanify(l.encap) }, mo('vnsRsCIfAttN', { tDn: dn + '/cDev-' + v._cdev + '/cIf-[' + l.cif + ']' })))) };
      },
    },
  },
  vnsCDev: { label: 'Concrete Device', fields: [NAME], cols: [ac('name'), col('Interfaces', r => MIT.kids(r.dn, ['vnsCIf']).map(d => MIT.a(d).name).join(', '))] },
  vnsCIf: { label: 'Concrete Interface', fields: [NAME, relDn('vnsRsCIfPathAtt', 'Path', 'fabricPathEp', { t: 'path' })],
    cols: [ac('name'), col('Path', r => pathLabel(relOf(r.dn, 'vnsRsCIfPathAtt', 'tDn')))] },
  vnsLIf: { label: 'Cluster Interface', fields: [NAME, { k: 'encap', l: 'Encap', ph: 'vlan-401', req: true }],
    normalize: v => { v.encap = vlanify(v.encap); return v; },
    cols: [ac('name'), col('Encap', r => r.encap), col('Concrete Interfaces', r => MIT.kids(r.dn, ['vnsRsCIfAttN']).map(d => rnOf(MIT.a(d).tDn).replace(/^cIf-\[|\]$/g, '')).join(', '))] },
  vnsSvcRedirectPol: {
    label: 'L4-L7 Policy-Based Redirect', menu: 'Create L4-L7 Policy-Based Redirect',
    fields: [NAME, { k: 'hashingAlgorithm', l: 'Hashing Algorithm', t: 'select', o: [['sip-dip-prototype', 'Source IP, Destination IP and Protocol number'], ['sip', 'Source IP'], ['dip', 'Destination IP']] }, DESCR],
    cols: [ac('name'), col('Destinations', r => MIT.kids(r.dn, ['vnsRedirectDest']).map(d => MIT.a(d).ip + ' / ' + MIT.a(d).mac).join(', '))],
    wizard: {
      title: 'Create L4-L7 Policy-Based Redirect',
      steps: [{ l: 'Policy', fields: [NAME, DESCR, { k: '_d', l: 'L3 Destinations', t: 'rows', start: true, cols: [{ k: 'ip', l: 'IP', ph: '192.168.100.10', req: true }, { k: 'mac', l: 'MAC', ph: '00:50:56:FA:01:01' }] }] }],
      build: (v, parent) => {
        const tn = parent.replace(/\/svcCont$/, '');
        return { url: tn, dn: tn + '/svcCont/svcRedirectPol-' + v.name, body: mo('vnsSvcCont', {}, mo('vnsSvcRedirectPol', { name: v.name, descr: v.descr },
          (v._d || []).filter(d => d.ip).map(d => mo('vnsRedirectDest', { ip: d.ip, mac: (d.mac || '').toUpperCase() })))) };
      },
    },
  },
  vnsRedirectDest: { label: 'Redirect Destination', fields: [{ k: 'ip', l: 'IP', create: true, req: true }, { k: 'mac', l: 'MAC' }, { k: 'destName', l: 'Destination Name' }],
    normalize: v => { v.mac = (v.mac || '').toUpperCase(); return v; },
    cols: [col('IP', r => r.ip), col('MAC', r => r.mac)] },
  vnsAbsGraph: {
    label: 'L4-L7 Service Graph Template', menu: 'Create L4-L7 Service Graph Template',
    fields: [NAME, DESCR],
    cols: [ac('name'), col('Nodes', r => MIT.kids(r.dn, ['vnsAbsNode']).map(d => MIT.a(d).name + ' (' + nameOfDn(relOf(d, 'vnsRsNodeToLDev', 'tDn')) + ', ' + MIT.a(d).routingMode + ')').join(', ')),
      col('State', r => { const g = ((App.state || {}).graphs || []).filter(x => x.graph === r.dn); return g.length ? g.map(x => stateBadge(x.state === 'applied' ? 'formed' : 'missing-target')) : '—'; })],
    wizard: {
      title: 'Create L4-L7 Service Graph Template',
      steps: [{ l: 'Graph', fields: [{ k: 'name', l: 'Graph Name', create: true, req: true, ph: 'FW-Graph' },
        { k: '_dev', l: 'Device (Drag & Drop)', t: 'tdn', target: ['vnsLDevVip'], tenantScope: true, req: true },
        { k: '_node', l: 'Node Name', def: 'N1', req: true },
        { k: '_ftype', l: 'Firewall', t: 'radio', o: [['GoTo', 'Routed'], ['GoThrough', 'Transparent']], def: 'GoTo' },
        { k: '_redir', l: 'Route Redirect', t: 'yesno', def: 'yes', help: 'Policy-Based Redirect: die ACI leitet den Verkehr zur Firewall um, die Hosts behalten ihr Gateway' }] }],
      build: (v, parent) => ({ dn: parent + '/AbsGraph-' + v.name, body: mo('vnsAbsGraph', { name: v.name },
        mo('vnsAbsTermNodeCon', { name: 'T1' }), mo('vnsAbsTermNodeProv', { name: 'T2' }),
        mo('vnsAbsNode', { name: v._node || 'N1', funcType: v._ftype, routingMode: v._redir === 'yes' ? 'Redirect' : 'unspecified', funcTemplateType: v._ftype === 'GoTo' ? 'FW_ROUTED' : 'FW_TRANS' },
          mo('vnsRsNodeToLDev', { tDn: v._dev }))) }),
    },
    actions: [['Apply L4-L7 Service Graph Template', dn => applyGraph(dn)]],
  },
  vnsAbsNode: { label: 'Function Node', fields: [NAME, { k: 'routingMode', l: 'Routing Mode', t: 'radio', o: [['Redirect', 'Redirect'], ['unspecified', 'unspecified']] },
    relDn('vnsRsNodeToLDev', 'L4-L7 Device', 'vnsLDevVip')],
    cols: [ac('name'), col('Device', r => nameOfDn(relOf(r.dn, 'vnsRsNodeToLDev', 'tDn'))), col('Routing Mode', r => r.routingMode)] },
  vnsLDevCtx: {
    label: 'Device Selection Policy',
    fields: [{ k: 'ctrctNameOrLbl', l: 'Contract Name', create: true, req: true }, { k: 'graphNameOrLbl', l: 'Graph Name', create: true, req: true },
      { k: 'nodeNameOrLbl', l: 'Node Name', create: true, req: true, def: 'N1' }, relDn('vnsRsLDevCtxToLDev', 'L4-L7 Device', 'vnsLDevVip')],
    cols: [col('Contract', r => r.ctrctNameOrLbl), col('Graph', r => r.graphNameOrLbl), col('Node', r => r.nodeNameOrLbl), col('Device', r => nameOfDn(relOf(r.dn, 'vnsRsLDevCtxToLDev', 'tDn')))],
  },
  vnsLIfCtx: { label: 'Logical Interface Context', fields: [{ k: 'connNameOrLbl', l: 'Connector Name', t: 'select', o: [['consumer', 'consumer'], ['provider', 'provider']], create: true, req: true },
    relDn('vnsRsLIfCtxToBD', 'Bridge Domain', 'fvBD', { tenantScope: true }), relDn('vnsRsLIfCtxToLIf', 'Cluster Interface', 'vnsLIf', { tenantScope: true }),
    relDn('vnsRsLIfCtxToSvcRedirectPol', 'L4-L7 Policy-Based Redirect', 'vnsSvcRedirectPol', { tenantScope: true })],
    cols: [col('Connector', r => r.connNameOrLbl), col('BD', r => nameOfDn(relOf(r.dn, 'vnsRsLIfCtxToBD', 'tDn'))), col('Cluster Interface', r => nameOfDn(relOf(r.dn, 'vnsRsLIfCtxToLIf', 'tDn'))),
      col('PBR', r => nameOfDn(relOf(r.dn, 'vnsRsLIfCtxToSvcRedirectPol', 'tDn')))] },
});

/* Apply L4-L7 Service Graph Template: Contract, EPG-Zuordnung und Device Selection Policy in einem Schritt */
function applyGraph(gdn) {
  const tn = tenantOf(gdn);
  const gname = MIT.a(gdn).name;
  const node = MIT.kids(gdn, ['vnsAbsNode'])[0];
  const nname = node ? MIT.a(node).name : 'N1';
  const ldev = node ? relOf(node, 'vnsRsNodeToLDev', 'tDn') : '';
  const epg = { t: 'tdn', target: ['fvAEPg', 'l3extInstP'], tenantScope: true, req: true };
  const conn = c => [{ k: '_' + c + 'bd', l: 'BD', t: 'tdn', target: ['fvBD'], tenantScope: true, req: true },
    { k: '_' + c + 'pbr', l: 'Redirect Policy', t: 'tdn', target: ['vnsSvcRedirectPol'], tenantScope: true },
    { k: '_' + c + 'lif', l: 'Cluster Interface', t: 'tdn', target: ['vnsLIf'], under: ldev + '/', req: true }];
  const steps = [
    { l: 'Contract', fields: [Object.assign({ k: '_cons', l: 'Consumer EPG / External Network' }, epg), Object.assign({ k: '_prov', l: 'Provider EPG / Internal Network' }, epg),
      { k: '_mode', l: 'Contract', t: 'radio', o: [['new', 'Create A New Contract'], ['old', 'Choose An Existing Contract Subject']], def: 'old' },
      { k: '_brc', l: 'Contract Name', t: 'tname', target: 'vzBrCP', show: v => v._mode === 'old' },
      { k: '_newname', l: 'Contract Name', ph: 'web-to-app', show: v => v._mode === 'new' },
      { k: '_flt', l: 'Filter', t: 'tname', target: 'vzFilter', empty: 'default (permit all)', show: v => v._mode === 'new' }] },
    { l: 'Graph Template', fields: [{ k: '_info', l: 'Graph', ro: true, def: gname + ' · Node ' + nname + ' · Device ' + nameOfDn(ldev) },
      { k: '_h1', l: 'Consumer Connector', ro: true, def: 'Type General, L3 Destination (VIP) ja' }].concat(conn('c'),
      [{ k: '_h2', l: 'Provider Connector', ro: true, def: 'Type General, L3 Destination (VIP) ja' }], conn('p')) },
  ];
  wizard('Apply L4-L7 Service Graph Template To EPGs', steps, { tenant: tn, cls: 'vnsAbsGraph', dn: gdn }, async v => {
    const cname = v._mode === 'new' ? v._newname : v._brc;
    if (!cname) throw new ApiError('Eingabe', 'Contract angeben');
    const kids = [];
    if (v._mode === 'new') {
      kids.push(mo('vzBrCP', { name: cname }, mo('vzSubj', { name: 'Subject', revFltPorts: 'yes' }, mo('vzRsSubjFiltAtt', { tnVzFilterName: v._flt || 'default' }),
        mo('vzRsSubjGraphAtt', { tnVnsAbsGraphName: gname }))));
    } else {
      const b = tn + '/brc-' + cname;
      await MIT.load(b);
      const subj = MIT.kids(b, ['vzSubj'])[0];
      if (!subj) throw new ApiError('Eingabe', 'Der Contract ' + cname + ' hat kein Subject');
      kids.push(mo('vzBrCP', { name: cname }, mo('vzSubj', { name: MIT.a(subj).name }, mo('vzRsSubjGraphAtt', { tnVnsAbsGraphName: gname }))));
    }
    const lic = c => mo('vnsLIfCtx', { connNameOrLbl: c === 'c' ? 'consumer' : 'provider' }, mo('vnsRsLIfCtxToBD', { tDn: v['_' + c + 'bd'] }),
      mo('vnsRsLIfCtxToLIf', { tDn: v['_' + c + 'lif'] }), v['_' + c + 'pbr'] ? mo('vnsRsLIfCtxToSvcRedirectPol', { tDn: v['_' + c + 'pbr'] }) : null);
    kids.push(mo('vnsLDevCtx', { ctrctNameOrLbl: cname, graphNameOrLbl: gname, nodeNameOrLbl: nname }, mo('vnsRsLDevCtxToLDev', { tDn: ldev }), lic('c'), lic('p')));
    await API.postMo(tn, mo('fvTenant', {}, kids));
    for (const [d, rel] of [[v._cons, 'fvRsCons'], [v._prov, 'fvRsProv']]) await API.postMo('uni', nestDn(d, mo(rel, { tnVzBrCPName: cname })));
    toast('Service Graph ' + gname + ' auf Contract ' + cname + ' angewendet');
    App.reload();
  });
}

/* Contract in einen anderen Tenant exportieren: legt dort ein vzCPIf (Imported Contract) an */
async function exportContract(dn) {
  const tenants = (await API.cls('fvTenant')).map(r => r.fvTenant.attributes.name).filter(n => 'uni/tn-' + n !== tenantOf(dn));
  const f = buildForm([{ k: 'name', l: 'Name', req: true, help: 'Name des Imported Contract im Ziel-Tenant' },
    { k: 'tenant', l: 'Tenant', t: 'select', o: tenants.map(n => [n, n]), req: true }], { name: MIT.a(dn).name, tenant: tenants[0] }, {}, 'create');
  const scope = MIT.a(dn).scope;
  const body = h('div', null, scope !== 'global' ? h('div', { class: 'card note warn' }, 'Der Contract hat Scope ' + scope + '. Für einen anderen Tenant braucht er Scope global.') : null, f.el);
  modal('Export Contract', body, [{ l: 'Abbrechen' }, {
    l: 'Submit', primary: true, fn: async () => {
      const v = f.get();
      if (!v.name || !v.tenant) throw new ApiError('Eingabe', 'Name und Tenant angeben');
      await API.postMo('uni/tn-' + v.tenant, mo('vzCPIf', { name: v.name }, mo('vzRsIf', { tDn: dn })));
      toast('Contract nach Tenant ' + v.tenant + ' exportiert');
      App.reload();
    },
  }]);
}

function ipInNet(ip, cidr) {
  const toN = s => s.split('.').reduce((a, b) => a * 256 + Number(b), 0);
  const [net, len] = cidr.split('/');
  const mask = len === '0' ? 0 : (0xFFFFFFFF << (32 - Number(len))) >>> 0;
  return ((toN(ip) & mask) >>> 0) === ((toN(net) & mask) >>> 0);
}

/* Platzhalter: Bereiche des APIC, die im Training ohne Funktion sind */
const PH = (l, text) => ({ l, ph: text || l + ' ist in Datacenter Prep nur als Menüpunkt vorhanden und hat keine Funktion.' });

/* Navigationsbaum: je Klasse die Unterordner (cls) */
const TREE = {
  fvTenant: [
    { l: 'Application Profiles', cls: ['fvAp'] },
    { l: 'Security Domains', cls: ['aaaDomainRef'], flat: 1, hidden: 1 },
    { l: 'Networking', sub: [{ l: 'Bridge Domains', cls: ['fvBD'] }, { l: 'VRFs', cls: ['fvCtx'] }, { l: 'L2Outs', cls: ['l2extOut'] }, { l: 'L3Outs', cls: ['l3extOut'] }, PH('SR-MPLS VRF L3Outs'), PH('Dot1Q Tunnels')] },
    PH('IP Address Pools'),
    { l: 'Contracts', sub: [{ l: 'Standard', cls: ['vzBrCP'] }, { l: 'Taboos', cls: ['vzTaboo'] }, { l: 'Imported', cls: ['vzCPIf'] }, { l: 'Filters', cls: ['vzFilter'] }, PH('Out-Of-Band Contracts')] },
    { l: 'Policies', sub: [{ l: 'Protocol', sub: [{ l: 'BFD', cls: ['bfdIfPol'] }, { l: 'BGP', sub: [{ l: 'BGP Timers', cls: ['bgpCtxPol'] }, { l: 'BGP Route Summarization', cls: ['bgpRtSummPol'] }] }, PH('Custom QoS'), PH('DHCP'), { l: 'EIGRP', sub: [{ l: 'EIGRP Interface', cls: ['eigrpIfPol'] }, { l: 'EIGRP Route Summarization', cls: ['eigrpRtSummPol'] }] }, PH('End Point Retention'), PH('IGMP Snoop'), PH('ND RA Prefix'),
      { l: 'OSPF Interface', cls: ['ospfIfPol'] }, PH('OSPF Timers'), PH('Route Maps for Route Control'), { l: 'Match Rules', cls: ['rtctrlSubjP'] }, PH('Set Rules'),
      { l: 'L4-L7 Policy-Based Redirect', cls: ['vnsSvcRedirectPol'], under: 'svcCont' }, PH('L4-L7 Redirect Health Groups'),
      { l: 'IP SLA', sub: [{ l: 'IP SLA Monitoring Policies', cls: ['fvIPSLAMonitoringPol'] }, { l: 'Track Members', cls: ['fvTrackMember'] }, { l: 'Track Lists', cls: ['fvTrackList'] }] },
      { l: 'OSPF Route Summarization', cls: ['ospfRtSummPol'] }] }, PH('Troubleshoot'), PH('Monitoring'), PH('NetFlow')] },
    { l: 'Services', sub: [{ l: 'L4-L7', sub: [{ l: 'Service Graph Templates', cls: ['vnsAbsGraph'] }, PH('Router configurations'), PH('Function Profiles'),
      { l: 'Devices', cls: ['vnsLDevVip'] }, PH('Imported Devices'), { l: 'Devices Selection Policies', cls: ['vnsLDevCtx'] },
      { l: 'Deployed Graph Instances', view: (w, tn) => Views.graphInstances(w, tn) }, PH('Deployed Devices'), PH('Inband Management Configuration for L4-L7 devices')] }] },
  ],
  fvAp: [{ l: 'Application EPGs', cls: ['fvAEPg'], filter: a => a.isAttrBasedEPg !== 'yes' }, { l: 'uSeg EPGs', cls: ['fvAEPg'], filter: a => a.isAttrBasedEPg === 'yes', defaults: { isAttrBasedEPg: 'yes' } },
    { l: 'Endpoint Security Groups', cls: ['fvESg'] }],
  fvESg: [{ l: 'Selectors', sub: [{ l: 'EPG Selectors', cls: ['fvEPgSelector'], flat: 1 }, { l: 'IP Subnet Selectors', cls: ['fvEPSelector'], flat: 1 }] },
    { l: 'Contracts', cls: ['fvRsProv', 'fvRsCons'], flat: 1 }],
  fvCrtrn: [{ l: 'IP Attributes', cls: ['fvIpAttr'], flat: 1 }, { l: 'MAC Attributes', cls: ['fvMacAttr'], flat: 1 }],
  aaaUser: [{ l: 'Security Domains', cls: ['aaaUserDomain'] }],
  aaaAuthRealm: [{ l: 'Default Authentication', rn: 'defaultauth' }, { l: 'Console Authentication', rn: 'consoleauth' }],
  aaaLoginDomain: [{ l: 'Domain Authentication', rn: 'domainauth' }],
  aaaUserDomain: [{ l: 'Roles', cls: ['aaaUserRole'], flat: 1 }],
  aaaTacacsPlusProviderGroup: [{ l: 'Providers', cls: ['aaaProviderRef'], flat: 1 }],
  aaaRadiusProviderGroup: [{ l: 'Providers', cls: ['aaaProviderRef'], flat: 1 }],
  aaaLdapProviderGroup: [{ l: 'Providers', cls: ['aaaProviderRef'], flat: 1 }],
  mgmtInB: [{ l: 'Static Node Management Addresses (In-Band)', cls: ['mgmtRsInBStNode'], flat: 1 }],
  fvAEPg: [{ l: 'uSeg Attributes', rn: 'crtrn' }, { l: 'Domains (VMs and Bare-Metals)', cls: ['fvRsDomAtt'], flat: 1 }, PH('EPG Members'), { l: 'Static Ports', cls: ['fvRsPathAtt'], flat: 1 },
    { l: 'Static Leafs', cls: ['fvRsNodeAtt'], flat: 1 }, { l: 'Contracts', cls: ['fvRsProv', 'fvRsCons', 'fvRsConsIf', 'fvRsProtBy'], flat: 1 }, PH('Static Endpoint'), { l: 'Subnets', cls: ['fvSubnet'], flat: 1 }],
  fvBD: [{ l: 'Subnets', cls: ['fvSubnet'], flat: 1 }, { l: 'Associated L3 Outs', cls: ['fvRsBDToOut'], flat: 1, hidden: 1 }, PH('ND Proxy Subnets')],
  fvCtx: [{ l: 'EPG Collection for VRF', rn: 'any' }],
  vzAny: [{ l: 'Contracts', cls: ['vzRsAnyToProv', 'vzRsAnyToCons'], flat: 1 }],
  vzBrCP: [{ l: 'Subjects', cls: ['vzSubj'] }],
  vzSubj: [{ l: 'Filters', cls: ['vzRsSubjFiltAtt'], flat: 1 }],
  vzTaboo: [{ l: 'Subjects', cls: ['vzTSubj'] }],
  vzTSubj: [{ l: 'Filters', cls: ['vzRsDenyRule'], flat: 1 }],
  vzFilter: [{ l: 'Entries', cls: ['vzEntry'], flat: 1 }],
  l3extOut: [{ l: 'Routing Protocols', cls: ['ospfExtP', 'bgpExtP', 'eigrpExtP'], flat: 1, max: 3 }, { l: 'Logical Node Profiles', cls: ['l3extLNodeP'] }, { l: 'External EPGs', cls: ['l3extInstP'] }, { l: 'Route Map for import and export route control', cls: ['rtctrlProfile'] }],
  rtctrlProfile: [{ l: 'Contexts', cls: ['rtctrlCtxP'] }],
  vnsLDevVip: [{ l: 'Concrete Devices', cls: ['vnsCDev'] }, { l: 'Cluster Interfaces', cls: ['vnsLIf'], flat: 1 }],
  vnsCDev: [{ l: 'Interfaces', cls: ['vnsCIf'], flat: 1 }],
  vnsAbsGraph: [{ l: 'Function Nodes', cls: ['vnsAbsNode'], flat: 1 }],
  vnsLDevCtx: [{ l: 'Logical Interface Contexts', cls: ['vnsLIfCtx'], flat: 1 }],
  vnsSvcRedirectPol: [{ l: 'Destinations', cls: ['vnsRedirectDest'], flat: 1 }],
  rtctrlCtxP: [{ l: 'Associated Matched Rules', cls: ['rtctrlRsCtxPToSubjP'], flat: 1 }],
  rtctrlSubjP: [{ l: 'Match Prefix', cls: ['rtctrlMatchRtDest'], flat: 1 }],
  l3extLNodeP: [{ l: 'Configured Nodes', cls: ['l3extRsNodeL3OutAtt'] }, { l: 'Logical Interface Profiles', cls: ['l3extLIfP'] }, { l: 'BGP Peer Connectivity Profiles (Loopback)', cls: ['bgpPeerP'], flat: 1 }],
  l3extRsNodeL3OutAtt: [{ l: 'Static Routes', cls: ['ipRouteP'] }],
  ipRouteP: [{ l: 'Next Hop Addresses', cls: ['ipNexthopP'], flat: 1 }],
  l3extLIfP: [{ l: 'Routed Interfaces / Sub-Interfaces / SVIs', cls: ['l3extRsPathL3OutAtt'] }, { l: 'Floating SVI', cls: ['l3extVirtualLIfP'] },
    { l: 'OSPF Interface Profile', cls: ['ospfIfP'], flat: 1, max: 1 }, { l: 'EIGRP Interface Profile', cls: ['eigrpIfP'], flat: 1, max: 1 }, { l: 'BFD Interface Profile', cls: ['bfdIfP'], flat: 1, max: 1 }],
  l3extRsPathL3OutAtt: [{ l: 'vPC Members (Side A / Side B)', cls: ['l3extMember'], flat: 1, max: 2 }, { l: 'IPv4 Secondary Addresses', cls: ['l3extIp'], flat: 1 }, { l: 'BGP Peer Connectivity Profiles', cls: ['bgpPeerP'], flat: 1 }],
  l3extMember: [{ l: 'IPv4 Secondary Addresses', cls: ['l3extIp'], flat: 1 }],
  l3extVirtualLIfP: [{ l: 'Path Attributes', cls: ['l3extRsDynPathAtt'], flat: 1 }, { l: 'IPv4 Secondary Addresses', cls: ['l3extIp'], flat: 1 }],
  fvTrackList: [{ l: 'Track Members', cls: ['fvRsOtmListMember'], flat: 1 }],
  l3extInstP: [{ l: 'Subnets', cls: ['l3extSubnet'], flat: 1 }, { l: 'Contracts', cls: ['fvRsProv', 'fvRsCons', 'fvRsConsIf', 'fvRsProtBy'], flat: 1 }],
  l2extOut: [{ l: 'Logical Node Profiles', cls: ['l2extLNodeP'] }, { l: 'External EPGs', cls: ['l2extInstP'] }],
  l2extLNodeP: [{ l: 'Logical Interface Profiles', cls: ['l2extLIfP'] }],
  l2extLIfP: [{ l: 'Paths', cls: ['l2extRsPathL2OutAtt'], flat: 1 }],
  l2extInstP: [{ l: 'Contracts', cls: ['fvRsProv', 'fvRsCons', 'fvRsConsIf', 'fvRsProtBy'], flat: 1 }],
  vmmDomP: [{ l: 'Controllers', cls: ['vmmCtrlrP'] }, { l: 'vCenter Credentials', cls: ['vmmUsrAccP'], flat: 1 }, { l: 'vSwitch Policy', rn: 'vswitchpolcont' }],
  fvnsVlanInstP: [{ l: 'Encap Blocks', cls: ['fvnsEncapBlk'], flat: 1 }],
  infraAttEntityP: [{ l: 'Domains', cls: ['infraRsDomP'], flat: 1 }],
  infraNodeP: [{ l: 'Leaf Selectors', cls: ['infraLeafS'] }, { l: 'Associated Interface Selector Profiles', cls: ['infraRsAccPortP'], flat: 1 }],
  infraLeafS: [{ l: 'Node Blocks', cls: ['infraNodeBlk'], flat: 1 }],
  infraAccPortP: [{ l: 'Access Port Selectors', cls: ['infraHPortS'] }],
  infraHPortS: [{ l: 'Port Blocks', cls: ['infraPortBlk'], flat: 1 }],
  fabricProtPol: [{ l: 'Explicit VPC Protection Groups', cls: ['fabricExplicitGEp'], flat: 1 }],
  fabricExplicitGEp: [{ l: 'Nodes', cls: ['fabricNodePEp'], flat: 1 }],
  fabricPodP: [{ l: 'Pod Selectors', cls: ['fabricPodS'], flat: 1 }],
  datetimePol: [{ l: 'NTP Servers', cls: ['datetimeNtpProv'], flat: 1 }],
  mgmtMgmtP: [{ l: 'Out-of-Band EPGs', cls: ['mgmtOoB'] }],
  mgmtOoB: [{ l: 'Static Node Management Addresses', cls: ['mgmtRsOoBStNode'], flat: 1 }],
};

/* Zusatzordner im Tenant mgmt */
const MGMT_TREE = [
  { l: 'Node Management EPGs', cls: ['mgmtOoB', 'mgmtInB'], parent: 'uni/tn-mgmt/mgmtp-default' },
  { l: 'Node Management Addresses', sub: [{ l: 'Static Node Management Addresses', cls: ['mgmtRsOoBStNode'], parent: 'uni/tn-mgmt/mgmtp-default/oob-default', flat: 1 }] },
  PH('Managed Node Connectivity Groups'),
];

const AAA_TREE = [
  { l: 'Authentication', sub: [{ l: 'AAA (Default / Console / Remote User Policy)', mo: 'uni/userext/authrealm' }, { l: 'Login Domains', cls: ['aaaLoginDomain'], parent: 'uni/userext' }] },
  { l: 'Security', sub: [{ l: 'Security Domains', cls: ['aaaDomain'], parent: 'uni/userext' }, { l: 'Local Users', cls: ['aaaUser'], parent: 'uni/userext' }, PH('Roles', 'Die Rollen sind fest vorgegeben: admin, aaa, access-admin, fabric-admin, nw-svc-admin, ops, read-all, tenant-admin, tenant-ext-admin, vmm-admin.')] },
  { l: 'TACACS+ Management', sub: [{ l: 'TACACS+ Providers', cls: ['aaaTacacsPlusProvider'], parent: 'uni/userext/tacacsext' }, { l: 'TACACS+ Provider Groups', cls: ['aaaTacacsPlusProviderGroup'], parent: 'uni/userext/tacacsext' }] },
  { l: 'RADIUS Management', sub: [{ l: 'RADIUS Providers', cls: ['aaaRadiusProvider'], parent: 'uni/userext/radiusext' }, { l: 'RADIUS Provider Groups', cls: ['aaaRadiusProviderGroup'], parent: 'uni/userext/radiusext' }] },
  { l: 'LDAP Management', sub: [{ l: 'LDAP Providers', cls: ['aaaLdapProvider'], parent: 'uni/userext/ldapext' }, { l: 'LDAP Provider Groups', cls: ['aaaLdapProviderGroup'], parent: 'uni/userext/ldapext' }] },
  { l: 'Login-Protokoll', view: w => Views.loginLog(w) },
];

const isPC = a => a.lagT === 'link', isVPC = a => a.lagT === 'node';
const ACCESS_TREE = [
  { l: 'Switches', sub: [{ l: 'Leaf Switches', sub: [{ l: 'Profiles', cls: ['infraNodeP'], parent: 'uni/infra' }, PH('Policy Groups'), PH('Overrides')] },
    { l: 'Spine Switches', sub: [PH('Profiles'), PH('Policy Groups')] }] },
  PH('Modules'),
  { l: 'Interfaces', sub: [{ l: 'Leaf Interfaces', sub: [{ l: 'Profiles', cls: ['infraAccPortP'], parent: 'uni/infra' },
    { l: 'Policy Groups', sub: [{ l: 'Leaf Access Port', cls: ['infraAccPortGrp'], parent: 'uni/infra/funcprof' },
      { l: 'PC Interface', cls: ['infraAccBndlGrp'], parent: 'uni/infra/funcprof', filter: isPC, defaults: { lagT: 'link' } },
      { l: 'VPC Interface', cls: ['infraAccBndlGrp'], parent: 'uni/infra/funcprof', filter: isVPC, defaults: { lagT: 'node' } },
      PH('PC/VPC Override'), PH('Leaf Breakout Port Group')] }, PH('Overrides')] },
  { l: 'Spine Interfaces', sub: [PH('Profiles'), PH('Policy Groups')] }] },
  { l: 'Policies', sub: [
    { l: 'Switch', sub: [{ l: 'Virtual Port Channel default', mo: 'uni/fabric/protpol' }, PH('Spanning Tree'), PH('Forwarding Scale Profile')] },
    { l: 'Interface', sub: [{ l: 'Link Level', cls: ['fabricHIfPol'], parent: 'uni/infra' }, { l: 'CDP Interface', cls: ['cdpIfPol'], parent: 'uni/infra' },
      { l: 'LLDP Interface', cls: ['lldpIfPol'], parent: 'uni/infra' }, { l: 'Port Channel', cls: ['lacpLagPol'], parent: 'uni/infra' },
      { l: 'Spanning Tree Interface', cls: ['stpIfPol'], parent: 'uni/infra' }, { l: 'MCP Interface', cls: ['mcpIfPol'], parent: 'uni/infra' },
      PH('Storm Control'), PH('L2 Interface')] },
    { l: 'Global', sub: [{ l: 'Attachable Access Entity Profiles', cls: ['infraAttEntityP'], parent: 'uni/infra' }, PH('QOS Class'), PH('DHCP Relay'), PH('MCP Instance Policy default')] },
    PH('Monitoring'), PH('Troubleshooting')] },
  { l: 'Pools', sub: [{ l: 'VLAN', cls: ['fvnsVlanInstP'], parent: 'uni/infra' }, PH('VXLAN'), PH('VSAN')] },
  { l: 'Physical and External Domains', sub: [{ l: 'Physical Domains', cls: ['physDomP'], parent: 'uni' }, PH('L2 Domains'), { l: 'External Bridged Domains', cls: ['l2extDomP'], parent: 'uni' },
    { l: 'L3 Domains', cls: ['l3extDomP'], parent: 'uni' }, PH('Fibre Channel Domains')] },
];

const VMM_TREE = [
  { l: 'VMM Domains', sub: [{ l: 'VMware', cls: ['vmmDomP'], parent: 'uni/vmmp-VMware' }, PH('Microsoft'), PH('Kubernetes'), PH('Red Hat'), PH('OpenStack')] },
  PH('Container Domains'),
];

const FABRICPOL_TREE = [
  { l: 'Pods', sub: [{ l: 'Policy Groups', cls: ['fabricPodPGrp'], parent: 'uni/fabric/funcprof' }, { l: 'Profiles', cls: ['fabricPodP'], parent: 'uni/fabric' }] },
  { l: 'Switches', sub: [PH('Leaf Switches'), PH('Spine Switches')] },
  PH('Modules'),
  { l: 'Interfaces', sub: [PH('Leaf Interfaces'), PH('Spine Interfaces')] },
  { l: 'Policies', sub: [{ l: 'Pod', sub: [{ l: 'Date and Time', cls: ['datetimePol'], parent: 'uni/fabric' }, PH('SNMP'), PH('Management Access'), PH('ISIS Policy default')] },
    PH('Switch'), PH('Interface'), PH('Global'), PH('Monitoring'), PH('Troubleshooting'), PH('Geolocation'), PH('Macsec'), PH('Analytics'), PH('Tags')] },
];

const ICON = {
  fvTenant: 'TN', fvAp: 'AP', fvAEPg: 'EPG', fvBD: 'BD', fvCtx: 'VRF', l3extOut: 'L3', vzBrCP: 'C', vzFilter: 'F', vzSubj: 'S', vzTaboo: 'T', vzTSubj: 'S',
  l3extLNodeP: 'NP', l3extLIfP: 'IP', l3extInstP: 'EX', l3extRsNodeL3OutAtt: 'N', l3extRsPathL3OutAtt: 'IF', ipRouteP: 'R', vzAny: '*',
  infraNodeP: 'SW', infraAccPortP: 'IF', infraAccPortGrp: 'PG', infraAccBndlGrp: 'PC', infraAttEntityP: 'AE', physDomP: 'PD',
  l3extDomP: 'L3D', fvnsVlanInstP: 'VL', infraHPortS: 'S', infraLeafS: 'S', fabricExplicitGEp: 'vPC', ospfIfPol: 'O',
  cdpIfPol: 'P', lldpIfPol: 'P', lacpLagPol: 'P', fabricHIfPol: 'P', mcpIfPol: 'P', stpIfPol: 'P', fabricProtPol: 'vPC',
  fabricPodPGrp: 'PG', fabricPodP: 'PP', datetimePol: 'NTP', mgmtOoB: 'OOB', rtctrlProfile: 'RM', rtctrlCtxP: 'C', rtctrlSubjP: 'MR', vnsLDevVip: 'FW', vnsAbsGraph: 'SG', vnsLDevCtx: 'DS', vnsSvcRedirectPol: 'PBR', vnsCDev: 'CD',
  vmmDomP: 'VDS', vmmCtrlrP: 'VC', l2extOut: 'L2', l2extInstP: 'EX', l2extDomP: 'L2D', vzCPIf: 'IC', l2extLNodeP: 'NP', l2extLIfP: 'IP',
};
