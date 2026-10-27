/* Betriebsthemen: Firmware, Import/Export, Monitoring und die zugehoerigen Simulationsseiten */
'use strict';

/* Laufende Ansicht alle 2 s neu zeichnen, solange sie sichtbar ist */
function live(w, draw, ms) {
  const t = setInterval(() => { if (!w.isConnected) return clearInterval(t); if (!document.querySelector('.modal-back')) draw(); }, ms || 2000);
}

Object.assign(Views, {
  dlStatus(r) {
    const d = (App.state.downloads || {})[r.dn + '|' + r.url];
    if (!d) return stateBadge('pending');
    return h('span', { title: d.status }, stateBadge(d.ok ? 'downloaded' : 'failed'), ' ', d.ok ? '' : d.status.replace(/^failed: /, ''));
  },

  lastJob(dn) {
    const j = (App.state.jobs || []).filter(x => x.policy === dn).pop();
    if (!j) return '—';
    return h('span', { title: j.details }, stateBadge(j.ok ? 'success' : 'failed'), ' ', fmtTs(j.ts));
  },

  async fwOverview(w0) {
    const w = w0.appendChild(h('div'));
    const draw = async () => {
      const f = await API.sim('firmware');
      clear(w);
      w.appendChild(paneHead('Firmware – Übersicht', 'Laufende Versionen, Upgrade Groups und Fortschritt', [iconBtn('⟳', 'Refresh', draw)]));
      w.appendChild(h('div', { class: 'card note' }, md('**Reihenfolge wie im echten Betrieb:** 1. Images ins Repository laden (*Images* bzw. *Download Tasks*), 2. **APIC zuerst** aktualisieren (*Controllers*), 3. Switches in **Upgrade Groups** – z. B. *gerade* (102, 104, 202) und *ungerade* (101, 103, 201) Node-IDs. So lädt nie ein vPC-Paar oder beide Spines gleichzeitig neu.')));
      w.appendChild(table([{ l: 'Node', f: r => r.name }, { l: 'ID', f: r => r.id }, { l: 'Role', f: r => r.role }, { l: 'Current Firmware', f: r => r.version },
        { l: 'Status', f: r => stateBadge(r.state === 'upgrading' ? 'reload' : r.state) }], f.nodes));
      const run = f.upgrades.filter(u => !u.done);
      if (run.length) {
        w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Laufende Upgrades'),
          table([{ l: 'Gruppe', f: r => r.grp }, { l: 'Ziel', f: r => r.version }, { l: 'Fortschritt', f: r => pct(r.pct, 100) }, { l: 'Rest', f: r => r.left + ' s' },
            { l: 'Warnung', f: r => (r.warn || []).join('; ') }], run)));
      }
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Upgrade Groups'),
        table([{ l: 'Gruppe', f: r => r.name }, { l: 'Nodes', f: r => r.nodes.join(', ') || '—' }, { l: 'Upgrade Policy', f: r => r.pol ? nameOfDn(r.pol) : '— (keine)' },
          { l: 'Hinweis', f: r => r.warn.length ? h('span', { class: 'bad' }, r.warn.join('; ')) : 'ok' }], f.groups, { empty: 'Noch keine Upgrade Groups (Infrastructure > Nodes).' })));
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Protokoll'),
        table([{ l: 'Zeit', f: r => fmtTs(r.ts) }, { l: 'Policy', f: r => nameOfDn(r.policy) }, { l: 'Ergebnis', f: r => stateBadge(r.ok ? 'ok' : 'failed') }, { l: 'Meldung', f: r => r.text }], f.log, { empty: '—' })));
    };
    await draw();
    live(w, draw, 2500);
  },

  async fwImages(w) {
    const f = await API.sim('firmware');
    w.appendChild(paneHead('Firmware – Images', 'Firmware Repository des APIC', [h('button', { class: 'btn primary small', onclick: () => createDialog('uni/fabric/fwrepop', 'firmwareOSource') }, '+ Add Firmware to APIC')]));
    w.appendChild(table([{ l: 'Name', f: r => r.name }, { l: 'Type', f: r => r.type }, { l: 'Version', f: r => r.version }, { l: 'Size', f: r => r.size }, { l: 'Download', f: r => fmtTs(r.date) }],
      f.repo, { empty: 'Das Repository ist leer. Mit „Add Firmware to APIC" lädt der APIC ein Image per SCP oder HTTP vom Fileserver (Simulation > Fileserver & Monitoring).' }));
  },

  async configJobs(w) {
    const rows = await API.sim('jobs');
    w.appendChild(paneHead('Import/Export – Jobs', 'Ergebnis jedes Exports und Imports (neueste zuerst)', [iconBtn('⟳', 'Refresh', () => App.reload())]));
    w.appendChild(table([{ l: 'Zeit', f: r => fmtTs(r.ts) }, { l: 'Typ', f: r => r.kind }, { l: 'Policy', f: r => nameOfDn(r.policy) }, { l: 'Status', f: r => stateBadge(r.ok ? 'success' : 'failed') },
      { l: 'Datei', f: r => r.file || '—' }, { l: 'Details', f: r => r.details }], rows, { empty: 'Noch keine Jobs. Eine Export Policy mit „Start Now: Triggered" startet sofort.' }));
  },

  async jsonImpExp(w) {
    await Views['admin/impexpJson'](w);
  },

  async monStatus(w) {
    const draw = async () => {
      const m = await API.sim('monitors');
      clear(w);
      w.appendChild(paneHead('Monitoring – Zustellung', 'Welche Ziele der APIC erreicht (Sources in Fabric > Fabric Policies > Policies > Monitoring > Common Policy)', [iconBtn('⟳', 'Refresh', draw)]));
      w.appendChild(table([{ l: 'Art', f: r => r.kind }, { l: 'Source', f: r => nameOfDn(r.src) }, { l: 'Min Severity', f: r => r.minSev }, { l: 'Ziel', f: r => r.host || '—' },
        { l: 'Collector', f: r => r.collector || '—' }, { l: 'Zustand', f: r => stateBadge(r.ok ? 'ok' : 'failed') }, { l: 'Grund', f: r => r.why || '' }], m.dests,
      { empty: 'Keine Monitoring Sources. Ohne Source in der Common Policy sendet der APIC nichts – auch wenn die Destination Group existiert.' }));
      w.appendChild(h('div', { class: 'card note' }, md('Gesendet wird nur, was **nach** der Konfiguration passiert: neue Faults (raised/cleared), Events und Audit-Einträge. Faults eines Switches schickt der Switch selbst – er braucht dafür eine Management-Adresse. Empfangene Meldungen siehst du unter **Simulation > Fileserver & Monitoring**.')));
    };
    await draw();
  },

  /* ================================================================ Simulation: Fileserver & Monitoring */
  async 'sim/servers'(w0) {
    const w = w0.appendChild(h('div'));
    const draw = async () => {
      const fs = await API.sim('fileserver');
      const m = await API.sim('monitors');
      clear(w);
      w.appendChild(paneHead('Simulation – Fileserver & Monitoring', 'Server im Management-Netz: SCP/SFTP/FTP/HTTP-Fileserver, Syslog-Server, SNMP-Manager, Mailserver',
        [h('button', { class: 'btn primary small', onclick: () => Views.monitorDialog(null, draw) }, '+ Collector')]));
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Fileserver ' + fs.ip, h('span', { class: 'grow' }),
        h('button', { class: 'btn small', onclick: () => Views.fileserverDialog(fs, draw) }, 'Bearbeiten')),
      h('div', { class: 'info' }, [['IP', fs.ip], ['Protokolle', fs.protocols.join(', ').toUpperCase()], ['Benutzer', fs.user], ['Passwort', fs.pwd], ['Verzeichnisse', fs.dirs.join(', ')], ['Zustand', fs.down ? 'ausgefallen' : 'läuft']]
        .map(([k, v]) => h('div', null, h('span', null, k), h('b', null, v)))),
      table([{ l: 'Datei', f: r => r.path }, { l: 'Größe', f: r => r.size }, { l: 'Art', f: r => r.image ? 'Firmware-Image' : r.export ? 'Config Export' + (r.target ? ' (' + r.target + ')' : '') : '' },
        { l: 'Inhalt', f: r => r.export ? r.objects + ' Objekte' + (r.secure ? ', mit Secure Properties (AES)' : ', ohne Passwörter') : '' }], fs.files, {
        actions: r => r.export ? [iconBtn('🗑', 'Löschen', () => confirmBox('Datei ' + r.path + ' löschen?', async () => { await API.sim('fileserver', { op: 'delete', path: r.path }); draw(); }), 'danger')] : [],
      })));
      m.monitors.forEach(c => {
        const log = (m.log[c.name] || []).slice().reverse();
        const card = h('div', { class: 'card' }, h('div', { class: 'card-h' }, h('b', null, c.name), ' · ', c.type.toUpperCase(), ' · ', c.ip + ':' + c.port,
          c.community ? ' · Community ' + c.community : '', c.down ? h('span', { class: 'bad' }, ' · ausgefallen') : '', h('span', { class: 'grow' }),
          c.type === 'snmp' ? h('button', { class: 'btn small', onclick: () => Views.snmpWalkDialog(c) }, 'snmpwalk …') : null,
          h('button', { class: 'btn small', onclick: () => Views.monitorDialog(c, draw) }, 'Bearbeiten'),
          h('button', { class: 'btn small', onclick: async () => { await API.sim('monitors', { op: 'clear', name: c.name }); draw(); } }, 'Leeren'),
          iconBtn('🗑', 'Löschen', () => confirmBox('Collector ' + c.name + ' entfernen?', async () => { await API.sim('monitors', { op: 'delete', name: c.name }); draw(); }), 'danger')),
        h('pre', { class: 'json termbox' }, log.length ? log.slice(0, 60).map(x => (x.dropped ? '✗ ' : '') + x.text).join('\n') : '(noch nichts empfangen)'));
        w.appendChild(card);
      });
      w.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Testmeldung'),
        h('p', null, 'Löst auf dem APIC einen Test-Fault (F9999) aus. Er geht an alle konfigurierten Syslog-, SNMP- und Callhome-Ziele, deren Filter passen.'),
        h('div', { class: 'formbtns' }, ['critical', 'major', 'minor', 'warning'].map(s => h('button', { class: 'btn small', onclick: async () => { await API.sim('monitors', { op: 'test', severity: s }); toast('Test-Fault ' + s + ' gesendet'); draw(); } }, s)))));
    };
    await draw();
    live(w, draw, 4000);
  },

  fileserverDialog(fs, after) {
    const f = buildForm([{ k: 'ip', l: 'IP-Adresse', req: true }, { k: 'user', l: 'Benutzer' }, { k: 'pwd', l: 'Passwort' }, { k: 'dirs', l: 'Verzeichnisse', help: 'Kommagetrennt, z. B. /backup, /images' },
      { k: 'down', l: 'Server ausgefallen', t: 'yesno' }], { ip: fs.ip, user: fs.user, pwd: fs.pwd, dirs: fs.dirs.join(', '), down: fs.down ? 'yes' : 'no' }, {}, 'create');
    modal('Fileserver', f.el, [{ l: 'Abbrechen' }, { l: 'Images wiederherstellen', fn: async () => { await API.sim('fileserver', { op: 'reset' }); after(); } },
      { l: 'Speichern', primary: true, fn: async () => { const v = f.get(); await API.sim('fileserver', { op: 'set', server: Object.assign(v, { down: v.down === 'yes' }) }); toast('Gespeichert'); after(); } }]);
  },

  monitorDialog(x, after) {
    const f = buildForm([{ k: 'name', l: 'Name', req: true }, { k: 'type', l: 'Typ', t: 'radio', o: [['syslog', 'Syslog-Server'], ['snmp', 'SNMP-Manager (Polling + Traps)'], ['smtp', 'Mailserver']] },
      { k: 'ip', l: 'IP-Adresse', req: true, ph: '192.168.10.60' }, { k: 'port', l: 'Port', ph: '514 / 162 / 25' }, { k: 'community', l: 'Community (SNMP)', help: 'Traps mit anderer Community verwirft der Manager' },
      { k: 'down', l: 'ausgefallen', t: 'yesno' }],
    x ? Object.assign({}, x, { port: String(x.port), down: x.down ? 'yes' : 'no' }) : { type: 'syslog', down: 'no' }, {}, 'create');
    modal(x ? 'Collector ' + x.name : 'Collector hinzufügen', f.el, [{ l: 'Abbrechen' }, { l: 'Speichern', primary: true, fn: async () => {
      const v = f.get();
      await API.sim('monitors', { op: 'set', old: x ? x.name : null, monitor: Object.assign(v, { down: v.down === 'yes' }) });
      toast('Gespeichert');
      after();
    } }]);
  },

  snmpWalkDialog(c) {
    const nodes = [['apic1', 'apic1 (Controller)']].concat((App.state.nodes || []).filter(n => n.state === 'active').map(n => [n.name, n.name + ' (' + n.id + ')']));
    const f = buildForm([{ k: 'node', l: 'Ziel', t: 'select', o: nodes }, { k: 'community', l: 'Community', req: true }], { node: 'apic1', community: c.community || 'public' }, {}, 'create');
    const out = h('pre', { class: 'json termbox' }, '');
    modal('snmpwalk von ' + c.name + ' (' + c.ip + ')', h('div', null, f.el, out), [{ l: 'Schließen' }, { l: 'Abfragen', primary: true, keep: true, fn: async () => {
      const v = f.get();
      const r = await API.sim('monitors', { op: 'walk', name: c.name, node: v.node, community: v.community });
      out.textContent = r.output + (r.why ? '\n\n[Simulator-Hinweis] ' + r.why : '');
      return false;
    } }], { wide: true });
  },

  /* ================================================================ Simulation: Legacy-Switches */
  async 'sim/legacy'(w) {
    const draw = () => {
      clear(w);
      const st = App.state;
      w.appendChild(paneHead('Simulation – Legacy-Switches', 'Klassische Switches (z. B. Catalyst ohne Spanning Tree zur Fabric) an Leaf-Ports – zum Testen von Schleifen, MCP und Endpoint Loop Protection',
        [h('button', { class: 'btn primary small', onclick: () => Views.legacyDialog(null, draw) }, '+ Legacy-Switch')]));
      w.appendChild(h('div', { class: 'card note' }, md('Ein Legacy-Switch verbindet alle seine Ports auf Layer 2 (Trunk, alle oder die angegebenen VLANs). Hängt er mit **zwei Links ohne Port-Channel** an der Fabric und ist auf beiden Ports dieselbe VLAN-Encap (oder untagged) deployed, entsteht eine **Schleife**: Broadcast-Storm, Endpoint-Flapping. Die ACI selbst nimmt nicht an Spanning Tree teil – dagegen helfen **MCP** (*Access Policies > Policies > Global > MCP Instance Policy default*, mit Key und ggf. *PDU per VLAN*) und **Endpoint Loop Protection** (*System Settings > Endpoint Controls*).')));
      w.appendChild(table([{ l: 'Name', f: r => r.name }, { l: 'Anschluss', f: r => r.links.map(l => nodeName(l[0]) + ' ' + l[1]).join(' + ') + (r.bond !== 'none' ? ' [LACP]' : '') },
        { l: 'VLANs', f: r => r.vlans || 'alle' }, { l: 'Schleife', f: r => r.status.loop ? stateBadge(r.status.action ? 'broken' : 'loop') : stateBadge('ok') },
        { l: 'Zustand', f: r => r.status.text || '' }], st.switches || [], {
        onRow: r => Views.legacyDialog(r, draw),
        actions: r => [iconBtn('🗑', 'Löschen', () => confirmBox('Switch ' + r.name + ' entfernen?', async () => { await API.sim('switches', { op: 'delete', name: r.name }); await App.refreshState(); draw(); }), 'danger')],
        empty: 'Noch keine Legacy-Switches.',
      }));
    };
    draw();
    App.view = { auto: draw };
  },

  legacyDialog(x, after) {
    const st = App.state;
    const leafOpts = [['', '— kein Link —']].concat(leafNodes().map(n => [n.serial, (n.name || n.serial) + (n.id ? ' – Node ' + n.id : '')]));
    const lk = (x && x.links) || [];
    const f = buildForm([{ k: 'name', l: 'Name', req: true, ph: 'cat-old' }, { k: 'vlans', l: 'VLANs', ph: 'leer = alle, z. B. 10,20' },
      { k: 'bond', l: 'Uplinks', t: 'radio', o: [['none', 'einzelne Links (kein Port-Channel)'], ['lacp', 'LACP Port-Channel']] },
      { k: 'l1', l: 'Link 1 Leaf', t: 'select', o: leafOpts, req: true }, { k: 'p1', l: 'Link 1 Port', ph: 'eth1/30', req: true },
      { k: 'l2', l: 'Link 2 Leaf', t: 'select', o: leafOpts }, { k: 'p2', l: 'Link 2 Port', ph: 'eth1/30' }, { k: 'descr', l: 'Beschreibung' }],
    x ? { name: x.name, vlans: x.vlans, bond: x.bond, l1: (lk[0] || [])[0], p1: (lk[0] || [])[1], l2: (lk[1] || [])[0] || '', p2: (lk[1] || [])[1] || '', descr: x.descr } : { bond: 'none', l1: (leafNodes()[0] || {}).serial, p1: 'eth1/30', l2: (leafNodes()[1] || {}).serial, p2: 'eth1/30' }, {}, 'create');
    modal(x ? 'Legacy-Switch ' + x.name : 'Legacy-Switch hinzufügen', f.el, [{ l: 'Abbrechen' }, { l: 'Speichern', primary: true, fn: async () => {
      const v = f.get();
      const links = [[v.l1, v.p1], [v.l2, v.p2]].filter(l => l[0] && l[1]);
      await API.sim('switches', { op: 'set', old: x ? x.name : null, switch: { name: v.name, vlans: v.vlans, bond: v.bond, links, descr: v.descr } });
      toast('Gespeichert');
      await App.refreshState();
      after();
    } }]);
  },
});

/* Die bisherige JSON-Seite bleibt unter Import/Export erreichbar */
Views['admin/impexpJson'] = Views['admin/impexp'];
delete Views['admin/impexp'];
