# Lernplan ENCOR 350-401 v1.2: 10 Wochen

Der Plan verbindet das [Anki-Deck](Anki/), die [Labs](CML-Labs/), die [Trainer](Trainer/) und die [Prüfungssimulation](Pruefungssimulation/). Er rechnet mit **etwa 8 Stunden pro Woche**. Hast du weniger Zeit, strecke ihn auf 12 Wochen und lass die Labs weg, die als „optional“ markiert sind.

## Das Prinzip

Jede Woche hat ein Thema und läuft in drei Schritten:

1. **Verstehen** mit den Anki-Karten zum Wochenthema.
2. **Anwenden** im Lab: erst aufbauen (Teil A), dann Fehler suchen (Teil B).
3. **Prüfen** mit den Übungsfragen (Teil C) und den Kann-Sätzen unten. Was nicht sitzt, gehst du gezielt noch einmal durch.

## Wochenrhythmus

| Tag | Dauer | Was |
|---|---|---|
| Mo, Mi, Fr, So | 20 Min. | Anki: fällige Karten plus Wochenthema (Filter in der Tabelle unten) |
| Di | 2 Std. | Lab Teil A: aufbauen und verifizieren |
| Do | 2 Std. | Lab Teil B: Tickets lösen, ohne in `solutions/` zu schauen |
| Sa | 1,5 Std. | Teil C üben, die Tickets des Labs im [Ticket-Trainer](Trainer/ticket-trainer.html), Lücken nacharbeiten |
| zwischendurch | 10 Min. | [Rechentrainer](Trainer/encor-rechentrainer.html) zum Wochenthema: STP in Woche 1, OSPF und EIGRP in Woche 3, BGP in Woche 4, DSCP in Woche 6 |

**So gehst du bei Teil B vor:** Symptom nachstellen, eingrenzen (welche Schicht, welches Gerät?), beheben, verifizieren. Erst wenn ein Ticket nach 20 Minuten nicht gelöst ist, schaust du in `FAULTS.md`. Danach wiederholst du die passende Karte im Deck, damit der Fehler beim nächsten Mal sitzt.

## Wochenplan

| Woche | Thema | Ziele | Labs (CML, EVE-NG oder PT) | Anki-Filter |
|---|---|---|---|---|
| 1 | Layer 2 | 3.1.a, 3.1.b, 3.1.c | [05](CML-Labs/05-VLAN-Trunk-EtherChannel/), [06](CML-Labs/06-STP-MST-Schutz/) | `tag:Ziel::3.1.*` |
| 2 | Gateway-Redundanz, Zeit, NAT | 3.3.a, 3.3.b, 3.3.c, 1.1.b | [07](CML-Labs/07-FHRP-HSRP-VRRP-GLBP/), [08](CML-Labs/08-NTP-Syslog-SNMP/), [09](CML-Labs/09-NAT-PAT/) | `tag:Ziel::3.3.a`, `3.3.b`, `3.3.c`, `1.1.b` |
| 3 | OSPF und EIGRP | 3.2.a, 3.2.b | [01](CML-Labs/01-OSPFv2-Multiarea/), [28](CML-Labs/28-OSPF-Areatypen-Summary-Auth/), [25](CML-Labs/25-EIGRP-Klassisch-Summary-Stub/), optional [02](CML-Labs/02-EIGRP-OSPFv3/) | `tag:Ziel::3.2.a`, `3.2.b` |
| 4 | BGP, Redistribution, PBR | 3.2.c, 3.2.d | [03](CML-Labs/03-eBGP-Policy/), [26](CML-Labs/26-iBGP-RouteReflector-Communities/), [27](CML-Labs/27-Redistribution-Routenfilter/), [29](CML-Labs/29-PBR-Quelle-Anwendung/) | `tag:Ziel::3.2.c`, `3.2.d` |
| 5 | Virtualisierung und Overlay | 2.1.a–c, 2.2.a, 2.2.b, 2.3.a, 2.3.b | [13](CML-Labs/13-VRF-Lite/), [14](CML-Labs/14-GRE-IPsec/), optional [15](CML-Labs/15-LISP/) und [16](CML-Labs/16-VXLAN/), Abschnitt Virtualisierung in [21](CML-Labs/21-Design-Fallstudien.md) | `tag:Domaene::2` |
| 6 | Architektur und Multicast | 1.1.a, 1.2, 1.3, 1.4, 3.3.d | [17](CML-Labs/17-QoS-MQC/), [12](CML-Labs/12-Multicast-PIM/), [21](CML-Labs/21-Design-Fallstudien.md) (SD-WAN, SD-Access, Design) | `tag:Domaene::1`, `tag:Ziel::3.3.d` |
| 7 | Assurance und Security | 4.1–4.5, 5.1, 5.2 | [18](CML-Labs/18-NetFlow-SPAN/), [04](CML-Labs/04-PBR-IPSLA/) (IP SLA), [10](CML-Labs/10-ACL-CoPP/), [11](CML-Labs/11-Zugriff-AAA/) | `tag:Domaene::4`, `tag:Ziel::5.1.*`, `tag:Ziel::5.2.*` |
| 8 | Security-Produkte und Automation | 5.3, 5.4, 4.6, 6.1–6.7 | [22](CML-Labs/22-Security-Szenarien.md), [19](CML-Labs/19-Programmierbarkeit-EEM/), [20](CML-Labs/20-Python-REST-Drills/) | `tag:Domaene::5`, `tag:Domaene::6` |
| 9 | Capstones (Fehlersuche im Gesamtnetz) | alle 3.x | [23](CML-Labs/23-Capstone-Campus-Edge-Troubleshooting/), [24](CML-Labs/24-Capstone-WAN-Overlay-Troubleshooting/), [30](CML-Labs/30-Capstone-Routing-Troubleshooting/) | `tag:Fokus::Exhibit` |
| 10 | Prüfungsphase | alle | keine neuen Labs; [Simulation](Pruefungssimulation/) mit „Falsch beantwortete wiederholen“, [Ticket-Trainer](Trainer/ticket-trainer.html) mit allen Tickets | `tag:Fokus::Falle`, `tag:Fokus::HighYield`, `tag:Fokus::Exhibit` |

Die Labs für [Packet Tracer](Packet-Tracer-Labs/) und [EVE-NG](EVE-NG-Labs/) haben dieselben Nummern. In jedem Lab steht, was auf der Plattform geht.

## Kann-Sätze: Woran du merkst, dass eine Woche sitzt

Beantworte die Frage am Ende jeder Zeile aus dem Kopf. Klappt das nicht, ist das dein Thema für den Samstag.

| Woche | Danach kannst du … | Selbsttest |
|---|---|---|
| 1 | Trunks und EtherChannels aufbauen, die STP-Root-Wahl vorhersagen und STP-Schutzfunktionen gezielt einsetzen. | Welcher Port wird Root Port, wenn zwei Wege gleich viel kosten? |
| 2 | HSRP mit Tracking einrichten, NTP mit Authentisierung aufsetzen und PAT von statischem NAT unterscheiden. | Warum übernimmt der Router mit höherer Priorität ohne Preempt nicht? |
| 3 | OSPF-Nachbarschaften und LSA-Typen erklären, Areatypen wählen und EIGRP-Feasible-Successors berechnen. | Woran scheitert eine Nachbarschaft, die in ExStart hängt? |
| 4 | Den BGP-Best-Path der Reihe nach durchgehen, Routen mit Prefix-Lists und Route-Maps filtern und Redistribution ohne Schleifen bauen. | Welches Attribut entscheidet zuerst: Local Preference oder AS-Path? |
| 5 | Hypervisor-Typen unterscheiden, VRFs trennen, GRE über IPsec schützen und das Prinzip von LISP und VXLAN erklären. | Was trägt ein VXLAN-Paket zusätzlich mit, und wie viel Overhead kostet das? |
| 6 | QoS mit MQC konfigurieren, SD-WAN- und SD-Access-Komponenten zuordnen und PIM Sparse Mode erklären. | Welche Rolle hat der SD-WAN Validator (vBond) beim Start eines Edge-Routers? |
| 7 | NetFlow, SPAN und IP SLA einrichten und ACLs, CoPP und AAA mit Fallback aufbauen. | Wann greift `local` in einer AAA-Methodenliste, und wann nicht? |
| 8 | 802.1X, MAB und TrustSec erklären, JSON lesen, REST-Aufrufe bauen und ein EEM-Applet schreiben. | Was ist der Unterschied zwischen PUT und PATCH? |
| 9 | Ein unbekanntes Netz systematisch eingrenzen und mehrere Fehler unter Zeitdruck lösen. | Mit welchem Befehl prüfst du zuerst, ob das Problem auf Layer 2 oder Layer 3 liegt? |
| 10 | Die Prüfung unter echten Bedingungen durchhalten. | Liegen alle Domänen in der Simulation über 75 %? |

## Woche 9: Capstones

Plane für jedes Capstone 2 bis 3 Stunden am Stück ein, **mit Zeitlimit** (Lab 23 und 24 je 90 Minuten, Lab 30 75 Minuten) und ohne `solutions/`. Notiere zu jedem Ticket die Ursache und wie lange du gebraucht hast. Alles, was länger als 15 Minuten gedauert hat, kommt auf deinen Merkzettel.

## Simulation ab Woche 7

Ab Woche 7 übst du in der Simulation die Domänen, die du schon hattest (Modus „Üben“). So siehst du Lücken früh. In Woche 9 machst du am Tag nach dem ersten Capstone einen vollen **Prüfungslauf** (60 Fragen, 75 Minuten). Notiere die Domänen unter 70 % und plane dafür die Karten in Woche 10 ein.

Die Simulation zeigt dir, wo du stehst. Fällt eine Domäne unter 60 %, bringt ein weiterer Lauf wenig. Mach dann zuerst das passende Lab und die Karten und übe danach erneut.

## Woche 10: Prüfungsphase

| Tag | Inhalt |
|---|---|
| 1 | Prüfungslauf (60 Fragen, 75 Min.). Danach alle falschen Fragen mit Erklärung lesen und die passenden Karten wiederholen. |
| 2 | `tag:Fokus::Exhibit` und `tag:Fokus::Falle`, höchstens 60 Karten. |
| 3 | Schwächste Domäne aus der Simulation: Modus „Üben“ plus die Karten dazu (`tag:Domaene::n`). |
| 4 | Ein Capstone ohne Hilfen, mit Zeitlimit. |
| 5 | Zweiter Prüfungslauf. Ziel: jede Domäne über 75 %. |
| 6 | Nur Karten zu den Fehlern aus beiden Läufen, dazu einmal das [Cheatsheet](ENCOR-Cheatsheet.pdf) lesen. |
| 7 | `tag:Fokus::HighYield`, kein neuer Stoff. |

In den zwei Tagen vor der Prüfung nur noch `tag:Fokus::HighYield` und das Cheatsheet. Und früh schlafen.

## Den Plan anpassen

- **Du kennst ein Thema schon aus der Arbeit** (z. B. OSPF oder HSRP): Teil A überspringen, nur Teil B und C machen. Die gewonnene Zeit steckst du in Woche 5 und 8, denn Virtualisierung und Automation sind meist die größte Lücke.
- **Dein Rechner hat zu wenig RAM für die schweren Labs** (15, 16, 19): Packet Tracer kann sie nicht abbilden. Nimm stattdessen die Karten `tag:Ziel::2.3.a`, `2.3.b`, `4.6` und die Python-Drills aus Lab 20.
- **Eine Karte geht immer wieder schief:** Nicht nur wiederholen, sondern das passende Lab-Ticket aus `ZIELE.md` nachbauen. Was du einmal selbst repariert hast, vergisst du kaum noch.

Alle Ziele mit ihren Labs auf einen Blick: [`CML-Labs/ZIELE.md`](CML-Labs/ZIELE.md).
