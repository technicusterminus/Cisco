BFD = " bfd interval 300 min_rx 300 multiplier 3"

LAB = dict(
    slug="E3-BFD-OSPF", num="E3", title="BFD für schnelle Fehlererkennung mit OSPF", minutes=75, level="mittel",
    summary=("Drei Router mit OSPF, davon zwei über einen Layer-2-Switch verbunden. Fällt ein Port hinter dem Switch aus, "
             "merkt der Nachbar das nur über den OSPF-Dead-Timer. Mit BFD sinkt die Erkennungszeit von 40 Sekunden auf unter "
             "eine Sekunde. Dazu die BFD-Timer-Aushandlung und die typischen Fehler bei der Konfiguration."),
    goals=["Den Ausfall hinter einem Switch ohne BFD messen und die Dead-Timer-Verzögerung erklären.",
           "BFD auf Interface-Ebene und als OSPF-Client konfigurieren.",
           "Mit `show bfd neighbors` und `show bfd neighbors details` Sitzungen, Timer und Clients prüfen.",
           "Erklären, wie sich die Erkennungszeit aus den Timern beider Seiten ergibt."],
    tags=[("1.8", "Bidirectional Forwarding Detection", 7), ("1.10.b", "OSPF: Nachbarschaft und Authentisierung", 10)],
    diagram="""
   R1 Lo1 10.1.1.1/24              R2 Lo1 10.2.2.2/24
   R1 ──Gi0/0── SW ──Gi0/0── R2
    │ Gi0/1                  Gi0/1 │
    └──── Gi0/0  R3  Gi0/1 ────────┘
""",
    nets=[("R1 Gi0/0 – SW – R2 Gi0/0", "10.0.12.0/24 (R1 .1, R2 .2)"),
          ("R1 Gi0/1 – R3 Gi0/0", "10.0.13.0/30 (.1/.2)"),
          ("R2 Gi0/1 – R3 Gi0/1", "10.0.23.0/30 (R2 .1, R3 .2)"),
          ("LANs (Loopback1)", "R1 10.1.1.0/24, R2 10.2.2.0/24")],
    topo_text=("Der direkte Weg R1–SW–R2 ist der kürzeste (Kosten 1 je Link), der Umweg über R3 kostet einen Link mehr. Weil R1 und R2 "
               "über den Switch verbunden sind, bleibt der Link an R1 **up**, wenn du auf R2 `shutdown` am Gi0/0 eingibst. R1 merkt "
               "den Ausfall nur durch ausbleibende Hellos. Genau dafür ist BFD da."),
    steps=[
        dict(t="OSPF aufbauen.", body="Auf R1, R2 und R3: `router ospf 1` mit eigener `router-id` und `network`-Anweisungen für alle Links und LANs in Area 0.",
             check="`show ip ospf neighbor` auf R1 zeigt R2 und R3 in FULL. `show ip route 10.2.2.0` führt über 10.0.12.2 (direkter Weg).",
             think="Welche Kosten hat der Weg über R3, und warum wird er jetzt nicht benutzt?"),
        dict(t="Ausfall ohne BFD messen.", body="Starte auf R1 `ping 10.2.2.2 source Loopback1 repeat 100000`. Gib auf R2 `shutdown` unter Gi0/0 ein.",
             check="Die Pings brechen ab. R1 behält R2 etwa 40 Sekunden in FULL, erst dann schwenkt die Route auf den Weg über R3. Danach `no shutdown` auf R2 Gi0/0.",
             think="Warum erkennt R1 den Ausfall nicht sofort am Interface?"),
        dict(t="BFD-Timer am Interface setzen.", body="Auf R1, R2 und R3 an jedem Interface mit OSPF-Nachbarn: `bfd interval 300 min_rx 300 multiplier 3`.",
             check="`show bfd neighbors` ist noch leer, weil noch kein Client (OSPF) die Sitzung anfordert.",
             think="Was legt `interval` fest, was `min_rx`, was `multiplier`?"),
        dict(t="OSPF als BFD-Client anmelden.", body="Unter `router ospf 1` auf allen Routern `bfd all-interfaces`.",
             check="`show bfd neighbors` listet pro Link eine Sitzung im Zustand Up, Client OSPF. `show ip ospf interface Gi0/0` nennt BFD.",
             think="Was ist der Unterschied zwischen `bfd all-interfaces` im Prozess und `ip ospf bfd` am Interface?"),
        dict(t="Ausfall mit BFD wiederholen.", body="Starte erneut den Dauer-Ping und gib `shutdown` auf R2 Gi0/0 ein.",
             check="Die Route schwenkt in unter einer Sekunde auf R3 um, höchstens wenige Pings gehen verloren. `show ip ospf neighbor` zeigt R2 nicht mehr.",
             think="Wie lang ist die Erkennungszeit bei 300 ms und Multiplier 3, und wovon hängt sie ab?"),
        dict(t="Weitere Clients einordnen.", body="Dieses Lab nutzt nur OSPF.",
             think="Wie bindest du BFD an BGP (`neighbor … fall-over bfd`) und an eine statische Route (`ip route static bfd …`)?")],
    answers=[
        ("1", "Die Kosten sind 1 (R1→R3) + 1 (R3→R2) + 1 (Loopback) = 3 gegen 1 + 1 = 2 über den Switch. Der Weg über R3 hat die höheren Kosten und wird nur als Backup bereitgehalten."),
        ("2", "Der Link zum Switch bleibt aktiv, nur die Gegenseite ist weg. R1 sieht Carrier und erkennt den Fehler erst am **Dead-Timer** (Standard bei Broadcast: 40 s, vier Hello-Intervalle à 10 s)."),
        ("3", "`interval` ist das Sendeintervall der eigenen Pakete, `min_rx` das kürzeste Empfangsintervall, das du akzeptierst, `multiplier` die Zahl verlorener Pakete, bis die Sitzung als down gilt."),
        ("4", "`bfd all-interfaces` meldet alle OSPF-Interfaces des Prozesses an, `ip ospf bfd` wirkt nur am Interface. Am Interface lässt sich BFD mit `ip ospf bfd disable` auch gezielt abschalten, selbst wenn der Prozess `all-interfaces` hat. Das ist eine klassische Fehlerquelle."),
        ("5", "Die Erkennungszeit ist **Multiplier der Gegenseite × größeres von (eigenes min_rx, Tx-Intervall der Gegenseite)**. Hier 3 × 300 ms = 900 ms. Ist ein Multiplier oder ein Intervall größer, bestimmt der größere Wert das Ergebnis."),
        ("6", "BGP: `neighbor <IP> fall-over bfd` (bei Single-Hop-eBGP). Statische Route: `ip route static bfd <Interface> <Next-Hop>` plus die statische Route, die dann nur bei lebender BFD-Sitzung installiert bleibt.")],
    nodes=[
        dict(name="R1", type="router", x=200, y=100,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.12.1 255.255.255.0
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.13.1 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.1.1.1 255.255.255.0""",
             sol="""
router ospf 1
 router-id 1.1.1.1
 network 10.0.12.0 0.0.0.255 area 0
 network 10.0.13.0 0.0.0.3 area 0
 network 10.1.1.0 0.0.0.255 area 0
 bfd all-interfaces
interface GigabitEthernet0/0
 bfd interval 300 min_rx 300 multiplier 3
interface GigabitEthernet0/1
 bfd interval 300 min_rx 300 multiplier 3"""),
        dict(name="R2", type="router", x=500, y=100,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.12.2 255.255.255.0
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.23.1 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.2.2.2 255.255.255.0""",
             sol="""
router ospf 1
 router-id 2.2.2.2
 network 10.0.12.0 0.0.0.255 area 0
 network 10.0.23.0 0.0.0.3 area 0
 network 10.2.2.0 0.0.0.255 area 0
 bfd all-interfaces
interface GigabitEthernet0/0
 bfd interval 300 min_rx 300 multiplier 3
interface GigabitEthernet0/1
 bfd interval 300 min_rx 300 multiplier 3"""),
        dict(name="R3", type="router", x=350, y=300,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.13.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.23.2 255.255.255.252
 no shutdown""",
             sol="""
router ospf 1
 router-id 3.3.3.3
 network 10.0.13.0 0.0.0.3 area 0
 network 10.0.23.0 0.0.0.3 area 0
 bfd all-interfaces
interface GigabitEthernet0/0
 bfd interval 300 min_rx 300 multiplier 3
interface GigabitEthernet0/1
 bfd interval 300 min_rx 300 multiplier 3"""),
        dict(name="SW", type="switch", x=350, y=100)],
    links=[("R1", "Gi0/0", "SW", "port0"), ("R2", "Gi0/0", "SW", "port1"),
           ("R1", "Gi0/1", "R3", "Gi0/0"), ("R2", "Gi0/1", "R3", "Gi0/1")],
    staggered=True,
    tickets=["Beim Test (R2 Gi0/0 `shutdown`) braucht R1 etwa 40 Sekunden, bis die Route umschwenkt; `show bfd neighbors` auf R1 zeigt keine Sitzung zu R2 im Zustand Up.",
             "Die BFD-Sitzung zwischen R1 und R3 fehlt; auf R1 steht für Gi0/1 keine Sitzung in `show bfd neighbors`.",
             "Der Umschwenk bei Ausfall von R2 Gi0/0 dauert rund 9 Sekunden statt unter einer Sekunde, obwohl die Sitzung Up ist.",
             "Trotz funktionierendem Direktweg läuft der Verkehr von R1 zu 10.2.2.2 über R3.",
             "Zwischen R3 und R2 gibt es keine BFD-Sitzung, auch nachdem R2 BFD im OSPF angemeldet hat."],
    faults=[
        dict(node="R2", old=" bfd all-interfaces", new=None,
             find="`show ip ospf interface Gi0/0` auf R2 nennt kein BFD. `show running-config | section router ospf` auf R2 enthält kein `bfd all-interfaces`. Auf R1 bleibt die Sitzung zu R2 Down.",
             cause="R2 hat OSPF nicht als BFD-Client angemeldet. R1 sendet BFD-Pakete, R2 hat dafür keine Sitzung und antwortet nicht. Der OSPF-Dead-Timer bleibt die einzige Erkennung.",
             fix="`bfd all-interfaces` unter `router ospf 1` auf R2."),
        dict(node="R1", old=BFD, new=None, nth=1,
             find="`show running-config interface Gi0/1` auf R1 enthält keine `bfd interval`-Zeile; Gi0/0 hat sie. `show bfd neighbors` zeigt keine Sitzung zu 10.0.13.2.",
             cause="Ohne `bfd interval …` am Interface gibt es keine Timer für die Sitzung. OSPF meldet den Nachbarn zwar an, BFD startet aber nicht.",
             fix="`bfd interval 300 min_rx 300 multiplier 3` unter Gi0/1 auf R1."),
        dict(node="R2", old=BFD, new=" bfd interval 300 min_rx 300 multiplier 30", nth=0,
             find="`show bfd neighbors details` auf R1 zeigt beim Nachbarn 10.0.12.2 den Received Multiplier 30. Die Erkennung dauert 30 × 300 ms = 9 s.",
             cause="R2 sendet Multiplier 30. R1 darf den Nachbarn erst nach 30 ausgebliebenen Paketen für tot erklären. Der größere Wert der beiden Seiten bestimmt die Erkennungszeit.",
             fix="`bfd interval 300 min_rx 300 multiplier 3` unter Gi0/0 auf R2."),
        dict(node="R1", old=None, new=" ip ospf cost 10", ctx="interface GigabitEthernet0/0", nth=1,
             find="`show ip ospf interface brief` auf R1 zeigt Kosten 10 für Gi0/0. `show ip route 10.2.2.0` zeigt den Next-Hop 10.0.13.2 (R3), nicht 10.0.12.2.",
             cause="Der manuell gesetzte OSPF-Cost 10 macht den Direktweg teurer (11) als den Umweg über R3 (3). Der Backup-Pfad ist der aktive Pfad.",
             fix="`ip ospf cost 10` unter Gi0/0 auf R1 entfernen."),
        dict(node="R3", old=None, new=" ip ospf bfd disable", ctx="interface GigabitEthernet0/1", nth=1,
             find="`show running-config interface Gi0/1` auf R3 enthält `ip ospf bfd disable`. Das überschreibt `bfd all-interfaces` des Prozesses.",
             cause="Die Interface-Einstellung gewinnt gegen die Prozess-Einstellung: OSPF meldet den Nachbarn an Gi0/1 nicht bei BFD an.",
             fix="`ip ospf bfd disable` unter Gi0/1 auf R3 entfernen.")],
    verify=["show ip ospf neighbor", "show ip ospf interface brief", "show bfd neighbors", "show bfd neighbors details",
            "show ip route 10.2.2.0", "ping 10.2.2.2 source Loopback1 repeat 100000   ! beim Ausfalltest"],
    verify_table=[("`show bfd neighbors` auf R1", "zwei Sitzungen (10.0.12.2 und 10.0.13.2) im Zustand Up, Client OSPF"),
                  ("`show bfd neighbors details` auf R1", "eigener und empfangener Multiplier 3, Intervall 300 ms"),
                  ("`show ip route 10.2.2.0` auf R1", "Next-Hop 10.0.12.2; nach dem Ausfall 10.0.13.2")],
    caveat=("BFD ist auf virtuellen Routern nicht mit Hardware vergleichbar: Die Pakete laufen über die CPU des Hosts. Bleibe bei **300 ms** "
            "oder mehr, sonst flattern die Sitzungen in der Simulation. Ob dein IOSv-Image BFD mit allen Optionen beherrscht, "
            "hängt von der Version ab; die Syntax folgt der IOS-15-Dokumentation und ist hier nicht in einer laufenden Simulation getestet."),
    teilc=[("`bfd all-interfaces` steht im OSPF, trotzdem gibt es keine BFD-Sitzung. Was prüfst du?",
            "**Interface-Timer, Gegenseite und Interface-Override.** 1) Hat das Interface `bfd interval …`? 2) Meldet auch die Gegenseite BFD an (`show ip ospf interface`)? 3) Steht am Interface `ip ospf bfd disable`? 4) Ist der OSPF-Nachbar überhaupt FULL? BFD wird erst nach einer aufgebauten Nachbarschaft angefordert."),
           ("Was ist der Unterschied zwischen BFD im Asynchronous Mode und im Echo Mode?",
            "**Asynchron schicken sich beide Seiten periodisch Control-Pakete, im Echo-Modus schickt eine Seite Pakete, die der Nachbar nur zurückspiegelt.** Der Echo-Weg prüft den Forwarding-Pfad des Nachbarn, ohne dessen Control Plane zu belasten. Die Control-Pakete laufen dann mit niedrigerer Rate weiter."),
           ("Warum ist ein sehr aggressives BFD-Intervall (50 ms) nicht immer eine gute Idee?",
            "**Kurze Timer erhöhen die CPU-Last und machen das Netz anfällig für Flapping.** Ein kurzer Aussetzer oder Last-Spitze lässt die Sitzung fallen, der Routing-Prozess berechnet neu, und das erzeugt oft mehr Instabilität, als es schützt. Auf Hardware mit BFD im Line-Card-Offload geht das, in virtuellen Umgebungen nicht.")],
    exam=["BFD erkennt Ausfälle unabhängig vom Routing-Protokoll in Millisekunden; die Routing-Protokolle melden sich als Clients an.",
          "Konfiguration: Timer am Interface (`bfd interval … min_rx … multiplier …`), Client im Protokoll (`bfd all-interfaces`, `neighbor … fall-over bfd`).",
          "Erkennungszeit = Multiplier der Gegenseite × max(eigenes min_rx, Tx der Gegenseite).",
          "`ip ospf bfd disable` am Interface schlägt `bfd all-interfaces` im Prozess.",
          "Fehlersuche: `show bfd neighbors [details]`, `show ip ospf interface`, `debug bfd packet` (kurz)."],
)
