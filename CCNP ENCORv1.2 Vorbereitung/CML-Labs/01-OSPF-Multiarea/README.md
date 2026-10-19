# Lab 01 – OSPF Multi-Area

**Blueprint:** 3.2.a (OSPF-Konzepte), 3.2.b (OSPF-Konfiguration), 5.3 (Routing-Authentifizierung) · **Deck-Tags:** `Ziel::3.2.a`, `Ziel::3.2.b`
**Dauer:** ca. 60–90 min · **Nodes:** 4× IOSv, 1× Unmanaged Switch

## Topologie

```
 Area 0              Area 1 (10.1.234.0/24)
 R1 ---- R2(ABR) ---- SW ---- R3 (Lo10-13 = 10.1.16-19.0/24)
 .1   .2        .2          |---- R4 (externes Netz 198.51.100.0/24 via Null0)
 10.0.12.0/30
```

| Gerät | Interface | Adresse |
|---|---|---|
| R1 | Lo0 / Gi0/0 | 1.1.1.1/32 / 10.0.12.1/30 |
| R2 | Lo0 / Gi0/0 / Gi0/1 | 2.2.2.2/32 / 10.0.12.2/30 / 10.1.234.2/24 |
| R3 | Lo0 / Gi0/0 / Lo10–13 | 3.3.3.3/32 / 10.1.234.3/24 / 10.1.16–19.1/24 |
| R4 | Lo0 / Gi0/0 | 4.4.4.4/32 / 10.1.234.4/24 (+ static 198.51.100.0/24 → Null0) |

Die Startkonfiguration enthält nur IP-Adressen. Das gesamte Routing baust du selbst.

## Aufgaben

1. **OSPF aufbauen.** Process-ID 1, Router-ID = jeweilige Loopback0. Die Link R1–R2 gehört zu Area 0, das LAN 10.1.234.0/24 und die Loopbacks 10–13 von R3 zu Area 1. Aktiviere OSPF **pro Interface** (`ip ospf 1 area X`), nicht per `network`-Statement. Loopback0 aller Router in Area 0 bzw. Area 1 passend zum Standort (R1/R2: Area 0, R3/R4: Area 1).
2. **DR/BDR steuern.** Im LAN soll **R3 DR** und **R4 BDR** sein, R2 darf nie DR/BDR werden. Löse das ohne Router-ID-Änderung.
3. **Passive Interfaces.** Setze auf R3 alle Loopbacks 10–13 passiv, Interface-Subnetze sollen weiter im LSDB bleiben. Nutze `passive-interface default` und öffne nur die nötigen Interfaces.
4. **Summarization.** R2 (ABR) soll die vier Netze 10.1.16.0–10.1.19.0/24 als **eine** Route nach Area 0 senden. Prüfe auf R1, dass nur die Zusammenfassung erscheint. Welche Maske?
5. **Externe Route.** R4 verteilt das Netz 198.51.100.0/24 per `redistribute static` ein (Metrik-Typ E1). Prüfe auf R1 den Code (`O E1`) und wie sich die Metrik gegenüber E2 unterscheidet. Welche Rolle spielt R2 hier (ASBR vs. ABR, Typ-4-LSA)?
6. **Stub-Bereich.** Mache Area 1 zu einer **Totally Stubby Area**. Was passiert mit der externen Route von R4 und was siehst du stattdessen auf R3? Danach: Ändere Area 1 in eine **NSSA**, sodass R4 seine externe Route weiterhin einspeisen kann. Welcher LSA-Typ transportiert sie, und wer wandelt sie um?
7. **Authentifizierung.** Aktiviere in Area 0 **SHA-256** Authentifizierung (OSPFv2 Key Chain mit `cryptographic-algorithm hmac-sha-256`) auf der Strecke R1–R2. Bring den Nachbarn dazu, in `down` zu fallen, indem du auf R1 einen falschen Key setzt, und lies die Fehlermeldung im Log.
8. **Timer.** Setze auf R1/R2 Hello 3 / Dead 12. Beobachte, was passiert, wenn nur eine Seite geändert wird, und lies die Ursache aus `debug ip ospf hello` (danach `undebug all`).
9. **Fehlersuche.** Lass einen Mitstreiter (oder dein späteres Ich) auf R3 `ip ospf network point-to-point` setzen. Warum bleibt die Nachbarschaft zu R4 und R2 in einem unklaren Zustand oder fällt aus? Wie erkennst du es mit `show ip ospf interface`?

## Verifikation

```
show ip ospf neighbor
show ip ospf interface brief
show ip ospf database
show ip route ospf
show ip ospf database summary / external / nssa-external
show ip protocols
```

Erwartet nach Aufgabe 1–5:

- R1: `O IA 10.1.16.0/22` (nur die Zusammenfassung), `O IA 10.1.234.0/24`, `O E1 198.51.100.0/24`.
- LAN: R3 `DR`, R4 `BDR`, R2 `DROTHER` (Priorität 0 auf R2).

## Lösungen

Musterkonfigurationen liegen in [`solutions/`](solutions/). Versuche es zuerst ohne.

## Prüfungsbezug

Typische Fallen, die du hier selbst erlebst: DR-Wahl ist nicht präemptiv, Hello/Dead müssen passen, Area-Typen müssen auf allen Routern der Area übereinstimmen (E-Flag/N-Flag im Hello), Summarization geht nur am ABR (`area range`) bzw. ASBR (`summary-address`), Metrik-Typ E1 addiert interne Kosten.
