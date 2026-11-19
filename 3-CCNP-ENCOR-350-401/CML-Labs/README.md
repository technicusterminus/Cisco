# CCNP ENCOR 350-401 v1.2 – Labs zum Kompendium

Diese Labs ergänzen das Anki-Kompendium (1.845 Karten). Die Karten bauen Wissen auf, in den Labs wendest du es an: **bauen, reparieren, üben**. Jedes der 47 Prüfungsziele des Kompendiums (`Ziel::…`) ist mindestens einem Lab zugeordnet.

**Inhalt:** 33 CML-Labs (30 Themen-Labs und 3 Capstones, 157 Fehler zum Reparieren in CML plus zwei Tickets zur Spiegelung auf Papier), ein Python-/API-Drill-Paket mit automatischen Tests, zwei Fallstudien-Pakete für Themen, die sich nicht sinnvoll simulieren lassen.

**Andere Plattformen:** Dieselben Labs gibt es für [Packet Tracer](../Packet-Tracer-Labs/) (soweit PT die Funktionen kann) und [EVE-NG](../EVE-NG-Labs/).

## Trainingscurriculum

[Curriculum und Blueprint-Matrix](CURRICULUM.md) · [Aufgaben ohne Befehlsliste](AUFGABEN.md) · [Hinweise, Nachweise und Lösungen](NACHWEISE.md)

Zusätzlich zu den 33 nummerierten CML-Labs verbindet die [Praxisstrecke Routing Assurance](Routing-Assurance/README.md) OSPF, direktes eBGP und IP SLA auf drei IOSv-Routern. Zwei importierbare Startstände trainieren Pfadwechsel und die Diagnose eines einzelnen ausgefallenen Dienstes.

Für den Einstieg importiere die Bauvariante und öffne den Guide. Die bisherigen README-Schritte kannst du bei Bedarf als geführte Fassung verwenden. Für Transfer startest du 23, 24 und 30 aus der jeweiligen Reparaturdatei.

## So ist jedes CML-Lab aufgebaut

| Datei | Zweck |
|---|---|
| `topology.yaml` | **Bauen:** Topologie mit Basis-Konfiguration und den Voraussetzungen der Aufgabe. Bei Multicast, VXLAN und PBR ist das benötigte Unicast-Routing beispielsweise bereits gesetzt. Das jeweilige Lernziel konfigurierst und verifizierst du selbst. |
| `topology-repair.yaml` | **Reparieren:** konfigurierte Topologie mit eingebauten Fehlern. Die Tickets stehen im CML-Guide und im README, die Auflösung in `solutions/FAULTS.md`. |
| `README.md` | Teil A Aufgaben, Teil B Tickets, Verifikation, Teil C Transferfragen mit Antworten, Prüfungsbezug |
| `solutions/*.cfg` | Musterlösung je Gerät (ohne Basis-IP-Adressen) |

**CML-Workbench:** Blaue Kopfboxen kennzeichnen Teil A, ockerfarbene Teil B. Farbige Kästen gruppieren Netzrollen und Standorte. Öffne den **Guide** für die Aufgaben der geladenen Variante. Im README stehen zusätzlich Topologie, Hintergrund und Transferfragen. Über **Canvas Settings → Annotations** blendest du die Kästen ein.

**IOSvL2 und Trunks:** Die Switch-Images unterstützen ISL und Dot1Q. Vor `switchport mode trunk` muss deshalb `switchport trunk encapsulation dot1q` stehen, sonst lehnt der Switch den Trunk-Modus ab. Topologien und Lösungen enthalten die Zeile.

## So arbeitest du ein Lab durch

1. **Teil A: Bauen.** Lies zuerst das Ziel des Labs und die Skizze. Baue dann Schritt für Schritt und prüfe jeden Schritt mit den Befehlen aus „Verifikation“. Erst am Ende vergleichst du mit `solutions/`.
2. **Teil B: Reparieren.** Am besten an einem anderen Tag. Lade die Reparatur-Topologie, lies das Ticket und gehe vor wie im Betrieb: Symptom nachstellen, eingrenzen, beheben, verifizieren. Erst nach 20 Minuten ohne Fortschritt in `solutions/FAULTS.md` schauen. Dort steht pro Ticket zuerst, mit welchem Befehl du den Fehler gefunden hättest, dann Ursache und Lösung.
3. **Teil C: Üben.** Beantworte die Transferfragen erst selbst, dann klappst du die Antwort auf.
4. **Nacharbeiten.** Wiederhole im Anki-Deck die Karten zum Ziel des Labs (`tag:Ziel::…`), besonders zu den Fehlern, die du nicht gefunden hast.

## Übersicht

| Lab | Thema | Ziele | Geräte | Fehler | Dauer |
|---|---|---|---|---|---|
| [01](01-OSPFv2-Multiarea/) | OSPFv2 Multi-Area | 3.2.a, 3.2.b | 4 | 4 | 90 min |
| [02](02-EIGRP-OSPFv3/) | EIGRP (Named Mode) und OSPFv3 | 3.2.a, 3.2.b | 3 | 4 | 90 min |
| [03](03-eBGP-Policy/) | eBGP Dual-Homing und Policy | 3.2.c | 4 | 5 | 90 min |
| [04](04-PBR-IPSLA/) | Policy-Based Routing mit IP SLA | 3.2.d, 4.4 | 6 | 4 | 75 min |
| [05](05-VLAN-Trunk-EtherChannel/) | VLANs, Trunks und EtherChannel | 3.1.a, 3.1.b | 7 | 4 | 90 min |
| [06](06-STP-MST-Schutz/) | Spanning Tree, MST und Schutzfunktionen | 3.1.c | 7 | 3 | 90 min |
| [07](07-FHRP-HSRP-VRRP-GLBP/) | First-Hop-Redundanz: HSRP, VRRP und GLBP | 3.3.c, 1.1.b | 8 | 4 | 90 min |
| [08](08-NTP-Syslog-SNMP/) | NTP, Syslog und SNMPv3 | 3.3.a, 4.1 | 3 | 4 | 75 min |
| [09](09-NAT-PAT/) | NAT und PAT | 3.3.b | 5 | 4 | 75 min |
| [10](10-ACL-CoPP/) | ACLs und Control-Plane Policing | 5.2.a, 5.2.b | 5 | 4 | 90 min |
| [11](11-Zugriff-AAA/) | Gerätezugriff und AAA | 5.1.a, 5.1.b | 2 | 4 | 75 min |
| [12](12-Multicast-PIM/) | Multicast mit IGMP und PIM Sparse Mode | 3.3.d | 7 | 4 | 90 min |
| [13](13-VRF-Lite/) | VRF-Lite mit überlappenden Adressen | 2.2.a | 6 | 4 | 75 min |
| [14](14-GRE-IPsec/) | GRE, IPsec und VTI | 2.2.b | 3 | 5 | 90 min |
| [15](15-LISP/) | LISP: Map-Server, Map-Resolver, xTR | 2.3.a | 6 | 4 | 90 min |
| [16](16-VXLAN/) | VXLAN: VTEP, VNI und Ingress Replication | 2.3.b | 4 | 4 | 75 min |
| [17](17-QoS-MQC/) | QoS mit MQC: Markieren, Policing, Shaping, LLQ | 1.4 | 6 | 4 | 90 min |
| [18](18-NetFlow-SPAN/) | Flexible NetFlow in CML, SPAN/RSPAN/ERSPAN als Konfigurationsübung | 4.2, 4.3 | 6 | 2 live + 2 Papier | 75 min |
| [19](19-Programmierbarkeit-EEM/) | RESTCONF, NETCONF, YANG und EEM | 4.6, 6.3, 6.5, 6.6 | 3 | 5 | 90 min |
| [23](23-Capstone-Campus-Edge-Troubleshooting/) | Capstone: Campus und Edge, Fehlersuche im Gesamtnetz | 3.1.a, 3.1.b, 3.1.c, 3.2.b, 3.3.a, 3.3.b, 3.3.c, 5.1.a, 5.2.a | 8 | 10 | 150 min |
| [24](24-Capstone-WAN-Overlay-Troubleshooting/) | Capstone: WAN, eBGP und IPsec-Overlay, Fehlersuche | 2.2.a, 2.2.b, 3.2.b, 3.2.c | 6 | 9 | 150 min |
| [25](25-EIGRP-Klassisch-Summary-Stub/) | EIGRP klassisch: Nachbarschaft, Authentifizierung, Summary und Stub | 3.2.a | 4 | 6 | 90 min |
| [26](26-iBGP-RouteReflector-Communities/) | iBGP mit Route Reflector, Local Preference und Communities | 3.2.c | 5 | 6 | 100 min |
| [27](27-Redistribution-Routenfilter/) | Redistribution zwischen OSPF und EIGRP mit Tags und Filtern | 3.2.a, 3.2.b | 4 | 6 | 100 min |
| [28](28-OSPF-Areatypen-Summary-Auth/) | OSPF vertieft: Area-Typen, Summarisierung und Authentifizierung | 3.2.b | 4 | 6 | 100 min |
| [29](29-PBR-Quelle-Anwendung/) | Policy-Based Routing nach Quelle und Anwendung | 3.2.d | 6 | 5 | 75 min |
| [30](30-Capstone-Routing-Troubleshooting/) | Capstone: Routing-Fehlersuche (OSPF, EIGRP, BGP, Redistribution) | 3.2.a, 3.2.b, 3.2.c | 5 | 8 | 150 min |
| [31](31-MST-Regionen-PVST-Interop/) | MST vertieft: Regionen, Instanzen, Pfadkosten und PVST-Interop (nur CML) | 3.1.c | 8 | 4 | 100 min |
| [32](32-Multicast-SSM-Bidir-MSDP/) | Multicast vertieft: IGMPv3 und SSM, Bidir-PIM, Anycast-RP mit MSDP | 3.3.d | 6 | 4 | 120 min |
| [33](33-Diagnose-Ping-Traceroute-Debug/) | Diagnose: Ping und Traceroute lesen, Debug und Conditional Debug sicher einsetzen | 4.1 | 5 | 4 | 90 min |
| [34](34-OSPF-Filter-Netztyp-MTU/) | OSPF: Routen filtern (ABR, ASBR, lokal) und Nachbarschaften mit Netztyp- und MTU-Fehlern | 3.2.b | 4 | 5 | 110 min |
| [35](35-IPSLA-Tracking-Jitter/) | IP SLA vertieft: Tracking mit Floating Static, UDP-Jitter mit Responder, TCP-Connect | 4.4 | 5 | 4 | 90 min |
| [36](36-EEM-Applets/) | EEM-Applets: Ereignisse, Aktionen und die typischen Fallen | 6.6 | 2 | 4 | 90 min |
| [20](20-Python-REST-Drills) | Python-/API-Drills (lokal, mit Tests) | 6.1, 6.2, 6.3, 6.4, 6.5, 6.7 | – | – | – |
| [21](21-Design-Fallstudien.md) | Fallstudien: Design, WAN, Fabric, Virtualisierung, Catalyst Center | 1.1.a, 1.1.b, 1.2.a, 1.2.b, 1.3.a, 1.3.b, 2.1.a, 2.1.b, 2.1.c, 4.5 | – | – | – |
| [22](22-Security-Szenarien.md) | Security-Szenarien (REST, Threat Defense, Endpoint, NGFW, TrustSec/MACsec) | 5.3, 5.4.a, 5.4.b, 5.4.c, 5.4.d | – | – | – |

## Abdeckung nach Prüfungsziel

Pro Ziel mit direkten Links zu Aufgaben und Lösungen: **[ZIELE.md](ZIELE.md)**.

| Ziel | Thema | Karten | Lab(s) |
|---|---|---|---|
| `1.1.a` | Campus-, Fabric- und Cloud-Design | 30 | 21 |
| `1.1.b` | Redundanz, FHRP und SSO | 26 | 07, 21 |
| `1.2.a` | SD-WAN: Ebenen und Komponenten | 35 | 21 |
| `1.2.b` | SD-WAN: Nutzen und Grenzen | 22 | 21 |
| `1.3.a` | SD-Access: Ebenen und Komponenten | 31 | 21 |
| `1.3.b` | Fabric und klassischer Campus | 19 | 21 |
| `1.4` | QoS-Konfigurationen | 48 | 17 |
| `2.1.a` | Hypervisor-Typen | 10 | 21 |
| `2.1.b` | Virtuelle Maschinen | 10 | 21 |
| `2.1.c` | Virtuelles Switching | 16 | 21 |
| `2.2.a` | VRF | 26 | 13, 24 |
| `2.2.b` | GRE und IPsec | 53 | 14, 24 |
| `2.3.a` | LISP | 18 | 15 |
| `2.3.b` | VXLAN | 14 | 16 |
| `3.1.a` | 802.1Q und Trunks | 31 | 05, 23 |
| `3.1.b` | EtherChannel | 34 | 05, 23 |
| `3.1.c` | RSTP, MST und Schutzfunktionen | 65 | 06, 23, 31 |
| `3.2.a` | EIGRP und OSPF vergleichen | 45 | 01, 02, 25, 27, 30 |
| `3.2.b` | OSPFv2 und OSPFv3 | 86 | 01, 02, 23, 24, 27, 28, 30, 34 |
| `3.2.c` | Direktes eBGP | 61 | 03, 24, 26, 30 |
| `3.2.d` | Policy-based Routing | 16 | 04, 29 |
| `3.3.a` | NTP und PTP | 32 | 08, 23 |
| `3.3.b` | NAT und PAT | 29 | 09, 23 |
| `3.3.c` | HSRP und VRRP | 30 | 07, 23 |
| `3.3.d` | Multicast-Verfahren | 46 | 12, 32 |
| `4.1` | Diagnose, SNMP und Syslog | 40 | 08, 33 |
| `4.2` | Flexible NetFlow | 24 | 18 |
| `4.3` | SPAN, RSPAN und ERSPAN | 22 | 18 |
| `4.4` | IP SLA | 22 | 04, 35 |
| `4.5` | Catalyst Center und KI-Workflows | 22 | 21 |
| `4.6` | NETCONF und RESTCONF | 40 | 19 |
| `5.1.a` | Lines und lokale Anmeldung | 27 | 11, 23 |
| `5.1.b` | AAA | 42 | 11 |
| `5.2.a` | ACLs | 52 | 10, 23 |
| `5.2.b` | CoPP | 23 | 10 |
| `5.3` | REST-API-Sicherheit | 27 | 22 |
| `5.4.a` | Threat Defense | 29 | 22 |
| `5.4.b` | Endpoint Security | 29 | 22 |
| `5.4.c` | Next-Generation Firewall | 25 | 22 |
| `5.4.d` | TrustSec und MACsec | 28 | 22 |
| `6.1` | Python lesen | 49 | 20 |
| `6.2` | JSON erstellen | 26 | 20 |
| `6.3` | YANG | 27 | 19, 20 |
| `6.4` | Controller-APIs | 27 | 20 |
| `6.5` | HTTP-Codes und API-Payloads | 29 | 19, 20 |
| `6.6` | EEM-Applets | 29 | 19, 36 |
| `6.7` | Agentenbasierte und agentenlose Automation | 25 | 20 |

## Empfohlene Reihenfolge

Die Reihenfolge folgt dem [Wochenplan im Lernplan](../LERNPLAN.md#wochenplan):

1. **Layer 2:** 05, 06.
2. **Gateway-Redundanz, Zeit, NAT:** 07, 08, 09.
3. **OSPF und EIGRP:** 01, 02 (OSPFv3-Teil), 28, 34 und 25. EIGRP Named Mode in 02 ist eine Vertiefung.
4. **BGP, Redistribution, PBR:** 03, 26, 27, 29.
5. **Virtualisierung und Overlay:** 13, 14, optional 15 und 16, dazu der Abschnitt Virtualisierung in 21.
6. **Architektur und Multicast:** 17, 12, 32, 21.
7. **Assurance und Security:** 18, 33, 04, 35, 10, 11.
8. **Security-Produkte und Automation:** 22, 19, 36, 20.
9. **Capstones:** 23, 24 und 30. Reine Fehlersuche im ganzen Netz, bei der ein Fehler den nächsten verdecken kann. Mach sie zuletzt und ohne Blick in die Lösungen.

## Voraussetzungen und Stand

- **Images:** IOSv und IOSvL2 (15.x), CSR1000v (IOS XE) und NX-OSv 9000. Lab 15 braucht ein IOSv-Image mit LISP, Lab 16 den NX-OSv 9000 mit viel RAM, Lab 19 einen CSR1000v und das Ubuntu-Cloud-Image des CML-Refplat.
- **Getestet:** Die Python-Drills (Lab 20) laufen mit den Musterlösungen grün. Bei den CML-Labs ist per Skript geprüft, dass das YAML lädt, alle Links auf vorhandene Interfaces zeigen und jeder eingebaute Fehler in der Konfiguration steckt. In einer laufenden CML-Instanz sind sie noch nicht durchgespielt.
- **Labs 32 bis 36 und der Live-Test:** Diese Labs entstehen aus den Definitionen in [`../Labs-Quelle`](../Labs-Quelle/). Dort liegt auch [`live_test.py`](../Labs-Quelle/live_test.py): Das Skript spielt ein Lab in einer laufenden CML- oder EVE-NG-Instanz durch (Musterlösung einspielen, jede Zeile auf Parser-Fehler prüfen, jeden Fehler einzeln einbauen, Symptom messen, Fix prüfen) und schreibt einen Bericht. Für alle Labs, auch 01 bis 31, gibt es dort eine Syntaxprüfung (`--syntax`), die jede vom Image abgelehnte Konfigurationszeile meldet. Wie du es startest, steht in [`../Labs-Quelle/README.md`](../Labs-Quelle/README.md). **Auch diese Labs sind bisher nicht in einer laufenden Instanz gelaufen**, der Live-Test ist das Werkzeug, um genau das nachzuholen.
- **Wenn ein Befehl nicht durchgeht:** Image-Versionen unterscheiden sich in Details. Prüfe die Syntax in der Cisco-Dokumentation. Das ist gleich eine gute Übung. Eine Korrektur per Issue hilft allen.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter sind reine Lab-Werte. Es stecken keine echten Netzdaten drin.
