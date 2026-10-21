# Lab 19 – RESTCONF, NETCONF, YANG und EEM

**Dauer:** 90 min · **Niveau:** mittel bis schwer · **Nodes:** 1× csr1000v, 1× external_connector, 1× iosv

Ein IOS-XE-Router wird programmierbar: RESTCONF und NETCONF aktivieren, YANG-Daten lesen und per HTTP-Methoden ändern, HTTP-Statuscodes lesen und ein EEM-Applet schreiben. Für die Python-Teile brauchst du Netzwerkzugang zu CSR1 (External Connector, Default NAT).

**Lernziele:** Nach diesem Lab kannst du …

- RESTCONF und NETCONF auf IOS XE aktivieren und abfragen.
- YANG-Pfade lesen und PUT, PATCH und GET unterscheiden.
- Ein EEM-Applet schreiben, das auf Syslog oder Tracking reagiert.

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
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

**Teil 1: Zugang über APIs**

1. **Benutzer, SSH und HTTPS.** Lege `admin` mit `privilege 15` an, aktiviere SSH Version 2, `ip http secure-server` und `ip http authentication local`. Lies die DHCP-Adresse von Gi1 aus (`show ip interface brief`).
   - **Prüfen:** `show ip http server secure status` meldet den HTTPS-Server als aktiv.
2. **RESTCONF.** Schalte `restconf` ein. Rufe vom CML-Host aus auf: `curl -k -u admin:… -H "Accept: application/yang-data+json" https://<CSR1>/restconf/data/ietf-interfaces:interfaces`.
   - **Prüfen:** Du bekommst Status 200 und JSON mit allen Interfaces.
   - **Denkfrage:** Welche HTTP-Methoden gibt es, und was bedeuten die Statuscodes 200, 201, 204, 400, 401, 403, 404, 405, 409, 415 und 500?
3. **NETCONF.** Schalte `netconf-yang` ein. Öffne eine Sitzung mit `ssh -p 830 admin@<CSR1> -s netconf`. Schicke nach dem `<hello>` ein `<get-config>` mit Filter auf `ietf-interfaces`.
   - **Prüfen:** Das `<hello>` des Routers listet seine Capabilities, darunter `urn:ietf:params:netconf:base:1.1`.
   - **Denkfrage:** Wozu dienen `<edit-config>`, `<commit>` und `<lock>`? Welche Datastores gibt es?
4. **YANG lesen.** Nimm die Antwort aus Schritt 2 und markiere darin Container, List (mit dem Key `name`) und Leafs.
   - **Denkfrage:** Was unterscheidet die Modelle `ietf-interfaces`, `Cisco-IOS-XE-native` und OpenConfig?
5. **Ändern per PATCH.** Setze per PATCH auf `…/ietf-interfaces:interfaces/interface=GigabitEthernet2` eine Description.
   - **Prüfen:** Die Antwort ist 204. `show running-config interface Gi2` zeigt die neue Description.
   - **Prüfen:** Provoziere danach Fehler: ein falscher Pfad liefert 404, ein kaputter Body 400.
6. **Python.** Führe [`python/restconf_get.py`](python/restconf_get.py) und [`python/netconf_get.py`](python/netconf_get.py) gegen CSR1 aus (Zugangsdaten als Argumente). Ergänze dann `restconf_patch.py`.
   - **Prüfen:** Beide Skripte geben die Interface-Liste aus.

**Teil 2: EEM**

7. **Applet bei Link-Wechsel.** Lege `event manager applet LINKFLAP` an mit `event syslog pattern "Interface GigabitEthernet2, changed state"`, `action 1.0 syslog msg "EEM: Link Gi2 hat Status gewechselt"`, `action 2.0 cli command "enable"` und `action 3.0 cli command "show ip interface brief | redirect flash:ipint.txt"`. Teste mit `shutdown` und `no shutdown` an Gi2.
   - **Prüfen:** `show logging | include EEM` zeigt die Meldung, `dir flash:` die Datei ipint.txt.
   - **Denkfrage:** Warum steht im Pattern der lange Interface-Name?
8. **Einordnen.**
   - **Denkfrage:** Was unterscheidet ein Applet von einem Tcl-Skript? Welche Auslöser und Aktionen gibt es, und wofür setzt man EEM typischerweise ein?
9. **EEM mit Tracking.** Lege eine IP-SLA-Messung zu 2.2.2.2 an (`ip sla schedule` nicht vergessen), dazu `track 1`. Ein Applet mit `event track 1 state down` schreibt eine Syslog-Meldung und fährt per `cli command` ein Test-Interface herunter.
   - **Prüfen:** Schalte auf R2 Lo0 ab. Nach einigen Sekunden geht `track 1` auf Down, und das Applet läuft.

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** GET liest, POST legt neu an, PUT ersetzt ganz, PATCH ändert einzelne Felder, DELETE löscht. 200 OK, 201 angelegt, 204 erfolgreich ohne Inhalt, 400 Anfrage fehlerhaft, 401 nicht angemeldet, 403 keine Berechtigung, 404 nicht gefunden, 405 Methode nicht erlaubt, 409 Konflikt (z. B. existiert schon), 415 falscher Content-Type, 500 Fehler im Server.
- **Zu 3:** `<edit-config>` ändert einen Datastore, `<commit>` übernimmt den Candidate in running, `<lock>` sperrt einen Datastore gegen gleichzeitige Änderungen. Datastores: running (aktiv), candidate (Entwurf), startup (beim Start geladen).
- **Zu 4:** `ietf-interfaces` ist ein herstellerneutrales Standardmodell mit wenigen Feldern. `Cisco-IOS-XE-native` bildet die ganze IOS-XE-Konfiguration ab, gilt aber nur für Cisco. OpenConfig ist ein herstellerübergreifendes Modell der Netzbetreiber.
- **Zu 7:** Das Pattern ist ein regulärer Ausdruck gegen den Text der Syslog-Meldung. Dort steht `GigabitEthernet2`, die Kurzform `Gi2` kommt nicht vor.
- **Zu 8:** Ein Applet besteht aus wenigen Zeilen in der Konfiguration. Ein Tcl-Skript liegt als Datei vor und kann Schleifen und Logik. Auslöser sind z. B. syslog, timer, cli, snmp, track und interface. Aktionen sind z. B. cli, syslog, mail und set. Typische Einsätze: Selbstheilung, automatische Sicherung bei Änderungen, Daten sammeln, sobald ein Fehler auftritt.

</details>

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

| Test | Das solltest du sehen |
|---|---|
| RESTCONF-GET | Status 200 mit JSON |
| NETCONF-Hello | `urn:ietf:params:netconf:base:1.1` in den Capabilities |
| Link-Wechsel an Gi2 | Syslog-Zeile vom EEM-Applet |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Was bedeutet HTTP 401, was 403?
<details><summary>Antwort</summary>

**401: nicht angemeldet. 403: angemeldet, aber nicht berechtigt.** Bei 401 fehlen die Zugangsdaten oder sie sind falsch. Bei 403 kennt der Server dich, dein Privileg oder deine Rolle reicht aber nicht.

</details>

2. Worin unterscheidet sich PUT von PATCH in RESTCONF?
<details><summary>Antwort</summary>

**PUT ersetzt die ganze Ressource, PATCH ändert nur die mitgeschickten Felder.** Was bei PUT fehlt, wird gelöscht oder auf den Standard gesetzt. PATCH lässt alles andere unberührt.

</details>

3. Warum löst `event syslog pattern "Gi2"` nicht aus?
<details><summary>Antwort</summary>

**Weil die Syslog-Meldung den langen Namen enthält.** Dort steht `GigabitEthernet2`. Das Pattern ist ein regulärer Ausdruck gegen den Text, und `Gi2` kommt darin nicht vor.

</details>

## Prüfungsbezug
- RESTCONF: HTTPS, JSON oder XML, REST-Methoden. NETCONF: SSH auf Port 830, XML-RPC, Datastores.
- YANG ist ein Datenmodell, kein Transport.
- Statuscodes: 2xx Erfolg, 4xx Fehler des Clients, 5xx Fehler des Servers.
- Ein EEM-Pattern muss den Syslog-Text treffen, also den vollen Interface-Namen.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
