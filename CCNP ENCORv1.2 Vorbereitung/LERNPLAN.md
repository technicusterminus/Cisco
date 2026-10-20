# Lernplan ENCOR 350-401 v1.2 – 10 Wochen

Verbindet das Anki-Deck mit den Labs. Annahme: **etwa 8 Stunden pro Woche** (4 × 20 Minuten Karten, 2 Lab-Abende à 2 Stunden, 1 Block am Wochenende). Bei weniger Zeit streckst du auf 12 Wochen und lässt die mit „optional“ markierten Labs weg.

## Wochenrhythmus

| Tag | Dauer | Was |
|---|---|---|
| Mo, Mi, Fr, So | 20 Min | Anki: fällige Karten plus das Wochenthema (`tag:Ziel::…`) |
| Di | 2 h | Lab Teil A (Bauen) |
| Do | 2 h | Lab Teil B (Reparieren), ohne Blick in `solutions/` |
| Sa | 1,5 h | Teil C (Üben), Lücken nacharbeiten, Karten zu Fehlern neu ansehen |

Regel für Teil B: Erst Symptom nachstellen, dann eingrenzen, dann beheben. Erst wenn ein Ticket nach 20 Minuten nicht fällt, in `FAULTS.md` nachsehen und danach die zugehörige Karte im Deck wiederholen.

## Wochenplan

| Woche | Thema | Ziele | Labs (CML, EVE-NG oder PT) | Anki-Filter |
|---|---|---|---|---|
| 1 | Layer 2 | 3.1.a, 3.1.b, 3.1.c | [05](CML-Labs/05-VLAN-Trunk-EtherChannel/), [06](CML-Labs/06-STP-MST-Schutz/) | `tag:Ziel::3.1.*` |
| 2 | Gateway-Redundanz, Zeit, NAT | 3.3.a, 3.3.b, 3.3.c, 1.1.b | [07](CML-Labs/07-FHRP-HSRP-VRRP-GLBP/), [08](CML-Labs/08-NTP-Syslog-SNMP/), [09](CML-Labs/09-NAT-PAT/) | `tag:Ziel::3.3.a`, `3.3.b`, `3.3.c`, `1.1.b` |
| 3 | OSPF und EIGRP | 3.2.a, 3.2.b | [01](CML-Labs/01-OSPFv2-Multiarea/), [28](CML-Labs/28-OSPF-Areatypen-Summary-Auth/), [25](CML-Labs/25-EIGRP-Klassisch-Summary-Stub/), optional [02](CML-Labs/02-EIGRP-OSPFv3/) | `tag:Ziel::3.2.a`, `3.2.b` |
| 4 | BGP, Redistribution, PBR | 3.2.c, 3.2.d | [03](CML-Labs/03-eBGP-Policy/), [26](CML-Labs/26-iBGP-RouteReflector-Communities/), [27](CML-Labs/27-Redistribution-Routenfilter/), [29](CML-Labs/29-PBR-Quelle-Anwendung/) | `tag:Ziel::3.2.c`, `3.2.d` |
| 5 | Virtualisierung und Overlay | 2.1.a–c, 2.2.a, 2.2.b, 2.3.a, 2.3.b | [13](CML-Labs/13-VRF-Lite/), [14](CML-Labs/14-GRE-IPsec/), [15](CML-Labs/15-LISP/) (optional), [16](CML-Labs/16-VXLAN/) (optional), Abschnitt Virtualisierung in [21](CML-Labs/21-Design-Fallstudien.md) | `tag:Domaene::2` |
| 6 | Architektur und Multicast | 1.1.a, 1.2, 1.3, 1.4, 3.3.d | [17](CML-Labs/17-QoS-MQC/), [12](CML-Labs/12-Multicast-PIM/), [21](CML-Labs/21-Design-Fallstudien.md) (SD-WAN, SD-Access, Design) | `tag:Domaene::1`, `tag:Ziel::3.3.d` |
| 7 | Assurance und Security | 4.1–4.5, 5.1, 5.2 | [18](CML-Labs/18-NetFlow-SPAN/), [04](CML-Labs/04-PBR-IPSLA/) (IP SLA), [10](CML-Labs/10-ACL-CoPP/), [11](CML-Labs/11-Zugriff-AAA/) | `tag:Domaene::4`, `5.1`, `5.2` |
| 8 | Security-Produkte und Automation | 5.3, 5.4, 4.6, 6.1–6.7 | [22](CML-Labs/22-Security-Szenarien.md), [19](CML-Labs/19-Programmierbarkeit-EEM/), [20](CML-Labs/20-Python-REST-Drills/) | `tag:Domaene::5`, `tag:Domaene::6` |
| 9 | Capstones (Fehlersuche) | alle 3.x | [23](CML-Labs/23-Capstone-Campus-Edge-Troubleshooting/), [24](CML-Labs/24-Capstone-WAN-Overlay-Troubleshooting/), [30](CML-Labs/30-Capstone-Routing-Troubleshooting/) | `tag:Fokus::Exhibit` |
| 10 | Prüfungsphase | alle | keine neuen Labs; [Simulation](Pruefungssimulation/) und Wiederholung | `tag:Fokus::Falle`, `tag:Fokus::HighYield`, `tag:Fokus::Exhibit` |

Packet-Tracer- und EVE-NG-Labs haben dieselben Nummern: [PacketTracer-Labs](PacketTracer-Labs/), [EVE-NG-Labs](EVE-NG-Labs/). Pro Lab steht dort, was in der Plattform geht.

## Woche 9: Capstones

Je Capstone 2 bis 3 Stunden am Stück, **mit Zeitlimit** (Lab 23: 90 Minuten, Lab 24: 90 Minuten, Lab 30: 75 Minuten) und ohne `solutions/`. Notiere pro Ticket Ursache und die Zeit bis zur Lösung. Alles, was länger als 15 Minuten gedauert hat, wird Karte oder Merkzettel.

## Simulation ab Woche 7

Ab Woche 7 lohnt sich eine erste **Probe-Simulation** (Modus „Üben“ je Domäne, die du schon hattest), damit Lücken früh sichtbar werden. In Woche 9 legst du einen ersten vollen **Prüfungslauf** (60 Fragen, 75 Minuten) auf den Tag nach dem ersten Capstone. Notiere die Domänen unter 70 % und plane dafür die Karten der Woche 10 ein.

## Woche 10: Prüfungsphase

| Tag | Inhalt |
|---|---|
| 1 | Simulation: Prüfungslauf (60 Fragen, 75 Min.), danach alle falschen Fragen mit Erklärung lesen; zugehörige Karten wiederholen |
| 2 | `tag:Fokus::Exhibit` und `tag:Fokus::Falle`, höchstens 60 Karten |
| 3 | Schwächste Domäne aus der Simulation: Modus „Üben“ plus passende Karten (`tag:Domaene::n`) |
| 4 | Capstone ohne Hilfen (Zeitlimit) |
| 5 | Zweiter Prüfungslauf; Ziel: jede Domäne über 75 % |
| 6 | Nur Karten zu Fehlern der beiden Läufe, [Cheatsheet](ENCOR-Cheatsheet.pdf) einmal lesen |
| 7 | `tag:Fokus::HighYield`, kein neuer Stoff |

Die zwei Tage vor der Prüfung nur noch `tag:Fokus::HighYield` und das Cheatsheet, früh schlafen.

**Einordnung der Simulation:** Sie ist ein Frühwarnsystem, kein Prognosewerkzeug. Fällt eine Domäne unter 60 %, hilft ein weiterer Lauf wenig. Dann zuerst das zugehörige Lab und die Karten, danach erneut üben.

## Anpassen

- **Du kennst ein Thema schon aus der Arbeit** (z. B. OSPF, HSRP): Teil A überspringen, nur Teil B und C machen und die Wochenzeit für Woche 5 und 8 verwenden, da sind Virtualisierung und Automation meist die Lücke.
- **Kein Platz für schwere Labs** (15, 16, 19 brauchen viel RAM): in Packet Tracer sind sie nicht machbar. Dann stattdessen die Karten `tag:Ziel::2.3.a`, `2.3.b`, `4.6` und die Python-Drills in Lab 20.
- **Nach einem Fehlversuch im Deck:** Karte nicht nur wiederholen, sondern das passende Lab-Ticket aus `ZIELE.md` nachbauen.

Weitere Hilfen: [Cheatsheet (PDF)](ENCOR-Cheatsheet.pdf) und [Prüfungssimulation](Pruefungssimulation/).

Zur Übersicht aller Ziele: [`CML-Labs/ZIELE.md`](CML-Labs/ZIELE.md).
