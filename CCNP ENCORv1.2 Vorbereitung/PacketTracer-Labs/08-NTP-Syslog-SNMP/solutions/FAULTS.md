# Fehlerliste – Lab 08 – NTP, Syslog und SNMPv3

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Weder R2 noch R3 synchronisieren; `show ntp associations` zeigt auf R2 `~` und Stratum 16 (R1 selbst hat keine Quelle).
- **Ursache:** R1 hat keine Zeitquelle und ist unsynchronisiert, der `ntp master`-Befehl fehlt.
- **Fix:** `ntp master 3` auf R1 setzen (und eine Weile warten).
- **Eingebaut:**

```diff
- ntp master 3
```

## Ticket 2 (R2)

- **Symptom:** R2 hat eine Assoziation mit R1, aber sie wird nie als Sys.Peer gewählt; `authenticated` steht auf `no`.
- **Ursache:** Key 1 ist definiert, aber nicht als `trusted-key` freigegeben: Pakete mit dieser Key-ID werden nicht akzeptiert.
- **Fix:** `ntp trusted-key 1` auf R2.
- **Eingebaut:**

```diff
- ntp trusted-key 1
```

## Ticket 3 (R3)

- **Symptom:** R3 bleibt unsynchronisiert, `show ntp associations` zeigt Reach 0 zu 10.0.23.10.
- **Ursache:** Tippfehler in der Server-Adresse.
- **Fix:** Server-Adresse auf 10.0.23.1 korrigieren.
- **Eingebaut:**

```diff
- ntp server 10.0.23.1 key 1
+ ntp server 10.0.23.10 key 1
```

## Ticket 4 (R2)

- **Symptom:** In `show logging` auf R2 fehlen Link-Up-Meldungen (`%LINEPROTO-5-UPDOWN`), obwohl der Link geflappt hat.
- **Ursache:** Level `errors` (3) blendet Meldungen der Severity 5 (notifications) aus.
- **Fix:** Level auf `informational` oder `notifications` setzen.
- **Eingebaut:**

```diff
- logging buffered 16384 informational
+ logging buffered 16384 errors
```

