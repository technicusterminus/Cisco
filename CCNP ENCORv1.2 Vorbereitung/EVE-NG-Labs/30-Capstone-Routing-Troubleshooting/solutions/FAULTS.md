# Fehlerliste – Lab 30 – Capstone: Routing-Fehlersuche (OSPF, EIGRP, BGP, Redistribution)

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Kein BGP: R1 hat keine Default-Route, R2/R3/R4 erreichen 203.0.113.1 nicht.
- **Ursache:** Falsche AS-Nummer des Providers auf R1.
- **Fix:** `remote-as 65000`.
- **Eingebaut:**

```diff
-  neighbor 198.51.100.2 remote-as 65000
+  neighbor 198.51.100.2 remote-as 65010
```

## Ticket 2 (R1)

- **Symptom:** BGP steht, R1 hat eine Default-Route, aber R2 und R3 haben keine.
- **Ursache:** R1 gibt die Default nicht in OSPF weiter.
- **Fix:** `default-information originate` unter `router ospf 1` auf R1.
- **Eingebaut:**

```diff
-  default-information originate
```

## Ticket 3 (R2)

- **Symptom:** R2 und R3 bilden keine Nachbarschaft; Mismatched Stub/Transit-Option im Debug.
- **Ursache:** Area 1 ist nur auf R3 als Stub definiert.
- **Fix:** `area 1 stub` auf R2.
- **Eingebaut:**

```diff
-  area 1 stub
```

## Ticket 4 (R2)

- **Symptom:** R1 und R3 sehen 172.20.4.0/24 nicht.
- **Ursache:** Ohne `subnets` redistribuiert OSPF nur klassenbehaftete Netze.
- **Fix:** `subnets` ergänzen.
- **Eingebaut:**

```diff
-  redistribute eigrp 100 subnets
+  redistribute eigrp 100
```

## Ticket 5 (R2)

- **Symptom:** Auf R4 fehlen die OSPF-Routen (R3-Loopback, 10.0.12.0/30); nur die statische Default erreicht R2.
- **Ursache:** Ohne Seed-Metrik übernimmt EIGRP die OSPF-Routen nicht.
- **Fix:** Metrik angeben (`metric 10000 100 255 1 1500`).
- **Eingebaut:**

```diff
-  redistribute ospf 1 metric 10000 100 255 1 1500
+  redistribute ospf 1
```

## Ticket 6 (R4)

- **Symptom:** R4 erreicht nichts außerhalb des direkten Links; `show ip route` zeigt die Default mit unerreichbarem Next-Hop.
- **Ursache:** Falscher Next-Hop der statischen Default auf R4.
- **Fix:** Next-Hop 10.0.24.1 (R2).
- **Eingebaut:**

```diff
- ip route 0.0.0.0 0.0.0.0 10.0.24.1
+ ip route 0.0.0.0 0.0.0.0 10.0.24.3
```

## Ticket 7 (R3)

- **Symptom:** Das Netz 192.168.3.0/24 fehlt auf R1/R2, Pings von R3-Lo10 ins Internet scheitern am Rückweg.
- **Ursache:** R3 nimmt Lo10 nicht in OSPF auf.
- **Fix:** `network 192.168.3.0 0.0.0.255 area 1` auf R3.
- **Eingebaut:**

```diff
-  network 192.168.3.0 0.0.0.255 area 1
```

## Ticket 8 (ISP)

- **Symptom:** Alle Pings von internen Quellen an 203.0.113.1 scheitern auf dem Rückweg, obwohl das Routing intern stimmt; Traceroute zeigt den Hinweg bis zum ISP.
- **Ursache:** Die Rückroute des ISP für 10.0.0.0/8 zeigt auf einen nicht vorhandenen Next-Hop.
- **Fix:** Next-Hop 198.51.100.1 (R1).
- **Eingebaut:**

```diff
- ip route 10.0.0.0 255.0.0.0 198.51.100.1
+ ip route 10.0.0.0 255.0.0.0 198.51.100.3
```

