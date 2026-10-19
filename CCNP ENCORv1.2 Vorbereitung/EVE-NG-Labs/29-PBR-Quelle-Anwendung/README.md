# Lab 29 – Policy-Based Routing nach Quelle und Anwendung

**Plattform:** EVE-NG · **Dauer:** 75 min · **Niveau:** mittel

Ein Branch-Router mit zwei Providern: Die Routing-Tabelle sendet alles über Provider A, per PBR wird ein bestimmter Host und Web-Verkehr über Provider B geleitet. Dazu die Wirkung von `deny` in einer PBR-Route-Map, die Reihenfolge der Auswertung und der Unterschied zwischen `ip policy` und `ip local policy`.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.2.d` | Policy-based Routing | 16 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| R4 | Cisco vIOS Router |  | 512 |
| SW | Network (Bridge) | Kein Gerät, sondern ein **Network**-Objekt (Linux-Bridge) mit Typ *Bridge*. | – |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **3.0 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R1 | Gi0/1 | R3 | Gi0/0 |
| R2 | Gi0/1 | R4 | Gi0/0 |
| R3 | Gi0/1 | R4 | Gi0/1 |
| R1 | Gi0/2 | SW | – |
| SW | – | H1 | Gi0/0 |
| SW | – | H2 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
   H1 ─┐                 ┌─ R2 (Provider A) ─┐
       ├─ SW ─ R1 ───────┤                    ├─ R4 (Server 192.0.2.44)
   H2 ─┘   Gi0/2 Gi0/0,Gi0/1└─ R3 (Provider B) ─┘
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R1 Gi0/1 – R3 Gi0/0 | 10.0.13.0/30 (.1/.2) |
| R2 Gi0/1 – R4 Gi0/0 | 10.0.24.0/30 (.1/.2) |
| R3 Gi0/1 – R4 Gi0/1 | 10.0.34.0/30 (.1/.2) |
| R1 Gi0/2 – SW | 10.1.0.0/24 (R1 .1, H1 .11, H2 .12) |

R4 hat Loopback0 192.0.2.44/32 als Server. R1 hat nur die Default-Route über R2. Soll: H1 normal über Provider A, H2 **immer** über Provider B, Web-Verkehr (TCP 80) aller Hosts über Provider B.

## Teil A – Bauen

1. **Ausgangszustand.** Statische Routen sind gesetzt. Prüfe `traceroute 192.0.2.44` von H1 und H2: Beide gehen über R2.
2. **Quellbasiert.** ACL `H2-ONLY` (`permit ip host 10.1.0.12 any`), Route-Map `PBR` Sequenz 10 mit `match ip address H2-ONLY` und `set ip next-hop 10.0.13.2`. Am Interface `Gi0/2` `ip policy route-map PBR`. Traceroute von H2: nun über R3, H1 weiter über R2. Warum wirkt die Policy am **Eingangs**-Interface?
3. **Anwendungsbasiert.** ACL `WEB` (`permit tcp any any eq 80`), Sequenz 20 mit demselben Next-Hop. Prüfe mit `show ip policy` und `show route-map PBR` die Zähler (Matches). Wie testest du TCP 80 ohne Server? (`debug ip policy`, `telnet 192.0.2.44 80`.)
4. **Reihenfolge.** Vertausche testweise Sequenz 10 und 20 (neue Nummern): Was ändert sich, wenn ein Paket auf beide Regeln passt? Was passiert mit Paketen, die auf **keine** Sequenz passen (normale Routing-Entscheidung) und mit `deny`-Sequenzen?
5. **Lokaler Verkehr.** R1-eigene Pakete umgeht `ip policy`. Mit `ip local policy route-map PBR` greift die Policy auch für sie. Wann braucht man das?
6. **Robustheit.** Wie würdest du Ausfall von Provider B abfangen (`set ip next-hop verify-availability` mit Track/IP SLA, oder `set ip next-hop … 10.0.12.2` als zweiter Eintrag)? Siehe Lab 04.

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** H2 und Web-Verkehr gehen über Provider A; `show ip policy` ist leer.

**Ticket 2:** H2 nimmt den normalen Weg, die Zähler der Sequenz 10 bleiben 0.

**Ticket 3:** H2 verliert die Verbindung zum Server (Timeouts), H1 ist unbeeinträchtigt.

**Ticket 4:** H2 geht über Provider A, obwohl ACL und Next-Hop stimmen; nur Web-Verkehr (Sequenz 20) wird umgeleitet.

**Ticket 5:** H2 (über Provider B) erreicht den Server nicht; die Traceroute endet bei R3.

## Verifikation

```
show ip policy
show route-map PBR
traceroute 192.0.2.44        ! von H1 und H2
debug ip policy              ! kurz, nur im Lab
show ip route 0.0.0.0
```
Erwartet: H1 geht über 10.0.12.2, H2 über 10.0.13.2; Zähler in `show route-map PBR` steigen.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. H2 nimmt trotz Policy den Weg über Provider A. Welche vier Dinge prüfst du?
<details><summary>Antwort</summary>

1) `ip policy route-map` am richtigen (Eingangs-)Interface, 2) Route-Map `permit` und Sequenz-Reihenfolge, 3) ACL trifft die Quelle (Zähler in `show access-lists`), 4) Next-Hop ist direkt erreichbar (ARP/Route).

</details>

2. Was bewirkt `set ip default next-hop` im Unterschied zu `set ip next-hop`?
<details><summary>Antwort</summary>

`default` wirkt nur, wenn die Routing-Tabelle **keine** spezifische Route für das Ziel hat; `next-hop` gilt immer vor der Tabelle.

</details>

3. Warum greift PBR nicht auf Pakete, die der Router selbst erzeugt?
<details><summary>Antwort</summary>

`ip policy` wird auf eingehende Pakete des Interfaces angewandt. Router-eigene Pakete laufen durch `ip local policy`.

</details>

## Prüfungsbezug

PBR entscheidet vor dem normalen Routing, nur für **eingehenden** Verkehr am Interface (lokal mit `ip local policy`). Match über ACL, Paketlänge; Set: Next-Hop, Interface, DSCP, Default-Next-Hop. Bei `permit` ohne Match auf ein Set wird normal geroutet; `deny` heißt: nicht per Policy, sondern normales Routing. Fehlt der Next-Hop, fällt das Paket auf die Routing-Tabelle zurück (außer `set interface`/`default`-Varianten mit Unterschieden).

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/29-PBR-Quelle-Anwendung/`](../../CML-Labs/29-PBR-Quelle-Anwendung/).
