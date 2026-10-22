# Fehlerliste – Lab C6 – EIGRP Named Mode: SHA-256, Unequal-Cost Load Balancing und Stub mit Leak-Map

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** R2 hat keine EIGRP-Nachbarn. Im Log steht bei jedem Versuch `K-value mismatch`.
- **So findest du es:** Im Log von R2 und seinen Nachbarn: `K-value mismatch`. `show eigrp protocols` auf R2 nennt K2 = 1, die Nachbarn haben K2 = 0. In der Konfiguration von R2 steht `metric weights 0 1 1 1 0 0 0`.
- **Ursache:** Unterschiedliche K-Werte. EIGRP-Nachbarn müssen dieselben K-Werte haben, sonst lehnen sie die Nachbarschaft ab.
- **Fix:** `no metric weights` (oder `metric weights 0 1 0 1 0 0 0`) unter der Address-Family auf R2.
- **Eingebaut:**

```diff
+  metric weights 0 1 1 1 0 0 0
```

## Ticket 2 (R3)

- **Symptom:** R3 hat keine EIGRP-Nachbarn. Die Links sind up, Pings zu R1 und R4 klappen.
- **So findest du es:** `show eigrp address-family ipv4 neighbors` auf R3 ist leer. `debug eigrp packets` auf R1 zeigt Pakete von 10.0.13.2, die an der Authentisierung scheitern. Der Schlüssel auf R3 lautet `EIGRP-lab` statt `EIGRP-Lab`.
- **Ursache:** Falsches Passwort für HMAC-SHA-256. Groß- und Kleinschreibung zählt, der Hash passt nicht.
- **Fix:** `authentication mode hmac-sha-256 EIGRP-Lab` unter `af-interface default` auf R3.
- **Eingebaut:**

```diff
-   authentication mode hmac-sha-256 EIGRP-Lab
+   authentication mode hmac-sha-256 EIGRP-lab
```

## Ticket 3 (R4)

- **Symptom:** Das Netz 10.4.2.0/24 fehlt auf allen anderen Routern, 10.4.1.0/24 ist da.
- **So findest du es:** `show eigrp address-family ipv4 interfaces` auf R4 listet Loopback1, aber nicht Loopback2. Die Wildcard 0.0.1.255 deckt nur 10.4.0.0 bis 10.4.1.255 ab.
- **Ursache:** Zu enge Wildcard im `network`-Befehl. 10.4.2.1 liegt außerhalb, Loopback2 nimmt nicht an EIGRP teil.
- **Fix:** `no network 10.4.0.0 0.0.1.255` und `network 10.4.0.0 0.0.3.255` auf R4.
- **Eingebaut:**

```diff
-  network 10.4.0.0 0.0.3.255
+  network 10.4.0.0 0.0.1.255
```

## Ticket 4 (R1)

- **Symptom:** R1 schickt Verkehr zu 10.4.1.0/24 nur über R2, obwohl der Weg über R3 als Feasible Successor bereitsteht.
- **So findest du es:** `show ip eigrp topology 10.4.1.0/24` auf R1 zeigt Successor und Feasible Successor, `show ip route 10.4.1.0` nur einen Weg. Unter `topology base` fehlt `variance 2`.
- **Ursache:** Ohne Varianz nutzt EIGRP nur Wege mit der besten Metrik. Der Feasible Successor bleibt Reserve.
- **Fix:** `variance 2` unter `topology base` auf R1.
- **Eingebaut:**

```diff
-   variance 2
```

## Ticket 5 (R4)

- **Symptom:** Ausfalltest: Nach `shutdown` auf R1 Gi0/0 verliert R2 seine Default-Route und erreicht 192.0.2.1 nicht mehr, obwohl R4 über R3 weiter angebunden ist.
- **So findest du es:** Während des Tests: `show ip route 0.0.0.0` auf R2 ist leer. `show ip protocols` auf R4 nennt den Stub ohne Leak-Map. R4 kennt die Default-Route von R3, gibt sie als Stub aber nicht weiter.
- **Ursache:** Ein Stub gibt nur seine eigenen Netze weiter. Ohne Leak-Map ist R2 nach dem Ausfall seines Links zu R1 auf die Netze von R4 beschränkt.
- **Fix:** `eigrp stub connected leak-map LEAK-DEFAULT` auf R4.
- **Eingebaut:**

```diff
-  eigrp stub connected leak-map LEAK-DEFAULT
+  eigrp stub connected
```
