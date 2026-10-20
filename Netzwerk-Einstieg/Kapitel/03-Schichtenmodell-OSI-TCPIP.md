# 3. Das Schichtenmodell (OSI und TCP/IP)

Netzwerkkommunikation ist kompliziert. Deshalb teilt man sie in **Schichten**: Jede Schicht hat eine klare Aufgabe und redet nur mit der Schicht darüber und darunter.

## OSI-Modell (sieben Schichten)

| Nr. | Schicht | Aufgabe | Beispiele | Dateneinheit |
|---|---|---|---|---|
| 7 | Anwendung | Schnittstelle zum Programm | HTTP, DNS, SSH | Daten |
| 6 | Darstellung | Format, Verschlüsselung | TLS, JSON | Daten |
| 5 | Sitzung | Verbindungen verwalten | – | Daten |
| 4 | Transport | Ende-zu-Ende, Ports | TCP, UDP | Segment |
| 3 | Vermittlung | Adressierung, Routing | IP, ICMP | Paket |
| 2 | Sicherung | Nachbar zu Nachbar, MAC | Ethernet, WLAN | Frame |
| 1 | Bitübertragung | Signale, Kabel | Kupfer, Glasfaser | Bits |

**Eselsbrücke (von oben):** *Alle Deutschen Studenten Trinken Verdammt Selten Bier* (Anwendung, Darstellung, Sitzung, Transport, Vermittlung, Sicherung, Bitübertragung).

## TCP/IP-Modell (vier bis fünf Schichten)

In der Praxis nutzt man TCP/IP:

| TCP/IP | OSI |
|---|---|
| Anwendung | 5–7 |
| Transport | 4 |
| Internet | 3 |
| Netzzugang | 1–2 |

## Kapselung (Encapsulation)

Beim Senden packt jede Schicht ihren Header (Absender-Info) dazu, wie Briefumschläge ineinander:

```
Daten
  └─ + TCP-Header (Ports)            → Segment
       └─ + IP-Header (IP-Adressen)  → Paket
            └─ + Ethernet-Header (MAC) + Trailer → Frame
                 └─ in Bits auf dem Kabel
```

Beim Empfänger wird in umgekehrter Reihenfolge ausgepackt (De-Kapselung).

## Wozu das Ganze?

Zum Fehlersuchen: Wenn eine Webseite nicht lädt, gehst du die Schichten durch.

- Layer 1: Kabel steckt? Link-LED an?
- Layer 2: Switch-Port aktiv, richtiges VLAN?
- Layer 3: IP-Adresse, Gateway, Route?
- Layer 4: Port erreichbar, Firewall?
- Layer 7: Dienst läuft, DNS-Name stimmt?

## Selbsttest

1. Auf welcher Schicht arbeiten Switches? Und Router?
2. Wie heißt die Dateneinheit auf Layer 2?
3. Auf welcher Schicht wird TCP eingesetzt?

<details><summary>Antworten</summary>

1. Switch: Layer 2, Router: Layer 3.
2. Frame.
3. Layer 4, Transport.
</details>

Zurück: [2. Geräte und Kabel](02-Geraete-und-Kabel.md) · Weiter: [4. Ethernet, MAC und Switch](04-Ethernet-MAC-Switch.md)
