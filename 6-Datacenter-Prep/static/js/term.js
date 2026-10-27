/* CLI-Fenster und API Inspector */
'use strict';

const Term = {
  win: null, node: 'apic1', hist: [], hpos: 0,

  prompt(node) { return (node || this.node) + '# '; },

  build(container, node, floating) {
    let cur = node || 'apic1';
    const out = h('pre', { class: 'term-out' }, (cur === 'apic1' ? 'Application Policy Infrastructure Controller (Datacenter Prep)\n' : 'Cisco NX-OS (ACI mode, Datacenter Prep)\n') + '"help" zeigt die Befehle, "ssh leaf101" wechselt zum Switch.\n\n');
    const pr = h('span', { class: 'term-pr' }, this.prompt(cur));
    const inp = h('input', { class: 'term-in', spellcheck: 'false', autocomplete: 'off' });
    const nodeSel = h('select', { class: 'term-node' });
    const fillNodes = () => {
      clear(nodeSel);
      nodeSel.appendChild(h('option', { value: 'apic1' }, 'apic1'));
      (App.state ? App.state.nodes : []).filter(n => n.state === 'active').sort((a, b) => a.id - b.id).forEach(n => nodeSel.appendChild(h('option', { value: n.name }, n.name)));
      nodeSel.value = cur;
    };
    fillNodes();
    const setNode = n => { cur = n; pr.textContent = this.prompt(cur); nodeSel.value = n; };
    nodeSel.onchange = () => { setNode(nodeSel.value); out.textContent += '\n--- ' + cur + ' ---\n'; out.scrollTop = out.scrollHeight; inp.focus(); };
    const run = async () => {
      const cmd = inp.value;
      inp.value = '';
      out.textContent += this.prompt(cur) + cmd + '\n';
      if (cmd.trim()) { this.hist.push(cmd); this.hpos = this.hist.length; }
      const m = /^\s*(?:ssh|attach)\s+(\S+)\s*$/.exec(cmd);
      if (m) {
        fillNodes();
        const ok = [...nodeSel.options].some(o => o.value === m[1]);
        if (ok) { setNode(m[1]); out.textContent += 'Verbunden mit ' + m[1] + '.\n'; } else out.textContent += 'ssh: ' + m[1] + ' nicht erreichbar\n';
      } else if (/^\s*(exit|logout)\s*$/.test(cmd)) {
        if (cur !== 'apic1') { setNode('apic1'); out.textContent += 'Verbindung beendet.\n'; } else if (floating) this.close();
      } else if (/^\s*clear\s*$/.test(cmd)) {
        out.textContent = '';
      } else if (cmd.trim()) {
        try {
          const r = await API.post('/sim/cli', { node: cur, cmd }, true);
          out.textContent += r.output + '\n';
        } catch (e) { out.textContent += 'Fehler: ' + (e.text || e.message) + '\n'; }
      }
      out.scrollTop = out.scrollHeight;
    };
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') run();
      else if (e.key === 'ArrowUp') { if (this.hpos > 0) { this.hpos--; inp.value = this.hist[this.hpos]; } e.preventDefault(); }
      else if (e.key === 'ArrowDown') { if (this.hpos < this.hist.length) { this.hpos++; inp.value = this.hist[this.hpos] || ''; } e.preventDefault(); }
    });
    const el = h('div', { class: 'term' + (floating ? ' floating' : '') },
      h('div', { class: 'term-bar' }, h('span', null, 'CLI'), nodeSel, h('span', { class: 'grow' }), floating ? h('button', { class: 'x', onclick: () => this.close() }, '×') : null),
      out, h('div', { class: 'term-line', onclick: () => inp.focus() }, pr, inp));
    container.appendChild(el);
    out.addEventListener('mouseup', () => { if (!window.getSelection().toString()) inp.focus(); });
    setTimeout(() => inp.focus(), 30);
    return el;
  },

  open(node) {
    this.close();
    this.win = this.build(document.body, node || 'apic1', true);
    const bar = this.win.querySelector('.term-bar');
    let dx = 0, dy = 0, drag = false;
    bar.addEventListener('mousedown', e => { if (e.target.tagName === 'SELECT' || e.target.tagName === 'BUTTON') return; drag = true; const r = this.win.getBoundingClientRect(); dx = e.clientX - r.left; dy = e.clientY - r.top; e.preventDefault(); });
    window.addEventListener('mousemove', e => { if (!drag || !this.win) return; this.win.style.left = (e.clientX - dx) + 'px'; this.win.style.top = (e.clientY - dy) + 'px'; this.win.style.right = 'auto'; this.win.style.bottom = 'auto'; });
    window.addEventListener('mouseup', () => { drag = false; });
  },

  embed(container, node) { this.build(container, node, false); },

  close() { if (this.win) { this.win.remove(); this.win = null; } },
};

const Inspector = {
  el: null, list: null, onlyWrite: false, filter: '',
  init() {
    API.onLog = e => { if (this.el && this.el.classList.contains('open')) this.add(e); };
  },
  toggle() {
    if (!this.el) this.build();
    this.el.classList.toggle('open');
    if (this.el.classList.contains('open')) this.render();
  },
  build() {
    this.list = h('div', { class: 'insp-list' });
    const only = h('input', { type: 'checkbox', onchange: () => { this.onlyWrite = only.checked; this.render(); } });
    const search = h('input', { placeholder: 'Filter (URL enthält …)', oninput: () => { this.filter = search.value; this.render(); } });
    this.el = h('div', { class: 'inspector' },
      h('div', { class: 'insp-bar' }, h('b', null, 'API Inspector'), h('label', { class: 'check' }, only, h('span', null, 'nur POST/DELETE')), search,
        h('button', { class: 'btn small', onclick: () => { API.log = []; this.render(); } }, 'Leeren'),
        h('span', { class: 'grow' }), h('button', { class: 'x', onclick: () => this.toggle() }, '×')),
      this.list);
    document.body.appendChild(this.el);
  },
  match(e) { return (!this.onlyWrite || e.method !== 'GET') && (!this.filter || e.url.includes(this.filter)) && e.url.startsWith('/api/'); },
  render() { clear(this.list); API.log.filter(e => this.match(e)).forEach(e => this.add(e, true)); this.list.scrollTop = this.list.scrollHeight; },
  add(e, bulk) {
    if (!this.match(e)) return;
    const pretty = v => { try { return JSON.stringify(v); } catch (x) { return String(v); } };
    const resp = pretty(e.resp);
    this.list.appendChild(h('div', { class: 'insp-e ' + e.method.toLowerCase() },
      h('div', { class: 'insp-h' }, '[' + e.ts.toLocaleTimeString('de-DE') + '] ', h('b', null, 'method: ' + e.method), '  ', e.status, '  ', e.ms + ' ms'),
      h('div', null, 'url: ' + location.origin + e.url),
      e.body !== undefined ? h('div', { class: 'insp-p' }, 'payload' + pretty(e.body)) : null,
      h('div', { class: 'insp-r' }, 'response: ' + (resp.length > 1500 ? resp.slice(0, 1500) + ' … (' + resp.length + ' Zeichen)' : resp))));
    if (!bulk) this.list.scrollTop = this.list.scrollHeight;
  },
};
