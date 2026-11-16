from lab_34 import gi, lo

HOST = "no ip routing\ninterface GigabitEthernet0/0\n ip address 192.168.1.10 255.255.255.0\n no shutdown\nip default-gateway 192.168.1.1"

LAB = dict(
    slug="35-IPSLA-Tracking-Jitter", num="35",
    title="IP SLA vertieft: Tracking mit Floating Static, UDP-Jitter mit Responder, TCP-Connect", minutes=90, level="mittel",
    summary=("Lab 04 nutzt IP SLA nur als Zulieferer für PBR. Ziel 4.4 verlangt, IP SLA selbst zu konfigurieren und zu "
             "prüfen. Hier baust du einen Standort mit zwei Providern: Eine Messung überwacht den Weg über ISP1 und "
             "schaltet bei einem Ausfall *hinter* dem Provider-Router auf ISP2 um. Dabei läufst du absichtlich in die "
             "zwei klassischen Fehler (Messung nicht gestartet, Messung folgt der Umschaltung). Danach misst du Jitter "
             "und Paketverlust mit einem Responder und die Antwortzeit eines TCP-Dienstes."),
    goals=["Eine IP-SLA-Messung anlegen, starten und ihren Zustand in `show ip sla statistics` lesen.",
           "Eine statische Route per `track` an eine Messung binden und mit einer Floating Static Route absichern.",
           "Begründen, warum das Messziel fest über den überwachten Weg geroutet sein muss.",
           "UDP-Jitter mit `ip sla responder` einrichten und Jitter, Verlust und Laufzeit je Richtung ablesen.",
           "`reachability` und `state` beim Tracking unterscheiden und Schwellwerte (`threshold`, `timeout`, `frequency`) einordnen."],
    tags=[("4.4", "IP SLA", 22)],
    diagram="""
                    ┌──── R2 (ISP1) ────┐
              Gi0/1 │ Gi0/0       Gi0/1 │ Gi0/0
  H1 ──── R1 ───────┤                   ├─────── R4   Lo0 10.255.0.4 (Dienst)
     Gi0/0    Gi0/2 │ Gi0/0       Gi0/1 │ Gi0/1       Lo1 10.255.1.4 (Messziel)
                    └──── R3 (ISP2) ────┘
""",
    nets=[("H1 – R1 Gi0/0", "192.168.1.0/24 (H1 .10, R1 .1)"), ("R1 Gi0/1 – R2 Gi0/0", "10.0.12.0/30 (.1/.2)"),
          ("R1 Gi0/2 – R3 Gi0/0", "10.0.13.0/30 (.1/.2)"), ("R2 Gi0/1 – R4 Gi0/0", "10.0.24.0/30 (.1/.2)"),
          ("R3 Gi0/1 – R4 Gi0/1", "10.0.34.0/30 (.1/.2)")],
    topo_text=("R2, R3 und R4 sind **fertig konfiguriert** (statische Routen). R4 steht für das Internet: Loopback0 10.255.0.4 "
               "ist der Dienst, den H1 erreichen will, Loopback1 10.255.1.4 dient nur als Messziel. Telnet auf R4 ist offen "
               "(Passwort `cisco`). R1 hat noch keine Route nach außen, das ist deine Aufgabe.\n\n"
               "**Ausfall simulieren:** `shutdown` auf **R4 Gi0/0**. Der Link R1–R2 bleibt dabei up, R1 merkt also von sich "
               "aus nichts. Genau diesen Fall soll IP SLA abdecken."),
    steps=[
        dict(t="Das Problem sehen.", body="Setze auf R1 `ip route 0.0.0.0 0.0.0.0 10.0.12.2` und als Ersatz `ip route 0.0.0.0 0.0.0.0 10.0.13.2 10`. Prüfe `ping 10.255.0.4` von H1. Schalte dann R4 Gi0/0 ab.",
             predict="Schaltet R1 auf ISP2 um?",
             check="Vor dem Ausfall geht der Ping. Danach nicht mehr: `show ip route 0.0.0.0` auf R1 zeigt weiter 10.0.12.2, Gi0/1 ist up/up. Schalte R4 Gi0/0 wieder ein.",
             think="Unter welcher Bedingung nimmt ein Router eine statische Route mit Next-Hop-Adresse aus der Tabelle?"),
        dict(t="Messung anlegen und starten.", body="Auf R1: `ip sla 1`, darin `icmp-echo 10.255.1.4 source-interface GigabitEthernet0/1`, `threshold 500`, `timeout 1000`, `frequency 5`. Sieh dir `show ip sla summary` an, **bevor** du `ip sla schedule 1 life forever start-time now` setzt.",
             predict="In welchem Zustand steht die Messung ohne `schedule`?",
             check="Ohne `schedule`: Zustand `Pending`, keine Messwerte. Mit `schedule`: `Active`. Der Return Code ist aber noch `Timeout` oder `No connection`, denn R1 hat keine brauchbare Route zum Messziel.",
             think="`frequency`, `timeout` und `threshold` stehen in einer festen Größenbeziehung. In welcher, und in welcher Einheit ist jeder Wert?"),
        dict(t="Messziel festnageln.", body="Setze auf R1 `ip route 10.255.1.4 255.255.255.255 10.0.12.2`.",
             check="`show ip sla statistics 1` zeigt `Latest operation return code: OK` und einen steigenden Zähler bei den Erfolgen.",
             think="Diese Host-Route wirkt jetzt überflüssig, die Default-Route zeigt ja ohnehin auf ISP1. Hebe dir die Frage für Schritt 5 auf."),
        dict(t="Route an die Messung binden.", body="`track 1 ip sla 1 reachability`. Ersetze die erste Default-Route durch `ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1`. Starte auf H1 `ping 10.255.0.4 repeat 1000` und schalte R4 Gi0/0 ab.",
             predict="Wie viele Pings gehen ungefähr verloren, bis ISP2 übernimmt?",
             check="Nach wenigen Sekunden meldet R1 `%TRACK-…-STATE: 1 ip sla 1 reachability Up -> Down`. `show ip route 0.0.0.0` zeigt 10.0.13.2 mit Distanz 10. Der Ping läuft weiter. Schalte R4 Gi0/0 wieder ein und beobachte die Rückkehr.",
             think="Woraus setzt sich die Umschaltzeit zusammen?"),
        dict(t="Die Falle: Messung folgt der Umschaltung.", body="Entferne die Host-Route aus Schritt 3 (`no ip route 10.255.1.4 255.255.255.255 10.0.12.2`). Schalte R4 Gi0/0 erneut ab und beobachte R1 eine Minute lang.",
             predict="Was passiert mit `track 1`, sobald die Default-Route auf ISP2 zeigt?",
             check="Das Log zeigt abwechselnd `Up -> Down` und `Down -> Up`, die Default-Route springt alle paar Sekunden. Setze die Host-Route wieder und schalte R4 Gi0/0 ein.",
             think="Erkläre den Kreislauf in drei Sätzen."),
        dict(t="Flattern dämpfen.", body="Setze unter `track 1` den Befehl `delay down 10 up 30`.",
             check="`show track 1` nennt beide Verzögerungen. Bei einem kurzen Ausfall unter 10 Sekunden bleibt die Route stehen.",
             think="Warum wählt man die Verzögerung für `up` meist länger als für `down`?"),
        dict(t="UDP-Jitter mit Responder.", body="Auf R1: `ip sla 2` mit `udp-jitter 10.255.1.4 16384 num-packets 20 interval 20`, `threshold 500`, `frequency 30`, dazu der `schedule`. Sieh dir das Ergebnis an und setze **erst dann** auf R4 `ip sla responder`.",
             predict="Was meldet die Messung, solange der Responder fehlt?",
             check="Ohne Responder: Return Code `No connection`. Mit Responder: `OK`, und `show ip sla statistics 2` zeigt Laufzeit, Jitter und Paketverlust getrennt nach Richtung (SD = Source to Destination, DS = zurück). `show ip sla responder` auf R4 zählt die Kontrollnachrichten.",
             think="Warum braucht `udp-jitter` einen Responder, `icmp-echo` aber nicht? Welchen Vorteil hat der Responder für die Genauigkeit?"),
        dict(t="TCP-Connect.", body="Auf R1: `ip sla 3` mit `tcp-connect 10.255.1.4 23 control disable`, `frequency 30`, dazu der `schedule`.",
             check="`show ip sla statistics 3` zeigt `OK` und die Dauer des Verbindungsaufbaus.",
             think="Wozu dient `control disable` hier?"),
        dict(t="`state` gegen `reachability`.", body="Lege `track 2 ip sla 2 state` an. Setze dann in `ip sla 2` testweise `threshold 1`. (Dazu musst du die Messung stoppen: `no ip sla schedule 2 …`, ändern, neu starten.)",
             predict="Die Jitter-Messung funktioniert weiter. Welchen Zustand zeigt `track 2`?",
             check="`show ip sla statistics 2`: Return Code `Over threshold`. `show track 2`: `Down`. Ein `track … reachability` auf dieselbe Messung bliebe `Up`. Setze `threshold 500` zurück.",
             think="Wann nimmst du `state`, wann `reachability`?"),
        dict(t="Melden lassen.", body="Setze `ip sla logging traps` und `ip sla reaction-configuration 1 react timeout threshold-type immediate action-type trapOnly`. Schalte R4 Gi0/0 kurz ab.",
             check="Im Log von R1 erscheint eine `%RTT-…`-Meldung zur Messung 1. `show ip sla reaction-configuration 1` nennt Reaktion und Schwelltyp.")],
    answers=[
        ("1", "**Nein.** Eine statische Route bleibt in der Tabelle, solange der Next-Hop rekursiv auflösbar ist, also solange das Ausgangs-Interface up ist. Ein Ausfall einen Hop weiter verändert daran nichts. Der Router braucht eine Messung, die den ganzen Weg prüft."),
        ("2", "**`Pending`.** Eine Messung ohne `schedule` läuft nie. Das ist der häufigste IP-SLA-Fehler überhaupt. Zu den Werten: `frequency` in Sekunden, `timeout` und `threshold` in Millisekunden. Es gilt threshold ≤ timeout < frequency. `timeout` entscheidet über Erfolg oder Misserfolg, `threshold` nur darüber, ob ein Erfolg als „zu langsam“ gilt."),
        ("4", "Rund **zwei bis drei Pings** bei einem Ping pro Sekunde und ohne `delay`: bis zu 5 Sekunden bis zur nächsten Messung, 1 Sekunde Timeout, dann reagiert das Track-Objekt und die Routing-Tabelle wird neu berechnet. Wer schneller umschalten will, senkt `frequency` und `timeout`, zahlt dafür aber mit mehr Fehlalarmen."),
        ("5", "Die Messung fällt aus, `track 1` geht Down, die Default-Route wechselt auf ISP2. Ohne Host-Route erreicht die Messung ihr Ziel jetzt über ISP2 und ist erfolgreich, `track 1` geht Up, die Default-Route wechselt zurück auf den kaputten ISP1. Dort fällt die Messung wieder aus, und alles beginnt von vorn. Die Host-Route zwingt die Messung dauerhaft auf den Weg, den sie überwachen soll. Deshalb nimmt man ein eigenes Messziel und nicht die Adresse des eigentlichen Dienstes."),
        ("6", "Ein Ausfall soll schnell erkannt werden, die Rückkehr aber erst gelten, wenn der Weg eine Weile stabil ist. Sonst pendelt der Verkehr bei einer wackligen Leitung ständig hin und her, und jede Umschaltung kostet Verbindungen."),
        ("7", "**`No connection`.** `udp-jitter` handelt vor jeder Messung über die Kontrollverbindung (UDP 1967) aus, auf welchem Port der Responder lauschen soll. Ohne Responder antwortet niemand auf dem UDP-Port. `icmp-echo` beantwortet jedes IP-Gerät von sich aus. Der Responder setzt außerdem Zeitstempel beim Empfang und beim Senden. So lässt sich seine eigene Bearbeitungszeit herausrechnen und die Laufzeit je Richtung bestimmen."),
        ("8", "Port 23 beantwortet der Telnet-Dienst von R4 selbst. `control disable` schaltet die Kontrollverbindung zum Responder ab, die sonst vorab versucht würde. So misst du auch gegen Geräte, die gar kein Cisco-Router sind, etwa einen Webserver auf Port 443."),
        ("9", "**`Down`.** `reachability` ist Up bei den Return Codes `OK` und `Over threshold`, `state` nur bei `OK`. Nimm `reachability`, wenn es um „Weg da oder nicht“ geht, etwa für eine Ersatzroute. Nimm `state`, wenn auch ein zu langsamer Weg als Ausfall zählen soll, etwa für Sprachverkehr.")],
    nodes=[
        dict(name="R1", type="router", x=200, y=200,
             base="\n".join(["interface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0\n no shutdown",
                             gi(1, "10.0.12.1"), gi(2, "10.0.13.1")]),
             sol="""
ip sla 1
 icmp-echo 10.255.1.4 source-interface GigabitEthernet0/1
 threshold 500
 timeout 1000
 frequency 5
ip sla schedule 1 life forever start-time now
ip sla 2
 udp-jitter 10.255.1.4 16384 num-packets 20 interval 20
 threshold 500
 frequency 30
ip sla schedule 2 life forever start-time now
ip sla 3
 tcp-connect 10.255.1.4 23 control disable
 frequency 30
ip sla schedule 3 life forever start-time now
ip sla logging traps
ip sla reaction-configuration 1 react timeout threshold-type immediate action-type trapOnly
track 1 ip sla 1 reachability
 delay down 10 up 30
track 2 ip sla 2 state
ip route 10.255.1.4 255.255.255.255 10.0.12.2
ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1
ip route 0.0.0.0 0.0.0.0 10.0.13.2 10"""),
        dict(name="R2", type="router", x=400, y=100,
             base="\n".join([gi(0, "10.0.12.2"), gi(1, "10.0.24.1"), "ip route 192.168.1.0 255.255.255.0 10.0.12.1",
                             "ip route 10.255.0.4 255.255.255.255 10.0.24.2", "ip route 10.255.1.4 255.255.255.255 10.0.24.2"]),
             sol=""),
        dict(name="R3", type="router", x=400, y=300,
             base="\n".join([gi(0, "10.0.13.2"), gi(1, "10.0.34.1"), "ip route 192.168.1.0 255.255.255.0 10.0.13.1",
                             "ip route 10.255.0.4 255.255.255.255 10.0.34.2", "ip route 10.255.1.4 255.255.255.255 10.0.34.2"]),
             sol=""),
        dict(name="R4", type="router", x=600, y=200,
             base="\n".join([lo(0, "10.255.0.4", "255.255.255.255"), lo(1, "10.255.1.4", "255.255.255.255"),
                             gi(0, "10.0.24.2"), gi(1, "10.0.34.2"),
                             "ip route 192.168.1.0 255.255.255.0 10.0.24.1", "ip route 192.168.1.0 255.255.255.0 10.0.34.1",
                             "ip route 10.0.12.0 255.255.255.252 10.0.24.1", "ip route 10.0.13.0 255.255.255.252 10.0.34.1",
                             "line vty 0 4\n password cisco\n login\n transport input telnet"]),
             sol="ip sla responder"),
        dict(name="H1", type="host", x=0, y=200, base=HOST, sol="", vpcs="ip 192.168.1.10/24 192.168.1.1")],
    links=[("H1", "Gi0/0", "R1", "Gi0/0"), ("R1", "Gi0/1", "R2", "Gi0/0"), ("R1", "Gi0/2", "R3", "Gi0/0"),
           ("R2", "Gi0/1", "R4", "Gi0/0"), ("R3", "Gi0/1", "R4", "Gi0/1")],
    vpcs=True,
    vpcs_note="H1 sendet nur Pings und Traceroutes, ein VPCS genügt: `ping 10.255.0.4 -c 1000` statt `ping … repeat 1000`.",
    staggered=True,
    tickets=["Der gesamte Verkehr von H1 läuft über ISP2, obwohl ISP1 in Ordnung ist. `show track 1` auf R1 steht auf `Down`.",
             "Sobald Ticket 1 gelöst ist: `show ip route 0.0.0.0` auf R1 zeigt zwei Next-Hops. Ein Teil der Verbindungen läuft weiter über ISP2.",
             "Die Jitter-Messung (IP SLA 2) liefert seit dem letzten Wartungsfenster nur `No connection`.",
             "Sobald Ticket 3 gelöst ist: `show track 2` bleibt `Down`, obwohl die Jitter-Messung Werte liefert."],
    faults=[
        dict(node="R1", old="ip sla schedule 1 life forever start-time now", new=None,
             find="`show ip sla summary` zeigt Messung 1 im Zustand `Pending`. `show ip sla statistics 1` hat keine Startzeit und keine Zähler. Mit `show ip sla configuration 1` siehst du: kein Zeitplan.",
             cause="Die Messung ist angelegt, aber nie gestartet. Ein Track-Objekt auf eine nicht laufende Messung ist Down, die Route mit `track 1` fehlt in der Tabelle.",
             fix="`ip sla schedule 1 life forever start-time now`.",
             inject=["no ip sla schedule 1"], revert=["ip sla schedule 1 life forever start-time now"],
             probe=("R1", "show track 1", r"Reachability is Up"), settle=50),
        dict(node="R1", old="ip route 0.0.0.0 0.0.0.0 10.0.13.2 10", new="ip route 0.0.0.0 0.0.0.0 10.0.13.2",
             find="`show ip route 0.0.0.0` zeigt beide Next-Hops mit Distanz 1. `show running-config | include ip route 0.0.0.0`: Der zweiten Route fehlt die Distanz.",
             cause="Ohne höhere administrative Distanz ist die Ersatzroute gleichwertig. Der Router verteilt die Last auf beide Provider, statt ISP2 nur im Notfall zu nutzen.",
             fix="`no ip route 0.0.0.0 0.0.0.0 10.0.13.2`, dann `ip route 0.0.0.0 0.0.0.0 10.0.13.2 10`.",
             inject=["no ip route 0.0.0.0 0.0.0.0 10.0.13.2 10", "ip route 0.0.0.0 0.0.0.0 10.0.13.2"],
             revert=["no ip route 0.0.0.0 0.0.0.0 10.0.13.2", "ip route 0.0.0.0 0.0.0.0 10.0.13.2 10"],
             probe=("R1", "show ip route 0.0.0.0", r"10\.0\.13\.2", False), settle=5),
        dict(node="R4", old="ip sla responder", new=None,
             find="`show ip sla responder` auf R4: Responder nicht aktiv. Auf R1 zeigt `show ip sla statistics 2` den Return Code `No connection`, während die ICMP-Messung 1 auf dasselbe Ziel funktioniert.",
             cause="`udp-jitter` braucht auf der Gegenseite den Responder. Er fehlt in der Konfiguration von R4.",
             fix="`ip sla responder` auf R4.",
             inject=["no ip sla responder"], revert=["ip sla responder"],
             probe=("R1", "show ip sla statistics 2", r"return code: OK"), settle=70),
        dict(node="R1", old=" threshold 500", new=" threshold 1", nth=1,
             find="`show ip sla statistics 2`: Return Code `Over threshold`. `show ip sla configuration 2` nennt als Schwelle 1 ms. `show track 2` überwacht `state`, nicht `reachability`.",
             cause="Die Schwelle von 1 ms unterschreitet kein realer Weg. Jede Messung gilt als zu langsam, und `track … state` wertet das als Ausfall.",
             fix="Messung 2 stoppen, `threshold 500` setzen, neu starten. (Oder bewusst auf `track 2 ip sla 2 reachability` wechseln.)",
             inject=["no ip sla schedule 2", "ip sla 2", "threshold 1", "exit", "ip sla schedule 2 life forever start-time now"],
             revert=["no ip sla schedule 2", "ip sla 2", "threshold 500", "exit", "ip sla schedule 2 life forever start-time now"],
             probe=("R1", "show track 2", r"State is Up"), settle=70)],
    verify=["show ip sla summary", "show ip sla configuration 1", "show ip sla statistics [1|2|3]", "show track",
            "show ip route 0.0.0.0", "show ip route track-table", "show ip sla responder                 ! auf R4",
            "show ip sla reaction-configuration 1"],
    verify_table=[("`show ip sla summary`", "Messungen 1 bis 3 `Active`, Return Code `OK`"),
                  ("`show track 1`", "`Reachability is Up`, Verzögerung 10/30 Sekunden"),
                  ("`show ip route 0.0.0.0` im Normalfall", "nur 10.0.12.2, Distanz 1"),
                  ("dasselbe bei abgeschaltetem R4 Gi0/0", "nur 10.0.13.2, Distanz 10"),
                  ("`show ip sla statistics 2`", "Jitter und Verlust für SD und DS, Return Code `OK`")],
    checks=[("R1", "show track 1", r"Reachability is Up"), ("R1", "show ip route 0.0.0.0", r"10\.0\.12\.2"),
            ("R1", "show ip sla statistics 2", r"return code: OK"), ("R1", "show ip sla statistics 3", r"return code: OK"),
            ("H1", "ping 10.255.0.4", r"Success rate is (80|100) percent")],
    settle=90,
    teilc=[("Eine Messung zeigt `Latest operation return code: Timeout`, obwohl ein Ping von der Konsole an dasselbe Ziel geht. Was prüfst du?",
            "**Die Quelle.** Der Ping von der Konsole nimmt die Adresse des Ausgangs-Interface. Die Messung nimmt, was unter `source-interface` oder `source-ip` steht. Hat die Gegenseite keine Rückroute zu dieser Adresse, oder ist die Messung in einer VRF (`vrf …` in der Messung fehlt), scheitert nur die Messung."),
           ("Warum lässt sich eine laufende Messung nicht ändern?",
            "**Weil ihre Parameter mit dem Start festgeschrieben werden.** Erst `no ip sla schedule N` (oder die Messung löschen), dann ändern, dann neu starten. In der Prüfung zeigt ein Exhibit oft genau die Fehlermeldung dazu."),
           ("HSRP soll die Priorität senken, wenn der Uplink zwar up ist, das Internet aber nicht erreichbar. Welche Bausteine brauchst du?",
            "**IP SLA, Track-Objekt, HSRP-Tracking.** `ip sla` misst ein Ziel hinter dem Uplink, `track 1 ip sla 1 reachability` übersetzt das Ergebnis in Up/Down, `standby 1 track 1 decrement 20` senkt die Priorität. Dazu `preempt` auf dem Partner, sonst übernimmt er nicht."),
           ("Welche Messung nimmst du für Sprachqualität, und was liefert sie zusätzlich, wenn du einen Codec angibst?",
            "**`udp-jitter` mit `codec`**, etwa `udp-jitter … codec g711ulaw`. Sie wählt Paketgröße und Abstand passend zum Codec und berechnet aus Laufzeit, Jitter und Verlust die Kennzahlen **MOS** und **ICPIF**.")],
    exam=["Ablauf: Messung definieren, mit `ip sla schedule` starten, mit `show ip sla statistics` prüfen. Ohne Schedule `Pending`.",
          "Einheiten: `frequency` Sekunden, `timeout` und `threshold` Millisekunden; threshold ≤ timeout < frequency.",
          "Tracking: `track N ip sla M reachability` (OK oder Over threshold) gegen `state` (nur OK); `delay down/up`.",
          "Floating Static: Ersatzroute mit höherer Distanz, Hauptroute mit `track`.",
          "Responder: `ip sla responder` auf dem Ziel, Kontrollverbindung UDP 1967; nötig für `udp-jitter`, optional für `tcp-connect` und `udp-echo`.",
          "Messarten: icmp-echo, udp-jitter, udp-echo, tcp-connect, http, dns, path-echo."],
    caveat=("In einer virtuellen Umgebung bleibt die Gegenseite eines Links up, wenn du ein Interface abschaltest. Deshalb "
            "simulierst du den Ausfall auf R4 und nicht auf R2. Die genauen Texte der Return Codes und der `%TRACK`-Meldungen "
            "können je nach IOSv-Version leicht abweichen."),
)
