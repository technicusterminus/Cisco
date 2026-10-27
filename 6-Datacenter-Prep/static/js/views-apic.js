/* APIC-Ansichten: Objekt-Tabs, System, Fabric, Admin, Operations */
'use strict';

const pct = (a, b) => h('div', { class: 'bar' }, h('div', { style: { width: Math.min(100, Math.round(100 * a / b)) + '%' } }), h('span', null, a + ' / ' + b));

Object.assign(Views, {
  placeholder(w, title, text) {
    w.appendChild(paneHead(title, ''));
    w.appendChild(h('div', { class: 'card note' }, md(text || title + ' ist in Datacenter Prep nur als Menüpunkt vorhanden und hat keine Funktion.')));
  },

  /* ================================================================ Objekt-Tabs */
  async summary(body, dn, o, spec) {
    const op = await API.sim('oper?dn=' + encodeURIComponent(dn));
    const faults = MIT.faults(dn, true);
    const cnt = s => faults.filter(f => f.severity === s).length;
    body.appendChild(h('div', { class: 'cards4' },
      h('div', { class: 'kpi' }, h('span', null, 'Health Score'), h('b', null, healthBadge(op.health))),
      h('div', { class: 'kpi' }, h('span', null, 'Faults (crit/maj/min/warn)'), h('b', null, [cnt('critical'), cnt('major'), cnt('minor'), cnt('warning')].join(' / '))),
      h('div', { class: 'kpi' }, h('span', null, 'Endpoints'), h('b', null, String(op.endpoints.length))),
      h('div', { class: 'kpi' }, h('span', null, 'Deployed Leaves'), h('b', null, String(new Set(op.deployed.map(d => d.node)).size)))));
    const kids = {};
    MIT.kids(dn).forEach(k => { const c = MIT.get(k).cls; if (c !== 'faultInst' && c !== 'fvCEp') kids[c] = (kids[c] || 0) + 1; });
    if (o.cls === 'fvTenant') {
      ['fvAp', 'fvBD', 'fvCtx', 'l3extOut', 'vzBrCP', 'vzFilter'].forEach(c => { kids[c] = MIT.kids(dn, [c]).length; });
      kids.fvAEPg = MIT.kids(dn, ['fvAp']).reduce((n, ap) => n + MIT.kids(ap, ['fvAEPg']).length, 0);
    }
    body.appendChild(h('div', { class: 'cols2' },
      h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Properties'),
        h('div', { class: 'info' }, [['Name', moLabel(dn)], ['Class', o.cls], ['Description', o.a.descr || '—']].concat(spec.info ? spec.info(o.a) : []).filter(r => r[1])
          .map(([k, v]) => h('div', null, h('span', null, k), h('b', null, v))))),
      h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Inhalt'),
        table([{ l: 'Objekt', f: r => createLabel(r[0]) }, { l: 'Anzahl', f: r => String(r[1]) }], Object.entries(kids).filter(r => MIT.meta[r[0]] && (!MIT.meta[r[0]].rel || MIT.meta[r[0]].naming.length))))));
    if (o.cls === 'fvAp') Views.apTopology(body, dn);
  },

  async oper(body, dn, o, spec) {
    const op = await API.sim('oper?dn=' + encodeURIComponent(dn));
    const names = { endpoints: 'Client End-Points', deployed: 'Deployed Leaves', contracts: 'Contracts', neighbors: 'Neighbors', routes: 'Routes', vmm: 'General' };
    const holder = h('div');
    const show = id => {
      clear(holder);
      if (id === 'endpoints') holder.appendChild(table([{ l: 'End Point', f: r => r.mac }, { l: 'IP', f: r => r.ip }, { l: 'Learning Source', f: r => r.src || 'learned' }, { l: 'Hosting Server', f: r => r.name },
        { l: 'Interface', f: r => pathLabel(r.path) }, { l: 'Encap', f: r => r.encap }, { l: 'EPG', f: r => r.epg.replace(/^uni\//, '') }], op.endpoints,
      { empty: 'Keine Endpoints gelernt. Prüfe Static Ports, Domains, VLAN und Faults – und ob ein simulierter Host mit diesem VLAN an dem Port sendet.' }));
      if (id === 'deployed') holder.appendChild(table([{ l: 'Node', f: r => r.node }, { l: 'Node ID', f: r => r.id }, { l: 'Interface', f: r => r.path ? pathLabel(r.path) : '—' },
        { l: 'Encap', f: r => r.encap || '—' }, { l: 'Deployment State', f: r => stateBadge(r.state === 'deployed' ? 'formed' : r.state) }], op.deployed, { empty: 'Auf keinem Leaf deployt.' }));
      if (id === 'contracts') holder.appendChild(table([{ l: 'Contract', f: r => r.contract.replace(/^uni\//, '') }, { l: 'Role', f: r => r.role }, { l: 'Scope', f: r => r.scope }], op.contracts, { empty: 'Keine Contracts.' }));
      if (id === 'neighbors') holder.appendChild(table([{ l: 'Neighbor', f: r => r.name }, { l: 'Node', f: r => r.node }, { l: 'Interface', f: r => r.iface }, { l: 'Protocol', f: r => r.proto },
        { l: 'Neighbor IP', f: r => r.ip }, { l: 'State', f: r => stateBadge(r.state) }, { l: 'Routen an Nachbar', f: r => r.learned.join(', ') }], op.neighbors, { empty: 'Keine Routing-Nachbarn.' }));
      if (id === 'vmm') {
        const v = op.vmm || {};
        holder.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'vCenter-Verbindung ', stateBadge(v.state || 'offline')),
          v.state === 'online' ? h('p', null, 'Verbunden mit vCenter ', h('b', null, v.vc), ' · Discovery Protocol am DVS: ', h('b', null, (v.discovery || '').toUpperCase())) : null,
          (v.reasons || []).map(r => h('p', { class: 'note warn' }, r))));
        holder.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Port Groups am Distributed Switch'),
          table([{ l: 'Port Group', f: r => r.name }, { l: 'EPG', f: r => r.epg.replace(/^uni\//, '') }, { l: 'VLAN', f: r => 'vlan-' + r.vlan }, { l: 'Resolution Immediacy', f: r => r.imm }],
            v.pgs || [], { empty: 'Keine Port Groups. Hänge eine EPG mit "Add VMM Domain Association" an diese Domain.' })));
        holder.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Hypervisors (ESXi im DVS)'),
          table([{ l: 'Host', f: r => r.name }, { l: 'Uplinks', f: r => r.legs.map(l => 'Node-' + l[0] + ' ' + l[1]).join(', ') },
            { l: 'Status', f: r => stateBadge(r.ok.length ? 'up' : 'down') }, { l: 'Hinweis', f: r => r.reasons.join('; ') }],
            v.hosts || [], { empty: 'Kein ESXi-Host in diesem DVS. ESXi-Hosts verwaltest du unter Simulation > vCenter.' })));
      }
      if (id === 'routes') holder.appendChild(table([{ l: 'Node', f: r => r.node }, { l: 'Prefix', f: r => r.prefix }, { l: 'Next Hop', f: r => r.nh }, { l: 'Interface', f: r => r.via }, { l: 'Protocol', f: r => r.proto }], op.routes, { empty: 'Keine Routen.' }));
    };
    const ids = spec.oper;
    body.appendChild(tabsBar(ids.map(i => [i, names[i]]), show, ids[0], 'wtabs sub'));
    body.appendChild(holder);
    show(ids[0]);
  },

  async stats(body, dn) {
    const op = await API.sim('oper?dn=' + encodeURIComponent(dn));
    body.appendChild(h('div', { class: 'card note' }, 'Paketzähler aus den Traffic-Tests (Operations > Visibility & Troubleshooting). Jede Anfrage und jede Antwort zählt als ein Paket.'));
    body.appendChild(table([{ l: 'Objekt', f: r => r.dn.replace(/^uni\//, '') }, { l: 'Tx Packets', f: r => String(r.txPkts || 0) }, { l: 'Rx Packets', f: r => String(r.rxPkts || 0) },
      { l: 'Dropped Packets', f: r => String(r.dropPkts || 0) }], op.statsRows, { empty: 'Noch keine Pakete gezählt.' }));
  },

  async health(body, dn, faults) {
    const op = await API.sim('oper?dn=' + encodeURIComponent(dn));
    const pen = { critical: 40, major: 15, minor: 5, warning: 1 };
    body.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Health Score ', healthBadge(op.health)),
      h('p', { class: 'muted' }, 'Der Health Score sinkt mit jedem Fault im Objekt und darunter: critical −40, major −15, minor −5, warning −1.'),
      table([{ l: 'Severity', f: f => sevBadge(f.severity) }, { l: 'Code', f: f => f.code }, { l: 'Affected Object', f: f => parentDn(f.dn) }, { l: 'Abzug', f: f => '−' + (pen[f.severity] || 0) }], faults, { empty: 'Keine Faults, Health 100.' })));
  },

  /* ================================================================ System */
  async 'system/quickstart'(w) {
    w.appendChild(paneHead('System – QuickStart', 'Typische Schritte nach der Installation'));
    const steps = [['Fabric Membership: Switches registrieren', () => App.go('fabric', 'inventory', 'membership')],
      ['BGP Route Reflector (Fabric-AS und Spines)', () => App.go('system', 'settings', 'bgprr')],
      ['Static Node Management Addresses (Tenant mgmt)', () => App.go('tenants', 'mgmt')],
      ['NTP: Date and Time Policy und Pod Policy Group', () => App.go('fabric', 'fabricpol')],
      ['Access Policies: Configure Interface, PC, and VPC', () => App.go('fabric', 'access', 'access-qs')],
      ['Tenant anlegen', () => createDialog('uni', 'fvTenant')]];
    w.appendChild(h('div', { class: 'tiles' }, steps.map(([l, fn], i) => h('div', { class: 'tile', onclick: fn }, h('b', null, (i + 1) + '. '), l))));
  },

  async 'system/controllers'(w) {
    const n = (await API.cls('topSystem', 'query-target-filter=' + encodeURIComponent('eq(topSystem.role,"controller")'))).map(r => r.topSystem.attributes);
    const su = App.state.setup || {};
    const fit = (su.ctrlCount || '1') === '1';
    w.appendChild(paneHead('Controllers', 'APIC-Cluster – ' + (su.fabricName || '')));
    w.appendChild(h('div', { class: 'cards4' }, h('div', { class: 'kpi' }, h('span', null, 'Target Cluster Size'), h('b', null, su.ctrlCount || '1')),
      h('div', { class: 'kpi' }, h('span', null, 'Operational Cluster Size'), h('b', null, '1')),
      h('div', { class: 'kpi' }, h('span', null, 'Health'), h('b', null, fit ? 'Fully Fit' : 'Not Fully Fit'))));
    if (!fit) w.appendChild(h('div', { class: 'card note warn' }, 'Im Setup wurden ' + su.ctrlCount + ' Controller angegeben, es gibt aber nur einen APIC. Der Cluster ist deshalb nicht Fully Fit (Fault S0101). Korrigieren lässt sich das nur mit einem Neuaufsetzen (acidiag touch clean, acidiag reboot).'));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Fabric-Parameter aus dem Setup'),
      table([{ l: 'Parameter', f: r => r[0] }, { l: 'Wert', f: r => r[1] }], [['Fabric Name', su.fabricName], ['Fabric ID', su.fabricId], ['Pod ID', su.podId],
        ['TEP Pool', su.tepPool], ['Infra VLAN', su.infraVlan], ['BD Multicast (GIPo)', su.gipo], ['OOB Management', su.oobIp + ' gw ' + su.oobGw]])));
    w.appendChild(table([{ l: 'ID', f: r => r.id }, { l: 'Name', f: r => r.name }, { l: 'IP (TEP)', f: r => r.address }, { l: 'OOB Address', f: r => r.oobMgmtAddr },
      { l: 'Admin State', f: () => 'In Service' }, { l: 'Operational State', f: () => stateBadge('active') }, { l: 'Health State', f: () => 'Fully Fit' }, { l: 'Serial', f: r => r.serial }, { l: 'Version', f: r => r.version }], n));
  },

  async 'system/events'(w) {
    const rows = (await API.cls('eventRecord', 'order-by=eventRecord.created|desc&page-size=300')).map(r => r.eventRecord.attributes);
    w.appendChild(paneHead('Events', 'Zustandswechsel in der Fabric (neueste zuerst)', [iconBtn('⟳', 'Refresh', () => App.renderMain())]));
    w.appendChild(eventTable(rows, true));
  },

  async 'system/audit'(w) {
    const rows = (await API.cls('aaaModLR', 'order-by=aaaModLR.created|desc&page-size=300')).map(r => r.aaaModLR.attributes);
    w.appendChild(paneHead('Audit Log', 'Jede Konfigurationsänderung mit Benutzer (neueste zuerst)', [iconBtn('⟳', 'Refresh', () => App.renderMain())]));
    w.appendChild(auditTable(rows, true));
  },

  async 'system/sessions'(w) {
    const rows = await API.sim('sessions');
    w.appendChild(paneHead('Active Sessions', ''));
    w.appendChild(table([{ l: 'User', f: r => r.user }, { l: 'Login Time', f: r => fmtTs(r.since) }, { l: 'Session ID', f: r => r.id + '…' }, { l: 'Läuft ab in', f: r => Math.round(r.expires / 60) + ' min' }], rows));
  },

  settingsRoots() {
    return [{ key: 'bgprr', label: 'BGP Route Reflector', icon: 'RR', kind: 'view', view: w => Views.bgpRR(w) },
      { key: 'ph:apicconn', label: 'APIC Connectivity Preferences', kind: 'folder', ph: 'Die Verbindung des APIC (inband/ooband) ist in Datacenter Prep fest auf Out-of-Band eingestellt.' },
      { key: 'ph:coop', label: 'COOP Group', kind: 'folder', ph: 'Die COOP-Datenbank (Endpoint-Mapping auf den Spines) wird automatisch simuliert.' },
      { key: 'ph:mtu', label: 'Control Plane MTU', kind: 'folder', ph: 'Control Plane MTU: 9000 (fest).' },
      { key: 'ph:epctl', label: 'Endpoint Controls', kind: 'folder', ph: 'Endpoint Loop Protection und Rogue EP Control sind nicht nachgebildet.' },
      { key: 'ph:fws', label: 'Fabric-Wide Settings', kind: 'folder', ph: 'Enforce Subnet Check, Domain Validation usw. sind nicht nachgebildet.' },
      { key: 'ph:qos', label: 'QOS', kind: 'folder', ph: 'QoS ist nicht nachgebildet.' },
      { key: 'sysinfo', label: 'Über Datacenter Prep', icon: 'i', kind: 'view', view: w => Views.about(w) }];
  },

  about(w) {
    w.appendChild(paneHead('Über Datacenter Prep', ''));
    w.appendChild(h('div', { class: 'card' }, md([
      '## Datacenter Prep',
      'Trainingsumgebung für Cisco ACI: ein simulierter APIC mit 2 Spines und 4 Leafs. Menüs, Baum und Formulare folgen der APIC-GUI, die REST-API dem APIC-Format. Ansible (`cisco.aci`), Postman, Python und curl funktionieren damit.',
      '- Konfiguration im Tenant, in den Access und Fabric Policies und in Fabric Membership wird wie beim APIC aufgelöst und deployt.',
      '- Simulierte Hosts und externe Router (Menü **Simulation**) erzeugen Endpoints, OSPF- und BGP-Nachbarschaften und Traffic.',
      '- Faults, Events, Audit Log, CLI (`show endpoint`, `show zoning-rule`, `moquery`) und der Traffic-Test zeigen das Ergebnis.',
      'Kein Cisco-Produkt. Cisco, ACI und APIC sind Marken von Cisco Systems, Inc.',
    ].join('\n'))));
  },

  /* ================================================================ Tenants */
  async 'tenants/search'(w) {
    const rows = (await API.cls('fvTenant', 'rsp-subtree-include=health', true));
    const q = h('input', { placeholder: 'Tenant-Name', style: { width: '280px' } });
    const res = h('div');
    const draw = () => clear(res).appendChild(table([{ l: 'Name', f: r => h('a', { class: 'lnk', onclick: () => App.go('tenants', r.fvTenant.attributes.name) }, r.fvTenant.attributes.name) },
      { l: 'Description', f: r => r.fvTenant.attributes.descr }, { l: 'Health', f: r => healthBadge(r.fvTenant.children ? r.fvTenant.children[0].healthInst.attributes.cur : 100) }],
    rows.filter(r => r.fvTenant.attributes.name.toLowerCase().includes(q.value.toLowerCase())), { onRow: r => App.go('tenants', r.fvTenant.attributes.name) }));
    q.oninput = draw;
    w.appendChild(paneHead('Tenant Search', ''));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'traffic' }, h('label', null, 'Tenant'), q)));
    w.appendChild(res);
    draw();
    q.focus();
  },

  /* ================================================================ Fabric Inventory */
  inventoryRoots() {
    const st = App.state;
    const nodeKids = n => [
      { key: 'node:' + n.id + ':if', label: 'Interfaces', kind: 'folder', dn: null, spec: {}, view: w => Views.nodeIfs(w, n.id, 'phys'),
        kids: () => [['phys', 'Physical Interfaces'], ['pc', 'PC Interfaces'], ['vpc', 'VPC Interfaces']].map(([k, l]) => ({ key: 'node:' + n.id + ':if:' + k, label: l, kind: 'view', icon: '≡', view: w => Views.nodeIfs(w, n.id, k) })) },
      { key: 'node:' + n.id + ':proto', label: 'Protocols', kind: 'folder', dn: null, spec: {}, view: w => Views.nodeProto(w, n.id, 'lldp'),
        kids: () => [['lldp', 'LLDP'], ['ospf', 'OSPF'], ['bgp', 'BGP'], ['ntp', 'NTP']].map(([k, l]) => ({ key: 'node:' + n.id + ':p:' + k, label: l, kind: 'view', icon: '≡', view: w => Views.nodeProto(w, n.id, k) })) },
    ];
    return [
      { key: 'inv-qs', label: 'Quick Start', icon: '?', kind: 'view', view: w => Views.placeholder(w, 'Inventory – Quick Start', 'Neue Switches registrierst du unter **Fabric Membership**. Die Topologie zeigt den Zustand der Fabric.') },
      { key: 'topology', label: 'Topology', icon: '⌗', kind: 'view', view: w => Views.topologyPage(w, false) },
      {
        key: 'pod1', label: 'Pod 1', icon: 'P', kind: 'view', view: w => Views.podView(w),
        kids: () => (st.nodes || []).filter(n => n.id && ['active', 'discovering', 'inactive'].includes(n.state)).sort((a, b) => a.id - b.id)
          .map(n => ({ key: 'node:' + n.id, label: n.name + ' (Node-' + n.id + ')', icon: n.role === 'spine' ? 'SP' : 'LF', kind: 'view', view: w2 => Views.nodeView(w2, n.id), kids: n.state === 'active' ? () => nodeKids(n) : null })),
      },
      { key: 'podsetup', label: 'Pod Fabric Setup Policy', icon: 'P', kind: 'view', view: w => {
        w.appendChild(paneHead('Pod Fabric Setup Policy', ''));
        w.appendChild(table([{ l: 'Pod ID', f: () => '1' }, { l: 'TEP Pool', f: () => '10.0.0.0/16' }, { l: 'Remote ID', f: () => '—' }], [1]));
      } },
      { key: 'membership', label: 'Fabric Membership', icon: 'FM', kind: 'view', view: w => Views.membership(w) },
      { key: 'ph:dupip', label: 'Duplicate IP Usage', kind: 'folder', ph: 'Keine doppelten IP-Adressen gefunden.' },
      { key: 'disabled', label: 'Disabled Interfaces and Decommissioned Switches', icon: '⊘', kind: 'view', view: w => Views.disabledIfs(w) },
    ];
  },

  async nodeIfs(w, id, kind) {
    const info = await API.sim('nodeinfo?id=' + id);
    const name = info.node.name;
    if (kind === 'phys') {
      const rows = await API.cls('topology/pod-' + POD() + '/node-' + id + '/l1PhysIf', 'rsp-subtree=children');
      const data = rows.map(r => { const a = r.l1PhysIf.attributes; const c = (r.l1PhysIf.children || [])[0]; return Object.assign({}, a, { oper: c ? c.ethpmPhysIf.attributes : {} }); })
        .sort((a, b) => portNum(a.id) - portNum(b.id));
      w.appendChild(paneHead('Physical Interfaces – ' + name, 'topology/pod-' + POD() + '/node-' + id + '/sys'));
      w.appendChild(table([{ l: 'Interface', f: r => r.id }, { l: 'Admin State', f: r => r.adminSt }, { l: 'Oper State', f: r => stateBadge(r.oper.operSt) }, { l: 'Oper State Reason', f: r => r.oper.operStQual },
        { l: 'Usage', f: r => r.usage }, { l: 'Layer', f: r => r.layer }, { l: 'Oper Speed', f: r => r.oper.operSpeed }, { l: 'VLANs', f: r => r.oper.operVlans }], data, {
        actions: r => r.portT === 'fab' ? [] : [h('button', { class: 'btn small', onclick: () => Views.toggleIf(id, r.id, r.adminSt === 'up', () => { clear(w); Views.nodeIfs(w, id, kind); }) }, r.adminSt === 'up' ? 'Disable' : 'Enable')],
      }));
    } else {
      const pcs = info.pcs.filter(p => p.type === kind);
      w.appendChild(paneHead((kind === 'pc' ? 'PC' : 'VPC') + ' Interfaces – ' + name, ''));
      w.appendChild(table([{ l: 'Interface', f: r => r.id }, { l: 'Policy Group', f: r => r.name }, { l: 'Protocol', f: r => ['active', 'passive'].includes(r.lacp) ? 'LACP (' + r.lacp + ')' : 'static' },
        { l: 'Members', f: r => r.members.map(m => m.port + ' (' + m.state + ')').join(', ') }, { l: 'Path', f: r => pathLabel(r.path) }], pcs, { empty: 'Keine ' + (kind === 'pc' ? 'Port-Channels' : 'vPCs') + ' auf diesem Switch.' }));
      if (kind === 'vpc' && info.vpc) w.appendChild(h('div', { class: 'card note' }, 'vPC-Domäne ' + info.vpc.id + ' (' + info.vpc.name + '): Switches ' + info.vpc.nodes.join(' + ') + ', Peer ' + (info.vpc.up ? 'up' : 'down')));
    }
  },

  toggleIf(id, port, disable, after) {
    const tdn = 'topology/pod-' + POD() + '/paths-' + id + '/pathep-[' + port + ']';
    confirmBox((disable ? 'Interface ' + port + ' auf Node ' + id + ' deaktivieren?' : 'Interface ' + port + ' wieder aktivieren?'), async () => {
      await API.postMo('uni/fabric/outofsvc', { fabricOOServicePol: { attributes: {}, children: [{ fabricRsOosPath: { attributes: disable ? { tDn: tdn, lc: 'blacklist' } : { tDn: tdn, status: 'deleted' } } }] } });
      toast(disable ? 'Interface deaktiviert' : 'Interface aktiviert');
      await App.refreshState();
      after();
    });
  },

  async nodeProto(w, id, kind) {
    const info = await API.sim('nodeinfo?id=' + id);
    const name = info.node.name;
    w.appendChild(paneHead(kind.toUpperCase() + ' – ' + name, ''));
    if (kind === 'lldp') w.appendChild(table([{ l: 'Local Interface', f: r => r.local }, { l: 'Neighbor', f: r => r.device }, { l: 'Neighbor Port', f: r => r.port }, { l: 'Capability', f: r => r.cap }], info.lldp));
    if (kind === 'ospf' || kind === 'bgp') w.appendChild(table([{ l: 'Neighbor', f: r => r.name }, { l: 'Address', f: r => r.ip }, { l: 'Interface', f: r => r.iface }, { l: 'VRF', f: r => r.vrf.replace(/^uni\//, '') },
      { l: 'State', f: r => stateBadge(r.state) }], info.neighbors.filter(n => n.proto === kind), { empty: 'Keine ' + kind.toUpperCase() + '-Nachbarn.' }));
    if (kind === 'ntp') w.appendChild(h('div', { class: 'card' + (info.ntp ? ' note warn' : ' note') }, info.ntp ? 'Nicht synchronisiert: ' + info.ntp : 'Mit dem NTP-Server synchronisiert. OOB-Adresse: ' + info.oob));
  },

  async disabledIfs(w) {
    await MIT.load('uni/fabric/outofsvc');
    w.appendChild(paneHead('Disabled Interfaces and Decommissioned Switches', 'uni/fabric/outofsvc'));
    const rows = MIT.kids('uni/fabric/outofsvc', ['fabricRsOosPath']).map(d => MIT.a(d));
    w.appendChild(table([{ l: 'Interface', f: r => pathLabel(r.tDn) }, { l: 'Status', f: r => r.lc }], rows, {
      actions: r => [h('button', { class: 'btn small', onclick: () => { const m = /paths-(\d+)\/pathep-\[(.+)\]/.exec(r.tDn); Views.toggleIf(m[1], m[2], false, () => App.renderWork()); } }, 'Enable')],
      empty: 'Keine deaktivierten Interfaces. Interfaces deaktivierst du unter Pod 1 > Switch > Interfaces > Physical Interfaces.',
    }));
  },

  async nodeView(w, id) {
    const n = App.state.nodes.find(x => x.id === id);
    if (!n) return;
    const dn = 'topology/pod-' + POD() + '/node-' + id;
    w.appendChild(paneHead('Node - ' + n.name, dn, [h('button', { class: 'btn small', onclick: () => Term.open(n.name) }, '⌨ CLI'),
      actionsButton([{ l: 'Open CLI', fn: () => Term.open(n.name) }, { l: 'Remove From Controller', danger: true, fn: () => App.go('fabric', 'inventory', 'membership') },
        { l: 'Open In Object Store Browser', fn: () => window.open('/visore.html#' + encodeURIComponent(dn), '_blank') }])]));
    const body = h('div', { class: 'wbody' });
    const show = async tab => {
      clear(body);
      if (tab === 'general') {
        const info = n.state === 'active' ? await API.sim('nodeinfo?id=' + id) : { oob: '', ntp: 'n/a' };
        body.appendChild(h('div', { class: 'info' }, [['Node ID', n.id], ['Name', n.name], ['Role', n.role], ['Model', n.model], ['Serial', n.serial], ['TEP Address', n.tep], ['State', n.state],
          ['OOB Management', info.oob || '0.0.0.0'], ['NTP', info.ntp ? 'nicht synchron' : 'synchron'], ['Version', n.state === 'active' ? 'n9000-16.0(5h)' : '—']].map(([k, v]) => h('div', null, h('span', null, k), h('b', null, String(v))))));
        if (n.state !== 'active') body.appendChild(h('div', { class: 'card note warn' }, 'Dieser Switch ist noch nicht aktiv (Discovery läuft oder kein Nachbar aktiv).'));
      }
      if (tab === 'health') {
        const fl = (await API.cls('faultInst', 'query-target-filter=' + encodeURIComponent('wcard(faultInst.dn,"^' + reEsc(dn) + '/")'))).map(r => r.faultInst.attributes);
        await Views.health(body, dn, fl);
      }
      if (tab === 'faults') {
        const fl = (await API.cls('faultInst', 'query-target-filter=' + encodeURIComponent('wcard(faultInst.dn,"^' + reEsc(dn) + '/")'))).map(r => r.faultInst.attributes);
        body.appendChild(faultTable(fl, false));
      }
      if (tab === 'history') await historyView(body, dn);
      if (tab === 'cli') Term.embed(body, n.name);
    };
    w.appendChild(tabsBar([['general', 'General'], ['health', 'Health'], ['faults', 'Faults'], ['history', 'History'], ['cli', 'CLI']], show, 'general'));
    w.appendChild(body);
    show('general');
  },

  /* ================================================================ Access Policies */
  accessQuickStart(w) {
    w.appendChild(paneHead('Access Policies – Quick Start', 'uni/infra'));
    w.appendChild(h('div', { class: 'tiles' },
      h('div', { class: 'tile big', onclick: () => Views.configureInterfaceWizard() }, h('b', null, 'Configure Interface, PC, and VPC'), h('div', { class: 'muted' }, 'Erzeugt Switch-Profil, Interface-Profil, Selector, Policy Group, AAEP, Domain und VLAN Pool in einem Schritt.')),
      h('div', { class: 'tile big', onclick: () => App.select(folderKey('uni/infra', ACCESS_TREE[0].sub[0].sub[0])) }, h('b', null, 'Manuell: Switch Profiles'), h('div', { class: 'muted' }, 'Jedes Objekt einzeln anlegen – wie in der Prüfung.'))));
    w.appendChild(h('div', { class: 'card' }, md([
      '## Die Kette der Access Policies',
      '1. **VLAN Pool** (Pools > VLAN) mit dem VLAN-Bereich, *Static Allocation* für Static Ports.',
      '2. **Domain** (Physical oder L3 Domain), die auf den VLAN Pool zeigt.',
      '3. **AAEP** (Policies > Global > Attachable Access Entity Profiles) mit der Domain.',
      '4. **Interface Policy Group** (Leaf Access Port, PC oder VPC Interface) mit dem AAEP.',
      '5. **Leaf Interface Profile** mit Access Port Selector (Ports) → Policy Group.',
      '6. **Leaf Profile** mit Leaf Selector (Node-IDs) → Interface Profile.',
      'Im Tenant hängt die EPG an derselben **Domain** und bekommt **Static Ports** mit dem VLAN. Fehlt ein Glied, meldet die EPG den Fault **F0467**.',
    ].join('\n'))));
  },

  configureInterfaceWizard() {
    const fields = [
      { k: 'nodes', l: 'Switches', t: 'nodemulti', ids: true, req: true },
      { k: 'ports', l: 'Interfaces', req: true, ph: '1/1-10 oder 1/20' },
      { k: 'type', l: 'Interface Type', t: 'radio', o: [['access', 'Individual'], ['pc', 'Port Channel (PC)'], ['vpc', 'Virtual Port Channel (VPC)']], def: 'access' },
      { k: 'pgname', l: 'Interface Policy Group', req: true, ph: 'IPG-Server' },
      { k: 'lacp', l: 'Port Channel Policy', t: 'select', o: [['active', 'LACP Active'], ['passive', 'LACP Passive'], ['off', 'Static Channel - Mode On']], def: 'active', show: v => v.type !== 'access' },
      { k: 'lldp', l: 'LLDP', t: 'radio', o: [['', 'default'], ['on', 'enabled'], ['off', 'disabled']], def: '' },
      { k: 'aaep', l: 'Attached Entity Profile', t: 'tdn', target: ['infraAttEntityP'], empty: '— neu anlegen —' },
      { k: 'aaepname', l: 'Neues AAEP', ph: 'AAEP-Server', show: v => !v.aaep },
      { k: 'dom', l: 'Domain', t: 'tdn', target: ['physDomP', 'l3extDomP'], empty: '— neue Physical Domain —', show: v => !v.aaep },
      { k: 'domname', l: 'Neue Physical Domain', ph: 'PhysDom-Server', show: v => !v.aaep && !v.dom },
      { k: 'vfrom', l: 'VLAN Range von', ph: '100', show: v => !v.aaep && !v.dom }, { k: 'vto', l: 'VLAN Range bis', ph: '199', show: v => !v.aaep && !v.dom },
    ];
    const finish = async v => {
      const ids = (v.nodes || []).map(Number).sort((a, b) => a - b);
      if (!ids.length) throw new ApiError('Eingabe', 'Mindestens einen Switch wählen');
      if (v.type === 'vpc' && ids.length !== 2) throw new ApiError('Eingabe', 'Für einen vPC genau zwei Switches wählen');
      const tag = 'Switch' + ids.join('-');
      const infra = [];
      const top = [];
      let aaep = v.aaep;
      if (!aaep) {
        const an = v.aaepname || 'AAEP-' + v.pgname;
        let dom = v.dom;
        if (!dom) {
          if (!v.domname || !v.vfrom) throw new ApiError('Eingabe', 'Neue Domain braucht Name und VLAN-Bereich');
          const pool = v.domname + '_vlans';
          infra.push(mo('fvnsVlanInstP', { name: pool, allocMode: 'static' }, mo('fvnsEncapBlk', { from: 'vlan-' + v.vfrom, to: 'vlan-' + (v.vto || v.vfrom) })));
          top.push(mo('physDomP', { name: v.domname }, mo('infraRsVlanNs', { tDn: 'uni/infra/vlanns-[' + pool + ']-static' })));
          dom = 'uni/phys-' + v.domname;
        }
        infra.push(mo('infraAttEntityP', { name: an }, mo('infraRsDomP', { tDn: dom })));
        aaep = 'uni/infra/attentp-' + an;
      }
      const pgKids = [mo('infraRsAttEntP', { tDn: aaep })];
      if (v.lldp) { infra.push(mo('lldpIfPol', { name: 'LLDP-' + v.lldp, adminRxSt: v.lldp === 'on' ? 'enabled' : 'disabled', adminTxSt: v.lldp === 'on' ? 'enabled' : 'disabled' })); pgKids.push(mo('infraRsLldpIfPol', { tnLldpIfPolName: 'LLDP-' + v.lldp })); }
      let pgdn;
      if (v.type === 'access') {
        infra.push(mo('infraFuncP', {}, mo('infraAccPortGrp', { name: v.pgname }, pgKids)));
        pgdn = 'uni/infra/funcprof/accportgrp-' + v.pgname;
      } else {
        infra.push(mo('lacpLagPol', { name: 'LACP-' + v.lacp, mode: v.lacp }));
        pgKids.push(mo('infraRsLacpPol', { tnLacpLagPolName: 'LACP-' + v.lacp }));
        infra.push(mo('infraFuncP', {}, mo('infraAccBndlGrp', { name: v.pgname, lagT: v.type === 'vpc' ? 'node' : 'link' }, pgKids)));
        pgdn = 'uni/infra/funcprof/accbundle-' + v.pgname;
      }
      const sel = v.pgname.replace(/[^\w.-]/g, '') + '-ifsel';
      infra.push(mo('infraAccPortP', { name: tag + '_Profile_ifselector' }, hportsBody(sel, v.ports, pgdn)));
      infra.push(mo('infraNodeP', { name: tag + '_Profile' }, leafSelBody(tag + '_Profile_selector', ids[0], ids[ids.length - 1]),
        mo('infraRsAccPortP', { tDn: 'uni/infra/accportprof-' + tag + '_Profile_ifselector' })));
      const body = mo('polUni', {}, mo('infraInfra', {}, infra), top);
      if (v.type === 'vpc') {
        const exist = (await classRows('fabricNodePEp')).map(a => a.id);
        if (!exist.includes(String(ids[0])) && !exist.includes(String(ids[1])))
          await API.postMo('uni/fabric/protpol', mo('fabricExplicitGEp', { name: tag + '_VPC', id: String(ids[0]) }, mo('fabricNodePEp', { id: String(ids[0]) }), mo('fabricNodePEp', { id: String(ids[1]) })));
      }
      await API.postMo('uni', body);
      toast('Interface-Konfiguration angelegt');
      App.reload();
    };
    wizard('Configure Interface, PC, and VPC', [{ l: 'Interfaces', fields }], {}, finish);
  },

  async interfaceConfiguration(w) {
    await MIT.load('uni/infra');
    w.appendChild(paneHead('Interface Configuration', 'Welche Policy Group liegt auf welchem Port?'));
    const rows = [];
    MIT.kids('uni/infra', ['infraNodeP']).forEach(np => {
      const nodes = MIT.kids(np, ['infraLeafS']).flatMap(ls => MIT.kids(ls, ['infraNodeBlk']).map(b => MIT.a(b).from_ + '-' + MIT.a(b).to_));
      MIT.kids(np, ['infraRsAccPortP']).forEach(rs => {
        const ifp = MIT.a(rs).tDn;
        MIT.kids(ifp, ['infraHPortS']).forEach(hs => {
          const ports = MIT.kids(hs, ['infraPortBlk']).map(d => { const a = MIT.a(d); return '1/' + a.fromPort + (a.toPort !== a.fromPort ? '-' + a.toPort : ''); }).join(', ');
          const pg = relOf(hs, 'infraRsAccBaseGrp', 'tDn');
          rows.push({ nodes: nodes.join(', '), ports, pg: nameOfDn(pg), type: pg.includes('accbundle-') ? (MIT.a(pg) && MIT.a(pg).lagT === 'node' ? 'vPC' : 'PC') : 'Access', prof: MIT.a(np).name, ifp: nameOfDn(ifp) });
        });
      });
    });
    w.appendChild(table([{ l: 'Nodes', f: r => r.nodes }, { l: 'Interfaces', f: r => r.ports }, { l: 'Port Type', f: r => r.type }, { l: 'Policy Group', f: r => r.pg },
      { l: 'Leaf Profile', f: r => r.prof }, { l: 'Interface Profile', f: r => r.ifp }], rows, { empty: 'Noch keine Interfaces konfiguriert.' }));
  },

  fabricPolQuickStart(w) {
    w.appendChild(paneHead('Fabric Policies – Quick Start', 'uni/fabric'));
    w.appendChild(h('div', { class: 'card' }, md([
      '## NTP für die Fabric',
      '1. **Policies > Pod > Date and Time**: Policy anlegen (oder *default* verwenden) und NTP-Server mit Management EPG *default* (Out-of-Band) eintragen.',
      '2. **Pods > Policy Groups**: Pod Policy Group anlegen und die Date Time Policy auswählen.',
      '3. **Pods > Profiles > Pod Profile default**: Im Pod Selector *default* die Policy Group eintragen.',
      '4. Die Switches brauchen eine Management-Adresse: **Tenants > mgmt > Node Management Addresses > Static Node Management Addresses**.',
      'Prüfen mit `show ntp peer-status` auf einem Switch.',
    ].join('\n'))));
  },

  /* ================================================================ Admin */
  async 'admin/firmware'(w) {
    const n = (await API.cls('fabricNode')).map(r => r.fabricNode.attributes).sort((a, b) => a.id - b.id);
    w.appendChild(paneHead('Firmware', 'Installierte Versionen'));
    w.appendChild(h('div', { class: 'card note' }, 'Firmware-Upgrades (Upgrade Groups, Repository) sind in Datacenter Prep nicht nachgebildet.'));
    w.appendChild(table([{ l: 'Node', f: r => r.name }, { l: 'ID', f: r => r.id }, { l: 'Role', f: r => r.role }, { l: 'Model', f: r => r.model }, { l: 'Current Firmware', f: r => r.version || '—' }], n));
  },

  /* ================================================================ Virtual Networking */
  async vmmQuickStart(w) {
    w.appendChild(paneHead('Virtual Networking – Quick Start', 'VMware vCenter anbinden'));
    w.appendChild(h('div', { class: 'card' }, md([
      'So bindest du ein vCenter an (wie im echten APIC):',
      '1. **VLAN Pool** mit **Dynamic Allocation** anlegen (Fabric > Access Policies > Pools > VLAN), z. B. vlan-1000 bis vlan-1099.',
      '2. **VMM Domain** anlegen: Rechtsklick auf **VMM Domains > VMware > Create vCenter Domain**. Name = Name des Distributed Switch, dazu VLAN Pool, AAEP, Credentials, vCenter (IP und Datacenter-Name) und die vSwitch Policy (LLDP oder CDP).',
      '3. Das **AAEP** an den ESXi-Ports muss die VMM Domain enthalten; die Interface Policy Group braucht LLDP oder CDP passend zur vSwitch Policy.',
      '4. In der EPG **Add VMM Domain Association** – der APIC legt im vCenter die Port Group **Tenant|AP|EPG** mit einem VLAN aus dem dynamischen Pool an.',
      '5. Unter **Simulation > vCenter** die VM-Netzwerkkarte in diese Port Group legen. Die VM wird als Endpoint gelernt (Learning Source **learned,vmm**).',
      '',
      '**Resolution Immediacy:** *Pre-provision* programmiert das VLAN auf allen Ports mit dem AAEP, *Immediate* sobald ein ESXi per LLDP/CDP am Port erkannt wird, *On Demand* erst, wenn eine VM in der Port Group läuft.',
    ].join('\n'))));
    const st = App.state;
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'VMM Domains'),
      table([{ l: 'Domain', f: r => r.name }, { l: 'vCenter', f: r => r.vc || '—' }, { l: 'State', f: r => stateBadge(r.state) }, { l: 'Port Groups', f: r => String(r.pgs.length) },
        { l: 'Hinweis', f: r => r.reasons.join('; ') }], st.vmm || [], { onRow: r => App.select('mo:' + r.dn), empty: 'Noch keine VMM Domain.' })));
  },

  async 'sim/vcenter'(w) {
    const draw = () => {
      clear(w);
      const st = App.state;
      w.appendChild(paneHead('Simulation – vCenter', 'Simulierter VMware vCenter mit ESXi-Hosts und VMs',
        [h('button', { class: 'btn primary small', onclick: () => Views.vcenterDialog() }, '+ vCenter')]));
      if (!(st.vcenters || []).length) w.appendChild(h('div', { class: 'card note' }, 'Noch kein vCenter. Lege eines an – der APIC verbindet sich über die VMM Domain (Controller-IP, Datacenter, Credentials) damit.'));
      (st.vcenters || []).forEach(vc => {
        const doms = (st.vmm || []).filter(v => v.vc === vc.name);
        const pgs = doms.flatMap(d => d.pgs.map(g => Object.assign({ dom: d.name }, g)));
        w.appendChild(h('div', { class: 'card' },
          h('div', { class: 'card-h' }, 'vCenter ', h('b', null, vc.name), ' · ', vc.ip, ' · Datacenter ', vc.datacenter, ' ', stateBadge(doms.length ? 'online' : 'offline'),
            h('span', { class: 'grow' }),
            h('button', { class: 'btn small', onclick: () => Views.vcenterDialog(vc) }, 'Bearbeiten'),
            h('button', { class: 'btn small', onclick: () => Views.esxiDialog(vc) }, '+ ESXi-Host'),
            iconBtn('🗑', 'Löschen', () => confirmBox('vCenter ' + vc.name + ' mit allen Hosts entfernen?', async () => { await API.sim('vcenters', { op: 'delete', kind: 'vcenter', name: vc.name }); await App.refreshState(); draw(); }), 'danger')),
          h('div', { class: 'muted small' }, 'Benutzer: ', vc.user || '—', doms.length ? ' · verbunden mit VMM Domain ' + doms.map(d => d.name).join(', ') : ' · keine verbundene VMM Domain'),
          h('h4', null, 'Distributed Port Groups (vom APIC angelegt)'),
          table([{ l: 'Port Group', f: r => r.name }, { l: 'DVS', f: r => r.dom }, { l: 'VLAN', f: r => 'vlan-' + r.vlan }, { l: 'EPG', f: r => r.epg.replace(/^uni\//, '') }], pgs,
            { empty: 'Keine Port Groups – erst wenn eine EPG an die VMM Domain gebunden ist, legt der APIC sie an.' }),
          h('h4', null, 'ESXi-Hosts'),
          table([{ l: 'Host', f: r => r.name }, { l: 'Uplinks', f: r => r.links.map(l => nodeName(l[0]) + ' ' + l[1]).join(' + ') }, { l: 'Im DVS', f: r => r.dvs.join(', ') || '—' },
            { l: 'Status', f: r => { const x = (st.vmm || []).flatMap(v => v.hosts).find(z => z.name === r.name); return x ? h('span', { title: x.reasons.join('; ') }, stateBadge(x.ok.length ? 'up' : 'down'), ' ', x.reasons.join('; ')) : stateBadge('—'); } },
            { l: 'VMs', f: r => String(r.vms.length) }], vc.hosts, {
            onRow: r => Views.esxiDialog(vc, r),
            actions: r => [h('button', { class: 'btn small', onclick: ev => { ev.stopPropagation(); Views.vmDialog(vc, r); } }, '+ VM'),
              iconBtn('🗑', 'Löschen', () => confirmBox('ESXi ' + r.name + ' entfernen?', async () => { await API.sim('vcenters', { op: 'delete', kind: 'esxi', vc: vc.name, name: r.name }); await App.refreshState(); draw(); }), 'danger')],
            empty: 'Keine ESXi-Hosts. Ein ESXi hängt mit 1–2 Uplinks an Leaf-Ports.',
          }),
          h('h4', null, 'Virtuelle Maschinen'),
          table([{ l: 'VM', f: r => r.name }, { l: 'ESXi', f: r => r.esxi }, { l: 'MAC', f: r => r.mac }, { l: 'IP', f: r => r.ip }, { l: 'Network Adapter', f: r => r.network || '—' },
            { l: 'Status', f: r => { const s = (st.vms || {})[r.name] || {}; return s.learned ? h('span', null, stateBadge('learned'), ' ', (s.epg || '').replace(/^uni\//, '')) : stateBadge(r.silent ? 'silent' : 'down'); } },
            { l: 'Hinweis', f: r => (((st.vms || {})[r.name] || {}).reasons || []).join('; ') }],
          vc.hosts.flatMap(x => x.vms.map(v => Object.assign({ esxi: x.name }, v))), {
            onRow: r => Views.vmDialog(vc, vc.hosts.find(x => x.name === r.esxi), r),
            actions: r => [iconBtn('🗑', 'Löschen', () => confirmBox('VM ' + r.name + ' entfernen?', async () => { await API.sim('vcenters', { op: 'delete', kind: 'vm', vc: vc.name, esxi: r.esxi, name: r.name }); await App.refreshState(); draw(); }), 'danger')],
            empty: 'Keine VMs.',
          })));
      });
    };
    draw();
    App.view = { auto: draw };
  },

  async vcSave(body, msg) {
    await API.sim('vcenters', body);
    toast(msg);
    await App.refreshState();
    if (App.view && App.view.auto) App.view.auto();
  },

  vcenterDialog(vc) {
    const f = buildForm([{ k: 'name', l: 'Name', req: true, ph: 'vcenter1' }, { k: 'ip', l: 'IP-Adresse', req: true, ph: '192.168.10.50' },
      { k: 'datacenter', l: 'Datacenter', req: true, ph: 'DC1' }, { k: 'user', l: 'Benutzer', ph: 'administrator@vsphere.local' },
      { k: 'pwd', l: 'Passwort', t: 'password', help: vc ? 'leer lassen = unverändert' : '' }],
    vc ? { name: vc.name, ip: vc.ip, datacenter: vc.datacenter, user: vc.user } : { datacenter: 'DC1', user: 'administrator@vsphere.local' }, {}, 'create');
    modal(vc ? 'vCenter ' + vc.name : 'vCenter hinzufügen', f.el, [{ l: 'Abbrechen' }, {
      l: 'Speichern', primary: true, fn: async () => {
        const v = f.get();
        if (vc && !v.pwd) v.pwd = '***';
        await Views.vcSave({ op: 'set', kind: 'vcenter', obj: v, old: vc ? vc.name : null }, 'vCenter ' + v.name + ' gespeichert');
      },
    }]);
  },

  esxiDialog(vc, x) {
    const st = App.state;
    const used = new Set();
    st.links.forEach(l => { used.add(l[0] + '|' + l[1]); used.add(l[2] + '|' + l[3]); });
    st.hosts.forEach(o => o.links.forEach(l => used.add(l[0] + '|' + l[1])));
    st.routers.forEach(o => used.add(o.serial + '|' + o.port));
    (st.vcenters || []).forEach(c => c.hosts.filter(o => !x || o.name !== x.name).forEach(o => o.links.forEach(l => used.add(l[0] + '|' + l[1]))));
    const leafOpts = leafNodes().map(n => [n.serial, (n.name || '(nicht registriert)') + (n.id ? ' – Node ' + n.id : '')]);
    const linkRow = (i, val) => {
      const leaf = h('select', null, i > 0 ? h('option', { value: '' }, '— kein zweiter Uplink —') : null, leafOpts.map(([v, l]) => h('option', { value: v }, l)));
      const port = h('select');
      const fill = () => {
        const cur = port.value || (val ? val[1] : '');
        clear(port);
        const n = leafNodes().find(z => z.serial === leaf.value);
        if (!n) return;
        for (let p = 1; p <= n.ports; p++) {
          const pn = 'eth1/' + p;
          const u = used.has(n.serial + '|' + pn);
          port.appendChild(h('option', { value: pn, disabled: u }, pn + (u ? ' (belegt)' : '')));
        }
        if (cur) port.value = cur;
        if (!port.value || port.selectedOptions[0].disabled) { const free = [...port.options].find(o => !o.disabled); if (free) port.value = free.value; }
      };
      leaf.onchange = fill;
      if (val) leaf.value = val[0]; else if (i > 0) leaf.value = '';
      fill();
      return { el: h('div', { class: 'pathw' }, leaf, port), get: () => leaf.value ? [leaf.value, port.value] : null };
    };
    const links = [linkRow(0, x && x.links[0]), linkRow(1, x && x.links[1])];
    const f = buildForm([{ k: 'name', l: 'Hostname', req: true, ph: 'esxi1' },
      { k: 'dvs', l: 'Distributed Switches', ph: 'VDS1', help: 'Namen der DVS (= VMM Domains), denen der Host im vCenter hinzugefügt ist, kommagetrennt' }],
    x ? { name: x.name, dvs: x.dvs.join(', ') } : {}, {}, 'create');
    const body = h('div', null, f.el, h('div', { class: 'form' },
      h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'vmnic0'), h('div', { class: 'fctl' }, links[0].el)),
      h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'vmnic1'), h('div', { class: 'fctl' }, links[1].el))));
    modal(x ? 'ESXi ' + x.name : 'ESXi-Host hinzufügen (' + vc.name + ')', body, [{ l: 'Abbrechen' }, {
      l: 'Speichern', primary: true, fn: async () => {
        const v = f.get();
        const obj = { name: v.name, dvs: String(v.dvs || '').split(',').map(z => z.trim()).filter(Boolean), links: links.map(l => l.get()).filter(Boolean) };
        await Views.vcSave({ op: 'set', kind: 'esxi', vc: vc.name, obj, old: x ? x.name : null }, 'ESXi ' + v.name + ' gespeichert');
      },
    }], { wide: true });
  },

  vmDialog(vc, esx, x) {
    const pgs = (App.state.vmm || []).filter(d => d.vc === vc.name).flatMap(d => d.pgs.map(g => g.name));
    const nets = [['', '— nicht verbunden —']].concat(pgs.map(p => [p, p]));
    if (x && x.network && !pgs.includes(x.network)) nets.push([x.network, x.network + ' (existiert nicht)']);
    const f = buildForm([{ k: 'name', l: 'VM-Name', req: true, ph: 'web-vm1' }, { k: 'mac', l: 'MAC-Adresse', req: true }, { k: 'ip', l: 'IP-Adresse/Maske', req: true, ph: '10.1.1.50/24' },
      { k: 'gw', l: 'Default Gateway', ph: '10.1.1.1' },
      { k: 'network', l: 'Network Adapter 1', t: 'select', o: nets, help: 'Port Group am DVS – erscheint erst, wenn der APIC sie angelegt hat' },
      { k: 'silent', l: 'Stille VM', t: 'yesno', cl: 'sendet nichts von sich aus' }],
    x ? { name: x.name, mac: x.mac, ip: x.ip, gw: x.gw, network: x.network, silent: x.silent ? 'yes' : 'no' } : { mac: randMac(), silent: 'no', network: pgs[0] || '' }, {}, 'create');
    modal(x ? 'VM ' + x.name : 'VM auf ' + esx.name + ' anlegen', f.el, [{ l: 'Abbrechen' }, {
      l: 'Speichern', primary: true, fn: async () => {
        const v = f.get();
        await Views.vcSave({ op: 'set', kind: 'vm', vc: vc.name, esxi: esx.name, obj: Object.assign(v, { silent: v.silent === 'yes' }), old: x ? x.name : null }, 'VM ' + v.name + ' gespeichert');
      },
    }]);
  },

  /* ================================================================ L4-L7 */
  async graphInstances(w, tn) {
    const st = App.state;
    const rows = (st.graphs || []).filter(g => g.dn.startsWith(tn + '/'));
    w.appendChild(paneHead('Deployed Graph Instances', tn));
    w.appendChild(table([{ l: 'Service Graph', f: r => nameOfDn(r.graph) }, { l: 'Contract', f: r => nameOfDn(r.brc) }, { l: 'Node', f: r => r.node || '—' },
      { l: 'Device', f: r => r.dev ? nameOfDn(r.dev) : '—' }, { l: 'State', f: r => stateBadge(r.state === 'applied' ? 'applied' : 'failed') },
      { l: 'Fehler', f: r => (r.reasons || []).join('; ') }], rows, { empty: 'Keine Service Graphs angewendet. Rechtsklick auf ein Service Graph Template > Apply L4-L7 Service Graph Template.' }));
  },

  async 'sim/devices'(w) {
    const draw = () => {
      clear(w);
      const st = App.state;
      w.appendChild(paneHead('Simulation – L4-L7 Geräte', 'Firewalls und andere Service-Appliances an Leaf-Ports',
        [h('button', { class: 'btn primary small', onclick: () => Views.deviceDialog() }, '+ Gerät')]));
      w.appendChild(h('div', { class: 'card note' }, 'Ein Gerät hat 802.1Q-Interfaces (VLAN, IP, MAC) und ein einfaches Regelwerk (z. B. "tcp/8080, icmp" oder "any"). '
        + 'Die ACI lernt die Interfaces, sobald ein Service Graph sie über Cluster Interfaces und Device Selection Policy einbindet.'));
      (st.devices || []).forEach(d => {
        w.appendChild(h('div', { class: 'card' },
          h('div', { class: 'card-h' }, h('b', null, d.name), ' · ', d.links.map(l => nodeName(l[0]) + ' ' + l[1]).join(' + '), ' · Regeln: ', d.allow.join(', '),
            h('span', { class: 'grow' }), h('button', { class: 'btn small', onclick: () => Views.deviceDialog(d) }, 'Bearbeiten'),
            iconBtn('🗑', 'Löschen', () => confirmBox('Gerät ' + d.name + ' entfernen?', async () => { await API.sim('devices', { op: 'delete', name: d.name }); await App.refreshState(); draw(); }), 'danger')),
          table([{ l: 'Interface', f: r => r.name }, { l: 'VLAN', f: r => r.vlan ? 'vlan-' + r.vlan : 'untagged' }, { l: 'IP', f: r => r.ip }, { l: 'MAC', f: r => r.mac },
            { l: 'Status', f: r => { const x = d.status[r.name] || {}; return x.learned ? h('span', null, stateBadge('learned'), ' Service-EPG') : stateBadge('down'); } },
            { l: 'Hinweis', f: r => ((d.status[r.name] || {}).reasons || []).join('; ') }], d.ifs)));
      });
      if (!(st.devices || []).length) w.appendChild(h('div', { class: 'card' }, 'Noch keine Geräte.'));
    };
    draw();
    App.view = { auto: draw };
  },

  deviceDialog(x) {
    const st = App.state;
    const leafOpts = leafNodes().map(n => [n.serial, (n.name || n.serial) + (n.id ? ' – Node ' + n.id : '')]);
    const f = buildForm([{ k: 'name', l: 'Name', req: true, ph: 'fw1' },
      { k: 'leaf', l: 'Leaf', t: 'select', o: leafOpts }, { k: 'port', l: 'Port', ph: 'eth1/20', req: true },
      { k: 'allow', l: 'Regelwerk', ph: 'tcp/8080, icmp  oder  any', help: 'Was die Firewall durchlässt' },
      { k: '_ifs', l: 'Interfaces', t: 'rows', start: true, cols: [{ k: 'name', l: 'Name', ph: 'outside', req: true }, { k: 'vlan', l: 'VLAN', ph: '401', w: '70px' },
        { k: 'ip', l: 'IP/Maske', ph: '192.168.100.10/24', req: true }, { k: 'mac', l: 'MAC', ph: '00:50:56:FA:01:01', req: true }] }],
    x ? { name: x.name, leaf: x.links[0][0], port: x.links[0][1], allow: x.allow.join(', '), _ifs: x.ifs.map(i => Object.assign({}, i, { vlan: String(i.vlan) })) }
      : { leaf: (leafOpts[0] || [''])[0], allow: 'any', _ifs: [{ mac: randMac() }] }, {}, 'create');
    modal(x ? 'Gerät ' + x.name : 'L4-L7 Gerät hinzufügen', f.el, [{ l: 'Abbrechen' }, {
      l: 'Speichern', primary: true, fn: async () => {
        const v = f.get();
        const obj = { name: v.name, links: [[v.leaf, v.port]], allow: String(v.allow || 'any').split(',').map(z => z.trim()).filter(Boolean),
          ifs: (v._ifs || []).filter(i => i.name).map(i => ({ name: i.name, vlan: Number(i.vlan || 0), ip: i.ip, mac: i.mac })) };
        await API.sim('devices', { op: 'set', obj, old: x ? x.name : null });
        toast('Gerät ' + v.name + ' gespeichert');
        await App.refreshState();
        if (App.view && App.view.auto) App.view.auto();
      },
    }], { wide: true });
  },

  /* ================================================================ Operations */
  async 'ops/capacity'(w) {
    const c = await API.sim('capacity');
    w.appendChild(paneHead('Capacity Dashboard', 'Auslastung der Leafs (Grenzwerte eines N9K-C93180YC-FX)'));
    w.appendChild(h('div', { class: 'cards4' }, Object.entries({ Tenants: c.fabric.tenants, VRFs: c.fabric.vrfs, 'Bridge Domains': c.fabric.bds, EPGs: c.fabric.epgs, Contracts: c.fabric.contracts, L3Outs: c.fabric.l3outs, Endpoints: c.fabric.endpoints })
      .map(([k, v]) => h('div', { class: 'kpi' }, h('span', null, k), h('b', null, String(v))))));
    w.appendChild(table([{ l: 'Leaf', f: r => r.node }, { l: 'VLANs', f: r => pct(r.vlans, r.vlansMax) }, { l: 'Endpoints', f: r => pct(r.endpoints, r.endpointsMax) },
      { l: 'Policy CAM (Zoning Rules)', f: r => pct(r.rules, r.rulesMax) }, { l: 'LPM Routes', f: r => pct(r.routes, r.routesMax) }, { l: 'VRFs', f: r => pct(r.vrfs, r.vrfsMax) }], c.leafs));
  },
});
