# 5. IP-Adressen

> **Darum geht's:** Die IP-Adresse ist die Anschrift eines Geräts. Wie bei einer Postadresse gibt es einen Teil für die Straße (Netz) und einen für die Hausnummer (Host). Die Subnetzmaske sagt, wo die Grenze liegt.
>
> **Danach kannst du:** eine IPv4-Adresse in Netz- und Hostanteil zerlegen · private, besondere und öffentliche Adressen erkennen · erklären, wozu das Default Gateway dient.

## IPv4

- 32 Bit, geschrieben als vier Zahlen von 0 bis 255: `192.168.1.25`.
- Jede Zahl steht für 8 Bit (ein **Oktett**).
- Eine Adresse besteht aus einem **Netzanteil** und einem **Hostanteil**. Die **Subnetzmaske** sagt, wo die Grenze liegt.

```
IP:    192.168.1.25
Maske: 255.255.255.0   (= /24)
Netz:  192.168.1.0
Host:           .25
```

## Besondere Adressen

| Adresse | Bedeutung |
|---|---|
| `192.168.1.0` (Hostbits alle 0) | **Netzadresse** |
| `192.168.1.255` (Hostbits alle 1) | **Broadcast** |
| `127.0.0.1` | Loopback, „ich selbst“ |
| `169.254.x.x` | APIPA: Kein DHCP gefunden |
| `224.0.0.0 – 239.255.255.255` | Multicast |

## Private und öffentliche Adressen

Private Bereiche (RFC 1918) werden im Internet nicht geroutet:

- `10.0.0.0/8`
- `172.16.0.0/12` (172.16.0.0 bis 172.31.255.255)
- `192.168.0.0/16`

Dein Heimnetz nutzt eine private Adresse; der Router übersetzt sie per **NAT** in die öffentliche Adresse des Providers.

## Das Default Gateway

Ein Host schickt Pakete für fremde Netze an das **Default Gateway** (meist den Router, `192.168.1.1`). Ohne Gateway erreichst du nur dein eigenes Subnetz.

## IPv6 in Kürze

- 128 Bit, hexadezimal: `2001:db8:0:1::25`.
- Kein Broadcast, kein NAT nötig, riesiger Adressraum.
- `fe80::/10` ist Link-Local (jedes Interface hat so eine).
- Typisches LAN-Präfix: `/64`.

## Adressen vergeben

- **Statisch**: von Hand eingetragen (Server, Router).
- **Dynamisch per DHCP**: automatisch (Clients).

## Das Wichtigste in Kürze

- Eine IPv4-Adresse hat 32 Bit, die Maske trennt Netz und Host.
- Privat sind 10.0.0.0/8, 172.16.0.0/12 und 192.168.0.0/16. Im Internet braucht es NAT.
- Für alles außerhalb des eigenen Netzes fragt ein Gerät sein Default Gateway.

## Selbsttest

1. Welche Adresse ist privat: `172.20.1.1` oder `172.40.1.1`?
2. Was bedeutet `169.254.x.x`?
3. Wozu dient das Default Gateway?

<details><summary>Antworten</summary>

1. **172.20.1.1.** Der private Bereich 172.16.0.0/12 reicht von 172.16 bis 172.31. 172.40 liegt außerhalb.
2. **Das Gerät hat keine Adresse per DHCP bekommen und sich selbst eine gegeben (APIPA).** Damit erreicht es nur Geräte im selben Segment, die ebenfalls eine 169.254-Adresse haben.
3. **Es ist der Ausgang in andere Netze.** Alles, was nicht im eigenen Subnetz liegt, schickt der Host an sein Gateway, meist den Router.

</details>

Zurück: [4. Ethernet und Switch](04-Ethernet-MAC-Switch.md) · Weiter: [6. Subnetting leicht gemacht](06-Subnetting.md)
