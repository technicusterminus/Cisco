# Fehlerliste – Lab E1 – DMVPN Phase 3 mit EIGRP

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (S1)

- **Symptom:** S1 hat keinen EIGRP-Nachbarn zum Hub; der Tunnel ist up/up, aber `show dmvpn` auf dem Hub listet S1 nicht.
- **So findest du es:** `show interfaces Tunnel0 | include Key` zeigt auf S1 den Key 0x65 (101), auf dem Hub 0x64 (100). Der Hub verwirft die GRE-Pakete mit fremdem Key.
- **Ursache:** Der Tunnel Key ist Teil des GRE-Headers und muss auf beiden Seiten gleich sein. Bei Abweichung verwirft der Empfänger das Paket, die NHRP-Registrierung kommt nie an.
- **Fix:** `tunnel key 100` auf S1.
- **Eingebaut:**

```diff
- tunnel key 100
+ tunnel key 101
```

## Ticket 2 (S2)

- **Symptom:** S2 hat keinen EIGRP-Nachbarn zum Hub; `show dmvpn` auf S2 zeigt den Hub nicht als UP.
- **So findest du es:** `show ip nhrp nhs detail` auf S2 zeigt als NBMA-Adresse des Hubs 198.51.100.2 (das ist die ISP-Seite). `ping 198.51.100.2` geht, das GRE-Paket der Registrierung landet aber beim ISP.
- **Ursache:** Die NBMA-Adresse des Hubs ist falsch (ISP-Interface statt Hub). Die Registrierung geht an den ISP-Router, der kein GRE terminiert.
- **Fix:** `ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast`.
- **Eingebaut:**

```diff
- ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast
+ ip nhrp nhs 172.16.0.1 nbma 198.51.100.2 multicast
```

## Ticket 3 (HUB)

- **Symptom:** Der Verkehr zwischen S1 und S2 läuft, geht aber immer über den Hub; `show ip route nhrp` ist auf beiden Spokes leer.
- **So findest du es:** `show running-config interface Tunnel0 | include redirect` auf dem Hub bleibt leer. `show ip nhrp traffic` zeigt keine gesendeten Traffic Indications.
- **Ursache:** Ohne `ip nhrp redirect` sagt der Hub den Spokes nie, dass es einen kürzeren Weg gibt. Die Spokes bleiben bei der Summary-Route über den Hub.
- **Fix:** `ip nhrp redirect` am Tunnel des Hubs.
- **Eingebaut:**

```diff
- ip nhrp redirect
```

## Ticket 4 (S2)

- **Symptom:** Von S1 zu S2 geht der Verkehr direkt, in der Gegenrichtung aber immer noch über den Hub.
- **So findest du es:** `show running-config interface Tunnel0 | include shortcut` auf S2 bleibt leer; auf S1 steht die Zeile. `show ip route nhrp` auf S2 bleibt leer.
- **Ursache:** Ohne `ip nhrp shortcut` wertet S2 die Redirects des Hubs nicht aus und installiert keine NHRP-Route. Der Rückweg bleibt bei der Summary über den Hub.
- **Fix:** `ip nhrp shortcut` am Tunnel von S2.
- **Eingebaut:**

```diff
- ip nhrp shortcut
```

## Ticket 5 (HUB)

- **Symptom:** S1 erreicht das LAN von S2 nicht; die Traceroute endet beim ISP.
- **So findest du es:** `show ip route eigrp` auf S1 zeigt nur 10.10.0.0/24 statt 10.10.0.0/16. `show ip route 10.10.2.1` greift auf die Default-Route zum ISP, daher endet die Traceroute dort.
- **Ursache:** Die Summary ist /24 statt /16 und deckt die Spoke-LANs nicht ab. Wegen Split Horizon gibt der Hub die Spoke-Routen nicht weiter, also fehlt jede Route zu 10.10.2.0/24.
- **Fix:** `ip summary-address eigrp 100 10.10.0.0 255.255.0.0` am Tunnel des Hubs.
- **Eingebaut:**

```diff
- ip summary-address eigrp 100 10.10.0.0 255.255.0.0
+ ip summary-address eigrp 100 10.10.0.0 255.255.255.0
```
