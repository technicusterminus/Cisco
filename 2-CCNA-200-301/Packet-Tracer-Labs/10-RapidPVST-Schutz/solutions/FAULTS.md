# Fehlerliste – Lab 10 – Rapid PVST+: Root Bridge, Port-Rollen und Schutzfunktionen

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW3)

- **Symptom:** Die Root Bridge ist nicht mehr SW1; SW2 meldet `ROOTGUARD_BLOCK` auf Fa0/2 und `show spanning-tree` zeigt Fa0/2 als `*ROOT_INCONS`.
- **So findest du es:** `show spanning-tree vlan 10` auf SW3 zeigt Priorität 0 plus VLAN-ID. SW2 meldet im Log `ROOTGUARD_BLOCK`.
- **Ursache:** SW3 hat die Priorität 0 und gewinnt die Root-Wahl; Root Guard auf SW2 blockiert den Port.
- **Fix:** Priorität auf SW3 zurücknehmen (`no spanning-tree vlan 1,10 priority`).
- **Eingebaut:**

```diff
- spanning-tree mode rapid-pvst
+ spanning-tree mode rapid-pvst
+ spanning-tree vlan 1,10 priority 0
```

## Ticket 2 (SW2)

- **Symptom:** Nach einem Linkausfall dauert die Umschaltung 30–50 Sekunden; `show spanning-tree` auf SW2 zeigt `Spanning tree enabled protocol ieee`.
- **So findest du es:** `show spanning-tree` auf SW2 meldet „protocol ieee“ statt „rstp“.
- **Ursache:** SW2 läuft in klassischem PVST+ statt Rapid PVST+: Rückfall auf Timer-basierte Konvergenz.
- **Fix:** `spanning-tree mode rapid-pvst`.
- **Eingebaut:**

```diff
- spanning-tree mode rapid-pvst
+ spanning-tree mode pvst
```

## Ticket 3 (SW3)

- **Symptom:** PC2 hat nach dem Einstecken eine längere Wartezeit bis zum Link-Status Forwarding als PC1; `show spanning-tree interface fa0/10 detail` zeigt Edge `no`.
- **So findest du es:** `show spanning-tree interface fa0/10 detail` auf SW3 zeigt, dass PortFast fehlt (kein Edge-Port).
- **Ursache:** Auf SW3 Fa0/10 fehlt PortFast, der Port wird nicht als Edge-Port behandelt.
- **Fix:** `spanning-tree portfast` am Port.
- **Eingebaut:**

```diff
-  spanning-tree portfast
```

## Ticket 4 (SW3)

- **Symptom:** Der Verkehr von PC2 in VLAN 10 nimmt den Umweg über SW2 statt des direkten Links zu SW1; der Root Port von SW3 für VLAN 10 ist Fa0/2.
- **So findest du es:** `show spanning-tree vlan 10` auf SW3 zeigt an Fa0/1 Kosten 4000. `show running-config interface fa0/1` enthält `spanning-tree vlan 10 cost 4000`.
- **Ursache:** Ein manueller Kostenwert (4000) auf SW3 Fa0/1 macht den direkten Link unattraktiv.
- **Fix:** `no spanning-tree vlan 10 cost` auf Fa0/1.
- **Eingebaut:**

```diff
- interface range FastEthernet0/1 - 2
-  switchport mode trunk
+ interface range FastEthernet0/1 - 2
+  switchport mode trunk
+ interface FastEthernet0/1
+  spanning-tree vlan 10 cost 4000
```

