# Anki-Deck: CCIE Enterprise Infrastructure

**Aktuelle Version:** 1.1 (Stand 23.10.2026) · **542 Karten** (358 Wissens- und Übungskarten, 184 Befehlskarten)
**Datei:** [`CCIE-EI_Kompendium_1.1_DE.apkg`](CCIE-EI_Kompendium_1.1_DE.apkg)

Grundlage sind die öffentlichen Prüfungsthemen von Cisco für CCIE Enterprise Infrastructure v1.1. Das Deck deckt den Theorieteil ab. Für die Labprüfung brauchst du zusätzlich viel Praxis, die Karten ersetzen sie nicht.

## Verteilung

Ohne die Befehlskarten, deren Verteilung im Abschnitt „Befehlsreferenz“ steht.

| Domäne | Inhalt | Karten |
|---|---|---:|
| 1 Network Infrastructure | Switching, Routing-Konzepte, EIGRP, OSPF, BGP, Multicast | 226 |
| 2 Software Defined Infrastructure | SD-Access, SD-WAN | 28 |
| 3 Transport Technologies | GRE, IPsec, DMVPN, MPLS, L3VPN | 37 |
| 4 Security und Services | AAA, CoPP, Layer-2-Security, QoS, FHRP, NAT, Monitoring | 50 |
| 5 Automation und Programmierbarkeit | Datenformate, NETCONF, RESTCONF, EEM, Guest Shell | 17 |

Domäne 1 ist am dichtesten, weil dort die meisten Details und die meisten Troubleshooting-Situationen liegen. Die Domänen 2 bis 5 sind kompakter und bilden die Grundlagen ab. Sie wachsen in späteren Versionen.

## So ist eine Karte aufgebaut

- **Frage:** eine konkrete Situation oder Frage, die mit „?“ endet.
- **Antwort:** beginnt fett mit dem direkten Treffer, danach folgen ein, zwei Sätze zum Mechanismus. Bei CLI-Karten steht die Konfiguration im Codeblock.
- **Quellen:** RFCs und Cisco-Dokumente zum Nachlesen.

Kartentypen: Wissen (160), CLI (85), Vergleich (44), Szenario (31), Prüfungsfalle (21), Rechnen (11), Exhibit (6), Befehl (184).

## Import

1. In Anki: Datei → Importieren → `.apkg` wählen.
2. Das Deck heißt „CCIE Enterprise Infrastructure · Kompendium“ und hat fünf Unterdecks, eines pro Domäne.

## Befehlsreferenz

184 Karten fragen Befehle ab wie eine Befehlstabelle zum Abdecken: Vorne steht die Aufgabe („Welcher Befehl zeigt …?“, „Wie legst du … an?“), hinten die genaue Syntax. Platzhalter stehen in spitzen Klammern (`<vlan-id>`), Optionales in eckigen (`[detail]`), Alternativen in geschweiften (`{in | out}`). Unter der Syntax steht der Konfigurationsmodus und in einem Satz, was der Befehl bewirkt oder worauf du achten musst.

| Suche | Was du bekommst |
|---|---|
| `tag:Fokus::Befehle` | alle Befehlskarten |
| `tag:Befehlsart::Pruefen` | `show`, `debug`, `ping` und andere Prüfbefehle |
| `tag:Befehlsart::Konfigurieren` | Konfigurationsbefehle |
| `tag:Fokus::Befehle tag:Ziel::1.5*` | Befehle zu einem Ziel |

Tipp: Schreib die Syntax auf oder tipp sie ins Lab, bevor du umdrehst. Erst dann merkst du, ob Reihenfolge und Schlüsselwörter sitzen.

Der Schwerpunkt liegt auf Befehlen, die über ENCOR und ENARSI hinausgehen: Private VLANs, Q-in-Q, Bridge Assurance, LFA, BGP Add-Path und Conditional Advertisement, Anycast RP mit MSDP, DVTI, Sham-Link, IBNS 2.0, hierarchische QoS, NAT64, Telemetrie und EEM. Verteilung: Network Infrastructure 110, SD-WAN 4, Transport 26, Security und Services 35, Automation 9.

Die Befehlskarten stehen in [`Quelle/9_befehle.txt`](Quelle/9_befehle.txt) und werden mit dem Deck gebaut.

## Gezielt lernen

| Suche im Browser oder als gefiltertes Deck | Was du bekommst |
|---|---|
| `tag:Modus::Zug` | kurze Karten ohne Code, gut für unterwegs (227 Karten) |
| `tag:Fokus::Falle` | typische Prüfungsfallen (21 Karten) |
| `tag:Typ::CLI` | Konfiguration und Befehle |
| `tag:Ziel::1.5*` | alles zu einem Prüfungsziel, hier BGP |
| `tag:Stufe::Schwer` | die anspruchsvollen Karten (95 Karten, ohne Befehlskarten) |
| `tag:Fokus::Befehle` | Befehle abfragen: Aufgabe vorne, Syntax hinten (184 Karten) |

## Hinweis zur Qualität

Die Karten sind nach den öffentlichen Standards und Cisco-Dokumenten geschrieben, aber nicht auf echter Hardware oder in einem Lab gegengeprüft. Wenn dir etwas auffällt, gib mir gern Bescheid, dann korrigiere ich es.

## Selbst ändern

Die Karten stehen als Textdateien im Ordner [`Quelle`](Quelle/), eine Datei pro Themenblock. Neu bauen:

```
pip install genanki
python3 Quelle/build_deck.py
```

Das Skript prüft beim Bauen, ob jede Frage mit „?“ endet, jede Antwort fett beginnt und keine Frage doppelt vorkommt.

## Versionen

- **1.1 (23.10.2026):** 184 Befehlskarten, Tag `Fokus::Befehle`. Bestehende Karten unverändert, Update-Import behält den Lernstand.
- **1.0 (22.10.2026):** erste Version mit 358 Karten.
