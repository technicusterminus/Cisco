LAB = dict(
    slug="E1-DMVPN-Phase3", num="E1", title="DMVPN Phase 3 mit EIGRP", minutes=90, level="schwer",
    summary=("Ein Hub und zwei Spokes bauen über einen simulierten Internet-Router ein DMVPN auf: mGRE, NHRP-Registrierung, "
             "EIGRP über den Tunnel und Phase 3 mit NHRP-Redirect und Shortcut. Du siehst, wie aus einer Summary-Route "
             "über den Hub eine direkte Spoke-to-Spoke-Verbindung wird."),
    goals=["Einen mGRE-Tunnel mit NHRP auf Hub und Spokes aufbauen und die Registrierung mit `show dmvpn` prüfen.",
           "EIGRP über das DMVPN betreiben und erklären, warum der Hub in Phase 3 eine Summary-Route sendet.",
           "Mit `show ip route nhrp` und `traceroute` nachweisen, dass ein Spoke-to-Spoke-Shortcut entstanden ist.",
           "Typische Fehler (Tunnel Key, NBMA-Adresse, Redirect, Shortcut, Summary) an ihrem Symptom erkennen."],
    tags=[("2.3", "DMVPN: Fehlersuche", 16), ("2.3.a", "DMVPN: GRE und mGRE", 5), ("2.3.b", "DMVPN: NHRP", 8),
          ("2.3.d", "DMVPN: Dynamische Nachbarn", 6), ("2.3.e", "DMVPN: Spoke-to-Spoke", 6)],
    diagram="""
              Internet (ISP)
        ┌────────────┼────────────┐
   Gi0/0│       Gi0/1│       Gi0/2│
      HUB           S1           S2
   Lo1 10.10.0.1  Lo1 10.10.1.1  Lo1 10.10.2.1
        └──── Tunnel0 172.16.0.0/24 (mGRE) ────┘
""",
    nets=[("HUB Gi0/0 – ISP Gi0/0", "198.51.100.0/30 (HUB .1, ISP .2)"),
          ("S1 Gi0/0 – ISP Gi0/1", "198.51.100.4/30 (S1 .5, ISP .6)"),
          ("S2 Gi0/0 – ISP Gi0/2", "198.51.100.8/30 (S2 .9, ISP .10)"),
          ("Tunnel0 (Overlay)", "172.16.0.0/24 (HUB .1, S1 .2, S2 .3)"),
          ("LANs (Loopback1)", "10.10.0.0/24 (HUB), 10.10.1.0/24 (S1), 10.10.2.0/24 (S2)")],
    topo_text=("Der ISP-Router kennt nur seine drei /30-Netze (das „Internet“ kennt keine privaten Adressen). HUB und Spokes haben "
               "Default-Routen zum ISP und erreichen sich so über die NBMA-Adressen (198.51.100.x). Die LANs sind Loopback1-Interfaces; "
               "du testest mit `ping … source Loopback1`. Verschlüsselung (IPsec) ist hier bewusst weggelassen, damit die "
               "NHRP-Logik im Vordergrund steht."),
    steps=[
        dict(t="Underlay prüfen.", body="Die Interfaces und Default-Routen sind gesetzt. Pinge vom HUB die NBMA-Adressen der Spokes (198.51.100.5 und .9) und von S1 die von S2.",
             check="Alle Pings gehen durch. Ohne funktionierendes Underlay gibt es kein DMVPN."),
        dict(t="Hub-Tunnel bauen.", body="Auf dem HUB: `interface Tunnel0` mit `ip address 172.16.0.1 255.255.255.0`, `tunnel source GigabitEthernet0/0`, `tunnel mode gre multipoint` und `tunnel key 100`. Dazu `ip nhrp network-id 100`, `ip nhrp authentication DMVPN` und `ip nhrp map multicast dynamic`.",
             check="`show interfaces Tunnel0` meldet up/up, `show dmvpn` zeigt noch keine Spokes.",
             think="Wozu dient `map multicast dynamic`, und was würde ohne diese Zeile mit EIGRP passieren?"),
        dict(t="Spokes anbinden.", body="Auf S1 und S2: derselbe Tunnel mit eigener Tunnel-IP (172.16.0.2 und .3), `tunnel mode gre multipoint`, `tunnel key 100`, gleiche NHRP-ID und Authentication. Statt `map multicast dynamic` trägst du den Hub ein: `ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast`.",
             check="`show dmvpn` auf dem HUB listet zwei Spokes im Zustand UP, Attribut `D` (dynamisch). Auf den Spokes steht der Hub mit Attribut `S` (statisch).",
             think="Welche Adresse ist die NBMA-Adresse und welche die Tunnel-Adresse? Warum braucht ein Spoke beide für den Hub?"),
        dict(t="EIGRP über den Tunnel.", body="Auf allen drei Routern `router eigrp 100` mit `network 172.16.0.0 0.0.0.255`, dem jeweiligen LAN (Loopback1) und `no auto-summary`.",
             check="`show ip eigrp neighbors` auf dem HUB zeigt zwei Nachbarn. Auf S1 steht die Route 10.10.0.0/24, aber (wegen Split Horizon) noch nicht 10.10.2.0/24.",
             think="Warum lernt S1 die LAN-Route von S2 nicht, und warum ist das in Phase 3 sogar gewollt?"),
        dict(t="Phase 3 einschalten.", body="Auf dem HUB: `ip summary-address eigrp 100 10.10.0.0 255.255.0.0` am Tunnel und `ip nhrp redirect`. Auf den Spokes: `ip nhrp shortcut`. Pinge danach von S1 `ping 10.10.2.1 source Loopback1 repeat 10`.",
             check="Vorher: `show ip route 10.10.2.1` auf S1 zeigt die Summary über 172.16.0.1. Nach dem Ping: `show ip route nhrp` zeigt 10.10.2.0/24 über 172.16.0.3, und `traceroute 10.10.2.1 source Loopback1` geht direkt zu 172.16.0.3.",
             think="Welche Rolle spielen Redirect (Hub) und Shortcut (Spoke), und wer schickt wem die Resolution Request?"),
        dict(t="MTU und MSS.", body="Setze am Tunnel `ip mtu 1400` und `ip tcp adjust-mss 1360` auf allen drei Routern.",
             check="`show interfaces Tunnel0 | include MTU` zeigt 1400.",
             think="Warum fragmentiert ein GRE-Tunnel ohne diese Werte große Pakete, und was kommt mit IPsec noch dazu?"),
        dict(t="Schutz einordnen.", body="IPsec ist in diesem Lab nicht konfiguriert.",
             think="Welche Zeile würdest du am Tunnel ergänzen (`tunnel protection ipsec profile …`), und welcher Zustand in `show dmvpn` zeigt, dass die IPsec-Phase hängt?")],
    answers=[
        ("2", "Der Hub ist nicht vorab konfiguriert, wer sich registriert: Er lernt die Spokes dynamisch. Mit `map multicast dynamic` nimmt er jeden registrierten Spoke in die Multicast-Replikationsliste auf. Ohne die Zeile gehen EIGRP-Hellos (224.0.0.10) nicht zu den Spokes, es entstehen keine Nachbarschaften."),
        ("3", "Die **NBMA-Adresse** (198.51.100.1) ist die öffentliche Underlay-Adresse, an die das GRE-Paket gesendet wird. Die **Tunnel-Adresse** (172.16.0.1) ist die Overlay-Adresse. Der Spoke braucht beide, weil er nur so die Zuordnung Overlay → Underlay kennt (statische NHRP-Zuordnung zum Hub)."),
        ("4", "EIGRP sendet auf dem Tunnel-Interface wegen Split Horizon keine Routen zurück, die es dort gelernt hat. Der Hub gibt S2s LAN also nicht an S1 weiter. In Phase 3 ist das egal und sogar gewollt, weil der Hub ohnehin eine Summary sendet und Details über NHRP nachgeladen werden."),
        ("5", "Der **Hub** bemerkt, dass ein Paket am selben Tunnel wieder hinausgeht, und schickt dem sendenden Spoke einen *NHRP Traffic Indication* (Redirect). Der **Spoke** mit `shortcut` fragt daraufhin per Resolution Request den NBMA-Eintrag des Ziel-Spokes ab (die Anfrage läuft über den Hub, die Antwort kommt direkt vom Ziel-Spoke) und installiert eine NHRP-Route (`H`) für das Zielnetz."),
        ("6", "GRE fügt 24 Byte hinzu (äußerer IP-Header 20 + GRE 4), mit Tunnel Key sind es 28. Ein 1500-Byte-Paket passt dann nicht mehr in 1500 Byte. `ip mtu 1400` und `adjust-mss 1360` halten TCP unter der Grenze. Mit IPsec kommen ESP-Header, IV und Padding hinzu, daher der Puffer."),
        ("7", "`tunnel protection ipsec profile <Name>` am Tunnel, mit ISAKMP-Profil und IPsec-Profil (Transform Set im *Transport Mode*). In `show dmvpn` steht der Peer im Zustand `IKE` oder `IPsec`, wenn die Verschlüsselung noch hängt, erst bei `UP` ist beides durch.")],
    nodes=[
        dict(name="HUB", type="router", x=200, y=100,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.1 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.10.0.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 198.51.100.2""",
             sol="""
interface Tunnel0
 ip address 172.16.0.1 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip nhrp network-id 100
 ip nhrp authentication DMVPN
 ip nhrp map multicast dynamic
 ip nhrp redirect
 ip summary-address eigrp 100 10.10.0.0 255.255.0.0
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
router eigrp 100
 network 172.16.0.0 0.0.0.255
 network 10.10.0.0 0.0.0.255
 no auto-summary"""),
        dict(name="ISP", type="router", x=400, y=200,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 198.51.100.6 255.255.255.252
 no shutdown
interface GigabitEthernet0/2
 ip address 198.51.100.10 255.255.255.252
 no shutdown""", sol=""),
        dict(name="S1", type="router", x=600, y=100,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.5 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.10.1.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 198.51.100.6""",
             sol="""
interface Tunnel0
 ip address 172.16.0.2 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip nhrp network-id 100
 ip nhrp authentication DMVPN
 ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast
 ip nhrp shortcut
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
router eigrp 100
 network 172.16.0.0 0.0.0.255
 network 10.10.1.0 0.0.0.255
 no auto-summary"""),
        dict(name="S2", type="router", x=400, y=350,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.9 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.10.2.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 198.51.100.10""",
             sol="""
interface Tunnel0
 ip address 172.16.0.3 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip nhrp network-id 100
 ip nhrp authentication DMVPN
 ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast
 ip nhrp shortcut
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel key 100
router eigrp 100
 network 172.16.0.0 0.0.0.255
 network 10.10.2.0 0.0.0.255
 no auto-summary""")],
    links=[("HUB", "Gi0/0", "ISP", "Gi0/0"), ("S1", "Gi0/0", "ISP", "Gi0/1"), ("S2", "Gi0/0", "ISP", "Gi0/2")],
    staggered=True,
    tickets=["S1 hat keinen EIGRP-Nachbarn zum Hub; der Tunnel ist up/up, aber `show dmvpn` auf dem Hub listet S1 nicht.",
             "S2 hat keinen EIGRP-Nachbarn zum Hub; `show dmvpn` auf S2 zeigt den Hub nicht als UP.",
             "Der Verkehr zwischen S1 und S2 läuft, geht aber immer über den Hub; `show ip route nhrp` ist auf beiden Spokes leer.",
             "Von S1 zu S2 geht der Verkehr direkt, in der Gegenrichtung aber immer noch über den Hub.",
             "S1 erreicht das LAN von S2 nicht; die Traceroute endet beim ISP."],
    faults=[
        dict(node="S1", old=" tunnel key 100", new=" tunnel key 101",
             find="`show interfaces Tunnel0 | include Key` zeigt auf S1 den Key 0x65 (101), auf dem Hub 0x64 (100). Der Hub verwirft die GRE-Pakete mit fremdem Key.",
             cause="Der Tunnel Key ist Teil des GRE-Headers und muss auf beiden Seiten gleich sein. Bei Abweichung verwirft der Empfänger das Paket, die NHRP-Registrierung kommt nie an.",
             fix="`tunnel key 100` auf S1."),
        dict(node="S2", old=" ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast",
             new=" ip nhrp nhs 172.16.0.1 nbma 198.51.100.2 multicast",
             find="`show ip nhrp nhs detail` auf S2 zeigt als NBMA-Adresse des Hubs 198.51.100.2 (das ist die ISP-Seite). `ping 198.51.100.2` geht, das GRE-Paket der Registrierung landet aber beim ISP.",
             cause="Die NBMA-Adresse des Hubs ist falsch (ISP-Interface statt Hub). Die Registrierung geht an den ISP-Router, der kein GRE terminiert.",
             fix="`ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast`."),
        dict(node="HUB", old=" ip nhrp redirect", new=None,
             find="`show running-config interface Tunnel0 | include redirect` auf dem Hub bleibt leer. `show ip nhrp traffic` zeigt keine gesendeten Traffic Indications.",
             cause="Ohne `ip nhrp redirect` sagt der Hub den Spokes nie, dass es einen kürzeren Weg gibt. Die Spokes bleiben bei der Summary-Route über den Hub.",
             fix="`ip nhrp redirect` am Tunnel des Hubs."),
        dict(node="S2", old=" ip nhrp shortcut", new=None,
             find="`show running-config interface Tunnel0 | include shortcut` auf S2 bleibt leer; auf S1 steht die Zeile. `show ip route nhrp` auf S2 bleibt leer.",
             cause="Ohne `ip nhrp shortcut` wertet S2 die Redirects des Hubs nicht aus und installiert keine NHRP-Route. Der Rückweg bleibt bei der Summary über den Hub.",
             fix="`ip nhrp shortcut` am Tunnel von S2."),
        dict(node="HUB", old=" ip summary-address eigrp 100 10.10.0.0 255.255.0.0",
             new=" ip summary-address eigrp 100 10.10.0.0 255.255.255.0",
             find="`show ip route eigrp` auf S1 zeigt nur 10.10.0.0/24 statt 10.10.0.0/16. `show ip route 10.10.2.1` greift auf die Default-Route zum ISP, daher endet die Traceroute dort.",
             cause="Die Summary ist /24 statt /16 und deckt die Spoke-LANs nicht ab. Wegen Split Horizon gibt der Hub die Spoke-Routen nicht weiter, also fehlt jede Route zu 10.10.2.0/24.",
             fix="`ip summary-address eigrp 100 10.10.0.0 255.255.0.0` am Tunnel des Hubs.")],
    verify=["show dmvpn", "show ip nhrp", "show ip nhrp nhs detail           ! auf den Spokes", "show ip eigrp neighbors",
            "show ip route eigrp", "show ip route nhrp                 ! Shortcut-Routen (H)",
            "ping 10.10.2.1 source Loopback1 repeat 10    ! auf S1",
            "traceroute 10.10.2.1 source Loopback1", "show interfaces Tunnel0 | include Key|MTU"],
    verify_table=[("`show dmvpn` auf dem HUB", "zwei Spokes im Zustand UP, Attribut `D`"),
                  ("`show dmvpn` auf einem Spoke", "der Hub mit Attribut `S`; nach einem Ping zum anderen Spoke zusätzlich ein Eintrag mit `D`"),
                  ("`show ip route nhrp` auf S1 nach dem Ping", "`H 10.10.2.0/24` über 172.16.0.3"),
                  ("`traceroute` von S1 nach 10.10.2.1", "erster Versuch über 172.16.0.1, danach direkt über 172.16.0.3")],
    teilc=[("Was ändert sich zwischen Phase 2 und Phase 3?",
            "**In Phase 3 sendet der Hub eine Summary, und die Spokes bekommen den direkten Weg per NHRP-Redirect/Shortcut.** In Phase 2 muss der Hub die Spoke-Routen unverändert (mit Original-Next-Hop, `no ip next-hop-self eigrp`) weitergeben, die Spokes lernen alle Details und lösen den Next-Hop per NHRP-Resolution auf. Phase 3 skaliert besser, weil die Routing-Tabelle klein bleibt und Summarization möglich ist."),
           ("`show dmvpn` auf dem Spoke zeigt den Hub im Zustand `NHRP`. Wo suchst du?",
            "**Bei der NHRP-Registrierung und beim Underlay.** `NHRP` heißt: Der Eintrag existiert, aber die Registrierung wurde nicht bestätigt. Prüfe NBMA-Adresse, Tunnel Key, `network-id`, Authentication und ob das Underlay-GRE (IP-Protokoll 47) durchkommt."),
           ("Warum kann es zu Problemen kommen, wenn zwei Spokes hinter NAT sitzen?",
            "**Weil NAT die NBMA-Adresse verändert, die der Hub lernt.** DMVPN kommt damit klar, wenn nur ein Spoke hinter NAT sitzt und IPsec NAT-Traversal (UDP 4500) nutzt. Zwei Spokes hinter jeweils eigenem NAT können sich oft nicht direkt erreichen, dann bleibt der Verkehr über den Hub.")],
    exam=["Phase 1: Hub-and-Spoke, p2p-GRE auf den Spokes. Phase 2: Spoke-to-Spoke, Hub ohne Summary. Phase 3: Redirect und Shortcut, Summary möglich.",
          "Hub: `ip nhrp map multicast dynamic`, `ip nhrp redirect`. Spoke: `ip nhrp nhs … nbma … multicast`, `ip nhrp shortcut`.",
          "Fehlersuche von unten: Underlay-Ping, GRE (Key, Source), NHRP (ID, Authentication, NBMA), IPsec, Routing.",
          "Zustände in `show dmvpn`: NHRP, IKE, IPsec, UP. Attribute: S statisch, D dynamisch, T1 Route installiert, T2 Next-Hop-Override (Shortcut).",
          "EIGRP über DMVPN: Split Horizon am Hub-Tunnel beachten, bei Phase 2 `no ip next-hop-self eigrp`."],
)
