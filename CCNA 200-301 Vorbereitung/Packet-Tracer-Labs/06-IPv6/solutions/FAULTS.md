# Fehlerliste – Lab 06 – IPv6: Adressen, Adresstypen und EUI-64

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** PC1 erhält keine Adresse per SLAAC und erreicht nichts; `show ipv6 interface gi0/0` zeigt keine Router Advertisements.
- **Ursache:** Auf R1 fehlt `ipv6 unicast-routing`: kein IPv6-Routing, keine Router Advertisements.
- **Fix:** `ipv6 unicast-routing` global aktivieren.
- **Eingebaut:**

```diff
- ipv6 unicast-routing
```

## Ticket 2 (R1)

- **Symptom:** PC1 erreicht R2 (Link), aber nicht LAN2; `show ipv6 route` zeigt die Route mit einem nicht erreichbaren Next Hop.
- **Ursache:** Next Hop 2001:db8:acad:12::3 existiert nicht, R2 hat ::2.
- **Fix:** Next Hop auf 2001:db8:acad:12::2 korrigieren.
- **Eingebaut:**

```diff
- ipv6 route 2001:db8:acad:20::/64 2001:db8:acad:12::2
+ ipv6 route 2001:db8:acad:20::/64 2001:db8:acad:12::3
```

## Ticket 3 (R2)

- **Symptom:** PC2 bekommt eine Adresse aus einem unerwarteten Präfix (…:21::), Antworten an PC1 laufen ins Leere, da R1 …:20::/64 routet.
- **Ursache:** Falsches Präfix am LAN2-Interface (21 statt 20).
- **Fix:** Präfix 2001:db8:acad:20::/64 verwenden.
- **Eingebaut:**

```diff
-  ipv6 address 2001:db8:acad:20::/64 eui-64
+  ipv6 address 2001:db8:acad:21::/64 eui-64
```

## Ticket 4 (R2)

- **Symptom:** LAN2 erreicht nichts jenseits von R2 (auch nicht LAN1).
- **Ursache:** Default-Route mit falschem Next Hop.
- **Fix:** Next Hop 2001:db8:acad:12::1.
- **Eingebaut:**

```diff
- ipv6 route ::/0 2001:db8:acad:12::1
+ ipv6 route ::/0 2001:db8:acad:12::5
```

