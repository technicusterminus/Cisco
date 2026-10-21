# Fehlerliste – Lab 19 – RESTCONF, NETCONF, YANG und EEM

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (CSR1)

- **Symptom:** RESTCONF-Aufrufe liefern `401 Unauthorized`, obwohl Benutzer und Passwort stimmen.
- **So findest du es:** Die API antwortet mit 401. `show running-config | include ip http` zeigt keine Zeile `ip http authentication local`.
- **Ursache:** Ohne `ip http authentication local` prüft der HTTP-Server nicht gegen lokale Benutzer.
- **Fix:** `ip http authentication local` setzen.
- **Eingebaut:**

```diff
- ip http authentication local
```

## Ticket 2 (CSR1)

- **Symptom:** Die NETCONF-Verbindung auf Port 830 wird abgelehnt (`Connection refused`).
- **So findest du es:** Die Verbindung auf Port 830 wird abgelehnt. `show netconf-yang status` meldet NETCONF als deaktiviert, oder `netconf-yang` fehlt in der Konfiguration.
- **Ursache:** NETCONF-YANG ist nicht aktiviert, der SSH-Subsystem-Listener auf 830 fehlt.
- **Fix:** `netconf-yang` aktivieren.
- **Eingebaut:**

```diff
- netconf-yang
```

## Ticket 3 (CSR1)

- **Symptom:** `curl https://…/restconf/` hängt oder bricht mit Connection refused ab, SSH funktioniert.
- **So findest du es:** `curl` bekommt keine Verbindung. `show ip http server secure status` meldet den HTTPS-Server als deaktiviert.
- **Ursache:** HTTPS-Server ist ausgeschaltet; RESTCONF braucht `ip http secure-server`.
- **Fix:** `ip http secure-server` aktivieren.
- **Eingebaut:**

```diff
- ip http secure-server
```

## Ticket 4 (CSR1)

- **Symptom:** Beim Link-Flap auf Gi2 erscheint die EEM-Syslog-Zeile nie, `show event manager policy registered` zeigt das Applet.
- **So findest du es:** `show event manager history events` zeigt kein ausgelöstes Ereignis. Vergleiche das Pattern mit dem echten Text in `show logging`.
- **Ursache:** Das Pattern nutzt die Kurzform `Gi2`, der Syslog-Text enthält `GigabitEthernet2`.
- **Fix:** Pattern auf den vollständigen Interface-Namen anpassen.
- **Eingebaut:**

```diff
- event syslog pattern "Interface GigabitEthernet2, changed state"
+ event syslog pattern "Interface Gi2, changed state"
```

## Ticket 5 (R2)

- **Symptom:** `show track 1` auf CSR1 ist Down (IP SLA 2.2.2.2 schlägt fehl), R2 antwortet nicht.
- **So findest du es:** `show ip sla statistics` auf CSR1 meldet Timeouts. `show ip route 0.0.0.0` auf R2 zeigt einen Next-Hop, den es nicht gibt.
- **Ursache:** R2 hat die Rückroute zu CSR1 verfehlt: Default-Route zeigt auf eine falsche Adresse, Echo-Reply kann nicht zurück.
- **Fix:** Default-Route auf 10.0.12.1 korrigieren.
- **Eingebaut:**

```diff
- ip route 0.0.0.0 0.0.0.0 10.0.12.1
+ ip route 0.0.0.0 0.0.0.0 10.0.12.11
```

