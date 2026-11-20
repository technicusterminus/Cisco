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


# ---------------------------------------------------------------------------------------------------------------
# CCNP Enterprise Wireless (ENWLSI): Local Web Authentication. Befehlskette: Cisco-Dokument 224922, Autorisierung: 217457
# (ueber Websuche zitiert, siehe docs/QUELLEN.md). Die Portal-Anmeldung ist vereinfacht: Der Client traegt am Client-Eintrag
# seine Portal-Zugangsdaten (web), sonst bleibt er in Webauth Pending.
def web_client(mac, user=None, password=None, ap='ap-lobby'):
    c = {'mac': mac, 'ssid': 'Gast', 'ap': ap, 'protocol': '11ac'}
    if user is not None:
        c['web'] = {'user': user, 'password': password}
    return c


def guest_base():
    return ['wlan Guest 2 Gast', 'no shutdown', 'exit',
            'wireless profile policy PP_Guest', 'vlan 99', 'no shutdown', 'exit',
            'wireless tag policy PT_Guest', 'wlan Guest policy PP_Guest', 'exit', 'ap %s' % L1, 'policy-tag PT_Guest', 'exit']


def webauth_chain(authz=True):
    return ['username gast1 privilege 0 password 0 Gast#1', 'aaa authentication login WEBAUTH local'] + \
           (['aaa authorization network default local'] if authz else []) + \
           ['wlan Guest 2 Gast', 'security web-auth', 'security web-auth authentication-list WEBAUTH',
            'security web-auth parameter-map global', 'exit']


WEB_TOOLS = ['WebUI: Configuration > Security > Web Auth und Tags & Profiles > WLANs', 'Monitoring > Wireless > Clients',
             'Client-Diagnose (nur im geführten Modus)', 'CLI: show wlan summary, show wireless client summary']
WEB_LIMITS = LIMITS + ['Die Portal-Anmeldung ist vereinfacht: Es gibt keine Portalseite; der Client trägt seine Zugangsdaten im Client-Eintrag.',
                       'Nicht modelliert: Weiterleitung per HTTP, Zertifikat des Portals, Consent und Webconsent, Central Web Authentication, '
                       'externe Portale, Sitzungs-Timeouts.']

lab(id='12-webauth-authorization', title='12 Gast-WLAN: Portal-Anmeldung scheitert trotz richtigem Konto', topic='Web Authentication / Troubleshooting',
    level='Fortgeschritten', duration='25 min', kind='troubleshooting', track=TRACK_WIFI, prerequisites=['Lab 01'], tools=WEB_TOOLS, limits=WEB_LIMITS,
    goals=['Die Bausteine von Local Web Authentication kennen', 'Den fehlenden Baustein finden, ohne die Portal-Anmeldung abzuschalten'],
    intro='Das Gast-WLAN **Gast** verlangt eine Anmeldung am Portal. Der Gast **gast1** hat ein gültiges lokales Konto, bleibt aber im Zustand '
          '*Webauth Pending* hängen. Die Authentication List, die Parameter Map und der Benutzer sind vorhanden.\n\n'
          'Zum Test: gast1 (richtige Zugangsdaten) und Mallory (kein Konto) in der Lobby.',
    requirements=['gast1 ist verbunden (Zustand Run) und im VLAN 99.', 'Mallory bleibt ohne Netzzugang (Webauth Pending).',
                  'Das WLAN verlangt weiterhin die Portal-Anmeldung.'],
    hints=['**Konzept:** Die Anmeldung am Portal braucht neben der Authentication List und dem Benutzer noch eine Autorisierung.',
           '**Ebene:** Globale AAA-Konfiguration, nicht das WLAN oder das Policy Profile.',
           '**Prüfschritte:** Die Client-Diagnose nennt, was fehlt. Die Seite Security > Web Auth zeigt den Stand der Autorisierung.',
           '**Lösung:** `aaa authorization network default local` konfigurieren. Die Portal-Anmeldung nicht abschalten.'],
    cause='Die Autorisierung aaa authorization network default local fehlt; ohne sie funktioniert die lokale Portal-Anmeldung nicht.',
    startCommands=guest_base() + webauth_chain(authz=False),
    worldClients=[web_client('58bf.eaaa.0001', 'gast1', 'Gast#1'), web_client('58bf.eaaa.0002', 'mallory', 'egal')],
    checks=[chk('gast1: verbunden, VLAN 99', 'client', mac='58bf.eaaa.0001', state='Run', vlan='99'),
            chk('Mallory hat keinen Netzzugang', 'client', 'security', mac='58bf.eaaa.0002', state='Webauth Pending'),
            chk('Das WLAN verlangt weiterhin Web Authentication', 'wlan', 'security', profile='Guest', attrs={'webAuth': True})],
    questions=[q('q1', 'Was hängt am Gast-WLAN mit Web Authentication zusammen (lokale Variante)?',
                 ['Authentication List (login, local), Parameter Map, Autorisierung und lokale Benutzer', 'Nur die Parameter Map', 'Ein RADIUS-Server mit EAP', 'Ein PSK im WLAN'], 0,
                 'Laut Cisco-Dokumenten 224922 und 217457 gehören Methodenliste, Parameter Map, die Autorisierung und lokale Benutzer zusammen.'),
               q('q2', 'Warum ist es keine Lösung, Web Authentication am WLAN abzuschalten?',
                 ['Dann kommt auch Mallory ohne Konto ins Netz', 'Dann ist das WLAN down', 'Dann verliert gast1 sein Konto', 'Das geht nicht'], 0,
                 'Ohne Web Auth ist das WLAN offen: Alle Clients sind im Zustand Run, die Sicherheitsprüfung fällt durch.')],
    solution='WebUI: Security > Web Auth > Autorisierung: Konfigurieren. CLI: `aaa authorization network default local`.')
SOLUTIONS['12-webauth-authorization'] = ['aaa authorization network default local']

lab(id='13-webauth-einrichten', title='13 Gast-WLAN mit Portal-Anmeldung einrichten', topic='Web Authentication / Design',
    level='Fortgeschritten', duration='30 min', kind='requirements', track=TRACK_WIFI, prerequisites=['Lab 12'], tools=WEB_TOOLS, limits=WEB_LIMITS,
    goals=['Local Web Authentication von Grund auf einrichten', 'Die Reihenfolge der Bausteine verstehen: Liste, Autorisierung, Parameter Map, WLAN'],
    intro='Das Gast-WLAN **Gast** (VLAN 99) ist offen: Jeder kommt hinein. Es soll eine Anmeldung am Portal verlangen. Der lokale Benutzer **gast1** '
          '(Passwort **Gast#1**) soll sich anmelden dürfen. Die Parameter Map **global** ist vordefiniert und kann verwendet werden.',
    requirements=['gast1 ist verbunden (Zustand Run) und im VLAN 99.', 'Mallory (ohne Konto) bleibt ohne Netzzugang (Webauth Pending).',
                  'Das WLAN verlangt Web Authentication (Authentication List und Parameter Map gesetzt).', 'Das Gast-VLAN bleibt 99.'],
    hints=['**Konzept:** Web Authentication ist eine zweite Stufe nach dem Verbinden. Dafür braucht der Controller eine Methodenliste, eine Autorisierung und eine Parameter Map; im WLAN werden sie verknüpft.',
           '**Ebene:** Globale AAA-Konfiguration plus Sicherheits-Einstellungen im WLAN-Profil.',
           '**Prüfschritte:** Fehlt ein Baustein, bleibt gast1 in Webauth Pending; die Client-Diagnose nennt den fehlenden Baustein.',
           '**Lösung:** Benutzer gast1 anlegen; Authentication List `WEBAUTH` (login, local); `aaa authorization network default local`; im WLAN Gast Web Authentication mit dieser Liste und der Parameter Map global einschalten.'],
    cause='Das WLAN ist offen konfiguriert; es gibt weder einen Benutzer noch eine Authentication List noch die Autorisierung.',
    startCommands=guest_base(),
    worldClients=[web_client('58bf.eaaa.0001', 'gast1', 'Gast#1'), web_client('58bf.eaaa.0002', 'mallory', 'egal')],
    checks=[chk('gast1: verbunden, VLAN 99', 'client', mac='58bf.eaaa.0001', state='Run', vlan='99'),
            chk('Mallory hat keinen Netzzugang', 'client', 'security', mac='58bf.eaaa.0002', state='Webauth Pending'),
            chk('Web Authentication mit Liste und Parameter Map', 'wlan', profile='Guest',
                attrs={'webAuth': True, 'webAuthList': 'WEBAUTH', 'webAuthMap': 'global'}),
            chk('Das Gast-Policy-Profile bleibt im VLAN 99', 'policy', name='PP_Guest', attrs={'vlan': '99'})],
    questions=[q('q1', 'Wann gilt ein Client mit Web Authentication als verbunden (Run)?',
                 ['Erst nach erfolgreicher Anmeldung am Portal', 'Sobald er mit dem WLAN verbunden ist', 'Sobald er eine IP-Adresse hat', 'Wenn der AP ihn sieht'], 0,
                 'Bis zur Anmeldung steht der Client im Zustand Webauth Pending (Layer 3), danach in Run.'),
               q('q2', 'Warum reicht es nicht, nur den Benutzer anzulegen?',
                 ['Das WLAN muss Web Authentication mit Liste und Parameter Map verlangen, und die Autorisierung muss vorhanden sein', 'Benutzer gelten nur für SSH', 'Der Benutzer braucht Privilege 15', 'Der Controller muss neu starten'], 0,
                 'Das Konto allein schaltet nichts ein; die Kette WLAN, Liste, Parameter Map und Autorisierung muss stehen.')],
    solution='WebUI: Security > Web Auth: Benutzer gast1, Authentication List WEBAUTH, Autorisierung; Tags & Profiles > WLANs > Gast: Web Authentication. '
             'CLI: `username gast1 privilege 0 password 0 Gast#1`; `aaa authentication login WEBAUTH local`; `aaa authorization network default local`; '
             '`wlan Guest 2 Gast` / `security web-auth` / `security web-auth authentication-list WEBAUTH` / `security web-auth parameter-map global`.')
SOLUTIONS['13-webauth-einrichten'] = webauth_chain(authz=True)


# ---------------------------------------------------------------------------------------------------------------
# CCNP Enterprise Wireless (ENWLSI): Mobility zwischen Controllern. Befehle und Felder von show wireless mobility summary:
# Cisco-Dokument 213913 (ueber Websuche zitiert, siehe docs/QUELLEN.md). Die Gegenseite (worldMobility) ist simuliert.
def mobility_remote(knows_group='Campus', up=True):
    return {'name': 'wlc2', 'ip': '10.10.0.20', 'mac': 'aabb.cc00.0200', 'group': 'Campus', 'up': up,
            'knows': {'ip': '10.10.0.10', 'mac': 'aabb.cc00.0100', 'group': knows_group}, 'wlans': {'Corp': 'psk'}}


def roam_client(mac, psk='Sommer2026', roam=True):
    c = client(mac, 'Corp', psk, 'ap-lobby')
    if roam:
        c['roam'] = {'from': '10.10.0.20'}
    return c


MOB_TOOLS = ['WebUI: Configuration > Wireless > Mobility', 'Monitoring > Wireless > Clients', 'Client-Diagnose (nur im geführten Modus)',
             'CLI: show wireless mobility summary, show wireless client summary']
MOB_LIMITS = LIMITS + ['Die Gegenseite ist ein simulierter Controller (wlc2); ob zwei Controller sich in der Praxis genauso verhalten, ist nicht belegt.',
                       'Das Roaming ist vereinfacht: Es gibt nur "Inter-Controller" oder eine neue Sitzung. Nicht modelliert: Anchor/Foreign, Guest Anchor, '
                       'L2- und L3-Roaming im Detail, Datenverschlüsselung des Tunnels, Software-Mindestversionen.']
MOB_BASE = corp() + ['ap %s' % L1, 'policy-tag PT_Corp', 'exit']

lab(id='14-mobility-gruppenname', title='14 Roaming zwischen Controllern: Sitzung bricht ab', topic='Mobility / Troubleshooting',
    level='Fortgeschritten', duration='25 min', kind='troubleshooting', track=TRACK_WIFI, prerequisites=['Lab 01'], tools=MOB_TOOLS, limits=MOB_LIMITS,
    goals=['Lesen, was `show wireless mobility summary` über den Tunnel zu einem Peer verrät', 'Die Einstellung finden, die den Tunnel verhindert, ohne den Peer zu entfernen'],
    intro='Ein zweiter Controller **wlc2** (10.10.0.20, MAC aabb.cc00.0200, Mobility-Gruppe **Campus**) ist als Mobility-Peer eingetragen. '
          'Trotzdem verliert ein Laptop beim Wechsel von wlc2 in die Lobby seine Sitzung: Er verbindet sich neu, statt zu roamen.\n\n'
          'Zum Test: ein Laptop, der von wlc2 kommt, und ein Laptop mit falschem Schlüssel in der Lobby.',
    requirements=['Der Laptop von wlc2 ist verbunden (VLAN 20) und hat geroamt (Inter-Controller).', 'Der Mobility-Tunnel zu 10.10.0.20 ist oben (Control und Data Path).',
                  'Der Laptop mit falschem Schlüssel bleibt abgewiesen.', 'Das WLAN bleibt bei PSK.'],
    hints=['**Konzept:** Roaming zwischen Controllern setzt einen funktionierenden Mobility-Tunnel voraus. Beide Seiten müssen zueinander passen.',
           '**Ebene:** Der Peer-Eintrag am Controller. WLAN, Policy und Tags sind in Ordnung.',
           '**Prüfschritte:** `show wireless mobility summary` zeigt Control und Data Path des Peers; die Client-Diagnose nennt, woran der Tunnel scheitert.',
           '**Lösung:** Den Peer-Eintrag mit dem richtigen Gruppennamen **Campus** neu setzen (`wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus`). Den Peer nicht entfernen.'],
    cause='Im Peer-Eintrag steht der Gruppenname Zentrale; der Controller wlc2 gehört zur Gruppe Campus. Der Tunnel kommt nicht hoch.',
    startCommands=MOB_BASE + ['wireless mobility group name Campus', 'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Zentrale'],
    worldMobility=[mobility_remote('Campus')],
    worldClients=[roam_client('58bf.eaaa.0001'), roam_client('58bf.eaaa.0002', psk='falsch', roam=False)],
    checks=[chk('Laptop von wlc2: verbunden, VLAN 20, geroamt', 'client', mac='58bf.eaaa.0001', state='Run', vlan='20', roam='Inter-Controller'),
            chk('Mobility-Tunnel zu 10.10.0.20 ist oben', 'mobilitypeer', ip='10.10.0.20'),
            chk('Laptop mit falschem Schlüssel bleibt abgewiesen', 'client', 'security', mac='58bf.eaaa.0002', state='Not Associated'),
            chk('Das WLAN nutzt weiterhin PSK', 'wlan', 'security', profile='Corp_Profile', attrs={'akm': 'psk'})],
    questions=[q('q1', 'Was zeigt `show wireless mobility summary` für den Peer?',
                 ['Gruppenname, MAC-Adresse und den Zustand von Control und Data Path', 'Die Clients des Peers', 'Die WLANs des Peers', 'Die Laufzeit des Peers'], 0,
                 'Die Ausgabe nennt die Mobility-Daten dieses Controllers und die Peers samt Tunnelzustand (im Simulator in einem vereinfachten Format).'),
               q('q2', 'Warum ist es keine Lösung, den Peer-Eintrag zu entfernen?',
                 ['Dann gibt es keinen Tunnel mehr, und der Laptop roamt nicht', 'Dann ist das WLAN down', 'Dann verliert der Laptop seine IP-Adresse', 'Das geht nicht'], 0,
                 'Ohne Peer gibt es keinen Tunnel; der Laptop verbindet sich zwar, aber als neue Sitzung. Die Prüfung verlangt Roaming.')],
    solution='WebUI: Configuration > Wireless > Mobility > Peer 10.10.0.20 > Edit: Gruppenname Campus. '
             'CLI: `wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus`.')
SOLUTIONS['14-mobility-gruppenname'] = ['wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus']

lab(id='15-mobility-einrichten', title='15 Mobility mit einem neuen Controller einrichten', topic='Mobility / Design',
    level='Fortgeschritten', duration='30 min', kind='requirements', track=TRACK_WIFI, prerequisites=['Lab 14'], tools=MOB_TOOLS, limits=MOB_LIMITS,
    goals=['Mobility zwischen zwei Controllern von Grund auf einrichten', 'Verstehen, dass beide Seiten zueinander passen müssen'],
    intro='Der neue Controller **wlc2** (10.10.0.20, MAC aabb.cc00.0200, Mobility-Gruppe **Campus**) soll Mobility-Peer werden. Das Team von wlc2 hat diesen Controller '
          'dort bereits eingetragen: mit seiner IP und MAC und mit dem Gruppennamen **Zentrale**. Hier ist noch nichts eingerichtet.',
    requirements=['Der Mobility-Tunnel zu 10.10.0.20 ist oben (Control und Data Path).', 'Der Laptop von wlc2 ist verbunden (VLAN 20) und hat geroamt (Inter-Controller).',
                  'Der Laptop mit falschem Schlüssel bleibt abgewiesen.'],
    hints=['**Konzept:** Mobility braucht eine Konfiguration auf beiden Seiten, und beide müssen übereinstimmen: Wie die Gegenseite uns kennt, und wie wir sie kennen.',
           '**Ebene:** Globale Mobility-Einstellungen: der eigene Gruppenname und der Peer-Eintrag.',
           '**Prüfschritte:** `show wireless mobility summary` zeigt den eigenen Gruppennamen und den Zustand des Peers; die Client-Diagnose nennt, woran der Tunnel scheitert.',
           '**Lösung:** Eigenen Gruppennamen auf **Zentrale** setzen (`wireless mobility group name Zentrale`) und den Peer mit MAC, IP und der Gruppe **Campus** eintragen (`wireless mobility group member mac-address … ip … group Campus`).'],
    cause='Es ist keine Mobility konfiguriert: Der eigene Gruppenname ist der Standardwert, und es gibt keinen Peer-Eintrag.',
    startCommands=MOB_BASE, worldMobility=[mobility_remote('Zentrale')],
    worldClients=[roam_client('58bf.eaaa.0001'), roam_client('58bf.eaaa.0002', psk='falsch', roam=False)],
    checks=[chk('Mobility-Tunnel zu 10.10.0.20 ist oben', 'mobilitypeer', ip='10.10.0.20'),
            chk('Laptop von wlc2: verbunden, VLAN 20, geroamt', 'client', mac='58bf.eaaa.0001', state='Run', vlan='20', roam='Inter-Controller'),
            chk('Laptop mit falschem Schlüssel bleibt abgewiesen', 'client', 'security', mac='58bf.eaaa.0002', state='Not Associated')],
    questions=[q('q1', 'Was muss für einen funktionierenden Mobility-Tunnel auf beiden Seiten stimmen?',
                 ['Der Peer ist mit passender IP, MAC und Gruppe eingetragen, und die Gegenseite kennt diesen Controller ebenfalls richtig', 'Nur die IP-Adressen', 'Nur der Gruppenname', 'Nichts, Tunnel bauen sich selbst auf'], 0,
                 'Im Simulator kommt der Tunnel nur hoch, wenn beide Einträge zueinander passen (Simulator-Modell).'),
               q('q2', 'Warum reicht der Peer-Eintrag allein nicht?',
                 ['Die Gegenseite erwartet diesen Controller unter dem Gruppennamen Zentrale, hier ist noch der Standardname gesetzt', 'Weil Peers nur mit Passwort funktionieren', 'Weil der Eintrag erst nach einem Neustart gilt', 'Weil das WLAN fehlt'], 0,
                 'Der eigene Gruppenname gehört zur Konfiguration der Gegenseite: Sie hat diesen Controller dort eingetragen.')],
    solution='WebUI: Configuration > Wireless > Mobility: Gruppenname Zentrale; Peer 10.10.0.20 hinzufügen (MAC, Gruppe Campus). '
             'CLI: `wireless mobility group name Zentrale`; `wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus`.')
SOLUTIONS['15-mobility-einrichten'] = ['wireless mobility group name Zentrale', 'wireless mobility group member mac-address aabb.cc00.0200 ip 10.10.0.20 group Campus']


# ---------------------------------------------------------------------------------------------------------------
# CCNP Enterprise Wireless (ENWLSI): RF-Profile und RF Tags. Struktur (ap dot11 <band> rf-profile, wireless tag rf, Zuordnung per AP) und
# der Stolperstein "RF-Profil wirkt nicht, weil der RF Tag nicht am AP haengt": Cisco-Dokument 213911 und Community-Beitraege, die Befehle
# tx-power min/max und 5ghz-rf-policy stammen aus einem Community-Beispiel (nicht offiziell, siehe docs/QUELLEN.md).
RF_TOOLS = ['WebUI: Configuration > Tags & Profiles > RF und Configuration > Wireless > Access Points', 'CLI: show ap tag summary']
RF_LIMITS = LIMITS + ['Die Wirkung eines RF-Profils ist vereinfacht: maximale Sendeleistung und Band an/aus je AP. Es gibt keine Funkumgebung, keine Clients mit Signalstärke und kein RRM.',
                      'Nicht modelliert: DCA und Kanalbreite, Datenraten, Band Select, Coverage Hole Detection, RX-SOP, Tx-Power-Wertebereiche des Geräts '
                      '(der Simulator erlaubt 1 bis 30 dBm).']
RF_PROFILE_CMDS = ['ap dot11 5ghz rf-profile RF_LOBBY', 'tx-power max 14', 'no shutdown', 'exit']
RF_TAG_CMDS = ['wireless tag rf RFT_LOBBY', '5ghz-rf-policy RF_LOBBY', 'exit']
RF_LOBBY = {'profile': 'RF_LOBBY', 'txMax': 14, 'radio': 'on'}
RF_GLOBAL = {'profile': None, 'txMax': None, 'radio': 'on'}

lab(id='16-rf-tag-fehlt', title='16 RF-Profil angelegt, aber die Lobby sendet unverändert', topic='RF / Troubleshooting',
    level='Fortgeschritten', duration='20 min', kind='troubleshooting', track=TRACK_WIFI, prerequisites=['Lab 01'], tools=RF_TOOLS, limits=RF_LIMITS,
    goals=['Die Kette RF-Profil, RF Tag und AP-Zuordnung kennen', 'Die Wirkung auf einen einzelnen AP begrenzen'],
    intro='Für die Lobby sollen kleinere Funkzellen gelten: Das RF-Profil **RF_LOBBY** begrenzt das 5-GHz-Band auf 14 dBm und ein RF Tag **RFT_LOBBY** verweist darauf. '
          'Trotzdem sendet **ap-lobby** unverändert mit den globalen Einstellungen. **ap-lager** soll unverändert bleiben.',
    requirements=['ap-lobby nutzt im 5-GHz-Band das Profil RF_LOBBY (max. 14 dBm, Funk an).', 'ap-lager bleibt bei den globalen Einstellungen.'],
    hints=['**Konzept:** Ein RF-Profil wirkt nie allein. Es braucht einen Verweis aus einem RF Tag, und der AP muss dieses RF Tag tragen.',
           '**Ebene:** Die AP-Zuordnung. Profil und RF Tag selbst sind in Ordnung.',
           '**Prüfschritte:** `show ap tag summary` zeigt das RF Tag jedes APs; die Seite Configuration > Wireless > Access Points zeigt die Wirkung je Band.',
           '**Lösung:** Dem AP ap-lobby das RF Tag **RFT_LOBBY** zuweisen (`ap a4b2.32aa.0001`, `rf-tag RFT_LOBBY`). Nicht das Default RF Tag ändern: Das träfe auch ap-lager.'],
    cause='ap-lobby trägt das Default RF Tag; das RF Tag RFT_LOBBY mit dem Profil ist keinem AP zugewiesen.',
    startCommands=RF_PROFILE_CMDS + RF_TAG_CMDS,
    checks=[chk('ap-lobby nutzt RF_LOBBY im 5-GHz-Band', 'aprf', ap='ap-lobby', band='5ghz', attrs=RF_LOBBY),
            chk('ap-lager bleibt bei den globalen Einstellungen', 'aprf', 'security', ap='ap-lager', band='5ghz', attrs=RF_GLOBAL)],
    questions=[q('q1', 'Wann wirkt ein RF-Profil an einem AP?',
                 ['Wenn ein RF Tag darauf verweist und der AP dieses RF Tag trägt', 'Sobald es angelegt und aktiviert ist', 'Sobald der AP neu startet', 'Nur im FlexConnect-Modus'], 0,
                 'Die Kette ist Profil, RF Tag, AP. Ein Profil ohne zugewiesenes RF Tag bleibt wirkungslos.'),
               q('q2', 'Warum ist es keine Lösung, das Default RF Tag auf das Profil zeigen zu lassen?',
                 ['Dann gilt es für alle APs, auch ap-lager', 'Das Default RF Tag lässt sich nicht ändern', 'Dann wird das Band abgeschaltet', 'Dann verliert die Lobby ihre Policy'], 0,
                 'Das Default RF Tag tragen alle APs ohne eigenes Tag. Die Anforderung begrenzt die Wirkung auf die Lobby.')],
    solution='WebUI: Configuration > Wireless > Access Points > ap-lobby > Edit Tags: RF Tag RFT_LOBBY. CLI: `ap a4b2.32aa.0001`, `rf-tag RFT_LOBBY`.')
SOLUTIONS['16-rf-tag-fehlt'] = ['ap %s' % L1, 'rf-tag RFT_LOBBY']

lab(id='17-rf-lobby-einrichten', title='17 Kleinere Funkzellen in der Lobby einrichten', topic='RF / Design',
    level='Fortgeschritten', duration='25 min', kind='requirements', track=TRACK_WIFI, prerequisites=['Lab 16'], tools=RF_TOOLS, limits=RF_LIMITS,
    goals=['Ein RF-Profil, ein RF Tag und die Zuordnung von Grund auf einrichten', 'Typische Stolpersteine kennen: neues Profil ist zunächst deaktiviert'],
    intro='In der Lobby sollen die Zellen im 5-GHz-Band kleiner werden: maximal **14 dBm** Sendeleistung. Nur **ap-lobby** ist betroffen, **ap-lager** und das 2,4-GHz-Band '
          'bleiben unverändert. Es gibt noch kein RF-Profil und kein RF Tag.',
    requirements=['ap-lobby nutzt im 5-GHz-Band ein RF-Profil mit max. 14 dBm und eingeschaltetem Funk.', 'ap-lager bleibt bei den globalen Einstellungen.',
                  'Das 2,4-GHz-Band von ap-lobby bleibt bei den globalen Einstellungen.'],
    hints=['**Konzept:** Profil anlegen, in einem RF Tag je Band darauf verweisen, das RF Tag dem AP zuweisen.',
           '**Ebene:** RF-Profil für 5 GHz, RF Tag, AP-Zuordnung.',
           '**Prüfschritte:** Ein neu angelegtes RF-Profil ist zunächst deaktiviert und schaltet das Band ab. Prüfe den Status in der Seite Configuration > Wireless > Access Points.',
           '**Lösung:** `ap dot11 5ghz rf-profile RF_LOBBY` mit `tx-power max 14` und `no shutdown`; `wireless tag rf RFT_LOBBY` mit `5ghz-rf-policy RF_LOBBY`; am AP `rf-tag RFT_LOBBY`.'],
    cause='Es gibt weder ein RF-Profil noch ein RF Tag; der AP nutzt das Default RF Tag.',
    startCommands=[],
    checks=[chk('ap-lobby nutzt ein RF-Profil im 5-GHz-Band mit 14 dBm und Funk an', 'aprf', ap='ap-lobby', band='5ghz', attrs={'profile': 'RF_LOBBY', 'txMax': 14, 'radio': 'on'}),
            chk('ap-lager bleibt bei den globalen Einstellungen', 'aprf', 'security', ap='ap-lager', band='5ghz', attrs=RF_GLOBAL),
            chk('Das 2,4-GHz-Band von ap-lobby bleibt global', 'aprf', 'security', ap='ap-lobby', band='24ghz', attrs=RF_GLOBAL)],
    questions=[q('q1', 'Was bewirkt ein deaktiviertes RF-Profil, auf das ein RF Tag verweist?',
                 ['Das Band wird an den APs mit diesem RF Tag abgeschaltet', 'Nichts, es wird ignoriert', 'Die Sendeleistung wird auf das Minimum gesetzt', 'Der AP startet neu'], 0,
                 'Ein deaktiviertes Profil, einem RF Tag zugewiesen, ist ein gängiger Weg, ein Band an bestimmten APs abzuschalten (Community-Beitrag; im Simulator so festgelegt).'),
               q('q2', 'Warum bleibt ap-lager unverändert?',
                 ['Es trägt weiter das Default RF Tag', 'Weil es im Local Mode läuft', 'Weil es kein 5-GHz-Funkmodul hat', 'Weil RF-Profile nur einen AP betreffen'], 0,
                 'Die Wirkung hängt am RF Tag des einzelnen APs.')],
    solution='WebUI: Tags & Profiles > RF: RF-Profil RF_LOBBY (5 GHz, max 14, Enabled), RF Tag RFT_LOBBY mit diesem Profil; Wireless > Access Points > ap-lobby: RF Tag RFT_LOBBY. '
             'CLI: `ap dot11 5ghz rf-profile RF_LOBBY` / `tx-power max 14` / `no shutdown`; `wireless tag rf RFT_LOBBY` / `5ghz-rf-policy RF_LOBBY`; `ap a4b2.32aa.0001` / `rf-tag RFT_LOBBY`.')
SOLUTIONS['17-rf-lobby-einrichten'] = RF_PROFILE_CMDS + RF_TAG_CMDS + ['ap %s' % L1, 'rf-tag RFT_LOBBY', 'exit']


# ---------------------------------------------------------------------------------------------------------------
# CCNP Enterprise Wireless (ENWLSI): QoS mit Metal-Profilen. Cisco-Dokument 222241 (ueber Websuche zitiert, siehe docs/QUELLEN.md):
# service-policy input/output im Policy Profile, hoechste DSCP-Werte Bronze 8, Silver 0, Gold 34, Platinum 46.
def qos_client(mac, ssid, dscp, psk=None, ap='ap-lobby'):
    c = {'mac': mac, 'ssid': ssid, 'ap': ap, 'protocol': '11ac', 'dscp': dscp}
    if psk is not None:
        c['psk'] = psk
    return c


def qos_base(corp_out='', corp_in='', guest_out='', guest_in=''):
    """Startkonfiguration: WLAN Corp (PSK, PP_Corp, VLAN 20) und WLAN Gast (offen, PP_Guest, VLAN 99) in einem Policy Tag an ap-lobby."""
    def svc(out, inn):
        return (['service-policy output ' + out] if out else []) + (['service-policy input ' + inn] if inn else [])
    return ['wlan Corp_Profile 1 Corp', 'security wpa akm psk', 'security wpa psk set-key ascii 0 Sommer2026', 'no shutdown', 'exit',
            'wlan Guest 2 Gast', 'no shutdown', 'exit',
            'wireless profile policy PP_Corp', 'vlan 20', 'no shutdown'] + svc(corp_out, corp_in) + [
            'exit', 'wireless profile policy PP_Guest', 'vlan 99', 'no shutdown'] + svc(guest_out, guest_in) + [
            'exit', 'wireless tag policy PT_QOS', 'wlan Corp_Profile policy PP_Corp', 'wlan Guest policy PP_Guest', 'exit', 'ap %s' % L1, 'policy-tag PT_QOS', 'exit']


QOS_TOOLS = ['WebUI: Configuration > Tags & Profiles > Policy', 'Monitoring > Wireless > Clients', 'Client-Diagnose (nur im geführten Modus)',
             'CLI: show wireless profile policy summary, show wireless client summary']
QOS_LIMITS = LIMITS + ['QoS ist stark vereinfacht: Ein Client sendet Verkehr mit einem DSCP-Wert; das Metal-Profil im Policy Profile begrenzt den höchsten Wert je Richtung. '
                       'Es gibt keine Bandbreite, keine Warteschlangen, kein AVC und keine WMM-Zuordnung.',
                       'Das Cisco-Dokument 222241 beschreibt die Metal-Profile für APs im Local Mode; FlexConnect ist dort nicht behandelt, der Simulator wertet es gleich aus.',
                       'Ohne service-policy gibt es im Simulator keine Begrenzung; das Standardverhalten des Geräts ist nicht belegt.']
VOICE = qos_client('58bf.eaaa.0001', 'Corp', 46, psk='Sommer2026')
GUEST_TOUCH = qos_client('58bf.eaaa.0002', 'Gast', 46)

lab(id='18-qos-metal-falsch', title='18 Sprache im Corp-WLAN verliert ihre Priorität', topic='QoS / Troubleshooting',
    level='Fortgeschritten', duration='20 min', kind='troubleshooting', track=TRACK_WIFI, prerequisites=['Lab 01'], tools=QOS_TOOLS, limits=QOS_LIMITS,
    goals=['Die Metal-Profile und ihren höchsten DSCP-Wert kennen', 'Beide Richtungen (Output und Input) im Policy Profile beachten'],
    intro='Ein Laptop im Corp-WLAN sendet Sprache mit **DSCP 46**, aber sie wird auf dem Weg abgewertet. Das Gast-WLAN soll weiterhin begrenzt bleiben: '
          'Auch dort sendet ein Laptop mit DSCP 46, soll aber höchstens DSCP 8 bekommen.',
    requirements=['Der Corp-Laptop behält DSCP 46 in beide Richtungen (zum Client und vom Client).', 'Der Gast-Laptop wird in beide Richtungen auf DSCP 8 begrenzt.'],
    hints=['**Konzept:** Ein Metal-Profil legt den höchsten DSCP-Wert fest, der in der jeweiligen Richtung erhalten bleibt. Jedes Profil gilt für einen Wert, den der Verkehr nicht übersteigen darf.',
           '**Ebene:** Das Policy Profile der Corp-Clients. Das Gast-Profil ist in Ordnung.',
           '**Prüfschritte:** Die Seite Monitoring > Clients bzw. die Client-Diagnose zeigt, welcher DSCP-Wert je Richtung ankommt. Die Policy-Seite zeigt das Profil je Richtung.',
           '**Lösung:** Im Policy Profile **PP_Corp** Output **platinum** und Input **platinum-up** setzen (`service-policy output platinum`, `service-policy input platinum-up`). Das Gast-Profil nicht ändern.'],
    cause='Das Policy Profile PP_Corp nutzt Silver (höchster DSCP 0); die Sprache wird zu Best Effort abgewertet.',
    startCommands=qos_base('silver', 'silver-up', 'bronze', 'bronze-up'), worldClients=[VOICE, GUEST_TOUCH],
    checks=[chk('Corp-Laptop: DSCP 46 in beide Richtungen', 'client', mac='58bf.eaaa.0001', state='Run', dscpDown=46, dscpUp=46),
            chk('Gast-Laptop: DSCP 8 in beide Richtungen', 'client', 'security', mac='58bf.eaaa.0002', state='Run', dscpDown=8, dscpUp=8)],
    questions=[q('q1', 'Welchen höchsten DSCP-Wert lässt das Metal-Profil Platinum zu?',
                 ['46', '34', '8', '0'], 0, 'Laut Cisco-Dokument 222241: Platinum 46, Gold 34, Bronze 8, Silver 0.'),
               q('q2', 'Warum ist es keine Lösung, auch das Gast-Profil auf Platinum zu setzen?',
                 ['Dann könnten auch Gäste Sprache mit hoher Priorität senden', 'Das Gast-Profil lässt sich nicht ändern', 'Dann verliert der Corp-Laptop seine Verbindung', 'Platinum gilt nur für Corp'], 0,
                 'Die Anforderung begrenzt Gäste auf DSCP 8. Mit Platinum käme ihr Verkehr unbegrenzt durch.')],
    solution='WebUI: Tags & Profiles > Policy > PP_Corp > Edit: QoS Output platinum, QoS Input platinum-up. CLI: `wireless profile policy PP_Corp`, `service-policy output platinum`, `service-policy input platinum-up`.')
SOLUTIONS['18-qos-metal-falsch'] = ['wireless profile policy PP_Corp', 'service-policy output platinum', 'service-policy input platinum-up']

lab(id='19-qos-gast-begrenzen', title='19 Gäste in beide Richtungen begrenzen', topic='QoS / Design',
    level='Fortgeschritten', duration='25 min', kind='requirements', track=TRACK_WIFI, prerequisites=['Lab 18'], tools=QOS_TOOLS, limits=QOS_LIMITS,
    goals=['Ein Metal-Profil in beiden Richtungen setzen', 'Verstehen, dass Output und Input getrennt konfiguriert werden'],
    intro='Im Gast-WLAN sendet ein Laptop Verkehr mit **DSCP 46**. Gäste sollen höchstens **DSCP 8** (Bronze) bekommen, in beide Richtungen. '
          'Das Corp-WLAN darf nicht gebremst werden: Dort bleibt DSCP 46 erhalten. Zurzeit ist nirgends QoS konfiguriert.',
    requirements=['Der Gast-Laptop wird in beide Richtungen auf DSCP 8 begrenzt.', 'Der Corp-Laptop behält DSCP 46 in beide Richtungen.'],
    hints=['**Konzept:** Das Metal-Profil gilt je Richtung getrennt: zum Client (Output) und vom Client (Input). Beide gehören zum selben Profil.',
           '**Ebene:** Das Policy Profile der Gäste.',
           '**Prüfschritte:** Die Client-Diagnose zeigt den DSCP-Wert je Richtung. Ist nur eine Richtung begrenzt, bleibt die andere unverändert.',
           '**Lösung:** Im Policy Profile **PP_Guest** Output **bronze** und Input **bronze-up** setzen.'],
    cause='Im Policy Profile der Gäste ist keine service-policy konfiguriert; der Verkehr wird nicht begrenzt.',
    startCommands=qos_base(), worldClients=[VOICE, GUEST_TOUCH],
    checks=[chk('Gast-Laptop: DSCP 8 in beide Richtungen', 'client', mac='58bf.eaaa.0002', state='Run', dscpDown=8, dscpUp=8),
            chk('Corp-Laptop bleibt bei DSCP 46 in beide Richtungen', 'client', 'security', mac='58bf.eaaa.0001', state='Run', dscpDown=46, dscpUp=46)],
    questions=[q('q1', 'Was passiert, wenn nur `service-policy output bronze` gesetzt ist?',
                 ['Der Verkehr zum Client ist begrenzt, der vom Client nicht', 'Beide Richtungen sind begrenzt', 'Das Profil wird abgelehnt', 'Der Client wird getrennt'], 0,
                 'Output und Input sind getrennte Einstellungen. Ohne Input-Profil bleibt der Verkehr vom Client unverändert (Simulator-Modell).'),
               q('q2', 'Warum ist es keine Lösung, das Gast-Profil auf Silver zu setzen?',
                 ['Silver begrenzt auf DSCP 0, die Anforderung nennt DSCP 8', 'Silver gibt es nicht', 'Silver gilt nur für Corp', 'Silver lässt alles durch'], 0,
                 'Laut Cisco-Dokument 222241 liegt der höchste Wert bei Silver 0 und bei Bronze 8.')],
    solution='WebUI: Tags & Profiles > Policy > PP_Guest > Edit: QoS Output bronze, QoS Input bronze-up. CLI: `wireless profile policy PP_Guest`, `service-policy output bronze`, `service-policy input bronze-up`.')
SOLUTIONS['19-qos-gast-begrenzen'] = ['wireless profile policy PP_Guest', 'service-policy output bronze', 'service-policy input bronze-up']


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
