# Lab 01 – OSPFv2 Multi-Area

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel

OSPF-Areas, ABR/ASBR, DR/BDR, Summarization, Stub/NSSA, Authentifizierung und typische OSPF-Fehler.

**Lernziele:** Nach diesem Lab kannst du …

- OSPFv2 über mehrere Areas aufbauen und die Rolle von ABR und Backbone erklären.
- Nachbarschaftsprobleme an ihrem Zustand erkennen (INIT, 2WAY, EXSTART) und gezielt beheben.
- Routen am ABR mit `area range` zusammenfassen und das Ergebnis in der LSDB nachweisen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.2.a` | EIGRP und OSPF vergleichen | 45 |
| `Ziel::3.2.b` | OSPFv2 und OSPFv3 | 86 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| SW | Network (Bridge) | Kein Gerät, sondern ein **Network**-Objekt (Linux-Bridge) mit Typ *Bridge*. | – |
| R3 | Cisco vIOS Router |  | 512 |
| R4 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.0 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R2 | Gi0/1 | SW | – |
| R3 | Gi0/0 | SW | – |
| R4 | Gi0/0 | SW | – |


## Topologie

```
 Area 0              Area 1 (10.1.234.0/24)
 R1 ---- R2 (ABR) ---- SW ---- R3 (Lo10-13 = 10.1.16-19.0/24)
 10.0.12.0/30                \--- R4 (extern 198.51.100.0/24 via Null0)
```

| Gerät | Interface | Adresse |
|---|---|---|
| R1 | Lo0 / Gi0/0 | 1.1.1.1/32 / 10.0.12.1/30 |
| R2 | Lo0 / Gi0/0 / Gi0/1 | 2.2.2.2/32 / 10.0.12.2/30 / 10.1.234.2/24 |
| R3 | Lo0 / Gi0/0 / Lo10–13 | 3.3.3.3/32 / 10.1.234.3/24 / 10.1.16–19.1/24 |
| R4 | Lo0 / Gi0/0 | 4.4.4.4/32 / 10.1.234.4/24, statisch 198.51.100.0/24 → Null0 |

## Teil A – Bauen

1. **OSPF aufbauen.** Process-ID 1, Router-ID = Loopback0. Link R1–R2 und Loopbacks von R1/R2 in Area 0, LAN 10.1.234.0/24, Loopback0 von R3/R4 und R3-Loopbacks 10–13 in Area 1. Aktiviere OSPF **pro Interface** (`ip ospf 1 area X`) statt per `network`.
2. **DR/BDR.** Im LAN soll R3 DR und R4 BDR sein, R2 darf nie DR/BDR werden. Löse es per Priorität, ohne Router-IDs zu ändern. Warum ist die Wahl nicht präemptiv und was musst du nach der Änderung tun?
3. **Passive Interfaces.** R3: `passive-interface default`, nur Gi0/0 aktiv. Die Loopback-Netze bleiben im LSDB.
4. **Summarization.** R2 sendet 10.1.16.0–19.0/24 als **eine** Route nach Area 0 (`area 1 range`). Welche Maske? Was zeigt R1?
5. **Externe Route.** R4 verteilt 198.51.100.0/24 per `redistribute static` (Metrik-Typ 1) ein. Beobachte `O E1` auf R1 und erkläre Typ-4-LSA, ASBR und ABR. Wie unterscheidet sich die Metrik von E2?
6. **Stub-Varianten.** Mache Area 1 zur **Totally Stubby Area** (R4 muss dafür seine Redistribution aufgeben). Was siehst du auf R3 statt der Externen? Wechsle danach auf **NSSA**, sodass R4 extern einspeisen darf. Welcher LSA-Typ (7) wird von wem zu Typ 5 umgewandelt?
7. **Authentifizierung.** SHA-256 per Key-Chain auf R1–R2. Setze auf R1 testweise einen falschen Schlüssel und lies Log und `show ip ospf neighbor`.
8. **Timer.** Hello 3/Dead 12 nur auf R1: Was passiert, was zeigt `debug ip ospf hello`? (`undebug all` nicht vergessen.)

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** R1 und R2 werden nicht Nachbarn, `show ip ospf neighbor` ist auf R1 leer, Area 0 ist isoliert.

**Ticket 2:** R3 erscheint nirgends als Nachbar, R2 und R4 sehen nur sich gegenseitig.

**Ticket 3:** R1 sieht vier einzelne /24 (10.1.16–19) statt der Zusammenfassung.

**Ticket 4:** R4 bleibt in `INIT`/taucht nicht als Nachbar auf, während R3 und R2 sich sehen.

## Verifikation

```
show ip ospf neighbor
show ip ospf interface brief
show ip ospf database [summary|external|nssa-external]
show ip route ospf
show ip protocols
```
Erwartet nach Aufgabe 1–5: R1 hat `O IA 10.1.16.0/22`, `O IA 10.1.234.0/24` und `O E1 198.51.100.0/24`. LAN: R3 DR, R4 BDR, R2 DROTHER.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Welche LSA-Typen sieht ein Router in einer Totally Stubby Area?
<details><summary>Antwort</summary>

**Typ 1 und Typ 2 aus der eigenen Area, dazu eine Default-Route als Typ 3 vom ABR.** Alle anderen Typ-3-LSAs sowie Typ 4 und 5 hält der ABR draußen. Deshalb ist die Tabelle in einer Totally Stubby Area so klein.

</details>

2. Zwei Router hängen im selben Subnetz, bleiben aber in `2WAY`. Ist das ein Fehler?
<details><summary>Antwort</summary>

**Nein, wenn beide DROTHER sind.** Auf Broadcast-Netzen bilden nur DR und BDR mit allen eine volle Adjazenz (FULL). Zwei DROTHERs bleiben untereinander bewusst in 2WAY. Ein Fehler wäre es erst, wenn auch DR oder BDR in 2WAY hängen bleiben.

</details>

3. Warum sieht man auf dem ABR nach `area range` trotzdem die Einzelnetze?
<details><summary>Antwort</summary>

**Weil die Zusammenfassung nur nach außen wirkt.** In der LSDB von Area 1 und in der Routing-Tabelle des ABR bleiben die Einzelnetze stehen. Nur Area 0 bekommt die Summary. Dazu legt der ABR eine Route nach Null0 an, damit Pakete an nicht vorhandene Teilnetze keine Schleife bilden.

</details>

## Prüfungsbezug

Hello/Dead und Area-Typ (E-/N-Flag) müssen übereinstimmen, DR-Wahl ist nicht präemptiv, Summarization nur am ABR (`area range`) oder ASBR (`summary-address`), E1 addiert interne Kosten, Stub blockiert Typ 5, NSSA transportiert Typ 7.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/01-OSPFv2-Multiarea/`](../../CML-Labs/01-OSPFv2-Multiarea/).
