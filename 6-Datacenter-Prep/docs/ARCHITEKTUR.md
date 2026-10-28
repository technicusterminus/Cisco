# Architektur

Eine Python-Anwendung ohne Fremdpakete (Python ≥ 3.8) und eine Weboberfläche ohne Build-Schritt. Kein Microservice, keine Cloud, kein externer Dienst.

## Eine gemeinsame Wahrheit

```
GUI (static/js)  REST-API (/api)  CLI (/sim/cli)  Simulator-API (/sim)
        \             |               |               /
         +----------- dcprep/server.py (Sim, eine Instanz je Übungswelt) -----------+
                      |                                                           |
          Store (model.py): Konfiguration als MIT          sim-Dict: Hosts, Router, vCenter, Lab, Einstellungen
                      |                                                           |
                      +------------------ Engine.rebuild() -----------------------+
                                          |
                     Operational State: Nodes, Pfade, Deployments, Endpoints, Routen, Contracts, Faults, Health
                                          |
              trace.run (Connectivity)   cli.Cli (show-Befehle)   assess (Lab-Bewertung)   flows (Testmatrix)
```

Alle Bedienwege schreiben in denselben Store und lesen denselben operativen Zustand. Traffic Inspector, Testmatrix und Lab-Bewertung rufen dieselbe Funktion `trace.run` auf. Die Tests in `tests/test_least_privilege.py` prüfen das (`test_grader_and_inspector_share_engine`, `test_cli_sees_same_state`, `TestEndToEndRest`).

## Verantwortlichkeiten

| Schicht | Modul | Aufgabe |
|---|---|---|
| A Domänenmodell | `model.py` | Klassen, DN/RN-Regeln, Attribute mit Defaults und Enums, Eltern/Kinder, Relationen |
| B Änderungen und Validierung | `model.post`, `model.delete` | atomarer POST: ein Fehler im Baum verwirft alles; Validierung von Namen, Werten und Eltern |
| C Operational State | `engine.py`, `multipod.py`, `msite.py`, `ops.py` | rechnet nach jeder Änderung alles neu: Discovery, Access-Auflösung, EPG-Deployment, Endpoint Learning, L3Out, Contracts, Faults, Health |
| D Connectivity/Policy | `trace.py`, `Engine.packet`, `Engine.permit_scope` | Diagnose eines Flusses mit Verdikt, Reason Code, Fehlerort und angewendeter Policy |
| E Lab und Assessment | `server.check_lab`, `assess.py`, `labs/*.json`, `Labs-Quelle/` | deklarative Labs, Prüfungen nach Zustand, Kategorien, Least Privilege, Hinweise, Modi |
| F Persistenz | `server.Sim` (`state.json`, Saves, Snapshots, `progress.json`), `users.py` | eine Übungswelt je Benutzer, Speicherstände mit Schema-Version, Import mit Prüfung |
| G UI | `static/` | APIC-ähnliche Struktur, Traffic Inspector, Labs |
| H CLI/API | `cli.py`, `query.py`, `server.Handler` | Show-Befehle aus dem Zustand, REST im APIC-Format (Teilumfang) |

## Konfiguration und Betrieb getrennt

Der Store hält nur Konfiguration. `Engine.rebuild()` leert den operativen Teil (`store.clear_oper()`) und baut ihn neu auf. Ein konfiguriertes Objekt ist deshalb nicht automatisch funktionsfähig: Eine EPG ohne passende Domain bekommt einen Fault F0467 und keinen gelernten Endpoint.

## Determinismus

`Engine.rebuild(now)` nimmt die Zeit als Parameter. Zeitabhängig sind nur Discovery und Firmware-Upgrade; beide sind mit 0 Sekunden sofort fertig. Die Engine nutzt keinen Zufall. `trace.run` ist eine reine Funktion des Zustands, bis auf die Paketzähler für die Stats-Ansicht.

## Persistenz

| Datei | Inhalt | Version |
|---|---|---|
| `data/users/<name>/state.json` | Konfiguration, Zähler, simulierte Welt | `version: 1` |
| `data/users/<name>/saves/*.json` | Speicherstände inkl. Lab und Prüfergebnis | `SAVE_VERSION = 1`, Import prüft Art und Version |
| `data/users/<name>/snapshots/*.json` | Config Rollbacks (nur Konfiguration) | – |
| `data/users/<name>/progress.json` | Fortschritt je Lab: bestanden, Hinweise, Modus | – |

Lab-Instanzen sind isoliert: Ein Lab startet immer aus `reset()` plus Lab-Konfiguration; der vorige Stand wird automatisch als `auto-<lab>` gesichert.

## Sicherheit

- Standardmäßig nur `127.0.0.1`. Keine Verbindung zu echten APICs, keine Telemetrie.
- Das Terminal führt keine Shell-Befehle aus; `cli.py` kennt nur eine feste Befehlsliste.
- Passwörter der Benutzer mit PBKDF2 und Salt. Keine Secrets im Repository.
- `subprocess` nur für `openssl` beim optionalen `--https`.
