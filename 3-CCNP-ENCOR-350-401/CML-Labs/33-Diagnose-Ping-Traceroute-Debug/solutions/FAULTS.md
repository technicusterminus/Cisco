# Fehlerliste – Lab 33 – Diagnose: Ping und Traceroute lesen, Debug und Conditional Debug sicher einsetzen

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R3)

- **Symptom:** H1 erreicht SRV nicht. Der Ping von H1 zeigt `U.U.U`.
- **So findest du es:** `U` heißt: Ein Router hat geantwortet, dass er das Ziel nicht kennt. `traceroute 192.168.3.10` von H1 zeigt schon in Zeile 1 `!H` von 192.168.1.1. `show ip route 192.168.3.0` auf R1 und R2 ist leer, auf R3 ist das Netz nur `connected`. `show ip ospf interface brief` auf R3 listet Gi0/1 nicht.
- **Ursache:** R3 gibt sein Server-Netz nicht in OSPF bekannt. R1 hat keine Route und meldet das dem Absender.
- **Fix:** Auf R3 unter `router ospf 1`: `network 192.168.3.0 0.0.0.255 area 0`.
- **Eingebaut:**

```diff
- network 192.168.3.0 0.0.0.255 area 0
```

## Ticket 2 (R3)

- **Symptom:** Der Ping von H1 zu SRV geht, aber Traceroute bricht in Zeile 3 mit `!A` ab. Das Monitoring meldet den Standort deshalb als gestört.
- **So findest du es:** `!A` heißt *administratively prohibited*, also eine ACL. Die Meldung kommt von 10.0.23.2. `show access-lists TRANSIT` auf R3 zeigt steigende Treffer auf `deny ip any any log`, im Log stehen die verworfenen UDP-Pakete mit Zielport ab 33434.
- **Ursache:** Die ACL erlaubt ICMP und TCP, aber nicht die UDP-Proben von Traceroute. Der Ping bleibt deshalb unauffällig.
- **Fix:** In `ip access-list extended TRANSIT` vor dem `deny`: `permit udp any any range 33434 33534`.
- **Eingebaut:**

```diff
- permit udp any any range 33434 33534
```

## Ticket 3 (R2)

- **Symptom:** Anwender melden: Anmelden am Server geht, große Dateien übertragen hängt. `ping 192.168.3.10 size 1500 df-bit` von H1 zeigt nur Punkte, kein `M`.
- **So findest du es:** Sweep-Ping mit DF-Bit: bis 1400 Byte `!`, darüber `.` statt `M`. Der Verlust beginnt genau an der MTU-Grenze, also verwirft R2 die Pakete, ohne es zu melden. `show ip interface GigabitEthernet0/0 | include unreachables` auf R2: „ICMP unreachables are never sent“.
- **Ursache:** `no ip unreachables` auf dem Eingangs-Interface unterdrückt auch die Meldung *Fragmentation needed*. Path MTU Discovery kann nicht arbeiten, große Pakete mit DF-Bit verschwinden.
- **Fix:** `ip unreachables` auf R2 Gi0/0. (Alternativ am Rand `ip tcp adjust-mss`, das hilft aber nur TCP.)
- **Eingebaut:**

```diff
+ no ip unreachables
```

## Ticket 4 (R1)

- **Symptom:** Auf R1 läuft `debug ip icmp` laut `show debugging`, aber `show logging` zeigt keine einzige Debug-Zeile.
- **So findest du es:** `show logging` auf R1 nennt in der Kopfzeile „Buffer logging: level warnings“. Debug-Meldungen haben Stufe 7 und werden nicht gespeichert.
- **Ursache:** Der Puffer nimmt nur Stufe 0 bis 4 an. Die Konsole ist auf `informational` begrenzt, also landen Debugs nirgends.
- **Fix:** `logging buffered 16384 debugging` auf R1.
- **Eingebaut:**

```diff
-logging buffered 16384 debugging
+logging buffered 16384 warnings
```
