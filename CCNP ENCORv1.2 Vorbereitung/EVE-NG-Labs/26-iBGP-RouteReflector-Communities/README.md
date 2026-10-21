# Lab 26 – iBGP mit Route Reflector, Local Preference und Communities

**Plattform:** EVE-NG · **Dauer:** 100 min · **Niveau:** schwer

Ein AS mit drei Routern und zwei Upstream-Providern: iBGP über Loopbacks mit Route Reflector, `next-hop-self`, Pfadsteuerung per Local Preference und Markierung per Community. Der OSPF-Underlay liefert die Loopback-Erreichbarkeit.

**Lernziele:** Nach diesem Lab kannst du …

- iBGP mit Route Reflector und Loopback-Peering aufbauen.
- Next-Hop-Probleme in iBGP erkennen und mit `next-hop-self` lösen.
- Mit Local Preference und Communities den Ausgang des ganzen AS steuern.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.2.c` | Direktes eBGP | 61 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| ISP1 | Cisco vIOS Router |  | 512 |
| ISP2 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.5 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.5 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R1 | Gi0/1 | R3 | Gi0/0 |
| R2 | Gi0/1 | ISP1 | Gi0/0 |
| R3 | Gi0/1 | ISP2 | Gi0/0 |


## Topologie

```
                R1 (RR, AS 65001)
          Gi0/0 /          \ Gi0/1
     10.0.12.0/30        10.0.13.0/30
            R2              R3
       Gi0/1 │              │ Gi0/1
    192.0.2.0/30         192.0.2.4/30
          ISP1 (65100)    ISP2 (65200)
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R1 Gi0/1 – R3 Gi0/0 | 10.0.13.0/30 (.1/.2) |
| R2 Gi0/1 – ISP1 Gi0/0 | 192.0.2.0/30 (.1/.2) |
| R3 Gi0/1 – ISP2 Gi0/0 | 192.0.2.4/30 (.5/.6) |

Loopback0 (/32): R1 10.255.0.1, R2 10.255.0.2, R3 10.255.0.3. OSPF 1 Area 0 trägt die internen Netze (nicht die Provider-Links). Provider-Prefixe: ISP1 kündigt 203.0.113.0/24 und 198.51.100.0/24 an, ISP2 kündigt 203.0.113.0/24 und 198.18.0.0/24 an (gleicher Prefix von zwei Providern!).

## Teil A – Bauen

1. **Underlay.** OSPF 1 Area 0 für Links und Loopbacks (`network 10.0.0.0 0.255.255.255 area 0`) auf R1 bis R3. Prüfe, dass R2 die Loopback von R3 per Ping erreicht.
2. **iBGP mit Route Reflector.** R1 als RR: `neighbor 10.255.0.2/.3 remote-as 65001`, `update-source Loopback0`, `route-reflector-client`. R2 und R3 peeren **nur** zu R1. Warum braucht iBGP sonst eine Vollvermaschung, und was löst der RR? Welche Attribute (`ORIGINATOR_ID`, `CLUSTER_LIST`) verhindern Schleifen?
3. **eBGP.** R2 zu ISP1 (65100), R3 zu ISP2 (65200). Prüfe `show ip bgp summary`.
4. **Next-Hop.** Die Provider-Links stehen nicht im OSPF. Setze auf R2 und R3 `neighbor 10.255.0.1 next-hop-self`. Was passiert ohne (Next-Hop nicht erreichbar, Route `inaccessible`)?
5. **Local Preference.** Auf R2: Route-Map `ISP1-IN` in Richtung ISP1 mit `set local-preference 200`. Prüfe auf R3 `show ip bgp 203.0.113.0`: Welcher Pfad gewinnt und warum (Local-Pref vor AS-Pfadlänge)? Wohin geht ein Ping von R3 an 203.0.113.1?
6. **Communities.** In derselben Route-Map `set community 65001:100 additive`, global `ip bgp-community new-format`, `neighbor … send-community` zwischen R1, R2 und R3. Prüfe `show ip bgp community 65001:100` auf R3. Wozu setzt man Communities (Policy-Weitergabe ohne Prefix-Listen)?
7. **Pfadauswahl.** Schreibe die Entscheidungsreihenfolge auf (Weight, Local-Pref, lokal erzeugt, AS-Pfadlänge, Origin, MED, eBGP vor iBGP, IGP-Metrik zum Next-Hop, Router-ID).

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **6 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Die iBGP-Session R1–R3 bleibt `Active`/`Idle`, auf R1 steht R3 nicht im Zustand `Established`.

**Ticket 2:** R1 und R3 listen die Prefixe von ISP1 mit Next-Hop 192.0.2.2 ohne `>` (nicht Best), `show ip bgp` zeigt `inaccessible`.

**Ticket 3:** Der Verkehr zu 203.0.113.0/24 verlässt das AS über ISP2, obwohl ISP1 bevorzugt sein soll.

**Ticket 4:** R3 zeigt `show ip bgp community 65001:100` leer, obwohl R2 die Community setzt und R1 sie hat.

**Ticket 5:** Die eBGP-Session R3–ISP2 steht auf `Idle`; im Log `Notification … (peer in wrong AS)`.

**Ticket 6:** R1 und R3 erreichen 10.255.0.2 nicht, die iBGP-Session zu R2 bleibt unten, obwohl der Link steht.

## Verifikation

```
show ip bgp summary
show ip bgp
show ip bgp 203.0.113.0
show ip bgp community 65001:100
show ip route bgp
```
Erwartet: R1 hat zwei Peers (Clients), R3 sieht 203.0.113.0/24 mit Local-Pref 200 über R2 (Next-Hop 10.255.0.2), 198.18.0.0/24 direkt über ISP2.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. R3 sieht Routen von ISP1, markiert als `inaccessible`. Ursache und Fix?
<details><summary>Antwort</summary>

**Der Next-Hop 192.0.2.2 ist im IGP unbekannt.** iBGP gibt den eBGP-Next-Hop unverändert weiter, und R3 kann ihn nicht auflösen. Lösung: `next-hop-self` auf R2 zum RR, oder die Provider-Links ins IGP aufnehmen, z. B. als passives OSPF-Interface.

</details>

2. Warum reicht `route-reflector-client` allein nicht, wenn Communities beim Client ankommen sollen?
<details><summary>Antwort</summary>

**Weil Communities ohne `send-community` gar nicht verschickt werden.** Das gilt pro Nachbar und ist standardmäßig aus. Auch der RR muss `send-community` zum Client gesetzt haben.

</details>

3. Zwei Pfade zum selben Prefix: Local-Pref 200 mit AS-Pfad 3 Hops, Local-Pref 100 mit 1 Hop. Wer gewinnt?
<details><summary>Antwort</summary>

**Der Pfad mit Local Preference 200.** Local Preference steht in der Best-Path-Reihenfolge vor der Länge des AS-Pfads. Die drei Hops spielen also keine Rolle mehr.

</details>

## Prüfungsbezug

iBGP-Nachbarn leiten Routen nicht an andere iBGP-Nachbarn weiter (Split Horizon), Route Reflector oder Konföderation lösen das. Next-Hop bleibt bei iBGP unverändert (`next-hop-self`). Local Preference wirkt nur innerhalb des AS (Standard 100, höher gewinnt), MED zwischen benachbarten AS (niedriger gewinnt). `send-community` ist für Communities nötig. eBGP-AD 20, iBGP 200.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/26-iBGP-RouteReflector-Communities/`](../../CML-Labs/26-iBGP-RouteReflector-Communities/).
