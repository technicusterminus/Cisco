# Lab C6 – EIGRP Named Mode: SHA-256, Unequal-Cost Load Balancing und Stub mit Leak-Map

**Plattform:** EVE-NG · **Dauer:** 100 min · **Niveau:** mittel bis schwer

Vier Router im EIGRP Named Mode mit HMAC-SHA-256. Der Weg von der Zentrale zur Filiale führt über zwei Verteiler mit unterschiedlicher Verzögerung: Mit `variance` nutzt R1 beide, sofern der zweite die Feasibility Condition erfüllt. Die Filiale R4 ist ein Stub und damit nie Transit, gibt per Leak-Map aber die Default-Route weiter, damit ein Verteiler bei einem Linkausfall nicht abgeschnitten ist.

**Lernziele:** Nach diesem Lab kannst du …

- EIGRP im Named Mode mit `af-interface` und `topology base` konfigurieren und HMAC-SHA-256 einsetzen.
- Successor und Feasible Successor aus den Verzögerungen ableiten und Unequal-Cost Load Balancing mit `variance` nachweisen.
- Einen Stub mit Leak-Map bauen und erklären, warum ein Stub keine Queries bekommt.
- Abgelehnte Nachbarschaften an K-Werten und Authentisierung erkennen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::1.2.i` | Authentisierung von Routing-Protokollen | 5 |
| `Ziel::1.3.b` | EIGRP: Metrik und Wide Metrics | 4 |
| `Ziel::1.3.d` | EIGRP: Load Balancing | 3 |
| `Ziel::1.3.e` | EIGRP: Named Mode | 4 |
| `Ziel::1.3.f` | EIGRP: Optimierung, Stub, LFA und Leak-Maps | 4 |

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
| R1 | Gi0/1 | R3 | Gi0/0 |
| R2 | Gi0/1 | R4 | Gi0/0 |
| R3 | Gi0/1 | R4 | Gi0/1 |

## Topologie

```
                 R1   Lo1 10.1.1.1/24, Lo100 192.0.2.1 = Internet
          Gi0/0 /  \ Gi0/1  (delay 10 = 100 µs)
               /    \
        Gi0/0 /      \ Gi0/0
           R2          R3
        Gi0/1 \      / Gi0/1
               \    /
        Gi0/0   \  /  Gi0/1
                 R4   Stub, Lo1 10.4.1.1/24, Lo2 10.4.2.1/24
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R1 Gi0/1 – R3 Gi0/0 | 10.0.13.0/30 (.1/.2) |
| R2 Gi0/1 – R4 Gi0/0 | 10.0.24.0/30 (.1/.2) |
| R3 Gi0/1 – R4 Gi0/1 | 10.0.34.0/30 (.1/.2) |
| LANs (Loopbacks) | R1 10.1.1.0/24, R4 10.4.1.0/24 und 10.4.2.0/24 |
| „Internet“ | 192.0.2.1/32 auf R1 Loopback100, nicht in EIGRP |

Alle Links haben dieselbe Bandbreite (1 Gbit/s), die Pfadwahl hängt deshalb nur an der Verzögerung. R1 bekommt an Gi0/1 eine höhere Verzögerung, R4 an seinen Loopbacks eine niedrigere als üblich, damit die Rechnung überschaubar bleibt. R1 ist der Übergang ins Internet und verteilt eine Default-Route.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Named Mode mit Authentisierung.** Auf allen vier Routern `router eigrp CCIE` → `address-family ipv4 unicast autonomous-system 100` mit `eigrp router-id` (R1 10.1.1.1, R2 10.0.0.2, R3 10.0.0.3, R4 10.0.0.4) und `network`-Anweisungen für alle Links. Unter `af-interface default` `authentication mode hmac-sha-256 EIGRP-Lab`. R1 kündigt zusätzlich 10.1.1.0/24 an.
   - **Prüfen:** `show eigrp address-family ipv4 neighbors`: R1 und R4 sehen je zwei Nachbarn, R2 und R3 ebenfalls zwei.
   - **Denkfrage:** Warum geht HMAC-SHA-256 nur im Named Mode?
2. **Netze von R4.** Auf R4 `network 10.4.0.0 0.0.3.255` und an Loopback1 und Loopback2 `delay 10` (100 µs).
   - **Prüfen:** R1 kennt 10.4.1.0/24 und 10.4.2.0/24.
   - **Denkfrage:** Welche Netze erfasst `network 10.4.0.0 0.0.3.255`?
3. **Ungleiche Wege.** Auf R1 an Gi0/1 (Richtung R3) `delay 10`.
   - **Prüfen:** `show ip eigrp topology 10.4.1.0/24` auf R1: Successor über R2 (10.0.12.2), Feasible Successor über R3 (10.0.13.2). In der Routing-Tabelle steht nur der Weg über R2.
   - **Denkfrage:** Warum ist der Weg über R3 ein Feasible Successor? Rechne mit den Verzögerungen.
4. **Unequal-Cost Load Balancing.** Auf R1 unter `topology base` `variance 2`.
   - **Prüfen:** `show ip route 10.4.1.0` zeigt zwei Wege mit unterschiedlichem *traffic share count*.
   - **Denkfrage:** Warum reicht `variance 2`, und was gilt für einen Weg, der die Feasibility Condition nicht erfüllt?
5. **Default-Route ins Internet.** Auf R1 `ip route 0.0.0.0 0.0.0.0 Null0` und unter `topology base` `redistribute static metric 1000000 10 255 1 1500`.
   - **Prüfen:** R2, R3 und R4 haben `D*EX 0.0.0.0/0`. `ping 192.0.2.1 source Loopback1` von R4 klappt.
   - **Denkfrage:** Warum ist 192.0.2.1 erreichbar, obwohl es nicht in EIGRP steht?
6. **R4 als Stub.** Auf R4 `eigrp stub connected`. Teste dann: `shutdown` auf R1 Gi0/0, danach `show ip route 0.0.0.0` auf R2. Anschließend `no shutdown`.
   - **Prüfen:** `show ip protocols` auf R4 meldet den Stub. Während des Tests hat R2 keine Default-Route mehr, obwohl R4 über R3 weiter Verbindung hat.
   - **Denkfrage:** Welchen Vorteil bringt ein Stub bei Queries?
7. **Leak-Map.** Auf R4 `ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0`, `route-map LEAK-DEFAULT permit 10` mit `match ip address prefix-list DEFAULT` und `eigrp stub connected leak-map LEAK-DEFAULT`. Wiederhole den Test.
   - **Prüfen:** Bei `shutdown` auf R1 Gi0/0 hat R2 die Default-Route über R4 (10.0.24.2) und erreicht 192.0.2.1.
   - **Denkfrage:** Warum leakt R4 nur die Default-Route und nicht alles?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** **Weil der Classic Mode nur MD5 über Key-Chains kennt.** HMAC-SHA-256 gibt es nur in der Named-Konfiguration, das Passwort steht direkt unter `af-interface`. Wie bei MD5 müssen beide Seiten denselben Schlüssel haben, Groß- und Kleinschreibung zählt.
- **Zu 2:** **10.4.0.0 bis 10.4.3.255.** Die Wildcard 0.0.3.255 lässt die letzten zwei Bits des dritten Oktetts und das ganze vierte Oktett offen. Beide Loopbacks liegen darin, dazu Platz für zwei weitere /24.
- **Zu 3:** **Weil die Reported Distance von R3 kleiner ist als die Feasible Distance über R2.** Bei gleicher Bandbreite entscheidet die Verzögerung: R3 meldet für 10.4.1.0/24 10 µs (R3–R4) + 100 µs (Loopback) = 110 µs. Die Feasible Distance über R2 enthält 10 + 10 + 100 = 120 µs. 110 < 120, die Feasibility Condition ist erfüllt.
- **Zu 4:** **Die Metrik über R3 liegt unter dem Doppelten der besten Metrik.** Über R2 summieren sich 120 µs, über R3 100 + 10 + 100 = 210 µs; mit dem gleichen Bandbreitenanteil ergibt das ein Verhältnis von etwa 1,7. Ein Weg ohne Feasibility Condition kommt nie in die Lastverteilung, egal wie groß die Varianz ist, sonst drohten Schleifen.
- **Zu 5:** **Weil R1 eine Default-Route verteilt.** Die anderen Router schicken alles, was sie nicht kennen, zu R1, und dort ist 192.0.2.1 direkt angeschlossen.
- **Zu 6:** **Ein Stub wird nicht befragt.** Fällt eine Route aus, schicken R2 und R3 keine Query an R4. Die Suche bleibt klein, Stuck in Active wird unwahrscheinlicher. Gleichzeitig gibt R4 keine gelernten Routen weiter und wird so nie zum Transit.
- **Zu 7:** **Damit R4 kein Transit für das ganze Netz wird.** Die Default-Route reicht R2 im Fehlerfall, um weiter ins Internet und zu R1 zu kommen. Mit allen Routen würde R4 bei jedem Ausfall zum Umweg für beliebigen Verkehr.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** R2 hat keine EIGRP-Nachbarn. Im Log steht bei jedem Versuch `K-value mismatch`.

**Ticket 2:** R3 hat keine EIGRP-Nachbarn. Die Links sind up, Pings zu R1 und R4 klappen.

**Ticket 3:** Das Netz 10.4.2.0/24 fehlt auf allen anderen Routern, 10.4.1.0/24 ist da.

**Ticket 4:** R1 schickt Verkehr zu 10.4.1.0/24 nur über R2, obwohl der Weg über R3 als Feasible Successor bereitsteht.

**Ticket 5:** Ausfalltest: Nach `shutdown` auf R1 Gi0/0 verliert R2 seine Default-Route und erreicht 192.0.2.1 nicht mehr, obwohl R4 über R3 weiter angebunden ist.

## Verifikation
```
show eigrp address-family ipv4 neighbors
show eigrp address-family ipv4 interfaces detail
show eigrp protocols
show ip eigrp topology 10.4.1.0/24
show ip route 10.4.1.0
show ip route 0.0.0.0
show ip protocols
```

| Befehl | Das solltest du sehen |
|---|---|
| `show eigrp address-family ipv4 neighbors` auf R4 | R2 und R3 |
| `show ip eigrp topology 10.4.1.0/24` auf R1 | Successor über 10.0.12.2, Feasible Successor über 10.0.13.2 |
| `show ip route 10.4.1.0` auf R1 | zwei Wege mit unterschiedlichem traffic share count |
| `show ip route 0.0.0.0` auf R2 bei `shutdown` von R1 Gi0/0 | D*EX über 10.0.24.2, von R4 geleakt |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Was zeigt `show ip eigrp topology all-links` zusätzlich zu `show ip eigrp topology`?
<details><summary>Antwort</summary>

**Auch die Wege, die die Feasibility Condition nicht erfüllen.** Die normale Ausgabe zeigt nur Successors und Feasible Successors. So siehst du, warum ein Weg nicht als Backup taugt.

</details>

2. Ein Router steht minutenlang für eine Route im Zustand Active. Was passiert, und wie beugst du vor?
<details><summary>Antwort</summary>

**Er wartet auf Antworten auf seine Queries.** Bleibt eine Antwort aus, fragt er nach der Hälfte der Active-Zeit (Standard 3 Minuten) per SIA-Query nach und baut die Nachbarschaft erst ab, wenn auch darauf nichts kommt. Vorbeugen: den Query-Bereich mit Summaries und Stubs klein halten.

</details>

3. Warum zeigt `show ip route` eine andere Metrik als `show eigrp address-family ipv4 topology`?
<details><summary>Antwort</summary>

**Wide Metrics sind 64 Bit groß, die Routing-Tabelle speichert nur 32 Bit.** IOS teilt die Metrik vor dem Eintrag durch den RIB-Scale (`metric rib-scale`, Standard 128).

</details>

4. Was passiert mit dem Verkehr, wenn der Successor ausfällt und ein Feasible Successor existiert?
<details><summary>Antwort</summary>

**Der Feasible Successor übernimmt sofort, ohne Query.** Er ist nachweislich schleifenfrei, deshalb muss der Router niemanden fragen. Gibt es keinen, geht die Route in den Zustand Active, und die Queries beginnen.

</details>

## Prüfungsbezug
- Named Mode: `router eigrp <Name>` → `address-family ipv4 unicast autonomous-system <AS>`; Interface-Einstellungen unter `af-interface`, Pfadwahl und Redistribution unter `topology base`.
- Feasibility Condition: RD < FD. Nur Feasible Successors kommen für `variance` in Frage.
- Stub: `eigrp stub [connected|summary|static|redistributed|receive-only] [leak-map]`; Stubs werden nicht befragt.
- Nachbarschaft scheitert bei unterschiedlichen K-Werten, AS-Nummern oder Schlüsseln, bei fremdem Subnetz und bei `passive-interface`.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-Konfiguration)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
