# Lab 07 – First-Hop-Redundanz: HSRP, VRRP und GLBP

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel

Zwei Distribution-Router, ein Access-Switch, drei VLANs mit je einem anderen FHRP-Protokoll. Dazu Tracking, Preemption, Timer und die Frage, welche Redundanzstufe (Link, Gerät, Standort) Hochverfügbarkeit wirklich liefert.

**Lernziele:** Nach diesem Lab kannst du …

- HSRP, VRRP und GLBP konfigurieren und ihre Unterschiede erklären.
- Mit Tracking und Preemption steuern, wann die Rolle wechselt.
- Redundanz auf Link-, Geräte- und Chassis-Ebene (SSO/NSF) einordnen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.3.c` | HSRP und VRRP | 30 |
| `Ziel::1.1.b` | Redundanz, FHRP und SSO | 22 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| SW | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H3 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H4 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **4.2 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.2 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | SW | Gi0/0 |
| R2 | Gi0/0 | SW | Gi0/1 |
| R1 | Gi0/1 | R2 | Gi0/1 |
| R1 | Gi0/2 | R3 | Gi0/0 |
| R2 | Gi0/2 | R3 | Gi0/1 |
| SW | Gi1/0 | H1 | Gi0/0 |
| SW | Gi1/1 | H2 | Gi0/0 |
| SW | Gi1/2 | H3 | Gi0/0 |
| SW | Gi1/3 | H4 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
                     R3 (Core, 8.8.8.8)
                  Gi0/0         Gi0/1
                    │             │
   H1 (V10) ─┐   R1 ─────────── R2       R1/R2 Gi0/1 ↔ Gi0/1  (10.0.12.0/30)
   H2 (V20) ─┼─ SW ── Gi0/0↔R1.Gi0/0    R1 Gi0/2 ↔ R3 Gi0/0, R2 Gi0/2 ↔ R3 Gi0/1
   H3 (V30) ─┤     └─ Gi0/1↔R2.Gi0/0
   H4 (V30) ─┘
```

| VLAN | Protokoll | VIP | R1 | R2 | Rolle (Soll) |
|---|---|---|---|---|---|
| 10 | **HSRP v2** | 10.10.10.1 | .2 | .3 | R1 Active (Prio 110, preempt, Track Uplink) |
| 20 | **VRRP** | 10.10.20.1 | .2 | .3 | R2 Master (Prio 110) |
| 30 | **GLBP** | 10.10.30.1 | .2 | .3 | R1 AVG (Prio 110), Round-Robin |

Hosts: H1 10.10.10.11, H2 10.10.20.12, H3 10.10.30.13, H4 10.10.30.14 (Gateway = VIP). Uplinks: R1 Gi0/2 ↔ R3 Gi0/0 (10.0.13.0/30), R2 Gi0/2 ↔ R3 Gi0/1 (10.0.23.0/30), R3 Lo0 8.8.8.8/32. OSPF 1 (Area 0) läuft bereits auf den Uplinks und zwischen R1/R2.

## Teil A – Bauen

1. **Subinterfaces.** Auf R1 und R2 `Gi0/0.10/.20/.30` (`encapsulation dot1Q`, eigene IP .2 bzw. .3). Auf dem Switch SW: VLANs 10/20/30 anlegen, Trunks zu R1 und R2 (Allowed 10,20,30), Hosts als Access (H1 V10, H2 V20, H3/H4 V30).
2. **HSRP (VLAN 10).** `standby version 2`, Gruppe 10, VIP .1, R1 Priorität 110 mit `preempt`, R2 Default 100. Lies `show standby brief`: Active/Standby/Virtual-MAC `0000.0C9F.Fxxx`. Warum ist Preempt standardmäßig aus?
3. **Tracking.** `track 1 interface Gi0/2 line-protocol` und `standby 10 track 1 decrement 20`. Schalte R1 Gi0/2 ab: Wechselt R2 auf Active? Welcher Decrement-Wert ist nötig (110 − x < 100)? Warum bräuchte man bei Layer-3-Uplinks ein besseres Track-Objekt (IP SLA, Route-Existenz)?
4. **VRRP (VLAN 20).** `vrrp 20 ip 10.10.20.1`, R2 `priority 110`. VRRP (RFC 5798) vs. HSRP: Preempt ist Standard, Multicast 224.0.0.18, Master/Backup, virtuelle MAC `0000.5E00.01xx`.
5. **GLBP (VLAN 30).** `glbp 30 ip 10.10.30.1`, R1 `priority 110 preempt`, `load-balancing round-robin`. Prüfe von H3 und H4 per `show arp`, dass die Gateway-MAC **unterschiedlich** ist (AVF 1/2). Welche Rollen gibt es (AVG/AVF)?
6. **Timer.** Setze bei HSRP `timers msec 200 msec 750` und beobachte die Ausfallzeit mit `ping repeat 1000` beim Abschalten von R1 Gi0/0. Vergleiche mit Default (3/10 s) und mit BFD-Ansatz.
7. **HA-Konzepte.** Beschreibe zu jeder Redundanzstufe (Link: EtherChannel, Gerät: FHRP/StackWise, Chassis: SSO/NSF, Standort: Dual-Site) die typische Ausfallzeit und Konfiguration. Was leisten **SSO** und **NSF** im Gegensatz zu FHRP?

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Auf VLAN 10 melden beide Router `Active`, im Log steht `%HSRP-4-DIFFVIP1`.

**Ticket 2:** Nach Abschalten von R1 Gi0/2 bleibt R1 HSRP Active, der Verkehr von VLAN 10 geht ins Leere.

**Ticket 3:** VLAN 20 zeigt auf beiden Routern `Master`, Hosts erhalten unregelmäßig Pings.

**Ticket 4:** Nach dem Wiederanschalten von R1 Gi0/2 bleibt R2 Active, obwohl R1 höhere Priorität hat.

## Verifikation

```
show standby brief          show vrrp brief          show glbp brief
show track
show ip route ospf
show arp                    ! auf den Hosts
```
Erwartet: R1 HSRP Active, R2 VRRP Master, R1 AVG mit AVF 1 (R1) und AVF 2 (R2).

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. HSRP-Priorität R1 = 110, R2 = 100, R1 verliert den Uplink, Track decrement 5. Wer ist Active?
<details><summary>Antwort</summary>

**Immer noch R1.** 110 − 5 = 105, und 105 ist größer als 100. Der Decrement muss größer sein als der Abstand zu R2, hier also mindestens 11.

</details>

2. Wozu GLBP, wenn HSRP genügt?
<details><summary>Antwort</summary>

**Weil GLBP die Last auf mehrere Router verteilt.** Bei HSRP und VRRP leitet pro Gruppe nur der aktive Router weiter. GLBP gibt verschiedenen Hosts verschiedene virtuelle MAC-Adressen, ohne zusätzliche Gruppen oder Konfiguration pro Host.

</details>

3. Was ist der Unterschied zwischen SSO und FHRP?
<details><summary>Antwort</summary>

**SSO schützt innerhalb eines Geräts, FHRP gegen den Ausfall eines ganzen Geräts.** SSO schaltet auf den zweiten Supervisor um und übernimmt den Zustand. FHRP lässt einen zweiten Router die gemeinsame virtuelle IP übernehmen.

</details>

## Prüfungsbezug

HSRP: v1 224.0.0.2, v2 224.0.0.102, Priorität 100, Preempt aus. VRRP: Master/Backup, Preempt an, 224.0.0.18. GLBP: AVG vergibt virtuelle MACs an AVFs (pro Gruppe max. 4). Track senkt die Priorität, ändert aber nichts, wenn die Differenz nicht reicht. SSO hält den Control Plane Zustand zwischen Supervisoren, NSF erlaubt Weiterleiten während Neustart.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/07-FHRP-HSRP-VRRP-GLBP/`](../../CML-Labs/07-FHRP-HSRP-VRRP-GLBP/).
