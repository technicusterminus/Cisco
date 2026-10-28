# Cisco – Zertifizierungsvorbereitung

Deutschsprachige Lernmaterialien für Cisco-Prüfungen, vom Einstieg bis zum CCIE. Die Ordner sind in der empfohlenen Reihenfolge nummeriert.

| Ordner | Prüfung | Inhalt |
|---|---|---|
| [`1-Netzwerk-Einstieg`](1-Netzwerk-Einstieg/) | ohne Vorkenntnisse | 12 Kapitel, Cheatsheet, Glossar, 5 Übungen, Anki-Deck (137 Karten, davon 35 Befehle), Quiz (57 Fragen) und 4-Wochen-Lernplan bis zum Start in die CCNA |
| [`2-CCNA-200-301`](2-CCNA-200-301/) | CCNA 200-301 v1.1 | Anki-Deck (792 Karten, davon 171 Befehle), 26 Packet-Tracer-Labs, Subnetting- und Ticket-Trainer, Prüfungssimulation (273 Fragen), Cheatsheet und 8-Wochen-Lernplan zu allen 53 Prüfungszielen |
| [`3-CCNP-ENCOR-350-401`](3-CCNP-ENCOR-350-401/) | CCNP ENCOR 350-401 v1.2 | Anki-Deck deutsch (1.776 Karten, davon 345 Befehle) und englisch (1.981 Karten, davon 429 MC und 136 Show-Karten), Prüfungssimulation (241 Fragen), Rechen- und Ticket-Trainer, Cheatsheet, 10-Wochen-Lernplan und Labs für CML, EVE-NG und Packet Tracer zu allen 47 Zielen |
| [`4-CCNP-ENARSI-300-410`](4-CCNP-ENARSI-300-410/) | CCNP ENARSI 300-410 | Anki-Deck (709 Karten, davon 231 Befehle), Prüfungssimulation (179 Fragen), 6 eigene Labs für CML und EVE-NG und Zuordnung der passenden ENCOR-Labs |
| [`5-CCIE-Enterprise-Infrastructure`](5-CCIE-Enterprise-Infrastructure/) | CCIE Enterprise Infrastructure | Anki-Deck (542 Karten, davon 184 Befehle), Prüfungssimulation (175 Fragen), 6 eigene Labs für CML und EVE-NG und Zuordnung der passenden ENCOR- und ENARSI-Labs |
| [`6-Datacenter-Prep`](6-Datacenter-Prep/) | Data Center ACI (z. B. DCACI 300-620) | Datacenter Prep: simulierter APIC mit derselben GUI-Struktur (Menüs, Baum, Tabs, Wizards), APIC-REST-API (getestet mit Ansible `cisco.aci`), CLI, Faults, Events, Audit Log, Day 0 mit Setup-Dialog, Verification-Befehle, Traffic-Test, VMM mit simuliertem vCenter, Shared Services, L2Out, Transit Routing, Service Graph mit PBR, Traffic Inspector mit ALLOW/DROP/UNRESOLVED und Reason Codes, 33 Labs mit automatischer Prüfung des Endzustands |

Netzwerk-Einstieg, CCNA und ENCOR haben einen Wochenplan (`LERNPLAN.md`), ENARSI und CCIE eine Lernempfehlung im README.

## Aufbau der Ordner

Jeder Prüfungsordner folgt demselben Schema, soweit es den Baustein dort gibt:

| Unterordner | Inhalt |
|---|---|
| `Anki/` | Deck als `.apkg` zum Importieren, README mit Aufbau und Versionen |
| `Anki/Quelle/` | Kartentexte und Skripte, aus denen das Deck entsteht |
| `Pruefungssimulation/` | Simulation als einzelne HTML-Datei, läuft offline im Browser |
| `Trainer/` | Rechen-, Subnetting- und Ticket-Trainer, ebenfalls offline im Browser |
| `CML-Labs/`, `EVE-NG-Labs/`, `Packet-Tracer-Labs/` | Labs je Plattform, Musterlösungen und Fehlerlisten jeweils in `solutions/` |
| `Labs-Quelle/` | Lab-Definitionen und Generator, aus denen die CML- und EVE-NG-Dateien entstehen |

**So ist das Material aufgebaut:** Jede Antwort nennt zuerst den Kern und erklärt dann, warum. Jedes Deck hat Befehlskarten (`tag:Fokus::Befehle`): Aufgabe vorne, genaue Syntax mit Modus hinten. Jedes Lab beginnt mit Lernzielen, und jedes Fehler-Ticket sagt, mit welchem Befehl du den Fehler findest. Die Prüfungssimulationen laden auch eigene Fragenpools im JSON-Format.

> Kein offizielles Cisco-Material. Cisco, CCNA, CCNP, CCIE, ENCOR, ENARSI, ACI, APIC und Packet Tracer sind Marken von Cisco Systems, Inc.
