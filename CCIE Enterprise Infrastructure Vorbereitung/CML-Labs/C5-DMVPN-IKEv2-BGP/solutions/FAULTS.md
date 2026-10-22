# Fehlerliste – Lab C5 – DMVPN Phase 3 mit IKEv2 und BGP mit dynamischen Nachbarn

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (S1)

- **Symptom:** S1 ist nicht im DMVPN: `show dmvpn` auf S1 zeigt den Hub nicht im Zustand UP. Das Underlay ist in Ordnung.
- **So findest du es:** `show crypto ikev2 sa` auf S1: keine SA. `debug crypto ikev2` auf dem Hub meldet beim IKE_SA_INIT, dass kein passender Vorschlag gefunden wurde (NO_PROPOSAL_CHOSEN). `show crypto ikev2 proposal` auf S1 nennt die DH-Gruppe 19, der Hub erwartet 14.
- **Ursache:** Die IKEv2-Vorschläge passen nicht zusammen. S1 bietet nur DH-Gruppe 19 an, der Hub akzeptiert nur 14. IKE scheitert, bevor überhaupt authentisiert wird.
- **Fix:** Unter `crypto ikev2 proposal PROP` auf S1 `no group 19` und `group 14`.
- **Eingebaut:**

```diff
- group 14
+ group 19
```

## Ticket 2 (S2)

- **Symptom:** S2 taucht in `show dmvpn` auf dem Hub nicht auf. `ping 198.51.100.1 source GigabitEthernet0/0` von S2 klappt.
- **So findest du es:** `show crypto ikev2 sa` auf S2 zeigt keine SA im Status READY. `debug crypto ikev2` auf dem Hub meldet beim IKE_AUTH einen Authentisierungsfehler. Der Keyring auf S2 enthält `DMVPN-Lab-Kei`.
- **Ursache:** Unterschiedlicher Pre-Shared Key: IKE_SA_INIT klappt, IKE_AUTH scheitert. Ohne IPsec-SA kommt die NHRP-Registrierung von S2 nicht beim Hub an.
- **Fix:** Im Keyring KR auf S2 unter `peer ANY` `pre-shared-key DMVPN-Lab-Key`.
- **Eingebaut:**

```diff
-  pre-shared-key DMVPN-Lab-Key
+  pre-shared-key DMVPN-Lab-Kei
```

## Ticket 3 (HUB)

- **Symptom:** Die Tunnel stehen und beide Spokes sind registriert, aber keiner hat eine BGP-Sitzung zum Hub. Die Spokes kennen 10.10.0.0/16 nicht.
- **So findest du es:** `show ip bgp summary` auf S1: Nachbar 172.16.0.1 in *Active*. Auf dem Hub erscheinen keine dynamischen Nachbarn, `show running-config | include listen` nennt 172.16.1.0/24. Die Tunneladressen liegen in 172.16.0.0/24.
- **Ursache:** Der Hub nimmt BGP-Verbindungen nur aus dem konfigurierten Bereich an. Die Spokes verbinden sich aus 172.16.0.0/24 und werden abgewiesen. Von sich aus baut der Hub keine Sitzung auf, er kennt die Spokes ja nicht.
- **Fix:** `no bgp listen range 172.16.1.0/24 peer-group SPOKES` und `bgp listen range 172.16.0.0/24 peer-group SPOKES` auf dem Hub.
- **Eingebaut:**

```diff
- bgp listen range 172.16.0.0/24 peer-group SPOKES
+ bgp listen range 172.16.1.0/24 peer-group SPOKES
```

## Ticket 4 (HUB)

- **Symptom:** Verkehr zwischen den Spokes läuft dauerhaft über den Hub: `traceroute 10.10.2.1 source Loopback1` von S1 zeigt auch beim dritten Versuch 172.16.0.1 als ersten Hop.
- **So findest du es:** `show ip route nhrp` auf S1 bleibt leer, `show ip nhrp` enthält keinen Eintrag für 10.10.2.0/24. `show running-config interface Tunnel0` auf dem Hub: `ip nhrp redirect` fehlt.
- **Ursache:** Ohne Redirect erfahren die Spokes nie, dass es einen direkten Weg gibt. Der Hub leitet weiter und bleibt im Pfad.
- **Fix:** `ip nhrp redirect` unter Tunnel0 auf dem Hub.
- **Eingebaut:**

```diff
- ip nhrp redirect
```

## Ticket 5 (S1)

- **Symptom:** Von S2 zu S1 entsteht nach dem ersten Paket ein direkter Weg, von S1 zu S2 bleibt der Verkehr beim Hub.
- **So findest du es:** Nach Verkehr in beide Richtungen zeigt `show ip route nhrp` auf S2 die Route 10.10.1.0/24 über 172.16.0.2, auf S1 aber keine Route zu 10.10.2.0/24. `show running-config interface Tunnel0` auf S1: `ip nhrp shortcut` fehlt.
- **Ursache:** Der Hub schickt S1 einen Redirect, aber ohne `ip nhrp shortcut` stellt S1 keine Auflösungsanfrage und installiert keine Shortcut-Route. Auf Anfragen von S2 antwortet S1 trotzdem, deshalb klappt die andere Richtung.
- **Fix:** `ip nhrp shortcut` unter Tunnel0 auf S1.
- **Eingebaut:**

```diff
- ip nhrp shortcut
```
