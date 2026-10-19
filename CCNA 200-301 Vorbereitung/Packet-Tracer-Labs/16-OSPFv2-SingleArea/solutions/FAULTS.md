# Fehlerliste – Lab 16 – OSPFv2 Single Area: Nachbarn, DR/BDR, Router-ID

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R3)

- **Symptom:** Im Log erscheint `%OSPF-4-DUP_RTRID_NBR`, LSAs werden inkonsistent, einzelne Routen verschwinden.
- **Ursache:** R3 verwendet dieselbe Router-ID wie R1.
- **Fix:** Eindeutige Router-ID (3.3.3.3) setzen und `clear ip ospf process`.
- **Eingebaut:**

```diff
-  router-id 3.3.3.3
+  router-id 1.1.1.1
```

## Ticket 2 (R4)

- **Symptom:** R4 wird nicht FULL zu R2; `show ip ospf neighbor` ist auf R2 und R4 leer, PC4 erreicht niemanden.
- **Ursache:** Area-Mismatch am Link R2–R4 (Area 1 statt Area 0).
- **Fix:** Area 0 setzen.
- **Eingebaut:**

```diff
-  network 10.16.24.0 0.0.0.3 area 0
+  network 10.16.24.0 0.0.0.3 area 1
```

## Ticket 3 (R3)

- **Symptom:** PC3 erreicht seine Nachbarn nicht und LAN 192.168.3.0/24 fehlt in den Routingtabellen der anderen Router.
- **Ursache:** Die Wildcard 0.0.0.0 passt nicht auf die Interface-Adresse 192.168.3.1: das Interface nimmt nicht an OSPF teil.
- **Fix:** Wildcard 0.0.0.255 verwenden.
- **Eingebaut:**

```diff
-  network 192.168.3.0 0.0.0.255 area 0
+  network 192.168.3.0 0.0.0.0 area 0
```

## Ticket 4 (R2)

- **Symptom:** R2 und R4 bilden keine Nachbarschaft: `show ip ospf interface gi0/1` zeigt Hello 5, R4 hat 10.
- **Ursache:** Hello-Intervall-Mismatch am P2P-Link.
- **Fix:** Hello-Intervall entfernen (`no ip ospf hello-interval`).
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  ip ospf network point-to-point
+ interface GigabitEthernet0/1
+  ip ospf hello-interval 5
+  ip ospf network point-to-point
```

## Ticket 5 (R1)

- **Symptom:** Im Segment ist R2 DR, R1 nur DROTHER; die Rollen stimmen nicht mit dem Entwurf überein.
- **Ursache:** Priorität 0 auf R1: er darf nicht DR/BDR werden.
- **Fix:** Priorität 200 setzen, danach OSPF-Prozess neu starten.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip ospf priority 200
+ interface GigabitEthernet0/0
+  ip ospf priority 0
```

