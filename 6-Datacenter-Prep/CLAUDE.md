# Datacenter Prep – Projektkonventionen

Didaktischer Cisco-ACI-Simulator: Python-Standardbibliothek im Backend, Vanilla-JS ohne Build-Schritt im Frontend. Kein echter APIC, keine Nexus-Emulation.

## Prüfkommandos (alle aus `6-Datacenter-Prep/`)

```sh
python3 -m unittest discover -s tests          # Unit-, Integrations- und Abnahmetests (Python)
node tests/gui/smoke.js                        # GUI: Startseite, Labs & Stände, Benutzer (braucht Playwright)
node tests/gui/acceptance.js                   # GUI: Abnahmefall Lab 32 von Start bis Reset
node tests/gui/troubleshooting.js              # GUI: Endpoint-Verlauf, Link-Ausfall, Labs 36/37
for f in static/js/*.js; do node --check $f; done   # Syntax des Frontends
python3 Labs-Quelle/build_labs.py              # labs/*.json neu erzeugen (deterministisch)
python3 start.py --no-browser                  # Start (Port 8080, belegt -> nächster freier)
```

Build, Typecheck und Lint gibt es nicht: Es ist kein Build-Werkzeug, kein Typchecker und kein Linter konfiguriert.

## Regeln

- **Eine Wahrheit:** GUI, REST, CLI, Traffic-Test und Lab-Bewertung lesen denselben `Store` (Konfiguration) und dieselbe `Engine` (abgeleiteter Zustand). Keine zweite Logik im Frontend oder in Labs.
- **Labs** werden nur in `Labs-Quelle/build_labs.py` geändert. `labs/*.json` sind generiert. Jedes Lab braucht `SOLUTIONS[...]`. Der Test `TestLabs` verlangt: Ohne Lösung ist das Lab nicht bestanden, mit Lösung ist es bestanden.
- **Keine erfundenen Cisco-Artefakte.** Reason Codes (`POLICY_*`, `EP_*` …), S-Fault-Codes, das Dienstmodell und Simulator-Befehle sind als simulator-spezifisch gekennzeichnet. Echte Klassen, Attribute und Fault-Codes nur, wenn sie belegt sind (siehe `docs/REFERENZPROFIL.md`).
- **Determinismus:** kein `random` in Engine und Labs, keine Zeitstempel in generierten Lab-Dateien. Discovery und Upgrades laufen nach Sekunden-Einstellung (`settings.discoverySeconds`), in Tests auf 0.
- **Fachliche Erwartungen in Tests** werden nur mit Begründung im Commit geändert, nie abgeschwächt, um grün zu werden.
- Python-Code ohne Umlaute in Bezeichnern und Kommentaren (`ue` statt `ü`). UI-Texte deutsch mit Umlauten, Cisco-Begriffe englisch.
- Persistenz: `data/` (gitignored), pro Benutzer `data/users/<name>/`. Spielstände haben `kind`/`version` (`Sim.SAVE_VERSION`).

## Wo was liegt

Siehe `docs/ARCHITEKTUR.md`. Simulationsumfang und Regelbasis: `docs/REFERENZPROFIL.md`. Neue Labs: `docs/LAB-AUTHORING.md`. Offene Punkte: `docs/BACKLOG.md`.
