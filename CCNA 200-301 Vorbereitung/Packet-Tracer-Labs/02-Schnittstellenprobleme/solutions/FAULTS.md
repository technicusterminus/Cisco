# Fehlerliste – Lab 02 – Schnittstellen- und Kabelprobleme (Duplex, Speed, Fehler)

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW1)

- **Symptom:** PC1 erreicht nichts hinter dem Trunk-Uplink; `show interfaces status` auf SW1 zeigt Fa0/24 mit `10`/`half` und Link down oder Probleme.
- **Ursache:** SW1 hat Speed/Duplex fest auf 10/half eingestellt, SW2 verhandelt automatisch auf 100/full: Mismatch.
- **Fix:** Auf SW1 Fa0/24 `speed auto`/`duplex auto`.
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

- **Symptom:** Zwischen PC und R1 stockt es nach einiger Last; `show interfaces gi0/0` zeigt Halbduplex gegen Vollduplex auf dem Switch.
- **Ursache:** R1 Gi0/0 ist auf `duplex half` fixiert, SW2 Fa0/2 steht auf Auto/Vollduplex.
- **Fix:** `duplex auto` (oder beidseitig identisch fest).
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip address 192.168.2.1 255.255.255.0
+ interface GigabitEthernet0/0
+  ip address 192.168.2.1 255.255.255.0
+  duplex half
```

## Ticket 4 (PC2)

- **Symptom:** PC2 erreicht PC1 nicht (ping `Destination host unreachable`), obwohl alles verbunden ist.
- **Ursache:** Falsche Subnetzmaske am PC (/25 statt /24): PC1 liegt aus seiner Sicht ausserhalb des Subnetzes.
- **Fix:** Maske 255.255.255.0 setzen.
- **Eingebaut:** Endgerät-Einstellung `mask` = `255.255.255.128`

