# Lab 02 – EIGRP (Named Mode) und OSPFv3

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel

Dual-Stack-Dreieck: IPv4 mit EIGRP im Named Mode (inkl. Unequal-Cost-Load-Balancing, Summarization, Authentifizierung), IPv6 mit OSPFv3 Address-Families. So vergleichst du beide IGPs am selben Netz.

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

**Teil 1 – EIGRP (IPv4)**

1. **Named Mode.** Konfiguriere `router eigrp LAB` mit `address-family ipv4 unicast autonomous-system 100`, Router-ID = Lo0. Alle Interfaces `passive` per `af-interface default`, nur die Transit-Links aktiv. Erkläre den Unterschied zu Classic-Mode (`router eigrp 100`) und was „Wide Metrics“ ändern.
2. **Topologie lesen.** Welche Route nimmt R1 zu 10.3.0.0/24, und warum? Lies `show ip eigrp topology 10.3.0.0/24` und benenne Successor, Feasible Successor, FD und RD (AD).
3. **Unequal-Cost.** R1 soll Verkehr zu R3 im Verhältnis der Metriken über beide Pfade verteilen. Bestimme das nötige `variance` (FD des FS / FD des Successors, aufrunden) und setze es unter `topology base`. Prüfe in `show ip route`, dass **zwei** Pfade installiert sind. Warum ist der zweite Pfad nur ein FS, wenn seine AD kleiner als die FD des Successors ist (Loop-Freiheit, DUAL)?
4. **Summarization.** R3 fasst die vier Loopback-Netze auf den Transit-Links zu 10.3.0.0/22 zusammen (`summary-address` im `af-interface`). Was erscheint auf R1 und welche Distanz hat die Summary-Route auf R3 (Null0, AD 5)?
5. **Authentifizierung.** HMAC-SHA-256 im Named Mode auf allen Transit-Links (`authentication mode hmac-sha-256 0 <Passwort>`). Wie unterscheidet sich das von der MD5-Key-Chain im Classic-Mode?
6. **Stub.** Setze R3 testweise als `eigrp stub connected` und beobachte, welche Anfragen (Queries) R1/R2 dadurch nicht mehr senden. Welches Problem mit SIA (Stuck-in-Active) löst das?

**Teil 2 – OSPFv3 (IPv6)**

7. **IPv6 aktivieren.** `ipv6 unicast-routing` ist gesetzt, Interfaces tragen schon Adressen. Starte `router ospfv3 1` mit `address-family ipv6 unicast`, Router-ID = Lo0 (Pflicht, es gibt keine IPv4-Adresse als Fallback), und aktiviere pro Interface `ospfv3 1 ipv6 area 0`.
8. **Link-Local verstehen.** Welche Adressen sind Next-Hops in `show ipv6 route ospf` (fe80::/10) und warum? Welches LSA-Paar (Typ 8 / Link-LSA, Typ 9 / Intra-Area-Prefix) ist neu gegenüber OSPFv2?
9. **Vergleich.** Fülle die Tabelle aus: Metrik (EIGRP composite vs. OSPF cost), Algorithmus (DUAL vs. SPF), Transport (IP 88 vs. IP 89), Admin-Distanz (90/170 vs. 110), Konvergenz, Unequal-Cost (ja/nein).

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
Erwartet: R1 hat zu 10.3.0.0/22 zwei EIGRP-Pfade (nach Variance), alle OSPFv3-Nachbarn FULL, IPv6-Pings Lo0↔Lo0 funktionieren.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Ein Pfad hat AD 100 und FD 150, der Successor hat FD 120. Ist der Pfad Feasible Successor?
<details><summary>Antwort</summary>

Ja: Die Bedingung vergleicht die AD des Nachbarn (100) mit der FD des Successors (120), 100 < 120. Die eigene FD (150) des Pfades ist dafür unerheblich, sie bestimmt nur, ob er mit Variance genutzt werden kann.

</details>

2. Welche K-Werte sind Default und warum müssen sie auf beiden Nachbarn identisch sein?
<details><summary>Antwort</summary>

K1=K3=1 (Bandwidth und Delay), K2=K4=K5=0. Unterschiedliche K-Werte verhindern die Nachbarschaft (`K-value mismatch`), weil die Metriken nicht vergleichbar wären.

</details>

3. Wie finden OSPFv3-Nachbarn einander, wenn es keine IPv4-Adresse gibt?
<details><summary>Antwort</summary>

Per Link-Local-IPv6-Adresse (fe80::) und Multicast FF02::5/FF02::6. Die Router-ID bleibt 32 Bit und muss manuell gesetzt werden, falls keine IPv4-Adresse existiert.

</details>

## Prüfungsbezug

EIGRP-Named-Mode-Hierarchie, Feasibility Condition (AD < FD), Variance nur mit Feasible Successors, Admin-Distanzen (EIGRP intern 90, extern 170, summary 5), OSPFv3-Router-ID Pflicht, Link-Local als Next-Hop.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/02-EIGRP-OSPFv3/`](../../CML-Labs/02-EIGRP-OSPFv3/).
