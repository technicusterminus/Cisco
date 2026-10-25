# Fehlerliste – Lab 17 – First Hop Redundancy: HSRP mit Preempt und Tracking

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** Im Log steht `%HSRP-4-DIFFVIP1`. Solange R1 Active ist, läuft alles. Fällt R1 aus, wird R2 Active, aber die PCs verlieren trotzdem ihr Gateway.
- **So findest du es:** `show standby brief` auf R1 und R2 vergleichen: Die Spalte „Virtual IP“ zeigt .1 und .11.
- **Ursache:** R2 verwendet eine andere virtuelle IP (10.17.1.11). Die Wahl von Active und Standby läuft trotzdem normal nach Priorität. Wird R2 Active, übernimmt er aber nur .11, und das Gateway 10.17.1.1 der PCs antwortet nicht mehr.
- **Fix:** Virtuelle IP 10.17.1.1 auf R2.
- **Eingebaut:**

```diff
-  standby 1 ip 10.17.1.1
+  standby 1 ip 10.17.1.11
```

## Ticket 2 (R1)

- **Symptom:** Nach der Rückkehr von R1 bleibt R2 Active; R1 bleibt Standby, obwohl er höhere Priorität hat.
- **So findest du es:** `show standby` auf R1 enthält keine Zeile „Preemption enabled“.
- **Ursache:** Auf R1 fehlt `preempt`.
- **Fix:** `standby 1 preempt`.
- **Eingebaut:**

```diff
-  standby 1 preempt
```

## Ticket 3 (R1)

- **Symptom:** Beim Ausfall von R1 Gi0/1 bleibt R1 Active und der Internet-Verkehr der PCs läuft ins Leere.
- **So findest du es:** `show standby` auf R1 nach Abschalten von Gi0/1: Die Priorität sinkt nur auf 105.
- **Ursache:** Der Tracking-Abzug (5) reicht nicht: 110 − 5 = 105 liegt weiterhin über R2 (100).
- **Fix:** Abzug mindestens 11, z. B. 20.
- **Eingebaut:**

```diff
-  standby 1 track GigabitEthernet0/1 20
+  standby 1 track GigabitEthernet0/1 5
```

## Ticket 4 (PC2)

- **Symptom:** PC2 verliert die Verbindung ins Internet, sobald R1 ausfällt, PC1 nicht.
- **So findest du es:** `ipconfig` auf PC2 zeigt das Gateway 10.17.1.2, das ist die echte Adresse von R1.
- **Ursache:** PC2 nutzt die reale Router-IP (10.17.1.2) statt der virtuellen Gateway-IP.
- **Fix:** Gateway 10.17.1.1.
- **Eingebaut:** Endgerät-Einstellung `gw` = `10.17.1.2`

