# Lernplan CCNA 200-301 v1.1 – 8 Wochen

Verbindet Anki-Deck, Packet-Tracer-Labs, Subnetting-Trainer und Prüfungssimulation. Annahme: **etwa 7 Stunden pro Woche** (4 × 20 Minuten Karten, 2 Lab-Abende à 1,5 Stunden, 1 Block am Wochenende). Bei weniger Zeit streckst du auf 10 bis 12 Wochen.

Gewichtung der Prüfung: Network Fundamentals 20 %, Network Access 20 %, IP Connectivity 25 %, IP Services 10 %, Security Fundamentals 15 %, Automation and Programmability 10 %. IP Connectivity bekommt deshalb eine ganze Woche, Services und Automation teilen sich Wochen mit anderen Themen.

## Wochenrhythmus

| Tag | Dauer | Was |
|---|---|---|
| Mo, Mi, Fr, So | 20 Min | Anki: fällige Karten plus Wochenthema (`tag:Ziel::…`) |
| Di | 1,5 h | Lab Teil A (Bauen) |
| Do | 1,5 h | Lab Teil B (Reparieren), ohne Blick in `solutions/` |
| Sa | 1,5 h | Teil C (Üben), Lücken nacharbeiten, Karten zu Fehlern neu ansehen |

Regel für Teil B: Erst Symptom nachstellen, dann eingrenzen, dann beheben. Erst wenn ein Ticket nach 15 Minuten nicht fällt, in `solutions/FAULTS.md` nachsehen und danach die passende Karte wiederholen.

Anki-Filter: `tag:Ziel::1.1` trifft genau Ziel 1.1, nicht 1.10 bis 1.13. Mehrere Ziele verbindest du mit `or`, z. B. `tag:Ziel::1.1 or tag:Ziel::1.2`. Ganze Domäne: `tag:Domaene::2`.

## Wochenplan

| Woche | Thema | Ziele | Labs (Packet Tracer) | Anki-Filter |
|---|---|---|---|---|
| 1 | Komponenten, Kabel, Ports, TCP/UDP | 1.1–1.5 | [01](Packet-Tracer-Labs/01-Komponenten-Topologien-Kabel/), [02](Packet-Tracer-Labs/02-Schnittstellenprobleme/), [03](Packet-Tracer-Labs/03-MAC-Tabelle-Switching/), [04](Packet-Tracer-Labs/04-TCP-UDP/) | `tag:Ziel::1.1 or tag:Ziel::1.2 or tag:Ziel::1.3 or tag:Ziel::1.4 or tag:Ziel::1.5` |
| 2 | Adressierung: IPv4, Subnetting, IPv6 | 1.6–1.10 | [05](Packet-Tracer-Labs/05-IPv4-VLSM/), [06](Packet-Tracer-Labs/06-IPv6/), täglich 15 Min [Subnetting-Trainer](Trainer/subnetting-trainer.html) | `tag:Ziel::1.6 or tag:Ziel::1.7 or tag:Ziel::1.8 or tag:Ziel::1.9 or tag:Ziel::1.10` |
| 3 | Layer 2: VLAN, Trunk, EtherChannel, STP | 2.1–2.5 | [07](Packet-Tracer-Labs/07-VLAN-InterVLAN/), [08](Packet-Tracer-Labs/08-Trunking-DTP-CDP-LLDP/), [09](Packet-Tracer-Labs/09-EtherChannel-LACP/), [10](Packet-Tracer-Labs/10-RapidPVST-Schutz/) | `tag:Ziel::2.1 or tag:Ziel::2.2 or tag:Ziel::2.3 or tag:Ziel::2.4 or tag:Ziel::2.5` |
| 4 | Wireless, Virtualisierung, Verwaltungszugriff | 1.11, 1.12, 2.6–2.9, 5.9, 5.10 | [11](Packet-Tracer-Labs/11-Wireless-Architektur-WLC-AP/), [12](Packet-Tracer-Labs/12-WLAN-GUI-WPA2/), [13](Packet-Tracer-Labs/13-Geraetezugriff-SSH/), Abschnitt Virtualisierung in [28](Packet-Tracer-Labs/28-Konzept-Fallstudien.md) | `tag:Ziel::1.11 or tag:Ziel::1.12 or tag:Ziel::2.6 or tag:Ziel::2.7 or tag:Ziel::2.8 or tag:Ziel::2.9` |
| 5 | IP Connectivity: Routing, OSPF, FHRP | 3.1–3.5 | [14](Packet-Tracer-Labs/14-Routing-Tabelle-Longest-Match/), [15](Packet-Tracer-Labs/15-Statisches-Routing-Floating/), [16](Packet-Tracer-Labs/16-OSPFv2-SingleArea/), [17](Packet-Tracer-Labs/17-FHRP-HSRP/) | `tag:Domaene::3` |
| 6 | IP Services | 4.1–4.9 | [18](Packet-Tracer-Labs/18-DHCP-DNS-Relay/), [19](Packet-Tracer-Labs/19-NAT-PAT/), [20](Packet-Tracer-Labs/20-NTP-Syslog-SNMP/), [21](Packet-Tracer-Labs/21-TFTP-FTP/), [22](Packet-Tracer-Labs/22-QoS-MQC/) | `tag:Domaene::4` |
| 7 | Security | 5.1–5.8 | [23](Packet-Tracer-Labs/23-ACL/), [24](Packet-Tracer-Labs/24-Layer2-Security/), [25](Packet-Tracer-Labs/25-IPsec-Site-to-Site/), [26](Packet-Tracer-Labs/26-AAA-RADIUS/), Sicherheitsabschnitte in [28](Packet-Tracer-Labs/28-Konzept-Fallstudien.md) | `tag:Domaene::5`, später `tag:Fokus::Falle` |
| 8 | Automation, Fallstudien, Simulation | 6.1–6.7 | [27](Packet-Tracer-Labs/27-Automation-JSON-REST/), [28](Packet-Tracer-Labs/28-Konzept-Fallstudien.md), danach [Prüfungssimulation](Pruefungssimulation/) | `tag:Domaene::6`, danach `tag:Fokus::Falle` |

## Woche 8: Simulation und Feinschliff

- Tag 1 bis 3: Automation (Lab 27, Fallstudien Abschnitt 6) und die schwächsten Karten der Wochen 1 bis 7 (Anki: Karteikarten durchsuchen, nach Schwierigkeit sortieren).
- Tag 4: Erste Prüfungssimulation unter Zeitlimit (90 Minuten). Alle Fehler notieren.
- Tag 5 bis 6: Fehlerthemen gezielt wiederholen (Karte, Lab-Ticket oder Fallstudie). Zweite Simulation.
- Tag 7: Nur Anki: `tag:Fokus::Falle`, höchstens 60 Karten. Nichts Neues mehr.

## Subnetting als Gewohnheit

Subnetting entscheidet in der Prüfung direkt über Punkte und indirekt über Zeit (ACL-Wildcards, OSPF-Netze, VLSM). Plane ab Woche 2 jeden Tag 10 bis 15 Minuten im [Subnetting-Trainer](Trainer/subnetting-trainer.html) ein, auch in späteren Wochen. Ziel: Subnetz, Broadcast und Hostbereich in unter 30 Sekunden ohne Hilfsmittel.

## Wenn du hinterherhängst

1. Lab Teil C und optionale Aufgaben streichen, Teil A und B behalten.
2. Anki nie ausfallen lassen; lieber Labs kürzen.
3. Die Wochen 5 (Routing) und 7 (Security) nicht schrumpfen: Dort liegt die meiste Prüfungspunktzahl.
