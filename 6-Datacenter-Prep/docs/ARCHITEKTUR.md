# Architektur

Ein Prozess, ein Python-Paket (`dcprep/`), eine statische Weboberfläche (`static/`). Es gibt keine Microservices, keine Datenbank, keine externen Abhängigkeiten. Die Wahl ist historisch gewachsen und passt zum Ziel: läuft offline auf jedem Rechner mit Python ≥ 3.8 und ist ohne Build-Schritt testbar.

```
 Browser (static/)          REST-Clients (Ansible, curl, Python)       CLI im Browser
        │                              │                                  │
        └──────────── HTTP ────────────┴──────────────────────────────────┘
                                       │
                          H  server.py  Handler (/api, /sim, /dp)
                                       │      users.py: Benutzer → eigene Sim
                                       ▼
                        F  Sim (server.py): Persistenz, Labs, Speicherstände
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
  A/B  model.py Store          C  engine.py Engine      E  check_lab, exposure_check
       Klassen, DN, Validierung     abgeleiteter Zustand      (Lab-Bewertung)
       atomarer POST                Discovery, Deployment,          │
              │                     Endpoints, Routing,             │
              │                     Zoning Rules, Faults            │
              │                        │                            │
              └──────────► D  trace.py Connectivity-Engine ◄────────┘
                               (Traffic-Test, Verdict, Reason Codes)
```

| Verantwortung | Modul | Hinweise |
|---|---|---|
| A Domänenmodell | `model.py` (`mo(...)`-Tabelle) | Klassen mit RN-Format, Eltern, Defaults, Enums, Relationen (`tDn`/`tn…Name`) |
| B Änderungen und Validierung | `model.post`, `Store` | atomar: Fehler im Baum → nichts wird übernommen. Fehlercodes 102/103/121/122/801 im APIC-Format |
| C Operational State | `engine.py` (`Engine.rebuild`) | wird nach jeder Änderung vollständig neu berechnet. Konfiguriert ≠ funktionsfähig: Endpoints, Deployments, Nachbarschaften und Faults entstehen hier aus Konfiguration + simulierter Welt |
| D Connectivity/Policy | `trace.py`, `Engine.packet` | ein Test = Folge von Prüfschritten. Ergebnis `verdict` ALLOW/DROP/UNRESOLVED, `reason`, `location`, `policy`, `path`, `hint` |
| E Lab- und Assessment-Engine | `Sim.check_lab`, `Sim.exposure_check`, `labs/*.json` | deklarative Checks, Kategorien `function`/`security`, Fragen, Hinweise, Modi |
| F Persistenz, Szenarien | `Sim.save`, `save_blob`/`load_blob`, `users.py` | `data/users/<name>/state.json`, `saves/`, `snapshots/`, `progress.json`. Spielstand mit `kind` und `version` |
| G UI | `static/js/*.js` | Darstellung, Formulare (`specs.js`), Traffic Inspector (`traceCard` in `views.js`), Lab-Karte |
| H CLI-/API-Adapter | `server.py` (`/api/...`), `query.py`, `cli.py` | REST im APIC-Format (Teilumfang), CLI liest denselben Engine-Zustand |

## Eine Wahrheit

- Jede Änderung (GUI-Formular, REST, Ansible, Lab-Start, Spielstand laden) geht durch `model.post` bzw. `Store.load_config`, danach `Sim.changed()` → `Engine.rebuild()`.
- Traffic Inspector (`POST /sim/traffic`), Testmatrix (`flows.py`), Lab-Checks vom Typ `traffic` und `exposure` rufen alle `trace.run` auf.
- Die Policy-Matrix (`flows.policy_matrix`, `GET /sim/policymatrix`) fragt `Engine.packet` direkt ab – dieselbe Policy-Entscheidung, die `trace.run` im Schritt *Policy Anfrage* verwendet.
- Die CLI (`cli.py`) formatiert nur Engine-Zustand (`show zoning-rule` = `Engine`-Regeln, `show endpoint` = gelernte Hosts).
- Tests: `tests/test_acceptance.py` prüft genau diese Kopplung (REST → Trace → CLI → Bewertung).

## Determinismus

- Gleicher Ausgangszustand + gleiche Aktionen = gleiches Ergebnis. Getestet in `TestStartState.test_start_state_fails_lab_and_is_reproducible`.
- Kein Zufall in Engine und Labs. Die Ausnahme ist die vorgeschlagene MAC beim Anlegen eines Hosts in der GUI; sie ist nur ein Formularvorschlag.
- Zeitabhängig sind Discovery-Schritte, Firmware-Upgrades und Fault-Lebenszyklus (Wanduhr × Einstellung). Für Tests steht die Einstellung auf 0 Sekunden. Eine echte simulierte Uhr fehlt noch (Backlog B-07).

## Lab-Sitzung

`sim.labSession = {mode, hints, answers, checks, started, log}`. Sie wird bei jedem Lab-Start und Reset neu angelegt, ist Teil des Spielstands und verändert nie die Konfiguration. `log` ist das Diagnoseprotokoll (`Sim.lab_log`, höchstens 200 Einträge): Traffic-Tests und CLI-Befehle über HTTP, Hinweise, Antworten und Prüfläufe. Es wird angezeigt (`GET /sim/labs/log`, Lab-Karte), fließt aber nie in die Bewertung ein. `lab_public()` liefert der Oberfläche nur, was der Modus erlaubt.
