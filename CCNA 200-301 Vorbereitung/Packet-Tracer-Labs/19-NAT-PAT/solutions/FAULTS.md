# Fehlerliste – Lab 19 – Inside Source NAT: statisch, Pool und PAT

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Weder PC1 noch PC2 erreichen 8.8.8.8, `show ip nat translations` ist leer.
- **So findest du es:** `show ip nat statistics` listet bei „Inside interfaces“ nichts. `show ip nat translations` ist leer.
- **Ursache:** Am LAN-Interface fehlt `ip nat inside`.
- **Fix:** `ip nat inside` auf Gi0/0.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip nat inside
+ interface GigabitEthernet0/0
```

## Ticket 2 (R1)

- **Symptom:** NAT scheint konfiguriert, aber keine Übersetzung; der ISP sieht private Quellen.
- **So findest du es:** `show access-lists` zeigt bei ACL 1 keine Treffer. Das Netz 192.168.1.0 passt nicht zum LAN 192.168.19.0.
- **Ursache:** ACL 1 beschreibt 192.168.1.0/24, das LAN ist 192.168.19.0/24.
- **Fix:** ACL korrigieren.
- **Eingebaut:**

```diff
- access-list 1 permit 192.168.19.0 0.0.0.255
+ access-list 1 permit 192.168.1.0 0.0.0.255
```

## Ticket 3 (R1)

- **Symptom:** PC1 kommt hinaus, PC2 danach nicht mehr; `show ip nat statistics` zählt Misses.
- **So findest du es:** `show ip nat statistics` zeigt steigende Misses. `show running-config | include ip nat inside source` endet ohne `overload`.
- **Ursache:** Ohne `overload` bildet NAT nur 1:1 auf die einzelne Interface-Adresse ab.
- **Fix:** `overload` ergänzen.
- **Eingebaut:**

```diff
- ip nat inside source list 1 interface GigabitEthernet0/1 overload
+ ip nat inside source list 1 interface GigabitEthernet0/1
```

## Ticket 4 (R1)

- **Symptom:** Der ISP erreicht 203.0.113.10 (Webserver) nicht.
- **So findest du es:** `show ip nat translations` zeigt 203.0.113.10 mit einer inneren Adresse, die im LAN nicht vorkommt.
- **Ursache:** Das statische NAT zeigt auf eine nicht vorhandene innere Adresse.
- **Fix:** Innere Adresse 192.168.19.100.
- **Eingebaut:**

```diff
- ip nat inside source static 192.168.19.100 203.0.113.10
+ ip nat inside source static 192.168.19.101 203.0.113.10
```

