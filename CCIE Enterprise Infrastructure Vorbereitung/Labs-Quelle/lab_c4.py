LAB = dict(
    slug="C4-L3VPN-Shared-Services", num="C4", title="MPLS L3VPN: Shared Services, AS-Override und Route-Target-Design",
    minutes=110, level="schwer",
    summary=("Ein Provider verbindet zwei Standorte von Kunde A, die beide AS 65100 nutzen, und stellt einen Shared-Services-Server "
             "bereit, den Kunde A und Kunde B erreichen dürfen. Untereinander müssen A und B getrennt bleiben. Du entwirfst die Route "
             "Targets so, dass genau das herauskommt, und löst das Problem mit dem gleichen Kunden-AS per `as-override`. Core, LDP "
             "und die VPNv4-Sitzung sind vorgegeben."),
    goals=["Ein Route-Target-Design für Shared Services entwerfen: wer exportiert was, wer importiert was.",
           "Erklären, warum importierte Routen nicht weiter exportiert werden und Kunden deshalb getrennt bleiben.",
           "PE-CE-eBGP mit gleichem Kunden-AS an mehreren Standorten per `as-override` lösen.",
           "VPN-Fehler mit `show bgp vpnv4 unicast all <Präfix>` am Route Target festmachen."],
    tags=[("3.2.a", "MPLS und LDP", 8), ("3.2.b", "MPLS L3VPN", 11)],
    diagram="""
  CEA1  AS 65100                                                CEA2  AS 65100
  Lo1 10.100.1.1/24                                             Lo1 10.100.2.1/24
    | Gi0/0                                                       | Gi0/0
    | Gi0/1  VRF A                                       VRF A    | Gi0/1
   PE1  AS 64500  Gi0/0 ------------- MPLS ------------- Gi0/0  PE2  AS 64500
   Lo0 10.255.0.1                                               Lo0 10.255.0.2
   Lo10 10.110.1.1/24 = LAN von Kunde B (VRF B)                   | Gi0/2  VRF SHARED
                                                                  | Gi0/0
                                                                CES  AS 65200
                                                                Lo1 10.200.0.1/24 = Shared Services
""",
    nets=[("PE1 Gi0/0 – PE2 Gi0/0 (Core, OSPF und LDP)", "10.0.12.0/30 (.1/.2)"),
          ("PE1 Gi0/1 – CEA1 Gi0/0 (VRF A)", "192.168.11.0/30 (PE .1, CE .2)"),
          ("PE2 Gi0/1 – CEA2 Gi0/0 (VRF A)", "192.168.12.0/30 (PE .1, CE .2)"),
          ("PE2 Gi0/2 – CES Gi0/0 (VRF SHARED)", "192.168.13.0/30 (PE .1, CE .2)"),
          ("Kundennetze", "A: 10.100.1.0/24 und 10.100.2.0/24, B: 10.110.1.0/24 (Loopback10 auf PE1), Shared: 10.200.0.0/24")],
    topo_text=("Vorgegeben sind OSPF und LDP im Core sowie die iBGP-Sitzung für VPNv4 zwischen PE1 und PE2. Kunde B hat in diesem "
               "Lab keinen eigenen Router: Loopback10 auf PE1 in VRF B steht für sein LAN. Das Route-Target-Schema: Kunde A 64500:100, "
               "Kunde B 64500:200, Shared Services 64500:999."),
    steps=[
        dict(t="Core prüfen.", body="`show mpls ldp neighbor` und `show bgp vpnv4 unicast all summary` auf beiden PEs.",
             check="LDP-Nachbar und VPNv4-Sitzung stehen, noch ohne Präfixe.",
             think="PE1 und PE2 sind direkt verbunden. Wie viele Labels trägt ein VPN-Paket auf dem Link zwischen ihnen?"),
        dict(t="VRF A.",
             body="Auf PE1 und PE2 `vrf definition A` mit `rd 64500:100` und unter `address-family ipv4` Export und Import 64500:100. "
                  "Hänge das CE-Interface in die VRF: `vrf forwarding A`, danach die IP-Adresse (PE1 192.168.11.1/30, PE2 192.168.12.1/30).",
             check="`show vrf` zeigt A mit dem CE-Interface, `ping vrf A 192.168.11.2` von PE1 klappt.",
             think="Warum musst du die IP-Adresse nach `vrf forwarding` neu setzen?"),
        dict(t="PE-CE mit eBGP.",
             body="CEA1 und CEA2: `router bgp 65100`, Loopback1-Netz per `network`, Nachbar ist der PE mit `remote-as 64500`. "
                  "PE1 und PE2: unter `router bgp 64500` → `address-family ipv4 vrf A` den CE mit `remote-as 65100` eintragen und aktivieren.",
             check="PE1 kennt in VRF A beide Kundennetze (`show ip route vrf A`). CEA2 kennt 10.100.1.0/24 aber **nicht**.",
             think="Warum fehlt das Netz auf CEA2, obwohl PE2 es in der VRF hat?"),
        dict(t="AS-Override.", body="Auf PE1 und PE2 `neighbor … as-override` für den jeweiligen CE.",
             check="CEA2 hat 10.100.1.0/24 mit dem AS-Pfad `64500 64500`. `ping 10.100.1.1 source Loopback1` von CEA2 klappt.",
             think="Welche Gefahr entsteht durch `as-override`, wenn ein Standort an zwei PEs hängt, und was hilft dagegen?"),
        dict(t="Shared Services.",
             body="PE2: `vrf definition SHARED` mit `rd 64500:999`, Export 64500:999, Import 64500:999, 64500:100 und 64500:200. "
                  "Gi0/2 in SHARED (192.168.13.1/30), eBGP zu CES (AS 65200). CES: `router bgp 65200`, kündigt 10.200.0.0/24 an. "
                  "In VRF A auf beiden PEs zusätzlich `route-target import 64500:999`.",
             check="CEA1 und CEA2 erreichen 10.200.0.1. CES kennt 10.100.1.0/24 und 10.100.2.0/24.",
             think="SHARED importiert die Netze von Kunde A. Warum landen sie trotzdem nicht bei Kunde B?"),
        dict(t="Kunde B.",
             body="PE1: `vrf definition B` mit `rd 64500:200`, Export und Import 64500:200 und Import 64500:999. `interface Loopback10` "
                  "mit `vrf forwarding B` und 10.110.1.1/24, unter `address-family ipv4 vrf B` `redistribute connected`.",
             check="`ping vrf B 10.200.0.1 source Loopback10` auf PE1 klappt. CEA1 hat keine Route zu 10.110.1.0/24.",
             think="Was müsste gelten, damit Kunde A und Kunde B dieselben privaten Adressen nutzen dürfen?")],
    answers=[
        ("1", "**Nur eins, das VPN-Label.** PE2 vergibt für seine Loopback implicit-null, deshalb entfernt PE1 als vorletzter Hop das "
              "Transport-Label (Penultimate Hop Popping). Mit einem P-Router dazwischen stünden auf dem ersten Link zwei Labels im Paket."),
        ("2", "**Weil `vrf forwarding` alle IP-Adressen vom Interface entfernt**, sie gehören danach in eine andere Routing-Tabelle. "
              "IOS meldet das auch. Deshalb immer erst die VRF, dann die Adresse."),
        ("3", "**Weil der AS-Pfad 65100 enthält, den AS von CEA2.** PE2 gibt die Route mit `64500 65100` weiter, CEA2 verwirft sie wegen "
              "des eigenen AS. Das ist derselbe Schleifenschutz wie im Internet."),
        ("4", "**Es kann eine Schleife entstehen.** Eine Route von Standort 1 geht über den ersten PE ins VPN und kommt über den zweiten "
              "PE zu Standort 1 zurück; weil 65100 ersetzt wurde, erkennt der CE sie nicht. Abhilfe ist Site of Origin (SoO): Der PE "
              "markiert die Routen eines Standorts und schickt sie nicht an einen Nachbarn mit derselben Markierung zurück."),
        ("5", "**Weil ein PE das Export-RT einer VRF nur an Routen hängt, die in dieser VRF entstanden sind.** Importierte Routen "
              "behalten ihre RTs und werden nicht neu exportiert. Kunde B importiert 64500:200 und 64500:999, aber nicht 64500:100."),
        ("6", "**Sie dürfen sich nicht in dem überschneiden, was SHARED importiert.** Der Shared-Server braucht eindeutige Ziele für "
              "seine Antworten. Überlappende Kundennetze gehen nur mit NAT vor den Shared Services oder mit getrennten Shared-VRFs pro Kunde.")],
    nodes=[
        dict(name="CEA1", type="router", x=50, y=100,
             base="""
interface GigabitEthernet0/0
 ip address 192.168.11.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.100.1.1 255.255.255.0""",
             sol="""
router bgp 65100
 bgp router-id 10.100.1.1
 bgp log-neighbor-changes
 network 10.100.1.0 mask 255.255.255.0
 neighbor 192.168.11.1 remote-as 64500"""),
        dict(name="PE1", type="router", x=250, y=250,
             base="""
interface Loopback0
 ip address 10.255.0.1 255.255.255.255
interface GigabitEthernet0/0
 ip address 10.0.12.1 255.255.255.252
 mpls ip
 no shutdown
interface GigabitEthernet0/1
 no shutdown
mpls label protocol ldp
mpls ldp router-id Loopback0 force
router ospf 1
 router-id 10.255.0.1
 network 10.255.0.1 0.0.0.0 area 0
 network 10.0.12.0 0.0.0.3 area 0
router bgp 64500
 bgp router-id 10.255.0.1
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 10.255.0.2 remote-as 64500
 neighbor 10.255.0.2 update-source Loopback0
 address-family vpnv4
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.2 send-community extended
 exit-address-family""",
             sol="""
vrf definition A
 rd 64500:100
 address-family ipv4
  route-target export 64500:100
  route-target import 64500:100
  route-target import 64500:999
 exit-address-family
vrf definition B
 rd 64500:200
 address-family ipv4
  route-target export 64500:200
  route-target import 64500:200
  route-target import 64500:999
 exit-address-family
interface GigabitEthernet0/1
 vrf forwarding A
 ip address 192.168.11.1 255.255.255.252
interface Loopback10
 vrf forwarding B
 ip address 10.110.1.1 255.255.255.0
router bgp 64500
 address-family ipv4 vrf A
  neighbor 192.168.11.2 remote-as 65100
  neighbor 192.168.11.2 activate
  neighbor 192.168.11.2 as-override
 exit-address-family
 address-family ipv4 vrf B
  redistribute connected
 exit-address-family"""),
        dict(name="PE2", type="router", x=550, y=250,
             base="""
interface Loopback0
 ip address 10.255.0.2 255.255.255.255
interface GigabitEthernet0/0
 ip address 10.0.12.2 255.255.255.252
 mpls ip
 no shutdown
interface GigabitEthernet0/1
 no shutdown
interface GigabitEthernet0/2
 no shutdown
mpls label protocol ldp
mpls ldp router-id Loopback0 force
router ospf 1
 router-id 10.255.0.2
 network 10.255.0.2 0.0.0.0 area 0
 network 10.0.12.0 0.0.0.3 area 0
router bgp 64500
 bgp router-id 10.255.0.2
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 neighbor 10.255.0.1 remote-as 64500
 neighbor 10.255.0.1 update-source Loopback0
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community extended
 exit-address-family""",
             sol="""
vrf definition A
 rd 64500:100
 address-family ipv4
  route-target export 64500:100
  route-target import 64500:100
  route-target import 64500:999
 exit-address-family
vrf definition SHARED
 rd 64500:999
 address-family ipv4
  route-target export 64500:999
  route-target import 64500:999
  route-target import 64500:100
  route-target import 64500:200
 exit-address-family
interface GigabitEthernet0/1
 vrf forwarding A
 ip address 192.168.12.1 255.255.255.252
interface GigabitEthernet0/2
 vrf forwarding SHARED
 ip address 192.168.13.1 255.255.255.252
router bgp 64500
 address-family ipv4 vrf A
  neighbor 192.168.12.2 remote-as 65100
  neighbor 192.168.12.2 activate
  neighbor 192.168.12.2 as-override
 exit-address-family
 address-family ipv4 vrf SHARED
  neighbor 192.168.13.2 remote-as 65200
  neighbor 192.168.13.2 activate
 exit-address-family"""),
        dict(name="CEA2", type="router", x=750, y=100,
             base="""
interface GigabitEthernet0/0
 ip address 192.168.12.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.100.2.1 255.255.255.0""",
             sol="""
router bgp 65100
 bgp router-id 10.100.2.1
 bgp log-neighbor-changes
 network 10.100.2.0 mask 255.255.255.0
 neighbor 192.168.12.1 remote-as 64500"""),
        dict(name="CES", type="router", x=750, y=400,
             base="""
interface GigabitEthernet0/0
 ip address 192.168.13.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.200.0.1 255.255.255.0""",
             sol="""
router bgp 65200
 bgp router-id 10.200.0.1
 bgp log-neighbor-changes
 network 10.200.0.0 mask 255.255.255.0
 neighbor 192.168.13.1 remote-as 64500""")],
    links=[("CEA1", "Gi0/0", "PE1", "Gi0/1"), ("PE1", "Gi0/0", "PE2", "Gi0/0"), ("PE2", "Gi0/1", "CEA2", "Gi0/0"),
           ("PE2", "Gi0/2", "CES", "Gi0/0")],
    staggered=True,
    tickets=["PE1 lernt von CEA1 kein einziges Präfix, obwohl die BGP-Sitzung steht.",
             "CEA2 erreicht das Netz von CEA1 (10.100.1.0/24) nicht.",
             "CEA1 hat keine Route zu 10.100.2.0/24, und auch der Shared-Server CES kennt das Netz von CEA2 nicht.",
             "CEA1 erreicht den Shared-Server 10.200.0.1 nicht, CEA2 schon.",
             "Kunde B erreicht den Shared-Server nicht: `ping vrf B 10.200.0.1 source Loopback10` auf PE1 scheitert, obwohl PE1 "
             "in VRF B eine Route zu 10.200.0.0/24 hat."],
    faults=[
        dict(node="CEA1", old=" network 10.100.1.0 mask 255.255.255.0", new=" network 10.100.1.0 mask 255.255.0.0",
             find="`show bgp vpnv4 unicast vrf A summary` auf PE1: Nachbar 192.168.11.2 mit 0 empfangenen Präfixen. Auf CEA1 steht "
                  "`network 10.100.1.0 mask 255.255.0.0`, in der Routing-Tabelle gibt es aber nur 10.100.1.0/24. `show ip bgp` auf CEA1 "
                  "ist leer.",
             cause="Falsche Maske im `network`-Befehl. BGP kündigt ein `network` nur an, wenn genau dieses Präfix mit dieser Maske in "
                   "der Routing-Tabelle steht.",
             fix="`no network 10.100.1.0 mask 255.255.0.0` und `network 10.100.1.0 mask 255.255.255.0` auf CEA1."),
        dict(node="PE2", old="  neighbor 192.168.12.2 as-override", new=None,
             find="`show ip bgp` auf CEA2 enthält 10.100.1.0/24 nicht. PE2 sendet es mit dem Pfad `64500 65100` "
                  "(`show bgp vpnv4 unicast vrf A neighbors 192.168.12.2 advertised-routes`), CEA2 sieht den eigenen AS und verwirft es. "
                  "Auf PE2 fehlt `as-override` für 192.168.12.2.",
             cause="Beide Standorte nutzen AS 65100. Ohne `as-override` steht 65100 im AS-Pfad, und der eBGP-Schleifenschutz von CEA2 greift.",
             fix="`neighbor 192.168.12.2 as-override` unter `address-family ipv4 vrf A` auf PE2."),
        dict(node="PE2", old="  route-target export 64500:100", new="  route-target export 64500:101",
             find="`show bgp vpnv4 unicast all 10.100.2.0` auf PE2 zeigt das Präfix mit dem Extended Community RT:64500:101. "
                  "PE1 und die VRF SHARED importieren 64500:100.",
             cause="Falsches Export-RT in VRF A auf PE2. Die Route verlässt die VRF mit 64500:101, und niemand importiert dieses RT, "
                   "weder PE1 noch die lokale VRF SHARED.",
             fix="`no route-target export 64500:101` und `route-target export 64500:100` in VRF A auf PE2."),
        dict(node="PE1", old="  route-target import 64500:999", new=None, nth=0,
             find="`show ip route vrf A 10.200.0.0` auf PE1: keine Route. `show bgp vpnv4 unicast all 10.200.0.0` auf PE1 zeigt das "
                  "Präfix mit RT:64500:999, übernommen aber nur in VRF B. `show vrf detail A` auf PE1: Import nur 64500:100.",
             cause="VRF A auf PE1 importiert das Route Target der Shared Services nicht. Der Server kündigt richtig an, PE1 übernimmt "
                   "die Route nur nicht in VRF A.",
             fix="`route-target import 64500:999` unter `vrf definition A` → `address-family ipv4` auf PE1."),
        dict(node="PE2", old="  route-target import 64500:200", new=None,
             find="Hin geht es, zurück nicht: `show ip bgp` auf CES enthält 10.110.1.0/24 nicht. `show vrf detail SHARED` auf PE2 "
                  "zeigt die Imports 64500:999 und 64500:100, 64500:200 fehlt.",
             cause="Shared Services muss die Netze aller berechtigten Kunden importieren, sonst fehlt der Rückweg. Typisch für einseitige "
                   "Fehler: Die Route zum Server ist da, die Antwort findet nicht zurück.",
             fix="`route-target import 64500:200` in der VRF SHARED auf PE2.")],
    verify=["show mpls ldp neighbor", "show bgp vpnv4 unicast all summary", "show bgp vpnv4 unicast all", "show bgp vpnv4 unicast all 10.200.0.0",
            "show ip route vrf A", "show ip route vrf SHARED", "show vrf detail",
            "ping 10.200.0.1 source Loopback1           ! auf CEA1 und CEA2",
            "ping vrf B 10.200.0.1 source Loopback10    ! auf PE1"],
    verify_table=[("`show ip route vrf A` auf PE1", "10.100.1.0/24 vom CE, 10.100.2.0/24 und 10.200.0.0/24 über 10.255.0.2"),
                  ("`show ip bgp` auf CEA2", "10.100.1.0/24 mit AS-Pfad `64500 64500`, 10.200.0.0/24 mit `64500 65200`"),
                  ("`show ip bgp` auf CES", "10.100.1.0/24, 10.100.2.0/24 und 10.110.1.0/24"),
                  ("`ping 10.110.1.1 source Loopback1` auf CEA1", "scheitert: Kunde A und Kunde B bleiben getrennt")],
    teilc=[("Wann nimmst du beim PE-CE-Routing `allowas-in` auf dem CE statt `as-override` auf dem PE?",
            "**Wenn der Provider-Router nicht angefasst werden kann oder soll.** `allowas-in` ist Sache des Kunden, `as-override` Sache "
            "des Providers. Beide schwächen den Schleifenschutz; bei mehrfach angebundenen Standorten gehört SoO dazu."),
           ("Wofür braucht es die RD, wenn doch das RT über den Import entscheidet?",
            "**Die RD macht Präfixe in VPNv4 eindeutig, das RT steuert Import und Export.** Zwei Kunden mit 10.1.0.0/24 werden durch "
            "unterschiedliche RDs zu zwei verschiedenen VPNv4-Präfixen. Unterschiedliche RDs pro PE für dieselbe VRF erlauben zudem "
            "Multipath über mehrere PEs, weil ein Route Reflector sonst nur den besten Pfad weitergibt."),
           ("Ein PE, der kein Route Reflector ist, verwirft VPNv4-Routen, deren RT er nicht importiert. Was passiert, wenn du später ein Import-RT ergänzt?",
            "**Er fordert die Routen per Route Refresh neu an.** Die automatische Route-Target-Filterung spart Speicher; nach einer neuen "
            "Import-Regel holt IOS die fehlenden Routen selbst nach, ein Reset der Sitzung ist nicht nötig."),
           ("PE-CE mit OSPF statt BGP: Warum erscheinen die Netze von Standort 1 an Standort 2 als O IA und nicht als O E2, und wozu dient ein Sham Link?",
            "**Weil der PE OSPF-Routen aus derselben OSPF-Domäne (gleiche Domain-ID) als Inter-Area-Routen (Typ 3) einspeist.** Gibt es "
            "zusätzlich einen Backdoor-Link zwischen den Standorten in derselben Area, gewinnt dieser als Intra-Area-Route immer. Ein "
            "Sham Link zwischen den PEs macht den Weg über das VPN zu einem Intra-Area-Link, dann entscheiden die Kosten.")],
    exam=["RD macht Präfixe eindeutig, RT steuert Import und Export. Shared Services: zusätzliche Import-RTs auf beiden Seiten.",
          "Importierte Routen werden nicht neu exportiert, deshalb bleiben Kunden trotz gemeinsamer Shared-VRF getrennt.",
          "Gleicher Kunden-AS an mehreren Standorten: `as-override` (PE) oder `allowas-in` (CE), bei Mehrfachanbindung mit SoO.",
          "Fehlersuche Schicht für Schicht: IGP und LDP, VPNv4-Sitzung, RTs (`show bgp vpnv4 unicast all <Präfix>`), VRF-Routing, PE-CE."],
)
