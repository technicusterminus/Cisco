# Trainer

Zwei Übungsprogramme, beide als einzelne HTML-Datei. Im Browser öffnen, sie laufen offline.

## Rechentrainer

Datei: [`ccie-rechentrainer.html`](ccie-rechentrainer.html). Zufallsaufgaben, bei denen du rechnen musst, statt dich an eine Antwort zu erinnern. Jede Aufgabe ist neu, und der Lösungsweg rechnet mit den Zahlen der Aufgabe.

| Aufgabentyp | Was du bestimmst |
|---|---|
| MTU und MSS | Overlay-MTU und TCP-MSS bei GRE, VXLAN und MPLS mit einem bis drei Labels |
| OSPF-Kosten und Pfadwahl | Kosten pro Pfad bei beliebiger Referenzbandbreite und den gewählten Pfad, auch bei gleichen Kosten |
| EIGRP-Metrik | kleinste Bandbreite, Delay-Summe und die Metrik mit Standard-K-Werten |
| Summarization | die kürzeste Zusammenfassung mehrerer /24-Netze und ob sie Netze mit abdeckt, die nicht aufgeführt sind |
| Multicast-MAC | die Ziel-MAC einer Multicast-Gruppe und warum sich 32 Gruppen eine MAC teilen |

## Ticket-Trainer

Datei: [`ticket-trainer.html`](ticket-trainer.html). Die 30 Fehler-Tickets aus den CCIE-Labs C1 bis C6 als Quiz: Du liest das Symptom und wählst unter vier Ursachen die richtige. Die falschen Antworten stammen aus anderen Tickets desselben Labs, sie klingen also plausibel.

- **Hinweis zeigen** blendet ein, wie man die Ursache findet. Wer ihn nutzt, hat das Ticket noch nicht sicher gelöst.
- Nach der Antwort siehst du Ursache, Fix und den eingebauten Fehler als Diff.
- Der Browser merkt sich den Fortschritt. „Nur noch nicht sicher gelöste“ wiederholt alles, was falsch oder nur mit Hinweis gelöst war.

## So nutzt du sie

Den Rechentrainer in kurzen Runden zwischendurch, zehn Minuten am Tag reichen. Den Ticket-Trainer nach jedem Lab für dessen fünf Tickets und in der Prüfungsphase für alle 30. Die Tickets ersetzen das Lab nicht: Im Lab suchst du den Fehler an der Konsole, hier übst du, aus dem Symptom die Ursache zu schließen. Wer ein Ticket ohne Hinweis löst, findet den Fehler auch an der echten Konsole schneller.
