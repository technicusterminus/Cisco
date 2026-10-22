# Lab C3 – OSPF: Virtual Link mit Authentisierung, NSSA, Typ-3-Filter und Netzwerktypen

**Plattform:** EVE-NG · **Dauer:** 110 min · **Niveau:** schwer

Fünf Router in vier Areas: Area 2 hängt nicht an Area 0 und braucht einen Virtual Link durch Area 1, der wegen der MD5-Authentisierung im Backbone eine eigene Falle hat. Dazu eine NSSA mit ASBR, die ihre Default-Route erst bekommt, wenn der ABR sie erzeugt, ein Typ-3-Filter, der in die richtige Richtung zeigen muss, und ein Netzwerktyp-Mismatch, bei dem die Nachbarschaft FULL ist und trotzdem keine Route ankommt.

**Lernziele:** Nach diesem Lab kannst du …

- Einen Virtual Link durch eine Transit-Area bauen und erklären, warum er die Authentisierung von Area 0 übernimmt.
- NSSA mit Typ-7-LSAs, Übersetzung am ABR und Default-Route konfigurieren und in der Datenbank nachweisen.
- Typ-3-LSAs mit `area … filter-list` gezielt filtern und `in` von `out` unterscheiden.
- Einen Netzwerktyp-Mismatch an FULL-Nachbarn ohne Routen erkennen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::1.2.i` | Authentisierung von Routing-Protokollen | 5 |
| `Ziel::1.4.b` | OSPF: Netzwerktypen, LSA-Typen und Area-Typen | 10 |
| `Ziel::1.4.c` | OSPF: Pfadwahl und Summarization | 5 |
| `Ziel::1.4.d` | OSPF: Betrieb, Router-ID, DR/BDR und Absicherung | 7 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| R4 | Cisco vIOS Router |  | 512 |
| R5 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.6 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R1 | Gi0/1 | R3 | Gi0/0 |
| R3 | Gi0/1 | R4 | Gi0/0 |
| R2 | Gi0/1 | R5 | Gi0/0 |

## Topologie

```
   Area 2           Area 1                 Area 0 (MD5)                Area 3 (NSSA)
   R4 Gi0/0 --- Gi0/1 R3 Gi0/0 --- Gi0/1 R1 Gi0/0 --- Gi0/0 R2 Gi0/1 --- Gi0/0 R5
   Lo1 10.4.4.1/24    ABR 1/2            Lo1  10.1.1.1/24     ABR 0/3            Lo1 10.5.5.1/24
   Lo2 10.4.5.1/24                       Lo99 10.1.99.1/24                       ASBR: 172.16.5.0/24
                      <==== Virtual Link durch Area 1 ====>   Lo100 192.0.2.1 = Internet
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 (Area 0) | 10.0.12.0/30 (.1/.2) |
| R1 Gi0/1 – R3 Gi0/0 (Area 1) | 10.0.13.0/30 (.1/.2) |
| R3 Gi0/1 – R4 Gi0/0 (Area 2) | 10.0.34.0/30 (.1/.2) |
| R2 Gi0/1 – R5 Gi0/0 (Area 3) | 10.0.25.0/30 (.1/.2) |
| Router-IDs | R1 1.1.1.1, R2 2.2.2.2, R3 3.3.3.3, R4 4.4.4.4, R5 5.5.5.5 |
| Netze (Loopbacks) | R1 10.1.1.0/24 und Testnetz 10.1.99.0/24, R4 10.4.4.0/24 und 10.4.5.0/24, R5 10.5.5.0/24 |
| „Internet“ | 192.0.2.1/32 auf R1 Loopback100, nicht in OSPF |

Area 0 besteht nur aus R1, R2 und dem Link dazwischen, mit MD5-Authentisierung. R3 verbindet Area 1 und Area 2, hängt aber nicht am Backbone. R5 speist als ASBR in der NSSA ein externes Netz ein. R1 ist der Übergang ins Internet und verteilt eine Default-Route. Das Testnetz 10.1.99.0/24 soll nur in Area 0 bekannt sein, mindestens aber nicht in Area 3. OSPF konfigurierst du am Interface mit `ip ospf 1 area <n>`.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Area 0 mit MD5.** R1 und R2: `router ospf 1` mit `router-id`, `area 0 authentication message-digest`, am Link 10.0.12.0/30 `ip ospf message-digest-key 1 md5 CCIE` und `ip ospf 1 area 0`. Auf R1 kommen Loopback1 und Loopback99 in Area 0, jeweils mit `ip ospf network point-to-point`.
   - **Prüfen:** `show ip ospf neighbor` auf R1 zeigt R2 in FULL. `show ip ospf interface Gi0/0` nennt Message-Digest-Authentisierung mit Key 1.
   - **Denkfrage:** Warum bekommen die Loopbacks `ip ospf network point-to-point`?
2. **Area 1 und Area 2.** R1 Gi0/1 und R3 Gi0/0 in Area 1, R3 Gi0/1 und R4 komplett in Area 2 (Loopbacks wieder mit `ip ospf network point-to-point`). Router-IDs 3.3.3.3 und 4.4.4.4.
   - **Prüfen:** R3 ist mit R1 und R4 FULL. R1 kennt die Netze von R4 aber **nicht**, und R4 kennt nur Area 2.
   - **Denkfrage:** Warum gibt R3 die Netze aus Area 2 nicht an Area 1 weiter, obwohl es in beiden Areas sitzt?
3. **Virtual Link.** R1: `area 1 virtual-link 3.3.3.3 message-digest-key 1 md5 CCIE`. R3: `area 1 virtual-link 1.1.1.1 message-digest-key 1 md5 CCIE` und `area 0 authentication message-digest`.
   - **Prüfen:** `show ip ospf virtual-links` auf R3: Nachbarschaft zu 1.1.1.1 FULL. R1 kennt 10.4.4.0/24 und 10.4.5.0/24 als O IA.
   - **Denkfrage:** Warum braucht R3 `area 0 authentication message-digest`, obwohl es kein Interface in Area 0 hat?
4. **Zusammenfassen.** Auf R3 `area 2 range 10.4.4.0 255.255.254.0`.
   - **Prüfen:** R1 sieht nur noch 10.4.4.0/23. Auf R3 steht eine Discard-Route `10.4.4.0/23 is a summary, … Null0`.
   - **Denkfrage:** Wofür ist die Discard-Route auf R3 gut?
5. **NSSA mit ASBR.** R2 Gi0/1 und R5 in Area 3, auf beiden `area 3 nssa`. R5: Router-ID 5.5.5.5, `ip route 172.16.5.0 255.255.255.0 Null0` und `redistribute static subnets`, Loopback1 mit `ip ospf network point-to-point` in Area 3.
   - **Prüfen:** `show ip ospf database nssa-external` auf R5: Typ-7-LSA für 172.16.5.0/24. Auf R1 steht dasselbe Netz als O E2, aus einem Typ-5-LSA, das R2 übersetzt hat.
   - **Denkfrage:** Welcher Router übersetzt Typ 7 in Typ 5, und was gilt bei mehreren ABRs?
6. **Default-Route ins Internet.** R1: `default-information originate always`. Teste auf R5 `ping 192.0.2.1 source Loopback1`. Der Ping scheitert. Ändere auf R2 die Area-3-Zeile in `area 3 nssa default-information-originate`.
   - **Prüfen:** R5 hat jetzt `O*N2 0.0.0.0/0`, der Ping klappt.
   - **Denkfrage:** Warum kommt die Default-Route von R1 nicht in Area 3, und welche andere Lösung gäbe es?
7. **Testnetz aus Area 3 fernhalten.** Auf R2: `ip prefix-list NO-TEST seq 5 deny 10.1.99.0/24`, `ip prefix-list NO-TEST seq 10 permit 0.0.0.0/0 le 32` und `area 3 filter-list prefix NO-TEST in`.
   - **Prüfen:** R5 hat 10.1.99.0/24 nicht mehr in der Routing-Tabelle, 10.1.1.0/24 schon.
   - **Denkfrage:** Warum braucht die Prefix-Liste die zweite Zeile?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** **Damit OSPF das Loopback-Netz mit seiner echten Maske ankündigt.** Standardmäßig ist eine Loopback ein Host und erscheint als /32. Mit point-to-point steht 10.1.1.0/24 in der Datenbank, wie ein echtes LAN.
- **Zu 2:** **Weil ein Router nur dann als ABR arbeitet, wenn er am Backbone hängt.** Inter-Area-Routen laufen immer über Area 0, zwischen zwei Nicht-Backbone-Areas gibt es keine Summaries. R3 hat keine Verbindung zu Area 0, also erzeugt er keine Typ-3-LSAs.
- **Zu 3:** **Weil der Virtual Link ein Interface in Area 0 ist.** Er übernimmt deren Authentisierungstyp. Ohne `area 0 authentication message-digest` sendet R3 über den Virtual Link ohne Authentisierung, R1 erwartet MD5 und verwirft die Pakete. Der Schlüssel am Virtual Link allein reicht nicht.
- **Zu 4:** **Sie verhindert Schleifen und unnötigen Verkehr.** Kommt bei R3 ein Paket für ein nicht vorhandenes Netz innerhalb von 10.4.4.0/23 an, verwirft R3 es, statt es über die Default-Route zurückzuschicken.
- **Zu 5:** **Der ABR der NSSA, hier R2.** Bei mehreren ABRs übersetzt nur der mit der höchsten Router-ID, außer einer ist mit `area 3 nssa translate type7 always` fest eingestellt. Das Typ-5-LSA trägt R2 als Absender und eine Adresse von R5 als Forwarding-Adresse; diese Adresse muss deshalb in den anderen Areas erreichbar sein.
- **Zu 6:** **Weil eine NSSA keine Typ-5-LSAs annimmt, und die Default-Route von R1 ist eine.** Lösungen: `default-information-originate` am ABR (Typ-7-Default, `O*N2`) oder `no-summary` (Totally NSSA, Default als Typ 3, `O*IA`). Mit `no-summary` fielen aber alle Inter-Area-Routen weg, und der Filter aus Schritt 7 wäre sinnlos.
- **Zu 7:** **Weil eine Prefix-Liste mit einem impliziten Deny endet.** Ohne die zweite Zeile würde der Filter alle Typ-3-LSAs nach Area 3 blockieren, nicht nur das Testnetz.

</details>

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** R5 steht mit R2 in FULL, hat aber keine einzige OSPF-Route. R2 kennt das LAN von R5 (10.5.5.0/24) nicht.

**Ticket 2:** R5 hat Routen zu den internen Netzen, erreicht aber 192.0.2.1 (Internet über R1) nicht.

**Ticket 3:** Das Testnetz 10.1.99.0/24 soll nicht in Area 3 gelangen. R5 hat es trotzdem in der Routing-Tabelle, obwohl R2 einen Filter hat.

**Ticket 4:** R1 und R2 kennen die Netze von R4 nicht. `show ip ospf virtual-links` auf R3 zeigt den Virtual Link zu 1.1.1.1, aber keine Nachbarschaft im Zustand FULL.

**Ticket 5:** R1 sieht statt der Zusammenfassung 10.4.4.0/23 die beiden Einzelnetze 10.4.4.0/24 und 10.4.5.0/24.

## Verifikation
```
show ip ospf neighbor
show ip ospf interface brief
show ip ospf virtual-links
show ip ospf database
show ip route ospf
ping 192.0.2.1 source Loopback1   ! auf R5
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip ospf virtual-links` auf R3 | Virtual Link zu 1.1.1.1, Nachbarschaft FULL, Message-Digest |
| `show ip route ospf` auf R1 | O IA 10.4.4.0/23, O IA 10.5.5.0/24, O E2 172.16.5.0/24 |
| `show ip route` auf R5 | O*N2 0.0.0.0/0, O IA 10.1.1.0/24, kein 10.1.99.0/24 |
| `ping 192.0.2.1 source Loopback1` auf R5 | erfolgreich über die NSSA-Default-Route |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Area 0 zerfällt durch einen Linkausfall in zwei Hälften, die beide noch an Area 1 hängen. Was passiert, und wie hilft ein Virtual Link?
<details><summary>Antwort</summary>

**Die beiden Hälften tauschen keine Inter-Area-Routen mehr aus**, weil Summaries nicht über eine Nicht-Backbone-Area zwischen Backbone-Teilen laufen. Ein Virtual Link durch Area 1 verbindet die Hälften wieder zu einer Area 0. Dauerhaft ist ein zweiter physischer Backbone-Link die bessere Lösung.

</details>

2. Warum darf die Transit-Area eines Virtual Links keine Stub- oder NSSA-Area sein?
<details><summary>Antwort</summary>

**Weil über den Virtual Link Backbone-Verkehr zu allen Zielen läuft, auch zu externen.** Die Transit-Area muss dafür volle Routing-Information haben, eine Stub-Area hat keine Typ-5-LSAs. Ein Virtual Link durch eine Stub- oder NSSA-Area ist deshalb nicht erlaubt.

</details>

3. Ein Router soll nach dem Neustart erst Verkehr bekommen, wenn BGP konvergiert ist. Was setzt du in OSPF?
<details><summary>Antwort</summary>

**`max-metric router-lsa on-startup wait-for-bgp`.** Der Router meldet seine Links mit maximaler Metrik, die anderen umgehen ihn, solange es Alternativen gibt. Sobald BGP fertig ist, spätestens nach 600 Sekunden, meldet er normale Kosten.

</details>

4. Was unterscheidet `area 2 range … not-advertise` von `area 2 filter-list prefix … out`?
<details><summary>Antwort</summary>

**`range not-advertise` unterdrückt einen zusammengefassten Block von Netzen aus Area 2, `filter-list` arbeitet mit beliebigen Prefix-Listen auf allen Typ-3-LSAs, die der ABR aus der Area heraus erzeugt.** Externe Routen (Typ 5 und 7) erfasst keiner von beiden, dafür gibt es `summary-address` oder Filter am ASBR.

</details>

## Prüfungsbezug
- Jede Area muss an Area 0 hängen; sonst Virtual Link durch eine normale Transit-Area (`area <Transit> virtual-link <RID>`).
- Der Virtual Link gehört zu Area 0 und übernimmt deren Authentisierung.
- Netzwerktyp-Mismatch Broadcast und Punkt-zu-Punkt: Nachbarschaft FULL, aber keine Routen.
- NSSA: Typ 7 statt Typ 5, Übersetzung durch den ABR mit der höchsten Router-ID. Default nur mit `default-information-originate` (O*N2) oder `no-summary` (O*IA).
- `area X filter-list prefix … in|out` filtert nur Typ-3-LSAs am ABR, `area X range` fasst nur Intra-Area-Netze zusammen.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-Konfiguration)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
