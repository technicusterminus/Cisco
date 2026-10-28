# Entwicklung: Konventionen und Prüfkommandos

## Prüfkommandos (aus `6-Datacenter-Prep`)

```sh
python3 -m unittest discover -s tests      # alle Unit-, Integrations- und HTTP-Tests (~20 s)
python3 tests/e2e_browser.py               # Browser-E2E für Lab 32, braucht Playwright + Chromium (sonst übersprungen)
python3 Labs-Quelle/build_labs.py          # Labs neu erzeugen, danach git diff labs/ prüfen
ruff check --select E9,F dcprep tests      # Syntax- und Pyflakes-Fehler (Altlasten siehe docs/BACKLOG.md)
python3 start.py --no-browser --port 8080  # Server starten
```

## Konventionen

- Nur Python-Standardbibliothek zur Laufzeit. Keine Pakete hinzufügen.
- Oberfläche, Erklärungen und Lab-Texte auf Deutsch. Cisco-Klassen, Attribute, CLI-Befehle und API-Namen auf Englisch.
- Keine erfundenen Cisco-Codes, Befehle oder API-Antworten. Eigene Fault-Codes beginnen mit **S**, Reason Codes des Traffic-Tests sind als simulator-spezifisch dokumentiert.
- Jede neue Regel in der Engine: Eintrag in `docs/REGELBASIS.md` mit Quelle oder dem Vermerk „nicht verifiziert“, dazu ein Test.
- Neue Funktion: Status in `docs/REFERENZPROFIL.md` (umgesetzt, vereinfacht, nicht unterstützt).
- Labs nur in `Labs-Quelle/build_labs.py` ändern, nie in `labs/*.json`.
- Traffic Inspector, Testmatrix und Lab-Bewertung nutzen `trace.run`. Keine zweite Auswertung bauen.
- Tests nicht abschwächen. Eine fachliche Erwartung nur mit Begründung im Commit ändern.
- Keine zufälligen Werte in Engine oder Labs. Zeit nur über `Engine.rebuild(now)` und die Einstellungen.
