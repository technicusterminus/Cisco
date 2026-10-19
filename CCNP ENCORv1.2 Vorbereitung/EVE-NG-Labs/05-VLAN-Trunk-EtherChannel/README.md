# Lab 05 – VLANs, Trunks und EtherChannel

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** leicht bis mittel

Drei Switches, Router-on-a-Stick und drei Hosts: 802.1Q-Trunks (Native VLAN, Allowed VLANs, DTP, VTP) und EtherChannel mit LACP, PAgP und statischem Modus.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.1.a` | 802.1Q und Trunks | 31 |
| `Ziel::3.1.b` | EtherChannel | 34 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| SW1 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW2 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW3 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| R1 | Cisco vIOS Router |  | 512 |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H3 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **4.2 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.8 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| SW1 | Gi0/0 | SW2 | Gi0/0 |
| SW1 | Gi0/1 | SW2 | Gi0/1 |
| SW1 | Gi0/2 | SW3 | Gi0/0 |
| SW1 | Gi0/3 | SW3 | Gi0/1 |
| SW1 | Gi1/0 | R1 | Gi0/0 |
| SW2 | Gi1/0 | H1 | Gi0/0 |
| SW3 | Gi1/0 | H2 | Gi0/0 |
| SW3 | Gi1/1 | H3 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
                      ┌── Po1 (LACP, 2 Links) ── SW2 ── H1 (VLAN10)
 R1 ══trunk══ SW1 ════┤
                      └── Po2 (PAgP, 2 Links) ── SW3 ──┬── H2 (VLAN20)
                                                       └── H3 (VLAN10)
```

| VLAN | Name | Subnetz | Gateway (R1 Subinterface) |
|---|---|---|---|
| 10 | USERS | 10.10.10.0/24 | .1 (`Gi0/0.10`) |
| 20 | SERVERS | 10.10.20.0/24 | .1 (`Gi0/0.20`) |
| 99 | NATIVE | – | ungenutzt |

H1 10.10.10.11 (SW2 Gi1/0), H2 10.10.20.12 (SW3 Gi1/0), H3 10.10.10.13 (SW3 Gi1/1). Verkabelung: SW1 Gi0/0–0/1 ↔ SW2 Gi0/0–0/1, SW1 Gi0/2–0/3 ↔ SW3 Gi0/0–0/1, SW1 Gi1/0 ↔ R1 Gi0/0.

## Teil A – Bauen

1. **VLANs.** Lege VLAN 10 (USERS), 20 (SERVERS) und 99 (NATIVE) auf allen Switches an. Setze **VTP auf `transparent`** (`vtp mode transparent`). Warum ist VTP Server/Client auf einer neuen Switch mit höherer Revision gefährlich?
2. **Trunk zum Router.** SW1 Gi1/0 als statischer Trunk (`switchport mode trunk`, `nonegotiate`), Native VLAN 99, erlaubte VLANs 10 und 20. R1 bekommt Subinterfaces `Gi0/0.10` und `.20` (`encapsulation dot1Q`, `ip address`). Prüfe, dass H1 sein Gateway erreicht.
3. **EtherChannel LACP.** SW1–SW2 als **Po1 mit LACP** (SW1 `active`, SW2 `passive`), als Trunk (10, 20, Native 99). Prüfe `show etherchannel summary` auf Flags `SU`/`P`. Welche Modus-Kombinationen bilden einen Channel und welche nicht (active/passive, passive/passive, on/active)?
4. **EtherChannel PAgP.** SW1–SW3 als **Po2 mit PAgP** (SW1 `desirable`, SW3 `auto`). Vergleiche PAgP und LACP (Cisco-proprietär vs. IEEE 802.3ad, Mode-Namen, max. Ports pro Channel).
5. **Hosts.** Ports H1 (VLAN 10), H2 (VLAN 20), H3 (VLAN 10) als Access, `spanning-tree portfast`. Teste: H1 → H3 (gleiches VLAN, nur Layer 2), H1 → H2 (inter-VLAN via R1).
6. **Lastverteilung.** Setze `port-channel load-balance src-dst-ip` und prüfe mit `show etherchannel load-balance`. Warum nutzt ein einzelner Flow nur einen Link? Erkläre Hash-Berechnung (Quell-/Ziel-IP/MAC/Port).
7. **Native-VLAN-Trick.** Stelle bewusst auf SW3 Po2 Native VLAN 1 ein und lies das Log (`%CDP-4-NATIVE_VLAN_MISMATCH`). Welche Angriffsfläche (VLAN Hopping per Double Tagging) schließt ein ungenutztes Native VLAN?
8. **Pruning.** Beschränke die Trunks auf nur die tatsächlich benötigten VLANs und prüfe `show interfaces trunk` (Spalten *allowed*, *active*, *forwarding*).

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Po1 kommt nicht hoch: Auf SW1 sind die Ports `s` (suspended), H1 hat keine Verbindung.

**Ticket 2:** H2 (VLAN 20) hat weder Gateway noch Verbindung, H3 (VLAN 10) funktioniert.

**Ticket 3:** Alle Hosts in VLAN 20 erreichen ihr Gateway 10.10.20.1 nicht, VLAN 10 ist in Ordnung.

**Ticket 4:** H3 (10.10.10.13) erreicht weder H1 noch das Gateway.

## Verifikation

```
show vlan brief
show interfaces trunk
show etherchannel summary
show etherchannel load-balance
show lacp neighbor
show pagp neighbor
show vtp status
```
Erwartet: `Po1(SU)` mit `Gi0/0(P) Gi0/1(P)`, `Po2(SU)` mit PAgP, alle drei Hosts pingen ihr Gateway, H1 pingt H2 über R1.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Zwei Switches stehen auf `dynamic auto`. Entsteht ein Trunk?
<details><summary>Antwort</summary>

Nein: Beide warten passiv, Ergebnis ist Access. Mindestens eine Seite muss `desirable` oder `trunk` sein.

</details>

2. Ein Port ist in einem Channel gelistet, aber als `s` (suspended) markiert. Typische Ursache?
<details><summary>Antwort</summary>

Mismatch von Parametern oder Modi zur Gegenseite (z. B. `on` gegen `active`, andere VLAN-Liste, Speed/Duplex), sodass der Port nicht gebündelt wird.

</details>

3. Wozu `switchport nonegotiate`?
<details><summary>Antwort</summary>

Schaltet DTP-Frames ab: Verhindert, dass ein Angreifer einen Trunk aushandelt. Setzt voraus, dass der Port statisch auf `access` oder `trunk` steht.

</details>

## Prüfungsbezug

LACP: active+active/passive bildet, passive+passive nicht. PAgP: desirable+desirable/auto. `on` verhandelt nicht und passt nur zu `on`. Parameter (Speed, Duplex, Trunk, Native/Allowed VLANs) müssen auf allen Mitgliedsports gleich sein. DTP: `dynamic auto`+`auto` ergibt Access, `desirable` zieht einen Trunk hoch; `switchport nonegotiate` schaltet DTP ab.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/05-VLAN-Trunk-EtherChannel/`](../../CML-Labs/05-VLAN-Trunk-EtherChannel/).
