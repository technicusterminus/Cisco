# Fehlerliste – Lab 04 – Policy-Based Routing mit IP SLA

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Die Route-Map ist konfiguriert, aber H1 läuft weiter über ISP1 (`show route-map` zeigt 0 Treffer).
- **So findest du es:** `show route-map` zeigt 0 Treffer. `show ip interface Gi0/0 | include policy` meldet keine Policy, `show ip interface Gi0/1` dagegen schon.
- **Ursache:** `ip policy` hängt am WAN-Interface Gi0/1 statt am LAN-Interface Gi0/0: PBR wirkt nur auf Pakete, die dort eingehen.
- **Fix:** Policy von Gi0/1 entfernen, an Gi0/0 binden.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip policy route-map PBR
+ interface GigabitEthernet0/1
+  ip policy route-map PBR
```

## Ticket 2 (R1)

- **Symptom:** PBR-Route-Map ist am LAN aktiv, aber H1 nimmt nicht den Weg über ISP2.
- **So findest du es:** `show access-lists` zeigt bei der PBR-ACL keine Treffer. Vergleiche die Quelladresse in der ACL mit der echten Adresse von H1.
- **Ursache:** Die ACL referenziert eine falsche Quelladresse (.21).
- **Fix:** ACL auf 192.168.1.11 korrigieren.
- **Eingebaut:**

```diff
- permit ip host 192.168.1.11 any
+ permit ip host 192.168.1.21 any
```

## Ticket 3 (R1)

- **Symptom:** H1 läuft nicht über ISP2, obwohl ACL und Policy stimmen; `show track 1` ist Down.
- **So findest du es:** `show track 1` ist Down. `show ip sla statistics` meldet, dass die Operation nie gelaufen ist, `show ip sla configuration` zeigt keine Schedule.
- **Ursache:** Die IP-SLA-Operation wurde nie geplant: ohne `ip sla schedule` gibt es keine Messung, der Track bleibt Down und PBR verwirft den Next-Hop.
- **Fix:** `ip sla schedule 1 life forever start-time now` ergänzen.
- **Eingebaut:**

```diff
- ip sla schedule 1 life forever start-time now
```

## Ticket 4 (R3)

- **Symptom:** H1 hat Internet-Ausfall (Pings zu 8.8.8.8 scheitern), H2 funktioniert; der Pfad bis R3 steht.
- **So findest du es:** `traceroute 8.8.8.8` von H1 endet bei R3. `show ip route 0.0.0.0` auf R3 meldet „Network not in table“.
- **Ursache:** ISP2 (R3) hat keine Default-Route Richtung R4: Pakete, die PBR dorthin lenkt, werden verworfen.
- **Fix:** Default-Route auf R3 setzen (`ip route 0.0.0.0 0.0.0.0 10.0.34.2`).
- **Eingebaut:**

```diff
- ip route 0.0.0.0 0.0.0.0 10.0.34.2
```

