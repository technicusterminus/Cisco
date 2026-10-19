# Fehlerliste – Lab 23 – Capstone: Campus und Edge, Fehlersuche im Gesamtnetz

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW1)

- **Symptom:** H20 erreicht seinen Gateway nicht, H10 schon. Von R1 aus ist 10.10.20.12 nicht erreichbar.
- **Ursache:** Auf dem Trunk SW1 Gi0/0 (zum HSRP-Active R1) ist nur VLAN 10 erlaubt: Das VLAN 20 erreicht R1 nicht.
- **Fix:** `switchport trunk allowed vlan 10,20` auf SW1 Gi0/0 (oder `add 20`).
- **Eingebaut:**

```diff
- interface FastEthernet0/1
-  switchport mode trunk
-  switchport nonegotiate
-  switchport trunk allowed vlan 10,20
+ interface FastEthernet0/1
+  switchport mode trunk
+  switchport nonegotiate
+  switchport trunk allowed vlan 10
```

## Ticket 2 (R2)

- **Symptom:** Nach dem Reparieren des Trunks melden in VLAN 10 beide Router `Active`. `show standby brief` auf R1 und R2 zeigt jeweils `Active` und keinen Standby-Partner; Hosts erhalten ARP-Antworten verschiedener Router.
- **Ursache:** R2 verwendet auf dem Subinterface .10 HSRP Version 1, R1 Version 2: die Router sprechen unterschiedliche Multicast-Adressen (224.0.0.2 / 224.0.0.102) und sehen sich nicht.
- **Fix:** `standby version 2` auf R2 `Gi0/0.10` ergänzen.
- **Eingebaut:**

```diff
-  standby version 2
-  standby 10 ip 10.10.10.1
+  standby 10 ip 10.10.10.1
```

## Ticket 3 (EDGE)

- **Symptom:** Alles funktioniert, aber beim Test (Abschalten von R1) verlieren alle Hosts das Internet, obwohl R2 HSRP Active wird. `show ip ospf neighbor` auf EDGE zeigt nur R1.
- **Ursache:** EDGE belässt Gi0/1 (zu R2) passiv: Es gibt keine OSPF-Nachbarschaft zu R2 und damit keinen Rückweg über R2.
- **Fix:** `no passive-interface GigabitEthernet0/1` unter `router ospf 1` auf EDGE.
- **Eingebaut:**

```diff
-  no passive-interface GigabitEthernet0/1
```

## Ticket 4 (EDGE)

- **Symptom:** H10 erreicht 8.8.8.8, H20 nicht, obwohl das Routing stimmt. `show ip nat translations` enthält nur Einträge aus 10.10.10.x.
- **Ursache:** Die NAT-ACL erlaubt nur 10.10.10.0/24: Pakete aus VLAN 20 werden nicht übersetzt und mit privater Quelladresse verworfen.
- **Fix:** ACL auf `10.10.0.0 0.0.255.255` (oder zweite Zeile für VLAN 20).
- **Eingebaut:**

```diff
- access-list 1 permit 10.10.0.0 0.0.255.255
+ access-list 1 permit 10.10.10.0 0.0.0.255
```

## Ticket 5 (R1)

- **Symptom:** H20 kann H10 anpingen, obwohl die Segmente getrennt sein sollen. `show access-lists` zeigt keine Treffer auf der deny-Zeile.
- **Ursache:** Die ACL wird von oben nach unten geprüft: `permit ip any any` steht vor dem `deny`, die deny-Zeile wird nie erreicht.
- **Fix:** Reihenfolge ändern (ACL entfernen und mit `deny` zuerst neu anlegen, oder Sequenznummern nutzen).
- **Eingebaut:**

```diff
-  deny ip 10.10.20.0 0.0.0.255 10.10.10.0 0.0.0.255
-  permit ip any any
+  permit ip any any
+  deny ip 10.10.20.0 0.0.0.255 10.10.10.0 0.0.0.255
```

## Ticket 6 (SW2)

- **Symptom:** `show spanning-tree root` zeigt für VLAN 10 und 20 SW2 als Root, Design verlangt SW1. Der Verkehr der Hosts nimmt einen Umweg, SW1 hat `Root port Po1`.
- **Ursache:** SW2 hat Priorität 0 (statt 61440) und gewinnt die Root-Wahl im Access-Bereich: Das Spanning Tree weicht vom Design ab.
- **Fix:** Priorität auf 61440 zurücksetzen (und per `spanning-tree vlan 10,20 root primary` oder Root Guard schützen).
- **Eingebaut:**

```diff
- spanning-tree vlan 10,20 priority 61440
+ spanning-tree vlan 10,20 priority 0
```

## Ticket 7 (SW2)

- **Symptom:** Po1 bündelt nicht: `show etherchannel summary` zeigt auf SW1 `(s)`/`(I)`-Ports, die Verbindung zu H10 und H20 ist unzuverlässig oder fällt ganz aus.
- **Ursache:** SW1 verhandelt per LACP (`active`), SW2 steht auf `on` und sendet keine LACPDUs: Die Seiten finden nicht zusammen.
- **Fix:** `channel-group 1 mode passive` (oder `active`) auf SW2, beide Seiten LACP.
- **Eingebaut:**

```diff
-  channel-group 1 mode passive
+  channel-group 1 mode on
```

## Ticket 8 (R2)

- **Symptom:** `show ntp status` auf R2: `Clock is unsynchronized`, R1 ist synchron. `show ntp associations` zeigt Reach 0.
- **Ursache:** Tippfehler in der NTP-Server-Adresse (…33 statt …3).
- **Fix:** `ntp server 10.255.0.3` auf R2.
- **Eingebaut:**

```diff
- ntp server 10.255.0.3
+ ntp server 10.255.0.33
```

## Ticket 9 (R2)

- **Symptom:** SSH von R1 auf R2 wird abgewiesen (`Connection refused by remote host`), Telnet dagegen geht.
- **Ursache:** `transport input telnet` erlaubt auf den vty-Lines kein SSH, und Telnet überträgt Zugangsdaten im Klartext.
- **Fix:** `transport input ssh` auf R2 `line vty 0 4`.
- **Eingebaut:**

```diff
-  login local
-  transport input ssh
+  login local
+  transport input telnet
```

## Ticket 10 (EDGE)

- **Symptom:** H10/H20 erreichen 8.8.8.8 nicht. EDGE erreicht den ISP, R1 und R2 haben aber keine Default-Route (`show ip route 0.0.0.0` → `Network not in table`).
- **Ursache:** EDGE gibt die statische Default-Route nicht per OSPF weiter: `default-information originate` fehlt.
- **Fix:** `default-information originate` unter `router ospf 1` auf EDGE.
- **Eingebaut:**

```diff
-  default-information originate
```

