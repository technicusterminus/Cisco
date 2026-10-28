"""Browser-End-to-End fuer Lab 32 (optional, braucht Playwright mit Chromium).

Startet den Server, meldet sich an, startet das Lab, testet im Traffic Inspector (DROP mit Reason Code),
spielt die Loesung per REST ein, testet erneut (ALLOW), prueft das Lab, laedt die Seite neu.

Aufruf aus 6-Datacenter-Prep:  python3 tests/e2e_browser.py [Ordner fuer Screenshots]
Ohne Playwright endet das Skript mit Exit-Code 0 und einem Hinweis (kein Teil von unittest discover).
"""
import sys, os, tempfile, threading
sys.path.insert(0, os.getcwd())
from dcprep.server import serve
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('Playwright nicht installiert - Browser-Test uebersprungen')
    sys.exit(0)
OUT = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
from test_least_privilege import solution
hub, httpd = serve('127.0.0.1', 0, tempfile.mkdtemp(), 'admin', discovery=0)
base = 'http://127.0.0.1:%d' % httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
res = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1440, 'height': 1000})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(base + '/')
    pg.get_by_text('standard', exact=True).first.click()
    pg.wait_for_selector('input[type=password]')
    pg.locator('.login input').first.fill('admin')
    pg.locator('.login input[type=password]').fill('admin')
    pg.get_by_role('button', name='Login').click()
    pg.wait_for_timeout(1200)
    # Lab 32 starten
    pg.evaluate("App.go('sim', 'labs')"); pg.wait_for_timeout(800)
    row = pg.locator('.labrow', has_text='32 Least Privilege')
    row.get_by_role('button', name='▶ Starten').click()
    pg.get_by_role('button', name='OK').or_(pg.get_by_role('button', name='Ja')).first.click()
    pg.wait_for_timeout(1200)
    pg.screenshot(path=OUT + '/02-lab32.png', full_page=True)
    # Traffic Inspector
    pg.evaluate("App.go('ops', 'vis')"); pg.wait_for_timeout(600)
    sels = pg.locator('.traffic select')
    sels.nth(0).select_option('web1'); sels.nth(1).select_option('app1'); sels.nth(2).select_option('tcp')
    pg.locator('.traffic input[placeholder=Port]').fill('443')
    pg.get_by_role('button', name='Start').click(); pg.wait_for_timeout(600)
    res['before'] = pg.locator('.trace').first.inner_text()
    pg.screenshot(path=OUT + '/03-drop.png', full_page=True)
    # Loesung per REST mit derselben Browser-Session (wie API Inspector / Automatisierung)
    st = pg.evaluate("async (body) => { const r = await fetch('/api/mo/uni.json', {method: 'POST', body: JSON.stringify(body)}); return r.status; }", solution())
    res['post'] = st
    pg.get_by_role('button', name='Start').click(); pg.wait_for_timeout(600)
    res['after'] = pg.locator('.trace').first.inner_text()
    pg.screenshot(path=OUT + '/04-allow.png', full_page=True)
    # Lab pruefen und Hinweis
    pg.evaluate("App.go('sim', 'labs')"); pg.wait_for_timeout(800)
    pg.get_by_role('button', name='Hinweis (1 / 4)').click(); pg.wait_for_timeout(400)
    pg.get_by_role('button', name='✔ Lab prüfen').click(); pg.wait_for_timeout(800)
    res['check'] = pg.locator('.lab .trace').inner_text()
    pg.screenshot(path=OUT + '/05-check.png', full_page=True)
    # Reload: Fortschritt bleibt
    pg.reload(); pg.wait_for_timeout(1500)
    pg.evaluate("App.go('sim', 'labs')"); pg.wait_for_timeout(800)
    res['reload'] = pg.locator('.labrow', has_text='32 Least Privilege').inner_text()
    b.close()
res['errors'] = errs
assert not errs, errs
assert 'DROP' in res['before'] and 'POLICY_IMPLICIT_DENY' in res['before'], res['before']
assert res['post'] == 200
assert 'ALLOW' in res['after'] and 'Provider → Consumer' in res['after'], res['after']
assert 'Alle Prüfungen bestanden' in res['check'] and 'Sicherheit: 6 / 6' in res['check'], res['check']
assert '32 Least Privilege' in res['reload']
print('Browser-E2E bestanden, Screenshots in', OUT)
