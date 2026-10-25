# Fehlerliste – Lab 21 – TFTP und FTP: Konfigurations- und Image-Sicherung

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** `copy running-config ftp:` auf R2 scheitert mit Login-Fehler, auf R1 geht es.
- **So findest du es:** `show running-config | include ftp` auf R2 zeigt ein anderes Passwort als auf R1.
- **Ursache:** Falsches FTP-Passwort auf R2.
- **Fix:** `ip ftp password cisco`.
- **Eingebaut:**

```diff
- ip ftp password cisco
+ ip ftp password cisco1
```

## Ticket 2 (R1)

- **Symptom:** R1 erreicht den Server (10.21.1.100) nicht, TFTP/FTP-Transfers melden Timeout.
- **So findest du es:** `show ip interface brief` und `show running-config interface gi0/0` auf R1 zeigen die Maske 255.255.255.192. Rechne nach: Liegt 10.21.1.100 noch im Netz von R1?
- **Ursache:** Falsche Maske /26 auf R1: Das Netz von R1 reicht nur von 10.21.1.0 bis .63. 10.21.1.100 liegt außerhalb, und R1 hat keine Route dorthin.
- **Fix:** Maske 255.255.255.0.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip address 10.21.1.1 255.255.255.0
+ interface GigabitEthernet0/0
+  ip address 10.21.1.1 255.255.255.192
```

## Ticket 3 (SW1)

- **Symptom:** Der Server ist von beiden Routern nicht erreichbar.
- **So findest du es:** `show interfaces status` auf SW1 zeigt den Port zum Server als `disabled`.
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

