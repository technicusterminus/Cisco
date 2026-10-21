# Fehlerliste – Lab 13 – VRF-Lite mit überlappenden Adressen

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Im Log steht `Address 10.1.1.1 overlaps with GigabitEthernet0/0`, BLUE-Site 1 (CB1) ist nicht erreichbar.
- **So findest du es:** Die Log-Meldung „overlaps with GigabitEthernet0/0“ zeigt den Konflikt. `show ip vrf interfaces` listet das BLUE-Interface unter RED.
- **Ursache:** Das BLUE-Interface wurde der VRF RED zugewiesen; die gleiche IP kollidiert dort mit Gi0/0.
- **Fix:** `vrf forwarding BLUE` setzen und IP neu vergeben.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  vrf forwarding BLUE
+ interface GigabitEthernet0/1
+  vrf forwarding RED
```

## Ticket 2 (R2)

- **Symptom:** RED läuft Ende zu Ende, BLUE hat zwischen R1 und R2 keine OSPF-Nachbarschaft.
- **So findest du es:** `show ip ospf vrf BLUE neighbor` auf R2 ist leer. `show interfaces` am BLUE-Subinterface zeigt eine andere VLAN-ID als auf R1.
- **Ursache:** VLAN-Tag des BLUE-Subinterfaces ist 201 statt 200: R1 und R2 sprechen nicht im selben VLAN.
- **Fix:** Tag auf 200 korrigieren.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/2.200
-  encapsulation dot1Q 200
+ interface GigabitEthernet0/2.200
+  encapsulation dot1Q 201
```

## Ticket 3 (R2)

- **Symptom:** CB2 bildet keinen Nachbarn zu R2, die BLUE-Site 2 (192.168.2.0/24) fehlt in der Routing-Tabelle von R1.
- **So findest du es:** `show ip ospf 2 interface brief` auf R2 listet Gi0/1 nicht. Das `network`-Statement für 10.2.2.0/30 fehlt.
- **Ursache:** Auf R2 fehlt in OSPF 2 (VRF BLUE) das Netz zum Kunden: Das Interface Gi0/1 nimmt nicht an OSPF teil.
- **Fix:** Netzwerk-Statement für 10.2.2.0/30 ergänzen.
- **Eingebaut:**

```diff
- router ospf 2 vrf BLUE
-  router-id 2.2.2.2
-  network 10.2.2.0 0.0.0.3 area 0
+ router ospf 2 vrf BLUE
+  router-id 2.2.2.2
```

## Ticket 4 (CR2)

- **Symptom:** RED-Site 2 ist nicht erreichbar (192.168.2.0/24 fehlt in VRF RED auf R1), BLUE funktioniert.
- **So findest du es:** `show ip route vrf RED` auf R1 hat 192.168.2.0/24 nicht. `show ip ospf interface brief` auf CR2 listet die Loopback nicht, weil das `network`-Statement ein anderes Netz nennt.
- **Ursache:** Die Loopback-LAN von CR2 wird in OSPF nicht angekündigt (falsches Netz).
- **Fix:** Netzwerk-Statement auf 192.168.2.0 korrigieren.
- **Eingebaut:**

```diff
- network 192.168.2.0 0.0.0.255 area 0
+ network 192.168.22.0 0.0.0.255 area 0
```

