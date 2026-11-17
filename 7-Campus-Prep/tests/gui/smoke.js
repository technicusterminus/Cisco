/* GUI-Rauchtest der C9800-Oberflaeche: Konfiguration ueber die Dialoge, Fehlerfall, CLI-Ansicht.
   Aufruf: node tests/gui/smoke.js   (braucht Node.js und Playwright mit Chromium; startet den Server selbst) */
'use strict';
const { spawn } = require('child_process');
const net = require('net');
const path = require('path');

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { console.log('Playwright nicht installiert – GUI-Test übersprungen.'); process.exit(0); }

const ROOT = path.resolve(__dirname, '..', '..');
const freePort = () => new Promise(res => { const s = net.createServer(); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); }); });
const fails = [];
const check = (ok, msg) => { console.log((ok ? '  ok   ' : '  FEHLER ') + msg); if (!ok) fails.push(msg); };

(async () => {
  const port = await freePort();
  const srv = spawn(process.env.PYTHON || 'python3', ['start.py', String(port)], { cwd: ROOT, stdio: 'ignore' });
  const U = 'http://127.0.0.1:' + port + '/';
  for (let i = 0; i < 50; i++) { try { await fetch(U + 'wlc/api/state'); break; } catch (e) { await new Promise(r => setTimeout(r, 200)); } }
  const b = await chromium.launch();
  const errs = [];
  try {
    const p = await (await b.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    let rejected = 0;   // die absichtlichen Ablehnungen (HTTP 400) des Tests werden separat gezaehlt
    p.on('console', m => { if (m.type() !== 'error') return; if (/status of 400/.test(m.text())) rejected++; else errs.push('console: ' + m.text()); });
    p.on('dialog', d => d.accept());
    const go = async id => { await p.click('nav a[data-view="' + id + '"]'); await p.waitForTimeout(250); };
    const text = async () => p.evaluate(() => document.getElementById('main').innerText);
    const apply = async () => { await p.click('[data-id="apply"]'); await p.waitForTimeout(400); };

    await p.goto(U); await p.waitForSelector('nav a');
    check((await p.title()).includes('Campus Prep'), 'Seite lädt mit Titel');
    check(await p.locator('nav a').count() >= 8, 'Navigation zeigt alle Ansichten');
    await go('clients');
    check((await text()).includes('Keine Clients verbunden'), 'Ohne Konfiguration ist kein Client verbunden');

    // WLAN anlegen (mit CLI-Vorschau)
    await go('wlans'); await p.click('[data-id="add-wlan"]');
    await p.fill('[data-id="wlan-profile"]', 'Corp_Profile'); await p.fill('[data-id="wlan-ssid"]', 'Corp');
    await p.selectOption('[data-id="wlan-sec"]', 'psk'); await p.fill('[data-id="wlan-psk"]', 'Sommer2026');
    await p.check('[data-id="wlan-enabled"]');
    const prev = await p.textContent('[data-id="cli-preview"]');
    check(/configure terminal[\s\S]*wlan Corp_Profile 1 Corp[\s\S]*security wpa akm psk[\s\S]*set-key ascii 0 Sommer2026[\s\S]*no shutdown[\s\S]*end/.test(prev), 'CLI-Äquivalent zeigt die Befehle');
    await apply();
    const wl = await text();
    console.log('       Tabelle: ' + wl.split('\n').filter(l => l.includes('Corp_Profile')).join(' | ').replace(/\t/g, ' ').slice(0, 120));
    check(/UP\s+Corp_Profile\s+1\s+Corp\s+\[WPA2\]\[PSK\]\[AES\]/.test(wl), 'WLAN erscheint in der Tabelle mit Status UP');
    check(!(await p.content()).includes('Sommer2026'), 'Der Key steht nicht im DOM');

    // Fehlerfall: doppelte ID, nichts wird uebernommen
    await p.click('[data-id="add-wlan"]');
    await p.fill('[data-id="wlan-profile"]', 'Gast'); await p.fill('[data-id="wlan-ssid"]', 'Gast'); await p.fill('[data-id="wlan-id"]', '1');
    await apply();
    check(/bereits vergeben/.test(await p.textContent('.err')) && /nichts wurde übernommen/.test(await p.textContent('.err')), 'Doppelte WLAN-ID wird abgelehnt, Rollback gemeldet');
    await p.click('.modal-bg button:has-text("Cancel")'); await p.waitForTimeout(150);
    check(!(await text()).includes('Gast'), 'Nach dem Fehler existiert das Profil Gast nicht');

    // Validierung im Dialog
    await p.click('[data-id="add-wlan"]'); await p.fill('[data-id="wlan-profile"]', 'x y');
    await apply();
    check(/Profile Name/.test(await p.textContent('.err')), 'Ungültiger Profilname wird im Dialog gemeldet');
    await p.click('.modal-bg button:has-text("Cancel")'); await p.waitForTimeout(150);

    // Policy Profile
    await go('policies'); await p.click('[data-id="add-policy"]');
    await p.fill('[data-id="policy-name"]', 'PP_Corp'); await p.fill('[data-id="policy-vlan"]', '20'); await p.check('[data-id="policy-enabled"]');
    await apply();
    check(/PP_Corp[\s\S]*20/.test(await text()) && /ENABLED/.test(await text()), 'Policy Profile angelegt und ENABLED');

    // Policy Tag mit Zuordnung
    await go('tags'); await p.click('[data-id="add-tag"]');
    await p.fill('[data-id="tag-name"]', 'PT_Corp'); await p.click('[data-id="add-map"]');
    check(/wlan Corp_Profile policy PP_Corp/.test(await p.textContent('[data-id="cli-preview"]')), 'Tag-Dialog bietet WLAN und Policy Profile an');
    await apply();
    check(await p.locator('[data-tag="PT_Corp"]').count() === 1, 'Policy Tag erscheint');

    // Diagnose: AP noch auf dem Default Policy Tag
    await go('diag');
    check(/default-policy-tag[\s\S]*nicht ausgestrahlt/.test(await text()), 'Diagnose: SSID wird am AP mit Default Policy Tag nicht ausgestrahlt');
    await go('clients');
    check((await text()).includes('Keine Clients verbunden'), 'Weiterhin kein Client verbunden');

    // Tag am AP setzen
    await go('apcfg'); await p.click('[data-id="ap-tag-ap-lobby"]');
    await p.selectOption('[data-id="ap-policy-tag"]', 'PT_Corp');
    check(/ap a4b2\.32aa\.0001\s+policy-tag PT_Corp/.test(await p.textContent('[data-id="cli-preview"]')), 'AP-Dialog zeigt ap/policy-tag');
    await apply();
    check(/PT_Corp[\s\S]*Static/.test(await text()), 'AP hat das Tag, Tag Source Static');
    await go('clients');
    check(/58bf\.eaaa\.0001[\s\S]*Run[\s\S]*PSK/.test(await text()), 'Client 1 ist im Zustand Run');
    check(!(await text()).includes('58bf.eaaa.0002'), 'Client 2 (falscher Key) ist nicht in der Client-Liste');
    await go('diag');
    check(/Pre-Shared Key stimmt nicht/.test(await text()), 'Diagnose nennt den falschen Pre-Shared Key');

    // Loeschen mit Abhaengigkeit
    await go('wlans'); await p.click('button.danger:has-text("Delete")'); await p.waitForTimeout(400);
    check((await p.textContent('#toast')).includes('Policy Tags eingetragen'), 'Löschen eines verwendeten WLANs wird abgelehnt');
    check((await text()).includes('Corp_Profile'), 'Das WLAN besteht weiter');

    // CLI-Ansicht
    await go('cli');
    await p.fill('[data-id="cli-input"]', 'show wlan summary'); await p.press('[data-id="cli-input"]', 'Enter'); await p.waitForTimeout(300);
    check(/Number of WLANs: 1[\s\S]*Corp_Profile/.test(await p.textContent('[data-id="term"]')), 'CLI-Ansicht zeigt show wlan summary');
    await p.fill('[data-id="cli-input"]', 'show wireless stats ap join summary'); await p.press('[data-id="cli-input"]', 'Enter'); await p.waitForTimeout(300);
    check(/nicht belegt/.test(await p.textContent('[data-id="term"]')), 'Nicht belegter Show-Befehl wird abgelehnt');

    await go('dash'); await p.screenshot({ path: process.env.SHOT || '/tmp/campus-dash.png' });
    check(/Clients verbunden/.test(await text()), 'Dashboard zeigt die Kacheln');
    // Alle Ansichten ohne JS-Fehler
    for (const id of ['dash', 'aps', 'clients', 'wlans', 'policies', 'tags', 'apcfg', 'cli', 'diag']) { await go(id); }
    check(rejected === 2, 'Genau die zwei absichtlichen Ablehnungen (HTTP 400) wurden ausgelöst: ' + rejected);
    check(errs.length === 0, 'Keine JavaScript-Fehler' + (errs.length ? ': ' + errs.join(' | ') : ''));
  } finally { await b.close(); srv.kill(); }
  console.log(fails.length ? '\n' + fails.length + ' Fehler' : '\nAlle GUI-Prüfungen bestanden.');
  process.exit(fails.length ? 1 : 0);
})();
