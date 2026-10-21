# Fehlerliste – Lab 02 – Schnittstellen- und Kabelprobleme (Duplex, Speed, Fehler)

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW1)

- **Symptom:** Alles ist erreichbar, aber Übertragungen zwischen PC1 und PC2 sind auffällig langsam. `show interfaces status` auf SW1 zeigt Fa0/24 mit `10` und `half`.
- **So findest du es:** `show interfaces status` auf SW1 zeigt Fa0/24 mit `10`/`half` ohne `a-`, also fest eingestellt. SW2 zeigt `a-10`/`a-half`: Er hat sich angepasst.
- **Ursache:** SW1 hat Speed und Duplex fest auf 10/half eingestellt. SW2 steht auf Auto, bekommt keine Aushandlung und erkennt nur die Geschwindigkeit. Für das Duplex fällt er auf Halbduplex zurück. Der Uplink läuft, aber mit einem Zehntel der Bandbreite und Kollisionen.
- **Fix:** Auf SW1 Fa0/24 `speed auto` und `duplex auto`. Danach zeigen beide Seiten `a-100`/`a-full`.
- **Eingebaut:**

```diff
- interface FastEthernet0/24
-  speed auto
-  duplex auto
+ interface FastEthernet0/24
+  speed 10
+  duplex half
```

## Ticket 2 (SW2)

- **Symptom:** Das Gateway R1 ist von PC2 aus nicht erreichbar, der Switch-Port zu R1 meldet `administratively down`.
- **So findest du es:** `show interfaces status` auf SW2 zeigt den Port zu R1 als `disabled`, `show interfaces` meldet „administratively down“.
- **Ursache:** Port Fa0/2 an SW2 ist administrativ abgeschaltet.
- **Fix:** `no shutdown` auf Fa0/2.
- **Eingebaut:**

```diff
- interface FastEthernet0/2
-  no shutdown
+ interface FastEthernet0/2
+  shutdown
```

## Ticket 3 (R1)

- **Symptom:** Zwischen den PCs und R1 stockt es bei Last, Pings verlieren einzelne Pakete. CDP meldet einen Duplex-Mismatch an Gi0/0.
- **So findest du es:** `show interfaces gi0/0` auf R1 zeigt „Full-duplex, 100Mb/s“ fest eingestellt. `show interfaces status` auf SW2 zeigt Fa0/2 mit `a-100`/`a-half`, `show interfaces fa0/2` zählt Late Collisions.
- **Ursache:** R1 Gi0/0 ist fest auf 100/full eingestellt und verhandelt nicht. SW2 Fa0/2 steht auf Auto, erkennt nur die Geschwindigkeit und fällt auf Halbduplex zurück. R1 sendet jederzeit, SW2 hält das für Kollisionen: Duplex-Mismatch.
- **Fix:** Auf R1 `speed auto` und `duplex auto` (oder beide Seiten identisch fest einstellen).
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip address 192.168.2.1 255.255.255.0
+ interface GigabitEthernet0/0
+  ip address 192.168.2.1 255.255.255.0
+  speed 100
+  duplex full
```

## Ticket 4 (PC2)

- **Symptom:** PC2 erreicht PC1 nicht (ping `Destination host unreachable`), obwohl alles verbunden ist.
- **So findest du es:** `ipconfig` auf PC2 zeigt 192.168.20.12. Vergleiche mit PC1 (192.168.2.11) und dem Gateway: Das dritte Oktett passt nicht.
- **Ursache:** Tippfehler in der Adresse von PC2 (192.168.20.12 statt 192.168.2.12). PC2 liegt damit in einem anderen Netz als PC1 und sein Gateway.
- **Fix:** Adresse 192.168.2.12 setzen.
- **Eingebaut:** Endgerät-Einstellung `ip` = `192.168.20.12`

