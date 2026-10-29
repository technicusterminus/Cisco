# Fehlerliste – Lab 31 – MST vertieft: Regionen, Instanzen, Pfadkosten und PVST-Interop

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (AS2)

- **Symptom:** Auf AS2 zeigt `show spanning-tree mst` Boundary-Ports zu DS1 und DS2, und AS2 hält sich für Instanz 2 selbst für die Root.
- **So findest du es:** `show spanning-tree mst configuration` auf AS2 und DS1 vergleichen: Name und VLAN-Zuordnung stimmen, die Revision nicht. `show spanning-tree mst configuration digest` zeigt verschiedene Digests.
- **Ursache:** Revision 2 statt 1. AS2 bildet eine eigene Region. Zur Region CAMPUS gilt nur die CIST, innerhalb seiner Ein-Switch-Region ist AS2 Root für Instanz 2.
- **Fix:** In `spanning-tree mst configuration` `revision 1` setzen. Danach sind die Digests gleich und die Boundary-Ports zu DS1/DS2 verschwinden.
- **Eingebaut:**

```diff
  spanning-tree mst configuration
   name CAMPUS
-  revision 1
+  revision 2
```

## Ticket 2 (DS2)

- **Symptom:** Die Lastverteilung fehlt: Auch VLAN 20 läuft über DS1, `show spanning-tree mst 2` zeigt DS1 als Root.
- **So findest du es:** `show spanning-tree mst 2` auf DS2: Bridge-Priorität 32770 (32768 + Instanz 2), DS1 meldet 8194.
- **Ursache:** Auf DS2 fehlt die Priorität für Instanz 2. DS1 hat 8192 und gewinnt.
- **Fix:** `spanning-tree mst 2 priority 4096` auf DS2.
- **Eingebaut:**

```diff
  spanning-tree mst 0-1 priority 8192
- spanning-tree mst 2 priority 4096
```

## Ticket 3 (AS1)

- **Symptom:** VLAN 10 von H1 läuft über DS2 zur Root DS1, obwohl AS1 einen direkten Uplink zu DS1 hat. Instanz 2 ist unauffällig.
- **So findest du es:** `show spanning-tree mst 1` auf AS1: Root-Port ist Gi0/1, Gi0/0 ist Alternate mit Kosten 200000. `show spanning-tree mst 1 detail` oder `show running-config interface Gi0/0` zeigt die Ursache.
- **Ursache:** An Gi0/0 sind die Kosten für Instanz 1 auf 200000 gesetzt. Der Weg über DS2 kostet 40000 und gewinnt. Instanz 2 ist nicht betroffen, weil die Kosten pro Instanz gelten.
- **Fix:** `no spanning-tree mst 1 cost` an Gi0/0.
- **Eingebaut:**

```diff
+ interface GigabitEthernet0/0
+  spanning-tree mst 1 cost 200000
```

## Ticket 4 (LEG1)

- **Symptom:** H3 erreicht weder sein Gateway noch H1. AS2 und DS2 haben Ports im Zustand `BKN*`.
- **So findest du es:** `show spanning-tree inconsistentports` auf AS2 und DS2: Gi0/2 bzw. Gi0/3 sind *PVST Sim. Inconsistent*. Log `%SPANTREE-2-PVSTSIM_FAIL ... VLAN 10`. Auf LEG1 `show spanning-tree vlan 10`: LEG1 hält sich selbst für die Root (Priorität 10).
- **Ursache:** LEG1 hat für VLAN 10 die Priorität 0 und sendet eine bessere BPDU als die CIST-Root DS1 (4096). Weil die CIST-Root in der Region liegt, blockiert die Region beide Boundary-Ports, LEG1 ist abgeschnitten.
- **Fix:** `no spanning-tree vlan 10 priority` auf LEG1. Die Ports erholen sich ohne shut/no shut.
- **Eingebaut:**

```diff
  spanning-tree mode rapid-pvst
+ spanning-tree vlan 10 priority 0
```
