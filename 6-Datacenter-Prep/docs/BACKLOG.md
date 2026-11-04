# Backlog (priorisiert)

Alle Punkte sind offen. Erledigt ist, was in `docs/GAP-ANALYSE.md` als „behoben“ steht.

## Phase 2: Lernplattform

| # | Punkt | Begründung | Umfang |
|---|---|---|---|
| B-09 | Dark Mode und Tastaturbedienung (Fokus-Reihenfolge, Shortcuts) | Barrierefreiheit | CSS-Tokens, Frontend |

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
| T-02 | Typprüfung einführen (Lint mit `ruff --select E9,F` ist eingeführt und sauber) |
