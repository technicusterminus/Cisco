/* Campus Prep: Oberflaeche des C9800-Simulators. Keine zweite Logik: Jedes Formular erzeugt CLI-Befehle, die der Server
   atomar durch dieselbe CLI schickt. Die Menuestruktur ist aus dem Wissen ueber die C9800-WebUI nachgebaut (docs/QUELLEN.md). */
'use strict';

const h = (tag, attrs, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, '');
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  kids.flat(Infinity).forEach(c => { if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c))); });
  return e;
};

/* Transport: Im Servermodus gehen die Aufrufe per fetch an den Python-Server. In WLC-Simulator.html setzt die Seite vorher
   window.CampusTransport (die Engine aus engine.js im Browser); die Oberflaeche merkt keinen Unterschied. */
const call = (method, path, body) => window.CampusTransport
  ? window.CampusTransport(method, path, body)
  : fetch(path, { method, headers: body === undefined ? {} : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
      .then(async r => ({ status: r.status, body: await r.json() }));

const api = {
  state: () => call('GET', '/wlc/api/state').then(r => r.body),
  apply: commands => call('POST', '/wlc/api/apply', { commands }).then(r => Object.assign({ http: r.status }, r.body)),
  post: (path, body) => call('POST', path, body || {}).then(r => Object.assign({ http: r.status }, r.body)),
  get: path => call('GET', path).then(r => Object.assign({ http: r.status }, r.body)),
  cli: command => call('POST', '/wlc/cli', { command }).then(r => r.body),
};

let S = null;
const NAV = [
  { id: 'dash', l: 'Dashboard' },
  { id: 'labs', l: 'Labs (Simulation)' },
  { g: 'Monitoring', sub: 'Wireless', items: [['aps', 'Access Points'], ['clients', 'Clients']] },
  { g: 'Configuration', sub: 'Tags & Profiles', items: [['wlans', 'WLANs'], ['policies', 'Policy'], ['flex', 'Flex'], ['tags', 'Tags (Policy)'], ['sitetags', 'Tags (Site)']] },
  { g: 'Configuration', sub: 'Wireless', items: [['apcfg', 'Access Points']] },
  { g: 'Administration', items: [['cli', 'Command Line Interface']] },
  { g: 'Troubleshooting', items: [['diag', 'Client-Diagnose (Simulation)']] },
];
const TITLES = { dash: 'Dashboard', labs: 'Labs (Simulation)', aps: 'Monitoring > Wireless > Access Points', clients: 'Monitoring > Wireless > Clients',
  wlans: 'Configuration > Tags & Profiles > WLANs', policies: 'Configuration > Tags & Profiles > Policy',
  flex: 'Configuration > Tags & Profiles > Flex', sitetags: 'Configuration > Tags & Profiles > Tags > Site',
  tags: 'Configuration > Tags & Profiles > Tags > Policy', apcfg: 'Configuration > Wireless > Access Points',
  cli: 'Administration > Command Line Interface', diag: 'Troubleshooting > Client-Diagnose (Simulation)' };

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('on');
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('on'), 2600);
}

const badge = (text, kind) => h('span', { class: 'badge ' + kind }, text);
const stateBadge = s => badge(s, ['UP', 'ENABLED', 'Registered', 'Run'].includes(s) ? 'ok' : ['DOWN', 'DISABLED', 'Not joined', 'Not Associated'].includes(s) ? 'bad' : 'warn');

function table(cols, rows, empty) {
  const body = rows.length ? rows.map(r => h('tr', null, cols.map(c => h('td', { class: c.cls || null }, c.f(r)))))
    : [h('tr', null, h('td', { class: 'empty', colspan: cols.length }, empty || 'No items have been found.'))];
  return h('div', { class: 'tablewrap' }, h('table', null, h('thead', null, h('tr', null, cols.map(c => h('th', null, c.l)))), h('tbody', null, body)));
}

/* ---------------------------------------------------------------- Dialog */
function field(label, input, hint) {
  return [h('label', null, label), input, hint ? h('div', { class: 'hint' }, hint) : null];
}

function modal(title, body, cmds, onDone) {
  const err = h('div', { class: 'err', hidden: true, role: 'alert' });
  const pre = h('pre', { 'data-id': 'cli-preview' });
  const upd = () => {
    try { pre.textContent = ['configure terminal'].concat(cmds(), ['end']).join('\n'); } catch (e) { pre.textContent = '(' + e.message + ')'; }
  };
  body.addEventListener('input', upd); body.addEventListener('change', upd);
  const close = () => { bg.remove(); document.removeEventListener('keydown', esc); };
  const esc = ev => { if (ev.key === 'Escape') close(); };
  const apply = h('button', { class: 'primary', 'data-id': 'apply', onclick: async () => {
    err.hidden = true;
    let list;
    try { list = cmds(); } catch (e) { err.textContent = e.message; err.hidden = false; return; }
    apply.disabled = true;
    const r = await api.apply(list);
    apply.disabled = false;
    if (!r.ok) {
      err.textContent = (r.error ? 'Fehler bei "' + r.error.command + '": ' + r.error.message : r.error) + ' - nichts wurde übernommen.';
      err.hidden = false; return;
    }
    close(); toast('Konfiguration angewendet'); await onDone();
  } }, 'Apply to Device');
  const bg = h('div', { class: 'modal-bg', role: 'dialog', 'aria-modal': 'true', 'aria-label': title },
    h('div', { class: 'modal' }, h('h2', null, title), body,
      h('details', { open: true }, h('summary', { class: 'muted' }, 'CLI-Äquivalent'), pre), err,
      h('div', { class: 'btns' }, h('button', { onclick: close }, 'Cancel'), apply)));
  document.body.append(bg); document.addEventListener('keydown', esc); upd();
  const first = bg.querySelector('input:not([disabled]),select:not([disabled])'); if (first) first.focus();
}

const need = (cond, msg) => { if (!cond) throw new Error(msg); };

/* ---------------------------------------------------------------- Ansichten */
const VIEWS = {};

VIEWS.dash = main => {
  if (S.lab) main.append(h('div', { class: 'note' }, 'Aktuelles Lab: ', h('b', null, S.lab.id), ' (', S.lab.mode === 'exam' ? 'Prüfungsmodus' : 'geführt', ') – ',
    h('a', { href: '#/labs' }, 'Aufgaben und Prüfung öffnen')));
  const up = S.aps.filter(a => a.state === 'Registered').length;
  const run = S.clients.filter(c => c.state === 'Run').length;
  main.append(h('div', { class: 'tiles' },
    [[up + ' / ' + S.aps.length, 'Access Points registriert'], [run, 'Clients verbunden'],
      [S.wlans.filter(w => w.status === 'UP').length + ' / ' + S.wlans.length, 'WLANs UP'],
      [S.policies.filter(p => p.status === 'ENABLED').length + ' / ' + S.policies.length, 'Policy Profiles ENABLED']]
      .map(([n, l]) => h('div', { class: 'tile' }, h('div', { class: 'n' }, n), h('div', { class: 'l' }, l)))));
  main.append(h('h2', null, 'Controller'), h('div', { class: 'card' },
    h('div', null, h('b', null, S.wlc.hostname), ' · ', S.wlc.platformId, ' · IOS XE ', S.wlc.version),
    h('div', { class: 'muted' }, 'Management ', S.wlc.ip, ' · ', S.wlc.location)));
  main.append(h('h2', null, 'Access Points'), apTable());
};

const apTable = () => table([{ l: 'AP Name', f: a => a.name }, { l: 'AP Model', f: a => a.model }, { l: 'Ethernet MAC', f: a => a.ethMac },
  { l: 'Radio MAC', f: a => a.radioMac }, { l: 'IP Address', f: a => a.ip }, { l: 'Location', f: a => a.location },
  { l: 'Country', f: a => a.country }, { l: 'Status', f: a => stateBadge(a.state) }, { l: 'AP Mode', f: a => a.mode }], S.aps);

VIEWS.aps = main => main.append(apTable());

VIEWS.clients = main => {
  const rows = S.clients.filter(c => c.state !== 'Not Associated');
  main.append(table([{ l: 'MAC Address', f: c => c.mac }, { l: 'AP Name', f: c => c.ap }, { l: 'WLAN ID', f: c => c.wlan },
    { l: 'SSID', f: c => c.ssid }, { l: 'State', f: c => stateBadge(c.state) }, { l: 'Protocol', f: c => c.protocol },
    { l: 'Auth Method', f: c => c.method }], rows, 'Keine Clients verbunden.'));
};

VIEWS.wlans = main => {
  main.append(h('div', { class: 'bar' }, h('button', { class: 'primary', 'data-id': 'add-wlan', onclick: () => wlanDialog() }, '+ Add')));
  main.append(table([{ l: 'Status', f: w => stateBadge(w.status) }, { l: 'Profile Name', f: w => w.profile }, { l: 'ID', f: w => w.id },
    { l: 'SSID', f: w => w.ssid }, { l: 'Security', f: w => w.security },
    { l: '', f: w => [h('button', { class: 'small', onclick: () => wlanDialog(w) }, 'Edit'), ' ',
      h('button', { class: 'small danger', onclick: () => remove('no wlan ' + w.profile, 'WLAN ' + w.profile) }, 'Delete')] }], S.wlans));
};

function wlanDialog(w) {
  const prof = h('input', { 'data-id': 'wlan-profile', value: w ? w.profile : '', disabled: !!w, placeholder: 'Corp_Profile' });
  const id = h('input', { 'data-id': 'wlan-id', type: 'number', min: 1, max: 4096, value: w ? w.id : nextWlanId(), disabled: !!w });
  const ssid = h('input', { 'data-id': 'wlan-ssid', value: w ? w.ssid : '', disabled: !!w, placeholder: 'Corp' });
  const sec = h('select', { 'data-id': 'wlan-sec' }, h('option', { value: 'open' }, 'Open'), h('option', { value: 'psk' }, 'WPA2 Personal (PSK)'));
  sec.value = w ? w.akm : 'open';
  const key = h('input', { 'data-id': 'wlan-psk', type: 'password', autocomplete: 'off', placeholder: w && w.pskSet ? '(unverändert)' : '' });
  const en = h('input', { 'data-id': 'wlan-enabled', type: 'checkbox' }); en.checked = w ? w.status === 'UP' : false;
  const body = h('div', null,
    h('div', { class: 'row' }, field('Profile Name', prof), field('WLAN ID', id), field('SSID', ssid, 'Im Simulator ohne Leerzeichen.'),
      field('Security', sec), field('Pre-Shared Key', key, 'Ohne Leerzeichen.'), field('Status Enabled', en)));
  modal(w ? 'Edit WLAN ' + w.profile : 'Add WLAN', body, () => {
    if (!w) {
      need(/^[\w.-]{1,32}$/.test(prof.value), 'Profile Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
      need(/^\S{1,32}$/.test(ssid.value), 'SSID: 1-32 Zeichen ohne Leerzeichen');
      need(+id.value >= 1 && +id.value <= 4096, 'WLAN ID: 1-4096');
    }
    const c = ['wlan ' + (w ? w.profile : prof.value) + ' ' + (w ? w.id : id.value) + ' ' + (w ? w.ssid : ssid.value)];
    if (sec.value === 'psk') {
      c.push('security wpa akm psk');
      if (key.value || !(w && w.pskSet)) {
        need(/^\S{8,63}$/.test(key.value), 'Pre-Shared Key: 8-63 Zeichen ohne Leerzeichen');
        c.push('security wpa psk set-key ascii 0 ' + key.value);
      }
    } else if (w && w.akm === 'psk') c.push('no security wpa akm psk');
    c.push(en.checked ? 'no shutdown' : 'shutdown');
    return c;
  }, refresh);
}
const nextWlanId = () => Math.max(0, ...S.wlans.map(x => x.id)) + 1;

VIEWS.policies = main => {
  main.append(h('div', { class: 'bar' }, h('button', { class: 'primary', 'data-id': 'add-policy', onclick: () => policyDialog() }, '+ Add')));
  main.append(table([{ l: 'Status', f: p => stateBadge(p.status) }, { l: 'Policy Profile Name', f: p => p.name },
    { l: 'Description', f: p => p.description || 'Not required' }, { l: 'VLAN', f: p => p.vlan }, { l: 'Switching', f: p => p.central ? 'Central' : 'Local' },
    { l: '', f: p => [h('button', { class: 'small', onclick: () => policyDialog(p) }, 'Edit'), ' ',
      h('button', { class: 'small danger', onclick: () => remove('no wireless profile policy ' + p.name, 'Policy Profile ' + p.name) }, 'Delete')] }], S.policies));
};

function policyDialog(p) {
  const name = h('input', { 'data-id': 'policy-name', value: p ? p.name : '', disabled: !!p, placeholder: 'PP_Corp' });
  const vlan = h('input', { 'data-id': 'policy-vlan', value: p ? p.vlan : '1', placeholder: 'ID oder Name' });
  const central = h('input', { 'data-id': 'policy-central', type: 'checkbox' }); central.checked = p ? p.central : true;
  const descr = h('input', { 'data-id': 'policy-descr', value: p ? p.description : '' });
  const en = h('input', { 'data-id': 'policy-enabled', type: 'checkbox' }); en.checked = p ? p.status === 'ENABLED' : false;
  const body = h('div', { class: 'row' }, field('Name', name), field('VLAN', vlan, 'ID (zentral) oder Name (bei lokalem Switching: Name aus dem Flex Profile).'),
    field('Central Switching', central, 'Ausgeschaltet: lokales Switching (nur für FlexConnect-APs).'), field('Description', descr), field('Status Enabled', en));
  modal(p ? 'Edit Policy Profile ' + p.name : 'Add Policy Profile', body, () => {
    if (!p) need(/^[\w.-]{1,32}$/.test(name.value), 'Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
    need(/^[\w.-]{1,32}$/.test(vlan.value), 'VLAN: ID oder Name (1-32 Zeichen, Buchstaben, Ziffern, . _ -)');
    const c = ['wireless profile policy ' + (p ? p.name : name.value), 'vlan ' + vlan.value, central.checked ? 'central switching' : 'no central switching'];
    if (descr.value.trim()) c.push('description ' + descr.value.trim());
    c.push(en.checked ? 'no shutdown' : 'shutdown');
    return c;
  }, refresh);
}

VIEWS.flex = main => {
  main.append(h('div', { class: 'bar' }, h('button', { class: 'primary', 'data-id': 'add-flex', onclick: () => flexDialog() }, '+ Add'),
    h('span', { class: 'muted' }, 'Ein Flex Profile listet die VLANs, die ein FlexConnect-AP lokal schaltet.')));
  main.append(table([{ l: 'Flex Profile Name', f: f => f.name }, { l: 'Native VLAN', f: f => f.native || '–' },
    { l: 'VLANs (Name, ID)', f: f => f.vlans.length ? f.vlans.map(v => v.name + ' (' + (v.id == null ? '?' : v.id) + ')').join(', ') : '–' },
    { l: '', f: f => f.builtin ? [h('button', { class: 'small', onclick: () => flexDialog(f) }, 'Edit'), ' ', badge('vordefiniert', 'warn')] :
      [h('button', { class: 'small', onclick: () => flexDialog(f) }, 'Edit'), ' ',
        h('button', { class: 'small danger', onclick: () => remove('no wireless profile flex ' + f.name, 'Flex Profile ' + f.name) }, 'Delete')] }], S.flexProfiles));
};

function flexDialog(f) {
  const name = h('input', { 'data-id': 'flex-name', value: f ? f.name : '', disabled: !!f, placeholder: 'FP_Lager' });
  const native = h('input', { 'data-id': 'flex-native', type: 'number', min: 1, max: 4094, value: f && f.native ? f.native : '', placeholder: 'optional' });
  const rows = h('div', { 'data-id': 'flex-rows' });
  const addRow = v => {
    const n = h('input', { placeholder: 'VLAN-Name', value: v ? v.name : '', disabled: !!v, 'aria-label': 'VLAN-Name' });
    const i = h('input', { type: 'number', min: 1, max: 4094, placeholder: 'ID', value: v && v.id != null ? v.id : '', style: 'width:90px', 'aria-label': 'VLAN-ID' });
    const r = h('div', { class: 'maprow' }, n, i, h('button', { class: 'small', type: 'button', onclick: () => { r.remove(); rows.dispatchEvent(new Event('input', { bubbles: true })); } }, '✕'));
    r.get = () => ({ name: n.value.trim(), id: i.value.trim() }); rows.append(r);
  };
  (f ? f.vlans : []).forEach(addRow);
  const body = h('div', null, h('div', { class: 'row' }, field('Name', name), field('Native VLAN ID', native)),
    h('h2', null, 'VLAN-Name → VLAN-ID'), rows,
    h('button', { class: 'small', 'data-id': 'flex-add-vlan', type: 'button', onclick: () => { addRow(); rows.dispatchEvent(new Event('input', { bubbles: true })); } }, '+ Add VLAN'));
  modal(f ? 'Edit Flex Profile ' + f.name : 'Add Flex Profile', body, () => {
    if (!f) need(/^[\w.-]{1,32}$/.test(name.value), 'Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
    need(native.value === '' || (+native.value >= 1 && +native.value <= 4094), 'Native VLAN: 1-4094');
    const list = [...rows.children].map(r => r.get());
    list.forEach(v => { need(/^[\w.-]{1,32}$/.test(v.name), 'VLAN-Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)'); need(+v.id >= 1 && +v.id <= 4094, 'VLAN-ID: 1-4094'); });
    need(new Set(list.map(v => v.name)).size === list.length, 'Jeder VLAN-Name darf nur einmal vorkommen');
    const c = ['wireless profile flex ' + (f ? f.name : name.value)];
    if (native.value !== '') c.push('native-vlan-id ' + native.value); else if (f && f.native) c.push('no native-vlan-id');
    if (f) f.vlans.filter(o => !list.some(v => v.name === o.name)).forEach(o => c.push('no vlan-name ' + o.name));
    list.forEach(v => c.push('vlan-name ' + v.name, 'vlan-id ' + v.id));
    return c;
  }, refresh);
}

VIEWS.sitetags = main => {
  main.append(h('div', { class: 'bar' }, h('button', { class: 'primary', 'data-id': 'add-site', onclick: () => siteDialog() }, '+ Add'),
    h('span', { class: 'muted' }, 'Ein Site Tag ohne Local Site versetzt die APs, die es erhalten, in den FlexConnect-Modus.')));
  main.append(table([{ l: 'Site Tag Name', f: t => t.name }, { l: 'Local Site', f: t => t.local ? 'Yes' : 'No' },
    { l: 'Flex Profile', f: t => t.flexProfile || '–' },
    { l: '', f: t => t.builtin ? [h('button', { class: 'small', onclick: () => siteDialog(t) }, 'Edit'), ' ', badge('vordefiniert', 'warn')] :
      [h('button', { class: 'small', onclick: () => siteDialog(t) }, 'Edit'), ' ',
        h('button', { class: 'small danger', onclick: () => remove('no wireless tag site ' + t.name, 'Site Tag ' + t.name) }, 'Delete')] }], S.siteTags));
};

function siteDialog(t) {
  const name = h('input', { 'data-id': 'site-name', value: t ? t.name : '', disabled: !!t, placeholder: 'ST_Lager' });
  const local = h('input', { 'data-id': 'site-local', type: 'checkbox' }); local.checked = t ? t.local : true;
  const flex = h('select', { 'data-id': 'site-flex' }, S.flexProfiles.map(x => h('option', { value: x.name }, x.name)));
  if (t && t.flexProfile) flex.value = t.flexProfile;
  const sync = () => { flex.disabled = local.checked; };
  local.addEventListener('change', sync); sync();
  const body = h('div', { class: 'row' }, field('Name', name), field('Enable Local Site', local, 'Ausgeschaltet: AP im FlexConnect-Modus.'),
    field('Flex Profile', flex, 'Nur wählbar, wenn Local Site ausgeschaltet ist.'));
  modal(t ? 'Edit Site Tag ' + t.name : 'Add Site Tag', body, () => {
    if (!t) need(/^[\w.-]{1,32}$/.test(name.value), 'Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
    const c = ['wireless tag site ' + (t ? t.name : name.value), local.checked ? 'local-site' : 'no local-site'];
    if (!local.checked) c.push('flex-profile ' + flex.value);
    return c;
  }, refresh);
}

VIEWS.tags = main => {
  main.append(h('div', { class: 'bar' }, h('button', { class: 'primary', 'data-id': 'add-tag', onclick: () => tagDialog() }, '+ Add'),
    h('span', { class: 'muted' }, 'Policy Tags verbinden WLAN-Profile mit Policy Profiles. Ein AP strahlt nur die WLANs seines Policy Tags aus.')));
  S.policyTags.forEach(t => main.append(h('div', { class: 'card', 'data-tag': t.name },
    h('div', { class: 'bar' }, h('b', null, t.name), t.builtin ? badge('vordefiniert', 'warn') : null, h('span', { class: 'grow' }),
      t.builtin ? null : [h('button', { class: 'small', onclick: () => tagDialog(t) }, 'Edit'),
        h('button', { class: 'small danger', onclick: () => remove('no wireless tag policy ' + t.name, 'Policy Tag ' + t.name) }, 'Delete')]),
    table([{ l: 'WLAN Profile', f: m => m.wlan }, { l: 'Policy Profile', f: m => m.policy }], t.maps, 'Keine WLANs zugeordnet.'))));
};

function tagDialog(t) {
  const name = h('input', { 'data-id': 'tag-name', value: t ? t.name : '', disabled: !!t, placeholder: 'PT_Corp' });
  const rows = h('div', { 'data-id': 'tag-rows' });
  const opt = (list, val) => { const s = h('select', null, list.map(x => h('option', { value: x }, x))); if (val) s.value = val; return s; };
  const addRow = (m) => {
    const w = opt(S.wlans.map(x => x.profile), m && m.wlan), p = opt(S.policies.map(x => x.name), m && m.policy);
    const r = h('div', { class: 'maprow' }, w, '→', p, h('button', { class: 'small', type: 'button', onclick: () => { r.remove(); rows.dispatchEvent(new Event('input', { bubbles: true })); } }, '✕'));
    r.get = () => [w.value, p.value]; rows.append(r);
  };
  (t ? t.maps : []).forEach(addRow);
  const body = h('div', null, h('div', { class: 'row' }, field('Name', name)),
    h('h2', null, 'WLAN Profile → Policy Profile'), rows,
    h('button', { class: 'small', 'data-id': 'add-map', type: 'button', onclick: () => { addRow(); rows.dispatchEvent(new Event('input', { bubbles: true })); } }, '+ Add Map'));
  modal(t ? 'Edit Policy Tag ' + t.name : 'Add Policy Tag', body, () => {
    if (!t) need(/^[\w.-]{1,32}$/.test(name.value), 'Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
    const maps = [...rows.children].map(r => r.get()).filter(m => m[0] && m[1]);
    need(new Set(maps.map(m => m[0])).size === maps.length, 'Jedes WLAN darf nur einmal vorkommen');
    const c = ['wireless tag policy ' + (t ? t.name : name.value)];
    if (t) t.maps.filter(o => !maps.some(m => m[0] === o.wlan)).forEach(o => c.push('no wlan ' + o.wlan + ' policy ' + o.policy));
    maps.forEach(m => c.push('wlan ' + m[0] + ' policy ' + m[1]));
    return c;
  }, refresh);
}

VIEWS.apcfg = main => {
  main.append(h('div', { class: 'note' }, 'Ein AP ohne eigenes Tag nutzt die Default Tags. Tag Source zeigt, ob ein Tag zugewiesen (Static) oder der Standard ist. Der AP-Modus kommt vom Site Tag.'));
  main.append(table([{ l: 'AP Name', f: a => a.name }, { l: 'AP MAC', f: a => a.ethMac }, { l: 'Site Tag', f: a => a.siteTag },
    { l: 'Policy Tag', f: a => a.policyTag }, { l: 'RF Tag', f: a => a.rfTag }, { l: 'AP Mode', f: a => a.mode }, { l: 'Tag Source', f: a => a.tagSource },
    { l: '', f: a => h('button', { class: 'small', 'data-id': 'ap-tag-' + a.name, onclick: () => apDialog(a) }, 'Edit Tags') }], S.aps));
};

function apDialog(a) {
  const tag = h('select', { 'data-id': 'ap-policy-tag' }, S.policyTags.map(t => h('option', { value: t.name }, t.name)));
  tag.value = a.policyTag;
  const site = h('select', { 'data-id': 'ap-site-tag' }, S.siteTags.map(t => h('option', { value: t.name }, t.name)));
  site.value = a.siteTag;
  const body = h('div', { class: 'row' }, field('AP Name', h('input', { value: a.name, disabled: true })), field('Policy Tag', tag), field('Site Tag', site, 'Ein Site Tag ohne Local Site versetzt den AP in den FlexConnect-Modus.'));
  modal('Edit Tags: ' + a.name, body, () => ['ap ' + a.ethMac, tag.value === 'default-policy-tag' ? 'no policy-tag' : 'policy-tag ' + tag.value,
    site.value === 'default-site-tag' ? 'no site-tag' : 'site-tag ' + site.value], refresh);
}

async function remove(cmd, what) {
  if (!confirm(what + ' löschen?')) return;
  const r = await api.apply([cmd]);
  if (!r.ok) { toast(r.error.message); return; }
  toast(what + ' gelöscht'); refresh();
}

VIEWS.cli = async main => {
  const term = h('div', { class: 'term', 'data-id': 'term', tabindex: 0, role: 'log' });
  const first = await api.cli('');
  let prompt = first.prompt;
  const input = h('input', { 'data-id': 'cli-input', style: 'flex:1', autocomplete: 'off', spellcheck: 'false', 'aria-label': 'Befehl' });
  const label = h('span', { class: 'muted' }, prompt);
  const run = async () => {
    const cmd = input.value; input.value = '';
    const r = await api.cli(cmd);
    term.append(h('div', { class: 'in' }, prompt + ' ' + cmd), r.output ? h('div', null, r.output) : null);
    prompt = r.prompt; label.textContent = prompt; term.scrollTop = term.scrollHeight;
    S = await api.state();
  };
  input.addEventListener('keydown', ev => { if (ev.key === 'Enter') run(); });
  main.append(h('div', { class: 'note' }, 'Diese Sitzung hat einen eigenen Modus (exec/config), unabhängig von den Dialogen. Belegt sind nur die in der README genannten Show-Befehle.'),
    term, h('div', { class: 'bar', style: 'margin-top:8px' }, label, input, h('button', { class: 'primary', onclick: run }, 'Run')));
};

VIEWS.diag = main => {
  if (!S.diagAvailable) { main.append(h('div', { class: 'note', 'data-id': 'diag-locked' }, 'Im Prüfungsmodus ist die Client-Diagnose nicht verfügbar. Nutze Monitoring, die Show-Befehle und die CLI.')); return; }
  main.append(h('div', { class: 'note' }, 'Simulation: Diese Seite gibt es am echten Controller nicht. Sie erklärt, warum ein Client (nicht) verbunden ist. Die Begründungen sind ein didaktisches Modell.'));
  main.append(table([{ l: 'MAC Address', f: c => c.mac }, { l: 'SSID', f: c => c.ssid }, { l: 'AP', f: c => c.ap },
    { l: 'Ergebnis', f: c => stateBadge(c.state) }, { l: 'Switching', f: c => c.switching || '–' }, { l: 'Begründung', cls: 'reason', f: c => c.reasons.length ? c.reasons.join(' ') : 'Verbunden' }], S.clients));
};

/* ---------------------------------------------------------------- Labs */
/* Kleines Markdown: **fett**, `code`, Zeilen mit "- " als Liste. Es wird nie HTML eingesetzt. */
function md(text) {
  const inline = line => line.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map(t =>
    t.startsWith('**') ? h('b', null, t.slice(2, -2)) : t.startsWith('`') ? h('code', null, t.slice(1, -1)) : t);
  const out = []; let list = null;
  text.split('\n').forEach(l => {
    if (l.startsWith('- ')) { if (!list) { list = h('ul'); out.push(list); } list.append(h('li', null, inline(l.slice(2)))); return; }
    list = null; if (l.trim()) out.push(h('p', null, inline(l)));
  });
  return out;
}

VIEWS.labs = async main => {
  const r = await api.get('/wlc/api/labs');
  const cur = r.current;
  if (cur) main.append(labCard(cur));
  const done = r.labs.filter(l => l.progress.passed).length, exam = r.labs.filter(l => l.progress.examPassed).length;
  main.append(h('div', { class: 'tiles' }, [[done + ' / ' + r.labs.length, 'Labs bestanden'], [exam, 'davon im Prüfungsmodus'],
    [r.labs.reduce((a, l) => a + l.progress.starts, 0), 'Starts insgesamt']].map(([n, l]) => h('div', { class: 'tile' }, h('div', { class: 'n' }, n), h('div', { class: 'l' }, l)))));
  main.append(h('h2', null, cur ? 'Weitere Labs' : 'Verfügbare Labs'));
  const mode = h('select', { 'data-id': 'lab-mode', 'aria-label': 'Modus' }, h('option', { value: 'guided' }, 'Geführt (Hinweise, Diagnose)'),
    h('option', { value: 'exam' }, 'Prüfung (ohne Hilfe)'));
  main.append(h('div', { class: 'bar' }, 'Modus: ', mode, h('span', { class: 'muted' }, 'Ein Lab-Start setzt die Welt auf den Ausgangszustand zurück.')));
  main.append(table([{ l: 'Status', f: l => l.progress.examPassed ? badge('Prüfung bestanden', 'ok') : l.progress.guidedPassed ? badge('Geführt bestanden', 'ok')
      : l.progress.starts ? badge('begonnen', 'warn') : h('span', { class: 'muted' }, 'offen') },
    { l: 'Lab', f: l => h('b', null, l.title) }, { l: 'Track', f: l => l.track }, { l: 'Thema', f: l => l.topic }, { l: 'Niveau', f: l => l.level },
    { l: 'Dauer', f: l => l.duration }, { l: 'Art', f: l => l.kind === 'troubleshooting' ? 'Fehlersuche' : 'Anforderungen' },
    { l: '', f: l => h('button', { class: 'small primary', 'data-id': 'start-' + l.id.slice(0, 2), onclick: async () => {
      if (cur && !confirm('Das laufende Lab wird ersetzt. Fortfahren?')) return;
      const x = await api.post('/wlc/api/lab/start', { id: l.id, mode: mode.value });
      if (x.http !== 200) { toast(x.error); return; }
      toast('Gestartet: ' + l.title); refresh();
    } }, 'Start') }], r.labs));
  await savesCard(main);
};

async function savesCard(main) {
  main.append(h('h2', null, 'Stände'));
  if (!S.persistent) {
    main.append(h('div', { class: 'note' }, S.standalone ? 'Der Browser stellt keinen lokalen Speicher bereit (z. B. im privaten Modus): Der Zustand geht beim Schließen verloren, Stände sind nicht verfügbar.'
      : 'Der Zustand wird in dieser Sitzung nicht dauerhaft gespeichert (Start mit --ephemeral).'));
    return;
  }
  const sv = await api.get('/wlc/api/saves');
  const name = h('input', { 'data-id': 'save-name', placeholder: 'z. B. lab01-vor-hint', 'aria-label': 'Name des Stands', maxlength: 40 });
  main.append(h('div', { class: 'muted', style: 'margin-bottom:8px' },
    (S.standalone ? 'Der aktuelle Zustand wird automatisch im Browser gespeichert (lokaler Speicher, nur auf diesem Gerät) und beim Öffnen wieder geladen. ' : 'Der aktuelle Zustand wird automatisch gespeichert und beim Start wieder geladen. ') +
    'Ein Stand enthält Konfiguration, Welt und die Lab-Sitzung; der Fortschritt bleibt erhalten.'));
  main.append(h('div', { class: 'bar' }, name, h('button', { 'data-id': 'save', onclick: async () => {
    const x = await api.post('/wlc/api/saves', { name: name.value.trim() });
    if (x.http !== 200) { toast(x.error); return; }
    toast('Stand gespeichert'); refresh();
  } }, 'Stand speichern')));
  main.append(table([{ l: 'Name', f: x => x.name }, { l: 'Lab', f: x => x.lab || '–' }, { l: 'WLANs', f: x => x.wlans },
    { l: '', f: x => [x.broken ? badge('nicht lesbar', 'bad') : h('button', { class: 'small', 'data-id': 'load-' + x.name, onclick: async () => {
      if (!confirm('Den aktuellen Zustand durch den Stand "' + x.name + '" ersetzen?')) return;
      const r = await api.post('/wlc/api/saves/load', { name: x.name });
      if (r.http !== 200) { toast(r.error); return; }
      toast('Stand geladen'); refresh();
    } }, 'Laden'), ' ', h('button', { class: 'small danger', 'data-id': 'del-' + x.name, onclick: async () => {
      if (!confirm('Stand "' + x.name + '" löschen?')) return;
      await api.post('/wlc/api/saves/delete', { name: x.name }); refresh();
    } }, 'Löschen')] }], sv.saves, 'Keine Stände gespeichert.'));
  main.append(h('div', { class: 'bar', style: 'margin-top:10px' }, h('button', { class: 'danger', 'data-id': 'reset-progress', onclick: async () => {
    if (!confirm('Den gesamten Lab-Fortschritt zurücksetzen?')) return;
    await api.post('/wlc/api/progress/reset'); toast('Fortschritt zurückgesetzt'); refresh();
  } }, 'Fortschritt zurücksetzen')));
}

function labCard(lab) {
  const exam = lab.mode === 'exam';
  const result = h('div', { 'data-id': 'check-result' });
  const sol = h('div', { 'data-id': 'solution' });
  const card = h('div', { class: 'card', 'data-lab': lab.id },
    h('div', { class: 'bar' }, h('b', null, lab.title), badge(exam ? 'Prüfungsmodus' : 'Geführt', exam ? 'warn' : 'ok'), h('span', { class: 'grow' }),
      h('span', { class: 'muted' }, lab.level + ' · ' + lab.duration)),
    h('div', { class: 'muted', 'data-id': 'lab-track' }, lab.track),
    md(lab.intro),
    h('h2', null, 'Anforderungen'), h('ul', null, lab.requirements.map(x => h('li', null, x))),
    h('details', null, h('summary', null, 'Lernziele, Werkzeuge und Grenzen dieses Szenarios'),
      h('p', null, h('b', null, 'Lernziele')), h('ul', null, lab.goals.map(x => h('li', null, x))),
      h('p', null, h('b', null, 'Werkzeuge')), h('ul', null, lab.tools.map(x => h('li', null, x))),
      h('p', null, h('b', null, 'Grenzen')), h('ul', null, lab.limits.map(x => h('li', null, x)))),
    exam ? h('div', { class: 'muted', style: 'margin:8px 0' }, 'Prüfungsmodus: keine Hinweise, keine Lösung, keine Diagnose, keine Details in der Auswertung.') : hintBox(lab),
    lab.questions.length ? [h('h2', null, 'Verständnisfragen (zählen nicht zum Bestehen)'), lab.questions.map(q => question(lab, q))] : null,
    h('div', { class: 'bar', style: 'margin-top:14px' },
      h('button', { class: 'primary', 'data-id': 'lab-check', onclick: async () => { const c = await api.post('/wlc/api/lab/check'); result.textContent = ''; result.append(checkView(c)); } }, 'Lab prüfen'),
      h('button', { 'data-id': 'lab-reset', onclick: async () => { if (!confirm('Das Lab auf den Ausgangszustand zurücksetzen?')) return; await api.post('/wlc/api/lab/reset'); toast('Zurückgesetzt'); refresh(); } }, 'Zurücksetzen'),
      exam ? null : h('button', { 'data-id': 'lab-solution', onclick: async () => { const x = await api.get('/wlc/api/lab/solution'); sol.textContent = ''; if (x.solution) sol.append(h('div', { class: 'note' }, md(x.solution))); } }, 'Lösung zeigen'),
      h('button', { class: 'danger', onclick: async () => { await api.post('/wlc/api/lab/stop'); refresh(); } }, 'Lab beenden')),
    result, sol);
  return card;
}

function hintBox(lab) {
  const box = h('div', { 'data-id': 'hints' });
  const draw = l => {
    box.textContent = '';
    l.hints.forEach((t, i) => box.append(h('div', { class: 'note', 'data-hint': i + 1 }, md(t))));
    if (l.hintsUsed < l.hintsTotal) box.append(h('button', { 'data-id': 'hint', onclick: async () => { const x = await api.post('/wlc/api/lab/hint'); if (x.current) draw(x.current); } },
      'Hinweis anzeigen (Stufe ' + (l.hintsUsed + 1) + ' von ' + l.hintsTotal + ')'));
  };
  draw(lab);
  return box;
}

function question(lab, q) {
  const fb = h('div', { class: 'muted' });
  const name = 'q-' + q.id;
  return h('div', { class: 'card', 'data-q': q.id }, h('div', null, h('b', null, q.q)),
    q.options.map((o, i) => h('label', { style: 'display:block;margin:4px 0' }, h('input', { type: 'radio', name, onchange: async () => {
      const x = await api.post('/wlc/api/lab/answer', { id: q.id, answer: i });
      fb.textContent = x.correct ? '✔ richtig. ' + (x.explain || '') : '✖ nicht richtig. ' + (x.explain || '');
    } }), ' ', o)), fb);
}

function checkView(c) {
  if (c.error) return h('div', { class: 'err' }, c.error);
  const cats = Object.entries(c.categories).map(([k, v]) => h('div', { class: 'tile' }, h('div', { class: 'n' }, v.ok + ' / ' + v.total),
    h('div', { class: 'l' }, k === 'security' ? 'Sicherheit / Least Privilege' : 'Funktion')));
  return h('div', { style: 'margin-top:12px' },
    h('div', { class: 'bar' }, c.passed ? badge('bestanden', 'ok') : badge('noch nicht bestanden', 'bad'),
      h('span', { class: 'muted' }, 'Hinweise genutzt: ' + c.hintsUsed + ' · Fragen richtig: ' + c.questions.right + ' / ' + c.questions.total)),
    h('div', { class: 'tiles' }, cats),
    h('ol', null, c.checks.map(x => h('li', null, x.ok ? '✔ ' : '✖ ', x.desc, x.detail ? h('div', { class: 'muted' }, x.detail) : null))));
}

/* ---------------------------------------------------------------- Rahmen */
function current() { return (location.hash.replace(/^#\//, '') || 'dash'); }

function drawNav() {
  const nav = document.getElementById('nav'); nav.textContent = '';
  let lastG = null, lastSub = null;
  NAV.forEach(n => {
    if (n.id) { nav.append(link(n.id, n.l)); return; }
    if (n.g !== lastG) { nav.append(h('div', { class: 'grp' }, n.g)); lastG = n.g; lastSub = null; }
    if (n.sub && n.sub !== lastSub) { nav.append(h('div', { class: 'sub' }, n.sub)); lastSub = n.sub; }
    n.items.forEach(([id, l]) => nav.append(link(id, l)));
  });
}
const link = (id, l) => h('a', { href: '#/' + id, class: id === current() ? 'on' : '', 'data-view': id, 'aria-current': id === current() ? 'page' : null,
  onclick: ev => { if (id === current()) { ev.preventDefault(); refresh(); } } }, l);   // Klick auf die aktuelle Seite laedt sie neu

async function refresh() {
  const seq = refresh.seq = (refresh.seq || 0) + 1;      // nur die letzte Aktualisierung darf die Seite aendern
  const st = await api.state();
  if (seq !== refresh.seq) return;
  S = st;
  document.getElementById('host').textContent = S.wlc.hostname + ' · ' + S.wlc.ip + (S.standalone ? ' · läuft lokal im Browser' : '');
  drawNav();
  const id = VIEWS[current()] ? current() : 'dash';
  const box = h('div');                                   // erst im Hintergrund aufbauen, dann in einem Schritt einsetzen
  box.append(h('h1', null, TITLES[id]));
  await VIEWS[id](box);
  if (seq !== refresh.seq) return;
  const main = document.getElementById('main');
  main.textContent = '';
  main.append(...box.childNodes);
}

window.addEventListener('hashchange', refresh);
refresh();
