# Quellen und Belegstand

Regel wie in `6-Datacenter-Prep`: Befehle, Ausgabeformate, API-Pfade und Attribute werden nur übernommen, wenn sie belegt sind. Alles andere steht hier als *Wissen* (bekannt, aber in der Sitzung nicht gegen eine Quelle geprüft) oder als *Simulator-Festlegung*.

Cisco-Seiten (cisco.com, developer.cisco.com) waren beim Bau nicht erreichbar. Belegt wurde über öffentliche Repositories und Pakete.

## Belegt

| Thema | Quelle | Was daraus übernommen ist |
|---|---|---|
| C9800 Show-Ausgaben | genieparser (CiscoTestAutomation), `iosxe/show_wlan.py`, `show_ap.py`, `show_wireless.py`: Schemas und Beispielausgaben in den Parser-Kommentaren | Kopfzeilen und Spalten von `show wlan summary`, `show ap summary`, `show wireless client summary`, `show ap tag summary`, `show wireless profile policy summary`; die Liste der existierenden `show wireless …`/`show ap …`-Befehle |
| Catalyst-Center-API-Pfade | Python-SDK `dnacentersdk` 2.11.4 (Pfade aus dem Quelltext gelesen, nicht ausgeführt) | `POST /dna/system/api/v1/auth/token` (HTTP Basic, Antwort liefert das Token), Header `X-Auth-Token`, `GET /dna/intent/api/v1/network-device`, `…/network-device/count`, `…/network-device/{id}`-Familie, Filter-Parameter von `get_device_list` |
| Catalyst-Center-Felder eines Geräts | Ansible-Collection `cisco.dnac`, `network_device_info` (RETURN-Beispiel) | Feldnamen von `network-device`: `hostname`, `managementIpAddress`, `macAddress`, `serialNumber`, `platformId`, `softwareType`, `softwareVersion`, `family`, `type`, `role`, `reachabilityStatus`, `managementState`, `upTime`, `uptimeSeconds`, `associatedWlcIp`, `apManagerInterfaceIp` und weitere; Hülle `{"response": …, "version": …}` |

## Wissen (nicht in der Sitzung geprüft)

| Thema | Annahme |
|---|---|
| C9800 Konfigurationsbefehle | `wlan <profil> <id> <ssid>`, `security wpa psk set-key ascii 0 <key>`, `no shutdown`; `wireless profile policy <name>` mit `vlan`, `no shutdown`; `wireless tag policy <name>` mit `wlan <profil> policy <policy>`; `ap <ethernet-mac>` mit `policy-tag <name>`. Prompts `(config-wlan)#`, `(config-wireless-policy)#`, `(config-policy-tag)#`, `(config-ap)#` |
| C9800 Standardverhalten | WLAN und Policy Profile sind nach dem Anlegen administrativ down; ein AP ohne eigenes Tag nutzt `default-policy-tag`, `default-site-tag`, `default-rf-tag`; das Default Policy Tag enthält keine WLANs, die SSID wird dann nicht ausgestrahlt |
| Catalyst Center Token | Antwort von `auth/token` ist `{"Token": "<token>"}` (das SDK reicht das Objekt ungetypt durch, der Schlüssel ist nicht im Quelltext zu sehen) |
| Gerätewerte | `family` "Wireless Controller" bzw. "Unified AP", `softwareType` "IOS-XE", `reachabilityStatus` "Reachable", `managementState` "Managed" sind übliche Werte, nicht belegt |

| C9800-WebUI | Menüstruktur (Dashboard, Monitoring > Wireless, Configuration > Tags & Profiles und Wireless, Administration > Command Line Interface, Troubleshooting) und Spaltennamen sind aus dem Wissen über die WebUI nachgebaut, nicht gegen Screenshots geprüft |

## Simulator-Festlegungen

- Die Sicherheitsspalte von `show wlan summary` für PSK (`[WPA2][PSK][AES]`) ist aus den belegten 802.1x-Zeilen abgeleitet; ein PSK-Beispiel gab es in den Quellen nicht.
- Die Spalte *Method* heißt für PSK `PSK`; belegt sind nur `Dot1x` und `MAB`.
- Die Spalte *Tag Source* von `show ap tag summary` zeigt `Default`, wenn der AP kein eigenes Tag hat; belegt ist nur `Static`.
- Fehlermeldungen der CLI (`% Invalid input detected: "…"`) sind vereinfacht; das Gerät nennt den Fehlerort mit einer `^`-Markierung. Die Meldung für nicht umgesetzte Show-Befehle ist simulator-spezifisch.
- Die Client-Entscheidung (assoziiert oder nicht, mit Begründung) ist ein didaktisches Modell, keine Controller-Pipeline. Die Begründungen sind simulator-spezifisch.
- Fehler- und 401-Antworten des simulierten Catalyst Center sind vereinfacht.
- Die Löschbefehle `no wlan`, `no wireless profile policy`, `no wireless tag policy` lehnen ab, solange das Objekt in einem Policy Tag oder an einem AP verwendet wird. Ob und mit welchem Text das Gerät so reagiert, ist nicht belegt; Meldungen simulator-spezifisch. `no policy-tag` ohne Argument setzt den AP auf das Default Policy Tag.
- Die Seite *Client-Diagnose* und das *CLI-Äquivalent* in den Dialogen gibt es am echten Gerät nicht (Lernhilfen).
- Die Weboberfläche wendet Änderungen atomar an: Ein Fehler in einem Befehl setzt die Konfiguration auf den Stand davor zurück.
- Gespeicherte Stände und der Lab-Fortschritt sind ein Format dieses Projekts (`kind` campusprep-state, Version 1), kein Cisco-Format. Sie enthalten die Übungsschlüssel der Labs im Klartext; das Verzeichnis `data/` gehört nicht ins Repository.
- Zugangsdaten des Simulators sind Übungswerte (`admin`/`admin`), keine echten.

## Offen (nicht umgesetzt, weil nicht belegt)

- Ausgabeformate aller weiteren `show wireless …`-Befehle, `show wlan all`, `show ap name … config general`.
- Antwortformate von Site-, Health-, Client- und Wireless-Endpunkten des Catalyst Center (GET-Antworten sind im SDK ungetypt).
- RESTCONF/NETCONF-Modelle des C9800.
