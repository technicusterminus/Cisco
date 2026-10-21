# Fehlerliste – Lab 18 – DHCP (Router, Server, Relay) und DNS

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** PC3 (LAN B) erhält keine Adresse (169.254.x.x), PC1/PC2 funktionieren.
- **So findest du es:** `show ip interface gi0/1 | include Helper` auf R1 bleibt leer.
- **Ursache:** Am LAN-B-Interface fehlt `ip helper-address`: Der Broadcast erreicht den Server nicht.
- **Fix:** `ip helper-address 10.18.3.10` auf Gi0/1.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  ip helper-address 10.18.3.10
+ interface GigabitEthernet0/1
```

## Ticket 2 (R1)

- **Symptom:** PC1/PC2 haben eine Adresse, erreichen aber nichts außerhalb von LAN A; `ipconfig` zeigt Gateway 10.18.1.254.
- **So findest du es:** `ipconfig /all` auf PC1 zeigt das Gateway 10.18.1.254. `show running-config | section dhcp` zeigt `default-router 10.18.1.254`.
- **Ursache:** Der Pool verteilt ein nicht existierendes Gateway.
- **Fix:** `default-router 10.18.1.1`.
- **Eingebaut:**

```diff
-  default-router 10.18.1.1
+  default-router 10.18.1.254
```

## Ticket 3 (R1)

- **Symptom:** PC1 erreicht `www.lab.local` nicht per Namen, per IP schon.
- **So findest du es:** `ipconfig /all` auf PC1 zeigt den DNS-Server 10.18.3.11.
- **Ursache:** Der Pool verteilt einen falschen DNS-Server (10.18.3.11).
- **Fix:** `dns-server 10.18.3.10`.
- **Eingebaut:**

```diff
-  dns-server 10.18.3.10
+  dns-server 10.18.3.11
```

## Ticket 4 (R1)

- **Symptom:** PC2 erhält nach PC1 keine Adresse mehr, `show ip dhcp pool` zeigt keine freien Adressen.
- **So findest du es:** `show ip dhcp pool` zeigt keine freien Adressen. `show running-config | include excluded` schließt fast den ganzen Bereich aus.
- **Ursache:** Der Ausschlussbereich deckt fast den ganzen Pool ab.
- **Fix:** Ausschluss auf 10.18.1.1–10.18.1.10 begrenzen.
- **Eingebaut:**

```diff
- ip dhcp excluded-address 10.18.1.1 10.18.1.10
+ ip dhcp excluded-address 10.18.1.1 10.18.1.254
```

