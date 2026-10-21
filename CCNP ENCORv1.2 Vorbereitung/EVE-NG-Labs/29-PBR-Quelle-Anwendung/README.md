# Lab 29 – Policy-Based Routing nach Quelle und Anwendung

**Plattform:** EVE-NG · **Dauer:** 75 min · **Niveau:** mittel

Ein Branch-Router mit zwei Providern: Die Routing-Tabelle sendet alles über Provider A, per PBR wird ein bestimmter Host und Web-Verkehr über Provider B geleitet. Dazu die Wirkung von `deny` in einer PBR-Route-Map, die Reihenfolge der Auswertung und der Unterschied zwischen `ip policy` und `ip local policy`.

**Lernziele:** Nach diesem Lab kannst du …

- Verkehr nach Quelle und nach Anwendung (Port) auf verschiedene Provider lenken.
- Die Wirkung von `permit` und `deny` in einer PBR-Route-Map erklären.
- Mit `show route-map` und `show access-lists` nachweisen, welche Sequenz greift.

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

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/29-PBR-Quelle-Anwendung/`](../../CML-Labs/29-PBR-Quelle-Anwendung/).
