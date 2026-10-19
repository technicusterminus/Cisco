# Fehlerliste – Lab 11 – Wireless-Architekturen: WLC, Lightweight-AP und DHCP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Der LAP bekommt eine Adresse, erscheint aber nicht im WLC.
- **Ursache:** Option 43 enthält 10.11.1.6, der WLC hat 10.11.1.5.
- **Fix:** `option 43 hex f104.0a0b.0105`.
- **Eingebaut:**

```diff
-  option 43 hex f104.0a0b.0105
+  option 43 hex f104.0a0b.0106
```

## Ticket 2 (SW1)

- **Symptom:** Der LAP ist offline (keine Link-LED), `show interfaces status` auf SW1 zeigt Fa0/2 als disabled.
- **Ursache:** Der Switchport des LAP ist abgeschaltet.
- **Fix:** `no shutdown` auf Fa0/2.
- **Eingebaut:**

```diff
- interface range FastEthernet0/1 - 2
-  switchport mode access
-  spanning-tree portfast
+ interface range FastEthernet0/1 - 2
+  switchport mode access
+  spanning-tree portfast
+ interface FastEthernet0/2
+  shutdown
```

## Ticket 3 (R1)

- **Symptom:** LAP und Laptop erhalten keine Adresse (APIPA oder keine Anmeldung); `show ip dhcp pool` zeigt 0 freie Adressen.
- **Ursache:** Der ausgeschlossene Bereich umfasst den ganzen Pool.
- **Fix:** Excluded-Address nur 10.11.1.1–10.11.1.10.
- **Eingebaut:**

```diff
- ip dhcp excluded-address 10.11.1.1 10.11.1.10
+ ip dhcp excluded-address 10.11.1.1 10.11.1.254
```

