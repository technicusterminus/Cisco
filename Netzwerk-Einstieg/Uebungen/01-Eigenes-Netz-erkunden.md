# Übung 1: Dein eigenes Netz erkunden

## Aufgabe

Finde heraus, wie dein Rechner im Netz hängt.

**Windows:** Eingabeaufforderung öffnen, `ipconfig /all`.
**macOS/Linux:** Terminal öffnen, `ifconfig` bzw. `ip addr`, und für Gateway/DNS `netstat -rn` bzw. `ip route` und `cat /etc/resolv.conf`.

Trage ein:

| Frage | Dein Wert |
|---|---|
| Deine IPv4-Adresse | |
| Subnetzmaske | |
| Präfixlänge (/…) | |
| Default Gateway | |
| DNS-Server | |
| MAC-Adresse | |
| DHCP aktiv? | |

## Denkfragen

1. Ist deine Adresse privat? Aus welchem Bereich?
2. Wie viele Hosts passen in dein Subnetz?
3. Welche Netzadresse und welche Broadcastadresse hat dein Subnetz?
4. Wem gehört der Hersteller-Teil deiner MAC? (Suche nach „MAC OUI lookup“.)

<details><summary>Lösungshinweise</summary>

1. Meist `192.168.x.x` oder `10.x.x.x`, also privat nach RFC 1918.
2. Bei /24 sind es 254.
3. Bei `192.168.1.25/24`: Netz `192.168.1.0`, Broadcast `192.168.1.255`.
4. Der Hersteller deiner Netzwerkkarte oder deines WLAN-Chips.
</details>
