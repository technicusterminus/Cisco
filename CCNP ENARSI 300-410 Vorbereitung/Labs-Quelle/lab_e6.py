LAB = dict(
    slug="E6-IPv6-First-Hop-Security", num="E6", title="IPv6 First Hop Security: RA Guard und DHCPv6 Guard", minutes=90, level="mittel",
    summary=("Im IPv6-Zugangsnetz kann jeder Host Router Advertisements und DHCPv6-Antworten senden. Du richtest auf dem Switch "
             "RA Guard und DHCPv6 Guard ein, sodass nur der Router-Port als Router und DHCPv6-Server gilt, und siehst, wie sich der "
             "Zustand am Host ändert. Dazu die Einordnung von IPv6 Snooping, ND Inspection und Source Guard."),
    goals=["Die Wirkung eines Rogue-Routers und eines Rogue-DHCPv6-Servers am Host nachweisen.",
           "RA-Guard-Policies (`device-role host` und `router`) anlegen und an Ports binden.",
           "DHCPv6-Guard-Policies (`device-role client` und `server`) anlegen und binden.",
           "Die Rolle der Ports prüfen und die Ergänzungen (Snooping, ND Inspection, Source Guard) einordnen."],
    tags=[("3.4", "IPv6 First Hop Security: Feinheiten", 13)],
    diagram="""
              ┌── R1 (legitimer Router, DHCPv6-Server, 2001:db8:1::/64)
   SW (L2) ───┤── H1 (Host, SLAAC + DHCPv6)
              └── ATK (Rogue-Router und Rogue-DHCPv6, 2001:db8:bad::/64)
""",
    nets=[("SW Gi0/0 – R1 Gi0/0", "2001:db8:1::/64 (R1 ::1) – legitimer Router, Router-Port"),
          ("SW Gi0/1 – H1 Gi0/0", "Hostport"),
          ("SW Gi0/2 – ATK Gi0/0", "2001:db8:bad::/64 (ATK ::1) – Angreifer-Port, gleiches VLAN")],
    topo_text=("Alle drei Geräte hängen im selben VLAN am Switch. R1 sendet Router Advertisements für 2001:db8:1::/64 mit gesetztem M-Flag und bietet "
               "per DHCPv6 Adressen und einen DNS-Server (2001:db8:1::53). ATK macht genau dasselbe für 2001:db8:bad::/64. "
               "H1 nimmt SLAAC-Adressen aus Router Advertisements und fordert zusätzlich eine Adresse per DHCPv6 an. "
               "Konfigurieren musst du nur den Switch; R1 und ATK sind in der Ausgangslage fertig."),
    steps=[
        dict(t="Angriff sichtbar machen.", body="Auf H1: `show ipv6 routers`, `show ipv6 interface brief`, `show ipv6 route ::/0` und `show ipv6 dhcp interface`.",
             check="H1 sieht zwei Router (R1 und ATK), hat Adressen aus beiden Präfixen und zwei Default-Routen. Die DHCPv6-Adresse stammt von einem der beiden Server.",
             think="Was kann der Angreifer damit erreichen, und welche zwei Mechanismen nutzt er?"),
        dict(t="RA-Guard-Policies anlegen.", body="Auf SW: `ipv6 nd raguard policy HOST-POLICY` mit `device-role host`, `ipv6 nd raguard policy ROUTER-POLICY` mit `device-role router`.",
             check="`show ipv6 nd raguard policy` listet beide Policies mit der Rolle.",
             think="Warum schaltet RA Guard auf Hostports nur Router Advertisements ab und nicht allen ICMPv6-Verkehr?"),
        dict(t="RA Guard an die Ports binden.", body="Gi0/0 (R1): `ipv6 nd raguard attach-policy ROUTER-POLICY`. Gi0/1 (H1) und Gi0/2 (ATK): `ipv6 nd raguard attach-policy HOST-POLICY`. Setze danach auf H1 das Interface zurück (`shutdown`, `no shutdown`).",
             check="`show ipv6 routers` auf H1 nennt nur noch R1. Die Adresse aus dem ATK-Präfix und die zweite Default-Route sind weg.",
             think="Warum hätte H1 den Eintrag von ATK auch ohne das Zurücksetzen noch eine Weile behalten?"),
        dict(t="DHCPv6 Guard.", body="Auf SW: `ipv6 dhcp guard policy SERVER-POLICY` mit `device-role server` und `ipv6 dhcp guard policy CLIENT-POLICY` mit `device-role client`. Binde Gi0/0 an SERVER-POLICY, Gi0/1 und Gi0/2 an CLIENT-POLICY (`ipv6 dhcp guard attach-policy …`). Auf H1 die DHCPv6-Anfrage erneuern.",
             check="`show ipv6 interface brief` auf H1 zeigt nur noch Adressen aus 2001:DB8:1::/64. `show ipv6 dhcp guard policy` listet die Policies mit den Zielen.",
             think="Welche Nachrichten blockiert `device-role client`, und warum reicht RA Guard allein nicht?"),
        dict(t="Ergänzungen einordnen.", body="Mehr ist in diesem Lab nicht konfiguriert.",
             think="Was leisten IPv6 Snooping, ND Inspection und Source Guard zusätzlich, und was nützt RA Guard nichts gegen fragmentierte Router Advertisements?")],
    answers=[
        ("1", "Mit einem **Rogue-RA** wird der Angreifer zum Default-Gateway des Hosts und kann den Verkehr mitlesen oder umleiten (Man in the Middle). Mit einem **Rogue-DHCPv6-Server** liefert er Adressen und einen eigenen DNS-Server und lenkt Namensauflösungen um."),
        ("2", "RA Guard filtert nur **Router Advertisements** (ICMPv6 Typ 134), weil nur die Quelle der RAs ein Router sein darf. Neighbor Solicitation, Echo und alle anderen ICMPv6-Typen müssen weiter fließen, sonst funktioniert IPv6 nicht."),
        ("3", "Die Adresse und die Default-Route aus dem alten RA bleiben, bis ihre Lebenszeit (Router Lifetime und Valid/Preferred Lifetime) abläuft. RA Guard wirkt nur auf neue Pakete. Für den Test sofort: Interface zurücksetzen oder die Einträge löschen."),
        ("4", "`device-role client` blockiert DHCPv6-Antworten, die nur Server senden (Advertise, Reply, Reconfigure). RA Guard schützt nur gegen RAs. Ein Rogue-DHCPv6-Server braucht aber keinen RA, er antwortet direkt auf die Anfrage des Hosts."),
        ("5", "**IPv6 Snooping** baut eine Bindungstabelle (Adresse, MAC, Port) aus ND und DHCPv6 auf. **ND Inspection** prüft ND-Nachrichten gegen diese Tabelle (verhindert Spoofing von Neighbor Advertisements). **Source Guard** filtert Pakete, deren Absenderadresse nicht zur Bindung passt. RA Guard lässt sich mit fragmentierten RAs oder Extension Headern umgehen, wenn der Switch die Header nicht vollständig lesen kann (RFC 7113). Abhilfe: Fragmente auf Hostports verwerfen oder Extension-Header-Filter.")],
    nodes=[
        dict(name="SW", type="l2", x=300, y=150,
             base="""
interface GigabitEthernet0/0
 switchport mode access
 no shutdown
interface GigabitEthernet0/1
 switchport mode access
 no shutdown
interface GigabitEthernet0/2
 switchport mode access
 no shutdown""",
             sol="""
ipv6 nd raguard policy HOST-POLICY
 device-role host
ipv6 nd raguard policy ROUTER-POLICY
 device-role router
ipv6 dhcp guard policy SERVER-POLICY
 device-role server
ipv6 dhcp guard policy CLIENT-POLICY
 device-role client
interface GigabitEthernet0/0
 ipv6 nd raguard attach-policy ROUTER-POLICY
 ipv6 dhcp guard attach-policy SERVER-POLICY
interface GigabitEthernet0/1
 ipv6 nd raguard attach-policy HOST-POLICY
 ipv6 dhcp guard attach-policy CLIENT-POLICY
interface GigabitEthernet0/2
 ipv6 nd raguard attach-policy HOST-POLICY
 ipv6 dhcp guard attach-policy CLIENT-POLICY"""),
        dict(name="R1", type="router", x=100, y=50,
             base="""
ipv6 unicast-routing
ipv6 dhcp pool LAN1
 address prefix 2001:DB8:1::/64
 dns-server 2001:DB8:1::53
interface GigabitEthernet0/0
 ipv6 address 2001:DB8:1::1/64
 ipv6 nd managed-config-flag
 ipv6 dhcp server LAN1
 no shutdown""", sol=""),
        dict(name="H1", type="host", x=100, y=150,
             base="""
interface GigabitEthernet0/0
 ipv6 enable
 ipv6 address autoconfig
 ipv6 address dhcp
 no shutdown""", sol=""),
        dict(name="ATK", type="router", x=100, y=250,
             base="""
ipv6 unicast-routing
ipv6 dhcp pool EVIL
 address prefix 2001:DB8:BAD::/64
 dns-server 2001:DB8:BAD::53
interface GigabitEthernet0/0
 ipv6 address 2001:DB8:BAD::1/64
 ipv6 nd managed-config-flag
 ipv6 dhcp server EVIL
 no shutdown""", sol="")],
    links=[("SW", "Gi0/0", "R1", "Gi0/0"), ("SW", "Gi0/1", "H1", "Gi0/0"), ("SW", "Gi0/2", "ATK", "Gi0/0")],
    vpcs=False,
    vpcs_note="Für dieses Lab brauchst du **vIOS-Hosts**: VPCS kann kein DHCPv6 und keine ND-Auswertung wie ein IOS-Host.",
    staggered=True,
    tickets=["H1 sieht weiterhin die Router Advertisements von ATK (`show ipv6 routers` listet zwei Router), obwohl RA Guard eingerichtet ist.",
             "H1 bekommt keinen Default-Router und keine Adresse aus 2001:DB8:1::/64; `show ipv6 routers` ist leer.",
             "ATK schickt RAs, und sie erreichen H1, obwohl am Port Gi0/2 die Host-Policy hängt.",
             "H1 bekommt per DHCPv6 eine Adresse aus 2001:DB8:BAD::/64, obwohl der Port von ATK eine Client-Policy trägt.",
             "H1 bekommt gar keine DHCPv6-Adresse mehr, auch nicht von R1; SLAAC funktioniert."],
    faults=[
        dict(node="SW", old=" ipv6 nd raguard attach-policy HOST-POLICY", new=None, nth=1,
             find="`show ipv6 nd raguard policy HOST-POLICY` listet als Ziel nur Gi0/1. Auf Gi0/2 fehlt die Bindung (`show running-config interface Gi0/2`).",
             cause="Am Angreifer-Port ist keine RA-Guard-Policy gebunden. RAs von ATK werden ungefiltert weitergeleitet.",
             fix="`ipv6 nd raguard attach-policy HOST-POLICY` unter Gi0/2."),
        dict(node="SW", old=" ipv6 nd raguard attach-policy ROUTER-POLICY", new=" ipv6 nd raguard attach-policy HOST-POLICY",
             find="`show ipv6 nd raguard policy HOST-POLICY` listet Gi0/0 (R1), Gi0/1 und Gi0/2 als Ziele. Die Policy ROUTER-POLICY hat kein Ziel.",
             cause="Der Router-Port trägt die Host-Policy. RAs des legitimen Routers werden dort verworfen, H1 sieht nie einen Router.",
             fix="`ipv6 nd raguard attach-policy ROUTER-POLICY` unter Gi0/0."),
        dict(node="SW", old=" device-role host", new=" device-role router",
             find="`show ipv6 nd raguard policy HOST-POLICY` zeigt `device-role router`. Damit lässt die Policy RAs durch.",
             cause="Die Policy heißt HOST-POLICY, hat aber die Rolle router. Sie erlaubt RAs auf allen Ports, an die sie gebunden ist.",
             fix="`device-role host` in HOST-POLICY."),
        dict(node="SW", old=" ipv6 dhcp guard attach-policy CLIENT-POLICY", new=None, nth=1,
             find="`show ipv6 dhcp guard policy CLIENT-POLICY` listet als Ziel nur Gi0/1, nicht Gi0/2.",
             cause="Am Angreifer-Port ist kein DHCPv6 Guard gebunden. Advertise und Reply des Rogue-Servers werden durchgelassen.",
             fix="`ipv6 dhcp guard attach-policy CLIENT-POLICY` unter Gi0/2."),
        dict(node="SW", old=" device-role server", new=" device-role client",
             find="`show ipv6 dhcp guard policy SERVER-POLICY` zeigt `device-role client`.",
             cause="Der Port von R1 trägt eine Policy mit Rolle client. Server-Nachrichten (Advertise, Reply) von R1 werden verworfen.",
             fix="`device-role server` in SERVER-POLICY.")],
    verify=["show ipv6 nd raguard policy", "show ipv6 dhcp guard policy", "show ipv6 routers               ! auf H1",
            "show ipv6 interface brief         ! auf H1", "show ipv6 route ::/0               ! auf H1", "show ipv6 dhcp interface         ! auf H1"],
    verify_table=[("`show ipv6 routers` auf H1", "nur R1 (Link-Local von R1)"),
                  ("`show ipv6 interface brief` auf H1", "nur Adressen aus 2001:DB8:1::/64"),
                  ("`show ipv6 nd raguard policy` auf SW", "ROUTER-POLICY an Gi0/0, HOST-POLICY an Gi0/1 und Gi0/2"),
                  ("`show ipv6 dhcp guard policy` auf SW", "SERVER-POLICY an Gi0/0, CLIENT-POLICY an Gi0/1 und Gi0/2")],
    caveat=("RA Guard und DHCPv6 Guard hängen vom Switch-Image ab. Das IOSvL2-Image kennt die Befehle womöglich nur eingeschränkt oder gar nicht; "
            "dann lies das Lab als Konfigurations- und Denkaufgabe (Teil A, Teil C, die Tickets mit den Lösungen). Die Syntax folgt der Cisco-IOS-15-Dokumentation und ist hier "
            "nicht in einer laufenden Simulation getestet. Auf Catalyst-Switches mit IOS XE heißen einige Befehle anders (SISF)."),
    teilc=[("Ein Host bekommt über SLAAC keinen Default-Router, obwohl der Router RAs sendet. Was prüfst du auf dem Switch?",
            "**Rolle und Bindung des Router-Ports.** Hängt am Router-Port eine Policy mit `device-role router` (nicht host)? Sind Policy und Port richtig gebunden (`show ipv6 nd raguard policy`)? Gibt es eine zweite Filterung (VACL, PACL, ND Inspection) auf dem Pfad?"),
           ("Warum braucht man DHCPv6 Guard zusätzlich zu RA Guard?",
            "**Weil ein Rogue-DHCPv6-Server keinen RA braucht.** Der Host fragt per Multicast (ff02::1:2) nach einem Server, der Angreifer antwortet mit Adresse und DNS-Server. RA Guard schaut nur auf RAs, nicht auf DHCPv6-Nachrichten."),
           ("Was bewirkt ein Preference-Limit oder `match ipv6 access-list` in einer RA-Guard-Policy?",
            "**Es erlaubt nur RAs, deren Absender und Inhalt zur Vorgabe passen.** Mit `match ipv6 access-list` prüfst du die Absenderadresse, mit `match ra prefix-list` die angekündigten Präfixe, mit `router-preference maximum` begrenzt du die angekündigte Priorität. So kann auch auf dem Router-Port nur der erwartete Router mit den erwarteten Präfixen senden.")],
    exam=["RA Guard: `ipv6 nd raguard policy … / device-role host|router`, Bindung mit `ipv6 nd raguard attach-policy`.",
          "DHCPv6 Guard: `ipv6 dhcp guard policy … / device-role client|server`, optional Match auf Server-Adresse und Präfix.",
          "Hostport = Rolle host/client, Router-/Serverport = Rolle router/server. Eine falsch gesetzte Rolle ist der häufigste Fehler.",
          "Ergänzungen: IPv6 Snooping (Bindungstabelle), ND Inspection (prüft ND gegen die Tabelle), Source Guard (prüft die Absenderadresse).",
          "RA Guard kann durch fragmentierte RAs oder Extension Header umgangen werden (RFC 7113)."],
)
