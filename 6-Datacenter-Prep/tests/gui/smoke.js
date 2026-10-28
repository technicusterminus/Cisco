/* GUI-Rauchtest: Startseite, APIC-Login, Labs & Stände, Benutzerverwaltung, Benutzerwechsel.
   Aufruf: node tests/gui/smoke.js      (braucht Node.js und Playwright mit Chromium)
   Startet Datacenter Prep selbst auf einem freien Port mit leerem Datenordner. */
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

(async () => {
  const port = await freePort();
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'dcprep-gui-'));
  const srv = spawn(process.env.PYTHON || 'python3', ['start.py', '--port', String(port), '--no-browser', '--data', data, '--discovery', '0.05'], { cwd: ROOT, stdio: 'ignore' });
  const U = 'http://127.0.0.1:' + port + '/';
  for (let i = 0; i < 50; i++) { try { await fetch(U + 'dp/me'); break; } catch (e) { await new Promise(r => setTimeout(r, 200)); } }
  const b = await chromium.launch();
  const errs = [];
  try {
    const p = await (await b.newContext({ viewport: { width: 1400, height: 900 } })).newPage();
    p.on('pageerror', e => errs.push(e.message));
    p.on('dialog', d => d.accept());
    const L = id => p.locator('.labrow').filter({ has: p.locator('.labrow-t > b', { hasText: new RegExp('^' + id + ' ') }) }).first();
    const confirm = async () => { await p.click('.modal .btn.primary'); await p.waitForTimeout(1200); };

    await p.goto(U); await p.waitForSelector('.ucards');
    check(await p.locator('.ucard:has-text("standard")').count() === 1, 'Startseite zeigt Benutzer standard');
    await p.click('.ucard:has-text("standard")'); await p.waitForSelector('.login-who');
    check((await p.textContent('.login-who')).includes('standard'), 'APIC-Login zeigt die Übungswelt');
    await p.fill('input[type=password]', 'admin'); await p.click('text=Login'); await p.waitForSelector('.tabs');

    await p.evaluate(() => App.go('sim', 'labs')); await p.waitForSelector('.lablist');
    await L('03').locator('.labrow-act button:has-text("Starten")').click(); await confirm();
    check(await p.evaluate(() => App.state.lab && App.state.lab.id) === '03-tenant-epg', 'Lab 03 gestartet');
    await p.click('.card.lab button:has-text("Lab prüfen")'); await p.waitForSelector('.trace-sum');
    check(/von 8 Prüfungen/.test(await p.textContent('.trace-sum')), 'Lab-Prüfung läuft');
    await p.click('.card.lab button:has-text("Stand speichern")'); await p.waitForSelector('.modal');
    await p.fill('.modal input', 'mein-stand'); await confirm();
    await p.evaluate(() => App.go('sim', 'labs')); await p.waitForTimeout(600);
    await L('04').locator('.labrow-act button:has-text("Starten")').click(); await confirm();
    await L('03').locator('.labrow-act button:has-text("Stände (")').click();
    const t3 = await L('03').textContent();
    check(t3.includes('auto-03-tenant-epg') && t3.includes('mein-stand'), 'Lab 03 hat automatischen und eigenen Stand');
    await L('03').locator('.labrow-act button:has-text("Fortsetzen")').click(); await confirm();
    check(await p.evaluate(() => App.state.lab && App.state.lab.id) === '03-tenant-epg', 'Fortsetzen lädt Lab 03');
    await p.locator('.card.lab button:has-text("Auf Default")').click(); await p.waitForSelector('.modal');
    await p.check('.modal input[type=checkbox]'); await confirm();
    check((await L('03').textContent()).includes('Stände (0)'), 'Default mit Löschen entfernt alle Stände');

    await p.click('.tbtn:has-text("👤")'); await p.click('.ctxitem:has-text("Benutzerverwaltung")'); await p.waitForSelector('.modal table');
    await p.locator('.modal .card input').first().fill('Anna');
    await p.locator('.modal .card input[type=password]').first().fill('geheim');
    await p.click('.modal .card .btn.primary:has-text("Anlegen")'); await p.waitForTimeout(800);
    check((await p.textContent('.modal table')).includes('Anna'), 'Verwalter legt Anna an');
    await p.keyboard.press('Escape'); await p.goto(U); await p.waitForSelector('.tabs');
    await p.click('.tbtn:has-text("👤")'); await p.click('.ctxitem:has-text("Benutzer wechseln")'); await p.waitForSelector('.ucards');
    await p.click('.ucard:has-text("Anna")'); await p.fill('.ucard-pw input', 'falsch'); await p.click('.ucard-pw button'); await p.waitForTimeout(500);
    check((await p.textContent('.login-err')).includes('Passwort falsch'), 'falsches Passwort abgelehnt');
    await p.fill('.ucard-pw input', 'geheim'); await p.click('.ucard-pw button'); await p.waitForSelector('.login-who');
    check((await p.textContent('.login-who')).includes('Anna'), 'Anna hat eine eigene Übungswelt');
  } catch (e) {
    fails.push('Abbruch: ' + e.message.split('\n')[0]);
  } finally {
    await b.close();
    srv.kill();
    fs.rmSync(data, { recursive: true, force: true });
  }
  errs.forEach(e => fails.push('JS-Fehler: ' + e));
  console.log(fails.length ? '\n' + fails.length + ' Fehler:\n- ' + fails.join('\n- ') : '\nGUI-Test bestanden.');
  process.exit(fails.length ? 1 : 0);
})();
