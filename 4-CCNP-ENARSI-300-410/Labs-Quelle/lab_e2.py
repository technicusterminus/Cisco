LAB = dict(
    slug="E2-MPLS-L3VPN", num="E2", title="MPLS L3VPN mit LDP und MP-BGP", minutes=100, level="schwer",
    summary=("Ein kleines Provider-Netz (PE1, P, PE2) verbindet zwei Standorte eines Kunden per MPLS L3VPN: OSPF und LDP im Core, "
             "VRF mit Route Distinguisher und Route Targets auf den PEs, eBGP zu den Kunden-Routern (CE) und VPNv4 zwischen den PEs. "
             "Dazu die typische Fehlersuche, wenn die BGP-Sitzung steht, aber kein Verkehr fließt."),
    goals=["Core-Underlay mit OSPF und LDP aufbauen und Label-Bindings prüfen.",
           "Eine VRF mit RD und Route Targets anlegen und PE-CE-Routing per eBGP in der VRF betreiben.",
           "VPNv4 zwischen den PEs konfigurieren und erklären, was RD und RT jeweils tun.",
           "Mit `show mpls ldp neighbor`, `show vrf detail` und `show bgp vpnv4 unicast all` die Ebene eines Fehlers eingrenzen."],
    tags=[("2.1", "MPLS: Fehlersuche", 23), ("2.2", "MPLS L3VPN: Fehlersuche", 19)],
    diagram="""
 CE1 ─── PE1 ─────── P ─────── PE2 ─── CE2
 AS65001  \\_______ AS 65000 _______/  AS65002
  Lo1 10.100.1.1/24                Lo1 10.100.2.1/24
""",
    nets=[("CE1 Gi0/0 – PE1 Gi0/1", "192.168.1.0/30 (PE1 .1, CE1 .2), in der VRF CUST-A"),
          ("PE1 Gi0/0 – P Gi0/0", "10.0.12.0/30 (.1/.2)"),
          ("P Gi0/1 – PE2 Gi0/0", "10.0.23.0/30 (.1/.2)"),
          ("PE2 Gi0/1 – CE2 Gi0/0", "192.168.2.0/30 (PE2 .1, CE2 .2), in der VRF CUST-A"),
          ("Loopback0", "PE1 10.255.0.1/32, P 10.255.0.2/32, PE2 10.255.0.3/32"),
          ("Kunden-LANs (Loopback1)", "CE1 10.100.1.0/24, CE2 10.100.2.0/24")],
    topo_text=("Der Provider ist AS 65000, die Kunden-Router CE1 und CE2 sind AS 65001 und 65002. Die Interfaces zu den CEs stehen in der "
               "Ausgangslage **ohne IP-Adresse**: Erst kommt `vrf forwarding`, dann die Adresse, sonst löscht IOS die Adresse wieder. "
               "Der P-Router führt nur Core-Routen und Labels, kein BGP und keine VRF."),
    steps=[
        dict(t="Core-Underlay mit OSPF.", body="Auf PE1, P und PE2: `router ospf 1` mit `router-id` gleich Loopback0 und `network`-Anweisungen für die Loopback0-/32 und die Core-Links in Area 0.",
             check="`show ip route ospf` auf PE1 enthält 10.255.0.2/32 und 10.255.0.3/32. `ping 10.255.0.3 source Loopback0` geht durch.",
             think="Warum müssen die Loopbacks als /32 im IGP stehen, und was passiert bei einer Summary?"),
        dict(t="LDP einschalten.", body="Auf den Core-Interfaces `mpls ip`, global `mpls label protocol ldp` und `mpls ldp router-id Loopback0 force`.",
             check="`show mpls ldp neighbor` zeigt auf dem P zwei Nachbarn, auf den PEs einen. `show mpls forwarding-table` listet Labels für die Loopbacks.",
             think="Warum läuft die LDP-Sitzung zwischen den Loopbacks (Transport-Adresse) und nicht zwischen den Link-Adressen?"),
        dict(t="VRF auf den PEs anlegen.", body="`vrf definition CUST-A` mit `rd 65000:100` und im `address-family ipv4` `route-target export 65000:100` und `route-target import 65000:100`. Dann am CE-Interface erst `vrf forwarding CUST-A`, danach die IP-Adresse.",
             check="`show vrf` listet CUST-A mit dem Interface. `ping vrf CUST-A 192.168.1.2` geht durch.",
             think="Was passiert mit der IP-Adresse, wenn du `vrf forwarding` nachträglich setzt?"),
        dict(t="PE-CE-Routing mit eBGP.", body="Auf den PEs im `address-family ipv4 vrf CUST-A` den CE als Nachbarn eintragen und aktivieren. Auf den CEs `router bgp` mit dem PE als Nachbar (AS 65000) und `network` für das LAN (Loopback1).",
             check="`show bgp vpnv4 unicast vrf CUST-A summary` auf den PEs: CE-Nachbar Established. Die PE-VRF enthält das Kunden-LAN (`show ip route vrf CUST-A`).",
             think="Warum sitzt der CE-Nachbar im VRF-Address-Family und nicht unter dem globalen BGP?"),
        dict(t="VPNv4 zwischen den PEs.", body="Auf PE1 und PE2: `router bgp 65000`, `no bgp default ipv4-unicast`, Nachbar = Loopback0 des anderen PE (`remote-as 65000`, `update-source Loopback0`). Im `address-family vpnv4` den Nachbarn aktivieren und `send-community extended`.",
             check="`show bgp vpnv4 unicast all summary` zeigt den Nachbarn Established mit empfangenen Präfixen. `show ip route vrf CUST-A` auf PE1 enthält 10.100.2.0/24 als BGP-Route.",
             think="Was unterscheidet Route Distinguisher und Route Target, und warum braucht VPNv4 beide?"),
        dict(t="Ende zu Ende.", body="Auf CE1: `ping 10.100.2.1 source Loopback1` und `traceroute 10.100.2.1 source Loopback1`.",
             check="Der Ping geht durch. Die Traceroute zeigt PE1, P (mit `[MPLS: Label … ]`), PE2, CE2.",
             think="Warum braucht der P-Router keine Routen zu den Kundennetzen, und wie viele Labels trägt das Paket zwischen PE1 und P?")],
    answers=[
        ("1", "LDP vergibt Labels nur für Präfixe, die **exakt** in der Routing-Tabelle stehen. Der BGP-Next-Hop eines VPNv4-Präfixes ist die /32-Loopback des PE. Steht sie nur als Summary (zum Beispiel /24) im IGP, gibt es kein Label für die /32, und der Transport-LSP bricht ab."),
        ("2", "LDP-Hellos laufen auf den Link-Adressen (Multicast 224.0.0.2). Die TCP-Sitzung selbst baut sich zur **Transport-Adresse** auf, standardmäßig die LDP-Router-ID. Mit `router-id Loopback0 force` ist das die stabile Loopback. Sie muss im IGP erreichbar sein, sonst kommt die Sitzung nicht hoch."),
        ("3", "IOS löscht die IP-Adresse eines Interfaces, wenn du `vrf forwarding` setzt oder änderst (Meldung „Removing all IP addresses“). Reihenfolge: erst VRF, dann Adresse."),
        ("4", "Die Kundenroute gehört in die Routing-Tabelle der VRF, nicht in die globale. Der VRF-Address-Family hält pro VRF eine eigene BGP-Tabelle und eigene Nachbarn. Das globale BGP ist für die PE-PE-Sitzung."),
        ("5", "Der **RD** macht ein IPv4-Präfix im Provider-Netz eindeutig (RD + Präfix = VPNv4-Präfix), damit überlappende Kundenadressen nebeneinander existieren. Das **RT** steuert, welche Routen eine VRF exportiert und importiert (Topologie des VPN). Die Eindeutigkeit allein sagt nichts darüber, wer die Route sehen darf."),
        ("6", "Der P-Router schaltet nur nach dem äußeren (Transport-)Label. Er kennt keine Kundenpräfixe. Zwischen PE1 und P trägt das Paket **zwei Labels**: das Transport-Label (für den LSP zu PE2) und das VPN-Label (bestimmt die VRF auf PE2). Wegen Penultimate Hop Popping entfernt der P das Transport-Label, PE2 sieht nur noch das VPN-Label.")],
    nodes=[
        dict(name="CE1", type="router", x=0, y=150,
             base="""
interface GigabitEthernet0/0
 ip address 192.168.1.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.100.1.1 255.255.255.0""",
             sol="""
router bgp 65001
 bgp router-id 10.100.1.1
 neighbor 192.168.1.1 remote-as 65000
 network 10.100.1.0 mask 255.255.255.0"""),
        dict(name="PE1", type="router", x=200, y=150,
             base="""
interface Loopback0
 ip address 10.255.0.1 255.255.255.255
interface GigabitEthernet0/0
 ip address 10.0.12.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 no shutdown""",
             sol="""
vrf definition CUST-A
 rd 65000:100
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:100
 exit-address-family
interface GigabitEthernet0/1
 vrf forwarding CUST-A
 ip address 192.168.1.1 255.255.255.252
router ospf 1
 router-id 10.255.0.1
 network 10.255.0.1 0.0.0.0 area 0
 network 10.0.12.0 0.0.0.3 area 0
mpls label protocol ldp
mpls ldp router-id Loopback0 force
interface GigabitEthernet0/0
 mpls ip
router bgp 65000
 bgp router-id 10.255.0.1
 no bgp default ipv4-unicast
 neighbor 10.255.0.3 remote-as 65000
 neighbor 10.255.0.3 update-source Loopback0
 address-family vpnv4
  neighbor 10.255.0.3 activate
  neighbor 10.255.0.3 send-community extended
 exit-address-family
 address-family ipv4 vrf CUST-A
  neighbor 192.168.1.2 remote-as 65001
  neighbor 192.168.1.2 activate
 exit-address-family"""),
        dict(name="P", type="router", x=400, y=150,
             base="""
interface Loopback0
 ip address 10.255.0.2 255.255.255.255
interface GigabitEthernet0/0
 ip address 10.0.12.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.23.1 255.255.255.252
 no shutdown""",
             sol="""
router ospf 1
 router-id 10.255.0.2
 network 10.255.0.2 0.0.0.0 area 0
 network 10.0.12.0 0.0.0.3 area 0
 network 10.0.23.0 0.0.0.3 area 0
mpls label protocol ldp
mpls ldp router-id Loopback0 force
interface GigabitEthernet0/0
 mpls ip
interface GigabitEthernet0/1
 mpls ip"""),
        dict(name="PE2", type="router", x=600, y=150,
             base="""
interface Loopback0
 ip address 10.255.0.3 255.255.255.255
interface GigabitEthernet0/0
 ip address 10.0.23.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 no shutdown""",
             sol="""
vrf definition CUST-A
 rd 65000:100
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:100
 exit-address-family
interface GigabitEthernet0/1
 vrf forwarding CUST-A
 ip address 192.168.2.1 255.255.255.252
router ospf 1
 router-id 10.255.0.3
 network 10.255.0.3 0.0.0.0 area 0
 network 10.0.23.0 0.0.0.3 area 0
mpls label protocol ldp
mpls ldp router-id Loopback0 force
interface GigabitEthernet0/0
 mpls ip
router bgp 65000
 bgp router-id 10.255.0.3
 no bgp default ipv4-unicast
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 update-source Loopback0
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community extended
 exit-address-family
 address-family ipv4 vrf CUST-A
  neighbor 192.168.2.2 remote-as 65002
  neighbor 192.168.2.2 activate
 exit-address-family"""),
        dict(name="CE2", type="router", x=800, y=150,
             base="""
interface GigabitEthernet0/0
 ip address 192.168.2.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 10.100.2.1 255.255.255.0""",
             sol="""
router bgp 65002
 bgp router-id 10.100.2.1
 neighbor 192.168.2.1 remote-as 65000
 network 10.100.2.0 mask 255.255.255.0""")],
    links=[("CE1", "Gi0/0", "PE1", "Gi0/1"), ("PE1", "Gi0/0", "P", "Gi0/0"),
           ("P", "Gi0/1", "PE2", "Gi0/0"), ("PE2", "Gi0/1", "CE2", "Gi0/0")],
    staggered=True,
    tickets=["Die BGP-Sitzung zwischen PE1 und PE2 kommt nicht hoch; `show bgp vpnv4 unicast all summary` zeigt den Nachbarn dauerhaft in Active oder Idle.",
             "CE2 lernt 10.100.1.0/24 nicht, obwohl PE1 die Route von CE1 hat und die VPNv4-Sitzung steht.",
             "CE1 lernt 10.100.2.0/24 nicht, obwohl PE2 die Route von CE2 hat und die VPNv4-Sitzung steht.",
             "Alle Routen sind da, aber `ping 10.100.2.1 source Loopback1` von CE1 scheitert; die Traceroute zeigt nach PE1 nur noch Sterne.",
             "Die eBGP-Sitzung zwischen CE2 und PE2 steht nicht; CE2 meldet Active, PE2 hat keine Route aus dem Kundennetz."],
    faults=[
        dict(node="PE2", old=" neighbor 10.255.0.1 update-source Loopback0", new=None,
             find="`show bgp vpnv4 unicast all neighbors 10.255.0.1` auf PE2 zeigt als lokale Adresse nicht 10.255.0.3. Auf PE1 steht der Nachbar 10.255.0.3 in Active: PE1 erwartet die Verbindung von der Loopback-Adresse.",
             cause="PE2 baut die TCP-Verbindung mit der Adresse des ausgehenden Interfaces (10.0.23.2) auf. PE1 kennt als Nachbar aber 10.255.0.3 und lehnt die Quelle ab. `update-source Loopback0` fehlt.",
             fix="`neighbor 10.255.0.1 update-source Loopback0` auf PE2."),
        dict(node="PE1", old="  route-target export 65000:100", new=None,
             find="`show bgp vpnv4 unicast all 10.100.1.0/24` auf PE1 zeigt die Route ohne `Extended Community: RT:…`. `show vrf detail CUST-A` führt keinen Export-RT auf.",
             cause="Die VRF auf PE1 exportiert kein Route Target. Die Route geht ohne RT an PE2, dort importiert keine VRF sie (Route-Target-Filter).",
             fix="`route-target export 65000:100` im `address-family ipv4` der VRF auf PE1."),
        dict(node="PE1", old="  route-target import 65000:100", new="  route-target import 65000:101",
             find="`show vrf detail CUST-A` auf PE1 zeigt Import-RT 65000:101. PE2 exportiert mit 65000:100 (`show bgp vpnv4 unicast all 10.100.2.0/24` auf PE2).",
             cause="Der Import-RT auf PE1 stimmt nicht mit dem Export-RT von PE2 überein. PE1 verwirft die Routen von PE2 schon beim Eingang.",
             fix="`route-target import 65000:100` auf PE1."),
        dict(node="P", old=" mpls ip", new=None, nth=1,
             find="`show mpls ldp neighbor` auf dem P zeigt nur PE1, nicht PE2. `show mpls interfaces` listet Gi0/1 nicht. Die BGP-Sitzung steht, weil sie über das IGP läuft.",
             cause="Auf dem P-Interface zu PE2 fehlt `mpls ip`. Ohne LDP-Sitzung gibt es zwischen P und PE2 kein Label, der Transport-LSP ist an dieser Stelle unterbrochen. IP-Routing und BGP laufen weiter, die Kundenpakete (mit Label) nicht. Die ICMP-Antworten des P-Routers laufen ebenfalls durch den unterbrochenen LSP, deshalb zeigt die Traceroute hinter PE1 nur Sterne.",
             fix="`mpls ip` unter Gi0/1 auf dem P."),
        dict(node="CE2", old=" neighbor 192.168.2.1 remote-as 65000", new=" neighbor 192.168.2.1 remote-as 65100",
             find="`show ip bgp summary` auf CE2: Nachbar 192.168.2.1 in Idle/Active. `show ip bgp neighbors 192.168.2.1` nennt das erwartete Remote-AS 65100. Das Log meldet „bad peer AS“.",
             cause="CE2 erwartet beim PE das AS 65100, der PE sendet 65000. Die Sitzung wird mit einer Notification abgebrochen.",
             fix="`neighbor 192.168.2.1 remote-as 65000` auf CE2.")],
    verify=["show mpls ldp neighbor", "show mpls interfaces", "show mpls forwarding-table", "show vrf detail CUST-A",
            "show bgp vpnv4 unicast all summary", "show bgp vpnv4 unicast all", "show ip route vrf CUST-A",
            "show ip cef vrf CUST-A 10.100.2.0", "traceroute 10.100.2.1 source Loopback1     ! von CE1"],
    verify_table=[("`show mpls ldp neighbor` auf dem P", "zwei Nachbarn (10.255.0.1 und 10.255.0.3), State: Oper"),
                  ("`show bgp vpnv4 unicast all summary` auf PE1", "10.255.0.3 mit Zahl im Feld State/PfxRcd (nicht Active)"),
                  ("`show ip route vrf CUST-A` auf PE1", "10.100.1.0/24 über BGP vom CE1, 10.100.2.0/24 über BGP vom PE2 (10.255.0.3)"),
                  ("`traceroute` von CE1 nach 10.100.2.1", "PE1, P mit `[MPLS: Label …]`, PE2, CE2")],
    teilc=[("Die VPNv4-Sitzung steht und beide PEs haben die Routen, aber der Ping zwischen den CEs scheitert. Was prüfst du?",
            "**Den Transport-LSP.** BGP steht über das IGP, Pakete der VPN brauchen aber Labels. `show mpls ldp neighbor` auf jedem Core-Router, `show mpls forwarding-table` und `show ip cef <Loopback des Ziel-PE>` (Label vorhanden?), `traceroute` und `show mpls interfaces`. Meist fehlt `mpls ip` an einem Interface oder ein LDP-Nachbar."),
           ("Zwei Kunden nutzen beide 10.1.1.0/24. Was sorgt dafür, dass VPNv4 beide Präfixe unterscheiden kann, und was, dass sie sich nicht mischen?",
            "**Der RD macht sie eindeutig, die RTs trennen sie.** Mit unterschiedlichen RDs sind es zwei verschiedene VPNv4-Präfixe. Mit unterschiedlichen RTs importiert jede VRF nur die Routen ihres Kunden."),
           ("Was ändert sich, wenn die PEs über einen Route Reflector sprechen sollen, der selbst keine VRF hat?",
            "**Der RR muss die VPNv4-Routen ohne Import-RT behalten.** Normalerweise verwirft ein Router VPNv4-Routen, deren RT keine lokale VRF importiert (`bgp default route-target filter`). Ein RR braucht deshalb `no bgp default route-target filter`, damit er alle Routen annimmt und weitergibt.")],
    exam=["Reihenfolge der Fehlersuche: IGP → LDP → BGP VPNv4 → VRF (RD/RT) → PE-CE-Routing.",
          "Typisch: BGP-Sitzung steht, Ping scheitert → Transport-LSP (LDP, `mpls ip`, /32 im IGP) prüfen.",
          "RT-Filter: Ohne passenden Import-RT landet eine VPNv4-Route nicht in der VRF (und wird ohne `no bgp default route-target filter` nicht einmal gehalten).",
          "VPNv4 braucht `send-community extended`, sonst gehen die RTs verloren.",
          "Zwei Labels im Core: Transport (LDP) außen, VPN-Label (MP-BGP) innen; PHP entfernt das äußere Label am vorletzten Hop."],
)
