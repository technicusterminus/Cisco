# Fehlerliste – Lab C2 – Multicast: Anycast RP mit MSDP, RPF-Umleitung und SSM

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** R3 hat keinen einzigen PIM-Nachbarn.
- **So findest du es:** `show ip pim interface` auf R2: Gi0/1 fehlt in der Liste. Ohne PIM auf dieser Seite gibt es zwischen R2 und R3 keine Nachbarschaft, und R3 hat keinen anderen PIM-Nachbarn.
- **Ursache:** PIM fehlt auf R2 Gi0/1. Der einzige Multicast-Weg zwischen R2 und R3 ist damit tot.
- **Fix:** `ip pim sparse-mode` unter Gi0/1 auf R2.
- **Eingebaut:**

```diff
- ip pim sparse-mode
```

## Ticket 2 (R2)

- **Symptom:** `show ip msdp summary` auf R2 und R3 zeigt keine Sitzung im Zustand Up.
- **So findest du es:** `show ip msdp summary` auf R2 nennt den Peer 10.0.0.13 statt 10.0.0.3, im Zustand Down. R3 wartet vergeblich auf 10.0.0.2.
- **Ursache:** Tippfehler in der Peer-Adresse. R2 versucht, 10.0.0.13 zu erreichen, die es nicht gibt, und nimmt keine Verbindung von 10.0.0.3 an, weil diese Adresse bei R2 nicht als Peer eingetragen ist.
- **Fix:** `no ip msdp peer 10.0.0.13` und `ip msdp peer 10.0.0.3 connect-source Loopback0` auf R2.
- **Eingebaut:**

```diff
-ip msdp peer 10.0.0.3 connect-source Loopback0
+ip msdp peer 10.0.0.13 connect-source Loopback0
```

## Ticket 3 (R1)

- **Symptom:** Die Rendezvous Points bekommen von der Quelle nichts mit: `show ip mroute 239.1.1.1` auf R2 zeigt keinen Eintrag mit 10.1.1.10, auch während SRC an 239.1.1.1 sendet.
- **So findest du es:** `show ip pim rp mapping` auf R1 nennt 10.255.255.254. `show ip route 10.255.255.254` findet keine Route, R1 kann seine Register-Nachrichten nicht zustellen.
- **Ursache:** Falsche RP-Adresse auf R1. Als First-Hop-Router muss R1 die Quelle beim RP registrieren; an eine Adresse, die niemand trägt, kommt keine Register-Nachricht an. SSM braucht keinen RP und läuft deshalb weiter.
- **Fix:** `no ip pim rp-address 10.255.255.254` und `ip pim rp-address 10.255.255.255` auf R1.
- **Eingebaut:**

```diff
-ip pim rp-address 10.255.255.255
+ip pim rp-address 10.255.255.254
```

## Ticket 4 (R3)

- **Symptom:** RCV empfängt die Multicast-Pings von SRC weiterhin nicht, obwohl R3 die Quelle 10.1.1.10 kennt (`show ip msdp sa-cache`).
- **So findest du es:** `show ip rpf 10.1.1.10` auf R3 nennt GigabitEthernet0/0 mit dem RPF-Nachbarn 10.0.13.1. Auf diesem Interface läuft kein PIM (`show ip pim interface`), also kann R3 dorthin keinen Join schicken.
- **Ursache:** Die RPF-Prüfung folgt dem Unicast-Routing, und das zeigt über die Firewall-Strecke ohne PIM. Die statische Mroute, die den RPF-Weg auf R2 umlenkt, fehlt.
- **Fix:** `ip mroute 10.1.1.0 255.255.255.0 10.0.23.1` auf R3.
- **Eingebaut:**

```diff
-ip mroute 10.1.1.0 255.255.255.0 10.0.23.1
```

## Ticket 5 (R3)

- **Symptom:** Die SSM-Gruppe 232.1.1.1 fehlt in `show ip igmp groups` auf R3, obwohl RCV sie mit der Quelle 10.1.1.10 abonniert hat.
- **So findest du es:** `show ip igmp interface GigabitEthernet0/2` auf R3 zeigt IGMP-Version 2. RCV meldet sich mit IGMPv3 und Quellangabe an, R3 wertet auf diesem Interface aber keine Quellen aus. Für den SSM-Bereich 232.0.0.0/8 nimmt R3 ohne Quelle keine Anmeldung an.
- **Ursache:** IGMPv3 fehlt am Empfänger-Interface. Ohne Version 3 gibt es keine quellspezifischen Anmeldungen und damit kein SSM.
- **Fix:** `ip igmp version 3` unter Gi0/2 auf R3.
- **Eingebaut:**

```diff
- ip igmp version 3
```
