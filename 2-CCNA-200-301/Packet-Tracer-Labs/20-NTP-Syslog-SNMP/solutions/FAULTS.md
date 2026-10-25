# Fehlerliste – Lab 20 – NTP, Syslog und SNMP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** `show ntp status` auf R2 meldet `Clock is unsynchronized`.
- **So findest du es:** `show ntp associations` auf R2 zeigt 10.20.1.11 mit Reach 0. Den Server gibt es nicht.
- **Ursache:** R2 fragt einen nicht existierenden NTP-Server (10.20.1.11) ab.
- **Fix:** `ntp server 10.20.1.1`.
- **Eingebaut:**

```diff
- ntp server 10.20.1.1
+ ntp server 10.20.1.11
```

## Ticket 2 (R2)

- **Symptom:** Meldungen von R1 erscheinen im Syslog-Server, solche von R2 nicht.
- **So findest du es:** `show logging` auf R2 zeigt bei „Logging to“ eine andere Adresse als 10.20.1.100.
- **Ursache:** Falsche Syslog-Zieladresse auf R2.
- **Fix:** `logging host 10.20.1.100`.
- **Eingebaut:**

```diff
- logging host 10.20.1.100
+ logging host 10.20.1.101
```

## Ticket 3 (R1)

- **Symptom:** Auf dem Syslog-Server fehlen von R1 die Meldungen `%LINEPROTO-5-UPDOWN` und `%SYS-5-CONFIG_I`. `%LINK-3-UPDOWN` kommt an.
- **So findest du es:** `show logging` auf R1 zeigt „Trap logging: level errors“.
- **Ursache:** Der Trap-Level ist `errors` (3). R1 schickt nur Meldungen mit Level 0 bis 3, Notifications (5) und Informational (6) bleiben im lokalen Log.
- **Fix:** `logging trap informational`.
- **Eingebaut:**

```diff
- logging trap informational
+ logging trap errors
```

## Ticket 4 (R2)

- **Symptom:** Der MIB-Browser erhält von R2 keine Antwort (Timeout), von R1 schon.
- **So findest du es:** `show snmp community` auf R2 zeigt `Labro`. Communitys unterscheiden Groß- und Kleinschreibung.
- **Ursache:** Die Community unterscheidet sich in der Groß-/Kleinschreibung (`Labro` statt `LabRO`).
- **Fix:** `snmp-server community LabRO RO`.
- **Eingebaut:**

```diff
- snmp-server community LabRO RO
+ snmp-server community Labro RO
```

