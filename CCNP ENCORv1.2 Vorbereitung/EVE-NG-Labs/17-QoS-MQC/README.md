# Lab 17 – QoS mit MQC: Markieren, Policing, Shaping, LLQ

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel bis schwer

Branch-Router mit schmaler WAN-Strecke (2 Mbit/s): Klassifizieren und Markieren am Rand, Hierarchical Shaping mit Child-Queueing (LLQ/CBWFQ) am WAN-Ausgang, Policing auf dem Gast-Netz und WRED. Verkehr erzeugst du mit Pings und DSCP-Werten (`tos`).

**Lernziele:** Nach diesem Lab kannst du …

- Verkehr mit MQC klassifizieren und markieren.
- LLQ, Policing und Shaping konfigurieren und ihre Wirkung an den Zählern ablesen.
- Die Trust Boundary begründen und Fehler in Klassen und Bindungen finden.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::1.4` | QoS-Konfigurationen | 48 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| SW | Network (Bridge) | Kein Gerät, sondern ein **Network**-Objekt (Linux-Bridge) mit Typ *Bridge*. | – |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H3 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| SRV | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **3.0 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **1.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | SW | – |
| H1 | Gi0/0 | SW | – |
| H2 | Gi0/0 | SW | – |
| H3 | Gi0/0 | SW | – |
| R1 | Gi0/1 | R2 | Gi0/0 |
| R2 | Gi0/1 | SRV | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
 H1 (Voice) ─┐
 H2 (Video) ─┼─ SW ── R1 ═══ WAN (shaped 2 Mbit/s) ═══ R2 ── SRV
 H3 (Gast)  ─┘      Gi0/0    Gi0/1                       Gi0/0
```

| Link | Netz |
|---|---|
| LAN | 192.168.10.0/24 (R1 .1, H1 .11, H2 .12, H3 .13) |
| R1 Gi0/1 – R2 Gi0/0 | 10.0.12.0/30 (R1 .1, R2 .2) |
| R2 Gi0/1 – SRV | 10.0.20.0/24 (R2 .1, SRV .10) |

Statische Routen sind vorhanden. Ping-Quellen: H1 Ping mit `tos 184` (EF, DSCP 46), H2 mit `tos 136` (AF41), H3 ohne Markierung.

## Teil A – Bauen

1. **Trust Boundary.** Entscheide, welchen Hosts du die Markierung glaubst. H1 und H2 sind vertrauenswürdig (DSCP bleibt), H3 (Gast) wird auf DSCP 0 umgeschrieben. Baue am LAN-Interface (Gi0/0, input) `policy-map MARK`: `class-map` per ACL für H3 → `set dscp default`.
2. **Klassen.** `class-map match-any VOICE` (`match dscp ef`), `VIDEO` (`match dscp af41`), `CRIT` (`match dscp af31`). Warum `match-any`, wenn mehrere Kriterien alternativ gelten (und was macht `match-all` bei zwei sich ausschließenden DSCP-Werten)?
3. **Child-Policy (Queueing).** `policy-map QUEUE`: VOICE `priority percent 20` (LLQ, impliziter Policer), VIDEO `bandwidth percent 30`, CRIT `bandwidth percent 25`, `class class-default` `fair-queue` mit `random-detect dscp-based`. Wie wirkt LLQ gegenüber CBWFQ (strikte Priorität, aber begrenzt)?
4. **Parent-Shaper.** `policy-map WAN`: `class class-default` → `shape average 2000000` (2 Mbit/s!) und `service-policy QUEUE`. Wende an: `interface Gi0/1` → `service-policy output WAN`. Warum muss man shapen, wenn die physische Schnittstelle schneller ist als der gebuchte Provider-Rate?
5. **Policing Gast.** Am LAN-Interface zusätzlich H3-Verkehr mit `police rate 256000 bps conform-action transmit exceed-action drop` begrenzen. Unterschied Policing (verwerfen/remarken, kein Puffer) und Shaping (puffern, glätten).
6. **Testen.** Von H1, H2, H3 Pings (`repeat 1000 size 1200`) mit den DSCP-Werten Richtung SRV, gleichzeitig. Lies `show policy-map interface Gi0/1`: Pakete pro Klasse, Drops, Queue-Tiefe. Wann tritt Verlust in `class-default` vor dem in VIDEO auf?
7. **Konzepte.** Erkläre DiffServ-PHBs (EF, AF, CS, BE), DSCP/IP-Precedence/CoS, Tail Drop vs. WRED, Congestion Avoidance vs. Congestion Management, Trust-Modelle in Campus (Trust Boundary am Access-Port, `mls qos trust`/AutoQoS).

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Die Klasse VOICE bleibt in `show policy-map interface` bei null Paketen, obwohl H1 mit DSCP 46 sendet.

**Ticket 2:** Der WAN-Link wird überfüllt, Voice leidet, `show policy-map interface Gi0/1` zeigt keine Policy.

**Ticket 3:** Der Durchsatz Richtung SRV bricht auf einen winzigen Bruchteil ein, Pings dauern extrem lang.

**Ticket 4:** Der Gast (H3) wird als Voice klassifiziert und nimmt der echten Sprache die Priority-Queue weg.

## Verifikation

```
show policy-map interface GigabitEthernet0/1
show policy-map interface GigabitEthernet0/0
show class-map
show ip interface Gi0/1 | include service
```
Erwartet: Klasse VOICE zählt Pakete (DSCP 46), Priorität nie gedroppt, `class-default` droppt bei Überlast, Gast-Verkehr als `exceed` im Policer.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Warum sind EF-Pakete in der LLQ trotzdem nicht unbegrenzt?
<details><summary>Antwort</summary>

**Weil ein eingebauter Policer die Priority-Queue begrenzt.** Sie darf nur die konfigurierte Rate nutzen, wenn es eng wird. Sonst könnte Sprache alle anderen Klassen aushungern.

</details>

2. `show policy-map interface` zeigt in der Klasse VIDEO null Pakete, obwohl Video läuft. Was prüfst du?
<details><summary>Antwort</summary>

**Die Match-Bedingung, die Bindung und ob vorher umgeschrieben wird.** Passt der DSCP-Wert? Steht da `match-all` mit mehreren Werten? Wird DSCP auf dem Weg überschrieben? Hängt die Policy am richtigen Interface in der richtigen Richtung?

</details>

3. Wann `police` statt `shape` für das Gästenetz?
<details><summary>Antwort</summary>

**Wenn Überschuss sofort verworfen werden soll.** Policing setzt eine harte Obergrenze ohne Puffer. Shaping würde Gast-Pakete zwischenspeichern und dadurch Verzögerung erzeugen.

</details>

## Prüfungsbezug

DSCP: EF = 46, AF41 = 34, AF31 = 26, CS3 = 24, BE = 0. Policing wirkt in/out, Shaping nur out. LLQ = `priority`, immer mit Policer. `bandwidth` summiert max. 75 % der Interface-Bandbreite (Default `max-reserved-bandwidth`). Queueing greift nur bei Überlast, auf Ethernet-Interfaces braucht man oft einen Shaper als Parent.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/17-QoS-MQC/`](../../CML-Labs/17-QoS-MQC/).
