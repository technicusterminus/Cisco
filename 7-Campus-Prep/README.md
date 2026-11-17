# Campus Prep

Simulierter **Catalyst 9800 WLC** und simuliertes **Catalyst Center** in einer gemeinsamen Welt. Python-Standardbibliothek, keine Abhängigkeiten, läuft offline. Kein echtes Gerät, keine Verbindung zu echten Controllern.

> Stand: Phase 1, 2a, 2c und 2d (siehe [`docs/UMFANG.md`](docs/UMFANG.md)). Die WLC hat eine Weboberfläche und sechs Labs, das Catalyst Center noch keine Oberfläche.

## Starten

```sh
python3 start.py            # Port 8090, nur localhost; Zustand in ./data; Oberfläche unter http://127.0.0.1:8090/
python3 start.py --ephemeral   # ohne dauerhaften Zustand (temporäres Verzeichnis, für Tests)
python3 -m unittest discover -s tests
node tests/gui/smoke.js     # Browser-Test (braucht Node.js und Playwright)
python3 Labs-Quelle/build_labs.py   # labs/*.json neu erzeugen (deterministisch)
```

## WLC-Oberfläche

`http://127.0.0.1:8090/` zeigt die WebUI des simulierten C9800: Dashboard, Monitoring (Access Points, Clients), Configuration (WLANs, Policy, Tags, AP-Tags), Administration (CLI) und die Simulations-Seite *Client-Diagnose*, die erklärt, warum ein Client nicht verbunden ist. Jeder Dialog zeigt vorab das **CLI-Äquivalent**; Änderungen laufen durch dieselbe CLI und werden atomar angewendet (bei einem Fehler bleibt alles wie vorher). Die Menüstruktur ist aus dem Wissen über die WebUI nachgebaut (siehe `docs/QUELLEN.md`).

## Labs

Die Seite *Labs (Simulation)* startet sechs Labs (vier Fehlersuchen, zwei Aufgaben nach Anforderungen), siehe [`docs/LAB-KATALOG.md`](docs/LAB-KATALOG.md). Ein Start setzt die Welt zurück. Bewertet wird das Verhalten (Client verbunden, VLAN, Zuordnungen), mit getrennten Prüfungen für *Funktion* und *Sicherheit / Least Privilege*; die naheliegende falsche Abkürzung besteht nie. Modi: *geführt* (vier Hinweisstufen, Lösung, Client-Diagnose) und *Prüfung* (keine Hilfe, keine Details). Verständnisfragen zählen nicht zum Bestehen.

## Speichern und Fortschritt

Der Zustand (Konfiguration, Welt, laufende Lab-Sitzung) wird nach jeder Änderung automatisch in `./data` gespeichert und beim Start wieder geladen (`--data DIR` wählt ein anderes Verzeichnis, `--ephemeral` schaltet das ab). Auf der Seite *Labs* gibt es zusätzlich **benannte Stände** (speichern, laden, löschen; der Fortschritt bleibt dabei erhalten) und den **Lab-Fortschritt**: je Lab bestanden (geführt oder Prüfung), Starts, Prüfläufe, wenigste Hinweise, richtige Fragen.

Die Dateien sind versioniert (`kind`, `version`), werden atomar geschrieben und enthalten keine Zeitstempel. Eine beschädigte oder fremde Datei wird nicht geladen, sondern als `*.bad` aufgehoben. Das Verzeichnis `data/` steht in `.gitignore`; es enthält die Übungsschlüssel der Labs im Klartext und gehört nicht ins Repository.

## WLC-CLI

`POST /wlc/cli` mit `{"command": "show wlan summary"}` liefert `{"output": …, "prompt": …}`. Die Sitzung merkt sich den Modus.

```sh
curl -s localhost:8090/wlc/cli -d '{"command":"configure terminal"}'
curl -s localhost:8090/wlc/cli -d '{"command":"wlan Corp_Profile 1 Corp"}'
```

Umgesetzt:

| Bereich | Befehle |
|---|---|
| Konfiguration | `wlan <profil> <id> <ssid>` mit `security wpa akm psk`, `security wpa psk set-key ascii 0 <key>`, `shutdown`; `wireless profile policy <name>` mit `vlan`, `description`, `shutdown`; `wireless tag policy <name>` mit `wlan <profil> policy <policy>`; `ap <ethernet-mac>` mit `policy-tag <name>` oder `no policy-tag`; Löschen mit `no wlan`, `no wireless profile policy`, `no wireless tag policy` |
| Show (Format belegt) | `show wlan summary`, `show ap summary`, `show ap tag summary`, `show wireless client summary`, `show wireless profile policy summary` |

Die Welt hat zwei APs und zwei Clients. Das Lernmoment: Ein AP ohne eigenes Policy Tag nutzt `default-policy-tag`, das kein WLAN enthält. Die SSID wird nicht ausgestrahlt, und `show wireless client summary` bleibt leer, bis dem AP ein Policy Tag mit dem WLAN zugewiesen ist. WLAN und Policy Profile sind nach dem Anlegen administrativ down.

## Catalyst Center

Pfade und Header wie im Original: `POST /dna/system/api/v1/auth/token` (HTTP Basic, Übungszugang `admin`/`admin`) liefert ein Token für den Header `X-Auth-Token`. Danach `GET /dna/intent/api/v1/network-device`, `…/network-device/count` und `…/network-device/{id}` mit den Filtern `hostname`, `family`, `managementIpAddress`, `macAddress`, `platformId`, `role`, `reachabilityStatus`, `softwareVersion`, `serialNumber`, `type`, `id`, `associatedWlcIp` sowie `offset` und `limit`.

Das Catalyst Center hat keinen eigenen Bestand: Controller und APs kommen aus derselben Welt wie bei der WLC-CLI. Ein AP, der nicht registriert ist, fehlt in beiden.

## Belegstand

Was belegt ist, was aus Wissen stammt und was offen bleibt, steht in [`docs/QUELLEN.md`](docs/QUELLEN.md). Nicht belegte Ausgaben und Endpunkte werden nicht erfunden: Der Simulator lehnt sie ab und sagt, dass sie fehlen.

> Kein offizielles Cisco-Material. Cisco, Catalyst und Catalyst Center sind Marken von Cisco Systems, Inc.
