import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from campusprep.labs import LabError  # noqa: E402
from campusprep.server import Sim, serve  # noqa: E402

L1, L2 = 'a4b2.32aa.0001', 'a4b2.32aa.0002'
ALL = ['01-ssid-nicht-sichtbar', '02-admin-down', '03-falscher-schluessel', '04-falsches-policy-profile',
       '05-gast-wlan-lobby', '06-aufraeumen']
# Woerter, die im sichtbaren Text vor dem Bestehen (Intro, Anforderungen, Pruefungsbeschreibungen) nicht stehen duerfen
LEAKS = {
    '01-ssid-nicht-sichtbar': ['policy-tag', 'Policy Tag', 'Tag Source', 'PT_Corp'],
    '02-admin-down': ['shutdown', 'administrativ', 'aktivieren'],
    '03-falscher-schluessel': ['set-key', 'Tippfehler', 'neu setzen'],
    '04-falsches-policy-profile': ['Policy Tag', 'PT_Corp', 'zuordnen'],
    '05-gast-wlan-lobby': ['PT_Lobby', 'PT_Lager', 'Policy Tag'],
    '06-aufraeumen': ['no policy-tag', 'no wlan', 'zuerst', 'Reihenfolge'],
}


def started(lab, mode='guided'):
    s = Sim()
    s.labs.start(lab, mode)
    return s


def fixed(lab, extra=None):
    s = started(lab)
    ok, _, err = s.apply(s.labs.labs[lab]['solutionCommands'] if extra is None else extra)
    assert ok, err
    return s


def failed(s):
    return [c['desc'] for c in s.labs.check()['checks'] if not c['ok']]


class TestLabs(unittest.TestCase):
    def test_every_lab_fails_without_and_passes_with_the_solution(self):
        self.assertEqual(sorted(Sim().labs.labs), ALL)
        for lab in ALL:
            with self.subTest(lab=lab):
                s = started(lab)
                self.assertFalse(s.labs.check()['passed'], 'ohne Loesung darf %s nicht bestanden sein' % lab)
                ok, _, err = s.apply(s.labs.labs[lab]['solutionCommands'])
                self.assertTrue(ok, err)
                r = s.labs.check()
                self.assertTrue(r['passed'], failed(s))
                self.assertTrue(r['checks'] and all(c['ok'] for c in r['checks']))

    def test_structure_and_no_solution_in_visible_text(self):
        self.assertEqual(sorted(LEAKS), ALL)
        for lab in ALL:
            with self.subTest(lab=lab):
                d = Sim().labs.labs[lab]
                self.assertEqual(len(d['hints']), 4)
                self.assertEqual(d['modes'], ['guided', 'exam'])
                self.assertTrue(d['goals'] and d['limits'] and d['cause'] and d['requirements'] and d['tools'])
                self.assertTrue(any(c['category'] == 'security' for c in d['checks']), 'Sicherheitspruefung fehlt')
                for qu in d['questions']:
                    self.assertLess(qu['answer'], len(qu['options']))
                text = d['intro'] + ' ' + ' '.join(d['requirements']) + ' ' + ' '.join(c['desc'] for c in d['checks'])
                for word in LEAKS[lab]:
                    self.assertNotIn(word, text, '%s verraet die Loesung von %s' % (word, lab))

    def test_checks_do_not_pass_vacuously(self):
        # Jede Pruefung kann scheitern: Im Startzustand ist mindestens eine Funktionspruefung offen.
        for lab in ALL:
            s = started(lab)
            fn = [c for c in s.labs.check()['checks'] if c['category'] == 'function']
            self.assertTrue(fn and any(not c['ok'] for c in fn), lab)

    def test_lab01_tagging_both_aps_violates_least_privilege(self):
        s = fixed('01-ssid-nicht-sichtbar', ['ap %s' % L1, 'policy-tag PT_Corp', 'exit', 'ap %s' % L2, 'policy-tag PT_Corp'])
        self.assertEqual(failed(s), ['ap-lager sendet Corp nicht'])
        self.assertFalse(s.labs.check()['passed'])

    def test_lab02_partial_fix_is_not_enough(self):
        s = fixed('02-admin-down', ['wlan Corp_Profile 1 Corp', 'no shutdown'])
        self.assertFalse(s.labs.check()['passed'])
        why = ' '.join(s.wlc.clients()[0]['reasons'])
        self.assertIn('Policy Profile PP_Corp ist administrativ down', why)

    def test_lab03_open_wlan_connects_but_fails_security(self):
        s = fixed('03-falscher-schluessel', ['wlan Corp_Profile 1 Corp', 'no security wpa akm psk'])
        r = s.labs.check()
        self.assertTrue(next(c for c in r['checks'] if c['category'] == 'function')['ok'], 'Der Client verbindet sich')
        self.assertFalse(r['passed'])
        self.assertEqual(failed(s), ['Corp nutzt weiterhin WPA2-PSK'])

    def test_lab04_enabling_the_guest_policy_is_the_wrong_fix(self):
        s = fixed('04-falsches-policy-profile', ['wireless profile policy PP_Gast', 'no shutdown'])
        c = s.wlc.clients()[0]
        self.assertEqual((c['state'], c['vlan']), ('Run', '99'))
        self.assertEqual(len(failed(s)), 2)
        self.assertFalse(s.labs.check()['passed'])

    def test_lab05_guest_in_the_shared_tag_leaks_into_the_lager(self):
        wrong = ['wlan Gast_Profile 2 Gast', 'no shutdown', 'exit', 'wireless profile policy PP_Gast', 'vlan 99', 'no shutdown', 'exit',
                 'wireless tag policy PT_Corp', 'wlan Gast_Profile policy PP_Gast']
        s = fixed('05-gast-wlan-lobby', wrong)
        self.assertEqual(failed(s), ['Gast-Laptop im Lager: keine Verbindung'])

    def test_lab05_an_equivalent_design_also_passes(self):
        alt = ['wlan Gast_Profile 2 Gast', 'no shutdown', 'exit', 'wireless profile policy PP_Gast', 'vlan 99', 'no shutdown', 'exit',
               'wireless tag policy PT_Corp', 'wlan Gast_Profile policy PP_Gast', 'exit',
               'wireless tag policy PT_Lager', 'wlan Corp_Profile policy PP_Corp', 'exit', 'ap %s' % L2, 'policy-tag PT_Lager']
        self.assertTrue(fixed('05-gast-wlan-lobby', alt).labs.check()['passed'])

    def test_lab06_wrong_order_is_refused_and_changes_nothing(self):
        s = started('06-aufraeumen')
        before = s.wlc.state()
        ok, _, err = s.apply(['no wlan Alt_Profile'])
        self.assertFalse(ok)
        self.assertIn('PT_Alt', err['message'])
        self.assertEqual(s.wlc.state(), before)

    def test_lab06_wiping_the_corp_mapping_fails(self):
        cmds = ['ap %s' % L2, 'no policy-tag', 'exit', 'no wireless tag policy PT_Alt', 'no wlan Alt_Profile',
                'no wireless profile policy PP_Alt', 'wireless tag policy PT_Corp', 'no wlan Corp_Profile policy PP_Corp']
        s = fixed('06-aufraeumen', cmds)
        self.assertEqual(sorted(failed(s)), ['Corp-Zuordnung unverändert', 'Lobby-Laptop weiterhin verbunden, VLAN 20'])


class TestGenerated(unittest.TestCase):
    def test_labs_json_matches_the_generator(self):
        """labs/*.json sind generiert: Wer sie von Hand aendert oder den Generator nicht laufen laesst, faellt hier auf."""
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location('build_labs', os.path.join(here, '..', 'Labs-Quelle', 'build_labs.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            mod.main(tmp)
            fresh = {f: open(os.path.join(tmp, f), encoding='utf-8').read() for f in sorted(os.listdir(tmp))}
        labs_dir = os.path.join(here, '..', 'labs')
        current = {f: open(os.path.join(labs_dir, f), encoding='utf-8').read() for f in sorted(os.listdir(labs_dir)) if f.endswith('.json')}
        self.assertEqual(sorted(fresh), sorted(current))
        for f in fresh:
            self.assertEqual(fresh[f], current[f], f)


class TestLabSession(unittest.TestCase):
    def test_guided_hints_in_order_and_limits(self):
        s = started('01-ssid-nicht-sichtbar')
        pub = s.labs.public()
        self.assertEqual((pub['hintsUsed'], pub['hints'], pub['hintsTotal']), (0, [], 4))
        for k in range(1, 5):
            p = s.labs.hint()
            self.assertEqual((p['hintsUsed'], len(p['hints'])), (k, k))
        self.assertTrue(p['hints'][0].startswith('**Konzept:**') and p['hints'][3].startswith('**Lösung:**'))
        with self.assertRaises(LabError) as cm:
            s.labs.hint()
        self.assertEqual(cm.exception.status, 409)

    def test_public_view_hides_the_solution(self):
        pub = started('03-falscher-schluessel').labs.public()
        for k in ('cause', 'solution', 'solutionCommands', 'startCommands', 'checks', 'worldClients'):
            self.assertNotIn(k, pub)
        self.assertNotIn('Sommer2025', json.dumps(pub))
        for qu in pub['questions']:
            self.assertNotIn('answer', qu)
            self.assertNotIn('explain', qu)

    def test_exam_mode_gives_no_help(self):
        s = started('04-falsches-policy-profile', 'exam')
        for fn in (s.labs.hint, s.labs.solution):
            with self.assertRaises(LabError) as cm:
                fn()
            self.assertEqual(cm.exception.status, 403)
        r = s.labs.check()
        self.assertTrue(all('detail' not in c for c in r['checks']))
        self.assertIsNone(s.labs.answer('q1', 0)['explain'])
        st = s.ui_state()
        self.assertFalse(st['diagAvailable'])
        self.assertTrue(all(c['reasons'] == [] for c in st['clients']))
        g = started('04-falsches-policy-profile', 'guided').ui_state()
        self.assertTrue(g['diagAvailable'] and any(c['reasons'] for c in g['clients']))

    def test_answers_do_not_count_for_passing(self):
        s = fixed('01-ssid-nicht-sichtbar')
        self.assertEqual(s.labs.answer('q1', 0)['correct'], True)
        self.assertEqual(s.labs.answer('q2', 0)['correct'], False)
        r = s.labs.check()
        self.assertEqual(r['questions'], {'right': 1, 'total': 2})
        self.assertTrue(r['passed'])
        with self.assertRaises(LabError):
            s.labs.answer('q1', 9)
        with self.assertRaises(LabError):
            s.labs.answer('gibtsnicht', 0)

    def test_reset_restores_the_start_and_errors(self):
        s = fixed('01-ssid-nicht-sichtbar')
        self.assertTrue(s.labs.check()['passed'])
        s.labs.hint()
        s.labs.reset()
        self.assertFalse(s.labs.check()['passed'])
        self.assertEqual(s.labs.public()['hintsUsed'], 0)
        with self.assertRaises(LabError) as cm:
            s.labs.start('99-gibt-es-nicht')
        self.assertEqual(cm.exception.status, 404)
        with self.assertRaises(LabError):
            s.labs.start('01-ssid-nicht-sichtbar', 'blitz')
        s.labs.stop()
        with self.assertRaises(LabError) as cm:
            s.labs.check()
        self.assertEqual(cm.exception.status, 409)

    def test_starting_a_lab_replaces_the_world(self):
        s = Sim()
        s.apply(['wlan Zufall 7 Test'])
        s.labs.start('02-admin-down')
        self.assertNotIn('Zufall', s.wlc.wlans)
        self.assertEqual([c['mac'] for c in s.world['clients']], ['58bf.eaaa.0001'])
        self.assertEqual(s.catc.devices()[0]['hostname'], 'wlc1')

    def test_labs_are_deterministic(self):
        a, b = fixed('05-gast-wlan-lobby'), fixed('05-gast-wlan-lobby')
        self.assertEqual(a.labs.check(), b.labs.check())
        self.assertEqual(a.wlc.state(), b.wlc.state())


class TestLabApi(unittest.TestCase):
    def setUp(self):
        self.srv, self.sim = serve(0)
        self.base = 'http://127.0.0.1:%d' % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def call(self, path, method='GET', data=None):
        req = urllib.request.Request(self.base + path, method=method, data=json.dumps(data).encode() if data is not None else None)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_flow(self):
        st, body = self.call('/wlc/api/labs')
        self.assertEqual((st, len(body['labs']), body['current']), (200, 6, None))
        self.assertEqual(self.call('/wlc/api/lab/check', 'POST', {})[0], 409)
        st, body = self.call('/wlc/api/lab/start', 'POST', {'id': '01-ssid-nicht-sichtbar', 'mode': 'guided'})
        self.assertEqual((st, body['current']['id']), (200, '01-ssid-nicht-sichtbar'))
        self.assertFalse(self.call('/wlc/api/lab/check', 'POST', {})[1]['passed'])
        self.assertEqual(self.call('/wlc/api/lab/hint', 'POST', {})[1]['current']['hintsUsed'], 1)
        st, body = self.call('/wlc/api/apply', 'POST', {'commands': ['ap %s' % L1, 'policy-tag PT_Corp']})
        self.assertEqual((st, body['ok']), (200, True))
        self.assertTrue(self.call('/wlc/api/lab/check', 'POST', {})[1]['passed'])
        self.assertIn('PT_Corp', self.call('/wlc/api/lab/solution')[1]['solution'])
        self.assertEqual(self.call('/wlc/api/lab/start', 'POST', {'id': 'x'})[0], 404)
        self.assertEqual(self.call('/wlc/api/lab/start', 'POST', {'id': '02-admin-down', 'mode': 'exam'})[0], 200)
        self.assertEqual(self.call('/wlc/api/lab/hint', 'POST', {})[0], 403)
        self.assertEqual(self.call('/wlc/api/lab/solution')[0], 403)
        self.assertFalse(self.call('/wlc/api/state')[1]['diagAvailable'])
        self.assertEqual(self.call('/wlc/api/lab/stop', 'POST', {})[1], {'current': None})


if __name__ == '__main__':
    unittest.main()
