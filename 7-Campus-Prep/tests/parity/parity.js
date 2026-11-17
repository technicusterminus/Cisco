/* Paritaetstest: static/engine.js (Browser-Engine) muss sich exakt wie die Python-Engine verhalten.

   Aufruf:  node tests/parity/parity.js [fixtures.json]
   Ohne Argument erzeugt der Test die Erwartungen selbst mit tests/parity/make_fixtures.py (Python 3 noetig). Jeder Schritt (HTTP-
   Methode, Pfad, Body) wird gegen die JS-Engine abgespielt; Status und Antwort muessen gleich sein, ebenso der Endzustand und
   der Lab-Fortschritt. Danach folgen Tests der Persistenz-Randfaelle, die sich ueber die HTTP-Schnittstelle nicht erzeugen lassen. */
'use strict';
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const assert = require('assert');
const E = require('../../static/engine.js');

const ROOT = path.resolve(__dirname, '..', '..');
const labsDir = path.join(ROOT, 'labs');
const labs = fs.readdirSync(labsDir).filter(f => f.endsWith('.json')).sort().map(f => JSON.parse(fs.readFileSync(path.join(labsDir, f), 'utf-8')));

let fixturesPath = process.argv[2];
let tmpDir = null;
if (!fixturesPath) {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-parity-'));
  fixturesPath = path.join(tmpDir, 'fixtures.json');
  const r = spawnSync(process.env.PYTHON || 'python3', [path.join(__dirname, 'make_fixtures.py'), fixturesPath], { cwd: ROOT, encoding: 'utf-8' });
  if (r.status !== 0) { console.error('Erzeugen der Erwartungen fehlgeschlagen:\n' + r.stderr); process.exit(2); }
}
const fixtures = JSON.parse(fs.readFileSync(fixturesPath, 'utf-8'));

const canon = x => {
  if (Array.isArray(x)) return x.map(canon);
  if (x && typeof x === 'object') { const o = {}; for (const k of Object.keys(x).sort()) o[k] = canon(x[k]); return o; }
  return x;
};
const norm = x => { const c = JSON.parse(JSON.stringify(x === undefined ? null : x)); return canon(c); };
const stripStandalone = x => { if (x && typeof x === 'object') { if (!Array.isArray(x)) delete x.standalone; Object.values(x).forEach(stripStandalone); } return x; };

function firstDiff(a, b, p) {
  if (JSON.stringify(a) === JSON.stringify(b)) return null;
  if (a && b && typeof a === 'object' && typeof b === 'object' && Array.isArray(a) === Array.isArray(b)) {
    for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) { const d = firstDiff(a[k], b[k], p + '.' + k); if (d) return d; }
  }
  return p + ': erwartet (Python) ' + JSON.stringify(a) + ' / erhalten (JS) ' + JSON.stringify(b);
}

let fails = 0, steps = 0;
for (const sc of fixtures.scenarios) {
  const sim = E.createSim({ labs, storage: sc.persistent ? E.memoryStorage() : null });
  let bad = null;
  for (const [i, st] of sc.steps.entries()) {
    steps++;
    const r = sim.handle(st.m, st.p, st.b);
    const got = { status: r.status, resp: stripStandalone(norm(r.body)) };
    const want = { status: st.status, resp: stripStandalone(norm(st.resp)) };
    const d = firstDiff(want, got, '');
    if (d) { bad = 'Schritt ' + (i + 1) + ' (' + st.m + ' ' + st.p + (st.b !== undefined ? ' ' + JSON.stringify(st.b).slice(0, 120) : '') + '): ' + d; break; }
  }
  if (!bad) {
    const d1 = firstDiff(norm(sc.snapshot), norm(sim.snapshotAll()), 'snapshot');
    const d2 = firstDiff(norm(sc.progress), norm(sim.labs.progress), 'progress');
    bad = d1 || d2;
  }
  if (bad) { fails++; console.log('  FEHLER ' + sc.name + '\n         ' + bad.slice(0, 600)); } else console.log('  ok   ' + sc.name);
}
console.log('\n' + fixtures.scenarios.length + ' Szenarien, ' + steps + ' Schritte, ' + fails + ' Abweichungen\n');

// ---------------------------------------------------------------------------------------------------------------
// Persistenz-Randfaelle (Gegenstuecke zu tests/test_persist.py)
const T = [];
const test = (name, fn) => T.push([name, fn]);
const solution = id => labs.find(l => l.id === id).solutionCommands;
const fresh = storage => E.createSim({ labs, storage });
const KEY = 'campusprep:';

test('Roundtrip von Konfiguration, Welt, Lab-Sitzung und Fortschritt ueber einen Neustart', () => {
  const st = E.memoryStorage();
  const s = fresh(st);
  s.labs.start('05-gast-wlan-lobby', 'guided'); s.apply(solution('05-gast-wlan-lobby')); s.labs.hint(); s.labs.answer('q1', 1);
  assert.ok(s.labs.check().passed); s.persist();
  const s2 = fresh(st);
  assert.deepStrictEqual(norm(s2.wlc.state()), norm(s.wlc.state()));
  assert.deepStrictEqual(norm(s2.world), norm(s.world));
  assert.deepStrictEqual(norm(s2.labs.session), norm(s.labs.session));
  assert.deepStrictEqual(norm(s2.labs.progress), norm(s.labs.progress));
  assert.ok(s2.labs.check().passed);
});
test('Keine Zeitstempel: ein zweiter, unabhaengiger Lauf schreibt dieselben Bytes', () => {
  const a = E.memoryStorage(), b = E.memoryStorage();
  for (const st of [a, b]) { const s = fresh(st); s.apply(['wlan P 1 Corp']); s.persist(); }
  assert.strictEqual(a.get(KEY + 'state'), b.get(KEY + 'state'));
});
test('Defekte und fremde Staende werden nicht geladen, sondern als *.bad aufgehoben', () => {
  for (const content of ['das ist kein json', JSON.stringify({ kind: 'anderes', version: 1 }), JSON.stringify({ kind: 'campusprep-state', version: 99, world: {}, wlc: {} })]) {
    const st = E.memoryStorage(); st.set(KEY + 'state', content);
    const s = fresh(st);
    assert.strictEqual(s.wlc.wlans.size, 0);
    assert.strictEqual(st.get(KEY + 'state.bad'), content);
    assert.strictEqual(st.get(KEY + 'state'), null);
  }
});
test('Strukturell kaputte Konfiguration wird aufgehoben', () => {
  const st = E.memoryStorage(); const s = fresh(st);
  s.apply(['wlan P 1 Corp']);
  const d = s.snapshotAll(); delete d.wlc.wlans.P.ssid;
  st.set(KEY + 'state', JSON.stringify(d));
  assert.strictEqual(fresh(st).wlc.wlans.size, 0);
  assert.ok(st.get(KEY + 'state.bad'));
});
test('Ein fehlgeschlagenes Laden laesst die laufende Sim unveraendert', () => {
  const s = fresh(E.memoryStorage());
  s.labs.start('01-ssid-nicht-sichtbar');
  const before = [norm(s.snapshotAll()), norm(s.wlc.state())];
  const bad = s.snapshotAll(); delete bad.wlc.wlans.Corp_Profile.ssid;
  assert.throws(() => s.restoreAll(bad), E.StoreError);
  assert.throws(() => s.restoreAll({ kind: 'x' }), E.StoreError);
  assert.deepStrictEqual([norm(s.snapshotAll()), norm(s.wlc.state())], before);
});
test('Die Lab-Sitzung aus einem Stand wird bereinigt', () => {
  const s = fresh(E.memoryStorage());
  s.labs.start('01-ssid-nicht-sichtbar');
  const d = s.snapshotAll();
  d.lab.hints = 99; d.lab.answers = { q1: 0, q2: 42, nix: 1 };
  s.restoreAll(d);
  assert.strictEqual(s.labs.session.hints, 4);
  assert.deepStrictEqual(norm(s.labs.session.answers), { q1: 0 });
  d.lab = { id: '99-unbekannt', mode: 'guided' };
  s.restoreAll(d);
  assert.strictEqual(s.labs.session, null);
});
test('Staende der Version 1 (ohne Flex Profiles und Site Tags) und alter Fortschritt bleiben ladbar', () => {
  const st = E.memoryStorage(); const s = fresh(st);
  s.labs.start('01-ssid-nicht-sichtbar'); s.apply(solution('01-ssid-nicht-sichtbar')); s.labs.check();
  const d = s.snapshotAll(); d.version = 1; delete d.wlc.flexProfiles; delete d.wlc.siteTags;
  st.set(KEY + 'state', JSON.stringify(d));
  st.set(KEY + 'progress', JSON.stringify({ kind: 'campusprep-progress', version: 1, labs: s.labs.progress }));
  const s2 = fresh(st);
  assert.deepStrictEqual(s2.wlc.state().siteTags.map(t => t.name), ['default-site-tag']);
  assert.deepStrictEqual(s2.wlc.state().flexProfiles.map(t => t.name), ['default-flex-profile']);
  assert.ok(s2.labs.check().passed);
  assert.ok(s2.labs.progress['01-ssid-nicht-sichtbar'].guidedPassed);
  assert.strictEqual(st.get(KEY + 'state.bad'), null);
});
test('Beschaedigter Fortschritt wird aufgehoben', () => {
  const st = E.memoryStorage(); st.set(KEY + 'progress', '[1,2');
  const s = fresh(st);
  assert.deepStrictEqual(norm(s.labs.progress), {});
  assert.strictEqual(st.get(KEY + 'progress.bad'), '[1,2');
});
test('Benannte Staende: kaputte Eintraege werden gemeldet und lassen sich nicht laden', () => {
  const st = E.memoryStorage(); const s = fresh(st);
  st.set(KEY + 'saves:kaputt', '{');
  assert.deepStrictEqual(norm(s.store.listNamed()), [{ name: 'kaputt', lab: null, wlans: 0, broken: true }]);
  assert.throws(() => s.store.loadNamed('kaputt'), /nicht lesbar/);
  assert.throws(() => s.store.loadNamed('gibtsnicht'), e => e.status === 404);
});
test('localStorage ist optional: ohne Speicher gibt es keine Staende, die Engine laeuft weiter', () => {
  const s = fresh(null);
  assert.strictEqual(s.handle('GET', '/wlc/api/saves').status, 409);
  assert.strictEqual(s.handle('POST', '/wlc/cli', { command: '' }).status, 200);
});

let jsFails = 0;
for (const [name, fn] of T) {
  try { fn(); console.log('  ok   ' + name); } catch (e) { jsFails++; console.log('  FEHLER ' + name + '\n         ' + String(e.message).split('\n')[0]); }
}
if (tmpDir) fs.rmSync(tmpDir, { recursive: true, force: true });
const total = fails + jsFails;
console.log('\n' + (total ? total + ' Fehler' : 'Paritaet und Persistenz bestanden.'));
process.exit(total ? 1 : 0);
