# Fehlerliste – Lab 27 – Redistribution zwischen OSPF und EIGRP mit Tags und Filtern

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** R4 lernt über R2 keine OSPF-Routen; `show ip route` auf R4 zeigt 10.1.0.0/24 nur (falls überhaupt) über R3.
- **So findest du es:** `show ip route` auf R4 zeigt die OSPF-Netze nicht über R2. `show ip eigrp topology` auf R2 meldet sie mit unendlicher Metrik, weil kein `metric` beim `redistribute` steht.
- **Ursache:** Beim Einspeisen in EIGRP fehlt die Seed-Metrik: Die Routen haben eine unendliche Metrik und werden nicht übernommen.
- **Fix:** Metrik angeben (`metric 10000 100 255 1 1500`) oder `default-metric` setzen.
- **Eingebaut:**

```diff
-  redistribute ospf 1 metric 10000 100 255 1 1500 route-map O2E
+  redistribute ospf 1 route-map O2E
```

## Ticket 2 (R3)

- **Symptom:** Über R3 erscheinen keine EIGRP-Netze in OSPF; R1 sieht 10.4.0.0/24 nur über R2 mit Metrik 20.
- **So findest du es:** `show ip ospf database external` auf R1 enthält keine Netze von R3. In der Konfiguration von R3 fehlt `subnets`.
- **Ursache:** Ohne `subnets` redistribuiert OSPF nur klassische Netze, die /24-Subnetze werden verworfen.
- **Fix:** `subnets` ergänzen.
- **Eingebaut:**

```diff
-  redistribute eigrp 100 subnets route-map E2O
+  redistribute eigrp 100 route-map E2O
```

## Ticket 3 (R3)

- **Symptom:** Auf R4 und R3 pendelt 10.1.0.0/24 zwischen den Domänen, R1 sieht die eigene Route als `O E2` mit Tag 2 zurück (Rückkopplung).
- **So findest du es:** `show ip route 10.1.0.0` auf R1 zeigt eine externe Route mit Tag 2. Die Route-Map E2O auf R3 enthält keine Zeile `match tag 1`.
- **Ursache:** Der Filter erkennt den Tag 1 nicht: Aus OSPF stammende, in EIGRP gesehene Routen werden von R3 erneut nach OSPF gegeben.
- **Fix:** `match tag 1` in `E2O` auf R3.
- **Eingebaut:**

```diff
- route-map E2O deny 10
-  match tag 1
+ route-map E2O deny 10
+  match tag 9
```

## Ticket 4 (R2)

- **Symptom:** R1 lernt 10.4.1.0/24, obwohl das Netz lokal bleiben sollte.
- **So findest du es:** `show ip route 10.4.1.0` auf R1 zeigt die Route. `show ip prefix-list` auf R2 nennt ein anderes Netz.
- **Ursache:** Die Prefix-Liste enthält das falsche Netz (10.4.2.0/24); 10.4.1.0/24 wird nicht gefiltert.
- **Fix:** Prefix auf 10.4.1.0/24 korrigieren.
- **Eingebaut:**

```diff
- ip prefix-list LOCAL-ONLY seq 5 permit 10.4.1.0/24
+ ip prefix-list LOCAL-ONLY seq 5 permit 10.4.2.0/24
```

## Ticket 5 (R4)

- **Symptom:** R3 und R4 haben keine EIGRP-Nachbarschaft; R4 erreicht OSPF-Netze nur über R2.
- **So findest du es:** `show ip eigrp neighbors` auf R4 listet R3 nicht. `show ip eigrp interfaces` auf R4 zeigt den Link zu R3 nicht.
- **Ursache:** Der Link R3–R4 ist auf R4 nicht im EIGRP-Prozess (`network` fehlt).
- **Fix:** `network 10.0.34.0 0.0.0.3` auf R4.
- **Eingebaut:**

```diff
-  network 10.0.34.0 0.0.0.3
```

## Ticket 6 (R3)

- **Symptom:** R1 und R3 bilden keine OSPF-Nachbarschaft; im Log `Mismatched Area ID`/hängt in `INIT`.
- **So findest du es:** Das Log meldet „Mismatched Area ID“. `show ip ospf interface brief` auf R1 und R3 zeigt für den Link verschiedene Areas.
- **Ursache:** Der Link liegt auf R3 in Area 1, auf R1 in Area 0.
- **Fix:** Area 0 auf R3.
- **Eingebaut:**

```diff
-  network 10.0.13.0 0.0.0.3 area 0
+  network 10.0.13.0 0.0.0.3 area 1
```

