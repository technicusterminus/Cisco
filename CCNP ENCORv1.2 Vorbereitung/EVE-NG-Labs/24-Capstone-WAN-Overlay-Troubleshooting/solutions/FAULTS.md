# Fehlerliste – Lab 24 – Capstone: WAN, eBGP und IPsec-Overlay, Fehlersuche

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Die BGP-Session R1–ISP kommt nicht hoch (`Idle`/`Active`), im Log steht `%BGP-3-NOTIFICATION: sent to neighbor 198.51.100.2 2/2 (peer in wrong AS)`.
- **Ursache:** Auf R1 ist der Nachbar-AS mit 65010 statt 65000 konfiguriert.
- **Fix:** `neighbor 198.51.100.2 remote-as 65000`.
- **Eingebaut:**

```diff
-  neighbor 198.51.100.2 remote-as 65000
+  neighbor 198.51.100.2 remote-as 65010
```

## Ticket 2 (R2)

- **Symptom:** R1 lernt das Transportnetz von R2 nicht (`show ip bgp` ohne 203.0.113.0/30), R1 erreicht 203.0.113.1 nicht, der Tunnel kommt von R1 aus nicht hoch.
- **Ursache:** R2 kündigt sein Transportnetz nicht an: `network 203.0.113.0 mask 255.255.255.252` fehlt.
- **Fix:** `network`-Statement unter `router bgp 65002` ergänzen.
- **Eingebaut:**

```diff
-  network 203.0.113.0 mask 255.255.255.252
```

## Ticket 3 (ISP)

- **Symptom:** R2 erreicht 198.51.100.1 nicht: Im BGP-Table von R2 fehlt 198.51.100.0/30, obwohl R1 es ankündigt. Beim ISP steht der Prefix in `show ip bgp neighbors 198.51.100.1 received-routes`, nicht aber im Table.
- **Ursache:** Die eingehende Prefix-Liste des ISP für R1 erlaubt den falschen Prefix (198.51.100.4/30): R1s Ankündigung wird verworfen.
- **Fix:** Prefix-Liste auf `198.51.100.0/30` korrigieren und `clear ip bgp 198.51.100.1 soft in`.
- **Eingebaut:**

```diff
- ip prefix-list FROM-R1 seq 5 permit 198.51.100.0/30
+ ip prefix-list FROM-R1 seq 5 permit 198.51.100.4/30
```

## Ticket 4 (R1)

- **Symptom:** Nach der Underlay-Korrektur ist Tunnel0 auf R1 `up/up`, aber R2 sieht keinen Tunnel-Verkehr und `show crypto isakmp sa` ist leer.
- **Ursache:** Die Tunnel-Destination auf R1 zeigt auf die Adresse des ISP statt auf R2: GRE-Pakete landen beim ISP und werden dort nicht weiterverarbeitet.
- **Fix:** `tunnel destination 203.0.113.1`.
- **Eingebaut:**

```diff
-  tunnel destination 203.0.113.1
+  tunnel destination 203.0.113.2
```

## Ticket 5 (R2)

- **Symptom:** `show crypto isakmp sa` bleibt in `MM_KEY_EXCH`/`MM_NO_STATE`, der OSPF-Nachbar fehlt, Pings durch den Tunnel scheitern.
- **Ursache:** Der Pre-shared Key auf R2 weicht von R1 ab (LabKey321 vs. LabKey123): Phase 1 scheitert bei der Authentifizierung.
- **Fix:** PSK auf beiden Seiten angleichen.
- **Eingebaut:**

```diff
- crypto isakmp key LabKey123 address 198.51.100.1
+ crypto isakmp key LabKey321 address 198.51.100.1
```

## Ticket 6 (R2)

- **Symptom:** Nach der IPsec-Korrektur bleibt der OSPF-Nachbar in `EXSTART`/`EXCHANGE` hängen (`%OSPF-5-ADJCHG` wechselt, `Neighbor ... stuck`).
- **Ursache:** MTU-Mismatch: R1 hat Tunnel-MTU 1400, R2 den Standard (1476): OSPF verwirft die DBD-Pakete.
- **Fix:** `ip mtu 1400` auf Tunnel0 von R2.
- **Eingebaut:**

```diff
-  ip mtu 1400
```

## Ticket 7 (R2)

- **Symptom:** Nach der MTU-Korrektur kommt noch immer kein OSPF-Nachbar hoch; das Log meldet `%OSPF-4-ERRRCV: Received invalid packet: Mismatch Authentication Key`.
- **Ursache:** Der MD5-Key auf R2 weicht ab: OSPF verwirft jedes Paket.
- **Fix:** Gleichen Key `OspfKey` auf beiden Seiten setzen.
- **Eingebaut:**

```diff
-  ip ospf message-digest-key 1 md5 OspfKey
+  ip ospf message-digest-key 1 md5 OspfKey2
```

## Ticket 8 (R2)

- **Symptom:** OSPF-Nachbar `FULL`, aber H1 erreicht H2 nicht; R1 hat keine Route nach 192.168.2.0/24.
- **Ursache:** R2 bindet sein LAN nicht in OSPF ein: Das Netz wird nicht angekündigt.
- **Fix:** `network 192.168.2.0 0.0.0.255 area 0` unter `router ospf 1` auf R2.
- **Eingebaut:**

```diff
-  network 192.168.2.0 0.0.0.255 area 0
```

## Ticket 9 (R1)

- **Symptom:** H3 (Gast) pingt H1 erfolgreich und sogar 10.99.0.2. `show ip route vrf GUEST` ist leer, die Gast-LAN liegt in der globalen Routing-Tabelle.
- **Ursache:** Gi0/2 gehört nicht zum VRF GUEST: Es gibt keine Isolation, das Interface nutzt die globale Tabelle.
- **Fix:** `ip vrf forwarding GUEST` am Interface, danach IP neu setzen.
- **Eingebaut:**

```diff
-  ip vrf forwarding GUEST
```

