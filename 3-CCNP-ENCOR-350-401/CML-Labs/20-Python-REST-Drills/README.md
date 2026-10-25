# Lab 20 – Python- und API-Drills (ohne CML)

**Blueprint-Bezug:** 6.1 Python lesen · 6.2 JSON erstellen · 6.3 YANG · 6.4 Controller-APIs · 6.5 HTTP-Codes und API-Payloads · 6.7 agentenbasierte/agentenlose Automation · Teile von 5.3 (REST-API-Sicherheit)
**Dauer:** ca. 3 h (in Häppchen) · **Niveau:** leicht bis mittel · **Voraussetzung:** Python 3.9+, `pip install requests pyyaml jinja2 pyang`

Diese Drills laufen komplett lokal: Eine kleine Mock-API (Standardbibliothek) spielt einen Controller mit Token-Anmeldung, Pagination, Fehlercodes und asynchronen Tasks. **Alle Tests wurden mit den Musterlösungen ausgeführt (grün).**

**Lernziele:** Nach diesen Drills kannst du …

- Python-Code lesen und seine Ausgabe vorhersagen.
- JSON-Bodies bauen und einen REST-Client mit Token, Pagination und Fehlercodes schreiben.
- YANG-Module lesen sowie Jinja2-Templates und Ansible-Playbooks reparieren.

| Aufgabe | Ziel | Was du tust |
|---|---|---|
| 1 `ex01_predict/` | 6.1 | Acht kurze Skripte: Ausgabe **vorhersagen**, dann ausführen und vergleichen |
| 2 `ex02_json/` | 6.2 | JSON-/XML-Bodies für RESTCONF/NETCONF bauen, `show ip interface brief` parsen |
| 3 `ex03_rest/` | 6.4, 6.5 | REST-Client gegen die Mock-API: Token, Pagination, 401/403/404/415/429/503, Retry |
| 4 `ex04_bugs/` | 6.1 | Fünf typische Fehler in Hilfsfunktionen reparieren |
| 5 `ex05_yang/` | 6.3 | YANG-Modul lesen, gültige und ungültige Instanzdaten erkennen |
| 6 `ex06_templates/` | 6.7 | Jinja2-Template schreiben und ein kaputtes Ansible-Playbook reparieren |

## Ablauf

```
cd ex02_json && python3 -m unittest -v test_ex02      # Tests schlagen zuerst fehl: NotImplementedError
cd ../ex03_rest && python3 -m unittest -v test_ex03   # Tests starten die Mock-API selbst
cd ../ex04_bugs && python3 -m unittest -v test_ex04
cd ../ex06_templates && python3 render.py && python3 check_playbook.py
```

Die Mock-API kannst du auch separat starten (`python3 mock_api/server.py 8080`) und mit `curl` erkunden. Zugang: `admin` / `Lab#2026!`, `viewer` / `View#2026!` (nur lesen).

```
curl -s -u admin:'Lab#2026!' -X POST http://127.0.0.1:8080/dna/system/api/v1/auth/token
curl -s -H "X-Auth-Token: <Token>" "http://127.0.0.1:8080/dna/intent/api/v1/network-device?offset=1&limit=5"
curl -i -H "X-Auth-Token: <Token>" http://127.0.0.1:8080/dna/intent/api/v1/network-device/dev-999     # 404
```

Lösungen liegen in `solutions/`. Erst nach eigenem Versuch öffnen.

## Fragen zu 6.7 (agentenbasiert vs. agentenlos)

1. Wie unterscheiden sich **Ansible** (agentenlos, Push über SSH/API, YAML-Playbooks) und **Puppet/Chef** (Agent auf dem Zielsystem, Pull-Modell, Manifests/Recipes)? Was bedeutet das für Netzwerkgeräte, auf denen man keinen Agenten installieren kann?
2. Was ist **Idempotenz**, und warum ist `ios_config` mit `lines` idempotent, ein Skript mit `send_command("interface …")` aber nicht?
3. Wofür steht jeweils: Inventory, Playbook, Play, Task, Modul, Handler, Variable, Template (Jinja2), Vault?
4. Nenne je einen Vor- und Nachteil von Push (Ansible) und Pull (Puppet) für ein Netz mit 2000 Switches.

<details><summary>Antworten</summary>

1. **Ansible braucht nichts auf dem Zielgerät, Puppet und Chef brauchen einen Agenten.** Ansible verbindet sich von einem zentralen Rechner per SSH, NETCONF oder API und schiebt die Änderungen hin (Push). Bei Puppet und Chef holt sich ein Agent auf dem Zielsystem regelmäßig den Sollzustand vom Server (Pull). Auf Switches und Routern lässt sich meist kein Agent installieren, deshalb ist dort agentenlos der Normalfall.
2. **Idempotent heißt: Mehrfaches Ausführen ergibt denselben Zustand, ohne unnötige Änderungen.** `ios_config` vergleicht die `lines` mit der laufenden Konfiguration und ändert nur, was abweicht. Ein Skript mit `send_command` schickt die Befehle bei jedem Lauf blind erneut.
3. **Inventory:** Liste der Zielgeräte und Gruppen. **Playbook:** Datei mit einem oder mehreren Plays. **Play:** ordnet Hosts ihre Tasks zu. **Task:** ein Aufruf eines Moduls. **Modul:** der Code, der die Aufgabe ausführt. **Handler:** Task, der nur nach einem `notify` läuft, z. B. Konfiguration speichern. **Variable:** Parameter. **Template:** Jinja2-Vorlage. **Vault:** verschlüsselte Geheimnisse.
4. **Push ist schnell und gezielt, Pull korrigiert Abweichungen von selbst.** Push: Änderungen wirken sofort, und der Einstieg ist einfach. Dafür ist die Parallelität begrenzt (Forks), und wer von Hand ändert, bleibt unbemerkt, bis der nächste Lauf kommt. Pull: Jedes Gerät holt sich regelmäßig seinen Sollzustand und stellt Abweichungen selbst zurück. Dafür braucht es Agenten und eine Server-Infrastruktur.

</details>
