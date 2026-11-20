"""Simulierter Catalyst 9800 WLC: Konfiguration, CLI, Client-Entscheidung.

Belegt sind die Ausgabeformate der Show-Befehle (genieparser, siehe docs/QUELLEN.md). Die Konfigurationsbefehle und das
Standardverhalten (Default Tags, administrativ down) stammen aus Wissen und sind dort als solches markiert. Die
Begruendungen der Client-Entscheidung sind simulator-spezifisch.
"""
import copy
import re

from .world import norm_mac

DEF_POLICY_TAG, DEF_SITE_TAG, DEF_RF_TAG = 'default-policy-tag', 'default-site-tag', 'default-rf-tag'
DEF_FLEX_PROFILE = 'default-flex-profile'
DEF_WEBAUTH_MAP = 'global'
NAME_RE = re.compile(r'^[\w.-]{1,32}$')


class CliError(Exception):
    pass


def is_ipv4(v):
    p = v.split('.')
    return len(p) == 4 and all(x.isdigit() and len(x) <= 3 and int(x) <= 255 for x in p)


class Wlc:
    def __init__(self, world):
        self.world = world
        self.wlans = {}        # profil -> {id, ssid, shutdown, akm, psk}
        self.policies = {}     # name -> {vlan, shutdown, descr}
        self.policy_tags = {DEF_POLICY_TAG: {}}   # name -> {wlan-profil: policy-profil}
        self.ap_cfg = {}       # ethMac -> {'policy_tag': name, 'site_tag': name}
        self.flex_profiles = {DEF_FLEX_PROFILE: {'native': None, 'vlans': {}, 'descr': ''}}   # vlans: name -> id oder None
        self.site_tags = {DEF_SITE_TAG: {'local': True, 'flex': None, 'descr': ''}}
        self.radius_servers = {}   # name -> {ip, auth_port, acct_port, key, timeout, retransmit}
        self.aaa_groups = {}       # name -> {servers: [radius-server-name]} (Reihenfolge = Reihenfolge der Versuche)
        self.aaa_lists = {}        # dot1x-Methodenliste name -> {group}
        self.local_users = {}      # Benutzername -> Passwort (username ... password; lokale Datenbank fuer Web-Auth)
        self.login_lists = {}      # Login-Methodenliste name -> {method: 'local'} (aaa authentication login ... local)
        self.authz_default_local = False   # aaa authorization network default local
        self.webauth_maps = {DEF_WEBAUTH_MAP: {'type': 'webauth', 'virtual_ip': '192.0.2.1'}}   # parameter-map type webauth

    # ------------------------------------------------------------------ Snapshot und Zustand fuer die Oberflaeche
    def snapshot(self):
        return copy.deepcopy((self.wlans, self.policies, self.policy_tags, self.ap_cfg, self.flex_profiles, self.site_tags,
                              self.radius_servers, self.aaa_groups, self.aaa_lists, self.local_users, self.login_lists,
                              self.authz_default_local, self.webauth_maps))

    def restore(self, snap):
        (self.wlans, self.policies, self.policy_tags, self.ap_cfg, self.flex_profiles, self.site_tags,
         self.radius_servers, self.aaa_groups, self.aaa_lists, self.local_users, self.login_lists,
         self.authz_default_local, self.webauth_maps) = copy.deepcopy(snap)

    def dump(self):
        """Konfiguration fuer die Persistenz (JSON-tauglich). Die Welt (APs, Clients) speichert die Sim."""
        return copy.deepcopy({'wlans': self.wlans, 'policies': self.policies, 'policyTags': self.policy_tags, 'apCfg': self.ap_cfg,
                              'flexProfiles': self.flex_profiles, 'siteTags': self.site_tags, 'radiusServers': self.radius_servers,
                              'aaaGroups': self.aaa_groups, 'aaaLists': self.aaa_lists, 'localUsers': self.local_users,
                              'loginLists': self.login_lists, 'authzDefaultLocal': self.authz_default_local,
                              'webauthMaps': self.webauth_maps})

    def load(self, d):
        self.wlans, self.policies = copy.deepcopy(d['wlans']), copy.deepcopy(d['policies'])
        self.policy_tags, self.ap_cfg = copy.deepcopy(d['policyTags']), copy.deepcopy(d['apCfg'])
        self.policy_tags.setdefault(DEF_POLICY_TAG, {})
        # Staende der Version 1 kennen weder Flex Profiles noch Site Tags: Standardobjekte verwenden
        self.flex_profiles = copy.deepcopy(d.get('flexProfiles') or {})
        self.flex_profiles.setdefault(DEF_FLEX_PROFILE, {'native': None, 'vlans': {}, 'descr': ''})
        self.site_tags = copy.deepcopy(d.get('siteTags') or {})
        self.site_tags.setdefault(DEF_SITE_TAG, {'local': True, 'flex': None, 'descr': ''})
        # Staende vor Version 3 kennen keine AAA-Objekte
        self.radius_servers = copy.deepcopy(d.get('radiusServers') or {})
        self.aaa_groups = copy.deepcopy(d.get('aaaGroups') or {})
        self.aaa_lists = copy.deepcopy(d.get('aaaLists') or {})
        # Staende vor Version 4 kennen keine Web-Auth-Objekte
        self.local_users = copy.deepcopy(d.get('localUsers') or {})
        self.login_lists = copy.deepcopy(d.get('loginLists') or {})
        self.authz_default_local = bool(d.get('authzDefaultLocal', False))
        self.webauth_maps = copy.deepcopy(d.get('webauthMaps') or {})
        self.webauth_maps.setdefault(DEF_WEBAUTH_MAP, {'type': 'webauth', 'virtual_ip': '192.0.2.1'})

    def state(self):
        """Alles, was die Weboberflaeche anzeigt (Schluessel werden nicht herausgegeben)."""
        aps = []
        for a in self.world['aps']:
            explicit = self.ap_cfg.get(a['ethMac'], {}).get('policy_tag') or self.ap_cfg.get(a['ethMac'], {}).get('site_tag')
            aps.append({'name': a['name'], 'model': a['model'], 'ethMac': a['ethMac'], 'radioMac': a['radioMac'], 'ip': a['ip'],
                        'location': a['location'], 'country': a['country'], 'state': 'Registered' if a.get('joined') else 'Not joined',
                        'policyTag': self.policy_tag_of(a), 'siteTag': self.site_tag_of(a), 'rfTag': DEF_RF_TAG, 'mode': self.ap_mode(a),
                        'tagSource': 'Static' if explicit else 'Default'})
        return {
            'wlc': dict(self.world['wlc']),
            'wlans': [{'profile': n, 'id': w['id'], 'ssid': w['ssid'], 'status': 'DOWN' if w['shutdown'] else 'UP',
                       'akm': w['akm'], 'pskSet': bool(w['psk']), 'authList': w.get('authlist', ''), 'webAuth': bool(w.get('webauth')), 'webAuthList': w.get('webauth_list', ''),
                       'webAuthMap': w.get('webauth_map', ''), 'security': self.security_of(w)}
                      for n, w in sorted(self.wlans.items(), key=lambda kv: kv[1]['id'])],
            'policies': [{'name': n, 'vlan': p['vlan'], 'description': p['descr'], 'central': p.get('central', True),
                          'aaaOverride': p.get('aaa_override', False),
                          'status': 'DISABLED' if p['shutdown'] else 'ENABLED'} for n, p in sorted(self.policies.items())],
            'radiusServers': [{'name': n, 'ip': r['ip'], 'authPort': r['auth_port'], 'acctPort': r['acct_port'], 'keySet': bool(r['key']),
                               'timeout': r['timeout'], 'retransmit': r['retransmit'], 'state': 'UP' if self.radius_reply(n)[0] else 'DEAD'}
                              for n, r in sorted(self.radius_servers.items())],
            'aaaGroups': [{'name': n, 'servers': list(g['servers'])} for n, g in sorted(self.aaa_groups.items())],
            'aaaLists': [{'name': n, 'group': g['group']} for n, g in sorted(self.aaa_lists.items())],
            'localUsers': [{'name': n, 'passwordSet': bool(pw)} for n, pw in sorted(self.local_users.items())],
            'loginLists': [{'name': n, 'method': l['method']} for n, l in sorted(self.login_lists.items())],
            'authzDefaultLocal': self.authz_default_local,
            'webauthMaps': [{'name': n, 'builtin': n == DEF_WEBAUTH_MAP, 'type': m['type'], 'virtualIp': m['virtual_ip']}
                            for n, m in sorted(self.webauth_maps.items())],
            'flexProfiles': [{'name': n, 'builtin': n == DEF_FLEX_PROFILE, 'description': f['descr'], 'native': f['native'],
                              'vlans': [{'name': k, 'id': v} for k, v in sorted(f['vlans'].items())]}
                             for n, f in sorted(self.flex_profiles.items())],
            'siteTags': [{'name': n, 'builtin': n == DEF_SITE_TAG, 'description': t['descr'], 'local': t['local'],
                          'flexProfile': None if t['local'] else (t['flex'] or DEF_FLEX_PROFILE)}
                         for n, t in sorted(self.site_tags.items())],
            'policyTags': [{'name': n, 'builtin': n == DEF_POLICY_TAG,
                            'maps': [{'wlan': k, 'policy': v} for k, v in sorted(m.items())]}
                           for n, m in sorted(self.policy_tags.items())],
            'aps': aps,
            'clients': [{'mac': c['mac'], 'ssid': c['ssid'], 'ap': c['ap'], 'protocol': c['protocol'], 'state': c['state'],
                         'wlan': c['wlan'], 'vlan': c['vlan'], 'method': c['method'], 'switching': c['switching'], 'mode': c['mode'],
                         'user': (c.get('eap') or c.get('web') or {}).get('user'), 'reasons': c['reasons']} for c in self.clients()],
        }

    # ------------------------------------------------------------------ Zustand
    def ap_by_eth(self, eth):
        return next((a for a in self.world['aps'] if a['ethMac'] == eth), None)

    def ap_by_name(self, name):
        return next((a for a in self.world['aps'] if a['name'] == name), None)

    def policy_tag_of(self, ap):
        return self.ap_cfg.get(ap['ethMac'], {}).get('policy_tag') or DEF_POLICY_TAG

    def site_tag_of(self, ap):
        return self.ap_cfg.get(ap['ethMac'], {}).get('site_tag') or DEF_SITE_TAG

    def ap_mode(self, ap):
        """Local oder FlexConnect: Der Modus kommt vom Site Tag (Local Site aus = FlexConnect, Cisco-Dokument 213945)."""
        st = self.site_tags.get(self.site_tag_of(ap))
        return 'Local' if st is None or st['local'] else 'FlexConnect'

    def flex_of(self, ap):
        st = self.site_tags.get(self.site_tag_of(ap))
        return None if st is None or st['local'] else (st['flex'] or DEF_FLEX_PROFILE)

    @staticmethod
    def flex_vlan(fp, v):
        """VLAN-ID, die der AP fuer den Wert aus dem Policy Profile kennt, sonst None. Namen muessen exakt passen (belegt);
        eine numerische ID passt auf eine VLAN-ID des Flex Profile oder seine Native VLAN (Annahme)."""
        if fp is None:
            return None
        if str(v).isdigit():
            i = int(v)
            return i if i in [x for x in fp['vlans'].values() if x is not None] or fp['native'] == i else None
        return fp['vlans'].get(v)

    @staticmethod
    def security_of(w):
        """Spalte Security von show wlan summary: Muster [WPA2][802.1x][AES] und [open] sind belegt, [PSK] ist abgeleitet."""
        return {'psk': '[WPA2][PSK][AES]', 'dot1x': '[WPA2][802.1x][AES]'}.get(w['akm'], '[open]')

    def radius_reply(self, name):
        """Antwortet der RADIUS-Server hinter dem konfigurierten Eintrag? (ok, Grund). Ohne Antwort verwirft der Controller den
        Versuch und nimmt den naechsten Server der Group; der Server gilt dann als DEAD (Simulator-Modell)."""
        srv = self.radius_servers.get(name)
        if srv is None:
            return False, 'RADIUS-Server %s ist nicht definiert' % name
        if not srv['ip']:
            return False, 'RADIUS-Server %s hat keine Adresse (address ipv4 fehlt)' % name
        ws = next((x for x in self.world.get('radius', {}).get('servers', []) if x['ip'] == srv['ip']), None)
        if ws is None or not ws['up']:
            return False, 'RADIUS-Server %s (%s) antwortet nicht' % (name, srv['ip'])
        if srv['auth_port'] != ws.get('auth_port', 1812):
            return False, 'RADIUS-Server %s (%s) antwortet nicht: Auth-Port %s stimmt nicht' % (name, srv['ip'], srv['auth_port'])
        if self.world['wlc']['ip'] not in ws['nas']:
            return False, 'RADIUS-Server %s verwirft die Anfrage: Der Controller ist dort nicht als Client eingetragen' % name
        if srv['key'] != ws['secret']:
            return False, 'RADIUS-Server %s verwirft die Anfrage: Das Shared Secret stimmt nicht' % name
        return True, ''

    def wlan_servers(self, w):
        """RADIUS-Server-Adressen in der Reihenfolge der Versuche fuer ein 802.1X-WLAN (leer, wenn die Kette unvollstaendig ist)."""
        mm = self.aaa_lists.get(w.get('authlist') or '')
        grp = self.aaa_groups.get(mm['group']) if mm else None
        return [self.radius_servers[n]['ip'] for n in (grp['servers'] if grp else []) if n in self.radius_servers]

    def _dot1x(self, client, w, res):
        """802.1X: Kette WLAN -> Authentication List -> Server Group -> RADIUS-Server pruefen. Rueckgabe (ok, Benutzer-Eintrag)."""
        eap = client.get('eap')
        if not eap:
            res['reasons'].append('Das Endgeraet sendet keine 802.1X-Zugangsdaten, das WLAN verlangt 802.1X')
            return False, None
        lst = w.get('authlist') or ''
        if not lst:
            res['reasons'].append('Am WLAN-Profil ist keine 802.1X-Authentication-List konfiguriert (security dot1x authentication-list)')
            return False, None
        mm = self.aaa_lists.get(lst)
        if mm is None:
            res['reasons'].append('Die Authentication List %s ist nicht definiert (aaa authentication dot1x)' % lst)
            return False, None
        grp = self.aaa_groups.get(mm['group'])
        if grp is None:
            res['reasons'].append('Die Server Group %s der Authentication List %s ist nicht definiert' % (mm['group'], lst))
            return False, None
        if not grp['servers']:
            res['reasons'].append('Die Server Group %s enthaelt keinen RADIUS-Server' % mm['group'])
            return False, None
        tried = []
        for name in grp['servers']:
            ok, why = self.radius_reply(name)
            if not ok:
                tried.append(why)
                continue
            ws = next(x for x in self.world['radius']['servers'] if x['ip'] == self.radius_servers[name]['ip'])
            user = next((u for u in ws['users'] if u['name'] == eap.get('user')), None)
            if user is None or user['password'] != eap.get('password'):
                res['reasons'].append('Access-Reject von %s: Benutzername oder Passwort falsch' % name)
                return False, None
            return True, user
        res['reasons'].append('Kein RADIUS-Server der Group %s antwortet: %s' % (mm['group'], '; '.join(tried)))
        return False, None

    def _webauth(self, client, w, res):
        """Local Web Authentication (Layer 3, nach der L2-Anmeldung): Der Client haengt im Zustand Webauth Pending, bis er sich
        am Portal mit einem lokalen Benutzer anmeldet. Konfigurationskette laut Cisco-Dokument 224922 (siehe docs/QUELLEN.md)."""
        lst = w.get('webauth_list') or ''
        if not lst:
            res['reasons'].append('Am WLAN-Profil ist keine Web-Auth-Authentication-List gesetzt (security web-auth authentication-list)')
            return False
        if lst not in self.login_lists:
            res['reasons'].append('Die Authentication List %s ist nicht definiert (aaa authentication login %s local)' % (lst, lst))
            return False
        pm = w.get('webauth_map') or ''
        if not pm:
            res['reasons'].append('Am WLAN-Profil ist keine Parameter Map gesetzt (security web-auth parameter-map)')
            return False
        if pm not in self.webauth_maps:
            res['reasons'].append('Die Parameter Map %s ist nicht definiert (parameter-map type webauth)' % pm)
            return False
        if not self.authz_default_local:
            res['reasons'].append('Die Autorisierung fehlt: aaa authorization network default local ist nicht konfiguriert, die lokale '
                                  'Anmeldung am Portal funktioniert ohne sie nicht')
            return False
        cred = client.get('web')
        if not cred:
            res['reasons'].append('Der Client hat sich noch nicht am Web-Portal angemeldet (Zustand Webauth Pending)')
            return False
        if self.local_users.get(cred.get('user')) != cred.get('password') or cred.get('user') not in self.local_users:
            res['reasons'].append('Anmeldung am Portal abgelehnt: Benutzername oder Passwort falsch')
            return False
        return True

    def decide(self, client):
        """Didaktisches Modell: Warum ist ein Client assoziiert oder nicht? Rueckgabe {state, ap, wlan, reasons}."""
        ap = self.ap_by_name(client['ap'])
        res = {'state': 'Not Associated', 'ap': client['ap'], 'wlan': None, 'policy': None, 'vlan': None, 'method': None,
               'switching': None, 'mode': None, 'reasons': []}
        if not ap or not ap.get('joined'):
            res['reasons'].append('AP %s ist nicht am Controller registriert' % client['ap'])
            return res
        wl = next((n for n, w in self.wlans.items() if w['ssid'] == client['ssid']), None)
        if wl is None:
            res['reasons'].append('Kein WLAN-Profil mit SSID %s konfiguriert' % client['ssid'])
            return res
        w = self.wlans[wl]
        tag = self.policy_tag_of(ap)
        pol = self.policy_tags.get(tag, {}).get(wl)
        if pol is None:
            res['reasons'].append('Das Policy Tag %s von %s enthaelt das WLAN %s nicht - die SSID wird an diesem AP nicht '
                                  'ausgestrahlt' % (tag, ap['name'], wl))
            return res
        if w['shutdown']:
            res['reasons'].append('WLAN-Profil %s ist administrativ down (shutdown)' % wl)
            return res
        p = self.policies.get(pol)
        if p is None:
            res['reasons'].append('Policy Profile %s im Policy Tag %s existiert nicht' % (pol, tag))
            return res
        if p['shutdown']:
            res['reasons'].append('Policy Profile %s ist administrativ down (shutdown)' % pol)
            return res
        central = p.get('central', True)
        res.update(wlan=w['id'], policy=pol, switching='central' if central else 'local', mode=self.ap_mode(ap))
        if central:
            if not str(p['vlan']).isdigit():
                res['reasons'].append('VLAN %s ist am Controller nicht definiert (der Simulator kennt fuer zentrales Switching nur '
                                      'numerische VLAN-IDs)' % p['vlan'])
                return res
            res['vlan'] = str(p['vlan'])
        else:
            if res['mode'] != 'FlexConnect':
                res['reasons'].append('Policy Profile %s schaltet lokal (no central switching), der AP %s arbeitet aber im Local Mode - '
                                      'lokales Switching setzt den FlexConnect-Modus voraus (Site Tag ohne Local Site)' % (pol, ap['name']))
                return res
            fname = self.flex_of(ap)
            vid = self.flex_vlan(self.flex_profiles.get(fname), p['vlan'])
            if vid is None:
                res['reasons'].append('Das VLAN %s des Policy Profile %s ist im Flex Profile %s nicht definiert (der Name muss exakt '
                                      'passen) - die Clients koennen sich nicht verbinden' % (p['vlan'], pol, fname))
                return res
            res['vlan'] = str(vid)
        if w['akm'] == 'psk':
            res['method'] = 'PSK'
            if client.get('psk') != w['psk']:
                res['reasons'].append('Pre-Shared Key stimmt nicht - die Authentifizierung scheitert')
                return res
        elif w['akm'] == 'dot1x':
            res['method'] = 'Dot1x'
            ok, user = self._dot1x(client, w, res)
            if not ok:
                return res
            # VLAN per RADIUS (Attribute 64/65/81): nur mit aaa-override im Policy Profile, sonst gilt das VLAN des Policy Profile
            if p.get('aaa_override', False) and user.get('vlan'):
                v = str(user['vlan'])
                if central:
                    if not v.isdigit():
                        res['reasons'].append('Das von RADIUS gelieferte VLAN %s ist am Controller nicht definiert (der Simulator kennt '
                                              'fuer zentrales Switching nur numerische VLAN-IDs)' % v)
                        return res
                    res['vlan'] = v
                else:
                    vid = self.flex_vlan(self.flex_profiles.get(self.flex_of(ap)), v)
                    if vid is None:
                        res['reasons'].append('Das von RADIUS gelieferte VLAN %s ist im Flex Profile %s nicht definiert - der Client kann '
                                              'sich nicht verbinden' % (v, self.flex_of(ap)))
                        return res
                    res['vlan'] = str(vid)
        else:
            res['method'] = 'None'
        if w.get('webauth'):
            if res['method'] == 'None':
                res['method'] = 'Web Auth'
            if not self._webauth(client, w, res):
                res['state'] = 'Webauth Pending'
                return res
        res['state'] = 'Run'
        return res

    def clients(self):
        out = []
        for c in self.world['clients']:
            d = self.decide(c)
            out.append(dict(c, **d))
        return out

    # ------------------------------------------------------------------ Show-Ausgaben (Format belegt)
    def show_wlan_summary(self):
        rows = sorted(self.wlans.items(), key=lambda kv: kv[1]['id'])
        out = ['Number of WLANs: %d' % len(rows), '',
               'ID   Profile Name                     SSID                             Status Security',
               '-' * 154]
        for n, w in rows:
            sec = self.security_of(w)
            out.append('%-4d %-32s %-32s %-6s %s' % (w['id'], n, w['ssid'], 'DOWN' if w['shutdown'] else 'UP', sec))
        return '\n'.join(out)

    def show_ap_summary(self):
        aps = [a for a in self.world['aps'] if a.get('joined')]
        out = ['Number of APs: %d' % len(aps), '',
               'AP Name                            Slots    AP Model  Ethernet MAC    Radio MAC       Location'
               '                          Country     IP Address                                 State',
               '-' * 163]
        for a in aps:
            out.append('%-34s %-8d %-9s %-15s %-15s %-33s %-11s %-42s %s' % (
                a['name'], 2, a['model'], a['ethMac'], a['radioMac'], a['location'], a['country'], a['ip'], 'Registered'))
        return '\n'.join(out)

    def show_ap_tag_summary(self):
        aps = [a for a in self.world['aps'] if a.get('joined')]
        out = ['Number of APs: %d' % len(aps), '',
               'AP Name                 AP Mac           Site Tag Name                     Policy Tag Name'
               '                   RF Tag Name                       Misconfigured    Tag Source',
               '-' * 172]
        for a in aps:
            tag = self.policy_tag_of(a)
            explicit = bool(self.ap_cfg.get(a['ethMac'], {}).get('policy_tag') or self.ap_cfg.get(a['ethMac'], {}).get('site_tag'))
            out.append('%-23s %-16s %-33s %-33s %-33s %-16s %s' % (
                a['name'], a['ethMac'], self.site_tag_of(a), tag, DEF_RF_TAG, 'No', 'Static' if explicit else 'Default'))
        return '\n'.join(out)

    def show_wireless_client_summary(self):
        cl = [c for c in self.clients() if c['state'] != 'Not Associated']
        out = ['Number of Clients: %d' % len(cl), '',
               'MAC Address    AP Name                                        Type ID   State             Protocol Method     Role',
               '-' * 121]
        for c in cl:
            out.append('%-14s %-46s %-4s %-4d %-17s %-8s %-10s %s' % (
                c['mac'], c['ap'], 'WLAN', c['wlan'], c['state'], c['protocol'], c['method'], 'Local'))
        return '\n'.join(out)

    def _name_desc_table(self, title, header, rows):
        out = ['Number of %s: %d' % (title, len(rows)), '', '%-33s %s' % (header, 'Description'), '-' * 72]
        out += [('%-33s %s' % (n, d)).rstrip() for n, d in rows]
        return '\n'.join(out)

    def show_flex_summary(self):
        return self._name_desc_table('Flex Profiles', 'Flex Profile Name', [(n, f['descr']) for n, f in sorted(self.flex_profiles.items())])

    def show_site_tag_summary(self):
        return self._name_desc_table('Site Tags', 'Site Tag Name', [(n, t['descr']) for n, t in sorted(self.site_tags.items())])

    def show_aaa_servers(self):
        """Nur Zeilen, deren Format der genieparser-Parser kennt; das Geraet gibt weitere aus (Platform State, Author, Account, Zaehler).
        Die Dauern sind simuliert."""
        out = []
        for i, (n, r) in enumerate(sorted(self.radius_servers.items()), 1):
            up = self.radius_reply(n)[0]
            out += ['RADIUS: id %d, priority 1, host %s, auth-port %d, acct-port %d, hostname %s' % (i, r['ip'] or '0.0.0.0', r['auth_port'], r['acct_port'], n),
                    '  State: current %s, duration 600s, previous duration 0s' % ('UP' if up else 'DEAD'),
                    '  Dead: total time %s, count %d' % ('0s' if up else '600s', 0 if up else 1),
                    '  Quarantined: No']
        return '\n'.join(out)

    def show_policy_summary(self):
        rows = sorted(self.policies.items())
        out = ['Number of Policy Profiles: %d' % len(rows), '',
               'Policy Profile Name               Description                             Status',
               '-' * 89]
        for n, p in rows:
            out.append('%-33s %-39s %s' % (n, p['descr'] or 'Not required', 'DISABLED' if p['shutdown'] else 'ENABLED'))
        return '\n'.join(out)


class Cli:
    """Zeilenweise CLI-Sitzung. Moduswechsel wie im IOS-XE (Prompts: Wissen, nicht belegt)."""
    PROMPTS = {'exec': '#', 'config': '(config)#', 'wlan': '(config-wlan)#', 'policy': '(config-wireless-policy)#',
               'ptag': '(config-policy-tag)#', 'ap': '(config-ap)#', 'flex': '(config-wireless-flex-profile)#',
               'flexvlan': '(config-wireless-flex-profile-vlan)#', 'stag': '(config-site-tag)#', 'radius': '(config-radius-server)#',
               'aaagrp': '(config-sg-radius)#', 'pmap': '(config-params-parameter-map)#'}

    def __init__(self, wlc):
        self.wlc, self.mode, self.ctx, self.ctx2 = wlc, 'exec', None, None

    @property
    def prompt(self):
        return self.wlc.world['wlc']['hostname'] + self.PROMPTS[self.mode]

    def run(self, line):
        """Eine Zeile ausfuehren; Ausgabe als Text. Fehler als 'Invalid input'-Hinweis wie ein Geraet."""
        try:
            return self._run(line.strip())
        except CliError as e:
            return '% ' + str(e)

    def _run(self, line):
        if not line:
            return ''
        w = line.split()
        if w[0] in ('end',):
            self.mode, self.ctx, self.ctx2 = 'exec', None, None
            return ''
        if w[0] == 'exit':
            if self.mode == 'flexvlan':
                self.mode, self.ctx2 = 'flex', None
                return ''
            self.mode = 'config' if self.mode not in ('exec', 'config') else 'exec'
            self.ctx = self.ctx2 = None
            return ''
        if w[0] == 'show' or (w[0] == 'do' and len(w) > 1 and w[1] == 'show'):
            return self._show(' '.join(w[1:] if w[0] == 'show' else w[2:]))
        if self.mode == 'exec':
            if line in ('configure terminal', 'conf t', 'configure t'):
                self.mode = 'config'
                return 'Enter configuration commands, one per line.  End with CNTL/Z.'
            raise CliError('Invalid input detected: "%s"' % line)
        return self._config(w)

    def _show(self, cmd):
        m = {'wlan summary': self.wlc.show_wlan_summary, 'ap summary': self.wlc.show_ap_summary,
             'ap tag summary': self.wlc.show_ap_tag_summary,
             'wireless client summary': self.wlc.show_wireless_client_summary,
             'wireless profile policy summary': self.wlc.show_policy_summary,
             'wireless profile flex summary': self.wlc.show_flex_summary,
             'wireless tag site summary': self.wlc.show_site_tag_summary,
             'aaa servers': self.wlc.show_aaa_servers}
        if cmd not in m:
            raise CliError('Der Befehl "show %s" ist in diesem Simulator (noch) nicht belegt/umgesetzt' % cmd)
        return m[cmd]()

    def _flex(self, w, no):
        """Flex Profile: native-vlan-id, vlan-name mit Untermodus vlan-id. Befehle des Elternmodus gelten auch im Untermodus."""
        fp = self.wlc.flex_profiles[self.ctx]
        bad = CliError('Invalid input detected: "%s"' % ' '.join(w))
        if w[0] == 'vlan-id' and self.mode == 'flexvlan' and (len(w) == 2 or (no and len(w) == 1)):
            if no:
                fp['vlans'][self.ctx2] = None
                return ''
            if not w[1].isdigit() or not 1 <= int(w[1]) <= 4094:
                raise CliError('VLAN-ID muss 1-4094 sein')
            fp['vlans'][self.ctx2] = int(w[1])
            return ''
        if w[0] == 'native-vlan-id' and (len(w) == 2 or (no and len(w) == 1)):
            if no:
                fp['native'] = None
            elif w[1].isdigit() and 1 <= int(w[1]) <= 4094:
                fp['native'] = int(w[1])
            else:
                raise CliError('VLAN-ID muss 1-4094 sein')
            self.mode, self.ctx2 = 'flex', None
            return ''
        if w[0] == 'vlan-name' and len(w) == 2:
            if no:
                if w[1] not in fp['vlans']:
                    raise CliError('VLAN-Name %s existiert im Flex Profile nicht' % w[1])
                del fp['vlans'][w[1]]
                self.mode, self.ctx2 = 'flex', None
                return ''
            if w[1] not in fp['vlans'] and not NAME_RE.match(w[1]):
                raise CliError('VLAN-Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
            fp['vlans'].setdefault(w[1], None)
            self.mode, self.ctx2 = 'flexvlan', w[1]
            return ''
        if w[0] == 'description' and len(w) > 1 and not no:
            fp['descr'] = ' '.join(w[1:])
            return ''
        raise bad

    def _config(self, w):
        c = self.wlc
        no = w[0] == 'no'
        if no:
            w = w[1:]
        if not w:
            raise CliError('Invalid input detected: "no"')
        # Das Objekt des aktuellen Untermodus kann inzwischen (z. B. ueber die Oberflaeche) geloescht worden sein
        store = {'wlan': c.wlans, 'policy': c.policies, 'ptag': c.policy_tags, 'flex': c.flex_profiles, 'flexvlan': c.flex_profiles,
                 'stag': c.site_tags, 'radius': c.radius_servers, 'aaagrp': c.aaa_groups, 'pmap': c.webauth_maps}.get(self.mode)
        if store is not None and self.ctx not in store:
            self.mode, self.ctx, self.ctx2 = 'config', None, None
            raise CliError('Das Objekt existiert nicht mehr')
        if self.mode == 'config':
            if w[0] == 'wlan' and len(w) == 4 and not no:
                if not w[2].isdigit() or not 1 <= int(w[2]) <= 4096:
                    raise CliError('WLAN-ID muss 1-4096 sein')
                prof = c.wlans.get(w[1])
                if any(n != w[1] and x['id'] == int(w[2]) for n, x in c.wlans.items()):
                    raise CliError('WLAN-ID %s ist bereits vergeben' % w[2])
                if prof is None:
                    c.wlans[w[1]] = {'id': int(w[2]), 'ssid': w[3], 'shutdown': True, 'akm': 'open', 'psk': '', 'authlist': ''}
                self.mode, self.ctx = 'wlan', w[1]
                return ''
            if w[:3] == ['wireless', 'profile', 'policy'] and len(w) == 4 and not no:
                c.policies.setdefault(w[3], {'vlan': '1', 'shutdown': True, 'descr': ''})
                self.mode, self.ctx = 'policy', w[3]
                return ''
            if w[:3] == ['wireless', 'tag', 'policy'] and len(w) == 4 and not no:
                c.policy_tags.setdefault(w[3], {})
                self.mode, self.ctx = 'ptag', w[3]
                return ''
            if w[0] == 'ap' and len(w) == 2 and not no:
                try:
                    eth = norm_mac(w[1])
                except ValueError as e:
                    raise CliError(str(e))
                c.ap_cfg.setdefault(eth, {})
                self.mode, self.ctx = 'ap', eth
                return ''
            if w[:3] == ['wireless', 'profile', 'flex'] and len(w) == 4 and not no:
                if w[3] not in c.flex_profiles and not NAME_RE.match(w[3]):
                    raise CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
                c.flex_profiles.setdefault(w[3], {'native': None, 'vlans': {}, 'descr': ''})
                self.mode, self.ctx = 'flex', w[3]
                return ''
            if w[:3] == ['wireless', 'tag', 'site'] and len(w) == 4 and not no:
                if w[3] not in c.site_tags and not NAME_RE.match(w[3]):
                    raise CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
                c.site_tags.setdefault(w[3], {'local': True, 'flex': None, 'descr': ''})
                self.mode, self.ctx = 'stag', w[3]
                return ''
            if w[0] == 'username' and not no and len(w) in (4, 5, 6, 7):
                i = 2
                if w[i] == 'privilege' and len(w) >= 6 and w[3].isdigit() and 0 <= int(w[3]) <= 15:
                    i = 4
                if len(w) - i in (2, 3) and w[i] == 'password' and (len(w) - i == 2 or w[i + 1] == '0'):
                    if not NAME_RE.match(w[1]):
                        raise CliError('Benutzername: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
                    c.local_users[w[1]] = w[-1]
                    return ''
                raise CliError('Invalid input detected: "%s"' % ' '.join(w))
            if no and w[0] == 'username' and len(w) == 2:
                if w[1] not in c.local_users:
                    raise CliError('Benutzer %s existiert nicht' % w[1])
                del c.local_users[w[1]]
                return ''
            if w[:3] == ['aaa', 'authentication', 'login'] and len(w) == 5 and w[4] == 'local' and not no:
                if not NAME_RE.match(w[3]):
                    raise CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
                c.login_lists[w[3]] = {'method': 'local'}
                return ''
            if no and w[:3] == ['aaa', 'authentication', 'login'] and len(w) == 4:
                if w[3] not in c.login_lists:
                    raise CliError('Authentication List %s existiert nicht' % w[3])
                users = sorted(n for n, x in c.wlans.items() if x.get('webauth_list') == w[3])
                if users:
                    raise CliError('Authentication List %s wird von WLANs verwendet (%s) - zuerst dort entfernen' % (w[3], ', '.join(users)))
                del c.login_lists[w[3]]
                return ''
            if w == ['aaa', 'authorization', 'network', 'default', 'local'] or (no and w[:4] == ['aaa', 'authorization', 'network', 'default']):
                c.authz_default_local = not no
                return ''
            if w[:3] == ['parameter-map', 'type', 'webauth'] and len(w) == 4 and not no:
                if w[3] not in c.webauth_maps and not NAME_RE.match(w[3]):
                    raise CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
                c.webauth_maps.setdefault(w[3], {'type': 'webauth', 'virtual_ip': ''})
                self.mode, self.ctx = 'pmap', w[3]
                return ''
            if no and w[:3] == ['parameter-map', 'type', 'webauth'] and len(w) == 4:
                if w[3] == DEF_WEBAUTH_MAP:
                    raise CliError('%s ist vordefiniert und kann nicht geloescht werden' % DEF_WEBAUTH_MAP)
                if w[3] not in c.webauth_maps:
                    raise CliError('Parameter Map %s existiert nicht' % w[3])
                users = sorted(n for n, x in c.wlans.items() if x.get('webauth_map') == w[3])
                if users:
                    raise CliError('Parameter Map %s wird von WLANs verwendet (%s) - zuerst dort entfernen' % (w[3], ', '.join(users)))
                del c.webauth_maps[w[3]]
                return ''
            if w == ['aaa', 'new-model']:
                return ''   # AAA ist im Simulator immer aktiv; der Befehl wird angenommen
            if w[:2] == ['radius', 'server'] and len(w) == 3 and not no:
                if w[2] not in c.radius_servers and not NAME_RE.match(w[2]):
                    raise CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
                c.radius_servers.setdefault(w[2], {'ip': '', 'auth_port': 1812, 'acct_port': 1813, 'key': '', 'timeout': 5, 'retransmit': 3})
                self.mode, self.ctx = 'radius', w[2]
                return ''
            if w[:4] == ['aaa', 'group', 'server', 'radius'] and len(w) == 5 and not no:
                if w[4] not in c.aaa_groups and not NAME_RE.match(w[4]):
                    raise CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
                c.aaa_groups.setdefault(w[4], {'servers': []})
                self.mode, self.ctx = 'aaagrp', w[4]
                return ''
            if w[:3] == ['aaa', 'authentication', 'dot1x'] and len(w) == 6 and w[4] == 'group' and not no:
                if not NAME_RE.match(w[3]):
                    raise CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)')
                if w[5] not in c.aaa_groups:
                    raise CliError('Server Group %s existiert nicht' % w[5])
                c.aaa_lists[w[3]] = {'group': w[5]}
                return ''
            if no and w[:3] == ['aaa', 'authentication', 'dot1x'] and len(w) == 4:
                if w[3] not in c.aaa_lists:
                    raise CliError('Authentication List %s existiert nicht' % w[3])
                users = sorted(n for n, x in c.wlans.items() if x.get('authlist') == w[3])
                if users:
                    raise CliError('Authentication List %s wird von WLANs verwendet (%s) - zuerst dort entfernen' % (w[3], ', '.join(users)))
                del c.aaa_lists[w[3]]
                return ''
            if no and w[:4] == ['aaa', 'group', 'server', 'radius'] and len(w) == 5:
                if w[4] not in c.aaa_groups:
                    raise CliError('Server Group %s existiert nicht' % w[4])
                users = sorted(n for n, x in c.aaa_lists.items() if x['group'] == w[4])
                if users:
                    raise CliError('Server Group %s wird von Authentication Lists verwendet (%s) - zuerst dort entfernen' % (w[4], ', '.join(users)))
                del c.aaa_groups[w[4]]
                return ''
            if no and w[:2] == ['radius', 'server'] and len(w) == 3:
                if w[2] not in c.radius_servers:
                    raise CliError('RADIUS-Server %s existiert nicht' % w[2])
                users = sorted(n for n, g in c.aaa_groups.items() if w[2] in g['servers'])
                if users:
                    raise CliError('RADIUS-Server %s ist in Server Groups eingetragen (%s) - zuerst dort entfernen' % (w[2], ', '.join(users)))
                del c.radius_servers[w[2]]
                return ''
            if no and w[:3] == ['wireless', 'profile', 'flex'] and len(w) == 4:
                if w[3] == DEF_FLEX_PROFILE:
                    raise CliError('%s ist vordefiniert und kann nicht geloescht werden' % DEF_FLEX_PROFILE)
                if w[3] not in c.flex_profiles:
                    raise CliError('Flex Profile %s existiert nicht' % w[3])
                users = sorted(n for n, t in c.site_tags.items() if t['flex'] == w[3])
                if users:
                    raise CliError('Flex Profile %s wird von Site Tags verwendet (%s) - zuerst dort entfernen' % (w[3], ', '.join(users)))
                del c.flex_profiles[w[3]]
                return ''
            if no and w[:3] == ['wireless', 'tag', 'site'] and len(w) == 4:
                if w[3] == DEF_SITE_TAG:
                    raise CliError('%s ist vordefiniert und kann nicht geloescht werden' % DEF_SITE_TAG)
                if w[3] not in c.site_tags:
                    raise CliError('Site Tag %s existiert nicht' % w[3])
                aps = sorted(a['name'] for a in c.world['aps'] if c.site_tag_of(a) == w[3])
                if aps:
                    raise CliError('Site Tag %s ist APs zugewiesen (%s) - zuerst dort entfernen' % (w[3], ', '.join(aps)))
                del c.site_tags[w[3]]
                return ''
            if no and w[0] == 'wlan' and len(w) == 2:
                if w[1] not in c.wlans:
                    raise CliError('WLAN-Profil %s existiert nicht' % w[1])
                users = sorted(t for t, m in c.policy_tags.items() if w[1] in m)
                if users:
                    raise CliError('WLAN-Profil %s ist in Policy Tags eingetragen (%s) - zuerst dort entfernen' % (w[1], ', '.join(users)))
                del c.wlans[w[1]]
                return ''
            if no and w[:3] == ['wireless', 'profile', 'policy'] and len(w) == 4:
                if w[3] not in c.policies:
                    raise CliError('Policy Profile %s existiert nicht' % w[3])
                users = sorted(t for t, m in c.policy_tags.items() if w[3] in m.values())
                if users:
                    raise CliError('Policy Profile %s wird von Policy Tags verwendet (%s) - zuerst dort entfernen' % (w[3], ', '.join(users)))
                del c.policies[w[3]]
                return ''
            if no and w[:3] == ['wireless', 'tag', 'policy'] and len(w) == 4:
                if w[3] == DEF_POLICY_TAG:
                    raise CliError('%s ist vordefiniert und kann nicht geloescht werden' % DEF_POLICY_TAG)
                if w[3] not in c.policy_tags:
                    raise CliError('Policy Tag %s existiert nicht' % w[3])
                aps = sorted(a['name'] for a in c.world['aps'] if c.policy_tag_of(a) == w[3])
                if aps:
                    raise CliError('Policy Tag %s ist APs zugewiesen (%s) - zuerst dort entfernen' % (w[3], ', '.join(aps)))
                del c.policy_tags[w[3]]
                return ''
            raise CliError('Invalid input detected: "%s"' % ' '.join(w))
        if self.mode == 'wlan':
            x = c.wlans[self.ctx]
            if w[0] == 'shutdown':
                x['shutdown'] = not no
            elif w[:4] == ['security', 'wpa', 'psk', 'set-key'] and len(w) == 7 and w[4] == 'ascii':
                x['psk'] = w[6]
            elif w[:3] == ['security', 'wpa', 'akm'] and len(w) == 4 and w[3] == 'psk':
                x['akm'] = 'open' if no else 'psk'
            elif w[:3] == ['security', 'wpa', 'akm'] and len(w) == 4 and w[3] == 'dot1x':
                x['akm'] = 'open' if no else 'dot1x'
            elif w[:3] == ['security', 'dot1x', 'authentication-list'] and (len(w) == 4 or (no and len(w) == 3)):
                x['authlist'] = '' if no else w[3]
            elif w == ['security', 'web-auth']:
                x['webauth'] = not no
                if no:
                    x['webauth_list'] = x['webauth_map'] = ''
            elif w[:3] == ['security', 'web-auth', 'authentication-list'] and (len(w) == 4 or (no and len(w) == 3)):
                x['webauth_list'] = '' if no else w[3]
            elif w[:3] == ['security', 'web-auth', 'parameter-map'] and (len(w) == 4 or (no and len(w) == 3)):
                x['webauth_map'] = '' if no else w[3]
            else:
                raise CliError('Invalid input detected: "%s"' % ' '.join(w))
            return ''
        if self.mode == 'policy':
            x = c.policies[self.ctx]
            if w[0] == 'shutdown':
                x['shutdown'] = not no
            elif w[0] == 'vlan' and len(w) == 2 and NAME_RE.match(w[1]):
                x['vlan'] = w[1]
            elif w == ['central', 'switching']:
                x['central'] = not no
            elif w == ['aaa-override']:
                x['aaa_override'] = not no
            elif w[0] == 'description' and len(w) > 1:
                x['descr'] = ' '.join(w[1:])
            else:
                raise CliError('Invalid input detected: "%s"' % ' '.join(w))
            return ''
        if self.mode == 'ptag':
            if w[0] == 'wlan' and len(w) == 4 and w[2] == 'policy':
                if no:
                    c.policy_tags[self.ctx].pop(w[1], None)
                else:
                    c.policy_tags[self.ctx][w[1]] = w[3]
                return ''
            raise CliError('Invalid input detected: "%s"' % ' '.join(w))
        if self.mode in ('flex', 'flexvlan'):
            return self._flex(w, no)
        if self.mode == 'radius':
            r = c.radius_servers[self.ctx]
            if w[:2] == ['address', 'ipv4'] and len(w) in (3, 7) and not no:
                if not is_ipv4(w[2]):
                    raise CliError('IPv4-Adresse ungueltig: %s' % w[2])
                if len(w) == 7:
                    if w[3] != 'auth-port' or w[5] != 'acct-port' or not w[4].isdigit() or not w[6].isdigit() \
                            or not (1 <= int(w[4]) <= 65535 and 1 <= int(w[6]) <= 65535):
                        raise CliError('Invalid input detected: "%s"' % ' '.join(w))
                    r['auth_port'], r['acct_port'] = int(w[4]), int(w[6])
                r['ip'] = w[2]
            elif w[0] == 'key' and not no and (len(w) == 2 or (len(w) == 3 and w[1] == '0')):
                r['key'] = w[-1]
            elif w[0] in ('timeout', 'retransmit') and len(w) == 2 and not no:
                hi = 1000 if w[0] == 'timeout' else 100
                if not w[1].isdigit() or not (0 if w[0] == 'retransmit' else 1) <= int(w[1]) <= hi:
                    raise CliError('Wert ausserhalb des Bereichs')
                r[w[0]] = int(w[1])
            else:
                raise CliError('Invalid input detected: "%s"' % ' '.join(w))
            return ''
        if self.mode == 'pmap':
            m = c.webauth_maps[self.ctx]
            if w == ['type', 'webauth'] and not no:
                m['type'] = 'webauth'
            elif w[:2] == ['virtual-ip', 'ipv4'] and len(w) == 3 and not no:
                if not is_ipv4(w[2]):
                    raise CliError('IPv4-Adresse ungueltig: %s' % w[2])
                m['virtual_ip'] = w[2]
            elif no and w[:2] == ['virtual-ip', 'ipv4']:
                m['virtual_ip'] = ''
            else:
                raise CliError('Invalid input detected: "%s"' % ' '.join(w))
            return ''
        if self.mode == 'aaagrp':
            g = c.aaa_groups[self.ctx]
            if w[:2] == ['server', 'name'] and len(w) == 3:
                if no:
                    if w[2] not in g['servers']:
                        raise CliError('RADIUS-Server %s ist nicht in der Group' % w[2])
                    g['servers'].remove(w[2])
                else:
                    if w[2] not in c.radius_servers:
                        raise CliError('RADIUS-Server %s existiert nicht' % w[2])
                    if w[2] not in g['servers']:
                        g['servers'].append(w[2])
                return ''
            raise CliError('Invalid input detected: "%s"' % ' '.join(w))
        if self.mode == 'stag':
            st = c.site_tags[self.ctx]
            if w[0] == 'flex-profile' and (len(w) == 2 or (no and len(w) == 1)):
                if no:
                    st['flex'] = None
                    return ''
                if st['local']:
                    raise CliError('Das Flex Profile steht nur zur Verfuegung, wenn Local Site deaktiviert ist (no local-site)')
                if w[1] not in c.flex_profiles:
                    raise CliError('Flex Profile %s existiert nicht' % w[1])
                st['flex'] = w[1]
            elif w == ['local-site']:
                st['local'] = not no
                if st['local']:
                    st['flex'] = None
            elif w[0] == 'description' and len(w) > 1 and not no:
                st['descr'] = ' '.join(w[1:])
            else:
                raise CliError('Invalid input detected: "%s"' % ' '.join(w))
            return ''
        if self.mode == 'ap':
            if w[0] == 'site-tag' and (len(w) == 2 or (no and len(w) == 1)):
                if no:
                    c.ap_cfg[self.ctx].pop('site_tag', None)
                else:
                    if w[1] not in c.site_tags:
                        raise CliError('Site Tag %s existiert nicht' % w[1])
                    c.ap_cfg[self.ctx]['site_tag'] = w[1]
                return ''
            if w[0] == 'policy-tag' and (len(w) == 2 or (no and len(w) == 1)):
                if no:
                    c.ap_cfg[self.ctx].pop('policy_tag', None)
                else:
                    c.ap_cfg[self.ctx]['policy_tag'] = w[1]
                return ''
            raise CliError('Invalid input detected: "%s"' % ' '.join(w))
        raise CliError('Invalid input detected')


def apply_commands(wlc, commands):
    """Befehle atomar durch die CLI anwenden: Bei einem Fehler wird die Konfiguration auf den Stand davor zurueckgesetzt.
    Rueckgabe (ok, Ergebnisse je Zeile, Fehler oder None). Oberflaeche, Labs und Tests gehen so durch dieselbe CLI."""
    snap = wlc.snapshot()
    cli = Cli(wlc)
    results = []
    for line in ['configure terminal'] + list(commands) + ['end']:
        out = cli.run(line)
        results.append({'command': line, 'output': out})
        if out.startswith('% '):
            wlc.restore(snap)
            return False, results, {'command': line, 'message': out[2:]}
    return True, results, None
