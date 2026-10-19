# Fehlerliste – Lab 28 – OSPF vertieft: Area-Typen, Summarisierung und Authentifizierung

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R3)

- **Symptom:** R2 und R3 bilden keine Nachbarschaft; im Log erscheint `Mismatch Authentication`-freie Meldung, `debug ip ospf adj` zeigt `Hello from … with mismatched Stub/Transit area option bit`.
- **Ursache:** Auf R3 fehlt `area 1 stub`: Die Area-Typen weichen ab (E-Bit).
- **Fix:** `area 1 stub` auf R3.
- **Eingebaut:**

```diff
-  area 1 stub
```

## Ticket 2 (R2)

- **Symptom:** R1 sieht drei einzelne Routen 192.168.1.0/24, 192.168.2.0/24, 192.168.3.0/24 und nur 192.168.0.0/24 als Summary.
- **Ursache:** Der Range deckt nur 192.168.0.0/24 ab, die anderen Netze werden einzeln ausgegeben.
- **Fix:** Maske 255.255.252.0 im `area range`.
- **Eingebaut:**

```diff
-  area 1 range 192.168.0.0 255.255.252.0
+  area 1 range 192.168.0.0 255.255.255.0
```

## Ticket 3 (R1)

- **Symptom:** R1 und R2 sind in `INIT`/ohne Nachbarschaft, Log: `Mismatched Authentication key`.
- **Ursache:** Das MD5-Passwort auf R1 weicht von R2 ab.
- **Fix:** Passwort angleichen.
- **Eingebaut:**

```diff
-  ip ospf message-digest-key 1 md5 OspfKey
+  ip ospf message-digest-key 1 md5 OspfKez
```

## Ticket 4 (R4)

- **Symptom:** 172.31.0.0/24 fehlt in Area 0, R1 sieht keine externe Route.
- **Ursache:** Ohne `subnets` wird das /24-Netz nicht redistribuiert (nur klassische Netze).
- **Fix:** `redistribute static subnets`.
- **Eingebaut:**

```diff
-  redistribute static subnets
+  redistribute static
```

## Ticket 5 (R4)

- **Symptom:** R4 hat keinen OSPF-Nachbarn zu R2, obwohl der Link steht.
- **Ursache:** Das Uplink-Interface von R4 ist passiv: Es werden keine Hellos gesendet.
- **Fix:** `no passive-interface GigabitEthernet0/0` auf R4.
- **Eingebaut:**

```diff
-  no passive-interface GigabitEthernet0/0
```

## Ticket 6 (R2)

- **Symptom:** R3 trägt trotz Stub-Area alle Inter-Area-Routen (O IA) statt nur der Default-Route.
- **Ursache:** Ohne `no-summary` sendet der ABR weiter Typ-3-LSAs in die Area: nur Stub, nicht Totally Stubby.
- **Fix:** `area 1 stub no-summary` auf dem ABR.
- **Eingebaut:**

```diff
-  area 1 stub no-summary
+  area 1 stub
```

