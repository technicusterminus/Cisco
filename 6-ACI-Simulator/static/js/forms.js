/* Formulare aus Feld-Spezifikationen (siehe specs.js) */
'use strict';

const optCache = new Map();

async function classRows(c) {
  const rows = await API.cls(c, '', true);
  return rows.map(r => Object.values(r)[0].attributes);
}

async function optionsFor(f, ctx) {
  if (f.o) return typeof f.o === 'function' ? f.o(ctx) : f.o;
  if (f.t === 'tname') {
    const rows = await classRows(f.target);
    const tn = ctx.tenant;
    let list;
    if (f.scope === 'infra') list = rows.filter(a => a.dn.startsWith('uni/infra/'));
    else list = rows.filter(a => (tn && a.dn.startsWith(tn + '/')) || a.dn.startsWith('uni/tn-common/'));
    const seen = new Set();
    const own = list.filter(a => !a.dn.startsWith('uni/tn-common/') || tn === 'uni/tn-common');
    own.forEach(a => seen.add(a.name));
    const common = list.filter(a => a.dn.startsWith('uni/tn-common/') && tn !== 'uni/tn-common' && !seen.has(a.name));
    return [['', f.empty || '— auswählen —']]
      .concat(own.map(a => [a.name, a.name]))
      .concat(common.map(a => [a.name, a.name + '  (common)']));
  }
  if (f.t === 'tdn' || f.t === 'tdnmulti') {
    let out = f.t === 'tdn' ? [['', f.empty || '— auswählen —']] : [];
    for (const c of [].concat(f.target)) {
      const rows = await classRows(c);
      const tn = ctx.tenant;
      rows.filter(a => !f.under || a.dn.startsWith(f.under))
        .filter(a => !f.tenantScope || (tn && a.dn.startsWith(tn + '/')) || a.dn.startsWith('uni/tn-common/'))
        .forEach(a => out.push([a.dn, (a.name || rnOf(a.dn)) + (f.tenantScope && a.dn.startsWith('uni/tn-common/') && tn !== 'uni/tn-common' ? '  (common)' : '') +
          (f.target.length > 1 || f.showCls ? '  (' + (MIT.meta[c] ? MIT.meta[c].label : c) + ')' : '')]));
    }
    return out;
  }
  if (f.t === 'node') {
    const rows = await classRows('fabricNode');
    const list = rows.filter(a => a.role === (f.role || 'leaf')).sort((a, b) => a.id - b.id);
    return [['', '— Node wählen —']].concat(list.map(a => [f.ids ? a.id : a.dn, a.name + ' (' + a.id + ')' + (a.fabricSt !== 'active' ? ' – ' + a.fabricSt : '')]));
  }
  return [];
}

function fieldValue(obj, f) {
  if (!obj) return undefined;
  if (f.rel) {
    const rn = MIT.meta[f.rel] ? makeRn(f.rel, {}) : null;
    const child = MIT.a(obj.dn + '/' + rn);
    return child ? child[f.k] : '';
  }
  return obj[f.k];
}

/* fields: Feldliste; init: {key: value}; ctx: {tenant, dn}; mode: 'create' | 'edit' */
function buildForm(fields, init, ctx, mode) {
  const rows = [];
  const getters = {};
  const vals = Object.assign({}, init);
  const grid = h('div', { class: 'form' });
  const update = () => {
    rows.forEach(({ f, row }) => { row.style.display = f.show && !f.show(collect()) ? 'none' : ''; });
  };
  const collect = () => {
    const out = {};
    for (const [k, g] of Object.entries(getters)) out[k] = g();
    return out;
  };
  fields.forEach(f => {
    const key = f.rel ? f.rel + '.' + f.k : f.k;
    const v = vals[key] !== undefined ? vals[key] : (f.def !== undefined ? f.def : (MIT.meta[ctx.cls] && MIT.meta[ctx.cls].attrs[f.k]) || '');
    const ro = (mode === 'edit' && (f.create || f.naming)) || f.ro;
    let ctl;
    const id = 'f_' + Math.random().toString(36).slice(2);
    switch (f.t) {
      case 'yesno': case 'ed': {
        const on = f.t === 'yesno' ? 'yes' : 'enabled', off = f.t === 'yesno' ? 'no' : 'disabled';
        const cb = h('input', { type: 'checkbox', id, checked: v === on, disabled: ro, onchange: update });
        getters[key] = () => cb.checked ? on : off;
        ctl = h('label', { class: 'check' }, cb, h('span', null, f.cl || ''));
        break;
      }
      case 'checks': {
        const set = new Set(String(v || '').split(',').filter(Boolean));
        const boxes = f.o.map(([val, lab]) => {
          const cb = h('input', { type: 'checkbox', checked: set.has(val), disabled: ro, onchange: update });
          return { val, cb, el: h('label', { class: 'check' }, cb, h('span', null, lab)) };
        });
        getters[key] = () => boxes.filter(b => b.cb.checked).map(b => b.val).join(',');
        ctl = h('div', { class: 'checks' }, boxes.map(b => b.el));
        break;
      }
      case 'radio': {
        const name = 'r' + id;
        const items = f.o.map(([val, lab]) => {
          const r = h('input', { type: 'radio', name, checked: v === val, disabled: ro, onchange: update });
          return { val, r, el: h('label', { class: 'check' }, r, h('span', null, lab)) };
        });
        getters[key] = () => (items.find(i => i.r.checked) || { val: v }).val;
        ctl = h('div', { class: 'radios' }, items.map(i => i.el));
        break;
      }
      case 'select': case 'tname': case 'tdn': case 'node': {
        const sel = h('select', { id, disabled: ro, onchange: update });
        const fill = opts => {
          clear(sel);
          let found = false;
          opts.forEach(([val, lab]) => { if (String(val) === String(v)) found = true; sel.appendChild(h('option', { value: val }, lab)); });
          if (!found && v) sel.appendChild(h('option', { value: v }, v + (f.t !== 'select' ? '  (nicht gefunden)' : '')));
          sel.value = v || (opts[0] ? opts[0][0] : '');
          update();
        };
        if (f.o && typeof f.o !== 'function') fill(f.o);
        else { sel.appendChild(h('option', { value: v }, v || 'lädt …')); optionsFor(f, ctx).then(fill).catch(() => fill([])); }
        getters[key] = () => sel.value;
        ctl = sel;
        break;
      }
      case 'tdnmulti': {
        const wrap = h('div', { class: 'checks' }, 'lädt …');
        let boxes = [];
        const set = new Set([].concat(v || []));
        optionsFor(f, ctx).then(opts => {
          clear(wrap);
          if (!opts.length) wrap.appendChild(h('span', { class: 'muted' }, f.none || 'Keine Objekte vorhanden'));
          boxes = opts.map(([val, lab]) => {
            const cb = h('input', { type: 'checkbox', checked: set.has(val) });
            wrap.appendChild(h('label', { class: 'check' }, cb, h('span', null, lab)));
            return { val, cb };
          });
        });
        getters[key] = () => boxes.filter(b => b.cb.checked).map(b => b.val);
        ctl = wrap;
        break;
      }
      case 'path': {
        const p = pathWidget(v, ro, f.types || ['port', 'pc', 'vpc'], update);
        getters[key] = p.get;
        ctl = p.el;
        break;
      }
      case 'textarea': {
        const ta = h('textarea', { id, rows: f.rows || 4, disabled: ro, placeholder: f.ph || '' }, v || '');
        getters[key] = () => ta.value;
        ctl = ta;
        break;
      }
      default: {
        const inp = h('input', { id, type: f.t === 'password' ? 'password' : 'text', value: v === undefined ? '' : v,
          disabled: ro, placeholder: f.ph || '', oninput: update, list: f.list ? id + 'l' : null, autocomplete: 'off' });
        getters[key] = () => inp.value.trim();
        ctl = f.list ? h('span', null, inp, h('datalist', { id: id + 'l' }, f.list.map(x => h('option', { value: x })))) : inp;
      }
    }
    const row = h('div', { class: 'frow' + (f.wide ? ' wide' : '') },
      h('label', { class: 'flab', for: id }, f.l + (f.req ? ' *' : '')),
      h('div', { class: 'fctl' }, ctl, f.help ? h('div', { class: 'help' }, f.help) : null));
    rows.push({ f, row });
    grid.appendChild(row);
  });
  setTimeout(update, 0);
  return { el: grid, get: collect };
}

/* Auswahl eines Pfads wie im APIC: Port / Direct Port Channel / Virtual Port Channel */
function pathWidget(value, ro, types, onchange) {
  let type = 'port';
  if (/protpaths-/.test(value || '')) type = 'vpc';
  else if (value && !/pathep-\[eth/.test(value)) type = 'pc';
  const m = /paths-(\d+)\/pathep-\[(eth[\d/]+)\]/.exec(value || '');
  const typeSel = h('select', { disabled: ro }, types.map(t => h('option', { value: t }, { port: 'Port', pc: 'Direct Port Channel', vpc: 'Virtual Port Channel' }[t])));
  typeSel.value = type;
  const nodeSel = h('select', { disabled: ro });
  const portSel = h('select', { disabled: ro });
  const bundleSel = h('select', { disabled: ro });
  const box = h('div', { class: 'pathw' });
  let nodes = [], paths = [];
  const render = () => {
    clear(box);
    box.appendChild(typeSel);
    if (typeSel.value === 'port') { box.appendChild(nodeSel); box.appendChild(portSel); }
    else box.appendChild(bundleSel);
    if (onchange) onchange();
  };
  const fillPorts = () => {
    const n = nodeSel.value;
    const cur = portSel.value || (m ? m[2] : '');
    clear(portSel);
    paths.filter(a => a.dn.includes('/paths-' + n + '/pathep-[eth')).sort((a, b) => portNum(a.name) - portNum(b.name))
      .forEach(a => portSel.appendChild(h('option', { value: a.name }, a.name)));
    if (cur) portSel.value = cur;
  };
  const fillBundles = () => {
    const t = typeSel.value;
    clear(bundleSel);
    const list = paths.filter(a => t === 'vpc' ? a.dn.includes('/protpaths-') : (!a.dn.includes('/protpaths-') && !/pathep-\[eth/.test(a.dn)));
    if (!list.length) bundleSel.appendChild(h('option', { value: '' }, t === 'vpc' ? 'kein vPC-Pfad (vPC-Policy-Gruppe auf Ports anwenden)' : 'kein Port-Channel-Pfad vorhanden'));
    list.forEach(a => bundleSel.appendChild(h('option', { value: a.dn }, pathLabel(a.dn))));
    if (value && list.find(a => a.dn === value)) bundleSel.value = value;
  };
  typeSel.onchange = () => { fillBundles(); render(); };
  nodeSel.onchange = () => { fillPorts(); if (onchange) onchange(); };
  portSel.onchange = () => onchange && onchange();
  bundleSel.onchange = () => onchange && onchange();
  Promise.all([classRows('fabricNode'), classRows('fabricPathEp')]).then(([n, p]) => {
    nodes = n.filter(a => a.role === 'leaf' && a.fabricSt === 'active').sort((a, b) => a.id - b.id);
    paths = p;
    nodes.forEach(a => nodeSel.appendChild(h('option', { value: a.id }, a.name + ' (' + a.id + ')')));
    if (m) nodeSel.value = m[1];
    if (!nodes.length) nodeSel.appendChild(h('option', { value: '' }, 'keine aktiven Leafs'));
    fillPorts(); fillBundles(); render();
  });
  render();
  return {
    el: box,
    get: () => {
      if (typeSel.value === 'port') return nodeSel.value && portSel.value ? 'topology/pod-1/paths-' + nodeSel.value + '/pathep-[' + portSel.value + ']' : (value || '');
      return bundleSel.value;
    },
  };
}

function portNum(p) { const m = /eth1\/(\d+)/.exec(p || ''); return m ? Number(m[1]) : 0; }

function pathLabel(dn) {
  let m = /protpaths-(\d+)-(\d+)\/pathep-\[(.+)\]$/.exec(dn || '');
  if (m) return 'vPC ' + m[3] + ' (Node ' + m[1] + '-' + m[2] + ')';
  m = /paths-(\d+)\/pathep-\[(.+)\]$/.exec(dn || '');
  if (m) return /^eth/.test(m[2]) ? 'Node ' + m[1] + ' ' + m[2] : 'PC ' + m[2] + ' (Node ' + m[1] + ')';
  m = /node-(\d+)$/.exec(dn || '');
  if (m) return 'Node ' + m[1];
  return dn;
}

/* Generischer Body aus Formularwerten */
function bodyFromForm(cls, fields, vals, mode, current) {
  const attrs = {};
  const children = [];
  fields.forEach(f => {
    if (f.virtual || f.ro) return;
    const key = f.rel ? f.rel + '.' + f.k : f.k;
    const v = vals[key];
    if (v === undefined) return;
    if (f.rel) {
      const old = current ? fieldValue(current, f) : undefined;
      if (mode === 'edit' && v === (old || '')) return;
      if (v === '' && MIT.meta[f.rel].rel && MIT.meta[f.rel].rel[0] === 'dn') {
        if (mode === 'edit' && old) children.push({ [f.rel]: { attributes: { status: 'deleted' } } });
        return;
      }
      if (v === '' && mode === 'create' && !f.keepEmpty) return;
      children.push({ [f.rel]: { attributes: { [f.k]: v } } });
      return;
    }
    if (mode === 'edit' && current && String(current[f.k] === undefined ? '' : current[f.k]) === String(v)) return;
    if (mode === 'create' && v === '' && !f.req) return;
    attrs[f.k] = v;
  });
  const body = { [cls]: { attributes: attrs } };
  if (children.length) body[cls].children = children;
  return body;
}
