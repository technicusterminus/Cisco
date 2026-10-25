# Fehlerliste – Lab 07 – VLANs, Trunks und Inter-VLAN-Routing

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW2)

- **Symptom:** PC3 (192.168.10.12) erreicht weder PC1 noch sein Gateway.
- **So findest du es:** `show vlan brief` auf SW2 listet den Port von PC3 bei VLAN 20, PC3 hat aber eine Adresse aus VLAN 10.
- **Ursache:** Der Access-Port von PC3 liegt in VLAN 20, die IP-Konfiguration gehört zu VLAN 10.
- **Fix:** `switchport access vlan 10` auf SW2 Fa0/1.
- **Eingebaut:**

```diff
- interface FastEthernet0/1
-  switchport mode access
-  switchport access vlan 10
+ interface FastEthernet0/1
+  switchport mode access
+  switchport access vlan 20
```

## Ticket 2 (SW1)

- **Symptom:** VLAN 10 läuft über beide Switches, VLAN 20 nicht: PC4 erreicht weder PC2 noch sein Gateway.
- **So findest du es:** `show interfaces trunk` auf SW1 zeigt VLAN 20 nicht bei „Vlans allowed on trunk“.
- **Ursache:** Auf dem Trunk SW1–SW2 ist VLAN 20 nicht erlaubt.
- **Fix:** `switchport trunk allowed vlan add 20` (oder 10,20).
- **Eingebaut:**

```diff
- interface FastEthernet0/24
-  switchport mode trunk
-  switchport trunk allowed vlan 10,20
+ interface FastEthernet0/24
+  switchport mode trunk
+  switchport trunk allowed vlan 10
```

## Ticket 3 (R1)

- **Symptom:** Hosts in VLAN 20 erreichen ihr Gateway 192.168.20.1 nicht, VLAN 10 funktioniert.
- **So findest du es:** `show interfaces gi0/0.20` auf R1 zeigt „Vlan ID 200“.
- **Ursache:** Das Subinterface Gi0/0.20 erwartet VLAN-Tag 200, der Switch sendet Tag 20.
- **Fix:** `encapsulation dot1Q 20`.
- **Eingebaut:**

```diff
-  encapsulation dot1Q 20
+  encapsulation dot1Q 200
```

## Ticket 4 (SW2)

- **Symptom:** Kein VLAN läuft zwischen SW1 und SW2; `show interfaces trunk` auf SW2 bleibt leer.
- **So findest du es:** `show interfaces fa0/24 switchport` auf SW2 meldet „Administrative Mode: static access“.
- **Ursache:** SW2 Fa0/24 ist Access-Port statt Trunk.
- **Fix:** `switchport mode trunk` und erlaubte VLANs 10,20.
- **Eingebaut:**

```diff
- interface FastEthernet0/24
-  switchport mode trunk
-  switchport trunk allowed vlan 10,20
+ interface FastEthernet0/24
+  switchport mode access
```

## Ticket 5 (PC2)

- **Symptom:** PC2 erreicht PC4 (gleiches VLAN), aber nichts in anderen Netzen.
- **So findest du es:** `ipconfig` auf PC2 zeigt das Gateway 192.168.20.254, R1 hat .1.
- **Ursache:** Das Gateway 192.168.20.254 existiert nicht, der Router hat .1.
- **Fix:** Gateway 192.168.20.1.
- **Eingebaut:** Endgerät-Einstellung `gw` = `192.168.20.254`

