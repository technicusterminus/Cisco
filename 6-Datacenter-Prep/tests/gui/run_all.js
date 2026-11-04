/* Alle GUI-Tests nacheinander mit Bericht.
   Aufruf: node tests/gui/run_all.js   (braucht Node.js und Playwright mit Chromium; ohne Playwright werden die Tests übersprungen) */
'use strict';
const { spawnSync } = require('child_process');
const path = require('path');

const TESTS = ['smoke.js', 'acceptance.js', 'troubleshooting.js'];
const rows = [];
for (const t of TESTS) {
  const t0 = Date.now();
  const r = spawnSync(process.execPath, [path.join(__dirname, t)], { encoding: 'utf8' });
  const out = (r.stdout || '') + (r.stderr || '');
  const lines = out.split('\n');
  const ok = lines.filter(l => l.startsWith('  ok')).length;
  const bad = lines.filter(l => l.startsWith('  FEHLER')).map(l => l.replace(/^\s*FEHLER\s*/, ''));
  const skipped = /übersprungen/.test(out);
  rows.push({ t, code: r.status, ok, bad, skipped, s: ((Date.now() - t0) / 1000).toFixed(1), last: lines.filter(Boolean).slice(-1)[0] || '' });
}
console.log('\nGUI-Tests');
console.log('-'.repeat(72));
for (const r of rows) {
  const st = r.skipped ? 'ÜBERSPRUNGEN' : r.code === 0 ? 'BESTANDEN' : 'FEHLGESCHLAGEN';
  console.log('%s %s %d Prüfungen ok, %d Fehler, %s s', r.t.padEnd(22), st.padEnd(15), r.ok, r.bad.length, r.s);
  r.bad.forEach(b => console.log('    - ' + b));
  if (r.code !== 0 && !r.bad.length) console.log('    ' + r.last);
}
console.log('-'.repeat(72));
const failed = rows.filter(r => r.code !== 0);
console.log(failed.length ? failed.length + ' von ' + rows.length + ' GUI-Tests fehlgeschlagen.' : 'Alle ' + rows.length + ' GUI-Tests bestanden.');
process.exit(failed.length ? 1 : 0);
