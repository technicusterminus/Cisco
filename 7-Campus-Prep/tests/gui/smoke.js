/* GUI-Rauchtest der C9800-Oberflaeche: Konfiguration ueber die Dialoge, Fehlerfall, CLI-Ansicht, Labs, Staende.
   Aufruf: node tests/gui/smoke.js                  (braucht Node.js und Playwright mit Chromium; startet den Server selbst)
           STANDALONE=1 node tests/gui/smoke.js     (dieselben Pruefungen gegen WLC-Simulator.html, ohne Server, per file://) */
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

const STANDALONE = process.env.STANDALONE === '1';

(async () => {
  let srv = null, U;
  if (STANDALONE) U = 'file://' + path.join(ROOT, 'WLC-Simulator.html');
  else {
    const port = await freePort();
    srv = spawn(process.env.PYTHON || 'python3', ['start.py', String(port), '--ephemeral'], { cwd: ROOT, stdio: 'ignore' });
    U = 'http://127.0.0.1:' + port + '/';
    for (let i = 0; i < 50; i++) { try { await fetch(U + 'wlc/api/state'); break; } catch (e) { await new Promise(r => setTimeout(r, 200)); } }
  }
  const b = await chromium.launch();
  const errs = [];
  try {
    const p = await (await b.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
    const requests = [];
    p.on('request', rq => requests.push(rq.url()));
    p.on('pageerror', e => errs.push('pageerror: ' + e.message));
    let rejected = 0, conflicts = 0;   // die absichtlichen Ablehnungen (HTTP 400 und 409) des Tests werden separat gezaehlt
    p.on('console', m => { if (m.type() !== 'error') return; if (/status of 400/.test(m.text())) rejected++; else if (/status of 409/.test(m.text())) conflicts++; else errs.push('console: ' + m.text()); });
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
    // gemeint ist das gerenderte DOM; Skripte (in WLC-Simulator.html die eingebetteten Lab-Daten) zaehlen nicht
    const dom = await p.evaluate(() => { const c = document.documentElement.cloneNode(true); c.querySelectorAll('script,style').forEach(e => e.remove()); return c.outerHTML; });
    check(!dom.includes('Sommer2026'), 'Der Key steht nicht im DOM');

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
    check(/Geführt bestanden/.test(await text()) && /1 \/ 19[\s\S]*Labs bestanden/.test(await text()), 'Fortschritt: Lab 01 ist als geführt bestanden markiert');
    await p.fill('[data-id="save-name"]', 'lab01-geloest'); await p.click('[data-id="save"]'); await p.waitForTimeout(500);
    check(await p.locator('[data-id="load-lab01-geloest"]').count() === 1, 'Stand wird gespeichert und aufgelistet');
    await p.fill('[data-id="save-name"]', '../evil'); await p.click('[data-id="save"]'); await p.waitForTimeout(400);
    check(/Name: 1-40 Zeichen/.test(await p.textContent('#toast')), 'Ungültiger Name wird abgelehnt');
    // Export und Import eines Stands als Datei
    const tmpDir = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'campusprep-gui-'));
    const [dl] = await Promise.all([p.waitForEvent('download'), p.click('[data-id="export-lab01-geloest"]')]);
    const expFile = require('path').join(tmpDir, dl.suggestedFilename());
    await dl.saveAs(expFile);
    check(dl.suggestedFilename() === 'campusprep-lab01-geloest.json', 'Export: Dateiname campusprep-<Name>.json');
    const expJson = JSON.parse(require('fs').readFileSync(expFile, 'utf8'));
    check(expJson.kind === 'campusprep-state' && expJson.lab && expJson.lab.id === '01-ssid-nicht-sichtbar', 'Export: gültiger Stand mit Lab-Sitzung');
    await p.setInputFiles('[data-id="import-file"]', expFile); await p.waitForTimeout(500);
    check(/Ein Stand mit diesem Namen existiert bereits|importiert/.test(await p.textContent('#toast')) && await p.locator('[data-id="load-lab01-geloest"]').count() === 1, 'Import: der vorhandene Name wird nicht überschrieben');
    await p.fill('[data-id="import-name"]', 'kopie'); await p.setInputFiles('[data-id="import-file"]', expFile); await p.waitForTimeout(600);
    check(await p.locator('[data-id="load-kopie"]').count() === 1 && /importiert als kopie/.test(await p.textContent('#toast')), 'Import: Datei wird als neuer Stand abgelegt');
    const badFile = require('path').join(tmpDir, 'kaputt.json'); require('fs').writeFileSync(badFile, '{"kind": "anderes"}');
    await p.fill('[data-id="import-name"]', 'kaputt'); await p.setInputFiles('[data-id="import-file"]', badFile); await p.waitForTimeout(500);
    check(/Kein Campus-Prep-Stand/.test(await p.textContent('#toast')) && await p.locator('[data-id="load-kaputt"]').count() === 0, 'Import: eine fremde Datei wird abgelehnt');
    const textFile = require('path').join(tmpDir, 'text.json'); require('fs').writeFileSync(textFile, 'das ist kein json');
    await p.setInputFiles('[data-id="import-file"]', textFile); await p.waitForTimeout(400);
    check(/kein gültiges JSON/.test(await p.textContent('#toast')), 'Import: ungültiges JSON wird abgelehnt');
    await p.fill('[data-id="import-name"]', '');
    await p.click('[data-id="del-kopie"]'); await p.waitForTimeout(400);
    check(await p.locator('[data-id="load-kopie"]').count() === 0, 'Der importierte Stand lässt sich löschen');
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
    check(/0 \/ 19[\s\S]*Labs bestanden/.test(await text()) && !/Geführt bestanden/.test(await text()), 'Fortschritt zurücksetzen');

    // 802.1X: AAA-Kette im Standardzustand ueber die Dialoge aufbauen, dann ein WLAN mit WPA2 Enterprise
    await go('aaa'); await p.click('[data-id="add-radius"]');
    await p.fill('[data-id="radius-name"]', 'RS1'); await p.fill('[data-id="radius-ip"]', '10.10.0.50'); await p.fill('[data-id="radius-key"]', 'RadiusKey1');
    check(/radius server RS1[\s\S]*address ipv4 10\.10\.0\.50 auth-port 1812 acct-port 1813[\s\S]*key RadiusKey1/.test(await p.textContent('[data-id="cli-preview"]')), 'RADIUS-Dialog zeigt das CLI-Äquivalent');
    await apply();
    check(/RS1[\s\S]*10\.10\.0\.50[\s\S]*1812 \/ 1813[\s\S]*gesetzt/.test(await text()), 'RADIUS-Server angelegt');
    check(!(await text()).includes('RadiusKey1'), 'Der RADIUS-Key wird nicht angezeigt');
    await p.click('[data-id="add-group"]'); await p.fill('[data-id="group-name"]', 'RG1'); await p.click('[data-id="group-add-server"]'); await apply();
    check(/RG1[\s\S]*RS1/.test(await text()), 'Server Group angelegt');
    await p.click('[data-id="add-list"]'); await p.fill('[data-id="list-name"]', 'DOT1X_LIST'); await apply();
    check(/DOT1X_LIST[\s\S]*dot1x[\s\S]*RG1/.test(await text()), 'Authentication List angelegt');
    await go('wlans'); await p.click('[data-id="add-wlan"]');
    await p.fill('[data-id="wlan-profile"]', 'Corp_1X'); await p.fill('[data-id="wlan-ssid"]', 'CorpDot1x'); await p.fill('[data-id="wlan-id"]', '5');
    await p.selectOption('[data-id="wlan-sec"]', 'dot1x');
    check(await p.locator('[data-id="wlan-psk"]').isHidden() && await p.locator('[data-id="wlan-authlist"]').isVisible(), 'Bei 802.1X ist die Authentication List sichtbar, der PSK nicht');
    check(/security wpa akm dot1x[\s\S]*security dot1x authentication-list DOT1X_LIST/.test(await p.textContent('[data-id="cli-preview"]')), 'WLAN-Dialog zeigt akm dot1x und authentication-list');
    await apply();
    check(/Corp_1X[\s\S]*\[WPA2\]\[802\.1x\]\[AES\]/.test(await text()), 'WLAN mit WPA2 Enterprise angelegt (Security wie im belegten Format)');
    await go('policies'); await p.click('button:has-text("Edit") >> nth=0'); await p.check('[data-id="policy-aaa"]');
    check(/aaa-override/.test(await p.textContent('[data-id="cli-preview"]')) && !/no aaa-override/.test(await p.textContent('[data-id="cli-preview"]')), 'Policy-Dialog: AAA Override ein ergibt aaa-override');
    await p.click('.modal-bg button:has-text("Cancel")'); await p.waitForTimeout(150);

    // 802.1X-Labs: 09 (Key), 10 (AAA Override), 11 (zweiter RADIUS-Server), jeweils ueber die Dialoge geloest
    const labCheck = async () => { await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300); return p.textContent('[data-id="check-result"]'); };
    const solved = r => /bestanden/.test(r) && !/noch nicht/.test(r);
    await go('labs'); await p.selectOption('[data-id="lab-mode"]', 'guided'); await p.click('[data-id="start-09"]'); await p.waitForTimeout(600);
    check(!solved(await labCheck()), 'Lab 09: ohne Lösung nicht bestanden');
    await go('diag');
    check(/anna[\s\S]*Shared Secret stimmt nicht/.test(await text()), 'Lab 09: Diagnose nennt das Shared Secret');
    await go('aaa');
    check(/RS1[\s\S]*DOWN/.test(await text()), 'Lab 09: der Server steht auf DOWN (DEAD)');
    await p.click('button:has-text("Edit") >> nth=0'); await p.fill('[data-id="radius-key"]', 'RadiusKey1'); await apply();
    check(/RS1[\s\S]*UP/.test(await text()), 'Lab 09: nach dem Key ist der Server UP');
    check(solved(await labCheck()), 'Lab 09: mit dem richtigen Key bestanden');
    await go('labs'); await p.click('[data-id="start-10"]'); await p.waitForTimeout(600);
    check(!solved(await labCheck()), 'Lab 10: ohne Lösung nicht bestanden');
    await go('policies'); await p.click('button:has-text("Edit") >> nth=0'); await p.check('[data-id="policy-aaa"]'); await apply();
    check(/Yes/.test(await text()), 'Lab 10: AAA Override ist an');
    check(solved(await labCheck()), 'Lab 10: mit AAA Override bestanden');
    await go('labs'); await p.click('[data-id="start-11"]'); await p.waitForTimeout(600);
    check(!solved(await labCheck()), 'Lab 11: ohne Lösung nicht bestanden');
    await go('aaa'); await p.click('[data-id="add-radius"]'); await p.fill('[data-id="radius-name"]', 'RS2'); await p.fill('[data-id="radius-ip"]', '10.10.0.51');
    await p.fill('[data-id="radius-key"]', 'RadiusKey1'); await apply();
    await p.locator('button:has-text("Edit")').nth(2).click(); await p.click('[data-id="group-add-server"]');
    await p.locator('[data-id="group-rows"] select').nth(1).selectOption('RS2');
    check(/server name RS1[\s\S]*server name RS2/.test(await p.textContent('[data-id="cli-preview"]').then(t => t.replace(/no server name \S+\n/g, ''))), 'Group-Dialog zeigt die Server in ihrer Reihenfolge');
    await apply();
    check(/RG1[\s\S]*RS1 → RS2/.test(await text()), 'Lab 11: RS2 steht hinter RS1 in der Group');
    check(solved(await labCheck()), 'Lab 11: mit zwei Servern in der Kette bestanden');

    // Web Authentication: Lab 13 komplett ueber die Dialoge, Lab 12 ueber den Autorisierungs-Schalter
    const labCheck2 = async () => { await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300); return p.textContent('[data-id="check-result"]'); };
    const solved2 = r => /bestanden/.test(r) && !/noch nicht/.test(r);
    await go('labs'); await p.selectOption('[data-id="lab-mode"]', 'guided'); await p.click('[data-id="start-13"]'); await p.waitForTimeout(600);
    check(!solved2(await labCheck2()), 'Lab 13: ohne Lösung nicht bestanden');
    await go('webauth');
    await p.click('[data-id="add-user"]'); await p.fill('[data-id="user-name"]', 'gast1'); await p.fill('[data-id="user-pw"]', 'Gast#1');
    check(/username gast1 privilege 0 password 0 Gast#1/.test(await p.textContent('[data-id="cli-preview"]')), 'Benutzer-Dialog zeigt das CLI-Äquivalent');
    await apply();
    check(/gast1[\s\S]*gesetzt/.test(await text()) && !(await text()).includes('Gast#1'), 'Lokaler Benutzer angelegt, das Passwort wird nicht angezeigt');
    await p.click('[data-id="add-login"]'); await p.fill('[data-id="login-name"]', 'WEBAUTH'); await apply();
    check(/WEBAUTH[\s\S]*login[\s\S]*local/.test(await text()), 'Authentication List (login) angelegt');
    check(/aaa authorization network default local: fehlt/.test(await text()), 'Die Autorisierung fehlt zunächst');
    await p.click('[data-id="authz-toggle"]'); await p.waitForTimeout(400);
    check(/aaa authorization network default local: konfiguriert/.test(await text()), 'Autorisierung konfiguriert');
    await go('wlans'); await p.click('button:has-text("Edit") >> nth=0'); await p.check('[data-id="wlan-webauth"]');
    check(/security web-auth[\s\S]*security web-auth authentication-list WEBAUTH[\s\S]*security web-auth parameter-map global/.test(await p.textContent('[data-id="cli-preview"]')), 'WLAN-Dialog zeigt die Web-Auth-Befehle');
    await apply();
    check(solved2(await labCheck2()), 'Lab 13: mit den Dialogen bestanden');
    await go('clients');
    check(/Webauth Pending/.test(await text()), 'Mallory steht in Webauth Pending');
    await go('labs'); await p.click('[data-id="start-12"]'); await p.waitForTimeout(600);
    check(!solved2(await labCheck2()), 'Lab 12: ohne Lösung nicht bestanden');
    await go('diag');
    check(/gast1[\s\S]*aaa authorization network default local/.test(await text()), 'Lab 12: Diagnose nennt die fehlende Autorisierung');
    await go('webauth'); await p.click('[data-id="authz-toggle"]'); await p.waitForTimeout(400);
    check(solved2(await labCheck2()), 'Lab 12: mit der Autorisierung bestanden');

    // QoS: Lab 19 und Lab 18 ueber den Policy-Dialog
    const labCheck5 = async () => { await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300); return p.textContent('[data-id="check-result"]'); };
    const solved5 = r => /bestanden/.test(r) && !/noch nicht/.test(r);
    const editPolicy = async name => { await go('policies'); await p.locator('tr', { hasText: name }).locator('button:has-text("Edit")').click(); };
    await go('labs'); await p.selectOption('[data-id="lab-mode"]', 'guided'); await p.click('[data-id="start-19"]'); await p.waitForTimeout(600);
    check(!solved5(await labCheck5()), 'Lab 19: ohne Lösung nicht bestanden');
    await go('diag');
    check(/DSCP[\s\S]*46 → 46 \/ 46/.test(await text()), 'Diagnose zeigt den DSCP-Wert je Richtung (ohne Begrenzung)');
    await editPolicy('PP_Guest'); await p.selectOption('[data-id="policy-qos-out"]', 'bronze');
    check(/service-policy output bronze/.test(await p.textContent('[data-id="cli-preview"]')) && /no service-policy input/.test(await p.textContent('[data-id="cli-preview"]')), 'Policy-Dialog zeigt das CLI-Äquivalent (nur Output gesetzt)');
    await apply();
    check(!solved5(await labCheck5()), 'Lab 19: nur eine Richtung begrenzt reicht nicht');
    await editPolicy('PP_Guest'); await p.selectOption('[data-id="policy-qos-in"]', 'bronze-up'); await apply();
    check(/bronze \/ bronze-up/.test((await (async () => { await go('policies'); return text(); })())), 'Policy-Tabelle zeigt QoS je Richtung');
    check(solved5(await labCheck5()), 'Lab 19: mit beiden Richtungen bestanden');
    await go('labs'); await p.click('[data-id="start-18"]'); await p.waitForTimeout(600);
    check(!solved5(await labCheck5()), 'Lab 18: ohne Lösung nicht bestanden');
    await editPolicy('PP_Corp'); await p.selectOption('[data-id="policy-qos-out"]', 'platinum'); await p.selectOption('[data-id="policy-qos-in"]', 'platinum-up'); await apply();
    check(solved5(await labCheck5()), 'Lab 18: mit Platinum in beide Richtungen bestanden');

    // RF: Lab 17 komplett ueber die Dialoge, Lab 16 ueber die AP-Zuordnung
    const labCheck4 = async () => { await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300); return p.textContent('[data-id="check-result"]'); };
    const solved4 = r => /bestanden/.test(r) && !/noch nicht/.test(r);
    await go('labs'); await p.selectOption('[data-id="lab-mode"]', 'guided'); await p.click('[data-id="start-17"]'); await p.waitForTimeout(600);
    check(!solved4(await labCheck4()), 'Lab 17: ohne Lösung nicht bestanden');
    await go('rf'); await p.click('[data-id="add-rfprof"]');
    await p.fill('[data-id="rfprof-name"]', 'RF_LOBBY'); await p.fill('[data-id="rfprof-max"]', '14');
    check(/ap dot11 5ghz rf-profile RF_LOBBY[\s\S]*tx-power max 14[\s\S]*shutdown/.test(await p.textContent('[data-id="cli-preview"]')) && !/no shutdown/.test(await p.textContent('[data-id="cli-preview"]')), 'RF-Dialog: ein neues Profil ist zunächst deaktiviert (shutdown)');
    await p.check('[data-id="rfprof-enabled"]');
    check(/no shutdown/.test(await p.textContent('[data-id="cli-preview"]')), 'RF-Dialog: Enabled ergibt no shutdown');
    await apply();
    check(/5 GHz[\s\S]*RF_LOBBY[\s\S]*14 dBm/.test(await text()), 'RF-Profil angelegt');
    await p.click('[data-id="add-rftag"]'); await p.fill('[data-id="rftag-name"]', 'RFT_LOBBY'); await p.selectOption('[data-id="rftag-5"]', 'RF_LOBBY');
    check(/wireless tag rf RFT_LOBBY[\s\S]*5ghz-rf-policy RF_LOBBY/.test(await p.textContent('[data-id="cli-preview"]')), 'RF-Tag-Dialog zeigt das CLI-Äquivalent');
    await apply();
    check(/RFT_LOBBY[\s\S]*RF_LOBBY/.test(await text()), 'RF Tag angelegt');
    check(!solved4(await labCheck4()), 'Lab 17: ohne AP-Zuordnung nicht bestanden');
    await go('apcfg'); await p.click('[data-id="ap-tag-ap-lobby"]'); await p.selectOption('[data-id="ap-rf-tag"]', 'RFT_LOBBY'); await apply();
    check(/ap-lobby[\s\S]*RF_LOBBY, max\. 14 dBm/.test(await text()), 'Access Points: Wirkung je Band sichtbar');
    check(solved4(await labCheck4()), 'Lab 17: mit den Dialogen bestanden');
    await go('labs'); await p.click('[data-id="start-16"]'); await p.waitForTimeout(600);
    check(!solved4(await labCheck4()), 'Lab 16: ohne Lösung nicht bestanden');
    await go('apcfg'); await p.click('[data-id="ap-tag-ap-lobby"]'); await p.selectOption('[data-id="ap-rf-tag"]', 'RFT_LOBBY'); await apply();
    check(solved4(await labCheck4()), 'Lab 16: mit der AP-Zuordnung bestanden');

    // Mobility: Lab 15 komplett ueber die Dialoge, Lab 14 ueber das Bearbeiten des Peers
    const labCheck3 = async () => { await go('labs'); await p.click('[data-id="lab-check"]'); await p.waitForTimeout(300); return p.textContent('[data-id="check-result"]'); };
    const solved3 = r => /bestanden/.test(r) && !/noch nicht/.test(r);
    await go('labs'); await p.selectOption('[data-id="lab-mode"]', 'guided'); await p.click('[data-id="start-15"]'); await p.waitForTimeout(600);
    check(!solved3(await labCheck3()), 'Lab 15: ohne Lösung nicht bestanden');
    await go('mobility');
    check(/Keine Mobility-Peers/.test(await text()), 'Mobility: zu Beginn kein Peer');
    await p.click('[data-id="edit-mobgroup"]'); await p.fill('[data-id="mobgroup-name"]', 'Zentrale');
    check(/wireless mobility group name Zentrale/.test(await p.textContent('[data-id="cli-preview"]')), 'Gruppen-Dialog zeigt das CLI-Äquivalent');
    await apply();
    await p.click('[data-id="add-peer"]'); await p.fill('[data-id="peer-ip"]', '10.10.0.20'); await p.fill('[data-id="peer-mac"]', 'aabb.cc00.0200'); await p.fill('[data-id="peer-group"]', 'Campus');
    check(/wireless mobility group member mac-address aabb\.cc00\.0200 ip 10\.10\.0\.20 group Campus/.test(await p.textContent('[data-id="cli-preview"]')), 'Peer-Dialog zeigt das CLI-Äquivalent');
    await apply();
    check(/10\.10\.0\.20[\s\S]*aabb\.cc00\.0200[\s\S]*Campus[\s\S]*UP[\s\S]*UP/.test(await text()), 'Peer angelegt, Control und Data Path oben');
    check(solved3(await labCheck3()), 'Lab 15: mit den Dialogen bestanden');
    await go('diag');
    check(/Inter-Controller/.test(await text()), 'Diagnose zeigt das Roaming (Inter-Controller)');
    await go('labs'); await p.click('[data-id="start-14"]'); await p.waitForTimeout(600);
    check(!solved3(await labCheck3()), 'Lab 14: ohne Lösung nicht bestanden');
    await go('diag');
    check(/Gruppenname Zentrale[\s\S]*Campus/.test(await text()), 'Lab 14: Diagnose nennt den falschen Gruppennamen');
    await go('mobility'); await p.click('button:has-text("Edit") >> nth=1'); await p.fill('[data-id="peer-group"]', 'Campus'); await apply();
    check(solved3(await labCheck3()), 'Lab 14: mit dem richtigen Gruppennamen bestanden');

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

    // Neuladen: Zustand und Lab-Sitzung bleiben erhalten (Server: im Speicher des Servers, Standalone: lokaler Speicher des Browsers)
    await p.reload(); await p.waitForSelector('nav a'); await go('dash');
    check(/Aktuelles Lab: 07-flexconnect-zweigstelle/.test(await text()), 'Nach dem Neuladen ist das Lab weiter aktiv');
    await go('apcfg');
    check(/ap-lager[\s\S]*FlexConnect/.test(await text()), 'Nach dem Neuladen ist die Konfiguration noch da');

    // Alle Ansichten ohne JS-Fehler
    for (const id of ['dash', 'labs', 'aaa', 'webauth', 'mobility', 'rf', 'flex', 'sitetags', 'aps', 'clients', 'wlans', 'policies', 'tags', 'apcfg', 'cli', 'diag']) { await go(id); }
    check(rejected === (STANDALONE ? 0 : 4) && conflicts === (STANDALONE ? 0 : 1), (STANDALONE ? 'Ohne Server gibt es keine HTTP-Fehler: ' : 'Genau die absichtlichen Ablehnungen (4 x HTTP 400, 1 x 409) wurden ausgelöst: ') + rejected + '/' + conflicts);
    if (STANDALONE) check(!requests.some(u => /^https?:/.test(u)), 'Keine Netzwerkzugriffe (läuft vollständig offline)' + (requests.some(u => /^https?:/.test(u)) ? ': ' + requests.filter(u => /^https?:/.test(u)).join(' ') : ''));
    check(errs.length === 0, 'Keine JavaScript-Fehler' + (errs.length ? ': ' + errs.join(' | ') : ''));
  } finally { await b.close(); if (srv) srv.kill(); }
  console.log(fails.length ? '\n' + fails.length + ' Fehler' : '\nAlle GUI-Prüfungen bestanden.');
  process.exit(fails.length ? 1 : 0);
})();
