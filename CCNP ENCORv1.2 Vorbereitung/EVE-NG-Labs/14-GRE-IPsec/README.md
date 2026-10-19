# Lab 14 – GRE, IPsec und VTI

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel bis schwer

Standortvernetzung über ein unsicheres Transportnetz: GRE-Tunnel, OSPF darüber, IPsec Tunnel Protection (IKEv1), anschließend IKEv2 und VTI. Dazu MTU/MSS und das typische Rekursiv-Routing-Problem.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::2.2.b` | GRE und IPsec | 53 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| CE1 | Cisco vIOS Router |  | 512 |
| ISP | Cisco vIOS Router |  | 512 |
| CE2 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **1.5 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **1.5 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| CE1 | Gi0/0 | ISP | Gi0/0 |
| ISP | Gi0/1 | CE2 | Gi0/0 |


## Topologie

```
 LAN1 ── CE1 ─────── ISP ─────── CE2 ── LAN2
 192.168.1.0/24  198.51.100.1/30 .2 | .2  203.0.113.1/30  192.168.2.0/24
        Tunnel0 (GRE, 172.16.0.0/30)  CE1 .1 / CE2 .2   Tunnel1 (VTI, 172.16.1.0/30)
```

| Gerät | Interface | Adresse |
|---|---|---|
| CE1 | Gi0/0 / Lo0 / Lo100 (LAN1) | 198.51.100.1/30 / 1.1.1.1/32 / 192.168.1.1/24 |
| ISP | Gi0/0 / Gi0/1 / Lo0 | 198.51.100.2/30 / 203.0.113.2/30 / 8.8.8.8/32 |
| CE2 | Gi0/0 / Lo0 / Lo100 (LAN2) | 203.0.113.1/30 / 2.2.2.2/32 / 192.168.2.1/24 |

CE1/CE2 haben je eine Default-Route zum ISP. Der ISP kennt nur die zwei Transfernetze.

## Teil A – Bauen

1. **Underlay.** `ping 203.0.113.1 source Gi0/0` von CE1: ok. Ping Lo100 ↔ Lo100: erfolglos. Warum? (Private LAN-Netze kennt der ISP nicht.)
2. **GRE-Tunnel.** `Tunnel0` mit Quelle Gi0/0, Ziel Gegenstelle, IP 172.16.0.1/.2 (/30). Prüfe `show interfaces tunnel0`: Tunnelprotokoll, Keepalive, Header-Overhead (GRE 24 Byte), Tunnel-MTU 1476. Was ist GRE (IP-Protokoll 47) und was kann es nicht (Verschlüsselung, Authentifizierung)?
3. **Routing über den Tunnel.** OSPF 1 auf Tunnel0 und den LAN-Loopbacks (Area 0, `ip ospf network point-to-point` auf dem Tunnel). LAN1 ↔ LAN2 muss pingen. Prüfe `show ip route 192.168.2.0` (Next-Hop über Tunnel0).
4. **Rekursiv-Routing-Falle.** Kündige testweise das Transfernetz (203.0.113.0/30) in OSPF an und beobachte `%TUN-5-RECURDOWN`: Der Tunnelzielpfad führt plötzlich über den Tunnel. Wie verhinderst du das (Netze nicht in den Overlay-IGP, Tunnel-VRF, Filter)?
5. **IPsec auf GRE (IKEv1).** ISAKMP-Policy (AES-256, SHA-256, DH 14, Pre-Shared Key), Transform-Set `esp-aes 256 esp-sha256-hmac` im **Transport-Mode**, `crypto ipsec profile`, `tunnel protection ipsec profile` auf Tunnel0. Prüfe `show crypto isakmp sa` (QM_IDLE), `show crypto ipsec sa` (encaps/decaps steigen). Warum Transport-Mode bei GRE (die GRE-Header sind schon der äußere IP-Header)?
6. **MTU/MSS.** Setze `ip mtu 1400` und `ip tcp adjust-mss 1360` auf dem Tunnel. Rechne den Overhead (IP 20 + GRE 4 + ESP ≈ 50–60) nach. Warum bricht sonst große TCP-Übertragung ab (Black-Hole bei DF-Bit/ICMP)?
7. **IKEv2 und VTI.** Baue `Tunnel1` als IPsec-VTI: `tunnel mode ipsec ipv4`, IKEv2 Proposal/Policy/Keyring/Profile, Transform-Set im **Tunnel-Mode**. Vergleiche mit GRE-over-IPsec (Multicast/Routing-Protokolle ohne GRE: VTI trägt nur IP-Unicast, aber dank IP-Tunnel auch IGP).
8. **IKEv1 vs. IKEv2.** Phase 1/2 vs. IKE_SA_INIT/IKE_AUTH, Main-/Aggressive-Mode, Authentifizierung, Resilienz (DPD, MOBIKE), Sicherheit, Standard (RFC 7296).

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Tunnel0 ist up/up, aber OSPF-Nachbar bleibt aus. `show crypto isakmp sa` zeigt MM_NO_STATE bzw. nichts.

**Ticket 2:** `QM_IDLE` steht, aber `encaps` steigt ohne `decaps` auf der Gegenseite; OSPF fällt aus.

**Ticket 3:** Tunnel0 zeigt up/up (Keepalive nicht aktiv), aber nichts kommt an; `show crypto isakmp sa` bleibt leer.

**Ticket 4:** Tunnel und IPsec stehen, aber OSPF-Nachbarschaft fehlt, LANs sind nicht erreichbar.

**Ticket 5:** Tunnel flappt zyklisch, das Log zeigt `%TUN-5-RECURDOWN` (Tunnel Interface is Down, recursive routing).

## Verifikation

```
show interfaces tunnel0
show crypto isakmp sa            show crypto ikev2 sa
show crypto ipsec sa | include encaps|decaps
show ip ospf neighbor
show ip route 192.168.2.0
ping 192.168.2.1 source Loopback100 size 1400 df-bit
```
Erwartet: OSPF-Nachbar FULL über Tunnel0, `QM_IDLE`, wachsende `encaps/decaps`, Ping mit 1400 Byte ohne Fragmentierung.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. `show crypto isakmp sa` zeigt `MM_NO_STATE`. Was heißt das?
<details><summary>Antwort</summary>

Phase 1 kommt nicht zustande: Gegenstelle nicht erreichbar, ISAKMP-Policy passt nicht (Algorithmen/DH/Auth), oder Pre-Shared Key-Mismatch.

</details>

2. Phase 1 steht (`QM_IDLE`), aber keine Daten. Was prüfst du?
<details><summary>Antwort</summary>

Phase 2: Transform-Set-Mismatch, Mode (Transport/Tunnel), Proxy-ACL/Profile, `encaps` ohne `decaps` deutet auf Rückrichtung oder ESP blockiert.

</details>

3. Warum fließt ohne GRE kein OSPF durch klassisches Crypto-Map-IPsec?
<details><summary>Antwort</summary>

IPsec transportiert nur Unicast. OSPF nutzt Multicast. Mit GRE (oder VTI) entsteht ein Interface, das Multicast tragen kann.

</details>

## Prüfungsbezug

GRE = IP-Protokoll 47. IPsec: ESP = 50, AH = 51, IKE = UDP 500 (NAT-T 4500). Transport-Mode schützt nur Payload, Tunnel-Mode kapselt das ganze Paket. VTI ist routbar, Crypto-Map nicht. IKEv1: Phase 1 (ISAKMP SA), Phase 2 (IPsec SA).

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/14-GRE-IPsec/`](../../CML-Labs/14-GRE-IPsec/).
