def router(n, links, extra=""):
    """Basis eines Routers: Loopback0, Links, OSPF als fertiges Unicast-Underlay."""
    out = [f"interface Loopback0\n ip address 10.255.0.{n} 255.255.255.255"]
    nets = [f" network 10.255.0.{n} 0.0.0.0 area 0"]
    for ifname, ip, mask, wild in links:
        out.append(f"interface {ifname}\n ip address {ip} {mask}\n no shutdown")
        net = ip.rsplit(".", 1)[0] + (".0" if mask == "255.255.255.0" else "." + str(int(ip.rsplit(".", 1)[1]) // 4 * 4))
        nets.append(f" network {net} {wild} area 0")
    out.append(f"router ospf 1\n router-id 10.255.0.{n}\n" + "\n".join(nets))
    return "\n".join(out) + extra


P30 = ("255.255.255.252", "0.0.0.3")
P24 = ("255.255.255.0", "0.0.0.255")

COMMON = """
ip multicast-routing
ip pim bidir-enable
ip pim ssm default
ip pim rp-address 10.255.0.100 10
ip pim rp-address 10.255.0.200 20 bidir
access-list 10 permit 239.1.0.0 0.0.255.255
access-list 20 permit 239.2.0.0 0.0.255.255
interface Loopback0
 ip pim sparse-mode"""

LAB = dict(
    slug="32-Multicast-SSM-Bidir-MSDP", num="32",
    title="Multicast vertieft: IGMPv3 und SSM, Bidir-PIM, Anycast-RP mit MSDP", minutes=120, level="schwer",
    summary=("Lab 12 hat PIM Sparse Mode mit einem RP gezeigt. Hier baust du auf demselben Netz nacheinander die drei "
             "Verfahren, die das Blueprint zusätzlich nennt: Source-Specific Multicast mit IGMPv3 (kein RP), "
             "Bidirectional PIM (nur Shared Tree, kein `(S,G)`) und zwei RPs mit gleicher Adresse, die sich ihre Quellen "
             "per MSDP mitteilen. Jedes Verfahren bekommt einen eigenen Gruppenbereich, damit du sie nebeneinander "
             "vergleichen kannst."),
    goals=["Für eine Gruppe aus dem Zustand in `show ip mroute` ablesen, ob sie als SSM, Bidir oder Sparse Mode läuft.",
           "SSM mit IGMPv3 aufbauen und erklären, warum ein Beitritt ohne Quelle im Bereich 232.0.0.0/8 nichts bewirkt.",
           "Bidir-PIM einrichten und die Rolle des Designated Forwarder (DF) am Ausgang von `show ip pim interface df` zeigen.",
           "Anycast-RP mit MSDP bauen und am SA-Cache nachweisen, wie ein RP von einer Quelle beim anderen RP erfährt.",
           "Die vier Verfahren (ASM, SSM, Bidir, Anycast-RP/MSDP) nach RP-Bedarf, Zustand und Einsatzfall einordnen."],
    tags=[("3.3.d", "Multicast-Verfahren", 46)],
    diagram="""
                    Lo1 10.255.0.100 (Anycast-RP)      Lo1 10.255.0.100 (Anycast-RP)
                    Lo2 10.255.0.200 (Bidir-RP)
  SRC ──── R1 ────────── R2 ═══════ MSDP (Lo0–Lo0) ═══════ R3 ────────── R4 ──── REC
      Gi0/1  Gi0/0   Gi0/0  Gi0/1                      Gi0/0  Gi0/1   Gi0/0  Gi0/1
""",
    nets=[("R1 Gi0/0 – R2 Gi0/0", "10.0.12.0/30 (.1/.2)"), ("R2 Gi0/1 – R3 Gi0/0", "10.0.23.0/30 (.1/.2)"),
          ("R3 Gi0/1 – R4 Gi0/0", "10.0.34.0/30 (.1/.2)"),
          ("R1 Gi0/1 – SRC", "192.168.1.0/24 (R1 .1, SRC .10)"), ("R4 Gi0/1 – REC", "192.168.4.0/24 (R4 .1, REC .10)")],
    topo_text=("Loopback0: R1 10.255.0.1 bis R4 10.255.0.4 (/32). OSPF 1 (Area 0) ist als Unicast-Underlay **fertig "
               "konfiguriert**, mit fest gesetzter Router-ID. Die Loopbacks 1 und 2 legst du in Teil A selbst an.\n\n"
               "| Gruppenbereich | Verfahren | RP |\n|---|---|---|\n"
               "| 232.0.0.0/8 | SSM | keiner |\n"
               "| 239.1.0.0/16 | Sparse Mode (ASM) | 10.255.0.100, Anycast auf R2 und R3 |\n"
               "| 239.2.0.0/16 | Bidir-PIM | 10.255.0.200 auf R2 |\n\n"
               "Testgruppen: **232.1.1.1**, **239.1.1.1**, **239.2.1.1**. Quelle ist immer SRC (192.168.1.10), Empfänger REC."),
    anycast=["10.255.0.100"],
    steps=[
        dict(t="Grundlage.", body="Setze auf R1 bis R4 `ip multicast-routing` und `ip pim sparse-mode` auf allen Gi-Interfaces und auf Loopback0.",
             check="`show ip pim neighbor` zeigt auf R2 und R3 je zwei Nachbarn. `show ip ospf neighbor` war schon vorher vollständig.",
             think="PIM selbst tauscht keine Routen aus. Woher nimmt ein Router die Information für den RPF-Check?"),
        dict(t="SSM einschalten.", body="Setze auf allen vier Routern `ip pim ssm default`. Stelle R4 Gi0/1 und REC Gi0/0 auf `ip igmp version 3`. REC tritt bei: `ip igmp join-group 232.1.1.1 source 192.168.1.10`.",
             predict="SRC sendet noch nichts. Welche Einträge stehen jetzt schon in `show ip mroute 232.1.1.1` auf R2: `(*,G)`, `(S,G)`, beide oder keiner?",
             check="`show ip igmp groups 232.1.1.1 detail` auf R4 nennt die Quelle 192.168.1.10 im Modus INCLUDE. `show ip mroute 232.1.1.1` zeigt auf R4, R3, R2 und R1 genau einen `(192.168.1.10, 232.1.1.1)`-Eintrag mit Flag `s`, kein `(*,G)`. `ping 232.1.1.1 repeat 5` auf SRC wird von 192.168.4.10 beantwortet.",
             think="Der Baum steht, bevor die Quelle ein Paket sendet. Warum geht das bei SSM, bei Sparse Mode aber nicht?"),
        dict(t="SSM-Falle: Beitritt ohne Quelle.", body="REC tritt zusätzlich `ip igmp join-group 232.2.2.2` bei, also ohne `source`.",
             predict="Entsteht auf R4 ein Multicast-Zustand für 232.2.2.2?",
             check="`show ip mroute 232.2.2.2` auf R4 bleibt leer, ein Ping von SRC an 232.2.2.2 bleibt unbeantwortet. Entferne den Beitritt danach wieder.",
             think="Was würde passieren, wenn R4 Gi0/1 noch auf IGMPv2 stünde und REC den Beitritt *mit* Quelle sendet?"),
        dict(t="Bidir-PIM.", body="Lege auf R2 `interface Loopback2` mit 10.255.0.200/32 und `ip pim sparse-mode` an und nimm die Adresse in OSPF auf. Setze auf allen Routern `ip pim bidir-enable`, `access-list 20 permit 239.2.0.0 0.0.255.255` und `ip pim rp-address 10.255.0.200 20 bidir`. REC tritt `239.2.1.1` bei, SRC sendet `ping 239.2.1.1 repeat 20`.",
             predict="Wie viele `(S,G)`-Einträge für 239.2.1.1 findest du nach dem Ping im ganzen Netz?",
             check="`show ip pim rp mapping` nennt 10.255.0.200 mit dem Zusatz `bidir`. `show ip mroute 239.2.1.1` zeigt überall nur `(*, 239.2.1.1)` mit Flag `B`, auch auf R1 direkt an der Quelle. `show ip pim interface df` listet pro Interface den DF für den RP 10.255.0.200.",
             think="Bei Bidir gibt es keine Register-Nachricht und keinen RPF-Check gegen die Quelle. Was verhindert dann Schleifen?"),
        dict(t="Anycast-RP ohne MSDP.", body="Lege auf R2 **und** R3 `interface Loopback1` mit derselben Adresse 10.255.0.100/32 und `ip pim sparse-mode` an und nimm sie auf beiden in OSPF auf. Setze auf allen Routern `access-list 10 permit 239.1.0.0 0.0.255.255` und `ip pim rp-address 10.255.0.100 10`. REC tritt `239.1.1.1` bei, SRC sendet `ping 239.1.1.1 repeat 10`.",
             predict="Zu welchem der beiden RPs schickt R1 sein Register, zu welchem R4 seinen Join? Antwortet REC auf den Ping?",
             check="`show ip route 10.255.0.100` zeigt auf R1 den Weg über R2, auf R4 den Weg über R3. Der Ping bleibt **unbeantwortet**. R2 kennt `(192.168.1.10, 239.1.1.1)` ohne Empfänger, R3 kennt `(*, 239.1.1.1)` ohne Quelle.",
             think="Warum ist die Router-ID in OSPF hier fest gesetzt? Was wäre passiert, wenn R2 und R3 sie automatisch gewählt hätten?"),
        dict(t="MSDP verbindet die RPs.", body="R2: `ip msdp peer 10.255.0.3 connect-source Loopback0` und `ip msdp originator-id Loopback0`. R3 spiegelbildlich mit Peer 10.255.0.2. Wiederhole den Ping.",
             check="`show ip msdp summary` zeigt den Peer im Zustand `Up`. Während SRC sendet, steht in `show ip msdp sa-cache` auf R3 der Eintrag `(192.168.1.10, 239.1.1.1), RP 10.255.0.2`. Der Ping wird jetzt beantwortet, und R3 hat einen `(S,G)`-Eintrag mit Flag `M`.",
             think="Wozu dient `originator-id`, und warum zeigt `connect-source` auf Loopback0 und nicht auf die Anycast-Adresse?"),
        dict(t="RP-Ausfall.", body="Starte auf SRC `ping 239.1.1.1 repeat 200` und schalte währenddessen auf R3 `interface Loopback1` ab.",
             predict="Welchen RP nutzt R4 danach, und wovon hängt die Dauer der Unterbrechung ab?",
             check="`show ip route 10.255.0.100` auf R4 zeigt nach der OSPF-Konvergenz den Weg über R3 zu R2. Der Ping läuft nach wenigen ausgefallenen Paketen weiter. Schalte Loopback1 danach wieder ein.",
             think="An welcher Stelle unterscheidet sich das von einem RP-Wechsel per BSR oder Auto-RP?"),
        dict(t="Vergleichen.", body="Fülle die Tabelle aus dem Gedächtnis aus, bevor du die Antwort aufklappst: Für **Sparse Mode (ASM)**, **SSM**, **Bidir** jeweils: RP nötig? Welche Einträge (`(*,G)`, `(S,G)`)? Welche IGMP-Version am Empfänger? Typischer Einsatz?")],
    answers=[
        ("1", "Aus der Unicast-Routing-Tabelle, hier also aus OSPF. Daher der Name *Protocol Independent* Multicast: PIM ist egal, welches Protokoll die Routen liefert. Fehlt die Unicast-Route zur Quelle oder zum RP, scheitert der RPF-Check, und es entsteht kein Baum."),
        ("2", "**Nur `(S,G)`.** Bei SSM nennt der Empfänger die Quelle im IGMPv3-Report. R4 kann den Join deshalb sofort Hop für Hop in Richtung Quelle schicken. Bei Sparse Mode kennt der Empfänger-Router die Quelle nicht und muss erst über den RP gehen."),
        ("3", "**Nein.** Im SSM-Bereich verwirft der Router jeden Beitritt ohne Quelle, es gibt dort kein `(*,G)`. Mit IGMPv2 am Router-Interface fällt auch der Host auf Version 2 zurück und kann gar keine Quelle mehr nennen. Der Report kommt an, wird aber ignoriert. Das ist einer der häufigsten SSM-Fehler und Ticket-Material."),
        ("4", "**Keinen.** Bidir kennt nur den Shared Tree. Daten fließen von der Quelle *aufwärts* zum RP und von dort abwärts, auf denselben `(*,G)`-Einträgen. Schleifen verhindert die DF-Wahl: Pro Segment gewinnt genau ein Router (der mit der besten Unicast-Metrik zum RP), und nur er darf Verkehr in Richtung RP weiterleiten."),
        ("5", "R1 registriert bei **R2**, R4 schickt den Join an **R3**: Jeder nimmt den RP, der laut OSPF am nächsten liegt. Die beiden RPs wissen nichts voneinander, also antwortet REC nicht. Zur Router-ID: Ohne feste Vorgabe wählt OSPF die höchste Loopback-Adresse. Das wäre auf R2 *und* R3 die 10.255.0.100 gewesen, also zwei Router mit derselben Router-ID. Anycast-Adressen dürfen nie zur Router-ID werden."),
        ("6", "MSDP trägt in jeder Source-Active-Meldung die Adresse des RP, der sie erzeugt hat. Ohne `originator-id` stünde dort die Anycast-Adresse, die beide Router besitzen. Der Empfänger könnte den Absender nicht von sich selbst unterscheiden. Aus demselben Grund läuft die TCP-Sitzung (Port 639) zwischen den eindeutigen Loopback0-Adressen: Ein Paket an 10.255.0.100 käme beim nächstgelegenen RP an, also bei einem selbst."),
        ("7", "R4 nutzt **R2**. Die Unterbrechung dauert so lange wie die OSPF-Konvergenz plus der neue Join. Bei BSR oder Auto-RP muss erst der Ausfall des RP per Holdtime erkannt und eine neue Zuordnung verteilt werden. Das dauert deutlich länger. Anycast-RP verlagert die Redundanz ins Unicast-Routing."),
        ("8", "**ASM:** RP nötig, erst `(*,G)`, dann `(S,G)`; IGMPv2 genügt; viele unbekannte Quellen. **SSM:** kein RP, nur `(S,G)`; IGMPv3 Pflicht; bekannte Quellen wie IPTV. **Bidir:** RP nötig (als Wurzel, er muss nicht einmal ein echtes Gerät sein), nur `(*,G)`; IGMPv2 genügt; sehr viele Quellen, die zugleich Empfänger sind. **MSDP** ist kein viertes Verfahren, sondern verbindet RPs von Sparse-Mode-Domänen.")],
    nodes=[
        dict(name="R1", type="router", x=150, y=200,
             base=router(1, [("GigabitEthernet0/0", "10.0.12.1") + P30, ("GigabitEthernet0/1", "192.168.1.1") + P24]),
             sol=COMMON + """
interface GigabitEthernet0/0
 ip pim sparse-mode
interface GigabitEthernet0/1
 ip pim sparse-mode"""),
        dict(name="R2", type="router", x=350, y=200,
             base=router(2, [("GigabitEthernet0/0", "10.0.12.2") + P30, ("GigabitEthernet0/1", "10.0.23.1") + P30]),
             sol=COMMON + """
interface Loopback1
 ip address 10.255.0.100 255.255.255.255
 ip pim sparse-mode
interface Loopback2
 ip address 10.255.0.200 255.255.255.255
 ip pim sparse-mode
interface GigabitEthernet0/0
 ip pim sparse-mode
interface GigabitEthernet0/1
 ip pim sparse-mode
router ospf 1
 network 10.255.0.100 0.0.0.0 area 0
 network 10.255.0.200 0.0.0.0 area 0
ip msdp peer 10.255.0.3 connect-source Loopback0
ip msdp originator-id Loopback0"""),
        dict(name="R3", type="router", x=550, y=200,
             base=router(3, [("GigabitEthernet0/0", "10.0.23.2") + P30, ("GigabitEthernet0/1", "10.0.34.1") + P30]),
             sol=COMMON + """
interface Loopback1
 ip address 10.255.0.100 255.255.255.255
 ip pim sparse-mode
interface GigabitEthernet0/0
 ip pim sparse-mode
interface GigabitEthernet0/1
 ip pim sparse-mode
router ospf 1
 network 10.255.0.100 0.0.0.0 area 0
ip msdp peer 10.255.0.2 connect-source Loopback0
ip msdp originator-id Loopback0"""),
        dict(name="R4", type="router", x=750, y=200,
             base=router(4, [("GigabitEthernet0/0", "10.0.34.2") + P30, ("GigabitEthernet0/1", "192.168.4.1") + P24]),
             sol=COMMON + """
interface GigabitEthernet0/0
 ip pim sparse-mode
interface GigabitEthernet0/1
 ip pim sparse-mode
 ip igmp version 3"""),
        dict(name="SRC", type="host", x=0, y=200,
             base="no ip routing\ninterface GigabitEthernet0/0\n ip address 192.168.1.10 255.255.255.0\n no shutdown\nip default-gateway 192.168.1.1",
             sol=""),
        dict(name="REC", type="host", x=900, y=200,
             base="no ip routing\ninterface GigabitEthernet0/0\n ip address 192.168.4.10 255.255.255.0\n no shutdown\nip default-gateway 192.168.4.1",
             sol="""
interface GigabitEthernet0/0
 ip igmp version 3
 ip igmp join-group 232.1.1.1 source 192.168.1.10
 ip igmp join-group 239.1.1.1
 ip igmp join-group 239.2.1.1""")],
    links=[("R1", "Gi0/0", "R2", "Gi0/0"), ("R2", "Gi0/1", "R3", "Gi0/0"), ("R3", "Gi0/1", "R4", "Gi0/0"),
           ("R1", "Gi0/1", "SRC", "Gi0/0"), ("R4", "Gi0/1", "REC", "Gi0/0")],
    vpcs=False,
    vpcs_note=("Die Hosts müssen vIOS sein: SRC sendet Multicast-Pings, REC tritt Gruppen per IGMPv3 mit Quellangabe bei. "
               "Beides kann ein VPCS nicht. In `solutions/REC.cfg` stehen die Beitritte aus Teil A."),
    staggered=True,
    tickets=["SSM: REC ist 232.1.1.1 mit Quelle 192.168.1.10 beigetreten, bekommt aber nichts. Auf R4 gibt es keinen `(S,G)`-Eintrag für die Gruppe.",
             "Bidir: Der Ping von SRC an 239.2.1.1 bleibt unbeantwortet. Die Gruppe 239.1.1.1 ist davon nicht betroffen, sobald die übrigen Tickets gelöst sind.",
             "Anycast-RP: `show ip msdp summary` zeigt auf R2 und R3 keinen Peer im Zustand `Up`.",
             "Anycast-RP: Auch mit stehender MSDP-Sitzung antwortet REC nicht auf Pings an 239.1.1.1. Der SA-Cache auf R3 bleibt leer, während SRC sendet."],
    faults=[
        dict(node="R4", old=" ip igmp version 3", new=None,
             find="`show ip igmp interface GigabitEthernet0/1` auf R4 meldet `IGMP version is 2`. `show ip igmp groups 232.1.1.1 detail` zeigt keinen Eintrag mit Quelle.",
             cause="Der Router fragt mit IGMPv2 ab. Der Host fällt dadurch ebenfalls auf Version 2 zurück und kann keine Quelle nennen. Einen Beitritt ohne Quelle verwirft der Router im SSM-Bereich 232.0.0.0/8.",
             fix="`ip igmp version 3` auf R4 Gi0/1."),
        dict(node="R3", old="ip pim rp-address 10.255.0.200 20 bidir", new="ip pim rp-address 10.255.0.200 20",
             find="`show ip pim rp mapping` auf R3 nennt 10.255.0.200 ohne den Zusatz `bidir`, auf R2 und R4 mit. `show ip pim interface df` ist auf R3 leer, und `show ip mroute 239.2.1.1` zeigt dort kein Flag `B`.",
             cause="R3 behandelt 239.2.0.0/16 als gewöhnlichen Sparse Mode, seine Nachbarn als Bidir. R3 nimmt an keiner DF-Wahl teil und leitet Verkehr auf dem Shared Tree nicht in beide Richtungen weiter. Der Modus einer Gruppe muss im ganzen Netz gleich sein.",
             fix="`ip pim rp-address 10.255.0.200 20 bidir` auf R3."),
        dict(node="R3", old="ip msdp peer 10.255.0.2 connect-source Loopback0", new="ip msdp peer 10.255.0.4 connect-source Loopback0",
             find="`show ip msdp peer` auf R3 nennt 10.255.0.4 als Peer. R4 spricht kein MSDP. Auf R2 steht der Peer 10.255.0.3 im Zustand `Down` oder `Connect`.",
             cause="R3 hat den falschen Peer eingetragen. MSDP ist eine TCP-Sitzung zwischen fest konfigurierten Adressen, beide Seiten müssen einander nennen.",
             fix="Auf R3 `no ip msdp peer 10.255.0.4`, dann `ip msdp peer 10.255.0.2 connect-source Loopback0`."),
        dict(node="R2", ctx="interface Loopback1", old=" ip pim sparse-mode", new=None,
             find="`show ip pim interface` auf R2 listet Loopback1 nicht. `show ip mroute 239.1.1.1` auf R2 zeigt keinen `(S,G)`-Eintrag, obwohl SRC sendet, und `debug ip pim` meldet Register, die R2 nicht als RP annimmt.",
             cause="Ein Router arbeitet nur dann als RP, wenn auf dem Interface mit der RP-Adresse PIM aktiv ist. R2 verarbeitet die Register von R1 nicht, kennt also keine aktive Quelle und erzeugt keine Source-Active-Meldung für R3.",
             fix="`ip pim sparse-mode` auf R2 Loopback1.")],
    verify=["show ip pim neighbor", "show ip pim rp mapping", "show ip igmp groups 232.1.1.1 detail      ! auf R4",
            "show ip mroute 232.1.1.1", "show ip mroute 239.2.1.1", "show ip pim interface df",
            "show ip msdp summary", "show ip msdp sa-cache", "show ip mroute 239.1.1.1",
            "ping 239.1.1.1 repeat 10                  ! auf SRC"],
    verify_table=[("`show ip mroute 232.1.1.1` auf R2", "nur `(192.168.1.10, 232.1.1.1)`, Flag `s`, kein `(*,G)`"),
                  ("`show ip mroute 239.2.1.1` auf R1", "nur `(*, 239.2.1.1)`, Flag `B`"),
                  ("`show ip pim rp mapping`", "10.255.0.100 für ACL 10, 10.255.0.200 für ACL 20 mit `bidir`"),
                  ("`show ip msdp summary` auf R2 und R3", "ein Peer, Zustand `Up`"),
                  ("`show ip msdp sa-cache` auf R3, während SRC sendet", "`(192.168.1.10, 239.1.1.1), RP 10.255.0.2`"),
                  ("Pings von SRC an 232.1.1.1, 239.1.1.1 und 239.2.1.1", "jeweils Antwort von 192.168.4.10")],
    teilc=[("Ein Empfänger meldet sich per IGMPv2 für 232.5.5.5 an. Die Router haben `ip pim ssm default`. Was passiert?",
            "**Nichts, der Beitritt wird ignoriert.** 232.0.0.0/8 ist der SSM-Bereich. Dort gibt es kein `(*,G)` und keinen RP. Ohne Quellangabe (IGMPv3 INCLUDE) kann der Router keinen Baum bauen. Abhilfe: IGMPv3 auf Host und Router, oder auf dem Router eine SSM-Zuordnung (`ip igmp ssm-map`), die v2-Beitritten eine Quelle zuweist."),
           ("In `show ip mroute` steht `(*, 239.2.1.1)` mit Flag `B` und mehreren Interfaces, aber kein `(S,G)`, obwohl gerade zwanzig Quellen senden. Ist das ein Fehler?",
            "**Nein, das ist Bidir-PIM.** Alle Quellen teilen sich den einen `(*,G)`-Eintrag. Genau das ist der Vorteil: Der Zustand im Router wächst nicht mit der Zahl der Quellen. Der Preis ist, dass der Verkehr immer über den Weg zum RP läuft und nie auf einen kürzeren Quellbaum wechselt."),
           ("Zwei RPs mit Anycast-Adresse, MSDP-Sitzung ist `Up`, aber der SA-Cache bleibt leer. Nenne zwei mögliche Ursachen.",
            "**(1) Der RP, bei dem die Quelle registriert, erkennt sich nicht als RP** (kein PIM auf dem RP-Interface, falsche Gruppen-ACL), er erzeugt also keine SA. **(2) Es sendet gerade keine Quelle.** SA-Einträge entstehen nur für aktive Quellen und altern nach kurzer Zeit aus. Dazu kommen SA-Filter und ein fehlgeschlagener RPF-Check auf den Peer, wenn es mehrere MSDP-Peers gibt."),
           ("Warum prüft Bidir-PIM eingehende Pakete nicht per RPF gegen die Quelle?",
            "**Weil Daten auf dem Shared Tree in beide Richtungen fließen.** Ein Paket von der Quelle zum RP kommt aus Sicht des klassischen RPF-Checks auf dem „falschen“ Interface an. Bidir ersetzt den Check durch den Designated Forwarder: Pro Segment darf nur der DF Pakete in Richtung RP annehmen und weiterleiten.")],
    exam=["SSM: Bereich 232.0.0.0/8, kein RP, nur `(S,G)`, braucht IGMPv3 (oder `ssm-map`).",
          "Bidir-PIM: nur `(*,G)`, keine Register-Nachricht, kein SPT-Wechsel, Schleifenschutz über den DF pro Segment.",
          "MSDP: TCP 639 zwischen RPs, Source-Active-Meldungen mit Quelle, Gruppe und erzeugendem RP.",
          "Anycast-RP: gleiche RP-Adresse auf mehreren Routern, Auswahl und Ausfallschutz über das Unicast-Routing, MSDP gleicht die Quellen ab.",
          "IGMPv2: Leave und gruppenspezifische Query. IGMPv3: Quellfilter INCLUDE/EXCLUDE, Reports an 224.0.0.22.",
          "Flags in `show ip mroute`: `s` SSM, `B` Bidir, `T` SPT-Bit, `M` per MSDP gelernt, `A` Kandidat für MSDP-Ankündigung."],
    caveat=("Die Flags und Zustandsnamen stammen aus der IOS-15-Dokumentation. Zeigt dein IOSv-Image bei Ticket 4 ein anderes "
            "Detail (etwa eine andere Debug-Meldung), zählt der Befund: Loopback1 fehlt in `show ip pim interface`. Bidir-PIM "
            "läuft in IOSv in Software und reagiert nach einer Änderung manchmal erst nach `clear ip mroute *`."),
)

# Live-Test: je Fehler einspielen (inject), zurücknehmen (revert) und eine Probe, die nur im gesunden Zustand passt.
_BOUNCE = ["interface GigabitEthernet0/0", "shutdown", "no shutdown"]
LIVE = [
    dict(inject={"R4": ["interface GigabitEthernet0/1", "no ip igmp version 3"], "REC": _BOUNCE},
         revert={"R4": ["interface GigabitEthernet0/1", "ip igmp version 3"], "REC": _BOUNCE},
         probe=("R4", "show ip mroute 232.1.1.1", r"192\.168\.1\.10, 232\.1\.1\.1"), settle=90),
    dict(inject=["no ip pim rp-address 10.255.0.200 20 bidir", "ip pim rp-address 10.255.0.200 20"],
         revert=["no ip pim rp-address 10.255.0.200 20", "ip pim rp-address 10.255.0.200 20 bidir"],
         probe=("R3", "show ip pim rp mapping", r"(?i)bidir"), settle=10),
    dict(inject=["no ip msdp peer 10.255.0.2", "ip msdp peer 10.255.0.4 connect-source Loopback0"],
         revert=["no ip msdp peer 10.255.0.4", "ip msdp peer 10.255.0.2 connect-source Loopback0"],
         probe=("R3", "show ip msdp summary", r"10\.255\.0\.2\s.*Up"), settle=100),
    dict(inject=["interface Loopback1", "no ip pim sparse-mode"], revert=["interface Loopback1", "ip pim sparse-mode"],
         probe=("R2", "show ip pim interface", r"Loopback1"), settle=10)]
for _f, _l in zip(LAB["faults"], LIVE):
    _f.update(_l)
LAB["settle"] = 150
LAB["checks"] = [("R2", "show ip msdp summary", r"10\.255\.0\.3\s.*Up"), ("R2", "show ip pim rp mapping", r"(?i)bidir"),
                 ("R4", "show ip mroute 232.1.1.1", r"192\.168\.1\.10, 232\.1\.1\.1"),
                 ("SRC", "ping 232.1.1.1 repeat 5", r"Reply to request"), ("SRC", "ping 239.2.1.1 repeat 5", r"Reply to request"),
                 ("SRC", "ping 239.1.1.1 repeat 10", r"Reply to request")]
