# Fehlerliste – Lab 01 – OSPFv2 Multi-Area

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** R1 und R2 werden nicht Nachbarn, `show ip ospf neighbor` ist auf R1 leer, Area 0 ist isoliert.
- **So findest du es:** `show ip ospf interface Gi0/0` zeigt auf beiden Seiten Authentisierung mit Key-Chain. `debug ip ospf adj` meldet dann „Mismatched Authentication Key“.
- **Ursache:** Die SHA-256-Schlüssel der Key-Chain unterscheiden sich (Authentifizierungsfehler, Hello wird verworfen).
- **Fix:** Key-String auf R1 an R2 angleichen, Nachbarschaft prüfen.
- **Eingebaut:**

```diff
- key-string LabKey123
+ key-string LabKey999
```

## Ticket 2 (R3)

- **Symptom:** R3 erscheint nirgends als Nachbar, R2 und R4 sehen nur sich gegenseitig.
- **So findest du es:** `show ip ospf interface brief` auf R3 listet Gi0/0 nicht oder `show ip protocols` zeigt es unter „Passive Interface(s)“.
- **Ursache:** `passive-interface default` ohne Ausnahme: R3 sendet auf Gi0/0 keine Hellos.
- **Fix:** `no passive-interface GigabitEthernet0/0` unter `router ospf 1`.
- **Eingebaut:**

```diff
- no passive-interface GigabitEthernet0/0
```

## Ticket 3 (R2)

- **Symptom:** R1 sieht vier einzelne /24 (10.1.16–19) statt der Zusammenfassung.
- **So findest du es:** `show ip ospf database summary` auf R1 zeigt die vier /24 einzeln. Vergleiche die `area range` auf R2 mit den tatsächlichen Netzen: 10.1.16.0/22 umfasst 16 bis 19.
- **Ursache:** Die `area range` beschreibt ein falsches Netz (10.1.20.0/22) und greift nicht.
- **Fix:** Range auf 10.1.16.0 255.255.252.0 korrigieren.
- **Eingebaut:**

```diff
- area 1 range 10.1.16.0 255.255.252.0
+ area 1 range 10.1.20.0 255.255.252.0
```

## Ticket 4 (R4)

- **Symptom:** R4 bleibt in `INIT`/taucht nicht als Nachbar auf, während R3 und R2 sich sehen.
- **So findest du es:** `show ip ospf interface Gi0/0` auf R4 und auf dem Nachbarn vergleichen: Die Zeile „Timer intervals configured, Hello …, Dead …“ unterscheidet sich.
- **Ursache:** Hello-Intervall 5 s auf R4 passt nicht zu den anderen (10 s): Hello-Parameter-Mismatch.
- **Fix:** Hello-Intervall auf R4 entfernen (Default 10 s).
- **Eingebaut:**

```diff
- ip ospf 1 area 1
-  ip ospf priority 100
+ ip ospf 1 area 1
+  ip ospf priority 100
+  ip ospf hello-interval 5
```

