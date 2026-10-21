# Fehlerliste – Lab 26 – iBGP mit Route Reflector, Local Preference und Communities

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R3)

- **Symptom:** Die iBGP-Session R1–R3 bleibt `Active`/`Idle`, auf R1 steht R3 nicht im Zustand `Established`.
- **So findest du es:** `show ip bgp summary` auf R1 zeigt R3 nicht Established. `debug ip bgp` auf R1 meldet eine Verbindung von 10.0.13.2, erwartet wird 10.255.0.3.
- **Ursache:** R3 sendet die BGP-Verbindung von der Adresse des Links (10.0.13.2), R1 erwartet 10.255.0.3 als Quelle: Die Quelladresse passt nicht.
- **Fix:** `neighbor 10.255.0.1 update-source Loopback0` auf R3.
- **Eingebaut:**

```diff
-  neighbor 10.255.0.1 update-source Loopback0
```

## Ticket 2 (R2)

- **Symptom:** R1 und R3 listen die Prefixe von ISP1 mit Next-Hop 192.0.2.2 ohne `>` (nicht Best), `show ip bgp` zeigt `inaccessible`.
- **So findest du es:** `show ip bgp` auf R1 und R3 zeigt die ISP1-Präfixe ohne `>`. `show ip bgp <Präfix>` meldet den Next-Hop 192.0.2.2 als „inaccessible“.
- **Ursache:** Der Next-Hop der eBGP-Routen (192.0.2.2) liegt nicht im IGP; ohne `next-hop-self` kann der RR/R3 ihn nicht auflösen.
- **Fix:** `next-hop-self` auf R2 Richtung R1.
- **Eingebaut:**

```diff
-  neighbor 10.255.0.1 next-hop-self
```

## Ticket 3 (R2)

- **Symptom:** Der Verkehr zu 203.0.113.0/24 verlässt das AS über ISP2, obwohl ISP1 bevorzugt sein soll.
- **So findest du es:** `show ip bgp 203.0.113.0` auf R1 zeigt beim ISP1-Pfad Local Preference 50, beim ISP2-Pfad 100.
- **Ursache:** Local-Pref 50 auf den ISP1-Routen: Die ISP2-Route (Standard 100) gewinnt.
- **Fix:** `set local-preference 200` in `ISP1-IN`.
- **Eingebaut:**

```diff
-  set local-preference 200
+  set local-preference 50
```

## Ticket 4 (R1)

- **Symptom:** R3 zeigt `show ip bgp community 65001:100` leer, obwohl R2 die Community setzt und R1 sie hat.
- **So findest du es:** `show ip bgp community 65001:100` auf R3 ist leer, auf R1 nicht. `show ip bgp neighbors 10.255.0.3 | include Community` auf R1 zeigt, dass keine Communities gesendet werden.
- **Ursache:** R1 sendet Communities nicht an R3 (`send-community` fehlt).
- **Fix:** `neighbor 10.255.0.3 send-community` auf R1.
- **Eingebaut:**

```diff
-  neighbor 10.255.0.3 send-community
```

## Ticket 5 (R3)

- **Symptom:** Die eBGP-Session R3–ISP2 steht auf `Idle`; im Log `Notification … (peer in wrong AS)`.
- **So findest du es:** Das Log auf R3 meldet „peer in wrong AS“. `show ip bgp summary` nennt bei ISP2 eine falsche AS.
- **Ursache:** Falsche AS-Nummer des Nachbarn auf R3.
- **Fix:** `remote-as 65200`.
- **Eingebaut:**

```diff
-  neighbor 192.0.2.6 remote-as 65200
+  neighbor 192.0.2.6 remote-as 65201
```

## Ticket 6 (R2)

- **Symptom:** R1 und R3 erreichen 10.255.0.2 nicht, die iBGP-Session zu R2 bleibt unten, obwohl der Link steht.
- **So findest du es:** `show ip route 10.255.0.2` auf R1 findet nichts. `show ip ospf interface brief` auf R2 listet die Loopback nicht.
- **Ursache:** Die OSPF-Wildcard 0.0.255.255 erfasst nur 10.0.x.x: Die Loopback 10.255.0.2 liegt nicht im Prozess.
- **Fix:** Wildcard 0.255.255.255 oder eigenes `network` für die Loopback.
- **Eingebaut:**

```diff
-  network 10.0.0.0 0.255.255.255 area 0
+  network 10.0.0.0 0.0.255.255 area 0
```

