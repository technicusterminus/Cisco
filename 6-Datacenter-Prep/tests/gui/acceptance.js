/* End-to-End-Abnahmefall im Browser (Lab 32, HTTPS mit Least Privilege):
   Lab starten -> Traffic Inspector zeigt DROP mit Policy-Ursache -> Contract anlegen -> ALLOW, SSH bleibt DROP ->
   Bewertung bestanden -> Neuladen behält den Stand -> Reset stellt den Ausgangszustand her -> Prüfungsmodus ohne Hinweise.
   Die Konfiguration schickt der Test als REST-POST aus der Seite (derselbe Aufruf, den die Formulare senden);
   die Wizards selbst deckt dieser Test nicht ab.
   Aufruf: node tests/gui/acceptance.js   (braucht Node.js und Playwright mit Chromium) */
'use strict';
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const net = require('net');

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { console.log('Playwright nicht installiert – GUI-Test übersprungen.'); process.exit(0); }

const ROOT = path.resolve(__dirname, '..', '..');
const freePort = () => new Promise(res => { const s = net.createServer(); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); }); });
const fails = [];
const check = (ok, msg) => { console.log((ok ? '  ok   ' : '  FEHLER ') + msg); if (!ok) fails.push(msg); };
const SHOTS = process.env.SHOTS;

const SOLUTION = { fvTenant: { attributes: { name: 'Shop' }, children: [
  { vzFilter: { attributes: { name: 'https' }, children: [{ vzEntry: { attributes: { name: 'https', etherT: 'ip', prot: 'tcp', dFromPort: '443', dToPort: '443' } } }] } },
  { vzBrCP: { attributes: { name: 'web-to-app-https', scope: 'context' }, children: [{ vzSubj: { attributes: { name: 's', revFltPorts: 'yes' }, children: [{ vzRsSubjFiltAtt: { attributes: { tnVzFilterName: 'https' } } }] } }] } },
  { fvAp: { attributes: { name: 'Webshop' }, children: [
    { fvAEPg: { attributes: { name: 'Web' }, children: [{ fvRsCons: { attributes: { tnVzBrCPName: 'web-to-app-https' } } }] } },
    { fvAEPg: { attributes: { name: 'App' }, children: [{ fvRsProv: { attributes: { tnVzBrCPName: 'web-to-app-https' } } }] } }] } }] } };

(async () => {
  const port = await freePort();
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'dcprep-e2e-'));
  const srv = spawn(process.env.PYTHON || 'python3', ['start.py', '--port', String(port), '--no-browser', '--data', data, '--discovery', '0.05'], { cwd: ROOT, stdio: 'ignore' });
  const U = 'http://127.0.0.1:' + port + '/';
  for (let i = 0; i < 50; i++) { try { await fetch(U + 'dp/me'); break; } catch (e) { await new Promise(r => setTimeout(r, 200)); } }
  const b = await chromium.launch();
  const errs = [];
  try {
    const p = await (await b.newContext({ viewport: { width: 1400, height: 950 } })).newPage();
    p.on('pageerror', e => errs.push(e.message));
    const shot = async n => { if (SHOTS) await p.screenshot({ path: path.join(SHOTS, n + '.png'), fullPage: false }); };
    const L = id => p.locator('.labrow').filter({ has: p.locator('.labrow-t > b', { hasText: new RegExp('^' + id + ' ') }) }).first();
    const trafficTest = async (dst, proto, port_) => {
      await p.evaluate(() => App.go('ops', 'vis')); await p.waitForSelector('.traffic select');
      const sel = p.locator('.traffic select');
      await sel.nth(0).selectOption('web1'); await sel.nth(1).selectOption(dst); await sel.nth(2).selectOption(proto);
      await p.fill('.traffic input[placeholder=Port]', String(port_ || ''));
      await p.click('.traffic button:has-text("Start")'); await p.waitForSelector('.trace .verdict');
      return p.textContent('.trace');
    };
    const labCheck = async () => {
      await p.evaluate(() => App.go('sim', 'labs')); await p.waitForSelector('.card.lab');
      await p.click('.card.lab button:has-text("Lab prüfen")'); await p.waitForSelector('.card.lab .trace .verdict');
      return p.textContent('.card.lab .trace');
    };

    await p.goto(U); await p.waitForSelector('.ucards');
    await p.click('.ucard:has-text("standard")'); await p.waitForSelector('.login-who');
    await p.fill('input[type=password]', 'admin'); await p.click('text=Login'); await p.waitForSelector('.tabs');

    // 1. Lab im geführten Modus starten
    await p.evaluate(() => App.go('sim', 'labs')); await p.waitForSelector('.lablist');
    await L('32').locator('.labrow-act button:has-text("Starten")').click(); await p.waitForSelector('.modal select');
    await p.selectOption('.modal select', 'guided'); await p.click('.modal .btn.primary'); await p.waitForSelector('.card.lab');
    const card = await p.innerText('.card.lab');  // nur sichtbarer Text (die Lösung ist eingeklappt)
    check(card.includes('Anforderungen') && card.includes('Geführter Modus'), 'Lab 32 im geführten Modus gestartet, Anforderungen sichtbar');
    check(!/web-to-app-https|Reverse Filter|tcp\/443 als Filter/.test(card), 'Aufgabentext verrät die Lösung nicht');
    await p.click('.card.lab button:has-text("Hinweis anzeigen")'); await p.waitForTimeout(400);
    check((await p.textContent('.card.lab')).includes('Implicit Deny'), 'Hinweis Stufe 1 (Konzept) wird angezeigt');
    await shot('01-lab');

    // 2. Ausgangszustand: HTTPS scheitert an der Policy
    let t = await trafficTest('app1', 'tcp', 443);
    check(t.includes('DROP') && t.includes('POLICY_IMPLICIT_DENY'), 'HTTPS web1 → app1: DROP mit POLICY_IMPLICIT_DENY');
    check(t.includes('Policy verwirft') && t.includes('Nächster Diagnoseschritt'), 'Fehlerort und Diagnosehinweis sichtbar');
    check(/Gateway 10\.10\.10\.1/.test(t) && /Routing in VRF/.test(t), 'Gateway und Routing als erfolgreich ausgewiesen');
    await shot('02-drop');

    // 3. Filter, Contract, Consumer/Provider anlegen (REST wie die Formulare)
    await p.evaluate(async body => { await API.postMo('uni/tn-Shop', body); }, SOLUTION);
    t = await trafficTest('app1', 'tcp', 443);
    check(t.includes('ALLOW') && t.includes('web-to-app-https') && t.includes('Provider → Consumer'), 'HTTPS: ALLOW, Hin- und Rückweg mit angewandter Regel');
    await shot('03-allow');
    t = await trafficTest('app1', 'tcp', 22);
    check(t.includes('DROP') && t.includes('POLICY_IMPLICIT_DENY'), 'SSH bleibt blockiert');

    // 4. Bewertung
    let r = await labCheck();
    check(r.includes('bestanden') && r.includes('7 von 7') && r.includes('Sicherheit / Least Privilege'), 'Lab bestanden: 7 von 7, Funktion und Sicherheit getrennt');
    await shot('04-bestanden');

    // 5. Neuladen behält Stand und Fortschritt
    await p.reload(); await p.waitForSelector('.tabs');
    r = await labCheck();
    check(r.includes('7 von 7'), 'Nach dem Neuladen weiterhin bestanden');

    // 6. Reset
    await p.click('.card.lab button:has-text("Auf Default")'); await p.waitForSelector('.modal');
    await p.click('.modal .btn.primary'); await p.waitForTimeout(1500);
    r = await labCheck();
    check(r.includes('noch nicht bestanden'), 'Reset: Ausgangszustand, Lab nicht bestanden');
    t = await trafficTest('app1', 'tcp', 443);
    check(t.includes('POLICY_IMPLICIT_DENY'), 'Reset: HTTPS wieder blockiert');
    await p.evaluate(() => App.go('sim', 'labs')); await p.waitForSelector('.lablist');
    check((await L('32').textContent()).includes('aktiv'), 'Lab bleibt aktiv');

    // 7. Prüfungsmodus
    await p.click('.card.lab button:has-text("Auf Default")'); await p.waitForSelector('.modal');
    await p.click('.modal .btn:has-text("Abbrechen")');
    await p.evaluate(async () => { await API.sim('labs/op', { op: 'reset', id: '32-https-least-privilege', mode: 'exam' }); await App.refreshState(); App.go('sim', 'labs'); });
    await p.waitForSelector('.card.lab'); await p.waitForTimeout(300);
    const ex = await p.textContent('.card.lab');
    check(ex.includes('Prüfungsmodus') && !ex.includes('Hinweis anzeigen') && !ex.includes('Lösung zeigen'), 'Prüfungsmodus: keine Hinweise, keine Lösung');
    await shot('05-pruefung');
  } catch (e) {
    fails.push('Abbruch: ' + e.message.split('\n')[0]);
  } finally {
    await b.close();
    srv.kill();
    fs.rmSync(data, { recursive: true, force: true });
  }
  errs.forEach(e => fails.push('JS-Fehler: ' + e));
  console.log(fails.length ? '\n' + fails.length + ' Fehler:\n- ' + fails.join('\n- ') : '\nAbnahmetest im Browser bestanden.');
  process.exit(fails.length ? 1 : 0);
})();
