/* Formulare, Tabellenfelder und Wizards aus Feld-Spezifikationen (siehe specs.js) */
'use strict';

async function classRows(c) {
  const rows = await API.cls(c, '', true);
  return rows.map(r => Object.values(r)[0].attributes);
}

async function optionsFor(f, ctx) {
  if (f.o) return typeof f.o === 'function' ? f.o(ctx) : f.o;
  const tn = ctx.tenant;
  if (f.t === 'tname' || f.t === 'tnamemulti') {
    const rows = await classRows(f.target);
    let list;
    if (f.scope === 'infra') list = rows.filter(a => a.dn.startsWith('uni/infra/'));
    else if (f.scope === 'fabric') list = rows.filter(a => a.dn.startsWith('uni/fabric/'));
    else list = rows.filter(a => (tn && a.dn.startsWith(tn + '/')) || a.dn.startsWith('uni/tn-common/'));
    const own = list.filter(a => !a.dn.startsWith('uni/tn-common/') || tn === 'uni/tn-common');
    const seen = new Set(own.map(a => a.name));
    const common = list.filter(a => a.dn.startsWith('uni/tn-common/') && tn !== 'uni/tn-common' && !seen.has(a.name));
    const opts = own.map(a => [a.name, a.name]).concat(common.map(a => [a.name, a.name + '  (common)']));
    return f.t === 'tnamemulti' ? opts : [['', f.empty || '— auswählen —']].concat(opts);
  }
  if (f.t === 'tdn' || f.t === 'tdnmulti') {
    const out = f.t === 'tdn' ? [['', f.empty || '— auswählen —']] : [];
    for (const c of [].concat(f.target)) {
      const rows = await classRows(c);
      rows.filter(a => !f.under || a.dn.startsWith(f.under))
        .filter(a => !f.filter || f.filter(a))
        .filter(a => !f.tenantScope || (tn && a.dn.startsWith(tn + '/')) || a.dn.startsWith('uni/tn-common/'))
        .forEach(a => out.push([a.dn, (a.name || rnOf(a.dn)) +
          (f.tenantScope && a.dn.startsWith('uni/tn-common/') && tn !== 'uni/tn-common' ? '  (common)' : '') +
          ([].concat(f.target).length > 1 || f.showCls ? '  (' + (MIT.meta[c] ? MIT.meta[c].label : c) + ')' : '')]));
    }
    return out;
  }
  if (f.t === 'node' || f.t === 'nodemulti') {
    const rows = await classRows('fabricNode');
    const roles = [].concat(f.role || 'leaf');
    const list = rows.filter(a => roles.includes(a.role)).sort((a, b) => a.id - b.id);
    const opts = list.map(a => [f.ids ? a.id : a.dn, a.name + ' (' + a.id + ')' + (a.fabricSt !== 'active' && a.role !== 'controller' ? ' – ' + a.fabricSt : '')]);
    return f.t === 'node' ? [['', '— Node wählen —']].concat(opts) : opts;
  }
  return [];
}

function fieldValue(obj, f) {
  if (!obj) return undefined;
  if (f.rel) {
    const child = MIT.a(obj.dn + '/' + makeRn(f.rel, {}));
    return child ? child[f.k] : '';
  }
  return obj[f.k];
}

/* Ein einzelnes Steuerelement. Rückgabe {el, get} */
function makeControl(f, v, ctx, ro, onchange, compact) {
  const id = 'f_' + Math.random().toString(36).slice(2);
  const ch = () => onchange && onchange();
  switch (f.t) {
    case 'yesno': case 'ed': {
      const on = f.t === 'yesno' ? 'yes' : 'enabled', off = f.t === 'yesno' ? 'no' : 'disabled';
      const cb = h('input', { type: 'checkbox', id, checked: v === on, disabled: ro, onchange: ch });
      return { id, el: h('label', { class: 'check' }, cb, h('span', null, f.cl || '')), get: () => cb.checked ? on : off };
    }
    case 'checks': {
      const set = new Set(String(v || '').split(',').filter(Boolean));
      const boxes = f.o.map(([val, lab]) => {
        const cb = h('input', { type: 'checkbox', checked: set.has(val), disabled: ro, onchange: ch });
        return { val, cb, el: h('label', { class: 'check' }, cb, h('span', null, lab)) };
      });
      return { id, el: h('div', { class: 'checks' }, boxes.map(b => b.el)), get: () => boxes.filter(b => b.cb.checked).map(b => b.val).join(',') };
    }
    case 'radio': {
      const name = 'r' + id;
      const items = f.o.map(([val, lab]) => {
        const r = h('input', { type: 'radio', name, checked: v === val, disabled: ro, onchange: ch });
        return { val, r, el: h('label', { class: 'check' }, r, h('span', null, lab)) };
      });
      return { id, el: h('div', { class: 'radios' }, items.map(i => i.el)), get: () => (items.find(i => i.r.checked) || { val: v }).val };
    }
    case 'select': case 'tname': case 'tdn': case 'node': {
      const sel = h('select', { id, disabled: ro, onchange: ch });
      const fill = opts => {
        clear(sel);
        let found = false;
        opts.forEach(([val, lab]) => { if (String(val) === String(v)) found = true; sel.appendChild(h('option', { value: val }, lab)); });
        if (!found && v) sel.appendChild(h('option', { value: v }, v + (f.t !== 'select' ? '  (nicht gefunden)' : '')));
        sel.value = v || (opts[0] ? opts[0][0] : '');
        ch();
      };
      if (f.o && typeof f.o !== 'function') fill(f.o);
      else { sel.appendChild(h('option', { value: v || '' }, v || 'lädt …')); optionsFor(f, ctx).then(fill).catch(() => fill([])); }
      return { id, el: sel, get: () => sel.value };
    }
    case 'tdnmulti': case 'tnamemulti': case 'nodemulti': {
      const wrap = h('div', { class: 'checks' + (compact ? ' compact' : '') }, 'lädt …');
      let boxes = [];
      const set = new Set([].concat(v || []).map(String));
      optionsFor(f, ctx).then(opts => {
        clear(wrap);
        if (!opts.length) wrap.appendChild(h('span', { class: 'muted' }, f.none || 'Keine Objekte vorhanden'));
        boxes = opts.map(([val, lab]) => {
          const cb = h('input', { type: 'checkbox', checked: set.has(String(val)), disabled: ro, onchange: ch });
          wrap.appendChild(h('label', { class: 'check' }, cb, h('span', null, lab)));
          return { val, cb };
        });
      });
      return { id, el: wrap, get: () => boxes.filter(b => b.cb.checked).map(b => b.val) };
    }
    case 'path': {
      const p = pathWidget(v, ro, f.types || ['port', 'pc', 'vpc'], ch);
      return { id, el: p.el, get: p.get };
    }
    case 'rows': {
      const r = rowsWidget(f, v || [], ctx, ro, ch);
      return { id, el: r.el, get: r.get };
    }
    case 'textarea': {
      const ta = h('textarea', { id, rows: f.rows || 4, disabled: ro, placeholder: f.ph || '' }, v || '');
      return { id, el: ta, get: () => ta.value };
    }
    default: {
      const inp = h('input', { id, type: f.t === 'password' ? 'password' : 'text', value: v === undefined || v === null ? '' : v,
        disabled: ro, placeholder: f.ph || '', oninput: ch, list: f.list ? id + 'l' : null, autocomplete: 'off', style: f.w ? { width: f.w } : null });
      return { id, el: f.list ? h('span', null, inp, h('datalist', { id: id + 'l' }, f.list.map(x => h('option', { value: x })))) : inp, get: () => inp.value.trim() };
    }
  }
}

/* Tabelle mit Zeilen wie in den APIC-Dialogen (+ / Papierkorb) */
function rowsWidget(f, rows, ctx, ro, onchange) {
  const body = h('tbody');
  const items = [];
  const add = vals => {
    const ctls = f.cols.map(c => {
      const dv = vals && vals[c.k] !== undefined ? vals[c.k] : (c.def !== undefined ? c.def : '');
      return { c, ctl: makeControl(c, dv, ctx, ro, onchange, true) };
    });
    const tr = h('tr', null, ctls.map(x => h('td', null, x.ctl.el)),
      h('td', { class: 'act' }, ro ? null : iconBtn('🗑', 'Zeile entfernen', () => { tr.remove(); items.splice(items.indexOf(item), 1); onchange && onchange(); }, 'danger')));
    const item = { tr, ctls };
    items.push(item);
    body.appendChild(tr);
    return item;
  };
  rows.forEach(r => add(r));
  if (!rows.length && f.start) add(null);
  const el = h('div', { class: 'rowsw' },
    h('table', { class: 'grid inner' }, h('thead', null, h('tr', null, f.cols.map(c => h('th', null, c.l + (c.req ? ' *' : ''))),
      h('th', { class: 'act' }, ro ? null : h('button', { class: 'ibtn plus', title: 'Zeile hinzufügen', onclick: ev => { ev.preventDefault(); add(null); } }, '+')))), body));
  return {
    el,
    get: () => items.map(it => {
      const o = {};
      it.ctls.forEach(({ c, ctl }) => { o[c.k] = ctl.get(); });
      return o;
    }).filter(o => {
      const txt = f.cols.filter(c => !['select', 'radio', 'yesno', 'ed', 'tname', 'tdn', 'node'].includes(c.t));
      return (txt.length ? txt : f.cols).some(c => { const x = o[c.k]; return Array.isArray(x) ? x.length : !!x; });
    }),
  };
}

/* fields: Feldliste; init: {key: value}; ctx: {tenant, dn, cls}; mode: 'create' | 'edit' */
function buildForm(fields, init, ctx, mode) {
  const rows = [];
  const getters = {};
  const vals = Object.assign({}, init);
  const grid = h('div', { class: 'form' });
  const collect = () => {
    const out = {};
    for (const [k, g] of Object.entries(getters)) out[k] = g();
    return out;
  };
  const update = () => { const v = collect(); rows.forEach(({ f, row }) => { row.style.display = f.show && !f.show(v) ? 'none' : ''; }); };
  fields.forEach(f => {
    const key = f.rel ? f.rel + '.' + f.k : f.k;
    const metaDef = MIT.meta[ctx.cls] && MIT.meta[ctx.cls].attrs[f.k];
    const v = vals[key] !== undefined ? vals[key] : (f.def !== undefined ? f.def : (metaDef !== undefined && !f.rel ? metaDef : ''));
    const ro = (mode === 'edit' && (f.create || f.naming)) || f.ro;
    const ctl = makeControl(f, v, ctx, ro, () => update());
    getters[key] = ctl.get;
    const row = h('div', { class: 'frow' + (f.t === 'rows' ? ' wide' : '') },
      h('label', { class: 'flab', for: ctl.id }, f.l + (f.req ? ' *' : '')),
      h('div', { class: 'fctl' }, ctl.el, f.help ? h('div', { class: 'help' }, f.help) : null));
    rows.push({ f, row });
    grid.appendChild(row);
  });
  setTimeout(update, 0);
  return { el: grid, get: collect, update };
}

function checkRequired(fields, v) {
  fields.forEach(f => {
    const key = f.rel ? f.rel + '.' + f.k : f.k;
    if (f.req && (!f.show || f.show(v)) && (v[key] === '' || v[key] === undefined)) throw new ApiError('Eingabe', 'Pflichtfeld: ' + f.l);
    if (f.t === 'rows' && (!f.show || f.show(v))) (v[key] || []).forEach(row => f.cols.forEach(c => {
      if (c.req && !row[c.k]) throw new ApiError('Eingabe', 'Pflichtfeld in ' + f.l + ': ' + c.l);
    }));
  });
}

/* Mehrstufiger Wizard wie beim APIC. steps: [{l, fields, show(v)}] */
function wizard(title, steps, ctx, onFinish) {
  const forms = steps.map(s => buildForm(s.fields, {}, ctx, 'create'));
  const all = () => Object.assign({}, ...forms.map(f => f.get()));
  const active = () => steps.map((s, i) => i).filter(i => !steps[i].show || steps[i].show(all()));
  let cur = 0;
  const head = h('div', { class: 'wsteps' });
  const holder = h('div');
  const body = h('div', null, head, holder);
  const chrome = () => {
    clear(head);
    const act = active();
    act.forEach((i, n) => head.appendChild(h('div', { class: 'wstep' + (i === cur ? ' cur' : '') + (act.indexOf(cur) > n ? ' done' : '') },
      h('span', { class: 'wnum' }, String(n + 1)), h('span', null, 'STEP ' + (n + 1)), h('b', null, steps[i].l))));
    const isLast = act[act.length - 1] === cur;
    m.box.querySelector('.wprev').style.display = act[0] === cur ? 'none' : '';
    m.box.querySelector('.wnext').style.display = isLast ? 'none' : '';
  };
  const render = () => {
    clear(holder).appendChild(forms[cur].el);
    forms[cur].update();
    chrome();
  };
  holder.addEventListener('change', () => setTimeout(chrome, 0));
  const m = modal(title, body, [
    { l: 'Abbrechen' },
    { l: 'Previous', cls: 'wprev', fn: () => { const act = active(); cur = act[Math.max(0, act.indexOf(cur) - 1)]; render(); return false; } },
    { l: 'Next', cls: 'wnext', fn: () => { checkRequired(steps[cur].fields, all()); const act = active(); cur = act[Math.min(act.length - 1, act.indexOf(cur) + 1)]; render(); return false; } },
    { l: 'Finish', cls: 'wfin', primary: true, fn: async () => {
      const v = all();
      active().forEach(i => checkRequired(steps[i].fields, v));
      await onFinish(v);
    } }], { wide: true });
  render();
  return m;
}

/* Auswahl eines Pfads wie im APIC: Port / Direct Port Channel / Virtual Port Channel */
function pathWidget(value, ro, types, onchange) {
  let type = 'port';
  if (/protpaths-/.test(value || '')) type = 'vpc';
  else if (value && !/pathep-\[eth/.test(value)) type = 'pc';
  const m = /paths-(\d+)\/pathep-\[(eth[\d/]+)\]/.exec(value || '');
  const typeSel = h('select', { disabled: ro }, types.map(t => h('option', { value: t }, { port: 'Port', pc: 'Direct Port Channel', vpc: 'Virtual Port Channel' }[t])));
  typeSel.value = types.includes(type) ? type : types[0];
  const nodeSel = h('select', { disabled: ro });
  const portSel = h('select', { disabled: ro });
  const bundleSel = h('select', { disabled: ro });
  const box = h('div', { class: 'pathw' });
  let paths = [];
  const render = () => {
    clear(box);
    box.appendChild(typeSel);
    if (typeSel.value === 'port') { box.appendChild(nodeSel); box.appendChild(portSel); } else box.appendChild(bundleSel);
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
    const nodes = n.filter(a => a.role === 'leaf' && a.fabricSt === 'active').sort((a, b) => a.id - b.id);
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
      if (typeSel.value === 'port') return nodeSel.value && portSel.value ? 'topology/pod-' + POD() + '/paths-' + nodeSel.value + '/pathep-[' + portSel.value + ']' : (value || '');
      return bundleSel.value;
    },
  };
}

function portNum(p) { const m = /eth1\/(\d+)/.exec(p || ''); return m ? Number(m[1]) : 0; }

function pathLabel(dn) {
  let m = /protpaths-(\d+)-(\d+)\/pathep-\[(.+)\]$/.exec(dn || '');
  if (m) return 'Pod-1/Node-' + m[1] + '-' + m[2] + '/' + m[3];
  m = /paths-(\d+)\/pathep-\[(.+)\]$/.exec(dn || '');
  if (m) return 'Pod-1/Node-' + m[1] + '/' + m[2];
  m = /node-(\d+)$/.exec(dn || '');
  if (m) return 'Pod-1/Node-' + m[1];
  return dn;
}

/* Generischer Body aus Formularwerten */
function bodyFromForm(cls, fields, vals, mode, current) {
  const attrs = {};
  const children = [];
  fields.forEach(f => {
    if (f.virtual || f.ro || f.t === 'rows') return;
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

function kid(body, child) {
  const c = Object.keys(body)[0];
  (body[c].children = body[c].children || []).push(child);
  return body;
}
