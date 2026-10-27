/* Multi-Pod und Remote Leaf: Pod Fabric Setup Policy, Wizards, IPN-Simulation */
'use strict';

Object.assign(SPEC, {
  fabricSetupP: { label: 'Pod TEP Pool', fields: [{ k: 'podId', l: 'Pod ID', create: true, req: true, ph: '2' }, { k: 'tepPool', l: 'TEP Pool', req: true, ph: '10.1.0.0/16' }],
    cols: [col('Pod', r => r.podId), col('TEP Pool', r => r.tepPool), col('Remote Pools', r => MIT.kids(r.dn, ['fabricExtSetupP']).map(d => MIT.a(d).remoteId + ': ' + MIT.a(d).tepPool).join(', ') || '—')] },
  fabricExtSetupP: { label: 'Remote Pool', fields: [{ k: 'remoteId', l: 'Remote ID', create: true, req: true, ph: '11' }, { k: 'tepPool', l: 'Remote Pool', req: true, ph: '10.11.0.0/20' }],
    cols: [col('Remote ID', r => r.remoteId), col('Pool', r => r.tepPool)] },
  fabricExtConnP: { label: 'Fabric External Connection Policy', fields: [{ k: 'id', l: 'ID', create: true, req: true, def: '1' }, NAME, { k: 'rt', l: 'Community', def: 'extended:as2-nn4:5:16' }],
    cols: [col('ID', r => r.id), ac('name'), col('Community', r => r.rt), col('Pods', r => MIT.kids(r.dn, ['fabricPodConnP']).map(d => MIT.a(d).id).join(', '))] },
  fabricPodConnP: { label: 'Pod Connection Profile', fields: [{ k: 'id', l: 'Pod ID', create: true, req: true }],
    cols: [col('Pod', r => r.id), col('Data Plane TEP', r => MIT.kids(r.dn, ['fabricIp']).map(d => MIT.a(d).addr).join(', ') || '—'),
      col('External TEP', r => MIT.kids(r.dn, ['fabricExtRoutablePodSubnet']).map(d => MIT.a(d).pool).join(', ') || '—')] },
  fabricIp: { label: 'Data Plane TEP', fields: [{ k: 'addr', l: 'Address', create: true, req: true, ph: '172.16.1.1/32' }], cols: [col('Address', r => r.addr)] },
  fabricExtRoutablePodSubnet: { label: 'External TEP Pool', fields: [{ k: 'pool', l: 'Pool', create: true, req: true, ph: '172.16.10.0/24' }], cols: [col('Pool', r => r.pool)] },
  fabricPeeringP: { label: 'Fabric Peering Profile', fields: [{ k: 'type', l: 'Peering Type', t: 'radio', o: [['automatic_with_full_mesh', 'Full Mesh'], ['automatic_with_rr', 'Route Reflector']] }] },
});
Object.assign(TREE, {
  fabricSetupP: [{ l: 'Remote Pools', cls: ['fabricExtSetupP'], flat: 1 }],
  fabricExtConnP: [{ l: 'Pod Connection Profiles', cls: ['fabricPodConnP'] }, { l: 'Fabric Peering Profile', rn: 'peeringP' }],
  fabricPodConnP: [{ l: 'Data Plane TEP', cls: ['fabricIp'], flat: 1 }, { l: 'External TEP Pools', cls: ['fabricExtRoutablePodSubnet'], flat: 1 }],
});
const INFRA_TREE = [{ l: 'Fabric Ext Connection Policies', cls: ['fabricExtConnP'], parent: 'uni/tn-infra' }];
Object.assign(ICON, { fabricExtConnP: 'EXT', fabricPodConnP: 'P', fabricSetupP: 'P' });

Object.assign(Views, {
  async podSetup(w) {
    await MIT.load('uni/controller/setuppol');
    const draw = () => {
      clear(w);
      w.appendChild(paneHead('Pod Fabric Setup Policy', 'TEP Pool je Pod und Remote Pools für Remote Leafs', [
        h('button', { class: 'btn primary small', onclick: () => createDialog('uni/controller/setuppol', 'fabricSetupP', 'Setup Pod (TEP Pool)') }, '+ Pod'),
        h('button', { class: 'btn small', onclick: () => createDialog('uni/controller/setuppol/setupp-1', 'fabricExtSetupP', 'Add Remote Pool (Pod 1)') }, '+ Remote Pool')]));
      w.appendChild(h('div', { class: 'card note' }, md('Pod 1 bekommt seinen TEP Pool aus dem Setup-Dialog des APIC. Jeder weitere Pod braucht hier einen eigenen, überschneidungsfreien Pool **bevor** seine Spines über das IPN entdeckt werden. Remote Leafs bekommen ihre TEP-Adressen aus einem **Remote Pool** (Remote ID) des Pods, zu dem sie gehören.')));
      folderView(w, 'uni/controller/setuppol', { l: 'Pods', cls: ['fabricSetupP'] }, true);
    };
    draw();
  },

  invQuickStart(w) {
    w.appendChild(paneHead('Inventory – Quick Start', ''));
    w.appendChild(h('div', { class: 'card' }, md('Neue Switches registrierst du unter **Fabric Membership**. Die Topologie zeigt den Zustand der Fabric.\n\n**Multi-Pod und Remote Leaf** (Lab 29 lädt die passende Topologie mit IPN):'),
      h('div', { class: 'formbtns' }, h('button', { class: 'btn primary', onclick: () => Views.addPodWizard() }, 'Add Pod (IPN-Anbindung)'),
        h('button', { class: 'btn', onclick: () => Views.addRlWizard() }, 'Add Remote Leaf'))));
  },

  addPodWizard() {
    const spines = (App.state.nodes || []).filter(n => n.role === 'spine');
    const f = buildForm([{ k: 'podId', l: 'Neuer Pod', req: true, ph: '2' }, { k: 'tepPool', l: 'TEP Pool des neuen Pods', req: true, ph: '10.1.0.0/16' },
      { k: 'area', l: 'OSPF Area zum IPN', ph: '0.0.0.0' }, { k: 'tep1', l: 'Data Plane TEP Pod 1', ph: '172.16.1.1/32' }, { k: 'tep2', l: 'Data Plane TEP neuer Pod', ph: '172.16.2.1/32' },
      { k: '_s', l: 'Spine-Interfaces zum IPN (Sub-Interface vlan-4)', t: 'rows', start: true, cols: [{ k: 'node', l: 'Node-ID', ph: '201' }, { k: 'pod', l: 'Pod', ph: '1' },
        { k: 'port', l: 'Port', ph: 'eth1/32' }, { k: 'ip', l: 'IP/Maske', ph: '192.168.1.1/30' }, { k: 'rid', l: 'Router ID', ph: '201.201.201.201' }] }],
    { podId: '2', tepPool: '10.1.0.0/16', area: '0.0.0.0', tep1: '172.16.1.1/32', tep2: '172.16.2.1/32',
      _s: spines.length ? spines.map((n, i) => ({ node: String(n.id || ''), pod: String(n.pod || 1), port: 'eth1/32', ip: '', rid: '' })) : [{ port: 'eth1/32' }] }, {}, 'create');
    modal('Add Pod – Multi-Pod einrichten', h('div', null, h('p', { class: 'muted' }, 'Legt den TEP Pool an, das Infra-L3Out multipod (Tenant infra, VRF overlay-1, OSPF und BGP) mit den Spine-Interfaces und die Fabric External Connection Policy mit den Data Plane TEPs. Spines eines neuen Pods, die noch nicht registriert sind, kannst du später ergänzen.'), f.el),
      [{ l: 'Abbrechen' }, { l: 'Anlegen', primary: true, fn: async () => {
        const v = f.get();
        const rows = (v._s || []).filter(r => r.node && r.ip);
        await API.postMo('uni/controller/setuppol', mo('fabricSetupPol', {}, mo('fabricSetupP', { podId: v.podId, tepPool: v.tepPool })));
        await API.postMo('uni/tn-infra', mo('fvTenant', {}, mo('l3extOut', { name: 'multipod' }, mo('l3extRsEctx', { tnFvCtxName: 'overlay-1' }),
          mo('ospfExtP', { areaId: v.area || '0.0.0.0' }), mo('bgpExtP', {}),
          mo('l3extLNodeP', { name: 'spines' }, rows.map(r => mo('l3extRsNodeL3OutAtt', { tDn: 'topology/pod-' + (r.pod || 1) + '/node-' + r.node, rtrId: r.rid || (r.node + '.' + r.node + '.' + r.node + '.' + r.node) })),
            rows.map(r => mo('l3extLIfP', { name: 'ipn-' + r.node }, mo('ospfIfP', {}), mo('l3extRsPathL3OutAtt', { tDn: 'topology/pod-' + (r.pod || 1) + '/paths-' + r.node + '/pathep-[' + (r.port || 'eth1/32') + ']', ifInstT: 'sub-interface', encap: 'vlan-4', addr: r.ip }))))),
          mo('fabricExtConnP', { id: '1', name: 'Multipod' }, mo('fabricPeeringP', { type: 'automatic_with_full_mesh' }),
            mo('fabricPodConnP', { id: '1' }, v.tep1 ? mo('fabricIp', { addr: v.tep1 }) : null),
            mo('fabricPodConnP', { id: v.podId }, v.tep2 ? mo('fabricIp', { addr: v.tep2 }) : null))));
        toast('Multi-Pod-Konfiguration angelegt');
        await App.refreshState();
      } }], { wide: true });
  },

  addRlWizard() {
    const f = buildForm([{ k: 'remoteId', l: 'Remote ID', req: true, ph: '11' }, { k: 'pool', l: 'Remote Pool', req: true, ph: '10.11.0.0/20' },
      { k: 'ext', l: 'External TEP Pool (Pod 1)', req: true, ph: '172.16.10.0/24', help: 'Routbare Adressen, unter denen das Remote Leaf die Spines und APICs erreicht' },
      { k: 'serial', l: 'Serial Remote Leaf', req: true, ph: 'SAL1931RL01' }, { k: 'nodeId', l: 'Node ID', req: true, ph: '301' }, { k: 'name', l: 'Name', req: true, ph: 'leaf301' },
      { k: 'port', l: 'Uplink-Port zum WAN-Router', ph: 'eth1/54' }, { k: 'ip', l: 'Uplink-IP (Sub-Interface vlan-4)', req: true, ph: '192.168.3.1/30' }, { k: 'rid', l: 'Router ID', ph: '30.30.30.30' }],
    { remoteId: '11', pool: '10.11.0.0/20', ext: '172.16.10.0/24', serial: 'SAL1931RL01', nodeId: '301', name: 'leaf301', port: 'eth1/54', rid: '30.30.30.30' }, {}, 'create');
    modal('Add Remote Leaf', h('div', null, h('p', { class: 'muted' }, 'Remote Pool, External TEP Pool, Registrierung als remote-leaf-wan und das Uplink-Interface im Infra-L3Out multipod. Das Infra-L3Out mit den Spines muss es schon geben (Add Pod oder von Hand).'), f.el),
      [{ l: 'Abbrechen' }, { l: 'Anlegen', primary: true, fn: async () => {
        const v = f.get();
        await API.postMo('uni/controller/setuppol/setupp-1', mo('fabricSetupP', {}, mo('fabricExtSetupP', { remoteId: v.remoteId, tepPool: v.pool })));
        await API.postMo('uni/tn-infra', mo('fvTenant', {}, mo('fabricExtConnP', { id: '1' }, mo('fabricPodConnP', { id: '1' }, mo('fabricExtRoutablePodSubnet', { pool: v.ext })))));
        await API.postMo('uni/controller/nodeidentpol', mo('fabricNodeIdentP', { serial: v.serial, nodeId: v.nodeId, name: v.name, podId: '1', nodeType: 'remote-leaf-wan', extPoolId: v.remoteId }));
        await API.postMo('uni/tn-infra/out-multipod', mo('l3extOut', {}, mo('l3extLNodeP', { name: 'remote-leaf-' + v.nodeId },
          mo('l3extRsNodeL3OutAtt', { tDn: 'topology/pod-1/node-' + v.nodeId, rtrId: v.rid }),
          mo('l3extLIfP', { name: 'wan-' + v.nodeId }, mo('ospfIfP', {}), mo('l3extRsPathL3OutAtt', { tDn: 'topology/pod-1/paths-' + v.nodeId + '/pathep-[' + (v.port || 'eth1/54') + ']', ifInstT: 'sub-interface', encap: 'vlan-4', addr: v.ip })))));
        toast('Remote Leaf ' + v.name + ' angelegt');
        await App.refreshState();
      } }], { wide: true });
  },

  /* ================================================================ Simulation: IPN & WAN */
  async 'sim/ipn'(w0) {
    const w = w0.appendChild(h('div'));
    const draw = async () => {
      const d = await API.sim('ipn');
      clear(w);
      w.appendChild(paneHead('Simulation – IPN & WAN', 'Inter-Pod Network zwischen den Pods und WAN-Router zum Remote Leaf'));
      if (!d.active) {
        w.appendChild(h('div', { class: 'card' }, md('Die aktuelle Topologie hat nur einen Pod. **Lab 29** lädt die Multi-Pod-Topologie mit Pod 2 (spine203/204, leaf105/106), IPN-Routern ipn1/ipn2 und dem Remote Leaf leaf301 hinter dem WAN-Router wan-rl.')));
        return;
      }
      w.appendChild(h('div', { class: 'card note' }, md('Anforderungen an das IPN: **Sub-Interface vlan-4** zu den Spines, **OSPF** (gleiche Area und MTU wie das Infra-L3Out), **MTU ≥ 9150** für VXLAN, **PIM Bidir** mit RP für den GIPo-Bereich (BUM-Verkehr) und **DHCP Relay** zu den APIC-Adressen (TEP des APIC: `' + d.apicTep + '`), damit Spines neuer Pods und Remote Leafs entdeckt werden.')));
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'OSPF-Nachbarschaften (Infra-L3Out ↔ IPN/WAN)'),
        table([{ l: 'Switch', f: a => nodeName(a.serial) }, { l: 'Pod', f: a => a.pod }, { l: 'Port', f: a => a.port }, { l: 'Router', f: a => a.router + ' ' + a.rport },
          { l: 'Zustand', f: a => stateBadge(a.state === 'FULL' ? 'FULL' : a.state === 'EXSTART' ? 'EXSTART' : 'down') }, { l: 'Grund', f: a => a.why || '' }], d.adj)));
      const rs = Object.entries(d.reasons || {});
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Discovery über IPN/WAN'),
        rs.length ? table([{ l: 'Switch', f: r => nodeName(r[0]) }, { l: 'Warum (noch) nicht', f: r => r[1] }], rs) : h('p', null, 'Alle Switches hinter IPN und WAN sind erreichbar.'),
        h('p', null, h('b', null, 'Datenpfad Pod 1 ↔ Pod 2: '), d.interpod ? h('span', { class: 'bad' }, d.interpod) : 'ok')));
      d.config.routers.forEach(r => {
        w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, h('b', null, r.name), ' · ', r.kind === 'wan' ? 'WAN-Router (Remote Leaf)' : 'IPN Pod ' + r.pod, ' · MTU ' + r.mtu,
          ' · Area ' + r.area, r.kind === 'ipn' ? ' · PIM Bidir ' + (r.pim && r.rp ? 'RP ' + r.rp : 'aus') : '', ' · DHCP Relay ' + ((r.relay || []).join(', ') || '—'),
          r.down ? h('span', { class: 'bad' }, ' · ausgefallen') : '', h('span', { class: 'grow' }), h('button', { class: 'btn small', onclick: () => Views.ipnDialog(r, draw) }, 'Bearbeiten')),
        table([{ l: 'Interface zu', f: i => nodeName(i.serial) + ' ' + i.port }, { l: 'VLAN', f: i => i.vlan }, { l: 'IP', f: i => i.ip || '—' }], r.ifs)));
      });
    };
    await draw();
    App.view = { auto: draw };
  },

  ipnDialog(r, after) {
    const f = buildForm([{ k: 'mtu', l: 'MTU', req: true }, { k: 'area', l: 'OSPF Area' }, { k: 'pim', l: 'PIM Bidir', t: 'yesno' }, { k: 'rp', l: 'Rendezvous Point', ph: '192.168.100.1' },
      { k: 'relay', l: 'DHCP Relay (Helper-Adressen)', ph: '10.0.0.1', help: 'Kommagetrennt: die TEP-Adressen der APICs' }, { k: 'down', l: 'Router ausgefallen', t: 'yesno' },
      { k: 'ifs', l: 'Interfaces', t: 'rows', cols: [{ k: 'port', l: 'Switch-Port', ro: true }, { k: 'vlan', l: 'VLAN' }, { k: 'ip', l: 'IP/Maske' }] }],
    { mtu: String(r.mtu), area: r.area, pim: r.pim ? 'yes' : 'no', rp: r.rp, relay: (r.relay || []).join(', '), down: r.down ? 'yes' : 'no',
      ifs: r.ifs.map(i => ({ port: nodeName(i.serial) + ' ' + i.port, vlan: String(i.vlan), ip: i.ip })) }, {}, 'create');
    modal('Router ' + r.name, f.el, [{ l: 'Abbrechen' }, { l: 'Speichern', primary: true, fn: async () => {
      const v = f.get();
      const ifs = r.ifs.map((i, n) => Object.assign({}, i, { vlan: Number((v.ifs[n] || {}).vlan || 0), ip: (v.ifs[n] || {}).ip || '' }));
      await API.sim('ipn', { router: { name: r.name, mtu: Number(v.mtu), area: v.area, pim: v.pim === 'yes', rp: v.rp, relay: v.relay, down: v.down === 'yes', ifs } });
      toast('Gespeichert');
      await App.refreshState();
      after();
    } }], { wide: true });
  },
});

/* ================================================================ Simulation: Multi-Site (NDO) */
Object.assign(Views, {
  async 'sim/ndo'(w0) {
    const w = w0.appendChild(h('div'));
    const draw = async () => {
      const d = await API.sim('ndo');
      clear(w);
      w.appendChild(paneHead('Simulation – Nexus Dashboard Orchestrator', 'Multi-Site: Sites, Infra Configuration und Templates (vereinfacht)'));
      if (!d.ndo) {
        w.appendChild(h('div', { class: 'card' }, md('In dieser Umgebung gibt es keinen NDO und keine zweite Site. **Lab 31** lädt die Multi-Site-Umgebung mit der simulierten Site **DC-HAM** und dem Intersite Network **isn1**.')));
        return;
      }
      const n = d.ndo;
      w.appendChild(h('div', { class: 'card ' + (d.state ? 'note' : '') }, h('b', null, 'Zustand: '), d.state ? h('span', { class: 'bad' }, d.state) : 'Infra zwischen den Sites ok'));
      const loc = n.sites.local;
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Sites', h('span', { class: 'grow' }),
        h('button', { class: 'btn small primary', onclick: () => Views.ndoOnboard(loc, draw) }, loc.onboarded ? 'Site neu onboarden' : '+ Add Site (lokaler APIC)')),
      table([{ l: 'Site', f: r => r.name }, { l: 'Site ID', f: r => r.id || '—' }, { l: 'Zustand', f: r => stateBadge(r.ok ? 'online' : 'offline') }, { l: 'Info', f: r => r.info }],
        [{ name: 'Lokal (' + ((App.state.setup || {}).fabricName || 'Fabric') + ')', id: loc.siteId, ok: loc.onboarded, info: loc.onboarded ? 'onboardet als ' + loc.user : (loc.error || 'nicht onboardet') },
          { name: 'DC-HAM', id: n.sites['DC-HAM'].siteId, ok: !n.sites['DC-HAM'].down, info: 'simulierte Site, APIC ' + n.remote.apic + ', Overlay Unicast TEP ' + n.remote.ucastTep }])));
      const inf = n.infra;
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Infra Configuration', h('span', { class: 'grow' }),
        h('button', { class: 'btn small', onclick: () => Views.ndoInfra(inf, draw) }, 'Bearbeiten'),
        h('button', { class: 'btn small primary', onclick: async () => { await API.sim('ndo', { op: 'deployInfra' }); toast('Infra deployt'); draw(); } }, 'Deploy')),
      h('div', { class: 'info' }, [['OSPF Area', inf.area], ['Overlay Unicast TEP', inf.ucastTep || '—'], ['BGP Peering', inf.peering], ['Deployt', inf.deployed ? 'ja' : 'nein']]
        .map(([k, v]) => h('div', null, h('span', null, k), h('b', null, v)))),
      table([{ l: 'Spine', f: r => r.node }, { l: 'Port zum ISN', f: r => r.port }, { l: 'IP', f: r => r.ip }, { l: 'BGP-EVPN Router-ID', f: r => r.evpnRid || '—' }], inf.spines, { empty: 'Noch keine Spines konfiguriert.' }),
      h('div', { class: 'card-h' }, 'OSPF zum ISN'),
      table([{ l: 'Spine', f: a => nodeName(a.serial) + ' ' + a.port }, { l: 'Router', f: a => a.router + ' ' + a.rport }, { l: 'Zustand', f: a => stateBadge(a.state === 'FULL' ? 'FULL' : 'down') }, { l: 'Grund', f: a => a.why || '' }], d.isn)));
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Schema Shop – Templates', h('span', { class: 'grow' }),
        h('button', { class: 'btn small primary', onclick: () => Views.ndoTemplate(null, draw) }, '+ Template')),
      table([{ l: 'Template', f: t => t.name }, { l: 'Tenant', f: t => t.tenant }, { l: 'Sites', f: t => t.sites.map(s => s === 'local' ? 'lokal' : s).join(', ') },
        { l: 'Objekte', f: t => [t.vrfs.length + ' VRF', t.bds.length + ' BD', t.aps.reduce((a, x) => a + x.epgs.length, 0) + ' EPG', t.contracts.length + ' Contract'].join(', ') },
        { l: 'Deployt', f: t => Object.keys(t.deployed || {}).length ? Object.keys(t.deployed).map(s => s === 'local' ? 'lokal' : s).join(', ') : '—' }], n.templates, {
        onRow: t => Views.ndoTemplate(t, draw),
        actions: t => [h('button', { class: 'btn small primary', onclick: async ev => { ev.stopPropagation(); await API.sim('ndo', { op: 'deploy', name: t.name }); toast('Template ' + t.name + ' deployt'); draw(); } }, 'Deploy to sites'),
          iconBtn('🗑', 'Löschen', () => confirmBox('Template ' + t.name + ' löschen? (Objekte im APIC bleiben)', async () => { await API.sim('ndo', { op: 'deleteTemplate', name: t.name }); draw(); }), 'danger')],
        empty: 'Noch keine Templates.',
      })));
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Endpoints in DC-HAM'),
        table([{ l: 'Host', f: x => x.name }, { l: 'IP', f: x => x.ip }, { l: 'EPG', f: x => x.tenant + '/' + x.ap + '/' + x.epg },
          { l: 'Deployt in DC-HAM', f: x => stateBadge(n.templates.some(t => t.tenant === x.tenant && (t.deployed || {})['DC-HAM'] && t.aps.some(a => a.name === x.ap && a.epgs.some(e => e.name === x.epg))) ? 'learned' : 'down') }],
        n.remote.hosts)));
    };
    await draw();
  },

  ndoOnboard(loc, after) {
    const f = buildForm([{ k: 'user', l: 'APIC-Benutzer', req: true }, { k: 'pwd', l: 'Passwort', t: 'password', req: true }, { k: 'siteId', l: 'Site ID', req: true, ph: '1' }],
      { user: 'admin', siteId: loc.siteId || '1' }, {}, 'create');
    modal('Site hinzufügen', f.el, [{ l: 'Abbrechen' }, { l: 'Onboarden', primary: true, fn: async () => { await API.sim('ndo', Object.assign({ op: 'onboard' }, f.get())); toast('Site onboardet'); after(); } }]);
  },

  ndoInfra(inf, after) {
    const f = buildForm([{ k: 'area', l: 'OSPF Area' }, { k: 'ucastTep', l: 'Overlay Unicast TEP', ph: '172.16.100.1/32' },
      { k: 'peering', l: 'BGP Peering Type', t: 'radio', o: [['full-mesh', 'Full Mesh'], ['route-server', 'Route Server']] },
      { k: 'spines', l: 'Spines', t: 'rows', start: true, cols: [{ k: 'node', l: 'Node-ID', ph: '201' }, { k: 'port', l: 'Port', ph: 'eth1/31' }, { k: 'ip', l: 'IP/Maske', ph: '10.255.1.1/30' }, { k: 'evpnRid', l: 'BGP-EVPN Router-ID', ph: '10.255.255.201' }] }],
    { area: inf.area, ucastTep: inf.ucastTep, peering: inf.peering, spines: inf.spines.length ? inf.spines.map(s => Object.assign({}, s, { node: String(s.node) })) : [{ node: '201', port: 'eth1/31' }, { node: '202', port: 'eth1/31' }] }, {}, 'create');
    modal('Infra Configuration – lokale Site', f.el, [{ l: 'Abbrechen' }, { l: 'Speichern', primary: true, fn: async () => { await API.sim('ndo', { op: 'infra', infra: f.get() }); toast('Gespeichert – jetzt deployen'); after(); } }], { wide: true });
  },

  ndoTemplate(t, after) {
    const epgs = t ? t.aps.flatMap(a => a.epgs.map(e => ({ ap: a.name, name: e.name, bd: e.bd, cons: (e.cons || []).join(','), prov: (e.prov || []).join(',') }))) : [{ ap: 'Webshop' }];
    const yn = [['no', 'nein'], ['yes', 'ja']];
    const f = buildForm([{ k: 'name', l: 'Template', req: true }, { k: 'tenant', l: 'Tenant', req: true },
      { k: 'sites', l: 'Sites', t: 'checks', o: [['local', 'lokale Site'], ['DC-HAM', 'DC-HAM']] },
      { k: 'vrfs', l: 'VRFs', t: 'rows', start: true, cols: [{ k: 'name', l: 'VRF' }] },
      { k: 'bds', l: 'Bridge Domains', t: 'rows', start: true, cols: [{ k: 'name', l: 'BD' }, { k: 'vrf', l: 'VRF' }, { k: 'subnet', l: 'Gateway/Maske' }, { k: 'l2stretch', l: 'L2 Stretch', t: 'select', o: yn }, { k: 'bum', l: 'Intersite BUM', t: 'select', o: yn }] },
      { k: 'epgs', l: 'EPGs', t: 'rows', start: true, cols: [{ k: 'ap', l: 'AP' }, { k: 'name', l: 'EPG' }, { k: 'bd', l: 'BD' }, { k: 'cons', l: 'konsumiert' }, { k: 'prov', l: 'stellt bereit' }] },
      { k: 'contracts', l: 'Contracts', t: 'rows', start: true, cols: [{ k: 'name', l: 'Contract' }, { k: 'filter', l: 'Filter', ph: 'tcp/8080,icmp oder any' }] }],
    t ? { name: t.name, tenant: t.tenant, sites: t.sites.join(','), vrfs: t.vrfs.map(v => ({ name: v })), bds: t.bds.map(b => Object.assign({}, b, { l2stretch: b.l2stretch ? 'yes' : 'no', bum: b.bum ? 'yes' : 'no' })), epgs, contracts: t.contracts }
      : { tenant: 'Shop', sites: 'local,DC-HAM', vrfs: [{ name: 'Prod' }], bds: [{ vrf: 'Prod', l2stretch: 'no', bum: 'no' }], epgs, contracts: [] }, {}, 'create');
    modal(t ? 'Template ' + t.name : 'Neues Template', f.el, [{ l: 'Abbrechen' }, { l: 'Speichern', primary: true, fn: async () => {
      const v = f.get();
      const split = x => String(x || '').split(',').map(s => s.trim()).filter(Boolean);
      const aps = {};
      (v.epgs || []).filter(e => e.name).forEach(e => { (aps[e.ap || 'AP'] = aps[e.ap || 'AP'] || []).push({ name: e.name, bd: e.bd, cons: split(e.cons), prov: split(e.prov) }); });
      await API.sim('ndo', { op: 'template', old: t ? t.name : null, template: { name: v.name, tenant: v.tenant, sites: split(v.sites), vrfs: (v.vrfs || []).map(x => x.name).filter(Boolean),
        bds: (v.bds || []).filter(b => b.name).map(b => ({ name: b.name, vrf: b.vrf, subnet: b.subnet, l2stretch: b.l2stretch === 'yes', bum: b.bum === 'yes' })),
        aps: Object.entries(aps).map(([name, e]) => ({ name, epgs: e })), contracts: (v.contracts || []).filter(c => c.name) } });
      toast('Template gespeichert – Deploy to sites nicht vergessen');
      after();
    } }], { wide: true });
  },
});
