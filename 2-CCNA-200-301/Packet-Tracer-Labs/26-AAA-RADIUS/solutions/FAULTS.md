# Fehlerliste – Lab 26 – AAA: Authentisierung mit RADIUS und lokalem Fallback

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Anmeldung als `admin` scheitert; RADIUS meldet keine gültige Antwort, der Router fällt auf `local` zurück und lehnt `admin` ab.
- **So findest du es:** `debug aaa authentication` zeigt Fehler bei der Antwort des Servers. `show running-config | include radius` zeigt den Key `RadKey2O26` mit einem O statt einer Null.
- **Ursache:** Der Shared Secret des Routers (`RadKey2O26`) passt nicht zum Server (`RadKey2026`).
- **Fix:** Gleiches Secret auf Router und Server.
- **Eingebaut:**

```diff
- radius-server host 10.26.1.100 key RadKey2026
+ radius-server host 10.26.1.100 key RadKey2O26
```

## Ticket 2 (R1)

- **Symptom:** Bei ausgeschaltetem RADIUS-Server kommt niemand mehr per Telnet auf den Router, auch `backup` nicht.
- **So findest du es:** `show running-config | section aaa` zeigt `group radius` ohne `local` am Ende.
- **Ursache:** Die Method-List hat keinen lokalen Fallback: Fällt der Server aus, gibt es keinen Zugang.
- **Fix:** `group radius local` mit lokalem Notfall-Benutzer.
- **Eingebaut:**

```diff
- aaa authentication login VTY-AUTH group radius local
+ aaa authentication login VTY-AUTH group radius
```

## Ticket 3 (R1)

- **Symptom:** Beim Telnet-Login erscheint eine Fehlermeldung zur Method-List bzw. es wird kein Passwort akzeptiert.
- **So findest du es:** `show running-config | section line vty` verweist auf `VTY`, definiert ist aber nur `VTY-AUTH`.
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
- **So findest du es:** `show ip interface brief` und `show running-config interface gi0/0` zeigen die Maske 255.255.255.192. Rechne nach: Liegt 10.26.1.100 noch im Netz von R1?
- **Ursache:** Falsche Maske /26 am Router: Das Netz von R1 reicht nur von 10.26.1.0 bis .63. Der Server (.100) liegt aus Sicht von R1 außerhalb.
- **Fix:** Maske 255.255.255.0.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip address 10.26.1.1 255.255.255.0
+ interface GigabitEthernet0/0
+  ip address 10.26.1.1 255.255.255.192
```

