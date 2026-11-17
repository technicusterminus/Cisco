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
  const srv = spawn(process.env.PYTHON || 'python3', ['start.py', String(port), '--ephemeral'], { cwd: ROOT, stdio: 'ignore' });
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
    check(await p.locator('nav a').count() >= 9, 'Navigation zeigt alle Ansichten');
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
    // Labs: gefuehrtes Lab 01 mit Hinweisen, falscher Abkuerzung und Loesung
    await go('labs'); await p.selectOption('[data-id="lab-mode"]', 'guided'); await p.click('[data-id="start-01"]'); await p.waitForTimeout(500);
    check(/Corp-SSID in der Lobby nicht sichtbar/.test(await text()) && /Anforderungen/.test(await text()), 'Lab 01 startet und zeigt Szenario und Anforderungen');
    await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300);
    let res = await p.textContent('[data-id="check-result"]');
    check(/noch nicht bestanden/.test(res) && /✖ Lobby-Laptop verbunden/.test(res), 'Prüfung: ohne Lösung nicht bestanden, Detail sichtbar');
    await go('diag');
    check(/default-policy-tag[\s\S]*nicht ausgestrahlt/.test(await text()), 'Geführt: Client-Diagnose erklärt die Ursache');
    await go('labs'); await p.click('[data-id="hint"]'); await p.waitForTimeout(250);
    check(await p.locator('[data-hint="1"]').count() === 1 && /Konzept/.test(await p.textContent('[data-hint="1"]')), 'Hinweis Stufe 1 erscheint');
    await p.click('[data-id="hint"]'); await p.waitForTimeout(250);
    check(await p.locator('[data-hint]').count() === 2 && /Stufe 3 von 4/.test(await p.textContent('[data-id="hints"]')), 'Hinweis Stufe 2, Knopf zeigt Stufe 3 von 4');
    // falsche Abkuerzung: beide APs taggen
    await go('apcfg'); await p.click('[data-id="ap-tag-ap-lobby"]'); await p.selectOption('[data-id="ap-policy-tag"]', 'PT_Corp'); await apply();
    await p.click('[data-id="ap-tag-ap-lager"]'); await p.selectOption('[data-id="ap-policy-tag"]', 'PT_Corp'); await apply();
    await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300);
    res = await p.textContent('[data-id="check-result"]');
    check(/noch nicht bestanden/.test(res) && /✖ ap-lager sendet Corp nicht/.test(res) && /✔ Lobby-Laptop verbunden/.test(res), 'Beide APs zu taggen verbindet den Laptop, verletzt aber die Sicherheitsprüfung');
    await go('apcfg'); await p.click('[data-id="ap-tag-ap-lager"]'); await p.selectOption('[data-id="ap-policy-tag"]', 'default-policy-tag'); await apply();
    await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300);
    check(/bestanden/.test(await p.textContent('[data-id="check-result"]')) && !/noch nicht/.test(await p.textContent('[data-id="check-result"]')), 'Mit der richtigen Lösung ist Lab 01 bestanden');
    await p.locator('[data-q="q1"] input').first().check(); await p.waitForTimeout(300);
    check(/✔ richtig/.test(await p.textContent('[data-q="q1"]')), 'Verständnisfrage wird beantwortet und erklärt');
    await p.click('[data-id="lab-solution"]'); await p.waitForTimeout(250);
    check(/Edit Tags/.test(await p.textContent('[data-id="solution"]')), 'Lösung zeigen im geführten Modus');
    // Staende und Fortschritt
    await go('labs');
    console.log('       Kacheln: ' + (await text()).split('\n').filter(l => /bestanden|Starts|Prüfungsmodus$|^\d+( \/ \d+)?$/.test(l)).join(' | ').slice(0, 200));
    check(/Geführt bestanden/.test(await text()) && /1 \/ 8[\s\S]*Labs bestanden/.test(await text()), 'Fortschritt: Lab 01 ist als geführt bestanden markiert');
    await p.fill('[data-id="save-name"]', 'lab01-geloest'); await p.click('[data-id="save"]'); await p.waitForTimeout(500);
    check(await p.locator('[data-id="load-lab01-geloest"]').count() === 1, 'Stand wird gespeichert und aufgelistet');
    await p.fill('[data-id="save-name"]', '../evil'); await p.click('[data-id="save"]'); await p.waitForTimeout(400);
    check(/Name: 1-40 Zeichen/.test(await p.textContent('#toast')), 'Ungültiger Name wird abgelehnt');
    // Pruefungsmodus: Lab 02
    await p.selectOption('[data-id="lab-mode"]', 'exam'); await p.click('[data-id="start-02"]'); await p.waitForTimeout(500);
    check(/Prüfungsmodus/.test(await text()) && await p.locator('[data-id="hint"]').count() === 0 && await p.locator('[data-id="lab-solution"]').count() === 0, 'Prüfungsmodus: keine Hinweise, keine Lösung');
    await go('diag');
    check(await p.locator('[data-id="diag-locked"]').count() === 1 && !/administrativ/.test(await text()), 'Prüfungsmodus: Client-Diagnose gesperrt, keine Begründung sichtbar');
    await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300);
    res = await p.textContent('[data-id="check-result"]');
    check(/noch nicht bestanden/.test(res) && !/Zustand Not Associated/.test(res), 'Prüfungsmodus: Auswertung ohne Details');
    await go('dash'); check(/Aktuelles Lab: 02-admin-down/.test(await text()), 'Dashboard zeigt das laufende Lab');
    await go('labs'); await p.click('[data-id="load-lab01-geloest"]'); await p.waitForTimeout(600);
    check(/01 Corp-SSID in der Lobby nicht sichtbar/.test(await p.textContent('[data-lab]')), 'Laden stellt das Lab 01 wieder her');
    await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300);
    check(/bestanden/.test(await p.textContent('[data-id="check-result"]')) && !/noch nicht/.test(await p.textContent('[data-id="check-result"]')), 'Der geladene Stand ist weiter gelöst');
    await p.click('[data-id="del-lab01-geloest"]'); await p.waitForTimeout(400);
    check(await p.locator('[data-id="load-lab01-geloest"]').count() === 0, 'Stand lässt sich löschen');
    await p.click('[data-id="reset-progress"]'); await p.waitForTimeout(400);
    check(/0 \/ 8[\s\S]*Labs bestanden/.test(await text()) && !/Geführt bestanden/.test(await text()), 'Fortschritt zurücksetzen');

    // CCNP Enterprise Wireless: FlexConnect-Lab 07, komplett ueber die Dialoge
    await go('labs'); await p.selectOption('[data-id="lab-mode"]', 'guided'); await p.click('[data-id="start-07"]'); await p.waitForTimeout(600);
    check(/CCNP Enterprise Wireless/.test(await p.textContent('[data-id="lab-track"]')) && /Zweigstelle Lager/.test(await text()), 'Lab 07 startet mit dem Track CCNP Enterprise Wireless');
    await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300);
    check(/noch nicht bestanden/.test(await p.textContent('[data-id="check-result"]')), 'Lab 07: ohne Lösung nicht bestanden');
    await go('flex'); await p.click('[data-id="add-flex"]'); await p.fill('[data-id="flex-name"]', 'FP_Lager'); await p.click('[data-id="flex-add-vlan"]');
    await p.fill('[data-id="flex-rows"] input[placeholder="VLAN-Name"]', 'CORP_LOCAL'); await p.fill('[data-id="flex-rows"] input[placeholder="ID"]', '20');
    check(/wireless profile flex FP_Lager[\s\S]*vlan-name CORP_LOCAL[\s\S]*vlan-id 20/.test(await p.textContent('[data-id="cli-preview"]')), 'Flex-Dialog zeigt das CLI-Äquivalent');
    await apply();
    check(/FP_Lager[\s\S]*CORP_LOCAL \(20\)/.test(await text()), 'Flex Profile mit VLAN-Name und ID angelegt');
    await go('policies'); await p.click('[data-id="add-policy"]'); await p.fill('[data-id="policy-name"]', 'PP_Corp_Flex'); await p.fill('[data-id="policy-vlan"]', 'CORP_LOCAL');
    await p.uncheck('[data-id="policy-central"]'); await p.check('[data-id="policy-enabled"]');
    check(/vlan CORP_LOCAL[\s\S]*no central switching/.test(await p.textContent('[data-id="cli-preview"]')), 'Policy-Dialog: Central Switching aus ergibt no central switching');
    await apply();
    check(/PP_Corp_Flex[\s\S]*CORP_LOCAL[\s\S]*Local/.test(await text()), 'Policy Profile mit lokalem Switching angelegt');
    await go('tags'); await p.click('[data-id="add-tag"]'); await p.fill('[data-id="tag-name"]', 'PT_Corp_Flex'); await p.click('[data-id="add-map"]');
    await p.selectOption('[data-id="tag-rows"] select >> nth=1', 'PP_Corp_Flex'); await apply();
    check(await p.locator('[data-tag="PT_Corp_Flex"]').count() === 1, 'Policy Tag für das Lager angelegt');
    await go('sitetags'); await p.click('[data-id="add-site"]'); await p.fill('[data-id="site-name"]', 'ST_Lager');
    check(await p.locator('[data-id="site-flex"]').isDisabled(), 'Flex Profile ist bei eingeschalteter Local Site nicht wählbar');
    await p.uncheck('[data-id="site-local"]'); await p.selectOption('[data-id="site-flex"]', 'FP_Lager');
    check(/no local-site[\s\S]*flex-profile FP_Lager/.test(await p.textContent('[data-id="cli-preview"]')), 'Site-Tag-Dialog zeigt no local-site und flex-profile');
    await apply();
    check(/ST_Lager[\s\S]*No[\s\S]*FP_Lager/.test(await text()), 'Site Tag ohne Local Site mit Flex Profile angelegt');
    await go('apcfg'); await p.click('[data-id="ap-tag-ap-lager"]'); await p.selectOption('[data-id="ap-policy-tag"]', 'PT_Corp_Flex'); await p.selectOption('[data-id="ap-site-tag"]', 'ST_Lager');
    check(/policy-tag PT_Corp_Flex[\s\S]*site-tag ST_Lager/.test(await p.textContent('[data-id="cli-preview"]')), 'AP-Dialog zeigt policy-tag und site-tag');
    await apply();
    check(/ap-lager[\s\S]*FlexConnect/.test(await text()), 'ap-lager arbeitet im FlexConnect-Modus');
    await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300);
    res = await p.textContent('[data-id="check-result"]');
    check(/bestanden/.test(res) && !/noch nicht/.test(res) && /lokal geschaltet/.test(res), 'Lab 07 ist bestanden (Lager-Laptop lokal geschaltet)');
    await go('diag'); check(/local/.test(await text()), 'Diagnose zeigt die Switching-Art');

    // Alle Ansichten ohne JS-Fehler
    for (const id of ['dash', 'labs', 'flex', 'sitetags', 'aps', 'clients', 'wlans', 'policies', 'tags', 'apcfg', 'cli', 'diag']) { await go(id); }
    check(rejected === 3, 'Genau die drei absichtlichen Ablehnungen (HTTP 400) wurden ausgelöst: ' + rejected);
    check(errs.length === 0, 'Keine JavaScript-Fehler' + (errs.length ? ': ' + errs.join(' | ') : ''));
  } finally { await b.close(); srv.kill(); }
  console.log(fails.length ? '\n' + fails.length + ' Fehler' : '\nAlle GUI-Prüfungen bestanden.');
  process.exit(fails.length ? 1 : 0);
})();
