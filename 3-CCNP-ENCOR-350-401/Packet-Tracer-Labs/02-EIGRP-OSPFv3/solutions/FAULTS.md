# Fehlerliste – Lab 02 – EIGRP (Named Mode) und OSPFv3

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** R2 hat keinen EIGRP-Nachbarn zu R1 oder R3, `show ip eigrp neighbors` ist leer, IPv6/OSPFv3 läuft normal.
- **So findest du es:** `show eigrp protocols` oder `show running-config | section router eigrp` auf R2: Die AS-Nummer in der address-family weicht von R1 und R3 ab.
- **Ursache:** AS-Nummer 101 statt 100 auf R2: EIGRP-Pakete mit anderer AS werden ignoriert.
- **Fix:** AS-Nummer auf R2 wieder auf 100 setzen.
- **Eingebaut:**

```diff
- autonomous-system 100
+ autonomous-system 101
```

## Ticket 2 (R1)

- **Symptom:** R1–R2 funktioniert, aber der Direktlink R1–R3 bildet keine Nachbarschaft (Log: Authentifizierungsfehler).
- **So findest du es:** Das Log auf R1 oder R3 meldet die Authentisierung. `show eigrp address-family ipv4 interfaces detail Gi0/1` zeigt den Authentisierungsmodus, die Passwörter vergleichst du in der Konfiguration.
- **Ursache:** Auf R1 Gi0/1 gilt ein anderes HMAC-Passwort als auf R3.
- **Fix:** Passwort auf R1 Gi0/1 an R3 angleichen.
- **Eingebaut:**

```diff
- af-interface GigabitEthernet0/1
-    no passive-interface
-    authentication mode hmac-sha-256 0 LabKey123
+ af-interface GigabitEthernet0/1
+    no passive-interface
+    authentication mode hmac-sha-256 0 FalschesPW
```

## Ticket 3 (R2)

- **Symptom:** R2–R3 bildet keine EIGRP-Nachbarschaft, R3 ist nur über den Direktlink R1–R3 erreichbar (Pfadwahl bei R1 ungewöhnlich).
- **So findest du es:** `show eigrp address-family ipv4 interfaces` auf R2 listet Gi0/1 nicht. In der Konfiguration steht `passive-interface` unter `af-interface default`.
- **Ursache:** Interface Gi0/1 ist per `af-interface default` passiv und nicht freigegeben.
- **Fix:** `no passive-interface` unter `af-interface GigabitEthernet0/1` setzen.
- **Eingebaut:**

```diff
-   af-interface GigabitEthernet0/1
-    no passive-interface
+   af-interface GigabitEthernet0/1
```

## Ticket 4 (R2)

- **Symptom:** Im IPv6-Netz fehlt die Nachbarschaft R2–R3 (EIGRP IPv4 läuft), `show ospfv3 neighbor` zeigt auf R2 keinen Nachbarn an Gi0/1.
- **So findest du es:** `show ospfv3 interface brief` auf R2 und R3: Gi0/1 steht auf beiden Seiten in einer anderen Area.
- **Ursache:** Area-Mismatch: R2 nutzt Area 1, R3 Area 0 auf demselben Link.
- **Fix:** Interface auf `ospfv3 1 ipv6 area 0` zurückstellen.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  ospfv3 1 ipv6 area 0
+ interface GigabitEthernet0/1
+  ospfv3 1 ipv6 area 1
```

