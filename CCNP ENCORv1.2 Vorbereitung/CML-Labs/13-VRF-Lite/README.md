# Lab 13 – VRF-Lite mit überlappenden Adressen

**Dauer:** 75 min · **Niveau:** mittel · **Nodes:** 6× iosv

Zwei Kunden (RED, BLUE) teilen sich zwei Router und einen Link, nutzen aber dieselben IP-Bereiche. Mit VRF-Lite trennst du Routing-Tabellen, nutzt Subinterfaces als Trunk und OSPF pro VRF.

**Lernziele:** Nach diesem Lab kannst du …

- VRF-Lite mit überlappenden Adressen aufbauen.
- Pro VRF ein eigenes OSPF betreiben und die Tabellen getrennt prüfen.
- Erklären, wofür Route Distinguisher in MPLS-VPNs nötig sind und warum VRF-Lite ohne sie auskommt.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::2.2.a` | VRF | 26 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
 CR1 ─┐                              ┌─ CR2
      ├─ R1 ════ (Gi0/2.100 RED / .200 BLUE) ════ R2 ─┤
 CB1 ─┘                              └─ CB2
```
RED = CR1 ↔ CR2, BLUE = CB1 ↔ CB2.

| Link | Netz (in beiden VRFs identisch!) |
|---|---|
| R1 Gi0/0 – CR1 Gi0/0 (RED) | 10.1.1.0/30 (R1 .1, CR1 .2) |
| R1 Gi0/1 – CB1 Gi0/0 (BLUE) | 10.1.1.0/30 (R1 .1, CB1 .2) |
| R1 Gi0/2.100 / .200 – R2 Gi0/2.100 / .200 | 10.0.12.0/30 (R1 .1, R2 .2) je VRF |
| R2 Gi0/0 – CR2 Gi0/0 (RED) | 10.2.2.0/30 (R2 .1, CR2 .2) |
| R2 Gi0/1 – CB2 Gi0/0 (BLUE) | 10.2.2.0/30 (R2 .1, CB2 .2) |

Kunden-LANs: Site 1 = 192.168.1.0/24 (Lo100 auf CR1/CB1), Site 2 = 192.168.2.0/24 (Lo100 auf CR2/CB2), in RED und BLUE identisch.

## Teil A – Bauen

1. **VRFs anlegen.** Auf R1 und R2 `vrf definition RED`/`BLUE` mit `address-family ipv4`. Weise die Kunden-Interfaces (`vrf forwarding`) zu. Beachte: Die IP-Adresse wird beim Zuweisen gelöscht und muss neu gesetzt werden. Welche Routing-Tabelle zeigt `show ip route` ohne VRF?
2. **Trunk-Subinterfaces.** Auf dem Link R1–R2 je Subinterface `.100` (RED) und `.200` (BLUE) mit `encapsulation dot1Q`, `vrf forwarding`, IP `10.0.12.1/.2`. Warum dürfen beide Subinterfaces dieselbe IP-Adresse tragen?
3. **OSPF pro VRF.** `router ospf 1 vrf RED`, `router ospf 2 vrf BLUE` auf R1/R2, dazu OSPF auf den CEs (Prozess 1, Area 0). Prüfe `show ip route vrf RED ospf` und die Router-IDs (VRF-spezifisch!).
4. **Ende-zu-Ende.** `ping vrf RED 192.168.2.1 source Loopback100` von R1 aus bzw. von CR1 aus `ping 192.168.2.1 source Lo100`. Zeige, dass dieselben Netze in beiden VRFs existieren und sich nicht in die Quere kommen.
5. **Trennung beweisen.** Pinge aus VRF RED eine BLUE-only-Adresse. Erkläre das Ergebnis (`% No route`, VRF-Tabellen sind getrennt).
6. **Route-Leaking.** Erzeuge auf R1 eine globale Loopback 10.99.99.1/32 und lasse VRF RED sie erreichen: `ip route vrf RED 10.99.99.1 255.255.255.255 Loopback99 global` plus Rückroute. Welche Sicherheitsfolgen hat Leaking, und wie macht man es sauber (Route-Target-Import/Export bei MP-BGP, Firewall-Fusion)?
7. **Konzepte.** Unterschied VRF-Lite ↔ MPLS-VRF: RD (unterscheidet gleiche Präfixe in MP-BGP), RT (steuert Import/Export), MPLS-Label. Wann reicht VRF-Lite?

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Im Log steht `Address 10.1.1.1 overlaps with GigabitEthernet0/0`, BLUE-Site 1 (CB1) ist nicht erreichbar.

**Ticket 2:** RED läuft Ende zu Ende, BLUE hat zwischen R1 und R2 keine OSPF-Nachbarschaft.

**Ticket 3:** CB2 bildet keinen Nachbarn zu R2, die BLUE-Site 2 (192.168.2.0/24) fehlt in der Routing-Tabelle von R1.

**Ticket 4:** RED-Site 2 ist nicht erreichbar (192.168.2.0/24 fehlt in VRF RED auf R1), BLUE funktioniert.

## Verifikation

```
show vrf
show ip route vrf RED
show ip ospf 1 neighbor        ! Prozess pro VRF
show ip vrf interfaces
ping vrf RED 192.168.2.1 source Loopback100
```
Erwartet: In jeder VRF auf R1 eine OSPF-Route nach 192.168.2.0/24, Pings Ende-zu-Ende in RED und in BLUE.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Zwei VRFs haben dasselbe Präfix 192.168.1.0/24. Warum entsteht kein Konflikt?
<details><summary>Antwort</summary>

**Weil jede VRF ihre eigene Routing-Tabelle hat.** Die beiden Präfixe liegen in getrennten Tabellen und getrennten FIBs. Sie begegnen sich nie.

</details>

2. Wozu dient der Route Distinguisher, wenn VRF-Lite ohne ihn auskommt?
<details><summary>Antwort</summary>

**Für MP-BGP in MPLS-VPNs.** Dort transportiert ein einziger BGP-Prozess die Routen aller Kunden. Gleiche Präfixe müssen unterscheidbar sein: RD (64 Bit) plus Präfix ergibt eine eindeutige VPNv4-Adresse. VRF-Lite braucht das nicht, weil die Tabellen getrennt bleiben.

</details>

3. Ping aus VRF RED zeigt `Success rate 0`, aber `show ip route vrf RED` hat die Route. Warum?
<details><summary>Antwort</summary>

**Meist fehlt der Rückweg oder die Quelle liegt in der falschen VRF.** Prüfe, ob der Ping mit einer Quelle aus der VRF gesendet wird (`ping vrf RED … source …`), ob die Gegenseite eine Route zurück hat und ob ihr Interface in derselben VRF liegt.

</details>

## Prüfungsbezug

VRF-Lite ist lokal signifikant, keine Labels. RD macht Präfixe eindeutig (nur in MP-BGP), RT steuert Import/Export. `vrf forwarding` löscht die IP-Adresse. OSPF-Prozesse laufen pro VRF, Interfaces gehören genau einer VRF.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
