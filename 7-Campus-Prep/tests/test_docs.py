"""Die Dokumentation darf nicht hinter den Labs zurueckbleiben: Anzahlen und Katalog werden gegen labs/*.json geprueft."""
import json
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WORDS = {n: w for n, w in enumerate(
    ['null', 'ein', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn', 'elf', 'zwölf', 'dreizehn', 'vierzehn', 'fünfzehn',
     'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn', 'zwanzig', 'einundzwanzig', 'zweiundzwanzig', 'dreiundzwanzig', 'vierundzwanzig',
     'fünfundzwanzig', 'sechsundzwanzig', 'siebenundzwanzig', 'achtundzwanzig', 'neunundzwanzig', 'dreißig'])}


def read(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as fh:
        return fh.read()


def labs():
    out = []
    d = os.path.join(ROOT, 'labs')
    for f in sorted(os.listdir(d)):
        if f.endswith('.json'):
            out.append(json.loads(read('labs', f)))
    return out


class TestDocs(unittest.TestCase):
    def test_every_lab_has_a_row_in_the_catalog(self):
        cat = read('docs', 'LAB-KATALOG.md')
        for lab in labs():
            nr = lab['id'].split('-')[0]
            self.assertRegex(cat, r'(?m)^\| %s ' % re.escape(nr), 'Lab %s fehlt im Katalog' % lab['id'])
            self.assertIn(lab['title'].split(' ', 1)[1][:25], cat, 'Titel von %s fehlt im Katalog' % lab['id'])

    def test_lab_counts_in_the_readmes_match_the_lab_files(self):
        ls = labs()
        trouble = sum(1 for x in ls if x['kind'] == 'troubleshooting')
        req = sum(1 for x in ls if x['kind'] == 'requirements')
        wifi = sum(1 for x in ls if x['track'].startswith('CCNP Enterprise Wireless'))
        readme = read('README.md')
        self.assertIn('%s Labs (%s Fehlersuchen, %s Aufgaben' % (WORDS[len(ls)], WORDS[trouble], WORDS[req]), readme)
        self.assertIn('%s Labs (%s davon für CCNP Enterprise Wireless)' % (WORDS[len(ls)], WORDS[wifi]), readme)
        self.assertIn('allen %s Labs' % WORDS[len(ls)], readme)
        root = read('..', 'README.md')
        self.assertIn('%d Labs mit automatischer Prüfung' % len(ls), root)

    def test_the_wireless_lab_range_in_the_docs_matches(self):
        nrs = sorted(int(x['id'].split('-')[0]) for x in labs() if x['track'].startswith('CCNP Enterprise Wireless'))
        self.assertEqual(nrs, list(range(nrs[0], nrs[-1] + 1)), 'Die Wireless-Labs sind nicht lueckenlos')
        self.assertIn('Die Labs %02d bis %02d tragen den Track' % (nrs[0], nrs[-1]), read('docs', 'LAB-KATALOG.md'))
        self.assertIn('Die Labs %02d bis %02d gehören zum Track' % (nrs[0], nrs[-1]), read('README.md'))

    def test_every_show_command_is_listed_in_the_readme(self):
        src = read('campusprep', 'wlc.py')
        cmds = re.findall(r"'([a-z0-9 ]+)': self\.wlc\.show_", src)
        self.assertGreaterEqual(len(cmds), 10)
        readme = read('README.md')
        for c in cmds:
            self.assertIn('`show %s`' % c, readme, 'show %s fehlt in der README' % c)

    def test_every_phase_of_the_scope_table_is_marked(self):
        for line in read('docs', 'UMFANG.md').splitlines():
            if re.match(r'\| (\d|\d[a-z]) \|', line):
                self.assertRegex(line, r'\| (umgesetzt|offen) \|$', line)


if __name__ == '__main__':
    unittest.main()
