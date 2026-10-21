# Fehlerliste – Lab 11 – Gerätezugriff und AAA

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Solange TACACS+ nicht erreichbar ist (das ist hier immer der Fall), kann sich niemand per Telnet anmelden, auch `admin` nicht.
- **So findest du es:** `show running-config | include aaa authentication` zeigt die Methodenliste nur mit `group`, ohne `local` am Ende. `debug aaa authentication` meldet beim Anmelden einen Timeout ohne weitere Methode.
- **Ursache:** Die Methodenliste hat kein Fallback `local`: bei Server-Timeout gibt es keine weitere Methode.
- **Fix:** `local` als letzte Methode ergänzen (Aussperr-Schutz).
- **Eingebaut:**

```diff
- aaa authentication login VTY_LIST group TACGRP local
+ aaa authentication login VTY_LIST group TACGRP
```

## Ticket 2 (R1)

- **Symptom:** Login per Telnet klappt, aber `admin` landet in `R1>` statt `R1#`.
- **So findest du es:** `show privilege` nach dem Login zeigt Level 1. In der Konfiguration fehlt `aaa authorization exec`, oder die Line verweist nicht darauf.
- **Ursache:** Ohne Exec-Autorisierung gilt das Default-Privileg der Line (1), das Privileg des Benutzers wird nicht übernommen.
- **Fix:** `aaa authorization exec VTY_LIST group TACGRP local` setzen und auf der Line mit `authorization exec VTY_LIST` verknüpfen.
- **Eingebaut:**

```diff
- aaa authorization exec VTY_LIST group TACGRP local
```

## Ticket 3 (R1)

- **Symptom:** Telnet-Anmeldung schlägt für alle Benutzer fehl, im Log steht `no method list`.
- **So findest du es:** Das Log meldet „no method list“. Vergleiche den Namen unter `line vty` mit `show running-config | include aaa authentication login`: Bindestrich gegen Unterstrich.
- **Ursache:** Die Line referenziert eine nicht existierende Methodenliste (`VTY-LIST` statt `VTY_LIST`).
- **Fix:** Namen der Methodenliste angleichen.
- **Eingebaut:**

```diff
- login authentication VTY_LIST
+ login authentication VTY-LIST
```

## Ticket 4 (R1)

- **Symptom:** Audit-Befund: untätige vty-Sitzungen laufen nie ab.
- **So findest du es:** `show running-config | section line vty` zeigt `exec-timeout 0 0`.
- **Ursache:** `exec-timeout 0 0` deaktiviert das Idle-Timeout der vty-Lines.
- **Fix:** `exec-timeout 5 0` setzen (je nach Policy).
- **Eingebaut:**

```diff
-  transport input telnet
-  exec-timeout 5 0
- line con 0
+  transport input telnet
+  exec-timeout 0 0
+ line con 0
```

