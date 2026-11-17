# Campus Prep – Projektkonventionen

Didaktischer Simulator für Catalyst 9800 WLC und Catalyst Center: Python-Standardbibliothek, kein echtes Gerät, keine Verbindung zu echten Controllern.

## Prüfkommandos (aus `7-Campus-Prep/`)

```sh
python3 -m unittest discover -s tests
ruff check --select E9,F campusprep tests start.py   # wenn ruff installiert ist
mypy campusprep --ignore-missing-imports             # wenn mypy installiert ist
node tests/gui/smoke.js                              # Browser-Test der WLC-Oberfläche (Playwright)
python3 Labs-Quelle/build_labs.py                    # labs/*.json neu erzeugen (deterministisch)
node --check static/app.js                           # Syntax des Frontends
python3 start.py                                     # Start auf Port 8090, Zustand in ./data (gitignored)
python3 start.py --ephemeral                         # ohne dauerhaften Zustand (Tests)
```

## Regeln

- **Eine Welt:** WLC-CLI, Catalyst-Center-API und Tests lesen denselben Zustand (`world.py`, `Wlc`). Das Catalyst Center hat keinen eigenen Bestand.
- **Keine erfundenen Cisco-Artefakte.** Befehle, Ausgabeformate, API-Pfade und Felder nur, wenn sie in `docs/QUELLEN.md` als belegt stehen. Aus Wissen Übernommenes steht dort als solches, Simulator-Festlegungen ebenso. Was nicht belegt ist, lehnt der Simulator ab, statt zu raten.
- **Oberfläche ohne eigene Logik:** Dialoge erzeugen CLI-Befehle und senden sie an `/wlc/api/apply`. Neue Konfiguration entsteht zuerst in der CLI (`wlc.py`), dann im Dialog.
- **Labs** werden nur in `Labs-Quelle/build_labs.py` geändert; `labs/*.json` sind generiert (ein Test prüft die Übereinstimmung). Jedes Lab braucht eine Musterlösung, eine Sicherheitsprüfung und für jede naheliegende falsche Abkürzung einen Test; ohne Lösung nicht bestanden, mit Lösung bestanden. Der sichtbare Text verrät die Lösung nicht (siehe `docs/LAB-KATALOG.md`).
- **Persistenz:** Zustand und Fortschritt gehen durch `store.py` (atomar, `kind`/`version`, sortierte Schlüssel, keine Zeitstempel). Neue Zustandsfelder gehören in `Sim.snapshot_all`/`restore_all` und, wenn sie das Format ändern, braucht `store.VERSION` eine neue Nummer. Ein Stand, der nicht passt, darf den laufenden Zustand nie verändern.
- **Tests prüfen die belegten Formate** mit denselben Mustern wie die Quelle (genieparser). Erwartungen nur mit Begründung im Commit ändern, nie abschwächen, um grün zu werden.
- **Determinismus:** kein `random`, keine Zeitstempel in Ausgaben, IDs aus `uuid5`.
- **Keine Secrets:** Zugangsdaten des Simulators sind Übungswerte. Keine echten Zugangsdaten, Lab-Anleitungen oder herstellerfremden Texte ins Repository.
- Python-Code ohne Umlaute in Bezeichnern und Kommentaren. Texte für Lernende deutsch, Cisco-Begriffe englisch.
