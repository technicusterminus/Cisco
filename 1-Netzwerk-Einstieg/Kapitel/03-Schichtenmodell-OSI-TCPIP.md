# 3. Das Schichtenmodell (OSI und TCP/IP)

> **Darum geht's:** Netzwerk ist viel auf einmal. Das Schichtenmodell teilt es in Stockwerke: Jedes Stockwerk erledigt eine Aufgabe und verlässt sich auf das darunter. So kannst du Probleme Stockwerk für Stockwerk suchen.
>
> **Danach kannst du:** die sieben OSI-Schichten und ihre Aufgaben aufzählen · Geräte und Protokolle einer Schicht zuordnen · erklären, wie Daten beim Senden verpackt werden.

Jede **Schicht** hat eine klare Aufgabe und redet nur mit der Schicht darüber und darunter.

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

## Das Wichtigste in Kürze

- OSI hat sieben Schichten, TCP/IP fasst sie zu vier zusammen.
- Beim Senden packt jede Schicht einen eigenen Umschlag (Header) um die Daten: Segment, Paket, Frame, Bits.
- Bei der Fehlersuche gehst du die Schichten von unten nach oben durch.

## Selbsttest

1. Auf welcher Schicht arbeiten Switches? Und Router?
2. Wie heißt die Dateneinheit auf Layer 2?
3. Auf welcher Schicht wird TCP eingesetzt?

<details><summary>Antworten</summary>

1. **Switches auf Layer 2, Router auf Layer 3.** Der Switch entscheidet nach der MAC-Adresse, der Router nach der IP-Adresse.
2. **Frame.** Auf Layer 3 heißt sie Paket, auf Layer 4 Segment.
3. **Auf Layer 4, der Transportschicht.** Dort sorgen TCP und UDP mit Portnummern dafür, dass die Daten beim richtigen Programm ankommen.

</details>

Zurück: [2. Geräte und Kabel](02-Geraete-und-Kabel.md) · Weiter: [4. Ethernet, MAC und Switch](04-Ethernet-MAC-Switch.md)
