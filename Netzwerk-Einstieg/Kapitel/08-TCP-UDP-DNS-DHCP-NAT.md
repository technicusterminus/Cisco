# 8. TCP, UDP, DNS, DHCP und NAT

> **Darum geht's:** Die IP-Adresse bringt ein Paket zum richtigen Rechner. Dort muss es noch zum richtigen Programm. Dafür gibt es Ports, und dazu kommen die Helfer, die das Netz im Alltag benutzbar machen: DNS, DHCP und NAT.
>
> **Danach kannst du:** die wichtigsten Ports und ihr Protokoll nennen · entscheiden, wann TCP und wann UDP passt · erklären, was DNS, DHCP und NAT jeweils tun.

## Ports

Die IP-Adresse findet den Rechner, der **Port** findet das Programm darauf. Ports gehen von 0 bis 65535.

| Dienst | Port | Protokoll |
|---|---|---|
| HTTP | 80 | TCP |
| HTTPS | 443 | TCP |
| SSH | 22 | TCP |
| Telnet | 23 | TCP |
| SMTP (Mail senden) | 25 | TCP |
| DNS | 53 | UDP (und TCP) |
| DHCP | 67 / 68 | UDP |
| TFTP | 69 | UDP |
| NTP | 123 | UDP |
| SNMP | 161 / 162 | UDP |

## TCP oder UDP?

| | TCP | UDP |
|---|---|---|
| Verbindung | Ja (Handshake) | Nein |
| Zuverlässig | Ja (Bestätigung, Wiederholung) | Nein |
| Geschwindigkeit | Etwas langsamer | Schnell, wenig Overhead |
| Typisch für | Web, Mail, SSH, Dateien | DNS, Sprache, Video, Streaming |

Der **TCP-Handshake**: SYN → SYN/ACK → ACK.

## DNS: Namen statt Zahlen

DNS übersetzt `www.example.com` in eine IP-Adresse. Ohne DNS müsstest du dir Adressen merken. Wichtige Einträge: **A** (IPv4), **AAAA** (IPv6), **MX** (Mail), **CNAME** (Alias).

Test: `nslookup www.example.com`.

## DHCP: Adressen automatisch

Statt jedem Gerät von Hand eine Adresse zu geben, verteilt der DHCP-Server Adresse, Maske, Gateway und DNS. Ablauf **DORA**:

1. **D**iscover: Client ruft per Broadcast „Gibt es einen DHCP-Server?“
2. **O**ffer: Server bietet eine Adresse an.
3. **R**equest: Client nimmt sie an.
4. **A**cknowledge: Server bestätigt.

Bekommt ein Rechner keine Antwort, vergibt er sich selbst `169.254.x.x`.

## NAT: Ein Internetanschluss für viele Geräte

Private Adressen sind im Internet nicht erlaubt. Der Router ersetzt deshalb die private Quelladresse durch seine öffentliche und merkt sich die Zuordnung über Ports (**PAT**). Antworten werden so wieder dem richtigen Gerät zugeordnet.

```
PC 192.168.1.10:49152  →  Router  →  Server  (Quelle: 203.0.113.5:1025)
```

## Das Wichtigste in Kürze

- IP-Adresse = Haus, Port = Wohnung darin.
- TCP ist zuverlässig mit Handshake, UDP schnell ohne Garantie.
- DNS übersetzt Namen, DHCP verteilt Adressen, NAT teilt eine öffentliche Adresse für viele Geräte.

## Selbsttest

1. Wofür steht Port 443?
2. Warum nutzt Sprache meist UDP?
3. Was bedeutet DORA?

<details><summary>Antworten</summary>

1. **HTTPS, also verschlüsseltes Web.** Unverschlüsseltes HTTP nutzt Port 80.
2. **Weil ein verspätetes Sprachpaket wertlos ist.** TCP würde verlorene Pakete neu senden, und die kämen zu spät. Bei Sprache ist eine kleine Lücke besser als Verzögerung.
3. **Discover, Offer, Request, Acknowledge: der Ablauf, mit dem ein Gerät per DHCP eine Adresse bekommt.**

</details>

Zurück: [7. Router und Routing](07-Router-und-Routing.md) · Weiter: [9. WLAN](09-WLAN.md)
