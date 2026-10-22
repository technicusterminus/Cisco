# CCNP ENARSI 300-410 Vorbereitung

Material für die Prüfung **300-410 ENARSI** (Implementing Cisco Enterprise Advanced Routing and Services), die Konzentrationsprüfung zum CCNP Enterprise neben ENCOR.

| Inhalt | Stand |
|---|---|
| [Anki-Deck](Anki/) mit 478 Karten zu allen Prüfungszielen | 1.0 |

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

Noch ohne eigenes Lab sind DMVPN Phase 2/3, MPLS L3VPN, BFD, uRPF, DHCP-Relay und IPv6 First Hop Security.

> Kein offizielles Cisco-Material. Cisco, CCNP und ENARSI sind Marken von Cisco Systems, Inc.
