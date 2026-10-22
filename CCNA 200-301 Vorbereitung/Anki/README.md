# CCNA 200-301 v1.1: Anki-Deck (Deutsch)

Datei: [`CCNA_200-301_v1.1_Kompendium_2.0_DE.apkg`](CCNA_200-301_v1.1_Kompendium_2.0_DE.apkg) · **621 Karten** zu allen 53 Prüfungszielen, in sechs Unterdecks (eines pro Domäne).

## So ist eine Karte aufgebaut

- **Frage:** konkret und mit Kontext, z. B. „Wie lautet die Broadcastadresse von 192.168.1.64/26?“
- **Antwort:** beginnt fett mit dem Kern (**192.168.1.127.**). Danach folgt kurz, warum: „/26 hat die Blockgröße 64. Das Subnetz reicht von .64 bis .127.“ Rechenwege stehen ausgeschrieben da.
- **Hinweis** (nicht immer vorhanden): eine Merkhilfe oder eine typische Falle.
- **Quellen:** Links zu den Prüfungsthemen von Cisco und den passenden RFCs.

## Kartentypen und Tags

- Typen: Wissen, Szenario, CLI, Interpretation, Vergleich, Exhibit (35 Karten mit echten `show`-Ausgaben), Rechnen (Subnetting, IPv6 kürzen, EUI-64, Wildcards) und Prüfungsfalle (53 Karten).
- Tags zum Filtern: `Ziel::2.5`, `Domaene::2`, `Typ::…`, `Stufe::…`, `Fokus::Falle`, `Modus::Zug`.

## Import und Update

Anki → Datei → Importieren → die `.apkg` wählen. Version 2.0 nutzt einen neuen Kartentyp (die Frage ist das erste Feld, damit der Kartenbrowser Fragen statt IDs zeigt). Anki legt deshalb neue Karten an, statt die alten zu aktualisieren: Lösche vor dem Import das alte CCNA-Deck. Der Lernfortschritt aus 1.x geht dabei verloren. Die Karten behalten ihre IDs (`C11-<Ziel>-<Nr>`) im Feld „ID“.

## Versionen

| Version | Änderung |
|---|---|
| 2.0 | 355 knappe Karten zu Situationsfragen umgeschrieben (Szenario statt Stichwort, fetter Kern in der Antwort). Neuer Kartentyp mit „Frage“ als erstem Feld, Text auch im Dunkelmodus (iOS) lesbar. Neues Deck, Lernstand startet neu (Tag `Didaktik::2_0`) |
| 1.1 | Alle Karten didaktisch überarbeitet: konkrete Fragen, Antworten beginnen mit dem Kern und erklären das Warum, Merkhilfen und Fallen als Hinweis. Lernfortschritt bleibt erhalten (Tag `Didaktik::1_1`) |
| 1.0 | Erste Version (621 Karten) |

Im Zweifel gilt die Dokumentation von Cisco. Fehler bitte als Issue melden, mit Karten-ID.

Passend dazu: [Packet-Tracer-Labs](../Packet-Tracer-Labs/), [Subnetting-Trainer](../Trainer/), [Prüfungssimulation](../Pruefungssimulation/) und der [Lernplan](../LERNPLAN.md).
