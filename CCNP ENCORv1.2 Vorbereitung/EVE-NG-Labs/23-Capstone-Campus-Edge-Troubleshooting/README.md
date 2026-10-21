# Lab 23 – Capstone: Campus und Edge, Fehlersuche im Gesamtnetz

**Plattform:** EVE-NG · **Dauer:** 150 min · **Niveau:** schwer

Ein komplettes kleines Campus-Netz mit Internet-Edge: Access-Switch mit EtherChannel, Distribution-Router mit HSRP, OSPF, NAT, ACL, NTP und SSH. Der Schwerpunkt liegt auf der Reparatur: Zehn Fehler aus allen Schichten, teils voneinander verdeckt, wie in einem echten Troubleshooting-Ticket der Prüfung.

**Lernziele:** Nach diesem Lab kannst du …

- Ein Campus-Netz mit Layer 2, HSRP, OSPF, NAT und ACLs als Ganzes lesen.
- Fehler systematisch von unten nach oben eingrenzen: erst Layer 2, dann Gateway, dann Routing, dann Dienste.
- Mehrere Fehler lösen, bei denen einer den nächsten verdeckt.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.1.a` | 802.1Q und Trunks | 31 |
| `Ziel::3.1.b` | EtherChannel | 34 |
| `Ziel::3.1.c` | RSTP, MST und Schutzfunktionen | 65 |
| `Ziel::3.2.b` | OSPFv2 und OSPFv3 | 86 |
| `Ziel::3.3.a` | NTP und PTP | 32 |
| `Ziel::3.3.b` | NAT und PAT | 29 |
| `Ziel::3.3.c` | HSRP und VRRP | 30 |
| `Ziel::5.1.a` | Lines und lokale Anmeldung | 27 |
| `Ziel::5.2.a` | ACLs | 52 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| EDGE | Cisco vIOS Router |  | 512 |
| ISP | Cisco vIOS Router |  | 512 |
| SW1 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW2 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| H10 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H20 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **4.5 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **3.5 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| EDGE | Gi0/2 | ISP | Gi0/0 |
| R1 | Gi0/2 | EDGE | Gi0/0 |
| R2 | Gi0/2 | EDGE | Gi0/1 |
| R1 | Gi0/1 | R2 | Gi0/1 |
| R1 | Gi0/0 | SW1 | Gi0/0 |
| R2 | Gi0/0 | SW1 | Gi0/1 |
| SW1 | Gi0/2 | SW2 | Gi0/2 |
| SW1 | Gi0/3 | SW2 | Gi0/3 |
| SW2 | Gi1/0 | H10 | Gi0/0 |
| SW2 | Gi1/1 | H20 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
                          ISP (8.8.8.8)
                             │ 203.0.113.0/30
                           EDGE (NAT, NTP-Master, Lo0 10.255.0.3)
                     Gi0/0 /          \ Gi0/1
                10.0.13.0/30          10.0.23.0/30
                     R1 ──────────── R2        R1/R2 Gi0/1 ↔ Gi0/1 (10.0.12.0/30)
                  Gi0/0 \            / Gi0/0    HSRP v2, V10 + V20
                          SW1 (Root)
                       Gi0/2-3 ║ Po1 (LACP)
                          SW2 (Access)
                      Gi1/0 │      │ Gi1/1
                       H10 (V10)  H20 (V20)
```

| Netz | Verwendung |
|---|---|
| 10.10.10.0/24 | VLAN 10, VIP .1, R1 .2, R2 .3, H10 .11 |
| 10.10.20.0/24 | VLAN 20, VIP .1, R1 .2, R2 .3, H20 .12 |
| 10.0.12.0/30 | R1 .1 – R2 .2 |
| 10.0.13.0/30 | R1 .1 – EDGE .2 |
| 10.0.23.0/30 | R2 .1 – EDGE .2 |
| 203.0.113.0/30 | ISP .1 – EDGE .2 |
| Loopbacks | R1 10.255.0.1, R2 10.255.0.2, EDGE 10.255.0.3 (NTP-Server), ISP 8.8.8.8 |

**Design-Vorgaben:** SW1 ist STP-Root für VLAN 10 und 20 (Priorität 4096), SW2 hat 61440. Po1 ist ein LACP-Trunk (nur VLAN 10, 20). R1 ist HSRP-Active (Priorität 110, preempt) für beide VLANs, R2 Standby. OSPF 1 Area 0 mit `passive-interface default`. EDGE originiert die Default-Route per OSPF und macht PAT (Quell-Netz 10.10.0.0/16) auf Gi0/2. VLAN 20 darf VLAN 10 nicht erreichen (ACL auf R1/R2, eingehend am VLAN-20-Subinterface). NTP-Quelle ist EDGE. Verwaltung nur per SSH (Benutzer `admin`, Passwort `Lab-Passw0rd!`).

## Teil A – Bauen

Dieses Lab ist vor allem zum **Reparieren** gedacht (Teil B). Wer es bauen will, geht in dieser Reihenfolge vor und prüft nach jeder Stufe:

1. **Layer 2.** VLAN 10/20 auf SW1/SW2, LACP-Po1 (`channel-group 1 mode active` auf SW1, `passive` auf SW2), Trunks zu R1/R2 (`switchport mode trunk`, `nonegotiate`, Allowed 10,20), Access-Ports für H10/H20 mit PortFast. Root-Design per `spanning-tree vlan 10,20 priority 4096` (SW1) bzw. 61440 (SW2). Prüfe `show etherchannel summary`, `show spanning-tree root`.
2. **Gateway-Redundanz.** Subinterfaces `Gi0/0.10/.20` auf R1/R2, HSRP **Version 2**, Gruppen 10 und 20, R1 Priorität 110 mit `preempt`. Prüfe `show standby brief` und dass H10/H20 ihr Gateway erreichen.
3. **Routing.** OSPF 1 mit `passive-interface default`, Gi0/1 und Gi0/2 (EDGE: Gi0/0 und Gi0/1) aktivieren; `network 10.0.0.0 0.255.255.255 area 0`. Auf EDGE Default-Route zum ISP und `default-information originate`.
4. **NAT.** EDGE: `access-list 1 permit 10.10.0.0 0.0.255.255`, `ip nat inside` auf Gi0/0 und Gi0/1, `ip nat outside` auf Gi0/2, `ip nat inside source list 1 interface GigabitEthernet0/2 overload`. Test: H10 und H20 pingen 8.8.8.8.
5. **ACL.** `ip access-list extended V20-IN` mit `deny ip 10.10.20.0 0.0.0.255 10.10.10.0 0.0.0.255` vor `permit ip any any`, am Subinterface .20 eingehend (R1 und R2).
6. **Zeit und Verwaltung.** EDGE `ntp master 3`, R1/R2 `ntp server 10.255.0.3`. Auf allen Routern `ip domain-name lab.local`, lokaler Benutzer, `crypto key generate rsa modulus 2048` (manuell, steht nicht in der Startkonfiguration), `ip ssh version 2`, vty `login local` und `transport input ssh`.
7. **Abnahme.** H10 pingt 8.8.8.8, H20 pingt 8.8.8.8, H20 pingt H10 **nicht**, `show ntp status` auf R1 und R2 zeigt synchronisiert, SSH von R1 zu R2 klappt, Abschalten von R1 lässt H10 und H20 über R2 im Internet.

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **10 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** H20 erreicht seinen Gateway nicht, H10 schon. Von R1 aus ist 10.10.20.12 nicht erreichbar.

**Ticket 2:** Nach dem Reparieren des Trunks melden in VLAN 10 beide Router `Active`. `show standby brief` auf R1 und R2 zeigt jeweils `Active` und keinen Standby-Partner; Hosts erhalten ARP-Antworten verschiedener Router.

**Ticket 3:** Alles funktioniert, aber beim Test (Abschalten von R1) verlieren alle Hosts das Internet, obwohl R2 HSRP Active wird. `show ip ospf neighbor` auf EDGE zeigt nur R1.

**Ticket 4:** H10 erreicht 8.8.8.8, H20 nicht, obwohl das Routing stimmt. `show ip nat translations` enthält nur Einträge aus 10.10.10.x.

**Ticket 5:** H20 kann H10 anpingen, obwohl die Segmente getrennt sein sollen. `show access-lists` zeigt keine Treffer auf der deny-Zeile.

**Ticket 6:** `show spanning-tree root` zeigt für VLAN 10 und 20 SW2 als Root, Design verlangt SW1. Der Verkehr der Hosts nimmt einen Umweg, SW1 hat `Root port Po1`.

**Ticket 7:** Po1 bündelt nicht: `show etherchannel summary` zeigt auf SW1 `(s)`/`(I)`-Ports, die Verbindung zu H10 und H20 ist unzuverlässig oder fällt ganz aus.

**Ticket 8:** `show ntp status` auf R2: `Clock is unsynchronized`, R1 ist synchron. `show ntp associations` zeigt Reach 0.

**Ticket 9:** SSH von R1 auf R2 wird abgewiesen (`Connection refused by remote host`), Telnet dagegen geht.

**Ticket 10:** H10/H20 erreichen 8.8.8.8 nicht. EDGE erreicht den ISP, R1 und R2 haben aber keine Default-Route (`show ip route 0.0.0.0` → `Network not in table`).

## Verifikation

```
show etherchannel summary          show spanning-tree root
show standby brief                 show ip ospf neighbor
show ip route ospf | include O\*   show ip nat translations
show access-lists                  show ntp status
show ip ssh                        ping 8.8.8.8 source 10.10.10.2
```
Erwartet: Po1 `SU` mit `Gi0/2(P) Gi0/3(P)`, SW1 Root, R1 Active für beide VLANs, EDGE hat zwei OSPF-Nachbarn, R1 und R2 haben eine `O*E2` Default-Route, NAT-Einträge für 10.10.x.x.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. H20 erreicht sein Gateway nicht, H10 schon. Welche Kommandos in welcher Reihenfolge?
<details><summary>Antwort</summary>

**Von unten nach oben: erst Layer 2, dann der Router.** `show vlan brief` und `show interfaces trunk` auf SW2 und SW1 (ist VLAN 20 vorhanden und auf dem Trunk erlaubt?), dann `show spanning-tree vlan 20` (blockiert ein Port?), dann `show standby brief` auf R1. Erst wenn Layer 2 stimmt, lohnt der Blick auf die Router.

</details>

2. Wozu `passive-interface default` im Campus-Design, und was ist die Nebenwirkung eines vergessenen `no passive-interface`?
<details><summary>Antwort</summary>

**Damit sich nur dort Nachbarn bilden, wo sie gewollt sind.** Passive Interfaces senden keine Hellos. Das schützt LAN- und Edge-Ports und spart CPU. Vergisst man auf einem Uplink `no passive-interface`, fehlt die Nachbarschaft ohne Fehlermeldung. Auffallen tut das erst, wenn der Ersatzweg gebraucht wird.

</details>

3. Warum zeigt `show ip nat translations` nichts, obwohl `ip nat inside source` konfiguriert ist?
<details><summary>Antwort</summary>

**Weil das Paket gar nicht übersetzt wird.** Typisch: Inside oder Outside fehlt an einem Interface, die ACL passt nicht auf das Quellnetz, oder es fehlt die Default-Route, sodass das Paket das Outside-Interface nie erreicht.

</details>

## Prüfungsbezug

Eine Troubleshooting-Aufgabe in der Prüfung gibt dir selten den Fehler, sondern ein Symptom. Arbeitsmethode: Layer 1/2 (Interface, VLAN, Trunk, Channel, STP), Layer 3 (Adressen, Gateway/FHRP, Routing), Dienste (NAT, ACL, NTP, SSH). Prüfe immer **beide Seiten** einer Verbindung, und denke an verdeckende Fehler: Ein Fehler weiter unten im Stack kann die Wirkung eines weiter oben liegenden verbergen.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/23-Capstone-Campus-Edge-Troubleshooting/`](../../CML-Labs/23-Capstone-Campus-Edge-Troubleshooting/).
