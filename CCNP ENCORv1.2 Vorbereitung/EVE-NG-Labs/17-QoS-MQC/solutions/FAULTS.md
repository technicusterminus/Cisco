# Fehlerliste – Lab 17 – QoS mit MQC: Markieren, Policing, Shaping, LLQ

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Die Klasse VOICE bleibt in `show policy-map interface` bei null Paketen, obwohl H1 mit DSCP 46 sendet.
- **Ursache:** `match-all` mit zwei verschiedenen DSCP-Werten kann nie zutreffen (ein Paket hat genau einen DSCP).
- **Fix:** `match-any` verwenden oder nur `match dscp ef` behalten.
- **Eingebaut:**

```diff
- class-map match-any VOICE
-  match dscp ef
+ class-map match-all VOICE
+  match dscp ef
+  match dscp cs5
```

## Ticket 2 (R1)

- **Symptom:** Der WAN-Link wird überfüllt, Voice leidet, `show policy-map interface Gi0/1` zeigt keine Policy.
- **Ursache:** Die Ausgangs-Policy hängt am LAN-Interface Gi0/0 statt am WAN-Interface Gi0/1; dort entsteht der Engpass.
- **Fix:** Policy an Gi0/1 (output) binden.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  service-policy output WAN
+ interface GigabitEthernet0/0
+  service-policy output WAN
```

## Ticket 3 (R1)

- **Symptom:** Der Durchsatz Richtung SRV bricht auf einen winzigen Bruchteil ein, Pings dauern extrem lang.
- **Ursache:** `shape average` erwartet bit/s: 2000 bps statt 2 000 000 bps (2 Mbit/s).
- **Fix:** Rate auf 2000000 korrigieren.
- **Eingebaut:**

```diff
- shape average 2000000
+ shape average 2000
```

## Ticket 4 (R1)

- **Symptom:** Der Gast (H3) wird als Voice klassifiziert und nimmt der echten Sprache die Priority-Queue weg.
- **Ursache:** Der Gast-Verkehr wird auf DSCP EF gesetzt statt auf Default und begrenzt: Missbrauch der Trust Boundary.
- **Fix:** Auf `set dscp default` und einen Policer zurückstellen.
- **Eingebaut:**

```diff
- policy-map MARK
-  class GUEST-CM
-   set dscp default
-   police rate 256000 bps conform-action transmit exceed-action drop
+ policy-map MARK
+  class GUEST-CM
+   set dscp ef
```

