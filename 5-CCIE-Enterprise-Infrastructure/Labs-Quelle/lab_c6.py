def eigrp(rid, nets, extra=""):
    lines = "\n".join(f"  network {n}" for n in nets)
    return f"""
router eigrp CCIE
 address-family ipv4 unicast autonomous-system 100
  af-interface default
   authentication mode hmac-sha-256 EIGRP-Lab
  exit-af-interface{extra}
{lines}
  eigrp router-id {rid}
 exit-address-family"""


LAB = dict(
    slug="C6-EIGRP-Named-Mode", num="C6", title="EIGRP Named Mode: SHA-256, Unequal-Cost Load Balancing und Stub mit Leak-Map",
    minutes=100, level="mittel bis schwer",
    summary=("Vier Router im EIGRP Named Mode mit HMAC-SHA-256. Der Weg von der Zentrale zur Filiale führt über zwei Verteiler "
             "mit unterschiedlicher Verzögerung: Mit `variance` nutzt R1 beide, sofern der zweite die Feasibility Condition erfüllt. "
             "Die Filiale R4 ist ein Stub und damit nie Transit, gibt per Leak-Map aber die Default-Route weiter, damit ein Verteiler "
             "bei einem Linkausfall nicht abgeschnitten ist."),
    goals=["EIGRP im Named Mode mit `af-interface` und `topology base` konfigurieren und HMAC-SHA-256 einsetzen.",
           "Successor und Feasible Successor aus den Verzögerungen ableiten und Unequal-Cost Load Balancing mit `variance` nachweisen.",
           "Einen Stub mit Leak-Map bauen und erklären, warum ein Stub keine Queries bekommt.",
           "Abgelehnte Nachbarschaften an K-Werten und Authentisierung erkennen."],
    tags=[("1.2.i", "Authentisierung von Routing-Protokollen", 5), ("1.3.b", "EIGRP: Metrik und Wide Metrics", 4),
          ("1.3.d", "EIGRP: Load Balancing", 3), ("1.3.e", "EIGRP: Named Mode", 4),
          ("1.3.f", "EIGRP: Optimierung, Stub, LFA und Leak-Maps", 4)],
    diagram="""
                 R1   Lo1 10.1.1.1/24, Lo100 192.0.2.1 = Internet
          Gi0/0 /  \\ Gi0/1  (delay 10 = 100 µs)
               /    \\
        Gi0/0 /      \\ Gi0/0
           R2          R3
        Gi0/1 \\      / Gi0/1
               \\    /
        Gi0/0   \\  /  Gi0/1
                 R4   Stub, Lo1 10.4.1.1/24, Lo2 10.4.2.1/24
""",
    nets=[("R1 Gi0/0 – R2 Gi0/0", "10.0.12.0/30 (.1/.2)"),
          ("R1 Gi0/1 – R3 Gi0/0", "10.0.13.0/30 (.1/.2)"),
          ("R2 Gi0/1 – R4 Gi0/0", "10.0.24.0/30 (.1/.2)"),
          ("R3 Gi0/1 – R4 Gi0/1", "10.0.34.0/30 (.1/.2)"),
          ("LANs (Loopbacks)", "R1 10.1.1.0/24, R4 10.4.1.0/24 und 10.4.2.0/24"),
          ("„Internet“", "192.0.2.1/32 auf R1 Loopback100, nicht in EIGRP")],
    topo_text=("Alle Links haben dieselbe Bandbreite (1 Gbit/s), die Pfadwahl hängt deshalb nur an der Verzögerung. R1 bekommt an Gi0/1 "
               "eine höhere Verzögerung, R4 an seinen Loopbacks eine niedrigere als üblich, damit die Rechnung überschaubar bleibt. "
               "R1 ist der Übergang ins Internet und verteilt eine Default-Route."),
    steps=[
        dict(t="Named Mode mit Authentisierung.",
             body="Auf allen vier Routern `router eigrp CCIE` → `address-family ipv4 unicast autonomous-system 100` mit `eigrp router-id` "
                  "(R1 10.1.1.1, R2 10.0.0.2, R3 10.0.0.3, R4 10.0.0.4) und `network`-Anweisungen für alle Links. Unter "
                  "`af-interface default` `authentication mode hmac-sha-256 EIGRP-Lab`. R1 kündigt zusätzlich 10.1.1.0/24 an.",
             check="`show eigrp address-family ipv4 neighbors`: R1 und R4 sehen je zwei Nachbarn, R2 und R3 ebenfalls zwei.",
             think="Warum geht HMAC-SHA-256 nur im Named Mode?"),
        dict(t="Netze von R4.",
             body="Auf R4 `network 10.4.0.0 0.0.3.255` und an Loopback1 und Loopback2 `delay 10` (100 µs).",
             check="R1 kennt 10.4.1.0/24 und 10.4.2.0/24.",
             think="Welche Netze erfasst `network 10.4.0.0 0.0.3.255`?"),
        dict(t="Ungleiche Wege.", body="Auf R1 an Gi0/1 (Richtung R3) `delay 10`.",
             check="`show ip eigrp topology 10.4.1.0/24` auf R1: Successor über R2 (10.0.12.2), Feasible Successor über R3 (10.0.13.2). "
                   "In der Routing-Tabelle steht nur der Weg über R2.",
             think="Warum ist der Weg über R3 ein Feasible Successor? Rechne mit den Verzögerungen."),
        dict(t="Unequal-Cost Load Balancing.", body="Auf R1 unter `topology base` `variance 2`.",
             check="`show ip route 10.4.1.0` zeigt zwei Wege mit unterschiedlichem *traffic share count*.",
             think="Warum reicht `variance 2`, und was gilt für einen Weg, der die Feasibility Condition nicht erfüllt?"),
        dict(t="Default-Route ins Internet.",
             body="Auf R1 `ip route 0.0.0.0 0.0.0.0 Null0` und unter `topology base` `redistribute static metric 1000000 10 255 1 1500`.",
             check="R2, R3 und R4 haben `D*EX 0.0.0.0/0`. `ping 192.0.2.1 source Loopback1` von R4 klappt.",
             think="Warum ist 192.0.2.1 erreichbar, obwohl es nicht in EIGRP steht?"),
        dict(t="R4 als Stub.",
             body="Auf R4 `eigrp stub connected`. Teste dann: `shutdown` auf R1 Gi0/0, danach `show ip route 0.0.0.0` auf R2. "
                  "Anschließend `no shutdown`.",
             check="`show ip protocols` auf R4 meldet den Stub. Während des Tests hat R2 keine Default-Route mehr, obwohl R4 über R3 "
                   "weiter Verbindung hat.",
             think="Welchen Vorteil bringt ein Stub bei Queries?"),
        dict(t="Leak-Map.",
             body="Auf R4 `ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0`, `route-map LEAK-DEFAULT permit 10` mit "
                  "`match ip address prefix-list DEFAULT` und `eigrp stub connected leak-map LEAK-DEFAULT`. Wiederhole den Test.",
             check="Bei `shutdown` auf R1 Gi0/0 hat R2 die Default-Route über R4 (10.0.24.2) und erreicht 192.0.2.1.",
             think="Warum leakt R4 nur die Default-Route und nicht alles?")],
    answers=[
        ("1", "**Weil der Classic Mode nur MD5 über Key-Chains kennt.** HMAC-SHA-256 gibt es nur in der Named-Konfiguration, das "
              "Passwort steht direkt unter `af-interface`. Wie bei MD5 müssen beide Seiten denselben Schlüssel haben, Groß- und "
              "Kleinschreibung zählt."),
        ("2", "**10.4.0.0 bis 10.4.3.255.** Die Wildcard 0.0.3.255 lässt die letzten zwei Bits des dritten Oktetts und das ganze vierte "
              "Oktett offen. Beide Loopbacks liegen darin, dazu Platz für zwei weitere /24."),
        ("3", "**Weil die Reported Distance von R3 kleiner ist als die Feasible Distance über R2.** Bei gleicher Bandbreite entscheidet "
              "die Verzögerung: R3 meldet für 10.4.1.0/24 10 µs (R3–R4) + 100 µs (Loopback) = 110 µs. Die Feasible Distance über R2 "
              "enthält 10 + 10 + 100 = 120 µs. 110 < 120, die Feasibility Condition ist erfüllt."),
        ("4", "**Die Metrik über R3 liegt unter dem Doppelten der besten Metrik.** Über R2 summieren sich 120 µs, über R3 "
              "100 + 10 + 100 = 210 µs; mit dem gleichen Bandbreitenanteil ergibt das ein Verhältnis von etwa 1,7. Ein Weg ohne "
              "Feasibility Condition kommt nie in die Lastverteilung, egal wie groß die Varianz ist, sonst drohten Schleifen."),
        ("5", "**Weil R1 eine Default-Route verteilt.** Die anderen Router schicken alles, was sie nicht kennen, zu R1, und dort ist "
              "192.0.2.1 direkt angeschlossen."),
        ("6", "**Ein Stub wird nicht befragt.** Fällt eine Route aus, schicken R2 und R3 keine Query an R4. Die Suche bleibt klein, "
              "Stuck in Active wird unwahrscheinlicher. Gleichzeitig gibt R4 keine gelernten Routen weiter und wird so nie zum Transit."),
        ("7", "**Damit R4 kein Transit für das ganze Netz wird.** Die Default-Route reicht R2 im Fehlerfall, um weiter ins Internet "
              "und zu R1 zu kommen. Mit allen Routen würde R4 bei jedem Ausfall zum Umweg für beliebigen Verkehr.")],
    nodes=[
        dict(name="R1", type="router", x=350, y=50,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.12.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.13.1 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.1.1.1 255.255.255.0
interface Loopback100
 ip address 192.0.2.1 255.255.255.255""",
             sol="""
ip route 0.0.0.0 0.0.0.0 Null0
interface GigabitEthernet0/1
 delay 10""" + eigrp("10.1.1.1", ["10.0.12.0 0.0.0.3", "10.0.13.0 0.0.0.3", "10.1.1.0 0.0.0.255"], """
  topology base
   variance 2
   redistribute static metric 1000000 10 255 1 1500
  exit-af-topology""")),
        dict(name="R2", type="router", x=150, y=250,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.12.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.24.1 255.255.255.252
 no shutdown""",
             sol=eigrp("10.0.0.2", ["10.0.12.0 0.0.0.3", "10.0.24.0 0.0.0.3"])),
        dict(name="R3", type="router", x=550, y=250,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.13.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.34.1 255.255.255.252
 no shutdown""",
             sol=eigrp("10.0.0.3", ["10.0.13.0 0.0.0.3", "10.0.34.0 0.0.0.3"])),
        dict(name="R4", type="router", x=350, y=450,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.24.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.34.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.4.1.1 255.255.255.0
interface Loopback2
 ip address 10.4.2.1 255.255.255.0""",
             sol="""
ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0
route-map LEAK-DEFAULT permit 10
 match ip address prefix-list DEFAULT
interface Loopback1
 delay 10
interface Loopback2
 delay 10""" + eigrp("10.0.0.4", ["10.0.24.0 0.0.0.3", "10.0.34.0 0.0.0.3", "10.4.0.0 0.0.3.255"]).replace(
                 "  eigrp router-id 10.0.0.4", "  eigrp router-id 10.0.0.4\n  eigrp stub connected leak-map LEAK-DEFAULT"))],
    links=[("R1", "Gi0/0", "R2", "Gi0/0"), ("R1", "Gi0/1", "R3", "Gi0/0"), ("R2", "Gi0/1", "R4", "Gi0/0"),
           ("R3", "Gi0/1", "R4", "Gi0/1")],
    staggered=True,
    tickets=["R2 hat keine EIGRP-Nachbarn. Im Log steht bei jedem Versuch `K-value mismatch`.",
             "R3 hat keine EIGRP-Nachbarn. Die Links sind up, Pings zu R1 und R4 klappen.",
             "Das Netz 10.4.2.0/24 fehlt auf allen anderen Routern, 10.4.1.0/24 ist da.",
             "R1 schickt Verkehr zu 10.4.1.0/24 nur über R2, obwohl der Weg über R3 als Feasible Successor bereitsteht.",
             "Ausfalltest: Nach `shutdown` auf R1 Gi0/0 verliert R2 seine Default-Route und erreicht 192.0.2.1 nicht mehr, obwohl R4 "
             "über R3 weiter angebunden ist."],
    faults=[
        dict(node="R2", old=None, new="  metric weights 0 1 1 1 0 0 0", ctx=" address-family ipv4 unicast autonomous-system 100",
             find="Im Log von R2 und seinen Nachbarn: `K-value mismatch`. `show eigrp protocols` auf R2 nennt K2 = 1, die Nachbarn haben "
                  "K2 = 0. In der Konfiguration von R2 steht `metric weights 0 1 1 1 0 0 0`.",
             cause="Unterschiedliche K-Werte. EIGRP-Nachbarn müssen dieselben K-Werte haben, sonst lehnen sie die Nachbarschaft ab.",
             fix="`no metric weights` (oder `metric weights 0 1 0 1 0 0 0`) unter der Address-Family auf R2."),
        dict(node="R3", old="   authentication mode hmac-sha-256 EIGRP-Lab", new="   authentication mode hmac-sha-256 EIGRP-lab",
             find="`show eigrp address-family ipv4 neighbors` auf R3 ist leer. `debug eigrp packets` auf R1 zeigt Pakete von 10.0.13.2, "
                  "die an der Authentisierung scheitern. Der Schlüssel auf R3 lautet `EIGRP-lab` statt `EIGRP-Lab`.",
             cause="Falsches Passwort für HMAC-SHA-256. Groß- und Kleinschreibung zählt, der Hash passt nicht.",
             fix="`authentication mode hmac-sha-256 EIGRP-Lab` unter `af-interface default` auf R3."),
        dict(node="R4", old="  network 10.4.0.0 0.0.3.255", new="  network 10.4.0.0 0.0.1.255",
             find="`show eigrp address-family ipv4 interfaces` auf R4 listet Loopback1, aber nicht Loopback2. Die Wildcard 0.0.1.255 "
                  "deckt nur 10.4.0.0 bis 10.4.1.255 ab.",
             cause="Zu enge Wildcard im `network`-Befehl. 10.4.2.1 liegt außerhalb, Loopback2 nimmt nicht an EIGRP teil.",
             fix="`no network 10.4.0.0 0.0.1.255` und `network 10.4.0.0 0.0.3.255` auf R4."),
        dict(node="R1", old="   variance 2", new=None,
             find="`show ip eigrp topology 10.4.1.0/24` auf R1 zeigt Successor und Feasible Successor, `show ip route 10.4.1.0` nur einen "
                  "Weg. Unter `topology base` fehlt `variance 2`.",
             cause="Ohne Varianz nutzt EIGRP nur Wege mit der besten Metrik. Der Feasible Successor bleibt Reserve.",
             fix="`variance 2` unter `topology base` auf R1."),
        dict(node="R4", old="  eigrp stub connected leak-map LEAK-DEFAULT", new="  eigrp stub connected",
             find="Während des Tests: `show ip route 0.0.0.0` auf R2 ist leer. `show ip protocols` auf R4 nennt den Stub ohne Leak-Map. "
                  "R4 kennt die Default-Route von R3, gibt sie als Stub aber nicht weiter.",
             cause="Ein Stub gibt nur seine eigenen Netze weiter. Ohne Leak-Map ist R2 nach dem Ausfall seines Links zu R1 auf die "
                   "Netze von R4 beschränkt.",
             fix="`eigrp stub connected leak-map LEAK-DEFAULT` auf R4.")],
    verify=["show eigrp address-family ipv4 neighbors", "show eigrp address-family ipv4 interfaces detail", "show eigrp protocols",
            "show ip eigrp topology 10.4.1.0/24", "show ip route 10.4.1.0", "show ip route 0.0.0.0", "show ip protocols"],
    verify_table=[("`show eigrp address-family ipv4 neighbors` auf R4", "R2 und R3"),
                  ("`show ip eigrp topology 10.4.1.0/24` auf R1", "Successor über 10.0.12.2, Feasible Successor über 10.0.13.2"),
                  ("`show ip route 10.4.1.0` auf R1", "zwei Wege mit unterschiedlichem traffic share count"),
                  ("`show ip route 0.0.0.0` auf R2 bei `shutdown` von R1 Gi0/0", "D*EX über 10.0.24.2, von R4 geleakt")],
    teilc=[("Was zeigt `show ip eigrp topology all-links` zusätzlich zu `show ip eigrp topology`?",
            "**Auch die Wege, die die Feasibility Condition nicht erfüllen.** Die normale Ausgabe zeigt nur Successors und Feasible "
            "Successors. So siehst du, warum ein Weg nicht als Backup taugt."),
           ("Ein Router steht minutenlang für eine Route im Zustand Active. Was passiert, und wie beugst du vor?",
            "**Er wartet auf Antworten auf seine Queries.** Bleibt eine Antwort aus, fragt er nach der Hälfte der Active-Zeit (Standard "
            "3 Minuten) per SIA-Query nach und baut die Nachbarschaft erst ab, wenn auch darauf nichts kommt. Vorbeugen: den Query-Bereich "
            "mit Summaries und Stubs klein halten."),
           ("Warum zeigt `show ip route` eine andere Metrik als `show eigrp address-family ipv4 topology`?",
            "**Wide Metrics sind 64 Bit groß, die Routing-Tabelle speichert nur 32 Bit.** IOS teilt die Metrik vor dem Eintrag durch den "
            "RIB-Scale (`metric rib-scale`, Standard 128)."),
           ("Was passiert mit dem Verkehr, wenn der Successor ausfällt und ein Feasible Successor existiert?",
            "**Der Feasible Successor übernimmt sofort, ohne Query.** Er ist nachweislich schleifenfrei, deshalb muss der Router niemanden "
            "fragen. Gibt es keinen, geht die Route in den Zustand Active, und die Queries beginnen.")],
    exam=["Named Mode: `router eigrp <Name>` → `address-family ipv4 unicast autonomous-system <AS>`; Interface-Einstellungen unter "
          "`af-interface`, Pfadwahl und Redistribution unter `topology base`.",
          "Feasibility Condition: RD < FD. Nur Feasible Successors kommen für `variance` in Frage.",
          "Stub: `eigrp stub [connected|summary|static|redistributed|receive-only] [leak-map]`; Stubs werden nicht befragt.",
          "Nachbarschaft scheitert bei unterschiedlichen K-Werten, AS-Nummern oder Schlüsseln, bei fremdem Subnetz und bei `passive-interface`."],
)
