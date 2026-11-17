"""Simulierter Catalyst 9800 WLC: Konfiguration, CLI, Client-Entscheidung.

Belegt sind die Ausgabeformate der Show-Befehle (genieparser, siehe docs/QUELLEN.md). Die Konfigurationsbefehle und das
Standardverhalten (Default Tags, administrativ down) stammen aus Wissen und sind dort als solches markiert. Die
Begruendungen der Client-Entscheidung sind simulator-spezifisch.
"""
import copy

from .world import norm_mac

DEF_POLICY_TAG, DEF_SITE_TAG, DEF_RF_TAG = 'default-policy-tag', 'default-site-tag', 'default-rf-tag'


class CliError(Exception):
    pass


class Wlc:
    def __init__(self, world):
        self.world = world
        self.wlans = {}        # profil -> {id, ssid, shutdown, akm, psk}
        self.policies = {}     # name -> {vlan, shutdown, descr}
        self.policy_tags = {DEF_POLICY_TAG: {}}   # name -> {wlan-profil: policy-profil}
        self.ap_cfg = {}       # ethMac -> {'policy_tag': name}

    # ------------------------------------------------------------------ Snapshot und Zustand fuer die Oberflaeche
    def snapshot(self):
        return copy.deepcopy((self.wlans, self.policies, self.policy_tags, self.ap_cfg))

    def restore(self, snap):
        self.wlans, self.policies, self.policy_tags, self.ap_cfg = copy.deepcopy(snap)

    def state(self):
        """Alles, was die Weboberflaeche anzeigt (Schluessel werden nicht herausgegeben)."""
        aps = []
        for a in self.world['aps']:
            explicit = self.ap_cfg.get(a['ethMac'], {}).get('policy_tag')
            aps.append({'name': a['name'], 'model': a['model'], 'ethMac': a['ethMac'], 'radioMac': a['radioMac'], 'ip': a['ip'],
                        'location': a['location'], 'country': a['country'], 'state': 'Registered' if a.get('joined') else 'Not joined',
                        'policyTag': self.policy_tag_of(a), 'siteTag': DEF_SITE_TAG, 'rfTag': DEF_RF_TAG,
                        'tagSource': 'Static' if explicit else 'Default'})
        return {
            'wlc': dict(self.world['wlc']),
            'wlans': [{'profile': n, 'id': w['id'], 'ssid': w['ssid'], 'status': 'DOWN' if w['shutdown'] else 'UP',
                       'akm': w['akm'], 'pskSet': bool(w['psk']),
                       'security': '[WPA2][PSK][AES]' if w['akm'] == 'psk' else '[open]'}
                      for n, w in sorted(self.wlans.items(), key=lambda kv: kv[1]['id'])],
            'policies': [{'name': n, 'vlan': p['vlan'], 'description': p['descr'],
                          'status': 'DISABLED' if p['shutdown'] else 'ENABLED'} for n, p in sorted(self.policies.items())],
            'policyTags': [{'name': n, 'builtin': n == DEF_POLICY_TAG,
                            'maps': [{'wlan': k, 'policy': v} for k, v in sorted(m.items())]}
                           for n, m in sorted(self.policy_tags.items())],
            'aps': aps,
            'clients': [{'mac': c['mac'], 'ssid': c['ssid'], 'ap': c['ap'], 'protocol': c['protocol'], 'state': c['state'],
                         'wlan': c['wlan'], 'vlan': c['vlan'], 'method': c['method'], 'reasons': c['reasons']} for c in self.clients()],
        }

    # ------------------------------------------------------------------ Zustand
    def ap_by_eth(self, eth):
        return next((a for a in self.world['aps'] if a['ethMac'] == eth), None)

    def ap_by_name(self, name):
        return next((a for a in self.world['aps'] if a['name'] == name), None)

    def policy_tag_of(self, ap):
        return self.ap_cfg.get(ap['ethMac'], {}).get('policy_tag') or DEF_POLICY_TAG

    def decide(self, client):
        """Didaktisches Modell: Warum ist ein Client assoziiert oder nicht? Rueckgabe {state, ap, wlan, reasons}."""
        ap = self.ap_by_name(client['ap'])
        res = {'state': 'Not Associated', 'ap': client['ap'], 'wlan': None, 'policy': None, 'vlan': None, 'method': None, 'reasons': []}
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
        res.update(wlan=w['id'], policy=pol, vlan=p['vlan'])
        if w['akm'] == 'psk':
            res['method'] = 'PSK'
            if client.get('psk') != w['psk']:
                res['reasons'].append('Pre-Shared Key stimmt nicht - die Authentifizierung scheitert')
                return res
        else:
            res['method'] = 'None'
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
            sec = '[WPA2][PSK][AES]' if w['akm'] == 'psk' else '[open]'
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
            explicit = bool(self.ap_cfg.get(a['ethMac'], {}).get('policy_tag'))
            out.append('%-23s %-16s %-33s %-33s %-33s %-16s %s' % (
                a['name'], a['ethMac'], DEF_SITE_TAG, tag, DEF_RF_TAG, 'No', 'Static' if explicit else 'Default'))
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
               'ptag': '(config-policy-tag)#', 'ap': '(config-ap)#'}

    def __init__(self, wlc):
        self.wlc, self.mode, self.ctx = wlc, 'exec', None

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
            self.mode, self.ctx = 'exec', None
            return ''
        if w[0] == 'exit':
            self.mode = 'config' if self.mode not in ('exec', 'config') else 'exec'
            self.ctx = None
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
             'wireless profile policy summary': self.wlc.show_policy_summary}
        if cmd not in m:
            raise CliError('Der Befehl "show %s" ist in diesem Simulator (noch) nicht belegt/umgesetzt' % cmd)
        return m[cmd]()

    def _config(self, w):
        c = self.wlc
        no = w[0] == 'no'
        if no:
            w = w[1:]
        if self.mode == 'config':
            if w[0] == 'wlan' and len(w) == 4 and not no:
                if not w[2].isdigit() or not 1 <= int(w[2]) <= 4096:
                    raise CliError('WLAN-ID muss 1-4096 sein')
                prof = c.wlans.get(w[1])
                if any(n != w[1] and x['id'] == int(w[2]) for n, x in c.wlans.items()):
                    raise CliError('WLAN-ID %s ist bereits vergeben' % w[2])
                if prof is None:
                    c.wlans[w[1]] = {'id': int(w[2]), 'ssid': w[3], 'shutdown': True, 'akm': 'open', 'psk': ''}
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
            else:
                raise CliError('Invalid input detected: "%s"' % ' '.join(w))
            return ''
        if self.mode == 'policy':
            x = c.policies[self.ctx]
            if w[0] == 'shutdown':
                x['shutdown'] = not no
            elif w[0] == 'vlan' and len(w) == 2:
                x['vlan'] = w[1]
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
        if self.mode == 'ap':
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
