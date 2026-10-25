# Fehlerliste – Lab C3 – OSPF: Virtual Link mit Authentisierung, NSSA, Typ-3-Filter und Netzwerktypen

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R5)

- **Symptom:** R5 steht mit R2 in FULL, hat aber keine einzige OSPF-Route. R2 kennt das LAN von R5 (10.5.5.0/24) nicht.
- **So findest du es:** `show ip ospf interface GigabitEthernet0/0` auf R5: Netzwerktyp POINT_TO_POINT. Auf R2 ist Gi0/1 BROADCAST mit R2 als DR. Die Hello- und Dead-Timer sind gleich (10/40), deshalb wird die Nachbarschaft FULL. In der Datenbank beschreibt R5 den Link aber als Punkt-zu-Punkt, R2 als Transitnetz mit DR; die SPF-Berechnung findet keine beidseitige Verbindung.
- **Ursache:** Netzwerktyp-Mismatch zwischen Broadcast und Punkt-zu-Punkt: Nachbarschaft FULL, aber keine Routen über diesen Link.
- **Fix:** `no ip ospf network point-to-point` unter Gi0/0 auf R5 (oder beide Seiten auf point-to-point).
- **Eingebaut:**

```diff
+ ip ospf network point-to-point
```

## Ticket 2 (R2)

- **Symptom:** R5 hat Routen zu den internen Netzen, erreicht aber 192.0.2.1 (Internet über R1) nicht.
- **So findest du es:** `show ip route 0.0.0.0` auf R5: keine Route. `show ip ospf database external` auf R2 zeigt die Default-Route von R1 als Typ-5-LSA, in die NSSA gelangt sie aber nicht. `show ip ospf database nssa-external` auf R5 enthält kein 0.0.0.0.
- **Ursache:** Eine NSSA bekommt, anders als eine Totally NSSA, keine Default-Route automatisch. Der ABR muss sie mit `default-information-originate` als Typ-7-LSA erzeugen.
- **Fix:** `area 3 nssa default-information-originate` unter `router ospf 1` auf R2.
- **Eingebaut:**

```diff
- area 3 nssa default-information-originate
+ area 3 nssa
```

## Ticket 3 (R2)

- **Symptom:** Das Testnetz 10.1.99.0/24 soll nicht in Area 3 gelangen. R5 hat es trotzdem in der Routing-Tabelle, obwohl R2 einen Filter hat.
- **So findest du es:** `show ip ospf database summary 10.1.99.0` auf R5 zeigt das Typ-3-LSA von R2. In der Konfiguration von R2 steht `area 3 filter-list prefix NO-TEST out`: Das filtert Routen, die Area 3 verlassen, nicht die, die hineingehen.
- **Ursache:** Falsche Richtung. `in` filtert die Typ-3-LSAs, die der ABR in die Area hinein erzeugt, `out` die, die er aus der Area heraus meldet. Da NO-TEST nur 10.1.99.0/24 sperrt und dieses Netz nicht aus Area 3 stammt, filtert `out` gar nichts.
- **Fix:** `no area 3 filter-list prefix NO-TEST out` und `area 3 filter-list prefix NO-TEST in` auf R2.
- **Eingebaut:**

```diff
- area 3 filter-list prefix NO-TEST in
+ area 3 filter-list prefix NO-TEST out
```

## Ticket 4 (R3)

- **Symptom:** R1 und R2 kennen die Netze von R4 nicht. `show ip ospf virtual-links` auf R3 zeigt den Virtual Link zu 1.1.1.1, aber keine Nachbarschaft im Zustand FULL.
- **So findest du es:** `debug ip ospf adj` auf R1 meldet beim Virtual Link einen falschen Authentisierungstyp (Mismatched Authentication type). `show running-config | section router ospf` auf R3: `area 0 authentication message-digest` fehlt.
- **Ursache:** Der Virtual Link ist ein Interface in Area 0 und übernimmt deren Authentisierungstyp. R1 verlangt MD5, R3 sendet ohne Authentisierung. Damit ist Area 2 vom Backbone abgeschnitten.
- **Fix:** `area 0 authentication message-digest` unter `router ospf 1` auf R3.
- **Eingebaut:**

```diff
- area 0 authentication message-digest
```

## Ticket 5 (R3)

- **Symptom:** R1 sieht statt der Zusammenfassung 10.4.4.0/23 die beiden Einzelnetze 10.4.4.0/24 und 10.4.5.0/24.
- **So findest du es:** `show ip route ospf` auf R1: zwei O-IA-Routen mit /24. Auf R3 steht `area 1 range 10.4.4.0 255.255.254.0`, die Netze liegen aber in Area 2.
- **Ursache:** Zusammenfassung unter der falschen Area. Eine Range fasst nur Netze der Area zusammen, unter der sie steht, und in Area 1 gibt es 10.4.x nicht.
- **Fix:** `no area 1 range 10.4.4.0 255.255.254.0` und `area 2 range 10.4.4.0 255.255.254.0` auf R3.
- **Eingebaut:**

```diff
- area 2 range 10.4.4.0 255.255.254.0
+ area 1 range 10.4.4.0 255.255.254.0
```
