# CCNP ENARSI 300-410 Vorbereitung

Material für die Prüfung **300-410 ENARSI** (Implementing Cisco Enterprise Advanced Routing and Services), die Konzentrationsprüfung zum CCNP Enterprise neben ENCOR.

| Inhalt | Stand |
|---|---|
| [Anki-Deck](Anki/) mit 478 Karten zu allen Prüfungszielen | 1.0 |
| [Prüfungssimulation](Pruefungssimulation/) mit 179 Fragen, 23 Exhibits und 8 Ordnen/Zuordnen, Prüfungsmodus 55 Fragen in 90 Minuten | 1.0 |
| [CML-Labs](CML-Labs/) und [EVE-NG-Labs](EVE-NG-Labs/): 6 Labs zu DMVPN, MPLS L3VPN, BFD, uRPF, DHCP-Relay und IPv6 First Hop Security, 29 eingebaute Fehler | 1.0 |

## Prüfung auf einen Blick

- 90 Minuten, vier Domänen: Layer-3-Technologien 35 %, VPN-Technologien 20 %, Infrastruktur-Security 20 %, Infrastruktur-Services 25 %.
- Der Schwerpunkt liegt auf **Troubleshooting**: Viele Ziele beginnen mit „Troubleshoot“. Es reicht nicht, eine Konfiguration zu kennen, du musst aus Symptomen und `show`-Ausgaben auf die Ursache schließen.
- ENCOR ist die Grundlage. Wer ENCOR noch nicht hat, lernt am besten zuerst die Infrastruktur-Domäne dort.

## Lernempfehlung

1. Pro Prüfungsziel zuerst die Karten mit `tag:Ziel::<Nummer>` durchgehen, dann im Lab nachbauen.
2. Bei jeder Prüfungsfalle (`tag:Fokus::Falle`) das Szenario im Lab absichtlich herbeiführen und den Fehler mit den genannten Befehlen finden.
3. In den letzten zwei Wochen täglich die fälligen Karten, dazu gezielt `tag:Stufe::Schwer`.

## Passende Labs aus dem ENCOR-Paket

Viele ENARSI-Themen lassen sich mit den vorhandenen ENCOR-Labs (CML und EVE-NG) üben:

| ENARSI-Ziel | ENCOR-Lab |
|---|---|
| 1.9 EIGRP | 02 EIGRP-OSPFv3, 25 EIGRP klassisch mit Summary und Stub |
| 1.10 OSPF | 01 OSPFv2 Multiarea, 28 OSPF-Areatypen, Summary, Auth |
| 1.11 BGP | 03 eBGP-Policy, 26 iBGP mit Route Reflector und Communities |
| 1.2–1.5 Route-Maps, Redistribution, Filter | 27 Redistribution und Routenfilter |
| 1.6 PBR, 4.5 IP SLA | 04 PBR-IPSLA, 29 PBR nach Quelle und Anwendung |
| 1.7 VRF-Lite | 13 VRF-Lite |
| 3.1 AAA | 11 Zugriff und AAA |
| 3.2/3.3 ACL und CoPP | 10 ACL-CoPP |
| 4.2/4.3 SNMP und Syslog | 08 NTP-Syslog-SNMP |
| 4.6 NetFlow | 18 NetFlow-SPAN |
| 2.3 DMVPN (Grundlage) | 14 GRE-IPsec |
| Troubleshooting gemischt | 30 Capstone Routing-Troubleshooting |

## Eigene ENARSI-Labs

Für Themen, die das ENCOR-Paket nicht abdeckt, gibt es sechs Labs, jeweils zum Bauen, Reparieren (Tickets) und Üben, für CML und EVE-NG:

| Lab | Thema | ENARSI-Ziel |
|---|---|---|
| E1 | DMVPN Phase 3 mit EIGRP | 2.3 |
| E2 | MPLS L3VPN mit LDP und MP-BGP | 2.1, 2.2 |
| E3 | BFD für schnelle Fehlererkennung mit OSPF | 1.8 |
| E4 | uRPF: Strict, Loose, ACL | 3.2.c |
| E5 | DHCP-Server und DHCP-Relay | 4.4 |
| E6 | IPv6 First Hop Security: RA Guard und DHCPv6 Guard | 3.4 |

Die Übersicht mit Dauer, Fehlerzahl und Ziel-Abdeckung steht in den READMEs von [CML-Labs](CML-Labs/README.md) und [EVE-NG-Labs](EVE-NG-Labs/README.md). Die Labs sind per Skript auf Konsistenz geprüft, aber noch nicht in einer laufenden Simulation durchgespielt. Packet Tracer ist nicht dabei, weil es DMVPN, MPLS, BFD und uRPF nicht abbildet.

> Kein offizielles Cisco-Material. Cisco, CCNP und ENARSI sind Marken von Cisco Systems, Inc.
