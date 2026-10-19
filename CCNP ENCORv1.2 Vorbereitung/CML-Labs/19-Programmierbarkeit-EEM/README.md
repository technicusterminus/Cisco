# Lab 19 – RESTCONF, NETCONF, YANG und EEM

**Dauer:** 90 min · **Niveau:** mittel bis schwer · **Nodes:** 1× csr1000v, 1× external_connector, 1× iosv

Ein IOS-XE-Router wird programmierbar: RESTCONF und NETCONF aktivieren, YANG-Daten lesen und per HTTP-Methoden ändern, HTTP-Statuscodes lesen und ein EEM-Applet schreiben. Für die Python-Teile brauchst du Netzwerkzugang zu CSR1 (External Connector, Default NAT).

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::4.6` | NETCONF und RESTCONF | 40 |
| `Ziel::6.3` | YANG | 21 |
| `Ziel::6.5` | HTTP-Codes und API-Payloads | 25 |
| `Ziel::6.6` | EEM-Applets | 27 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
 CML-Host (NAT) ─ EXT ─ CSR1 ─ R2 ─ Lo0 2.2.2.2
        Gi1 (DHCP)   Gi2  10.0.12.0/30
```

| Gerät | Interface | Adresse |
|---|---|---|
| CSR1 | Gi1 / Gi2 / Lo0 | DHCP (CML-NAT) / 10.0.12.1/30 / 1.1.1.1/32 |
| R2 | Gi0/0 / Lo0 | 10.0.12.2/30 / 2.2.2.2/32 |

Benutzer für alle Zugänge: `admin` / `Lab#2026!` (nur Lab).

## Teil A – Bauen

**Teil 1 – Zugang**

1. **Benutzer, SSH, HTTPS.** Lege `admin` (privilege 15) an, aktiviere SSH 2 und `ip http secure-server`, `ip http authentication local`. Lies die DHCP-Adresse von Gi1 aus.
2. **RESTCONF.** `restconf` aktivieren. Rufe `https://<CSR1>/restconf/data/ietf-interfaces:interfaces` per `curl -k -u admin:… -H "Accept: application/yang-data+json"` auf. Welche HTTP-Methoden gibt es (GET lesen, POST anlegen, PUT ersetzen, PATCH ändern, DELETE löschen) und was bedeuten die Statuscodes 200, 201, 204, 400, 401, 403, 404, 405, 409, 415, 500?
3. **NETCONF.** `netconf-yang` aktivieren (Port 830, SSH-Subsystem), Sitzung per `ssh -p 830 admin@<CSR1> -s netconf`; `<hello>` mit Capabilities, danach `<get-config>` mit Filter auf `ietf-interfaces`. Rollen von `<edit-config>`, `<commit>`, `<lock>`, Datastores (running/candidate/startup).
4. **YANG lesen.** Hole das JSON/XML der Interface-Liste und markiere Container, List (Key `name`), Leaf und Typen. Standard-Modell (`ietf-interfaces`) vs. Native (`Cisco-IOS-XE-native`) vs. OpenConfig.
5. **Ändern.** Setze per PATCH auf `…/interface=GigabitEthernet2` eine Description. Prüfe per CLI. Welche Fehler (400/404/409) provozierst du mit falschen Pfaden/Bodies?
6. **Python.** Nutze [`python/restconf_get.py`](python/restconf_get.py) und [`python/netconf_get.py`](python/netconf_get.py) (Login als Argumente) gegen CSR1. Ergänze `restconf_patch.py`.

**Teil 2 – EEM**

7. **Applet.** `event manager applet LINKFLAP`: `event syslog pattern "Interface GigabitEthernet2, changed state"`, `action 1.0 syslog msg "EEM: Link Gi2 hat Status gewechselt"`, `action 2.0 cli command "enable"`, `action 3.0 cli command "show ip interface brief | redirect flash:ipint.txt"`. Teste durch `shutdown`/`no shutdown` an Gi2.
8. **Konzepte.** Applet vs. Tcl-Skript, Event-Detektoren (syslog, timer, cli, snmp, track, interface), Actions (cli, syslog, mail, set), `event manager run`, Policy-Hierarchie, typische Einsatzfälle (Selbstheilung, Konfig-Backup bei Änderung).
9. **Track + EEM.** IP SLA zu 2.2.2.2 (`ip sla schedule` nicht vergessen), `track 1`, EEM-Event `track 1 state down` → syslog + `cli command "shutdown"` auf einem Test-Interface.

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** RESTCONF-Aufrufe liefern `401 Unauthorized`, obwohl Benutzer und Passwort stimmen.

**Ticket 2:** Die NETCONF-Verbindung auf Port 830 wird abgelehnt (`Connection refused`).

**Ticket 3:** `curl https://…/restconf/` hängt oder bricht mit Connection refused ab, SSH funktioniert.

**Ticket 4:** Beim Link-Flap auf Gi2 erscheint die EEM-Syslog-Zeile nie, `show event manager policy registered` zeigt das Applet.

**Ticket 5:** `show track 1` auf CSR1 ist Down (IP SLA 2.2.2.2 schlägt fehl), R2 antwortet nicht.

## Verifikation

```
show platform software yang-management process
show netconf-yang sessions
show ip http server status
show event manager policy registered
show logging | include EEM
```
Erwartet: RESTCONF antwortet mit 200 und JSON, NETCONF-Hello zeigt `urn:ietf:params:netconf:base:1.1`, EEM schreibt die Syslog-Zeile bei Link-Wechsel.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Was bedeutet HTTP 401, was 403?
<details><summary>Antwort</summary>

401: nicht authentifiziert (fehlende/falsche Zugangsdaten). 403: authentifiziert, aber nicht berechtigt (Privilege/Rolle).

</details>

2. Worin unterscheidet sich PUT von PATCH in RESTCONF?
<details><summary>Antwort</summary>

PUT ersetzt die Ressource vollständig (Ressource wird neu geschrieben), PATCH ändert nur die übergebenen Felder.

</details>

3. Warum löst `event syslog pattern "Gi2"` nicht aus?
<details><summary>Antwort</summary>

Die Syslog-Meldung enthält den ausgeschriebenen Namen `GigabitEthernet2`. Das Pattern ist ein Regex gegen den Text, `Gi2` kommt dort nicht vor.

</details>

## Prüfungsbezug

RESTCONF (HTTPS, JSON/XML, REST-Methoden) vs. NETCONF (SSH 830, XML-RPC, Datastores). YANG ist ein Datenmodell (kein Transport). Statuscodes: 2xx Erfolg, 4xx Clientfehler, 5xx Serverfehler. EEM-Pattern müssen den Syslog-Text exakt treffen (voller Interface-Name!).

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
