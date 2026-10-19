# Fehlerliste – Lab 25 – EIGRP klassisch: Nachbarschaft, Authentifizierung, Summary und Stub

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** R1 und R2 bilden keine Nachbarschaft (`show ip eigrp neighbors` leer am Link); `debug eigrp packets` meldet einen Authentifizierungsfehler.
- **Ursache:** Der Schlüssel in der Key-Chain von R2 weicht von R1 ab (EigrpKez statt EigrpKey).
- **Fix:** Key-String auf beiden Seiten angleichen.
- **Eingebaut:**

```diff
-   key-string EigrpKey
+   key-string EigrpKez
```

## Ticket 2 (R3)

- **Symptom:** R3 hat keine Nachbarn: `show ip eigrp neighbors` ist leer, auf R1 und R2 steht `K-value mismatch`.
- **Ursache:** R3 verwendet andere K-Werte (K2 aktiv). EIGRP-Nachbarn müssen identische Metrik-Gewichte haben.
- **Fix:** `metric weights` auf R3 entfernen (Standard 0 1 0 1 0 0).
- **Eingebaut:**

```diff
-  no auto-summary
+  no auto-summary
+  metric weights 0 1 1 1 0 0
```

## Ticket 3 (R4)

- **Symptom:** R4 hat keinen Nachbarn zu R2, 192.168.4.0/24 fehlt überall.
- **Ursache:** R4 läuft in AS 101, die anderen Router in AS 100: Nachbarschaft nur innerhalb gleicher AS.
- **Fix:** `router eigrp 100` auf R4 (Konfiguration übernehmen).
- **Eingebaut:**

```diff
- router eigrp 100
+ router eigrp 101
```

## Ticket 4 (R1)

- **Symptom:** R3 zeigt für das 172.16er-Netz zwei verschiedene Routen: `172.16.0.0/22` (über R2) und `172.16.0.0/23` (direkt von R1). Verkehr in 172.16.2.0/24 nimmt den Umweg.
- **Ursache:** Die Summary-Maske auf R1 Gi0/1 ist /23 statt /22: R3 bekommt direkt eine andere, zu kleine Summary.
- **Fix:** Maske 255.255.252.0 auf Gi0/1.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  ip summary-address eigrp 100 172.16.0.0 255.255.252.0
+ interface GigabitEthernet0/1
+  ip summary-address eigrp 100 172.16.0.0 255.255.254.0
```

## Ticket 5 (R4)

- **Symptom:** Nach Behebung der Nachbarschaft: R1 erreicht 192.168.4.1 nicht, obwohl R4 Nachbar von R2 ist.
- **Ursache:** `receive-only` unterdrückt jegliche Ankündigung: R4 bewirbt auch das direkt verbundene Netz nicht.
- **Fix:** `eigrp stub connected`.
- **Eingebaut:**

```diff
-  eigrp stub connected
+  eigrp stub receive-only
```

## Ticket 6 (R2)

- **Symptom:** R2 und R3 sind direkt verbunden, aber `show ip eigrp neighbors` auf R2 zeigt R3 nicht (Nachbarschaft nur über R1).
- **Ursache:** Der Link zu R3 ist auf R2 passiv: Es werden keine Hellos gesendet.
- **Fix:** `no passive-interface GigabitEthernet0/1` unter `router eigrp 100` auf R2.
- **Eingebaut:**

```diff
-  no passive-interface GigabitEthernet0/1
```

