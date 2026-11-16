# Fehlerliste – Lab 35 – IP SLA vertieft: Tracking mit Floating Static, UDP-Jitter mit Responder, TCP-Connect

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Der gesamte Verkehr von H1 läuft über ISP2, obwohl ISP1 in Ordnung ist. `show track 1` auf R1 steht auf `Down`.
- **So findest du es:** `show ip sla summary` zeigt Messung 1 im Zustand `Pending`. `show ip sla statistics 1` hat keine Startzeit und keine Zähler. Mit `show ip sla configuration 1` siehst du: kein Zeitplan.
- **Ursache:** Die Messung ist angelegt, aber nie gestartet. Ein Track-Objekt auf eine nicht laufende Messung ist Down, die Route mit `track 1` fehlt in der Tabelle.
- **Fix:** `ip sla schedule 1 life forever start-time now`.
- **Eingebaut:**

```diff
-ip sla schedule 1 life forever start-time now
```

## Ticket 2 (R1)

- **Symptom:** Sobald Ticket 1 gelöst ist: `show ip route 0.0.0.0` auf R1 zeigt zwei Next-Hops. Ein Teil der Verbindungen läuft weiter über ISP2.
- **So findest du es:** `show ip route 0.0.0.0` zeigt beide Next-Hops mit Distanz 1. `show running-config | include ip route 0.0.0.0`: Der zweiten Route fehlt die Distanz.
- **Ursache:** Ohne höhere administrative Distanz ist die Ersatzroute gleichwertig. Der Router verteilt die Last auf beide Provider, statt ISP2 nur im Notfall zu nutzen.
- **Fix:** `no ip route 0.0.0.0 0.0.0.0 10.0.13.2`, dann `ip route 0.0.0.0 0.0.0.0 10.0.13.2 10`.
- **Eingebaut:**

```diff
-ip route 0.0.0.0 0.0.0.0 10.0.13.2 10
+ip route 0.0.0.0 0.0.0.0 10.0.13.2
```

## Ticket 3 (R4)

- **Symptom:** Die Jitter-Messung (IP SLA 2) liefert seit dem letzten Wartungsfenster nur `No connection`.
- **So findest du es:** `show ip sla responder` auf R4: Responder nicht aktiv. Auf R1 zeigt `show ip sla statistics 2` den Return Code `No connection`, während die ICMP-Messung 1 auf dasselbe Ziel funktioniert.
- **Ursache:** `udp-jitter` braucht auf der Gegenseite den Responder. Er fehlt in der Konfiguration von R4.
- **Fix:** `ip sla responder` auf R4.
- **Eingebaut:**

```diff
-ip sla responder
```

## Ticket 4 (R1)

- **Symptom:** Sobald Ticket 3 gelöst ist: `show track 2` bleibt `Down`, obwohl die Jitter-Messung Werte liefert.
- **So findest du es:** `show ip sla statistics 2`: Return Code `Over threshold`. `show ip sla configuration 2` nennt als Schwelle 1 ms. `show track 2` überwacht `state`, nicht `reachability`.
- **Ursache:** Die Schwelle von 1 ms unterschreitet kein realer Weg. Jede Messung gilt als zu langsam, und `track … state` wertet das als Ausfall.
- **Fix:** Messung 2 stoppen, `threshold 500` setzen, neu starten. (Oder bewusst auf `track 2 ip sla 2 reachability` wechseln.)
- **Eingebaut:**

```diff
- threshold 500
+ threshold 1
```
