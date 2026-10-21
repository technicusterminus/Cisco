# Fehlerliste – Lab 22 – QoS: Klassifizierung, Markierung, Queuing, Policing und Shaping

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** `show policy-map interface gi0/1` zeigt die Policy nur im Eingang: Die Priorisierung im Ausgang greift nicht; Sprache leidet bei Last.
- **So findest du es:** `show policy-map interface gi0/1` zeigt die Policy als „Service-policy input“.
- **Ursache:** Policy in der falschen Richtung angewendet (input statt output).
- **Fix:** `service-policy output WAN-OUT`.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  service-policy output WAN-OUT
+ interface GigabitEthernet0/1
+  service-policy input WAN-OUT
```

## Ticket 2 (R1)

- **Symptom:** Die Klasse VOICE zählt keine Treffer (`0 packets`), Sprache landet in class-default.
- **So findest du es:** `show access-lists VOICE` zeigt `permit tcp …`. RTP läuft über UDP.
- **Ursache:** Die ACL matcht TCP statt UDP: RTP-Verkehr passt nicht.
- **Fix:** `permit udp any any range 16384 32767`.
- **Eingebaut:**

```diff
-  permit udp any any range 16384 32767
+  permit tcp any any range 16384 32767
```

## Ticket 3 (R1)

- **Symptom:** Beim Einfügen erscheint eine Meldung über zu hohe Bandbreitenzuteilung (Priority + BUSINESS > 75 % der Schnittstelle), die Policy ist unvollständig.
- **So findest du es:** Beim Einfügen meldet der Router, dass die Bandbreite nicht reicht. `show policy-map WAN-OUT` zeigt `priority percent 90` und `bandwidth percent 40`.
- **Ursache:** Priority 90 % plus Bandwidth 40 % ergeben 130 %. Das ist mehr, als sich am Interface reservieren lässt (bei älteren IOS-Versionen standardmäßig 75 %).
- **Fix:** Priority 20 % (oder `max-reserved-bandwidth` anpassen).
- **Eingebaut:**

```diff
-   priority percent 20
+   priority percent 90
```

