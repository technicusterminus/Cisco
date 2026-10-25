# Anki-Deck: Netzwerk-Einstieg

Datei: [`Netzwerk-Einstieg_Kompendium_1.4_DE.apkg`](Netzwerk-Einstieg_Kompendium_1.4_DE.apkg) mit **137 Karten** zu den 12 Kapiteln des Einsteigerpakets, davon 35 Befehlskarten.

## So ist eine Karte aufgebaut

- **Frage:** konkret, z. B. „Welches Präfix braucht man für 50 Hosts?“
- **Antwort:** beginnt fett mit dem Kern (**/26.**), danach kommt in ein, zwei Sätzen der Rechenweg oder der Grund: 50 + 2 = 52 Adressen, nächste Zweierpotenz 64 = 2^6, also 6 Hostbits und 32 − 6 = 26.

## Import und Lernen

1. In Anki: Datei → Importieren → `.apkg` wählen.
2. Lies zuerst das Kapitel, dann lerne die Karten mit dem Filter `tag:Kapitel::05` (Kapitelnummer anpassen).
3. Sag die Antwort laut oder schreib sie auf, bevor du umdrehst. Nur so merkst du, ob du sie wirklich weißt.

## Befehlsreferenz

35 Karten fragen Befehle ab wie eine Befehlstabelle zum Abdecken: Vorne steht die Aufgabe („Welcher Befehl zeigt …?“, „Wie legst du … an?“), hinten die genaue Syntax. Platzhalter stehen in spitzen Klammern (`<vlan-id>`), Optionales in eckigen (`[detail]`), Alternativen in geschweiften (`{in | out}`). Unter der Syntax steht der Konfigurationsmodus und in einem Satz, was der Befehl bewirkt oder worauf du achten musst.

| Suche | Was du bekommst |
|---|---|
| `tag:Fokus::Befehle` | alle Befehlskarten |
| `tag:Befehlsart::Pruefen` | `show`, `debug`, `ping` und andere Prüfbefehle |
| `tag:Befehlsart::Konfigurieren` | Konfigurationsbefehle |
| `tag:Fokus::Befehle tag:Kapitel::12` | Befehle zu einem Ziel |

Tipp: Schreib die Syntax auf oder tipp sie ins Lab, bevor du umdrehst. Erst dann merkst du, ob Reihenfolge und Schlüsselwörter sitzen.

Die Befehlskarten stehen in [`Quelle/befehle.txt`](Quelle/befehle.txt). Nach einer Änderung neu einspielen:

```
python3 Quelle/befehle_einspielen.py Netzwerk-Einstieg_Kompendium_1.4_DE.apkg Netzwerk-Einstieg_Kompendium_1.5_DE.apkg 1.5
```

Das Skript ersetzt nur die Karten mit `Fokus::Befehle` und lässt alle anderen unverändert.

## Aufbau

- Typen: Wissen, Vergleich, Szenario, Rechnen (Subnetting), Interpretation, CLI, Befehl.
- Tags: `Netzwerk_Einstieg`, `Kapitel::01` bis `Kapitel::12`, `Typ::…`, `Stufe::…`.
- Jede Karte hat eine feste ID (`EIN-<Kapitel>-<nnn>`). Version 1.3 nutzt einen neuen Kartentyp (Frage als erstes Feld). Anki legt deshalb neue Karten an: Lösche vor dem Import das alte Deck, der Lernstand startet neu.

## Versionen

| Version | Änderung |
|---|---|
| 1.4 | 35 Befehlskarten (Cisco-CLI, Windows- und Linux-Befehle zur Fehlersuche), Tag `Fokus::Befehle`. Gleicher Kartentyp wie 1.3: Update-Import über 1.3 behält den Lernstand |
| 1.3 | Neuer Kartentyp mit „Frage“ als erstem Feld, damit der Kartenbrowser (auch in AnkiMobile) Fragen statt IDs zeigt. Dunkelmodus bleibt lesbar. Inhalt unverändert, Lernstand startet neu |
| 1.2 | Dunkelmodus repariert (vorher heller Text auf weißem Grund, z. B. auf iOS). Der Kartenbrowser zeigt jetzt die Frage statt der ID. Inhalt unverändert, Lernfortschritt bleibt |
| 1.1 | Alle Karten didaktisch überarbeitet: konkrete Fragen, Antworten beginnen mit dem Kern und erklären ihn |
| 1.0 | Erste Version |

Die Karten sind eigene Formulierungen. Im Zweifel gilt die Dokumentation des Herstellers bzw. der RFC.
