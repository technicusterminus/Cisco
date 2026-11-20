// Prueft die Zufallsgeneratoren des Rechentrainers: keine Ausnahmen, Antworten liegen in den Optionen,
// neue Aufgaben werden mit einer unabhaengigen Rechnung gegengeprueft. Start: node test_rechentrainer.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage(); const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.join(__dirname, 'encor-rechentrainer.html'));
  const r = await p.evaluate(() => {
    const bad = [], seen = {};
    for (const k of Object.keys(gens)) {
      seen[k] = 0;
      for (let i = 0; i < 3000; i++) {
        let t; try { t = gens[k].gen(); } catch (e) { bad.push(k + ' wirft: ' + e.message); continue; }
        seen[k]++;
        for (const f of t.fields) { const opts = f.sel || f.multi; if (opts && ![].concat(f.a).every(x => opts.includes(x))) bad.push(k + ': Antwort nicht in Optionen'); }
        const d = t.data;
        if (k === 'var') {
          const s = d.nb.find(x => x.succ); if (d.nb.some(x => x.fd < s.fd)) bad.push('var: Successor hat nicht die kleinste FD');
          const used = d.nb.filter(x => x === s || (x.rd < s.fd && x.fd < d.v * s.fd)).map(x => x.ip).sort().join();
          if (used !== d.used.slice().sort().join()) bad.push('var: genutzte Nachbarn weichen ab');
          let m = 1; while (!d.nb.filter(x => x.rd < s.fd).every(x => x.fd < m * s.fd)) m++;
          if (m !== d.minV) bad.push('var: kleinste variance weicht ab ' + m + ' ' + d.minV);
        }
        if (k === 'cost') {
          const c = x => Math.max(1, Math.floor(d.ref / x)); const sum = a => a.reduce((s, x) => s + c(x), 0);
          if (sum(d.A) !== d.ca || sum(d.B) !== d.cb) bad.push('cost: Summe weicht ab');
          if (d.win !== (d.ca < d.cb ? 'A' : d.cb < d.ca ? 'B' : 'beide (ECMP)')) bad.push('cost: Gewinner weicht ab');
        }
        if (k === 'hsrp') {
          if (d.mode === 0) { const o = d.rs.slice().sort((a, b) => b.pr - a.pr || b.o - a.o); if (o[0].nm !== d.active || o[1].nm !== d.standby) bad.push('hsrp0 weicht ab'); }
          if (d.mode === 1) { const tk = d.p2 > d.p1 && d.pe; if (d.active !== (tk ? 'R2' : 'R1')) bad.push('hsrp1 weicht ab'); }
          if (d.mode === 2) { const np = d.p1 - d.d; if (np !== d.np || d.active !== (np < d.p2 && d.pe ? 'R2' : 'R1')) bad.push('hsrp2 weicht ab'); }
        }
        if (k === 'stp' && !/Extended System ID/.test(t.steps)) bad.push('stp: Hinweis auf Extended System ID fehlt');
      }
    }
    // Hex-Eingabe mit und ohne 0x
    const f = { hex: true, a: '0x2E' };
    const hexOk = good(f, '0x2e') && good(f, '2e') && good(f, ' 2E ') && !good(f, '0x2f');
    return { seen, bad: bad.slice(0, 8), nbad: bad.length, hexOk };
  });
  console.log(JSON.stringify(r));
  const ok = !r.nbad && r.hexOk && !errs.length && Object.values(r.seen).every(n => n === 3000);
  console.log(ok ? 'Rechentrainer-Test bestanden.' : 'FEHLER', errs.join('; '));
  await b.close(); process.exit(ok ? 0 : 1);
})();
