import importlib.util
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
HTML = os.path.join(ROOT, 'WLC-Simulator.html')


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def builder():
    spec = importlib.util.spec_from_file_location('build_standalone', os.path.join(ROOT, 'tools', 'build_standalone.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestStandaloneFile(unittest.TestCase):
    def test_html_matches_the_sources(self):
        """WLC-Simulator.html ist generiert: Wer app.js, engine.js, style.css oder die Labs aendert, muss
        tools/build_standalone.py laufen lassen."""
        self.assertEqual(read(HTML), builder().build(), 'WLC-Simulator.html ist veraltet: python3 tools/build_standalone.py')

    def test_html_is_self_contained_and_offline(self):
        html = read(HTML)
        self.assertNotRegex(html, r'(src|href)="https?://', 'keine externen Ressourcen')
        self.assertNotIn('/static/', html, 'keine Verweise auf den Server')
        self.assertNotRegex(html, r'<link[^>]+stylesheet', 'Stylesheet ist eingebettet')
        self.assertEqual(len(re.findall(r'<script src=', html)), 0)
        self.assertIn('window.CampusTransport', html)
        self.assertLess(len(html.encode('utf-8')), 1_000_000)

    def test_embedded_labs_equal_the_lab_files(self):
        html = read(HTML)
        m = re.search(r'window\.CAMPUS_LABS = (.*?);</script>', html, re.S)
        embedded = json.loads(m.group(1))
        labs_dir = os.path.join(ROOT, 'labs')
        files = [json.loads(read(os.path.join(labs_dir, f))) for f in sorted(os.listdir(labs_dir)) if f.endswith('.json')]
        self.assertEqual(embedded, files)
        self.assertEqual(len(embedded), 13)


@unittest.skipUnless(shutil.which('node'), 'Node.js nicht installiert')
class TestParityWithPythonEngine(unittest.TestCase):
    def test_browser_engine_behaves_like_the_python_engine(self):
        """Spielt Szenarien ueber den Python-Server ab und dieselben Schritte gegen static/engine.js (Status, Antworten,
        Endzustand, Lab-Fortschritt) sowie die Persistenz-Randfaelle. Ausgabe bei Abweichungen: erster Unterschied."""
        r = subprocess.run(['node', os.path.join(HERE, 'parity', 'parity.js')], cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-1000:])
        self.assertIn('Paritaet und Persistenz bestanden', r.stdout)


if __name__ == '__main__':
    unittest.main()
