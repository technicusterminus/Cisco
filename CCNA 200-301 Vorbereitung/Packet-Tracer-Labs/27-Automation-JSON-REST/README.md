# Lab 27 – Automatisierung: JSON, REST und Konfigurationsmanagement (ohne Packet Tracer)

**CCNA-Ziele:** 6.5 REST-API (Authentisierung, CRUD, HTTP-Verben, Datenformate) · 6.6 Konfigurationsmanagement (Ansible, Terraform) · 6.7 JSON lesen
**Dauer:** ca. 2 h · **Niveau:** leicht bis mittel · **Voraussetzung:** Python 3.9+, `pip install pyyaml`

Alles läuft lokal. Die Tests starten die Mock-API selbst (nur Standardbibliothek). **Die Tests wurden mit den Musterlösungen ausgeführt (grün).**

| Aufgabe | Ziel | Inhalt |
|---|---|---|
| 1 `ex01_json/` | 6.7 | JSON-Aufbau lesen, Daten in Python extrahieren, kaputtes JSON reparieren |
| 2 `ex02_rest/` | 6.5 | CRUD mit curl und Python-Client gegen eine VLAN-API (201, 204, 401, 403, 404, 409, 415) |
| 3 `ex03_config_mgmt/` | 6.6 | Ansible-Playbook reparieren, Terraform-Datei lesen, agentenlos vs. agentenbasiert |

## Ablauf

```
cd ex01_json && python3 -m unittest -v test_ex01     # schlägt zuerst fehl (NotImplementedError)
python3 check_json.py                                 # nach der Reparatur: OK
cd ../ex02_rest && python3 -m unittest -v test_ex02
cd ../ex03_config_mgmt && python3 check_playbook.py
```

Die Mock-API startest du auch einzeln: `python3 mock_api/server.py 8080`. Lösungen liegen in `solutions/`; erst nach eigenem Versuch öffnen.

## Zusatzfragen zu 6.1–6.4 (Konzepte)

Die Konzeptfragen zu Automatisierungs-Auswirkungen, controllerbasierten Netzen, SDN-Architekturen und KI im Netzbetrieb stehen in [`28-Konzept-Fallstudien.md`](../28-Konzept-Fallstudien.md).
