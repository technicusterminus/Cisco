# Fehlerliste – Lab 18 – Flexible NetFlow, SPAN und RSPAN

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** `show flow monitor MON cache` ist leer, obwohl Verkehr läuft; der Exporter zählt keine Pakete.
- **So findest du es:** `show flow monitor MON cache` ist leer. `show flow interface` zeigt den Monitor an keinem Interface.
- **Ursache:** Der Flow-Monitor ist auf keinem Interface aktiviert.
- **Fix:** `ip flow monitor MON input|output` am Interface Gi0/0 setzen.
- **Eingebaut:**

```diff
-  ip flow monitor MON input
-  ip flow monitor MON output
```

## Ticket 2 (R1)

- **Symptom:** Im Flow-Cache stehen nur noch Einträge je Host-Paar und Protokoll, Anwendungen (Ports) lassen sich nicht unterscheiden.
- **So findest du es:** `show flow record` zeigt keine `match transport`-Felder. Im Cache gibt es pro Host-Paar und Protokoll nur eine Zeile.
- **Ursache:** Der Record enthält keine Transport-Port-Key-Felder, daher werden alle Flows zwischen zwei Hosts zusammengefasst.
- **Fix:** `match transport source-port/destination-port` im Record ergänzen (Monitor-Zuordnung beachten: Record ändern geht nur ohne aktive Anwendung).
- **Eingebaut:**

```diff
-  match transport source-port
-  match transport destination-port
```

## Ticket 3 (SW2)

- **Symptom:** ANA2 sieht nichts vom RSPAN-Verkehr von H2, lokales SPAN auf SW1 funktioniert.
- **So findest du es:** `show interfaces trunk` auf SW2 zeigt VLAN 999 nicht bei den erlaubten VLANs.
- **Ursache:** Das Remote-VLAN 999 ist am SW2-Trunk nicht erlaubt: Die gespiegelten Frames kommen nicht an.
- **Fix:** VLAN 999 in der Allowed-Liste ergänzen.
- **Eingebaut:**

```diff
- interface FastEthernet0/1
-  switchport mode trunk
-  switchport nonegotiate
-  switchport trunk allowed vlan 10,999
+ interface FastEthernet0/1
+  switchport mode trunk
+  switchport nonegotiate
+  switchport trunk allowed vlan 10
```

## Ticket 4 (SW1)

- **Symptom:** ANA1 sieht H1-Verkehr nicht, `show monitor session 1` zeigt ein anderes Ziel.
- **So findest du es:** `show monitor session 1` auf SW1 zeigt einen anderen Zielport als den, an dem ANA1 hängt.
- **Ursache:** Das SPAN-Ziel zeigt auf Fa0/8, ANA1 hängt aber an Fa0/7.
- **Fix:** Ziel-Port auf Fa0/7 setzen.
- **Eingebaut:**

```diff
- monitor session 1 destination interface FastEthernet0/7
+ monitor session 1 destination interface FastEthernet0/8
```

