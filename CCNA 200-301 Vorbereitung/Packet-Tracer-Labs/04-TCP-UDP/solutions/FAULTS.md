# Fehlerliste – Lab 04 – TCP und UDP: Verbindungsaufbau, Ports, Dienste

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Webseite per IP (`http://10.4.2.10`) lädt, per Name (`www.lab.local`) nicht; `nslookup` läuft in ein Timeout.
- **So findest du es:** `show access-lists` auf R1 zeigt `permit tcp … eq domain`. Der Zähler bleibt bei 0, obwohl `nslookup` läuft.
- **Ursache:** Die ACL lässt DNS über TCP/53 statt UDP/53 zu: normale Anfragen (UDP) werden vom impliziten Deny verworfen.
- **Fix:** `permit udp … eq 53` setzen (optional zusätzlich TCP/53 für große Antworten).
- **Eingebaut:**

```diff
-  permit udp 10.4.1.0 0.0.0.255 host 10.4.2.10 eq 53
+  permit tcp 10.4.1.0 0.0.0.255 host 10.4.2.10 eq 53
```

## Ticket 2 (R1)

- **Symptom:** Ping und DNS gehen, die Webseite lädt nicht (Browser: Timeout).
- **So findest du es:** `show access-lists` auf R1 zeigt `eq 8080`. Der Browser fragt aber Port 80 an.
- **Ursache:** HTTP-Port falsch: die ACL erlaubt TCP/8080 statt TCP/80.
- **Fix:** `eq 80` (oder `eq www`) setzen.
- **Eingebaut:**

```diff
-  permit tcp 10.4.1.0 0.0.0.255 host 10.4.2.10 eq 80
+  permit tcp 10.4.1.0 0.0.0.255 host 10.4.2.10 eq 8080
```

## Ticket 3 (PC2)

- **Symptom:** Auf PC2 funktioniert `www.lab.local` nicht, auf PC1 schon.
- **So findest du es:** `ipconfig /all` auf PC2 zeigt den DNS-Server 10.4.2.11, auf PC1 10.4.2.10.
- **Ursache:** PC2 fragt einen nicht existierenden DNS-Server (10.4.2.11).
- **Fix:** DNS auf 10.4.2.10 setzen.
- **Eingebaut:** Endgerät-Einstellung `dns` = `10.4.2.11`

