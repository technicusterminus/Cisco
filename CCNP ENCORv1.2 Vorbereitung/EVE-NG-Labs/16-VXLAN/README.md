# Lab 16 – VXLAN: VTEP, VNI und Ingress Replication

**Plattform:** EVE-NG · **Dauer:** 75 min · **Niveau:** schwer

Zwei NX-OS-Leafs spannen VLAN 10 über ein geroutetes Underlay als VXLAN-Segment (VNI 10010). Statische Ingress Replication statt EVPN, damit die Grundmechanik sichtbar bleibt. **Ressourcenhungrig:** NX-OSv 9000 braucht mehrere GB RAM pro Node.

**Lernziele:** Nach diesem Lab kannst du …

- Ein VXLAN-Segment mit VTEPs, VNI und Ingress Replication aufbauen.
- Den Overhead von VXLAN berechnen und die nötige Underlay-MTU begründen.
- Flood-and-Learn und EVPN als Control Plane unterscheiden.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::2.3.b` | VXLAN | 14 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

**Image-Hinweis:** Die zwei Nexus-Nodes brauchen zusammen etwa 16 GB RAM. Mit weniger starten sie oft nicht oder laufen instabil; reicht der Host nicht, bleibt dieses Lab für die CML-Instanz mit mehr Reserven.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| LEAF1 | Cisco Nexus 9000v (NX-OSv 9k) | Bootet 5 bis 10 Minuten; Interface 1 des Nodes ist `mgmt0`, danach `Ethernet1/1` … | 8192 |
| LEAF2 | Cisco Nexus 9000v (NX-OSv 9k) | Bootet 5 bis 10 Minuten; Interface 1 des Nodes ist `mgmt0`, danach `Ethernet1/1` … | 8192 |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **17.0 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **16.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| H1 | Gi0/0 | LEAF1 | Eth1/2 |
| LEAF1 | Eth1/1 | LEAF2 | Eth1/1 |
| LEAF2 | Eth1/2 | H2 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
  H1 ─ LEAF1 (VTEP 10.255.0.1) ═══ routed Underlay ═══ LEAF2 (VTEP 10.255.0.2) ─ H2
  10.10.10.11    Eth1/2   Eth1/1 10.0.12.0/30 Eth1/1   Eth1/2   10.10.10.12
```

| Gerät | Loopback0 (VTEP) | Underlay | Access |
|---|---|---|---|
| LEAF1 | 10.255.0.1/32 | Eth1/1 10.0.12.1/30 | Eth1/2 VLAN 10 |
| LEAF2 | 10.255.0.2/32 | Eth1/1 10.0.12.2/30 | Eth1/2 VLAN 10 |

H1/H2 liegen im selben Subnetz 10.10.10.0/24, aber an verschiedenen Leafs: Das ist der Sinn von VXLAN (Layer-2 über Layer 3). Die Management-Schnittstelle `mgmt0` bleibt ungenutzt. Interface-Namen (Eth1/1, Eth1/2) hängen vom CML-Node-Typ ab: gegebenenfalls anpassen.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Underlay.** Mache Eth1/1 zum gerouteten Port (`no switchport` und IP-Adresse). Lege Loopback0 als VTEP-Adresse an. Starte OSPF 1 in Area 0 auf Eth1/1 und Loopback0, auf beiden Leafs.
   - **Prüfen:** `ping 10.255.0.2 source 10.255.0.1` auf LEAF1 klappt.
2. **Features einschalten.** Setze `feature ospf`, `feature nv overlay` und `feature vn-segment-vlan-based`.
   - **Denkfrage:** Wozu dient `vn-segment-vlan-based`?
3. **VLAN mit VNI verbinden.** Setze unter `vlan 10` den Befehl `vn-segment 10010`.
   - **Denkfrage:** Wie viele Segmente kann eine VNI unterscheiden, und wie viele eine VLAN-ID?
4. **NVE-Interface.** Konfiguriere `interface nve1` mit `no shutdown`, `source-interface loopback0` und `member vni 10010`. Darunter `ingress-replication protocol static` und `peer-ip` mit der VTEP-Adresse des anderen Leafs.
   - **Prüfen:** `show nve peers` zeigt den anderen Leaf mit State Up.
   - **Denkfrage:** Welche Alternativen zur statischen Ingress Replication gibt es?
5. **Hosts anschließen.** Setze Eth1/2 auf `switchport access vlan 10`. H1 und H2 bekommen 10.10.10.11 und .12.
   - **Prüfen:** H1 pingt H2, obwohl dazwischen ein geroutetes Netz liegt.
6. **Beobachten.** Sieh dir `show nve peers`, `show nve vni` und `show mac address-table` an.
   - **Prüfen:** Die MAC von H2 steht auf LEAF1 mit der VTEP-Adresse von LEAF2 statt einem Port.
   - **Denkfrage:** Wie lernt LEAF1 die MAC von H2? Wie sieht ein VXLAN-Paket aus, und welche MTU braucht das Underlay?
7. **Bezug zu SD-Access und EVPN.**
   - **Denkfrage:** Wo findest du VXLAN in SD-Access wieder? Was ändert EVPN gegenüber Flood-and-Learn?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** Das Feature erlaubt, ein VLAN per `vn-segment` einer VNI zuzuordnen. Ohne es gibt es den Befehl nicht.
- **Zu 3:** Die VNI hat 24 Bit, also rund 16 Millionen Segmente. Die VLAN-ID hat 12 Bit, also 4094 nutzbare VLANs.
- **Zu 4:** Statt einer festen Peer-Liste kann Broadcast-, unbekannter Unicast- und Multicast-Verkehr über eine Multicast-Gruppe im Underlay laufen (`mcast-group`, braucht PIM). Oder EVPN übernimmt: BGP verteilt die Liste der VTEPs und die bekannten MAC- und IP-Adressen.
- **Zu 6:** LEAF1 packt ein ankommendes VXLAN-Paket aus und merkt sich die innere Quell-MAC zusammen mit der äußeren Quell-IP, also dem VTEP von LEAF2. Aufbau eines Pakets: äußerer Ethernet-Header (14 Byte), äußerer IP-Header (20), UDP mit Zielport 4789 (8), VXLAN-Header mit VNI (8), dann der ursprüngliche Frame. Das sind 50 Byte Overhead, das Underlay braucht also mindestens 1550 Byte MTU. In der Praxis setzt man Jumbo-Frames (9216).
- **Zu 7:** In SD-Access ist jeder Fabric Edge ein VTEP. Ein virtuelles Netz entspricht einer VRF bzw. VNI, und die SGT steckt im erweiterten VXLAN-Header (VXLAN-GPO). EVPN verteilt MAC- und IP-Adressen per BGP, statt sie durch Fluten zu lernen. Das spart Broadcasts, und Multi-Homing wird möglich.

</details>

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** H1 und H2 im selben Subnetz erreichen sich nicht, `show nve vni` zeigt auf LEAF2 eine andere VNI.

**Ticket 2:** `show nve peers` ist auf LEAF1 leer oder zeigt einen Peer ohne Verkehr.

**Ticket 3:** Die Verbindung steht nie, `show nve interface` zeigt `Admin down`.

**Ticket 4:** LEAF2 erreicht 10.255.0.1 nicht (Ping auf die VTEP-Adresse scheitert), NVE-Peer bleibt down.

## Verifikation
```
show nve peers
show nve vni
show vxlan
show mac address-table
show ip ospf neighbors
ping 10.10.10.12                   ! von H1
```

| Befehl | Das solltest du sehen |
|---|---|
| `show nve peers` auf LEAF1 | Peer-IP 10.255.0.2, State Up |
| `show nve vni` | VNI 10010 Up, Modus static/ingress replication |
| Ping H1 → H2 | erfolgreich über das geroutete Underlay |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Wieso ist die Quell-Portnummer im äußeren UDP-Header pseudozufällig?
<details><summary>Antwort</summary>

**Damit das Underlay die Last per ECMP verteilen kann.** Der Quellport wird aus dem inneren Flow berechnet. So nehmen verschiedene Flows verschiedene Pfade, ein Flow bleibt aber auf einem Pfad.

</details>

2. Welche MTU braucht das Underlay bei Host-MTU 1500?
<details><summary>Antwort</summary>

**Mindestens 1550 Byte.** 1500 Byte Nutzlast plus etwa 50 Byte VXLAN-Overhead: 14 Ethernet + 20 IP + 8 UDP + 8 VXLAN. In der Praxis nimmt man im Underlay gleich Jumbo-Frames.

</details>

3. Was ist der Vorteil von EVPN gegenüber Flood-and-Learn?
<details><summary>Antwort</summary>

**EVPN verteilt MAC- und IP-Adressen per BGP, statt sie durch Fluten zu lernen.** Dadurch gibt es weniger Flooding (ARP-Suppression), Multi-Homing und saubere Mobilität von Hosts.

</details>

## Prüfungsbezug
- VXLAN verpackt Ethernet-Frames in UDP/IP mit Zielport 4789.
- Die VNI hat 24 Bit, der VTEP ist der Tunnelendpunkt.
- Overhead etwa 50 Byte, also mindestens 1550 Byte MTU im Underlay.
- Control Plane: Flood-and-Learn (Multicast oder Ingress Replication) oder EVPN.
- VXLAN streckt Layer 2 über ein Layer-3-Netz.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/16-VXLAN/`](../../CML-Labs/16-VXLAN/).
