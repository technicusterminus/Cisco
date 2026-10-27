/* APIC-Oberfläche: Shell, Navigation, Baum, generische Objektansichten */
'use strict';

const TABS = [
  { id: 'system', l: 'System', subs: [['dash', 'Dashboard'], ['faults', 'Faults'], ['settings', 'System Settings']] },
  { id: 'tenants', l: 'Tenants' },
  { id: 'fabric', l: 'Fabric', subs: [['inventory', 'Inventory'], ['fabricpol', 'Fabric Policies'], ['access', 'Access Policies']] },
  { id: 'vnet', l: 'Virtual Networking', subs: [['vmm', 'Inventory']] },
  { id: 'admin', l: 'Admin', subs: [['aaa', 'AAA'], ['rollback', 'Config Rollbacks'], ['impexp', 'Import/Export']] },
  { id: 'ops', l: 'Operations', subs: [['vis', 'Visibility & Troubleshooting'], ['ep', 'EP Tracker']] },
  { id: 'apps', l: 'Apps', subs: [['apps', 'Installed Apps']] },
  { id: 'sim', l: 'Simulation', subs: [['topo', 'Topologie & Hosts'], ['routers', 'Externe Router'], ['labs', 'Labs'], ['simset', 'Einstellungen']], special: true },
];

const App = {
  tab: 'system', sub: 'dash', sel: null, expanded: new Set(), state: null, tenants: [], view: null, auto: null,

  async init() {
    MIT.meta = await (await fetch('/sim/meta')).json();
    API.onAuthLost = () => this.showLogin('Sitzung abgelaufen – bitte erneut anmelden.');
    Inspector.init();
    try {
      const r = await API.post('/api/aaaRefresh.json', undefined, true);
      this.user = r.imdata[0].aaaLogin.attributes.userName;
      this.start();
    } catch (e) { this.showLogin(); }
  },

  showLogin(msg) {
    clearInterval(this.timer);
    const user = h('input', { value: 'admin', autocomplete: 'username' });
    const pwd = h('input', { type: 'password', autocomplete: 'current-password' });
    const err = h('div', { class: 'login-err' }, msg || '');
    const go = async () => {
      err.textContent = '';
      try {
        const r = await API.post('/api/aaaLogin.json', { aaaUser: { attributes: { name: user.value, pwd: pwd.value } } });
        this.user = r.imdata[0].aaaLogin.attributes.userName;
        this.start();
      } catch (e) { err.textContent = e.text || e.message; }
    };
    pwd.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
    user.addEventListener('keydown', e => { if (e.key === 'Enter') pwd.focus(); });
    const root = clear(document.getElementById('app'));
    root.appendChild(h('div', { class: 'login' },
      h('div', { class: 'login-box' },
        h('div', { class: 'login-brand' }, h('div', { class: 'logo-mark' }, 'APIC'), h('div', null, h('b', null, 'Application Policy Infrastructure Controller'), h('div', { class: 'muted' }, 'ACI Simulator · Version 6.0(5h)-sim'))),
        h('label', null, 'User ID'), user, h('label', null, 'Password'), pwd, err,
        h('button', { class: 'btn primary block', onclick: go }, 'Login'),
        h('p', { class: 'muted small' }, 'Standard-Login: admin / admin (beim Start mit --password änderbar). Kein offizielles Cisco-Produkt.'))));
    setTimeout(() => (user.value ? pwd : user).focus(), 50);
  },

  async start() {
    const root = clear(document.getElementById('app'));
    this.el = {
      tabs: h('nav', { class: 'tabs' }), subs: h('div', { class: 'subtabs' }), main: h('div', { class: 'main' }),
      badges: h('div', { class: 'badges' }),
    };
    const header = h('header', { class: 'top' },
      h('div', { class: 'brand', onclick: () => this.go('system', 'dash') }, h('span', { class: 'logo-mark small' }, 'APIC'), h('span', { class: 'brand-sub' }, 'ACI Simulator')),
      this.el.tabs,
      h('div', { class: 'tools' }, this.el.badges,
        h('button', { class: 'tbtn', title: 'Leaf-/APIC-CLI', onclick: () => Term.open() }, '⌨ CLI'),
        h('button', { class: 'tbtn', title: 'API Inspector', onclick: () => Inspector.toggle() }, '{ } API Inspector'),
        h('a', { class: 'tbtn', href: '/visore.html', target: '_blank', title: 'Object Store Browser' }, 'Visore'),
        h('button', { class: 'tbtn', onclick: () => this.logout(), title: 'Abmelden' }, '⏻ ' + this.user)));
    root.appendChild(header);
    root.appendChild(this.el.subs);
    root.appendChild(this.el.main);
    TABS.forEach(t => this.el.tabs.appendChild(h('a', { class: 'tab' + (t.special ? ' special' : ''), 'data-id': t.id, onclick: () => this.go(t.id) }, t.l)));
    await this.refreshState();
    const hs = location.hash.slice(1).split('|');
    if (hs[0] && TABS.find(t => t.id === hs[0])) this.go(hs[0], hs[1] || null, hs[2] ? decodeURIComponent(hs[2]) : null);
    else this.go('system', 'dash');
    clearInterval(this.timer);
    this.timer = setInterval(() => this.poll(), 3000);
  },

  async logout() {
    try { await API.post('/api/aaaLogout.json', {}); } catch (e) { /* egal */ }
    this.showLogin();
  },

  async refreshState() {
    try { this.state = await API.sim('state'); } catch (e) { return; }
    const f = this.state.faults || {};
    clear(this.el.badges);
    ['critical', 'major', 'minor', 'warning'].forEach(s => this.el.badges.appendChild(
      h('span', { class: 'fbadge ' + s, title: s + ' faults', onclick: () => this.go('system', 'faults') }, String(f[s] || 0))));
  },

  async poll() {
    if (document.hidden) return;
    const before = this.state && JSON.stringify([this.state.nodes, this.state.pending, this.state.faults, this.state.hosts.map(x => x.status), this.state.routers.map(x => x.status)]);
    await this.refreshState();
    const after = this.state && JSON.stringify([this.state.nodes, this.state.pending, this.state.faults, this.state.hosts.map(x => x.status), this.state.routers.map(x => x.status)]);
    if (before !== after && this.view && this.view.auto) this.view.auto();
  },

  /* ------------------------------------------------------------ Navigation */
  async go(tab, sub, sel) {
    const t = TABS.find(x => x.id === tab);
    this.tab = tab;
    if (tab === 'tenants') {
      const rows = await API.cls('fvTenant', '', true);
      this.tenants = rows.map(r => r.fvTenant.attributes.name).sort((a, b) => (a === 'common' ? -1 : b === 'common' ? 1 : a.localeCompare(b)));
      sub = sub || this.lastTenant || 'all';
    } else sub = sub || t.subs[0][0];
    this.sub = sub;
    if (tab === 'tenants' && sub !== 'all') this.lastTenant = sub;
    this.sel = sel || null;
    this.expanded = new Set();
    document.querySelectorAll('.tab').forEach(a => a.classList.toggle('active', a.dataset.id === tab));
    this.renderSubs();
    await this.renderMain();
  },

  renderSubs() {
    const s = clear(this.el.subs);
    const t = TABS.find(x => x.id === this.tab);
    let items = t.subs || [];
    if (this.tab === 'tenants') {
      items = [['all', 'ALL TENANTS'], ['__add', '+ Add Tenant']].concat(this.tenants.map(n => [n, n]));
    }
    items.forEach(([id, l]) => s.appendChild(h('a', {
      class: 'sub' + (id === this.sub ? ' active' : '') + (id === '__add' ? ' add' : ''),
      onclick: () => id === '__add' ? this.addTenant() : this.go(this.tab, id),
    }, l)));
  },

  addTenant() {
    const f = buildForm(SPEC.fvTenant.fields, {}, { cls: 'fvTenant' }, 'create');
    modal('Create Tenant', f.el, [{ l: 'Abbrechen' }, {
      l: 'Submit', primary: true, fn: async () => {
        const v = f.get();
        if (!v.name) throw new ApiError('Eingabe', 'Name ist ein Pflichtfeld');
        await API.postMo('uni', bodyFromForm('fvTenant', SPEC.fvTenant.fields, v, 'create'));
        toast('Tenant ' + v.name + ' angelegt');
        this.go('tenants', v.name);
      },
    }]);
  },

  setHash() { history.replaceState(null, '', '#' + [this.tab, this.sub, this.sel ? encodeURIComponent(this.sel) : ''].join('|')); },

  layout() {
    const nav = h('aside', { class: 'nav' });
    const work = h('section', { class: 'work' });
    clear(this.el.main).appendChild(h('div', { class: 'split' }, nav, h('div', { class: 'gutter' }), work));
    return { nav, work };
  },

  full() {
    const work = h('section', { class: 'work fullw' });
    clear(this.el.main).appendChild(work);
    return work;
  },

  async renderMain() {
    this.view = null;
    this.setHash();
    const key = this.tab + '/' + this.sub;
    try {
      if (this.tab === 'tenants' && this.sub !== 'all') return await this.treeView(await this.tenantRoots());
      if (key === 'fabric/access') return await this.treeView(await this.accessRoots());
      if (key === 'fabric/inventory') return await this.treeView(Views.inventoryRoots());
      if (key === 'system/settings') return await this.treeView(Views.settingsRoots());
      const fn = Views[key];
      const work = this.full();
      if (fn) await fn.call(Views, work);
      else work.appendChild(h('div', { class: 'placeholder' }, h('h2', null, 'Nicht simuliert'), h('p', null, 'Dieser Bereich des APIC ist im Simulator nicht enthalten.')));
    } catch (e) { errToast(e); console.error(e); }
  },

  /* ------------------------------------------------------------ Baum */
  async tenantRoots() {
    const dn = 'uni/tn-' + this.sub;
    await MIT.load(dn);
    if (dn !== 'uni/tn-common') await MIT.load('uni/tn-common');
    if (!MIT.get(dn)) throw new ApiError(404, 'Tenant ' + this.sub + ' existiert nicht');
    this.expanded.add('mo:' + dn);
    return [moNode(dn)];
  },

  async accessRoots() {
    await MIT.load('uni/infra');
    await MIT.load('uni/fabric/protpol');
    await MIT.loadClass('physDomP', 'rsp-subtree=full&rsp-subtree-include=faults');
    await MIT.loadClass('l3extDomP', 'rsp-subtree=full&rsp-subtree-include=faults');
    MIT.objs.set('uni', MIT.get('uni') || { cls: 'polUni', a: { dn: 'uni' }, kids: [] });
    const uni = MIT.get('uni');
    MIT.ofClass('physDomP').concat(MIT.ofClass('l3extDomP')).forEach(d => { if (!uni.kids.includes(d)) uni.kids.push(d); });
    uni.kids = uni.kids.filter(k => MIT.get(k));
    const top = { key: 'access-root', label: 'Quick Start', icon: '?', kind: 'view', view: w => Views.accessIntro(w) };
    return [top].concat(ACCESS_TREE.map(s => folderNode('', s)));
  },

  async treeView(roots) {
    const { nav, work } = this.layout();
    this.roots = roots;
    this.navEl = nav;
    this.workEl = work;
    if (this.sel) this.expandTo(this.sel);
    else if (roots[0]) this.sel = roots[0].key;
    this.renderTree();
    await this.renderWork();
  },

  renderTree() {
    const nav = clear(this.navEl);
    const walk = (node, depth, ul) => {
      const kids = node.kids ? node.kids() : [];
      const open = this.expanded.has(node.key);
      const faults = node.dn ? MIT.faults(node.dn, true) : [];
      const sev = ['critical', 'major', 'minor', 'warning'].find(s => faults.some(f => f.severity === s));
      const li = h('li', { class: 'tn' + (this.sel === node.key ? ' sel' : '') },
        h('div', { class: 'tnrow', style: { paddingLeft: (6 + depth * 14) + 'px' }, onclick: () => this.select(node.key) },
          h('span', { class: 'twist' + (kids.length ? '' : ' none'), onclick: ev => { ev.stopPropagation(); this.toggle(node.key); } }, kids.length ? (open ? '▾' : '▸') : ''),
          h('span', { class: 'ticon ' + (node.kind === 'folder' ? 'folder' : '') }, node.kind === 'folder' ? '' : (node.icon || '•')),
          h('span', { class: 'tlabel' }, node.label),
          sev ? h('span', { class: 'tfault ' + sev, title: faults.length + ' Fault(s)' }) : null));
      ul.appendChild(li);
      if (open && kids.length) {
        const sub = h('ul');
        kids.forEach(k => walk(k, depth + 1, sub));
        li.appendChild(sub);
      }
    };
    const ul = h('ul', { class: 'tree' });
    this.roots.forEach(r => walk(r, 0, ul));
    nav.appendChild(ul);
  },

  findPath(key) {
    const path = [];
    const dfs = (node, depth) => {
      if (depth > 14) return false;
      path.push(node);
      if (node.key === key) return true;
      for (const k of (node.kids ? node.kids() : [])) if (dfs(k, depth + 1)) return true;
      path.pop();
      return false;
    };
    for (const r of this.roots || []) if (dfs(r, 0)) return path;
    return null;
  },

  findNode(key) { const p = this.findPath(key); return p ? p[p.length - 1] : null; },

  expandTo(key) {
    const p = this.findPath(key);
    if (p) p.slice(0, -1).forEach(n => this.expanded.add(n.key));
  },

  toggle(key) {
    if (this.expanded.has(key)) this.expanded.delete(key); else this.expanded.add(key);
    this.renderTree();
  },

  async select(key) {
    this.sel = key;
    this.expanded.add(key);
    this.setHash();
    this.renderTree();
    await this.renderWork();
  },

  async renderWork() {
    const work = clear(this.workEl);
    this.view = null;
    const node = this.findNode(this.sel) || (this.roots || [])[0];
    if (!node) return;
    try {
      if (node.kind === 'mo') await moView(work, node.dn);
      else if (node.kind === 'folder') folderView(work, node.parent, node.spec);
      else if (node.view) await node.view(work);
    } catch (e) { errToast(e); console.error(e); }
  },

  /* Nach Änderungen Daten neu laden und Ansicht aktualisieren */
  async reload(selectDn) {
    if (this.tab === 'tenants' && this.sub !== 'all') this.roots = await this.tenantRoots();
    else if (this.tab === 'fabric' && this.sub === 'access') this.roots = await this.accessRoots();
    else if (this.tab === 'system' && this.sub === 'settings') { this.roots = Views.settingsRoots(); await MIT.load('uni/fabric/bgpInstP-default'); }
    else if (this.tab === 'fabric' && this.sub === 'inventory') this.roots = Views.inventoryRoots();
    await this.refreshState();
    if (!this.roots || !this.navEl || !document.body.contains(this.navEl)) return this.renderMain();
    if (selectDn) { this.expandTo('mo:' + selectDn); if (this.findNode('mo:' + selectDn)) { this.sel = 'mo:' + selectDn; this.expanded.add(this.sel); } }
    if (!this.findNode(this.sel)) this.sel = this.roots[0] && this.roots[0].key;
    this.setHash();
    this.renderTree();
    await this.renderWork();
  },

  gotoDn(dn) {
    const tn = tenantOf(dn);
    if (tn) return this.go('tenants', tn.slice(7), 'mo:' + bestMoDn(dn));
    if (/^uni\/(infra|phys-|l3dom-|fabric\/protpol)/.test(dn)) return this.go('fabric', 'access', 'mo:' + bestMoDn(dn));
    if (/^uni\/fabric\/bgpInstP/.test(dn)) return this.go('system', 'settings');
    if (/^uni\/controller/.test(dn)) return this.go('fabric', 'inventory', 'membership');
    const m = /^topology\/pod-1\/node-(\d+)/.exec(dn);
    if (m) return this.go('fabric', 'inventory', 'node:' + m[1]);
    window.open('/visore.html#' + encodeURIComponent(dn), '_blank');
  },
};

function bestMoDn(dn) {
  let d = dn.replace(/\/fault-[^/]+$/, '');
  while (d && !(MIT.get(d) && SPEC[MIT.get(d).cls])) {
    const p = parentDn(d);
    if (!p || p === d) break;
    d = p;
  }
  return d || dn;
}

/* ------------------------------------------------------------ Baumknoten */
function moLabel(dn) {
  const o = MIT.get(dn);
  if (!o) return rnOf(dn);
  const a = o.a;
  if (o.cls === 'vzAny') return 'EPG Collection for VRF';
  if (o.cls === 'fabricProtPol') return 'Virtual Port Channel default';
  if (o.cls === 'l3extRsNodeL3OutAtt') return pathLabel(a.tDn) + (a.rtrId ? ' (' + a.rtrId + ')' : '');
  if (o.cls === 'l3extRsPathL3OutAtt') return pathLabel(a.tDn);
  if (o.cls === 'ipRouteP') return a.ip;
  if (o.cls === 'fvSubnet' || o.cls === 'l3extSubnet') return a.ip;
  if (o.cls === 'bgpPeerP') return a.addr;
  return a.name || rnOf(dn);
}

function moNode(dn) {
  const o = MIT.get(dn);
  return {
    key: 'mo:' + dn, dn, kind: 'mo', label: moLabel(dn), icon: ICON[o && o.cls] || '•',
    kids: () => (TREE[o && o.cls] || []).map(s => s.rn ? (MIT.get(dn + '/' + s.rn) ? Object.assign(moNode(dn + '/' + s.rn), { label: s.l }) : null) : folderNode(dn, s)).filter(Boolean),
  };
}

function folderKey(p, spec) { return 'f:' + p + '#' + spec.l + '#' + (spec.cls || []).join(','); }

function folderNode(parent, spec) {
  if (spec.mo) return MIT.get(spec.mo) ? Object.assign(moNode(spec.mo), { label: spec.l }) : { key: 'x:' + spec.mo, label: spec.l, kind: 'view', view: w => w.appendChild(h('p', null, 'nicht vorhanden')) };
  const p = spec.parent !== undefined ? spec.parent : parent;
  return {
    key: folderKey(p, spec), kind: 'folder', label: spec.l, parent: p, spec, dn: null,
    kids: () => spec.sub ? spec.sub.map(s => folderNode(p, s)) : (spec.flat ? [] : MIT.kids(p, spec.cls).map(moNode)),
  };
}

/* ------------------------------------------------------------ Ansichten */
function paneHead(title, sub, buttons) {
  return h('div', { class: 'phead' }, h('div', null, h('h1', null, title), sub ? h('div', { class: 'psub' }, sub) : null), h('div', { class: 'pbtns' }, buttons || []));
}

function tabsBar(names, onSel, active) {
  const bar = h('div', { class: 'wtabs' });
  names.forEach(([id, l]) => bar.appendChild(h('a', { class: 'wtab' + (id === active ? ' active' : ''), onclick: () => { bar.querySelectorAll('.wtab').forEach(x => x.classList.remove('active')); bar.querySelector('[data-id="' + id + '"]').classList.add('active'); onSel(id); }, 'data-id': id }, l)));
  return bar;
}

function faultTable(faults, withLink) {
  return table([
    { l: 'Severity', f: f => sevBadge(f.severity), w: '90px' },
    { l: 'Code', f: f => f.code, w: '70px' },
    { l: 'Affected Object', f: f => withLink ? h('a', { class: 'lnk', onclick: () => App.gotoDn(parentDn(f.dn)) }, parentDn(f.dn)) : parentDn(f.dn) },
    { l: 'Description', f: f => f.descr },
    { l: 'Cause', f: f => f.cause, w: '120px' },
    { l: 'Created', f: f => fmtTs(f.created), w: '150px' },
  ], faults, { empty: 'Keine Faults – alles in Ordnung.' });
}

async function moView(work, dn) {
  const o = MIT.get(dn);
  if (!o) { work.appendChild(h('p', null, 'Objekt nicht gefunden: ' + dn)); return; }
  const spec = SPEC[o.cls] || { fields: [], cols: [] };
  const meta = MIT.meta[o.cls] || {};
  const label = spec.label || meta.label || o.cls;
  const faults = MIT.faults(dn, true);
  const btns = [
    iconBtn('⟳', 'Aktualisieren', () => App.reload()),
    iconBtn('⤓', 'Save as … (JSON)', () => saveAs(dn)),
    iconBtn('⤒', 'Post … (JSON hochladen)', () => postJson(dn)),
  ];
  const fixed = ['polUni', 'infraInfra', 'infraFuncP', 'fabricProtPol', 'vzAny'].includes(o.cls) || ['uni/tn-common', 'uni/tn-infra', 'uni/tn-mgmt'].includes(dn);
  if (meta.config && !fixed) btns.push(iconBtn('🗑', 'Löschen', () => deleteMo(dn), 'danger'));
  work.appendChild(paneHead(label + ' – ' + moLabel(dn), dn, btns));
  const tabs = [['policy', 'Policy']];
  if (spec.oper) tabs.push(['oper', 'Operational']);
  tabs.push(['faults', 'Faults' + (faults.length ? ' (' + faults.length + ')' : '')], ['json', 'JSON']);
  if (o.cls === 'fvAp') tabs.splice(1, 0, ['topo', 'Topology']);
  const body = h('div', { class: 'wbody' });
  const show = id => {
    clear(body);
    if (id === 'policy') renderPolicy(body, dn, o, spec);
    if (id === 'oper') renderOper(body, dn, spec);
    if (id === 'faults') body.appendChild(faultTable(faults, false));
    if (id === 'topo') Views.apTopology(body, dn);
    if (id === 'json') {
      const pre = h('pre', { class: 'json' }, 'lädt …');
      body.appendChild(pre);
      API.mo(dn, 'rsp-subtree=full&rsp-prop-include=config-only').then(r => { pre.textContent = JSON.stringify(r[0], null, 2); });
    }
  };
  const initial = App.pendingTab && tabs.find(t => t[0] === App.pendingTab) ? App.pendingTab : 'policy';
  App.pendingTab = null;
  work.appendChild(tabsBar(tabs, show, initial));
  work.appendChild(body);
  show(initial);
}

function renderPolicy(body, dn, o, spec) {
  if (spec.info) {
    const rows = spec.info(o.a).filter(r => r[1]);
    if (rows.length) body.appendChild(h('div', { class: 'info' }, rows.map(([k, v]) => h('div', null, h('span', null, k), h('b', null, v)))));
  }
  if (spec.fields && spec.fields.length) {
    const init = {};
    spec.fields.forEach(f => { init[f.rel ? f.rel + '.' + f.k : f.k] = fieldValue(o.a, f); });
    const form = buildForm(spec.fields, init, { tenant: tenantOf(dn), cls: o.cls, dn }, 'edit');
    const submit = async () => {
      let v = form.get();
      if (spec.normalize) v = spec.normalize(v);
      if (o.cls === 'aaaUser' && !v.pwd) delete v.pwd;
      const b = bodyFromForm(o.cls, spec.fields, v, 'edit', o.a);
      const inner = b[o.cls];
      if (!Object.keys(inner.attributes).length && !(inner.children || []).length) { toast('Keine Änderungen'); return; }
      try {
        await API.postMo(dn, b);
        toast('Gespeichert');
        App.reload(dn);
      } catch (e) { errToast(e); }
    };
    body.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Properties'), form.el,
      h('div', { class: 'formbtns' }, h('button', { class: 'btn', onclick: () => App.reload() }, 'Reset'), h('button', { class: 'btn primary', onclick: submit }, 'Submit'))));
  }
  (TREE[o.cls] || []).filter(s => s.flat).forEach(s => {
    const holder = h('div', { class: 'card' });
    folderView(holder, dn, s, true);
    body.appendChild(holder);
  });
}

function renderOper(body, dn, spec) {
  if (spec.oper === 'fvCEp') {
    const eps = MIT.kids(dn, ['fvCEp']).map(d => MIT.a(d));
    body.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Client End-Points'),
      table(SPEC.fvCEp.cols, eps, { empty: 'Keine Endpoints gelernt. Prüfe Static Ports, Domains, VLAN und die Faults dieser EPG – und ob ein simulierter Host an diesem Port mit diesem VLAN sendet.' })));
    const hosts = (App.state.hosts || []).filter(x => x.status.epg === dn || !x.status.learned);
    if (hosts.length) {
      body.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Simulierte Hosts (Simulator-Info)'),
        table([{ l: 'Host', f: r => r.name }, { l: 'IP', f: r => r.ip }, { l: 'VLAN', f: r => r.vlan || 'untagged' },
          { l: 'Status', f: r => r.status.learned ? stateBadge('learned') : stateBadge('down') },
          { l: 'Hinweis', f: r => (r.status.reasons || []).join('; ') }], hosts)));
    }
  }
}

function folderView(work, parent, spec, embedded) {
  const classes = spec.cls || [];
  const rowsDn = classes.length ? MIT.kids(parent, classes) : [];
  const canAdd = classes.length && classes.some(c => MIT.meta[c] && MIT.meta[c].config) && !(spec.max && rowsDn.length >= spec.max);
  const add = canAdd ? h('button', { class: 'btn primary small', onclick: () => createFor(parent, classes) }, '+ ' + (embedded ? 'Hinzufügen' : 'Create')) : null;
  if (embedded) work.appendChild(h('div', { class: 'card-h' }, spec.l, h('span', { class: 'grow' }), add));
  else work.appendChild(paneHead(spec.l, parent ? 'in ' + parent : '', [add, iconBtn('⟳', 'Aktualisieren', () => App.reload())]));
  if (spec.sub) {
    work.appendChild(h('div', { class: 'tiles' }, spec.sub.map(s => h('div', { class: 'tile', onclick: () => App.select(folderKey(s.parent !== undefined ? s.parent : parent, s)) }, s.l))));
    return;
  }
  const spec0 = SPEC[classes[0]] || { cols: [] };
  let cols = spec0.cols.slice();
  if (!cols.length) cols = [{ l: 'Name', f: r => r.name || rnOf(r.dn) }];
  const rows = rowsDn.map(d => Object.assign({}, MIT.a(d), { _cls: MIT.get(d).cls }));
  const faultCol = { l: '', w: '24px', f: r => { const fl = MIT.faults(r.dn, true); const s = ['critical', 'major', 'minor', 'warning'].find(x => fl.some(f => f.severity === x)); return s ? h('span', { class: 'tfault ' + s, title: fl.map(f => f.code + ': ' + f.descr).join('\n') }) : ''; } };
  const allCols = classes.length > 1 ? [{ l: 'Objekt', f: r => (SPEC[r._cls].cols[0].f(r)) }, { l: 'Typ', f: r => SPEC[r._cls].label || MIT.meta[r._cls].label }, { l: 'State', f: r => r.state ? stateBadge(r.state) : '' }] : cols;
  work.appendChild(table([faultCol].concat(allCols), rows, {
    onRow: r => spec.flat ? editDialog(r.dn) : App.select('mo:' + r.dn),
    actions: r => MIT.meta[r._cls].config ? [iconBtn('✎', 'Bearbeiten', () => editDialog(r.dn)), iconBtn('🗑', 'Löschen', () => deleteMo(r.dn), 'danger')] : [],
    empty: 'Noch keine Einträge. Mit „+" anlegen.',
  }));
}

function createFor(parent, classes) {
  if (classes.length === 1) return createDialog(parent, classes[0]);
  const sel = h('select', null, classes.map(c => h('option', { value: c }, SPEC[c].label || MIT.meta[c].label)));
  modal('Typ wählen', h('div', { class: 'form' }, h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'Typ'), h('div', { class: 'fctl' }, sel))),
    [{ l: 'Abbrechen' }, { l: 'Weiter', primary: true, fn: () => { setTimeout(() => createDialog(parent, sel.value), 10); } }]);
}

function createDialog(parent, cls) {
  const spec = SPEC[cls] || { fields: [] };
  const fields = spec.createFields || spec.fields.concat(spec.createExtra || []);
  const label = spec.label || MIT.meta[cls].label;
  const form = buildForm(fields, {}, { tenant: tenantOf(parent), cls, dn: parent }, 'create');
  modal('Create ' + label, form.el, [{ l: 'Abbrechen' }, {
    l: 'Submit', primary: true, fn: async () => {
      let v = form.get();
      if (spec.normalize) v = spec.normalize(v);
      fields.forEach(f => {
        const key = f.rel ? f.rel + '.' + f.k : f.k;
        if (f.req && (!f.show || f.show(v)) && (v[key] === '' || v[key] === undefined)) throw new ApiError('Eingabe', 'Pflichtfeld: ' + f.l);
      });
      const b = spec.build ? spec.build(v) : bodyFromForm(cls, fields, v, 'create');
      await API.postMo(parent, b);
      const rootCls = Object.keys(b)[0];
      const attrs = Object.assign({}, MIT.meta[rootCls].attrs, b[rootCls].attributes);
      const newDn = (parent ? parent + '/' : '') + makeRn(rootCls, attrs);
      toast(label + ' angelegt');
      App.reload(isFlat(cls) ? null : newDn);
    },
  }], { wide: fields.length > 6 });
}

function isFlat(cls) { return Object.values(TREE).some(list => list.some(s => s.flat && (s.cls || []).includes(cls))); }

function editDialog(dn) {
  const o = MIT.get(dn);
  const spec = SPEC[o.cls] || { fields: [] };
  const init = {};
  spec.fields.forEach(f => { init[f.rel ? f.rel + '.' + f.k : f.k] = fieldValue(o.a, f); });
  const form = buildForm(spec.fields, init, { tenant: tenantOf(dn), cls: o.cls, dn }, 'edit');
  modal((spec.label || MIT.meta[o.cls].label) + ' – ' + moLabel(dn), h('div', null, h('div', { class: 'muted small' }, dn), form.el), [
    { l: 'Löschen', fn: async () => { await API.delMo(dn); toast('Gelöscht'); App.reload(); } },
    { l: 'Abbrechen' },
    {
      l: 'Submit', primary: true, fn: async () => {
        let v = form.get();
        if (spec.normalize) v = spec.normalize(v);
        const b = bodyFromForm(o.cls, spec.fields, v, 'edit', o.a);
        if (!Object.keys(b[o.cls].attributes).length && !(b[o.cls].children || []).length) return;
        await API.postMo(dn, b);
        toast('Gespeichert');
        App.reload();
      },
    }]);
}

function deleteMo(dn) {
  confirmBox('Objekt ' + dn + ' mit allen Unterobjekten löschen?', async () => {
    await API.delMo(dn);
    toast('Gelöscht');
    App.sel = 'mo:' + parentDn(dn);
    App.reload();
  });
}

async function saveAs(dn) {
  const r = await API.mo(dn, 'rsp-subtree=full&rsp-prop-include=config-only');
  download(rnOf(dn).replace(/[^\w.-]+/g, '_') + '.json', JSON.stringify({ totalCount: '1', imdata: r }, null, 2));
}

async function postJson(dn) {
  const txt = await pickFile();
  if (!txt) return;
  try {
    let j = JSON.parse(txt);
    const items = j.imdata ? j.imdata : [j];
    for (const it of items) {
      const c = Object.keys(it)[0];
      await API.postMo(it[c].attributes && it[c].attributes.dn ? 'uni' : dn, it);
    }
    toast('JSON übernommen');
    App.reload();
  } catch (e) { errToast(e); }
}

window.addEventListener('DOMContentLoaded', () => App.init());
