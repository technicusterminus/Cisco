# Lab 27 – Redistribution zwischen OSPF und EIGRP mit Tags und Filtern

**Plattform:** EVE-NG · **Dauer:** 100 min · **Niveau:** schwer

Zwei Routing-Domänen (OSPF und EIGRP) werden an **zwei** Punkten gegenseitig verbunden. Ohne Schutz entstehen Routing-Schleifen und Rückkopplungen. Du lernst Metrik-Zuweisung, Route-Tags, Route-Maps und Prefix-Listen als Filter.

**Lernziele:** Nach diesem Lab kannst du …

- Routen zwischen OSPF und EIGRP gegenseitig redistribuieren.
- Seed-Metrik und `subnets` richtig setzen.
- Rückkopplungen an zwei Redistributionspunkten mit Route-Tags verhindern.

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
| R4 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.0 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R1 | Gi0/1 | R3 | Gi0/0 |
| R2 | Gi0/1 | R4 | Gi0/0 |
| R3 | Gi0/1 | R4 | Gi0/1 |


## Topologie

```
        R1 (Lo10 10.1.0.0/24)           OSPF 1 (Area 0)
      Gi0/0 /        \ Gi0/1
        R2              R3            R2/R3 = ASBR (OSPF <-> EIGRP)
      Gi0/1 \        / Gi0/1
            R4 (Lo10 10.4.0.0/24, Lo11 10.4.1.0/24)   EIGRP 100
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2), OSPF |
| R1 Gi0/1 – R3 Gi0/0 | 10.0.13.0/30 (.1/.2), OSPF |
| R2 Gi0/1 – R4 Gi0/0 | 10.0.24.0/30 (.1/.2), EIGRP |
| R3 Gi0/1 – R4 Gi0/1 | 10.0.34.0/30 (.1/.2), EIGRP |

Loopback0: R1 10.255.0.1, R2 .2, R3 .3, R4 .4. R1 Lo10 10.1.0.1/24 (OSPF-LAN), R4 Lo10 10.4.0.1/24 und Lo11 10.4.1.1/24 (EIGRP-LANs). **Vorgabe:** 10.4.1.0/24 ist lokal und darf nicht nach OSPF gelangen. Der Weg über R2 soll bevorzugt werden (R2 Metrik 20, R3 Metrik 100).

## Teil A – Bauen

1. **Domänen aufbauen.** OSPF 1 Area 0 auf R1 (alle Links, Loopbacks, Lo10 mit `ip ospf network point-to-point`, damit /24 statt /32 angekündigt wird), R2 und R3 (jeweils Richtung R1). EIGRP 100 auf R2, R3, R4 (Richtung R4, Lo10/Lo11, `no auto-summary`). Prüfe, dass R1 nichts von R4 weiß.
2. **Einfache Redistribution.** Nur auf R2: `redistribute eigrp 100 subnets` in OSPF und `redistribute ospf 1 metric 10000 100 255 1 1500` in EIGRP. Warum braucht EIGRP einen Seed-Metric (Bandbreite, Delay, Reliability, Load, MTU), OSPF nur optional (Standard 20, Typ E2)? Prüfe auf R1 `show ip route ospf` (`O E2`) und auf R4 `show ip route eigrp` (`D EX`, AD 170).
3. **Zweiter ASBR.** Ergänze dasselbe auf R3. Beobachte `show ip route` auf R2/R3/R4: Es entstehen Routen, die im Kreis laufen (Feedback), weil R3 die von R2 in EIGRP injizierten OSPF-Routen zurück nach OSPF gibt.
4. **Tags gegen Rückkopplung.** Route-Maps: `E2O` (EIGRP→OSPF): `deny` bei Tag 1 (kam aus OSPF), sonst `permit` mit `set tag 2` und Metrik; `O2E` (OSPF→EIGRP): `deny` bei Tag 2, sonst `permit` mit `set tag 1`. Setze die Route-Maps auf R2 und R3 an die `redistribute`-Befehle. Prüfe mit `show ip route 10.1.0.0` auf R4, dass Tag 1 sichtbar ist, und dass keine Schleife entsteht.
5. **Metrik steuern.** In `E2O` auf R2 `set metric 20`, auf R3 `set metric 100`: Welchen Weg wählt R1 für 10.4.0.0/24? Wie würdest du Typ E1 statt E2 setzen und wann ist das sinnvoll?
6. **Filter.** Prefix-Liste `LOCAL-ONLY` (`permit 10.4.1.0/24`), in `E2O` als erste Zeile (`deny`) mit `match ip address prefix-list LOCAL-ONLY`. Prüfe, dass 10.4.1.0/24 auf R1 fehlt, 10.4.0.0/24 aber da ist.
7. **Verwandtes.** `distribute-list` (bei EIGRP/OSPF-intern), `administrative distance` pro Quelle, `redistribute connected`, `default-information originate`. Wann ist einseitige Redistribution mit Default-Route statt gegenseitiger Redistribution besser?

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **6 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** R4 lernt über R2 keine OSPF-Routen; `show ip route` auf R4 zeigt 10.1.0.0/24 nur (falls überhaupt) über R3.

**Ticket 2:** Über R3 erscheinen keine EIGRP-Netze in OSPF; R1 sieht 10.4.0.0/24 nur über R2 mit Metrik 20.

**Ticket 3:** Auf R4 und R3 pendelt 10.1.0.0/24 zwischen den Domänen, R1 sieht die eigene Route als `O E2` mit Tag 2 zurück (Rückkopplung).

**Ticket 4:** R1 lernt 10.4.1.0/24, obwohl das Netz lokal bleiben sollte.

**Ticket 5:** R3 und R4 haben keine EIGRP-Nachbarschaft; R4 erreicht OSPF-Netze nur über R2.

**Ticket 6:** R1 und R3 bilden keine OSPF-Nachbarschaft; im Log `Mismatched Area ID`/hängt in `INIT`.

## Verifikation

```
show ip route ospf / eigrp
show ip route 10.4.0.0           ! Tag, Typ, Metrik
show ip ospf database external
show ip eigrp topology
show route-map
show ip prefix-list
```
Erwartet: R1 `O E2 10.4.0.0/24` mit Tag 2 über R2 (Metrik 20), kein 10.4.1.0/24; R4 `D EX 10.1.0.0/24` mit Tag 1 über R2 und R3, keine Routen mit Tag 2 zurück.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. R2 redistribuiert EIGRP nach OSPF, aber in OSPF erscheint nur das klassische Netz 10.0.0.0/8, nicht die /24. Ursache?
<details><summary>Antwort</summary>

**`subnets` fehlt.** Ohne dieses Schlüsselwort übernimmt OSPF nur klassenbehaftete Netze. Mit `redistribute eigrp 100 subnets` kommen alle Subnetze.

</details>

2. Wozu setzt man beim Redistribuieren Route-Tags?
<details><summary>Antwort</summary>

**Um zu markieren, woher eine Route stammt.** Ein zweiter Redistributionspunkt erkennt am Tag eine Route aus der anderen Domäne und gibt sie nicht zurück. So verhindert man Rückkopplungen, ohne Prefix-Lists pflegen zu müssen.

</details>

3. Warum ist gegenseitige Redistribution an zwei Punkten riskanter als an einem?
<details><summary>Antwort</summary>

**Weil Routen über den zweiten Punkt zurück in ihre Ursprungsdomäne fließen können.** Dort kommen sie mit schlechterer Metrik oder anderer AD an. Die Folge: Umwege oder Schleifen. Mit nur einem Punkt gibt es das nicht, dafür aber auch keine Redundanz.

</details>

## Prüfungsbezug

Redistribution braucht eine Metrik im Zielprotokoll (EIGRP: fünf Werte, OSPF: Standard 20, BGP: Metrik der IGP). Ohne `subnets` übernimmt OSPF nur klassische Netze. Bei mehreren ASBRs verhindern Route-Tags und Route-Maps Rückkopplungen; die Distanz (AD) schützt nur teilweise (EIGRP extern 170, OSPF 110). Typ E2: Metrik bleibt gleich, E1: addiert die interne Kosten.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/27-Redistribution-Routenfilter/`](../../CML-Labs/27-Redistribution-Routenfilter/).
