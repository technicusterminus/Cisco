# Fehlerliste – Lab 20 – NTP, Syslog und SNMP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** `show ntp status` auf R2 meldet `Clock is unsynchronized`.
- **Ursache:** R2 fragt einen nicht existierenden NTP-Server (10.20.1.11) ab.
- **Fix:** `ntp server 10.20.1.1`.
- **Eingebaut:**

```diff
- ntp server 10.20.1.1
+ ntp server 10.20.1.11
```

## Ticket 2 (R2)

- **Symptom:** Meldungen von R1 erscheinen im Syslog-Server, solche von R2 nicht.
- **Ursache:** Falsche Syslog-Zieladresse auf R2.
- **Fix:** `logging host 10.20.1.100`.
- **Eingebaut:**

```diff
- logging host 10.20.1.100
+ logging host 10.20.1.101
```

## Ticket 3 (R1)

- **Symptom:** Auf dem Syslog-Server fehlen die Link-Up/Down-Meldungen (Level 5/6) von R1; nur Fehler ab Level 3 kommen an.
- **Ursache:** Der Trap-Level ist `errors` (3): Notice/Informational werden nicht gesendet.
- **Fix:** `logging trap informational`.
- **Eingebaut:**

```diff
- logging trap informational
+ logging trap errors
```

## Ticket 4 (R2)

- **Symptom:** Der MIB-Browser erhält von R2 keine Antwort (Timeout), von R1 schon.
- **Ursache:** Die Community unterscheidet sich in der Gross-/Kleinschreibung (`Labro` statt `LabRO`).
- **Fix:** `snmp-server community LabRO RO`.
- **Eingebaut:**

```diff
- snmp-server community LabRO RO
+ snmp-server community Labro RO
```

