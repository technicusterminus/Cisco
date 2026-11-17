# Lab-Katalog

Alle Labs sind Eigenentwicklungen für den Simulator (keine Vorlagen von Cisco oder aus Kursunterlagen). Quelle ist `Labs-Quelle/build_labs.py`; `labs/*.json` werden daraus erzeugt (`python3 Labs-Quelle/build_labs.py`).

| Lab | Art | Thema | Lernmoment | Falsche Abkürzung, die die Prüfung abfängt |
|---|---|---|---|---|
| 01 Corp-SSID in der Lobby nicht sichtbar | Fehlersuche | Tags | Ein AP ohne eigenes Policy Tag nutzt das Default Policy Tag, das kein WLAN enthält | Beide APs taggen: Der Laptop verbindet sich, aber Corp sendet auch im Lager (Least Privilege) |
| 02 Alles eingerichtet, nichts funkt | Fehlersuche | Betriebszustand | WLAN-Profil und Policy Profile sind nach dem Anlegen administrativ down; zwei Ursachen nacheinander | Nur das WLAN aktivieren: Das Policy Profile hält den Client weiter draußen |
| 03 Der Schlüssel passt nicht | Fehlersuche | Sicherheit | Authentifizierungsfehler bei WPA2-PSK; der Key wird nie angezeigt | WLAN auf Open stellen: Der Client verbindet sich, Corp ist aber ungeschützt |
| 04 Richtiges WLAN, falsche Zuordnung | Fehlersuche | Tags | Das Policy Tag ordnet je WLAN ein Policy Profile zu | Das Gast-Profil aktivieren: Der Client landet im VLAN 99 statt im VLAN 20 |
| 05 Gast-WLAN nur in der Lobby | Anforderungen | Design | Zwei WLANs mit unterschiedlichem Geltungsbereich brauchen zwei Policy Tags | Gast in das gemeinsame Tag einfügen: Das Lager sendet dann auch Gast |
| 06 Altes WLAN sauber entfernen | Anforderungen | Betrieb | Abhängigkeiten zwischen AP, Policy Tag, WLAN und Policy Profile; Abbau von außen nach innen | Corp-Zuordnung mit entfernen: Der Laptop in der Lobby fällt aus |

## Aufbau eines Labs

Jedes Lab hat Szenario, Anforderungen, Lernziele, Werkzeuge, Grenzen, vier Hinweisstufen (Konzept, Ebene, Prüfschritte, Lösung), Prüfungen mit Kategorie (`function` oder `security`), zwei Verständnisfragen, die nicht zum Bestehen zählen, eine Musterlösung als CLI-Befehle und einen Text zur Lösung.

- **Bewertet wird das Verhalten**, nicht der Wortlaut: Prüfungen lesen den Zustand der Welt (Client verbunden, VLAN, WLAN-Eigenschaften, Zuordnungen). Gleichwertige Lösungen bestehen (Lab 05 hat dazu einen Test).
- **Modi:** *geführt* (Hinweise, Lösung, Client-Diagnose, Details in der Auswertung) und *Prüfung* (nichts davon; die Diagnosebegründungen werden auch aus dem Zustand der Oberfläche entfernt).
- **Das Lab verändert nie die Konfiguration von sich aus.** Ein Start setzt die Welt zurück und spielt die Startkonfiguration über dieselbe CLI ein; das Zurücksetzen stellt diesen Zustand wieder her.
- **Der sichtbare Text verrät die Lösung nicht:** Der Test `test_structure_and_no_solution_in_visible_text` prüft Szenario, Anforderungen und Prüfungsbeschreibungen gegen eine Liste von Lösungswörtern.

## Fortschritt

Je Lab werden gezählt: Starts, Prüfläufe, bestanden (geführt und Prüfung getrennt), die wenigsten genutzten Hinweise bei einem geführten Bestehen und die höchste Zahl richtiger Verständnisfragen. Ein nicht bestandener Prüflauf markiert nichts als bestanden; *Fortschritt zurücksetzen* leert alles. Der Fortschritt gehört nicht zu den benannten Ständen.

## Neues Lab anlegen

1. In `Labs-Quelle/build_labs.py` mit `lab(...)` anlegen und unter `SOLUTIONS[...]` eine Musterlösung eintragen.
2. In `tests/test_labs.py` die ID in `ALL` und die Lösungswörter in `LEAKS` ergänzen; für jede naheliegende Abkürzung einen Test schreiben.
3. `python3 Labs-Quelle/build_labs.py`, dann alle Prüfungen laufen lassen.
