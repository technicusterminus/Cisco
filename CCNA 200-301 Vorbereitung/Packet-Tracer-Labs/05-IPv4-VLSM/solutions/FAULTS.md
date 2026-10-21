# Fehlerliste – Lab 05 – IPv4-Adressierung, VLSM und private Bereiche

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** R1 und R2 sehen sich nicht, kein Ping über den Router-Link; die LANs erreichen sich nicht.
- **So findest du es:** `show ip interface brief` auf R1 und R2 vergleichen und die beiden /30-Netze ausrechnen: R1 liegt in .252/30, R2 in .248/30.
- **Ursache:** R2 hat am Link 192.168.50.250 statt .254. Mit /30 liegt R2 damit im Netz .248 bis .251, R1 (.253) im Netz .252 bis .255. Die beiden sind keine Nachbarn mehr.
- **Fix:** Adresse 192.168.50.254 255.255.255.252 setzen.
- **Eingebaut:**

```diff
-  ip address 192.168.50.254 255.255.255.252
+  ip address 192.168.50.250 255.255.255.252
```

## Ticket 2 (R1)

- **Symptom:** PC-A erreicht LAN-B, aber nicht LAN-C; `show ip route` zeigt die Route zu .96/28 mit dem eigenen Link-Interface als Next Hop.
- **So findest du es:** `show ip route` auf R1 zeigt die Route zu 192.168.50.96/28 mit Next Hop 192.168.50.253, das ist R1 selbst.
- **Ursache:** Der Next Hop zeigt auf die eigene Adresse (192.168.50.253) statt auf R2 (.254).
- **Fix:** Next Hop auf 192.168.50.254 ändern.
- **Eingebaut:**

```diff
- ip route 192.168.50.96 255.255.255.240 192.168.50.254
+ ip route 192.168.50.96 255.255.255.240 192.168.50.253
```

## Ticket 3 (PC-B)

- **Symptom:** PC-B hat keine Verbindung außer lokal; `ipconfig` zeigt eine Adresse, die auf .95 endet.
- **So findest du es:** `ipconfig` auf PC-B zeigt 192.168.50.95. Rechne nach: Das ist der Broadcast von .64/27.
- **Ursache:** 192.168.50.95 ist die Broadcast-Adresse von 192.168.50.64/27 und darf keinem Host gehören.
- **Fix:** Gültige Hostadresse vergeben, z. B. 192.168.50.70.
- **Eingebaut:** Endgerät-Einstellung `ip` = `192.168.50.95`

## Ticket 4 (PC-C)

- **Symptom:** PC-C erreicht nur das eigene Subnetz, aber keine anderen LANs.
- **So findest du es:** `ipconfig` auf PC-C zeigt das Gateway .98, `show ip interface brief` auf R2 die Adresse .97.
- **Ursache:** Der Default-Gateway liegt neben dem Router (.98 statt .97): kein Gerät antwortet darauf.
- **Fix:** Gateway 192.168.50.97 eintragen.
- **Eingebaut:** Endgerät-Einstellung `gw` = `192.168.50.98`

