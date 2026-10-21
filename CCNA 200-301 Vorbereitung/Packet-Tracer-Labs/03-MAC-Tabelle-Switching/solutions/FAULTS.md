# Fehlerliste – Lab 03 – Switching-Konzepte: MAC-Lernen, Aging, Flooding

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW2)

- **Symptom:** Zwischen den Switches wird auffällig viel geflutet: `show mac address-table` auf SW2 ist nach kurzer Zeit fast leer, Pakete erscheinen im Simulationsmodus wiederholt an allen Ports.
- **So findest du es:** `show mac address-table aging-time` auf SW2 zeigt 10 statt 300. Die Tabelle leert sich kurz nach jedem Ping wieder.
- **Ursache:** Aging-Time steht auf 10 Sekunden statt 300: gelernte Einträge verfallen fast sofort, unbekannte Ziele werden erneut geflutet.
- **Fix:** `mac address-table aging-time 300` (Standard) setzen.
- **Eingebaut:**

```diff
- mac address-table aging-time 300
+ mac address-table aging-time 10
```

## Ticket 2 (SW1)

- **Symptom:** Die Hosts an SW1 und SW2 sehen einander nicht, jede Seite erreicht nur die eigenen Nachbarn.
- **So findest du es:** `show interfaces status` auf SW1 zeigt den Uplink Fa0/24 als `disabled`.
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
- **So findest du es:** `ipconfig` auf PC3 zeigt die Maske 255.255.255.252. Rechne das Subnetz von 192.168.3.13/30 aus: .12 bis .15.
- **Ursache:** Maske /30 am PC3: 192.168.3.13/30 liegt im Netz .12 bis .15. PC1 (.11) liegt aus Sicht von PC3 außerhalb, PC2 (.12) ist für PC3 die Netzadresse. Nur PC4 (.14) ist ein gültiger Nachbar.
- **Fix:** Maske 255.255.255.0 setzen.
- **Eingebaut:** Endgerät-Einstellung `mask` = `255.255.255.252`

