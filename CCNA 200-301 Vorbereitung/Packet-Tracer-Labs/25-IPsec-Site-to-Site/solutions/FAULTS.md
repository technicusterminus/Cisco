# Fehlerliste – Lab 25 – IPsec Site-to-Site-VPN

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** Phase 1 kommt nicht zustande: `show crypto isakmp sa` ist leer oder `MM_NO_STATE`/`AG_NO_STATE`, im Debug `pre-shared key mismatch`.
- **So findest du es:** `show crypto isakmp sa` zeigt `MM_NO_STATE`. `debug crypto isakmp` meldet einen falschen Pre-Shared Key. Vergleiche die Schlüssel in beiden Konfigurationen.
- **Ursache:** Die Pre-Shared Keys unterscheiden sich (Groß-/Kleinschreibung).
- **Fix:** Identischen Schlüssel auf beiden Peers.
- **Eingebaut:**

```diff
- crypto isakmp key Lab2026vpnKey address 198.51.100.1
+ crypto isakmp key Lab2026vpnKeY address 198.51.100.1
```

## Ticket 2 (R2)

- **Symptom:** Phase 1 steht, aber PC1 und PC2 erreichen sich nicht; Zähler von `show crypto ipsec sa` bleiben 0 oder Phase 2 scheitert.
- **So findest du es:** `show access-lists 110` auf R2 nennt als Ziel 192.168.26.0 statt 192.168.25.0.
- **Ursache:** Die ACL von R2 ist nicht das Spiegelbild der ACL von R1 (Ziel 192.168.26.0 statt 192.168.25.0).
- **Fix:** ACL auf R2 spiegelbildlich: 172.25.2.0 → 192.168.25.0.
- **Eingebaut:**

```diff
- access-list 110 permit ip 172.25.2.0 0.0.0.255 192.168.25.0 0.0.0.255
+ access-list 110 permit ip 172.25.2.0 0.0.0.255 192.168.26.0 0.0.0.255
```

## Ticket 3 (R1)

- **Symptom:** Phase 1 ist `QM_IDLE`, aber Phase 2 kommt nicht zustande; Meldung `no matching transform set`/`IPSEC rejected`.
- **So findest du es:** `show crypto ipsec transform-set` auf R1 zeigt 3DES, auf R2 AES.
- **Ursache:** Die Transform-Sets passen nicht (3DES gegen AES-256).
- **Fix:** Gleiches Transform-Set auf beiden Seiten.
- **Eingebaut:**

```diff
- crypto ipsec transform-set TS esp-aes 256 esp-sha-hmac
+ crypto ipsec transform-set TS esp-3des esp-sha-hmac
```

## Ticket 4 (R1)

- **Symptom:** PC1 → PC2 pingt nicht und nichts wird verschlüsselt: `show crypto isakmp sa` bleibt leer, `show crypto map` zeigt kein Interface.
- **So findest du es:** `show crypto map` zeigt bei „Interfaces using crypto map“ nichts.
- **Ursache:** Die Crypto Map ist nicht am WAN-Interface angewendet.
- **Fix:** `crypto map CMAP` auf Gi0/1.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  crypto map CMAP
+ interface GigabitEthernet0/1
```

## Ticket 5 (R1)

- **Symptom:** ISAKMP-Verhandlung scheitert (`MM_NO_STATE`), Debug zeigt `no offers accepted`.
- **So findest du es:** `debug crypto isakmp` meldet „no offers accepted“. `show crypto isakmp policy` auf R1 zeigt MD5, auf R2 SHA.
- **Ursache:** Hash-Algorithmus der IKE-Policy passt nicht (MD5 gegen SHA).
- **Fix:** `hash sha` auf R1.
- **Eingebaut:**

```diff
- crypto isakmp policy 10
-  encryption aes 256
-  hash sha
+ crypto isakmp policy 10
+  encryption aes 256
+  hash md5
```

