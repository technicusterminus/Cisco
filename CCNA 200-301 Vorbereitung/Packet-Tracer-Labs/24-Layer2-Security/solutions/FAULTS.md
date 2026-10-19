# Fehlerliste – Lab 24 – Layer-2-Sicherheit: Port Security, DHCP Snooping, DAI

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW1)

- **Symptom:** Keiner der PCs erhält eine Adresse; `show ip dhcp snooping` zeigt Fa0/24 als untrusted, Offers von R1 werden verworfen.
- **Ursache:** Der Uplink zum legitimen DHCP-Server ist nicht als `trust` markiert.
- **Fix:** `ip dhcp snooping trust` auf Fa0/24.
- **Eingebaut:**

```diff
- interface FastEthernet0/24
-  ip dhcp snooping trust
```

## Ticket 2 (SW1)

- **Symptom:** Ein PC bekommt eine Adresse aus 192.168.66.0/24 vom Rogue-Server, Snooping wirkt nicht.
- **Ursache:** Snooping ist global an, aber für kein VLAN aktiv (`ip dhcp snooping vlan` fehlt).
- **Fix:** `ip dhcp snooping vlan 1`.
- **Eingebaut:**

```diff
- ip dhcp snooping
- ip dhcp snooping vlan 1
+ ip dhcp snooping
```

## Ticket 3 (SW1)

- **Symptom:** PC2 verliert die Verbindung, der Port ist `err-disabled` (Port-Security-Violation), obwohl er korrekt angeschlossen ist.
- **Ursache:** Statisch hinterlegte MAC (0001.0001.0001) passt nicht zu PC2; sein erster Frame löst die Violation aus.
- **Fix:** Sticky-Learning statt falscher statischer MAC; Port per `shutdown`/`no shutdown` zurücksetzen.
- **Eingebaut:**

```diff
- interface FastEthernet0/2
-  switchport mode access
-  switchport port-security
-  switchport port-security maximum 1
-  switchport port-security mac-address sticky
+ interface FastEthernet0/2
+  switchport mode access
+  switchport port-security
+  switchport port-security maximum 1
+  switchport port-security mac-address 0001.0001.0001
```

## Ticket 4 (SW1)

- **Symptom:** PCs bekommen Adressen, erreichen aber das Gateway nicht (ARP-Antworten des Routers werden von DAI verworfen).
- **Ursache:** Der Uplink ist für DAI nicht trusted; die ARP-Antworten des Routers passen nicht zur Bindungstabelle.
- **Fix:** `ip arp inspection trust` auf Fa0/24.
- **Eingebaut:**

```diff
- interface FastEthernet0/24
-  ip arp inspection trust
```

