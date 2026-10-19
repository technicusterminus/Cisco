# Lab 20 – Python- und API-Drills (ohne CML)

**Blueprint-Bezug:** 6.1 Python lesen · 6.2 JSON erstellen · 6.3 YANG · 6.4 Controller-APIs · 6.5 HTTP-Codes und API-Payloads · 6.7 agentenbasierte/agentenlose Automation · Teile von 5.3 (REST-API-Sicherheit)
**Dauer:** ca. 3 h (in Häppchen) · **Niveau:** leicht bis mittel · **Voraussetzung:** Python 3.9+, `pip install requests pyyaml jinja2 pyang`

Diese Drills laufen komplett lokal: Eine kleine Mock-API (Standardbibliothek) spielt einen Controller mit Token-Anmeldung, Pagination, Fehlercodes und asynchronen Tasks. **Alle Tests wurden mit den Musterlösungen ausgeführt (grün).**

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

1. Ansible verbindet sich von einem Kontrollknoten per SSH/NETCONF/API und führt Module aus, ohne Software auf dem Ziel (agentenlos). Puppet/Chef brauchen einen Agenten, der periodisch beim Master den Sollzustand abholt (Pull). Für Netzwerkgeräte ist die agentenlose Variante der Normalfall, weil Switches/Router keinen Agenten ausführen können.
2. Idempotenz: Mehrfaches Ausführen erzeugt denselben Zustand ohne unnötige Änderungen. `ios_config` vergleicht `lines` mit der laufenden Konfiguration und ändert nur Abweichungen. Ein CLI-Skript schickt Befehle blind.
3. Inventory = Liste der Zielgeräte/Gruppen; Playbook = Datei mit Plays; Play = Zuordnung Hosts → Tasks; Task = ein Modulaufruf; Modul = Code, der die Aufgabe ausführt; Handler = Task, der nur bei `notify` läuft (z. B. Konfiguration speichern); Variable = Parameter; Template = Jinja2-Vorlage; Vault = verschlüsselte Geheimnisse.
4. Push: sofortige, gezielte Änderungen und einfacher Start; dafür begrenzte Parallelität (Forks) und keine automatische Drift-Korrektur. Pull: Geräte holen sich den Sollzustand selbst und korrigieren Drift, dafür braucht man Agenten und eine Master-Infrastruktur.

</details>
