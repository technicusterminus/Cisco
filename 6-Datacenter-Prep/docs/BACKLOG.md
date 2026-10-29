# Backlog (priorisiert)

Alle Punkte sind offen. Erledigt ist, was in `docs/GAP-ANALYSE.md` als „behoben“ steht.

## Phase 2: Lernplattform

| # | Punkt | Begründung | Umfang |
|---|---|---|---|
| B-01 | Weitere Labs ins Anforderungsformat überführen (als Nächstes 09, 10, 12, 14; erledigt: 01 bis 07, 11, 13; neu im Format: 32 bis 45) | Die Lösung steht bei den übrigen Labs in der Aufgabe | je Lab Inhalt + Tests wie `test_acceptance.py` |
| B-08 | Topologie: Overlays für EPG, BD, VRF und Policy (Pfad und Drop-Punkt aus dem Traffic-Test sind umgesetzt) | Zusammenhänge sichtbar machen | Frontend |
| B-09 | Dark Mode und Tastaturbedienung (Fokus-Reihenfolge, Shortcuts) | Barrierefreiheit | CSS-Tokens, Frontend |
| B-12 | Change-History: welche Änderung wann, mit Diff, aus allen Bedienwegen | „Änderungen sicher planen“ | Store-Hook |

## Phase 3: Troubleshooting

| # | Punkt | Begründung |
|---|---|---|
| B-07 | Simulierte Uhr statt Wanduhr für Discovery, Upgrades und Fault-Lebenszyklus (soaking → raised → retaining) | Determinismus |

## Phase 4: Erweiterungen

| # | Punkt |
|---|---|
| B-06 | Subjects ohne „Apply Both Directions“ (vzInTerm/vzOutTerm) |
| B-16 | Contract-Prioritäten (vzAny vs. EPG vs. Taboo, Priority-Stufen) nach Abgleich mit echtem ACI präzisieren |
| B-17 | Fault-Codes gegen die Fault Reference prüfen (heute belegt: F0467) |

## Technik

| # | Punkt |
|---|---|
| T-01 | `engine.py` (2.300 Zeilen) entlang der Verantwortungen teilen: Access, Endpoints, Routing, Policy |
| T-02 | Lint (z. B. `python3 -m pyflakes`) und Typprüfung einführen, sobald Werkzeuge in der Umgebung verfügbar sind |
| T-03 | GUI-Tests in einen gemeinsamen Runner mit Bericht |
