#!/usr/bin/env python3
"""Trägt die Fragen zu den Labs 32 bis 36 in ../Pruefungssimulation/encor-pruefungssimulation.html ein (wiederholbar).

Format wie im Pool: d = Domäne, q = Frage, x = Exhibit (optional), o = Optionen, c = Index der richtigen Antwort(en),
e = Erklärung. t = "order": o steht in der richtigen Reihenfolge. t = "match": l links, o rechts, c ordnet zu.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(os.path.dirname(HERE), "Pruefungssimulation", "encor-pruefungssimulation.html")

NEW = [
    # ---- Lab 32: Multicast
    dict(d=3, q="Ein Empfänger soll per Source-Specific Multicast die Gruppe 232.1.1.1 von der Quelle 10.1.1.10 beziehen. Was muss am Empfänger-LAN gelten?",
         o=["IGMPv3 auf Host und Router, der Host meldet Gruppe und Quelle", "IGMPv2 genügt, die Quelle nennt der RP",
            "Ein statischer RP für 232.0.0.0/8 auf dem letzten Router", "PIM Dense Mode auf dem LAN-Interface"], c=[0],
         e="IGMPv3 mit Quellangabe. Nur IGMPv3 kann im Report eine Quelle nennen (INCLUDE). SSM kennt keinen RP und kein (*,G), der Router baut den (S,G)-Baum direkt zur Quelle. Einen Beitritt ohne Quelle verwirft er im SSM-Bereich."),
    dict(d=3, q="Welche Gruppe läuft laut Ausgabe als Bidirectional PIM?",
         x="R2# show ip mroute\n(*, 239.2.1.1), 00:04:10/00:03:12, RP 10.255.0.200, flags: B\n  Bidir-Upstream: Null, RPF nbr 0.0.0.0\n  Outgoing interface list:\n    GigabitEthernet0/1, Forward/Sparse, 00:04:10/00:03:12\n\n(10.1.1.10, 232.1.1.1), 00:02:01/00:02:58, flags: sT\n(*, 239.1.1.1), 00:06:00/00:02:40, RP 10.255.0.100, flags: S\n(10.1.1.10, 239.1.1.1), 00:01:30/00:02:10, flags: T",
         o=["239.2.1.1", "232.1.1.1", "239.1.1.1", "Keine, Bidir zeigt immer (S,G)-Einträge"], c=[0],
         e="239.2.1.1. Das Flag B steht für Bidir, und es gibt nur einen (*,G)-Eintrag. 232.1.1.1 ist SSM (Flag s, nur (S,G)), 239.1.1.1 ist gewöhnlicher Sparse Mode mit (*,G) und (S,G)."),
    dict(d=3, q="Was verhindert bei Bidirectional PIM Schleifen, obwohl es keinen RPF-Check gegen die Quelle gibt?",
         o=["Die Wahl eines Designated Forwarder je Segment", "Die Register-Nachricht an den RP", "Der Wechsel auf den Shortest Path Tree",
            "Der Assert-Mechanismus zwischen zwei Quellen"], c=[0],
         e="Der Designated Forwarder. Pro Segment gewinnt der Router mit der besten Unicast-Metrik zum RP, nur er leitet Verkehr in Richtung RP weiter. Register-Nachrichten und den SPT-Wechsel gibt es bei Bidir gar nicht."),
    dict(d=3, q="Zwei Router tragen dieselbe RP-Adresse (Anycast-RP). Wozu dient MSDP zwischen ihnen?",
         o=["Jeder RP teilt dem anderen mit, welche Quellen bei ihm aktiv sind", "Es wählt den aktiven RP und hält den anderen in Bereitschaft",
            "Es verteilt die RP-Adresse an alle PIM-Router", "Es ersetzt IGMP zwischen den beiden RPs"], c=[0],
         e="MSDP meldet aktive Quellen (Source-Active). Bei Anycast-RP registriert eine Quelle beim nächstgelegenen RP, ein Empfänger tritt beim nächstgelegenen RP bei. Das können verschiedene Router sein, erst MSDP bringt beide zusammen. Die Auswahl des RP erledigt das Unicast-Routing, nicht MSDP."),
    dict(d=3, q="Welche zwei Aussagen zu MSDP bei Anycast-RP sind richtig? (Wähle zwei)",
         o=["Die Sitzung läuft über TCP zwischen eindeutigen Adressen der RPs, nicht über die Anycast-Adresse",
            "`ip msdp originator-id` setzt in den SA-Meldungen eine eindeutige RP-Adresse",
            "MSDP nutzt UDP-Port 496 wie PIM Auto-RP", "Die Anycast-Adresse sollte OSPF-Router-ID beider RPs sein"], c=[0, 1],
         e="TCP (Port 639) zwischen eindeutigen Adressen, und `originator-id` für eine eindeutige Absenderangabe. Die Anycast-Adresse besitzen beide Router, als Sitzungsadresse oder Router-ID wäre sie doppelt vorhanden."),
    dict(t="match", d=3, q="Ordne jedem Multicast-Verfahren seine Eigenschaft zu.",
         l=["PIM Sparse Mode (ASM)", "SSM", "Bidir-PIM", "MSDP"],
         o=["RP nötig, erst (*,G), dann Wechsel auf (S,G)", "kein RP, nur (S,G), braucht IGMPv3", "nur (*,G), Verkehr fließt auf dem Shared Tree in beide Richtungen",
            "tauscht Informationen über aktive Quellen zwischen RPs aus"], c=[0, 1, 2, 3],
         e="ASM braucht den RP zum Kennenlernen von Quelle und Empfänger. SSM kennt die Quelle aus dem IGMPv3-Report. Bidir verzichtet ganz auf (S,G). MSDP ist kein eigenes Verteilverfahren, es verbindet RPs."),
    # ---- Lab 34: OSPF
    dict(d=3, q="R1 und R2 sind über Ethernet verbunden und zeigen einander als FULL. Trotzdem lernt keiner eine OSPF-Route vom anderen. Was ist die Ursache?",
         x="R1# show ip ospf interface Gi0/0 | include Network Type\n  Process ID 1, Router ID 10.255.0.1, Network Type BROADCAST, Cost: 1\nR2# show ip ospf interface Gi0/0 | include Network Type\n  Process ID 1, Router ID 10.255.0.2, Network Type POINT_TO_POINT, Cost: 1",
         o=["Die Netztypen passen nicht zusammen, SPF kann den Link nicht einrechnen", "Die Hello-Timer sind unterschiedlich",
            "Die MTU ist unterschiedlich", "Die Router liegen in verschiedenen Areas"], c=[0],
         e="Netztyp-Konflikt. Broadcast und Point-to-Point nutzen beide 10/40 Sekunden, deshalb kommt die Nachbarschaft zustande. Die Router beschreiben den Link in ihren LSAs aber verschieden (Transit-Netz mit DR gegen Punkt-zu-Punkt), SPF verwirft ihn. Ungleiche Timer, MTU oder Areas hätten FULL verhindert."),
    dict(d=3, q="In welchem Zustand bleibt eine OSPF-Nachbarschaft typischerweise hängen, wenn die IP-MTU der beiden Interfaces nicht übereinstimmt?",
         o=["EXSTART", "INIT", "2WAY", "LOADING"], c=[0],
         e="EXSTART (teils im Wechsel mit EXCHANGE). Die MTU steht im Database-Description-Paket, bei einer Abweichung wird es verworfen. INIT deutet auf einseitige Hellos, 2WAY ist zwischen DROTHER-Routern normal."),
    dict(d=3, q="Area 2 soll das Netz 10.1.18.0/24 aus Area 1 nicht lernen, Area 0 soll es behalten. Welche Konfiguration auf dem ABR zwischen Area 0 und Area 2 erfüllt das?",
         o=["`area 2 filter-list prefix NO-18 in`", "`area 2 filter-list prefix NO-18 out`", "`distribute-list prefix NO-18 out` unter `router ospf`",
            "`area 0 range 10.1.18.0 255.255.255.0 not-advertise`"], c=[0],
         e="`area 2 filter-list … in`. `in` filtert die Type-3-LSAs, die in Area 2 hinein angekündigt werden. `out` würde filtern, was aus Area 2 heraus geht. `distribute-list out` wirkt in OSPF nur auf redistribuierte Routen, und `area 0 range` gilt für Netze, die in Area 0 liegen."),
    dict(d=3, q="Ein Router in Area 1 erhält `distribute-list prefix NO-NET in` unter `router ospf 1`. Was ändert sich?",
         o=["Nur die eigene Routing-Tabelle, die LSDB und die Nachbarn bleiben unverändert", "Das LSA wird aus der LSDB aller Router der Area entfernt",
            "Der Router gibt das LSA nicht mehr an Nachbarn weiter", "Die Nachbarschaft wird neu aufgebaut und das Netz ausgehandelt"], c=[0],
         e="Nur die eigene Routing-Tabelle. Innerhalb einer Area müssen alle Router dieselbe LSDB haben, deshalb greift der Filter erst nach SPF beim Eintrag in die RIB. Nachbarn kennen das Netz weiter und schicken dem Router womöglich Verkehr, für den er keine Route mehr hat."),
    dict(d=3, q="Auf einem ASBR ist die statische Route 198.51.100.0/24 vorhanden, erscheint aber nicht als externe OSPF-Route. Warum?",
         x="ip prefix-list EXT-OK seq 5 permit 198.51.100.0/25\n!\nroute-map EXT permit 10\n match ip address prefix-list EXT-OK\n!\nrouter ospf 1\n redistribute static subnets route-map EXT",
         o=["Die Prefix-Liste verlangt exakt /25, die Route ist /24", "`subnets` verhindert die Verteilung von /24-Netzen",
            "Eine Route-Map ist bei `redistribute static` nicht erlaubt", "Externe Routen brauchen `default-information originate`"], c=[0],
         e="Die Präfixlänge passt nicht. Ohne `ge` oder `le` trifft ein Eintrag nur genau die angegebene Länge. Die /24-Route fällt auf das stille `deny` der Liste, die Route-Map lässt nichts durch."),
    dict(d=3, q="Welche zwei Befehle unterdrücken Routen an der Stelle, an der OSPF sie als LSA erzeugt? (Wähle zwei)",
         o=["`area 1 range 10.1.16.0 255.255.252.0 not-advertise` auf dem ABR", "`summary-address 203.0.113.0 255.255.255.0 not-advertise` auf dem ASBR",
            "`distribute-list 10 in` auf einem internen Router", "`passive-interface default` auf dem ABR"], c=[0, 1],
         e="`area range … not-advertise` (Type 3 am ABR) und `summary-address … not-advertise` (Type 5/7 am ASBR). `distribute-list in` filtert nur lokal die RIB. `passive-interface` unterbindet Nachbarschaften, das Netz wird weiter angekündigt."),
    # ---- Lab 33: Diagnose
    dict(d=4, q="Was bedeutet die Ausgabe dieses Pings?",
         x="R1# ping 192.168.3.10 size 1500 df-bit\nType escape sequence to abort.\nSending 5, 1500-byte ICMP Echos to 192.168.3.10, timeout is 2 seconds:\nPacket sent with the DF bit set\nM.M.M",
         o=["Ein Router auf dem Weg müsste fragmentieren, darf es wegen des DF-Bits aber nicht", "Das Ziel ist per ACL gesperrt",
            "Der Router hat keine Route zum Ziel", "Das Ziel antwortet nur auf jedes zweite Paket wegen Überlast"], c=[0],
         e="`M` heißt: Fragmentierung nötig, DF gesetzt (ICMP Typ 3 Code 4). Eine Strecke hat eine kleinere MTU als 1500. Die Punkte dazwischen entstehen, weil IOS solche Meldungen auf eine pro 500 ms begrenzt. Eine ACL ergäbe `U` oder `A`, eine fehlende Route `U`."),
    dict(d=4, q="Ein Ping von H1 zum Server geht durch, `traceroute` von H1 endet aber mit `!A`. Was ist die wahrscheinlichste Ursache?",
         o=["Eine ACL lässt ICMP durch, verwirft aber die UDP-Proben von Traceroute", "Auf dem Weg fehlt eine Route",
            "Die MTU einer Strecke ist zu klein", "Der Server hat ICMP-Antworten abgeschaltet"], c=[0],
         e="Eine ACL. `!A` steht für *administratively prohibited*. IOS sendet bei Traceroute UDP-Pakete an hohe Ports ab 33434, ein Ping nutzt ICMP Echo. Eine fehlende Route ergäbe `!H` oder `!N`, und dann ginge auch der Ping nicht."),
    dict(d=4, q="Du willst auf einem produktiven Router nur die OSPF-Hellos eines einzelnen Interface sehen. Welche Reihenfolge ist richtig?",
         t="order",
         o=["`logging buffered` setzen und die Konsole auf eine niedrigere Stufe begrenzen", "`debug condition interface …` setzen",
            "Bedingung mit `show debug condition` prüfen", "`debug ip ospf hello` einschalten", "Ausgabe mit `show logging` lesen",
            "`undebug all`, danach die Bedingung entfernen"],
         e="Erst das Ziel der Ausgabe absichern, dann die Bedingung setzen und prüfen, erst danach das Debug einschalten. Beim Aufräumen zuerst das Debug beenden: Würde die Bedingung zuerst entfernt, liefe das Debug kurz ungefiltert."),
    dict(d=4, q="`debug ip packet` läuft auf einem Router, zeigt aber keinen Verkehr, der durch ihn hindurchgeleitet wird. Warum?",
         o=["Das Debug zeigt nur prozessgeschaltete Pakete, Transitverkehr schaltet CEF", "Das Debug braucht zwingend eine ACL",
            "Transitverkehr erscheint nur mit `terminal monitor`", "Die Zeitstempel für Debug sind nicht aktiviert"], c=[0],
         e="CEF. `debug ip packet` sieht Pakete, die der Router im Prozess verarbeitet, also Verkehr an ihn selbst oder von ihm. Durchgeleitete Pakete nimmt CEF, ohne den Prozess zu beteiligen. Dafür eignen sich NetFlow, ein Mitschnitt oder ACL-Zähler."),
    dict(d=4, q="Welche Syslog-Stufen landen laut Konfiguration im Puffer?",
         x="logging buffered 16384 warnings\nlogging console informational\nlogging trap notifications",
         o=["0 bis 4", "4 bis 7", "nur 4", "0 bis 6"], c=[0],
         e="0 bis 4. Die angegebene Stufe ist eine Obergrenze: `warnings` (4) nimmt Emergency bis Warning auf. Debug-Meldungen (7) erscheinen hier weder im Puffer noch auf der Konsole (bis 6) noch beim Syslog-Server (bis 5)."),
    # ---- Lab 35: IP SLA
    dict(d=4, q="`track 1` ist Down, obwohl das Ziel der Messung per Ping erreichbar ist. Was fehlt?",
         x="R1# show ip sla summary\nID    Type        Destination     Stats   Return   Last\n                                  (ms)    Code     Run\n-----------------------------------------------------------\n 1    icmp-echo   10.255.1.4      -       Unknown  -\n\nR1# show running-config | section ip sla\nip sla 1\n icmp-echo 10.255.1.4 source-interface GigabitEthernet0/1\n frequency 5\ntrack 1 ip sla 1 reachability",
         o=["`ip sla schedule 1 life forever start-time now`", "`ip sla responder` auf dem Ziel", "`ip sla enable reaction-alerts`",
            "`track 1 ip sla 1 state`"], c=[0],
         e="Der Zeitplan. Eine Messung ohne `ip sla schedule` läuft nie, sie hat keine Werte und das Track-Objekt bleibt Down. Einen Responder braucht `icmp-echo` nicht."),
    dict(d=4, q="Eine Default-Route hängt an `track 1 ip sla 1 reachability`. Fällt der Provider aus, wechselt die Route alle paar Sekunden zwischen Haupt- und Ersatzweg. Was ist die Ursache?",
         o=["Das Messziel ist nach der Umschaltung über den Ersatzweg erreichbar, die Messung ist nicht auf den Hauptweg festgelegt",
            "Die Ersatzroute hat eine zu hohe administrative Distanz", "`frequency` ist kleiner als `timeout`",
            "Es fehlt `ip sla responder` beim Provider"], c=[0],
         e="Die Messung folgt der Umschaltung. Über den Ersatzweg gelingt sie wieder, das Track-Objekt geht Up, die Route springt zurück auf den defekten Weg, und alles beginnt von vorn. Abhilfe: eine Host-Route zum Messziel über den überwachten Next-Hop, dazu `delay down/up` am Track-Objekt."),
    dict(d=4, q="Welche zwei Aussagen zu `udp-jitter` sind richtig? (Wähle zwei)",
         o=["Auf dem Ziel muss `ip sla responder` aktiv sein", "Die Messung liefert Jitter und Paketverlust getrennt je Richtung",
            "Sie funktioniert gegen jedes IP-Gerät ohne Vorbereitung", "Sie nutzt ICMP Echo mit Zeitstempeln"], c=[0, 1],
         e="Responder nötig, Ergebnisse je Richtung (SD und DS). Vor der Messung handeln Sender und Responder über UDP 1967 den Port aus. Der Responder setzt Zeitstempel bei Empfang und Versand, so lässt sich seine Bearbeitungszeit herausrechnen."),
    dict(d=4, q="Eine Messung liefert den Return Code `Over threshold`. Welchen Zustand haben die beiden Track-Objekte?",
         x="track 1 ip sla 2 reachability\ntrack 2 ip sla 2 state",
         o=["track 1 Up, track 2 Down", "beide Up", "beide Down", "track 1 Down, track 2 Up"], c=[0],
         e="`reachability` ist Up bei `OK` und bei `Over threshold`, `state` nur bei `OK`. Die Messung hat geantwortet, aber langsamer als die Schwelle. `timeout` entscheidet über Erfolg, `threshold` nur über „zu langsam“."),
    # ---- Lab 36: EEM
    dict(d=6, q="In welcher Reihenfolge führt EEM die Aktionen dieses Applets aus?",
         x="event manager applet FLAPGUARD\n event syslog pattern \"LINEPROTO-5-UPDOWN\"\n action 1.0 cli command \"enable\"\n action 2.0 cli command \"configure terminal\"\n action 3.0 cli command \"interface Gi0/1\"\n action 10.0 cli command \"shutdown\"",
         o=["1.0, 10.0, 2.0, 3.0", "1.0, 2.0, 3.0, 10.0", "10.0, 3.0, 2.0, 1.0", "In der Reihenfolge der Eingabe"], c=[0],
         e="1.0, 10.0, 2.0, 3.0. EEM sortiert die Bezeichner als Zeichenketten, „10.0“ liegt vor „2.0“. `shutdown` käme im EXEC-Modus an und würde abgelehnt. Abhilfe: gleich lange Bezeichner wie 010, 020, 030."),
    dict(d=6, q="Ein Applet soll bei einem Ereignis ein Interface abschalten. Es läuft laut History, das Interface bleibt aber up. Was fehlt?",
         x="event manager applet IF-OFF\n event syslog pattern \"OSPF-5-ADJCHG.*from FULL to\"\n action 1.0 cli command \"configure terminal\"\n action 2.0 cli command \"interface GigabitEthernet0/1\"\n action 3.0 cli command \"shutdown\"\n action 4.0 cli command \"end\"",
         o=["`cli command \"enable\"` als erste Aktion", "`event manager run IF-OFF` nach dem Anlegen", "`sync yes` am Ereignis",
            "`action 5.0 set _exit_status \"1\"`"], c=[0],
         e="`enable`. Ein Applet öffnet eine eigene Sitzung im User-EXEC-Modus. Ohne `enable` wird schon `configure terminal` abgelehnt. `sync` und `_exit_status` gibt es nur bei `event cli`, und `event manager run` gilt für Applets mit `event none`."),
    dict(d=6, q="Was passiert, wenn jemand `write memory` eingibt?",
         x="event manager applet BACKUP\n event cli pattern \"^write memory\" sync yes\n action 1.0 cli command \"enable\"\n action 2.0 cli command \"copy running-config flash:backup.cfg\"\n action 3.0 syslog msg \"Sicherung geschrieben\"",
         o=["Das Applet läuft, die Konfiguration wird aber nicht gespeichert", "Erst läuft das Applet, dann wird gespeichert",
            "Applet und Befehl laufen gleichzeitig", "Der Befehl wird gespeichert, das Applet läuft nicht"], c=[0],
         e="Der Befehl wird verworfen. Bei `sync yes` wartet die CLI auf das Applet, und `_exit_status` entscheidet: nur bei 1 läuft der ursprüngliche Befehl. Hier wird er nie gesetzt. Es fehlt `action 4.0 set _exit_status \"1\"`."),
    dict(t="match", d=6, q="Ordne jedem EEM-Ereignis seinen Auslöser zu.",
         l=["`event syslog pattern`", "`event cli pattern`", "`event timer watchdog`", "`event none`", "`event track`"],
         o=["eine Logmeldung passt auf einen regulären Ausdruck", "ein eingegebener Befehl passt auf einen regulären Ausdruck",
            "wiederkehrend nach einer festen Zahl von Sekunden", "nur von Hand mit `event manager run`", "ein Track-Objekt wechselt den Zustand"],
         c=[0, 1, 2, 3, 4],
         e="Syslog und CLI vergleichen mit regulären Ausdrücken, bei CLI gegen den vollständig ausgeschriebenen Befehl. `watchdog` wiederholt sich, `countdown` läuft einmal, `cron` zu festen Zeiten. `event none` ist der Weg zum Testen."),
    dict(d=6, q="Welche zwei Aufgaben passen gut zu einem EEM-Applet? (Wähle zwei)",
         o=["Bei Verlust eines BGP-Nachbarn sofort Diagnoseausgaben auf dem Gerät sichern", "Einen gefährlichen Befehl auf dem Gerät abfangen",
            "Eine neue NTP-Konfiguration auf 400 Switches ausrollen", "Den Soll-Zustand aller Geräte zentral versionieren"], c=[0, 1],
         e="Reaktionen auf ein Ereignis direkt auf dem Gerät, auch ohne Verbindung zur Zentrale. Ausrollen und Versionieren über viele Geräte ist Aufgabe eines zentralen Werkzeugs wie Ansible oder eines Controllers."),
]


def main():
    src = open(PATH, encoding="utf-8").read()
    start = src.index("questions:[") + len("questions:")
    pool, end = json.JSONDecoder().raw_decode(src, start)
    have = {q["q"] for q in NEW}
    pool = [q for q in pool if q["q"] not in have] + NEW
    for q in NEW:
        assert q["e"] and len(q["o"]) >= 4
        if q.get("t") == "match":
            assert len(q["l"]) == len(q["o"]) == len(q["c"])
        elif q.get("t") != "order":
            assert all(0 <= c < len(q["o"]) for c in q["c"])
    open(PATH, "w", encoding="utf-8").write(src[:start] + json.dumps(pool, ensure_ascii=False) + src[end:])
    by = {}
    for q in pool:
        by[q["d"]] = by.get(q["d"], 0) + 1
    print(len(pool), "Fragen;", by, "; Exhibits:", sum(1 for q in pool if q.get("x")),
          "; Ordnen/Zuordnen:", sum(1 for q in pool if q.get("t")))


if __name__ == "__main__":
    main()
