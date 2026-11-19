# Lab 19 – RESTCONF, NETCONF, YANG und EEM

**Dauer:** 90 min · **Niveau:** mittel bis schwer · **Nodes:** 1× csr1000v, 1× Ubuntu, 1× iosv

Ein IOS-XE-Router wird programmierbar: RESTCONF und NETCONF aktivieren, YANG-Daten lesen und per HTTP-Methoden ändern, HTTP-Statuscodes lesen und ein EEM-Applet schreiben. Der Ubuntu-Knoten API-CLIENT bringt den API-Zugang im isolierten Lab mit. Beide Varianten starten mit festen IP-Adressen, lokalem Benutzer und AAA-Basis.

**Lernziele:** Nach diesem Lab kannst du …

- RESTCONF und NETCONF auf IOS XE aktivieren und abfragen.
- YANG-Pfade lesen und PUT, PATCH und GET unterscheiden.
- Ein EEM-Applet schreiben, das auf Syslog oder Tracking reagiert.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::4.6` | NETCONF und RESTCONF | 40 |
| `Ziel::6.3` | YANG | 27 |
| `Ziel::6.5` | HTTP-Codes und API-Payloads | 29 |
| `Ziel::6.6` | EEM-Applets | 29 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
 API-CLIENT ───────────── CSR1 ──────────── R2 ─ Lo0 2.2.2.2
 ens2 .2   192.0.2.0/30   Gi1 .1  Gi2 .1   10.0.12.0/30
```

| Gerät | Interface | Adresse |
|---|---|---|
| API-CLIENT | ens2 | 192.0.2.2/30 |
| CSR1 | Gi1 / Gi2 / Lo0 | 192.0.2.1/30 / 10.0.12.1/30 / 1.1.1.1/32 |
| R2 | Gi0/0 / Lo0 | 10.0.12.2/30 / 2.2.2.2/32 |

CSR1 verwendet `admin` / `Lab#2026!`. An der Linux-Konsole meldest du dich mit `cisco` / `cisco` an. Warte auf den Abschluss von cloud-init (`cloud-init status --wait`) und prüfe `ping -c 3 192.0.2.1`. Cisco dokumentiert beim ersten Start des CSR1000v mögliche administrativ abgeschaltete Ports. Stelle bei Bedarf auf Gi1 und Gi2 mit `no shutdown` den vorgesehenen Linkzustand her.

**Für beide Varianten:** Prüfe mit `show crypto key mypubkey rsa`, ob bereits ein RSA-Schlüssel existiert. Falls nötig, erzeuge ihn auf CSR1 in der Konsole mit `crypto key generate rsa general-keys modulus 2048` und aktiviere `ip ssh version 2`. Bestätige danach vom API-CLIENT per `ssh admin@192.0.2.1`, dass SSH auf Port 22 funktioniert. Die Grundübung benötigt keine Internetverbindung. [Cisco-Dokumentation zu CSR1000v](https://developer.cisco.com/docs/modeling-labs/csr-1000v/)

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

**Teil 1: Zugang über APIs**

1. **HTTPS aktivieren.** Der Benutzer und die lokale AAA-Basis stehen bereit. Prüfe die SSH-Erreichbarkeit wie oben. Setze `ip http authentication local` und `ip http secure-server`.
   - **Prüfen:** `show ip http server secure status` meldet den HTTPS-Server als aktiv.
2. **RESTCONF.** Schalte `restconf` ein. Führe vom API-CLIENT `python3 /opt/encor/restconf.py` aus und gib das CSR1-Passwort ein.
   - **Prüfen:** Du bekommst Status 200 und JSON mit allen Interfaces.
   - **Denkfrage:** Welche HTTP-Methoden gibt es, und was bedeuten die Statuscodes 200, 201, 204, 400, 401, 403, 404, 405, 409, 415 und 500?
3. **NETCONF.** Schalte `netconf-yang` ein. Öffne auf dem API-CLIENT eine Sitzung mit `ssh -p 830 -s admin@192.0.2.1 netconf`. Sende die folgenden zwei Zeilen jeweils vollständig. Das Client-Hello bietet nur NETCONF 1.0 an und verwendet deshalb auch für den RPC den Abschluss `]]>]]>`.

   ```xml
   <hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><capabilities><capability>urn:ietf:params:netconf:base:1.0</capability></capabilities></hello>]]>]]>
   <rpc message-id="1" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><get-config><source><running/></source><filter type="subtree"><interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/></filter></get-config></rpc>]]>]]>
   ```

   - **Prüfen:** Das `<hello>` des Routers listet seine Capabilities. Der anschließende `rpc-reply` enthält die Interface-Konfiguration.
   - **Denkfrage:** Wozu dienen `<edit-config>`, `<commit>` und `<lock>`? Welche Datastores gibt es?
4. **YANG lesen.** Nimm die Antwort aus Schritt 2 und markiere darin Container, List (mit dem Key `name`) und Leafs.
   - **Denkfrage:** Was unterscheidet die Modelle `ietf-interfaces`, `Cisco-IOS-XE-native` und OpenConfig?
5. **Ändern per PATCH.** Setze mit `python3 /opt/encor/restconf.py --description "ENCOR-Test"` die Description von GigabitEthernet2 per PATCH.
   - **Prüfen:** Die Antwort ist 204. `show running-config interface Gi2` zeigt die neue Description.
   - **Prüfen:** Rufe danach die Ressource mit einem falschen Pfad ab (`--path /restconf/data/ietf-interfaces:interfaces/interface=Missing`) und ordne den Statuscode ein. Wie würde sich ein syntaktisch ungültiger Request-Body davon unterscheiden?
6. **Python-Transfer (optional).** Für einen Client mit Netzwerkzugang zum CSR1 stehen die Beispiele in [`python/`](python/) bereit. Die vorkonfigurierte CML-Variante verwendet den Python-Client auf API-CLIENT.

**Teil 2: EEM**

7. **Applet bei Link-Wechsel.** Lege `event manager applet LINKFLAP` an mit `event syslog pattern "Interface GigabitEthernet2, changed state"`, `action 1.0 syslog msg "EEM: Link Gi2 hat Status gewechselt"`, `action 2.0 cli command "enable"` und `action 3.0 cli command "show ip interface brief | redirect flash:ipint.txt"`. Teste mit `shutdown` und `no shutdown` an Gi2.
   - **Prüfen:** `show logging | include EEM` zeigt die Meldung, `dir flash:` die Datei ipint.txt.
   - **Denkfrage:** Warum steht im Pattern der lange Interface-Name?
8. **Einordnen.**
   - **Denkfrage:** Was unterscheidet ein Applet von einem Tcl-Skript? Welche Auslöser und Aktionen gibt es, und wofür setzt man EEM typischerweise ein?
9. **EEM mit Tracking.** Lege eine IP-SLA-Messung zu 2.2.2.2 an (`ip sla schedule` nicht vergessen), dazu `track 1`. Ein Applet mit `event track 1 state down` schreibt eine Syslog-Meldung und speichert die Diagnoseausgabe in `flash:track-down.txt`. Nutze dafür `show ip sla statistics | redirect flash:track-down.txt`.
   - **Prüfen:** Schalte auf R2 Lo0 ab. Nach einigen Sekunden geht `track 1` auf Down, und das Applet erzeugt die Datei. Aktiviere Lo0 anschließend wieder.

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** GET liest, POST legt neu an, PUT ersetzt ganz, PATCH ändert einzelne Felder, DELETE löscht. 200 OK, 201 angelegt, 204 erfolgreich ohne Inhalt, 400 Anfrage fehlerhaft, 401 nicht angemeldet, 403 keine Berechtigung, 404 nicht gefunden, 405 Methode nicht erlaubt, 409 Konflikt (z. B. existiert schon), 415 falscher Content-Type, 500 Fehler im Server.
- **Zu 3:** `<edit-config>` ändert einen Datastore, `<commit>` übernimmt den Candidate in running, `<lock>` sperrt einen Datastore gegen gleichzeitige Änderungen. Datastores: running (aktiv), candidate (Entwurf), startup (beim Start geladen).
- **Zu 4:** `ietf-interfaces` ist ein herstellerneutrales Standardmodell mit wenigen Feldern. `Cisco-IOS-XE-native` bildet die ganze IOS-XE-Konfiguration ab, gilt aber nur für Cisco. OpenConfig ist ein herstellerübergreifendes Modell der Netzbetreiber.
- **Zu 7:** Das Pattern ist ein regulärer Ausdruck gegen den Text der Syslog-Meldung. Dort steht `GigabitEthernet2`, die Kurzform `Gi2` kommt nicht vor.
- **Zu 8:** Ein Applet besteht aus wenigen Zeilen in der Konfiguration. Ein Tcl-Skript liegt als Datei vor und kann Schleifen und Logik. Auslöser sind z. B. syslog, timer, cli, snmp, track und interface. Aktionen sind z. B. cli, syslog, mail und set. Typische Einsätze: Selbstheilung, automatische Sicherung bei Änderungen, Daten sammeln, sobald ein Fehler auftritt.

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml` und prüfe den SSH-Schlüssel wie oben. Reproduziere den HTTPS-Verbindungsfehler aus Ticket 3 vor dem Authentisierungsfehler aus Ticket 1. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** RESTCONF-Aufrufe liefern `401 Unauthorized`, obwohl Benutzer und Passwort stimmen.

**Ticket 2:** Die NETCONF-Verbindung auf Port 830 wird abgelehnt (`Connection refused`).

**Ticket 3:** Der RESTCONF-Aufruf hängt oder bricht mit Connection refused ab, SSH funktioniert.

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
| NETCONF-GET-CONFIG | `rpc-reply` mit Interface-Konfiguration |
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
