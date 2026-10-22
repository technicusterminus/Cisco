# Fehlerliste – Lab E2 – MPLS L3VPN mit LDP und MP-BGP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (PE2)

- **Symptom:** Die BGP-Sitzung zwischen PE1 und PE2 kommt nicht hoch; `show bgp vpnv4 unicast all summary` zeigt den Nachbarn dauerhaft in Active oder Idle.
- **So findest du es:** `show bgp vpnv4 unicast all neighbors 10.255.0.1` auf PE2 zeigt als lokale Adresse nicht 10.255.0.3. Auf PE1 steht der Nachbar 10.255.0.3 in Active: PE1 erwartet die Verbindung von der Loopback-Adresse.
- **Ursache:** PE2 baut die TCP-Verbindung mit der Adresse des ausgehenden Interfaces (10.0.23.2) auf. PE1 kennt als Nachbar aber 10.255.0.3 und lehnt die Quelle ab. `update-source Loopback0` fehlt.
- **Fix:** `neighbor 10.255.0.1 update-source Loopback0` auf PE2.
- **Eingebaut:**

```diff
- neighbor 10.255.0.1 update-source Loopback0
```

## Ticket 2 (PE1)

- **Symptom:** CE2 lernt 10.100.1.0/24 nicht, obwohl PE1 die Route von CE1 hat und die VPNv4-Sitzung steht.
- **So findest du es:** `show bgp vpnv4 unicast all 10.100.1.0/24` auf PE1 zeigt die Route ohne `Extended Community: RT:…`. `show vrf detail CUST-A` führt keinen Export-RT auf.
- **Ursache:** Die VRF auf PE1 exportiert kein Route Target. Die Route geht ohne RT an PE2, dort importiert keine VRF sie (Route-Target-Filter).
- **Fix:** `route-target export 65000:100` im `address-family ipv4` der VRF auf PE1.
- **Eingebaut:**

```diff
-  route-target export 65000:100
```

## Ticket 3 (PE1)

- **Symptom:** CE1 lernt 10.100.2.0/24 nicht, obwohl PE2 die Route von CE2 hat und die VPNv4-Sitzung steht.
- **So findest du es:** `show vrf detail CUST-A` auf PE1 zeigt Import-RT 65000:101. PE2 exportiert mit 65000:100 (`show bgp vpnv4 unicast all 10.100.2.0/24` auf PE2).
- **Ursache:** Der Import-RT auf PE1 stimmt nicht mit dem Export-RT von PE2 überein. PE1 verwirft die Routen von PE2 schon beim Eingang.
- **Fix:** `route-target import 65000:100` auf PE1.
- **Eingebaut:**

```diff
-  route-target import 65000:100
+  route-target import 65000:101
```

## Ticket 4 (P)

- **Symptom:** Alle Routen sind da, aber `ping 10.100.2.1 source Loopback1` von CE1 scheitert; die Traceroute zeigt nach PE1 nur noch Sterne.
- **So findest du es:** `show mpls ldp neighbor` auf dem P zeigt nur PE1, nicht PE2. `show mpls interfaces` listet Gi0/1 nicht. Die BGP-Sitzung steht, weil sie über das IGP läuft.
- **Ursache:** Auf dem P-Interface zu PE2 fehlt `mpls ip`. Ohne LDP-Sitzung gibt es zwischen P und PE2 kein Label, der Transport-LSP ist an dieser Stelle unterbrochen. IP-Routing und BGP laufen weiter, die Kundenpakete (mit Label) nicht. Die ICMP-Antworten des P-Routers laufen ebenfalls durch den unterbrochenen LSP, deshalb zeigt die Traceroute hinter PE1 nur Sterne.
- **Fix:** `mpls ip` unter Gi0/1 auf dem P.
- **Eingebaut:**

```diff
- mpls ip
```

## Ticket 5 (CE2)

- **Symptom:** Die eBGP-Sitzung zwischen CE2 und PE2 steht nicht; CE2 meldet Active, PE2 hat keine Route aus dem Kundennetz.
- **So findest du es:** `show ip bgp summary` auf CE2: Nachbar 192.168.2.1 in Idle/Active. `show ip bgp neighbors 192.168.2.1` nennt das erwartete Remote-AS 65100. Das Log meldet „bad peer AS“.
- **Ursache:** CE2 erwartet beim PE das AS 65100, der PE sendet 65000. Die Sitzung wird mit einer Notification abgebrochen.
- **Fix:** `neighbor 192.168.2.1 remote-as 65000` auf CE2.
- **Eingebaut:**

```diff
- neighbor 192.168.2.1 remote-as 65000
+ neighbor 192.168.2.1 remote-as 65100
```
