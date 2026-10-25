LAB = dict(
    slug="E5-DHCP-Relay", num="E5", title="DHCP-Server und DHCP-Relay über mehrere Router", minutes=75, level="mittel",
    summary=("Ein zentraler DHCP-Server (R2) versorgt zwei LANs hinter zwei Relay-Routern. Du baust Pools, Ausschlüsse und "
             "`ip helper-address` auf, verfolgst den Ablauf mit `debug ip dhcp server packet` und lernst, wie giaddr den Pool bestimmt, "
             "warum der Server eine Route zum Relay braucht und was Option 82 ändert."),
    goals=["Einen DHCP-Server mit Pools, ausgeschlossenen Adressen und Optionen konfigurieren.",
           "Auf einem Router `ip helper-address` setzen und die Rolle von giaddr bei der Pool-Auswahl erklären.",
           "Den DHCP-Ablauf (Discover, Offer, Request, Ack) mit Debug und Bindings nachvollziehen.",
           "Typische Fehler (Relay fehlt, falscher Server, falscher Pool, Ausschluss, fehlende Rückroute) am Symptom erkennen."],
    tags=[("4.4", "DHCP: Fehlersuche", 20)],
    diagram="""
   H1 ── R1 ── R2 (DHCP-Server) ── R3 ── H2
   LAN1       10.0.12.0/30   10.0.23.0/30      LAN2
 10.1.1.0/24                                 10.1.2.0/24
""",
    nets=[("H1 – R1 Gi0/0", "10.1.1.0/24 (R1 .1, Clients per DHCP)"),
          ("R1 Gi0/1 – R2 Gi0/0", "10.0.12.0/30 (.1/.2)"),
          ("R2 Gi0/1 – R3 Gi0/0", "10.0.23.0/30 (R2 .1, R3 .2)"),
          ("R3 Gi0/1 – H2", "10.1.2.0/24 (R3 .1, Clients per DHCP)")],
    topo_text=("R2 ist der DHCP-Server für beide LANs, R1 und R3 sind Relay-Router. R1 und R3 haben eine Default-Route zu R2, R2 hat statische Routen zu den "
               "beiden LANs. H1 und H2 sind IOS-Geräte mit `ip address dhcp` am Gi0/0 und noch ohne Adresse. Ziel: H1 bekommt eine Adresse "
               "aus 10.1.1.0/24, H2 aus 10.1.2.0/24, jeweils mit Gateway, DNS-Server und Domäne."),
    steps=[
        dict(t="Ausgangslage prüfen.", body="Auf H1: `show ip interface brief`. Auf R2: `ping 10.1.1.1` und `ping 10.1.2.1`.",
             check="H1 hat keine Adresse (unassigned). Die Pings von R2 zu den Relay-Adressen gehen durch.",
             think="Warum kann H1 ohne Relay nie einen Server in einem anderen Netz erreichen?"),
        dict(t="Server konfigurieren.", body="Auf R2: `ip dhcp excluded-address 10.1.1.1 10.1.1.10` (und für 10.1.2.1–10.1.2.10), dann die Pools `LAN1` und `LAN2` mit `network`, `default-router`, `dns-server 192.0.2.53`, `domain-name lab.example` und `lease 0 8`.",
             check="`show ip dhcp pool` listet beide Pools mit Netz und 0 Leases.",
             think="Warum schließt man Adressen aus, statt den Pool kleiner zu machen?"),
        dict(t="Relay auf R1.", body="Unter Gi0/0 (LAN-Seite) von R1: `ip helper-address 10.0.12.2`. Auf H1: `shutdown`, `no shutdown`.",
             check="H1 bekommt 10.1.1.11 mit Gateway 10.1.1.1. `show ip dhcp binding` auf R2 listet den Eintrag.",
             think="Welche Adresse trägt R1 als giaddr in das weitergeleitete Paket ein, und was macht R2 damit?"),
        dict(t="Relay auf R3.", body="Unter Gi0/1 von R3: `ip helper-address 10.0.23.1`. Auf H2 das Interface aus- und einschalten.",
             check="H2 bekommt 10.1.2.11 mit Gateway 10.1.2.1.",
             think="Welche Adressen von R2 könntest du auf R3 als Helper eintragen, und welche ist die sauberste Wahl?"),
        dict(t="Ablauf beobachten.", body="Auf R2: `debug ip dhcp server packet`. Auf H1 das Interface aus- und einschalten.",
             check="Du siehst DHCPDISCOVER, DHCPOFFER, DHCPREQUEST und DHCPACK mit giaddr 10.1.1.1. Schalte das Debugging danach mit `undebug all` aus.",
             think="Welche der vier Nachrichten sind Broadcasts, und wer macht aus dem Broadcast einen Unicast?"),
        dict(t="Option 82.", body="Setze testweise auf R1 unter Gi0/0 `ip dhcp relay information option`.",
             check="Der Client bekommt weiterhin eine Adresse. Auf R2 zeigt `debug ip dhcp server packet` die zusätzlichen Informationen.",
             think="Was passiert, wenn ein Switch mit DHCP Snooping Option 82 einfügt und der Router sie als Relay oder Server erhält? Was ändert `ip dhcp relay information trusted`?")],
    answers=[
        ("1", "Ein DHCPDISCOVER ist ein Broadcast (255.255.255.255) und endet am Router. Das Relay wandelt ihn in einen Unicast an den Server um."),
        ("2", "Ausschlüsse halten Adressen für statische Geräte (Gateway, Drucker, Server) frei, ohne das Netz des Pools zu zerstückeln. Der Pool bleibt ein zusammenhängendes Netz, das Verwalten ist übersichtlicher."),
        ("3", "R1 trägt die IP-Adresse des Interfaces ein, an dem die Anfrage ankam (10.1.1.1), als **giaddr**. R2 wählt anhand von giaddr den passenden Pool (10.1.1.0/24) und schickt Offer und Ack als Unicast an giaddr zurück. Dafür braucht R2 eine Route dorthin."),
        ("4", "Jede Adresse von R2, die R3 erreicht, funktioniert: 10.0.23.1 (am direkten Link) oder 10.0.12.2 (über die Default-Route zu R2). Am saubersten ist eine Loopback-Adresse des Servers, die auch bei einem Link-Ausfall erreichbar bleibt. Hier nimmt das Lab die direkte Adresse 10.0.23.1."),
        ("5", "Discover und (je nach Client-Zustand) Request sind Broadcasts im LAN, das Relay macht daraus Unicasts an den Server. Offer und Ack gehen vom Server unicast an giaddr, das Relay liefert sie im LAN an den Client (Unicast oder Broadcast, je nach Broadcast-Flag des Clients)."),
        ("6", "Option 82 (Relay Agent Information) trägt zum Beispiel Switch und Port. Fügt ein Snooping-Switch sie ein, hat das Paket aber giaddr 0.0.0.0. Ein Router verwirft solche Pakete standardmäßig. `ip dhcp relay information trusted` (am Interface) oder `ip dhcp relay information trust-all` erlaubt sie, sonst bekommt der Client keine Adresse.")],
    nodes=[
        dict(name="H1", type="host", x=0, y=150,
             base="""
interface GigabitEthernet0/0
 ip address dhcp
 no shutdown""", sol="", vpcs="ip dhcp"),
        dict(name="R1", type="router", x=200, y=150,
             base="""
interface GigabitEthernet0/0
 ip address 10.1.1.1 255.255.255.0
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.12.1 255.255.255.252
 no shutdown
ip route 0.0.0.0 0.0.0.0 10.0.12.2""",
             sol="""
interface GigabitEthernet0/0
 ip helper-address 10.0.12.2"""),
        dict(name="R2", type="router", x=400, y=150,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.12.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.23.1 255.255.255.252
 no shutdown
ip route 10.1.1.0 255.255.255.0 10.0.12.1
ip route 10.1.2.0 255.255.255.0 10.0.23.2""",
             sol="""
ip dhcp excluded-address 10.1.1.1 10.1.1.10
ip dhcp excluded-address 10.1.2.1 10.1.2.10
ip dhcp pool LAN1
 network 10.1.1.0 255.255.255.0
 default-router 10.1.1.1
 dns-server 192.0.2.53
 domain-name lab.example
 lease 0 8
ip dhcp pool LAN2
 network 10.1.2.0 255.255.255.0
 default-router 10.1.2.1
 dns-server 192.0.2.53
 domain-name lab.example
 lease 0 8"""),
        dict(name="R3", type="router", x=600, y=150,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.23.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.1.2.1 255.255.255.0
 no shutdown
ip route 0.0.0.0 0.0.0.0 10.0.23.1""",
             sol="""
interface GigabitEthernet0/1
 ip helper-address 10.0.23.1"""),
        dict(name="H2", type="host", x=800, y=150,
             base="""
interface GigabitEthernet0/0
 ip address dhcp
 no shutdown""", sol="", vpcs="ip dhcp")],
    links=[("H1", "Gi0/0", "R1", "Gi0/0"), ("R1", "Gi0/1", "R2", "Gi0/0"),
           ("R2", "Gi0/1", "R3", "Gi0/0"), ("R3", "Gi0/1", "H2", "Gi0/0")],
    vpcs=True,
    vpcs_note="Dann gelten VPCS-Befehle: `ip dhcp` startet die Anfrage (`ip dhcp -r` gibt die Adresse frei), `show ip` zeigt das Ergebnis, `trace <ziel>` statt `traceroute`.",
    staggered=True,
    tickets=["H1 bekommt keine Adresse; auf R2 zeigt `debug ip dhcp server packet` keine Anfragen aus 10.1.1.1.",
             "H2 bekommt keine Adresse; auf R2 zeigt `debug ip dhcp server packet` keine Anfragen aus 10.1.2.1.",
             "R2 empfängt die Anfragen von R3 (giaddr 10.1.2.1), H2 bekommt trotzdem keine Adresse; im Debug steht „there is no address pool for 10.1.2.1“.",
             "R2 empfängt die Anfragen von R1, H1 bekommt trotzdem keine Adresse; die Bindings bleiben leer.",
             "R2 sendet das DHCPOFFER für H2 (Debug zeigt es), H2 bekommt es trotzdem nicht."],
    faults=[
        dict(node="R1", old=" ip helper-address 10.0.12.2", new=None,
             find="`show ip interface Gi0/0` auf R1 nennt „Helper address is not set“. Die Anfrage von H1 endet an R1.",
             cause="Ohne `ip helper-address` leitet R1 den Broadcast nicht an den Server weiter.",
             fix="`ip helper-address 10.0.12.2` unter Gi0/0 auf R1."),
        dict(node="R3", old=" ip helper-address 10.0.23.1", new=" ip helper-address 10.0.32.1",
             find="`show ip interface Gi0/1` auf R3 nennt die Helper-Adresse 10.0.32.1. `show ip route 10.0.32.1` findet nur die Default-Route; die Adresse gehört niemandem.",
             cause="Zahlendreher in der Server-Adresse: Die Anfrage geht an 10.0.32.1, nicht an den Server 10.0.23.1.",
             fix="`ip helper-address 10.0.23.1` unter Gi0/1 auf R3."),
        dict(node="R2", old=" network 10.1.2.0 255.255.255.0", new=" network 10.1.20.0 255.255.255.0",
             find="`show ip dhcp pool LAN2` zeigt das Netz 10.1.20.0/24. Das Debug nennt „there is no address pool for 10.1.2.1“.",
             cause="Der Server wählt den Pool anhand von giaddr (10.1.2.1). Das Netz des Pools LAN2 (10.1.20.0/24) enthält die Adresse nicht, also gibt es keinen passenden Pool.",
             fix="`network 10.1.2.0 255.255.255.0` im Pool LAN2."),
        dict(node="R2", old="ip dhcp excluded-address 10.1.1.1 10.1.1.10", new="ip dhcp excluded-address 10.1.1.1 10.1.1.254",
             find="`show running-config | include excluded` zeigt den Bereich bis 10.1.1.254. `show ip dhcp pool LAN1` zeigt 0 Leases.",
             cause="Der Ausschluss deckt den ganzen Pool ab, es bleibt keine freie Adresse.",
             fix="`ip dhcp excluded-address 10.1.1.1 10.1.1.10`."),
        dict(node="R2", old="ip route 10.1.2.0 255.255.255.0 10.0.23.2", new=None,
             find="`show ip route 10.1.2.1` auf R2: „Network not in table“. Das Debug zeigt das gesendete DHCPOFFER, der Router kann es aber nicht zustellen.",
             cause="R2 sendet Offer und Ack als Unicast an giaddr (10.1.2.1). Ohne Route zu 10.1.2.0/24 geht das Paket ins Leere.",
             fix="`ip route 10.1.2.0 255.255.255.0 10.0.23.2` auf R2.")],
    verify=["show ip dhcp pool", "show ip dhcp binding", "show ip dhcp server statistics", "show ip interface GigabitEthernet0/0 | include Helper",
            "show ip interface brief                ! auf H1/H2", "debug ip dhcp server packet     ! kurz, danach undebug all",
            "show ip route 10.1.2.1                 ! auf R2: Rückweg zum Relay"],
    verify_table=[("`show ip interface brief` auf H1 / H2", "10.1.1.11 / 10.1.2.11 (erste Adresse nach dem Ausschluss)"),
                  ("`show ip dhcp binding` auf R2", "zwei Bindings (H1, H2) mit Lease-Ende"),
                  ("`show ip dhcp server statistics` auf R2", "Discover/Offer/Request/Ack zählen hoch")],
    teilc=[("Ein Client bekommt keine Adresse. In welcher Reihenfolge prüfst du?",
            "**Von der Anfrage bis zur Antwort.** 1) Kommt die Anfrage am Relay an (Link, VLAN)? 2) Steht der Helper am Eingangs-Interface und zeigt auf den Server? 3) Erreicht der Relay den Server (Ping, Route)? 4) Trifft giaddr einen Pool, und sind Adressen frei (Pool, Ausschlüsse, Bindings)? 5) Kommt die Antwort zurück (Route zum giaddr)?"),
           ("Warum ist die Adresse in giaddr wichtig, und was passiert, wenn der Relay mehrere IPs am Interface hat?",
            "**giaddr wählt den Pool und das Ziel der Antwort.** Hat das Interface Secondary-Adressen, nutzt der Relay die primäre Adresse als giaddr. Mit `ip dhcp smart-relay` wechselt er auf die Secondary-Adressen, wenn der Server auf die Anfragen nicht antwortet (zum Beispiel Pool voll). Der Server braucht dann auch für das Secondary-Netz einen Pool."),
           ("Was leitet `ip helper-address` außer DHCP noch weiter, und wie schaltest du das ab?",
            "**Mehr UDP-Broadcasts: TFTP (69), DNS (53), TACACS (49), Time (37), NetBIOS (137/138).** Mit `no ip forward-protocol udp <Port>` schaltest du einzelne ab. DHCP selbst (67/68) bleibt, solange der Helper steht.")],
    exam=["DHCP-Ablauf: Discover (Broadcast), Offer, Request, Ack. Das Relay macht aus dem Broadcast einen Unicast und setzt giaddr.",
          "Server wählt den Pool nach giaddr, Antwort geht an giaddr: Rückweg (Route) muss stimmen.",
          "`ip helper-address` steht auf dem **Client-seitigen** Interface und zeigt auf den Server.",
          "Option 82 und `ip dhcp relay information trusted/trust-all` bei Snooping-Switches mit giaddr 0.",
          "Fehlersuche: `show ip dhcp binding/pool/conflict/server statistics`, `debug ip dhcp server packet/events`."],
)
