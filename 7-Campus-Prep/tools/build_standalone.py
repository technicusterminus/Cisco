#!/usr/bin/env python3
"""Baut WLC-Simulator.html: eine einzelne Datei, die per Doppelklick im Browser laeuft (ohne Python, ohne Webserver, offline).

Die Datei enthaelt Oberflaeche (static/app.js, static/style.css), die Engine im Browser (static/engine.js) und alle Labs
(labs/*.json). Sie ist generiert und eingecheckt; tests/test_standalone.py prueft, dass sie zum Stand der Quellen passt.

    python3 tools/build_standalone.py
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'WLC-Simulator.html')


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def inline_script(code, what):
    """Skriptinhalt fuer <script>...</script>: darf weder </script noch <!-- enthalten."""
    low = code.lower()
    if '</script' in low or '<!--' in low:
        raise SystemExit('%s enthaelt </script oder <!-- und laesst sich nicht einbetten' % what)
    return code


def build():
    page = read('static', 'index.html')
    css_tag = '<link rel="stylesheet" href="/static/style.css">'
    js_tag = '<script src="/static/app.js"></script>'
    if page.count(css_tag) != 1 or page.count(js_tag) != 1:
        raise SystemExit('static/index.html hat nicht die erwarteten Tags')
    labs = []
    for f in sorted(os.listdir(os.path.join(ROOT, 'labs'))):
        if f.endswith('.json'):
            labs.append(json.loads(read('labs', f)))
    labs_json = json.dumps(labs, ensure_ascii=False, sort_keys=True).replace('</', '<\\/').replace('<!--', '<\\!--')
    boot = ("(function () {\n"
            "  var sim = CampusEngine.createSim({ labs: window.CAMPUS_LABS, storage: CampusEngine.browserStorage(), standalone: true });\n"
            "  window.CampusTransport = function (method, path, body) { return Promise.resolve(sim.handle(method, path, body)); };\n"
            "})();")
    scripts = '\n'.join([
        '<script>window.CAMPUS_LABS = %s;</script>' % labs_json,
        '<script>\n%s\n</script>' % inline_script(read('static', 'engine.js'), 'engine.js'),
        '<script>\n%s\n</script>' % boot,
        '<script>\n%s\n</script>' % inline_script(read('static', 'app.js'), 'app.js'),
    ])
    page = page.replace(css_tag, '<style>\n%s\n</style>' % read('static', 'style.css').replace('</style', '<\\/style'))
    page = page.replace(js_tag, scripts)
    page = page.replace('<title>Campus Prep – C9800 Simulator</title>', '<title>Campus Prep – C9800 WLC-Simulator</title>')
    page = page.replace('<body>', '<body>\n<!-- Generiert von tools/build_standalone.py. Nicht von Hand aendern: Quellen sind static/, labs/ und Labs-Quelle/. -->', 1)
    if re.search(r'(src|href)="https?://', page):
        raise SystemExit('Die Datei darf keine externen Ressourcen laden')
    return page


if __name__ == '__main__':
    html = build()
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('%s geschrieben (%d KB)' % (os.path.relpath(OUT), len(html.encode('utf-8')) // 1024))
    sys.exit(0)
