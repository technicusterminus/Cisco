# Fehlerliste – Lab 08 – Trunks, Native VLAN, DTP und CDP/LLDP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW3)

- **Symptom:** Auf SW2/SW3 erscheinen Meldungen zu `native vlan mismatch`; `show cdp neighbors detail` zeigt unterschiedliche Native VLANs, Verkehr im VLAN 99 stimmt nicht.
- **So findest du es:** `show interfaces trunk` auf SW2 und SW3 vergleichen: SW3 zeigt an Fa0/24 Native VLAN 1, SW2 Native VLAN 99.
- **Ursache:** SW3 nutzt Native VLAN 1, SW2 Native VLAN 99.
- **Fix:** `switchport trunk native vlan 99` auf SW3 Fa0/24.
- **Eingebaut:**

```diff
- interface FastEthernet0/24
-  switchport mode trunk
-  switchport trunk native vlan 99
+ interface FastEthernet0/24
+  switchport mode trunk
+  switchport trunk native vlan 1
```

## Ticket 2 (SW2)

- **Symptom:** PC1 erreicht PC2 nicht; auf SW2 zeigt `show interfaces trunk` für Fa0/23 nur VLAN 99 als erlaubt.
- **So findest du es:** `show interfaces trunk` auf SW2 zeigt bei Fa0/23 nur VLAN 99 als erlaubt.
- **Ursache:** VLAN 10 ist auf dem Trunk SW1–SW2 nicht erlaubt.
- **Fix:** `switchport trunk allowed vlan 10,99`.
- **Eingebaut:**

```diff
- interface FastEthernet0/23
-  switchport mode trunk
-  switchport trunk native vlan 99
-  switchport trunk allowed vlan 10,99
+ interface FastEthernet0/23
+  switchport mode trunk
+  switchport trunk native vlan 99
+  switchport trunk allowed vlan 99
```

## Ticket 3 (SW2)

- **Symptom:** `show cdp neighbors` auf SW1 und SW3 zeigt SW2 nicht mehr, obwohl der Link up ist.
- **So findest du es:** `show cdp` auf SW2 meldet „CDP is not enabled“.
- **Ursache:** CDP ist auf SW2 global abgeschaltet (`no cdp run`).
- **Fix:** `cdp run` global aktivieren.
- **Eingebaut:**

```diff
- lldp run
+ no cdp run
+ lldp run
```

## Ticket 4 (SW1)

- **Symptom:** Der Link SW1–SW2 wird nicht zum Trunk (Access-Betrieb); PC1 erreicht PC2 nicht.
- **So findest du es:** `show interfaces fa0/23 switchport` auf SW1 zeigt „Administrative Mode: dynamic auto“ und „Operational Mode: static access“. SW2 hat `nonegotiate`.
- **Ursache:** SW1 steht auf `dynamic auto`, SW2 hat `nonegotiate` und sendet keine DTP-Frames: auto wartet passiv, es entsteht nie ein Trunk.
- **Fix:** Auf SW1 `switchport mode trunk` setzen.
- **Eingebaut:**

```diff
- interface FastEthernet0/23
-  switchport mode trunk
+ interface FastEthernet0/23
+  switchport mode dynamic auto
```

