# Fehlerliste – Lab 09 – NAT und PAT

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Weder PC1 noch PC2 erreichen den ISP, `show ip nat translations` ist leer (Quelladresse bleibt privat).
- **Ursache:** Am LAN-Interface fehlt `ip nat inside`: Pakete werden nicht übersetzt.
- **Fix:** `ip nat inside` auf Gi0/0 setzen.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip nat inside
+ interface GigabitEthernet0/0
```

## Ticket 2 (R1)

- **Symptom:** Dasselbe Bild trotz korrektem Interface-Setup: keine Übersetzung, der ISP sieht nichts.
- **Ursache:** Die ACL für PAT beschreibt 192.168.1.0/24, das LAN ist aber 192.168.10.0/24.
- **Fix:** ACL auf das richtige Subnetz korrigieren.
- **Eingebaut:**

```diff
- access-list 1 permit 192.168.10.0 0.0.0.255
+ access-list 1 permit 192.168.1.0 0.0.0.255
```

## Ticket 3 (R1)

- **Symptom:** PC1 kommt raus, PC2 danach nicht mehr; `show ip nat statistics` zeigt Misses.
- **Ursache:** Ohne `overload` kann die Interface-Adresse nur einem Host zugeordnet werden (1:1).
- **Fix:** `overload` ergänzen.
- **Eingebaut:**

```diff
- ip nat inside source list 1 interface GigabitEthernet0/1 overload
+ ip nat inside source list 1 interface GigabitEthernet0/1
```

## Ticket 4 (R1)

- **Symptom:** Der ISP erreicht 203.0.113.10 (Server) nicht, `show ip nat translations` zeigt die Zuordnung zu .11.
- **Ursache:** Das statische NAT zeigt auf eine nicht vorhandene innere Adresse (172.16.0.11).
- **Fix:** Innere Adresse auf 172.16.0.10 korrigieren.
- **Eingebaut:**

```diff
- ip nat inside source static 172.16.0.10 203.0.113.10
+ ip nat inside source static 172.16.0.11 203.0.113.10
```

