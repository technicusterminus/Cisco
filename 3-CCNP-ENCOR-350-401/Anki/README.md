# Anki-Deck: CCNP ENCOR 350-401 v1.2

**Aktuelle Version:** 5.4 (Stand 03.11.2026) · **1.845 Karten** (1.497 Wissens- und Übungskarten, 348 Befehlskarten)
**Datei:** [`ENCOR_v1.2_Kompendium_5.4_DE.apkg`](ENCOR_v1.2_Kompendium_5.4_DE.apkg)

> **Neu:** Es gibt eine [englische Version](EN/) mit 1.981 Karten: Fragen und Begriffe auf Englisch wie in der Prüfung, Erklärungen auf Deutsch, dazu 429 MC-Karten im Prüfungsstil und 136 Show-Karten mit echten Ausgaben.

Das Deck deckt alle 47 Ziele des Blueprints ab. Die Karten fragen nicht nur Fakten ab, sondern erklären, warum etwas so ist. Für unterwegs gibt es kurze Karten ohne Code, fürs Prüfungstraining Exhibits und Fallen.

## Import

1. `.apkg` herunterladen und in Anki öffnen (Datei → Importieren).
2. Das Deck heißt „ENCOR v1.2 · Kompendium“ und hat sechs Unterdecks, eines pro Domäne.
3. **Von 5.1, 5.2 oder 5.3 auf 5.4:** einfach importieren. Notiztyp und Kennungen sind gleich, der Lernstand bleibt, neue Karten kommen als neue Karten dazu.
4. **Umstieg von 4.x oder 5.0:** Lösche vorher das alte ENCOR-Deck. Version 5.1 bringt einen neuen Notiztyp mit, damit der Text auch im iOS-Dunkelmodus lesbar ist. Ohne Löschen stehen alle Karten doppelt in der Sammlung, und der alte Lernstand geht ohnehin nicht über.

Künftige Updates behalten den Lernstand, solange Notiztyp und interne Kennungen gleich bleiben. Ändert sich das, steht es in der Versionstabelle unten.

## Verteilung

Ohne die Befehlskarten, deren Verteilung im Abschnitt „Befehlsreferenz“ steht.

| Domäne | Karten | Anteil | Blueprint |
|---|---:|---:|---:|
| 1 Architektur (QoS, SD-WAN, SD-Access, Redundanz) | 211 | 14,1 % | 15 % |
| 2 Virtualisierung (Hypervisor, VRF, GRE/IPsec, LISP, VXLAN) | 147 | 9,8 % | 10 % |
| 3 Infrastruktur (Layer 2, OSPF, EIGRP, BGP, NAT, HSRP, Multicast) | 475 | 31,7 % | 30 % |
| 4 Network Assurance (Syslog, SNMP, NetFlow, SPAN, IP SLA, Catalyst Center) | 170 | 11,4 % | 10 % |
| 5 Security (AAA, ACL, CoPP, 802.1X, TrustSec, MACsec, Firewall) | 282 | 18,8 % | 20 % |
| 6 Automation und KI (Python, JSON, YANG, NETCONF/RESTCONF, EEM, Ansible/Terraform) | 212 | 14,2 % | 15 % |

## So ist eine Karte aufgebaut

- **Frage:** konkret und mit Kontext, z. B. „Eine OSPF-Nachbarschaft hängt in ExStart oder Exchange. Was prüfst du zuerst?“
- **Antwort:** beginnt fett mit dem Kern (**Die MTU auf beiden Seiten.**). Danach folgen ein bis zwei Sätze, warum das so ist: Bei unterschiedlicher MTU werden die Database-Description-Pakete abgelehnt. Rechenwege stehen ausgeschrieben da.
- **Hinweis** (nicht immer vorhanden): eine Merkhilfe, eine typische Falle oder der nächste Prüfschritt.
- **Quellen:** Links zur Cisco-Dokumentation oder zum RFC.

Jede Karte hat eine feste ID (`E12-<Blueprint-Punkt>-<Nr>`) sowie Ziel, Thema, Typ und Stufe (Leicht, Mittel, Schwer). Über die ID findest du eine Karte im Browser wieder und kannst Fehler eindeutig melden.

| Typ | Karten | Zweck |
|---|---:|---|
| Wissen | 459 | Definitionen und Fakten, meist mit kleiner Situation |
| Szenario | 251 | Fehlersuche und Designentscheidungen |
| CLI | 218 | Konfiguration und Befehle |
| Interpretation | 173 | Ausgaben und Code lesen |
| Vergleich | 183 | Protokolle und Verfahren gegenüberstellen |
| Exhibit | 83 | `show`-Ausgaben und Konfigurationen wie in der Prüfung |
| Vertiefung | 57 | Warum funktioniert etwas so? |
| Prüfungsfalle | 46 | Typische Stolpersteine |
| Rechnen | 27 | Subnetze, Wildcards, Overhead, Metriken |
| Befehl | 348 | Aufgabe vorne, Syntax mit Modus hinten |

## Befehlsreferenz

348 Karten fragen Befehle ab wie eine Befehlstabelle zum Abdecken: Vorne steht die Aufgabe („Welcher Befehl zeigt …?“, „Wie legst du … an?“), hinten die genaue Syntax. Platzhalter stehen in spitzen Klammern (`<vlan-id>`), Optionales in eckigen (`[detail]`), Alternativen in geschweiften (`{in | out}`). Unter der Syntax steht der Konfigurationsmodus und in einem Satz, was der Befehl bewirkt oder worauf du achten musst.

| Suche | Was du bekommst |
|---|---|
| `tag:Fokus::Befehle` | alle Befehlskarten |
| `tag:Befehlsart::Pruefen` | `show`, `debug`, `ping` und andere Prüfbefehle |
| `tag:Befehlsart::Konfigurieren` | Konfigurationsbefehle |
| `tag:Fokus::Befehle tag:Ziel::3.1.c` | Befehle zu einem Ziel |

Tipp: Schreib die Syntax auf oder tipp sie ins Lab, bevor du umdrehst. Erst dann merkst du, ob Reihenfolge und Schlüsselwörter sitzen.

Verteilung der Befehlskarten: Architektur 24, Virtualisierung 35, Infrastruktur 178, Network Assurance 48, Security 52, Automation 11. Infrastruktur hat die meisten, weil Layer 2, OSPF, BGP, NAT, FHRP und Multicast die meiste CLI haben. Die Befehle aus den Befehlstabellen der Kapitel zur Paketweiterleitung (MAC-Tabelle, SDM, `show interfaces …`) stehen unter `Ziel::3.1.a`.

Die Befehlskarten stehen nach Domänen getrennt in [`Quelle/`](Quelle/). Nach einer Änderung neu einspielen:

```
python3 Quelle/befehle_einspielen.py ENCOR_v1.2_Kompendium_5.4_DE.apkg ENCOR_v1.2_Kompendium_5.5_DE.apkg 5.5
```

Das Skript ersetzt nur die Karten mit `Fokus::Befehle` und lässt alle anderen unverändert.

## Ergänzte Karten

Neue Wissens- und Übungskarten stehen in [`Quelle/ergaenzung_5.4.txt`](Quelle/ergaenzung_5.4.txt), im selben Format wie die Befehlskarten, nur mit `T: <Typ> <Stufe>`. Einspielen:

```
python3 Quelle/karten_ergaenzen.py ENCOR_v1.2_Kompendium_5.4_DE.apkg ENCOR_v1.2_Kompendium_5.5_DE.apkg 5.5
```

Version 5.4 ist so aus 5.3 entstanden. Das Skript legt nur Karten an, die noch nicht im Deck stehen, und lässt alle anderen unverändert. Ein zweiter Lauf auf dasselbe Deck ändert nichts.

## Gezielt lernen

Im Anki-Browser suchen oder als gefiltertes Deck anlegen:

| Suche | Karten | Wofür |
|---|---:|---|
| `tag:Modus::Zug` | 1.079 | Kurze Karten ohne Codeblöcke, gut für unterwegs |
| `tag:Fokus::Exhibit` | 132 | Ausgaben und Konfigurationen interpretieren |
| `tag:Fokus::Falle` | 71 | Prüfungsfallen |
| `tag:Fokus::HighYield` | 203 | Klassische Prüfungsfakten |
| `tag:Domaene::3` usw. | – | Eine Domäne |
| `tag:Ziel::3.2.b` usw. | – | Ein einzelnes Prüfungsziel, passend zu den Labs |
| `tag:Stufe::Schwer` | 123 | Die anspruchsvollsten Karten (ohne Befehlskarten) |
| `tag:Fokus::Befehle` | 348 | Befehle abfragen: Aufgabe vorne, Syntax hinten |

Welche Filter in welche Woche gehören, steht im [Lernplan](../LERNPLAN.md).

## Versionen

| Version | Änderung |
|---|---|
| 5.4 | 66 neue Karten für die Domänen, die unter dem Blueprint-Gewicht lagen: Architektur 26 (u. a. SD-WAN Nutzen und Grenzen, Fabric und klassischer Campus, Verfügbarkeit und Cloud-Modelle), Security 10 (CoPP, REST-API-Sicherheit, NGFW), Automation und KI 30 (JSON, YANG, Controller-APIs, HTTP-Codes, EEM, Push und Pull). Vorher unabhängig fachlich geprüft. Tag `Ergaenzung::5_4`, Quelle in `Quelle/ergaenzung_5.4.txt`. Bestehende Karten unverändert, Lernstand bleibt. |
| 5.3 | Drei neue Befehlskarten zu Trunk-Kapselung, DTP-Reihenfolge und `interface range`. Drei Befehlskarten korrigiert: IPsec-VTI trägt auch Multicast (die Karte sagte das Gegenteil), EEM-Applet mit `sync yes skip yes` statt `sync no skip yes`, EPC-Hinweis zu `brief` und `detail`. Sonst unverändert, Lernstand bleibt. |
| 5.2 | 345 Befehlskarten zu allen Zielen mit CLI-Bezug, Tag `Fokus::Befehle` und `Befehlsart::…`. Notiztyp und GUIDs wie 5.1: Update-Import behält den Lernstand. |
| 5.1 | Karten im iOS-Dunkelmodus lesbar (Textfarbe der Karte explizit gesetzt, vorher stand heller Text auf weißem Grund). Neuer Notiztyp und neue GUIDs, daher das alte Deck vor dem Import löschen. |
| 5.0 | Neuer Notiztyp: „Frage“ ist jetzt das erste Feld, im Anki-Browser stehen Fragen statt IDs. Neue GUIDs, der Lernstand von 4.x wird **nicht** übernommen. Inhalt sonst wie 4.5. |
| 4.5 | 431 flache Wissenskarten (Definitionen, Einzelfakten, Portnummern, „Was ist …?“) in Fragen mit kleiner Situation oder einem Warum umgeschrieben. Die Antwort beginnt fett mit dem Kern. |
| 4.4 | Alle Karten didaktisch überarbeitet: Fragen mit Kontext, Antworten beginnen mit dem direkten Treffer und erklären den Mechanismus, Hinweise nur noch als „Merke“, „Falle“ oder nächster Prüfschritt (Tag `Didaktik::4_4`). |
| 4.3 | Syntax- und Fachkorrekturen (u. a. Flexible NetFlow `match ipv4 protocol`, `ip sla schedule`, IKEv2-Begriffe, EEM-Label-Reihenfolge, NETCONF `discard-changes`), neue Virtualisierungs-, LISP-/VXLAN- und PBR-Karten. |
| 4.0 | +115 Karten: Vertiefung, weitere Exhibits, Security auf Blueprint-Niveau, Duplikate entfernt. |
| 3.0 | Schwache Karten entfernt, Exhibits mit `show`-Ausgaben, Prüfungsfallen, Lücken geschlossen (Security-Produkte, 802.1X, Automation). |
| 1.0 | Ausgangsdeck (972 Karten). |

## Fehler gefunden?

Die Karten sind eigene Formulierungen, die Quellenlinks führen zur Cisco-Dokumentation und zu den RFCs. Im Zweifel gilt die Cisco-Dokumentation. Wenn dir ein Fehler auffällt, melde ihn bitte als Issue, mit Karten-ID und Begründung.

> Kein offizielles Cisco-Material, nicht von Cisco geprüft oder freigegeben. Cisco, CCNP und ENCOR sind Marken von Cisco Systems, Inc.
