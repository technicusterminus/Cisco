# Anki-Deck: CCNP ENARSI 300-410

**Aktuelle Version:** 1.1 (Stand 23.10.2026) · **709 Karten** (478 Wissens- und Übungskarten, 231 Befehlskarten)
**Datei:** [`ENARSI_300-410_Kompendium_1.1_DE.apkg`](ENARSI_300-410_Kompendium_1.1_DE.apkg)

Grundlage sind die öffentlichen Prüfungsthemen von Cisco für 300-410 ENARSI (aktueller Stand mit Catalyst Center Assurance und IPFIX).

## Verteilung

Ohne die Befehlskarten, deren Verteilung im Abschnitt „Befehlsreferenz“ steht.

| Domäne | Gewicht im Blueprint | Karten |
|---|---:|---:|
| 1 Layer-3-Technologien (AD, Route-Maps, Redistribution, Summarization, PBR, VRF-Lite, BFD, EIGRP, OSPF, BGP) | 35 % | 199 |
| 2 VPN-Technologien (MPLS, L3VPN, DMVPN) | 20 % | 90 |
| 3 Infrastruktur-Security (AAA, ACLs, uRPF, CoPP, IPv6 First Hop Security) | 20 % | 79 |
| 4 Infrastruktur-Services (Gerätezugang, SNMP, Logging, DHCP, IP SLA, NetFlow, Catalyst Center Assurance) | 25 % | 110 |

Domäne 1 hat etwas mehr Karten als ihr Gewicht, weil EIGRP, OSPF und BGP die meisten Details haben und in der Prüfung oft in Troubleshooting-Fragen anderer Themen mitlaufen.

## So ist eine Karte aufgebaut

- **Frage:** eine konkrete Situation, wie sie im Betrieb oder in einer Troubleshooting-Frage vorkommt. Beispiel: „Zwei OSPF-Nachbarn hängen dauerhaft im Zustand EXSTART. Was ist die häufigste Ursache?“
- **Antwort:** beginnt fett mit dem direkten Treffer („Unterschiedliche Interface-MTU.“). Danach folgen ein, zwei Sätze zum Mechanismus, damit du verstehst, warum es so ist.
- **Hinweis:** nur, wenn er etwas bringt, etwa eine Eselsbrücke.
- **Quellen:** RFCs und Cisco-Dokumente zum Nachlesen.

Kartentypen: Wissen, Szenario, Vergleich, CLI, Befehl, Exhibit (Ausgabe deuten), Rechnen und Prüfungsfalle.

## Import

1. In Anki: Datei → Importieren → `.apkg` wählen.
2. Das Deck heißt „ENARSI 300-410 · Kompendium“ und hat vier Unterdecks, eines pro Domäne.
3. Im Kartenbrowser stehen die Fragen, nicht die IDs. Die Karten sind auch im Dunkelmodus (z. B. iOS) lesbar.

Spätere Versionen behalten deinen Lernfortschritt, solange sich die Frage einer Karte nicht ändert.

## Befehlsreferenz

231 Karten fragen Befehle ab wie eine Befehlstabelle zum Abdecken: Vorne steht die Aufgabe („Welcher Befehl zeigt …?“, „Wie legst du … an?“), hinten die genaue Syntax. Platzhalter stehen in spitzen Klammern (`<vlan-id>`), Optionales in eckigen (`[detail]`), Alternativen in geschweiften (`{in | out}`). Unter der Syntax steht der Konfigurationsmodus und in einem Satz, was der Befehl bewirkt oder worauf du achten musst.

| Suche | Was du bekommst |
|---|---|
| `tag:Fokus::Befehle` | alle Befehlskarten |
| `tag:Befehlsart::Pruefen` | `show`, `debug`, `ping` und andere Prüfbefehle |
| `tag:Befehlsart::Konfigurieren` | Konfigurationsbefehle |
| `tag:Fokus::Befehle tag:Ziel::1.11*` | Befehle zu einem Ziel |

Tipp: Schreib die Syntax auf oder tipp sie ins Lab, bevor du umdrehst. Erst dann merkst du, ob Reihenfolge und Schlüsselwörter sitzen.

Verteilung der Befehlskarten: Layer-3-Technologien 122, VPN-Technologien 31, Infrastruktur-Security 34, Infrastruktur-Services 44.

Die Befehlskarten stehen in [`Quelle/9_befehle.txt`](Quelle/9_befehle.txt) und werden mit dem Deck gebaut.

## Gezielt lernen

| Suche im Browser oder als gefiltertes Deck | Was du bekommst |
|---|---|
| `tag:Modus::Zug` | kurze Karten ohne Code, gut für unterwegs (321 Karten) |
| `tag:Fokus::Falle` | typische Prüfungsfallen (66 Karten) |
| `tag:Fokus::Exhibit` | Ausgaben von `show`-Befehlen deuten |
| `tag:Typ::CLI` | Konfiguration und Befehle |
| `tag:Ziel::1.11*` | alles zu einem Prüfungsziel, hier BGP |
| `tag:Stufe::Schwer` | die anspruchsvollen Karten |
| `tag:Fokus::Befehle` | Befehle abfragen: Aufgabe vorne, Syntax hinten |

Tipp: Sag die Antwort laut oder schreib sie auf, bevor du umdrehst. Bei CLI-Karten lohnt es sich, die Konfiguration einmal im Lab selbst einzugeben.

## Selbst ändern

Die Karten stehen als Textdateien im Ordner [`Quelle`](Quelle/), eine Datei pro Themenblock. Das Format steht oben in [`build_deck.py`](Quelle/build_deck.py). Neu bauen:

```
pip install genanki
python3 Quelle/build_deck.py
```

Das Skript prüft beim Bauen, ob jede Frage mit „?“ endet, jede Antwort fett beginnt und keine Frage doppelt vorkommt.

## Versionen

| Version | Änderung |
|---|---|
| 1.1 | 231 Befehlskarten zu allen Zielen mit CLI-Bezug, Tag `Fokus::Befehle`. Bestehende Karten unverändert, Update-Import behält den Lernstand |
| 1.0 | Erste Version: 478 Karten zu allen Zielen des Blueprints, fachlich gegengelesen |

## Vorbehalt

Die Karten sind eigene Formulierungen auf Basis der öffentlichen Prüfungsthemen, der RFCs und der Cisco-Dokumentation. Es sind keine Prüfungsfragen. Im Zweifel gilt die Dokumentation von Cisco.
