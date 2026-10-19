# Fehlerliste – Lab 26 – AAA: Authentisierung mit RADIUS und lokalem Fallback

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Anmeldung als `admin` scheitert; RADIUS meldet keine gültige Antwort, der Router fällt auf `local` zurück und lehnt `admin` ab.
- **Ursache:** Der Shared Secret des Routers (`RadKey2O26`) passt nicht zum Server (`RadKey2026`).
- **Fix:** Gleiches Secret auf Router und Server.
- **Eingebaut:**

```diff
- radius-server host 10.26.1.100 key RadKey2026
+ radius-server host 10.26.1.100 key RadKey2O26
```

## Ticket 2 (R1)

- **Symptom:** Bei ausgeschaltetem RADIUS-Server kommt niemand mehr per Telnet auf den Router, auch `backup` nicht.
- **Ursache:** Die Method-List hat keinen lokalen Fallback: Fällt der Server aus, gibt es keinen Zugang.
- **Fix:** `group radius local` mit lokalem Notfall-Benutzer.
- **Eingebaut:**

```diff
- aaa authentication login VTY-AUTH group radius local
+ aaa authentication login VTY-AUTH group radius
```

## Ticket 3 (R1)

- **Symptom:** Beim Telnet-Login erscheint eine Fehlermeldung zur Method-List bzw. es wird kein Passwort akzeptiert.
- **Ursache:** Die vty-Lines verweisen auf eine nicht definierte Method-List (`VTY` statt `VTY-AUTH`).
- **Fix:** `login authentication VTY-AUTH`.
- **Eingebaut:**

```diff
-  login authentication VTY-AUTH
-  transport input telnet
+  login authentication VTY
+  transport input telnet
```

## Ticket 4 (R1)

- **Symptom:** RADIUS-Anfragen erreichen den Server nicht (Timeout), Login nur per Fallback; Ping zum Server (10.26.1.100) schlägt fehl.
- **Ursache:** Falsche Maske /25 am Router: Der Server (…100) liegt aus Sicht von R1 ausserhalb des Subnetzes.
- **Fix:** Maske 255.255.255.0.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip address 10.26.1.1 255.255.255.0
+ interface GigabitEthernet0/0
+  ip address 10.26.1.1 255.255.255.128
```

