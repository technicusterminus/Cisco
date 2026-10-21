# Fehlerliste – Lab 15 – Statisches Routing: Default, Netz, Host, Floating (IPv4 und IPv6)

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Der Backup-Link wird bereits im Normalbetrieb mitbenutzt (`show ip route` zeigt zwei Pfade, Last wird verteilt), obwohl er nur Reserve sein soll.
- **So findest du es:** `show ip route 172.16.20.0` auf R1 zeigt zwei Wege mit `[1/0]`. `show running-config | include ip route` zeigt die Backup-Route ohne AD am Ende.
- **Ursache:** Die Floating Route hat die Standard-AD 1 statt 200: ECMP mit beiden Next Hops.
- **Fix:** AD 200 anhängen.
- **Eingebaut:**

```diff
- ip route 172.16.20.0 255.255.255.0 10.15.12.6 200
+ ip route 172.16.20.0 255.255.255.0 10.15.12.6
```

## Ticket 2 (R2)

- **Symptom:** PC1 pingt PC2, bekommt aber keine Antwort.
- **So findest du es:** `show ip route 192.168.15.0` auf R2 zeigt den Next Hop 10.15.12.3, das ist die Broadcast-Adresse des /30.
- **Ursache:** R2 hat einen falschen Next Hop (10.15.12.3 = Broadcast des /30), Rückweg fehlt.
- **Fix:** Next Hop 10.15.12.1.
- **Eingebaut:**

```diff
- ip route 192.168.15.0 255.255.255.0 10.15.12.1
+ ip route 192.168.15.0 255.255.255.0 10.15.12.3
```

## Ticket 3 (R1)

- **Symptom:** IPv4 funktioniert, IPv6 nicht: PC1 und PC2 können sich per IPv6 nicht erreichen, `show ipv6 route` ist leer.
- **So findest du es:** `show running-config | include ipv6 unicast-routing` auf R1 bleibt leer.
- **Ursache:** `ipv6 unicast-routing` fehlt auf R1.
- **Fix:** `ipv6 unicast-routing` aktivieren.
- **Eingebaut:**

```diff
- ipv6 unicast-routing
```

## Ticket 4 (R2)

- **Symptom:** IPv6-Ping von PC2 nach PC1 scheitert, IPv4 geht.
- **So findest du es:** `show ipv6 route static` auf R2 zeigt den Next Hop …::11. Den gibt es nicht.
- **Ursache:** IPv6-Next-Hop-Tippfehler (…::11).
- **Fix:** Next Hop 2001:db8:15:12::1.
- **Eingebaut:**

```diff
- ipv6 route 2001:db8:15:1::/64 2001:db8:15:12::1
+ ipv6 route 2001:db8:15:1::/64 2001:db8:15:12::11
```

