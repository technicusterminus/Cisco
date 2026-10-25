LAB = dict(
    slug="C3-OSPF-Virtual-Link-NSSA", num="C3", title="OSPF: Virtual Link mit Authentisierung, NSSA, Typ-3-Filter und Netzwerktypen",
    minutes=110, level="schwer",
    summary=("Fünf Router in vier Areas: Area 2 hängt nicht an Area 0 und braucht einen Virtual Link durch Area 1, der wegen der "
             "MD5-Authentisierung im Backbone eine eigene Falle hat. Dazu eine NSSA mit ASBR, die ihre Default-Route erst bekommt, "
             "wenn der ABR sie erzeugt, ein Typ-3-Filter, der in die richtige Richtung zeigen muss, und ein Netzwerktyp-Mismatch, "
             "bei dem die Nachbarschaft FULL ist und trotzdem keine Route ankommt."),
    goals=["Einen Virtual Link durch eine Transit-Area bauen und erklären, warum er die Authentisierung von Area 0 übernimmt.",
           "NSSA mit Typ-7-LSAs, Übersetzung am ABR und Default-Route konfigurieren und in der Datenbank nachweisen.",
           "Typ-3-LSAs mit `area … filter-list` gezielt filtern und `in` von `out` unterscheiden.",
           "Einen Netzwerktyp-Mismatch an FULL-Nachbarn ohne Routen erkennen."],
    tags=[("1.2.i", "Authentisierung von Routing-Protokollen", 5), ("1.4.b", "OSPF: Netzwerktypen, LSA-Typen und Area-Typen", 10),
          ("1.4.c", "OSPF: Pfadwahl und Summarization", 5), ("1.4.d", "OSPF: Betrieb, Router-ID, DR/BDR und Absicherung", 7)],
    diagram="""
   Area 2           Area 1                 Area 0 (MD5)                Area 3 (NSSA)
   R4 Gi0/0 --- Gi0/1 R3 Gi0/0 --- Gi0/1 R1 Gi0/0 --- Gi0/0 R2 Gi0/1 --- Gi0/0 R5
   Lo1 10.4.4.1/24    ABR 1/2            Lo1  10.1.1.1/24     ABR 0/3            Lo1 10.5.5.1/24
   Lo2 10.4.5.1/24                       Lo99 10.1.99.1/24                       ASBR: 172.16.5.0/24
                      <==== Virtual Link durch Area 1 ====>   Lo100 192.0.2.1 = Internet
""",
    nets=[("R1 Gi0/0 – R2 Gi0/0 (Area 0)", "10.0.12.0/30 (.1/.2)"),
          ("R1 Gi0/1 – R3 Gi0/0 (Area 1)", "10.0.13.0/30 (.1/.2)"),
          ("R3 Gi0/1 – R4 Gi0/0 (Area 2)", "10.0.34.0/30 (.1/.2)"),
          ("R2 Gi0/1 – R5 Gi0/0 (Area 3)", "10.0.25.0/30 (.1/.2)"),
          ("Router-IDs", "R1 1.1.1.1, R2 2.2.2.2, R3 3.3.3.3, R4 4.4.4.4, R5 5.5.5.5"),
          ("Netze (Loopbacks)", "R1 10.1.1.0/24 und Testnetz 10.1.99.0/24, R4 10.4.4.0/24 und 10.4.5.0/24, R5 10.5.5.0/24"),
          ("„Internet“", "192.0.2.1/32 auf R1 Loopback100, nicht in OSPF")],
    topo_text=("Area 0 besteht nur aus R1, R2 und dem Link dazwischen, mit MD5-Authentisierung. R3 verbindet Area 1 und Area 2, "
               "hängt aber nicht am Backbone. R5 speist als ASBR in der NSSA ein externes Netz ein. R1 ist der Übergang ins "
               "Internet und verteilt eine Default-Route. Das Testnetz 10.1.99.0/24 soll nur in Area 0 bekannt sein, mindestens "
               "aber nicht in Area 3. OSPF konfigurierst du am Interface mit `ip ospf 1 area <n>`."),
    steps=[
        dict(t="Area 0 mit MD5.",
             body="R1 und R2: `router ospf 1` mit `router-id`, `area 0 authentication message-digest`, am Link 10.0.12.0/30 "
                  "`ip ospf message-digest-key 1 md5 CCIE` und `ip ospf 1 area 0`. Auf R1 kommen Loopback1 und Loopback99 in Area 0, "
                  "jeweils mit `ip ospf network point-to-point`.",
             check="`show ip ospf neighbor` auf R1 zeigt R2 in FULL. `show ip ospf interface Gi0/0` nennt Message-Digest-Authentisierung mit Key 1.",
             think="Warum bekommen die Loopbacks `ip ospf network point-to-point`?"),
        dict(t="Area 1 und Area 2.",
             body="R1 Gi0/1 und R3 Gi0/0 in Area 1, R3 Gi0/1 und R4 komplett in Area 2 (Loopbacks wieder mit "
                  "`ip ospf network point-to-point`). Router-IDs 3.3.3.3 und 4.4.4.4.",
             check="R3 ist mit R1 und R4 FULL. R1 kennt die Netze von R4 aber **nicht**, und R4 kennt nur Area 2.",
             think="Warum gibt R3 die Netze aus Area 2 nicht an Area 1 weiter, obwohl es in beiden Areas sitzt?"),
        dict(t="Virtual Link.",
             body="R1: `area 1 virtual-link 3.3.3.3 message-digest-key 1 md5 CCIE`. R3: `area 1 virtual-link 1.1.1.1 "
                  "message-digest-key 1 md5 CCIE` und `area 0 authentication message-digest`.",
             check="`show ip ospf virtual-links` auf R3: Nachbarschaft zu 1.1.1.1 FULL. R1 kennt 10.4.4.0/24 und 10.4.5.0/24 als O IA.",
             think="Warum braucht R3 `area 0 authentication message-digest`, obwohl es kein Interface in Area 0 hat?"),
        dict(t="Zusammenfassen.", body="Auf R3 `area 2 range 10.4.4.0 255.255.254.0`.",
             check="R1 sieht nur noch 10.4.4.0/23. Auf R3 steht eine Discard-Route `10.4.4.0/23 is a summary, … Null0`.",
             think="Wofür ist die Discard-Route auf R3 gut?"),
        dict(t="NSSA mit ASBR.",
             body="R2 Gi0/1 und R5 in Area 3, auf beiden `area 3 nssa`. R5: Router-ID 5.5.5.5, `ip route 172.16.5.0 255.255.255.0 Null0` "
                  "und `redistribute static subnets`, Loopback1 mit `ip ospf network point-to-point` in Area 3.",
             check="`show ip ospf database nssa-external` auf R5: Typ-7-LSA für 172.16.5.0/24. Auf R1 steht dasselbe Netz als O E2, "
                   "aus einem Typ-5-LSA, das R2 übersetzt hat.",
             think="Welcher Router übersetzt Typ 7 in Typ 5, und was gilt bei mehreren ABRs?"),
        dict(t="Default-Route ins Internet.",
             body="R1: `default-information originate always`. Teste auf R5 `ping 192.0.2.1 source Loopback1`. Der Ping scheitert. "
                  "Ändere auf R2 die Area-3-Zeile in `area 3 nssa default-information-originate`.",
             check="R5 hat jetzt `O*N2 0.0.0.0/0`, der Ping klappt.",
             think="Warum kommt die Default-Route von R1 nicht in Area 3, und welche andere Lösung gäbe es?"),
        dict(t="Testnetz aus Area 3 fernhalten.",
             body="Auf R2: `ip prefix-list NO-TEST seq 5 deny 10.1.99.0/24`, `ip prefix-list NO-TEST seq 10 permit 0.0.0.0/0 le 32` "
                  "und `area 3 filter-list prefix NO-TEST in`.",
             check="R5 hat 10.1.99.0/24 nicht mehr in der Routing-Tabelle, 10.1.1.0/24 schon.",
             think="Warum braucht die Prefix-Liste die zweite Zeile?")],
    answers=[
        ("1", "**Damit OSPF das Loopback-Netz mit seiner echten Maske ankündigt.** Standardmäßig ist eine Loopback ein Host und "
              "erscheint als /32. Mit point-to-point steht 10.1.1.0/24 in der Datenbank, wie ein echtes LAN."),
        ("2", "**Weil ein Router nur dann als ABR arbeitet, wenn er am Backbone hängt.** Inter-Area-Routen laufen immer über Area 0, "
              "zwischen zwei Nicht-Backbone-Areas gibt es keine Summaries. R3 hat keine Verbindung zu Area 0, also erzeugt er keine "
              "Typ-3-LSAs."),
        ("3", "**Weil der Virtual Link ein Interface in Area 0 ist.** Er übernimmt deren Authentisierungstyp. Ohne "
              "`area 0 authentication message-digest` sendet R3 über den Virtual Link ohne Authentisierung, R1 erwartet MD5 und "
              "verwirft die Pakete. Der Schlüssel am Virtual Link allein reicht nicht."),
        ("4", "**Sie verhindert Schleifen und unnötigen Verkehr.** Kommt bei R3 ein Paket für ein nicht vorhandenes Netz innerhalb "
              "von 10.4.4.0/23 an, verwirft R3 es, statt es über die Default-Route zurückzuschicken."),
        ("5", "**Der ABR der NSSA, hier R2.** Bei mehreren ABRs übersetzt nur der mit der höchsten Router-ID, außer einer ist mit "
              "`area 3 nssa translate type7 always` fest eingestellt. Das Typ-5-LSA trägt R2 als Absender und eine Adresse von R5 als "
              "Forwarding-Adresse; diese Adresse muss deshalb in den anderen Areas erreichbar sein."),
        ("6", "**Weil eine NSSA keine Typ-5-LSAs annimmt, und die Default-Route von R1 ist eine.** Lösungen: "
              "`default-information-originate` am ABR (Typ-7-Default, `O*N2`) oder `no-summary` (Totally NSSA, Default als Typ 3, "
              "`O*IA`). Mit `no-summary` fielen aber alle Inter-Area-Routen weg, und der Filter aus Schritt 7 wäre sinnlos."),
        ("7", "**Weil eine Prefix-Liste mit einem impliziten Deny endet.** Ohne die zweite Zeile würde der Filter alle Typ-3-LSAs "
              "nach Area 3 blockieren, nicht nur das Testnetz.")],
    nodes=[
        dict(name="R1", type="router", x=350, y=200,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.12.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.13.1 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.1.1.1 255.255.255.0
interface Loopback99
 ip address 10.1.99.1 255.255.255.0
interface Loopback100
 ip address 192.0.2.1 255.255.255.255""",
             sol="""
router ospf 1
 router-id 1.1.1.1
 area 0 authentication message-digest
 area 1 virtual-link 3.3.3.3 message-digest-key 1 md5 CCIE
 default-information originate always
interface GigabitEthernet0/0
 ip ospf message-digest-key 1 md5 CCIE
 ip ospf 1 area 0
interface GigabitEthernet0/1
 ip ospf 1 area 1
interface Loopback1
 ip ospf network point-to-point
 ip ospf 1 area 0
interface Loopback99
 ip ospf network point-to-point
 ip ospf 1 area 0"""),
        dict(name="R2", type="router", x=550, y=200,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.12.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.25.1 255.255.255.252
 no shutdown""",
             sol="""
ip prefix-list NO-TEST seq 5 deny 10.1.99.0/24
ip prefix-list NO-TEST seq 10 permit 0.0.0.0/0 le 32
router ospf 1
 router-id 2.2.2.2
 area 0 authentication message-digest
 area 3 nssa default-information-originate
 area 3 filter-list prefix NO-TEST in
interface GigabitEthernet0/0
 ip ospf message-digest-key 1 md5 CCIE
 ip ospf 1 area 0
interface GigabitEthernet0/1
 ip ospf 1 area 3"""),
        dict(name="R3", type="router", x=200, y=200,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.13.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.34.1 255.255.255.252
 no shutdown""",
             sol="""
router ospf 1
 router-id 3.3.3.3
 area 0 authentication message-digest
 area 1 virtual-link 1.1.1.1 message-digest-key 1 md5 CCIE
 area 2 range 10.4.4.0 255.255.254.0
interface GigabitEthernet0/0
 ip ospf 1 area 1
interface GigabitEthernet0/1
 ip ospf 1 area 2"""),
        dict(name="R4", type="router", x=50, y=200,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.34.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.4.4.1 255.255.255.0
interface Loopback2
 ip address 10.4.5.1 255.255.255.0""",
             sol="""
router ospf 1
 router-id 4.4.4.4
interface GigabitEthernet0/0
 ip ospf 1 area 2
interface Loopback1
 ip ospf network point-to-point
 ip ospf 1 area 2
interface Loopback2
 ip ospf network point-to-point
 ip ospf 1 area 2"""),
        dict(name="R5", type="router", x=700, y=200,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.25.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.5.5.1 255.255.255.0""",
             sol="""
ip route 172.16.5.0 255.255.255.0 Null0
router ospf 1
 router-id 5.5.5.5
 area 3 nssa
 redistribute static subnets
interface GigabitEthernet0/0
 ip ospf 1 area 3
interface Loopback1
 ip ospf network point-to-point
 ip ospf 1 area 3""")],
    links=[("R1", "Gi0/0", "R2", "Gi0/0"), ("R1", "Gi0/1", "R3", "Gi0/0"), ("R3", "Gi0/1", "R4", "Gi0/0"),
           ("R2", "Gi0/1", "R5", "Gi0/0")],
    staggered=True,
    tickets=["R5 steht mit R2 in FULL, hat aber keine einzige OSPF-Route. R2 kennt das LAN von R5 (10.5.5.0/24) nicht.",
             "R5 hat Routen zu den internen Netzen, erreicht aber 192.0.2.1 (Internet über R1) nicht.",
             "Das Testnetz 10.1.99.0/24 soll nicht in Area 3 gelangen. R5 hat es trotzdem in der Routing-Tabelle, obwohl R2 einen Filter hat.",
             "R1 und R2 kennen die Netze von R4 nicht. `show ip ospf virtual-links` auf R3 zeigt den Virtual Link zu 1.1.1.1, "
             "aber keine Nachbarschaft im Zustand FULL.",
             "R1 sieht statt der Zusammenfassung 10.4.4.0/23 die beiden Einzelnetze 10.4.4.0/24 und 10.4.5.0/24."],
    faults=[
        dict(node="R5", old=None, new=" ip ospf network point-to-point", ctx="interface GigabitEthernet0/0", nth=1,
             find="`show ip ospf interface GigabitEthernet0/0` auf R5: Netzwerktyp POINT_TO_POINT. Auf R2 ist Gi0/1 BROADCAST mit R2 "
                  "als DR. Die Hello- und Dead-Timer sind gleich (10/40), deshalb wird die Nachbarschaft FULL. In der Datenbank beschreibt "
                  "R5 den Link aber als Punkt-zu-Punkt, R2 als Transitnetz mit DR; die SPF-Berechnung findet keine beidseitige Verbindung.",
             cause="Netzwerktyp-Mismatch zwischen Broadcast und Punkt-zu-Punkt: Nachbarschaft FULL, aber keine Routen über diesen Link.",
             fix="`no ip ospf network point-to-point` unter Gi0/0 auf R5 (oder beide Seiten auf point-to-point)."),
        dict(node="R2", old=" area 3 nssa default-information-originate", new=" area 3 nssa",
             find="`show ip route 0.0.0.0` auf R5: keine Route. `show ip ospf database external` auf R2 zeigt die Default-Route von R1 "
                  "als Typ-5-LSA, in die NSSA gelangt sie aber nicht. `show ip ospf database nssa-external` auf R5 enthält kein 0.0.0.0.",
             cause="Eine NSSA bekommt, anders als eine Totally NSSA, keine Default-Route automatisch. Der ABR muss sie mit "
                   "`default-information-originate` als Typ-7-LSA erzeugen.",
             fix="`area 3 nssa default-information-originate` unter `router ospf 1` auf R2."),
        dict(node="R2", old=" area 3 filter-list prefix NO-TEST in", new=" area 3 filter-list prefix NO-TEST out",
             find="`show ip ospf database summary 10.1.99.0` auf R5 zeigt das Typ-3-LSA von R2. In der Konfiguration von R2 steht "
                  "`area 3 filter-list prefix NO-TEST out`: Das filtert Routen, die Area 3 verlassen, nicht die, die hineingehen.",
             cause="Falsche Richtung. `in` filtert die Typ-3-LSAs, die der ABR in die Area hinein erzeugt, `out` die, die er aus der Area "
                   "heraus meldet. Da NO-TEST nur 10.1.99.0/24 sperrt und dieses Netz nicht aus Area 3 stammt, filtert `out` gar nichts.",
             fix="`no area 3 filter-list prefix NO-TEST out` und `area 3 filter-list prefix NO-TEST in` auf R2."),
        dict(node="R3", old=" area 0 authentication message-digest", new=None,
             find="`debug ip ospf adj` auf R1 meldet beim Virtual Link einen falschen Authentisierungstyp (Mismatched Authentication type). "
                  "`show running-config | section router ospf` auf R3: `area 0 authentication message-digest` fehlt.",
             cause="Der Virtual Link ist ein Interface in Area 0 und übernimmt deren Authentisierungstyp. R1 verlangt MD5, R3 sendet ohne "
                   "Authentisierung. Damit ist Area 2 vom Backbone abgeschnitten.",
             fix="`area 0 authentication message-digest` unter `router ospf 1` auf R3."),
        dict(node="R3", old=" area 2 range 10.4.4.0 255.255.254.0", new=" area 1 range 10.4.4.0 255.255.254.0",
             find="`show ip route ospf` auf R1: zwei O-IA-Routen mit /24. Auf R3 steht `area 1 range 10.4.4.0 255.255.254.0`, die Netze "
                  "liegen aber in Area 2.",
             cause="Zusammenfassung unter der falschen Area. Eine Range fasst nur Netze der Area zusammen, unter der sie steht, und in "
                   "Area 1 gibt es 10.4.x nicht.",
             fix="`no area 1 range 10.4.4.0 255.255.254.0` und `area 2 range 10.4.4.0 255.255.254.0` auf R3.")],
    verify=["show ip ospf neighbor", "show ip ospf interface brief", "show ip ospf virtual-links", "show ip ospf database",
            "show ip route ospf", "ping 192.0.2.1 source Loopback1   ! auf R5"],
    verify_table=[("`show ip ospf virtual-links` auf R3", "Virtual Link zu 1.1.1.1, Nachbarschaft FULL, Message-Digest"),
                  ("`show ip route ospf` auf R1", "O IA 10.4.4.0/23, O IA 10.5.5.0/24, O E2 172.16.5.0/24"),
                  ("`show ip route` auf R5", "O*N2 0.0.0.0/0, O IA 10.1.1.0/24, kein 10.1.99.0/24"),
                  ("`ping 192.0.2.1 source Loopback1` auf R5", "erfolgreich über die NSSA-Default-Route")],
    teilc=[("Area 0 zerfällt durch einen Linkausfall in zwei Hälften, die beide noch an Area 1 hängen. Was passiert, und wie hilft ein Virtual Link?",
            "**Die beiden Hälften tauschen keine Inter-Area-Routen mehr aus**, weil Summaries nicht über eine Nicht-Backbone-Area "
            "zwischen Backbone-Teilen laufen. Ein Virtual Link durch Area 1 verbindet die Hälften wieder zu einer Area 0. Dauerhaft ist "
            "ein zweiter physischer Backbone-Link die bessere Lösung."),
           ("Warum darf die Transit-Area eines Virtual Links keine Stub- oder NSSA-Area sein?",
            "**Weil über den Virtual Link Backbone-Verkehr zu allen Zielen läuft, auch zu externen.** Die Transit-Area muss dafür volle "
            "Routing-Information haben, eine Stub-Area hat keine Typ-5-LSAs. Ein Virtual Link durch eine Stub- oder NSSA-Area ist "
            "deshalb nicht erlaubt."),
           ("Ein Router soll nach dem Neustart erst Verkehr bekommen, wenn BGP konvergiert ist. Was setzt du in OSPF?",
            "**`max-metric router-lsa on-startup wait-for-bgp`.** Der Router meldet seine Links mit maximaler Metrik, die anderen "
            "umgehen ihn, solange es Alternativen gibt. Sobald BGP fertig ist, spätestens nach 600 Sekunden, meldet er normale Kosten."),
           ("Was unterscheidet `area 2 range … not-advertise` von `area 2 filter-list prefix … out`?",
            "**`range not-advertise` unterdrückt einen zusammengefassten Block von Netzen aus Area 2, `filter-list` arbeitet mit "
            "beliebigen Prefix-Listen auf allen Typ-3-LSAs, die der ABR aus der Area heraus erzeugt.** Externe Routen (Typ 5 und 7) erfasst "
            "keiner von beiden, dafür gibt es `summary-address` oder Filter am ASBR.")],
    exam=["Jede Area muss an Area 0 hängen; sonst Virtual Link durch eine normale Transit-Area (`area <Transit> virtual-link <RID>`).",
          "Der Virtual Link gehört zu Area 0 und übernimmt deren Authentisierung.",
          "Netzwerktyp-Mismatch Broadcast und Punkt-zu-Punkt: Nachbarschaft FULL, aber keine Routen.",
          "NSSA: Typ 7 statt Typ 5, Übersetzung durch den ABR mit der höchsten Router-ID. Default nur mit "
          "`default-information-originate` (O*N2) oder `no-summary` (O*IA).",
          "`area X filter-list prefix … in|out` filtert nur Typ-3-LSAs am ABR, `area X range` fasst nur Intra-Area-Netze zusammen."],
)
