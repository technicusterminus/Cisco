# CCNP ENCOR 350-401 v1.2 – Labs zum Kompendium

Diese Labs ergänzen das Anki-Kompendium (1.431 Karten). Die Karten bauen Wissen auf, in den Labs wendest du es an: **bauen, reparieren, üben**. Jedes der 47 Prüfungsziele des Kompendiums (`Ziel::…`) ist mindestens einem Lab zugeordnet.

**Inhalt:** 27 CML-Labs (24 Themen-Labs und 3 Capstones, zusammen 134 eingebaute Fehler zum Reparieren), ein Python-/API-Drill-Paket mit automatischen Tests, zwei Fallstudien-Pakete für Themen, die sich nicht sinnvoll simulieren lassen.

**Andere Plattformen:** Dieselben Labs gibt es für [Packet Tracer](../PacketTracer-Labs/) (soweit PT die Funktionen kann) und [EVE-NG](../EVE-NG-Labs/).

## So ist jedes CML-Lab aufgebaut

| Datei | Zweck |
|---|---|
| `topology.yaml` | **Bauen:** Topologie mit Basis-Konfiguration (Hostnamen, IP-Adressen). Das Routing/Switching baust du selbst. |
| `topology-repair.yaml` | **Reparieren:** komplett gebaute Topologie mit eingebauten Fehlern. Die Tickets stehen im README, die Auflösung in `solutions/FAULTS.md`. |
| `README.md` | Teil A Aufgaben, Teil B Tickets, Verifikation, Teil C Transferfragen mit Antworten, Prüfungsbezug |
| `solutions/*.cfg` | Musterlösung je Gerät (ohne Basis-IP-Adressen) |

## So arbeitest du ein Lab durch

1. **Teil A: Bauen.** Lies zuerst das Ziel des Labs und die Skizze. Baue dann Schritt für Schritt und prüfe jeden Schritt mit den Befehlen aus „Verifikation“. Erst am Ende vergleichst du mit `solutions/`.
2. **Teil B: Reparieren.** Am besten an einem anderen Tag. Lade die Reparatur-Topologie, lies das Ticket und gehe vor wie im Betrieb: Symptom nachstellen, eingrenzen, beheben, verifizieren. Erst nach 20 Minuten ohne Fortschritt in `solutions/FAULTS.md` schauen.
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
| [18](18-NetFlow-SPAN/) | Flexible NetFlow, SPAN und RSPAN | 4.2, 4.3 | 8 | 4 | 75 min |
| [19](19-Programmierbarkeit-EEM/) | RESTCONF, NETCONF, YANG und EEM | 4.6, 6.3, 6.5, 6.6 | 2 | 5 | 90 min |
| [23](23-Capstone-Campus-Edge-Troubleshooting/) | Capstone: Campus und Edge, Fehlersuche im Gesamtnetz | 3.1.a, 3.1.b, 3.1.c, 3.2.b, 3.3.a, 3.3.b, 3.3.c, 5.1.a, 5.2.a | 8 | 10 | 150 min |
| [24](24-Capstone-WAN-Overlay-Troubleshooting/) | Capstone: WAN, eBGP und IPsec-Overlay, Fehlersuche | 2.2.a, 2.2.b, 3.2.b, 3.2.c | 6 | 9 | 150 min |
| [25](25-EIGRP-Klassisch-Summary-Stub/) | EIGRP klassisch: Nachbarschaft, Authentifizierung, Summary und Stub | 3.2.a | 4 | 6 | 90 min |
| [26](26-iBGP-RouteReflector-Communities/) | iBGP mit Route Reflector, Local Preference und Communities | 3.2.c | 5 | 6 | 100 min |
| [27](27-Redistribution-Routenfilter/) | Redistribution zwischen OSPF und EIGRP mit Tags und Filtern | 3.2.a, 3.2.b | 4 | 6 | 100 min |
| [28](28-OSPF-Areatypen-Summary-Auth/) | OSPF vertieft: Area-Typen, Summarisierung und Authentifizierung | 3.2.b | 4 | 6 | 100 min |
| [29](29-PBR-Quelle-Anwendung/) | Policy-Based Routing nach Quelle und Anwendung | 3.2.d | 6 | 5 | 75 min |
| [30](30-Capstone-Routing-Troubleshooting/) | Capstone: Routing-Fehlersuche (OSPF, EIGRP, BGP, Redistribution) | 3.2.a, 3.2.b, 3.2.c | 5 | 8 | 150 min |
| [20](20-Python-REST-Drills) | Python-/API-Drills (lokal, mit Tests) | 6.1, 6.2, 6.3, 6.4, 6.5, 6.7 | – | – | – |
| [21](21-Design-Fallstudien.md) | Fallstudien: Design, WAN, Fabric, Virtualisierung, Catalyst Center | 1.1.a, 1.1.b, 1.2.a, 1.2.b, 1.3.a, 1.3.b, 2.1.a, 2.1.b, 2.1.c, 4.5 | – | – | – |
| [22](22-Security-Szenarien.md) | Security-Szenarien (REST, Threat Defense, Endpoint, NGFW, TrustSec/MACsec) | 5.3, 5.4.a, 5.4.b, 5.4.c, 5.4.d | – | – | – |

## Abdeckung nach Prüfungsziel

Pro Ziel mit direkten Links zu Aufgaben und Lösungen: **[ZIELE.md](ZIELE.md)**.

| Ziel | Thema | Karten | Lab(s) |
|---|---|---|---|
| `1.1.a` | Campus-, Fabric- und Cloud-Design | 26 | 21 |
| `1.1.b` | Redundanz, FHRP und SSO | 22 | 07, 21 |
| `1.2.a` | SD-WAN: Ebenen und Komponenten | 33 | 21 |
| `1.2.b` | SD-WAN: Nutzen und Grenzen | 14 | 21 |
| `1.3.a` | SD-Access: Ebenen und Komponenten | 29 | 21 |
| `1.3.b` | Fabric und klassischer Campus | 13 | 21 |
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
| `3.1.c` | RSTP, MST und Schutzfunktionen | 65 | 06, 23 |
| `3.2.a` | EIGRP und OSPF vergleichen | 45 | 01, 02, 25, 27, 30 |
| `3.2.b` | OSPFv2 und OSPFv3 | 86 | 01, 02, 23, 24, 27, 28, 30 |
| `3.2.c` | Direktes eBGP | 61 | 03, 24, 26, 30 |
| `3.2.d` | Policy-based Routing | 16 | 04, 29 |
| `3.3.a` | NTP und PTP | 32 | 08, 23 |
| `3.3.b` | NAT und PAT | 29 | 09, 23 |
| `3.3.c` | HSRP und VRRP | 30 | 07, 23 |
| `3.3.d` | Multicast-Verfahren | 46 | 12 |
| `4.1` | Diagnose, SNMP und Syslog | 40 | 08 |
| `4.2` | Flexible NetFlow | 24 | 18 |
| `4.3` | SPAN, RSPAN und ERSPAN | 22 | 18 |
| `4.4` | IP SLA | 22 | 04 |
| `4.5` | Catalyst Center und KI-Workflows | 22 | 21 |
| `4.6` | NETCONF und RESTCONF | 40 | 19 |
| `5.1.a` | Lines und lokale Anmeldung | 27 | 11, 23 |
| `5.1.b` | AAA | 42 | 11 |
| `5.2.a` | ACLs | 52 | 10, 23 |
| `5.2.b` | CoPP | 21 | 10 |
| `5.3` | REST-API-Sicherheit | 22 | 22 |
| `5.4.a` | Threat Defense | 29 | 22 |
| `5.4.b` | Endpoint Security | 29 | 22 |
| `5.4.c` | Next-Generation Firewall | 22 | 22 |
| `5.4.d` | TrustSec und MACsec | 28 | 22 |
| `6.1` | Python lesen | 49 | 20 |
| `6.2` | JSON erstellen | 19 | 20 |
| `6.3` | YANG | 21 | 19, 20 |
| `6.4` | Controller-APIs | 20 | 20 |
| `6.5` | HTTP-Codes und API-Payloads | 25 | 19, 20 |
| `6.6` | EEM-Applets | 27 | 19 |
| `6.7` | Agentenbasierte und agentenlose Automation | 21 | 20 |

## Empfohlene Reihenfolge

1. **Fundament:** 05 (VLAN/EtherChannel), 06 (STP), 07 (FHRP), 01 (OSPF), 03 (BGP).
   **Routing vertiefen:** 25 (EIGRP), 28 (OSPF-Areatypen), 26 (iBGP/Route Reflector), 27 (Redistribution).
2. **Betrieb und Sicherheit:** 08, 09, 10, 11, 04, 12.
3. **Overlay und QoS:** 13, 14, 15, 16, 17.
4. **Assurance und Automation:** 18, 19, 20.
5. **Konzept:** 21, 22 (Fallstudien), dazu die Karten mit `tag:Fokus::Exhibit` im Deck.
6. **Abschluss:** 23, 24 und 30 (Capstones). Reine Fehlersuche im ganzen Netz, bei der ein Fehler den nächsten verdecken kann. Mach sie zuletzt und ohne Blick in die Lösungen.

## Voraussetzungen und Stand

- **Images:** IOSv und IOSvL2 (15.x), CSR1000v (IOS XE) und NX-OSv 9000. Lab 15 braucht ein IOSv-Image mit LISP, Lab 16 den NX-OSv 9000 mit viel RAM, Lab 19 einen CSR1000v mit External Connector.
- **Getestet:** Die Python-Drills (Lab 20) laufen mit den Musterlösungen grün. Bei den CML-Labs ist per Skript geprüft, dass das YAML lädt, alle Links auf vorhandene Interfaces zeigen und jeder eingebaute Fehler in der Konfiguration steckt. In einer laufenden CML-Instanz sind sie noch nicht durchgespielt.
- **Wenn ein Befehl nicht durchgeht:** Image-Versionen unterscheiden sich in Details. Prüfe die Syntax in der Cisco-Dokumentation. Das ist gleich eine gute Übung. Eine Korrektur per Issue hilft allen.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter sind reine Lab-Werte. Es stecken keine echten Netzdaten drin.
