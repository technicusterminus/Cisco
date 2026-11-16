from lab_32 import router, P30, P24

LOG = """
service timestamps debug datetime msec
logging buffered 16384 debugging
logging console informational"""

R2_BASE = router(2, [("GigabitEthernet0/0", "10.0.12.2") + P30, ("GigabitEthernet0/1", "10.0.23.1") + P30]).replace(
    " ip address 10.0.23.1 255.255.255.252\n", " ip address 10.0.23.1 255.255.255.252\n ip mtu 1400\n")
R3_BASE = router(3, [("GigabitEthernet0/0", "10.0.23.2") + P30, ("GigabitEthernet0/1", "192.168.3.1") + P24]).replace(
    " ip address 10.0.23.2 255.255.255.252\n", " ip address 10.0.23.2 255.255.255.252\n ip mtu 1400\n")

LAB = dict(
    slug="33-Diagnose-Ping-Traceroute-Debug", num="33",
    title="Diagnose: Ping und Traceroute lesen, Debug und Conditional Debug sicher einsetzen", minutes=90, level="mittel",
    summary=("Ziel 4.1 verlangt, Netzprobleme mit Debugs, Conditional Debugs, Traceroute, Ping, SNMP und Syslog einzugrenzen. "
             "SNMP und Syslog übst du in Lab 08. Hier geht es um die Werkzeuge an der Konsole: Du lernst, die Zeichen von "
             "Ping und Traceroute als Befund zu lesen, eine MTU-Engstelle auszumessen und Debug-Ausgaben so einzugrenzen, "
             "dass sie den Router nicht lahmlegen. Das Netz ist fertig geroutet, damit die Werkzeuge im Mittelpunkt stehen."),
    goals=["Aus `!`, `.`, `U`, `M` und `!A`, `!H`, `*` ablesen, welches Gerät geantwortet hat und warum.",
           "Mit erweitertem Ping (Quelle, Größe, DF-Bit, Sweep) die Pfad-MTU bestimmen.",
           "Erklären, warum ein Ping durchgeht, während Traceroute scheitert, und umgekehrt.",
           "Debug-Ausgaben in den Puffer statt auf die Konsole lenken, per ACL filtern und mit `debug condition` auf ein Interface begrenzen.",
           "Für ein Symptom zuerst das passende Werkzeug wählen, statt alles einzuschalten."],
    tags=[("4.1", "Diagnose, SNMP und Syslog", 40)],
    diagram="""
                                    MTU 1400
  H1 ──── R1 ──────────── R2 ════════════════ R3 ──── SRV
     Gi0/0   Gi0/1    Gi0/0   Gi0/1       Gi0/0   Gi0/1
  .10      .1                                    .1      .10
""",
    nets=[("H1 – R1 Gi0/0", "192.168.1.0/24 (H1 .10, R1 .1)"), ("R1 Gi0/1 – R2 Gi0/0", "10.0.12.0/30 (.1/.2)"),
          ("R2 Gi0/1 – R3 Gi0/0", "10.0.23.0/30 (.1/.2), `ip mtu 1400` auf beiden Seiten"),
          ("R3 Gi0/1 – SRV", "192.168.3.0/24 (R3 .1, SRV .10)")],
    topo_text=("Loopback0: R1 10.255.0.1, R2 10.255.0.2, R3 10.255.0.3 (/32). OSPF 1 (Area 0) ist **fertig konfiguriert**. "
               "Der Link R2–R3 steht für eine Strecke mit kleinerer MTU, etwa einen Tunnel oder eine Provider-Leitung. "
               "H1 und SRV sind IOS-Geräte mit `no ip routing`.\n\n"
               "**Regel für dieses Lab:** Jedes Debug endet mit `undebug all`. Prüfe mit `show debugging`, dass nichts mehr läuft, "
               "bevor du den nächsten Schritt beginnst."),
    steps=[
        dict(t="Ping-Zeichen lesen.", body="Sende von H1 drei Pings: an SRV (`ping 192.168.3.10`), an einen Host, den es im Server-Netz nicht gibt (`ping 192.168.3.99`), und an ein Netz, das niemand kennt (`ping 10.99.99.99`).",
             predict="Welche Zeichen erwartest du beim zweiten und beim dritten Ping, `.` oder `U`? Und welches Gerät erzeugt sie?",
             check="Erster Ping `!!!!!`. Zweiter Ping `.....`. Dritter Ping `U.U.U`.",
             think="Warum wechseln sich beim dritten Ping `U` und `.` ab, statt fünfmal `U` zu zeigen?"),
        dict(t="Pfad-MTU ausmessen.", body="Sende von R1 `ping 192.168.3.10 source Loopback0 size 1500 df-bit`. Starte danach den erweiterten Ping (nur `ping` eingeben) mit DF-Bit und einem Sweep von 1390 bis 1410 in Einerschritten.",
             predict="Welches Zeichen zeigt der erste Ping, und von welcher Adresse kommt die Meldung dazu?",
             check="Der erste Ping zeigt `M.M.M`. Im Sweep sind die Größen bis 1400 erfolgreich, ab 1401 erscheint `M`. `debug ip icmp` auf R1 zeigt während des Pings die Meldung „frag. needed and DF set“ von 10.0.12.2.",
             think="Was steht in der ICMP-Meldung, damit der Absender seine Paketgröße anpassen kann? Was passiert mit TCP-Verbindungen, wenn ein Gerät auf dem Weg diese Meldung unterdrückt?"),
        dict(t="Traceroute lesen.", body="Führe auf H1 `traceroute 192.168.3.10` aus.",
             predict="Wie viele Zeilen erscheinen, und warum zeigt die letzte Zeile meist `x msec * y msec` mit einem Stern in der Mitte?",
             check="Vier Zeilen: 192.168.1.1, 10.0.12.2, 10.0.23.2, 192.168.3.10. Die letzte Zeile enthält einen Stern.",
             think="Welche Pakete sendet IOS bei Traceroute, und mit welcher ICMP-Meldung antworten die Router unterwegs, mit welcher das Ziel?"),
        dict(t="Ping geht, Traceroute nicht.", body="Lege auf R3 die ACL `TRANSIT` an und binde sie auf Gi0/0 eingehend: `permit ospf any any`, `permit icmp any any`, `permit tcp any any`, `deny ip any any log`. Wiederhole Ping und Traceroute von H1 zu SRV.",
             predict="Bis zu welchem Hop kommt Traceroute, und welches Zeichen steht dort?",
             check="Der Ping geht durch. Traceroute zeigt die Hops 1 und 2 und in Zeile 3 `!A` von 10.0.23.2. `show access-lists TRANSIT` zählt Treffer auf der `deny`-Zeile. Füge danach mit einer Sequenznummer **vor** dem `deny` die Zeile `permit udp any any range 33434 33534` ein und prüfe, dass Traceroute wieder vier Zeilen zeigt.",
             think="Windows sendet bei `tracert` ICMP Echo statt UDP. Was hätte ein Windows-Client mit der ersten Fassung der ACL gesehen?"),
        dict(t="Debug sicher einschalten.", body="Setze auf R1 bis R3 `service timestamps debug datetime msec`, `logging buffered 16384 debugging` und `logging console informational`. Schalte auf R3 `debug ip icmp` ein und pinge von R1 die 10.255.0.3. Lies das Ergebnis mit `show logging`, dann `undebug all`.",
             predict="Erscheinen die Debug-Zeilen jetzt noch auf der Konsole von R3?",
             check="Auf der Konsole erscheint nichts. `show logging` zeigt die Zeilen „ICMP: echo reply sent“ mit Zeitstempel in Millisekunden. `show debugging` ist nach `undebug all` leer.",
             think="Warum ist die Konsole der gefährlichste Ort für Debug-Ausgaben? Auf welchem Weg siehst du Debugs in einer SSH-Sitzung?"),
        dict(t="Debug per ACL filtern.", body="Lege auf R3 `access-list 199 permit icmp host 192.168.1.10 host 10.255.0.3` an und schalte `debug ip packet 199 detail` ein. Pinge von H1 zuerst die 10.255.0.3, dann SRV (192.168.3.10). Danach `undebug all`.",
             predict="Für welchen der beiden Pings zeigt R3 Debug-Zeilen?",
             check="Nur der Ping an 10.255.0.3 erscheint in `show logging`, mit ICMP-Typ 8. Der Ping an SRV läuft durch R3 hindurch und taucht nicht auf.",
             think="Die ACL hätte den zweiten Ping ohnehin nicht erfasst. Aber selbst mit `debug ip packet` ohne ACL wäre er nicht erschienen. Warum?"),
        dict(t="Conditional Debug.", body="R2 hat zwei OSPF-Nachbarn. Setze auf R2 zuerst die Bedingung `debug condition interface GigabitEthernet0/0`, prüfe sie mit `show debug condition` und schalte erst dann `debug ip ospf hello` ein. Lies nach 30 Sekunden `show logging`. Räume auf mit `undebug all` und `no debug condition all`.",
             predict="Von welchen Nachbarn siehst du Hello-Meldungen, und was fragt der Router beim Löschen der Bedingung?",
             check="`show debug condition` listet „Condition 1: interface Gi0/0“. Im Puffer stehen nur Hellos auf Gi0/0. Beim Löschen warnt der Router, dass ohne Bedingung eine Flut von Meldungen folgen kann, und verlangt eine Bestätigung.",
             think="Warum setzt du die Bedingung vor dem Debug und nimmst sie erst nach `undebug all` wieder weg?"),
        dict(t="Werkzeug wählen.", body="Ordne jedem Symptom das Werkzeug zu, mit dem du anfängst, bevor du die Antwort aufklappst: (a) „Kleine Dateien gehen, große Downloads hängen.“ (b) „Seit heute Morgen ist der Standort langsam.“ (c) „Der OSPF-Nachbar kommt nicht hoch.“ (d) „Ein Server ist von einem VLAN aus erreichbar, vom anderen nicht.“ (e) „Die CPU des Routers steht auf 99 %.“")],
    answers=[
        ("1", "Der zweite Ping zeigt **`.`**, der dritte **`U`**. Beim zweiten kennt jeder Router das Netz 192.168.3.0/24. R3 fragt per ARP nach .99, bekommt keine Antwort und verwirft das Paket stumm. Der Absender merkt nur den Timeout. Beim dritten hat schon R1 keine Route und schickt *Destination Unreachable* zurück. IOS begrenzt solche Meldungen auf eine pro 500 ms (`ip icmp rate-limit unreachable`), deshalb bleibt jede zweite aus."),
        ("2", "**`M`**, gesendet von R2 (10.0.12.2). Die Meldung ist ICMP Typ 3 Code 4 (*Fragmentation needed and DF set*) und enthält die MTU des nächsten Hops, hier 1400. Daraus berechnet der Absender die neue Paketgröße (Path MTU Discovery). Unterdrückt ein Gerät die Meldung, senden TCP-Verbindungen weiter zu große Segmente mit DF-Bit, die spurlos verschwinden: Verbindungsaufbau und kleine Pakete gehen, große Übertragungen hängen (*PMTUD Black Hole*)."),
        ("3", "**Vier Zeilen**, eine je Router und eine für das Ziel. IOS sendet je Hop drei UDP-Pakete an hohe Ports ab 33434 und erhöht die TTL von 1 an. Router unterwegs antworten mit *Time Exceeded* (Typ 11). Das Ziel antwortet mit *Port Unreachable* (Typ 3 Code 3), weil auf dem Port nichts lauscht. Diese Antwort unterliegt wieder der Begrenzung auf eine Meldung pro 500 ms, daher geht die mittlere der drei Proben verloren."),
        ("4", "Traceroute endet in **Zeile 3 mit `!A`** (*administratively prohibited*): R3 prüft die ACL, bevor es die TTL auswertet, und verwirft die UDP-Probe. Ein Windows-Client mit `tracert` wäre durchgekommen, weil `permit icmp any any` seine Echo-Pakete erlaubt. Dasselbe Netz liefert also je nach Werkzeug ein anderes Bild. `!H` hieße *Host unreachable* (keine Route), `!N` *Network unreachable*, `*` keine Antwort."),
        ("5", "**Nein.** `logging console informational` lässt nur Stufe 0 bis 6 auf die Konsole, Debug ist Stufe 7. Die Konsole ist langsam (9600 Baud) und wird Zeichen für Zeichen von der CPU bedient: Eine Debug-Flut blockiert den Router, bis er nicht mehr bedienbar ist. In einer SSH-Sitzung brauchst du `terminal monitor`, sonst siehst du gar nichts. Der Puffer ist der sichere Weg."),
        ("6", "Nur für den Ping an **10.255.0.3**. `debug ip packet` zeigt Pakete, die der Router im Prozess verarbeitet: Verkehr an ihn selbst oder von ihm. Durchgeleitete Pakete schaltet CEF, ohne dass der Prozess sie sieht. Wer Transitverkehr sehen will, nimmt NetFlow, einen Mitschnitt (EPC, SPAN) oder ACL-Zähler, nicht `debug ip packet`."),
        ("7", "Nur von dem Nachbarn auf **Gi0/0**. Die Reihenfolge schützt dich: Ist das Debug zuerst aktiv, läuft es für einen Moment ungefiltert. Aus demselben Grund fragt der Router beim Löschen der Bedingung nach, denn ein noch laufendes Debug wäre danach wieder unbegrenzt."),
        ("8", "(a) **Ping mit Größe und DF-Bit**, Verdacht MTU. (b) **Syslog und Schnittstellenzähler**, dann NetFlow: erst feststellen, was sich geändert hat. (c) **`show ip ospf interface` und `show ip ospf neighbor`**, erst danach gezielt `debug ip ospf adj` mit Bedingung. (d) **Traceroute von beiden Quellen** und ACL-Zähler: Wo trennen sich die Wege? (e) **`show processes cpu sorted`**, auf keinen Fall ein Debug: Ein Debug erhöht die Last weiter. Grundregel: erst `show`, dann eingegrenztes `debug`.")],
    nodes=[
        dict(name="R1", type="router", x=200, y=200,
             base=router(1, [("GigabitEthernet0/0", "192.168.1.1") + P24, ("GigabitEthernet0/1", "10.0.12.1") + P30]),
             sol=LOG),
        dict(name="R2", type="router", x=400, y=200, base=R2_BASE, sol=LOG),
        dict(name="R3", type="router", x=600, y=200, base=R3_BASE,
             sol=LOG + """
ip access-list extended TRANSIT
 permit ospf any any
 permit icmp any any
 permit tcp any any
 permit udp any any range 33434 33534
 deny ip any any log
interface GigabitEthernet0/0
 ip access-group TRANSIT in"""),
        dict(name="H1", type="host", x=0, y=200,
             base="no ip routing\ninterface GigabitEthernet0/0\n ip address 192.168.1.10 255.255.255.0\n no shutdown\nip default-gateway 192.168.1.1",
             sol=""),
        dict(name="SRV", type="host", x=800, y=200,
             base="no ip routing\ninterface GigabitEthernet0/0\n ip address 192.168.3.10 255.255.255.0\n no shutdown\nip default-gateway 192.168.3.1",
             sol="")],
    links=[("H1", "Gi0/0", "R1", "Gi0/0"), ("R1", "Gi0/1", "R2", "Gi0/0"), ("R2", "Gi0/1", "R3", "Gi0/0"),
           ("R3", "Gi0/1", "SRV", "Gi0/0")],
    vpcs=False,
    vpcs_note=("Nimm für H1 und SRV vIOS. Du brauchst auf H1 den erweiterten Ping mit DF-Bit und die IOS-Zeichen von Ping "
               "und Traceroute; ein VPCS zeigt sie anders an."),
    staggered=True,
    tickets=["H1 erreicht SRV nicht. Der Ping von H1 zeigt `U.U.U`.",
             "Der Ping von H1 zu SRV geht, aber Traceroute bricht in Zeile 3 mit `!A` ab. Das Monitoring meldet den Standort deshalb als gestört.",
             "Anwender melden: Anmelden am Server geht, große Dateien übertragen hängt. `ping 192.168.3.10 size 1500 df-bit` von H1 zeigt nur Punkte, kein `M`.",
             "Auf R1 läuft `debug ip icmp` laut `show debugging`, aber `show logging` zeigt keine einzige Debug-Zeile."],
    faults=[
        dict(node="R3", old=" network 192.168.3.0 0.0.0.255 area 0", new=None,
             find="`U` heißt: Ein Router hat geantwortet, dass er das Ziel nicht kennt. `traceroute 192.168.3.10` von H1 zeigt schon in Zeile 1 `!H` von 192.168.1.1. `show ip route 192.168.3.0` auf R1 und R2 ist leer, auf R3 ist das Netz nur `connected`. `show ip ospf interface brief` auf R3 listet Gi0/1 nicht.",
             cause="R3 gibt sein Server-Netz nicht in OSPF bekannt. R1 hat keine Route und meldet das dem Absender.",
             fix="Auf R3 unter `router ospf 1`: `network 192.168.3.0 0.0.0.255 area 0`."),
        dict(node="R3", old=" permit udp any any range 33434 33534", new=None,
             find="`!A` heißt *administratively prohibited*, also eine ACL. Die Meldung kommt von 10.0.23.2. `show access-lists TRANSIT` auf R3 zeigt steigende Treffer auf `deny ip any any log`, im Log stehen die verworfenen UDP-Pakete mit Zielport ab 33434.",
             cause="Die ACL erlaubt ICMP und TCP, aber nicht die UDP-Proben von Traceroute. Der Ping bleibt deshalb unauffällig.",
             fix="In `ip access-list extended TRANSIT` vor dem `deny`: `permit udp any any range 33434 33534`."),
        dict(node="R2", old=None, ctx="interface GigabitEthernet0/0", new=" no ip unreachables",
             find="Sweep-Ping mit DF-Bit: bis 1400 Byte `!`, darüber `.` statt `M`. Der Verlust beginnt genau an der MTU-Grenze, also verwirft R2 die Pakete, ohne es zu melden. `show ip interface GigabitEthernet0/0 | include unreachables` auf R2: „ICMP unreachables are never sent“.",
             cause="`no ip unreachables` auf dem Eingangs-Interface unterdrückt auch die Meldung *Fragmentation needed*. Path MTU Discovery kann nicht arbeiten, große Pakete mit DF-Bit verschwinden.",
             fix="`ip unreachables` auf R2 Gi0/0. (Alternativ am Rand `ip tcp adjust-mss`, das hilft aber nur TCP.)"),
        dict(node="R1", old="logging buffered 16384 debugging", new="logging buffered 16384 warnings",
             find="`show logging` auf R1 nennt in der Kopfzeile „Buffer logging: level warnings“. Debug-Meldungen haben Stufe 7 und werden nicht gespeichert.",
             cause="Der Puffer nimmt nur Stufe 0 bis 4 an. Die Konsole ist auf `informational` begrenzt, also landen Debugs nirgends.",
             fix="`logging buffered 16384 debugging` auf R1.")],
    verify=["ping 192.168.3.10                        ! auf H1", "ping 192.168.3.10 size 1500 df-bit       ! auf H1",
            "traceroute 192.168.3.10                  ! auf H1", "show access-lists TRANSIT                ! auf R3",
            "show ip interface Gi0/0 | include unreach", "show logging", "show debugging", "show debug condition"],
    verify_table=[("Ping H1 → SRV", "`!!!!!`"), ("Ping H1 → SRV mit 1500 Byte und DF-Bit", "`M.M.M`, Meldung von 10.0.12.2"),
                  ("Traceroute H1 → SRV", "vier Zeilen, kein `!A`"),
                  ("`show logging` auf R1 bis R3", "„Buffer logging: level debugging“, „Console logging: level informational“"),
                  ("`show debugging` am Ende", "leer")],
    teilc=[("Ein Ping zeigt `.!!!!`. Ist das ein Fehler?",
            "**Meist nicht.** Das erste Paket geht verloren, während ein Gerät auf dem Weg die MAC-Adresse per ARP auflöst. Beim zweiten Versuch steht `!!!!!`. Bleibt der erste Punkt bei jeder Wiederholung, liegt es nicht an ARP."),
           ("Traceroute zeigt in Zeile 4 `* * *`, in Zeile 5 antwortet das Ziel. Was schließt du daraus?",
            "**Hop 4 leitet weiter, antwortet aber nicht selbst.** Er sendet kein *Time Exceeded*, etwa wegen `no ip unreachables`, einer ACL für eigene ICMP-Meldungen oder CoPP. Solange spätere Hops antworten, ist das kein Ausfall. Ein Fehler wäre es erst, wenn ab einer Zeile nur noch Sterne kommen."),
           ("Du willst auf einem produktiven Router sehen, warum eine OSPF-Nachbarschaft auf Gi0/2 flattert. Welche Schritte in welcher Reihenfolge?",
            "**(1)** `show`-Befehle und Syslog zuerst. **(2)** `logging buffered … debugging`, Konsole begrenzen. **(3)** `debug condition interface Gi0/2`, mit `show debug condition` prüfen. **(4)** `debug ip ospf adj`. **(5)** Auswerten mit `show logging`. **(6)** `undebug all`, dann `no debug condition all`. Dazu vorher ein Rückweg: Sitzung mit `terminal monitor` und die Möglichkeit, `u all` blind zu tippen."),
           ("Was ändert `logging trap warnings`?",
            "**Nur, was an den Syslog-Server geht.** Jedes Ziel hat eine eigene Stufe: `logging console`, `logging monitor` (VTY), `logging buffered`, `logging trap` (Server). Die Stufe ist eine Obergrenze: `warnings` (4) schickt 0 bis 4. Merkhilfe für 0 bis 7: Emergency, Alert, Critical, Error, Warning, Notification, Informational, Debugging.")],
    exam=["Ping-Zeichen: `!` Antwort, `.` Timeout, `U` Unreachable, `M` Fragmentierung nötig, `Q` Source Quench, `?` unbekannt.",
          "Traceroute in IOS: UDP ab Port 33434, TTL steigt; unterwegs *Time Exceeded*, am Ziel *Port Unreachable*. `!A` ACL, `!H` Host, `!N` Netz.",
          "Erweiterter Ping: Quelle, Größe, DF-Bit, Sweep, Wiederholungen; damit prüfst du Rückweg und MTU.",
          "Debug: Stufe 7. Ziele einzeln begrenzen (`console`, `monitor`, `buffered`, `trap`). `terminal monitor` für VTY.",
          "Conditional Debug: `debug condition interface …`, `show debug condition`, Bedingung vor dem Debug setzen.",
          "`debug ip packet` zeigt nur prozessgeschaltete Pakete, mit ACL einschränken."],
    caveat=("Welche Debugs eine Bedingung aus `debug condition` beachten, hängt vom Image ab. Zeigt dein IOSv in Schritt 7 "
            "trotz Bedingung Hellos beider Nachbarn, dann ist der Ablauf (Bedingung setzen, prüfen, Debug, aufräumen) trotzdem "
            "das, was die Prüfung abfragt. Die Filterung per ACL aus Schritt 6 funktioniert in jedem Image. Auf IOS XE heißt "
            "das neuere Verfahren `debug platform condition`."),
)

# Live-Test: je Fehler einspielen (inject), zurücknehmen (revert) und eine Probe, die nur im gesunden Zustand passt.
LIVE = [
    dict(inject=["router ospf 1", "no network 192.168.3.0 0.0.0.255 area 0"],
         revert=["router ospf 1", "network 192.168.3.0 0.0.0.255 area 0"],
         probe=("H1", "ping 192.168.3.10", r"Success rate is (80|100) percent"), settle=20),
    dict(inject=["ip access-list extended TRANSIT", "no permit udp any any range 33434 33534"],
         revert=["ip access-list extended TRANSIT", "40 permit udp any any range 33434 33534"],
         probe=("H1", "traceroute 192.168.3.10", r"(?m)^\s*4\s+192\.168\.3\.10"), settle=5),
    dict(inject=["interface GigabitEthernet0/0", "no ip unreachables"], revert=["interface GigabitEthernet0/0", "ip unreachables"],
         probe=("H1", "ping 192.168.3.10 size 1500 df-bit", r"(?m)^[.M]*M[.M]*\s*$"), settle=5),
    dict(inject=["logging buffered 16384 warnings"], revert=["logging buffered 16384 debugging"],
         probe=("R1", "show logging | include Buffer logging", r"level debugging"), settle=2)]
for _f, _l in zip(LAB["faults"], LIVE):
    _f.update(_l)
LAB["settle"] = 60
LAB["checks"] = [("H1", "ping 192.168.3.10", r"Success rate is (80|100) percent"),
                 ("H1", "ping 192.168.3.10 size 1500 df-bit", r"(?m)^[.M]*M[.M]*\s*$"),
                 ("H1", "traceroute 192.168.3.10", r"(?m)^\s*4\s+192\.168\.3\.10"),
                 ("R3", "show access-lists TRANSIT", r"permit udp any any range 33434 33534")]
