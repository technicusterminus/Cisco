# Lab 16 – VXLAN: VTEP, VNI und Ingress Replication

**Plattform:** EVE-NG · **Dauer:** 75 min · **Niveau:** schwer

Zwei NX-OS-Leafs spannen VLAN 10 über ein geroutetes Underlay als VXLAN-Segment (VNI 10010). Statische Ingress Replication statt EVPN, damit die Grundmechanik sichtbar bleibt. **Ressourcenhungrig:** NX-OSv 9000 braucht mehrere GB RAM pro Node.

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

1. **Underlay.** Eth1/1 als Routed Port (`no switchport`, IP), Loopback0 als VTEP-Adresse, OSPF 1 (Area 0) auf beiden. LEAF1 muss `10.255.0.2` per Ping erreichen (Quelle Loopback0).
2. **Features.** `feature ospf`, `feature nv overlay`, `feature vn-segment-vlan-based`. Wozu `vn-segment-vlan-based`?
3. **VLAN-zu-VNI.** `vlan 10` → `vn-segment 10010`. Wie viele Bits hat die VNI (24 Bit, ca. 16 Mio.) im Vergleich zur VLAN-ID (12 Bit)?
4. **NVE-Interface.** `interface nve1`: `no shutdown`, `source-interface loopback0`, `member vni 10010`, `ingress-replication protocol static` + `peer-ip 10.255.0.2` (bzw. .1 auf dem anderen Leaf). Beschreibe die Alternative per Multicast (`mcast-group`) und EVPN (BGP als Control Plane).
5. **Access-Ports.** Eth1/2 als `switchport access vlan 10`. H1 und H2 bekommen 10.10.10.11/12: Ping muss gehen.
6. **Beobachten.** `show nve peers`, `show nve vni`, `show mac address-table`. Wo lernt ein Leaf die MAC von H2 (Flood-and-Learn über Remote-VTEP)? Was ist die Kapselung: Outer MAC/IP, UDP 4789, VXLAN-Header (8 Byte, Flag `I`, VNI), Inner Frame. Wie groß ist der Overhead (50 Byte) und welche MTU brauchst du im Underlay (≥ 1550, besser 9216)?
7. **Vergleich zu SD-Access.** Fabric-Edge ≙ VTEP, VN ≙ VNI/VRF, SGT in VXLAN-GPO-Header. Worin unterscheidet sich EVPN-VXLAN (BGP verteilt MAC/IP) von Flood-and-Learn?

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
Erwartet: `Peer-IP 10.255.0.2 State Up`, VNI 10010 `Up`, H1 ↔ H2 Ping über das Underlay.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Wieso ist die Quell-Portnummer im äußeren UDP-Header pseudozufällig?
<details><summary>Antwort</summary>

Sie wird aus dem inneren Flow gehasht, damit ECMP im Underlay die Last auf mehrere Pfade verteilt.

</details>

2. Welche MTU braucht das Underlay bei Host-MTU 1500?
<details><summary>Antwort</summary>

Mindestens 1550 (1500 + ca. 50 Byte VXLAN-Overhead), üblicherweise Jumbo-Frames im Underlay.

</details>

3. Was ist der Vorteil von EVPN gegenüber Flood-and-Learn?
<details><summary>Antwort</summary>

MAC- und IP-Adressen werden per BGP verteilt (Control Plane), ARP-Suppression reduziert Flooding, und es gibt Multi-Homing und saubere Mobilität.

</details>

## Prüfungsbezug

VXLAN kapselt Ethernet-Frames in UDP/IP (Port 4789), VNI 24 Bit, VTEP = Tunnel-Endpunkt. Overhead ~50 Byte. Control Plane: Flood-and-Learn (Multicast/Head-End) oder EVPN. VXLAN dehnt Layer-2-Domänen über Layer-3-Underlays.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/16-VXLAN/`](../../CML-Labs/16-VXLAN/).
