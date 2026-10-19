# Fehlerliste – Lab 11 – Gerätezugriff und AAA

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Solange TACACS+ nicht erreichbar ist (das ist hier immer der Fall), kann sich niemand per Telnet anmelden, auch `admin` nicht.
- **Ursache:** Die Methodenliste hat kein Fallback `local`: bei Server-Timeout gibt es keine weitere Methode.
- **Fix:** `local` als letzte Methode ergänzen (Aussperr-Schutz).
- **Eingebaut:**

```diff
- aaa authentication login VTY_LIST group TACGRP local
+ aaa authentication login VTY_LIST group TACGRP
```

## Ticket 2 (R1)

- **Symptom:** Login per Telnet klappt, aber `admin` landet in `R1>` statt `R1#`.
- **Ursache:** Ohne Exec-Autorisierung gilt das Default-Privileg der Line (1), das Privileg des Benutzers wird nicht übernommen.
- **Fix:** `aaa authorization exec VTY_LIST group TACGRP local` setzen und auf der Line mit `authorization exec VTY_LIST` verknüpfen.
- **Eingebaut:**

```diff
- aaa authorization exec VTY_LIST group TACGRP local
```

## Ticket 3 (R1)

- **Symptom:** Telnet-Anmeldung schlägt für alle Benutzer fehl, im Log steht `no method list`.
- **Ursache:** Die Line referenziert eine nicht existierende Methodenliste (`VTY-LIST` statt `VTY_LIST`).
- **Fix:** Namen der Methodenliste angleichen.
- **Eingebaut:**

```diff
- login authentication VTY_LIST
+ login authentication VTY-LIST
```

## Ticket 4 (R1)

- **Symptom:** Audit-Befund: untätige vty-Sitzungen laufen nie ab.
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

