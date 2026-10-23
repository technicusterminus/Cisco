# CCIE Enterprise Infrastructure Vorbereitung

Kostenloses Lernmaterial auf Deutsch für den Weg zum CCIE Enterprise Infrastructure. Die Inhalte bauen auf CCNP ENCOR und ENARSI auf.

## Inhalt

| Baustein | Stand |
|---|---|
| [Anki-Deck](Anki/) mit 542 Karten zu allen fünf Domänen, davon 184 Befehlskarten | fertig (Version 1.1) |
| [Prüfungssimulation](Pruefungssimulation/) mit 175 Fragen, 9 Exhibits und Ordnen/Zuordnen | fertig (Version 1.0) |
| [CML-Labs](CML-Labs/) und [EVE-NG-Labs](EVE-NG-Labs/): 6 Labs mit 30 eingebauten Fehlern, dazu die passenden Labs aus ENCOR und ENARSI | fertig (Version 1.0) |
| Trainer | in Planung |

## Die Prüfung

- **Voraussetzung:** die Qualifikationsprüfung ENCOR 350-401, Material dazu im [ENCOR-Ordner](../CCNP%20ENCORv1.2%20Vorbereitung/).
- **Labprüfung:** acht Stunden an einem Tag, aufgeteilt in Modul 1 *Design* (drei Stunden, ohne Gerätekonfiguration) und Modul 2 *Deploy, Operate and Optimize* (fünf Stunden an Geräten).
- **Gewichtung:** Network Infrastructure 30 %, Software Defined Infrastructure 25 %, Transport Technologies and Solutions 15 %, Infrastructure Security and Services 15 %, Infrastructure Automation and Programmability 15 %.

## Empfohlene Reihenfolge

1. Anki-Deck durcharbeiten und Lücken markieren.
2. Mit der Prüfungssimulation Wissenslücken aufdecken.
3. Die Grundlagen in den passenden Labs aus ENCOR und ENARSI sichern (Tabelle unten).
4. Die CCIE-Labs C1 bis C6. Teil B (Reparieren) jeweils mit Zeitlimit: höchstens 10 Minuten pro Ticket.

## Eigene CCIE-Labs

Jedes Lab hat drei Teile: Bauen, Reparieren (Tickets mit eingebauten Fehlern) und Üben (Transferfragen). Details, Dauer und Ziel-Abdeckung stehen in den READMEs von [CML-Labs](CML-Labs/README.md) und [EVE-NG-Labs](EVE-NG-Labs/README.md).

| Lab | Thema | CCIE-Ziel |
|---|---|---|
| [C1](CML-Labs/C1-BGP-AS-Pfad-und-Backup/) | BGP: `allowas-in`, private AS, GTSM und bedingte Ankündigung | 1.5.c, 1.5.d, 1.5.f |
| [C2](CML-Labs/C2-Multicast-Anycast-RP-MSDP/) | Multicast: Anycast RP mit MSDP, RPF-Umleitung und SSM | 1.6.a, 1.6.b, 1.6.c |
| [C3](CML-Labs/C3-OSPF-Virtual-Link-NSSA/) | OSPF: Virtual Link mit Authentisierung, NSSA, Typ-3-Filter und Netzwerktypen | 1.2.i, 1.4.b, 1.4.c, 1.4.d |
| [C4](CML-Labs/C4-L3VPN-Shared-Services/) | MPLS L3VPN: Shared Services, AS-Override und Route-Target-Design | 3.2.a, 3.2.b |
| [C5](CML-Labs/C5-DMVPN-IKEv2-BGP/) | DMVPN Phase 3 mit IKEv2 und BGP mit dynamischen Nachbarn | 1.5.e, 3.1.b, 3.1.c |
| [C6](CML-Labs/C6-EIGRP-Named-Mode/) | EIGRP Named Mode: SHA-256, Unequal-Cost Load Balancing und Stub mit Leak-Map | 1.2.i, 1.3.b, 1.3.d, 1.3.e, 1.3.f |

Die Labs brauchen nur IOSv und höchstens fünf Geräte. SD-Access und SD-WAN (Domäne 2) lassen sich damit nicht nachbauen, dafür gibt es Karten im Deck und Fragen in der Simulation.

## Passende Labs aus ENCOR und ENARSI

Die Grundlagen der übrigen Themen übst du mit den vorhandenen Labs. Die Links führen zu den CML-Fassungen, die EVE-NG-Fassungen tragen dieselben Namen.

| CCIE-Thema | Lab |
|---|---|
| 1.1 VLANs, Trunks, EtherChannel | [ENCOR 05](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/05-VLAN-Trunk-EtherChannel/) |
| 1.1.e Spanning Tree, MST, Schutzfunktionen | [ENCOR 06](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/06-STP-MST-Schutz/) |
| 1.2.c VRF-Lite | [ENCOR 13](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/13-VRF-Lite/) |
| 1.2.d Policy-Based Routing | [ENCOR 04](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/04-PBR-IPSLA/), [ENCOR 29](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/29-PBR-Quelle-Anwendung/) |
| 1.2.f, 1.2.h Filter und Redistribution | [ENCOR 27](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/27-Redistribution-Routenfilter/) |
| 1.2.j BFD | [ENARSI E3](../CCNP%20ENARSI%20300-410%20Vorbereitung/CML-Labs/E3-BFD-OSPF/) |
| 1.3 EIGRP-Grundlagen, Summary, Stub | [ENCOR 02](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/02-EIGRP-OSPFv3/), [ENCOR 25](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/25-EIGRP-Klassisch-Summary-Stub/) |
| 1.4 OSPF-Grundlagen, Areatypen | [ENCOR 01](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/01-OSPFv2-Multiarea/), [ENCOR 28](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/28-OSPF-Areatypen-Summary-Auth/) |
| 1.5 BGP-Grundlagen, Route Reflector, Communities | [ENCOR 03](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/03-eBGP-Policy/), [ENCOR 26](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/26-iBGP-RouteReflector-Communities/) |
| 1.6 Multicast-Grundlagen, statischer RP, BSR | [ENCOR 12](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/12-Multicast-PIM/) |
| 3.1.a, 3.1.b GRE, IPsec, VTI | [ENCOR 14](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/14-GRE-IPsec/) |
| 3.1.c DMVPN-Grundlagen mit EIGRP | [ENARSI E1](../CCNP%20ENARSI%20300-410%20Vorbereitung/CML-Labs/E1-DMVPN-Phase3/) |
| 3.2 MPLS, LDP, L3VPN-Grundlagen | [ENARSI E2](../CCNP%20ENARSI%20300-410%20Vorbereitung/CML-Labs/E2-MPLS-L3VPN/) |
| 4.1.a Härtung, AAA, ACL, CoPP | [ENCOR 10](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/10-ACL-CoPP/), [ENCOR 11](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/11-Zugriff-AAA/) |
| 4.1.c uRPF, IPv6 First Hop Security | [ENARSI E4](../CCNP%20ENARSI%20300-410%20Vorbereitung/CML-Labs/E4-uRPF/), [ENARSI E6](../CCNP%20ENARSI%20300-410%20Vorbereitung/CML-Labs/E6-IPv6-First-Hop-Security/) |
| 4.2 QoS | [ENCOR 17](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/17-QoS-MQC/) |
| 4.3.a FHRP, NTP, DHCP | [ENCOR 07](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/07-FHRP-HSRP-VRRP-GLBP/), [ENCOR 08](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/08-NTP-Syslog-SNMP/), [ENARSI E5](../CCNP%20ENARSI%20300-410%20Vorbereitung/CML-Labs/E5-DHCP-Relay/) |
| 4.3.b NAT, IP SLA, NetFlow, SPAN | [ENCOR 09](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/09-NAT-PAT/), [ENCOR 04](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/04-PBR-IPSLA/), [ENCOR 18](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/18-NetFlow-SPAN/) |
| 5 NETCONF, RESTCONF, YANG, EEM, Python | [ENCOR 19](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/19-Programmierbarkeit-EEM/), [ENCOR 20](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/20-Python-REST-Drills/) |

Zum Abschluss eignen sich die Capstones aus ENCOR ([23](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/23-Capstone-Campus-Edge-Troubleshooting/), [24](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/24-Capstone-WAN-Overlay-Troubleshooting/), [30](../CCNP%20ENCORv1.2%20Vorbereitung/CML-Labs/30-Capstone-Routing-Troubleshooting/)) als Zeittraining für die Fehlersuche.

> Kein offizielles Cisco-Material. Cisco, CCIE, CCNP, ENCOR und ENARSI sind Marken von Cisco Systems, Inc.
