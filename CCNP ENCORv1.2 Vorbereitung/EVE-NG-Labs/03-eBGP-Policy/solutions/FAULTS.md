# Fehlerliste – Lab 03 – eBGP Dual-Homing und Policy

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Die Session R1–R2 kommt nicht hoch (Idle/Active), das Log meldet eine falsche Nachbar-AS.
- **Ursache:** Auf R1 ist die erwartete Remote-AS 65011 statt 65010 eingetragen.
- **Fix:** `remote-as 65010` setzen.
- **Eingebaut:**

```diff
- neighbor 10.12.0.2 remote-as 65010
+ neighbor 10.12.0.2 remote-as 65011
```

## Ticket 2 (R1)

- **Symptom:** R1 wählt zu 198.51.100.0/24 den Pfad über ISP-B, obwohl ISP-A bevorzugt sein soll (LocPrf überall 100).
- **Ursache:** Route-Map FROM-ISPA ist nicht auf die Session angewendet; bei Gleichstand gewinnt die niedrigere Router-ID (3.3.3.3).
- **Fix:** `neighbor 10.12.0.2 route-map FROM-ISPA in`, danach `clear ip bgp 10.12.0.2 soft in`.
- **Eingebaut:**

```diff
-  neighbor 10.12.0.2 route-map FROM-ISPA in
```

## Ticket 3 (R1)

- **Symptom:** Auf R2 erscheint 198.51.100.0/24 zusätzlich mit AS-Path `65001 65020 65100`, R1 wird zum Transit.
- **Ursache:** Der Ausgangsfilter zu ISP-A fehlt; R1 reicht ISP-B-Routen weiter.
- **Fix:** `neighbor 10.12.0.2 route-map TO-ISPA out` setzen.
- **Eingebaut:**

```diff
-  neighbor 10.12.0.2 route-map TO-ISPA out
```

## Ticket 4 (R4)

- **Symptom:** Weder R2 noch R3 lernen 198.51.100.0/24, R1 hat keine Internet-Route.
- **Ursache:** Das `network`-Statement passt (Maske /25) nicht zur Route in der RIB (/24), also wird nichts angekündigt.
- **Fix:** Maske auf 255.255.255.0 korrigieren.
- **Eingebaut:**

```diff
-  network 198.51.100.0 mask 255.255.255.0
+  network 198.51.100.0 mask 255.255.255.128
```

## Ticket 5 (R1)

- **Symptom:** Der Kundenbereich 203.0.113.0/24 ist aus dem Internet nicht erreichbar, R2/R3 sehen kein Präfix von R1.
- **Ursache:** Die Null0-Anker-Route (/25) stimmt nicht mit dem `network`-Statement (/24) überein.
- **Fix:** Anker-Route auf /24 korrigieren.
- **Eingebaut:**

```diff
- ip route 203.0.113.0 255.255.255.0 Null0
+ ip route 203.0.113.0 255.255.255.128 Null0
```

