# Fehlerliste – Lab 15 – LISP: Map-Server, Map-Resolver, xTR

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (xTR2)

- **Symptom:** SITE2 wird auf dem MSMR nie als registriert angezeigt, H1 erreicht H2 nicht (Map-Reply negativ).
- **So findest du es:** `show lisp site` auf dem MSMR zeigt SITE2 als nicht registriert. `debug lisp control-plane map-server-registration` meldet einen Authentisierungsfehler.
- **Ursache:** Der Authentifizierungs-Schlüssel auf xTR2 passt nicht zum Site-Key auf dem MSMR: Map-Register wird abgelehnt.
- **Fix:** Key auf xTR2 anpassen.
- **Eingebaut:**

```diff
- key LispKey123
+ key LispFalsch
```

## Ticket 2 (xTR1)

- **Symptom:** xTR1 registriert sein EID-Netz nicht beim MSMR (SITE1 `no`), Rückverkehr von H2 funktioniert nicht.
- **So findest du es:** `show lisp site` zeigt SITE1 mit „no“. `show ip lisp` auf xTR1 meldet die ETR-Funktion als deaktiviert.
- **Ursache:** `ipv4 etr` fehlt: Der Router übernimmt keine ETR-Funktion, sendet keine Map-Register und entkapselt nicht.
- **Fix:** `ipv4 etr` aktivieren.
- **Eingebaut:**

```diff
-   ipv4 etr
```

## Ticket 3 (xTR2)

- **Symptom:** Der MSMR zeigt SITE2 nicht registriert, im Log `EID-prefix not configured`.
- **So findest du es:** Das Log auf dem MSMR meldet „EID-prefix not configured“. `show running-config | section router lisp` auf xTR2 zeigt ein anderes Präfix im `database-mapping`.
- **Ursache:** xTR2 registriert ein anderes EID-Präfix (192.168.22.0/24) als im MSMR-Site erlaubt.
- **Fix:** `database-mapping` auf 192.168.2.0/24 korrigieren.
- **Eingebaut:**

```diff
- database-mapping 192.168.2.0/24 locator-set RLOC
+ database-mapping 192.168.22.0/24 locator-set RLOC
```

## Ticket 4 (xTR1)

- **Symptom:** H1 erreicht H2 nie, `show ip lisp map-cache` ist leer (keine Map-Requests).
- **So findest du es:** `show ip lisp map-cache` auf xTR1 ist leer. `show ip lisp` zeigt keinen Map-Resolver.
- **Ursache:** Ohne `ipv4 itr map-resolver` weiß der ITR nicht, wen er für Mappings fragen soll.
- **Fix:** Map-Resolver 10.0.99.1 eintragen.
- **Eingebaut:**

```diff
-   ipv4 itr map-resolver 10.0.99.1
```

