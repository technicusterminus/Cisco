#!/usr/bin/env python3
"""Spielt Szenarien ueber den echten Python-HTTP-Server ab und zeichnet Status, Antworten und Endzustand auf.

tests/parity/parity.js spielt dieselben Schritte gegen static/engine.js ab (die Engine der eigenstaendigen Browser-Variante)
und vergleicht. Es gibt keine eingecheckte Fixture-Datei: Beide Engines werden bei jedem Lauf frisch verglichen.

    python3 tests/parity/make_fixtures.py OUT.json
"""
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, ROOT)
from campusprep.server import serve  # noqa: E402

L1, L2 = 'a4b2.32aa.0001', 'a4b2.32aa.0002'


def lab_ids():
    return sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, 'labs')) if f.endswith('.json'))


def lab_json(lab_id):
    with open(os.path.join(ROOT, 'labs', lab_id + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


class Recorder:
    def __init__(self, name, persistent=True):
        self.name, self.persistent, self.steps = name, persistent, []
        self._tmp = tempfile.TemporaryDirectory() if persistent else None
        self.srv, self.sim = serve(0, data_dir=self._tmp.name if persistent else None)
        self.base = 'http://127.0.0.1:%d' % self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def call(self, method, path, body=None, raw=False):
        """raw=True: body wird als JSON-Text gesendet, auch None (= JSON null). Sonst bedeutet None: kein Body."""
        data = json.dumps(body).encode() if (body is not None or raw) else None
        req = urllib.request.Request(self.base + path, method=method, data=data)
        try:
            with urllib.request.urlopen(req) as r:
                status, text = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read()
        out = json.loads(text)
        step = {'m': method, 'p': path, 'status': status, 'resp': out}
        if body is not None or raw:
            step['b'] = body
        self.steps.append(step)
        return out

    def cli(self, *lines):
        return [self.call('POST', '/wlc/cli', {'command': x}) for x in lines]

    def apply(self, cmds):
        return self.call('POST', '/wlc/api/apply', {'commands': list(cmds)})

    def finish(self):
        snap = self.sim.snapshot_all()
        prog = json.loads(json.dumps(self.sim.labs.progress))
        self.srv.shutdown()
        self.srv.server_close()
        if self._tmp:
            self._tmp.cleanup()
        return {'name': self.name, 'persistent': self.persistent, 'steps': self.steps, 'snapshot': snap, 'progress': prog}


# ---------------------------------------------------------------------------------------------------------------
CORP = ['wlan Corp_Profile 1 Corp', 'security wpa akm psk', 'security wpa psk set-key ascii 0 Sommer2026', 'no shutdown', 'exit',
        'wireless profile policy PP_Corp', 'vlan 20', 'no shutdown', 'exit',
        'wireless tag policy PT_Corp', 'wlan Corp_Profile policy PP_Corp', 'exit']
FLEX = ['wireless profile flex FP1', 'native-vlan-id 1', 'vlan-name CORP_LOCAL', 'vlan-id 20', 'vlan-name GAST', 'vlan-id 99', 'exit', 'exit',
        'wireless tag site ST1', 'no local-site', 'flex-profile FP1', 'exit']


def all_shows(r):
    r.cli('end', 'show wlan summary', 'show ap summary', 'show ap tag summary', 'show wireless client summary',
          'show wireless profile policy summary', 'show wireless profile flex summary', 'show wireless tag site summary',
          'show wireless stats ap join summary', 'show  wlan   summary')


def sc_cli_errors():
    r = Recorder('cli-exec-and-config-errors')
    r.cli('', '   ', 'foo', 'show wlan summary', 'conf t', 'exit', 'configure t', 'end', 'configure terminal', 'no', 'bogus', 'no bogus',
          'wlan A 0 x', 'wlan A 4097 x', 'wlan A x y', 'wlan A 1', 'wlan A 1 Corp x', 'wlan A 0001 Corp', 'wlan B 1 Other', 'wlan B 2 Other',
          'no', 'bogus', 'shutdown', 'no shutdown', 'security wpa akm psk', 'security wpa akm dot1x', 'security wpa psk set-key ascii 0 geheim',
          'security wpa psk set-key ascii 0', 'security wpa psk set-key hex 0 abc', 'no security wpa akm psk', 'end', 'show wlan summary',
          'configure terminal', 'wlan A 1 Corp', 'do show wlan summary', 'do show ap summary', 'do bogus', 'exit', 'exit', 'exit')
    all_shows(r)
    return r.finish()


def sc_cli_policy_ptag_ap():
    r = Recorder('cli-policy-ptag-ap')
    r.cli('configure terminal', 'wireless profile policy PP', 'vlan 20', 'vlan bad!name', 'vlan', 'vlan a b', 'central switching', 'no central switching',
          'no central', 'central', 'description a b   c', 'description', 'no description x', 'shutdown', 'no shutdown', 'bogus', 'exit',
          'wireless tag policy PT', 'wlan A policy PP', 'wlan A policy', 'wlan', 'no wlan A policy PP', 'no wlan A policy PP', 'wlan A policy PP', 'bogus', 'exit',
          'ap 1234', 'ap not-a-mac', 'ap A4B2-32AA-0001', 'policy-tag PT', 'policy-tag', 'no policy-tag', 'no policy-tag PT', 'site-tag nonexist',
          'site-tag default-site-tag', 'no site-tag', 'bogus', 'exit', 'ap a4b232aa0002', 'policy-tag PT', 'end')
    all_shows(r)
    r.cli('configure terminal', 'no wireless tag policy PT', 'no wireless profile policy PP', 'ap ' + L2, 'no policy-tag', 'exit',
          'no wireless tag policy PT', 'no wireless tag policy PT', 'no wireless profile policy PP', 'no wireless profile policy PP',
          'no wireless tag policy default-policy-tag', 'no wlan Gibtsnicht', 'no wlan', 'no wireless', 'end')
    return r.finish()


def sc_cli_flex():
    r = Recorder('cli-flex-and-site-tags')
    r.cli('configure terminal', 'wireless profile flex bad!name', 'wireless profile flex FP1', 'vlan-id 10', 'native-vlan-id 0', 'native-vlan-id 5000',
          'native-vlan-id x', 'native-vlan-id 7', 'no native-vlan-id', 'vlan-name bad!name', 'no vlan-name NIX', 'vlan-name A', 'vlan-id 5000', 'vlan-id x',
          'vlan-id 30', 'vlan-name B', 'vlan-id 31', 'no vlan-id', 'vlan-id 32', 'description  Mein  Profil', 'description', 'native-vlan-id 4', 'vlan-id 11',
          'vlan-name A', 'no vlan-name B', 'exit', 'vlan-name C', 'bogus', 'end')
    all_shows(r)
    r.cli('configure terminal', 'wireless tag site ST1', 'flex-profile FP1', 'no flex-profile', 'local-site', 'no local-site', 'flex-profile gibtsnicht',
          'flex-profile FP1', 'no flex-profile', 'flex-profile', 'description  Zweigstelle', 'description', 'bogus', 'exit',
          'wireless tag site bad!name', 'wireless tag site ST2', 'no local-site', 'exit', 'ap ' + L1, 'site-tag ST1', 'exit',
          'ap ' + L2, 'site-tag ST2', 'exit', 'no wireless profile flex FP1', 'no wireless tag site ST1', 'no wireless tag site ST2',
          'no wireless profile flex default-flex-profile', 'no wireless tag site default-site-tag', 'no wireless profile flex NIX', 'no wireless tag site NIX',
          'ap ' + L1, 'no site-tag', 'exit', 'ap ' + L2, 'no site-tag', 'exit', 'no wireless tag site ST1', 'no wireless tag site ST2', 'no wireless profile flex FP1', 'end')
    all_shows(r)
    return r.finish()


def sc_names():
    r = Recorder('cli-unusual-names')
    r.cli('configure terminal', 'wlan Gäste 1 Gast', 'security wpa akm psk', 'exit', 'wlan 123 2 Gast', 'exit', 'wlan constructor 3 Gast', 'exit',
          'wlan __proto__ 4 Gast', 'exit', 'wireless profile policy 123', 'vlan 20', 'no shutdown', 'exit', 'wireless profile policy constructor', 'vlan 21', 'exit',
          'wireless profile policy __proto__', 'exit', 'wireless tag policy __proto__', 'wlan Gäste policy 123', 'wlan 123 policy constructor', 'wlan __proto__ policy __proto__', 'exit',
          'wireless tag policy it\'s', 'exit', 'wireless profile flex 20', 'vlan-name 20', 'vlan-id 20', 'vlan-name __proto__', 'vlan-id 21', 'exit', 'exit',
          'wireless tag site 99', 'no local-site', 'flex-profile 20', 'exit', 'ap ' + L1, 'policy-tag __proto__', 'site-tag 99', 'end')
    all_shows(r)
    r.call('GET', '/wlc/api/state')
    r.cli('configure terminal', 'wlan Z 9 Corp', 'wlan Y 10 Corp', 'end')       # doppelte SSID: das erste Profil gilt
    r.call('GET', '/wlc/api/state')
    return r.finish()


def decide_cases():
    pol = lambda vlan, central: ['wireless profile policy PP', 'vlan %s' % vlan, 'central switching' if central else 'no central switching', 'no shutdown', 'exit']
    base = ['wlan P 1 Corp', 'no shutdown', 'exit']
    tag = ['wireless tag policy PT', 'wlan P policy PP', 'exit']
    flex = ['wireless profile flex FP', 'vlan-name CORP_LOCAL', 'vlan-id 20', 'exit', 'exit', 'wireless tag site ST', 'no local-site', 'flex-profile FP', 'exit']
    ap = lambda site: ['ap ' + L1, 'policy-tag PT'] + (['site-tag ST'] if site else []) + ['exit']
    return {
        'central-ok': base + pol(20, True) + tag + ap(False),
        'central-name': base + pol('CORP_LOCAL', True) + tag + ap(False),
        'local-on-local-mode-ap': base + pol('CORP_LOCAL', False) + tag + flex + ap(False),
        'local-ok': base + pol('CORP_LOCAL', False) + tag + flex + ap(True),
        'local-name-case': base + pol('Corp_Local', False) + tag + flex + ap(True),
        'local-numeric-by-id': base + pol(20, False) + tag + flex + ap(True),
        'local-numeric-unknown': base + pol(77, False) + tag + flex + ap(True),
        'local-native': ['wireless profile flex FP', 'native-vlan-id 7', 'exit', 'wireless tag site ST', 'no local-site', 'flex-profile FP', 'exit'] + base + pol(7, False) + tag + ap(True),
        'local-vlan-without-id': ['wireless profile flex FP', 'vlan-name CORP_LOCAL', 'exit', 'exit', 'wireless tag site ST', 'no local-site', 'flex-profile FP', 'exit'] + base + pol('CORP_LOCAL', False) + tag + ap(True),
        'default-flex-profile': ['wireless tag site ST', 'no local-site', 'exit'] + base + pol('CORP_LOCAL', False) + tag + ap(True),
        'wlan-down': ['wlan P 1 Corp', 'exit'] + pol(20, True) + tag + ap(False),
        'policy-down': base + ['wireless profile policy PP', 'vlan 20', 'exit'] + tag + ap(False),
        'ssid-unknown': pol(20, True) + tag + ap(False),
        'tag-missing-wlan': base + pol(20, True) + ['wireless tag policy PT', 'exit'] + ap(False),
        'policy-missing': base + ['wireless tag policy PT', 'wlan P policy NOPE', 'exit'] + ap(False),
        'psk-ok': ['wlan P 1 Corp', 'security wpa akm psk', 'security wpa psk set-key ascii 0 Sommer2026', 'no shutdown', 'exit'] + pol(20, True) + tag + ap(False),
        'psk-wrong': ['wlan P 1 Corp', 'security wpa akm psk', 'security wpa psk set-key ascii 0 Anders', 'no shutdown', 'exit'] + pol(20, True) + tag + ap(False),
    }


def sc_decide():
    """Je Fall ein eigener Server: sauberer Ausgangszustand ohne Reste eines Lab-Starts."""
    out = []
    for name, cmds in decide_cases().items():
        r = Recorder('decide-' + name)
        r.apply(cmds)
        r.call('GET', '/wlc/api/state')
        r.cli('end', 'show wireless client summary', 'show ap tag summary')
        out.append(r.finish())
    return out


def sc_cli_aaa():
    r = Recorder('cli-aaa-objects')
    r.cli('configure terminal', 'aaa new-model', 'no aaa new-model', 'aaa new-model x', 'radius server bad!name', 'radius server RS1', 'address ipv4 300.1.1.1',
          'address ipv4 1.2.3', 'address ipv6 ::1', 'address ipv4 10.0.0.1 auth-port 0 acct-port 1813', 'address ipv4 10.0.0.1 auth-port x acct-port 1813',
          'address ipv4 10.0.0.1 port 1812 acct-port 1813', 'address ipv4 10.0.0.1 auth-port 1812', 'address', 'key 7 abc', 'key', 'key 0', 'timeout 0', 'timeout 5000',
          'retransmit 101', 'retransmit x', 'retransmit', 'no key', 'no address ipv4 10.0.0.1', 'bogus', 'address ipv4 10.0.0.1', 'address ipv4 10.0.0.2 auth-port 1645 acct-port 1646',
          'key 0 geheim', 'key anders', 'timeout 7', 'retransmit 0', 'exit', 'radius server RS2', 'address ipv4 10.0.0.9', 'key x', 'end', 'show aaa servers',
          'configure terminal', 'aaa group server radius bad!name', 'aaa group server radius G', 'server name NIX', 'server name RS1', 'server name RS1', 'server name RS2',
          'no server name NIX', 'no server name RS2', 'server name RS2', 'bogus', 'exit', 'aaa authentication dot1x L group NIX', 'aaa authentication dot1x bad!name group G',
          'aaa authentication dot1x L group', 'aaa authentication dot1x L group G', 'aaa authentication dot1x L2 group G', 'wlan W 1 X', 'security wpa akm dot1x',
          'security dot1x authentication-list L', 'security dot1x authentication-list', 'no security dot1x authentication-list', 'security dot1x authentication-list L',
          'no security wpa akm dot1x', 'security wpa akm dot1x', 'exit', 'wireless profile policy PP', 'aaa-override', 'no aaa-override', 'aaa-override x', 'exit',
          'no radius server RS1', 'no aaa group server radius G', 'no aaa authentication dot1x L', 'no aaa authentication dot1x L2', 'no aaa group server radius G', 'end',
          'show wlan summary', 'show aaa servers', 'configure terminal', 'wlan W 1 X', 'no security dot1x authentication-list', 'exit', 'no aaa authentication dot1x L',
          'no aaa group server radius G', 'no radius server RS1', 'no radius server RS2', 'no radius server NIX', 'no aaa group server radius NIX',
          'no aaa authentication dot1x NIX', 'end', 'show aaa servers')
    r.call('GET', '/wlc/api/state')
    return r.finish()


def aaa_variants():
    flex = ['wireless profile policy PP_Corp', 'no central switching', 'aaa-override', 'vlan LOKAL', 'exit', 'wireless profile flex FP', 'vlan-name LOKAL', 'vlan-id 20', 'exit', 'exit',
            'wireless tag site ST', 'no local-site', 'flex-profile FP', 'exit', 'ap ' + L1, 'site-tag ST']
    rs2 = lambda key='RadiusKey1', ip='10.10.0.51': ['radius server RS2', 'address ipv4 %s' % ip, 'key %s' % key, 'exit', 'aaa group server radius RG1', 'server name RS2']
    w = lambda *c: ['wlan Corp_1X 1 CorpDot1x'] + list(c)
    return [
        ('09-radius-shared-secret', 'fixed', ['radius server RS1', 'key RadiusKey1']),
        ('09-radius-shared-secret', 'secret-case', ['radius server RS1', 'key radiuskey1']),
        ('09-radius-shared-secret', 'secret-key-0', ['radius server RS1', 'key 0 RadiusKey1']),
        ('09-radius-shared-secret', 'no-authlist', w('no security dot1x authentication-list')),
        ('09-radius-shared-secret', 'typo-list', w('security dot1x authentication-list TIPPFEHLER')),
        ('09-radius-shared-secret', 'port', ['radius server RS1', 'address ipv4 10.10.0.50 auth-port 1645 acct-port 1646', 'key RadiusKey1']),
        ('09-radius-shared-secret', 'wrong-ip', ['radius server RS1', 'address ipv4 10.10.0.99', 'key RadiusKey1']),
        ('09-radius-shared-secret', 'no-address', ['radius server RS1', 'address ipv4 0.0.0.0']),
        ('09-radius-shared-secret', 'empty-group', ['aaa group server radius RG1', 'no server name RS1']),
        ('09-radius-shared-secret', 'second-server', rs2('RadiusKey1', '10.10.0.50')),
        ('09-radius-shared-secret', 'open-wlan', w('no security wpa akm dot1x')),
        ('09-radius-shared-secret', 'psk-wlan', w('security wpa akm psk', 'security wpa psk set-key ascii 0 geheim')),
        ('09-radius-shared-secret', 'wlan-down', w('shutdown')),
        ('10-aaa-override-vlan', 'override', ['wireless profile policy PP_Corp', 'aaa-override']),
        ('10-aaa-override-vlan', 'override-then-off', ['wireless profile policy PP_Corp', 'aaa-override', 'no aaa-override']),
        ('10-aaa-override-vlan', 'policy-vlan-30', ['wireless profile policy PP_Corp', 'vlan 30']),
        ('10-aaa-override-vlan', 'override-name-vlan', ['wireless profile policy PP_Corp', 'aaa-override', 'vlan LOKAL']),
        ('10-aaa-override-vlan', 'override-local-switching', flex),
        ('10-aaa-override-vlan', 'override-local-switching-vlans', flex + ['wireless profile flex FP', 'vlan-name V30', 'vlan-id 30', 'vlan-name V40', 'vlan-id 40']),
        ('11-radius-redundanz', 'second-server', rs2()),
        ('11-radius-redundanz', 'repoint-first', ['radius server RS1', 'address ipv4 10.10.0.51']),
        ('11-radius-redundanz', 'second-wrong-key', rs2('Falsch')),
        ('11-radius-redundanz', 'second-first', rs2() + ['no server name RS1', 'server name RS1']),
        ('11-radius-redundanz', 'new-group', ['radius server RS2', 'address ipv4 10.10.0.51', 'key RadiusKey1', 'exit', 'aaa group server radius RG2', 'server name RS1', 'server name RS2', 'exit',
                                             'aaa authentication dot1x L2 group RG2', 'wlan Corp_1X 1 CorpDot1x', 'security dot1x authentication-list L2']),
        ('11-radius-redundanz', 'nas-missing-none', rs2() + ['radius server RS2', 'address ipv4 10.10.0.52']),
    ]


def sc_aaa_variants():
    out = []
    for lab, name, cmds in aaa_variants():
        r = Recorder('aaa-%s-%s' % (lab[:2], name))
        r.call('POST', '/wlc/api/lab/start', {'id': lab, 'mode': 'guided'})
        r.apply(cmds)
        r.call('GET', '/wlc/api/state')
        r.cli('end', 'show aaa servers', 'show wireless client summary', 'show wlan summary')
        r.call('POST', '/wlc/api/lab/check', {})
        out.append(r.finish())
    return out


def sc_cli_webauth():
    r = Recorder('cli-webauth-objects')
    r.cli('configure terminal', 'username', 'username a', 'username a password', 'username a password 0', 'username a password 0 pw1 extra', 'username bad!name password pw',
          'username a password pw1', 'username b password 0 pw2', 'username c privilege 0 password pw3', 'username d privilege 15 password 0 pw4',
          'username e privilege 99 password pw', 'username e privilege x password pw', 'username f secret pw', 'username g password 7 abc', 'username a password neu',
          'no username', 'no username nix', 'no username b', 'no username b',
          'aaa authentication login', 'aaa authentication login L', 'aaa authentication login L local', 'aaa authentication login bad!name local',
          'aaa authentication login L2 group RG', 'aaa authentication login L3 local extra', 'no aaa authentication login', 'no aaa authentication login NIX',
          'aaa authorization network default local', 'aaa authorization network default group RG', 'aaa authorization network x local', 'aaa authorization network default',
          'no aaa authorization network default local', 'no aaa authorization network default', 'aaa authorization network default local',
          'parameter-map type webauth', 'parameter-map type webauth bad!name', 'parameter-map type consent PM', 'parameter-map type webauth PM', 'type', 'type consent',
          'type webauth', 'type webauth x', 'virtual-ip', 'virtual-ip ipv4', 'virtual-ip ipv4 300.1.1.1', 'virtual-ip ipv6 ::1', 'virtual-ip ipv4 192.0.2.7', 'no virtual-ip ipv4',
          'virtual-ip ipv4 192.0.2.8', 'bogus', 'no bogus', 'exit', 'parameter-map type webauth global', 'virtual-ip ipv4 192.0.2.99', 'exit',
          'wlan W 1 X', 'security web-auth', 'security web-auth x', 'security web-auth authentication-list', 'security web-auth authentication-list L',
          'security web-auth parameter-map', 'security web-auth parameter-map PM', 'security web-auth parameter-map NIX', 'no security web-auth parameter-map',
          'security web-auth parameter-map PM', 'exit', 'no aaa authentication login L', 'no parameter-map type webauth PM', 'no parameter-map type webauth global',
          'wlan W 1 X', 'no security web-auth authentication-list', 'security web-auth authentication-list L', 'no security web-auth', 'exit',
          'no aaa authentication login L', 'no parameter-map type webauth PM', 'no parameter-map type webauth PM', 'end',
          'show wlan summary', 'show aaa servers', 'show wireless client summary')
    r.call('GET', '/wlc/api/state')
    return r.finish()


WEB_BASE = ['wlan Guest 2 Gast', 'no shutdown', 'exit', 'wireless profile policy PP_Guest', 'vlan 99', 'no shutdown', 'exit',
            'wireless tag policy PT_Guest', 'wlan Guest policy PP_Guest', 'exit', 'ap ' + L1, 'policy-tag PT_Guest', 'exit']
WEB_FULL = ['username gast1 privilege 0 password 0 Gast#1', 'aaa authentication login WEBAUTH local', 'aaa authorization network default local',
            'wlan Guest 2 Gast', 'security web-auth', 'security web-auth authentication-list WEBAUTH', 'security web-auth parameter-map global', 'exit']


def web_variants():
    w = lambda *c: ['wlan Guest 2 Gast'] + list(c) + ['exit']
    return [
        ('12-webauth-authorization', 'fixed', ['aaa authorization network default local']),
        ('12-webauth-authorization', 'authz-then-removed', ['aaa authorization network default local', 'no aaa authorization network default local']),
        ('12-webauth-authorization', 'web-auth-off', w('no security web-auth')),
        ('12-webauth-authorization', 'no-list', w('no security web-auth authentication-list')),
        ('12-webauth-authorization', 'typo-list', w('security web-auth authentication-list TIPPFEHLER') + ['aaa authorization network default local']),
        ('12-webauth-authorization', 'no-map', w('no security web-auth parameter-map') + ['aaa authorization network default local']),
        ('12-webauth-authorization', 'user-removed', ['aaa authorization network default local', 'no username gast1']),
        ('12-webauth-authorization', 'user-new-password', ['aaa authorization network default local', 'username gast1 password Anders#1']),
        ('12-webauth-authorization', 'wlan-down', ['aaa authorization network default local'] + w('shutdown')),
        ('12-webauth-authorization', 'psk-on-top', ['aaa authorization network default local'] + w('security wpa akm psk', 'security wpa psk set-key ascii 0 Sommer2026')),
        ('12-webauth-authorization', 'map-no-vip', ['parameter-map type webauth PM9', 'type webauth', 'exit', 'aaa authorization network default local'] + w('security web-auth parameter-map PM9')),
        ('13-webauth-einrichten', 'fixed', WEB_FULL),
        ('13-webauth-einrichten', 'no-user', [c for c in WEB_FULL if not c.startswith('username')]),
        ('13-webauth-einrichten', 'no-list', [c for c in WEB_FULL if 'login' not in c]),
        ('13-webauth-einrichten', 'no-authz', [c for c in WEB_FULL if 'authorization' not in c]),
        ('13-webauth-einrichten', 'no-map', [c for c in WEB_FULL if 'parameter-map' not in c]),
        ('13-webauth-einrichten', 'own-map', ['parameter-map type webauth PM1', 'type webauth', 'virtual-ip ipv4 192.0.2.5', 'exit'] +
         [c.replace('parameter-map global', 'parameter-map PM1') for c in WEB_FULL]),
        ('13-webauth-einrichten', 'only-user', ['username gast1 privilege 0 password 0 Gast#1']),
        ('13-webauth-einrichten', 'user-pw-case', WEB_FULL + ['username gast1 password gast#1']),
        ('13-webauth-einrichten', 'wrong-vlan', WEB_FULL + ['wireless profile policy PP_Guest', 'vlan 20']),
        ('13-webauth-einrichten', 'full-then-off', WEB_FULL + w('no security web-auth')),
        ('13-webauth-einrichten', 'delete-in-use', WEB_FULL + ['no aaa authentication login WEBAUTH', 'no parameter-map type webauth global']),
    ]


def sc_web_variants():
    out = []
    for lab, name, cmds in web_variants():
        r = Recorder('web-%s-%s' % (lab[:2], name))
        r.call('POST', '/wlc/api/lab/start', {'id': lab, 'mode': 'guided'})
        r.apply(cmds)
        r.call('GET', '/wlc/api/state')
        r.cli('end', 'show wireless client summary', 'show wlan summary')
        r.call('POST', '/wlc/api/lab/check', {})
        out.append(r.finish())
    return out


def sc_cli_mobility():
    r = Recorder('cli-mobility')
    r.cli('configure terminal', 'wireless mobility group name', 'wireless mobility group name bad!name', 'wireless mobility group name Neu', 'wireless mobility group name a b',
          'wireless mobility group member mac-address zz ip 10.10.0.20 group G', 'wireless mobility group member mac-address aabb.cc00.0200 ip 300.1.1.1 group G',
          'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.10 group G', 'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20',
          'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group bad!', 'wireless mobility group member ip 10.10.0.20',
          'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus', 'wireless mobility group member mac-address AA:BB:CC:00:02:00 ip 10.10.0.21 group G2',
          'wireless mobility group member mac-address aabb-cc00-0200 ip 10.10.0.22 group G3', 'no wireless mobility group member ip 10.9.9.9', 'no wireless mobility group member',
          'no wireless mobility group member ip 10.10.0.21', 'no wireless mobility group member ip 10.10.0.21', 'no wireless mobility group name', 'wireless mobility group bogus', 'end',
          'show wireless mobility summary', 'show wireless mobility', 'configure terminal', 'wireless mobility group name default', 'no wireless mobility group member ip 10.10.0.22',
          'end', 'show wireless mobility summary')
    r.call('GET', '/wlc/api/state')
    return r.finish()


MOB_MEMBER = 'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus'


def mob_variants():
    w = lambda *c: ['wlan Corp_Profile 1 Corp'] + list(c) + ['exit']
    return [
        ('14-mobility-gruppenname', 'fixed', [MOB_MEMBER]),
        ('14-mobility-gruppenname', 'peer-removed', ['no wireless mobility group member ip 10.10.0.20']),
        ('14-mobility-gruppenname', 'own-name-zentrale', ['wireless mobility group name Zentrale']),
        ('14-mobility-gruppenname', 'wrong-mac', ['wireless mobility group member mac-address aabb.cc00.0299 ip 10.10.0.20 group Campus']),
        ('14-mobility-gruppenname', 'wrong-ip', ['wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.21 group Campus']),
        ('14-mobility-gruppenname', 'open-wlan', [MOB_MEMBER] + w('no security wpa akm psk')),
        ('14-mobility-gruppenname', 'fixed-name-case', ['wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group campus']),
        ('14-mobility-gruppenname', 'dot1x-wlan', [MOB_MEMBER] + w('security wpa akm dot1x')),
        ('15-mobility-einrichten', 'fixed', ['wireless mobility group name Zentrale', MOB_MEMBER]),
        ('15-mobility-einrichten', 'only-name', ['wireless mobility group name Zentrale']),
        ('15-mobility-einrichten', 'only-member', [MOB_MEMBER]),
        ('15-mobility-einrichten', 'name-case', ['wireless mobility group name zentrale', MOB_MEMBER]),
        ('15-mobility-einrichten', 'wrong-mac', ['wireless mobility group name Zentrale', 'wireless mobility group member mac-address aabb.cc00.0299 ip 10.10.0.20 group Campus']),
        ('15-mobility-einrichten', 'wrong-group', ['wireless mobility group name Zentrale', 'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Zentrale']),
        ('15-mobility-einrichten', 'member-then-delete', ['wireless mobility group name Zentrale', MOB_MEMBER, 'no wireless mobility group member ip 10.10.0.20']),
        ('15-mobility-einrichten', 'second-peer', ['wireless mobility group name Zentrale', MOB_MEMBER, 'wireless mobility group member mac-address aabb.cc00.0300 ip 10.10.0.30 group X']),
    ]


def sc_mob_variants():
    out = []
    for lab, name, cmds in mob_variants():
        r = Recorder('mob-%s-%s' % (lab[:2], name))
        r.call('POST', '/wlc/api/lab/start', {'id': lab, 'mode': 'guided'})
        r.apply(cmds)
        r.call('GET', '/wlc/api/state')
        r.cli('end', 'show wireless mobility summary', 'show wireless client summary', 'show wlan summary')
        r.call('POST', '/wlc/api/lab/check', {})
        out.append(r.finish())
    return out


def sc_cli_rf():
    r = Recorder('cli-rf')
    r.cli('configure terminal', 'ap dot11', 'ap dot11 5ghz', 'ap dot11 5ghz rf-profile', 'ap dot11 6ghz rf-profile X', 'ap dot11 5ghz rf-profile bad!name', 'ap dot11 5ghz rf-profile P',
          'tx-power max 0', 'tx-power max 31', 'tx-power max x', 'tx-power', 'tx-power med 10', 'bogus', 'shutdown x', 'no bogus', 'tx-power max 10', 'tx-power min 11', 'tx-power min 10',
          'tx-power min 9', 'no tx-power min', 'no tx-power max', 'tx-power max 20', 'tx-power min 5', 'description Lobby 5 GHz', 'no shutdown', 'exit',
          'ap dot11 24ghz rf-profile P', 'tx-power max 18', 'exit', 'wireless tag rf', 'wireless tag rf bad!name', 'wireless tag rf T', '5ghz-rf-policy', '5ghz-rf-policy NIX',
          '24ghz-rf-policy NIX', '6ghz-rf-policy P', '5ghz-rf-policy P', '24ghz-rf-policy P', 'no 24ghz-rf-policy', 'bogus', 'exit', 'ap a4b2.32aa.0001', 'rf-tag', 'rf-tag NIX', 'rf-tag T',
          'exit', 'no ap dot11 5ghz rf-profile P', 'no wireless tag rf T', 'no wireless tag rf default-rf-tag', 'no wireless tag rf NIX', 'no ap dot11 5ghz rf-profile NIX', 'end',
          'show ap tag summary', 'configure terminal', 'ap a4b2.32aa.0001', 'no rf-tag', 'exit', 'wireless tag rf T', 'no 5ghz-rf-policy', 'exit', 'no wireless tag rf T',
          'no ap dot11 5ghz rf-profile P', 'no ap dot11 24ghz rf-profile P', 'end', 'show ap tag summary')
    r.call('GET', '/wlc/api/state')
    return r.finish()


RF_PROFILE = ['ap dot11 5ghz rf-profile RF_LOBBY', 'tx-power max 14', 'no shutdown', 'exit']
RF_TAG = ['wireless tag rf RFT_LOBBY', '5ghz-rf-policy RF_LOBBY', 'exit']


def rf_variants():
    return [
        ('16-rf-tag-fehlt', 'fixed', ['ap ' + L1, 'rf-tag RFT_LOBBY']),
        ('16-rf-tag-fehlt', 'default-tag', ['wireless tag rf default-rf-tag', '5ghz-rf-policy RF_LOBBY']),
        ('16-rf-tag-fehlt', 'wrong-ap', ['ap ' + L2, 'rf-tag RFT_LOBBY']),
        ('16-rf-tag-fehlt', 'both-aps', ['ap ' + L1, 'rf-tag RFT_LOBBY', 'exit', 'ap ' + L2, 'rf-tag RFT_LOBBY']),
        ('16-rf-tag-fehlt', 'profile-off', ['ap ' + L1, 'rf-tag RFT_LOBBY', 'exit', 'ap dot11 5ghz rf-profile RF_LOBBY', 'shutdown']),
        ('16-rf-tag-fehlt', 'max-changed', ['ap ' + L1, 'rf-tag RFT_LOBBY', 'exit', 'ap dot11 5ghz rf-profile RF_LOBBY', 'tx-power max 20']),
        ('17-rf-lobby-einrichten', 'fixed', RF_PROFILE + RF_TAG + ['ap ' + L1, 'rf-tag RFT_LOBBY', 'exit']),
        ('17-rf-lobby-einrichten', 'profile-disabled', ['ap dot11 5ghz rf-profile RF_LOBBY', 'tx-power max 14', 'exit'] + RF_TAG + ['ap ' + L1, 'rf-tag RFT_LOBBY']),
        ('17-rf-lobby-einrichten', 'no-assignment', RF_PROFILE + RF_TAG),
        ('17-rf-lobby-einrichten', 'only-profile', RF_PROFILE),
        ('17-rf-lobby-einrichten', 'wrong-ap', RF_PROFILE + RF_TAG + ['ap ' + L2, 'rf-tag RFT_LOBBY']),
        ('17-rf-lobby-einrichten', '24ghz-only', ['ap dot11 24ghz rf-profile RF24', 'tx-power max 14', 'no shutdown', 'exit', 'wireless tag rf RFT_LOBBY', '24ghz-rf-policy RF24', 'exit', 'ap ' + L1, 'rf-tag RFT_LOBBY']),
        ('17-rf-lobby-einrichten', 'both-bands', RF_PROFILE + ['ap dot11 24ghz rf-profile RF24', 'tx-power max 10', 'no shutdown', 'exit', 'wireless tag rf RFT_LOBBY', '5ghz-rf-policy RF_LOBBY', '24ghz-rf-policy RF24', 'exit', 'ap ' + L1, 'rf-tag RFT_LOBBY']),
        ('17-rf-lobby-einrichten', 'max-15', ['ap dot11 5ghz rf-profile RF_LOBBY', 'tx-power max 15', 'no shutdown', 'exit'] + RF_TAG + ['ap ' + L1, 'rf-tag RFT_LOBBY']),
        ('17-rf-lobby-einrichten', 'default-tag', RF_PROFILE + ['wireless tag rf default-rf-tag', '5ghz-rf-policy RF_LOBBY']),
    ]


def sc_rf_variants():
    out = []
    for lab, name, cmds in rf_variants():
        r = Recorder('rf-%s-%s' % (lab[:2], name))
        r.call('POST', '/wlc/api/lab/start', {'id': lab, 'mode': 'guided'})
        r.apply(cmds)
        r.call('GET', '/wlc/api/state')
        r.cli('end', 'show ap tag summary', 'show wlan summary')
        r.call('POST', '/wlc/api/lab/check', {})
        out.append(r.finish())
    return out


def sc_apply():
    r = Recorder('apply-atomic-and-validation')
    r.apply(CORP)
    r.apply(['wlan Q 2 Gast', 'no shutdown', 'bogus'])
    r.apply(['wlan Q 2 Gast', 'no shutdown'])
    r.apply(['wlan R 2 Gast'])
    r.apply([])
    r.apply(['no wlan Corp_Profile'])
    r.call('GET', '/wlc/api/state')
    for body in ([], 'text', 5, None, {}, {'commands': 'x'}, {'commands': [1]}, {'commands': None}):
        r.call('POST', '/wlc/api/apply', body, raw=True)
    r.call('POST', '/wlc/api/apply')                      # kein Body
    for body in ([], 'text', 5, None, {'command': 5}, {'command': None}, {}):
        r.call('POST', '/wlc/cli', body, raw=True)
    r.call('POST', '/wlc/cli')
    # CLI-Sitzung im Untermodus, Objekt wird ueber apply geloescht
    r.cli('configure terminal', 'wlan Tmp 7 Temp')
    r.apply(['no wlan Tmp'])
    r.cli('shutdown', 'wlan Tmp2 8 Temp2', 'end')
    r.cli('configure terminal', 'wireless profile policy PPtmp')
    r.apply(['no wireless profile policy PPtmp'])
    r.cli('vlan 5', 'end')
    return r.finish()


def lab_flow(lab_id, mode):
    r = Recorder('lab-%s-%s' % (lab_id, mode))
    lab = lab_json(lab_id)
    r.call('GET', '/wlc/api/labs')
    r.call('GET', '/wlc/api/lab')
    r.call('POST', '/wlc/api/lab/start', {'id': lab_id, 'mode': mode})
    r.call('GET', '/wlc/api/lab')
    r.call('POST', '/wlc/api/lab/check', {})
    r.call('GET', '/wlc/api/state')
    for _ in range(5 if mode == 'guided' else 1):
        r.call('POST', '/wlc/api/lab/hint', {})
    r.call('GET', '/wlc/api/lab/solution')
    for q in lab.get('questions', []):
        for i in range(len(q['options'])):
            r.call('POST', '/wlc/api/lab/answer', {'id': q['id'], 'answer': i})
    r.call('POST', '/wlc/api/lab/answer', {'id': 'nix', 'answer': 0})
    r.call('POST', '/wlc/api/lab/answer', {'id': lab['questions'][0]['id'], 'answer': 99})
    r.call('POST', '/wlc/api/lab/answer', {'id': lab['questions'][0]['id']})
    r.call('POST', '/wlc/api/lab/check', {})
    r.apply(lab['solutionCommands'])
    r.call('POST', '/wlc/api/lab/check', {})
    r.call('GET', '/wlc/api/state')
    r.call('GET', '/wlc/api/lab')
    r.call('GET', '/wlc/api/labs')
    r.cli('end', 'show wireless client summary', 'show ap tag summary')
    r.call('POST', '/wlc/api/lab/reset', {})
    r.call('POST', '/wlc/api/lab/check', {})
    r.call('POST', '/wlc/api/lab/stop', {})
    r.call('POST', '/wlc/api/lab/check', {})
    r.call('POST', '/wlc/api/lab/hint', {})
    r.call('POST', '/wlc/api/lab/reset', {})
    r.call('GET', '/wlc/api/lab/solution')
    r.call('GET', '/wlc/api/state')
    return r.finish()


def sc_lab_errors():
    r = Recorder('lab-errors')
    for body in ({'id': 'x'}, {'id': '01-ssid-nicht-sichtbar', 'mode': 'blitz'}, {}, {'id': 5}, {'id': '01-ssid-nicht-sichtbar', 'mode': None}):
        r.call('POST', '/wlc/api/lab/start', body)
    for path in ('hint', 'check', 'reset', 'answer'):
        r.call('POST', '/wlc/api/lab/' + path, {})
    r.call('GET', '/wlc/api/lab/solution')
    for body in ([], 'x', 5, None):
        r.call('POST', '/wlc/api/lab/start', body, raw=True)
        r.call('POST', '/wlc/api/saves', body, raw=True)
    r.call('POST', '/wlc/api/lab/start', {'id': lab_ids()[0], 'mode': 'exam'})
    for _ in range(2):
        r.call('POST', '/wlc/api/lab/hint', {})
    r.call('GET', '/wlc/api/lab/solution')
    r.call('POST', '/wlc/api/lab/nope', {})
    return r.finish()


def sc_saves():
    r = Recorder('saves-and-progress')
    r.call('GET', '/wlc/api/saves')
    r.apply(CORP)
    r.call('POST', '/wlc/api/saves', {'name': 'mit-wlan'})
    r.apply(['no wireless tag policy PT_Corp', 'no wlan Corp_Profile'])
    r.call('POST', '/wlc/api/saves', {'name': 'ohne-wlan'})
    r.call('POST', '/wlc/api/saves', {'name': 'a-b'})
    r.call('POST', '/wlc/api/saves', {'name': 'a'})
    r.call('GET', '/wlc/api/saves')
    r.call('POST', '/wlc/api/lab/start', {'id': '03-falscher-schluessel', 'mode': 'guided'})
    r.call('POST', '/wlc/api/lab/hint', {})
    r.call('POST', '/wlc/api/lab/answer', {'id': 'q1', 'answer': 0})
    r.call('POST', '/wlc/api/saves', {'name': 'im-lab'})
    r.call('POST', '/wlc/api/lab/stop', {})
    r.call('POST', '/wlc/api/saves/load', {'name': 'im-lab'})
    r.call('GET', '/wlc/api/lab')
    r.call('POST', '/wlc/api/saves/load', {'name': 'mit-wlan'})
    r.call('GET', '/wlc/api/state')
    r.call('GET', '/wlc/api/lab')
    for bad in ('', '../x', 'a b', 'x' * 41, '.versteckt', 'a/b', None, 5, 'ü', '..\\x'):
        r.call('POST', '/wlc/api/saves', {'name': bad})
        r.call('POST', '/wlc/api/saves/load', {'name': bad})
        r.call('POST', '/wlc/api/saves/delete', {'name': bad})
    r.call('POST', '/wlc/api/saves', {})
    r.call('POST', '/wlc/api/saves/load', {'name': 'gibtsnicht'})
    r.call('POST', '/wlc/api/saves/delete', {'name': 'gibtsnicht'})
    r.call('POST', '/wlc/api/saves/delete', {'name': 'ohne-wlan'})
    r.call('POST', '/wlc/api/saves/delete', {'name': 'ohne-wlan'})
    r.call('GET', '/wlc/api/saves')
    r.call('POST', '/wlc/api/lab/start', {'id': '01-ssid-nicht-sichtbar', 'mode': 'guided'})
    r.apply(['ap %s' % L1, 'policy-tag PT_Corp'])
    r.call('POST', '/wlc/api/lab/check', {})
    r.call('GET', '/wlc/api/labs')
    r.call('POST', '/wlc/api/progress/reset', {})
    r.call('GET', '/wlc/api/labs')
    r.call('POST', '/wlc/api/progress/reset', None, raw=True)
    r.call('GET', '/wlc/api/state')
    return r.finish()


def sc_no_persistence():
    r = Recorder('no-persistence', persistent=False)
    r.call('GET', '/wlc/api/state')
    r.call('GET', '/wlc/api/saves')
    r.call('POST', '/wlc/api/saves', {'name': 'x'})
    r.call('POST', '/wlc/api/saves/load', {'name': 'x'})
    r.call('POST', '/wlc/api/saves/delete', {'name': 'x'})
    r.call('POST', '/wlc/api/progress/reset', {})
    r.call('POST', '/wlc/api/lab/start', {'id': '02-admin-down', 'mode': 'guided'})
    r.call('POST', '/wlc/api/lab/check', {})
    r.call('GET', '/wlc/api/labs')
    return r.finish()


def build():
    out = [sc_cli_errors(), sc_cli_policy_ptag_ap(), sc_cli_flex(), sc_cli_aaa(), sc_cli_webauth(), sc_cli_mobility(), sc_cli_rf(), sc_names()] + sc_decide() + sc_aaa_variants() + sc_web_variants() + sc_mob_variants() + sc_rf_variants() + [sc_apply(), sc_lab_errors(), sc_saves(), sc_no_persistence()]
    for lab_id in lab_ids():
        for mode in ('guided', 'exam'):
            out.append(lab_flow(lab_id, mode))
    return {'version': 1, 'scenarios': out}


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    data = json.dumps(build(), ensure_ascii=False, sort_keys=True)
    if target:
        with open(target, 'w', encoding='utf-8') as fh:
            fh.write(data)
    else:
        print(data)
