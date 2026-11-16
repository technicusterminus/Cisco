def lo(n, addr, mask="255.255.255.0"):
    return f"interface Loopback{n}\n ip address {addr} {mask}"


def gi(n, addr):
    return f"interface GigabitEthernet0/{n}\n ip address {addr} 255.255.255.252\n no shutdown"


def ospf_if(name, area, p2p=True):
    return f"interface {name}\n" + (" ip ospf network point-to-point\n" if p2p else "") + f" ip ospf 1 area {area}"


ANY = "permit 0.0.0.0/0 le 32"

LAB = dict(
    slug="34-OSPF-Filter-Netztyp-MTU", num="34",
    title="OSPF: Routen filtern (ABR, ASBR, lokal) und Nachbarschaften mit Netztyp- und MTU-Fehlern", minutes=110, level="schwer",
    summary=("Das Blueprint nennt bei OSPF ausdrücklich Filterung, Nachbarschaft und die Netztypen Point-to-Point und "
             "Broadcast. Lab 01 und 28 decken Areas, Summaries und Authentisierung ab, gefiltert wird dort nicht. Hier "
             "lernst du die vier Stellen kennen, an denen OSPF Routen zurückhalten kann, und warum es innerhalb einer Area "
             "keine fünfte gibt. Dazu kommen zwei Nachbarschaftsfehler, die in `show ip ospf neighbor` harmlos aussehen."),
    goals=["Type-3-LSAs am ABR mit `area … filter-list` in beide Richtungen filtern und die Richtung begründen.",
           "`area range … not-advertise`, `distribute-list in` und eine Route-Map an der Redistribution voneinander abgrenzen.",
           "Erklären, warum `distribute-list in` die LSDB nicht verändert und wann das gefährlich wird.",
           "Einen Netztyp-Konflikt (Nachbar FULL, aber keine Routen) und einen MTU-Konflikt (EXSTART) erkennen.",
           "Zu einer Vorgabe („Area 2 darf Netz X nicht sehen“) das passende Werkzeug und den richtigen Router wählen."],
    tags=[("3.2.b", "OSPFv2 und OSPFv3", 86)],
    diagram="""
        Area 1                    Area 0                    Area 2
  R3 ──────────────── R2 ──────────────── R1 ──────────────── R4
     Gi0/0      Gi0/1    Gi0/0      Gi0/0    Gi0/1      Gi0/0
  Lo16–19                (ABR)             (ABR)           Lo20, Lo21
  10.1.16–19.0/24                                          10.2.20.0/24, 10.2.21.0/24
                                                           statisch: 198.51.100.0/24, 203.0.113.0/24 (ASBR)
""",
    nets=[("R1 Gi0/0 – R2 Gi0/0", "10.0.12.0/30 (.1/.2), Area 0"), ("R2 Gi0/1 – R3 Gi0/0", "10.0.23.0/30 (.1/.2), Area 1"),
          ("R1 Gi0/1 – R4 Gi0/0", "10.0.14.0/30 (.1/.2), Area 2"),
          ("R3 Loopback16 bis 19", "10.1.16.1/24 bis 10.1.19.1/24, Area 1"),
          ("R4 Loopback20, 21", "10.2.20.1/24, 10.2.21.1/24, Area 2"),
          ("R4 statisch auf Null0", "198.51.100.0/24 und 203.0.113.0/24")],
    topo_text=("Loopback0: R1 10.255.0.1 bis R4 10.255.0.4 (/32), jeweils in der Area des Routers (R1 und R2 in Area 0). "
               "Adressen und die beiden statischen Routen auf R4 sind vorhanden, OSPF baust du selbst.\n\n"
               "**Vorgaben, die am Ende gelten sollen:**\n\n"
               "1. Area 1 erscheint außerhalb als 10.1.16.0/23 plus 10.1.18.0/24.\n"
               "2. 10.1.19.0/24 verlässt Area 1 nie.\n"
               "3. Area 2 kennt 10.1.18.0/24 nicht, Area 0 schon.\n"
               "4. R3 trägt 10.2.21.0/24 nicht in seine Routing-Tabelle ein.\n"
               "5. Von den statischen Routen auf R4 gelangt nur 198.51.100.0/24 ins OSPF."),
    steps=[
        dict(t="OSPF aufbauen.", body="Starte auf allen Routern `router ospf 1` mit der Loopback0-Adresse als Router-ID. Aktiviere OSPF am Interface (`ip ospf 1 area X`) laut Skizze. Setze auf allen Gi-Links und allen Loopbacks außer Loopback0 `ip ospf network point-to-point`.",
             check="`show ip ospf neighbor` zeigt überall `FULL/  -`. R4 sieht 10.1.16.0/24 bis 10.1.19.0/24 als `O IA` mit Maske /24.",
             think="Warum steht bei den Nachbarn kein DR? Und wozu der Netztyp an den Loopbacks?"),
        dict(t="Netztyp-Konflikt.", body="Entferne auf R1 Gi0/0 `ip ospf network point-to-point`, R2 bleibt unverändert. Warte eine Minute.",
             predict="Bleibt die Nachbarschaft R1–R2 bestehen? Und was steht danach in `show ip route ospf` auf R1?",
             check="`show ip ospf neighbor` zeigt auf beiden Seiten wieder `FULL`. `show ip route ospf` auf R1 enthält trotzdem keine Route mehr, die über R2 führt. `show ip ospf interface Gi0/0 | include Network Type` nennt auf R1 BROADCAST, auf R2 POINT_TO_POINT. Stelle den Netztyp danach wieder her.",
             think="Die Hello-Timer passen (10/40), deshalb kommt die Nachbarschaft zustande. Warum rechnet SPF den Link dann nicht ein?"),
        dict(t="MTU-Konflikt.", body="Setze auf R3 Gi0/0 `ip mtu 1400` und führe dort `clear ip ospf process` aus.",
             predict="In welchem Zustand bleibt die Nachbarschaft R2–R3 stehen?",
             check="`show ip ospf neighbor` auf R2 zeigt R3 dauerhaft in `EXSTART`. `debug ip ospf adj` meldet, dass der Nachbar eine größere bzw. kleinere Interface-MTU hat. Entferne `ip mtu 1400` wieder.",
             think="`ip ospf mtu-ignore` würde die Nachbarschaft herstellen. Warum ist das meist die falsche Lösung?"),
        dict(t="Zusammenfassen.", body="Setze auf R2 `area 1 range 10.1.16.0 255.255.254.0`.",
             predict="Welche Routen aus Area 1 sieht R1 jetzt, und welche neue Route erscheint auf R2 selbst?",
             check="R1: 10.1.16.0/23, 10.1.18.0/24, 10.1.19.0/24 als `O IA`. R2: zusätzlich `O 10.1.16.0/23 is a summary, Null0`."),
        dict(t="Filtern beim Verlassen einer Area.", body="Vorgabe 2. Lege auf R2 die Prefix-Liste `A1-OUT` an (`deny 10.1.19.0/24`, dann `permit 0.0.0.0/0 le 32`) und setze `area 1 filter-list prefix A1-OUT out`.",
             predict="Auf welchen Routern verschwindet 10.1.19.0/24: R1, R2, R4?",
             check="R1 und R4 kennen das Netz nicht mehr, `show ip ospf database summary 10.1.19.0` ist dort leer. R2 hat es weiter als `O` (Intra-Area).",
             think="Was wäre passiert, wenn du die Zeile `permit 0.0.0.0/0 le 32` vergessen hättest?"),
        dict(t="Filtern beim Eintritt in eine Area.", body="Vorgabe 3. Lege auf R1 die Prefix-Liste `A2-IN` an (`deny 10.1.18.0/24`, dann alles erlauben) und setze `area 2 filter-list prefix A2-IN in`.",
             predict="Hat R1 selbst die Route 10.1.18.0/24 noch?",
             check="R1: ja, als `O IA`. R4: nein. 10.1.16.0/23 ist auf R4 weiter vorhanden.",
             think="`in` und `out` beziehen sich auf die genannte Area, nicht auf ein Interface. Formuliere beide Richtungen in einem Satz."),
        dict(t="`not-advertise` zum Vergleich.", body="Ändere auf R2 testweise die Zeile zu `area 1 range 10.1.16.0 255.255.254.0 not-advertise`.",
             predict="Was sieht R1 jetzt von 10.1.16.0/24 und 10.1.17.0/24?",
             check="Weder die Summary noch die beiden Einzelnetze erscheinen auf R1. Stelle danach die Zeile ohne `not-advertise` wieder her."),
        dict(t="Lokal filtern.", body="Vorgabe 4. Lege auf R3 die Prefix-Liste `NO-21` an (`deny 10.2.21.0/24`, dann alles erlauben) und setze unter `router ospf 1` den Befehl `distribute-list prefix NO-21 in`.",
             predict="Zwei Fragen: Steht 10.2.21.0/24 noch in `show ip route` auf R3? Steht es noch in `show ip ospf database summary 10.2.21.0` auf R3?",
             check="Routing-Tabelle: nein. LSDB: ja, unverändert.",
             think="Warum kann OSPF innerhalb einer Area keine LSAs filtern? Und wann erzeugt `distribute-list in` ein schwarzes Loch?"),
        dict(t="Am ASBR filtern.", body="Vorgabe 5. Lege auf R4 die Prefix-Liste `EXT-OK` (`permit 198.51.100.0/24`) und die Route-Map `EXT` an, die nur diese Liste erlaubt. Verteile mit `redistribute static subnets route-map EXT`.",
             check="R3 hat `O E2 198.51.100.0/24`. 203.0.113.0/24 fehlt überall außer auf R4. `show ip ospf database external` zeigt genau ein Type-5-LSA.",
             think="Welche Alternative gibt es am ASBR, um eine externe Route zu unterdrücken, ohne die Route-Map anzufassen?"),
        dict(t="Zuordnen.", body="Fülle aus dem Gedächtnis aus: Für **`area filter-list`**, **`area range not-advertise`**, **`distribute-list in`**, **Route-Map an `redistribute`** und **`summary-address not-advertise`** jeweils: Auf welchem Router? Welcher LSA-Typ ist betroffen? Wirkt es auf andere Router?")],
    answers=[
        ("1", "Auf einem Point-to-Point-Link gibt es nur zwei Router, eine DR-Wahl wäre überflüssig und kostet beim Start 40 Sekunden Wartezeit. Loopbacks meldet OSPF sonst als Host-Route /32, egal welche Maske konfiguriert ist. Mit dem Netztyp Point-to-Point erscheint die echte Maske."),
        ("2", "Die Nachbarschaft wird wieder **FULL**, aber die Routen fehlen. R1 beschreibt den Link in seinem Router-LSA als Transit-Netz mit einem DR und erwartet ein Network-LSA. R2 beschreibt denselben Link als Point-to-Point direkt zum Nachbarn. Die beiden Beschreibungen passen nicht zusammen, SPF findet keine beidseitige Verbindung und lässt den Link aus. FULL heißt nur: Die Datenbanken sind gleich. Es heißt nicht, dass ihr Inhalt einen Weg ergibt."),
        ("3", "In **EXSTART** (teils im Wechsel mit EXCHANGE). Die MTU steht im Database-Description-Paket. Ist die des Nachbarn größer als die eigene, verwirft der Router das Paket. `ip ospf mtu-ignore` schaltet nur die Prüfung ab. Die MTU bleibt ungleich, große LSA-Pakete und später der Nutzverkehr können trotzdem hängen bleiben. Richtig ist, die MTU auf beiden Seiten gleich zu setzen."),
        ("4", "R1 sieht die Summary 10.1.16.0/23 statt .16 und .17, dazu .18 und .19 einzeln, weil sie außerhalb des Bereichs liegen. R2 legt eine Discard-Route auf Null0 an: Pakete an einen nicht vorhandenen Teil der Summary werden verworfen statt einer Default-Route zu folgen (Schleifenschutz)."),
        ("5", "Auf **R1 und R4**. R2 behält die Route, denn es ist selbst Mitglied von Area 1 und rechnet sie aus den Type-1-LSAs. Der Filter wirkt nur auf die Type-3-LSAs, die R2 aus Area 1 heraus erzeugt. Ohne die `permit`-Zeile greift das stille `deny` am Ende jeder Prefix-Liste: Kein einziges Netz aus Area 1 käme mehr hinaus."),
        ("6", "**Ja.** R1 erhält das Type-3-LSA in Area 0 und nutzt es. Der Filter verhindert nur, dass R1 es nach Area 2 weitergibt. Merksatz: `area X filter-list … in` filtert, was **in Area X hinein** angekündigt wird, `out` filtert, was **aus Area X heraus** angekündigt wird. Beides passiert auf dem ABR dieser Area."),
        ("7", "**Nichts mehr.** `not-advertise` unterdrückt die Summary und zugleich alle Einzelnetze, die in den Bereich fallen. Es ist die kürzeste Art, einen ganzen Adressblock zu verbergen."),
        ("8", "Routing-Tabelle **nein**, LSDB **ja**. Alle Router einer Area müssen dieselbe Datenbank haben, sonst rechnet SPF auf jedem Router einen anderen Baum und es entstehen Schleifen. Deshalb filtert `distribute-list in` erst nach der SPF-Berechnung, beim Eintrag in die eigene Tabelle. Gefährlich wird es, wenn ein Router auf dem Transitweg filtert: Seine Nachbarn schicken ihm weiter Pakete für das Netz, er selbst hat keine Route und verwirft sie."),
        ("9", "`summary-address 203.0.113.0 255.255.255.0 not-advertise` unter `router ospf`. Das wirkt auf externe Routen am ASBR so wie `area range … not-advertise` auf Inter-Area-Routen am ABR."),
        ("10", "**`area filter-list`:** ABR, Type 3, wirkt auf alle Router dahinter. **`area range not-advertise`:** ABR, Type 3 für einen ganzen Block. **`distribute-list in`:** jeder Router, kein LSA betroffen, wirkt nur lokal. **Route-Map an `redistribute`:** ASBR, Type 5 (oder 7), wirkt auf alle. **`summary-address not-advertise`:** ASBR, Type 5/7.")],
    nodes=[
        dict(name="R1", type="router", x=400, y=200,
             base="\n".join([lo(0, "10.255.0.1", "255.255.255.255"), gi(0, "10.0.12.1"), gi(1, "10.0.14.1")]),
             sol="\n".join([f"ip prefix-list A2-IN seq 5 deny 10.1.18.0/24", f"ip prefix-list A2-IN seq 10 {ANY}",
                            "router ospf 1", " router-id 10.255.0.1", " area 2 filter-list prefix A2-IN in",
                            ospf_if("Loopback0", 0, False), ospf_if("GigabitEthernet0/0", 0), ospf_if("GigabitEthernet0/1", 2)])),
        dict(name="R2", type="router", x=200, y=200,
             base="\n".join([lo(0, "10.255.0.2", "255.255.255.255"), gi(0, "10.0.12.2"), gi(1, "10.0.23.1")]),
             sol="\n".join([f"ip prefix-list A1-OUT seq 5 deny 10.1.19.0/24", f"ip prefix-list A1-OUT seq 10 {ANY}",
                            "router ospf 1", " router-id 10.255.0.2", " area 1 range 10.1.16.0 255.255.254.0",
                            " area 1 filter-list prefix A1-OUT out",
                            ospf_if("Loopback0", 0, False), ospf_if("GigabitEthernet0/0", 0), ospf_if("GigabitEthernet0/1", 1)])),
        dict(name="R3", type="router", x=0, y=200,
             base="\n".join([lo(0, "10.255.0.3", "255.255.255.255"), gi(0, "10.0.23.2")] + [lo(k, f"10.1.{k}.1") for k in range(16, 20)]),
             sol="\n".join([f"ip prefix-list NO-21 seq 5 deny 10.2.21.0/24", f"ip prefix-list NO-21 seq 10 {ANY}",
                            "router ospf 1", " router-id 10.255.0.3", " distribute-list prefix NO-21 in",
                            ospf_if("Loopback0", 1, False), ospf_if("GigabitEthernet0/0", 1)]
                           + [ospf_if(f"Loopback{k}", 1) for k in range(16, 20)])),
        dict(name="R4", type="router", x=600, y=200,
             base="\n".join([lo(0, "10.255.0.4", "255.255.255.255"), gi(0, "10.0.14.2"), lo(20, "10.2.20.1"), lo(21, "10.2.21.1"),
                             "ip route 198.51.100.0 255.255.255.0 Null0", "ip route 203.0.113.0 255.255.255.0 Null0"]),
             sol="\n".join(["ip prefix-list EXT-OK seq 5 permit 198.51.100.0/24", "route-map EXT permit 10",
                            " match ip address prefix-list EXT-OK", "router ospf 1", " router-id 10.255.0.4",
                            " redistribute static subnets route-map EXT",
                            ospf_if("Loopback0", 2, False), ospf_if("GigabitEthernet0/0", 2), ospf_if("Loopback20", 2),
                            ospf_if("Loopback21", 2)]))],
    links=[("R1", "Gi0/0", "R2", "Gi0/0"), ("R2", "Gi0/1", "R3", "Gi0/0"), ("R1", "Gi0/1", "R4", "Gi0/0")],
    staggered=True,
    tickets=["R1 und R2 zeigen einander als `FULL`, aber R1 lernt keine einzige Route über R2 und umgekehrt.",
             "R3 kommt mit R2 nicht über `EXSTART` hinaus.",
             "Aus Area 1 ist außerhalb gar kein Netz mehr sichtbar, auch die Summary 10.1.16.0/23 nicht. Innerhalb von Area 1 ist alles in Ordnung.",
             "R4 hat eine Route nach 10.1.18.0/24. Laut Vorgabe 3 darf Area 2 dieses Netz nicht kennen.",
             "198.51.100.0/24 fehlt im ganzen Netz als externe Route. Auf R4 ist die statische Route vorhanden."],
    faults=[
        dict(node="R1", old=" ip ospf network point-to-point", new=None, nth=0,
             find="`show ip ospf interface GigabitEthernet0/0 | include Network Type` nennt auf R1 BROADCAST, auf R2 POINT_TO_POINT. `show ip ospf neighbor` zeigt auf R1 eine DR-Rolle, auf R2 einen Strich.",
             cause="Netztyp-Konflikt. Die Hello-Timer passen, also wird die Nachbarschaft FULL. Die Router beschreiben den Link in ihren LSAs aber unterschiedlich, SPF verwirft ihn.",
             fix="`ip ospf network point-to-point` auf R1 Gi0/0."),
        dict(node="R3", old=None, ctx="interface GigabitEthernet0/0", new=" ip mtu 1400",
             find="`show ip ospf neighbor` auf R2: R3 in EXSTART. `show ip interface GigabitEthernet0/0 | include MTU` zeigt auf R3 1400, auf R2 Gi0/1 1500. `debug ip ospf adj` nennt die MTU-Abweichung.",
             cause="Die IP-MTU der beiden Seiten ist ungleich. Der Router mit der kleineren MTU verwirft die Database-Description-Pakete des Nachbarn.",
             fix="`no ip mtu 1400` auf R3 Gi0/0 (nicht `ip ospf mtu-ignore`)."),
        dict(node="R2", old="ip prefix-list A1-OUT seq 10 permit 0.0.0.0/0 le 32", new=None,
             find="`show ip prefix-list A1-OUT` auf R2 enthält nur die `deny`-Zeile. `show ip ospf database summary` auf R1 zeigt kein LSA für Netze aus Area 1.",
             cause="Jede Prefix-Liste endet mit einem stillen `deny`. Ohne die `permit`-Zeile filtert `area 1 filter-list … out` alles, auch die Summary.",
             fix="`ip prefix-list A1-OUT seq 10 permit 0.0.0.0/0 le 32` auf R2."),
        dict(node="R1", old=" area 2 filter-list prefix A2-IN in", new=" area 2 filter-list prefix A2-IN out",
             find="`show running-config | section router ospf` auf R1: Die Filterliste hängt mit `out` an Area 2. `show ip ospf database summary 10.1.18.0` auf R4 zeigt das LSA mit R1 als Absender.",
             cause="`out` filtert, was aus Area 2 heraus angekündigt wird. 10.1.18.0/24 kommt aber von außen in die Area hinein, die Liste trifft nie.",
             fix="Auf R1: `no area 2 filter-list prefix A2-IN out`, dann `area 2 filter-list prefix A2-IN in`."),
        dict(node="R4", old="ip prefix-list EXT-OK seq 5 permit 198.51.100.0/24", new="ip prefix-list EXT-OK seq 5 permit 198.51.100.0/25",
             find="`show ip ospf database external` ist leer. `show route-map EXT` zählt keine Treffer. `show ip prefix-list EXT-OK` nennt /25, die statische Route ist /24.",
             cause="Eine Prefix-Liste ohne `ge`/`le` verlangt die exakte Präfixlänge. /25 passt nicht auf die /24-Route, die Route-Map verwirft sie.",
             fix="Prefix-Liste auf `permit 198.51.100.0/24` korrigieren.")],
    verify=["show ip ospf neighbor", "show ip ospf interface brief", "show ip route ospf",
            "show ip ospf database summary               ! Type 3", "show ip ospf database external              ! Type 5",
            "show ip prefix-list", "show route-map EXT                          ! auf R4"],
    verify_table=[("`show ip route ospf` auf R1", "10.1.16.0/23 und 10.1.18.0/24 als `O IA`, kein 10.1.19.0/24"),
                  ("`show ip route ospf` auf R4", "10.1.16.0/23 als `O IA`, weder 10.1.18.0/24 noch 10.1.19.0/24"),
                  ("`show ip route 10.2.21.0` auf R3", "kein Treffer (oder nur eine Default-Route), 10.2.20.0/24 ist vorhanden"),
                  ("`show ip route ospf` auf R3", "`O E2 198.51.100.0/24`, kein 203.0.113.0/24"),
                  ("`show ip ospf neighbor` überall", "`FULL/  -`")],
    checks=[("R1", "show ip route ospf", r"10\.1\.16\.0/23"), ("R1", "show ip route ospf", r"10\.1\.18\.0/24"),
            ("R3", "show ip route ospf", r"198\.51\.100\.0/24"), ("R2", "show ip ospf neighbor", r"10\.255\.0\.3\s+\d+\s+FULL")],
    teilc=[("Vorgabe: „Area 2 soll von außen nur eine Default-Route sehen.“ Brauchst du dafür eine Filterliste?",
            "**Nein, das ist eine Totally Stubby Area.** `area 2 stub no-summary` auf dem ABR, `area 2 stub` auf den übrigen Routern. Der ABR ersetzt dann alle Type-3- und Type-5-LSAs durch eine Default-Route. Weil R4 hier ASBR ist, müsste es `area 2 nssa no-summary` sein. Eine Filterliste ist das Werkzeug für einzelne Netze, nicht für „alles“."),
           ("Zwei Router sind über Ethernet verbunden, einer mit Netztyp Broadcast, einer mit Point-to-Multipoint. Kommt die Nachbarschaft zustande?",
            "**Nein, schon die Hellos passen nicht.** Broadcast und Point-to-Point nutzen 10/40 Sekunden, Point-to-Multipoint und Non-Broadcast 30/120. Unterschiedliche Timer verhindern die Nachbarschaft. Gefährlicher ist die Kombination Broadcast und Point-to-Point: gleiche Timer, Nachbarschaft FULL, aber keine Routen."),
           ("Warum filtert `distribute-list out` unter `router ospf` keine normalen OSPF-Routen?",
            "**Weil OSPF keine Routen verschickt, sondern LSAs.** `distribute-list out` wirkt in OSPF nur auf Routen, die per Redistribution in den Prozess kommen, also am ASBR. Für alles andere gibt es `area filter-list` am ABR."),
           ("Ein Nachbar hängt in `2WAY`. Fehler?",
            "**Auf einem Broadcast-Segment zwischen zwei DROTHER-Routern ist das normal.** Volle Nachbarschaft gibt es nur mit DR und BDR. Ein Fehler ist es, wenn *kein* Router DR werden kann (alle mit Priorität 0) oder wenn der Link Point-to-Point sein sollte.")],
    exam=["Filterstellen: ABR (Type 3: `area filter-list`, `area range not-advertise`), ASBR (Type 5/7: Route-Map, `summary-address not-advertise`), lokal (`distribute-list in`, nur RIB).",
          "Innerhalb einer Area wird nicht gefiltert: gleiche LSDB für alle.",
          "Nachbarschaft braucht: gleiches Subnetz, gleiche Area, gleiche Timer, gleichen Area-Typ, gleiche Authentisierung, eindeutige Router-ID, passende MTU.",
          "Zustände: DOWN, INIT, 2WAY, EXSTART, EXCHANGE, LOADING, FULL. EXSTART hängt bei MTU-Konflikt.",
          "Netztypen: Broadcast und NBMA wählen DR/BDR, Point-to-Point und Point-to-Multipoint nicht. Timer 10/40 oder 30/120.",
          "Prefix-Liste: ohne `ge`/`le` exakte Länge, am Ende stilles `deny`."],
)

# Live-Test: je Fehler einspielen (inject), zurücknehmen (revert) und eine Probe, die nur im gesunden Zustand passt.
LIVE = [
    dict(inject=["interface GigabitEthernet0/0", "no ip ospf network point-to-point"],
         revert=["interface GigabitEthernet0/0", "ip ospf network point-to-point"],
         probe=("R1", "show ip route ospf", r"10\.1\.16\.0/23"), settle=70),
    dict(inject=["interface GigabitEthernet0/0", "ip mtu 1400", "shutdown", "no shutdown"],
         revert=["interface GigabitEthernet0/0", "no ip mtu 1400", "shutdown", "no shutdown"],
         probe=("R2", "show ip ospf neighbor", r"10\.255\.0\.3\s+\d+\s+FULL"), settle=40),
    dict(inject=["no ip prefix-list A1-OUT seq 10"], revert=["ip prefix-list A1-OUT seq 10 permit 0.0.0.0/0 le 32"],
         probe=("R1", "show ip route ospf", r"10\.1\.16\.0/23"), settle=20),
    dict(inject=["router ospf 1", "no area 2 filter-list prefix A2-IN in", "area 2 filter-list prefix A2-IN out"],
         revert=["router ospf 1", "no area 2 filter-list prefix A2-IN out", "area 2 filter-list prefix A2-IN in"],
         probe=("R4", "show ip route 10.1.18.0", r"not in table"), settle=20),
    dict(inject=["no ip prefix-list EXT-OK seq 5", "ip prefix-list EXT-OK seq 5 permit 198.51.100.0/25"],
         revert=["no ip prefix-list EXT-OK seq 5", "ip prefix-list EXT-OK seq 5 permit 198.51.100.0/24"],
         probe=("R3", "show ip route ospf", r"198\.51\.100\.0/24"), settle=20)]
for _f, _l in zip(LAB["faults"], LIVE):
    _f.update(_l)
LAB["settle"] = 90
LAB["checks"] += [("R4", "show ip route ospf", r"10\.1\.16\.0/23"), ("R3", "show ip route 10.2.21.0", r"not in table")]
