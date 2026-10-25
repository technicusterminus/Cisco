# Trainer

Zwei Übungsprogramme, beide als einzelne HTML-Datei. Im Browser öffnen, sie laufen offline.

## Rechentrainer

Datei: [`encor-rechentrainer.html`](encor-rechentrainer.html). Zufallsaufgaben, bei denen du rechnen oder ableiten musst, statt dich an eine Frage zu erinnern. Jede Aufgabe ist neu.

| Aufgabentyp | Was du bestimmst |
|---|---|
| BGP Best Path | besten Pfad und das entscheidende Kriterium aus einer Tabelle mit Weight, LocPrf, AS-Pfad, Origin, MED, Typ, IGP-Metrik, Alter und Router-ID |
| STP | Root Bridge, Root Port eines Switches und den blockierten Port in einem Dreieck oder Ring |
| OSPF DR/BDR | DR und BDR aus Priorität und Router-ID, auch mit einem Router, der später dazukommt |
| OSPF Areatypen und LSAs | welche LSA-Typen es in welcher Area gibt, wer sie erzeugt und woher die Default-Route kommt |
| EIGRP Feasible Successor | Successor und Feasible Successors aus `show ip eigrp topology` |
| QoS: DSCP und PHB | AF, EF und CS in Dezimal, Binär, IP Precedence und ToS-Byte umrechnen |

Der Lösungsweg rechnet mit den Zahlen der Aufgabe. Bei BGP geht er die Kriterien der Reihe nach durch, bis eines entscheidet.

## Ticket-Trainer

Datei: [`ticket-trainer.html`](ticket-trainer.html). Die 134 Fehler-Tickets aus den Labs als Quiz: Du liest das Symptom und wählst unter vier Ursachen die richtige. Die falschen Antworten stammen aus anderen Tickets desselben Labs, sie klingen also plausibel.

- **Hinweis zeigen** blendet ein, wie man die Ursache findet. Wer ihn nutzt, hat das Ticket noch nicht sicher gelöst.
- Nach der Antwort siehst du Ursache, Fix und den eingebauten Fehler als Diff.
- Der Browser merkt sich den Fortschritt. „Nur noch nicht sicher gelöste“ wiederholt alles, was falsch oder nur mit Hinweis gelöst war.

## So nutzt du sie

Den Rechentrainer am besten in kurzen Runden zwischendurch, 10 Minuten am Tag reichen. Den Ticket-Trainer nach jedem Lab für dessen Tickets und in der Prüfungsphase für alle. Wer ein Ticket ohne Hinweis lösen kann, kann es auch an der echten Konsole.
