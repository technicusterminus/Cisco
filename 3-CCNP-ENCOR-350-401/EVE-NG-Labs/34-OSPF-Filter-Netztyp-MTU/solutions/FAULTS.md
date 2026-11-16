# Fehlerliste – Lab 34 – OSPF: Routen filtern (ABR, ASBR, lokal) und Nachbarschaften mit Netztyp- und MTU-Fehlern

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** R1 und R2 zeigen einander als `FULL`, aber R1 lernt keine einzige Route über R2 und umgekehrt.
- **So findest du es:** `show ip ospf interface GigabitEthernet0/0 | include Network Type` nennt auf R1 BROADCAST, auf R2 POINT_TO_POINT. `show ip ospf neighbor` zeigt auf R1 eine DR-Rolle, auf R2 einen Strich.
- **Ursache:** Netztyp-Konflikt. Die Hello-Timer passen, also wird die Nachbarschaft FULL. Die Router beschreiben den Link in ihren LSAs aber unterschiedlich, SPF verwirft ihn.
- **Fix:** `ip ospf network point-to-point` auf R1 Gi0/0.
- **Eingebaut:**

```diff
- ip ospf network point-to-point
```

## Ticket 2 (R3)

- **Symptom:** R3 kommt mit R2 nicht über `EXSTART` hinaus.
- **So findest du es:** `show ip ospf neighbor` auf R2: R3 in EXSTART. `show ip interface GigabitEthernet0/0 | include MTU` zeigt auf R3 1400, auf R2 Gi0/1 1500. `debug ip ospf adj` nennt die MTU-Abweichung.
- **Ursache:** Die IP-MTU der beiden Seiten ist ungleich. Der Router mit der kleineren MTU verwirft die Database-Description-Pakete des Nachbarn.
- **Fix:** `no ip mtu 1400` auf R3 Gi0/0 (nicht `ip ospf mtu-ignore`).
- **Eingebaut:**

```diff
+ ip mtu 1400
```

## Ticket 3 (R2)

- **Symptom:** Aus Area 1 ist außerhalb gar kein Netz mehr sichtbar, auch die Summary 10.1.16.0/23 nicht. Innerhalb von Area 1 ist alles in Ordnung.
- **So findest du es:** `show ip prefix-list A1-OUT` auf R2 enthält nur die `deny`-Zeile. `show ip ospf database summary` auf R1 zeigt kein LSA für Netze aus Area 1.
- **Ursache:** Jede Prefix-Liste endet mit einem stillen `deny`. Ohne die `permit`-Zeile filtert `area 1 filter-list … out` alles, auch die Summary.
- **Fix:** `ip prefix-list A1-OUT seq 10 permit 0.0.0.0/0 le 32` auf R2.
- **Eingebaut:**

```diff
-ip prefix-list A1-OUT seq 10 permit 0.0.0.0/0 le 32
```

## Ticket 4 (R1)

- **Symptom:** R4 hat eine Route nach 10.1.18.0/24. Laut Vorgabe 3 darf Area 2 dieses Netz nicht kennen.
- **So findest du es:** `show running-config | section router ospf` auf R1: Die Filterliste hängt mit `out` an Area 2. `show ip ospf database summary 10.1.18.0` auf R4 zeigt das LSA mit R1 als Absender.
- **Ursache:** `out` filtert, was aus Area 2 heraus angekündigt wird. 10.1.18.0/24 kommt aber von außen in die Area hinein, die Liste trifft nie.
- **Fix:** Auf R1: `no area 2 filter-list prefix A2-IN out`, dann `area 2 filter-list prefix A2-IN in`.
- **Eingebaut:**

```diff
- area 2 filter-list prefix A2-IN in
+ area 2 filter-list prefix A2-IN out
```

## Ticket 5 (R4)

- **Symptom:** 198.51.100.0/24 fehlt im ganzen Netz als externe Route. Auf R4 ist die statische Route vorhanden.
- **So findest du es:** `show ip ospf database external` ist leer. `show route-map EXT` zählt keine Treffer. `show ip prefix-list EXT-OK` nennt /25, die statische Route ist /24.
- **Ursache:** Eine Prefix-Liste ohne `ge`/`le` verlangt die exakte Präfixlänge. /25 passt nicht auf die /24-Route, die Route-Map verwirft sie.
- **Fix:** Prefix-Liste auf `permit 198.51.100.0/24` korrigieren.
- **Eingebaut:**

```diff
-ip prefix-list EXT-OK seq 5 permit 198.51.100.0/24
+ip prefix-list EXT-OK seq 5 permit 198.51.100.0/25
```
