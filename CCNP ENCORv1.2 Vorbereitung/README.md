# CCNP ENCOR 350-401 v1.2 Vorbereitung

Material für die Prüfung **350-401 ENCOR v1.2** (Implementing and Operating Cisco Enterprise Network Core Technologies). ENCOR ist die Kernprüfung für den CCNP Enterprise und zugleich die Qualifikationsprüfung für die CCIE-Enterprise-Infrastructure-Labprüfung.

| Inhalt | Umfang |
|---|---|
| [Anki-Deck](Anki/) | 1.776 Karten zu allen 47 Prüfungszielen, davon 345 Befehlskarten, Version 5.2 |
| [Prüfungssimulation](Pruefungssimulation/) | 241 Fragen, davon 43 Exhibits und 21 zum Ordnen und Zuordnen; Prüfungsmodus mit 60 Fragen in 75 Minuten |
| [Trainer](Trainer/) | Rechentrainer (BGP, STP, OSPF, EIGRP, QoS) und Ticket-Trainer mit den 134 Lab-Tickets |
| [Labs](#labs) | 27 Labs für CML und EVE-NG, 23 davon auch für Packet Tracer, mit 134 eingebauten Fehlern; dazu Python-Drills und zwei Fallstudien-Pakete |
| [Lernplan](LERNPLAN.md) | 10 Wochen, verbindet Deck, Labs, Trainer und Simulation |
| [Cheatsheet](ENCOR-Cheatsheet.pdf) | 4 Seiten zum Ausdrucken |

Simulation und Trainer sind einzelne HTML-Dateien und laufen offline im Browser.

## Prüfung auf einen Blick

- 120 Minuten, sechs Domänen: Architektur 15 %, Virtualisierung 10 %, Infrastruktur 30 %, Network Assurance 10 %, Security 20 %, Automation und KI 15 %.
- Wireless gehört seit v1.2 nicht mehr zu ENCOR und fehlt deshalb auch hier.
- Den größten Block bildet die Infrastruktur mit Layer 2, OSPF, EIGRP, BGP, NAT, FHRP und Multicast. Dort lohnt sich die meiste Lab-Zeit.

## So fängst du an

1. Lies den [Lernplan](LERNPLAN.md). Er legt fest, welche Karten, Labs und Trainer in welche Woche gehören.
2. Importiere das [Anki-Deck](Anki/). Wer noch eine Version vor 5.1 hat, löscht das alte Deck vorher.
3. Woche 1 beginnt mit [Lab 05](CML-Labs/05-VLAN-Trunk-EtherChannel/) und [Lab 06](CML-Labs/06-STP-MST-Schutz/). Wie ein Lab abläuft, steht in der [Lab-Übersicht](CML-Labs/README.md).
4. Ab Woche 7 kommt die [Prüfungssimulation](Pruefungssimulation/) im Modus „Üben“ dazu, ab Woche 9 im Prüfungsmodus.

## Labs

Jedes Lab hat drei Teile: **Bauen** (Schritt für Schritt, mit Prüfbefehl nach jedem Schritt), **Reparieren** (Tickets mit eingebauten Fehlern, wie im Betrieb) und **Üben** (Transferfragen mit aufklappbaren Antworten). Musterlösungen und Fehlerlisten liegen in `solutions/`.

| Plattform | Umfang | Hinweis |
|---|---|---|
| [CML](CML-Labs/) | 27 Labs mit Bau- und Reparatur-Topologie, dazu Python-Drills (20) und Fallstudien (21, 22) | Referenz, deckt alle Ziele ab |
| [EVE-NG](EVE-NG-Labs/) | dieselben 27 Labs als Import-ZIP (je Lab „Bauen“ und „Reparieren“ mit Startkonfiguration), dazu Node- und Kabeltabellen für den Aufbau von Hand | Interface-Namen wie in CML |
| [Packet Tracer](PacketTracer-Labs/) | 23 Labs mit 117 Fehlern | Multicast, LISP, VXLAN und RESTCONF/EEM nur in CML oder EVE-NG |

Die Labs in der Reihenfolge des Lernplans:

| Woche | Thema | Labs |
|---|---|---|
| 1 | Layer 2 | 05 VLAN, Trunk, EtherChannel · 06 STP, MST, Schutzfunktionen |
| 2 | Gateway-Redundanz, Zeit, NAT | 07 HSRP, VRRP, GLBP · 08 NTP, Syslog, SNMP · 09 NAT, PAT |
| 3 | OSPF und EIGRP | 01 OSPFv2 Multi-Area · 28 OSPF-Areatypen · 25 EIGRP klassisch · 02 EIGRP Named Mode und OSPFv3 (optional) |
| 4 | BGP, Redistribution, PBR | 03 eBGP-Policy · 26 iBGP mit Route Reflector · 27 Redistribution · 29 PBR nach Quelle und Anwendung |
| 5 | Virtualisierung und Overlay | 13 VRF-Lite · 14 GRE, IPsec, VTI · 15 LISP und 16 VXLAN (optional) |
| 6 | Architektur und Multicast | 17 QoS mit MQC · 12 Multicast mit PIM · 21 Design-Fallstudien |
| 7 | Assurance und Security | 18 NetFlow, SPAN · 04 PBR mit IP SLA · 10 ACL, CoPP · 11 Zugriff, AAA |
| 8 | Security-Produkte und Automation | 22 Security-Szenarien · 19 RESTCONF, NETCONF, EEM · 20 Python-Drills |
| 9 | Capstones | 23 Campus und Edge · 24 WAN und Overlay · 30 Routing |

Welches Lab welches Prüfungsziel abdeckt, steht in [`CML-Labs/ZIELE.md`](CML-Labs/ZIELE.md). Die Topologien entstehen per Skript, geprüft sind Verkabelung, Ports und Fehlermuster. In einer laufenden Instanz sind sie noch nicht durchgespielt. Hakt etwas, hilft ein Issue mit der Lab-Nummer.

## Danach

Für den CCNP Enterprise fehlt noch eine Konzentrationsprüfung, etwa [ENARSI](../CCNP%20ENARSI%20300-410%20Vorbereitung/). Wer auf den CCIE zielt, findet die nächsten Schritte in [CCIE Enterprise Infrastructure](../CCIE%20Enterprise%20Infrastructure%20Vorbereitung/).

## Fehler gefunden?

Karten, Fragen und Labs sind eigene Formulierungen. Im Zweifel gilt die Cisco-Dokumentation. Wenn dir ein Fehler auffällt, melde ihn bitte als Issue, mit Karten-ID oder Lab-Nummer.

> Kein offizielles Cisco-Material, nicht von Cisco geprüft oder freigegeben. Cisco, CCNP, CCIE und ENCOR sind Marken von Cisco Systems, Inc.
