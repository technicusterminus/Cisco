# 2. Geräte und Kabel

> **Darum geht's:** Jedes Gerät im Netz hat eine bestimmte Aufgabe, und jedes Kabel hat Grenzen. Wer das weiß, erkennt viele Probleme schon beim Hinsehen.
>
> **Danach kannst du:** Switch, Router, Access Point, Firewall und Modem auseinanderhalten · Kupfer, Multimode- und Singlemode-Faser passend einsetzen · Duplex und PoE erklären.

## Die wichtigsten Geräte

| Gerät | Was es tut | Arbeitet mit |
|---|---|---|
| **Hub** (veraltet) | Wiederholt jedes Signal an alle Ports | Bits |
| **Switch** | Leitet Frames gezielt anhand von MAC-Adressen weiter | MAC-Adressen |
| **Router** | Verbindet verschiedene Netze, wählt Wege | IP-Adressen |
| **Access Point (AP)** | Verbindet WLAN-Geräte mit dem Kabelnetz | Funk und MAC |
| **Firewall** | Erlaubt oder blockiert Verkehr nach Regeln | IP, Ports, Anwendungen |
| **Modem** | Wandelt Signale des Providers (DSL, Kabel, Glasfaser) | Signale |

Dein Heimrouter ist meistens alles in einem: Modem, Router, Switch, WLAN-Access-Point und Firewall.

## Kabel

### Kupfer (Twisted Pair)

- Der Standard im Büro und zu Hause: das Netzwerkkabel mit RJ45-Stecker.
- Kategorien: Cat5e (1 Gbit/s), Cat6 (bis 10 Gbit/s auf kurzer Strecke), Cat6a (10 Gbit/s bis 100 m).
- **Maximale Länge: 100 Meter** pro Segment.
- Anfällig für Störungen, günstig, einfach.

### Glasfaser

- Überträgt Licht, nicht Strom: störungsfrei und über große Distanzen.
- **Multimode**: dicker Kern, kurze Strecken (Gebäude, Rechenzentrum).
- **Singlemode**: dünner Kern, viele Kilometer.
- Anschluss oft über steckbare Module (SFP).

### Funk

WLAN (802.11) überträgt auf 2,4, 5 oder 6 GHz. Bequem, aber geteilt, störanfälliger und weniger sicher als Kabel, wenn es schlecht konfiguriert ist.

## Straight-through oder Crossover?

- **Straight-through** zwischen *unterschiedlichen* Geräten (PC ↔ Switch).
- **Crossover** zwischen *gleichen* Geräten (Switch ↔ Switch).
- Heute erledigt **Auto-MDIX** das meist automatisch. Du brauchst fast immer nur ein normales Kabel.

## Geschwindigkeiten

| Name | Rate |
|---|---|
| Fast Ethernet | 100 Mbit/s |
| Gigabit Ethernet | 1 Gbit/s |
| 10 Gigabit Ethernet | 10 Gbit/s |

## Duplex

- **Vollduplex**: Senden und Empfangen gleichzeitig (heute normal).
- **Halbduplex**: abwechselnd (Hubs, ältere Technik).
- Stimmen die Einstellungen an beiden Enden nicht überein (**Duplex-Mismatch**), wird die Verbindung sehr langsam.

## PoE

Power over Ethernet versorgt Geräte wie Access Points, IP-Telefone und Kameras über das Netzwerkkabel mit Strom. Eine Steckdose weniger.

## Das Wichtigste in Kürze

- Switch arbeitet mit MAC-Adressen, Router mit IP-Adressen. Der Heimrouter vereint beides plus WLAN und Firewall.
- Kupfer reicht 100 m, Multimode einige hundert Meter, Singlemode viele Kilometer.
- Stimmt das Duplex an beiden Enden nicht überein, wird der Link langsam, obwohl er funktioniert.

## Selbsttest

1. Wie lang darf ein Kupferkabel zwischen Switch und PC sein?
2. Wann braucht man Singlemode statt Multimode?
3. Wofür ist PoE gut?

<details><summary>Antworten</summary>

1. **Höchstens 100 Meter.** Danach wird das Signal zu schwach und zu störanfällig.
2. **Bei langen Strecken, also über mehrere Kilometer.** Singlemode hat einen sehr dünnen Kern, das Licht läuft fast ohne Streuung und kommt weit. Multimode reicht nur einige hundert Meter.
3. **Es liefert Strom über das Netzwerkkabel.** Access Points, IP-Telefone und Kameras brauchen dann keine eigene Steckdose.

</details>

Zurück: [1. Was ist ein Netzwerk?](01-Was-ist-ein-Netzwerk.md) · Weiter: [3. Das Schichtenmodell](03-Schichtenmodell-OSI-TCPIP.md)
