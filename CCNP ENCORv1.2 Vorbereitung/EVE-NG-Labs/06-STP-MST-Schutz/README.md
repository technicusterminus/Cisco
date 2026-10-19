# Lab 06 – Spanning Tree, MST und Schutzfunktionen

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel bis schwer

Vier Switches im Dreiecksverbund plus „Rogue“-Switch: Rapid-PVST, Root-Platzierung und Lastverteilung, Umstieg auf MST, PortFast, BPDU Guard, Root Guard, Loop Guard und typische STP-Fehler.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.1.c` | RSTP, MST und Schutzfunktionen | 65 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| SW1 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW2 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW3 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW4 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW5 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **4.8 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **3.8 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| SW1 | Gi0/0 | SW2 | Gi0/0 |
| SW1 | Gi0/1 | SW3 | Gi0/0 |
| SW1 | Gi0/2 | SW4 | Gi0/0 |
| SW2 | Gi0/1 | SW3 | Gi0/1 |
| SW2 | Gi0/2 | SW4 | Gi0/1 |
| SW3 | Gi0/2 | SW4 | Gi0/2 |
| SW3 | Gi1/0 | H1 | Gi0/0 |
| SW4 | Gi1/0 | H2 | Gi0/0 |
| SW3 | Gi1/1 | SW5 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
        SW1 ───── SW2          Distribution (Root-Kandidaten)
        │ ╲     ╱ │
        │   ╲ ╱   │
        │   ╱ ╲   │
        SW3 ───── SW4          Access
        │         │
   H1 ──┤         └── H2      (beide VLAN 10)
   SW5 (Rogue, BPDU-Quelle) am Port Gi1/1 von SW3
```

| Link | Ports |
|---|---|
| SW1–SW2 | Gi0/0 ↔ Gi0/0 |
| SW1–SW3 | Gi0/1 ↔ Gi0/0 |
| SW1–SW4 | Gi0/2 ↔ Gi0/0 |
| SW2–SW3 | Gi0/1 ↔ Gi0/1 |
| SW2–SW4 | Gi0/2 ↔ Gi0/1 |
| SW3–SW4 | Gi0/2 ↔ Gi0/2 |
| H1 / H2 | SW3 Gi1/0 / SW4 Gi1/0 (VLAN 10) |
| SW5 | SW3 Gi1/1 ↔ SW5 Gi0/0 (SW5 ist ab Werk `shutdown`) |

VLANs 10 und 20 sind angelegt, die Inter-Switch-Links sind noch **nicht** als Trunks konfiguriert (Aufgabe 1). Hosts: H1 10.10.10.11, H2 10.10.10.12 (/24).

## Teil A – Bauen

1. **Trunks.** Alle sechs Inter-Switch-Links statische Trunks (`mode trunk`, `nonegotiate`, erlaubte VLANs 10,20, Native 99, VLAN 99 anlegen). Prüfe, dass H1 ↔ H2 pingen.
2. **Rapid-PVST lesen.** Auf SW3: `show spanning-tree vlan 10`. Wer ist Root (niedrigste Bridge-ID = Priorität + MAC)? Welche Ports sind Root, Designated, Alternate? Warum sind Alternate-Ports in RSTP sofort einsatzbereit?
3. **Root platzieren.** SW1 Root für VLAN 10, SW2 Root für VLAN 20 (jeweils Secondary für das andere) mit `spanning-tree vlan X root primary|secondary`. Welche Priorität wird gesetzt? Wie beeinflusst `spanning-tree cost` die Pfadwahl (Standardkosten Short-Metrik: 1 Gbit/s = 4, 100 Mbit/s = 19; Long-Metrik: 1 Gbit/s = 20000)?
4. **Umstieg auf MST.** `spanning-tree mode mst`, Region `ENCOR`, Revision 1, Instanz 1 = VLAN 10, Instanz 2 = VLAN 20 auf **allen** Switches. Prioritäten: Instanz 0 und 1 SW1 (4096), Instanz 2 SW2 (4096), jeweils der andere als Backup (8192). Warum sind Name, Revision **und** VLAN-Mapping Teil des Region-Digests, und was passiert bei Abweichung (Boundary-Port, alle VLANs hängen am IST)?
5. **Edge-Schutz.** Auf H1/H2-Ports und Gi1/1 (SW5): `portfast`, `bpduguard`. Aktiviere SW5 (`no shutdown`) mit niedriger Priorität und beobachte das Err-Disable. Dann zusätzlich `errdisable recovery cause bpduguard` mit Intervall 60 s. Wie unterscheidet sich **BPDU Filter** (still, gefährlich) von **BPDU Guard**?
6. **Root Guard.** Setze Root Guard auf den Distribution→Access-Ports (SW1 Gi0/1, Gi0/2, SW2 Gi0/1, Gi0/2). Erkläre den Zustand `root-inconsistent` und warum Root Guard keine Nachbarn blockiert, sondern nur Superior BPDUs.
7. **Loop Guard und UDLD.** Aktiviere Loop Guard auf den Access-Uplinks (`spanning-tree guard loop` oder global `spanning-tree loopguard default`) und `udld enable`/`udld aggressive`. Welcher Fehler (unidirektionale Verbindung, BPDU-Verlust) entsteht ohne sie?
8. **Konvergenz testen.** `ping 10.10.10.12 repeat 1000` von H1, dann Root-Link abschalten: Wie lange dauert der Ausfall bei Rapid-PVST/MST (Proposal/Agreement, `show spanning-tree summary`)?

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **3 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Alle Hosts erreichen sich, aber `show spanning-tree mst` auf SW4 meldet Boundary-Ports zur eigenen MST-Region; die Lastverteilung nach Instanz funktioniert nicht.

**Ticket 2:** Instanz 2 hat dieselbe Root wie Instanz 1 (SW1), die VLAN-Lastverteilung fehlt.

**Ticket 3:** Nachdem jemand an Gi1/1 einen kleinen Switch angeschlossen hat, wechselt die Root und das Netz flattert. SW3 zeigt eine neue Root über Gi1/1.

## Verifikation

```
show spanning-tree
show spanning-tree mst configuration
show spanning-tree mst 1
show spanning-tree inconsistentports
show spanning-tree summary
show errdisable recovery
show udld neighbors
```
Erwartet: SW1 Root für IST und Instanz 1, SW2 Root für Instanz 2, SW4/SW3 haben Alternate-Ports, keine `Boundary`-Ports, SW5 verursacht kein Root-Wechsel (BPDU Guard).

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Welcher Switch wird Root, wenn alle Prioritäten gleich sind?
<details><summary>Antwort</summary>

Der mit der niedrigsten MAC-Adresse (Bridge-ID = Priorität + MAC). Bei PVST+ steckt die VLAN-ID in der Extended System ID.

</details>

2. Ein Switch hat Port-Zustand `BKN*`. Was bedeutet das?
<details><summary>Antwort</summary>

`Broken`: Der Port ist durch Root Guard (`ROOT_Inc`), Loop Guard (`LOOP_Inc`) oder Type-/PVID-Inconsistency blockiert. Die Details zeigt `show spanning-tree inconsistentports`.

</details>

3. Warum PortFast **und** BPDU Guard?
<details><summary>Antwort</summary>

PortFast überspringt die Wartezeit am Edge-Port. BPDU Guard stellt sicher, dass dort kein Switch hängt, da PortFast sonst Loops erlauben würde.

</details>

## Prüfungsbezug

Rapid-PVST: eine Instanz pro VLAN, MST: pro Instanz gruppierte VLANs (nur eine PVST+-Instanz an der Boundary). Port-Rollen Root/Designated/Alternate/Backup, Zustände Discarding/Learning/Forwarding. Root Guard am Port Richtung Access, BPDU Guard am Edge, Loop Guard auf Non-Designated Ports. Default Pfadkosten: 1G=4 (short) bzw. 20000 (long), Priorität in 4096er-Schritten (+VLAN-ID bei PVST).

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/06-STP-MST-Schutz/`](../../CML-Labs/06-STP-MST-Schutz/).
