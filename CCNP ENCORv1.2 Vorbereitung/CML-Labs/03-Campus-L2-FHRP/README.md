# Lab 03 – Campus Layer 2, EtherChannel und HSRP

**Blueprint:** 3.1.a (Layer-2-Trunks), 3.1.b (EtherChannel), 3.1.c (RSTP/MST), 1.2/3.3.c (First-Hop-Redundanz, Access-Layer-Schutz)
**Deck-Tags:** `Ziel::3.1.a`, `Ziel::3.1.b`, `Ziel::3.1.c` · **Dauer:** ca. 75–90 min · **Nodes:** 4× IOSvL2, 2× IOSv als Hosts

## Topologie

```
     SW1 ═══(Po1)═══ SW2         Distribution (L3, HSRP)
      │ ╲             ╱ │
      │   ╲         ╱   │
     SW3             SW4         Access (L2)
      │               │
      H1 (VLAN10)     H2 (VLAN20)
```

| Link | Ports |
|---|---|
| SW1–SW2 | Gi0/0–0/1 (Gi0/0 ↔ Gi0/0, Gi0/1 ↔ Gi0/1) → Port-Channel 1 |
| SW1–SW3 / SW2–SW3 | SW1 Gi0/2 ↔ SW3 Gi0/0 / SW2 Gi0/2 ↔ SW3 Gi0/1 |
| SW1–SW4 / SW2–SW4 | SW1 Gi0/3 ↔ SW4 Gi0/0 / SW2 Gi0/3 ↔ SW4 Gi0/1 |
| SW3–H1 / SW4–H2 | Gi1/0 ↔ H1/H2 Gi0/0 |

| VLAN | Name | Subnetz | HSRP-VIP | SW1 | SW2 |
|---|---|---|---|---|---|
| 10 | USERS | 10.10.10.0/24 | .1 | .2 (Active) | .3 |
| 20 | SERVERS | 10.10.20.0/24 | .1 | .3 | .2 (Active) |

H1 (10.10.10.101) liegt in VLAN 10, H2 (10.10.20.102) in VLAN 20, Hosts nutzen die VIP als Gateway. Die Startkonfiguration enthält nur Hostnamen, IP-Adressen auf den Hosts und Rapid-PVST.

## Aufgaben

1. **VLANs.** Lege VLAN 10 (USERS) und 20 (SERVERS) auf allen vier Switches an. Setze die Access-Ports zu H1 (VLAN 10) und H2 (VLAN 20). Lege zusätzlich VLAN 999 „PARKING“ an und erkläre, wofür man es im Alltag nutzt (unbenutzte Ports, Native VLAN).
2. **Trunks.** Konfiguriere alle Inter-Switch-Links als **statische 802.1Q-Trunks** (`switchport mode trunk`, `switchport nonegotiate`), erlaubte VLANs nur 10 und 20, Native VLAN 999. Wozu dient das Native VLAN 999 und welchen Angriff erschwert es (VLAN Hopping per Double Tagging)?
3. **EtherChannel.** Bündele SW1–SW2 mit **LACP** (SW1 `active`, SW2 `passive`) zu Port-Channel 1 (Trunk). Verifiziere mit `show etherchannel summary`. Was passiert, wenn auf beiden Seiten `passive` steht? Was bei `on` gegen `active`?
4. **Rapid-PVST Root.** SW1 soll Root Bridge für VLAN 10, SW2 für VLAN 20 sein, jeweils als Secondary für das andere VLAN. Setze die Priorität mit `spanning-tree vlan X root primary/secondary` und prüfe, welcher Wert tatsächlich gesetzt wird. Welche Ports blockieren (Alternate) auf SW3 und SW4?
5. **Access-Schutz.** Aktiviere auf den Host-Ports **PortFast** und **BPDU Guard**. Teste: Hänge in CML einen zusätzlichen Switch an einen Host-Port (statt des Hosts) und beobachte `err-disabled` samt Log-Meldung. Setze `errdisable recovery cause bpduguard` mit 60 s Intervall.
6. **Root Guard / Loop Guard.** Wo setzt man **Root Guard** (Distribution → Access) und wo **Loop Guard** (Uplinks, nicht-designated Ports)? Konfiguriere Root Guard auf den Ports SW1/SW2 Gi0/2–0/3 und erkläre den Zustand `root-inconsistent`.
7. **SVIs und HSRP.** Lege auf SW1 und SW2 `ip routing` und die SVIs `vlan10`/`vlan20` an (SW1 .2, SW2 .3 in VLAN 10; umgekehrt in VLAN 20), HSRP Version 2 mit VIP .1, Priorität 110 für den jeweiligen Active-Router, `preempt`. Der Active-Router für ein VLAN soll **mit der STP-Root des VLANs übereinstimmen**. Warum ist das wichtig?
8. **Failover.** Starte auf H1 `ping 10.10.20.102 repeat 1000` und schalte SW1 Gi0/2 ab (`shutdown`). Wie lange bricht der Ping? Welche Rolle spielt HSRP, welche RSTP? Optional: `standby 10 track` bzw. `standby 10 timers msec 200 msec 750` verkürzt die Umschaltzeit.
9. **Fehlersuche.** Stelle auf SW3 Gi0/0 den Native-VLAN auf 1 (statt 999). Was meldet das Log (`%CDP-4-NATIVE_VLAN_MISMATCH`) und welche Auswirkung hat das auf STP (PVST+ Inconsistency)?

## Verifikation

```
show vlan brief
show interfaces trunk
show etherchannel summary
show spanning-tree vlan 10
show spanning-tree inconsistentports
show standby brief
show standby vlan 10
```

Erwartet: `Po1(SU)` mit zwei `P`-Ports; SW1 Root für VLAN 10, SW2 Root für VLAN 20; `show standby brief` zeigt SW1 `Active` für VLAN 10 und `Standby` für VLAN 20; H1 pingt H2.

## Lösungen

Siehe [`solutions/`](solutions/).

## Prüfungsbezug

LACP-Modus-Kombinationen (active/active, active/passive ok; passive/passive nie; on/on ok, on/active nie), Rapid-PVST-Port-Rollen und -Zustände, HSRP-Preempt-Default (aus!), HSRP-v2-Multicast 224.0.0.102, virtuelle MAC 0000.0C9F.Fxxx.
