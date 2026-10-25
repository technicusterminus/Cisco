# Fehlerliste – Lab 06 – Spanning Tree, MST und Schutzfunktionen

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW4)

- **Symptom:** Alle Hosts erreichen sich, aber `show spanning-tree mst` auf SW4 meldet Boundary-Ports zur eigenen MST-Region; die Lastverteilung nach Instanz funktioniert nicht.
- **So findest du es:** `show spanning-tree mst configuration` auf SW4 und SW1 vergleichen: Der Name unterscheidet sich (Groß- und Kleinschreibung zählt). `show spanning-tree mst configuration digest` zeigt verschiedene Digests.
- **Ursache:** Der Region-Name auf SW4 weicht ab (case-sensitive), dadurch ein anderer Digest: SW4 bildet eine eigene Region und alle VLANs hängen am IST.
- **Fix:** Name auf `ENCOR` korrigieren, Digest mit `show spanning-tree mst configuration digest` vergleichen.
- **Eingebaut:**

```diff
- name ENCOR
+ name Encor
```

## Ticket 2 (SW2)

- **Symptom:** Instanz 2 hat dieselbe Root wie Instanz 1 (SW1), die VLAN-Lastverteilung fehlt.
- **So findest du es:** `show spanning-tree mst 2` auf SW1 und SW2: SW1 ist Root für Instanz 2. Die Priorität von SW2 steht dort auf dem Standardwert.
- **Ursache:** Auf SW2 fehlt die Priorität 4096 für Instanz 2; SW1 hat dort 8192 und gewinnt.
- **Fix:** `spanning-tree mst 2 priority 4096` auf SW2 setzen.
- **Eingebaut:**

```diff
- spanning-tree mst 2 priority 4096
```

## Ticket 3 (SW3)

- **Symptom:** Nachdem jemand an Fa0/6 einen kleinen Switch angeschlossen hat, wechselt die Root und das Netz flattert. SW3 zeigt eine neue Root über Fa0/6.
- **So findest du es:** `show spanning-tree root` auf SW3 zeigt eine neue Root mit Priorität 0 über den Edge-Port. `show spanning-tree interface <Port> detail` zeigt, dass BPDU Guard nicht aktiv ist.
- **Ursache:** BPDU Guard fehlt am Edge-Port: SW5 (Priorität 0) darf BPDUs senden und wird Root.
- **Fix:** `spanning-tree bpduguard enable` am Port setzen (Port ggf. mit shut/no shut zurücksetzen).
- **Eingebaut:**

```diff
- interface FastEthernet0/6
-  switchport mode access
-  switchport access vlan 10
-  spanning-tree portfast
-  spanning-tree bpduguard enable
+ interface FastEthernet0/6
+  switchport mode access
+  switchport access vlan 10
+  spanning-tree portfast
```

