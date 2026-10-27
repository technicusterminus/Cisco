/* DOM-Helfer, Dialoge, Tabellen, Formulare */
'use strict';

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (k === 'html') el.innerHTML = v;
      else if (k === 'value') el.value = v;
      else if (k === 'checked') el.checked = !!v;
      else el.setAttribute(k, v === true ? '' : v);
    }
  }
  kids.flat(Infinity).forEach(c => {
    if (c === null || c === undefined || c === false) return;
    el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  });
  return el;
}

function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }

function toast(msg, kind) {
  const t = h('div', { class: 'toast ' + (kind || 'ok') }, msg);
  document.getElementById('toasts').appendChild(t);
  setTimeout(() => t.classList.add('gone'), kind === 'err' ? 7000 : 3500);
  setTimeout(() => t.remove(), kind === 'err' ? 7600 : 4100);
}

function errToast(e) { toast((e.code && e.code !== 'net' ? 'Fehler ' + e.code + ': ' : '') + (e.text || e.message), 'err'); }

/* Modaler Dialog. buttons: [{l, primary, fn(close) -> Promise|false}] */
function modal(title, body, buttons, opts) {
  opts = opts || {};
  const back = h('div', { class: 'modal-back' });
  const err = h('div', { class: 'modal-err' });
  const close = () => back.remove();
  const foot = h('div', { class: 'modal-foot' });
  (buttons || [{ l: 'Schließen' }]).forEach(b => {
    const btn = h('button', { class: 'btn ' + (b.primary ? 'primary ' : '') + (b.cls || '') }, b.l);
    btn.onclick = async () => {
      if (!b.fn) return close();
      err.textContent = '';
      btn.disabled = true;
      try {
        const r = await b.fn(close);
        if (r !== false) close();
      } catch (e) {
        err.textContent = (e.code ? 'Fehler ' + e.code + ': ' : '') + (e.text || e.message);
      } finally { btn.disabled = false; }
    };
    foot.appendChild(btn);
  });
  const box = h('div', { class: 'modal' + (opts.wide ? ' wide' : '') },
    h('div', { class: 'modal-head' }, h('span', null, title), h('button', { class: 'x', onclick: close, title: 'Schließen' }, '×')),
    h('div', { class: 'modal-body' }, body), err, foot);
  back.appendChild(box);
  back.addEventListener('mousedown', ev => { if (ev.target === back && !opts.sticky) close(); });
  document.body.appendChild(back);
  const first = box.querySelector('input:not([disabled]),select:not([disabled])');
  if (first) first.focus();
  box.addEventListener('keydown', ev => {
    if (ev.key === 'Enter' && ev.target.tagName === 'INPUT' && buttons) {
      const p = [...foot.querySelectorAll('.btn.primary')].pop();
      if (p) p.click();
    }
    if (ev.key === 'Escape') close();
  });
  return { close, box, err };
}

function confirmBox(text, fn) {
  modal('Bestätigen', h('p', null, text), [{ l: 'Abbrechen' }, { l: 'Ja, ausführen', primary: true, fn }]);
}

/* Tabelle: cols=[{l, f(row)}], rows=[...], opts {onRow, actions(row) -> [el], empty} */
function table(cols, rows, opts) {
  opts = opts || {};
  const thead = h('thead', null, h('tr', null, cols.map(c => h('th', { style: c.w ? { width: c.w } : null }, c.l)),
    opts.actions ? h('th', { class: 'act' }) : null));
  const tbody = h('tbody');
  if (!rows.length) {
    tbody.appendChild(h('tr', null, h('td', { colspan: cols.length + (opts.actions ? 1 : 0), class: 'empty' },
      opts.empty || 'Keine Einträge')));
  }
  rows.forEach(r => {
    const tr = h('tr', { class: opts.onRow ? 'click' : '' }, cols.map(c => {
      const v = c.f(r);
      return h('td', null, v instanceof Node ? v : (v === undefined || v === null || v === '' ? '—' : String(v)));
    }), opts.actions ? h('td', { class: 'act' }, opts.actions(r)) : null);
    if (opts.onRow) tr.addEventListener('click', ev => { if (!ev.target.closest('.act')) opts.onRow(r); });
    tbody.appendChild(tr);
  });
  return h('div', { class: 'tablewrap' }, h('table', { class: 'grid' }, thead, tbody));
}

function sevBadge(sev) {
  return h('span', { class: 'sev ' + sev }, { critical: 'Critical', major: 'Major', minor: 'Minor', warning: 'Warning', cleared: 'Cleared' }[sev] || sev);
}

function stateBadge(state) {
  const cls = { formed: 'ok', 'missing-target': 'bad', active: 'ok', discovering: 'warn', inactive: 'bad', pending: 'warn',
    undiscovered: 'off', up: 'ok', down: 'bad', FULL: 'ok', Established: 'ok', learned: 'ok', online: 'ok', offline: 'bad', silent: 'warn' }[state] || 'off';
  return h('span', { class: 'pill ' + cls }, state || '—');
}

function healthBadge(score) {
  const s = score === undefined || score === null ? 100 : Number(score);
  return h('span', { class: 'health ' + (s >= 90 ? 'ok' : s >= 70 ? 'warn' : 'bad') }, String(s));
}

function iconBtn(sym, title, fn, cls) {
  return h('button', { class: 'ibtn ' + (cls || ''), title, onclick: ev => { ev.stopPropagation(); fn(ev); } }, sym);
}

function download(name, text) {
  const a = h('a', { href: URL.createObjectURL(new Blob([text], { type: 'application/json' })), download: name });
  document.body.appendChild(a); a.click(); a.remove();
}

function pickFile() {
  return new Promise(res => {
    const i = h('input', { type: 'file', accept: '.json,application/json', style: { display: 'none' } });
    i.onchange = () => { const f = i.files[0]; if (!f) return res(null); const r = new FileReader(); r.onload = () => res(r.result); r.readAsText(f); };
    document.body.appendChild(i); i.click(); setTimeout(() => i.remove(), 60000);
  });
}

function fmtTs(ts) {
  if (!ts || ts === 'never') return '—';
  const d = new Date(ts);
  return isNaN(d) ? ts : d.toLocaleString('de-DE');
}
