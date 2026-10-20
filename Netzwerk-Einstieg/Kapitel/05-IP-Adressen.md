# 5. IP-Adressen

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

## Selbsttest

1. Welche Adresse ist privat: `172.20.1.1` oder `172.40.1.1`?
2. Was bedeutet `169.254.x.x`?
3. Wozu dient das Default Gateway?

<details><summary>Antworten</summary>

1. `172.20.1.1`. Privat ist nur 172.16–172.31.
2. Der Host hat keine Adresse per DHCP bekommen (APIPA).
3. Es leitet Pakete in andere Netze weiter.
</details>

Zurück: [4. Ethernet und Switch](04-Ethernet-MAC-Switch.md) · Weiter: [6. Subnetting leicht gemacht](06-Subnetting.md)
