# Fehlerliste – Lab 14 – Routing-Tabelle lesen und die Weiterleitungsentscheidung vorhersagen

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Ping 10.1.1.1 scheitert; `traceroute` endet an R3, das die Adresse nicht kennt (oder zurückgibt).
- **Ursache:** Die spezifischste Route /24 zeigt auf R3 statt R4.
- **Fix:** Next Hop 192.168.14.10.
- **Eingebaut:**

```diff
- ip route 10.1.1.0 255.255.255.0 192.168.14.10
+ ip route 10.1.1.0 255.255.255.0 192.168.14.6
```

## Ticket 2 (R1)

- **Symptom:** 10.1.5.5 landet nicht bei R3 sondern über /8 bei R2; `show ip route 10.1.5.5` zeigt 10.0.0.0/8.
- **Ursache:** Falsche Maske (/23 statt /16): 10.1.5.5 liegt nicht mehr in 10.1.0.0/23.
- **Fix:** Maske 255.255.0.0.
- **Eingebaut:**

```diff
- ip route 10.1.0.0 255.255.0.0 192.168.14.6
+ ip route 10.1.0.0 255.255.254.0 192.168.14.6
```

## Ticket 3 (R3)

- **Symptom:** R1 kann 10.1.5.5 anpingen, bekommt aber keine Antwort (R3 kennt den Rückweg nicht).
- **Ursache:** R3 hat keine Default-/Rückroute zu R1: Pakete kommen an, Antworten verschwinden.
- **Fix:** `ip route 0.0.0.0 0.0.0.0 192.168.14.5` auf R3.
- **Eingebaut:**

```diff
- ip route 0.0.0.0 0.0.0.0 192.168.14.5
```

## Ticket 4 (R1)

- **Symptom:** 8.8.8.8 und 172.16.0.1 erreichen R2 nicht; `show ip route` zeigt den Default via R4.
- **Ursache:** Default-Route zeigt auf R4 (192.168.14.10) statt R2.
- **Fix:** Next Hop 192.168.14.2.
- **Eingebaut:**

```diff
- ip route 0.0.0.0 0.0.0.0 192.168.14.2
+ ip route 0.0.0.0 0.0.0.0 192.168.14.10
```

