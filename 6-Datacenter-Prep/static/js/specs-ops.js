/* Betriebsthemen: Firmware, Import/Export, Monitoring, DHCP Relay, QoS, MCP */
'use strict';

const TRIGGERED = [['untriggered', 'Untriggered'], ['triggered', 'Triggered (jetzt ausführen)']];
const FAULT_SEVS = [['critical', 'critical'], ['major', 'major'], ['minor', 'minor'], ['warning', 'warning'], ['info', 'info']];
const SYSLOG_SEVS = ['emergencies', 'alerts', 'critical', 'errors', 'warnings', 'notifications', 'information', 'debugging'].map(x => [x, x]);
const INCL = [['faults', 'Faults'], ['events', 'Events'], ['audit', 'Audit Logs'], ['session', 'Session Logs']];
const MGMT_EPG = { k: 'tDn', l: 'Management EPG', t: 'tdn', target: ['mgmtOoB', 'mgmtInB'], empty: '— Management EPG wählen —' };
const fwVersions = type => async () => [['', '— Version aus dem Repository —']].concat((await API.sim('firmware')).repo.filter(i => i.type === type).map(i => [i.version, i.version + '  (' + i.name + ')']));
const trigger = (dn, cls, label) => async () => { await API.postMo(dn, mo(cls, { adminSt: 'triggered' })); toast(label); App.reload(); App.refreshState(); };
const blocks = dn => MIT.kids(dn, ['fabricNodeBlk']).map(b => { const a = MIT.a(b); return a.from_ === a.to_ ? a.from_ : a.from_ + '-' + a.to_; }).join(', ');
const remoteRow = (dn, rel) => relOf(dn, rel || 'configRsRemotePath', 'tnFileRemotePathName');

Object.assign(SPEC, {
  /* ---------------- Firmware ---------------- */
  firmwareOSource: {
    label: 'Firmware Download Task', menu: 'Add Firmware to APIC',
    fields: [NAME, { k: 'proto', l: 'Protocol', t: 'radio', o: [['scp', 'Secure copy'], ['http', 'HTTP'], ['sftp', 'SFTP']], def: 'scp' },
      { k: 'url', l: 'URL', req: true, ph: '192.168.10.50:/images/aci-n9000-dk9.16.0.6c.bin', help: 'SCP/SFTP: host:/pfad/datei, HTTP: http://host/pfad/datei' },
      { k: 'user', l: 'Username', ph: 'backup' }, { k: 'password', l: 'Password', t: 'password' }],
    cols: [ac('name'), col('Protocol', r => r.proto), col('URL', r => r.url), col('Status', r => Views.dlStatus(r))],
  },
  firmwareCtrlrFwP: {
    label: 'Controller Firmware',
    fields: [{ k: 'version', l: 'Target Firmware Version', t: 'select', o: fwVersions('controller') }, { k: 'ignoreCompat', l: 'Ignore Compatibility Check', t: 'radio', o: [['false', 'No'], ['true', 'Yes']] }],
    actions: [['Upgrade Controller Now', () => trigger('uni/controller/ctrlrmaintpol', 'maintCtrlrMaintP', 'Controller-Upgrade ausgelöst')()]],
  },
  maintMaintP: {
    label: 'Upgrade Policy',
    fields: [NAME, { k: 'version', l: 'Target Firmware Version', t: 'select', o: fwVersions('switch') },
      { k: 'graceful', l: 'Graceful Maintenance', t: 'yesno', help: 'Switch vor dem Reload per GIR aus dem Forwarding nehmen' },
      { k: 'runMode', l: 'Run Mode', t: 'radio', o: [['pauseOnlyOnFailures', 'Pause only upon upgrade failure'], ['pauseNever', 'Do not pause on failure']] },
      { k: 'ignoreCompat', l: 'Ignore Compatibility Check', t: 'radio', o: [['false', 'No'], ['true', 'Yes']] },
      { k: 'adminSt', l: 'Upgrade Start', t: 'radio', o: TRIGGERED }],
    cols: [ac('name'), col('Target Version', r => r.version || '—'), col('Graceful', r => r.graceful)],
  },
  maintMaintGrp: {
    label: 'Upgrade Group', menu: 'Create Node Upgrade Group',
    fields: [NAME, relName('maintRsMgrpp', 'tnMaintMaintPName', 'Upgrade Policy', 'maintMaintP', { scope: 'fabric', req: true })],
    cols: [ac('name'), col('Nodes', r => blocks(r.dn) || '—'), col('Upgrade Policy', r => relOf(r.dn, 'maintRsMgrpp', 'tnMaintMaintPName')),
      col('Target Version', r => { const p = MIT.a('uni/fabric/maintpol-' + relOf(r.dn, 'maintRsMgrpp', 'tnMaintMaintPName')); return p ? p.version || '—' : '—'; })],
    wizard: {
      title: 'Create Node Upgrade Group',
      steps: [{ l: 'Group', fields: [NAME, { k: '_ver', l: 'Target Firmware Version', t: 'select', o: fwVersions('switch'), req: true },
        { k: '_graceful', l: 'Graceful Maintenance', t: 'yesno', def: 'no' },
        { k: '_n', l: 'Nodes', t: 'rows', start: true, cols: [{ k: 'from', l: 'Von Node-ID', ph: '101' }, { k: 'to', l: 'Bis Node-ID', ph: '101' }] },
        { k: '_now', l: 'Upgrade sofort starten', t: 'yesno', def: 'no', help: 'Sonst später über Actions > Upgrade Now' }] }],
      build: v => ({ url: 'uni/fabric', dn: 'uni/fabric/maintgrp-' + v.name, body: mo('fabricInst', {},
        mo('maintMaintP', { name: v.name, version: v._ver, graceful: v._graceful, adminSt: v._now === 'yes' ? 'triggered' : 'untriggered' }),
        mo('maintMaintGrp', { name: v.name }, mo('maintRsMgrpp', { tnMaintMaintPName: v.name }),
          (v._n || []).filter(n => n.from).map((n, i) => mo('fabricNodeBlk', { name: 'blk' + (i + 1), from_: String(n.from), to_: String(n.to || n.from) })))) }),
    },
    actions: [['Upgrade Now', dn => trigger('uni/fabric/maintpol-' + relOf(dn, 'maintRsMgrpp', 'tnMaintMaintPName'), 'maintMaintP', 'Upgrade ausgelöst')()],
      ['Add Nodes', dn => createDialog(dn, 'fabricNodeBlk')]],
  },
  fabricNodeBlk: { label: 'Node Block', fields: [NAME, { k: 'from_', l: 'From', req: true, ph: '101' }, { k: 'to_', l: 'To', req: true, ph: '102' }],
    cols: [ac('name'), col('From', r => r.from_), col('To', r => r.to_)] },

  /* ---------------- Import/Export ---------------- */
  pkiExportEncryptionKey: {
    label: 'Global AES Passphrase Encryption Settings',
    fields: [{ k: 'strongEncryptionEnabled', l: 'Enable Encryption', t: 'yesno' }, { k: 'passphrase', l: 'Passphrase', t: 'password', help: 'Mindestens 16 Zeichen. Ohne Verschlüsselung enthält ein Export keine Passwörter und Keys.' }],
    normalize: v => { if (!v.passphrase) delete v.passphrase; else if (v.passphrase.length < 16) throw new ApiError('Eingabe', 'Die Passphrase braucht mindestens 16 Zeichen'); return v; },
  },
  fileRemotePath: {
    label: 'Remote Location', menu: 'Create Remote Location',
    fields: [NAME, { k: 'host', l: 'Host Name/IP Address', req: true, ph: '192.168.10.50' }, { k: 'protocol', l: 'Protocol', t: 'radio', o: [['scp', 'SCP'], ['sftp', 'SFTP'], ['ftp', 'FTP']], def: 'scp' },
      { k: 'remotePath', l: 'Remote Path', ph: '/backup' }, { k: 'remotePort', l: 'Remote Port', def: '22' }, { k: 'userName', l: 'Username' }, { k: 'userPasswd', l: 'Password', t: 'password' },
      relDn('fileRsARemoteHostToEpg', 'Management EPG', ['mgmtOoB', 'mgmtInB'], { req: true })],
    normalize: v => { if (!v.userPasswd) delete v.userPasswd; return v; },
    cols: [ac('name'), col('Host', r => r.host), col('Protocol', r => r.protocol), col('Path', r => r.remotePath), col('User', r => r.userName)],
  },
  configExportP: {
    label: 'Configuration Export Policy', menu: 'Create Configuration Export Policy',
    fields: [NAME, { k: 'format', l: 'Format', t: 'radio', o: [['json', 'JSON'], ['xml', 'XML']] }, { k: 'snapshot', l: 'Snapshot', t: 'radio', o: [['false', 'No (Remote Location)'], ['true', 'Yes (auf dem APIC)']] },
      { k: 'targetDn', l: 'Target DN', ph: 'leer = gesamte Fabric, z. B. uni/tn-Shop' }, { k: 'includeSecureFields', l: 'Include Secure Fields', t: 'yesno' },
      relName('configRsRemotePath', 'tnFileRemotePathName', 'Remote Location', 'fileRemotePath', { scope: 'fabric' }), { k: 'adminSt', l: 'Start Now', t: 'radio', o: TRIGGERED }, DESCR],
    cols: [ac('name'), col('Target', r => r.targetDn || '(Fabric)'), col('Snapshot', r => r.snapshot), col('Remote Location', r => remoteRow(r.dn) || '—'), col('Letzter Lauf', r => Views.lastJob(r.dn))],
    actions: [['Start Export Now', dn => trigger(dn, 'configExportP', 'Export gestartet')()]],
  },
  configImportP: {
    label: 'Configuration Import Policy', menu: 'Create Configuration Import Policy',
    fields: [NAME, { k: 'fileName', l: 'File Name', req: true, ph: 'ce2_Backup-2026-10-27T10-00-00.tar.gz' }, { k: 'importType', l: 'Import Type', t: 'radio', o: [['merge', 'Merge'], ['replace', 'Replace']] },
      { k: 'importMode', l: 'Import Mode', t: 'radio', o: [['atomic', 'Atomic'], ['best-effort', 'Best Effort']] }, { k: 'snapshot', l: 'Snapshot vor dem Import', t: 'radio', o: [['false', 'No'], ['true', 'Yes']] },
      relName('configRsRemotePath', 'tnFileRemotePathName', 'Remote Location', 'fileRemotePath', { scope: 'fabric', req: true }), { k: 'adminSt', l: 'Start Now', t: 'radio', o: TRIGGERED }, DESCR],
    cols: [ac('name'), col('File', r => r.fileName), col('Type', r => r.importType + ' / ' + r.importMode), col('Remote Location', r => remoteRow(r.dn) || '—'), col('Letzter Lauf', r => Views.lastJob(r.dn))],
    actions: [['Start Import Now', dn => trigger(dn, 'configImportP', 'Import gestartet')()]],
  },

  /* ---------------- Monitoring ---------------- */
  snmpPol: {
    label: 'SNMP Policy', fields: [NAME, { k: 'adminSt', l: 'Admin State', t: 'ed' }, { k: 'contact', l: 'Contact', ph: 'noc@firma.de' }, { k: 'loc', l: 'Location', ph: 'RZ1 Reihe 4' }, DESCR],
    cols: [ac('name'), col('Admin State', r => r.adminSt), col('Communities', r => MIT.kids(r.dn, ['snmpCommunityP']).map(d => MIT.a(d).name).join(', '))],
    wizard: { title: 'Create SNMP Policy', steps: [{ l: 'SNMP Policy', fields: [NAME, { k: 'adminSt', l: 'Admin State', t: 'ed', def: 'enabled' }, { k: 'contact', l: 'Contact' }, { k: 'loc', l: 'Location' },
      { k: '_c', l: 'Community Policies', t: 'rows', start: true, cols: [{ k: 'name', l: 'Community', ph: 'NMS-Read' }] },
      { k: '_g', l: 'Client Group: Client-Adressen (Management EPG Out-of-Band)', t: 'rows', start: true, cols: [{ k: 'addr', l: 'Client IP', ph: '192.168.10.61' }] }] }],
    build: (v, parent) => ({ dn: parent + '/snmppol-' + v.name, body: mo('snmpPol', { name: v.name, adminSt: v.adminSt, contact: v.contact, loc: v.loc },
      (v._c || []).filter(c => c.name).map(c => mo('snmpCommunityP', { name: c.name })),
      (v._g || []).some(c => c.addr) ? mo('snmpClientGrpP', { name: 'nms' }, mo('snmpRsEpg', { tDn: 'uni/tn-mgmt/mgmtp-default/oob-default' }),
        v._g.filter(c => c.addr).map(c => mo('snmpClientP', { addr: c.addr }))) : null) }) },
  },
  snmpCommunityP: { label: 'Community Policy', fields: [{ k: 'name', l: 'Community', create: true, req: true }, DESCR], cols: [ac('name')] },
  snmpClientGrpP: { label: 'Client Group Policy', fields: [NAME, relDn('snmpRsEpg', 'Management EPG', ['mgmtOoB', 'mgmtInB'], { req: true })],
    cols: [ac('name'), col('EPG', r => nameOfDn(relOf(r.dn, 'snmpRsEpg', 'tDn'))), col('Clients', r => MIT.kids(r.dn, ['snmpClientP']).map(d => MIT.a(d).addr).join(', '))] },
  snmpClientP: { label: 'Client Entry', fields: [{ k: 'addr', l: 'Address', create: true, req: true }, { k: 'name', l: 'Name' }], cols: [col('Address', r => r.addr), ac('name')] },
  snmpGroup: { label: 'SNMP Monitoring Destination Group', menu: 'Create SNMP Monitoring Destination Group', fields: [NAME, DESCR],
    cols: [ac('name'), col('Trap Destinations', r => MIT.kids(r.dn, ['snmpTrapDest']).map(d => MIT.a(d).host + ':' + MIT.a(d).port).join(', '))] },
  snmpTrapDest: { label: 'SNMP Trap Destination', fields: [{ k: 'host', l: 'Host Name/IP', create: true, req: true }, { k: 'port', l: 'Port', create: true, def: '162' },
    { k: 'ver', l: 'Version', t: 'radio', o: [['v1', 'v1'], ['v2c', 'v2c'], ['v3', 'v3']], def: 'v2c' }, { k: 'secName', l: 'Community/Security Name', req: true },
    relDn('snmpRsARemoteHostToEpg', 'Management EPG', ['mgmtOoB', 'mgmtInB'], { req: true })],
    cols: [col('Host', r => r.host), col('Port', r => r.port), col('Version', r => r.ver), col('Community', r => r.secName)] },
  syslogGroup: { label: 'Syslog Monitoring Destination Group', menu: 'Create Syslog Monitoring Destination Group',
    fields: [NAME, { k: 'format', l: 'Format', t: 'radio', o: [['aci', 'aci'], ['nxos', 'nxos'], ['rfc5424-ietf', 'rfc5424-ietf']] }, DESCR],
    cols: [ac('name'), col('Format', r => r.format), col('Destinations', r => MIT.kids(r.dn, ['syslogRemoteDest']).map(d => MIT.a(d).host).join(', '))] },
  syslogRemoteDest: { label: 'Syslog Remote Destination', fields: [{ k: 'host', l: 'Host Name/IP', create: true, req: true }, { k: 'name', l: 'Name' },
    { k: 'adminState', l: 'Admin State', t: 'ed', def: 'enabled' }, { k: 'severity', l: 'Severity', t: 'select', o: SYSLOG_SEVS, def: 'warnings' },
    { k: 'port', l: 'Port', def: '514' }, { k: 'forwardingFacility', l: 'Forwarding Facility', t: 'select', o: [0, 1, 2, 3, 4, 5, 6, 7].map(i => ['local' + i, 'local' + i]), def: 'local7' },
    relDn('fileRsARemoteHostToEpg', 'Management EPG', ['mgmtOoB', 'mgmtInB'], { req: true })],
    cols: [col('Host', r => r.host), col('Severity', r => r.severity), col('Port', r => r.port), col('Admin', r => r.adminState)] },
  callhomeGroup: { label: 'Callhome Destination Group', menu: 'Create Callhome Destination Group', fields: [NAME, DESCR],
    cols: [ac('name'), col('From', r => (MIT.a(r.dn + '/prof') || {}).from || '—'), col('SMTP', r => (MIT.a(r.dn + '/prof/smtp') || {}).host || '—'),
      col('Destinations', r => MIT.kids(r.dn, ['callhomeDest']).map(d => MIT.a(d).email).join(', '))],
    wizard: { title: 'Create Callhome Destination Group', steps: [{ l: 'Profil', fields: [NAME, { k: '_from', l: 'From Email', req: true, ph: 'apic@firma.de' }, { k: '_contact', l: 'Contact', ph: 'NOC' },
      { k: '_smtp', l: 'SMTP Server', req: true, ph: '192.168.10.62' }, { k: '_port', l: 'SMTP Port', def: '25' },
      { k: '_d', l: 'Destinations', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'noc' }, { k: 'email', l: 'Email', ph: 'noc@firma.de' }, { k: 'format', l: 'Format', t: 'select', o: [['aml', 'aml'], ['short-txt', 'short-txt'], ['xml', 'xml']] }] }] }],
    build: (v, parent) => ({ dn: parent + '/chgroup-' + v.name, body: mo('callhomeGroup', { name: v.name },
      mo('callhomeProf', { from: v._from, contact: v._contact, port: v._port || '25' }, mo('callhomeSmtpServer', { host: v._smtp }, mo('fileRsARemoteHostToEpg', { tDn: 'uni/tn-mgmt/mgmtp-default/oob-default' }))),
      (v._d || []).filter(d => d.name).map(d => mo('callhomeDest', { name: d.name, email: d.email, format: d.format || 'aml' }))) }) },
  },
  callhomeProf: { label: 'Callhome Profile', fields: [{ k: 'from', l: 'From Email' }, { k: 'replyTo', l: 'Reply-To Email' }, { k: 'contact', l: 'Contact' }, { k: 'email', l: 'Contact Email' }, { k: 'phone', l: 'Phone' }, { k: 'customer', l: 'Customer ID' }, { k: 'site', l: 'Site ID' }, { k: 'port', l: 'SMTP Port' }] },
  callhomeSmtpServer: { label: 'SMTP Server', fields: [{ k: 'host', l: 'SMTP Server', req: true }, relDn('fileRsARemoteHostToEpg', 'Management EPG', ['mgmtOoB', 'mgmtInB'])] },
  callhomeDest: { label: 'Callhome Destination', fields: [NAME, { k: 'email', l: 'Email', req: true }, { k: 'format', l: 'Format', t: 'radio', o: [['aml', 'aml'], ['short-txt', 'short-txt'], ['xml', 'xml']] }, { k: 'adminState', l: 'Admin State', t: 'ed', def: 'enabled' }],
    cols: [ac('name'), col('Email', r => r.email), col('Format', r => r.format), col('Admin', r => r.adminState)] },
  syslogSrc: { label: 'Syslog Source', menu: 'Create Syslog Source', fields: [NAME, { k: 'minSev', l: 'Min Severity', t: 'select', o: FAULT_SEVS, def: 'warning' },
    { k: 'incl', l: 'Include', t: 'checks', o: INCL, def: 'faults' }, relDn('syslogRsDestGroup', 'Dest Group', 'syslogGroup', { req: true })],
    cols: [ac('name'), col('Min Severity', r => r.minSev), col('Include', r => r.incl), col('Dest Group', r => nameOfDn(relOf(r.dn, 'syslogRsDestGroup', 'tDn')))] },
  snmpSrc: { label: 'SNMP Source', menu: 'Create SNMP Source', fields: [NAME, { k: 'minSev', l: 'Min Severity', t: 'select', o: FAULT_SEVS, def: 'warning' },
    { k: 'incl', l: 'Include', t: 'checks', o: INCL, def: 'faults' }, relDn('snmpRsDestGroup', 'Dest Group', 'snmpGroup', { req: true })],
    cols: [ac('name'), col('Min Severity', r => r.minSev), col('Include', r => r.incl), col('Dest Group', r => nameOfDn(relOf(r.dn, 'snmpRsDestGroup', 'tDn')))] },
  callhomeSrc: { label: 'Callhome Source', fields: [{ k: 'minSev', l: 'Min Severity', t: 'select', o: FAULT_SEVS, def: 'major' },
    { k: 'incl', l: 'Include', t: 'checks', o: INCL, def: 'faults' }, relDn('callhomeRsDestGroup', 'Dest Group', 'callhomeGroup', { req: true })],
    cols: [col('Min Severity', r => r.minSev), col('Include', r => r.incl), col('Dest Group', r => nameOfDn(relOf(r.dn, 'callhomeRsDestGroup', 'tDn')))] },

  /* ---------------- DHCP Relay ---------------- */
  dhcpRelayP: {
    label: 'DHCP Relay Policy', menu: 'Create DHCP Relay Policy',
    fields: [NAME, DESCR], cols: [ac('name'), col('Owner', r => r.owner), col('Providers', r => MIT.kids(r.dn, ['dhcpRsProv']).map(d => MIT.a(d).addr + ' (' + nameOfDn(MIT.a(d).tDn) + ')').join(', '))],
    wizard: { title: 'Create DHCP Relay Policy', steps: [{ l: 'Policy', fields: [NAME, DESCR,
      { k: '_p', l: 'Providers', t: 'rows', start: true, cols: [{ k: 'tDn', l: 'EPG (Application EPG des DHCP-Servers)', t: 'tdn', target: ['fvAEPg', 'l3extInstP'], tenantScope: true }, { k: 'addr', l: 'DHCP Server Address', ph: '10.1.2.10' }] }] }],
    build: (v, parent) => ({ dn: parent + '/relayp-' + v.name, body: mo('dhcpRelayP', { name: v.name, descr: v.descr, owner: parent === 'uni/infra' ? 'infra' : 'tenant' },
      (v._p || []).filter(p => p.tDn).map(p => mo('dhcpRsProv', { tDn: p.tDn, addr: p.addr }))) }) },
  },
  dhcpRsProv: { label: 'DHCP Provider', fields: [{ k: 'tDn', l: 'EPG', t: 'tdn', target: ['fvAEPg', 'l3extInstP'], create: true, req: true }, { k: 'addr', l: 'DHCP Server Address', req: true }],
    cols: [col('EPG', r => r.tDn), col('Server', r => r.addr), col('State', relState)] },
  dhcpLbl: { label: 'DHCP Relay Label', fields: [{ k: 'owner', l: 'Scope', t: 'radio', o: [['tenant', 'tenant'], ['infra', 'infra']], create: true, def: 'tenant' },
    { k: 'name', l: 'Name (DHCP Relay Policy)', create: true, req: true, ph: 'Name der DHCP Relay Policy' }],
    cols: [ac('name'), col('Scope', r => r.owner)] },

  /* ---------------- QoS / MCP / Loop Protection ---------------- */
  qosInstPol: { label: 'QOS Class Policies', fields: [{ k: 'ctrl', l: 'Preserve CoS', t: 'checks', o: [['dot1p-preserve', 'Dot1p Preserve']] }] },
  qosClass: { label: 'QoS Class', fields: [{ k: 'admin', l: 'Admin State', t: 'ed' }, { k: 'mtu', l: 'MTU' }],
    cols: [col('Class', r => r.prio), col('Admin', r => r.admin), col('MTU', r => r.mtu), col('Scheduling', r => { const s = MIT.a(r.dn + '/sched') || {}; return (s.meth || 'wrr') + ' ' + (s.bw || '') + '%'; })] },
  mcpInstPol: { label: 'MCP Instance Policy', fields: [{ k: 'adminSt', l: 'Admin State', t: 'ed' }, { k: 'key', l: 'Key', t: 'password', help: 'Ohne Key sendet MCP keine PDUs' },
    { k: 'ctrl', l: 'Controls', t: 'checks', o: [['pdu-per-vlan', 'Enable MCP PDU per VLAN']] }, { k: 'loopDetectMult', l: 'Loop Detect Multiplication Factor' },
    { k: 'loopProtectAct', l: 'Loop Protection Action', t: 'radio', o: [['port-disable', 'Port Disable'], ['none', 'none']] },
    { k: 'initDelayTime', l: 'Initial Delay (sec)' }, { k: 'txFreq', l: 'Transmission Frequency (sec)' }],
    normalize: v => { if (!v.key) delete v.key; return v; } },
  epLoopProtectP: { label: 'EP Loop Protection Policy', fields: [{ k: 'adminSt', l: 'Admin State', t: 'ed' }, { k: 'loopDetectIntvl', l: 'Loop Detection Interval (sec)' }, { k: 'loopDetectMult', l: 'Loop Detection Multiplication Factor' },
    { k: 'action', l: 'Action', t: 'checks', o: [['bd-learn-disable', 'BD Learn Disable'], ['port-disable', 'Port Disable']] }] },
});

/* bestehende Specs ergaenzen */
SPEC.fabricPodPGrp.fields.push(relName('fabricRsSnmpPol', 'tnSnmpPolName', 'SNMP Policy', 'snmpPol', { scope: 'fabric', empty: 'default', keepEmpty: true }));
SPEC.fabricPodPGrp.cols.push(col('SNMP Policy', r => relOf(r.dn, 'fabricRsSnmpPol', 'tnSnmpPolName') || 'default'));

Object.assign(TREE, {
  maintMaintGrp: [{ l: 'Node Blocks', cls: ['fabricNodeBlk'], flat: 1 }],
  snmpPol: [{ l: 'Community Policies', cls: ['snmpCommunityP'], flat: 1 }, { l: 'Client Group Policies', cls: ['snmpClientGrpP'] }],
  snmpClientGrpP: [{ l: 'Client Entries', cls: ['snmpClientP'], flat: 1 }],
  snmpGroup: [{ l: 'Trap Destinations', cls: ['snmpTrapDest'], flat: 1 }],
  syslogGroup: [{ l: 'Remote Destinations', cls: ['syslogRemoteDest'], flat: 1 }],
  callhomeGroup: [{ l: 'Profile', rn: 'prof' }, { l: 'Destinations', cls: ['callhomeDest'], flat: 1 }],
  callhomeProf: [{ l: 'SMTP Server', rn: 'smtp' }],
  dhcpRelayP: [{ l: 'Providers', cls: ['dhcpRsProv'], flat: 1 }],
  qosInstPol: [{ l: 'Classes', cls: ['qosClass'], flat: 1 }],
  monCommonPol: [{ l: 'Callhome/Smart Callhome', cls: ['callhomeSrc'], flat: 1, max: 1 }, { l: 'SNMP', cls: ['snmpSrc'], flat: 1 }, { l: 'Syslog', cls: ['syslogSrc'], flat: 1 }],
});
TREE.fvBD.push({ l: 'DHCP Relay Labels', cls: ['dhcpLbl'], flat: 1 });
(function () {
  const pol = TREE.fvTenant.find(s => s.l === 'Policies').sub.find(s => s.l === 'Protocol').sub;
  const i = pol.findIndex(s => s.l === 'DHCP');
  pol[i] = { l: 'DHCP', sub: [{ l: 'Relay Policies', cls: ['dhcpRelayP'] }, PH('Option Policies')] };
  const pod = FABRICPOL_TREE.find(s => s.l === 'Policies').sub;
  const p = pod.find(s => s.l === 'Pod').sub;
  p[p.findIndex(s => s.l === 'SNMP')] = { l: 'SNMP', cls: ['snmpPol'], parent: 'uni/fabric' };
  pod[pod.findIndex(s => s.l === 'Monitoring')] = { l: 'Monitoring', sub: [{ l: 'Common Policy', mo: 'uni/fabric/moncommon' }, PH('default'), PH('Fabric Node Controls')] };
  const glob = ACCESS_TREE.find(s => s.l === 'Policies').sub.find(s => s.l === 'Global').sub;
  glob[glob.findIndex(s => s.l === 'QOS Class')] = { l: 'QOS Class', mo: 'uni/infra/qosinst-default' };
  glob[glob.findIndex(s => s.l === 'DHCP Relay')] = { l: 'DHCP Relay', cls: ['dhcpRelayP'], parent: 'uni/infra' };
  glob[glob.findIndex(s => s.l === 'MCP Instance Policy default')] = { l: 'MCP Instance Policy default', mo: 'uni/infra/mcpInstP-default' };
}());

const FIRMWARE_TREE = [
  { l: 'Upgrade-Übersicht', view: w => Views.fwOverview(w) },
  { l: 'Infrastructure', sub: [{ l: 'Controllers', mo: 'uni/controller/ctrlrfwpol' },
    { l: 'Nodes (Upgrade Groups)', cls: ['maintMaintGrp'], parent: 'uni/fabric' }, { l: 'Upgrade Policies', cls: ['maintMaintP'], parent: 'uni/fabric' }] },
  { l: 'Images', view: w => Views.fwImages(w) },
  { l: 'Download Tasks', cls: ['firmwareOSource'], parent: 'uni/fabric/fwrepop' },
];
const IMPEXP_TREE = [
  { l: 'Export Policies', sub: [{ l: 'Configuration', cls: ['configExportP'], parent: 'uni/fabric' }] },
  { l: 'Import Policies', sub: [{ l: 'Configuration', cls: ['configImportP'], parent: 'uni/fabric' }] },
  { l: 'Remote Locations', cls: ['fileRemotePath'], parent: 'uni/fabric' },
  { l: 'Global AES Encryption', mo: 'uni/exportcryptkey' },
  { l: 'Jobs', view: w => Views.configJobs(w) },
  { l: 'JSON Save as / Upload', view: w => Views.jsonImpExp(w) },
];
const COLLECTORS_TREE = [
  { l: 'Monitoring Destinations', sub: [{ l: 'Callhome', cls: ['callhomeGroup'], parent: 'uni/fabric' }, { l: 'SNMP', cls: ['snmpGroup'], parent: 'uni/fabric' }, { l: 'Syslog', cls: ['syslogGroup'], parent: 'uni/fabric' }] },
  { l: 'Zustellung (Zustand)', view: w => Views.monStatus(w) },
];
Object.assign(ICON, { maintMaintGrp: 'UG', maintMaintP: 'UP', firmwareOSource: 'DL', configExportP: 'EX', configImportP: 'IM', fileRemotePath: 'RL', snmpPol: 'SN', snmpGroup: 'SN',
  syslogGroup: 'SL', callhomeGroup: 'CH', dhcpRelayP: 'DH', qosInstPol: 'Q', mcpInstPol: 'MCP', monCommonPol: 'MON', snmpClientGrpP: 'CG', callhomeProf: 'P', callhomeSmtpServer: 'S' });
