/* REST-Client mit API Inspector und lokalem MIT-Cache */
'use strict';

class ApiError extends Error {
  constructor(code, text) { super(text); this.code = code; this.text = text; }
}

const enc = dn => dn.split('').map(c => /[A-Za-z0-9_\-.\/:]/.test(c) ? c : encodeURIComponent(c)).join('');

const API = {
  log: [],
  onLog: null,
  onAuthLost: null,
  record(e) {
    this.log.push(e);
    if (this.log.length > 400) this.log.shift();
    if (this.onLog) this.onLog(e);
  },
  async req(method, url, body, quiet) {
    const t0 = performance.now();
    const opt = { method, credentials: 'same-origin', headers: {} };
    if (body !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    let r, j = null;
    try {
      r = await fetch(url, opt);
      const txt = await r.text();
      try { j = txt ? JSON.parse(txt) : null; } catch (e) { j = txt; }
    } catch (e) {
      throw new ApiError('net', 'Keine Verbindung zum Simulator (' + e.message + ')');
    }
    if (!quiet) this.record({ ts: new Date(), method, url, body, status: r.status, resp: j, ms: Math.round(performance.now() - t0) });
    if (r.status === 401 && j && j.imdata && j.imdata[0] && j.imdata[0].error && j.imdata[0].error.attributes.code === 'DCP-NOUSER' && typeof Launcher !== 'undefined') Launcher.show('Bitte anmelden.');
    if (r.status === 403 && this.onAuthLost && !url.includes('aaaLogin')) this.onAuthLost();
    if (!r.ok) {
      const e = j && j.imdata && j.imdata[0] && j.imdata[0].error;
      throw new ApiError(e ? e.attributes.code : r.status, e ? e.attributes.text : (r.statusText || 'Fehler'));
    }
    return j;
  },
  get(url, quiet) { return this.req('GET', url, undefined, quiet); },
  post(url, body, quiet) { return this.req('POST', url, body, quiet); },
  del(url) { return this.req('DELETE', url); },
  async mo(dn, q) { return (await this.get('/api/node/mo/' + enc(dn) + '.json' + (q ? '?' + q : ''))).imdata; },
  async cls(c, q, quiet) { return (await this.get('/api/node/class/' + c + '.json' + (q ? '?' + q : ''), quiet)).imdata; },
  postMo(dn, body) { return this.post('/api/node/mo/' + enc(dn) + '.json', body); },
  delMo(dn) { return this.del('/api/node/mo/' + enc(dn) + '.json'); },
  sim(path, body) { return body === undefined ? this.get('/sim/' + path, true) : this.post('/sim/' + path, body); },
};

/* Lokaler Cache der MIT-Objekte (dn -> {cls, a, kids}) */
const MIT = {
  objs: new Map(),
  meta: {},
  get(dn) { return this.objs.get(dn); },
  a(dn) { const o = this.objs.get(dn); return o ? o.a : null; },
  ingest(item, parent) {
    const cls = Object.keys(item)[0];
    const body = item[cls];
    const a = body.attributes;
    const dn = a.dn || (parent ? parent + '/' + a.rn : a.rn);
    a.dn = dn;
    const prev = this.objs.get(dn);
    const o = { cls, a, kids: [] };
    this.objs.set(dn, o);
    if (parent && this.objs.has(parent)) {
      const p = this.objs.get(parent);
      if (!p.kids.includes(dn)) p.kids.push(dn);
    }
    (body.children || []).forEach(ch => {
      const cc = Object.keys(ch)[0];
      if (cc === 'moCount' || cc === 'healthInst') return;
      const cdn = this.ingest(ch, dn);
      if (!o.kids.includes(cdn)) o.kids.push(cdn);
    });
    if (prev && !body.children) o.kids = prev.kids.filter(k => this.objs.has(k));
    return dn;
  },
  drop(dn) {
    const o = this.objs.get(dn);
    if (!o) return;
    o.kids.forEach(k => this.drop(k));
    this.objs.delete(dn);
  },
  async load(dn) {
    const res = await API.mo(dn, 'rsp-subtree=full&rsp-subtree-include=faults');
    this.drop(dn);
    res.forEach(r => this.ingest(r, parentDn(dn)));
    const p = this.objs.get(parentDn(dn));
    if (p && !p.kids.includes(dn) && res.length) p.kids.push(dn);
    return this.objs.get(dn);
  },
  async loadClass(c, q) {
    const res = await API.cls(c, q || '');
    res.forEach(r => this.ingest(r, null));
    return res.map(r => Object.values(r)[0].attributes.dn);
  },
  kids(dn, classes) {
    const o = this.objs.get(dn);
    if (!o) return [];
    return o.kids.filter(k => this.objs.has(k) && (!classes || classes.includes(this.objs.get(k).cls)));
  },
  ofClass(c, prefix) {
    const out = [];
    this.objs.forEach((o, dn) => { if (o.cls === c && (!prefix || dn.startsWith(prefix))) out.push(dn); });
    return out.sort();
  },
  faults(dn, deep) {
    const out = [];
    const walk = d => {
      this.kids(d).forEach(k => {
        const o = this.objs.get(k);
        if (o.cls === 'faultInst') out.push(o.a);
        else if (deep) walk(k);
      });
    };
    walk(dn);
    return out;
  },
};

function splitDn(dn) {
  const parts = []; let buf = ''; let depth = 0;
  for (const ch of dn) {
    if (ch === '[') depth++;
    else if (ch === ']') depth--;
    if (ch === '/' && depth === 0) { parts.push(buf); buf = ''; } else buf += ch;
  }
  if (buf) parts.push(buf);
  return parts;
}
function parentDn(dn) { return splitDn(dn).slice(0, -1).join('/'); }
function rnOf(dn) { const p = splitDn(dn); return p[p.length - 1] || ''; }
function tenantOf(dn) { const p = splitDn(dn); return p[0] === 'uni' && p[1] && p[1].startsWith('tn-') ? 'uni/' + p[1] : null; }
function makeRn(cls, attrs) {
  const m = MIT.meta[cls];
  return m.rn.replace(/\{(\w+)\}/g, (_, k) => attrs[k]);
}
function POD(id) { const n = id && App.state && (App.state.nodes || []).find(x => String(x.id) === String(id)); return (n && n.pod) || (App.state && App.state.pod) || 1; }
