# CCNP ENCOR 350-401 v1.2 – Anki-Kompendium (Deutsch)

Ein deutschsprachiges Anki-Deck für die Prüfung **Cisco 350-401 ENCOR v1.2**. Es deckt alle Themen des Blueprints ab. Die Karten fragen nicht nur Fakten ab, sondern erklären, warum etwas so ist. Für unterwegs gibt es kurze Karten ohne Code, fürs Prüfungstraining Exhibits und Fallen.

**Aktuelle Version:** 4.4 (Stand 21.10.2026) · **1.431 Karten**
**Datei:** [`ENCOR_v1.2_Kompendium_4.4_DE.apkg`](ENCOR_v1.2_Kompendium_4.4_DE.apkg)

## Weiteres Material

| Was | Wo |
|---|---|
| Prüfungssimulation, 189 Fragen, 60 Fragen in 75 Minuten (HTML, offline) | [`Pruefungssimulation/`](Pruefungssimulation/) |
| Cheatsheet, 4 Seiten (PDF) | [`ENCOR-Cheatsheet.pdf`](ENCOR-Cheatsheet.pdf) |
| 10-Wochen-Lernplan mit Deck, Labs und Simulation | [`LERNPLAN.md`](LERNPLAN.md) |
| Labs für CML, EVE-NG, Packet Tracer | [`CML-Labs/`](CML-Labs/), [`EVE-NG-Labs/`](EVE-NG-Labs/), [`PacketTracer-Labs/`](PacketTracer-Labs/) |

## Schnellstart

1. `.apkg` herunterladen und in Anki öffnen (Datei → Importieren).
2. Das Deck `ENCOR v1.2 · Kompendium` erscheint mit sechs Unterdecks, eines pro Blueprint-Domäne.
3. Ein Update-Import über eine ältere Version behält deinen Lernfortschritt (gleiche Karten-IDs).

## Inhalt nach Blueprint

| Domäne | Karten | Anteil | Blueprint |
|---|---:|---:|---:|
| 1 Architektur (QoS, SD-WAN, SD-Access, Redundanz) | 185 | 12,9 % | 15 % |
| 2 Virtualisierung (Hypervisor, VRF, GRE/IPsec, LISP, VXLAN) | 147 | 10,3 % | 10 % |
| 3 Infrastruktur (Layer 2, OSPF, EIGRP, BGP, NAT, HSRP, Multicast) | 475 | 33,2 % | 30 % |
| 4 Network Assurance (Syslog, SNMP, NetFlow, SPAN, IP SLA, Catalyst Center) | 170 | 11,9 % | 10 % |
| 5 Security (AAA, ACL, CoPP, 802.1X, TrustSec, MACsec, Firewall) | 272 | 19,0 % | 20 % |
| 6 Automation und KI (Python, JSON, YANG, NETCONF/RESTCONF, EEM, Ansible/Terraform) | 182 | 12,7 % | 15 % |

Wireless gehört in v1.2 nicht mehr zu 350-401 (es liegt bei ENWLSI) und ist bewusst nicht enthalten.

## Kartentypen

| Typ | Anzahl | Zweck |
|---|---:|---|
| Wissen | 445 | Definitionen und Fakten |
| Szenario | 233 | Fehlersuche und Designentscheidungen |
| CLI | 213 | Konfiguration und Befehle |
| Interpretation | 169 | Ausgaben und Code lesen |
| Vergleich | 168 | Protokolle und Verfahren gegenüberstellen |
| Exhibit | 81 | `show`-Ausgaben und Konfigurationen wie in der Prüfung |
| Vertiefung | 54 | Warum funktioniert etwas so? |
| Prüfungsfalle | 43 | Typische Stolpersteine |
| Rechnen | 25 | Subnetze, Wildcards, Overhead, Metriken |

## Gefilterte Decks mit Tags

In Anki unter **Karteikarten durchsuchen** oder als gefiltertes Deck:

| Tag | Karten | Wofür |
|---|---:|---|
| `tag:Modus::Zug` | 1.022 | Kurze Karten ohne Codeblöcke, gut für unterwegs |
| `tag:Fokus::Exhibit` | 127 | Ausgaben und Konfigurationen interpretieren |
| `tag:Fokus::Falle` | 68 | Prüfungsfallen |
| `tag:Fokus::HighYield` | 203 | Klassische Prüfungsfakten |
| `tag:Domaene::3` usw. | – | Eine Blueprint-Domäne |
| `tag:Ziel::3.2.b` usw. | – | Ein einzelner Blueprint-Punkt |
| `tag:Korrektur::2026_10_19` | – | Nachträglich fachlich geschärfte Karten |

## So ist eine Karte aufgebaut

- **Frage:** konkret und mit Kontext, z. B. „Eine OSPF-Nachbarschaft hängt in ExStart oder Exchange. Was prüfst du zuerst?“
- **Antwort:** beginnt fett mit dem Kern (**Die MTU auf beiden Seiten.**). Danach folgen ein bis zwei Sätze, warum das so ist: Bei unterschiedlicher MTU werden die Database-Description-Pakete abgelehnt. Rechenwege stehen ausgeschrieben da.
- **Hinweis** (nicht immer vorhanden): eine Merkhilfe, eine typische Falle oder der nächste Prüfschritt.
- **Quellen:** Links zur Cisco-Dokumentation oder zum RFC.

Jede Karte hat eine feste ID (`E12-<Blueprint-Punkt>-<Nr>`), dazu Thema, Typ und Stufe (Leicht, Mittel, Schwer). Die IDs bleiben über alle Versionen gleich. Deshalb behält ein Update-Import deinen Lernfortschritt.

## Lernempfehlung

Am besten folgst du dem [10-Wochen-Lernplan](LERNPLAN.md). Er verbindet Deck, Labs und Simulation. Kurz gefasst:

1. **Wochen 1 bis 8:** je ein Thema. Karten mit dem passenden Filter (`tag:Ziel::…` oder `tag:Domaene::N`), dazu das Lab.
2. **Woche 9:** Capstones, also Fehlersuche im ganzen Netz unter Zeitdruck.
3. **Woche 10:** nur noch `tag:Fokus::Exhibit`, `tag:Fokus::Falle`, `tag:Fokus::HighYield` und Prüfungsläufe in der Simulation.

Für unterwegs eignet sich `tag:Modus::Zug`: kurze Karten ohne Codeblöcke.

## Fehler gefunden?

Die Karten sind eigene Formulierungen, die Quellenlinks führen zur Cisco-Dokumentation und zu den RFCs. Im Zweifel gilt die Cisco-Dokumentation. Wenn dir ein Fehler auffällt, melde ihn bitte als Issue, mit Karten-ID und Begründung.

## Versionen

| Version | Änderung |
|---|---|
| 4.4 | Alle Karten didaktisch überarbeitet: Fragen mit Kontext, Antworten beginnen mit dem direkten Treffer und erklären den Mechanismus, Hinweise nur noch als „Merke“, „Falle“ oder nächster Prüfschritt. Gleiche GUIDs, Lernfortschritt bleibt erhalten (Tag `Didaktik::4_4`) |
| 4.3 | Syntax- und Fachkorrekturen (u. a. Flexible NetFlow `match ipv4 protocol`, `ip sla schedule`, IKEv2-Begriffe, EEM-Label-Reihenfolge, NETCONF `discard-changes`), neue Virtualisierungs-, LISP-/VXLAN- und PBR-Karten |
| 4.0 | +115 Karten: Vertiefung, weitere Exhibits, Security auf Blueprint-Niveau, Duplikate entfernt |
| 3.0 | Schwache Karten entfernt, Exhibits mit `show`-Ausgaben, Prüfungsfallen, Lücken geschlossen (Security-Produkte, 802.1X, Automation) |
| 1.0 | Ausgangsdeck (972 Karten) |

## Rechtliches

Kein offizielles Cisco-Material, nicht von Cisco geprüft oder freigegeben. Cisco, CCNP und ENCOR sind Marken von Cisco Systems, Inc. Das Deck dient der privaten Prüfungsvorbereitung.

## Labs: CML, Packet Tracer, EVE-NG

Zu jedem der 47 Ziele gibt es Übungsmaterial in drei Zweigen. Jedes Lab hat dieselben drei Teile:

1. **Bauen:** Schritt für Schritt aufbauen und verifizieren.
2. **Reparieren:** Tickets mit eingebauten Fehlern lösen, wie im Betrieb.
3. **Üben:** Transferfragen mit aufklappbaren Antworten.

Musterlösungen und Fehlerlisten liegen jeweils in `solutions/`. Die Datei `ZIELE.md` in jedem Zweig ordnet die Prüfungsziele den Aufgaben zu.

| Zweig | Inhalt | Hinweis |
|---|---|---|
| [`CML-Labs/`](CML-Labs/) | 27 Labs für Cisco Modeling Labs 2.x (24 Themen-Labs, 3 Capstones zur Fehlersuche im Gesamtnetz) mit Bau- und Reparatur-Topologie (134 Fehler), dazu Python-/API-Drills mit automatischen Tests und zwei Fallstudien-Pakete | Referenz-Zweig, alle Ziele |
| [`EVE-NG-Labs/`](EVE-NG-Labs/) | Dieselben 27 Labs für EVE-NG: Node- und Kabeltabellen, Konfigurationsdateien, Hilfsskript zum Einspielen per Konsole | Interface-Namen wie in CML |
| [`PacketTracer-Labs/`](PacketTracer-Labs/) | 23 Labs mit Aufbau, Konfigurationen und 117 Fehlern; 4 Labs (Multicast, LISP, VXLAN, RESTCONF/EEM) sind in Packet Tracer nicht darstellbar und verweisen auf CML/EVE-NG | Pro Lab Eignung (geeignet, teilweise) |

Die Python-Drills haben automatische Tests. Die Topologien entstehen per Skript, geprüft sind Verkabelung, Ports und Fehlermuster. In einer laufenden Instanz sind sie noch nicht durchgespielt. Hakt etwas, hilft ein Issue mit Lab-Nummer.
