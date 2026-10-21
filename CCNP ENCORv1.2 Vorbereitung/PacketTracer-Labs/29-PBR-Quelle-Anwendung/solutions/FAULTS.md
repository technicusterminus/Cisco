# Fehlerliste – Lab 29 – Policy-Based Routing nach Quelle und Anwendung

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** H2 und Web-Verkehr gehen über Provider A; `show ip policy` ist leer.
- **So findest du es:** `show ip policy` ist leer. `show ip interface Gi0/2 | include policy` meldet keine Policy.
- **Ursache:** Die Route-Map ist nicht am Eingangs-Interface Gi0/2 aktiviert.
- **Fix:** `ip policy route-map PBR` unter Gi0/2.
- **Eingebaut:**

```diff
-  ip policy route-map PBR
```

## Ticket 2 (R1)

- **Symptom:** H2 nimmt den normalen Weg, die Zähler der Sequenz 10 bleiben 0.
- **So findest du es:** `show route-map PBR` zeigt bei Sequenz 10 null Treffer. `show access-lists` zeigt die Host-Adresse .21 statt .12.
- **Ursache:** Die ACL trifft die falsche Quelladresse (10.1.0.21).
- **Fix:** Host-Adresse auf 10.1.0.12 korrigieren.
- **Eingebaut:**

```diff
-  permit ip host 10.1.0.12 any
+  permit ip host 10.1.0.21 any
```

## Ticket 3 (R1)

- **Symptom:** H2 geht über Provider A, obwohl Sequenz 10 auf `permit` steht und in `show route-map PBR` Treffer zählt.
- **So findest du es:** `show route-map PBR` zeigt bei Sequenz 10 den Next-Hop 10.0.31.2. `show ip route 10.0.31.2` liefert nur die Default über R2: Die Adresse liegt in keinem angeschlossenen Netz.
- **Ursache:** Zahlendreher im Next-Hop (10.0.31.2 statt 10.0.13.2). `set ip next-hop` greift nur, wenn der Next-Hop direkt angeschlossen ist. Sonst ignoriert R1 die Anweisung und routet das Paket normal, also über die Default zu Provider A.
- **Fix:** Next-Hop 10.0.13.2 (R3).
- **Eingebaut:**

```diff
-  set ip next-hop 10.0.13.2
+  set ip next-hop 10.0.31.2
```

## Ticket 4 (R1)

- **Symptom:** H2 geht über Provider A, obwohl ACL und Next-Hop stimmen; nur Web-Verkehr (Sequenz 20) wird umgeleitet.
- **So findest du es:** `show route-map PBR` zeigt Sequenz 10 als `deny`. Nur Sequenz 20 zählt Treffer.
- **Ursache:** `deny` in einer PBR-Route-Map heißt: Das Paket wird nicht per Policy behandelt, sondern normal geroutet.
- **Fix:** Sequenz 10 auf `permit`.
- **Eingebaut:**

```diff
- route-map PBR permit 10
+ route-map PBR deny 10
```

## Ticket 5 (R3)

- **Symptom:** H2 (über Provider B) erreicht den Server nicht; die Traceroute endet bei R3.
- **So findest du es:** `traceroute` von H2 endet bei R3. `show ip route 192.0.2.44` auf R3 findet nichts.
- **Ursache:** R3 hat keine Route zum Server: Das Paket wird verworfen.
- **Fix:** Statische Route auf R3 (`ip route 192.0.2.44 255.255.255.255 10.0.34.2`).
- **Eingebaut:**

```diff
- ip route 192.0.2.44 255.255.255.255 10.0.34.2
```

