# Campus Prep – Projektkonventionen

Didaktischer Simulator für Catalyst 9800 WLC und Catalyst Center: Python-Standardbibliothek, kein echtes Gerät, keine Verbindung zu echten Controllern.

## Prüfkommandos (aus `7-Campus-Prep/`)

```sh
python3 -m unittest discover -s tests
ruff check --select E9,F campusprep tests start.py   # wenn ruff installiert ist
mypy campusprep --ignore-missing-imports             # wenn mypy installiert ist
node tests/gui/smoke.js                              # Browser-Test der WLC-Oberfläche (Playwright)
node --check static/app.js                           # Syntax des Frontends
python3 start.py                                     # Start auf Port 8090
```

## Regeln

- **Eine Welt:** WLC-CLI, Catalyst-Center-API und Tests lesen denselben Zustand (`world.py`, `Wlc`). Das Catalyst Center hat keinen eigenen Bestand.
- **Keine erfundenen Cisco-Artefakte.** Befehle, Ausgabeformate, API-Pfade und Felder nur, wenn sie in `docs/QUELLEN.md` als belegt stehen. Aus Wissen Übernommenes steht dort als solches, Simulator-Festlegungen ebenso. Was nicht belegt ist, lehnt der Simulator ab, statt zu raten.
- **Oberfläche ohne eigene Logik:** Dialoge erzeugen CLI-Befehle und senden sie an `/wlc/api/apply`. Neue Konfiguration entsteht zuerst in der CLI (`wlc.py`), dann im Dialog.
- **Tests prüfen die belegten Formate** mit denselben Mustern wie die Quelle (genieparser). Erwartungen nur mit Begründung im Commit ändern, nie abschwächen, um grün zu werden.
- **Determinismus:** kein `random`, keine Zeitstempel in Ausgaben, IDs aus `uuid5`.
- **Keine Secrets:** Zugangsdaten des Simulators sind Übungswerte. Keine echten Zugangsdaten, Lab-Anleitungen oder herstellerfremden Texte ins Repository.
- Python-Code ohne Umlaute in Bezeichnern und Kommentaren. Texte für Lernende deutsch, Cisco-Begriffe englisch.
