# Anki-Deck: Netzwerk-Einstieg

Datei: [`Netzwerk-Einstieg_Kompendium_1.3_DE.apkg`](Netzwerk-Einstieg_Kompendium_1.3_DE.apkg) mit **102 Karten** zu den 12 Kapiteln des Einsteigerpakets.

## So ist eine Karte aufgebaut

- **Frage:** konkret, z. B. „Welches Präfix braucht man für 50 Hosts?“
- **Antwort:** beginnt fett mit dem Kern (**/26.**), danach kommt in ein, zwei Sätzen der Rechenweg oder der Grund: 50 + 2 = 52 Adressen, nächste Zweierpotenz 64 = 2^6, also 6 Hostbits und 32 − 6 = 26.

## Import und Lernen

1. In Anki: Datei → Importieren → `.apkg` wählen.
2. Lies zuerst das Kapitel, dann lerne die Karten mit dem Filter `tag:Kapitel::05` (Kapitelnummer anpassen).
3. Sag die Antwort laut oder schreib sie auf, bevor du umdrehst. Nur so merkst du, ob du sie wirklich weißt.

## Aufbau

- Typen: Wissen, Vergleich, Szenario, Rechnen (Subnetting), Interpretation, CLI.
- Tags: `Netzwerk_Einstieg`, `Kapitel::01` bis `Kapitel::12`, `Typ::…`, `Stufe::…`.
- Jede Karte hat eine feste ID (`EIN-<Kapitel>-<nnn>`). Version 1.3 nutzt einen neuen Kartentyp (Frage als erstes Feld). Anki legt deshalb neue Karten an: Lösche vor dem Import das alte Deck, der Lernstand startet neu.

## Versionen

| Version | Änderung |
|---|---|
| 1.3 | Neuer Kartentyp mit „Frage“ als erstem Feld, damit der Kartenbrowser (auch in AnkiMobile) Fragen statt IDs zeigt. Dunkelmodus bleibt lesbar. Inhalt unverändert, Lernstand startet neu |
| 1.2 | Dunkelmodus repariert (vorher heller Text auf weißem Grund, z. B. auf iOS). Der Kartenbrowser zeigt jetzt die Frage statt der ID. Inhalt unverändert, Lernfortschritt bleibt |
| 1.1 | Alle Karten didaktisch überarbeitet: konkrete Fragen, Antworten beginnen mit dem Kern und erklären ihn |
| 1.0 | Erste Version |

Die Karten sind eigene Formulierungen. Im Zweifel gilt die Dokumentation des Herstellers bzw. der RFC.
