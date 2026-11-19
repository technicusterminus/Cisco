#!/usr/bin/env python3
"""Erzeugt labs/*.json (deterministisch). Labs werden nur hier geaendert; labs/*.json sind generiert.

Jedes Lab hat eine Musterloesung in SOLUTIONS (CLI-Befehle). Der Test TestLabs verlangt: Ohne Loesung ist das Lab nicht
bestanden, mit Loesung ist es bestanden. Bewertet wird das Verhalten der Welt, nicht der Wortlaut der Befehle.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'labs')

L1, L2 = 'a4b2.32aa.0001', 'a4b2.32aa.0002'     # Ethernet-MACs von ap-lobby und ap-lager
LIMITS = ['Das Client-Modell ist didaktisch: Es erklärt, ob und warum ein Client verbunden ist, ist aber keine Abbildung der '
          'Controller-Pipeline.',
          'Nicht modelliert: 802.1x/RADIUS, FlexConnect, RF-Profile, Roaming, Mobility.']
TRACK_WIFI = 'CCNP Enterprise Wireless (300-430 ENWLSI)'
TOOLS = ['WebUI: Monitoring > Wireless > Clients', 'WebUI: Configuration > Tags & Profiles und Wireless > Access Points',
         'Client-Diagnose (nur im geführten Modus)', 'CLI: show wlan summary, show ap tag summary, show wireless client summary']


def client(mac, ssid, psk, ap, proto='11ac'):
    return {'mac': mac, 'ssid': ssid, 'psk': psk, 'ap': ap, 'protocol': proto}


def corp(key='Sommer2026', enabled=True, policy_enabled=True, tag_policy='PP_Corp'):
    """Startkonfiguration: WLAN Corp, Policy Profile und Policy Tag."""
    c = ['wlan Corp_Profile 1 Corp', 'security wpa akm psk', 'security wpa psk set-key ascii 0 ' + key,
         'no shutdown' if enabled else 'shutdown', 'exit',
         'wireless profile policy PP_Corp', 'vlan 20', 'no shutdown' if policy_enabled else 'shutdown', 'exit']
    if tag_policy:
        c += ['wireless tag policy PT_Corp', 'wlan Corp_Profile policy ' + tag_policy, 'exit']
    return c


def chk(desc, typ, category='function', **kw):
    d = {'desc': desc, 'type': typ, 'category': category}
    d.update(kw)
    return d


def q(qid, text, options, answer, explain):
    return {'id': qid, 'q': text, 'options': options, 'answer': answer, 'explain': explain}


LABS = []
SOLUTIONS = {}


def lab(**kw):
    kw.setdefault('modes', ['guided', 'exam'])
    kw.setdefault('limits', LIMITS)
    kw.setdefault('tools', TOOLS)
    kw.setdefault('fabric', 'wlc1 mit ap-lobby und ap-lager')
    kw.setdefault('track', 'Grundlagen Wireless')
    assert len(kw['hints']) == 4, kw['id']
    LABS.append(kw)


LAPTOP = '58bf.eaaa.0001'

# ---------------------------------------------------------------------------------------------------------------
lab(id='01-ssid-nicht-sichtbar', title='01 Corp-SSID in der Lobby nicht sichtbar', topic='Wireless / Tags',
    level='Einstieg', duration='15 min', kind='troubleshooting', prerequisites=[],
    goals=['Den Weg vom WLAN-Profil zum AP nachvollziehen', 'Das Standardverhalten eines AP ohne eigene Zuordnung kennen',
           'Eine Lösung wählen, die nur dort sendet, wo es nötig ist'],
    intro='Die Firma hat das WLAN **Corp** (WPA2-PSK, VLAN 20) eingerichtet. Die Konfiguration wirkt vollständig, trotzdem '
          'findet der Laptop in der Lobby die SSID nicht.\n\n- Controller wlc1, zwei APs: **ap-lobby** und **ap-lager**\n'
          '- Lobby-Laptop 58bf.eaaa.0001 mit dem richtigen Schlüssel\n- Im Lager soll Corp **nicht** ausgestrahlt werden.',
    requirements=['Der Laptop in der Lobby ist mit Corp verbunden und im VLAN 20.',
                  'Corp bleibt mit WPA2-PSK geschützt.',
                  'Corp wird nur in der Lobby ausgestrahlt, nicht im Lager.'],
    hints=['**Konzept:** Ein AP strahlt nur die WLANs aus, die ihm über seine Tags zugeordnet sind. Prüfe, was dem AP zugeordnet ist.',
           '**Ebene:** Zuordnung am AP, nicht WLAN oder Policy Profile: Beide sind aktiv.',
           '**Prüfschritte:** `show ap tag summary` zeigt je AP das Policy Tag und die Tag Source. Vergleiche mit dem Tag, das Corp enthält.',
           '**Lösung:** Dem AP ap-lobby das Policy Tag **PT_Corp** zuweisen. ap-lager bleibt unverändert.'],
    cause='ap-lobby nutzt das Default Policy Tag (Tag Source Default), und das enthält keine WLANs.',
    startCommands=corp(), worldClients=[client(LAPTOP, 'Corp', 'Sommer2026', 'ap-lobby')],
    checks=[chk('Lobby-Laptop verbunden, VLAN 20', 'client', mac=LAPTOP, state='Run', vlan='20'),
            chk('Corp nutzt weiterhin WPA2-PSK', 'wlan', 'security', profile='Corp_Profile', attrs={'akm': 'psk'}),
            chk('ap-lager sendet Corp nicht', 'aptag', 'security', ap='ap-lager', tag='default-policy-tag')],
    questions=[q('q1', 'Welches Policy Tag nutzt ein AP, dem du keines zuweist?',
                 ['Das Default Policy Tag, das keine WLANs enthält', 'Das erste Policy Tag in der Liste', 'Das Tag mit den meisten WLANs', 'Keines, der AP sendet dann alle WLANs'], 0,
                 'Ohne Zuordnung gilt default-policy-tag. Es enthält keine WLAN-zu-Policy-Zuordnung, die SSID wird nicht ausgestrahlt.'),
        q('q2', 'Warum ist es besser, nur ap-lobby zu taggen statt beide APs?',
          ['Weil jeder AP nur ein Tag haben darf', 'Weil Corp im Lager nicht gebraucht wird und sonst unnötig erreichbar wäre', 'Weil sonst die Lizenz nicht reicht', 'Weil das Lager kein WLAN unterstützt'], 1,
          'Least Privilege gilt auch für Funk: Eine SSID sendet nur dort, wo sie gebraucht wird.')],
    solution='In der WebUI: Configuration > Wireless > Access Points > ap-lobby > Edit Tags > Policy Tag PT_Corp. '
             'CLI: `configure terminal`, `ap a4b2.32aa.0001`, `policy-tag PT_Corp`, `end`.')
SOLUTIONS['01-ssid-nicht-sichtbar'] = ['ap %s' % L1, 'policy-tag PT_Corp']

# ---------------------------------------------------------------------------------------------------------------
lab(id='02-admin-down', title='02 Alles eingerichtet, nichts funkt', topic='Wireless / Betriebszustand',
    level='Einstieg', duration='15 min', kind='troubleshooting', prerequisites=['Lab 01'],
    goals=['Administrativen Zustand von WLAN und Policy Profile unterscheiden', 'Mehrere Ursachen nacheinander finden'],
    intro='Ein Kollege hat Corp komplett angelegt und dem AP ap-lobby zugewiesen. Der Laptop in der Lobby verbindet sich trotzdem nicht.\n\n'
          '- Corp: WPA2-PSK, VLAN 20, Zuordnung am AP ist erledigt\n- Der Kollege hat nach dem Anlegen nichts weiter konfiguriert.',
    requirements=['Der Laptop in der Lobby ist mit Corp verbunden und im VLAN 20.', 'Corp bleibt mit WPA2-PSK geschützt.'],
    hints=['**Konzept:** Neu angelegte Objekte sind nicht automatisch aktiv. Es gibt mehrere Stellen mit einem Admin-Zustand.',
           '**Ebene:** Konfigurationszustand von WLAN und Policy Profile, die Zuordnung am AP stimmt.',
           '**Prüfschritte:** `show wlan summary` zeigt den Status des WLAN, `show wireless profile policy summary` den des Policy Profile. Beide prüfen.',
           '**Lösung:** Das WLAN-Profil **und** das Policy Profile aktivieren (`no shutdown`).'],
    cause='WLAN-Profil und Policy Profile sind nach dem Anlegen administrativ down.',
    startCommands=corp(enabled=False, policy_enabled=False) + ['ap %s' % L1, 'policy-tag PT_Corp'],
    worldClients=[client(LAPTOP, 'Corp', 'Sommer2026', 'ap-lobby')],
    checks=[chk('Lobby-Laptop verbunden, VLAN 20', 'client', mac=LAPTOP, state='Run', vlan='20'),
            chk('Corp nutzt weiterhin WPA2-PSK', 'wlan', 'security', profile='Corp_Profile', attrs={'akm': 'psk'})],
    questions=[q('q1', 'In welchem Zustand ist ein neu angelegtes WLAN-Profil?',
                 ['Administrativ down', 'Aktiv, sobald ein AP es kennt', 'Aktiv, aber ohne Sicherheit', 'Es hängt vom AP-Modell ab'], 0,
                 'Ein neues WLAN-Profil und ein neues Policy Profile müssen aktiviert werden, bevor sie wirken.'),
        q('q2', 'Reicht es, nur das WLAN-Profil zu aktivieren?',
          ['Ja, das Policy Profile ist optional', 'Nein, auch das Policy Profile muss aktiv sein', 'Nur wenn ein VLAN gesetzt ist', 'Nur bei WPA2'], 1,
          'Die Verbindung braucht beides: das WLAN-Profil und das Policy Profile, auf das das Policy Tag verweist.')],
    solution='WebUI: Configuration > Tags & Profiles > WLANs > Corp_Profile > Edit: Status Enabled; danach unter Policy das Profil PP_Corp ebenso. '
             'CLI: `wlan Corp_Profile 1 Corp`, `no shutdown`, dann `wireless profile policy PP_Corp`, `no shutdown`.')
SOLUTIONS['02-admin-down'] = ['wlan Corp_Profile 1 Corp', 'no shutdown', 'exit', 'wireless profile policy PP_Corp', 'no shutdown']

# ---------------------------------------------------------------------------------------------------------------
lab(id='03-falscher-schluessel', title='03 Der Schlüssel passt nicht', topic='Wireless / Sicherheit',
    level='Einstieg', duration='15 min', kind='troubleshooting', prerequisites=['Lab 01'],
    goals=['Einen Authentifizierungsfehler erkennen', 'Das Problem beheben, ohne die Sicherheit abzuschalten'],
    intro='Der Laptop in der Lobby verbindet sich nicht mit Corp. Tags, Profile und VLAN sind in Ordnung. '
          'Der Schlüssel, den die Mitarbeiter kennen, lautet **Sommer2026**.',
    requirements=['Der Laptop in der Lobby ist mit Corp verbunden und im VLAN 20.',
                  'Corp bleibt mit WPA2-PSK geschützt, ein offenes WLAN ist keine Lösung.'],
    hints=['**Konzept:** Bei WPA2-PSK müssen der Schlüssel am Client und am Controller übereinstimmen.',
           '**Ebene:** Sicherheit des WLAN-Profils, nicht Zuordnung oder Zustand.',
           '**Prüfschritte:** Der Schlüssel wird nie angezeigt. Setze ihn neu und prüfe dann den Client.',
           '**Lösung:** Am WLAN-Profil den Schlüssel auf **Sommer2026** setzen. Nicht auf Open umstellen.'],
    cause='Am Controller ist ein anderer Schlüssel hinterlegt (Tippfehler), die Authentifizierung scheitert.',
    startCommands=corp(key='Sommer2025') + ['ap %s' % L1, 'policy-tag PT_Corp'],
    worldClients=[client(LAPTOP, 'Corp', 'Sommer2026', 'ap-lobby')],
    checks=[chk('Lobby-Laptop verbunden, VLAN 20', 'client', mac=LAPTOP, state='Run', vlan='20'),
            chk('Corp nutzt weiterhin WPA2-PSK', 'wlan', 'security', profile='Corp_Profile', attrs={'akm': 'psk'})],
    questions=[q('q1', 'Warum zeigt die WebUI den Pre-Shared Key nicht an?',
                 ['Damit er nicht ausgelesen werden kann', 'Weil er nicht gespeichert wird', 'Weil er nur für Gäste gilt', 'Weil das nur der Client kennen darf'], 0,
                 'Geheimnisse werden nicht zurückgegeben. Man setzt sie neu, statt sie nachzulesen.'),
        q('q2', 'Das WLAN auf Open zu stellen, würde den Laptop verbinden. Warum ist das trotzdem falsch?',
          ['Weil dann das VLAN fehlt', 'Weil Corp dann für jeden ohne Schlüssel erreichbar wäre', 'Weil Open nur im Lager geht', 'Weil der AP dann abstürzt'], 1,
          'Die Verbindung klappt, aber die Anforderung (geschütztes WLAN) ist verletzt. Das ist die Sicherheitsprüfung des Labs.')],
    solution='WebUI: WLANs > Corp_Profile > Edit: Pre-Shared Key Sommer2026. CLI: `wlan Corp_Profile 1 Corp`, `security wpa psk set-key ascii 0 Sommer2026`.')
SOLUTIONS['03-falscher-schluessel'] = ['wlan Corp_Profile 1 Corp', 'security wpa psk set-key ascii 0 Sommer2026']

# ---------------------------------------------------------------------------------------------------------------
lab(id='04-falsches-policy-profile', title='04 Richtiges WLAN, falsche Zuordnung', topic='Wireless / Tags',
    level='Mittel', duration='20 min', kind='troubleshooting', prerequisites=['Lab 01'],
    goals=['Die Zuordnung von WLAN-Profil zu Policy Profile im Policy Tag lesen', 'Nicht das erstbeste deaktivierte Objekt aktivieren'],
    intro='Der Laptop in der Lobby kommt nicht ins WLAN Corp. Der Schlüssel stimmt, der AP ist zugewiesen.\n\n'
          '- Es gibt zwei Policy Profiles: **PP_Corp** (VLAN 20, aktiv) und **PP_Gast** (VLAN 99, bisher nicht aktiviert)\n'
          '- Mitarbeiter gehören ins VLAN 20, nicht ins Gästenetz.',
    requirements=['Der Laptop in der Lobby ist mit Corp verbunden und im VLAN 20.', 'Das Gast-Policy-Profile bleibt deaktiviert.',
                  'Corp bleibt mit WPA2-PSK geschützt.'],
    hints=['**Konzept:** Das Policy Tag entscheidet, mit welchem Policy Profile ein WLAN an einem AP betrieben wird.',
           '**Ebene:** Zuordnung im Policy Tag. Die Objekte selbst sind in Ordnung.',
           '**Prüfschritte:** Unter Configuration > Tags die Zuordnung von Corp_Profile ansehen: Auf welches Policy Profile zeigt sie?',
           '**Lösung:** Im Policy Tag PT_Corp das WLAN Corp_Profile dem Policy Profile **PP_Corp** zuordnen. PP_Gast nicht aktivieren.'],
    cause='Das Policy Tag verweist für Corp auf das (deaktivierte) Gast-Profil statt auf PP_Corp.',
    startCommands=corp(tag_policy='PP_Gast') + ['wireless profile policy PP_Gast', 'vlan 99', 'exit', 'ap %s' % L1, 'policy-tag PT_Corp'],
    worldClients=[client(LAPTOP, 'Corp', 'Sommer2026', 'ap-lobby')],
    checks=[chk('Lobby-Laptop verbunden, VLAN 20', 'client', mac=LAPTOP, state='Run', vlan='20'),
            chk('Gast-Policy-Profile bleibt deaktiviert', 'policy', 'security', name='PP_Gast', attrs={'status': 'DISABLED'}),
            chk('Corp nutzt weiterhin WPA2-PSK', 'wlan', 'security', profile='Corp_Profile', attrs={'akm': 'psk'})],
    questions=[q('q1', 'Was passiert, wenn du stattdessen PP_Gast aktivierst?',
                 ['Der Laptop verbindet sich, landet aber im VLAN 99', 'Nichts, das Profil wird ignoriert', 'Der AP startet neu', 'Der Laptop bekommt zwei VLANs'], 0,
                 'Der Client wäre verbunden, aber im falschen Netz. Genau das fängt die Prüfung auf VLAN 20 ab.'),
        q('q2', 'Wo wird festgelegt, welches Policy Profile für ein WLAN gilt?',
          ['Im WLAN-Profil selbst', 'Im Policy Tag, das dem AP zugewiesen ist', 'Im Site Tag', 'Am Client'], 1,
          'Das Policy Tag ordnet je WLAN-Profil ein Policy Profile zu.')],
    solution='WebUI: Configuration > Tags & Profiles > Tags > PT_Corp > Edit: Corp_Profile → PP_Corp. CLI: `wireless tag policy PT_Corp`, `wlan Corp_Profile policy PP_Corp`.')
SOLUTIONS['04-falsches-policy-profile'] = ['wireless tag policy PT_Corp', 'wlan Corp_Profile policy PP_Corp']

# ---------------------------------------------------------------------------------------------------------------
C_LOB, C_LAG, G_LOB, G_LAG = '58bf.eaaa.0001', '58bf.eaaa.0002', '58bf.eaaa.0003', '58bf.eaaa.0004'
lab(id='05-gast-wlan-lobby', title='05 Gast-WLAN nur in der Lobby', topic='Wireless / Design',
    level='Mittel', duration='30 min', kind='requirements', prerequisites=['Lab 01', 'Lab 04'],
    goals=['Zwei WLANs mit unterschiedlichem Geltungsbereich planen', 'Mit wenigen Tags mehrere APs unterschiedlich bedienen'],
    intro='Die Firma braucht ein Gast-WLAN. Corp läuft bereits an beiden APs (VLAN 20, WPA2-PSK).\n\n'
          '- Das Gast-WLAN heißt **Gast**, ist offen und gehört ins VLAN **99**\n- Gäste gibt es nur in der Lobby\n'
          '- Je ein Laptop als Test: Corp in Lobby und Lager, Gast in Lobby und Lager',
    requirements=['Gast-WLAN (SSID Gast): Der Gast-Laptop in der Lobby ist verbunden und im VLAN 99.',
                  'Der Gast-Laptop im Lager bekommt keine Verbindung.',
                  'Corp bleibt in Lobby und Lager unverändert erreichbar (VLAN 20).',
                  'Corp bleibt mit WPA2-PSK geschützt.'],
    hints=['**Konzept:** Welche WLANs ein AP ausstrahlt, bestimmt sein Policy Tag. APs mit unterschiedlichen WLANs brauchen unterschiedliche Tags.',
           '**Ebene:** Design: Du brauchst neue Objekte (WLAN, Policy Profile) und eine neue Zuordnung.',
           '**Prüfschritte:** Lege Gast als offenes WLAN mit eigenem Policy Profile (VLAN 99) an. Überlege, welcher AP welche WLANs braucht.',
           '**Lösung:** WLAN Gast_Profile (offen) und Policy Profile PP_Gast (VLAN 99) anlegen und aktivieren, ein Policy Tag **PT_Lobby** mit Corp und Gast bilden und ap-lobby zuweisen. ap-lager behält PT_Corp.'],
    cause='Aufgabe nach Anforderungen: Es gibt keinen einzelnen Fehler.',
    startCommands=corp() + ['ap %s' % L1, 'policy-tag PT_Corp', 'exit', 'ap %s' % L2, 'policy-tag PT_Corp'],
    worldClients=[client(C_LOB, 'Corp', 'Sommer2026', 'ap-lobby'), client(C_LAG, 'Corp', 'Sommer2026', 'ap-lager'),
                  client(G_LOB, 'Gast', '', 'ap-lobby'), client(G_LAG, 'Gast', '', 'ap-lager')],
    checks=[chk('Gast-Laptop in der Lobby: verbunden, VLAN 99', 'client', mac=G_LOB, state='Run', vlan='99'),
            chk('Corp-Laptop in der Lobby: verbunden, VLAN 20', 'client', mac=C_LOB, state='Run', vlan='20'),
            chk('Corp-Laptop im Lager: verbunden, VLAN 20', 'client', mac=C_LAG, state='Run', vlan='20'),
            chk('Gast-Laptop im Lager: keine Verbindung', 'client', 'security', mac=G_LAG, state='Not Associated'),
            chk('Corp nutzt weiterhin WPA2-PSK', 'wlan', 'security', profile='Corp_Profile', attrs={'akm': 'psk'})],
    questions=[q('q1', 'Wie viele Policy Tags brauchst du mindestens für diese Anforderung?',
                 ['Eines für beide APs', 'Zwei, weil die APs unterschiedliche WLANs senden sollen', 'Eines pro WLAN', 'Keines'], 1,
                 'Ein Tag mit Corp und Gast für die Lobby, eines nur mit Corp für das Lager.'),
        q('q2', 'Was wäre die einfachste, aber falsche Lösung?',
          ['Gast in das bestehende Tag einfügen, das beide APs nutzen', 'Gast als WPA2-WLAN anlegen', 'Ein eigenes VLAN verwenden', 'Das Policy Profile aktivieren'], 0,
          'Dann sendet auch das Lager das Gast-WLAN. Die Sicherheitsprüfung für den Gast-Laptop im Lager schlägt an.')],
    solution='Gast_Profile (ID 2, offen) und PP_Gast (VLAN 99) anlegen und aktivieren; Policy Tag PT_Lobby mit Corp_Profile→PP_Corp und Gast_Profile→PP_Gast; ap-lobby auf PT_Lobby. '
             'Gleichwertig: Gast in PT_Corp ergänzen und für das Lager ein eigenes Tag nur mit Corp bilden.')
SOLUTIONS['05-gast-wlan-lobby'] = [
    'wlan Gast_Profile 2 Gast', 'no shutdown', 'exit', 'wireless profile policy PP_Gast', 'vlan 99', 'no shutdown', 'exit',
    'wireless tag policy PT_Lobby', 'wlan Corp_Profile policy PP_Corp', 'wlan Gast_Profile policy PP_Gast', 'exit',
    'ap %s' % L1, 'policy-tag PT_Lobby']

# ---------------------------------------------------------------------------------------------------------------
A_LAG = '58bf.eaaa.0005'
lab(id='06-aufraeumen', title='06 Altes WLAN sauber entfernen', topic='Wireless / Betrieb',
    level='Mittel', duration='20 min', kind='requirements', prerequisites=['Lab 01'],
    goals=['Abhängigkeiten zwischen WLAN, Policy Profile, Policy Tag und AP erkennen', 'In der richtigen Reihenfolge abbauen'],
    intro='Das alte WLAN **Alt** wird nicht mehr gebraucht. Es läuft im Lager und ist über eigene Objekte eingerichtet. Corp in der Lobby darf dabei nicht ausfallen.',
    requirements=['Das WLAN-Profil Alt_Profile, das Policy Profile PP_Alt und das Policy Tag PT_Alt sind entfernt.',
                  'Corp läuft weiter: Der Laptop in der Lobby bleibt verbunden (VLAN 20).',
                  'Die Zuordnung von Corp bleibt unverändert.'],
    hints=['**Konzept:** Objekte, die noch verwendet werden, lassen sich nicht löschen. Baue von außen nach innen ab.',
           '**Ebene:** Reihenfolge der Abhängigkeiten, nicht Funktion.',
           '**Prüfschritte:** Wer verwendet das Policy Tag, wer das WLAN, wer das Policy Profile? Die Fehlermeldung beim Löschen nennt es.',
           '**Lösung:** Erst dem AP ap-lager das Tag wegnehmen, dann das Policy Tag PT_Alt löschen, danach das WLAN Alt_Profile und das Policy Profile PP_Alt.'],
    cause='Aufgabe nach Anforderungen: Die Reihenfolge ergibt sich aus den Abhängigkeiten.',
    startCommands=corp() + ['ap %s' % L1, 'policy-tag PT_Corp', 'exit',
                            'wlan Alt_Profile 2 Alt', 'security wpa akm psk', 'security wpa psk set-key ascii 0 AltesPasswort', 'no shutdown', 'exit',
                            'wireless profile policy PP_Alt', 'vlan 30', 'no shutdown', 'exit',
                            'wireless tag policy PT_Alt', 'wlan Alt_Profile policy PP_Alt', 'exit', 'ap %s' % L2, 'policy-tag PT_Alt'],
    worldClients=[client(LAPTOP, 'Corp', 'Sommer2026', 'ap-lobby'), client(A_LAG, 'Alt', 'AltesPasswort', 'ap-lager')],
    limits=LIMITS + ['Ob das Gerät diese Abhängigkeiten beim Löschen so erzwingt, ist nicht belegt; der Simulator erzwingt sie.'],
    checks=[chk('Alt_Profile ist entfernt', 'absent', kind='wlan', name='Alt_Profile'),
            chk('PP_Alt ist entfernt', 'absent', kind='policy', name='PP_Alt'),
            chk('PT_Alt ist entfernt', 'absent', kind='tag', name='PT_Alt'),
            chk('Lobby-Laptop weiterhin verbunden, VLAN 20', 'client', mac=LAPTOP, state='Run', vlan='20'),
            chk('Corp-Zuordnung unverändert', 'tagmap', 'security', tag='PT_Corp', maps={'Corp_Profile': 'PP_Corp'})],
    questions=[q('q1', 'Warum lässt sich das WLAN-Profil zuerst nicht löschen?',
                 ['Weil es in einem Policy Tag eingetragen ist', 'Weil es aktiv ist', 'Weil ein Client verbunden ist', 'Weil es die ID 2 hat'], 0,
                 'Der Simulator verlangt, dass ein Objekt nirgends mehr verwendet wird. Zuerst das Tag am AP lösen, dann das Tag löschen, dann WLAN und Policy Profile.'),
        q('q2', 'In welcher Reihenfolge baust du ab?',
          ['AP-Zuordnung, Policy Tag, dann WLAN und Policy Profile', 'WLAN, Policy Profile, Policy Tag, AP', 'Policy Profile, WLAN, AP', 'Reihenfolge ist egal'], 0,
          'Von dem, was andere Objekte benutzt, zu dem, was benutzt wird.')],
    solution='WebUI: Wireless > Access Points > ap-lager: Tag auf Default; Tags > PT_Alt löschen; WLANs > Alt_Profile löschen; Policy > PP_Alt löschen. '
             'CLI: `ap a4b2.32aa.0002`, `no policy-tag`, `exit`, `no wireless tag policy PT_Alt`, `no wlan Alt_Profile`, `no wireless profile policy PP_Alt`.')
SOLUTIONS['06-aufraeumen'] = ['ap %s' % L2, 'no policy-tag', 'exit', 'no wireless tag policy PT_Alt', 'no wlan Alt_Profile',
                              'no wireless profile policy PP_Alt']

# ---------------------------------------------------------------------------------------------------------------
# CCNP Enterprise Wireless (ENWLSI): FlexConnect. Befehle: Cisco-Dokumente 213945/213924 (siehe docs/QUELLEN.md)
LOB_C, LAG_C = '58bf.eaaa.0001', '58bf.eaaa.0002'
FLEX_TOOLS = ['WebUI: Configuration > Tags & Profiles > Policy, Flex, Tags, Site Tags und Wireless > Access Points',
              'Monitoring > Wireless > Clients', 'Client-Diagnose (nur im geführten Modus)',
              'CLI: show ap tag summary, show wireless profile flex summary, show wireless tag site summary, show wireless client summary']
FLEX_LIMITS = LIMITS + ['Nicht modelliert: Standalone-Betrieb bei WAN-Ausfall, lokale Authentifizierung am AP, Flex-ACLs, Central DHCP/Association, '
                        'AAA-Override, VLAN-Gruppen.',
                        'Durchsatz und WAN-Last werden nicht simuliert; der Simulator unterscheidet nur zentrales und lokales Switching.']

lab(id='07-flexconnect-zweigstelle', title='07 Zweigstelle Lager: Corp lokal schalten', topic='FlexConnect / Design',
    level='Fortgeschritten', duration='40 min', kind='requirements', track=TRACK_WIFI, prerequisites=['Lab 01', 'Lab 04', 'Lab 05'],
    tools=FLEX_TOOLS, limits=FLEX_LIMITS,
    goals=['Zentrales und lokales Switching unterscheiden', 'Den Zusammenhang von Policy Profile, Flex Profile und Site Tag herstellen',
           'Eine Zweigstelle auf FlexConnect umstellen, ohne den Hauptstandort zu verändern'],
    intro='Die Firma betreibt Corp (WPA2-PSK, VLAN 20) an beiden APs; der gesamte Verkehr läuft bisher über den Controller. '
          'Das Lager ist eine Zweigstelle hinter einer langsamen WAN-Leitung.\n\n- **ap-lobby** (Hauptstandort) soll unverändert bleiben\n'
          '- **ap-lager** soll den Corp-Verkehr selbst ins **VLAN 20** schalten, statt ihn zum Controller zu tunneln\n'
          '- Je ein Laptop als Test in Lobby und Lager',
    requirements=['Der Laptop in der Lobby bleibt verbunden (VLAN 20) und wird weiter zentral geschaltet.',
                  'Der Laptop im Lager ist verbunden (VLAN 20) und wird lokal geschaltet.',
                  'ap-lager arbeitet im FlexConnect-Modus, ap-lobby bleibt im Local Mode.',
                  'Corp bleibt mit WPA2-PSK geschützt.'],
    hints=['**Konzept:** Ob ein AP Clientdaten selbst ins VLAN schaltet, hängt von seinem Betriebsmodus ab. Den legt nicht das WLAN fest, sondern ein Tag am AP.',
           '**Ebene:** Mehrere Objekte wirken zusammen: Das Policy Profile bestimmt die Switching-Art, ein Flex Profile sagt dem AP, welche VLANs er lokal kennt, und ein Site Tag bestimmt den Modus. Das Lager braucht eigene Tags.',
           '**Prüfschritte:** Lege zuerst das Flex Profile mit dem lokalen VLAN an. Das Policy Profile für lokales Switching verweist auf genau diesen VLAN-Namen. Dann Policy Tag, Site Tag ohne Local Site mit dem Flex Profile, und beide Tags dem AP zuweisen.',
           '**Lösung:** Flex Profile **FP_Lager** mit `vlan-name CORP_LOCAL` / `vlan-id 20`; Policy Profile **PP_Corp_Flex** mit `vlan CORP_LOCAL` und `no central switching`, aktiviert; Policy Tag **PT_Corp_Flex** (Corp_Profile → PP_Corp_Flex); Site Tag **ST_Lager** mit `no local-site` und `flex-profile FP_Lager`; ap-lager bekommt PT_Corp_Flex und ST_Lager.'],
    cause='Aufgabe nach Anforderungen: Es gibt keinen einzelnen Fehler.',
    startCommands=corp() + ['ap %s' % L1, 'policy-tag PT_Corp', 'exit', 'ap %s' % L2, 'policy-tag PT_Corp'],
    worldClients=[client(LOB_C, 'Corp', 'Sommer2026', 'ap-lobby'), client(LAG_C, 'Corp', 'Sommer2026', 'ap-lager')],
    checks=[chk('Lobby-Laptop: verbunden, VLAN 20, zentral geschaltet', 'client', mac=LOB_C, state='Run', vlan='20', switching='central'),
            chk('Lager-Laptop: verbunden, VLAN 20, lokal geschaltet', 'client', mac=LAG_C, state='Run', vlan='20', switching='local'),
            chk('ap-lager arbeitet im FlexConnect-Modus', 'apmode', ap='ap-lager', mode='FlexConnect'),
            chk('ap-lobby bleibt im Local Mode', 'apmode', 'security', ap='ap-lobby', mode='Local'),
            chk('Corp nutzt weiterhin WPA2-PSK', 'wlan', 'security', profile='Corp_Profile', attrs={'akm': 'psk'})],
    questions=[q('q1', 'Woran erkennt der Controller, dass ein AP im FlexConnect-Modus arbeitet?',
                 ['Am Site Tag des APs: Local Site ist ausgeschaltet', 'Am WLAN-Profil', 'Am VLAN im Policy Profile', 'Am AP-Modell'], 0,
                 'Ein Site Tag ohne Local Site versetzt jeden AP, der es erhält, in den FlexConnect-Modus (Cisco-Dokument 213945).'),
               q('q2', 'Welche VLANs gehören in das Flex Profile?',
                 ['Alle VLANs des Controllers', 'Die VLANs, die der AP lokal schalten soll', 'Nur das Management-VLAN', 'Keine, es enthält nur Timer'], 1,
                 'Das Flex Profile listet die VLANs, die der AP selbst braucht. Das VLAN für zentrales Switching steht dort nicht (Cisco-Dokument 213945).')],
    solution='WebUI: Tags & Profiles > Flex: FP_Lager mit VLAN CORP_LOCAL / 20; Policy: PP_Corp_Flex mit VLAN CORP_LOCAL, Central Switching aus, aktiviert; '
             'Tags: PT_Corp_Flex; Site Tags: ST_Lager mit Local Site aus und Flex Profile FP_Lager; Wireless > Access Points > ap-lager: beide Tags. '
             'CLI: `wireless profile flex FP_Lager` / `vlan-name CORP_LOCAL` / `vlan-id 20`; `wireless profile policy PP_Corp_Flex` / `vlan CORP_LOCAL` / `no central switching` / `no shutdown`; '
             '`wireless tag policy PT_Corp_Flex` / `wlan Corp_Profile policy PP_Corp_Flex`; `wireless tag site ST_Lager` / `no local-site` / `flex-profile FP_Lager`; '
             '`ap a4b2.32aa.0002` / `policy-tag PT_Corp_Flex` / `site-tag ST_Lager`.')
SOL07 = ['wireless profile flex FP_Lager', 'vlan-name CORP_LOCAL', 'vlan-id 20', 'exit', 'exit',
         'wireless profile policy PP_Corp_Flex', 'vlan CORP_LOCAL', 'no central switching', 'no shutdown', 'exit',
         'wireless tag policy PT_Corp_Flex', 'wlan Corp_Profile policy PP_Corp_Flex', 'exit',
         'wireless tag site ST_Lager', 'no local-site', 'flex-profile FP_Lager', 'exit',
         'ap %s' % L2, 'policy-tag PT_Corp_Flex', 'site-tag ST_Lager']
SOLUTIONS['07-flexconnect-zweigstelle'] = SOL07

# ---------------------------------------------------------------------------------------------------------------
lab(id='08-flexconnect-vlan-name', title='08 Zweigstelle: Lager-Laptop ohne Verbindung', topic='FlexConnect / Troubleshooting',
    level='Fortgeschritten', duration='25 min', kind='troubleshooting', track=TRACK_WIFI, prerequisites=['Lab 07'],
    tools=FLEX_TOOLS, limits=FLEX_LIMITS,
    goals=['Die Abhängigkeit zwischen Policy Profile und Flex Profile lesen', 'Eine Fehlersuche bei lokalem Switching systematisch führen',
           'Nicht auf zentrales Switching ausweichen, wenn lokales Switching verlangt ist'],
    intro='Das Lager wurde auf FlexConnect umgestellt: lokales Switching ins VLAN 20, eigene Tags, Site Tag ohne Local Site. '
          'Seitdem kommt der Laptop im Lager nicht mehr ins WLAN Corp. In der Lobby läuft alles.\n\n'
          '- Schlüssel, Tags und Zustände wurden geprüft und sind in Ordnung\n- Das Lager soll bei lokalem Switching bleiben.',
    requirements=['Der Laptop im Lager ist verbunden (VLAN 20) und wird lokal geschaltet.',
                  'ap-lager bleibt im FlexConnect-Modus.',
                  'Die Lobby bleibt unverändert: verbunden, VLAN 20, zentral geschaltet.'],
    hints=['**Konzept:** Bei lokalem Switching muss der AP das VLAN des Policy Profile selbst kennen. Er vergleicht dafür den Eintrag im Policy Profile mit dem, was sein Flex Profile definiert.',
           '**Ebene:** Zuordnung zwischen Policy Profile und Flex Profile. Modus, Tags und Zustände sind in Ordnung.',
           '**Prüfschritte:** Lies das Policy Profile und das Flex Profile nebeneinander. Stehen die VLAN-Angaben dort Zeichen für Zeichen gleich?',
           '**Lösung:** Den VLAN-Namen im Policy Profile PP_Corp_Flex auf **Corp_Local** setzen (oder im Flex Profile den Namen auf CORP_LOCAL ändern). Auf zentrales Switching auszuweichen ist keine Lösung.'],
    cause='Der VLAN-Name im Policy Profile (CORP_LOCAL) stimmt nicht mit dem im Flex Profile (Corp_Local) überein; die Namen müssen exakt passen.',
    startCommands=corp() + ['ap %s' % L1, 'policy-tag PT_Corp', 'exit',
                            'wireless profile flex FP_Lager', 'vlan-name Corp_Local', 'vlan-id 20', 'exit', 'exit',
                            'wireless profile policy PP_Corp_Flex', 'vlan CORP_LOCAL', 'no central switching', 'no shutdown', 'exit',
                            'wireless tag policy PT_Corp_Flex', 'wlan Corp_Profile policy PP_Corp_Flex', 'exit',
                            'wireless tag site ST_Lager', 'no local-site', 'flex-profile FP_Lager', 'exit',
                            'ap %s' % L2, 'policy-tag PT_Corp_Flex', 'site-tag ST_Lager'],
    worldClients=[client(LOB_C, 'Corp', 'Sommer2026', 'ap-lobby'), client(LAG_C, 'Corp', 'Sommer2026', 'ap-lager')],
    checks=[chk('Lager-Laptop: verbunden, VLAN 20, lokal geschaltet', 'client', mac=LAG_C, state='Run', vlan='20', switching='local'),
            chk('ap-lager bleibt im FlexConnect-Modus', 'apmode', 'security', ap='ap-lager', mode='FlexConnect'),
            chk('Lobby-Laptop unverändert: verbunden, VLAN 20, zentral geschaltet', 'client', 'security', mac=LOB_C, state='Run', vlan='20', switching='central')],
    questions=[q('q1', 'Was geschieht, wenn der VLAN-Name im Policy Profile nicht exakt im Flex Profile steht?',
                 ['Die Clients können sich nicht mit dem WLAN verbinden', 'Der AP nimmt das nächstbeste VLAN', 'Der Controller wechselt auf zentrales Switching', 'Nichts, Namen werden ignoriert'], 0,
                 'Nach Cisco-Dokument 213945 müssen die Namen exakt passen, sonst können sich Clients nicht verbinden.'),
               q('q2', 'Warum wäre zentrales Switching hier keine Lösung?',
                 ['Der Lager-Verkehr würde über das WAN zum Controller laufen, obwohl er lokal bleiben soll', 'FlexConnect lässt sich damit nicht mehr nutzen', 'Das VLAN würde gelöscht', 'Es geht nur im Local Mode'], 0,
                 'Die Anforderung ist lokales Switching im Lager. Zentrales Switching würde die Prüfung auf lokale Schaltung verfehlen.')],
    solution='WebUI: Policy > PP_Corp_Flex > Edit: VLAN Corp_Local. CLI: `wireless profile policy PP_Corp_Flex`, `vlan Corp_Local`. '
             'Gleichwertig: Im Flex Profile FP_Lager `no vlan-name Corp_Local`, `vlan-name CORP_LOCAL`, `vlan-id 20`.')
SOLUTIONS['08-flexconnect-vlan-name'] = ['wireless profile policy PP_Corp_Flex', 'vlan Corp_Local']

# ---------------------------------------------------------------------------------------------------------------
# CCNP Enterprise Wireless (ENWLSI): 802.1X mit RADIUS. Befehlskette: Cisco-Dokument 213919, AAA Override: Dokument 217043
# (ueber Websuche zitiert, siehe docs/QUELLEN.md). Der RADIUS-Server ist die simulierte Gegenseite (worldRadius).
RADIUS_USERS = [{'name': 'anna', 'password': 'Passw0rt!', 'vlan': '30'}, {'name': 'bernd', 'password': 'Geheim#2', 'vlan': '40'},
                {'name': 'carla', 'password': 'Sommer#3', 'vlan': None}]


def radius_server(ip='10.10.0.50', up=True):
    return {'ip': ip, 'auth_port': 1812, 'secret': 'RadiusKey1', 'up': up, 'nas': ['10.10.0.10'], 'users': [dict(u) for u in RADIUS_USERS]}


def eap_client(mac, user, password, ap='ap-lobby'):
    return {'mac': mac, 'ssid': 'CorpDot1x', 'eap': {'user': user, 'password': password}, 'ap': ap, 'protocol': '11ac'}


def dot1x_cfg(key='RadiusKey1', override=False):
    """Startkonfiguration: RADIUS-Server RS1, Group RG1, Methodenliste DOT1X_LIST, WLAN Corp_1X mit 802.1X, Policy Profile und Tag."""
    return ['aaa new-model',
            'radius server RS1', 'address ipv4 10.10.0.50 auth-port 1812 acct-port 1813', 'key ' + key, 'exit',
            'aaa group server radius RG1', 'server name RS1', 'exit',
            'aaa authentication dot1x DOT1X_LIST group RG1',
            'wlan Corp_1X 1 CorpDot1x', 'security wpa akm dot1x', 'security dot1x authentication-list DOT1X_LIST', 'no shutdown', 'exit',
            'wireless profile policy PP_Corp', 'vlan 20', 'no shutdown'] + (['aaa-override'] if override else []) + [
            'exit', 'wireless tag policy PT_Corp', 'wlan Corp_1X policy PP_Corp', 'exit', 'ap %s' % L1, 'policy-tag PT_Corp', 'exit']


AAA_TOOLS = ['WebUI: Configuration > Security > AAA, Configuration > Tags & Profiles > WLANs und Policy', 'Monitoring > Wireless > Clients',
             'Client-Diagnose (nur im geführten Modus)', 'CLI: show aaa servers, show wlan summary, show wireless client summary']
AAA_LIMITS = LIMITS + ['Der RADIUS-Server ist eine simulierte Gegenseite (Benutzer, Geheimnis, VLAN-Zuweisung); es gibt keine ISE-Oberfläche.',
                       'Nicht modelliert: EAP-Methoden und Zertifikate, Central Web Authentication, CoA, Accounting, Dead-Criteria-Zeiten. Die Dauern in '
                       '`show aaa servers` sind simuliert; das Gerät zeigt dort mehr Zeilen.']

lab(id='09-radius-shared-secret', title='09 802.1X: Anmeldung scheitert trotz richtiger Zugangsdaten', topic='802.1X / Troubleshooting',
    level='Fortgeschritten', duration='25 min', kind='troubleshooting', track=TRACK_WIFI, prerequisites=['Lab 01'], tools=AAA_TOOLS, limits=AAA_LIMITS,
    goals=['Die AAA-Kette vom WLAN bis zum RADIUS-Server lesen', 'Zwischen "Server antwortet nicht" und "Benutzer abgewiesen" unterscheiden',
           'Das Problem beheben, ohne die Authentifizierung abzuschwächen'],
    intro='Das WLAN **CorpDot1x** (WPA2-Enterprise) ist eingerichtet, aber Anna kommt trotz richtiger Zugangsdaten nicht hinein.\n\n'
          '- Der RADIUS-Server 10.10.0.50 läuft und ist erreichbar\n- Das Netzwerkteam hat mit dem RADIUS-Team den Wert **RadiusKey1** vereinbart\n'
          '- Zum Test: Anna (richtige Zugangsdaten) und Mallory (kein Benutzer im RADIUS) in der Lobby',
    requirements=['Anna ist mit CorpDot1x verbunden und im VLAN 20.', 'Mallory bleibt abgewiesen.', 'Das WLAN bleibt bei 802.1X.'],
    hints=['**Konzept:** Controller und RADIUS-Server müssen sich gegenseitig vertrauen. Dafür gibt es pro Server-Eintrag einen vereinbarten Wert, den beide Seiten kennen müssen.',
           '**Ebene:** Der Server-Eintrag am Controller. WLAN, Authentication List und Server Group sind in Ordnung.',
           '**Prüfschritte:** `show aaa servers` zeigt den Zustand des Servers. Steht er auf DEAD, obwohl der Server läuft, bekommt der Controller keine Antwort auf seine Anfragen.',
           '**Lösung:** Im RADIUS-Server-Eintrag **RS1** den Key auf **RadiusKey1** setzen (`key RadiusKey1`). Nicht auf Open oder PSK ausweichen.'],
    cause='Am RADIUS-Server-Eintrag RS1 steht ein anderes Shared Secret (RadiusKey2) als am Server (RadiusKey1); der Server verwirft die Anfragen.',
    startCommands=dot1x_cfg(key='RadiusKey2'), worldRadius=[radius_server()],
    worldClients=[eap_client('58bf.eaaa.0001', 'anna', 'Passw0rt!'), eap_client('58bf.eaaa.0002', 'mallory', 'egal')],
    checks=[chk('Anna: verbunden, VLAN 20', 'client', mac='58bf.eaaa.0001', state='Run', vlan='20'),
            chk('Mallory bleibt abgewiesen', 'client', 'security', mac='58bf.eaaa.0002', state='Not Associated'),
            chk('Das WLAN nutzt weiterhin 802.1X', 'wlan', 'security', profile='Corp_1X', attrs={'akm': 'dot1x'})],
    questions=[q('q1', 'Wofür dient das gemeinsame Geheimnis (Shared Secret) zwischen Controller und RADIUS-Server?',
                 ['Es identifiziert Controller und Server gegenseitig und schützt Teile der RADIUS-Nachrichten', 'Es ist das Passwort der Benutzer', 'Es verschlüsselt den WLAN-Verkehr der Clients', 'Es legt das VLAN fest'], 0,
                 'Das Secret gehört zum Eintrag des Servers. Stimmt es nicht, verwirft der Server die Anfragen. Mit den Passwörtern der Benutzer oder der Funkverschlüsselung hat es nichts zu tun.'),
               q('q2', 'Woran siehst du am Controller, dass der Server nicht antwortet?',
                 ['`show aaa servers`: State current DEAD', '`show wlan summary`: Status DOWN', '`show ap summary`: State Registered', '`show wireless client summary` ist leer'], 0,
                 'Ein Server ohne Antwort gilt als DEAD (im Simulator; die genauen Auslöser am Gerät sind nicht belegt). Die anderen Ausgaben zeigen WLAN, AP und Clients.')],
    solution='WebUI: Configuration > Security > AAA > RADIUS-Server RS1 > Edit: Key RadiusKey1. CLI: `radius server RS1`, `key RadiusKey1`.')
SOLUTIONS['09-radius-shared-secret'] = ['radius server RS1', 'key RadiusKey1']

lab(id='10-aaa-override-vlan', title='10 802.1X: Alle im selben VLAN trotz RADIUS-Zuweisung', topic='802.1X / Troubleshooting',
    level='Fortgeschritten', duration='25 min', kind='troubleshooting', track=TRACK_WIFI, prerequisites=['Lab 09'], tools=AAA_TOOLS, limits=AAA_LIMITS,
    goals=['Dynamische VLAN-Zuweisung per RADIUS verstehen', 'Den Ort der Einstellung finden: Policy Profile, nicht RADIUS oder WLAN'],
    intro='Die Anmeldung per 802.1X funktioniert für alle. Im RADIUS sind aber VLANs hinterlegt: **Anna** soll ins VLAN 30, **Bernd** ins VLAN 40. '
          '**Carla** hat im RADIUS kein VLAN und bleibt im Standard-VLAN 20 des WLANs. Zurzeit landen alle drei im VLAN 20.',
    requirements=['Anna ist verbunden und im VLAN 30.', 'Bernd ist verbunden und im VLAN 40.', 'Carla ist verbunden und im VLAN 20.',
                  'Das WLAN bleibt bei 802.1X.'],
    hints=['**Konzept:** RADIUS kann dem Controller bei der Anmeldung ein VLAN mitgeben. Ob der Controller es übernimmt, entscheidet eine Einstellung auf der Controller-Seite.',
           '**Ebene:** Policy Profile. Die Authentifizierung selbst funktioniert, WLAN und RADIUS sind in Ordnung.',
           '**Prüfschritte:** Alle drei landen im VLAN des Policy Profile: Die Angaben aus RADIUS werden ignoriert. Prüfe die Optionen des Policy Profile.',
           '**Lösung:** Im Policy Profile PP_Corp **AAA Override** einschalten (`aaa-override`). Das VLAN des Policy Profile zu ändern ist keine Lösung.'],
    cause='Im Policy Profile ist AAA Override aus: Die VLAN-Attribute aus RADIUS werden ignoriert, es gilt das VLAN des Policy Profile.',
    startCommands=dot1x_cfg(), worldRadius=[radius_server()],
    worldClients=[eap_client('58bf.eaaa.0001', 'anna', 'Passw0rt!'), eap_client('58bf.eaaa.0002', 'bernd', 'Geheim#2'), eap_client('58bf.eaaa.0003', 'carla', 'Sommer#3')],
    checks=[chk('Anna: verbunden, VLAN 30', 'client', mac='58bf.eaaa.0001', state='Run', vlan='30'),
            chk('Bernd: verbunden, VLAN 40', 'client', mac='58bf.eaaa.0002', state='Run', vlan='40'),
            chk('Carla: verbunden, VLAN 20', 'client', mac='58bf.eaaa.0003', state='Run', vlan='20'),
            chk('Das WLAN nutzt weiterhin 802.1X', 'wlan', 'security', profile='Corp_1X', attrs={'akm': 'dot1x'})],
    questions=[q('q1', 'Welche RADIUS-Attribute transportieren das VLAN?',
                 ['Tunnel-Type, Tunnel-Medium-Type und Tunnel-Private-Group-ID (64, 65, 81)', 'User-Name und User-Password', 'Framed-IP-Address', 'Session-Timeout'], 0,
                 'Laut Cisco-Dokument 217043: IETF 64 (Tunnel-Type = VLAN), 65 (Tunnel-Medium-Type = 802) und 81 (Tunnel-Private-Group-ID = VLAN-ID).'),
               q('q2', 'Was passiert mit dem VLAN aus RADIUS, wenn AAA Override im Policy Profile aus ist?',
                 ['Es wird ignoriert: Der Client landet im VLAN des Policy Profile', 'Der Client wird abgewiesen', 'Es überschreibt das WLAN-Profil', 'Der Controller wählt ein VLAN zufällig'], 0,
                 'Ohne AAA Override gilt das VLAN des Policy Profile; Carla ohne VLAN-Attribut bleibt auch mit Override dort.')],
    solution='WebUI: Tags & Profiles > Policy > PP_Corp > Edit: AAA Override ein. CLI: `wireless profile policy PP_Corp`, `aaa-override`.')
SOLUTIONS['10-aaa-override-vlan'] = ['wireless profile policy PP_Corp', 'aaa-override']

lab(id='11-radius-redundanz', title='11 802.1X: Anmeldung trotz Ausfall des ersten RADIUS-Servers', topic='802.1X / Design',
    level='Fortgeschritten', duration='30 min', kind='requirements', track=TRACK_WIFI, prerequisites=['Lab 09'], tools=AAA_TOOLS, limits=AAA_LIMITS,
    goals=['Server Groups und die Reihenfolge der Versuche verstehen', 'Redundanz herstellen, ohne den vorhandenen Eintrag umzubiegen'],
    intro='Der RADIUS-Server 10.10.0.50 ist ausgefallen, die Anmeldung per 802.1X schlägt fehl. Ein zweiter RADIUS-Server **10.10.0.51** läuft und kennt dieselben '
          'Benutzer und denselben vereinbarten Wert **RadiusKey1**. Die Anmeldung soll auch dann klappen, wenn einer der Server ausfällt.',
    requirements=['Anna ist verbunden (VLAN 20), obwohl 10.10.0.50 nicht antwortet.',
                  'Die Authentifizierung des WLANs nutzt beide RADIUS-Server (10.10.0.50 und 10.10.0.51).',
                  'Ein Benutzer mit falschem Passwort bleibt abgewiesen.', 'Das WLAN bleibt bei 802.1X.'],
    hints=['**Konzept:** Der Controller fragt die Server einer Server Group der Reihe nach. Antwortet einer nicht, nimmt er den nächsten.',
           '**Ebene:** Server-Einträge und Server Group. WLAN und Authentication List verweisen schon auf die Group.',
           '**Prüfschritte:** Der vorhandene Eintrag soll bleiben, wie er ist: Er zeigt weiter auf den ersten Server. Ergänze einen zweiten Eintrag und nimm ihn in dieselbe Group auf.',
           '**Lösung:** RADIUS-Server **RS2** mit Adresse 10.10.0.51 und Key RadiusKey1 anlegen und in die Server Group **RG1** aufnehmen (`server name RS2`). Die Adresse von RS1 nicht umbiegen.'],
    cause='Die Server Group enthält nur den ausgefallenen ersten Server; es gibt keinen zweiten Eintrag.',
    startCommands=dot1x_cfg(), worldRadius=[radius_server('10.10.0.50', up=False), radius_server('10.10.0.51')],
    worldClients=[eap_client('58bf.eaaa.0001', 'anna', 'Passw0rt!'), eap_client('58bf.eaaa.0002', 'anna', 'falsch')],
    checks=[chk('Anna: verbunden, VLAN 20', 'client', mac='58bf.eaaa.0001', state='Run', vlan='20'),
            chk('Beide RADIUS-Server sind in der Kette des WLANs', 'wlanservers', 'security', profile='Corp_1X', servers=['10.10.0.50', '10.10.0.51']),
            chk('Falsches Passwort bleibt abgewiesen', 'client', 'security', mac='58bf.eaaa.0002', state='Not Associated'),
            chk('Das WLAN nutzt weiterhin 802.1X', 'wlan', 'security', profile='Corp_1X', attrs={'akm': 'dot1x'})],
    questions=[q('q1', 'Was passiert, wenn der erste Server der Group nicht antwortet?',
                 ['Der Controller fragt den nächsten Server der Group', 'Der Client wird sofort abgewiesen', 'Der Controller wechselt auf PSK', 'Der Client wählt einen anderen Server'], 0,
                 'Die Reihenfolge der Server in der Group bestimmt die Reihenfolge der Versuche; ohne weiteren Eintrag bleibt nur der Ausfall.'),
               q('q2', 'Warum ist es keine Lösung, die Adresse von RS1 auf 10.10.0.51 umzustellen?',
                 ['Dann gibt es wieder nur einen Server und keine Redundanz', 'Weil RS1 dann nicht mehr existiert', 'Weil die Adresse nicht änderbar ist', 'Weil der Key dann nicht mehr passt'], 0,
                 'Die Anmeldung würde klappen, aber ein Ausfall von 10.10.0.51 legt wieder alles lahm. Die Prüfung verlangt beide Server in der Kette.')],
    solution='WebUI: Security > AAA: RADIUS-Server RS2 (10.10.0.51, Key RadiusKey1) anlegen; Server Group RG1 > RS2 hinzufügen. '
             'CLI: `radius server RS2` / `address ipv4 10.10.0.51 auth-port 1812 acct-port 1813` / `key RadiusKey1`; `aaa group server radius RG1` / `server name RS2`.')
SOLUTIONS['11-radius-redundanz'] = ['radius server RS2', 'address ipv4 10.10.0.51 auth-port 1812 acct-port 1813', 'key RadiusKey1', 'exit',
                                    'aaa group server radius RG1', 'server name RS2']


def main(out=OUT, verbose=True):
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith('.json'):
            os.remove(os.path.join(out, f))
    for lb in LABS:
        assert lb['id'] in SOLUTIONS, 'Loesung fehlt: ' + lb['id']
        lb = dict(lb, solutionCommands=SOLUTIONS[lb['id']])
        with open(os.path.join(out, lb['id'] + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(lb, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write('\n')
    if verbose:
        print('%d Labs geschrieben nach %s' % (len(LABS), os.path.abspath(out)))


if __name__ == '__main__':
    main(*sys.argv[1:2])
