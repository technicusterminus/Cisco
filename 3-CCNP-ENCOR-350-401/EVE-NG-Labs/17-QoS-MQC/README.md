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

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

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
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Trust Boundary festlegen.** H1 und H2 sind vertrauenswürdig, ihre Markierung bleibt. H3 (Gast) wird auf DSCP 0 zurückgesetzt. Baue dafür eine ACL für H3, eine `class-map` darauf und eine `policy-map MARK` mit `set dscp default`. Binde sie mit `service-policy input MARK` an Gi0/0.
   - **Prüfen:** `show policy-map interface Gi0/0` zählt Pakete in der Gast-Klasse, sobald H3 sendet.
   - **Denkfrage:** Warum darf man nicht jedem Endgerät seine Markierung glauben?
2. **Klassen anlegen.** Lege an: `class-map match-any VOICE` mit `match dscp ef`, `VIDEO` mit `match dscp af41` und `CRIT` mit `match dscp af31`.
   - **Denkfrage:** Wann ist `match-any` nötig, und was passiert bei `match-all` mit zwei verschiedenen DSCP-Werten?
3. **Warteschlangen (Child-Policy).** Baue `policy-map QUEUE`: VOICE mit `priority percent 20`, VIDEO mit `bandwidth percent 30`, CRIT mit `bandwidth percent 25`, `class class-default` mit `fair-queue` und `random-detect dscp-based`.
   - **Denkfrage:** Was unterscheidet die Priority-Queue (LLQ) von `bandwidth` (CBWFQ)?
4. **Shaper als Parent.** Baue `policy-map WAN` mit `class class-default`, darin `shape average 2000000` und `service-policy QUEUE`. Binde sie mit `service-policy output WAN` an Gi0/1.
   - **Prüfen:** `show policy-map interface Gi0/1` zeigt den Shaper mit 2 Mbit/s und darunter die vier Klassen.
   - **Denkfrage:** Warum braucht man den Shaper, obwohl Gi0/1 viel schneller ist?
5. **Gast begrenzen.** Ergänze in der Gast-Klasse von `MARK` einen Policer: `police rate 256000 bps conform-action transmit exceed-action drop`.
   - **Denkfrage:** Was ist der Unterschied zwischen Policing und Shaping?
6. **Unter Last testen.** Pinge gleichzeitig von H1 (`tos 184`), H2 (`tos 136`) und H3 mit `repeat 1000 size 1200` zu SRV.
   - **Prüfen:** `show policy-map interface Gi0/1` zeigt Pakete pro Klasse und Drops. Die meisten Drops entstehen in `class-default`.
   - **Denkfrage:** Warum verliert `class-default` zuerst Pakete und nicht VIDEO?
7. **Begriffe ordnen.**
   - **Denkfrage:** Was bedeuten EF, AF, CS und BE? Was ist der Unterschied zwischen Tail Drop und WRED und zwischen Congestion Management und Congestion Avoidance?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Jedes Endgerät kann seine Pakete selbst als EF markieren. Ein Gast würde damit der echten Sprache die Priority-Queue wegnehmen. Deshalb vertraut man Markierungen nur ab einer festgelegten Grenze, meist am Access-Port, und nur bei bekannten Geräten wie IP-Telefonen.
- **Zu 2:** `match-any` trifft, sobald eine der Bedingungen passt. Bei nur einer Bedingung ist es gleich, ob any oder all. `match-all` mit zwei verschiedenen DSCP-Werten trifft nie, weil ein Paket nur einen DSCP-Wert hat.
- **Zu 3:** Die Priority-Queue wird immer zuerst bedient, das hält Verzögerung und Jitter klein. Damit sie die anderen nicht aushungert, begrenzt ein eingebauter Policer sie bei Stau auf die konfigurierte Rate. `bandwidth` garantiert nur einen Mindestanteil, ohne Vorrang.
- **Zu 4:** Warteschlangen greifen nur, wenn das Interface selbst überlastet ist. Gi0/1 schafft weit mehr als 2 Mbit/s, also staut sich beim Router nichts. Der Provider würde stattdessen wahllos verwerfen. Der Shaper erzeugt den Engpass von 2 Mbit/s im Router selbst, und erst damit wirken die Warteschlangen.
- **Zu 5:** Policing verwirft oder markiert um, was über der Rate liegt, sofort und ohne Puffer. Es geht in beide Richtungen. Shaping puffert den Überschuss und sendet ihn später. Das glättet den Verkehr, kostet aber Verzögerung, und geht nur ausgehend.
- **Zu 6:** VIDEO hat 30 % fest zugesagt. `class-default` hat keine Zusage und bekommt nur, was übrig bleibt. WRED verwirft dort außerdem schon früh.
- **Zu 7:** EF (Expedited Forwarding) für Sprache, AF (Assured Forwarding) in vier Klassen mit je drei Drop-Stufen, CS (Class Selector) kompatibel zu IP Precedence, BE (Best Effort) = DSCP 0. Tail Drop verwirft erst, wenn die Warteschlange voll ist, und trifft dann alle Verbindungen gleichzeitig. WRED verwirft vorher zufällig und nach Markierung gewichtet. Congestion Management heißt einreihen und bedienen (CBWFQ, LLQ). Congestion Avoidance heißt Stau vermeiden, bevor er entsteht (WRED).

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

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

| Befehl | Das solltest du sehen |
|---|---|
| `show policy-map interface Gi0/1` | VOICE zählt Pakete mit DSCP 46, ohne Drops, solange H1 unter 20 % bleibt |
| | `class-default` verwirft bei Überlast |
| `show policy-map interface Gi0/0` | Gast-Verkehr im Policer als exceeded |

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
- DSCP: EF = 46, AF41 = 34, AF31 = 26, CS3 = 24, BE = 0.
- Policing wirkt ein- und ausgehend, Shaping nur ausgehend.
- `priority` (LLQ) hat immer einen eingebauten Policer.
- Mit `bandwidth` lassen sich standardmäßig höchstens 75 % der Interface-Bandbreite vergeben.
- Warteschlangen greifen nur bei Überlast. Auf schnellen Ethernet-Interfaces braucht es dafür oft einen Shaper als Parent.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/17-QoS-MQC/`](../../CML-Labs/17-QoS-MQC/).
