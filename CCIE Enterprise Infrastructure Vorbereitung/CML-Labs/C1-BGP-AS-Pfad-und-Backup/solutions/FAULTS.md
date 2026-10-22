# Fehlerliste – Lab C1 – BGP: allowas-in, private AS, GTSM und bedingte Ankündigung

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (BR)

- **Symptom:** BR erreicht das Netz der Zentrale nicht: `ping 198.51.100.1 source Loopback1` scheitert, und `show ip bgp` auf BR enthält 198.51.100.0/24 nicht, obwohl ISP1 das Netz kennt.
- **So findest du es:** Auf ISP1 zeigt `show ip bgp 198.51.100.0` das Netz mit dem Pfad `65001`, an BR geht es also als `64501 65001`. `show ip bgp neighbors 10.0.21.1` auf BR zählt abgelehnte Präfixe wegen AS-Pfad-Schleife. In der BGP-Konfiguration von BR fehlt `allowas-in`.
- **Ursache:** Ohne `allowas-in` verwirft BR jede Route, in deren AS-Pfad der eigene AS 65001 steht. Das ist der normale eBGP-Schleifenschutz, hier aber unerwünscht, weil beide Standorte denselben AS nutzen.
- **Fix:** `neighbor 10.0.21.1 allowas-in 1` unter `router bgp 65001` auf BR.
- **Eingebaut:**

```diff
- neighbor 10.0.21.1 allowas-in 1
```

## Ticket 2 (ISP2)

- **Symptom:** Die BGP-Sitzung zwischen HQ und ISP2 bleibt down, obwohl `ping 10.0.12.1` von HQ klappt.
- **So findest du es:** `show ip bgp summary` auf HQ zeigt 10.0.12.1 in *Idle* oder *Active*. `show ip bgp neighbors 10.0.12.1` auf HQ nennt GTSM mit einer minimalen eingehenden TTL von 254. Auf ISP2 fehlt `ttl-security` für 10.0.12.2.
- **Ursache:** GTSM nur auf einer Seite: HQ erwartet eine TTL von mindestens 254, ISP2 sendet eBGP-Pakete mit TTL 1. HQ verwirft sie, bevor BGP sie sieht.
- **Fix:** `neighbor 10.0.12.2 ttl-security hops 1` unter `router bgp 64502` auf ISP2.
- **Eingebaut:**

```diff
- neighbor 10.0.12.2 ttl-security hops 1
```

## Ticket 3 (ISP1)

- **Symptom:** Der Internet-Router NET sieht 198.51.100.0/24 und 203.0.113.0/24 mit dem privaten AS 65001 im Pfad.
- **So findest du es:** `show ip bgp` auf NET: Pfad `64501 65001`. In der Konfiguration von ISP1 fehlt für 10.0.31.2 die Zeile `remove-private-as`, ISP2 hat sie für seinen Nachbarn NET.
- **Ursache:** ISP1 gibt den AS-Pfad unverändert an NET weiter. Private AS-Nummern (64512 bis 65534) gehören nicht ins Internet.
- **Fix:** `neighbor 10.0.31.2 remove-private-as` auf ISP1, danach `clear ip bgp 10.0.31.2 soft out`.
- **Eingebaut:**

```diff
- neighbor 10.0.31.2 remove-private-as
```

## Ticket 4 (ISP1)

- **Symptom:** ISP2 bekommt 198.51.100.0/24 von HQ, obwohl ISP1 läuft. NET hat das Netz von beiden Providern in der BGP-Tabelle.
- **So findest du es:** `show ip bgp 0.0.0.0` auf HQ: keine Default-Route. Damit ist die Non-Exist-Bedingung erfüllt, `show ip bgp neighbors 10.0.12.1 | include Condition` zeigt *Advertise*. Auf ISP1 fehlt `default-originate` für 10.0.11.2.
- **Ursache:** Die Default-Route von ISP1 ist der Merker für die Bedingung. Fehlt sie, hält HQ ISP1 für ausgefallen und kündigt das Netz dauerhaft bei ISP2 an.
- **Fix:** `neighbor 10.0.11.2 default-originate` unter `router bgp 64501` auf ISP1.
- **Eingebaut:**

```diff
- neighbor 10.0.11.2 default-originate
```

## Ticket 5 (HQ)

- **Symptom:** Ausfalltest: Nach `shutdown` auf HQ Gi0/0 erreicht NET das Netz 198.51.100.0/24 auch nach zwei Minuten nicht. ISP2 bekommt die Backup-Route nie.
- **So findest du es:** `show ip bgp neighbors 10.0.12.1 | include Condition` auf HQ bleibt auch nach dem Ausfall bei *Withdraw*. `show ip prefix-list DEFAULT` zeigt `0.0.0.0/0 le 32`: Die Liste passt auf jede Route, auch auf 192.0.2.0/24 von ISP2.
- **Ursache:** Mit `le 32` beschreibt die Prefix-Liste nicht mehr nur die Default-Route, sondern alle Präfixe. Die Bedingung gilt als erfüllt, solange irgendeine passende Route existiert, und von ISP2 kommen weiter Routen. Die Backup-Ankündigung wird deshalb nie ausgelöst.
- **Fix:** `no ip prefix-list DEFAULT seq 5` und `ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0` auf HQ.
- **Eingebaut:**

```diff
-ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0
+ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0 le 32
```
