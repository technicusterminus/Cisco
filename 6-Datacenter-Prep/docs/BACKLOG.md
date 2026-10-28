# Backlog (priorisiert)

Alle Punkte sind offen. Erledigt ist, was in `docs/GAP-ANALYSE.md` als „behoben“ steht.

## Phase 2: Lernplattform

| # | Punkt | Begründung | Umfang |
|---|---|---|---|
| B-01 | Weitere Labs ins Anforderungsformat überführen (als Nächstes 05, 06, 11, 13; erledigt: 02, 03, 04, 07) | Die Lösung steht bei den übrigen Labs in der Aufgabe | je Lab Inhalt + Tests wie `test_acceptance.py` |
| B-08 | Topologie: berechneten Pfad und Drop-Punkt aus `trace.path` hervorheben, Overlays für EPG, BD, VRF und Policy | gefordert, heute nur als Pfadleiste im Traffic Inspector | Frontend |
| B-09 | Dark Mode und Tastaturbedienung (Fokus-Reihenfolge, Shortcuts) | Barrierefreiheit | CSS-Tokens, Frontend |
| B-11 | Contract-/Policy-Matrix je VRF: EPG × EPG mit angewandter Regel | Überblick statt Einzeltest | baut auf `Engine.packet` auf |
| B-12 | Change-History: welche Änderung wann, mit Diff, aus allen Bedienwegen | „Änderungen sicher planen“ | Store-Hook |

## Phase 3: Troubleshooting

| # | Punkt | Begründung |
|---|---|---|
| B-05 | Intra-EPG-Contracts (`fvRsIntraEpg`) bei Isolation auswerten | fachlich unvollständig |
| B-07 | Simulierte Uhr statt Wanduhr für Discovery, Upgrades und Fault-Lebenszyklus (soaking → raised → retaining) | Determinismus |
| B-13 | Diagnoseprozess erfassen: ausgeführte Traffic-Tests und CLI-Befehle je Lab-Sitzung protokollieren und anzeigen, ohne die Denkweise zu „bewerten“ | optionaler Troubleshooting-Modus |
| B-14 | CLI-Ausgabe als „verifiziert“ oder „simulator-spezifisch“ kennzeichnen; bei nicht unterstützten Befehlen einen Diagnoseweg vorschlagen | Ehrlichkeit des Terminals |

## Phase 4: Erweiterungen

| # | Punkt |
|---|---|
| B-06 | Subjects ohne „Apply Both Directions“ (vzInTerm/vzOutTerm) |
| B-10 | OT-Szenario (Soll-Lab 26): Zonen Engineering, Applikation, Monitoring, Management; nur definierte Beziehungen; Monitoring getrennt von Admin; negative Tests für laterale Kommunikation. Didaktisch, ohne Sicherheitsgarantie |
| B-15 | Soll-Labs 20, 21, 22, 25 im neuen Format (External EPG vs. Routing, Rückweg, Preferred Group, Snapshot-Rollback) |
| B-16 | Contract-Prioritäten (vzAny vs. EPG vs. Taboo, Priority-Stufen) nach Abgleich mit echtem ACI präzisieren |
| B-17 | Fault-Codes gegen die Fault Reference prüfen (heute belegt: F0467) |

## Technik

| # | Punkt |
|---|---|
| T-01 | `engine.py` (2.300 Zeilen) entlang der Verantwortungen teilen: Access, Endpoints, Routing, Policy |
| T-02 | Lint (z. B. `python3 -m pyflakes`) und Typprüfung einführen, sobald Werkzeuge in der Umgebung verfügbar sind |
| T-03 | GUI-Tests in einen gemeinsamen Runner mit Bericht |
