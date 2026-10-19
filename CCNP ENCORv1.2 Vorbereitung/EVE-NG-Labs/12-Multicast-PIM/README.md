# Lab 12 – Multicast mit IGMP und PIM Sparse Mode

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel bis schwer

Multicast-Verteilung über ein Routernetz: IGMP, PIM-SM mit statischem RP, Auto-RP/BSR im Vergleich, SSM, RPF-Check und typische Fehler. Quelle und Empfänger sind IOS-Hosts.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.3.d` | Multicast-Verfahren | 46 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| R4 | Cisco vIOS Router |  | 512 |
| SRC | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| REC1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| REC2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **3.5 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R2 | Gi0/1 | R3 | Gi0/0 |
| R2 | Gi0/2 | R4 | Gi0/0 |
| R1 | Gi0/1 | SRC | Gi0/0 |
| R3 | Gi0/1 | REC1 | Gi0/0 |
| R4 | Gi0/1 | REC2 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
  SRC ── R1 ──── R2 (RP, Lo0 10.255.0.2) ──── R3 ── REC1
        .1 Gi0/0   │  Gi0/1      Gi0/0
                   └── Gi0/2 ── R4 ── REC2
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R2 Gi0/1 – R3 Gi0/0 | 10.0.23.0/30 (.1/.2) |
| R2 Gi0/2 – R4 Gi0/0 | 10.0.24.0/30 (.1/.2) |
| R1 Gi0/1 – SRC | 192.168.1.0/24 (R1 .1, SRC .10) |
| R3 Gi0/1 – REC1 | 192.168.3.0/24 (R3 .1, REC1 .10) |
| R4 Gi0/1 – REC2 | 192.168.4.0/24 (R4 .1, REC2 .10) |

Loopbacks: R1 10.255.0.1, R2 10.255.0.2 (RP), R3 10.255.0.3, R4 10.255.0.4 (jeweils /32). OSPF 1 (Area 0) als Unicast-Underlay ist vorhanden. Multicast-Gruppe für Tests: **239.1.1.1**.

## Teil A – Bauen

1. **Multicast aktivieren.** Auf allen Routern `ip multicast-routing`, auf allen Interfaces (inkl. Loopback des RP und LANs) `ip pim sparse-mode`. Prüfe `show ip pim neighbor`.
2. **Statischer RP.** `ip pim rp-address 10.255.0.2` auf allen Routern. Prüfe `show ip pim rp mapping`. Warum ist der RP eine Loopback-Adresse? Was passiert, wenn der RP ausfällt (Redundanz: Anycast-RP/MSDP, Phantom-RP)?
3. **Empfänger anmelden.** Auf REC1 und REC2: `interface Gi0/0` → `ip igmp join-group 239.1.1.1`. Prüfe `show ip igmp groups` auf R3/R4 und `show ip mroute 239.1.1.1` auf dem RP: Wo entsteht `(*,G)`? Welche Rolle spielt der IGMP-Querier?
4. **Quelle starten.** Auf SRC: `ping 239.1.1.1 repeat 100`. Beide Empfänger müssen Echo-Replies senden (die Antwort geht Unicast zurück). Beobachte auf R1 die PIM-Register-Nachricht, auf R2 `(S,G)` und beim ersten Empfänger-Router den Wechsel auf den Shortest Path Tree (`show ip mroute`, Flags `S`, `J`, `T`).
5. **RPF-Check.** Erkläre den Reverse Path Forwarding Check. Erzeuge ihn gezielt zu Fall, indem du auf R3 eine Route zur Quelle (192.168.1.0/24) über das falsche Interface setzt, und lies `show ip rpf 192.168.1.10` und `debug ip mpacket` (kurz). Was ist die Ausgabe `RPF failed`?
6. **SPT-Schwelle.** Setze auf R3 `ip pim spt-threshold infinity` und beobachte, dass der Verkehr beim RP-Tree bleibt. Wann ist das sinnvoll?
7. **Auto-RP oder BSR.** Ersetze den statischen RP durch **BSR** (R2 `ip pim bsr-candidate Loopback0`, `ip pim rp-candidate Loopback0 group-list 10`), prüfe die Zuordnung auf R3. Vergleiche Auto-RP (Cisco, Dense-Mode-Fallback, 224.0.1.39/40) mit BSR (offen, Standard).
8. **SSM.** `ip pim ssm default` (232.0.0.0/8) und `ip igmp version 3` am Empfänger, `ip igmp join-group 232.1.1.1 source 192.168.1.10`. Warum braucht SSM keinen RP?

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** R3 hat keinen PIM-Nachbarn zu R2; REC1 bekommt keine Pakete, REC2 funktioniert.

**Ticket 2:** REC2 empfängt keine Pakete, `show ip pim rp mapping` auf R4 zeigt einen anderen RP als auf den übrigen Routern.

**Ticket 3:** Weder REC1 noch REC2 empfangen etwas, obwohl alle Join-Zustände stehen. Auf R1 gibt es keine `(S,G)`-Einträge.

**Ticket 4:** Der RP zeigt `(*,G)`-Einträge nicht und Multicast wird auf R2 nicht weitergeleitet.

## Verifikation

```
show ip pim neighbor
show ip pim rp mapping
show ip igmp groups
show ip mroute [239.1.1.1]
show ip rpf 192.168.1.10
show ip mfib / show ip multicast
```
Erwartet: R2 hat `(*, 239.1.1.1)` mit RP = lokal und eine `(192.168.1.10, 239.1.1.1)`-Zeile; REC1 und REC2 antworten auf Ping.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Welche MAC-Adresse gehört zur Gruppe 239.1.1.1?
<details><summary>Antwort</summary>

01-00-5E-01-01-01: Die 23 niedrigsten Bits der IP werden in 01-00-5E-0x übernommen (die oberen 5 Bits der Gruppe gehen verloren).

</details>

2. Warum sieht ein Empfänger-Router nach dem ersten Datenpaket `(S,G)` mit Flag `T`?
<details><summary>Antwort</summary>

Er hat auf den Shortest Path Tree zur Quelle gewechselt und leitet jetzt auf dem direkten Weg weiter.

</details>

3. Was löst ein `RPF failed` aus?
<details><summary>Antwort</summary>

Das Paket kommt nicht auf dem Interface an, das laut Unicast-Routing der Rückweg zur Quelle ist. Mögliche Ursachen: asymmetrisches Routing, fehlende Route, falsches statisches `mroute`.

</details>

## Prüfungsbezug

Multicast-Bereiche: 224.0.0.0/24 lokal, 232/8 SSM, 239/8 administrativ. PIM-SM: Shared Tree `(*,G)` zum RP, Quellbaum `(S,G)`, Register-/Join-Nachrichten, RPF-Check am Eingang. IGMPv2 (Querier, General Query), IGMPv3 (Source-Filter für SSM). Multicast-MAC: 01-00-5E + untere 23 Bit der IP.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/12-Multicast-PIM/`](../../CML-Labs/12-Multicast-PIM/).
