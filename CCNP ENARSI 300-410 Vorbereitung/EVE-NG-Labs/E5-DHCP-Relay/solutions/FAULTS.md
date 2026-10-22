# Fehlerliste – Lab E5 – DHCP-Server und DHCP-Relay über mehrere Router

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** H1 bekommt keine Adresse; auf R2 zeigt `debug ip dhcp server packet` keine Anfragen aus 10.1.1.1.
- **So findest du es:** `show ip interface Gi0/0` auf R1 nennt „Helper address is not set“. Die Anfrage von H1 endet an R1.
- **Ursache:** Ohne `ip helper-address` leitet R1 den Broadcast nicht an den Server weiter.
- **Fix:** `ip helper-address 10.0.12.2` unter Gi0/0 auf R1.
- **Eingebaut:**

```diff
- ip helper-address 10.0.12.2
```

## Ticket 2 (R3)

- **Symptom:** H2 bekommt keine Adresse; auf R2 zeigt `debug ip dhcp server packet` keine Anfragen aus 10.1.2.1.
- **So findest du es:** `show ip interface Gi0/1` auf R3 nennt die Helper-Adresse 10.0.32.1. `show ip route 10.0.32.1` findet nur die Default-Route; die Adresse gehört niemandem.
- **Ursache:** Zahlendreher in der Server-Adresse: Die Anfrage geht an 10.0.32.1, nicht an den Server 10.0.23.1.
- **Fix:** `ip helper-address 10.0.23.1` unter Gi0/1 auf R3.
- **Eingebaut:**

```diff
- ip helper-address 10.0.23.1
+ ip helper-address 10.0.32.1
```

## Ticket 3 (R2)

- **Symptom:** R2 empfängt die Anfragen von R3 (giaddr 10.1.2.1), H2 bekommt trotzdem keine Adresse; im Debug steht „there is no address pool for 10.1.2.1“.
- **So findest du es:** `show ip dhcp pool LAN2` zeigt das Netz 10.1.20.0/24. Das Debug nennt „there is no address pool for 10.1.2.1“.
- **Ursache:** Der Server wählt den Pool anhand von giaddr (10.1.2.1). Das Netz des Pools LAN2 (10.1.20.0/24) enthält die Adresse nicht, also gibt es keinen passenden Pool.
- **Fix:** `network 10.1.2.0 255.255.255.0` im Pool LAN2.
- **Eingebaut:**

```diff
- network 10.1.2.0 255.255.255.0
+ network 10.1.20.0 255.255.255.0
```

## Ticket 4 (R2)

- **Symptom:** R2 empfängt die Anfragen von R1, H1 bekommt trotzdem keine Adresse; die Bindings bleiben leer.
- **So findest du es:** `show running-config | include excluded` zeigt den Bereich bis 10.1.1.254. `show ip dhcp pool LAN1` zeigt 0 Leases.
- **Ursache:** Der Ausschluss deckt den ganzen Pool ab, es bleibt keine freie Adresse.
- **Fix:** `ip dhcp excluded-address 10.1.1.1 10.1.1.10`.
- **Eingebaut:**

```diff
-ip dhcp excluded-address 10.1.1.1 10.1.1.10
+ip dhcp excluded-address 10.1.1.1 10.1.1.254
```

## Ticket 5 (R2)

- **Symptom:** R2 sendet das DHCPOFFER für H2 (Debug zeigt es), H2 bekommt es trotzdem nicht.
- **So findest du es:** `show ip route 10.1.2.1` auf R2: „Network not in table“. Das Debug zeigt das gesendete DHCPOFFER, der Router kann es aber nicht zustellen.
- **Ursache:** R2 sendet Offer und Ack als Unicast an giaddr (10.1.2.1). Ohne Route zu 10.1.2.0/24 geht das Paket ins Leere.
- **Fix:** `ip route 10.1.2.0 255.255.255.0 10.0.23.2` auf R2.
- **Eingebaut:**

```diff
-ip route 10.1.2.0 255.255.255.0 10.0.23.2
```
