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
| EIGRP Variance | welche Nachbarn bei `variance` Verkehr bekommen (Feasible Successor und FD kleiner als Variance × FD des Successors) und die kleinste passende Variance |
| OSPF Kosten | Interface-Kosten aus der Reference Bandwidth, Pfadkosten und Pfadwahl (auch ECMP) |
| HSRP Wahl und Preempt | Active und Standby bei gleichzeitigem Start, bei späterem Einschalten und nach einem Tracking-Ausfall (Priorität, höchste IP, Preempt) |
| QoS: DSCP und PHB | AF, EF und CS in Dezimal, Binär, IP Precedence und ToS-Byte umrechnen |

Der Lösungsweg rechnet mit den Zahlen der Aufgabe. `node test_rechentrainer.js` (Playwright) prüft alle Generatoren mit je 3000 Aufgaben und rechnet die neuen Aufgabentypen unabhängig nach. Bei BGP geht er die Kriterien der Reihe nach durch, bis eines entscheidet.

## Ticket-Trainer

Datei: [`ticket-trainer.html`](ticket-trainer.html). Die 155 Fehler-Tickets aus den Labs 01 bis 30 und 32 bis 36 als Quiz: Du liest das Symptom und wählst unter vier Ursachen die richtige. Die falschen Antworten stammen aus anderen Tickets desselben Labs, sie klingen also plausibel.

- **Hinweis zeigen** blendet ein, wie man die Ursache findet. Wer ihn nutzt, hat das Ticket noch nicht sicher gelöst.
- Nach der Antwort siehst du Ursache, Fix und den eingebauten Fehler als Diff.
- Der Browser merkt sich den Fortschritt. „Nur noch nicht sicher gelöste“ wiederholt alles, was falsch oder nur mit Hinweis gelöst war.

## So nutzt du sie

Den Rechentrainer am besten in kurzen Runden zwischendurch, 10 Minuten am Tag reichen. Den Ticket-Trainer nach jedem Lab für dessen Tickets und in der Prüfungsphase für alle. Wer ein Ticket ohne Hinweis lösen kann, kann es auch an der echten Konsole.
