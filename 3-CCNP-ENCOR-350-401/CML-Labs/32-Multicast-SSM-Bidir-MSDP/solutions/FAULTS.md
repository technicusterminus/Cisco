# Fehlerliste – Lab 32 – Multicast vertieft: IGMPv3 und SSM, Bidir-PIM, Anycast-RP mit MSDP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R4)

- **Symptom:** SSM: REC ist 232.1.1.1 mit Quelle 192.168.1.10 beigetreten, bekommt aber nichts. Auf R4 gibt es keinen `(S,G)`-Eintrag für die Gruppe.
- **So findest du es:** `show ip igmp interface GigabitEthernet0/1` auf R4 meldet `IGMP version is 2`. `show ip igmp groups 232.1.1.1 detail` zeigt keinen Eintrag mit Quelle.
- **Ursache:** Der Router fragt mit IGMPv2 ab. Der Host fällt dadurch ebenfalls auf Version 2 zurück und kann keine Quelle nennen. Einen Beitritt ohne Quelle verwirft der Router im SSM-Bereich 232.0.0.0/8.
- **Fix:** `ip igmp version 3` auf R4 Gi0/1.
- **Eingebaut:**

```diff
- ip igmp version 3
```

## Ticket 2 (R3)

- **Symptom:** Bidir: Der Ping von SRC an 239.2.1.1 bleibt unbeantwortet. Die Gruppe 239.1.1.1 ist davon nicht betroffen, sobald die übrigen Tickets gelöst sind.
- **So findest du es:** `show ip pim rp mapping` auf R3 nennt 10.255.0.200 ohne den Zusatz `bidir`, auf R2 und R4 mit. `show ip pim interface df` ist auf R3 leer, und `show ip mroute 239.2.1.1` zeigt dort kein Flag `B`.
- **Ursache:** R3 behandelt 239.2.0.0/16 als gewöhnlichen Sparse Mode, seine Nachbarn als Bidir. R3 nimmt an keiner DF-Wahl teil und leitet Verkehr auf dem Shared Tree nicht in beide Richtungen weiter. Der Modus einer Gruppe muss im ganzen Netz gleich sein.
- **Fix:** `ip pim rp-address 10.255.0.200 20 bidir` auf R3.
- **Eingebaut:**

```diff
-ip pim rp-address 10.255.0.200 20 bidir
+ip pim rp-address 10.255.0.200 20
```

## Ticket 3 (R3)

- **Symptom:** Anycast-RP: `show ip msdp summary` zeigt auf R2 und R3 keinen Peer im Zustand `Up`.
- **So findest du es:** `show ip msdp peer` auf R3 nennt 10.255.0.4 als Peer. R4 spricht kein MSDP. Auf R2 steht der Peer 10.255.0.3 im Zustand `Down` oder `Connect`.
- **Ursache:** R3 hat den falschen Peer eingetragen. MSDP ist eine TCP-Sitzung zwischen fest konfigurierten Adressen, beide Seiten müssen einander nennen.
- **Fix:** Auf R3 `no ip msdp peer 10.255.0.4`, dann `ip msdp peer 10.255.0.2 connect-source Loopback0`.
- **Eingebaut:**

```diff
-ip msdp peer 10.255.0.2 connect-source Loopback0
+ip msdp peer 10.255.0.4 connect-source Loopback0
```

## Ticket 4 (R2)

- **Symptom:** Anycast-RP: Auch mit stehender MSDP-Sitzung antwortet REC nicht auf Pings an 239.1.1.1. Der SA-Cache auf R3 bleibt leer, während SRC sendet.
- **So findest du es:** `show ip pim interface` auf R2 listet Loopback1 nicht. `show ip mroute 239.1.1.1` auf R2 zeigt keinen `(S,G)`-Eintrag, obwohl SRC sendet, und `debug ip pim` meldet Register, die R2 nicht als RP annimmt.
- **Ursache:** Ein Router arbeitet nur dann als RP, wenn auf dem Interface mit der RP-Adresse PIM aktiv ist. R2 verarbeitet die Register von R1 nicht, kennt also keine aktive Quelle und erzeugt keine Source-Active-Meldung für R3.
- **Fix:** `ip pim sparse-mode` auf R2 Loopback1.
- **Eingebaut:**

```diff
- ip pim sparse-mode
```
