# Fehlerliste – Lab 05 – VLANs, Trunks und EtherChannel

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW2)

- **Symptom:** Po1 kommt nicht hoch: Auf SW1 sind die Ports `s` (suspended), H1 hat keine Verbindung.
- **So findest du es:** `show etherchannel summary` auf SW1 zeigt die Ports mit `(s)`. Auf SW2 zeigt derselbe Befehl den Modus `on`, also kein Protokoll, während SW1 LACP spricht.
- **Ursache:** Statischer Modus `on` auf SW2 trifft LACP `active` auf SW1: LACPDUs werden nicht beantwortet, der Channel wird nicht gebildet.
- **Fix:** SW2 auf `passive` oder `active` zurückstellen.
- **Eingebaut:**

```diff
- channel-group 1 mode passive
+ channel-group 1 mode on
```

## Ticket 2 (SW3)

- **Symptom:** H2 (VLAN 20) hat weder Gateway noch Verbindung, H3 (VLAN 10) funktioniert.
- **So findest du es:** `show interfaces trunk` auf SW3: In der Zeile „Vlans allowed on trunk“ fehlt VLAN 20 bei Po2.
- **Ursache:** VLAN 20 fehlt in der Allowed-Liste von Po2 auf SW3.
- **Fix:** `switchport trunk allowed vlan 10,20` auf Po2 setzen.
- **Eingebaut:**

```diff
- interface Port-channel2
-  switchport mode trunk
-  switchport trunk native vlan 99
-  switchport trunk allowed vlan 10,20
+ interface Port-channel2
+  switchport mode trunk
+  switchport trunk native vlan 99
+  switchport trunk allowed vlan 10
```

## Ticket 3 (R1)

- **Symptom:** Alle Hosts in VLAN 20 erreichen ihr Gateway 10.10.20.1 nicht, VLAN 10 ist in Ordnung.
- **So findest du es:** `show interfaces Gi0/0.20` auf R1 zeigt „Encapsulation 802.1Q Virtual LAN, Vlan ID 21“.
- **Ursache:** Das Subinterface erwartet VLAN-Tag 21 statt 20.
- **Fix:** `encapsulation dot1Q 20` setzen.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0.20
-  encapsulation dot1Q 20
+ interface GigabitEthernet0/0.20
+  encapsulation dot1Q 21
```

## Ticket 4 (SW3)

- **Symptom:** H3 (10.10.10.13) erreicht weder H1 noch das Gateway.
- **So findest du es:** `show vlan brief` auf SW3 zeigt den Port von H3 in VLAN 20, die Adresse von H3 gehört aber zu VLAN 10.
- **Ursache:** Der Access-Port von H3 liegt in VLAN 20, die Adresse gehört aber zu VLAN 10.
- **Fix:** `switchport access vlan 10` am Port Gi1/1 setzen.
- **Eingebaut:**

```diff
- interface GigabitEthernet1/1
-  switchport mode access
-  switchport access vlan 10
+ interface GigabitEthernet1/1
+  switchport mode access
+  switchport access vlan 20
```

