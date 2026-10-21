# Fehlerliste – Lab 10 – ACLs und Control-Plane Policing

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Seit der ACL am Edge funktioniert aus dem LAN nichts mehr (kein Ping nach 8.8.8.8, kein HTTP von außen), Zähler der ersten Zeile steigt.
- **So findest du es:** `show access-lists` zeigt steigende Treffer auf der ersten Zeile `deny ip any any`, alle anderen Zeilen bleiben bei 0.
- **Ursache:** Ein `deny ip any any` steht vor allen Permit-Zeilen und verwirft alles (Shadowing).
- **Fix:** Das frühe Deny entfernen, Reihenfolge der Zeilen prüfen.
- **Eingebaut:**

```diff
-  10 permit icmp any any echo-reply
+  5 deny ip any any
+  10 permit icmp any any echo-reply
```

## Ticket 2 (R1)

- **Symptom:** SRV kann trotz `deny` ins LAN pingen.
- **So findest du es:** `show ip interface` am DMZ-Interface zeigt die ACL als „Outgoing access list“. Gedacht ist sie für Verkehr, der aus der DMZ kommt.
- **Ursache:** Die ACL steht auf `out` statt `in`: Sie prüft nur Verkehr zur DMZ, nicht den, der aus ihr kommt.
- **Fix:** Richtung auf `in` stellen.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/2
-  ip access-group DMZ-IN in
+ interface GigabitEthernet0/2
+  ip access-group DMZ-IN out
```

## Ticket 3 (R1)

- **Symptom:** `show policy-map control-plane` zeigt bei `CM-ICMP` null Treffer, Ping-Flut wird nicht begrenzt.
- **So findest du es:** `show policy-map control-plane` zeigt bei CM-ICMP 0 Pakete. `show access-lists` zeigt in der zugehörigen ACL `permit udp`.
- **Ursache:** Die ACL für die CoPP-Klasse matcht UDP statt ICMP.
- **Fix:** Auf `permit icmp any any` korrigieren.
- **Eingebaut:**

```diff
- ip access-list extended ICMP-ACL
-  permit icmp any any
+ ip access-list extended ICMP-ACL
+  permit udp any any
```

## Ticket 4 (R1)

- **Symptom:** Telnet von PC1 auf R1 wird sofort getrennt, obwohl PC1 im Management-Netz liegen soll.
- **So findest du es:** `show access-lists MGMT` zeigt bei jedem Telnet-Versuch Treffer auf dem impliziten Deny. Das erlaubte Netz in der ACL passt nicht zu PC1.
- **Ursache:** Die Standard-ACL MGMT erlaubt 192.168.1.0/24 statt 192.168.10.0/24; die vty-`access-class` verwirft PC1.
- **Fix:** ACL auf 192.168.10.0 0.0.0.255 korrigieren.
- **Eingebaut:**

```diff
-  permit 192.168.10.0 0.0.0.255
+  permit 192.168.1.0 0.0.0.255
```

