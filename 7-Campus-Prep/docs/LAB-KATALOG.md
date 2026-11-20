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

## CCNP Enterprise Wireless (300-430 ENWLSI)

Die Labs 07 bis 19 tragen den Track *CCNP Enterprise Wireless*: FlexConnect (07, 08), 802.1X mit RADIUS (09 bis 11), Local Web Authentication (12, 13), Mobility (14, 15), RF (16, 17) und QoS (18, 19), Prüfungsthemen der 300-430 (Quellen und Vorbehalte in `docs/QUELLEN.md`). Die Labs 01 bis 06 sind Grundlagen.

| Lab | Art | Lernmoment | Falsche Abkürzung, die die Prüfung abfängt |
|---|---|---|---|
| 07 Zweigstelle Lager: Corp lokal schalten | Anforderungen | Policy Profile (lokales Switching), Flex Profile (lokale VLANs), Site Tag (Modus) und zwei Policy Tags greifen ineinander | Beide APs auf FlexConnect stellen: Die Lobby verliert den Local Mode und schaltet lokal. Lokales Switching für alle: Die APs im Local Mode lassen den Client nicht zu. Flex Profile ohne das VLAN: Der Client bleibt draußen |
| 08 Zweigstelle: Lager-Laptop ohne Verbindung | Fehlersuche | Der VLAN-Name im Policy Profile muss exakt dem im Flex Profile entsprechen | Zentrales Switching einschalten oder den AP zurück in den Local Mode: Die Prüfung verlangt lokale Schaltung im FlexConnect-Modus |

| 09 802.1X: Anmeldung scheitert trotz richtiger Zugangsdaten | Fehlersuche | Das Shared Secret muss auf WLC und RADIUS-Server gleich sein (Groß-/Kleinschreibung zählt); ein falsches Secret macht den Server DEAD | Das WLAN auf PSK oder Open herabstufen: alle verbinden sich, die Sicherheitsprüfung fällt durch. Den Server auf eine andere Adresse zeigen lassen: keine Lösung |
| 10 802.1X: Alle im selben VLAN trotz RADIUS-Zuweisung | Fehlersuche | Das VLAN aus RADIUS gilt nur mit `aaa-override` im Policy Profile | Das VLAN des Policy Profile ändern: Die Prüfung verlangt das VLAN des Benutzers aus RADIUS |
| 11 802.1X: Anmeldung trotz Ausfall des ersten RADIUS-Servers | Anforderungen | Reihenfolge der Server in der Server Group; ein nicht erreichbarer Server wird übersprungen, ein Access-Reject löst keinen Failover aus | Den ersten Server auf die Adresse des zweiten umbiegen: verbindet, aber ohne Redundanz. Zweiter Server mit falschem Secret: hilft nicht |
| 12 Gast-WLAN: Portal-Anmeldung scheitert trotz richtigem Konto | Fehlersuche | Die lokale Portal-Anmeldung braucht neben Liste, Parameter Map und Benutzer auch die Autorisierung | Web Authentication am WLAN abschalten: Auch Mallory ohne Konto kommt hinein, die Sicherheitsprüfung fällt durch |
| 13 Gast-WLAN mit Portal-Anmeldung einrichten | Anforderungen | Reihenfolge der Bausteine: Benutzer, Login-Liste, Autorisierung, Parameter Map, Web Auth im WLAN | Nur den Benutzer anlegen: Das WLAN bleibt offen, Mallory kommt ohne Anmeldung hinein. Ohne Parameter Map oder Autorisierung bleibt jeder in Webauth Pending |
| 14 Roaming zwischen Controllern: Sitzung bricht ab | Fehlersuche | Der Tunnel zum Peer kommt nur hoch, wenn Gruppe und MAC im Peer-Eintrag zum Peer passen | Den Peer entfernen oder den eigenen Gruppennamen ändern: Der Tunnel bleibt unten, der Laptop roamt nicht. Das WLAN öffnen: Auch der Laptop mit falschem Schlüssel kommt hinein |
| 15 Mobility mit einem neuen Controller einrichten | Anforderungen | Beide Seiten müssen zueinander passen: Der eigene Gruppenname (wie die Gegenseite uns kennt) und der Peer-Eintrag | Nur den Peer eintragen oder nur den Gruppennamen setzen: Der Tunnel bleibt unten |
| 16 RF-Profil angelegt, aber die Lobby sendet unverändert | Fehlersuche | Ein RF-Profil wirkt nur über ein RF Tag, das der AP trägt | Das Default RF Tag auf das Profil zeigen lassen: Es trifft auch ap-lager |
| 17 Kleinere Funkzellen in der Lobby einrichten | Anforderungen | Profil, RF Tag und AP-Zuordnung; ein neues Profil ist zunächst deaktiviert | Profil ohne `no shutdown`: Das Band ist aus. Nur das 2,4-GHz-Profil oder das falsche Band: Das 5-GHz-Band bleibt unverändert. Default RF Tag: Trifft alle APs |
| 18 Sprache im Corp-WLAN verliert ihre Priorität | Fehlersuche | Das Metal-Profil legt den höchsten DSCP-Wert je Richtung fest (Silver 0, Platinum 46) | Platinum auch für Gäste: Sie dürften dann DSCP 46 senden. Alle service-policy entfernen: Die Gäste sind nicht mehr begrenzt. Nur Output setzen: Der Verkehr vom Client bleibt bei 0 |
| 19 Gäste in beide Richtungen begrenzen | Anforderungen | Output und Input sind getrennte Einstellungen; Bronze ist 8 | Nur eine Richtung: Die andere bleibt bei 46. Silver (0) oder Gold (34): falscher Wert. Auch das Corp-WLAN auf Bronze: Corp wird gebremst |

Gleichwertig bei Lab 08: den Namen im Policy Profile anpassen oder im Flex Profile umbenennen.

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
