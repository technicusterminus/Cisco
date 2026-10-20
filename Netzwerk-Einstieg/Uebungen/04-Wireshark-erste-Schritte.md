# Übung 4: Wireshark, ein Paket sehen

Wireshark ist kostenlos (wireshark.org). Starte die Aufzeichnung auf deiner aktiven Netzwerkkarte. Erfasse nur Verkehr in deinem eigenen Netz und auf eigenen Geräten.

## Aufgabe A: Ping aufzeichnen

1. Filter setzen: `icmp`.
2. In einem Terminal `ping 8.8.8.8` ausführen.
3. Klicke auf ein „Echo (ping) request“-Paket und öffne die Details.

Finde die Schichten:

| Schicht | Wo im Paket | Was du lesen kannst |
|---|---|---|
| Layer 2 | Ethernet II | Quell- und Ziel-MAC |
| Layer 3 | Internet Protocol | Quell-/Ziel-IP, TTL |
| ICMP | Internet Control Message | Typ 8 (Request), Typ 0 (Reply) |

**Fragen:** Wem gehört die Ziel-MAC? (Tipp: Es ist nicht 8.8.8.8, sondern dein Gateway.) Warum?

## Aufgabe B: DNS

1. Filter `dns`.
2. `nslookup www.example.com` ausführen.
3. Finde Query und Response. Welche UDP-Ports siehst du?

## Aufgabe C: TCP-Handshake

1. Filter `tcp.flags.syn==1`.
2. Rufe im Browser eine Webseite auf.
3. Suche SYN, SYN/ACK, ACK (Rechtsklick → Follow → TCP Stream).

<details><summary>Lösungshinweise</summary>

- Die Ziel-MAC ist die deines Gateways, weil 8.8.8.8 in einem anderen Netz liegt.
- DNS: Quellport zufällig, Zielport 53 (UDP).
- Handshake: SYN → SYN/ACK → ACK, danach erst TLS und HTTP.
</details>
