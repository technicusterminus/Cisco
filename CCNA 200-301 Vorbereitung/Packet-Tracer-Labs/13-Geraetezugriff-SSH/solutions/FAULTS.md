# Fehlerliste – Lab 13 – Gerätezugriff: lokale Passwörter, Passwortrichtlinie und SSH

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** `ssh -l admin 10.13.1.1` wird abgelehnt (`Connection refused`), Telnet geht stattdessen.
- **Ursache:** Die vty-Lines erlauben nur Telnet.
- **Fix:** `transport input ssh` auf den vty-Lines.
- **Eingebaut:**

```diff
-  transport input ssh
+  transport input telnet
```

## Ticket 2 (R1)

- **Symptom:** Die Schlüsselerzeugung scheitert (`Please define a domain-name first`), `show ip ssh` meldet SSH disabled; SSH ist nicht möglich.
- **Ursache:** Ohne `ip domain-name` kann kein RSA-Schlüssel erzeugt werden, damit startet SSH nicht.
- **Fix:** `ip domain-name lab.local`, dann `crypto key generate rsa modulus 2048`.
- **Eingebaut:**

```diff
- ip domain-name lab.local
```

## Ticket 3 (R1)

- **Symptom:** SSH baut die Verbindung auf, aber die Anmeldung wird immer abgelehnt (`Access denied`).
- **Ursache:** `login local` verlangt einen lokalen Benutzer; es existiert keiner.
- **Fix:** `username admin privilege 15 secret …` anlegen.
- **Eingebaut:**

```diff
- username admin privilege 15 secret Lab#2026!
```

## Ticket 4 (R1)

- **Symptom:** Telnet/SSH zeigen `Password required, but none set` und trennen die Verbindung.
- **Ursache:** `login` ohne `password` auf den vty-Lines (kein Passwort gesetzt).
- **Fix:** `login local` (mit lokalem Benutzer) oder `password` setzen.
- **Eingebaut:**

```diff
- line vty 0 4
-  login local
+ line vty 0 4
+  login
```

