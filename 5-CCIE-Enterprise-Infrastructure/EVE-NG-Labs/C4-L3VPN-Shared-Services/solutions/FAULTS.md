# Fehlerliste – Lab C4 – MPLS L3VPN: Shared Services, AS-Override und Route-Target-Design

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (CEA1)

- **Symptom:** PE1 lernt von CEA1 kein einziges Präfix, obwohl die BGP-Sitzung steht.
- **So findest du es:** `show bgp vpnv4 unicast vrf A summary` auf PE1: Nachbar 192.168.11.2 mit 0 empfangenen Präfixen. Auf CEA1 steht `network 10.100.1.0 mask 255.255.0.0`, in der Routing-Tabelle gibt es aber nur 10.100.1.0/24. `show ip bgp` auf CEA1 ist leer.
- **Ursache:** Falsche Maske im `network`-Befehl. BGP kündigt ein `network` nur an, wenn genau dieses Präfix mit dieser Maske in der Routing-Tabelle steht.
- **Fix:** `no network 10.100.1.0 mask 255.255.0.0` und `network 10.100.1.0 mask 255.255.255.0` auf CEA1.
- **Eingebaut:**

```diff
- network 10.100.1.0 mask 255.255.255.0
+ network 10.100.1.0 mask 255.255.0.0
```

## Ticket 2 (PE2)

- **Symptom:** CEA2 erreicht das Netz von CEA1 (10.100.1.0/24) nicht.
- **So findest du es:** `show ip bgp` auf CEA2 enthält 10.100.1.0/24 nicht. PE2 sendet es mit dem Pfad `64500 65100` (`show bgp vpnv4 unicast vrf A neighbors 192.168.12.2 advertised-routes`), CEA2 sieht den eigenen AS und verwirft es. Auf PE2 fehlt `as-override` für 192.168.12.2.
- **Ursache:** Beide Standorte nutzen AS 65100. Ohne `as-override` steht 65100 im AS-Pfad, und der eBGP-Schleifenschutz von CEA2 greift.
- **Fix:** `neighbor 192.168.12.2 as-override` unter `address-family ipv4 vrf A` auf PE2.
- **Eingebaut:**

```diff
-  neighbor 192.168.12.2 as-override
```

## Ticket 3 (PE2)

- **Symptom:** CEA1 hat keine Route zu 10.100.2.0/24, und auch der Shared-Server CES kennt das Netz von CEA2 nicht.
- **So findest du es:** `show bgp vpnv4 unicast all 10.100.2.0` auf PE2 zeigt das Präfix mit dem Extended Community RT:64500:101. PE1 und die VRF SHARED importieren 64500:100.
- **Ursache:** Falsches Export-RT in VRF A auf PE2. Die Route verlässt die VRF mit 64500:101, und niemand importiert dieses RT, weder PE1 noch die lokale VRF SHARED.
- **Fix:** `no route-target export 64500:101` und `route-target export 64500:100` in VRF A auf PE2.
- **Eingebaut:**

```diff
-  route-target export 64500:100
+  route-target export 64500:101
```

## Ticket 4 (PE1)

- **Symptom:** CEA1 erreicht den Shared-Server 10.200.0.1 nicht, CEA2 schon.
- **So findest du es:** `show ip route vrf A 10.200.0.0` auf PE1: keine Route. `show bgp vpnv4 unicast all 10.200.0.0` auf PE1 zeigt das Präfix mit RT:64500:999, übernommen aber nur in VRF B. `show vrf detail A` auf PE1: Import nur 64500:100.
- **Ursache:** VRF A auf PE1 importiert das Route Target der Shared Services nicht. Der Server kündigt richtig an, PE1 übernimmt die Route nur nicht in VRF A.
- **Fix:** `route-target import 64500:999` unter `vrf definition A` → `address-family ipv4` auf PE1.
- **Eingebaut:**

```diff
-  route-target import 64500:999
```

## Ticket 5 (PE2)

- **Symptom:** Kunde B erreicht den Shared-Server nicht: `ping vrf B 10.200.0.1 source Loopback10` auf PE1 scheitert, obwohl PE1 in VRF B eine Route zu 10.200.0.0/24 hat.
- **So findest du es:** Hin geht es, zurück nicht: `show ip bgp` auf CES enthält 10.110.1.0/24 nicht. `show vrf detail SHARED` auf PE2 zeigt die Imports 64500:999 und 64500:100, 64500:200 fehlt.
- **Ursache:** Shared Services muss die Netze aller berechtigten Kunden importieren, sonst fehlt der Rückweg. Typisch für einseitige Fehler: Die Route zum Server ist da, die Antwort findet nicht zurück.
- **Fix:** `route-target import 64500:200` in der VRF SHARED auf PE2.
- **Eingebaut:**

```diff
-  route-target import 64500:200
```
