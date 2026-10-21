# Lab 16 – VXLAN: VTEP, VNI und Ingress Replication

**Dauer:** 75 min · **Niveau:** schwer · **Nodes:** 2× iosv, 2× nxosv9000

Zwei NX-OS-Leafs spannen VLAN 10 über ein geroutetes Underlay als VXLAN-Segment (VNI 10010). Statische Ingress Replication statt EVPN, damit die Grundmechanik sichtbar bleibt. **Ressourcenhungrig:** NX-OSv 9000 braucht mehrere GB RAM pro Node.

**Lernziele:** Nach diesem Lab kannst du …

- Ein VXLAN-Segment mit VTEPs, VNI und Ingress Replication aufbauen.
- Den Overhead von VXLAN berechnen und die nötige Underlay-MTU begründen.
- Flood-and-Learn und EVPN als Control Plane unterscheiden.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::2.3.b` | VXLAN | 14 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

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

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

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

VXLAN kapselt Ethernet-Frames in UDP/IP (Port 4789), VNI 24 Bit, VTEP = Tunnel-Endpunkt. Overhead ~50 Byte. Control Plane: Flood-and-Learn (Multicast/Head-End) oder EVPN. VXLAN dehnt Layer-2-Domänen über Layer-3-Underlays.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
