import copy
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from campusprep.server import Sim, serve  # noqa: E402
from campusprep.store import StoreError, check_name  # noqa: E402

LAB = '05-gast-wlan-lobby'


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def sol(s, lab=LAB):
    return s.labs.labs[lab]['solutionCommands']


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)


class TestState(Base):
    def test_roundtrip_of_config_world_lab_session_and_progress(self):
        s = Sim(data_dir=self.dir)
        s.labs.start(LAB, 'guided')
        s.apply(sol(s))
        s.labs.hint()
        s.labs.answer('q1', 1)
        self.assertTrue(s.labs.check()['passed'])
        s.persist()
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.state(), s.wlc.state())
        self.assertEqual(s2.world, s.world)
        self.assertEqual(s2.labs.session, s.labs.session)
        self.assertEqual(s2.labs.progress, s.labs.progress)
        self.assertTrue(s2.labs.check()['passed'], 'das Lab ist nach dem Neustart weiter bestanden')
        self.assertEqual(s2.catc.devices(), s.catc.devices())

    def test_no_temp_files_and_deterministic_content(self):
        s = Sim(data_dir=self.dir)
        s.apply(['wlan P 1 Corp'])
        s.persist()
        first = read(os.path.join(self.dir, 'state.json'))
        s.persist()
        self.assertEqual(read(os.path.join(self.dir, 'state.json')), first)
        self.assertEqual([f for f in os.listdir(self.dir) if f.endswith('.tmp')], [])
        d = json.loads(first)
        self.assertEqual((d['kind'], d['version']), ('campusprep-state', 6))   # 6: RF-Profile und RF Tags; 5: Mobility (Gruppe, Peers); 4: Web-Auth (lokale Benutzer, Login-Listen, Parameter Maps); 3: AAA-Objekte
        # Determinismus: ein zweiter, unabhaengiger Lauf mit denselben Aktionen schreibt dieselben Bytes (keine Zeitstempel)
        with tempfile.TemporaryDirectory() as other:
            s2 = Sim(data_dir=other)
            s2.apply(['wlan P 1 Corp'])
            s2.persist()
            self.assertEqual(read(os.path.join(other, 'state.json')), first)

    def test_garbage_and_foreign_state_are_quarantined_not_loaded(self):
        for content in ('das ist kein json', json.dumps({'kind': 'anderes', 'version': 1}),
                        json.dumps({'kind': 'campusprep-state', 'version': 99, 'world': {}, 'wlc': {}})):
            with self.subTest(content=content[:30]):
                path = os.path.join(self.dir, 'state.json')
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(content)
                s = Sim(data_dir=self.dir)
                self.assertEqual(s.wlc.wlans, {})
                self.assertTrue(os.path.exists(path + '.bad'))
                self.assertFalse(os.path.exists(path))
                os.remove(path + '.bad')

    def test_structurally_broken_config_is_quarantined(self):
        s = Sim(data_dir=self.dir)
        s.apply(['wlan P 1 Corp'])
        d = s.snapshot_all()
        del d['wlc']['wlans']['P']['ssid']
        with open(os.path.join(self.dir, 'state.json'), 'w', encoding='utf-8') as fh:
            json.dump(d, fh)
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.wlans, {})
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'state.json.bad')))

    def test_failed_restore_leaves_the_running_sim_untouched(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('01-ssid-nicht-sichtbar')
        before = (s.snapshot_all(), s.wlc.state())
        bad = copy.deepcopy(before[0])
        del bad['wlc']['wlans']['Corp_Profile']['ssid']
        with self.assertRaises(StoreError):
            s.restore_all(bad)
        with self.assertRaises(StoreError):
            s.restore_all({'kind': 'x'})
        self.assertEqual((s.snapshot_all(), s.wlc.state()), before)

    def test_session_from_a_save_is_sanitised(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('01-ssid-nicht-sichtbar')
        d = s.snapshot_all()
        d['lab'].update(hints=99, answers={'q1': 0, 'q2': 42, 'nix': 1})
        s.restore_all(d)
        self.assertEqual(s.labs.session['hints'], 4)
        self.assertEqual(s.labs.session['answers'], {'q1': 0})
        d['lab'] = {'id': '99-unbekannt', 'mode': 'guided'}
        s.restore_all(d)
        self.assertIsNone(s.labs.session)


class TestMigration(Base):
    def test_version_1_state_and_progress_still_load(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('01-ssid-nicht-sichtbar')
        s.apply(s.labs.labs['01-ssid-nicht-sichtbar']['solutionCommands'])
        s.labs.check()
        st = s.snapshot_all()
        st['version'] = 1
        del st['wlc']['flexProfiles'], st['wlc']['siteTags']
        with open(os.path.join(self.dir, 'state.json'), 'w', encoding='utf-8') as fh:
            json.dump(st, fh)
        with open(os.path.join(self.dir, 'progress.json'), 'w', encoding='utf-8') as fh:
            json.dump({'kind': 'campusprep-progress', 'version': 1, 'labs': s.labs.progress}, fh)
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.state()['wlans'], s.wlc.state()['wlans'])
        self.assertEqual([t['name'] for t in s2.wlc.state()['siteTags']], ['default-site-tag'])
        self.assertEqual([f['name'] for f in s2.wlc.state()['flexProfiles']], ['default-flex-profile'])
        self.assertTrue(s2.labs.check()['passed'])
        self.assertTrue(s2.labs.progress['01-ssid-nicht-sichtbar']['guidedPassed'])
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'state.json.bad')))

    def test_version_2_state_without_aaa_objects_still_loads(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('07-flexconnect-zweigstelle')
        s.apply(s.labs.labs['07-flexconnect-zweigstelle']['solutionCommands'])
        st = s.snapshot_all()
        st['version'] = 2
        for k in ('radiusServers', 'aaaGroups', 'aaaLists'):
            del st['wlc'][k]
        del st['world']['radius']
        with open(os.path.join(self.dir, 'state.json'), 'w', encoding='utf-8') as fh:
            json.dump(st, fh)
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.state()['radiusServers'], [])
        self.assertEqual(s2.world['radius']['servers'][0]['ip'], '10.10.0.50', 'Standard-RADIUS-Server wird ergaenzt')
        self.assertTrue(s2.labs.check()['passed'])
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'state.json.bad')))

    def test_version_3_state_without_web_auth_objects_still_loads(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('09-radius-shared-secret')
        s.apply(s.labs.labs['09-radius-shared-secret']['solutionCommands'])
        st = s.snapshot_all()
        st['version'] = 3
        for k in ('localUsers', 'loginLists', 'authzDefaultLocal', 'webauthMaps'):
            del st['wlc'][k]
        with open(os.path.join(self.dir, 'state.json'), 'w', encoding='utf-8') as fh:
            json.dump(st, fh)
        s2 = Sim(data_dir=self.dir)
        w = s2.wlc.state()
        self.assertEqual((w['localUsers'], w['loginLists'], w['authzDefaultLocal']), ([], [], False))
        self.assertEqual([m['name'] for m in w['webauthMaps']], ['global'], 'Parameter Map global wird ergaenzt')
        self.assertTrue(s2.labs.check()['passed'])
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'state.json.bad')))

    def test_version_4_state_without_mobility_still_loads(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('09-radius-shared-secret')
        s.apply(s.labs.labs['09-radius-shared-secret']['solutionCommands'])
        st = s.snapshot_all()
        st['version'] = 4
        for k in ('mobilityGroup', 'mobilityPeers'):
            del st['wlc'][k]
        del st['world']['mobility']
        with open(os.path.join(self.dir, 'state.json'), 'w', encoding='utf-8') as fh:
            json.dump(st, fh)
        s2 = Sim(data_dir=self.dir)
        w = s2.wlc.state()
        self.assertEqual((w['mobilityGroup'], w['mobilityPeers']), ('default', []))
        self.assertEqual(s2.world['mobility']['controllers'][0]['name'], 'wlc2', 'Standard-Gegenseite wird ergaenzt')
        self.assertTrue(s2.labs.check()['passed'])
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'state.json.bad')))

    def test_version_5_state_without_rf_objects_still_loads(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('15-mobility-einrichten')
        s.apply(s.labs.labs['15-mobility-einrichten']['solutionCommands'])
        st = s.snapshot_all()
        st['version'] = 5
        for k in ('rfProfiles', 'rfTags'):
            del st['wlc'][k]
        with open(os.path.join(self.dir, 'state.json'), 'w', encoding='utf-8') as fh:
            json.dump(st, fh)
        s2 = Sim(data_dir=self.dir)
        w = s2.wlc.state()
        self.assertEqual((w['rfProfiles'], [t['name'] for t in w['rfTags']]), ([], ['default-rf-tag']))
        self.assertTrue(s2.labs.check()['passed'])
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'state.json.bad')))

    def test_rf_config_roundtrips(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('17-rf-lobby-einrichten')
        s.apply(s.labs.labs['17-rf-lobby-einrichten']['solutionCommands'])
        s.persist()
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.state(), s.wlc.state())
        self.assertTrue(s2.labs.check()['passed'])

    def test_mobility_config_roundtrips(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('15-mobility-einrichten')
        s.apply(s.labs.labs['15-mobility-einrichten']['solutionCommands'])
        s.persist()
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.state(), s.wlc.state())
        self.assertEqual(s2.world['mobility'], s.world['mobility'])
        self.assertTrue(s2.labs.check()['passed'])

    def test_web_auth_config_roundtrips(self):
        s = Sim(data_dir=self.dir)
        s.apply(['username gast1 privilege 0 password 0 Gast#1', 'aaa authentication login WEBAUTH local', 'aaa authorization network default local',
                 'parameter-map type webauth PM1', 'type webauth', 'virtual-ip ipv4 192.0.2.5', 'exit',
                 'wlan Guest 2 Gast', 'security web-auth', 'security web-auth authentication-list WEBAUTH', 'security web-auth parameter-map PM1'])
        s.persist()
        before = s.wlc.state()
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.state(), before)
        self.assertTrue(before['authzDefaultLocal'])
        self.assertEqual(before['wlans'][0]['webAuthMap'], 'PM1')

    def test_aaa_config_roundtrips(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('09-radius-shared-secret')
        s.persist()
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.state(), s.wlc.state())
        self.assertEqual(s2.world['radius'], s.world['radius'])

    def test_flex_config_roundtrips(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('07-flexconnect-zweigstelle')
        s.apply(s.labs.labs['07-flexconnect-zweigstelle']['solutionCommands'])
        s.persist()
        s2 = Sim(data_dir=self.dir)
        self.assertEqual(s2.wlc.state(), s.wlc.state())
        self.assertTrue(s2.labs.check()['passed'])


class TestNamedSaves(Base):
    def test_names_are_validated(self):
        for bad in ('', '../x', 'a b', 'x' * 41, '.versteckt', 'a/b', None, 5, 'ü'):
            with self.assertRaises(StoreError, msg=repr(bad)):
                check_name(bad)
        for good in ('stand1', 'Lab-01_vor.Hint', 'x' * 40):
            self.assertEqual(check_name(good), good)

    def test_save_list_load_delete(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('02-admin-down')
        s.store.save_named('vor-der-loesung', s.snapshot_all())
        s.apply(sol(s, '02-admin-down'))
        self.assertTrue(s.labs.check()['passed'])
        s.store.save_named('geloest', s.snapshot_all())
        listed = s.store.list_named()
        self.assertEqual([x['name'] for x in listed], ['geloest', 'vor-der-loesung'])
        self.assertTrue(all(x['lab'] == '02-admin-down' for x in listed))
        progress = copy.deepcopy(s.labs.progress)
        s.restore_all(s.store.load_named('vor-der-loesung'))
        self.assertFalse(s.labs.check()['passed'], 'der Stand vor der Lösung ist wieder da')
        self.assertEqual(s.labs.session['id'], '02-admin-down')
        self.assertEqual(s.labs.progress['02-admin-down']['passed'], progress['02-admin-down']['passed'], 'Fortschritt gehört nicht zum Stand')
        s.restore_all(s.store.load_named('geloest'))
        self.assertTrue(s.labs.check()['passed'])
        s.store.delete_named('geloest')
        self.assertEqual([x['name'] for x in s.store.list_named()], ['vor-der-loesung'])

    def test_unknown_and_broken_saves(self):
        s = Sim(data_dir=self.dir)
        for fn in (s.store.load_named, s.store.delete_named):
            with self.assertRaises(StoreError) as cm:
                fn('gibtsnicht')
            self.assertEqual(cm.exception.status, 404)
        with open(os.path.join(self.dir, 'saves', 'kaputt.json'), 'w', encoding='utf-8') as fh:
            fh.write('{')
        self.assertEqual(s.store.list_named(), [{'name': 'kaputt', 'lab': None, 'wlans': 0, 'broken': True}])
        with self.assertRaises(StoreError):
            s.store.load_named('kaputt')


class TestProgress(Base):
    def test_guided_and_exam_passes_are_tracked_separately(self):
        s = Sim(data_dir=self.dir)
        lab = '03-falscher-schluessel'
        s.labs.start(lab, 'guided')
        self.assertEqual(s.labs.list()[2]['progress']['starts'], 1)
        s.labs.check()
        s.labs.hint()
        s.labs.hint()
        s.apply(sol(s, lab))
        s.labs.answer('q1', 0)
        s.labs.check()
        p = s.labs.progress[lab]
        self.assertEqual((p['passed'], p['guidedPassed'], p['examPassed'], p['bestHints'], p['checks'], p['questionsRight']),
                         (True, True, False, 2, 2, 1))
        s.labs.start(lab, 'exam')
        s.apply(sol(s, lab))
        s.labs.check()
        p = s.labs.progress[lab]
        self.assertEqual((p['examPassed'], p['bestHints'], p['starts']), (True, 2, 2))
        s.labs.start(lab, 'guided')
        s.apply(sol(s, lab))
        s.labs.check()
        self.assertEqual(s.labs.progress[lab]['bestHints'], 0, 'bestHints behält das Minimum')

    def test_failed_checks_do_not_mark_as_passed_and_reset(self):
        s = Sim(data_dir=self.dir)
        s.labs.start('01-ssid-nicht-sichtbar')
        s.labs.check()
        self.assertFalse(s.labs.progress['01-ssid-nicht-sichtbar']['passed'])
        self.assertEqual(s.labs.list()[1]['progress'], {'starts': 0, 'checks': 0, 'passed': False, 'guidedPassed': False,
                                                         'examPassed': False, 'bestHints': None, 'questionsRight': 0})
        s.labs.reset_progress()
        self.assertEqual(s.labs.progress, {})

    def test_corrupt_progress_is_quarantined(self):
        with open(os.path.join(self.dir, 'progress.json'), 'w', encoding='utf-8') as fh:
            fh.write('[1,2')
        s = Sim(data_dir=self.dir)
        self.assertEqual(s.labs.progress, {})
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'progress.json.bad')))


class TestHttp(Base):
    def start(self, data_dir):
        self.srv, self.sim = serve(0, data_dir=data_dir)
        self.base = 'http://127.0.0.1:%d' % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()

    def call(self, path, method='GET', data=None):
        req = urllib.request.Request(self.base + path, method=method, data=json.dumps(data).encode() if data is not None else None)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_state_survives_a_server_restart_without_explicit_save(self):
        self.start(self.dir)
        try:
            self.assertTrue(self.call('/wlc/api/state')[1]['persistent'])
            self.call('/wlc/api/lab/start', 'POST', {'id': '03-falscher-schluessel', 'mode': 'guided'})
            self.call('/wlc/api/apply', 'POST', {'commands': ['wlan Corp_Profile 1 Corp', 'security wpa psk set-key ascii 0 Sommer2026']})
            self.call('/wlc/api/lab/hint', 'POST', {})
            self.assertTrue(self.call('/wlc/api/lab/check', 'POST', {})[1]['passed'])
        finally:
            self.stop()
        self.start(self.dir)
        try:
            cur = self.call('/wlc/api/labs')[1]
            self.assertEqual((cur['current']['id'], cur['current']['hintsUsed']), ('03-falscher-schluessel', 1))
            row = next(x for x in cur['labs'] if x['id'] == '03-falscher-schluessel')
            self.assertTrue(row['progress']['guidedPassed'])
            self.assertTrue(self.call('/wlc/api/lab/check', 'POST', {})[1]['passed'])
        finally:
            self.stop()

    def test_cli_changes_are_persisted_too(self):
        self.start(self.dir)
        try:
            for line in ('configure terminal', 'wlan P 1 Corp', 'end'):
                self.call('/wlc/cli', 'POST', {'command': line})
        finally:
            self.stop()
        self.assertIn('P', Sim(data_dir=self.dir).wlc.wlans)

    def test_saves_api(self):
        self.start(self.dir)
        try:
            self.call('/wlc/api/apply', 'POST', {'commands': ['wlan P 1 Corp']})
            st, body = self.call('/wlc/api/saves', 'POST', {'name': 'mit-wlan'})
            self.assertEqual((st, [x['name'] for x in body['saves']]), (200, ['mit-wlan']))
            self.call('/wlc/api/apply', 'POST', {'commands': ['no wlan P']})
            self.assertEqual(self.call('/wlc/api/state')[1]['wlans'], [])
            self.assertEqual(self.call('/wlc/api/saves/load', 'POST', {'name': 'mit-wlan'})[0], 200)
            self.assertEqual(self.call('/wlc/api/state')[1]['wlans'][0]['profile'], 'P')
            self.assertEqual(self.call('/wlc/api/saves/load', 'POST', {'name': 'nix'})[0], 404)
            self.assertEqual(self.call('/wlc/api/saves/delete', 'POST', {'name': 'mit-wlan'})[1], {'saves': []})
        finally:
            self.stop()

    def test_path_traversal_in_save_names(self):
        self.start(self.dir)
        try:
            for bad in ('../evil', '..\\evil', '/etc/x', 'a/b', ''):
                self.assertEqual(self.call('/wlc/api/saves', 'POST', {'name': bad})[0], 400, bad)
            self.assertFalse(os.path.exists(os.path.join(self.dir, 'evil.json')))
            self.assertFalse(os.path.exists(os.path.join(self.dir, '..', 'evil.json')))
            self.assertEqual(self.call('/wlc/api/saves/load', 'POST', {'name': '../state'})[0], 400)
        finally:
            self.stop()

    def test_progress_reset_and_ephemeral_mode(self):
        self.start(self.dir)
        try:
            self.call('/wlc/api/lab/start', 'POST', {'id': '01-ssid-nicht-sichtbar'})
            self.call('/wlc/api/lab/check', 'POST', {})
            self.assertEqual(next(x for x in self.call('/wlc/api/labs')[1]['labs'])['progress']['starts'], 1)
            labs = self.call('/wlc/api/progress/reset', 'POST', {})[1]['labs']
            self.assertEqual(labs[0]['progress']['starts'], 0)
        finally:
            self.stop()
        self.start(None)
        try:
            self.assertFalse(self.call('/wlc/api/state')[1]['persistent'])
            self.assertEqual(self.call('/wlc/api/saves')[0], 409)
            self.assertEqual(self.call('/wlc/api/saves', 'POST', {'name': 'x'})[0], 409)
        finally:
            self.stop()


if __name__ == '__main__':
    unittest.main()
