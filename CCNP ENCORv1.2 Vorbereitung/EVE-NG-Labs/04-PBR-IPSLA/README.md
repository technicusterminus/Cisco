# Lab 04 – Policy-Based Routing mit IP SLA

**Plattform:** EVE-NG · **Dauer:** 75 min · **Niveau:** mittel

Branch-Router mit zwei Providern: bestimmte Quelle per PBR über ISP2, Rest über ISP1. Der PBR-Next-Hop wird per IP SLA und Track überwacht. Dazu Local-PBR für routereigenen Verkehr.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.2.d` | Policy-based Routing | 16 |
| `Ziel::4.4` | IP SLA | 22 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| SW | Network (Bridge) | Kein Gerät, sondern ein **Network**-Objekt (Linux-Bridge) mit Typ *Bridge*. | – |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| R4 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **3.0 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | SW | – |
| H1 | Gi0/0 | SW | – |
| H2 | Gi0/0 | SW | – |
| R1 | Gi0/1 | R2 | Gi0/0 |
| R1 | Gi0/2 | R3 | Gi0/0 |
| R2 | Gi0/1 | R4 | Gi0/0 |
| R3 | Gi0/1 | R4 | Gi0/1 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
 H1 .11 ─┐                 ┌─ R2 (ISP1) ─┐
         SW ── R1 (Branch) ┤             ├─ R4 (Internet: 8.8.8.8, 9.9.9.9)
 H2 .12 ─┘   192.168.1.0/24└─ R3 (ISP2) ─┘
```

| Link | Netz | Seiten |
|---|---|---|
| LAN | 192.168.1.0/24 | R1 .1, H1 .11, H2 .12 |
| R1–R2 (ISP1) | 10.0.12.0/30 | R1 .1 / R2 .2 |
| R1–R3 (ISP2) | 10.0.13.0/30 | R1 .1 / R3 .2 |
| R2–R4 | 10.0.24.0/30 | R2 .1 / R4 .2 |
| R3–R4 | 10.0.34.0/30 | R3 .1 / R4 .2 |

Statisches Routing ist vorgegeben: R1 hat Default via ISP1; R2/R3 haben Default zu R4 und Rückroute ins LAN; R4 kennt 192.168.1.11/32 via R3, den Rest des LANs via R2. R4 hat Lo0 8.8.8.8/32 und Lo1 9.9.9.9/32.

## Teil A – Bauen

1. **Ausgangslage.** Prüfe von H1 und H2 mit `traceroute 8.8.8.8`, dass beide über ISP1 (R2) laufen.
2. **PBR.** H1 (192.168.1.11) soll über ISP2 (R3, 10.0.13.2) laufen, H2 weiter über ISP1. Baue ACL `H1-ONLY`, Route-Map `PBR` (`match ip address`, `set ip next-hop`) und binde sie **eingehend** an das LAN-Interface von R1 (`ip policy route-map`). Prüfe per `traceroute` und `show route-map PBR` (Zähler).
3. **Reihenfolge.** Was passiert mit Verkehr, der keine Route-Map-Sequenz trifft? Was mit Verkehr, der zwar zum `match`, aber zu keinem `set` führt? Wozu dient `set ip default next-hop` im Vergleich zu `set ip next-hop` (Routing-Tabelle zuerst oder PBR zuerst)?
4. **Überwachung.** Baue `ip sla 1` (icmp-echo 10.0.13.2, Quelle Gi0/2, alle 5 s) und **plane ihn ein** (`ip sla schedule 1 life forever start-time now`). Erzeuge `track 1 ip sla 1 reachability` und nutze in der Route-Map `set ip next-hop verify-availability 10.0.13.2 10 track 1`. Schalte R1 Gi0/2 testweise ab: Was geschieht mit H1?
5. **Local PBR.** Pings, die R1 selbst nach 9.9.9.9 sendet, sollen über ISP2 laufen. Warum greift `ip policy` am LAN-Interface nicht für diesen Verkehr, und welcher Befehl ist stattdessen nötig (`ip local policy route-map`)?
6. **Debug.** Nutze `debug ip policy` kurz zur Fehlersuche (danach `undebug all`) und prüfe CEF-Pfad: Warum verliert man mit PBR eventuell Performance, wenn die Plattform es nicht in Hardware kann?

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Die Route-Map ist konfiguriert, aber H1 läuft weiter über ISP1 (`show route-map` zeigt 0 Treffer).

**Ticket 2:** PBR-Route-Map ist am LAN aktiv, aber H1 nimmt nicht den Weg über ISP2.

**Ticket 3:** H1 läuft nicht über ISP2, obwohl ACL und Policy stimmen; `show track 1` ist Down.

**Ticket 4:** H1 hat Internet-Ausfall (Pings zu 8.8.8.8 scheitern), H2 funktioniert; der Pfad bis R3 steht.

## Verifikation

```
traceroute 8.8.8.8               ! auf H1 und H2
show route-map PBR
show ip policy
show ip sla statistics 1
show track 1
show ip route 8.8.8.8
```
Erwartet: H1 geht über 10.0.13.2, H2 über 10.0.12.2, `track 1` Up, `ip sla statistics` mit Erfolgszählern.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Wie beeinflusst `set ip next-hop verify-availability` das Routing?
<details><summary>Antwort</summary>

Der Next-Hop wird nur benutzt, solange das verknüpfte Track-Objekt Up ist. Fällt es, wird die nächste Sequenz oder normales Routing verwendet.

</details>

2. Ein IP-SLA-Echo gelingt nicht, obwohl Ping manuell geht. Was prüfst du?
<details><summary>Antwort</summary>

Quelladresse/Quell-Interface der Operation, `ip sla schedule`, Frequenz/Timeout, ACL/CoPP auf dem Zielpfad und die Frage, ob die Operation überhaupt gestartet ist (`show ip sla configuration`).

</details>

3. Wieso nutzt man PBR statt statischer Route mit Zeit-/AD-Spielereien?
<details><summary>Antwort</summary>

PBR kann nach Quelle, Protokoll oder Port unterscheiden, normales Routing nur nach Ziel.

</details>

## Prüfungsbezug

PBR wirkt nur auf eingehenden Verkehr des Interfaces (Router-eigener Verkehr nur mit `ip local policy`). Ohne `ip sla schedule` läuft keine Messung (Track bleibt down). `set ip next-hop` überschreibt die Routing-Tabelle, `set ip default next-hop` greift nur ohne Tabelleneintrag.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/04-PBR-IPSLA/`](../../CML-Labs/04-PBR-IPSLA/).
