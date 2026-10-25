# Fehlerliste – Lab 14 – GRE, IPsec und VTI

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (CE2)

- **Symptom:** Tunnel0 ist up/up, aber OSPF-Nachbar bleibt aus. `show crypto isakmp sa` zeigt MM_NO_STATE bzw. nichts.
- **So findest du es:** `show crypto isakmp sa` zeigt MM_NO_STATE. `debug crypto isakmp` meldet einen Fehler bei der Authentisierung. Die Keys vergleichst du in der Konfiguration (`crypto isakmp key` bzw. Keyring).
- **Ursache:** Pre-Shared Keys unterscheiden sich: Phase 1 scheitert.
- **Fix:** Key auf CE2 an CE1 angleichen.
- **Eingebaut:**

```diff
- crypto isakmp key CiscoLab123 address 198.51.100.1
+ crypto isakmp key CiscoLab999 address 198.51.100.1
```

## Ticket 2 (CE1)

- **Symptom:** `show crypto isakmp sa` zeigt `QM_IDLE`, aber über den Tunnel geht nichts: Der OSPF-Nachbar bleibt aus, `encaps` und `decaps` stehen auf 0.
- **So findest du es:** Phase 1 steht also, Phase 2 nicht. `show crypto ipsec sa` zeigt keine aktive ESP-SA, das Log bzw. `debug crypto ipsec` meldet, dass kein Proposal passt. `show crypto ipsec transform-set` zeigt AES-128 auf CE1 und AES-256 auf CE2.
- **Ursache:** Die Transform-Sets passen nicht zusammen (AES-128 gegen AES-256). Ohne gemeinsames Proposal entsteht keine IPsec-SA, deshalb verschlüsselt CE1 nichts und die Zähler bleiben bei 0.
- **Fix:** Transform-Set auf beiden Seiten gleich konfigurieren.
- **Eingebaut:**

```diff
- crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac
+ crypto ipsec transform-set TS esp-aes 128 esp-sha256-hmac
```

## Ticket 3 (CE1)

- **Symptom:** Tunnel0 zeigt up/up (Keepalive nicht aktiv), aber nichts kommt an; `show crypto isakmp sa` bleibt leer.
- **So findest du es:** `show interfaces Tunnel0` auf CE1 zeigt ein Tunnelziel, das es nicht gibt. Ein Ping auf diese Adresse scheitert.
- **Ursache:** Tunnelziel zeigt auf eine nicht existierende Adresse.
- **Fix:** Tunnelziel auf 203.0.113.1 setzen.
- **Eingebaut:**

```diff
- tunnel destination 203.0.113.1
+ tunnel destination 203.0.113.11
```

## Ticket 4 (CE2)

- **Symptom:** Tunnel und IPsec stehen, aber OSPF-Nachbarschaft fehlt, LANs sind nicht erreichbar.
- **So findest du es:** `show ip ospf interface brief` auf CE2 listet Tunnel0 nicht.
- **Ursache:** OSPF auf CE2 enthält das Tunnelnetz nicht; Tunnel0 nimmt nicht am Routing teil.
- **Fix:** Tunnelnetz 172.16.0.0/30 in OSPF aufnehmen (oder `ip ospf 1 area 0` am Interface).
- **Eingebaut:**

```diff
-  network 172.16.0.0 0.0.0.3 area 0
```

## Ticket 5 (CE2)

- **Symptom:** Tunnel flappt zyklisch, das Log zeigt `%TUN-5-RECURDOWN` (Tunnel Interface is Down, recursive routing).
- **So findest du es:** Das Log zeigt `%TUN-5-RECURDOWN`. `show ip route <Tunnelziel>` auf CE1 zeigt einen Weg über Tunnel0, also über sich selbst.
- **Ursache:** CE2 kündigt das Transfernetz im Overlay-OSPF an; CE1 lernt es über den Tunnel und routet das Tunnelziel durch den eigenen Tunnel.
- **Fix:** Transfernetz aus OSPF nehmen, nur Overlay und LANs im IGP.
- **Eingebaut:**

```diff
-  network 192.168.2.0 0.0.0.255 area 0
+  network 192.168.2.0 0.0.0.255 area 0
+  network 203.0.113.0 0.0.0.3 area 0
```

