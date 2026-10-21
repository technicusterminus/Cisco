# Lab 06 – Spanning Tree, MST und Schutzfunktionen

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel bis schwer

Vier Switches im Dreiecksverbund plus „Rogue“-Switch: Rapid-PVST, Root-Platzierung und Lastverteilung, Umstieg auf MST, PortFast, BPDU Guard, Root Guard, Loop Guard und typische STP-Fehler.

**Lernziele:** Nach diesem Lab kannst du …

- Die STP-Root-Wahl vorhersagen und gezielt steuern.
- MST mit Region, Instanzen und Prioritäten konfigurieren.
- PortFast, BPDU Guard und Root Guard sinnvoll einsetzen.

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
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Trunks.** Lege VLAN 99 an. Mache alle sechs Links zwischen den Switches zu festen Trunks (`mode trunk`, `nonegotiate`) mit den erlaubten VLANs 10 und 20 und Native VLAN 99.
   - **Prüfen:** H1 pingt H2.
2. **Rapid-PVST lesen.** Führe auf SW3 `show spanning-tree vlan 10` aus.
   - **Prüfen:** Finde die Root (niedrigste Bridge-ID) und die Rolle jedes Ports: Root, Designated oder Alternate.
   - **Denkfrage:** Warum kann ein Alternate-Port in RSTP sofort übernehmen?
3. **Root festlegen.** Mache SW1 zur Root für VLAN 10 und SW2 zur Root für VLAN 20, jeweils mit dem anderen als Ersatz: `spanning-tree vlan X root primary` bzw. `secondary`.
   - **Prüfen:** `show spanning-tree root` zeigt für VLAN 10 SW1, für VLAN 20 SW2.
   - **Denkfrage:** Welche Priorität setzen `primary` und `secondary`? Wie kannst du mit `spanning-tree cost` die Pfadwahl beeinflussen?
4. **Auf MST umstellen.** Setze auf allen Switches `spanning-tree mode mst` mit Region `ENCOR`, Revision 1, Instanz 1 = VLAN 10, Instanz 2 = VLAN 20. Prioritäten: Instanz 0 und 1 SW1 4096, Instanz 2 SW2 4096, der jeweils andere 8192.
   - **Prüfen:** `show spanning-tree mst configuration` ist auf allen Switches gleich. `show spanning-tree mst` zeigt keine Boundary-Ports.
   - **Denkfrage:** Warum müssen Name, Revision und VLAN-Zuordnung überall gleich sein, und was passiert sonst?
5. **Edge-Ports schützen.** Setze an den Ports von H1, H2 und an Gi1/1 (SW5) `spanning-tree portfast` und `spanning-tree bpduguard enable`. Schalte SW5 mit `no shutdown` ein.
   - **Prüfen:** Der Port zu SW5 geht in den Zustand err-disabled, die Root bleibt SW1. Danach `errdisable recovery cause bpduguard` mit `errdisable recovery interval 60` setzen.
   - **Denkfrage:** Was ist der Unterschied zwischen BPDU Guard und BPDU Filter?
6. **Root Guard.** Setze `spanning-tree guard root` an den Ports der Distribution-Switches Richtung Access (SW1 Gi0/1, Gi0/2, SW2 Gi0/1, Gi0/2).
   - **Prüfen:** `show spanning-tree inconsistentports` ist leer, solange niemand eine bessere BPDU schickt.
   - **Denkfrage:** Was macht Root Guard, wenn doch eine bessere BPDU kommt, und warum blockiert er normale Nachbarn nicht?
7. **Loop Guard und UDLD.** Aktiviere Loop Guard auf den Uplinks der Access-Switches (`spanning-tree guard loop` oder global `spanning-tree loopguard default`) und `udld aggressive`.
   - **Denkfrage:** Welcher Fehler entsteht ohne die beiden, wenn ein Link nur noch in eine Richtung überträgt?
8. **Konvergenz messen.** Starte auf H1 `ping 10.10.10.12 repeat 1000` und schalte den Link zur Root ab.
   - **Prüfen:** Zähle die verlorenen Pings. Bei Rapid-PVST und MST sind es nur wenige.

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** RSTP hält den Alternate-Port als fertigen Ersatz für den Root-Port bereit. Fällt der Root-Port aus, wechselt der Alternate-Port direkt auf Forwarding, ohne Listening und Learning.
- **Zu 3:** `primary` setzt 24576 oder, falls nötig, einen Wert 4096 unter der aktuellen Root. `secondary` setzt 28672. Mit `spanning-tree cost` machst du einen Port teurer oder günstiger. Der Switch nimmt den Weg mit den geringsten Gesamtkosten zur Root (Standard kurz: 1 Gbit/s = 4, 100 Mbit/s = 19, lang: 1 Gbit/s = 20 000).
- **Zu 4:** Aus Name, Revision und VLAN-Zuordnung berechnet MST einen Digest, an dem sich Switches derselben Region erkennen. Weicht ein Wert ab, bildet der Switch eine eigene Region. Die Ports dazwischen werden Boundary-Ports, und dort laufen alle VLANs über die IST. Die Lastverteilung nach Instanz geht verloren.
- **Zu 5:** BPDU Guard schaltet den Port ab, sobald eine BPDU ankommt. Das ist laut und sicher. BPDU Filter am Interface unterdrückt BPDUs einfach. Hängt dort ein Switch, merkt STP nichts, und es kann eine Schleife entstehen.
- **Zu 6:** Kommt eine bessere BPDU, setzt Root Guard den Port auf root-inconsistent und blockiert ihn. Hören die besseren BPDUs auf, gibt er den Port von selbst wieder frei. Normale Nachbarn senden schlechtere BPDUs, die lässt Root Guard durch.
- **Zu 7:** Kommen auf einem Port keine BPDUs mehr an, hält STP den Weg für frei und schaltet einen blockierten Port auf Forwarding. Die Folge ist eine Schleife. Loop Guard setzt den Port in diesem Fall auf loop-inconsistent. UDLD erkennt die einseitige Verbindung und schaltet den Port ab.

</details>

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

| Befehl | Das solltest du sehen |
|---|---|
| `show spanning-tree mst` | SW1 Root für Instanz 0 und 1, SW2 Root für Instanz 2 |
| `show spanning-tree mst 1` auf SW3 und SW4 | mindestens ein Alternate-Port, keine Boundary-Ports |
| `show interfaces status err-disabled` auf SW3 | der Port zu SW5, ausgelöst durch BPDU Guard |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Welcher Switch wird Root, wenn alle Prioritäten gleich sind?
<details><summary>Antwort</summary>

**Der Switch mit der niedrigsten MAC-Adresse.** Die Bridge-ID besteht aus Priorität und MAC. Bei gleicher Priorität entscheidet die MAC. Bei PVST+ ist die VLAN-ID in der Priorität enthalten (Extended System ID).

</details>

2. Ein Switch hat Port-Zustand `BKN*`. Was bedeutet das?
<details><summary>Antwort</summary>

**Der Port ist durch eine Schutzfunktion blockiert (Broken).** Ursachen sind Root Guard (`ROOT_Inc`), Loop Guard (`LOOP_Inc`) oder eine Type- bzw. PVID-Inkonsistenz. Welche es ist, zeigt `show spanning-tree inconsistentports`.

</details>

3. Warum PortFast **und** BPDU Guard?
<details><summary>Antwort</summary>

**PortFast spart die Wartezeit, BPDU Guard sichert sie ab.** PortFast schaltet einen Edge-Port sofort auf Forwarding. Hängt dort doch ein Switch, könnte eine Schleife entstehen. BPDU Guard schaltet den Port ab, sobald eine BPDU ankommt.

</details>

## Prüfungsbezug
- Rapid-PVST hat eine Instanz pro VLAN, MST fasst VLANs zu Instanzen zusammen.
- Port-Rollen: Root, Designated, Alternate, Backup. Zustände: Discarding, Learning, Forwarding.
- Root Guard an Ports Richtung Access, BPDU Guard an Edge-Ports, Loop Guard an blockierenden Ports.
- Standardkosten 1 Gbit/s: 4 (kurz) bzw. 20 000 (lang). Priorität in Schritten von 4096, bei PVST plus VLAN-ID.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/06-STP-MST-Schutz/`](../../CML-Labs/06-STP-MST-Schutz/).
