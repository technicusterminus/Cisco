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
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Subinterfaces und Switch.** Lege auf R1 und R2 die Subinterfaces `Gi0/0.10`, `.20` und `.30` an (`encapsulation dot1Q`, R1 jeweils .2, R2 jeweils .3). Lege auf dem Switch die VLANs 10, 20 und 30 an, mache die Ports zu R1 und R2 zu Trunks (erlaubt: 10, 20, 30) und die Host-Ports zu Access-Ports (H1 VLAN 10, H2 VLAN 20, H3 und H4 VLAN 30).
   - **Prüfen:** R1 pingt R2 in allen drei VLANs.
2. **HSRP in VLAN 10.** Konfiguriere `standby version 2` und Gruppe 10 mit der virtuellen IP 10.10.10.1. R1 bekommt Priorität 110 mit `preempt`, R2 behält 100.
   - **Prüfen:** `show standby brief` zeigt R1 als Active, R2 als Standby und die virtuelle MAC `0000.0C9F.F00A`.
   - **Denkfrage:** Warum ist Preempt bei HSRP standardmäßig aus?
3. **Tracking.** Lege auf R1 `track 1 interface Gi0/2 line-protocol` an und koppel es mit `standby 10 track 1 decrement 20` an HSRP. Schalte dann Gi0/2 auf R1 ab.
   - **Prüfen:** `show standby` auf R1 zeigt Priorität 90, R2 wird Active.
   - **Denkfrage:** Welcher Decrement ist mindestens nötig? Und warum reicht der Zustand des Interfaces bei einem Layer-3-Uplink oft nicht aus?
4. **VRRP in VLAN 20.** Konfiguriere `vrrp 20 ip 10.10.20.1` auf beiden Routern, R2 bekommt `vrrp 20 priority 110`.
   - **Prüfen:** `show vrrp brief` zeigt R2 als Master.
   - **Denkfrage:** Was unterscheidet VRRP von HSRP?
5. **GLBP in VLAN 30.** Konfiguriere `glbp 30 ip 10.10.30.1`, auf R1 `glbp 30 priority 110` und `glbp 30 preempt`, auf beiden `glbp 30 load-balancing round-robin`.
   - **Prüfen:** H3 und H4 pingen ihr Gateway. `show arp` auf H3 und H4 zeigt für 10.10.30.1 zwei verschiedene MAC-Adressen.
   - **Denkfrage:** Welche Rollen gibt es bei GLBP, und wer verteilt die MAC-Adressen?
6. **Timer verkürzen.** Setze in HSRP `standby 10 timers msec 200 msec 750`. Starte auf H1 `ping 10.10.10.1 repeat 1000` und schalte Gi0/0 auf R1 ab.
   - **Prüfen:** Es gehen nur wenige Pings verloren. Mit den Standardwerten (3 s Hello, 10 s Hold) wären es deutlich mehr.
   - **Denkfrage:** Was wäre eine Alternative zu sehr kurzen Timern?
7. **Redundanz einordnen.** Ordne zu, was auf welcher Ebene schützt: Link (EtherChannel), Gerät (FHRP, StackWise), Chassis (SSO, NSF), Standort (zweites Rechenzentrum).
   - **Denkfrage:** Was leisten SSO und NSF, was FHRP nicht kann?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** Ohne Preempt bleibt ein Router Active, bis er ausfällt. So vermeidet HSRP, dass die Rolle ständig hin und her springt, wenn ein Router neu startet. Wer die Rolle zurückholen soll, braucht `preempt` ausdrücklich.
- **Zu 3:** Die Priorität muss unter die von R2 fallen: 110 − x < 100, also mindestens 11. Ein Interface kann up sein, obwohl dahinter nichts mehr erreichbar ist. Besser ist dann ein Track auf eine Route (`track … ip route … reachability`) oder auf IP SLA.
- **Zu 4:** VRRP ist ein offener Standard (RFC 5798) und nutzt 224.0.0.18. Es heißt Master und Backup statt Active und Standby, Preempt ist standardmäßig an, und die virtuelle MAC lautet `0000.5E00.01xx`. Die virtuelle IP darf sogar die echte Adresse eines Routers sein.
- **Zu 5:** Der Active Virtual Gateway (AVG) beantwortet die ARP-Anfragen und verteilt dabei die virtuellen MAC-Adressen. Bis zu vier Active Virtual Forwarders (AVF) leiten die Pakete weiter. Jeder Host bekommt so ein anderes Gateway, obwohl alle dieselbe IP benutzen.
- **Zu 6:** BFD erkennt Ausfälle in Millisekunden und meldet sie an die Protokolle. So bleibt die CPU-Last durch Hellos klein.
- **Zu 7:** SSO hält den Zustand zwischen zwei Supervisoren in einem Gerät synchron. Fällt einer aus, übernimmt der andere ohne Neustart. NSF leitet in dieser Zeit weiter Pakete weiter, die Nachbarn halten ihre Routen. FHRP schützt dagegen gegen den Ausfall eines ganzen Geräts mit Hilfe eines zweiten.

</details>

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

| Befehl | Das solltest du sehen |
|---|---|
| `show standby brief` | R1 Active für VLAN 10 |
| `show vrrp brief` | R2 Master für VLAN 20 |
| `show glbp brief` | R1 als AVG, R1 und R2 je ein AVF |

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
- HSRP: v1 224.0.0.2, v2 224.0.0.102, Priorität 100, Preempt aus.
- VRRP: Master/Backup, Preempt an, 224.0.0.18.
- GLBP: Der AVG verteilt bis zu vier virtuelle MAC-Adressen an die AVFs.
- Tracking senkt die Priorität, wirkt aber nur, wenn die Differenz reicht.
- SSO synchronisiert die Control Plane zwischen Supervisoren, NSF leitet während des Wechsels weiter.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/07-FHRP-HSRP-VRRP-GLBP/`](../../CML-Labs/07-FHRP-HSRP-VRRP-GLBP/).
