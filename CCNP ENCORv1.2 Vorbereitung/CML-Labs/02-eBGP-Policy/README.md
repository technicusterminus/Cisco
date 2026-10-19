# Lab 02 – eBGP Dual-Homing und Policy

**Blueprint:** 3.2.c (BGP), 3.2.d teilweise (Route-Maps) · **Deck-Tags:** `Ziel::3.2.c`
**Dauer:** ca. 60–90 min · **Nodes:** 4× IOSv

## Topologie

```
            AS 65010            AS 65100
         ┌── R2 ───────┐
 AS 65001│  Gi0/0 Gi0/1│
   R1 ───┤             ├── R4  (Internet, 198.51.100.0/24)
         │  Gi0/0 Gi0/1│
         └── R3 ───────┘
            AS 65020
```

| Link | Netz | Seiten |
|---|---|---|
| R1–R2 | 10.12.0.0/30 | R1 .1 / R2 .2 |
| R1–R3 | 10.13.0.0/30 | R1 .1 / R3 .2 |
| R2–R4 | 10.24.0.0/30 | R2 .1 / R4 .2 |
| R3–R4 | 10.34.0.0/30 | R3 .1 / R4 .2 |

R1 = Kunde (AS 65001) mit Präfix **203.0.113.0/24** (statisch Null0, wird per `network` angekündigt). R2 = ISP-A (AS 65010), R3 = ISP-B (AS 65020), R4 = „Internet“ (AS 65100) mit **198.51.100.0/24** auf Loopback1. Private AS-Nummern werden hier nur zu Übungszwecken benutzt.

## Aufgaben

1. **eBGP-Sessions.** Baue die vier eBGP-Sessions auf (R1–R2, R1–R3, R2–R4, R3–R4), Peering über die direkten Interface-Adressen. Router-ID = Loopback0.
2. **Präfixe ankündigen.** R1 kündigt 203.0.113.0/24 an, R4 kündigt 198.51.100.0/24 an. Prüfe, dass beide Seiten jeweils den Pfad über beide ISPs sehen. Welches Attribut entscheidet aktuell, welchen Pfad R1 zu 198.51.100.0/24 wählt, und warum wählt BGP bei Gleichstand trotzdem einen? (Reihenfolge der Best-Path-Auswahl nennen.)
3. **Ausgehend steuern (Local-Preference).** R1 soll Verkehr ins Internet **bevorzugt über ISP-A (R2)** senden, ISP-B nur als Backup. Setze `local-preference 200` für alles, was von R2 gelernt wird, per Route-Map **eingehend**. Warum ist Local-Preference nur innerhalb der AS wirksam und was ändert das bei einem iBGP-Design mit mehreren Border-Routern?
4. **Eingehend steuern (AS-Path-Prepending).** Eingehender Verkehr aus dem Internet soll ebenfalls **über ISP-A** kommen. R1 stellt bei Ankündigung an R3 den eigenen AS dreimal voran. Prüfe auf R4, welchen Pfad R4 zu 203.0.113.0/24 wählt, und welcher AS-Path bei R3 ankommt.
5. **MED.** Entferne das Prepending und setze stattdessen auf R1 bei der Ankündigung an R2 `metric 50`, an R3 `metric 100`. Wirkt MED bei R4? Begründe, warum nicht (zwei verschiedene Nachbar-ASe) und was `bgp always-compare-med` ändern würde.
6. **No-Transit-Filter.** R1 darf nicht zum Transit zwischen ISP-A und ISP-B werden. Ohne Filter würde R1 die Routen von R2 an R3 weitergeben und umgekehrt. Verhindere das mit einer Route-Map, die **ausgehend** nur lokal erzeugte Routen erlaubt (`ip as-path access-list 1 permit ^$`). Prüfe auf R2/R3, was jeweils ankommt.
7. **Soft Reset / Policy-Änderungen.** Ändere eine Route-Map und wende sie an, ohne die Session zu resetten (`clear ip bgp * soft in/out` bzw. Route Refresh). Warum ist `clear ip bgp *` im Betrieb ein Fehler?
8. **Optional: Präfix-Limit und Bogon-Filter.** Setze auf R1 `neighbor … maximum-prefix 100 80` und blockiere eingehend 10.0.0.0/8 per Prefix-List.

## Verifikation

```
show ip bgp summary
show ip bgp
show ip bgp 198.51.100.0/24
show ip bgp neighbors 10.12.0.2 advertised-routes
show ip bgp neighbors 10.12.0.2 received-routes   ! nur mit soft-reconfiguration inbound
show route-map
show ip bgp regexp ^65010
```

Erwartet nach Aufgabe 3: R1 wählt zu 198.51.100.0/24 den Next-Hop 10.12.0.2 (LocPrf 200). Nach Aufgabe 4: R4 wählt zu 203.0.113.0/24 den Pfad über R2 (kürzerer AS-Path).

## Lösungen

Siehe [`solutions/`](solutions/).

## Prüfungsbezug

Die Best-Path-Reihenfolge (Weight → Local-Pref → lokal erzeugt → AS-Path-Länge → Origin → MED → eBGP vor iBGP → IGP-Metrik → älteste Route → Router-ID) kommt in Prüfungsfragen immer wieder. Local-Pref und Weight steuern **ausgehend**, AS-Path-Prepending und MED steuern **eingehend**.
