# Lab 29 – Policy-Based Routing nach Quelle und Anwendung

**Dauer:** 75 min · **Niveau:** mittel

Ein Branch-Router mit zwei Providern: Die Routing-Tabelle sendet alles über Provider A, per PBR wird ein bestimmter Host und Web-Verkehr über Provider B geleitet. Dazu die Wirkung von `deny` in einer PBR-Route-Map, die Reihenfolge der Auswertung und der Unterschied zwischen `ip policy` und `ip local policy`.

**Lernziele:** Nach diesem Lab kannst du …

- Verkehr nach Quelle und nach Anwendung (Port) auf verschiedene Provider lenken.
- Die Wirkung von `permit` und `deny` in einer PBR-Route-Map erklären.
- Mit `show route-map` und `show access-lists` nachweisen, welche Sequenz greift.

| ENCOR-Ziel (`Ziel::…`) | Thema |
|---|---|
| 3.2.d | Policy-based Routing |

**So arbeitest du:** Teil A = Bauen, Teil B = Reparieren, Teil C = Üben. Die Konfigurationsdateien liegen in `build/` (Ausgangszustand zum Einfügen in die CLI), `repair/` (fertig gebaut, mit Fehlern) und `solutions/` (Musterlösung und Fehlerliste, erst nach eigenem Versuch öffnen). Anleitung zum Einfügen: siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien).

## Topologie

```mermaid
graph LR
  n0["R1<br/>2911"]
  n1["R2<br/>2911"]
  n2["R3<br/>2911"]
  n3["R4<br/>2911"]
  n4["SW<br/>2960-24TT"]
  n5["H1<br/>PC-PT"]
  n6["H2<br/>PC-PT"]
  n0 ---|"Gi0/0 ↔ Gi0/0"| n1
  n0 ---|"Gi0/1 ↔ Gi0/0"| n2
  n1 ---|"Gi0/1 ↔ Gi0/0"| n3
  n2 ---|"Gi0/1 ↔ Gi0/1"| n3
  n0 ---|"Gi0/2 ↔ Fa0/1"| n4
  n4 ---|"Fa0/2 ↔ Fa0"| n5
  n4 ---|"Fa0/3 ↔ Fa0"| n6
```

**Entwurfsskizze (aus dem CML-Lab; Portnamen der Switches siehe Verkabelungstabelle):**

```
   H1 ─┐                 ┌─ R2 (Provider A) ─┐
       ├─ SW ─ R1 ───────┤                    ├─ R4 (Server 192.0.2.44)
   H2 ─┘   Gi0/2 Gi0/0,Gi0/1└─ R3 (Provider B) ─┘
```

### Geräte

| Gerät | Modell in Packet Tracer | Rolle |
|---|---|---|
| R1 | 2911 | Router |
| R2 | 2911 | Router |
| R3 | 2911 | Router |
| R4 | 2911 | Router |
| SW | 2960-24TT | Switch (im CML-Lab unmanaged; ohne Konfiguration) |
| H1 | PC-PT | Host |
| H2 | PC-PT | Host |

### Verkabelung

| Von | Port | Nach | Port | Kabel |
|---|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 | Copper Cross-Over |
| R1 | Gi0/1 | R3 | Gi0/0 | Copper Cross-Over |
| R2 | Gi0/1 | R4 | Gi0/0 | Copper Cross-Over |
| R3 | Gi0/1 | R4 | Gi0/1 | Copper Cross-Over |
| R1 | Gi0/2 | SW | Fa0/1 | Copper Straight-Through |
| SW | Fa0/2 | H1 | Fa0 | Copper Straight-Through |
| SW | Fa0/3 | H2 | Fa0 | Copper Straight-Through |

### Adressplan (Ausgangszustand)

| Gerät | Interface | Adresse | Maske | Gateway | DNS |
|---|---|---|---|---|---|
| R1 | Gi0/0 | 10.0.12.1 | 255.255.255.252 | | |
| R1 | Gi0/1 | 10.0.13.1 | 255.255.255.252 | | |
| R1 | Gi0/2 | 10.1.0.1 | 255.255.255.0 | | |
| R2 | Gi0/0 | 10.0.12.2 | 255.255.255.252 | | |
| R2 | Gi0/1 | 10.0.24.1 | 255.255.255.252 | | |
| R3 | Gi0/0 | 10.0.13.2 | 255.255.255.252 | | |
| R3 | Gi0/1 | 10.0.34.1 | 255.255.255.252 | | |
| R4 | Loopback0 | 192.0.2.44 | 255.255.255.255 | | |
| R4 | Gi0/0 | 10.0.24.2 | 255.255.255.252 | | |
| R4 | Gi0/1 | 10.0.34.2 | 255.255.255.252 | | |
| H1 | Fa0 (GUI) | 10.1.0.11 | 255.255.255.0 | 10.1.0.1 |  |
| H2 | Fa0 (GUI) | 10.1.0.12 | 255.255.255.0 | 10.1.0.1 |  |

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R1 Gi0/1 – R3 Gi0/0 | 10.0.13.0/30 (.1/.2) |
| R2 Gi0/1 – R4 Gi0/0 | 10.0.24.0/30 (.1/.2) |
| R3 Gi0/1 – R4 Gi0/1 | 10.0.34.0/30 (.1/.2) |
| R1 Gi0/2 – SW | 10.1.0.0/24 (R1 .1, H1 .11, H2 .12) |

R4 hat Loopback0 192.0.2.44/32 als Server. R1 hat nur die Default-Route über R2. Soll: H1 normal über Provider A, H2 **immer** über Provider B, Web-Verkehr (TCP 80) aller Hosts über Provider B.

### Portzuordnung der Switches (CML → Packet Tracer)

Aufgaben, Verkabelung, Konfigurationen und Fehlerlisten verwenden die Packet-Tracer-Ports. Die Tabelle zeigt, welcher Port der CML-Vorlage dazu gehört. Nur die Skizze nennt noch die CML-Ports. Umrechnung: `GiX/Y` → `Fa0/(X·4+Y+1)`.

| Switch | CML-Port | PT-Port |
|---|---|---|
| SW | Gi0/0 | Fa0/1 |
| SW | Gi0/1 | Fa0/2 |
| SW | Gi0/2 | Fa0/3 |

> **Packet-Tracer-Hinweis:** **Eignung: geeignet.** Alle verwendeten Funktionen gibt es in Packet Tracer; Ausgabeformate einzelner `show`-Befehle weichen leicht ab. Die CML-Switches (Gi-Ports) sind hier 3560-24PS bzw. 2960 mit FastEthernet-Ports: Die Portzuordnung steht unter dem Adressplan.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Ausgangslage prüfen.** Die statischen Routen sind gesetzt. Führe auf H1 und H2 `traceroute 192.0.2.44` aus.
   - **Prüfen:** Beide laufen über R2 (Provider A).
2. **Nach Quelle umleiten.** Lege die ACL `H2-ONLY` an (`permit ip host 10.1.0.12 any`). Die Route-Map `PBR` bekommt in Sequenz 10 `match ip address H2-ONLY` und `set ip next-hop 10.0.13.2`. Binde sie mit `ip policy route-map PBR` an Gi0/2.
   - **Prüfen:** `traceroute` von H2 geht jetzt über R3, von H1 weiter über R2.
   - **Denkfrage:** Warum gehört die Policy an Gi0/2 und nicht an die Uplinks?
3. **Nach Anwendung umleiten.** Lege die ACL `WEB` an (`permit tcp any any eq 80`) und hänge sie als Sequenz 20 mit demselben Next-Hop an.
   - **Prüfen:** Ein `telnet 192.0.2.44 80` von H1 lässt in `show route-map PBR` die Zähler von Sequenz 20 steigen, auch wenn dort kein Webserver antwortet.
4. **Reihenfolge testen.** Lege die beiden Regeln testweise in umgekehrter Reihenfolge an.
   - **Denkfrage:** Welche Sequenz greift, wenn ein Paket auf beide passt? Was passiert mit Paketen, die auf keine Sequenz passen, und mit einer `deny`-Sequenz?
5. **Verkehr des Routers selbst.** Pakete, die R1 selbst erzeugt, laufen an `ip policy` vorbei. Mit `ip local policy route-map PBR` gilt die Policy auch für sie.
   - **Denkfrage:** Wann braucht man das?
6. **Ausfall abfangen.**
   - **Denkfrage:** Wie stellst du sicher, dass H2 bei einem Ausfall von Provider B nicht im Leeren landet?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** PBR wirkt nur auf Pakete, die an diesem Interface ankommen. Die Pakete von H1 und H2 kommen an Gi0/2 an. An den Uplinks gehen sie nur hinaus.
- **Zu 4:** Die Sequenz mit der kleinsten Nummer gewinnt, der Rest wird nicht mehr geprüft. Hier haben beide denselben Next-Hop, also ändert sich nur, welcher Zähler steigt. Pakete ohne Treffer und Pakete, die auf eine `deny`-Sequenz passen, werden normal nach der Routing-Tabelle weitergeleitet.
- **Zu 5:** Wenn Pakete des Routers einen bestimmten Weg nehmen sollen, etwa IP-SLA-Messungen, Syslog oder Management-Verkehr über einen bestimmten Provider.
- **Zu 6:** Mit `set ip next-hop verify-availability` und einem Track auf eine IP-SLA-Messung, wie in Lab 04. Oder mit einem zweiten Next-Hop in derselben Zeile (`set ip next-hop 10.0.13.2 10.0.12.2`). IOS nimmt den ersten, der erreichbar ist.

</details>

## Teil B – Reparieren

Baue die Topologie wie oben (oder behalte deine aus Teil A), setze alle Geräte zurück (`erase startup-config`, `reload` bzw. neues Gerät) und füge dann die Dateien aus `repair/` ein. Es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann Layer für Layer eingrenzen, beheben und beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** H2 und Web-Verkehr gehen über Provider A; `show ip policy` ist leer.

**Ticket 2:** H2 nimmt den normalen Weg, die Zähler der Sequenz 10 bleiben 0.

**Ticket 3:** H2 geht über Provider A, obwohl Sequenz 10 auf `permit` steht und in `show route-map PBR` Treffer zählt.

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

| Befehl | Das solltest du sehen |
|---|---|
| `traceroute` von H1 / H2 | H1 über 10.0.12.2, H2 über 10.0.13.2 |
| `show route-map PBR` | steigende Zähler in Sequenz 10 und 20 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. H2 nimmt trotz Policy den Weg über Provider A. Welche vier Dinge prüfst du?
<details><summary>Antwort</summary>

**Interface, Route-Map, ACL und Next-Hop.** 1) Hängt `ip policy route-map` am Eingangs-Interface? 2) Steht die Sequenz auf `permit`, und stimmt die Reihenfolge? 3) Trifft die ACL die Quelle (Zähler in `show access-lists`)? 4) Ist der Next-Hop direkt erreichbar (ARP, Route)?

</details>

2. Was bewirkt `set ip default next-hop` im Unterschied zu `set ip next-hop`?
<details><summary>Antwort</summary>

**`default` greift nur, wenn es keine spezifische Route gibt.** `set ip next-hop` wirkt immer, noch vor der Routing-Tabelle. `set ip default next-hop` wird nur benutzt, wenn die Tabelle für das Ziel keine spezifischere Route als die Default hat.

</details>

3. Warum greift PBR nicht auf Pakete, die der Router selbst erzeugt?
<details><summary>Antwort</summary>

**Weil `ip policy` nur auf Pakete wirkt, die am Interface ankommen.** Pakete, die der Router selbst erzeugt, kommen nirgends an. Für sie gibt es `ip local policy route-map`.

</details>

## Prüfungsbezug
- PBR entscheidet vor dem normalen Routing, und nur für Pakete, die am Interface ankommen. Für eigene Pakete gibt es `ip local policy`.
- Match über ACL oder Paketlänge. Set: Next-Hop, Interface, DSCP, Default-Next-Hop.
- Ohne Treffer und bei `deny` wird normal geroutet.
- Ist der Next-Hop nicht erreichbar, fällt das Paket auf die Routing-Tabelle zurück.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
