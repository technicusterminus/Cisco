# Fehlerliste – Lab 09 – EtherChannel mit LACP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW2)

- **Symptom:** `show etherchannel summary` zeigt kein `Po1(SU)`, die Links bleiben stand-alone (`I`) oder suspendiert; STP blockiert einen Link, ggf. Err-Disable.
- **Ursache:** SW2 verwendet statisches `on`, SW1 verhandelt per LACP `active`: die Modi sind inkompatibel.
- **Fix:** Auf SW2 `channel-group 1 mode active` (oder passive).
- **Eingebaut:**

```diff
-  channel-group 1 mode active
+  channel-group 1 mode on
```

## Ticket 2 (SW2)

- **Symptom:** Der Channel steht (`Po1(SU)`), aber PC1 und PC2 erreichen sich nicht.
- **Ursache:** Der Port-Channel auf SW2 lässt nur VLAN 20 zu, SW1 nur VLAN 10.
- **Fix:** Auf SW2 `switchport trunk allowed vlan 10`.
- **Eingebaut:**

```diff
- interface Port-channel1
-  switchport mode trunk
-  switchport trunk allowed vlan 10
+ interface Port-channel1
+  switchport mode trunk
+  switchport trunk allowed vlan 20
```

## Ticket 3 (SW1)

- **Symptom:** Nur ein Member (Fa0/21) ist gebündelt, Fa0/22 meldet `s` oder `I`; die Bandbreite des Channels ist nur 100 Mbit/s.
- **Ursache:** Fa0/22 hat eine abweichende Geschwindigkeit (10 Mbit/s) und passt nicht zum Channel.
- **Fix:** `speed auto` (oder identisch zu Fa0/21) auf Fa0/22.
- **Eingebaut:**

```diff
- interface range FastEthernet0/21 - 22
-  channel-group 1 mode active
+ interface FastEthernet0/22
+  speed 10
+ interface range FastEthernet0/21 - 22
+  channel-group 1 mode active
```

## Ticket 4 (SW1)

- **Symptom:** PC1 erreicht PC2 nicht, obwohl der Channel steht.
- **Ursache:** Der PC-Port an SW1 liegt in VLAN 20.
- **Fix:** `switchport access vlan 10`.
- **Eingebaut:**

```diff
- interface FastEthernet0/1
-  switchport mode access
-  switchport access vlan 10
+ interface FastEthernet0/1
+  switchport mode access
+  switchport access vlan 20
```

