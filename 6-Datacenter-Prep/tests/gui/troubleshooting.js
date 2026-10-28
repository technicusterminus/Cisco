/* GUI-Test Troubleshooting: Endpoint-Verlauf im EP Tracker (Lab 36), physische Ursachen im Traffic Inspector (Lab 37),
   Link-Ereignis über die Hosttabelle. Aufruf: node tests/gui/troubleshooting.js (braucht Node.js und Playwright mit Chromium) */
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

(async () => {
  const port = await freePort();
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'dcprep-ts-'));
  const srv = spawn(process.env.PYTHON || 'python3', ['start.py', '--port', String(port), '--no-browser', '--data', data, '--discovery', '0.05'], { cwd: ROOT, stdio: 'ignore' });
  const U = 'http://127.0.0.1:' + port + '/';
  for (let i = 0; i < 50; i++) { try { await fetch(U + 'dp/me'); break; } catch (e) { await new Promise(r => setTimeout(r, 200)); } }
  const b = await chromium.launch();
  const errs = [];
  try {
    const p = await (await b.newContext({ viewport: { width: 1400, height: 950 } })).newPage();
    p.on('pageerror', e => errs.push(e.message));
    p.on('dialog', d => d.accept());
    const shot = async n => { if (SHOTS) await p.screenshot({ path: path.join(SHOTS, n + '.png') }); };
    const startLab = async id => { await p.evaluate(async lid => { await API.sim('labs/op', { op: 'reset', id: lid, mode: 'guided' }); await App.refreshState(); }, id); };
    const trafficTest = async (src, dst, proto, port_) => {
      await p.evaluate(() => App.go('ops', 'vis')); await p.waitForSelector('.traffic select');
      const sel = p.locator('.traffic select');
      await sel.nth(0).selectOption(src); await sel.nth(1).selectOption(dst); await sel.nth(2).selectOption(proto);
      await p.fill('.traffic input[placeholder=Port]', String(port_ || ''));
      await p.click('.traffic button:has-text("Start")'); await p.waitForSelector('.trace .verdict');
      return p.textContent('.trace');
    };
    await p.goto(U); await p.waitForSelector('.ucards');
    await p.click('.ucard:has-text("standard")'); await p.waitForSelector('.login-who');
    await p.fill('input[type=password]', 'admin'); await p.click('text=Login'); await p.waitForSelector('.tabs');

    // Lab 36: Verlauf im EP Tracker
    await startLab('36-endpoint-move');
    await p.evaluate(() => App.go('ops', 'ep')); await p.waitForSelector('.traffic input');
    await p.fill('.traffic input', 'app2'); await p.click('.traffic button:has-text("Suchen")'); await p.waitForTimeout(600);
    const ep = await p.innerText('.main');
    check(ep.includes('Verlauf app2') && ep.includes('leaf101 eth1/6') && ep.includes('nicht mehr gelernt'), 'EP Tracker zeigt den Verlauf von app2 (alter Ort leaf101 eth1/6)');
    await shot('ts-01-ephist');
    let t = await trafficTest('web1', 'app2', 'tcp', 8080);
    check(t.includes('EP_NOT_LEARNED'), 'web1 → app2: EP_NOT_LEARNED');

    // Lab 37: drei Ursachen
    await startLab('37-link-or-policy');
    t = await trafficTest('web1', 'app1', 'tcp', 8080);
    check(t.includes('PORT_ADMIN_DOWN') && t.includes('kein Link') && !t.includes('Angewandte Policy'), 'Ticket 1: PORT_ADMIN_DOWN, keine Policy-Entscheidung');
    t = await trafficTest('jump1', 'web1', 'tcp', 22);
    check(t.includes('POLICY_IMPLICIT_DENY') && t.includes('Policy verwirft'), 'Ticket 2: Policy-Drop');
    t = await trafficTest('web1', 'web3', 'icmp');
    check(t.includes('LINK_DOWN') && t.includes('Kabel'), 'Ticket 3: LINK_DOWN mit Hinweis auf Kabel/NIC');
    await shot('ts-02-linkdown');

    // Link-Ereignis über die Hosttabelle
    await p.evaluate(() => App.go('sim', 'topo')); await p.waitForSelector('text=Simulierte Hosts');
    const row = p.locator('tr', { hasText: 'web3' }).first();
    await row.locator('button:has-text("Link verbinden")').click(); await p.waitForTimeout(800);
    t = await trafficTest('web1', 'web3', 'icmp');
    check(t.includes('ALLOW'), 'Nach „Link verbinden“ ist web3 erreichbar');
    await p.evaluate(() => App.go('ops', 'ep')); await p.waitForSelector('.traffic input');
    await p.fill('.traffic input', 'web3'); await p.click('.traffic button:has-text("Suchen")'); await p.waitForTimeout(600);
    check((await p.innerText('.main')).includes('Link up'), 'Verlauf von web3 enthält das Link-Ereignis');
  } catch (e) {
    fails.push('Abbruch: ' + e.message.split('\n')[0]);
  } finally {
    await b.close();
    srv.kill();
    fs.rmSync(data, { recursive: true, force: true });
  }
  errs.forEach(e => fails.push('JS-Fehler: ' + e));
  console.log(fails.length ? '\n' + fails.length + ' Fehler:\n- ' + fails.join('\n- ') : '\nTroubleshooting-Test im Browser bestanden.');
  process.exit(fails.length ? 1 : 0);
})();
