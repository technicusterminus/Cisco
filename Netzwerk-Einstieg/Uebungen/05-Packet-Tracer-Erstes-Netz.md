# Übung 5: Packet Tracer, dein erstes Netz

Cisco Packet Tracer ist kostenlos (Cisco Networking Academy, Kurs „Getting Started with Cisco Packet Tracer“).

## Ziel

Zwei Subnetze mit je einem PC, verbunden über einen Router, und ein erfolgreicher Ping dazwischen.

```
PC1 ── SW1 ── R1 ── SW2 ── PC2
 192.168.1.0/24   192.168.2.0/24
```

## Aufbau

1. Zwei PCs, zwei Switches (2960), ein Router (2911 oder 1941) platzieren.
2. Mit Copper-Straight-Through-Kabeln verbinden: PC1–SW1, SW1–R1 (Gi0/0), R1 (Gi0/1)–SW2, SW2–PC2.

## Konfiguration

**PC1** (Desktop → IP Configuration): IP `192.168.1.10`, Maske `255.255.255.0`, Gateway `192.168.1.1`.
**PC2**: IP `192.168.2.10`, Maske `255.255.255.0`, Gateway `192.168.2.1`.

**Router R1** (CLI):

```
enable
configure terminal
hostname R1
interface gigabitEthernet 0/0
 ip address 192.168.1.1 255.255.255.0
 no shutdown
interface gigabitEthernet 0/1
 ip address 192.168.2.1 255.255.255.0
 no shutdown
end
copy running-config startup-config
```

Die Switches brauchen keine Konfiguration.

## Test

1. Auf PC1 (Desktop → Command Prompt): `ping 192.168.1.1` (Gateway), dann `ping 192.168.2.10` (PC2).
2. Auf R1: `show ip interface brief` und `show ip route`.

**Fragen:**
1. Warum klappt der erste Ping auf PC2 manchmal nicht? (ARP!)
2. Was passiert, wenn du am Router `no shutdown` bei Gi0/1 vergisst?
3. Welche Einträge stehen in der Routing-Tabelle, und was bedeuten `C` und `L`?

<details><summary>Lösungshinweise</summary>

1. **Wegen ARP.** Vor dem ersten Paket muss PC1 die MAC des Gateways und der Router die MAC von PC2 erfragen. Bis dahin geht ein Ping verloren, die folgenden klappen.
2. **Gi0/1 bleibt `administratively down`.** Damit fehlt das Netz 192.168.2.0/24 in der Routing-Tabelle, und PC2 ist nicht erreichbar.
3. **Zwei C- und zwei L-Einträge.** `C` = direkt verbundenes Netz (192.168.1.0/24 und 192.168.2.0/24), `L` = die eigene Adresse am Interface als /32.

</details>

## Weiter

Wenn das klappt, hast du den Kern von Switching und Routing verstanden. Mach als Nächstes die [Packet-Tracer-Labs der CCNA](../../CCNA%20200-301%20Vorbereitung/Packet-Tracer-Labs/), beginnend mit Lab 01.
