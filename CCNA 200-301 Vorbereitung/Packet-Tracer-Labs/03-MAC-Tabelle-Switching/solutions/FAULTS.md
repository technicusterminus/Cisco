# Fehlerliste – Lab 03 – Switching-Konzepte: MAC-Lernen, Aging, Flooding

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW2)

- **Symptom:** Zwischen den Switches wird auffällig viel geflutet: `show mac address-table` auf SW2 ist nach kurzer Zeit fast leer, Pakete erscheinen im Simulationsmodus wiederholt an allen Ports.
- **Ursache:** Aging-Time steht auf 10 Sekunden statt 300: gelernte Einträge verfallen fast sofort, unbekannte Ziele werden erneut geflutet.
- **Fix:** `mac address-table aging-time 300` (Standard) setzen.
- **Eingebaut:**

```diff
- mac address-table aging-time 300
+ mac address-table aging-time 10
```

## Ticket 2 (SW1)

- **Symptom:** Die Hosts an SW1 und SW2 sehen einander nicht, jede Seite erreicht nur die eigenen Nachbarn.
- **Ursache:** Der Uplink Fa0/24 an SW1 ist administrativ abgeschaltet.
- **Fix:** `no shutdown` auf SW1 Fa0/24.
- **Eingebaut:**

```diff
- interface FastEthernet0/24
-  no shutdown
+ interface FastEthernet0/24
+  shutdown
```

## Ticket 3 (PC3)

- **Symptom:** PC3 erreicht nur PC4, aber weder PC1 noch PC2.
- **Ursache:** Maske /30 am PC3: 192.168.3.13/30 liegt im Netz .12-.15, PC1 (.11) und PC2 (.12) sind aus Sicht von PC3 nicht im selben Subnetz.
- **Fix:** Maske 255.255.255.0 setzen.
- **Eingebaut:** Endgerät-Einstellung `mask` = `255.255.255.252`

