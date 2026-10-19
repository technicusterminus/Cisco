# Lab 09 – NAT und PAT

**Plattform:** EVE-NG · **Dauer:** 75 min · **Niveau:** mittel

Edge-Router mit LAN, DMZ und ISP: PAT (Overload), dynamisches NAT mit Pool, statisches NAT und Port-Forwarding. Du lernst die vier NAT-Adressbegriffe, die Reihenfolge der Operationen und die typischen Fehler.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.3.b` | NAT und PAT | 29 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| SW | Network (Bridge) | Kein Gerät, sondern ein **Network**-Objekt (Linux-Bridge) mit Typ *Bridge*. | – |
| PC1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| PC2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| R1 | Cisco vIOS Router |  | 512 |
| ISP | Cisco vIOS Router |  | 512 |
| SRV | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.5 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **1.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | SW | – |
| PC1 | Gi0/0 | SW | – |
| PC2 | Gi0/0 | SW | – |
| R1 | Gi0/1 | ISP | Gi0/0 |
| R1 | Gi0/2 | SRV | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
 PC1 ─┐                          ┌─ SRV (DMZ 172.16.0.10, HTTP)
      ├─ SW ── R1 ──────────── ISP ── Lo0 8.8.8.8
 PC2 ─┘  LAN   Gi0/0 Gi0/1 .2   (203.0.113.0/30)
 192.168.10.0/24  R1 Gi0/2 = DMZ 172.16.0.0/24
```

| Gerät | Interface | Adresse | NAT-Rolle |
|---|---|---|---|
| R1 | Gi0/0 | 192.168.10.1/24 | inside |
| R1 | Gi0/1 | 203.0.113.1/30 | outside |
| R1 | Gi0/2 | 172.16.0.1/24 | inside (DMZ) |
| ISP | Gi0/0 / Lo0 | 203.0.113.2/30 / 8.8.8.8/32 | – |
| PC1/PC2 | Gi0/0 | 192.168.10.11 / .12 | – |
| SRV | Gi0/0 | 172.16.0.10/24 (HTTP-Server an) | – |

Der ISP kennt das Supernetz 203.0.113.0/24 (via R1), daher sind alle Adressen des /24 für NAT nutzbar. R1 hat Default zum ISP.

## Teil A – Bauen

1. **Problem erkennen.** PC1 pingt 8.8.8.8: erfolglos. Warum (private Quelle, ISP hat keine Rückroute)? Prüfe mit `debug ip icmp` auf dem ISP.
2. **PAT.** `ip nat inside`/`outside` auf den Interfaces, Standard-ACL 1 für 192.168.10.0/24, `ip nat inside source list 1 interface Gi0/1 overload`. Prüfe `show ip nat translations` und `show ip nat statistics`. Welche Rolle spielen die Quellports?
3. **Vier Adressbegriffe.** Ordne in einer Übersetzung die Adressen *inside local*, *inside global*, *outside local*, *outside global* zu. Welche davon ändert NAT im üblichen Szenario?
4. **Dynamisches NAT.** Definiere Pool `POOL` (203.0.113.16–203.0.113.19, /24) und binde PC2 per ACL 2 ohne Overload daran. Starte vier verschiedene PCs gleichzeitig (oder simuliere) und beobachte Pool-Erschöpfung (`show ip nat statistics`: Misses).
5. **Statisches NAT.** SRV soll aus dem Internet erreichbar sein: `ip nat inside source static 172.16.0.10 203.0.113.10`. Teste `telnet 203.0.113.10 80` vom ISP. Welche Proxy-ARP-/Routing-Frage stellt sich, wenn die globale Adresse im Transfernetz selbst liegt?
6. **Static PAT / Port-Forwarding.** Leite TCP/8080 an der Interface-Adresse 203.0.113.1 auf SRV:80 weiter (`ip nat inside source static tcp 172.16.0.10 80 interface Gi0/1 8080`).
7. **Reihenfolge.** Erkläre Inside→Outside: Routing → NAT; Outside→Inside: NAT → Routing; ACL-Verhalten (Inbound-ACL sieht vor NAT die globale Adresse). Wo setzt man deshalb ACLs?
8. **Debug.** `debug ip nat detailed` kurz nutzen und `clear ip nat translation *`. Wann ist `clear` im Betrieb heikel (aktive Sessions)?

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Weder PC1 noch PC2 erreichen den ISP, `show ip nat translations` ist leer (Quelladresse bleibt privat).

**Ticket 2:** Dasselbe Bild trotz korrektem Interface-Setup: keine Übersetzung, der ISP sieht nichts.

**Ticket 3:** PC1 kommt raus, PC2 danach nicht mehr; `show ip nat statistics` zeigt Misses.

**Ticket 4:** Der ISP erreicht 203.0.113.10 (Server) nicht, `show ip nat translations` zeigt die Zuordnung zu .11.

## Verifikation

```
show ip nat translations [verbose]
show ip nat statistics
show access-lists
debug ip nat
```
Erwartet: PC1/PC2 erscheinen als `203.0.113.1:port` (PAT), SRV statisch auf 203.0.113.10, Port 8080 leitet an 172.16.0.10:80.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. PC1 kann den ISP erreichen, PC2 nicht. Welche drei Dinge prüfst du?
<details><summary>Antwort</summary>

ACL 1 (Subnetz passend?), Interface-Zuordnung inside/outside, Pool/Overload (Erschöpfung `Misses` in `show ip nat statistics`).

</details>

2. Warum sieht man in `show ip nat translations` bei PAT mehrere Zeilen pro Host?
<details><summary>Antwort</summary>

Pro Flow (Protokoll + Quell-/Zielport) eine Übersetzung; die Verbindungstabelle trägt pro Sitzung eigene Einträge.

</details>

3. Wozu braucht man `ip nat inside source static tcp … interface`?
<details><summary>Antwort</summary>

Port-Forwarding: Ein Dienst im Inneren wird über einen bestimmten Port der externen Interface-Adresse erreichbar, ohne eine eigene öffentliche Adresse zu verbrauchen.

</details>

## Prüfungsbezug

Inside Local = interne Host-Adresse, Inside Global = öffentliche Sicht auf den internen Host. NAT ohne Overload braucht ausreichend Poolgröße. Static NAT ist bidirektional, dynamisches NAT nur bei Verkehr von innen. NAT-Reihenfolge vor/nach Routing abhängig von der Richtung. `ip nat inside source` braucht `ip nat inside/outside` an den Interfaces.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/09-NAT-PAT/`](../../CML-Labs/09-NAT-PAT/).
