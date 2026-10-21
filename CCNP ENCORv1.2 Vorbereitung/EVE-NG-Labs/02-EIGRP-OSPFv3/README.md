# Lab 02 – EIGRP (Named Mode) und OSPFv3

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel

Dual-Stack-Dreieck: IPv4 mit EIGRP im Named Mode (inkl. Unequal-Cost-Load-Balancing, Summarization, Authentifizierung), IPv6 mit OSPFv3 Address-Families. So vergleichst du beide IGPs am selben Netz.

**Lernziele:** Nach diesem Lab kannst du …

- EIGRP im Named Mode und OSPFv3 parallel betreiben.
- Feasible Successors mit der Feasibility Condition bestimmen.
- Nachbarschaftsfehler bei EIGRP (AS, Authentisierung, passive) und OSPFv3 (Area) unterscheiden.

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
| R3 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **1.5 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **1.5 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R2 | Gi0/1 | R3 | Gi0/0 |
| R1 | Gi0/1 | R3 | Gi0/1 |


## Topologie

```
        R2
      /    \        Gi0/0 R1-R2  10.0.12.0/30   2001:db8:12::/64   BW 10 Mbit
    R1 ---- R3      Gi0/1 R2-R3  10.0.23.0/30   2001:db8:23::/64   BW 10 Mbit
                    Gi0/1 R1-R3  10.0.13.0/30   2001:db8:13::/64   BW  2 Mbit (langsamer Direktlink)
```

| Gerät | Lo0 | Links | Zusatz |
|---|---|---|---|
| R1 | 1.1.1.1/32, 2001:db8:ff::1/128 | Gi0/0 → R2 (.1), Gi0/1 → R3 (.1) | – |
| R2 | 2.2.2.2/32, 2001:db8:ff::2/128 | Gi0/0 → R1 (.2), Gi0/1 → R3 (.1) | – |
| R3 | 3.3.3.3/32, 2001:db8:ff::3/128 | Gi0/0 → R2 (.2), Gi0/1 → R1 (.3) | Lo10–13 = 10.3.0.0–3.0/24 |
IPv6-Hosts-Teil jeweils `::1`, `::2` bzw. `::3` im jeweiligen /64.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

**Teil 1: EIGRP für IPv4**

1. **Named Mode einrichten.** Konfiguriere `router eigrp LAB` mit `address-family ipv4 unicast autonomous-system 100` und der Loopback0 als Router-ID. Setze unter `af-interface default` alle Interfaces passiv und nimm nur die Transit-Links mit `no passive-interface` wieder heraus.
   - **Prüfen:** `show ip eigrp neighbors` zeigt auf jedem Router zwei Nachbarn.
   - **Denkfrage:** Was ist der Unterschied zum klassischen `router eigrp 100`, und was ändern die Wide Metrics?
2. **Topologie lesen.** Sieh dir auf R1 `show ip eigrp topology 10.3.0.0/24` an.
   - **Prüfen:** Benenne Successor, Feasible Successor, Feasible Distance (FD) und Reported Distance (RD).
   - **Denkfrage:** Warum geht R1 über R2, obwohl der Direktlink zu R3 nur einen Hop hat?
3. **Ungleiche Lastverteilung.** R1 soll beide Wege zu R3 nutzen, im Verhältnis ihrer Metriken. Berechne `variance` = FD über den Feasible Successor ÷ FD des Successors, aufgerundet. Setze den Wert unter `topology base`.
   - **Prüfen:** `show ip route 10.3.0.0` zeigt zwei Pfade mit unterschiedlichem Traffic-Share.
   - **Denkfrage:** Warum darf `variance` nur Feasible Successors mitbenutzen und nicht jeden beliebigen Pfad?
4. **Zusammenfassen.** R3 fasst Lo10 bis Lo13 auf den Transit-Links zu 10.3.0.0/22 zusammen (`summary-address` unter `af-interface`).
   - **Prüfen:** R1 sieht nur noch `D 10.3.0.0/22`. R3 selbst hat eine Route `10.3.0.0/22 → Null0` mit Administrativer Distanz 5.
   - **Denkfrage:** Wozu legt R3 die Route nach Null0 an?
5. **Authentisierung.** Schütze alle Transit-Links mit HMAC-SHA-256: `authentication mode hmac-sha-256 0 <Passwort>` unter `af-interface`.
   - **Prüfen:** Die Nachbarschaften stehen danach wieder. Ein falsches Passwort auf einer Seite lässt die Nachbarschaft fallen.
   - **Denkfrage:** Was kann der Named Mode hier, was der klassische Modus nicht kann?
6. **Stub.** Setze R3 testweise als `eigrp stub connected`.
   - **Prüfen:** `show ip eigrp neighbors detail` auf R1 zeigt R3 als Stub.
   - **Denkfrage:** Welche Nachrichten bekommt R3 dadurch nicht mehr, und welches Problem löst das?

**Teil 2: OSPFv3 für IPv6**

7. **OSPFv3 starten.** `ipv6 unicast-routing` ist gesetzt, die Interfaces haben schon IPv6-Adressen. Starte `router ospfv3 1` mit `address-family ipv6 unicast`. Setze die Router-ID von Hand auf die IPv4-Adresse der Loopback0. Aktiviere OSPFv3 an jedem Interface mit `ospfv3 1 ipv6 area 0`.
   - **Prüfen:** `show ospfv3 neighbor` zeigt alle Nachbarn im Zustand FULL. Ein Ping von Lo0 zu Lo0 per IPv6 klappt.
8. **Link-Local verstehen.** Sieh dir `show ipv6 route ospf` an.
   - **Denkfrage:** Warum sind die Next-Hops fe80::-Adressen? Welche zwei LSA-Typen sind in OSPFv3 neu?
9. **Vergleichen.** Fülle diese Tabelle selbst aus, bevor du die Antwort aufklappst: Metrik, Algorithmus, IP-Protokoll, Administrative Distanz, ungleiche Lastverteilung bei EIGRP und OSPF.

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Im Named Mode steht alles in einer Hierarchie: `address-family`, darunter `af-interface` für die Interface-Einstellungen und `topology base` für Routing-Optionen. IPv4 und IPv6 laufen in einem Prozess. Im klassischen Modus sind die Einstellungen auf Prozess und Interfaces verteilt. Wide Metrics rechnen mit 64 Bit und feinerem Delay. So lassen sich auch Links über 1 Gbit/s noch unterscheiden.
- **Zu 2:** Die EIGRP-Metrik nimmt die kleinste Bandbreite auf dem Weg. Über R2 sind das 10 Mbit/s, auf dem Direktlink nur 2 Mbit/s. Die geringere Bandbreite wiegt schwerer als ein zusätzlicher Hop.
- **Zu 3:** Nur ein Feasible Successor ist garantiert schleifenfrei. Seine RD ist kleiner als die eigene FD, also liegt er näher am Ziel und routet nicht über dich zurück. Bei anderen Pfaden ist das nicht sicher.
- **Zu 4:** Die Route nach Null0 verhindert Schleifen. Kommt ein Paket für ein Teilnetz der Summary, das es nicht gibt, verwirft R3 es, statt es per Default-Route zurückzuschicken.
- **Zu 5:** Der Named Mode kann HMAC-SHA-256. Der klassische Modus kennt nur MD5 über eine Key-Chain.
- **Zu 6:** R1 und R2 schicken R3 keine Queries mehr. Fällt ein Weg weg, bleibt die Suche nach Ersatz kleiner. Das senkt das Risiko für Stuck in Active (SIA).
- **Zu 8:** OSPFv3 bildet seine Nachbarschaften über die Link-Local-Adressen, also sind diese auch die Next-Hops. Neu sind das Link-LSA (Typ 8, Adressen auf dem Link) und das Intra-Area-Prefix-LSA (Typ 9). Typ 1 und 2 tragen in OSPFv3 keine Präfixe mehr.
- **Zu 9:**

| | EIGRP | OSPF |
|---|---|---|
| Metrik | aus Bandbreite und Delay | Kosten = Referenz ÷ Bandbreite |
| Algorithmus | DUAL | SPF (Dijkstra) |
| IP-Protokoll | 88 | 89 |
| Administrative Distanz | intern 90, extern 170 | 110 |
| Ungleiche Lastverteilung | ja, mit `variance` | nein |

</details>

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** R2 hat keinen EIGRP-Nachbarn zu R1 oder R3, `show ip eigrp neighbors` ist leer, IPv6/OSPFv3 läuft normal.

**Ticket 2:** R1–R2 funktioniert, aber der Direktlink R1–R3 bildet keine Nachbarschaft (Log: Authentifizierungsfehler).

**Ticket 3:** R2–R3 bildet keine EIGRP-Nachbarschaft, R3 ist nur über den Direktlink R1–R3 erreichbar (Pfadwahl bei R1 ungewöhnlich).

**Ticket 4:** Im IPv6-Netz fehlt die Nachbarschaft R2–R3 (EIGRP IPv4 läuft), `show ospfv3 neighbor` zeigt auf R2 keinen Nachbarn an Gi0/1.

## Verifikation
```
show ip eigrp neighbors
show ip eigrp topology
show ip route eigrp
show ospfv3 neighbor
show ipv6 route ospf
show ospfv3 interface brief
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip route eigrp` auf R1 | 10.3.0.0/22 über zwei Pfade (nach Schritt 3 und 4) |
| `show ospfv3 neighbor` | alle Nachbarn FULL |
| `ping ipv6 2001:db8:ff::3 source lo0` auf R1 | Antwort von R3 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Ein Pfad hat AD 100 und FD 150, der Successor hat FD 120. Ist der Pfad Feasible Successor?
<details><summary>Antwort</summary>

**Ja.** Die Feasibility Condition vergleicht nur die Reported Distance des Nachbarn (100) mit der Feasible Distance des Successors (120): 100 < 120. Die eigene Distanz über diesen Pfad (150) spielt dafür keine Rolle. Sie entscheidet nur, ob der Pfad mit `variance` zusätzlich genutzt werden darf.

</details>

2. Welche K-Werte sind Default und warum müssen sie auf beiden Nachbarn identisch sein?
<details><summary>Antwort</summary>

**K1 = K3 = 1 (Bandbreite und Delay), K2 = K4 = K5 = 0.** Unterschiedliche K-Werte verhindern die Nachbarschaft („K-value mismatch“). Sonst würden beide Router dieselbe Strecke mit verschiedenen Formeln bewerten, und die Metriken wären nicht vergleichbar.

</details>

3. Wie finden OSPFv3-Nachbarn einander, wenn es keine IPv4-Adresse gibt?
<details><summary>Antwort</summary>

**Über ihre Link-Local-Adressen (fe80::) und die Multicast-Adressen FF02::5 und FF02::6.** Die Router-ID bleibt aber eine 32-Bit-Zahl. Gibt es keine IPv4-Adresse, musst du sie mit `router-id` von Hand setzen, sonst startet der Prozess nicht.

</details>

## Prüfungsbezug
- Feasibility Condition: RD des Nachbarn < FD des Successors.
- `variance` nutzt nur Feasible Successors.
- Administrative Distanz: EIGRP intern 90, extern 170, Summary 5.
- OSPFv3 braucht eine Router-ID im IPv4-Format. Gibt es keine IPv4-Adresse, muss sie von Hand gesetzt werden.
- In OSPFv3 sind Link-Local-Adressen die Next-Hops.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/02-EIGRP-OSPFv3/`](../../CML-Labs/02-EIGRP-OSPFv3/).
