CRYPTO = """
crypto ikev2 proposal PROP
 encryption aes-cbc-256
 integrity sha256
 group 14
crypto ikev2 policy POL
 proposal PROP
crypto ikev2 keyring KR
 peer ANY
  address 0.0.0.0 0.0.0.0
  pre-shared-key DMVPN-Lab-Key
crypto ikev2 profile IKEV2-DMVPN
 match identity remote address 0.0.0.0
 authentication remote pre-share
 authentication local pre-share
 keyring local KR
crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
 mode transport
crypto ipsec profile IPSEC-DMVPN
 set transform-set TS
 set ikev2-profile IKEV2-DMVPN"""


def spoke_tunnel(ip):
    return f"""
interface Tunnel0
 ip address {ip} 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip nhrp network-id 1
 ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast
 ip nhrp shortcut
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel protection ipsec profile IPSEC-DMVPN"""


LAB = dict(
    slug="C5-DMVPN-IKEv2-BGP", num="C5", title="DMVPN Phase 3 mit IKEv2 und BGP mit dynamischen Nachbarn",
    minutes=120, level="schwer",
    summary=("Ein Hub und zwei Spokes bauen über einen Internet-Router ein DMVPN auf, diesmal geschützt mit IPsec und IKEv2. "
             "Das Routing läuft über iBGP: Der Hub nimmt Spokes über einen Listen-Range ohne einzelne Nachbar-Einträge an und "
             "gibt ihnen nur eine Zusammenfassung. Die direkten Wege zwischen den Spokes entstehen per NHRP-Redirect und -Shortcut, "
             "jeweils mit eigener IPsec-Verbindung."),
    goals=["IKEv2 mit Proposal, Policy, Keyring und Profil aufbauen und an ein DMVPN-Tunnelinterface binden.",
           "Die Reihenfolge IKEv2, IPsec, NHRP verstehen und Fehler in der richtigen Schicht suchen.",
           "BGP mit `bgp listen range` und Peer-Group betreiben und erklären, warum hier kein Route Reflector nötig ist.",
           "Phase 3 mit Summary, Redirect und Shortcut nachweisen."],
    tags=[("1.5.e", "BGP: Konvergenz und Skalierung", 6), ("3.1.b", "IPsec und IKE", 5), ("3.1.c", "DMVPN", 9)],
    diagram="""
                 HUB   Lo1 10.10.100.1/24, Tunnel0 172.16.0.1
                  | Gi0/0  198.51.100.1
                  |
                  | Gi0/0  198.51.100.2
                 INET  (Internet, nur Underlay)
         Gi0/1  /      \\  Gi0/2
       .6      /        \\      .10
       .5     /          \\     .9
         Gi0/0            Gi0/0
        S1                    S2
   Lo1 10.10.1.1/24       Lo1 10.10.2.1/24
   Tunnel0 172.16.0.2     Tunnel0 172.16.0.3
""",
    nets=[("HUB Gi0/0 – INET Gi0/0", "198.51.100.0/30 (HUB .1, INET .2)"),
          ("S1 Gi0/0 – INET Gi0/1", "198.51.100.4/30 (S1 .5, INET .6)"),
          ("S2 Gi0/0 – INET Gi0/2", "198.51.100.8/30 (S2 .9, INET .10)"),
          ("Tunnel0 (DMVPN)", "172.16.0.0/24 (HUB .1, S1 .2, S2 .3)"),
          ("LANs (Loopback1)", "HUB 10.10.100.0/24, S1 10.10.1.0/24, S2 10.10.2.0/24"),
          ("BGP", "AS 65000 auf allen drei Routern (iBGP)")],
    topo_text=("Die Underlay-Adressen und Default-Routen Richtung INET sind vorgegeben, INET selbst braucht keine Routen. Alles, was "
               "durch den Tunnel geht, ist mit IPsec geschützt: Spoke-zu-Hub ab dem Start, Spoke-zu-Spoke, sobald NHRP den direkten "
               "Weg aufbaut. Pre-Shared Key, Proposal und Profilnamen sind auf allen Routern gleich."),
    steps=[
        dict(t="Underlay prüfen.", body="Pinge vom HUB 198.51.100.5 und 198.51.100.9.",
             check="Beide Pings klappen.",
             think="Welche Adressen und Routen muss ein Spoke kennen, bevor der Tunnel steht?"),
        dict(t="IKEv2 und IPsec-Profil.",
             body="Auf HUB, S1 und S2 identisch: `crypto ikev2 proposal PROP` (`encryption aes-cbc-256`, `integrity sha256`, `group 14`), "
                  "`crypto ikev2 policy POL` mit `proposal PROP`, `crypto ikev2 keyring KR` mit `peer ANY`, `address 0.0.0.0 0.0.0.0` und "
                  "`pre-shared-key DMVPN-Lab-Key`, `crypto ikev2 profile IKEV2-DMVPN` mit `match identity remote address 0.0.0.0`, "
                  "`authentication remote pre-share`, `authentication local pre-share` und `keyring local KR`. Dazu "
                  "`crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac` mit `mode transport` und `crypto ipsec profile IPSEC-DMVPN` "
                  "mit `set transform-set TS` und `set ikev2-profile IKEV2-DMVPN`.",
             check="`show crypto ikev2 proposal` und `show crypto ipsec profile` zeigen die Einträge auf allen drei Routern.",
             think="Warum nimmt man bei DMVPN den Transport Mode?"),
        dict(t="Hub-Tunnel.",
             body="Auf dem HUB `interface Tunnel0` mit 172.16.0.1/24, `tunnel source GigabitEthernet0/0`, `tunnel mode gre multipoint`, "
                  "`ip nhrp network-id 1`, `ip nhrp map multicast dynamic`, `no ip redirects`, `ip mtu 1400`, `ip tcp adjust-mss 1360` "
                  "und `tunnel protection ipsec profile IPSEC-DMVPN`.",
             check="`show interface Tunnel0` ist up/up.",
             think="Warum braucht der Hub keine statische NHRP-Zuordnung zu den Spokes?"),
        dict(t="Spokes anbinden.",
             body="Auf S1 und S2 derselbe Tunnel mit eigener Adresse (172.16.0.2 und .3), statt `map multicast dynamic` aber "
                  "`ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast`.",
             check="`show crypto ikev2 sa` auf jedem Spoke zeigt eine SA zum Hub im Status READY. `show dmvpn` auf dem HUB listet beide "
                   "Spokes im Zustand UP.",
             think="In welcher Reihenfolge laufen IKEv2, IPsec und NHRP ab, wenn ein Spoke startet?"),
        dict(t="BGP mit dynamischen Nachbarn.",
             body="HUB: `router bgp 65000` mit `neighbor SPOKES peer-group`, `neighbor SPOKES remote-as 65000`, "
                  "`bgp listen range 172.16.0.0/24 peer-group SPOKES`, `network 10.10.100.0 mask 255.255.255.0` und "
                  "`aggregate-address 10.10.0.0 255.255.0.0 summary-only`. Spokes: `router bgp 65000`, eigenes LAN per `network`, "
                  "Nachbar 172.16.0.1 mit `remote-as 65000`.",
             check="`show ip bgp summary` auf dem HUB zeigt zwei dynamisch angelegte Nachbarn (mit `*` markiert). Jeder Spoke hat "
                   "10.10.0.0/16 über 172.16.0.1, aber keine Netze der anderen Spokes.",
             think="Der Hub ist kein Route Reflector. Warum reicht das hier trotzdem?"),
        dict(t="Phase 3.",
             body="HUB: `ip nhrp redirect` am Tunnel. S1 und S2: `ip nhrp shortcut`. Dann auf S1 zweimal "
                  "`traceroute 10.10.2.1 source Loopback1`.",
             check="Der erste Traceroute geht über 172.16.0.1, der zweite direkt zu 172.16.0.3. `show ip route nhrp` auf S1 zeigt "
                   "10.10.2.0/24 über 172.16.0.3, `show crypto ikev2 sa` eine zusätzliche SA zu 198.51.100.9.",
             think="Wozu die Zusammenfassung auf dem Hub, wenn NHRP die direkten Wege ohnehin selbst findet?"),
        dict(t="Schutz prüfen.", body="Auf S1 `show crypto ipsec sa peer 198.51.100.9`, während Pings zwischen den Spoke-LANs laufen.",
             check="Die Zähler für verschlüsselte und entschlüsselte Pakete steigen.",
             think="Was passiert mit dem direkten Weg, wenn eine Weile kein Verkehr zwischen S1 und S2 fließt?")],
    answers=[
        ("1", "**Nur die NBMA-Adresse des Hubs (198.51.100.1) und einen Weg dorthin**, hier die Default-Route. Die Tunnel- und "
              "NBMA-Adressen der anderen Spokes lernt er über NHRP, die LANs über BGP."),
        ("2", "**Weil GRE schon einen äußeren IP-Header mit den NBMA-Adressen mitbringt.** Der Transport Mode schützt das GRE-Paket, "
              "ohne einen zweiten äußeren IP-Header hinzuzufügen, und spart so 20 Byte pro Paket. Tunnel Mode funktioniert auch, "
              "kostet aber mehr Overhead."),
        ("3", "**Weil die Spokes sich selbst registrieren.** Jeder Spoke meldet dem Hub per NHRP Registration Request seine Tunnel- und "
              "NBMA-Adresse. `ip nhrp map multicast dynamic` nimmt die registrierten Spokes zusätzlich in die Liste für Multicast auf, "
              "etwa für die Hellos eines IGP."),
        ("4", "**Erst IKEv2 (IKE_SA_INIT, dann IKE_AUTH mit dem Pre-Shared Key), daraus die IPsec-SA, dann die NHRP-Registrierung durch "
              "den geschützten Tunnel.** Scheitert IKE, kommt keine Registrierung an. Deshalb zuerst `show crypto ikev2 sa`, "
              "dann `show crypto ipsec sa`, dann `show dmvpn`."),
        ("5", "**Weil der Hub die Routen der Spokes gar nicht weitergeben muss.** Er fasst alles zu 10.10.0.0/16 zusammen, und dieses "
              "Aggregat erzeugt er selbst. Selbst erzeugte Routen gibt ein iBGP-Router an alle iBGP-Nachbarn weiter. Nur wenn die Spokes "
              "die spezifischen Netze der anderen Spokes bräuchten, müsste der Hub sie als Route Reflector spiegeln."),
        ("6", "**Damit die Spokes klein bleiben.** Jeder Spoke braucht nur 10.10.0.0/16 Richtung Hub. Die direkten Wege legt NHRP bei "
              "Bedarf als spezifischere Route an (`H` in der Routing-Tabelle), und sie verfallen wieder. Ohne Summary müsste jeder Spoke "
              "alle Spoke-Netze kennen, bei hunderten Standorten eine große BGP-Tabelle."),
        ("7", "**Er verfällt.** Der NHRP-Eintrag und die Shortcut-Route laufen nach der NHRP-Haltezeit ab (`ip nhrp holdtime`), mit "
              "ihnen verschwindet auch die direkte IPsec-Verbindung. Das nächste Paket geht wieder zuerst über den Hub, bis Redirect und "
              "Shortcut den direkten Weg neu aufbauen.")],
    nodes=[
        dict(name="HUB", type="router", x=350, y=50,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.1 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.10.100.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 198.51.100.2""",
             sol=CRYPTO + """
interface Tunnel0
 ip address 172.16.0.1 255.255.255.0
 no ip redirects
 ip mtu 1400
 ip tcp adjust-mss 1360
 ip nhrp network-id 1
 ip nhrp map multicast dynamic
 ip nhrp redirect
 tunnel source GigabitEthernet0/0
 tunnel mode gre multipoint
 tunnel protection ipsec profile IPSEC-DMVPN
router bgp 65000
 bgp router-id 10.10.100.1
 bgp log-neighbor-changes
 neighbor SPOKES peer-group
 neighbor SPOKES remote-as 65000
 bgp listen range 172.16.0.0/24 peer-group SPOKES
 network 10.10.100.0 mask 255.255.255.0
 aggregate-address 10.10.0.0 255.255.0.0 summary-only"""),
        dict(name="INET", type="router", x=350, y=250,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 198.51.100.6 255.255.255.252
 no shutdown
interface GigabitEthernet0/2
 ip address 198.51.100.10 255.255.255.252
 no shutdown"""),
        dict(name="S1", type="router", x=150, y=450,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.5 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.10.1.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 198.51.100.6""",
             sol=CRYPTO + spoke_tunnel("172.16.0.2") + """
router bgp 65000
 bgp router-id 10.10.1.1
 bgp log-neighbor-changes
 network 10.10.1.0 mask 255.255.255.0
 neighbor 172.16.0.1 remote-as 65000"""),
        dict(name="S2", type="router", x=550, y=450,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.9 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.10.2.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 198.51.100.10""",
             sol=CRYPTO + spoke_tunnel("172.16.0.3") + """
router bgp 65000
 bgp router-id 10.10.2.1
 bgp log-neighbor-changes
 network 10.10.2.0 mask 255.255.255.0
 neighbor 172.16.0.1 remote-as 65000""")],
    links=[("HUB", "Gi0/0", "INET", "Gi0/0"), ("S1", "Gi0/0", "INET", "Gi0/1"), ("S2", "Gi0/0", "INET", "Gi0/2")],
    staggered=True,
    tickets=["S1 ist nicht im DMVPN: `show dmvpn` auf S1 zeigt den Hub nicht im Zustand UP. Das Underlay ist in Ordnung.",
             "S2 taucht in `show dmvpn` auf dem Hub nicht auf. `ping 198.51.100.1 source GigabitEthernet0/0` von S2 klappt.",
             "Die Tunnel stehen und beide Spokes sind registriert, aber keiner hat eine BGP-Sitzung zum Hub. Die Spokes kennen "
             "10.10.0.0/16 nicht.",
             "Verkehr zwischen den Spokes läuft dauerhaft über den Hub: `traceroute 10.10.2.1 source Loopback1` von S1 zeigt auch beim "
             "dritten Versuch 172.16.0.1 als ersten Hop.",
             "Von S2 zu S1 entsteht nach dem ersten Paket ein direkter Weg, von S1 zu S2 bleibt der Verkehr beim Hub."],
    faults=[
        dict(node="S1", old=" group 14", new=" group 19",
             find="`show crypto ikev2 sa` auf S1: keine SA. `debug crypto ikev2` auf dem Hub meldet beim IKE_SA_INIT, dass kein passender "
                  "Vorschlag gefunden wurde (NO_PROPOSAL_CHOSEN). `show crypto ikev2 proposal` auf S1 nennt die DH-Gruppe 19, der Hub "
                  "erwartet 14.",
             cause="Die IKEv2-Vorschläge passen nicht zusammen. S1 bietet nur DH-Gruppe 19 an, der Hub akzeptiert nur 14. IKE scheitert, "
                   "bevor überhaupt authentisiert wird.",
             fix="Unter `crypto ikev2 proposal PROP` auf S1 `no group 19` und `group 14`."),
        dict(node="S2", old="  pre-shared-key DMVPN-Lab-Key", new="  pre-shared-key DMVPN-Lab-Kei",
             find="`show crypto ikev2 sa` auf S2 zeigt keine SA im Status READY. `debug crypto ikev2` auf dem Hub meldet beim IKE_AUTH "
                  "einen Authentisierungsfehler. Der Keyring auf S2 enthält `DMVPN-Lab-Kei`.",
             cause="Unterschiedlicher Pre-Shared Key: IKE_SA_INIT klappt, IKE_AUTH scheitert. Ohne IPsec-SA kommt die NHRP-Registrierung "
                   "von S2 nicht beim Hub an.",
             fix="Im Keyring KR auf S2 unter `peer ANY` `pre-shared-key DMVPN-Lab-Key`."),
        dict(node="HUB", old=" bgp listen range 172.16.0.0/24 peer-group SPOKES", new=" bgp listen range 172.16.1.0/24 peer-group SPOKES",
             find="`show ip bgp summary` auf S1: Nachbar 172.16.0.1 in *Active*. Auf dem Hub erscheinen keine dynamischen Nachbarn, "
                  "`show running-config | include listen` nennt 172.16.1.0/24. Die Tunneladressen liegen in 172.16.0.0/24.",
             cause="Der Hub nimmt BGP-Verbindungen nur aus dem konfigurierten Bereich an. Die Spokes verbinden sich aus 172.16.0.0/24 "
                   "und werden abgewiesen. Von sich aus baut der Hub keine Sitzung auf, er kennt die Spokes ja nicht.",
             fix="`no bgp listen range 172.16.1.0/24 peer-group SPOKES` und `bgp listen range 172.16.0.0/24 peer-group SPOKES` auf dem Hub."),
        dict(node="HUB", old=" ip nhrp redirect", new=None,
             find="`show ip route nhrp` auf S1 bleibt leer, `show ip nhrp` enthält keinen Eintrag für 10.10.2.0/24. "
                  "`show running-config interface Tunnel0` auf dem Hub: `ip nhrp redirect` fehlt.",
             cause="Ohne Redirect erfahren die Spokes nie, dass es einen direkten Weg gibt. Der Hub leitet weiter und bleibt im Pfad.",
             fix="`ip nhrp redirect` unter Tunnel0 auf dem Hub."),
        dict(node="S1", old=" ip nhrp shortcut", new=None,
             find="Nach Verkehr in beide Richtungen zeigt `show ip route nhrp` auf S2 die Route 10.10.1.0/24 über 172.16.0.2, auf S1 aber "
                  "keine Route zu 10.10.2.0/24. `show running-config interface Tunnel0` auf S1: `ip nhrp shortcut` fehlt.",
             cause="Der Hub schickt S1 einen Redirect, aber ohne `ip nhrp shortcut` stellt S1 keine Auflösungsanfrage und installiert keine "
                   "Shortcut-Route. Auf Anfragen von S2 antwortet S1 trotzdem, deshalb klappt die andere Richtung.",
             fix="`ip nhrp shortcut` unter Tunnel0 auf S1.")],
    verify=["show crypto ikev2 sa", "show crypto ipsec sa", "show dmvpn", "show ip nhrp", "show ip bgp summary", "show ip route nhrp",
            "traceroute 10.10.2.1 source Loopback1   ! auf S1, zweimal"],
    verify_table=[("`show dmvpn` auf dem HUB", "zwei Spokes im Zustand UP"),
                  ("`show crypto ikev2 sa` auf S1", "SA zum Hub im Status READY, nach Spoke-Verkehr auch zu 198.51.100.9"),
                  ("`show ip bgp summary` auf dem HUB", "zwei dynamische Nachbarn (mit `*`) mit je einem Präfix"),
                  ("`show ip route nhrp` auf S1", "10.10.2.0/24 über 172.16.0.3 nach dem ersten Traceroute")],
    caveat=("IOSv verschlüsselt in Software, für Pings und Traceroutes reicht das. `ip nhrp nhs … nbma … multicast` und "
            "`keyring local` brauchen IOS 15.2 oder neuer. Die Meldungen von `debug crypto ikev2` unterscheiden sich je nach Version im Wortlaut."),
    teilc=[("Warum stört ein fehlendes `ip nhrp map multicast dynamic` auf dem Hub in diesem Lab nicht, mit OSPF oder EIGRP über DMVPN aber schon?",
            "**BGP läuft per Unicast über TCP.** OSPF und EIGRP schicken ihre Hellos an Multicast-Adressen. Ohne Multicast-Zuordnung "
            "erreichen die Hellos des Hubs die Spokes nicht, und es entsteht keine Nachbarschaft."),
           ("Welche Rolle spielt `ip nhrp network-id`, und muss sie auf allen Routern gleich sein?",
            "**Sie ist nur lokal bedeutsam.** Sie ordnet ein Tunnel-Interface einer NHRP-Instanz zu. Unterschiedliche Werte auf Hub und "
            "Spokes stören nicht; gleiche Werte auf zwei Tunneln desselben Routers würden sie zu einem NHRP-Netz zusammenführen."),
           ("Wie begrenzt du das Risiko, wenn der Hub BGP-Sitzungen aus einem ganzen Bereich annimmt?",
            "**Mit einem engen Bereich, einem Passwort für die Peer-Group und `bgp listen limit`.** Der Hub nimmt jede Verbindung aus dem "
            "Bereich an. `bgp listen limit` begrenzt die Zahl der dynamischen Nachbarn (Standard 100), ein Passwort hält fremde Geräte "
            "fern, die zufällig eine Tunneladresse haben."),
           ("Was ändert sich am Spoke, wenn ein zweiter Hub dazukommt (Dual Hub, Single Cloud)?",
            "**Der Spoke registriert sich bei beiden Hubs und hat zu beiden eine BGP-Sitzung.** Er trägt zwei `ip nhrp nhs`-Zeilen. "
            "Welcher Hub bevorzugt wird, steuerst du per BGP, etwa über Local Preference oder ein kürzeres Aggregat vom primären Hub.")],
    exam=["DMVPN Phase 3: Hub mit `ip nhrp redirect`, Spokes mit `ip nhrp shortcut`; der Hub darf zusammenfassen.",
          "Schutz mit IKEv2: Proposal, Policy, Keyring, Profil, Transform-Set (Transport Mode), IPsec-Profil, `tunnel protection`.",
          "Fehlersuche von unten: Underlay-Ping, `show crypto ikev2 sa`, `show crypto ipsec sa`, `show dmvpn`, Routing, `show ip route nhrp`.",
          "BGP über DMVPN: `bgp listen range` mit Peer-Group, die Sitzung geht immer vom Spoke aus."],
)
