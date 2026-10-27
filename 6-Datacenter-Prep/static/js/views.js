/* Spezialansichten: System, Fabric, Admin, Operations, Simulation */
'use strict';

function md(text) {
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const inline = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/\*([^*]+)\*/g, '<i>$1</i>');
  const out = [];
  let list = null;
  String(text || '').split('\n').forEach(line => {
    const m = /^\s*(?:[-*]|\d+\.)\s+(.*)$/.exec(line);
    if (m) { if (!list) { list = []; } list.push('<li>' + inline(m[1]) + '</li>'); return; }
    if (list) { out.push('<ul>' + list.join('') + '</ul>'); list = null; }
    if (/^### /.test(line)) out.push('<h4>' + inline(line.slice(4)) + '</h4>');
    else if (/^## /.test(line)) out.push('<h3>' + inline(line.slice(3)) + '</h3>');
    else if (line.trim()) out.push('<p>' + inline(line) + '</p>');
  });
  if (list) out.push('<ul>' + list.join('') + '</ul>');
  return h('div', { class: 'md', html: out.join('') });
}

const leafNodes = () => (App.state.nodes || []).filter(n => n.role === 'leaf');
const nodeName = serial => { const n = (App.state.nodes || []).find(x => x.serial === serial); return n ? (n.name ? n.name + ' (' + n.id + ')' : serial) : serial; };
const randMac = () => '00:50:56:' + [0, 0, 0].map(() => Math.floor(Math.random() * 256).toString(16).padStart(2, '0')).join(':').toUpperCase();

const Views = {
  /* ================================================================ System */
  async 'system/dash'(w) {
    const draw = async () => {
      const [tn, nodes, faults] = await Promise.all([API.cls('fvTenant', 'rsp-subtree-include=health', true), API.cls('fabricNode', 'rsp-subtree-include=health', true), API.cls('faultInst', '', true)]);
      clear(w);
      const st = App.state;
      const cnt = s => st.nodes.filter(n => n.state === s).length;
      const fc = s => faults.filter(f => f.faultInst.attributes.severity === s).length;
      const health = x => { const c = Object.values(x)[0].children; return c ? c[0].healthInst.attributes.cur : 100; };
      w.appendChild(paneHead('System – Dashboard', 'Überblick über Fabric, Tenants und Faults'));
      w.appendChild(h('div', { class: 'cards4' },
        h('div', { class: 'kpi' }, h('span', null, 'Aktive Switches'), h('b', null, cnt('active') + ' / ' + st.nodes.length)),
        h('div', { class: 'kpi' }, h('span', null, 'In Discovery / wartend'), h('b', null, cnt('discovering') + ' / ' + st.pending.length)),
        h('div', { class: 'kpi' }, h('span', null, 'Tenants'), h('b', null, String(tn.length))),
        h('div', { class: 'kpi' }, h('span', null, 'Faults (crit/maj/min/warn)'), h('b', null, [fc('critical'), fc('major'), fc('minor'), fc('warning')].join(' / ')))));
      if (st.lab) w.appendChild(h('div', { class: 'card note' }, 'Aktuelles Lab: ', h('b', null, st.lab.title), ' – ', h('a', { class: 'lnk', onclick: () => App.go('sim', 'labs') }, 'Aufgaben und Prüfung öffnen')));
      if (st.pending.length) w.appendChild(h('div', { class: 'card note warn' }, st.pending.length + ' Switch(es) warten auf Registrierung: ', h('a', { class: 'lnk', onclick: () => App.go('fabric', 'inventory', 'membership') }, 'Fabric Membership öffnen')));
      w.appendChild(h('div', { class: 'cols2' },
        h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Tenants'),
          table([{ l: 'Tenant', f: r => h('a', { class: 'lnk', onclick: () => App.go('tenants', r.fvTenant.attributes.name) }, r.fvTenant.attributes.name) }, { l: 'Health', f: r => healthBadge(health(r)) }], tn)),
        h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Nodes'),
          table([{ l: 'Node', f: r => r.fabricNode.attributes.name }, { l: 'ID', f: r => r.fabricNode.attributes.id }, { l: 'Role', f: r => r.fabricNode.attributes.role },
            { l: 'State', f: r => stateBadge(r.fabricNode.attributes.fabricSt === 'unknown' ? 'active' : r.fabricNode.attributes.fabricSt) }, { l: 'Health', f: r => healthBadge(health(r)) }],
          nodes.sort((a, b) => a.fabricNode.attributes.id - b.fabricNode.attributes.id)))));
    };
    await draw();
    App.view = { auto: draw };
  },

  async 'system/faults'(w) {
    let sev = '';
    const draw = async () => {
      const rows = (await API.cls('faultInst', 'order-by=faultInst.severity')).map(r => r.faultInst.attributes);
      const order = { critical: 0, major: 1, minor: 2, warning: 3 };
      rows.sort((a, b) => order[a.severity] - order[b.severity] || a.dn.localeCompare(b.dn));
      clear(w);
      w.appendChild(paneHead('Faults', rows.length + ' aktive Faults in der Fabric', [iconBtn('⟳', 'Aktualisieren', draw)]));
      const bar = h('div', { class: 'filterbar' }, ['', 'critical', 'major', 'minor', 'warning'].map(s => h('button', { class: 'btn small' + (s === sev ? ' primary' : ''), onclick: () => { sev = s; draw(); } }, s || 'Alle')));
      w.appendChild(bar);
      w.appendChild(faultTable(rows.filter(r => !sev || r.severity === sev), true));
    };
    await draw();
    App.view = { auto: draw };
  },

  settingsRoots() {
    return [{ key: 'bgprr', label: 'BGP Route Reflector', icon: 'RR', kind: 'view', view: w => Views.bgpRR(w) },
      { key: 'sysinfo', label: 'Über den Simulator', icon: 'i', kind: 'view', view: w => Views.about(w) }];
  },

  async bgpRR(w) {
    const dn = 'uni/fabric/bgpInstP-default';
    await MIT.load(dn);
    clear(w);
    w.appendChild(paneHead('BGP Route Reflector Policy – default', dn));
    w.appendChild(h('div', { class: 'card note' }, 'Die ACI verteilt externe Routen (aus L3Outs) per MP-BGP an alle Leafs. Dafür braucht die Fabric eine AS-Nummer und mindestens einen Spine als Route Reflector. Ohne diese Policy kennen nur die Border Leafs die externen Routen.'));
    const asn = MIT.a(dn + '/as');
    const inp = h('input', { value: asn ? asn.asn : '', placeholder: '65001' });
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Properties'),
      h('div', { class: 'form' }, h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'Autonomous System Number'), h('div', { class: 'fctl' }, inp))),
      h('div', { class: 'formbtns' }, h('button', {
        class: 'btn primary', onclick: async () => {
          try {
            await API.postMo(dn, { bgpInstPol: { attributes: {}, children: [inp.value ? { bgpAsP: { attributes: { asn: inp.value } } } : { bgpAsP: { attributes: { status: 'deleted' } } }] } });
            toast('Gespeichert'); App.reload();
          } catch (e) { errToast(e); }
        },
      }, 'Submit'))));
    if (!MIT.get(dn + '/rr')) { await API.postMo(dn, { bgpInstPol: { attributes: {}, children: [{ bgpRRP: { attributes: {} } }] } }); await MIT.load(dn); }
    const holder = h('div', { class: 'card' });
    folderView(holder, dn + '/rr', { l: 'Route Reflector Nodes', cls: ['bgpRRNodePEp'], flat: 1 }, true);
    w.appendChild(holder);
  },

  about(w) {
    w.appendChild(paneHead('Über den Simulator', ''));
    w.appendChild(h('div', { class: 'card' }, md([
      '## Datacenter Prep',
      'Simuliert einen APIC mit einer Fabric aus 2 Spines und 4 Leafs. Die REST-API entspricht dem APIC (`/api/aaaLogin.json`, `/api/mo/...`, `/api/class/...`), Ansible (`cisco.aci`), Terraform und Postman funktionieren damit.',
      '- Konfiguration im Tenant, in den Access Policies und in Fabric Membership wird wie beim APIC aufgelöst und deployt.',
      '- Simulierte Hosts und externe Router (Menü **Simulation**) erzeugen Endpoints, OSPF-/BGP-Nachbarschaften und Traffic.',
      '- Faults, CLI (`show endpoint`, `show zoning-rule`, `moquery`) und der Traffic-Test zeigen das Ergebnis.',
      'Kein offizielles Cisco-Produkt. Cisco, ACI und APIC sind Marken von Cisco Systems, Inc.',
    ].join('\n'))));
  },

  /* ================================================================ Tenants */
  async 'tenants/all'(w) {
    const [tn, faults] = await Promise.all([API.cls('fvTenant', 'rsp-subtree-include=health'), API.cls('faultInst', '', true)]);
    const fl = faults.map(f => f.faultInst.attributes);
    w.appendChild(paneHead('All Tenants', tn.length + ' Tenants', [h('button', { class: 'btn primary small', onclick: () => App.addTenant() }, '+ Add Tenant')]));
    w.appendChild(table([
      { l: 'Name', f: r => h('a', { class: 'lnk', onclick: () => App.go('tenants', r.fvTenant.attributes.name) }, r.fvTenant.attributes.name) },
      { l: 'Description', f: r => r.fvTenant.attributes.descr },
      { l: 'Health', f: r => healthBadge(r.fvTenant.children ? r.fvTenant.children[0].healthInst.attributes.cur : 100) },
      { l: 'Faults', f: r => String(fl.filter(f => f.dn.startsWith(r.fvTenant.attributes.dn + '/')).length) },
    ], tn, { onRow: r => App.go('tenants', r.fvTenant.attributes.name) }));
  },

  apTopology(body, apDn) {
    const epgs = MIT.kids(apDn, ['fvAEPg']);
    const contracts = new Map();
    epgs.forEach(e => {
      MIT.kids(e, ['fvRsProv', 'fvRsCons']).forEach(r => {
        const a = MIT.a(r);
        const k = a.tnVzBrCPName;
        if (!contracts.has(k)) contracts.set(k, { prov: [], cons: [] });
        contracts.get(k)[MIT.get(r).cls === 'fvRsProv' ? 'prov' : 'cons'].push(e);
      });
    });
    const W = Math.max(640, epgs.length * 170 + 60);
    const svg = ['<svg class="aptopo" viewBox="0 0 ' + W + ' 300" xmlns="http://www.w3.org/2000/svg">'];
    const ex = i => 40 + i * 170;
    const cx = i => 60 + i * 150;
    [...contracts.entries()].forEach(([name, c], i) => {
      c.cons.forEach(e => svg.push('<line x1="' + (ex(epgs.indexOf(e)) + 65) + '" y1="200" x2="' + cx(i) + '" y2="80" class="cons"/>'));
      c.prov.forEach(e => svg.push('<line x1="' + cx(i) + '" y1="80" x2="' + (ex(epgs.indexOf(e)) + 65) + '" y2="200" class="prov"/>'));
      svg.push('<circle cx="' + cx(i) + '" cy="70" r="20" class="brc"/><text x="' + cx(i) + '" y="40" class="tc">' + name + '</text><text x="' + cx(i) + '" y="75" class="tc small">C</text>');
    });
    epgs.forEach((e, i) => {
      const bd = relOf(e, 'fvRsBd', 'tnFvBDName') || 'default';
      svg.push('<rect x="' + ex(i) + '" y="200" width="130" height="46" rx="6" class="epg"/><text x="' + (ex(i) + 65) + '" y="220" class="tc">' + MIT.a(e).name + '</text><text x="' + (ex(i) + 65) + '" y="237" class="tc small">BD: ' + bd + '</text>');
    });
    svg.push('</svg>');
    body.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Application Profile Topology'),
      h('div', { class: 'muted small' }, 'Grün: Consumer → Contract, Blau: Contract → Provider'), h('div', { html: svg.join('') })));
  },

  /* ================================================================ Fabric */
  inventoryRoots() {
    return [
      { key: 'topology', label: 'Topology', icon: '⌗', kind: 'view', view: w => Views.topologyPage(w, false) },
      {
        key: 'pod1', label: 'Pod 1', icon: 'P', kind: 'view', view: w => Views.podView(w),
        kids: () => (App.state.nodes || []).filter(n => n.id && ['active', 'discovering', 'inactive'].includes(n.state)).sort((a, b) => a.id - b.id)
          .map(n => ({ key: 'node:' + n.id, label: n.name + ' (Node-' + n.id + ')', icon: n.role === 'spine' ? 'SP' : 'LF', kind: 'view', view: w2 => Views.nodeView(w2, n.id) })),
      },
      { key: 'membership', label: 'Fabric Membership', icon: 'FM', kind: 'view', view: w => Views.membership(w) },
    ];
  },

  podView(w) {
    const draw = () => {
      clear(w);
      w.appendChild(paneHead('Pod 1', 'Fabric-Knoten im Pod'));
      w.appendChild(table([{ l: 'Name', f: n => n.name }, { l: 'Node ID', f: n => n.id }, { l: 'Role', f: n => n.role }, { l: 'Model', f: n => n.model },
        { l: 'Serial', f: n => n.serial }, { l: 'TEP', f: n => n.tep }, { l: 'State', f: n => stateBadge(n.state) }],
      App.state.nodes.filter(n => n.id).sort((a, b) => a.id - b.id), { onRow: n => App.select('node:' + n.id) }));
    };
    draw();
    App.view = { auto: () => { draw(); App.renderTree(); } };
  },

  async nodeView(w, id) {
    const n = App.state.nodes.find(x => x.id === id);
    if (!n) return;
    w.appendChild(paneHead((n.role === 'spine' ? 'Spine' : 'Leaf') + ' – ' + n.name, 'topology/pod-' + POD() + '/node-' + id, [h('button', { class: 'btn small', onclick: () => Term.open(n.name) }, '⌨ CLI öffnen')]));
    const body = h('div', { class: 'wbody' });
    const show = async tab => {
      clear(body);
      if (tab === 'general') {
        body.appendChild(h('div', { class: 'info' }, [['Node ID', n.id], ['Name', n.name], ['Role', n.role], ['Model', n.model], ['Serial', n.serial], ['TEP Address', n.tep], ['State', n.state],
          ['Version', n.state === 'active' ? 'n9000-16.0(5h)' : '—']].map(([k, v]) => h('div', null, h('span', null, k), h('b', null, String(v))))));
        if (n.state !== 'active') body.appendChild(h('div', { class: 'card note warn' }, 'Dieser Switch ist noch nicht aktiv (Discovery läuft oder kein Nachbar aktiv).'));
      }
      if (tab === 'if') {
        const rows = await API.cls('topology/pod-' + POD() + '/node-' + id + '/l1PhysIf', 'rsp-subtree=children');
        const data = rows.map(r => { const a = r.l1PhysIf.attributes; const c = (r.l1PhysIf.children || [])[0]; return Object.assign({}, a, { oper: c ? c.ethpmPhysIf.attributes : {} }); })
          .sort((a, b) => portNum(a.id) - portNum(b.id));
        const upOnly = h('input', { type: 'checkbox', checked: true });
        const tbl = h('div');
        const render = () => {
          clear(tbl).appendChild(table([{ l: 'Interface', f: r => r.id }, { l: 'Admin', f: r => r.adminSt }, { l: 'Oper', f: r => stateBadge(r.oper.operSt) }, { l: 'Reason', f: r => r.oper.operStQual },
            { l: 'Usage', f: r => r.usage }, { l: 'Layer', f: r => r.layer }, { l: 'Speed', f: r => r.oper.operSpeed }, { l: 'VLANs', f: r => r.oper.operVlans }],
          data.filter(r => !upOnly.checked || r.oper.operSt === 'up' || r.oper.operStQual !== 'link-not-connected')));
        };
        upOnly.onchange = render;
        body.appendChild(h('label', { class: 'check' }, upOnly, h('span', null, 'nur verbundene Ports')));
        body.appendChild(tbl);
        render();
      }
      if (tab === 'cli') Term.embed(body, n.name);
    };
    w.appendChild(tabsBar([['general', 'General'], ['if', 'Interfaces'], ['cli', 'CLI']], show, 'general'));
    w.appendChild(body);
    show('general');
  },

  async membership(w) {
    let tab = 'reg';
    const draw = async () => {
      const [ident, pend] = await Promise.all([API.cls('fabricNodeIdentP', '', true), API.cls('dhcpClient', '', true)]);
      clear(w);
      w.appendChild(paneHead('Fabric Membership', 'Switches registrieren: Serial → Node ID und Name', [iconBtn('⟳', 'Aktualisieren', draw)]));
      const body = h('div', { class: 'wbody' });
      w.appendChild(tabsBar([['reg', 'Registered Nodes (' + ident.length + ')'], ['pend', 'Nodes Pending Registration (' + pend.length + ')']], t => { tab = t; draw(); }, tab));
      w.appendChild(body);
      if (tab === 'reg') {
        const rows = ident.map(r => r.fabricNodeIdentP.attributes).map(a => Object.assign(a, { st: App.state.nodes.find(n => n.serial === a.serial) }));
        body.appendChild(table([{ l: 'Serial Number', f: r => r.serial }, { l: 'Pod ID', f: r => r.podId }, { l: 'Node ID', f: r => r.nodeId }, { l: 'Name', f: r => r.name },
          { l: 'Role', f: r => r.st ? r.st.role : 'unbekannt' }, { l: 'IP (TEP)', f: r => r.st && r.st.state === 'active' ? r.st.tep : '0.0.0.0' },
          { l: 'Status', f: r => stateBadge(r.st ? r.st.state : 'nicht verkabelt') }],
        rows, { actions: r => [iconBtn('🗑', 'Remove From Controller', () => confirmBox('Node ' + r.nodeId + ' (' + r.serial + ') aus der Fabric entfernen?', async () => { await API.delMo(r.dn); toast('Entfernt'); App.refreshState().then(draw); }), 'danger')], empty: 'Noch keine Switches registriert. Siehe Tab „Nodes Pending Registration".' }));
      } else {
        body.appendChild(h('div', { class: 'card note' }, 'Ein Switch erscheint hier, sobald er per LLDP an einem aktiven Knoten erkannt wird (zuerst der Leaf am APIC, danach die Spines, dann die übrigen Leafs).'));
        body.appendChild(table([{ l: 'Serial Number', f: r => r.id }, { l: 'Model', f: r => r.model }, { l: 'Role', f: r => r.nodeRole }, { l: 'Pod', f: r => r.podId }, { l: 'Status', f: () => stateBadge('pending') }],
          pend.map(r => r.dhcpClient.attributes), { actions: r => [h('button', { class: 'btn primary small', onclick: () => Views.registerDialog(r, draw) }, 'Register')], empty: 'Keine Switches warten auf Registrierung.' }));
      }
    };
    await draw();
    App.view = { auto: () => { draw(); if (App.navEl) App.renderTree(); } };
  },

  registerDialog(r, after) {
    const f = buildForm([{ k: 'serial', l: 'Serial Number', ro: true }, { k: 'podId', l: 'Pod ID' }, { k: 'nodeId', l: 'Node ID', req: true, ph: r.nodeRole === 'spine' ? '201' : '101' },
      { k: 'name', l: 'Node Name', req: true, ph: r.nodeRole === 'spine' ? 'spine201' : 'leaf101' }, { k: 'role', l: 'Role', ro: true }], { serial: r.id, podId: '1', role: r.nodeRole }, { cls: 'fabricNodeIdentP' }, 'create');
    modal('Register ' + r.id, f.el, [{ l: 'Abbrechen' }, {
      l: 'Register', primary: true, fn: async () => {
        const v = f.get();
        if (!v.nodeId || !v.name) throw new ApiError('Eingabe', 'Node ID und Name angeben');
        await API.postMo('uni/controller/nodeidentpol', { fabricNodeIdentP: { attributes: { serial: r.id, nodeId: v.nodeId, name: v.name, podId: v.podId || '1' } } });
        toast(v.name + ' registriert – Discovery läuft');
        await App.refreshState();
        after();
      },
    }]);
  },

  async 'fabric/fabricpol'(w) {
    w.appendChild(paneHead('Fabric Policies', ''));
    w.appendChild(h('div', { class: 'card' }, md('Die Fabric Policies (Pod-, Switch- und Monitoring-Policies) laufen im Simulator mit Standardwerten. Die für den Betrieb wichtige **BGP Route Reflector Policy** findest du unter **System > System Settings > BGP Route Reflector**, die vPC-Domänen unter **Fabric > Access Policies > Policies > Switch > Virtual Port Channel default**.')));
  },

  accessIntro(w) {
    w.appendChild(paneHead('Access Policies', 'uni/infra'));
    w.appendChild(h('div', { class: 'card' }, md([
      '## Die Kette der Access Policies',
      'Damit eine EPG auf einem Port mit einem VLAN deployt wird, muss die ganze Kette stehen:',
      '1. **VLAN Pool** (Pools > VLAN) mit dem VLAN-Bereich, Allocation Mode *static* für Static Ports.',
      '2. **Domain** (Physical oder L3 Domain), die auf den VLAN Pool zeigt.',
      '3. **AAEP** (Policies > Global > Attachable Access Entity Profiles), das die Domain enthält.',
      '4. **Interface Policy Group** (Leaf Access Port, PC oder vPC), die auf das AAEP zeigt.',
      '5. **Leaf Interface Profile** mit Access Port Selector (Ports) → Policy Group.',
      '6. **Leaf Switch Profile** mit Leaf Selector (Node-IDs) → Interface Profile.',
      'Im Tenant hängt die EPG dann an derselben **Domain** und bekommt **Static Ports** mit dem VLAN. Fehlt ein Glied, meldet die EPG den Fault **F0467** (invalid-vlan oder invalid-path).',
    ].join('\n'))));
  },

  async 'apps/apps'(w) {
    w.appendChild(paneHead('Apps', ''));
    w.appendChild(h('div', { class: 'card' }, md('Keine Apps installiert. Zum Nachsehen von Objekten gibt es **Visore** (Object Store Browser) oben rechts, für REST-Aufrufe den **API Inspector**.')));
  },

  /* ================================================================ Admin */
  async 'admin/aaa'(w) {
    await MIT.load('uni/userext');
    App.view = null;
    App.roots = null;
    const holder = h('div', { class: 'card' });
    w.appendChild(paneHead('AAA – Local Users', 'uni/userext'));
    folderView(holder, 'uni/userext', { l: 'Local Users', cls: ['aaaUser'], flat: 1 }, true);
    w.appendChild(holder);
  },

  async 'admin/rollback'(w) {
    const draw = async () => {
      const list = await API.sim('snapshots');
      clear(w);
      w.appendChild(paneHead('Config Rollbacks', 'Snapshots der Konfiguration erstellen und zurückspielen', [h('button', {
        class: 'btn primary small', onclick: () => {
          const f = buildForm([{ k: 'name', l: 'Name', req: true, ph: 'vor-lab-3' }, { k: 'descr', l: 'Beschreibung' }], { name: 'snapshot-' + new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '') }, {}, 'create');
          modal('Create a snapshot now', f.el, [{ l: 'Abbrechen' }, { l: 'Erstellen', primary: true, fn: async () => { const v = f.get(); await API.sim('snapshots', { op: 'create', name: v.name, descr: v.descr }); toast('Snapshot erstellt'); draw(); } }]);
        },
      }, '+ Create a snapshot now')]));
      w.appendChild(table([{ l: 'Name', f: r => r.name }, { l: 'Erstellt', f: r => fmtTs(r.created) }, { l: 'Beschreibung', f: r => r.descr }, { l: 'Objekte', f: r => r.objects }], list, {
        actions: r => [h('button', { class: 'btn small', onclick: () => confirmBox('Konfiguration auf Snapshot „' + r.name + '" zurücksetzen? Änderungen seitdem gehen verloren.', async () => { await API.sim('snapshots', { op: 'rollback', name: r.name }); toast('Rollback durchgeführt'); App.refreshState(); }) }, 'Rollback'),
          iconBtn('🗑', 'Löschen', () => confirmBox('Snapshot löschen?', async () => { await API.sim('snapshots', { op: 'delete', name: r.name }); draw(); }), 'danger')],
        empty: 'Noch keine Snapshots.',
      }));
    };
    await draw();
  },

  async 'admin/impexp'(w) {
    const tn = (await API.cls('fvTenant', '', true)).map(r => r.fvTenant.attributes.name);
    const sel = h('select', null, h('option', { value: 'uni' }, 'Gesamte Konfiguration (uni)'), tn.map(n => h('option', { value: 'uni/tn-' + n }, 'Tenant ' + n)),
      h('option', { value: 'uni/infra' }, 'Access Policies (uni/infra)'));
    w.appendChild(paneHead('Import/Export', 'Konfiguration als JSON sichern und einspielen'));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Export'), h('div', { class: 'form' }, h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'Bereich'), h('div', { class: 'fctl' }, sel))),
      h('div', { class: 'formbtns' }, h('button', { class: 'btn primary', onclick: () => saveAs(sel.value) }, 'JSON herunterladen'))));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Import'),
      h('p', null, 'Eine JSON-Datei im APIC-Format (z. B. aus „Save as" oder einem echten APIC) wird per POST an /api/mo/uni.json gesendet und mit der bestehenden Konfiguration zusammengeführt (Merge).'),
      h('div', { class: 'formbtns' }, h('button', { class: 'btn primary', onclick: () => postJson('uni') }, 'JSON-Datei hochladen'))));
  },

  /* ================================================================ Operations */
  async 'ops/vis'(w) {
    const st = App.state;
    const srcSel = h('select', null, st.hosts.map(x => h('option', { value: x.name }, 'Host ' + x.name + ' (' + x.ip + ')')), st.routers.map(x => h('option', { value: x.name }, 'Router ' + x.name + ' (' + x.ip + ')')));
    const dstSel = h('select', null, st.hosts.map(x => h('option', { value: x.name }, 'Host ' + x.name + ' (' + x.ip + ')')), st.routers.map(x => h('option', { value: x.name }, 'Router ' + x.name + ' (' + x.ip + ')')), h('option', { value: '__ip' }, 'Andere IP-Adresse …'));
    const ip = h('input', { placeholder: 'z. B. 8.8.8.8 oder Gateway 10.1.1.1', style: { display: 'none' } });
    dstSel.onchange = () => { ip.style.display = dstSel.value === '__ip' ? '' : 'none'; };
    const proto = h('select', null, h('option', { value: 'icmp' }, 'ICMP (ping)'), h('option', { value: 'tcp' }, 'TCP'), h('option', { value: 'udp' }, 'UDP'));
    const port = h('input', { placeholder: 'Port', style: { width: '80px' } });
    const out = h('div');
    const run = async () => {
      try {
        const r = await API.sim('traffic', { src: srcSel.value, dst: dstSel.value === '__ip' ? ip.value : dstSel.value, proto: proto.value, port: Number(port.value || 0) });
        clear(out).appendChild(h('div', { class: 'card trace ' + (r.ok ? 'ok' : 'bad') }, h('div', { class: 'trace-sum' }, r.ok ? '✔ ' : '✖ ', r.summary),
          h('ol', null, r.steps.map(s => h('li', { class: s.ok === false ? 'bad' : s.ok ? 'ok' : 'info' }, h('b', null, s.title), s.detail ? h('div', { class: 'muted' }, s.detail) : null)))));
      } catch (e) { errToast(e); }
    };
    w.appendChild(paneHead('Visibility & Troubleshooting', 'Traffic zwischen Endpoints testen – Schritt für Schritt durch die Fabric'));
    if (!st.hosts.length) w.appendChild(h('div', { class: 'card note warn' }, 'Noch keine simulierten Hosts. Lege unter ', h('a', { class: 'lnk', onclick: () => App.go('sim', 'topo') }, 'Simulation > Topologie & Hosts'), ' Hosts an oder lade ein Lab.'));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'traffic' }, h('label', null, 'Quelle'), srcSel, h('label', null, 'Ziel'), dstSel, ip, h('label', null, 'Protokoll'), proto, port,
      h('button', { class: 'btn primary', onclick: run }, 'Start'))));
    w.appendChild(out);
  },

  async 'ops/ep'(w) {
    const q = h('input', { placeholder: 'IP oder MAC, z. B. 10.1.1.10', style: { width: '260px' } });
    const res = h('div');
    const search = async () => {
      const v = q.value.trim();
      const filt = v ? 'query-target-filter=' + encodeURIComponent('or(eq(fvCEp.ip,"' + v + '"),eq(fvCEp.mac,"' + v.toUpperCase() + '"),wcard(fvCEp.dn,"' + v + '"))') : '';
      const rows = (await API.cls('fvCEp', filt)).map(r => r.fvCEp.attributes);
      clear(res).appendChild(table([{ l: 'MAC', f: r => r.mac }, { l: 'IP', f: r => r.ip }, { l: 'Encap', f: r => r.encap }, { l: 'Path', f: r => pathLabel(r.fabricPathDn) },
        { l: 'EPG', f: r => h('a', { class: 'lnk', onclick: () => App.gotoDn(parentDn(r.dn)) }, parentDn(r.dn).replace(/^uni\//, '')) }], rows, { empty: 'Kein Endpoint gefunden.' }));
    };
    q.addEventListener('keydown', e => { if (e.key === 'Enter') search(); });
    w.appendChild(paneHead('EP Tracker', 'Wo ist ein Endpoint gelernt?'));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'traffic' }, h('label', null, 'Endpoint'), q, h('button', { class: 'btn primary', onclick: search }, 'Suchen'))));
    w.appendChild(res);
    search();
  },

  /* ================================================================ Simulation */
  topologySvg(st, opts) {
    const nodes = st.nodes;
    const spines = nodes.filter(n => n.role === 'spine');
    const leaves = nodes.filter(n => n.role === 'leaf');
    const W = Math.max(900, leaves.length * 210 + 120);
    const pos = {};
    spines.forEach((n, i) => { pos[n.serial] = [W / 2 + (i - (spines.length - 1) / 2) * 300, 50]; });
    leaves.forEach((n, i) => { pos[n.serial] = [110 + i * ((W - 220) / Math.max(1, leaves.length - 1)), 200]; });
    pos[st.apic.serial] = [W / 2, 330];
    const bottom = [];
    st.hosts.forEach(x => bottom.push({ kind: 'host', o: x, x: avg(x.links.map(l => (pos[l[0]] || [0])[0])) }));
    st.routers.forEach(x => bottom.push({ kind: 'router', o: x, x: avg((x.links || [[x.serial, x.port]]).map(l => (pos[l[0]] || [0])[0])) }));
    (st.vcenters || []).forEach(vc => vc.hosts.forEach(x => bottom.push({ kind: 'esxi', o: x, vc, x: avg(x.links.map(l => (pos[l[0]] || [0])[0])) })));
    bottom.sort((a, b) => a.x - b.x);
    let lastX = -999;
    bottom.forEach(b => { b.x = Math.max(b.x, lastX + 105); lastX = b.x; });
    const shift = bottom.length ? Math.min(0, (W - 60) - lastX) : 0;
    bottom.forEach(b => { b.x += shift; b.y = 400; });
    const H = bottom.length ? 470 : 380;
    const s = ['<svg class="topo" viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg">'];
    const nstate = serial => { if (serial === st.apic.serial) return 'active'; const n = nodes.find(x => x.serial === serial); return n ? n.state : 'undiscovered'; };
    st.links.forEach(([a, , b]) => {
      const pa = pos[a], pb = pos[b];
      if (!pa || !pb) return;
      const ok = nstate(a) === 'active' && nstate(b) === 'active';
      s.push('<line x1="' + pa[0] + '" y1="' + pa[1] + '" x2="' + pb[0] + '" y2="' + pb[1] + '" class="lnk ' + (ok ? 'up' : 'down') + '"/>');
    });
    bottom.forEach(b => {
      const links = b.kind === 'router' ? (b.o.links || [[b.o.serial, b.o.port]]) : b.o.links;
      if (b.kind === 'esxi') b.up = (st.vmm || []).some(v => v.hosts.some(x => x.name === b.o.name && x.ok.length));
      const cls = b.kind === 'host' ? (b.o.status.learned ? 'up' : 'warn') : b.kind === 'esxi' ? (b.up ? 'up' : 'warn') : (b.o.status.link && b.o.status.adj !== 'DOWN' && b.o.status.adj !== 'EXSTART' && b.o.status.adj !== 'Idle' ? 'up' : 'warn');
      links.forEach(([ser, port]) => {
        const p = pos[ser];
        if (!p) return;
        s.push('<line x1="' + p[0] + '" y1="' + (p[1] + 18) + '" x2="' + b.x + '" y2="' + (b.y - 16) + '" class="lnk ' + cls + '"/>');
        const mx = p[0] + (b.x - p[0]) * 0.22, my = p[1] + 18 + (b.y - 16 - p[1] - 18) * 0.22;
        s.push('<text x="' + mx + '" y="' + my + '" class="plab">' + port.replace('eth', '') + '</text>');
      });
    });
    const box = (x, y, w2, hh, cls, l1, l2, data) => s.push('<g class="nd ' + cls + '" data-k="' + data + '"><rect x="' + (x - w2 / 2) + '" y="' + (y - hh / 2) + '" width="' + w2 + '" height="' + hh + '" rx="6"/><text x="' + x + '" y="' + (y - 2) + '" class="t1">' + l1 + '</text><text x="' + x + '" y="' + (y + 12) + '" class="t2">' + l2 + '</text></g>');
    nodes.forEach(n => {
      const p = pos[n.serial];
      box(p[0], p[1], 130, 38, 'sw ' + n.state, n.name || n.serial, n.name ? n.role + ' ' + n.id + ' · ' + n.state : n.role + ' · ' + n.state, 'node:' + n.serial);
    });
    box(pos[st.apic.serial][0], pos[st.apic.serial][1], 120, 38, 'apic active', st.apic.name, 'APIC', 'apic');
    bottom.forEach(b => {
      if (b.kind === 'host') box(b.x, b.y, 100, 34, 'host ' + (b.o.status.learned ? 'up' : 'warn'), b.o.name, b.o.ip.split('/')[0], 'host:' + b.o.name);
      else if (b.kind === 'esxi') box(b.x, b.y, 100, 34, 'host esxi ' + (b.up ? 'up' : 'warn'), b.o.name, 'ESXi · ' + b.o.vms.length + ' VM', 'esxi:' + b.vc.name + '|' + b.o.name);
      else box(b.x, b.y, 100, 34, 'router ' + (b.o.status.link ? 'up' : 'warn'), b.o.name, (b.o.protocol || '') + ' ' + (b.o.status.adj || ''), 'router:' + b.o.name);
    });
    s.push('</svg>');
    const el = h('div', { class: 'topowrap', html: s.join('') });
    el.addEventListener('click', ev => {
      const g = ev.target.closest('g.nd');
      if (!g) return;
      const k = g.dataset.k;
      if (opts && opts.onClick) opts.onClick(k);
    });
    return el;
  },

  async topologyPage(w, withHosts) {
    const draw = () => {
      clear(w);
      const st = App.state;
      w.appendChild(paneHead(withHosts ? 'Simulation – Topologie & Hosts' : 'Topology', 'Pod 1 · grün = aktiv, orange = Discovery, grau = nicht registriert',
        withHosts ? [h('button', { class: 'btn primary small', onclick: () => Views.hostDialog() }, '+ Host'), h('button', { class: 'btn small', onclick: () => Views.routerDialog() }, '+ Externer Router')] : null));
      w.appendChild(h('div', { class: 'card' }, Views.topologySvg(st, {
        onClick: k => {
          if (k.startsWith('host:')) Views.hostDialog(st.hosts.find(x => x.name === k.slice(5)));
          else if (k.startsWith('esxi:')) App.go('sim', 'vcenter');
          else if (k.startsWith('router:')) Views.routerDialog(st.routers.find(x => x.name === k.slice(7)));
          else if (k.startsWith('node:')) {
            const n = st.nodes.find(x => x.serial === k.slice(5));
            if (n && n.id && n.state === 'active') App.go('fabric', 'inventory', 'node:' + n.id);
            else App.go('fabric', 'inventory', 'membership');
          } else if (k === 'apic') Term.open('apic1');
        },
      })));
      if (withHosts) {
        w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Simulierte Hosts (Bare-Metal-Server)', h('span', { class: 'grow' }), h('button', { class: 'btn primary small', onclick: () => Views.hostDialog() }, '+ Host')),
          table([{ l: 'Name', f: r => r.name }, { l: 'MAC', f: r => r.mac }, { l: 'IP', f: r => r.ip }, { l: 'Gateway', f: r => r.gw }, { l: 'VLAN', f: r => r.vlan ? 'vlan-' + r.vlan : 'untagged' },
            { l: 'Anschluss', f: r => r.links.map(l => nodeName(l[0]) + ' ' + l[1]).join(' + ') + (r.bond !== 'none' ? ' [' + r.bond + ']' : '') },
            { l: 'Status', f: r => r.status.learned ? h('span', null, stateBadge('learned'), ' ', parentDn(r.status.epg + '/x').replace(/^uni\//, '')) : r.status.quiet ? h('span', { title: 'Stiller Host: wird erst gelernt, wenn er antwortet oder selbst sendet' }, stateBadge('silent')) : stateBadge('down') },
            { l: 'Hinweis', f: r => (r.status.reasons || []).join('; ') }], st.hosts, {
            onRow: r => Views.hostDialog(r),
            actions: r => [iconBtn('🗑', 'Löschen', () => confirmBox('Host ' + r.name + ' entfernen?', async () => { await API.sim('hosts', { op: 'delete', name: r.name }); await App.refreshState(); draw(); }), 'danger')],
            empty: 'Noch keine Hosts. Ein Host simuliert einen Server an einem Leaf-Port – mit VLAN, MAC und IP.',
          })));
      }
    };
    draw();
    App.view = { auto: draw };
  },

  async 'sim/topo'(w) { return this.topologyPage(w, true); },

  hostDialog(x) {
    const st = App.state;
    const used = new Set();
    st.links.forEach(l => { used.add(l[0] + '|' + l[1]); used.add(l[2] + '|' + l[3]); });
    st.hosts.filter(o => !x || o.name !== x.name).forEach(o => o.links.forEach(l => used.add(l[0] + '|' + l[1])));
    st.routers.forEach(o => used.add(o.serial + '|' + o.port));
    (st.vcenters || []).forEach(vc => vc.hosts.forEach(o => o.links.forEach(l => used.add(l[0] + '|' + l[1]))));
    const leafOpts = leafNodes().map(n => [n.serial, (n.name || '(nicht registriert)') + (n.id ? ' – Node ' + n.id : '') + ' – ' + n.serial]);
    const linkRow = (i, val) => {
      const leaf = h('select', null, i > 0 ? h('option', { value: '' }, '— kein weiterer Link —') : null, leafOpts.map(([v, l]) => h('option', { value: v }, l)));
      const port = h('select');
      const fill = () => {
        const cur = port.value || (val ? val[1] : '');
        clear(port);
        const n = leafNodes().find(z => z.serial === leaf.value);
        if (!n) return;
        for (let p = 1; p <= n.ports; p++) {
          const pn = 'eth1/' + p;
          const u = used.has(n.serial + '|' + pn) && !(val && val[0] === n.serial && val[1] === pn);
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
    const f = buildForm([
      { k: 'name', l: 'Hostname', req: true, ph: 'web1' }, { k: 'mac', l: 'MAC-Adresse', req: true }, { k: 'ip', l: 'IP-Adresse/Maske', req: true, ph: '10.1.1.10/24' },
      { k: 'gw', l: 'Default Gateway', ph: '10.1.1.1' }, { k: 'vlan', l: 'VLAN-Tag', ph: '0 = untagged', help: '0 = Host sendet untagged (Access-Port), sonst 802.1Q-Tag' },
      { k: 'bond', l: 'NIC-Bonding', t: 'select', o: [['none', 'keins (ein Link aktiv)'], ['lacp-active', 'LACP active (802.3ad)'], ['lacp-passive', 'LACP passive'], ['static', 'statisch (mode on)']] },
      { k: 'silent', l: 'Stiller Host', t: 'yesno', cl: 'sendet nichts von sich aus (kein GARP, kein Traffic) – wird erst durch ARP Flooding oder ARP Glean entdeckt' },
      { k: 'descr', l: 'Beschreibung' }],
    x ? { name: x.name, mac: x.mac, ip: x.ip, gw: x.gw, vlan: String(x.vlan || 0), bond: x.bond, descr: x.descr, silent: x.silent ? 'yes' : 'no' } : { mac: randMac(), vlan: '0', bond: 'none', silent: 'no' }, {}, 'create');
    const body = h('div', null, f.el, h('div', { class: 'form' }, h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'Link 1'), h('div', { class: 'fctl' }, links[0].el)),
      h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'Link 2 (für PC/vPC)'), h('div', { class: 'fctl' }, links[1].el))));
    modal(x ? 'Host ' + x.name + ' bearbeiten' : 'Host hinzufügen', body, [{ l: 'Abbrechen' }, {
      l: 'Speichern', primary: true, fn: async () => {
        const v = f.get();
        const host = Object.assign(v, { vlan: Number(v.vlan || 0), links: links.map(l => l.get()).filter(Boolean), silent: v.silent === 'yes' });
        await API.sim('hosts', { host, old: x ? x.name : null });
        toast('Host ' + v.name + ' gespeichert');
        await App.refreshState();
        if (App.view && App.view.auto) App.view.auto();
      },
    }], { wide: true });
  },

  async 'sim/routers'(w) {
    const draw = () => {
      clear(w);
      const st = App.state;
      w.appendChild(paneHead('Simulation – Externe Router', 'Router außerhalb der Fabric für L3Outs (Static, OSPF, BGP, EIGRP) – mit zweitem Link für vPC, BFD und Ausfall-Simulation', [h('button', { class: 'btn primary small', onclick: () => Views.routerDialog() }, '+ Externer Router')]));
      w.appendChild(table([{ l: 'Name', f: r => r.name }, { l: 'Anschluss', f: r => nodeName(r.serial) + ' ' + r.port + (r.vlan ? ' vlan-' + r.vlan : ' (routed)') },
        { l: 'IP', f: r => r.ip }, { l: 'Protokoll', f: r => r.protocol + (r.protocol === 'ospf' ? ' area ' + r.ospf.area : r.protocol === 'bgp' ? ' AS ' + r.bgp.asn : '') }, { l: 'MTU', f: r => r.mtu },
        { l: 'Nachbarschaft', f: r => (r.status.adjs || []).length > 1 ? h('span', null, r.status.adjs.map(a => h('span', { style: { marginRight: '6px' } }, a.node + ' ', stateBadge(a.state))))
          : stateBadge(r.status.link ? r.status.adj : 'down') },
        { l: 'BFD', f: r => (r.status.bfd || []).map(b => b.node + ': ' + b.state).join(', ') || '—' }, { l: 'Kennt von ACI', f: r => (r.status.learned || []).join(', ') },
        { l: 'Hinweis', f: r => (r.status.reasons || []).join('; ') }], st.routers, {
        onRow: r => Views.routerDialog(r),
        actions: r => [iconBtn('🗑', 'Löschen', () => confirmBox('Router ' + r.name + ' entfernen?', async () => { await API.sim('routers', { op: 'delete', name: r.name }); await App.refreshState(); draw(); }), 'danger')],
        empty: 'Noch keine externen Router.',
      }));
      w.appendChild(h('div', { class: 'card note' }, md('Der Router verhält sich wie ein Gerät außerhalb der Fabric. Bei **OSPF** müssen Area, Area Type, Hello/Dead, MTU und Netzwerktyp passen, sonst bleibt die Nachbarschaft hängen (z. B. **EXSTART** bei MTU-Mismatch – die ACI nutzt standardmäßig MTU 9000). Bei **BGP** müssen Peer-Adresse und AS-Nummern stimmen und die Fabric braucht eine AS-Nummer (BGP Route Reflector Policy).')));
    };
    draw();
    App.view = { auto: draw };
  },

  routerDialog(x) {
    const st = App.state;
    const used = new Set();
    st.links.forEach(l => { used.add(l[0] + '|' + l[1]); used.add(l[2] + '|' + l[3]); });
    st.hosts.forEach(o => o.links.forEach(l => used.add(l[0] + '|' + l[1])));
    st.routers.filter(o => !x || o.name !== x.name).forEach(o => (o.links || [[o.serial, o.port]]).forEach(l => used.add(l[0] + '|' + l[1])));
    (st.vcenters || []).forEach(vc => vc.hosts.forEach(o => o.links.forEach(l => used.add(l[0] + '|' + l[1]))));
    (st.devices || []).forEach(d => d.links.forEach(l => used.add(l[0] + '|' + l[1])));
    const portOpts = [];
    leafNodes().forEach(n => { for (let p = 1; p <= n.ports; p++) { const pn = 'eth1/' + p; if (!used.has(n.serial + '|' + pn)) portOpts.push([n.serial + '|' + pn, (n.name || n.serial) + ' ' + pn]); } });
    const o = x || {};
    const f = buildForm([
      { k: 'name', l: 'Name', req: true, ph: 'wan-rtr1' },
      { k: 'att', l: 'Anschluss (Leaf/Port)', t: 'select', o: portOpts },
      { k: 'att2', l: 'Zweiter Link (für vPC/PC)', t: 'select', o: [['', '— keiner —']].concat(portOpts) },
      { k: 'bond', l: 'Bonding zum zweiten Link', t: 'select', o: [['none', 'keins'], ['lacp-active', 'LACP active'], ['lacp-passive', 'LACP passive'], ['static', 'statisch (mode on)']], show: v => !!v.att2 },
      { k: 'vlan', l: 'VLAN-Tag', ph: '0 = routed (ungetaggt)', help: '0 für Routed Interface, sonst VLAN für Sub-Interface oder SVI' },
      { k: 'ip', l: 'IP-Adresse/Maske', req: true, ph: '172.16.1.2/30' }, { k: 'mtu', l: 'MTU', ph: '1500' }, { k: 'routerId', l: 'Router ID', ph: '172.16.255.1' },
      { k: 'protocol', l: 'Routing-Protokoll', t: 'radio', o: [['static', 'Static'], ['ospf', 'OSPF'], ['bgp', 'BGP'], ['eigrp', 'EIGRP']] },
      { k: 'easn', l: 'EIGRP AS', ph: '100', show: v => v.protocol === 'eigrp' },
      { k: 'bfd', l: 'BFD aktiv', t: 'yesno' },
      { k: 'area', l: 'OSPF Area', ph: '0.0.0.0', show: v => v.protocol === 'ospf' },
      { k: 'areaType', l: 'OSPF Area Type', t: 'select', o: [['regular', 'regular'], ['nssa', 'nssa'], ['stub', 'stub']], show: v => v.protocol === 'ospf' },
      { k: 'nwT', l: 'OSPF Netzwerktyp', t: 'select', o: [['bcast', 'broadcast'], ['p2p', 'point-to-point']], show: v => v.protocol === 'ospf' },
      { k: 'hello', l: 'Hello / Dead', ph: '10', show: v => v.protocol === 'ospf' }, { k: 'dead', l: 'Dead Interval', ph: '40', show: v => v.protocol === 'ospf' },
      { k: 'mtuIgnore', l: 'ip ospf mtu-ignore', t: 'yesno', show: v => v.protocol === 'ospf' },
      { k: 'asn', l: 'Eigene AS-Nummer', ph: '65100', show: v => v.protocol === 'bgp' }, { k: 'peerAs', l: 'Remote-AS (ACI)', ph: '65001', show: v => v.protocol === 'bgp' },
      { k: 'bpwd', l: 'BGP-Passwort (MD5)', show: v => v.protocol === 'bgp' },
      { k: 'bhold', l: 'BGP Hold / Keepalive', ph: '180', show: v => v.protocol === 'bgp' }, { k: 'bka', l: 'BGP Keepalive', ph: '60', show: v => v.protocol === 'bgp' },
      { k: 'bsrc', l: 'Update-Source (Loopback des Routers)', ph: 'leer = Interface-IP', show: v => v.protocol === 'bgp', help: 'Für eBGP über Loopbacks: Router-Loopback, die in der ACI als BGP Peer im Node Profile steht' },
      { k: 'bpeer', l: 'Neighbor (ACI-Adresse)', ph: 'leer = Interface-IP der ACI', show: v => v.protocol === 'bgp' },
      { k: 'down', l: 'Router ausgeschaltet', t: 'yesno', help: 'Simuliert einen Ausfall (z. B. für IP SLA / Track)' },
      { k: 'networks', l: 'Netze hinter dem Router', ph: '8.8.8.0/24, 1.1.1.0/24', help: 'Ziele, die der Router erreicht (für den Traffic-Test)' },
      { k: 'advertise', l: 'Kündigt der ACI an (OSPF/BGP)', ph: '0.0.0.0/0' },
      { k: 'staticBack', l: 'Statische Routen zurück in die ACI', ph: '10.1.0.0/16', help: 'nur nötig bei Static-L3Out ohne Routing-Protokoll' },
    ], {
      name: o.name, att: o.serial ? o.serial + '|' + o.port : '', vlan: String(o.vlan || 0), ip: o.ip, mtu: String(o.mtu || 1500), routerId: o.routerId, protocol: o.protocol || 'ospf',
      area: (o.ospf || {}).area || '0.0.0.0', areaType: (o.ospf || {}).areaType || 'regular', nwT: (o.ospf || {}).nwT || 'bcast', hello: String((o.ospf || {}).hello || 10), dead: String((o.ospf || {}).dead || 40),
      mtuIgnore: (o.ospf || {}).mtuIgnore ? 'yes' : 'no', asn: (o.bgp || {}).asn || '65100', peerAs: (o.bgp || {}).peerAs || '65001',
      att2: (o.links && o.links[1]) ? o.links[1][0] + '|' + o.links[1][1] : '', bond: o.bond || 'none', easn: (o.eigrp || {}).asn || '100', bfd: o.bfd ? 'yes' : 'no',
      bpwd: (o.bgp || {}).password || '', bhold: String((o.bgp || {}).hold || 180), bka: String((o.bgp || {}).keepalive || 60), bsrc: (o.bgp || {}).updateSource || '',
      bpeer: (o.bgp || {}).peerAddr || '', down: o.down ? 'yes' : 'no',
      networks: (o.networks || ['8.8.8.0/24']).join(', '), advertise: (o.advertise || ['0.0.0.0/0']).join(', '), staticBack: (o.staticBack || []).join(', '),
    }, {}, 'create');
    const list = s => String(s || '').split(',').map(z => z.trim()).filter(Boolean);
    modal(x ? 'Router ' + x.name + ' bearbeiten' : 'Externer Router', f.el, [{ l: 'Abbrechen' }, {
      l: 'Speichern', primary: true, fn: async () => {
        const v = f.get();
        const [serial, port] = (v.att || '|').split('|');
        const links = [[serial, port]].concat(v.att2 ? [v.att2.split('|')] : []);
        const r = { name: v.name, serial, port, links, bond: v.att2 ? v.bond : 'none', vlan: Number(v.vlan || 0), ip: v.ip, mtu: Number(v.mtu || 1500), routerId: v.routerId, protocol: v.protocol,
          ospf: { area: v.area, areaType: v.areaType, nwT: v.nwT, hello: Number(v.hello || 10), dead: Number(v.dead || 40), mtuIgnore: v.mtuIgnore === 'yes' },
          eigrp: { asn: v.easn || '100' }, bfd: v.bfd === 'yes', down: v.down === 'yes',
          bgp: { asn: v.asn, peerAs: v.peerAs, password: v.bpwd, hold: Number(v.bhold || 180), keepalive: Number(v.bka || 60), updateSource: v.bsrc, peerAddr: v.bpeer },
          networks: list(v.networks), advertise: list(v.advertise), staticBack: list(v.staticBack) };
        await API.sim('routers', { router: r, old: x ? x.name : null });
        toast('Router ' + v.name + ' gespeichert');
        await App.refreshState();
        if (App.view && App.view.auto) App.view.auto();
      },
    }], { wide: true });
  },

  async 'sim/labs'(w) {
    const labs = await API.sim('labs');
    let saves = await API.sim('saves');
    const autoNote = () => App.state.lab ? ' Dein Stand im aktuellen Lab „' + App.state.lab.title + '" wird vorher automatisch gesichert.' : '';
    const draw = async () => {
      clear(w);
      const cur = App.state.lab;
      w.appendChild(paneHead('Labs', 'Geführte Übungen mit automatischer Prüfung'));
      if (cur) {
        const res = h('div');
        const check = async () => {
          const r = await API.sim('labs/check');
          clear(res).appendChild(h('div', { class: 'card trace ' + (r.passed === r.total ? 'ok' : 'bad') },
            h('div', { class: 'trace-sum' }, r.passed === r.total ? '✔ Alle Prüfungen bestanden!' : r.passed + ' von ' + r.total + ' Prüfungen bestanden'),
            h('ol', null, r.checks.map(c => h('li', { class: c.ok ? 'ok' : 'bad' }, h('b', null, c.desc), c.info ? h('div', { class: 'muted' }, c.info) : null)))));
        };
        const sol = h('div', { style: { display: 'none' } }, md(cur.solution || 'Keine Musterlösung hinterlegt.'));
        w.appendChild(h('div', { class: 'card lab' }, h('div', { class: 'card-h' }, 'Aktuelles Lab: ' + cur.title),
          md(cur.intro || ''),
          cur.goals && cur.goals.length ? h('div', null, h('h4', null, 'Lernziele'), h('ul', null, cur.goals.map(g => h('li', null, g)))) : null,
          h('h4', null, 'Aufgaben'),
          h('ol', { class: 'tasks' }, (cur.tasks || []).map(t => h('li', null, h('b', null, t.title), md(t.text), t.hint ? h('details', null, h('summary', null, 'Tipp'), md(t.hint)) : null))),
          h('div', { class: 'formbtns' }, h('button', { class: 'btn', onclick: () => Saves.saveDialog() }, '💾 Stand speichern'),
            h('button', { class: 'btn', onclick: () => { sol.style.display = sol.style.display ? '' : 'none'; } }, 'Lösung zeigen/verbergen'),
            h('button', { class: 'btn primary', onclick: check }, '✔ Lab prüfen')), sol, res));
      }
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Alle Labs'),
        table([{ l: 'Lab', f: l => h('b', null, l.title) }, { l: 'Thema', f: l => l.topic }, { l: 'Niveau', f: l => l.level }, { l: 'Dauer', f: l => l.duration }], labs, {
          actions: l => [
            saves.some(x => x.lab === l.id) ? h('button', {
              class: 'btn small', title: 'Letzten Spielstand dieses Labs laden', onclick: () => {
                const last = saves.filter(x => x.lab === l.id)[0];
                confirmBox('Lab „' + l.title + '" fortsetzen? Geladen wird „' + last.name + '" vom ' + fmtTs(last.created) +
                  (last.progress ? ' (' + last.progress[0] + ' von ' + last.progress[1] + ' Prüfungen)' : '') + '.' + autoNote(), () => Saves.load(last.name));
              },
            }, '▶ Fortsetzen') : null,
            h('button', {
              class: 'btn primary small', onclick: () => confirmBox('Lab „' + l.title + '" neu starten? Die Fabric wird auf den Startzustand des Labs gesetzt.' + autoNote(), async () => {
                await API.sim('labs/load', { id: l.id });
                if (l.fabric === 'factory') return location.reload();
                toast('Lab geladen');
                await App.refreshState();
                saves = await API.sim('saves');
                draw();
              }),
            }, saves.some(x => x.lab === l.id) ? 'Neu starten' : 'Laden')],
        })));
    };
    await draw();
  },

  async 'sim/simset'(w) {
    const st = App.state;
    const inp = h('input', { value: st.settings.discoverySeconds, style: { width: '80px' } });
    w.appendChild(paneHead('Simulation – Einstellungen', ''));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Fabric Discovery'),
      h('div', { class: 'form' }, h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'Sekunden pro Discovery-Schritt'), h('div', { class: 'fctl' }, inp, h('div', { class: 'help' }, 'Ein echter Switch braucht mehrere Minuten, bis er nach der Registrierung aktiv ist. 0 = sofort.')))),
      h('div', { class: 'formbtns' }, h('button', { class: 'btn primary', onclick: async () => { await API.sim('settings', { discoverySeconds: Number(inp.value) }); toast('Gespeichert'); App.refreshState(); } }, 'Speichern'))));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Zurücksetzen'),
      h('p', null, 'Setzt die gesamte Konfiguration zurück. Hosts und Router werden entfernt.'),
      h('div', { class: 'formbtns' },
        h('button', { class: 'btn', onclick: () => confirmBox('Alles löschen und mit einer FERTIG registrierten Fabric starten?', async () => { await API.sim('reset', { mode: 'discovered' }); toast('Zurückgesetzt'); await App.refreshState(); App.go('system', 'dash'); }) }, 'Reset: Fabric registriert'),
        h('button', { class: 'btn danger', onclick: () => confirmBox('APIC in den Werkszustand setzen? Alles wird gelöscht, danach startet der Setup-Dialog an der Konsole (Day 0).', async () => { await API.sim('reset', { mode: 'factory' }); location.reload(); }) }, 'Reset: Werkszustand (Day 0)'),
        h('button', { class: 'btn danger', onclick: () => confirmBox('Alles löschen und mit einer LEEREN Fabric starten (Switches müssen registriert werden)?', async () => { await API.sim('reset', { mode: 'empty' }); toast('Zurückgesetzt'); await App.refreshState(); App.go('fabric', 'inventory', 'membership'); }) }, 'Reset: Fabric leer'))));
    w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Verkabelung'), md('Die physische Topologie ist fest: **spine201/202** an Port 1–4 zu den Leafs (Leaf eth1/49 → spine201, eth1/50 → spine202), der **APIC** an leaf101 und leaf102 jeweils eth1/48. Hosts und Router kannst du an alle freien Leaf-Ports anschließen.'),
      table([{ l: 'A', f: l => nodeName(l[0]) }, { l: 'Port', f: l => l[1] }, { l: 'B', f: l => nodeName(l[2]) }, { l: 'Port', f: l => l[3] }], st.links.map(l => l.map(x => x === st.apic.serial ? 'apic1' : x)))));
  },
};

function avg(a) { return a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0; }
