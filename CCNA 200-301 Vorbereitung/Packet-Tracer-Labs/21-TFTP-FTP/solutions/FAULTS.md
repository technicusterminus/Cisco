# Fehlerliste – Lab 21 – TFTP und FTP: Konfigurations- und Image-Sicherung

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** `copy running-config ftp:` auf R2 scheitert mit Login-Fehler, auf R1 geht es.
- **Ursache:** Falsches FTP-Passwort auf R2.
- **Fix:** `ip ftp password cisco`.
- **Eingebaut:**

```diff
- ip ftp password cisco
+ ip ftp password cisco1
```

## Ticket 2 (R1)

- **Symptom:** R1 erreicht den Server (10.21.1.100) nicht, TFTP/FTP-Transfers melden Timeout.
- **Ursache:** Falsche Maske /25 auf R1: 10.21.1.100 liegt ausserhalb von 10.21.1.0/25.
- **Fix:** Maske 255.255.255.0.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip address 10.21.1.1 255.255.255.0
+ interface GigabitEthernet0/0
+  ip address 10.21.1.1 255.255.255.128
```

## Ticket 3 (SW1)

- **Symptom:** Der Server ist von beiden Routern nicht erreichbar.
- **Ursache:** Der Switchport zum Server ist abgeschaltet.
- **Fix:** `no shutdown` auf Fa0/3.
- **Eingebaut:**

```diff
- interface range FastEthernet0/1 - 3
-  no shutdown
+ interface range FastEthernet0/1 - 3
+  no shutdown
+ interface FastEthernet0/3
+  shutdown
```

