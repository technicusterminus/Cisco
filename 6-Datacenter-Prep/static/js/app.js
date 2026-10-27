/* Datacenter Prep: Shell, Navigation, Baum, Objektansichten wie im APIC */
'use strict';

const TABS = [
  { id: 'system', l: 'System', subs: [['quickstart', 'QuickStart'], ['dash', 'Dashboard'], ['controllers', 'Controllers'], ['settings', 'System Settings'],
    ['licensing', 'Smart Licensing'], ['faults', 'Faults'], ['zones', 'Config Zones'], ['events', 'Events'], ['audit', 'Audit Log'], ['sessions', 'Active Sessions']] },
  { id: 'tenants', l: 'Tenants' },
  { id: 'fabric', l: 'Fabric', subs: [['inventory', 'Inventory'], ['fabricpol', 'Fabric Policies'], ['access', 'Access Policies']] },
  { id: 'vnet', l: 'Virtual Networking', subs: [['vmm', 'Inventory']] },
  { id: 'admin', l: 'Admin', subs: [['aaa', 'AAA'], ['schedulers', 'Schedulers'], ['hist', 'Historical Record Policies'], ['firmware', 'Firmware'],
    ['collectors', 'External Data Collectors'], ['rollback', 'Config Rollbacks'], ['impexp', 'Import/Export'], ['downloads', 'Downloads']] },
  { id: 'ops', l: 'Operations', subs: [['vis', 'Visibility & Troubleshooting'], ['capacity', 'Capacity Dashboard'], ['ep', 'EP Tracker'], ['viz', 'Visualization']] },
  { id: 'apps', l: 'Apps', subs: [['apps', 'Installed Apps'], ['appfaults', 'Faults']] },
  { id: 'integrations', l: 'Integrations', subs: [['integrations', 'Integrations']] },
  { id: 'sim', l: 'Simulation', subs: [['topo', 'Topologie & Hosts'], ['routers', 'Externe Router'], ['vcenter', 'vCenter'], ['labs', 'Labs'], ['simset', 'Einstellungen']], special: true },
];

const App = {
  tab: 'system', sub: 'dash', sel: null, expanded: new Set(), state: null, tenants: [], view: null,

  async init() {
    MIT.meta = await (await fetch('/sim/meta')).json();
    const su = await (await fetch('/sim/setup')).json();
    if (!su.done) return SetupConsole.show(su);
    API.onAuthLost = () => this.showLogin('Sitzung abgelaufen – bitte erneut anmelden.');
    Inspector.init();
    document.addEventListener('click', () => Ctx.close());
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
        h('div', { class: 'login-brand' }, h('div', { class: 'logo-mark' }, 'DC'), h('div', null, h('b', null, 'Datacenter Prep'), h('div', { class: 'muted' }, 'Application Policy Infrastructure Controller – Trainingsumgebung'))),
        h('label', null, 'User ID'), user, h('label', null, 'Password'), pwd, err,
        h('button', { class: 'btn primary block', onclick: go }, 'Login'),
        h('p', { class: 'muted small' }, 'Standard-Login: admin / admin. Simulierte Umgebung zum Üben, kein Cisco-Produkt.'))));
    pwd.focus();
  },

  async start() {
    const root = clear(document.getElementById('app'));
    this.el = { tabs: h('nav', { class: 'tabs' }), subs: h('div', { class: 'subtabs' }), main: h('div', { class: 'main' }), badges: h('div', { class: 'badges' }) };
    root.appendChild(h('header', { class: 'top' },
      h('div', { class: 'brand', onclick: () => this.go('system', 'dash') }, h('span', { class: 'logo-mark small' }, 'DC'), h('span', { class: 'brand-sub' }, 'Datacenter Prep')),
      this.el.tabs,
      h('div', { class: 'tools' }, this.el.badges,
        h('button', { class: 'tbtn', title: 'APIC- und Switch-CLI', onclick: () => Term.open() }, '⌨ CLI'),
        h('button', { class: 'tbtn', title: 'API Inspector', onclick: () => Inspector.toggle() }, '{ } API Inspector'),
        h('a', { class: 'tbtn', href: '/visore.html', target: '_blank', title: 'Object Store Browser' }, 'Visore'),
        h('button', { class: 'tbtn', onclick: () => this.logout(), title: 'Abmelden' }, '⏻ ' + this.user))));
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
    const sig = () => this.state && JSON.stringify([this.state.nodes, this.state.pending, this.state.faults, this.state.hosts.map(x => x.status), this.state.routers.map(x => x.status)]);
    const before = sig();
    await this.refreshState();
    if (before !== sig() && this.view && this.view.auto && !document.querySelector('.modal-back')) this.view.auto();
  },

  /* ------------------------------------------------------------ Navigation */
  async go(tab, sub, sel) {
    const t = TABS.find(x => x.id === tab);
    this.tab = tab;
    if (tab === 'tenants') {
      const rows = await API.cls('fvTenant', '', true);
      this.tenants = rows.map(r => r.fvTenant.attributes.name).sort((a, b) => (a === 'common' ? -1 : b === 'common' ? 1 : a.localeCompare(b)));
      sub = sub || this.lastTenant || 'all';
      if (!['all', 'search'].includes(sub) && !this.tenants.includes(sub)) sub = 'all';
    } else sub = sub || t.subs[0][0];
    this.sub = sub;
    if (tab === 'tenants' && !['all', 'search'].includes(sub)) this.lastTenant = sub;
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
    if (this.tab === 'tenants') items = [['all', 'ALL TENANTS'], ['__add', 'Add Tenant'], ['search', 'Tenant Search']].concat(this.tenants.map(n => [n, n]));
    items.forEach(([id, l]) => s.appendChild(h('a', {
      class: 'sub' + (id === this.sub ? ' active' : '') + (id === '__add' ? ' add' : ''),
      onclick: () => id === '__add' ? createDialog('uni', 'fvTenant') : this.go(this.tab, id),
    }, l)));
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

  isTreeView() {
    const k = this.tab + '/' + this.sub;
    return (this.tab === 'tenants' && !['all', 'search'].includes(this.sub)) || ['fabric/access', 'fabric/inventory', 'fabric/fabricpol', 'system/settings', 'vnet/vmm'].includes(k);
  },

  async rootsFor() {
    const k = this.tab + '/' + this.sub;
    if (this.tab === 'tenants') return this.tenantRoots();
    if (k === 'fabric/access') return this.accessRoots();
    if (k === 'fabric/fabricpol') return this.fabricPolRoots();
    if (k === 'vnet/vmm') return this.vmmRoots();
    if (k === 'fabric/inventory') return Views.inventoryRoots();
    if (k === 'system/settings') { await MIT.load('uni/fabric/bgpInstP-default'); return Views.settingsRoots(); }
    return [];
  },

  async renderMain() {
    this.view = null;
    this.setHash();
    try {
      if (this.isTreeView()) return await this.treeView(await this.rootsFor());
      const fn = Views[this.tab + '/' + this.sub];
      const work = this.full();
      if (fn) await fn.call(Views, work);
      else Views.placeholder(work, (TABS.find(t => t.id === this.tab).subs || []).find(s => s[0] === this.sub)[1]);
    } catch (e) { errToast(e); console.error(e); }
  },

  /* ------------------------------------------------------------ Baum */
  async tenantRoots() {
    const dn = 'uni/tn-' + this.sub;
    await MIT.load(dn);
    if (dn !== 'uni/tn-common') await MIT.load('uni/tn-common');
    if (!MIT.get(dn)) throw new ApiError(404, 'Tenant ' + this.sub + ' existiert nicht');
    this.expanded.add('mo:' + dn);
    const root = moNode(dn);
    if (dn === 'uni/tn-mgmt') {
      const base = root.kids;
      root.kids = () => base().concat(MGMT_TREE.map(s => folderNode(dn, s)));
    }
    return [root];
  },

  async accessRoots() {
    await MIT.load('uni/infra');
    await MIT.load('uni/fabric/protpol');
    await MIT.loadClass('physDomP', 'rsp-subtree=full&rsp-subtree-include=faults');
    await MIT.loadClass('l3extDomP', 'rsp-subtree=full&rsp-subtree-include=faults');
    await MIT.loadClass('l2extDomP', 'rsp-subtree=full&rsp-subtree-include=faults');
    attachToUni(MIT.ofClass('physDomP').concat(MIT.ofClass('l3extDomP'), MIT.ofClass('l2extDomP')));
    return [{ key: 'access-qs', label: 'Quick Start', icon: '?', kind: 'view', view: w => Views.accessQuickStart(w) },
      { key: 'access-ifcfg', label: 'Interface Configuration', icon: 'IF', kind: 'view', view: w => Views.interfaceConfiguration(w) }]
      .concat(ACCESS_TREE.map(s => folderNode('', s)));
  },

  async vmmRoots() {
    await MIT.load('uni/vmmp-VMware');
    await MIT.load('uni/infra');
    return [{ key: 'vmm-qs', label: 'Quick Start', icon: '?', kind: 'view', view: w => Views.vmmQuickStart(w) }].concat(VMM_TREE.map(s => folderNode('', s)));
  },

  async fabricPolRoots() {
    await MIT.load('uni/fabric');
    return [{ key: 'fp-qs', label: 'Quick Start', icon: '?', kind: 'view', view: w => Views.fabricPolQuickStart(w) }].concat(FABRICPOL_TREE.map(s => folderNode('', s)));
  },

  async treeView(roots) {
    const { nav, work } = this.layout();
    this.roots = roots;
    this.navEl = nav;
    this.workEl = work;
    if (this.sel && this.sel.startsWith('mo:') && !this.findNode(this.sel)) {
      let d = parentDn(this.sel.slice(3));
      while (d && d !== 'uni' && !this.findNode('mo:' + d)) d = parentDn(d);
      if (d && this.findNode('mo:' + d)) this.sel = 'mo:' + d;
    }
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
      const row = h('div', { class: 'tnrow' + (node.ph ? ' ph' : ''), style: { paddingLeft: (6 + depth * 14) + 'px' }, onclick: () => this.select(node.key) },
        h('span', { class: 'twist' + (kids.length ? '' : ' none'), onclick: ev => { ev.stopPropagation(); this.toggle(node.key); } }, kids.length ? (open ? '▾' : '▸') : ''),
        h('span', { class: 'ticon ' + (node.kind === 'folder' ? 'folder' : '') }, node.kind === 'folder' ? '' : (node.icon || '•')),
        h('span', { class: 'tlabel' }, node.label),
        sev ? h('span', { class: 'tfault ' + sev, title: faults.length + ' Fault(s)' }) : null);
      row.addEventListener('contextmenu', ev => { ev.preventDefault(); this.select(node.key); Ctx.open(ev, actionsFor(node)); });
      const li = h('li', { class: 'tn' + (this.sel === node.key ? ' sel' : '') }, row);
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
  expandTo(key) { const p = this.findPath(key); if (p) p.slice(0, -1).forEach(n => this.expanded.add(n.key)); },
  toggle(key) { if (this.expanded.has(key)) this.expanded.delete(key); else this.expanded.add(key); this.renderTree(); },

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
      if (node.ph) Views.placeholder(work, node.label, node.ph);
      else if (node.view) await node.view(work);
      else if (node.kind === 'mo') await moView(work, node.dn);
      else if (node.kind === 'folder') folderView(work, node.parent, node.spec);
    } catch (e) { errToast(e); console.error(e); }
  },

  /* Nach Änderungen Daten neu laden und Ansicht aktualisieren */
  async reload(selectDn) {
    await this.refreshState();
    if (!this.isTreeView()) return this.renderMain();
    this.roots = await this.rootsFor();
    if (!this.navEl || !document.body.contains(this.navEl)) return this.renderMain();
    if (selectDn) { this.expandTo('mo:' + selectDn); if (this.findNode('mo:' + selectDn)) { this.sel = 'mo:' + selectDn; this.expanded.add(this.sel); } }
    if (!this.findNode(this.sel)) this.sel = this.roots[0] && this.roots[0].key;
    this.setHash();
    this.renderTree();
    await this.renderWork();
  },

  gotoDn(dn) {
    dn = dn.replace(/^subj-\[(.*)\]\/(mod|rec)-\d+$/, '$1');
    const tn = tenantOf(dn);
    if (tn) return this.go('tenants', tn.slice(7), 'mo:' + bestMoDn(dn));
    if (/^uni\/vmmp-/.test(dn)) return this.go('vnet', 'vmm', 'mo:' + bestMoDn(dn));
    if (/^uni\/(infra|phys-|l3dom-|l2dom-|fabric\/protpol)/.test(dn)) return this.go('fabric', 'access', 'mo:' + bestMoDn(dn));
    if (/^uni\/fabric\/bgpInstP/.test(dn)) return this.go('system', 'settings');
    if (/^uni\/fabric\/(funcprof|podprof|time-)/.test(dn)) return this.go('fabric', 'fabricpol', 'mo:' + bestMoDn(dn));
    if (/^uni\/fabric\/outofsvc/.test(dn)) return this.go('fabric', 'inventory', 'disabled');
    if (/^uni\/controller/.test(dn)) return this.go('fabric', 'inventory', 'membership');
    const m = /^topology\/pod-\d+\/node-(\d+)/.exec(dn);
    if (m) return this.go('fabric', 'inventory', 'node:' + m[1]);
    window.open('/visore.html#' + encodeURIComponent(dn), '_blank');
  },
};

function attachToUni(dns) {
  if (!MIT.get('uni')) MIT.objs.set('uni', { cls: 'polUni', a: { dn: 'uni' }, kids: [] });
  const uni = MIT.get('uni');
  dns.forEach(d => { if (!uni.kids.includes(d)) uni.kids.push(d); });
  uni.kids = uni.kids.filter(k => MIT.get(k));
}

function bestMoDn(dn) {
  let d = dn.replace(/\/fault-[^/]+$/, '');
  if (!MIT.get(d)) return d;
  while (d && !(MIT.get(d) && SPEC[MIT.get(d).cls])) {
    const p = parentDn(d);
    if (!p || p === d) break;
    d = p;
  }
  return d || dn;
}

/* ------------------------------------------------------------ Kontextmenü */
const Ctx = {
  el: null,
  open(ev, items) {
    this.close();
    if (!items.length) return;
    this.el = h('div', { class: 'ctxmenu', style: { left: ev.clientX + 'px', top: ev.clientY + 'px' } },
      items.map(it => it === '-' ? h('div', { class: 'ctxsep' }) : h('div', { class: 'ctxitem' + (it.danger ? ' danger' : ''), onclick: e => { e.stopPropagation(); this.close(); it.fn(); } }, it.l)));
    document.body.appendChild(this.el);
    const r = this.el.getBoundingClientRect();
    if (r.bottom > window.innerHeight) this.el.style.top = Math.max(0, window.innerHeight - r.height - 6) + 'px';
    if (r.right > window.innerWidth) this.el.style.left = Math.max(0, window.innerWidth - r.width - 6) + 'px';
  },
  close() { if (this.el) { this.el.remove(); this.el = null; } },
};

function createLabel(cls) { return (SPEC[cls] && SPEC[cls].label) || (MIT.meta[cls] && MIT.meta[cls].label) || cls; }

function actionsFor(node) {
  const out = [];
  if (node.ph) return out;
  if (node.kind === 'folder' && node.spec.cls) {
    node.spec.cls.filter(c => MIT.meta[c] && MIT.meta[c].config).forEach(c => out.push({ l: (SPEC[c] && SPEC[c].menu) || 'Create ' + createLabel(c), fn: () => createDialog(node.parent, c, null, node.spec.defaults) }));
  }
  if (node.kind === 'mo' && node.dn) {
    const o = MIT.get(node.dn);
    if (!o) return out;
    const spec = SPEC[o.cls] || {};
    (spec.actions || []).forEach(([l, fn]) => out.push({ l, fn: () => fn(node.dn) }));
    const collect = list => list.flatMap(s => s.sub ? collect(s.sub) : (s.cls && !s.hidden && !s.ph && s.parent === undefined ? [s] : []));
    if (!(spec.actions || []).length) collect(TREE[o.cls] || []).forEach(s => s.cls.filter(c => MIT.meta[c] && MIT.meta[c].config && !MIT.meta[c].rel)
      .forEach(c => out.push({ l: 'Create ' + createLabel(c), fn: () => createDialog(node.dn, c, null, s.defaults) })));
    if (out.length) out.push('-');
    if (isDeletable(node.dn)) out.push({ l: 'Delete', danger: true, fn: () => deleteMo(node.dn) });
    out.push({ l: 'Save as …', fn: () => saveAs(node.dn) }, { l: 'Post …', fn: () => postJson(node.dn) },
      { l: 'Open In Object Store Browser', fn: () => window.open('/visore.html#' + encodeURIComponent(node.dn), '_blank') });
  }
  return out;
}

function isDeletable(dn) {
  const o = MIT.get(dn);
  return o && MIT.meta[o.cls] && MIT.meta[o.cls].config && !['polUni', 'infraInfra', 'infraFuncP', 'fabricProtPol', 'vzAny', 'fabricFuncP', 'fabricOOServicePol'].includes(o.cls) &&
    !['uni/tn-common', 'uni/tn-infra', 'uni/tn-mgmt'].includes(dn);
}

/* ------------------------------------------------------------ Baumknoten */
function moLabel(dn) {
  const o = MIT.get(dn);
  if (!o) return rnOf(dn);
  const a = o.a;
  if (o.cls === 'vzAny') return 'EPG Collection for VRF';
  if (o.cls === 'fabricProtPol') return 'Virtual Port Channel default';
  if (['l3extRsNodeL3OutAtt', 'l3extRsPathL3OutAtt', 'l2extRsPathL2OutAtt', 'mgmtRsOoBStNode'].includes(o.cls)) return pathLabel(a.tDn);
  if (['ipRouteP', 'fvSubnet', 'l3extSubnet'].includes(o.cls)) return a.ip;
  if (o.cls === 'bgpPeerP') return a.addr;
  return a.name || rnOf(dn);
}

function moNode(dn) {
  const o = MIT.get(dn);
  return {
    key: 'mo:' + dn, dn, kind: 'mo', label: moLabel(dn), icon: ICON[o && o.cls] || '•',
    kids: () => (TREE[o && o.cls] || []).filter(s => !s.hidden).map(s => s.rn ? (MIT.get(dn + '/' + s.rn) ? Object.assign(moNode(dn + '/' + s.rn), { label: s.l }) : null) : folderNode(dn, s)).filter(Boolean),
  };
}

function folderKey(p, spec) { return 'f:' + p + '#' + spec.l + '#' + (spec.cls || []).join(',') + (spec.filter ? '#' + JSON.stringify(spec.defaults) : ''); }

function folderNode(parent, spec) {
  if (spec.ph) return { key: 'ph:' + parent + '#' + spec.l, label: spec.l, kind: 'folder', ph: spec.ph, dn: null, spec };
  if (spec.mo) return MIT.get(spec.mo) ? Object.assign(moNode(spec.mo), { label: spec.l }) : { key: 'x:' + spec.mo, label: spec.l, kind: 'view', view: w => w.appendChild(h('p', null, 'nicht vorhanden')) };
  const p = spec.parent !== undefined ? spec.parent : parent;
  return {
    key: folderKey(p, spec), kind: 'folder', label: spec.l, parent: p, spec, dn: null,
    kids: () => spec.sub ? spec.sub.map(s => folderNode(p, s)) : (spec.flat ? [] : folderRows(p, spec).map(moNode)),
  };
}

function folderRows(parent, spec) {
  return MIT.kids(parent, spec.cls).filter(d => !spec.filter || spec.filter(MIT.a(d)));
}

/* ------------------------------------------------------------ Ansichten */
function paneHead(title, sub, buttons) {
  return h('div', { class: 'phead' }, h('div', null, h('h1', null, title), sub ? h('div', { class: 'psub' }, sub) : null), h('div', { class: 'pbtns' }, buttons || []));
}

function tabsBar(names, onSel, active, cls) {
  const bar = h('div', { class: cls || 'wtabs' });
  names.forEach(([id, l]) => bar.appendChild(h('a', {
    class: 'wtab' + (id === active ? ' active' : ''), 'data-id': id,
    onclick: () => { bar.querySelectorAll('.wtab').forEach(x => x.classList.remove('active')); bar.querySelector('[data-id="' + id + '"]').classList.add('active'); onSel(id); },
  }, l)));
  return bar;
}

function actionsButton(items) {
  const b = h('button', { class: 'ibtn wide', title: 'Actions' }, '⚙ ▾');
  b.addEventListener('click', ev => { ev.stopPropagation(); const r = b.getBoundingClientRect(); Ctx.open({ clientX: r.right - 260, clientY: r.bottom + 2 }, items); });
  return b;
}

function faultTable(faults, withLink) {
  return table([
    { l: 'Severity', f: f => sevBadge(f.severity), w: '90px' },
    { l: 'Code', f: f => f.code, w: '70px' },
    { l: 'Affected Object', f: f => withLink ? h('a', { class: 'lnk', onclick: () => App.gotoDn(parentDn(f.dn)) }, parentDn(f.dn)) : parentDn(f.dn) },
    { l: 'Description', f: f => f.descr },
    { l: 'Cause', f: f => f.cause, w: '120px' },
    { l: 'Creation Time', f: f => fmtTs(f.created), w: '150px' },
  ], faults, { empty: 'Keine Faults – alles in Ordnung.' });
}

const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

async function historyView(body, dn) {
  const sub = h('div');
  const show = async id => {
    clear(sub).appendChild(h('p', { class: 'muted' }, 'lädt …'));
    const cls = id === 'events' ? 'eventRecord' : 'aaaModLR';
    const rows = (await API.cls(cls, 'query-target-filter=' + encodeURIComponent('wcard(' + cls + '.affected,"^' + reEsc(dn) + '")') + '&order-by=' + cls + '.created|desc&page-size=200'))
      .map(r => Object.values(r)[0].attributes);
    clear(sub).appendChild(id === 'events' ? eventTable(rows) : auditTable(rows));
  };
  body.appendChild(tabsBar([['events', 'Events'], ['audit', 'Audit Log']], show, 'events', 'wtabs sub'));
  body.appendChild(sub);
  show('events');
}

function eventTable(rows, link) {
  return table([{ l: 'Severity', f: r => sevBadge(r.severity === 'info' ? 'cleared' : r.severity), w: '90px' }, { l: 'Code', f: r => r.code, w: '90px' },
    { l: 'Affected Object', f: r => link ? h('a', { class: 'lnk', onclick: () => App.gotoDn(r.affected) }, r.affected) : r.affected },
    { l: 'Description', f: r => r.descr }, { l: 'Cause', f: r => r.cause, w: '110px' }, { l: 'Creation Time', f: r => fmtTs(r.created), w: '150px' }], rows, { empty: 'Keine Events.' });
}

function auditTable(rows, link) {
  return table([{ l: 'Creation Time', f: r => fmtTs(r.created), w: '150px' }, { l: 'ID', f: r => r.id, w: '100px' }, { l: 'User', f: r => r.user, w: '70px' },
    { l: 'Action', f: r => r.ind, w: '90px' }, { l: 'Affected Object', f: r => link ? h('a', { class: 'lnk', onclick: () => App.gotoDn(r.affected) }, r.affected) : r.affected },
    { l: 'Description', f: r => r.descr }, { l: 'Changes', f: r => r.changeSet }], rows, { empty: 'Keine Änderungen protokolliert.' });
}

async function moView(work, dn) {
  const o = MIT.get(dn);
  if (!o) { work.appendChild(h('p', null, 'Objekt nicht gefunden: ' + dn)); return; }
  const spec = SPEC[o.cls] || { fields: [], cols: [] };
  const meta = MIT.meta[o.cls] || {};
  const label = spec.label || meta.label || o.cls;
  const faults = MIT.faults(dn, true);
  const acts = actionsFor({ kind: 'mo', dn });
  work.appendChild(paneHead(label + ' - ' + moLabel(dn), dn, [iconBtn('⟳', 'Refresh', () => App.reload()), actionsButton(acts)]));
  const tabs = [];
  if (spec.summary) tabs.push(['summary', 'Summary']);
  tabs.push(['policy', 'Policy']);
  if (spec.oper) tabs.push(['oper', 'Operational']);
  if (spec.summary) tabs.push(['stats', 'Stats'], ['health', 'Health']);
  if (spec.topo) tabs.splice(1, 0, ['topo', 'Topology']);
  tabs.push(['faults', 'Faults' + (faults.length ? ' (' + faults.length + ')' : '')], ['history', 'History']);
  const body = h('div', { class: 'wbody' });
  const show = async id => {
    clear(body);
    App.lastTab = id;
    if (id === 'summary') await Views.summary(body, dn, o, spec);
    if (id === 'policy') renderPolicy(body, dn, o, spec);
    if (id === 'oper') await Views.oper(body, dn, o, spec);
    if (id === 'stats') await Views.stats(body, dn);
    if (id === 'health') await Views.health(body, dn, faults);
    if (id === 'faults') body.appendChild(faultTable(faults, false));
    if (id === 'topo') Views.apTopology(body, dn);
    if (id === 'history') await historyView(body, dn);
  };
  const keep = App.lastTab && tabs.find(t => t[0] === App.lastTab) && App.lastDn === dn ? App.lastTab : (spec.summary && App.lastTab === 'summary' ? 'summary' : 'policy');
  App.lastDn = dn;
  work.appendChild(tabsBar(tabs, show, keep));
  work.appendChild(body);
  await show(keep);
}

function renderPolicy(body, dn, o, spec) {
  const groups = spec.groups || [['general', 'General']];
  const holder = h('div');
  const showGroup = g => {
    clear(holder);
    if (g === groups[0][0] && spec.info) {
      const rows = spec.info(o.a).filter(r => r[1]);
      if (rows.length) holder.appendChild(h('div', { class: 'info' }, rows.map(([k, v]) => h('div', null, h('span', null, k), h('b', null, v)))));
    }
    const fields = (spec.fields || []).filter(f => (f.g || groups[0][0]) === g);
    if (fields.length) {
      const init = {};
      fields.forEach(f => { init[f.rel ? f.rel + '.' + f.k : f.k] = fieldValue(o.a, f); });
      const form = buildForm(fields, init, { tenant: tenantOf(dn), cls: o.cls, dn }, 'edit');
      const submit = async () => {
        let v = form.get();
        if (spec.normalize) v = spec.normalize(v);
        if (o.cls === 'aaaUser' && !v.pwd) delete v.pwd;
        const b = bodyFromForm(o.cls, fields, v, 'edit', o.a);
        const inner = b[o.cls];
        if (!Object.keys(inner.attributes).length && !(inner.children || []).length) { toast('Keine Änderungen'); return; }
        try { await API.postMo(dn, b); toast('Gespeichert'); App.reload(dn); } catch (e) { errToast(e); }
      };
      holder.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Properties'), form.el,
        h('div', { class: 'formbtns' }, h('button', { class: 'btn', onclick: () => App.reload() }, 'Reset'), h('button', { class: 'btn primary', onclick: submit }, 'Submit'))));
    }
    (TREE[o.cls] || []).filter(s => s.flat && ((spec.flatGroups || {})[s.cls[0]] || groups[0][0]) === g).forEach(s => {
      const c = h('div', { class: 'card' });
      folderView(c, dn, s, true);
      holder.appendChild(c);
    });
  };
  if (groups.length > 1) body.appendChild(tabsBar(groups, showGroup, groups[0][0], 'wtabs sub'));
  body.appendChild(holder);
  showGroup(groups[0][0]);
}

function folderView(work, parent, spec, embedded) {
  const classes = spec.cls || [];
  const rowsDn = classes.length ? folderRows(parent, spec) : [];
  const canAdd = classes.length && classes.some(c => MIT.meta[c] && MIT.meta[c].config) && !(spec.max && rowsDn.length >= spec.max);
  const add = canAdd ? h('button', { class: 'ibtn plus', title: 'Create', onclick: () => createFor(parent, classes, spec.defaults) }, '+') : null;
  if (embedded) work.appendChild(h('div', { class: 'card-h' }, spec.l, h('span', { class: 'grow' }), add));
  else work.appendChild(paneHead(spec.l, parent ? parent : '', [add, iconBtn('⟳', 'Refresh', () => App.reload()),
    actionsButton(classes.filter(c => MIT.meta[c] && MIT.meta[c].config).map(c => ({ l: 'Create ' + createLabel(c), fn: () => createDialog(parent, c, null, spec.defaults) })))]));
  if (spec.sub) {
    work.appendChild(h('div', { class: 'tiles' }, spec.sub.map(s => h('div', { class: 'tile' + (s.ph ? ' ph' : ''), onclick: () => App.select(s.ph ? 'ph:' + parent + '#' + s.l : folderKey(s.parent !== undefined ? s.parent : parent, s)) }, s.l))));
    return;
  }
  const spec0 = SPEC[classes[0]] || { cols: [] };
  const cols = spec0.cols.length ? spec0.cols : [{ l: 'Name', f: r => r.name || rnOf(r.dn) }];
  const rows = rowsDn.map(d => Object.assign({}, MIT.a(d), { _cls: MIT.get(d).cls }));
  const faultCol = { l: '', w: '24px', f: r => { const fl = MIT.faults(r.dn, true); const s = ['critical', 'major', 'minor', 'warning'].find(x => fl.some(f => f.severity === x)); return s ? h('span', { class: 'tfault ' + s, title: fl.map(f => f.code + ': ' + f.descr).join('\n') }) : ''; } };
  const allCols = classes.length > 1 ? [{ l: 'Name', f: r => SPEC[r._cls].cols[0].f(r) }, { l: 'Type', f: r => SPEC[r._cls].label || MIT.meta[r._cls].label }, { l: 'State', f: r => r.state ? stateBadge(r.state) : '' }] : cols;
  work.appendChild(table([faultCol].concat(allCols), rows, {
    onRow: r => spec.flat ? editDialog(r.dn) : App.select('mo:' + r.dn),
    actions: r => MIT.meta[r._cls].config ? [iconBtn('✎', 'Bearbeiten', () => editDialog(r.dn)), iconBtn('🗑', 'Delete', () => deleteMo(r.dn), 'danger')] : [],
    empty: 'No items have been found. Select Actions to create a new item.',
  }));
}

function createFor(parent, classes, defaults) {
  if (classes.length === 1) return createDialog(parent, classes[0], null, defaults);
  const r = h('div', { class: 'radios' });
  const name = 'c' + Math.random();
  classes.forEach((c, i) => r.appendChild(h('label', { class: 'check' }, h('input', { type: 'radio', name, value: c, checked: i === 0 }), h('span', null, createLabel(c)))));
  modal('Typ wählen', h('div', { class: 'form' }, h('div', { class: 'frow' }, h('label', { class: 'flab' }, 'Typ'), h('div', { class: 'fctl' }, r))),
    [{ l: 'Abbrechen' }, { l: 'Weiter', primary: true, fn: () => { const v = r.querySelector('input:checked').value; setTimeout(() => createDialog(parent, v), 10); } }]);
}

function createDialog(parent, cls, title, defaults) {
  const spec = SPEC[cls] || { fields: [] };
  const label = createLabel(cls);
  const ctx = { tenant: tenantOf(parent) || (cls === 'fvTenant' ? null : null), cls, dn: parent };
  const done = async (body, url, newDn) => {
    await API.postMo(url || parent, body);
    toast(label + ' angelegt');
    if (cls === 'fvTenant') return App.go('tenants', rnOf(newDn).slice(3));
    App.reload(isFlat(cls) ? null : newDn);
  };
  if (spec.wizard) {
    const steps = spec.wizard.steps.map(s => Object.assign({}, s, { fields: s.fields.map(f => defaults && defaults[f.k] !== undefined ? Object.assign({}, f, { def: defaults[f.k] }) : f) }));
    return wizard(title || spec.wizard.title, steps, ctx, async v => {
      if (spec.normalize) v = spec.normalize(v);
      const r = spec.wizard.build(v, parent);
      await done(r.body, r.url, r.dn);
    });
  }
  const fields = (spec.fields || []).map(f => defaults && defaults[f.k] !== undefined ? Object.assign({}, f, { def: defaults[f.k] }) : f);
  const form = buildForm(fields, {}, ctx, 'create');
  modal(title || 'Create ' + label, form.el, [{ l: 'Abbrechen' }, {
    l: 'Submit', primary: true, fn: async () => {
      let v = form.get();
      if (spec.normalize) v = spec.normalize(v);
      checkRequired(fields, v);
      const b = bodyFromForm(cls, fields, v, 'create');
      const attrs = Object.assign({}, MIT.meta[cls].attrs, b[cls].attributes);
      await done(b, null, (parent ? parent + '/' : '') + makeRn(cls, attrs));
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
  modal((spec.label || MIT.meta[o.cls].label) + ' - ' + moLabel(dn), h('div', null, h('div', { class: 'muted small' }, dn), form.el), [
    { l: 'Delete', fn: async () => { await API.delMo(dn); toast('Gelöscht'); App.reload(); } },
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
    const j = JSON.parse(txt);
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
