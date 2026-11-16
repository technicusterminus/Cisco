# Lab 34 – OSPF: Routen filtern (ABR, ASBR, lokal) und Nachbarschaften mit Netztyp- und MTU-Fehlern

**Plattform:** EVE-NG · **Dauer:** 110 min · **Niveau:** schwer

Das Blueprint nennt bei OSPF ausdrücklich Filterung, Nachbarschaft und die Netztypen Point-to-Point und Broadcast. Lab 01 und 28 decken Areas, Summaries und Authentisierung ab, gefiltert wird dort nicht. Hier lernst du die vier Stellen kennen, an denen OSPF Routen zurückhalten kann, und warum es innerhalb einer Area keine fünfte gibt. Dazu kommen zwei Nachbarschaftsfehler, die in `show ip ospf neighbor` harmlos aussehen.

**Lernziele:** Nach diesem Lab kannst du …

- Type-3-LSAs am ABR mit `area … filter-list` in beide Richtungen filtern und die Richtung begründen.
- `area range … not-advertise`, `distribute-list in` und eine Route-Map an der Redistribution voneinander abgrenzen.
- Erklären, warum `distribute-list in` die LSDB nicht verändert und wann das gefährlich wird.
- Einen Netztyp-Konflikt (Nachbar FULL, aber keine Routen) und einen MTU-Konflikt (EXSTART) erkennen.
- Zu einer Vorgabe („Area 2 darf Netz X nicht sehen“) das passende Werkzeug und den richtigen Router wählen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.2.b` | OSPFv2 und OSPFv3 | 86 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| R4 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.0 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R2 | Gi0/1 | R3 | Gi0/0 |
| R1 | Gi0/1 | R4 | Gi0/0 |

## Topologie

```
        Area 1                    Area 0                    Area 2
  R3 ──────────────── R2 ──────────────── R1 ──────────────── R4
     Gi0/0      Gi0/1    Gi0/0      Gi0/0    Gi0/1      Gi0/0
  Lo16–19                (ABR)             (ABR)           Lo20, Lo21
  10.1.16–19.0/24                                          10.2.20.0/24, 10.2.21.0/24
                                                           statisch: 198.51.100.0/24, 203.0.113.0/24 (ASBR)
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2), Area 0 |
| R2 Gi0/1 – R3 Gi0/0 | 10.0.23.0/30 (.1/.2), Area 1 |
| R1 Gi0/1 – R4 Gi0/0 | 10.0.14.0/30 (.1/.2), Area 2 |
| R3 Loopback16 bis 19 | 10.1.16.1/24 bis 10.1.19.1/24, Area 1 |
| R4 Loopback20, 21 | 10.2.20.1/24, 10.2.21.1/24, Area 2 |
| R4 statisch auf Null0 | 198.51.100.0/24 und 203.0.113.0/24 |

Loopback0: R1 10.255.0.1 bis R4 10.255.0.4 (/32), jeweils in der Area des Routers (R1 und R2 in Area 0). Adressen und die beiden statischen Routen auf R4 sind vorhanden, OSPF baust du selbst.

**Vorgaben, die am Ende gelten sollen:**

1. Area 1 erscheint außerhalb als 10.1.16.0/23 plus 10.1.18.0/24.
2. 10.1.19.0/24 verlässt Area 1 nie.
3. Area 2 kennt 10.1.18.0/24 nicht, Area 0 schon.
4. R3 trägt 10.2.21.0/24 nicht in seine Routing-Tabelle ein.
5. Von den statischen Routen auf R4 gelangt nur 198.51.100.0/24 ins OSPF.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A. Bei **Erst vorhersagen** schreibst du deine Erwartung auf, *bevor* du den Befehl eingibst. Lag die Vorhersage daneben, hast du genau die Stelle gefunden, an der dein Modell noch nicht stimmt. Die Auflösung steht ebenfalls bei den Antworten.

1. **OSPF aufbauen.** Starte auf allen Routern `router ospf 1` mit der Loopback0-Adresse als Router-ID. Aktiviere OSPF am Interface (`ip ospf 1 area X`) laut Skizze. Setze auf allen Gi-Links und allen Loopbacks außer Loopback0 `ip ospf network point-to-point`.
   - **Prüfen:** `show ip ospf neighbor` zeigt überall `FULL/  -`. R4 sieht 10.1.16.0/24 bis 10.1.19.0/24 als `O IA` mit Maske /24.
   - **Denkfrage:** Warum steht bei den Nachbarn kein DR? Und wozu der Netztyp an den Loopbacks?
2. **Netztyp-Konflikt.** Entferne auf R1 Gi0/0 `ip ospf network point-to-point`, R2 bleibt unverändert. Warte eine Minute.
   - **Erst vorhersagen:** Bleibt die Nachbarschaft R1–R2 bestehen? Und was steht danach in `show ip route ospf` auf R1?
   - **Prüfen:** `show ip ospf neighbor` zeigt auf beiden Seiten wieder `FULL`. `show ip route ospf` auf R1 enthält trotzdem keine Route mehr, die über R2 führt. `show ip ospf interface Gi0/0 | include Network Type` nennt auf R1 BROADCAST, auf R2 POINT_TO_POINT. Stelle den Netztyp danach wieder her.
   - **Denkfrage:** Die Hello-Timer passen (10/40), deshalb kommt die Nachbarschaft zustande. Warum rechnet SPF den Link dann nicht ein?
3. **MTU-Konflikt.** Setze auf R3 Gi0/0 `ip mtu 1400` und führe dort `clear ip ospf process` aus.
   - **Erst vorhersagen:** In welchem Zustand bleibt die Nachbarschaft R2–R3 stehen?
   - **Prüfen:** `show ip ospf neighbor` auf R2 zeigt R3 dauerhaft in `EXSTART`. `debug ip ospf adj` meldet, dass der Nachbar eine größere bzw. kleinere Interface-MTU hat. Entferne `ip mtu 1400` wieder.
   - **Denkfrage:** `ip ospf mtu-ignore` würde die Nachbarschaft herstellen. Warum ist das meist die falsche Lösung?
4. **Zusammenfassen.** Setze auf R2 `area 1 range 10.1.16.0 255.255.254.0`.
   - **Erst vorhersagen:** Welche Routen aus Area 1 sieht R1 jetzt, und welche neue Route erscheint auf R2 selbst?
   - **Prüfen:** R1: 10.1.16.0/23, 10.1.18.0/24, 10.1.19.0/24 als `O IA`. R2: zusätzlich `O 10.1.16.0/23 is a summary, Null0`.
5. **Filtern beim Verlassen einer Area.** Vorgabe 2. Lege auf R2 die Prefix-Liste `A1-OUT` an (`deny 10.1.19.0/24`, dann `permit 0.0.0.0/0 le 32`) und setze `area 1 filter-list prefix A1-OUT out`.
   - **Erst vorhersagen:** Auf welchen Routern verschwindet 10.1.19.0/24: R1, R2, R4?
   - **Prüfen:** R1 und R4 kennen das Netz nicht mehr, `show ip ospf database summary 10.1.19.0` ist dort leer. R2 hat es weiter als `O` (Intra-Area).
   - **Denkfrage:** Was wäre passiert, wenn du die Zeile `permit 0.0.0.0/0 le 32` vergessen hättest?
6. **Filtern beim Eintritt in eine Area.** Vorgabe 3. Lege auf R1 die Prefix-Liste `A2-IN` an (`deny 10.1.18.0/24`, dann alles erlauben) und setze `area 2 filter-list prefix A2-IN in`.
   - **Erst vorhersagen:** Hat R1 selbst die Route 10.1.18.0/24 noch?
   - **Prüfen:** R1: ja, als `O IA`. R4: nein. 10.1.16.0/23 ist auf R4 weiter vorhanden.
   - **Denkfrage:** `in` und `out` beziehen sich auf die genannte Area, nicht auf ein Interface. Formuliere beide Richtungen in einem Satz.
7. **`not-advertise` zum Vergleich.** Ändere auf R2 testweise die Zeile zu `area 1 range 10.1.16.0 255.255.254.0 not-advertise`.
   - **Erst vorhersagen:** Was sieht R1 jetzt von 10.1.16.0/24 und 10.1.17.0/24?
   - **Prüfen:** Weder die Summary noch die beiden Einzelnetze erscheinen auf R1. Stelle danach die Zeile ohne `not-advertise` wieder her.
8. **Lokal filtern.** Vorgabe 4. Lege auf R3 die Prefix-Liste `NO-21` an (`deny 10.2.21.0/24`, dann alles erlauben) und setze unter `router ospf 1` den Befehl `distribute-list prefix NO-21 in`.
   - **Erst vorhersagen:** Zwei Fragen: Steht 10.2.21.0/24 noch in `show ip route` auf R3? Steht es noch in `show ip ospf database summary 10.2.21.0` auf R3?
   - **Prüfen:** Routing-Tabelle: nein. LSDB: ja, unverändert.
   - **Denkfrage:** Warum kann OSPF innerhalb einer Area keine LSAs filtern? Und wann erzeugt `distribute-list in` ein schwarzes Loch?
9. **Am ASBR filtern.** Vorgabe 5. Lege auf R4 die Prefix-Liste `EXT-OK` (`permit 198.51.100.0/24`) und die Route-Map `EXT` an, die nur diese Liste erlaubt. Verteile mit `redistribute static subnets route-map EXT`.
   - **Prüfen:** R3 hat `O E2 198.51.100.0/24`. 203.0.113.0/24 fehlt überall außer auf R4. `show ip ospf database external` zeigt genau ein Type-5-LSA.
   - **Denkfrage:** Welche Alternative gibt es am ASBR, um eine externe Route zu unterdrücken, ohne die Route-Map anzufassen?
10. **Zuordnen.** Fülle aus dem Gedächtnis aus: Für **`area filter-list`**, **`area range not-advertise`**, **`distribute-list in`**, **Route-Map an `redistribute`** und **`summary-address not-advertise`** jeweils: Auf welchem Router? Welcher LSA-Typ ist betroffen? Wirkt es auf andere Router?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Auf einem Point-to-Point-Link gibt es nur zwei Router, eine DR-Wahl wäre überflüssig und kostet beim Start 40 Sekunden Wartezeit. Loopbacks meldet OSPF sonst als Host-Route /32, egal welche Maske konfiguriert ist. Mit dem Netztyp Point-to-Point erscheint die echte Maske.
- **Zu 2:** Die Nachbarschaft wird wieder **FULL**, aber die Routen fehlen. R1 beschreibt den Link in seinem Router-LSA als Transit-Netz mit einem DR und erwartet ein Network-LSA. R2 beschreibt denselben Link als Point-to-Point direkt zum Nachbarn. Die beiden Beschreibungen passen nicht zusammen, SPF findet keine beidseitige Verbindung und lässt den Link aus. FULL heißt nur: Die Datenbanken sind gleich. Es heißt nicht, dass ihr Inhalt einen Weg ergibt.
- **Zu 3:** In **EXSTART** (teils im Wechsel mit EXCHANGE). Die MTU steht im Database-Description-Paket. Ist die des Nachbarn größer als die eigene, verwirft der Router das Paket. `ip ospf mtu-ignore` schaltet nur die Prüfung ab. Die MTU bleibt ungleich, große LSA-Pakete und später der Nutzverkehr können trotzdem hängen bleiben. Richtig ist, die MTU auf beiden Seiten gleich zu setzen.
- **Zu 4:** R1 sieht die Summary 10.1.16.0/23 statt .16 und .17, dazu .18 und .19 einzeln, weil sie außerhalb des Bereichs liegen. R2 legt eine Discard-Route auf Null0 an: Pakete an einen nicht vorhandenen Teil der Summary werden verworfen statt einer Default-Route zu folgen (Schleifenschutz).
- **Zu 5:** Auf **R1 und R4**. R2 behält die Route, denn es ist selbst Mitglied von Area 1 und rechnet sie aus den Type-1-LSAs. Der Filter wirkt nur auf die Type-3-LSAs, die R2 aus Area 1 heraus erzeugt. Ohne die `permit`-Zeile greift das stille `deny` am Ende jeder Prefix-Liste: Kein einziges Netz aus Area 1 käme mehr hinaus.
- **Zu 6:** **Ja.** R1 erhält das Type-3-LSA in Area 0 und nutzt es. Der Filter verhindert nur, dass R1 es nach Area 2 weitergibt. Merksatz: `area X filter-list … in` filtert, was **in Area X hinein** angekündigt wird, `out` filtert, was **aus Area X heraus** angekündigt wird. Beides passiert auf dem ABR dieser Area.
- **Zu 7:** **Nichts mehr.** `not-advertise` unterdrückt die Summary und zugleich alle Einzelnetze, die in den Bereich fallen. Es ist die kürzeste Art, einen ganzen Adressblock zu verbergen.
- **Zu 8:** Routing-Tabelle **nein**, LSDB **ja**. Alle Router einer Area müssen dieselbe Datenbank haben, sonst rechnet SPF auf jedem Router einen anderen Baum und es entstehen Schleifen. Deshalb filtert `distribute-list in` erst nach der SPF-Berechnung, beim Eintrag in die eigene Tabelle. Gefährlich wird es, wenn ein Router auf dem Transitweg filtert: Seine Nachbarn schicken ihm weiter Pakete für das Netz, er selbst hat keine Route und verwirft sie.
- **Zu 9:** `summary-address 203.0.113.0 255.255.255.0 not-advertise` unter `router ospf`. Das wirkt auf externe Routen am ASBR so wie `area range … not-advertise` auf Inter-Area-Routen am ABR.
- **Zu 10:** **`area filter-list`:** ABR, Type 3, wirkt auf alle Router dahinter. **`area range not-advertise`:** ABR, Type 3 für einen ganzen Block. **`distribute-list in`:** jeder Router, kein LSA betroffen, wirkt nur lokal. **Route-Map an `redistribute`:** ASBR, Type 5 (oder 7), wirkt auf alle. **`summary-address not-advertise`:** ASBR, Type 5/7.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** R1 und R2 zeigen einander als `FULL`, aber R1 lernt keine einzige Route über R2 und umgekehrt.

**Ticket 2:** R3 kommt mit R2 nicht über `EXSTART` hinaus.

**Ticket 3:** Aus Area 1 ist außerhalb gar kein Netz mehr sichtbar, auch die Summary 10.1.16.0/23 nicht. Innerhalb von Area 1 ist alles in Ordnung.

**Ticket 4:** R4 hat eine Route nach 10.1.18.0/24. Laut Vorgabe 3 darf Area 2 dieses Netz nicht kennen.

**Ticket 5:** 198.51.100.0/24 fehlt im ganzen Netz als externe Route. Auf R4 ist die statische Route vorhanden.

## Verifikation
```
show ip ospf neighbor
show ip ospf interface brief
show ip route ospf
show ip ospf database summary               ! Type 3
show ip ospf database external              ! Type 5
show ip prefix-list
show route-map EXT                          ! auf R4
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip route ospf` auf R1 | 10.1.16.0/23 und 10.1.18.0/24 als `O IA`, kein 10.1.19.0/24 |
| `show ip route ospf` auf R4 | 10.1.16.0/23 als `O IA`, weder 10.1.18.0/24 noch 10.1.19.0/24 |
| `show ip route 10.2.21.0` auf R3 | kein Treffer (oder nur eine Default-Route), 10.2.20.0/24 ist vorhanden |
| `show ip route ospf` auf R3 | `O E2 198.51.100.0/24`, kein 203.0.113.0/24 |
| `show ip ospf neighbor` überall | `FULL/  -` |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Vorgabe: „Area 2 soll von außen nur eine Default-Route sehen.“ Brauchst du dafür eine Filterliste?
<details><summary>Antwort</summary>

**Nein, das ist eine Totally Stubby Area.** `area 2 stub no-summary` auf dem ABR, `area 2 stub` auf den übrigen Routern. Der ABR ersetzt dann alle Type-3- und Type-5-LSAs durch eine Default-Route. Weil R4 hier ASBR ist, müsste es `area 2 nssa no-summary` sein. Eine Filterliste ist das Werkzeug für einzelne Netze, nicht für „alles“.

</details>

2. Zwei Router sind über Ethernet verbunden, einer mit Netztyp Broadcast, einer mit Point-to-Multipoint. Kommt die Nachbarschaft zustande?
<details><summary>Antwort</summary>

**Nein, schon die Hellos passen nicht.** Broadcast und Point-to-Point nutzen 10/40 Sekunden, Point-to-Multipoint und Non-Broadcast 30/120. Unterschiedliche Timer verhindern die Nachbarschaft. Gefährlicher ist die Kombination Broadcast und Point-to-Point: gleiche Timer, Nachbarschaft FULL, aber keine Routen.

</details>

3. Warum filtert `distribute-list out` unter `router ospf` keine normalen OSPF-Routen?
<details><summary>Antwort</summary>

**Weil OSPF keine Routen verschickt, sondern LSAs.** `distribute-list out` wirkt in OSPF nur auf Routen, die per Redistribution in den Prozess kommen, also am ASBR. Für alles andere gibt es `area filter-list` am ABR.

</details>

4. Ein Nachbar hängt in `2WAY`. Fehler?
<details><summary>Antwort</summary>

**Auf einem Broadcast-Segment zwischen zwei DROTHER-Routern ist das normal.** Volle Nachbarschaft gibt es nur mit DR und BDR. Ein Fehler ist es, wenn *kein* Router DR werden kann (alle mit Priorität 0) oder wenn der Link Point-to-Point sein sollte.

</details>

## Prüfungsbezug
- Filterstellen: ABR (Type 3: `area filter-list`, `area range not-advertise`), ASBR (Type 5/7: Route-Map, `summary-address not-advertise`), lokal (`distribute-list in`, nur RIB).
- Innerhalb einer Area wird nicht gefiltert: gleiche LSDB für alle.
- Nachbarschaft braucht: gleiches Subnetz, gleiche Area, gleiche Timer, gleichen Area-Typ, gleiche Authentisierung, eindeutige Router-ID, passende MTU.
- Zustände: DOWN, INIT, 2WAY, EXSTART, EXCHANGE, LOADING, FULL. EXSTART hängt bei MTU-Konflikt.
- Netztypen: Broadcast und NBMA wählen DR/BDR, Point-to-Point und Point-to-Multipoint nicht. Timer 10/40 oder 30/120.
- Prefix-Liste: ohne `ge`/`le` exakte Länge, am Ende stilles `deny`.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/34-OSPF-Filter-Netztyp-MTU/`](../../CML-Labs/34-OSPF-Filter-Netztyp-MTU/).
