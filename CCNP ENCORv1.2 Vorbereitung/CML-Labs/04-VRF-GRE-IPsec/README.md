# Lab 04 – VRF-Lite, GRE und IPsec

**Blueprint:** 2.2.a (Overlay: GRE, IPsec), 2.2.b (VRF), 5.x (Verschlüsselung) · **Deck-Tags:** `Ziel::2.2.a`, `Ziel::2.2.b`
**Dauer:** ca. 75 min · **Nodes:** 3× IOSv

## Topologie

```
 [VRF RED + BLUE]                           [VRF RED + BLUE]
   CE1 ──────── ISP ──────── CE2
  198.51.100.1/30  .2 | .2  203.0.113.1/30
 Lo0 1.1.1.1/32     Lo0 8.8.8.8      Lo0 2.2.2.2/32
```

Der ISP routet nur zwischen den beiden Transitnetzen (kennt keine Kundennetze). CE1 und CE2 haben jeweils eine Default-Route zum ISP. Auf CE1 und CE2 werden zwei Kunden-VRFs aufgebaut, **RED** und **BLUE**, mit **überlappenden Adressräumen**.

| VRF | CE1 LAN (Loopback) | CE2 LAN (Loopback) | Tunnel-Netz |
|---|---|---|---|
| RED | Lo101 192.168.1.1/24 | Lo101 192.168.2.1/24 | 172.16.1.0/30 (Tunnel1) |
| BLUE | Lo102 192.168.1.1/24 | Lo102 192.168.2.1/24 | 172.16.2.0/30 (Tunnel2) |

Ja: In beiden VRFs ist das Netz identisch. Genau das sollst du nutzen und verstehen.

## Aufgaben

1. **Underlay prüfen.** Von CE1 muss `ping 203.0.113.1 source GigabitEthernet0/0` funktionieren. Ein Ping von Lo0 zu Lo0 (2.2.2.2) scheitert dagegen: Warum? (Der ISP kennt die Loopbacks nicht.) Genau deshalb wird später die Gi0/0-Adresse als Tunnelquelle benutzt.
2. **VRFs anlegen.** Definiere auf CE1 und CE2 die VRFs RED und BLUE (`vrf definition`, `address-family ipv4`). Lege Lo101 in RED und Lo102 in BLUE an und prüfe, dass die gleiche Adresse 192.168.x.1 in beiden VRFs existieren darf. Welche Routing-Tabelle zeigt `show ip route` ohne VRF?
3. **GRE-Tunnel pro VRF.** Baue zwischen CE1 und CE2 zwei GRE-Tunnel (Tunnel1 und Tunnel2). Tunnelquelle ist Gi0/0, Tunnelziel die Gi0/0-Adresse der Gegenstelle. Tunnel1 gehört in VRF RED (172.16.1.1/.2), Tunnel2 in VRF BLUE (172.16.2.1/.2). Wichtig: Das **Tunnelinterface** liegt in der VRF, die **Transportseite** (Source/Destination) bleibt in der globalen Tabelle. Welcher Befehl würde die Transportseite in eine VRF legen (`tunnel vrf`)?
4. **OSPF pro VRF.** Starte auf beiden CEs zwei OSPF-Prozesse (`router ospf 1 vrf RED`, `router ospf 2 vrf BLUE`) und tausche die Loopback-Netze über die Tunnel aus. Prüfe: `show ip route vrf RED ospf` zeigt auf CE1 192.168.2.0/24 und `show ip route vrf BLUE ospf` ebenfalls. Pingen müssen RED→RED und BLUE→BLUE funktionieren, `ping vrf RED 192.168.2.1 source Loopback101`.
5. **Trennung beweisen.** Welcher Ping scheitert? Teste einen Ping von VRF RED an eine Adresse, die es nur in BLUE gibt (z. B. 172.16.2.2). Erkläre die Ausgabe.
6. **IPsec auf Tunnel1.** Schütze nur **Tunnel1** per IPsec Tunnel Protection: ISAKMP-Policy (AES-256, SHA-256, DH Group 14, Pre-Shared Key), Transform-Set `esp-aes 256 esp-sha256-hmac`, Mode Transport, IPsec-Profile, `tunnel protection ipsec profile`. Prüfe mit `show crypto isakmp sa` und `show crypto ipsec sa`, dass nur der Verkehr in VRF RED verschlüsselt (encaps/decaps zählen) wird. Wieso nutzt man bei GRE-über-IPsec Transport- statt Tunnel-Mode?
7. **MTU/MSS.** Ermittle die effektive MTU von Tunnel1 (`show interfaces tunnel1`, `show ip interface tunnel1`) und setze `ip mtu 1400` sowie `ip tcp adjust-mss 1360`. Rechne den Overhead GRE (24 B) + IPsec-Transport (ca. 50–60 B) nach. Warum bricht sonst große TCP-Übertragung?
8. **Fehlersuche.** Füge auf CE1 versehentlich eine statische Route `ip route 203.0.113.0 255.255.255.252 Tunnel1` hinzu. Was passiert mit dem Tunnel? (`%TUN-5-RECURDOWN`, rekursives Routing). Wie behebst du das?

## Verifikation

```
show vrf
show ip route vrf RED
show interfaces tunnel1
show crypto isakmp sa
show crypto ipsec sa | include encaps|decaps
show ip ospf 1 neighbor
ping vrf RED 192.168.2.1 source Loopback101
```

Erwartet: Beide OSPF-Nachbarn FULL, in beiden VRFs je eine `O 192.168.2.0/24`-Route, `encaps`/`decaps` > 0 nur für Tunnel1.

## Lösungen

Siehe [`solutions/`](solutions/).

## Prüfungsbezug

GRE = IP-Protokoll 47, ohne Verschlüsselung. IPsec: ESP = Protokoll 50, IKE = UDP 500 (NAT-T 4500). Tunnel-Mode vs. Transport-Mode, VRF-Lite vs. MPLS-VRF, RD/RT gehören zu MP-BGP (hier nicht gebraucht, VRF-Lite nutzt keine).
