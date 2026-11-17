# Campus Prep

Simulierter **Catalyst 9800 WLC** und simuliertes **Catalyst Center** in einer gemeinsamen Welt. Python-Standardbibliothek, keine Abhängigkeiten, läuft offline. Kein echtes Gerät, keine Verbindung zu echten Controllern.

> Stand: Phase 1 (siehe [`docs/UMFANG.md`](docs/UMFANG.md)). Es gibt noch keine Weboberfläche und keine Labs.

## Starten

```sh
python3 start.py            # Port 8090, nur localhost
python3 -m unittest discover -s tests
```

## WLC-CLI

`POST /wlc/cli` mit `{"command": "show wlan summary"}` liefert `{"output": …, "prompt": …}`. Die Sitzung merkt sich den Modus.

```sh
curl -s localhost:8090/wlc/cli -d '{"command":"configure terminal"}'
curl -s localhost:8090/wlc/cli -d '{"command":"wlan Corp_Profile 1 Corp"}'
```

Umgesetzt:

| Bereich | Befehle |
|---|---|
| Konfiguration | `wlan <profil> <id> <ssid>` mit `security wpa akm psk`, `security wpa psk set-key ascii 0 <key>`, `shutdown`; `wireless profile policy <name>` mit `vlan`, `description`, `shutdown`; `wireless tag policy <name>` mit `wlan <profil> policy <policy>`; `ap <ethernet-mac>` mit `policy-tag <name>` |
| Show (Format belegt) | `show wlan summary`, `show ap summary`, `show ap tag summary`, `show wireless client summary`, `show wireless profile policy summary` |

Die Welt hat zwei APs und zwei Clients. Das Lernmoment: Ein AP ohne eigenes Policy Tag nutzt `default-policy-tag`, das kein WLAN enthält. Die SSID wird nicht ausgestrahlt, und `show wireless client summary` bleibt leer, bis dem AP ein Policy Tag mit dem WLAN zugewiesen ist. WLAN und Policy Profile sind nach dem Anlegen administrativ down.

## Catalyst Center

Pfade und Header wie im Original: `POST /dna/system/api/v1/auth/token` (HTTP Basic, Übungszugang `admin`/`admin`) liefert ein Token für den Header `X-Auth-Token`. Danach `GET /dna/intent/api/v1/network-device`, `…/network-device/count` und `…/network-device/{id}` mit den Filtern `hostname`, `family`, `managementIpAddress`, `macAddress`, `platformId`, `role`, `reachabilityStatus`, `softwareVersion`, `serialNumber`, `type`, `id`, `associatedWlcIp` sowie `offset` und `limit`.

Das Catalyst Center hat keinen eigenen Bestand: Controller und APs kommen aus derselben Welt wie bei der WLC-CLI. Ein AP, der nicht registriert ist, fehlt in beiden.

## Belegstand

Was belegt ist, was aus Wissen stammt und was offen bleibt, steht in [`docs/QUELLEN.md`](docs/QUELLEN.md). Nicht belegte Ausgaben und Endpunkte werden nicht erfunden: Der Simulator lehnt sie ab und sagt, dass sie fehlen.

> Kein offizielles Cisco-Material. Cisco, Catalyst und Catalyst Center sind Marken von Cisco Systems, Inc.
