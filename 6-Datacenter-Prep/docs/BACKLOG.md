# Backlog (priorisiert)

Alle Punkte sind offen. Erledigt ist, was in `docs/GAP-ANALYSE.md` als „behoben“ steht.

## Phase 2: Lernplattform

| # | Punkt | Begründung | Umfang |
|---|---|---|---|

## Phase 3: Troubleshooting

| # | Punkt | Begründung |
|---|---|---|

## Phase 4: Erweiterungen

| # | Punkt |
|---|---|
| B-16 | Rest der Contract-Prioritäten: Wirkung von `priorityOverride` (level1–level3 ↔ lowest/medium/highest belegen), ESG-/Inter-VRF-Stufen 10–12. Table 8 und 23 des Contract Guide, Deny+Log und implizites DHCP sind umgesetzt |
| B-17 | Fault-Codes gegen die Fault Reference prüfen. Belegt ist nur F0467; alle übrigen Faults tragen S-Codes (simulator-spezifisch). Eine Websuche (Nov. 2026) fand für keinen Kandidaten (z. B. F0523, F0956, F2534) eine Cisco-Quelle, nur Forenbeiträge. Der Test-Fault heißt jetzt S9100 statt F9999 |

## Technik

Keine offenen Punkte. Lint (`ruff`), Typprüfung (`mypy`), Aufteilung der Engine und der GUI-Testrunner sind umgesetzt.
