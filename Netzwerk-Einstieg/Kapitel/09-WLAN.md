# 9. WLAN

## Grundlagen

- Standard: **IEEE 802.11**. Die Wi-Fi-Bezeichnungen: Wi-Fi 4 (n), Wi-Fi 5 (ac), Wi-Fi 6 (ax), Wi-Fi 6E (ax mit 6 GHz).
- **SSID** = Netzwerkname. **BSSID** = MAC-Adresse des Funkmoduls eines AP.
- Mehrere APs mit derselben SSID ergeben ein Netz zum Herumlaufen (**Roaming**).

## Frequenzbänder

| Band | Vorteil | Nachteil |
|---|---|---|
| 2,4 GHz | Reichweite, Wanddurchdringung | Nur 3 überlappungsfreie Kanäle (1, 6, 11), viele Störer |
| 5 GHz | Mehr Kanäle, schneller | Kürzere Reichweite |
| 6 GHz | Sehr viel freies Spektrum | Noch kürzere Reichweite, neuere Geräte |

## Probleme im WLAN

- **Interferenz**: Nachbar-WLAN auf demselben Kanal, Mikrowelle, Bluetooth.
- **Geteiltes Medium**: Alle Geräte teilen sich die Funkzeit.
- **Reichweite**: Wände, Metall und Wasser dämpfen.

## Sicherheit

| Verfahren | Bewertung |
|---|---|
| Offen | Unverschlüsselt |
| WEP | Kaputt, nie benutzen |
| WPA2-Personal (AES) | Üblich, braucht starkes Passwort |
| WPA2/3-Enterprise | Anmeldung pro Benutzer (802.1X, RADIUS) |
| WPA3 | Aktueller Standard |

Tipp fürs Heimnetz: WPA2 oder WPA3, langes Passwort, Gäste-WLAN getrennt, Router-Firmware aktuell halten, WPS aus.

## Unternehmens-WLAN

Viele Access Points werden zentral von einem **Wireless LAN Controller (WLC)** verwaltet. Die APs sind sogenannte *Lightweight APs* und sprechen mit dem Controller über **CAPWAP**.

## Selbsttest

1. Welche 2,4-GHz-Kanäle überlappen sich nicht?
2. Was ist eine SSID?
3. Warum ist WEP gefährlich?

<details><summary>Antworten</summary>

1. 1, 6 und 11.
2. Der Name des WLANs.
3. Die Verschlüsselung ist gebrochen und lässt sich in Minuten knacken.
</details>

Zurück: [8. TCP, UDP, DNS, DHCP, NAT](08-TCP-UDP-DNS-DHCP-NAT.md) · Weiter: [10. Sicherheit](10-Sicherheit-Grundlagen.md)
