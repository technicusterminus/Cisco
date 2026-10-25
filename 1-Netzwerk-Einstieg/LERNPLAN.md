# Lernplan: 4 Wochen vom Einsteiger zum Start in die CCNA

Annahme: **etwa 5 Stunden pro Woche** (4 × 15 Minuten Karten, 2 Abende à 1 Stunde, 1 Block am Wochenende).

| Woche | Kapitel | Übungen | Anki-Filter | Quiz |
|---|---|---|---|---|
| 1 | [1 Netzwerk](Kapitel/01-Was-ist-ein-Netzwerk.md), [2 Geräte, Kabel](Kapitel/02-Geraete-und-Kabel.md), [3 Schichtenmodell](Kapitel/03-Schichtenmodell-OSI-TCPIP.md) | [1 Eigenes Netz](Uebungen/01-Eigenes-Netz-erkunden.md) | `tag:Kapitel::01 or tag:Kapitel::02 or tag:Kapitel::03` | Block 1 |
| 2 | [4 Ethernet, Switch](Kapitel/04-Ethernet-MAC-Switch.md), [5 IP-Adressen](Kapitel/05-IP-Adressen.md), [6 Subnetting](Kapitel/06-Subnetting.md) | [2 Ping, Traceroute](Uebungen/02-Ping-und-Traceroute.md), [3 DNS, ARP](Uebungen/03-DNS-und-ARP.md) | `tag:Kapitel::04 or tag:Kapitel::05 or tag:Kapitel::06` | Block 2 |
| 3 | [7 Routing](Kapitel/07-Router-und-Routing.md), [8 TCP, UDP, DNS, DHCP, NAT](Kapitel/08-TCP-UDP-DNS-DHCP-NAT.md), [9 WLAN](Kapitel/09-WLAN.md) | [4 Wireshark](Uebungen/04-Wireshark-erste-Schritte.md) | `tag:Kapitel::07 or tag:Kapitel::08 or tag:Kapitel::09` | Block 3 und 4 |
| 4 | [10 Sicherheit](Kapitel/10-Sicherheit-Grundlagen.md), [11 Fehlersuche](Kapitel/11-Fehlersuche.md), [12 Cisco-CLI](Kapitel/12-Cisco-CLI-und-Weg-zur-CCNA.md) | [5 Packet Tracer](Uebungen/05-Packet-Tracer-Erstes-Netz.md) | alle Kapitel, nur fällige Karten | Block 5, danach das gesamte Quiz |

## Woran du merkst, dass eine Woche sitzt

| Woche | Danach kannst du … | Selbsttest |
|---|---|---|
| 1 | Geräte, Kabel und die OSI-Schichten erklären. | Auf welcher Schicht arbeitet ein Switch, und warum? |
| 2 | Adressen lesen und einfache Subnetze rechnen. | Netz und Broadcast von 192.168.5.200/28? |
| 3 | Routing-Entscheidungen erklären und TCP, UDP, DNS, DHCP und NAT einordnen. | Welche Route gewinnt für 10.1.1.5: /16 oder /24? |
| 4 | Eine Störung mit Ping eingrenzen und ein kleines Netz in Packet Tracer bauen. | 8.8.8.8 antwortet, ein Name nicht. Woran liegt es? |

Klappt eine Antwort nicht, lies den Abschnitt „Das Wichtigste in Kürze“ des Kapitels noch einmal und wiederhole die passenden Karten.

## Täglich

- 15 Minuten Anki, auch wenn du an dem Tag nichts Neues liest.
- In Woche 2 zusätzlich täglich 10 Minuten Subnetting-Training mit dem [Subnetting-Trainer](../2-CCNA-200-301/Trainer/subnetting-trainer.html).

## Bereit für die CCNA?

Du kannst einsteigen, wenn du

- ein Subnetz mit Blockgrößen-Methode in unter einer Minute bestimmst,
- die fünf Schritte der Fehlersuche und die Ping-Reihenfolge aus dem Kopf kannst,
- das Quiz zweimal mit mindestens 80 % schaffst und
- das Packet-Tracer-Netz aus Übung 5 ohne Anleitung baust.

Dann geht es weiter mit dem [CCNA-Lernpaket](../2-CCNA-200-301/) und seinem [8-Wochen-Lernplan](../2-CCNA-200-301/LERNPLAN.md).
