# 1. Was ist ein Netzwerk?

Ein Netzwerk verbindet Geräte, damit sie Daten austauschen können: Dein Laptop mit dem Drucker, dein Handy mit dem Internet, ein Server mit hundert Rechnern.

## Die vier Grundbausteine

| Baustein | Aufgabe | Beispiel |
|---|---|---|
| **Endgeräte** | Nutzen oder bieten Dienste an | PC, Handy, Server, Drucker, Kamera |
| **Verbindungen** | Transportieren die Signale | Kabel (Kupfer, Glasfaser), Funk (WLAN) |
| **Vermittler** | Leiten Daten dorthin, wo sie hinsollen | Switch, Router, Access Point |
| **Regeln (Protokolle)** | Legen fest, wie kommuniziert wird | Ethernet, IP, TCP, HTTP, DNS |

Ohne Protokolle wäre ein Netzwerk wie ein Postamt ohne Adressformat: Die Briefe gehen irgendwohin, aber nicht zuverlässig an den Richtigen.

## Netzgrößen

- **PAN**: Personal Area Network, wenige Meter (Bluetooth).
- **LAN**: Local Area Network, ein Gebäude oder Stockwerk. Dein Heimnetz ist ein LAN.
- **WAN**: Wide Area Network, verbindet Standorte über große Strecken. Das Internet ist das größte WAN.
- **WLAN**: Ein LAN über Funk.

## Client und Server

Ein **Server** stellt einen Dienst bereit (Webseite, Datei, E-Mail). Ein **Client** nutzt ihn. Dein Browser ist ein Client, `www.example.com` liegt auf einem Server. Dieselbe Maschine kann beides sein.

## Wie schickt ein Gerät etwas ab? (der Überblick)

```
Dein PC ──Kabel──> Switch ──Kabel──> Router ──> Internet ──> Server
```

1. Dein PC verpackt die Daten mit Adressen.
2. Der Switch bringt sie im selben Netz zum richtigen Port.
3. Der Router schickt sie in ein anderes Netz weiter.
4. Am Ziel wird alles wieder ausgepackt.

Genau diese Schritte lernst du in den nächsten Kapiteln im Detail.

## Merksatz

**Switch = innerhalb eines Netzes. Router = zwischen Netzen.**

## Selbsttest

1. Nenne die vier Grundbausteine eines Netzwerks.
2. Was ist der Unterschied zwischen Client und Server?
3. Ist dein Heimnetz ein LAN oder ein WAN?

<details><summary>Antworten</summary>

1. Endgeräte, Verbindungen, Vermittler, Protokolle.
2. Der Server bietet einen Dienst an, der Client nutzt ihn.
3. Ein LAN. Die Verbindung zum Provider ist Teil eines WAN.
</details>

Weiter: [2. Geräte und Kabel](02-Geraete-und-Kabel.md)
