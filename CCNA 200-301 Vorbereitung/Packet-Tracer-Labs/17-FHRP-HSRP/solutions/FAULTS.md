# Fehlerliste – Lab 17 – First Hop Redundancy: HSRP mit Preempt und Tracking

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** `show standby brief` zeigt auf beiden Routern `Active`, unterschiedliche virtuelle IPs (…1 und …11); `%HSRP-4-DIFFVIP1` im Log.
- **Ursache:** R2 verwendet eine andere virtuelle IP (10.17.1.11).
- **Fix:** Virtuelle IP 10.17.1.1 auf R2.
- **Eingebaut:**

```diff
-  standby 1 ip 10.17.1.1
+  standby 1 ip 10.17.1.11
```

## Ticket 2 (R1)

- **Symptom:** Nach der Rückkehr von R1 bleibt R2 Active; R1 bleibt Standby, obwohl er höhere Priorität hat.
- **Ursache:** Auf R1 fehlt `preempt`.
- **Fix:** `standby 1 preempt`.
- **Eingebaut:**

```diff
-  standby 1 preempt
```

## Ticket 3 (R1)

- **Symptom:** Beim Ausfall von R1 Gi0/1 bleibt R1 Active und der Internet-Verkehr der PCs läuft ins Leere.
- **Ursache:** Der Tracking-Abzug (5) reicht nicht: 110 − 5 = 105 liegt weiterhin über R2 (100).
- **Fix:** Abzug mindestens 11, z. B. 20.
- **Eingebaut:**

```diff
-  standby 1 track GigabitEthernet0/1 20
+  standby 1 track GigabitEthernet0/1 5
```

## Ticket 4 (PC2)

- **Symptom:** PC2 verliert die Verbindung ins Internet, sobald R1 ausfällt, PC1 nicht.
- **Ursache:** PC2 nutzt die reale Router-IP (10.17.1.2) statt der virtuellen Gateway-IP.
- **Fix:** Gateway 10.17.1.1.
- **Eingebaut:** Endgerät-Einstellung `gw` = `10.17.1.2`

