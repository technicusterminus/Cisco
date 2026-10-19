# Fehlerliste – Lab 16 – VXLAN: VTEP, VNI und Ingress Replication

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (LEAF2)

- **Symptom:** H1 und H2 im selben Subnetz erreichen sich nicht, `show nve vni` zeigt auf LEAF2 eine andere VNI.
- **Ursache:** VLAN 10 ist auf LEAF2 auf VNI 10011 gemappt, auf LEAF1 auf 10010: Das Segment stimmt nicht überein.
- **Fix:** VNI auf beiden Leafs identisch machen.
- **Eingebaut:**

```diff
-   vn-segment 10010
+   vn-segment 10011
```

## Ticket 2 (LEAF1)

- **Symptom:** `show nve peers` ist auf LEAF1 leer oder zeigt einen Peer ohne Verkehr.
- **Ursache:** Die Ingress-Replication-Peerliste zeigt auf eine falsche VTEP-Adresse.
- **Fix:** Peer-IP auf 10.255.0.2 korrigieren.
- **Eingebaut:**

```diff
-       peer-ip 10.255.0.2
+       peer-ip 10.255.0.22
```

## Ticket 3 (LEAF2)

- **Symptom:** Die Verbindung steht nie, `show nve interface` zeigt `Admin down`.
- **Ursache:** Das NVE-Interface ist administrativ ausgeschaltet.
- **Fix:** `no shutdown` am nve1.
- **Eingebaut:**

```diff
- interface nve1
-   no shutdown
+ interface nve1
+   shutdown
```

## Ticket 4 (LEAF1)

- **Symptom:** LEAF2 erreicht 10.255.0.1 nicht (Ping auf die VTEP-Adresse scheitert), NVE-Peer bleibt down.
- **Ursache:** Die VTEP-Loopback wird nicht ins Underlay-OSPF aufgenommen: Der Gegen-VTEP hat keine Route.
- **Fix:** `ip router ospf 1 area 0.0.0.0` an Loopback0 ergänzen.
- **Eingebaut:**

```diff
- interface loopback0
-   ip address 10.255.0.1/32
-   ip router ospf 1 area 0.0.0.0
+ interface loopback0
+   ip address 10.255.0.1/32
```

