# Lab 30 – Capstone: Routing-Fehlersuche (OSPF, EIGRP, BGP, Redistribution)

**Dauer:** 150 min · **Niveau:** schwer · **Nodes:** 5× iosv

Ein Unternehmensnetz mit OSPF (Area 0 und Stub-Area 1), einem EIGRP-Standort, eBGP zum Provider und Default-Route-Weitergabe. Acht Fehler quer durch alle Protokolle, teils voneinander verdeckt: Die Aufgabe ist reine Fehlersuche, wie in der Prüfung.

**Lernziele:** Nach diesem Lab kannst du …

- Ein Netz mit BGP, OSPF (inklusive Stub-Area), EIGRP und Redistribution durchgängig verfolgen.
- Hinweg und Rückweg getrennt prüfen.
- Unter Zeitdruck Fehler in der richtigen Reihenfolge abarbeiten.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.2.a` | EIGRP und OSPF vergleichen | 45 |
| `Ziel::3.2.b` | OSPFv2 und OSPFv3 | 86 |
| `Ziel::3.2.c` | Direktes eBGP | 61 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
   ISP (65000, Lo10 203.0.113.0/24)
     │ 198.51.100.0/30
     R1 (AS 65001, OSPF ASBR, default-originate)
     │ 10.0.12.0/30 (Area 0)
     R2 (ABR + ASBR zu EIGRP)
  Gi0/1 /      \ Gi0/2
 10.0.23.0/30   10.0.24.0/30
 R3 (Area 1 stub)   R4 (EIGRP 100, Lo10 172.20.4.0/24)
 Lo10 192.168.3.0/24
```

| Link | Netz |
|---|---|
| ISP Gi0/0 – R1 Gi0/0 | 198.51.100.0/30 (ISP .2, R1 .1), eBGP |
| R1 Gi0/1 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2), OSPF Area 0 |
| R2 Gi0/1 – R3 Gi0/0 | 10.0.23.0/30 (.1/.2), OSPF Area 1 (Stub) |
| R2 Gi0/2 – R4 Gi0/0 | 10.0.24.0/30 (.1/.2), EIGRP 100 |

Loopback0: R1 10.255.0.1, R2 .2, R3 .3 (Area 1), R4 .4 (EIGRP). R3 Lo10 192.168.3.1/24, R4 Lo10 172.20.4.1/24, ISP Lo10 203.0.113.1/24. **Soll:** Alle internen Netze erreichen 203.0.113.1 über eine Default-Route (aus BGP in OSPF, R4 per statischer Default auf R2); R4s Netz ist in OSPF sichtbar; der ISP hat statische Rückrouten für die internen Netze.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

Dieses Lab ist vor allem zum Reparieren gedacht. Wenn du es selbst baust, gehe von außen nach innen vor: Provider, OSPF, EIGRP, dann die Verbindung dazwischen.

1. **Provider.** Baue eBGP zwischen R1 (AS 65001) und ISP (AS 65000) auf. Der ISP schickt mit `neighbor 198.51.100.1 default-originate` eine Default-Route und kündigt 203.0.113.0/24 an. Für den Rückweg bekommt der ISP statische Routen zu 10.0.0.0/8, 172.20.0.0/16 und 192.168.0.0/16, alle über R1.
   - **Prüfen:** `show ip bgp summary` auf R1 zeigt den ISP Established. `show ip route` auf R1 enthält `B* 0.0.0.0/0`.
2. **OSPF.** Area 0 zwischen R1 und R2, Area 1 als Stub zwischen R2 und R3 (`area 1 stub` auf beiden). R1 gibt die Default-Route mit `default-information originate` in OSPF weiter. Die Loopbacks von R3 bekommen `ip ospf network point-to-point`.
   - **Prüfen:** R2 hat `O*E2 0.0.0.0/0`, R3 eine Default-Route `O*IA` vom ABR.
3. **EIGRP-Standort.** Starte EIGRP 100 auf R2 und R4 für den Link und Lo10 von R4, mit `no auto-summary`. R4 bekommt `ip route 0.0.0.0 0.0.0.0 10.0.24.1`.
   - **Prüfen:** `show ip eigrp neighbors` zeigt R2 und R4 als Nachbarn.
4. **Redistribution.** Setze auf R2 `redistribute eigrp 100 subnets` unter OSPF und `redistribute ospf 1 metric 10000 100 255 1 1500` unter EIGRP.
   - **Prüfen:** R1 sieht `O E2 172.20.4.0/24`, R4 sieht die OSPF-Netze als `D EX`.
   - **Denkfrage:** Warum braucht es hier keine Tags?
5. **Abnahme.** Pinge von R3 und R4 mit `ping 203.0.113.1 source Loopback10`. Prüfe `show ip route` auf allen Routern.
   - **Prüfen:** Beide Pings klappen. Du findest die Codes `B`, `O*E2`, `O IA`, `O E2` und `D EX`.

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 4:** Es gibt nur einen Punkt, an dem Routen zwischen OSPF und EIGRP wechseln. Eine Route kann nicht über einen zweiten Punkt in ihre Ursprungsdomäne zurückfließen. Tags braucht man erst bei zwei oder mehr Punkten (siehe Lab 27).

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **8 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Kein BGP: R1 hat keine Default-Route, R2/R3/R4 erreichen 203.0.113.1 nicht.

**Ticket 2:** BGP steht, R1 hat eine Default-Route, aber R2 und R3 haben keine.

**Ticket 3:** R2 und R3 bilden keine Nachbarschaft; Mismatched Stub/Transit-Option im Debug.

**Ticket 4:** R1 und R3 sehen 172.20.4.0/24 nicht.

**Ticket 5:** Auf R4 fehlen die OSPF-Routen (R3-Loopback, 10.0.12.0/30); nur die statische Default erreicht R2.

**Ticket 6:** R4 erreicht 203.0.113.1 nicht, schon der erste Hop im Traceroute bleibt stumm. Die Default-Route steht aber in `show ip route`.

**Ticket 7:** Das Netz 192.168.3.0/24 fehlt auf R1/R2, Pings von R3-Lo10 ins Internet scheitern am Rückweg.

**Ticket 8:** Pings aus den 10er-Netzen an 203.0.113.1 scheitern auf dem Rückweg, obwohl das Routing intern stimmt. Der Traceroute zeigt den Hinweg bis zum ISP.

## Verifikation
```
show ip bgp summary           show ip route bgp
show ip ospf neighbor         show ip route ospf
show ip eigrp neighbors       show ip route eigrp
ping 203.0.113.1 source Loopback10
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip bgp summary` auf R1 | ISP Established |
| `show ip route` auf R2 und R3 | eine Default-Route (`O*E2` bzw. `O*IA`) |
| `show ip route ospf` auf R1 | `O E2 172.20.4.0/24` |
| Ping von R3 und R4 an 203.0.113.1 | erfolgreich |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Alle OSPF-Nachbarschaften sind `FULL`, aber R3 hat keine Default-Route. Prüfpunkte in Reihenfolge?
<details><summary>Antwort</summary>

**Den Weg der Default-Route verfolgen: BGP, dann OSPF, dann Stub.** Auf R1: `show ip route 0.0.0.0` (kommt die Default per BGP?) und ob `default-information originate` gesetzt ist. Auf R2: Steht die Default als `O*E2` in der Tabelle? Ist Area 1 auf beiden Seiten `stub`? Dann erzeugt der ABR die Default für R3.

</details>

2. Ping R4-Loopback → 203.0.113.1 scheitert, `traceroute` endet an R1. Wo liegt vermutlich das Problem?
<details><summary>Antwort</summary>

**Hinter R1, und zwar wahrscheinlich auf dem Rückweg.** Bis R1 ist der Hinweg da. Entweder fehlt die BGP-Default auf R1, oder der ISP kennt 172.20.0.0/16 nicht und schickt die Antwort nicht zurück. Prüfe `show ip route` auf dem ISP.

</details>

3. Warum ist die Redistribution an einem Punkt hier ohne Tags ungefährlich?
<details><summary>Antwort</summary>

**Weil es nur einen Punkt zwischen den Domänen gibt.** Eine Route kann nicht über einen zweiten Punkt zurückfließen. Erst bei zwei Redistributionspunkten braucht man Tags oder Filter (siehe Lab 27).

</details>

## Prüfungsbezug
- Vorgehen bei Routing-Fehlern: erst die Nachbarschaft (Zustand bei OSPF, EIGRP, BGP), dann die Routen (welcher Code, welche Distanz), dann die Weiterleitung (Next-Hop, Rückweg).
- Bei Redistribution immer die Metrik (EIGRP: fünf Werte) und `subnets` prüfen.
- In OSPF kommt eine Default-Route nur mit `default-information originate`. In Stub-Areas erzeugt der ABR sie selbst.
- Ein Ping braucht Hin- und Rückweg.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
