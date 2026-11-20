# Campus Prep

Simulierter **Catalyst 9800 WLC** und simuliertes **Catalyst Center** in einer gemeinsamen Welt. Python-Standardbibliothek, keine Abhängigkeiten, läuft offline. Kein echtes Gerät, keine Verbindung zu echten Controllern.

> Stand: Phase 1, 2a, 2c, 2d, 2e, 3a, 3b, 3c, 3d, 3e und 3f (siehe [`docs/UMFANG.md`](docs/UMFANG.md)). Die WLC hat eine Weboberfläche und neunzehn Labs (dreizehn davon für CCNP Enterprise Wireless), das Catalyst Center noch keine Oberfläche.

## Ohne Python öffnen

**`WLC-Simulator.html` per Doppelklick im Browser öffnen** (Chrome, Edge, Firefox): Die WLC mit Weboberfläche, CLI und allen neunzehn Labs läuft vollständig im Browser, ohne Python, ohne Webserver und ohne Netzwerk. Der Zustand und der Lab-Fortschritt bleiben im lokalen Speicher des Browsers erhalten (pro Browser und Gerät; im privaten Modus nicht).

Grenzen der Einzeldatei:

- Das **Catalyst Center** ist nicht enthalten: Seine REST-API braucht einen Server (`python3 start.py`).
- Der **Prüfungsmodus** ist hier eine Selbstverpflichtung: Hinweise und Lösungen stehen im Quelltext der Datei. Mit dem Server liefert die API sie im Prüfungsmodus nicht aus.
- Die Datei ist **generiert** (`python3 tools/build_standalone.py`) und eingecheckt; ein Test prüft, dass sie zu den Quellen passt.

Die Browser-Engine (`static/engine.js`) ist eine zweite Umsetzung derselben Regeln wie die Python-Engine. Ein Paritätstest spielt viele Szenarien (über 1000 HTTP-Schritte, alle Labs in beiden Modi, Persistenz-Randfälle) gegen beide ab und verlangt identische Antworten (`node tests/parity/parity.js`).

## Starten

```sh
python3 start.py            # Port 8090, nur localhost; Zustand in ./data; Oberfläche unter http://127.0.0.1:8090/
python3 start.py --ephemeral   # ohne dauerhaften Zustand (temporäres Verzeichnis, für Tests)
python3 -m unittest discover -s tests
node tests/gui/smoke.js     # Browser-Test (braucht Node.js und Playwright)
STANDALONE=1 node tests/gui/smoke.js   # derselbe Test gegen WLC-Simulator.html (ohne Server, offline)
node tests/parity/parity.js # Python-Engine und Browser-Engine müssen gleich antworten
python3 tools/build_standalone.py   # WLC-Simulator.html neu bauen
python3 Labs-Quelle/build_labs.py   # labs/*.json neu erzeugen (deterministisch)
```

## WLC-Oberfläche

`http://127.0.0.1:8090/` zeigt die WebUI des simulierten C9800: Dashboard, Monitoring (Access Points, Clients), Configuration (WLANs, Policy, Tags, AP-Tags), Administration (CLI) und die Simulations-Seite *Client-Diagnose*, die erklärt, warum ein Client nicht verbunden ist. Jeder Dialog zeigt vorab das **CLI-Äquivalent**; Änderungen laufen durch dieselbe CLI und werden atomar angewendet (bei einem Fehler bleibt alles wie vorher). Die Menüstruktur ist aus dem Wissen über die WebUI nachgebaut (siehe `docs/QUELLEN.md`).

## Labs

Die Seite *Labs (Simulation)* startet neunzehn Labs (elf Fehlersuchen, acht Aufgaben nach Anforderungen), siehe [`docs/LAB-KATALOG.md`](docs/LAB-KATALOG.md). Die Labs 07 bis 19 gehören zum Track *CCNP Enterprise Wireless (300-430 ENWLSI)* und üben FlexConnect, 802.1X mit RADIUS, Local Web Authentication, Mobility, RF-Profile und QoS. Ein Start setzt die Welt zurück. Bewertet wird das Verhalten (Client verbunden, VLAN, Zuordnungen), mit getrennten Prüfungen für *Funktion* und *Sicherheit / Least Privilege*; die naheliegende falsche Abkürzung besteht nie. Modi: *geführt* (vier Hinweisstufen, Lösung, Client-Diagnose) und *Prüfung* (keine Hilfe, keine Details). Verständnisfragen zählen nicht zum Bestehen.

## Speichern und Fortschritt

Der Zustand (Konfiguration, Welt, laufende Lab-Sitzung) wird nach jeder Änderung automatisch in `./data` gespeichert und beim Start wieder geladen (`--data DIR` wählt ein anderes Verzeichnis, `--ephemeral` schaltet das ab). Auf der Seite *Labs* gibt es zusätzlich **benannte Stände** (speichern, laden, löschen; der Fortschritt bleibt dabei erhalten) und **Export und Import als Datei** (`campusprep-<Name>.json`, auch in `WLC-Simulator.html`: Sicherung, Wechsel des Browsers oder Weitergabe; ein Import prüft die Datei, legt sie als neuen Stand ab und lädt sie nicht; ein vorhandener Name wird nicht überschrieben; die Datei enthält die Konfigurationswerte (Schlüssel, Passwörter) im Klartext, es sind Übungswerte: keine echten Zugangsdaten eintragen oder weitergeben) und den **Lab-Fortschritt**: je Lab bestanden (geführt oder Prüfung), Starts, Prüfläufe, wenigste Hinweise, richtige Fragen.

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
| FlexConnect | `wireless profile flex <name>` mit `native-vlan-id` und `vlan-name`/`vlan-id`; `wireless tag site <name>` mit `no local-site` und `flex-profile`; im Policy Profile `no central switching`; am AP `site-tag`. Ein Site Tag ohne Local Site versetzt den AP in den FlexConnect-Modus |
| Show (Format belegt) | `show wlan summary`, `show ap summary`, `show ap tag summary`, `show wireless client summary`, `show wireless profile policy summary`, `show wireless profile flex summary`, `show wireless tag site summary` |

Die Welt hat zwei APs und zwei Clients. Das Lernmoment: Ein AP ohne eigenes Policy Tag nutzt `default-policy-tag`, das kein WLAN enthält. Die SSID wird nicht ausgestrahlt, und `show wireless client summary` bleibt leer, bis dem AP ein Policy Tag mit dem WLAN zugewiesen ist. WLAN und Policy Profile sind nach dem Anlegen administrativ down.

## Catalyst Center

Pfade und Header wie im Original: `POST /dna/system/api/v1/auth/token` (HTTP Basic, Übungszugang `admin`/`admin`) liefert ein Token für den Header `X-Auth-Token`. Danach `GET /dna/intent/api/v1/network-device`, `…/network-device/count` und `…/network-device/{id}` mit den Filtern `hostname`, `family`, `managementIpAddress`, `macAddress`, `platformId`, `role`, `reachabilityStatus`, `softwareVersion`, `serialNumber`, `type`, `id`, `associatedWlcIp` sowie `offset` und `limit`.

Das Catalyst Center hat keinen eigenen Bestand: Controller und APs kommen aus derselben Welt wie bei der WLC-CLI. Ein AP, der nicht registriert ist, fehlt in beiden.

## Belegstand

Was belegt ist, was aus Wissen stammt und was offen bleibt, steht in [`docs/QUELLEN.md`](docs/QUELLEN.md). Nicht belegte Ausgaben und Endpunkte werden nicht erfunden: Der Simulator lehnt sie ab und sagt, dass sie fehlen.

> Kein offizielles Cisco-Material. Cisco, Catalyst und Catalyst Center sind Marken von Cisco Systems, Inc.
