# Trainer

## Subnetting-Trainer

Datei: [`subnetting-trainer.html`](subnetting-trainer.html). Im Browser öffnen, läuft offline.

Aufgabentypen mit Lösungsweg:

- Subnetz bestimmen (Netz, Broadcast, erster und letzter Host, Hostzahl)
- Hosts → Präfix und Maske
- Maske ↔ Präfix
- Wildcard-Maske
- Selbes Subnetz? (ja/nein)
- VLSM-Aufteilung eines /24
- IPv6 kürzen
- EUI-64 aus MAC-Adresse

Die Aufgaben sind zufällig, der Lösungsweg rechnet Schritt für Schritt mit den Zahlen der jeweiligen Aufgabe. Die Rechenlogik ist gegen Pythons `ipaddress`-Modul mit je 300 Aufgaben pro Typ geprüft.

### So übst du

1. **Erst rechnen, dann vergleichen.** Schreib dein Ergebnis auf, bevor du den Lösungsweg öffnest.
2. **Eine Methode für alles:** Blockgröße = 256 − Maskenwert im interessanten Oktett. Die Netz-ID ist das größte Vielfache der Blockgröße, das nicht über der Adresse liegt. Der Broadcast liegt eins vor dem nächsten Netz.
3. **Erst Genauigkeit, dann Tempo.** Wenn zehn Aufgaben am Stück stimmen, achte auf die Zeit.

Ziel: Netz, Broadcast und Hostbereich in unter 30 Sekunden ohne Hilfsmittel.

## Ticket-Trainer

Datei: [`ticket-trainer.html`](ticket-trainer.html). Die 95 Fehler-Tickets aus den Packet-Tracer-Labs als Quiz: Du liest das Symptom und wählst unter vier Ursachen die richtige. Die falschen Antworten stammen aus anderen Tickets desselben Labs.

- **Hinweis zeigen** blendet ein, wie man die Ursache findet. Wer ihn nutzt, hat das Ticket noch nicht sicher gelöst.
- Nach der Antwort siehst du Ursache, Fix und den eingebauten Fehler als Diff.
- Der Browser merkt sich den Fortschritt. „Nur noch nicht sicher gelöste“ wiederholt alles, was falsch oder nur mit Hinweis gelöst war.

Am meisten bringt er direkt nach einem Lab für dessen Tickets und in der Prüfungsphase für alle.
