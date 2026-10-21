# Übung 1: Dein eigenes Netz erkunden

**Ziel:** Du findest Adresse, Maske, Gateway, DNS-Server und MAC deines Rechners und ordnest sie ein.

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

1. **Fast immer privat, meist aus 192.168.0.0/16 oder 10.0.0.0/8.** Dein Router übersetzt sie per NAT in seine öffentliche Adresse.
2. **Bei /24 sind es 254 Hosts.** 8 Hostbits ergeben 256 Adressen, minus Netzadresse und Broadcast.
3. **Bei 192.168.1.25/24: Netz 192.168.1.0, Broadcast 192.168.1.255.** Netz = alle Hostbits 0, Broadcast = alle Hostbits 1.
4. **Der Hersteller deiner Netzwerkkarte oder deines WLAN-Chips.** Die ersten drei Byte der MAC (OUI) sind ihm fest zugeteilt. Manche Geräte nutzen im WLAN aus Datenschutzgründen eine zufällige MAC, dann findest du keinen Hersteller.

</details>
