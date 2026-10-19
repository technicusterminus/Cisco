# Fehlerliste – Lab 07 – First-Hop-Redundanz: HSRP, VRRP und GLBP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** Auf VLAN 10 melden beide Router `Active`, im Log steht `%HSRP-4-DIFFVIP1`.
- **Ursache:** Die virtuelle IP auf R2 (10.10.10.10) weicht von R1 (10.10.10.1) ab; beide glauben, einzige Active zu sein.
- **Fix:** VIP auf R2 an R1 angleichen.
- **Eingebaut:**

```diff
- standby 10 ip 10.10.10.1
+ standby 10 ip 10.10.10.10
```

## Ticket 2 (R1)

- **Symptom:** Nach Abschalten von R1 Gi0/2 bleibt R1 HSRP Active, der Verkehr von VLAN 10 geht ins Leere.
- **Ursache:** Decrement 5 senkt die Priorität nur auf 105, R2 hat 100: kein Wechsel.
- **Fix:** Decrement größer als die Differenz (z. B. 20).
- **Eingebaut:**

```diff
-  standby 10 track 1 decrement 20
+  standby 10 track 1 decrement 5
```

## Ticket 3 (R2)

- **Symptom:** VLAN 20 zeigt auf beiden Routern `Master`, Hosts erhalten unregelmäßig Pings.
- **Ursache:** VRRP-Gruppennummer 21 auf R2 statt 20: Die Router bilden getrennte Gruppen mit derselben VIP.
- **Fix:** Gruppen-ID auf 20 korrigieren (und `priority 110` ebenfalls unter Gruppe 20).
- **Eingebaut:**

```diff
-  vrrp 20 ip 10.10.20.1
+  vrrp 21 ip 10.10.20.1
```

## Ticket 4 (R1)

- **Symptom:** Nach dem Wiederanschalten von R1 Gi0/2 bleibt R2 Active, obwohl R1 höhere Priorität hat.
- **Ursache:** Ohne `preempt` übernimmt der Router mit höherer Priorität die Active-Rolle nicht zurück.
- **Fix:** `standby 10 preempt` ergänzen.
- **Eingebaut:**

```diff
-  standby 10 preempt
```

