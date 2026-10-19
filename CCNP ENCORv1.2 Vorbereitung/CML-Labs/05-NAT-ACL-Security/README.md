# Lab 05 – NAT, ACL und Device Hardening

**Blueprint:** 3.3.b (Zugriffskontrolle: ACL, uRPF, NAT als Dienst), 5.1 (Gerätezugriff, AAA), 5.2/5.3 (Schutzmechanismen) · **Deck-Tags:** `Ziel::3.3.b`, `Ziel::5.1.*`
**Dauer:** ca. 75 min · **Nodes:** 2× Router (R1 Edge, ISP), 3× IOSv als Hosts

## Topologie

```
 PC1 ─┐                           ┌─ SRV (DMZ 172.16.0.0/24)
      ├─ SW ── R1 ── ISP        R1 Gi0/2
 PC2 ─┘  LAN    Gi0/1  .2   Lo0 8.8.8.8
 192.168.10.0/24   203.0.113.0/30
```

| Gerät | Interface | Adresse | Zone |
|---|---|---|---|
| R1 | Gi0/0 | 192.168.10.1/24 | inside (LAN) |
| R1 | Gi0/1 | 203.0.113.1/30 | outside |
| R1 | Gi0/2 | 172.16.0.1/24 | DMZ |
| ISP | Gi0/0 / Lo0 | 203.0.113.2/30 / 8.8.8.8/32 | – |
| SRV | Gi0/0 | 172.16.0.10/24 | DMZ |

R1 hat bereits eine Default-Route zum ISP, der ISP kennt über ein statisches Supernetz 203.0.113.0/24 den Rückweg. Die Server-Adresse **203.0.113.10** (Teil des /24) soll später auf SRV zeigen.

## Aufgaben

1. **Basis.** PC1 und PC2 müssen den ISP (8.8.8.8) erreichen. Das scheitert zunächst: Warum? (Private Quelladresse, ISP hat keine Rückroute, kein NAT.) Prüfe mit `traceroute` und `debug ip icmp` auf dem ISP.
2. **PAT (Overload).** Konfiguriere `ip nat inside/outside` auf R1 und eine Standard-ACL, die 192.168.10.0/24 erlaubt. Nutze `ip nat inside source list 1 interface GigabitEthernet0/1 overload`. Beobachte `show ip nat translations` und `show ip nat statistics`. Warum sieht der ISP nur eine Quelladresse? Welche Rolle spielen die Quellports?
3. **Static NAT.** Veröffentliche SRV: 172.16.0.10 ↔ 203.0.113.10 (`ip nat inside source static`). Das Interface Gi0/2 braucht `ip nat inside`. Teste vom ISP: `ping 203.0.113.10`. Die Adresse liegt nicht im Link-/30 zwischen R1 und ISP: Wie kommt der Verkehr trotzdem bei R1 an (Supernetz-Route auf dem ISP) und warum braucht R1 dafür keine zusätzliche Route?
4. **Inbound-ACL am Edge.** Auf Gi0/1 (inbound) soll nur Folgendes erlaubt sein: ICMP Echo-Reply, etabliertes TCP (`established`), TCP 80/443 zum veröffentlichten Server, UDP-DNS-Antworten (`eq 53`). Beachte die Reihenfolge bei eingehendem Verkehr: **Inbound-ACL → NAT → Routing**. Die ACL sieht daher noch die **öffentliche** Zieladresse (203.0.113.10, inside global), nicht 172.16.0.10. Wie ändert sich das bei ausgehendem Verkehr (Routing → NAT → Outbound-ACL)? Prüfe die Hit-Counter (`show access-lists`).
5. **Inter-Zone-Regeln (DMZ).** DMZ→LAN soll komplett gesperrt sein, LAN→DMZ nur TCP 80/443 und ICMP. Realisiere das mit ACLs auf Gi0/2 (inbound) und Gi0/0 (inbound). Warum sind Standard-ACLs hier falsch platziert, und warum setzt man Extended ACLs möglichst nah an die Quelle?
6. **Management absichern.** Domainname + RSA 2048 erzeugen, `ip ssh version 2`, lokale Benutzer mit `secret` (Typ 9/scrypt), `aaa new-model`, `aaa authentication login default local`, vty auf `transport input ssh`, `access-class` mit Management-ACL (nur 192.168.10.0/24), `exec-timeout 5 0`, `login block-for 60 attempts 3 within 30`. Teste mit einem SSH-Login von PC1 (`ssh -l admin 192.168.10.1`). Welche Probleme erwartest du bei Telnet? Wieso reicht `enable secret` allein nicht?
7. **Privilege Levels / Rollen.** Lege einen Benutzer `operator` mit `privilege 5` an, der nur `show ip interface brief` und `show ip route` ausführen darf (`privilege exec level 5 show ip route`). Teste. Wie unterscheidet sich das von RBAC/TACACS+-Command-Authorization?
8. **uRPF.** Aktiviere auf Gi0/1 `ip verify unicast source reachable-via rx`. Was wird verworfen? Warum ist **strict** bei asymmetrischem Routing (z. B. Dual-Homing) gefährlich und `loose` die Alternative?
9. **Control-Plane / Logging.** Konfiguriere `logging buffered 16384`, `logging host` (optional) und `service timestamps`. Aktiviere `login on-failure log`. Schau dir `show control-plane host open-ports` an: Welche Dienste lauschen auf R1, und welche davon schaltest du ab (`no ip http server`, `no service tcp-small-servers`, `no ip source-route`)?

## Verifikation

```
show ip nat translations
show ip nat statistics
show access-lists
show ip interface Gi0/1 | include access list|verify
show ip ssh
show users
show running-config | section line vty
```

Erwartet: PC1/PC2 erscheinen als `203.0.113.1:port`, SRV als statischer Eintrag, Inbound-ACL-Zähler steigen bei Tests, SSH-Sitzung nur von LAN-Adressen.

## Lösungen

Siehe [`solutions/`](solutions/).

## Prüfungsbezug

Inside/Outside Local/Global (vier Adressbegriffe!), Reihenfolge ACL → NAT → Routing (inbound) bzw. Routing → NAT → ACL (outbound), Standard-ACL möglichst nahe am Ziel, Extended nahe an der Quelle, Typ-9/Typ-8 statt Typ-5/7-Passwörtern, `aaa new-model` ändert das Login-Verhalten auf allen Lines.
