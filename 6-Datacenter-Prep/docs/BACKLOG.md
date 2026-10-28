# Gap-Analyse und Backlog

Stand: 28.10.2026, nach dem ersten vertikalen Schnitt (Lab 32, strukturierte Connectivity-Ergebnisse, Lab-Bewertung nach Kategorien).

## Gap-Analyse

### 1. Was funktioniert bereits?

- Ein gemeinsamer Zustand für GUI, REST, CLI, Traffic-Test, Testmatrix und Lab-Bewertung (Store + `Engine.rebuild`).
- Objektmodell mit echten APIC-Klassen, atomarem POST, Validierung, Relationen, die auf `common/default` auflösen.
- Access-Policy-Kette bis zum Endpoint Learning, mit Fault F0467 bei Fehlern.
- Contracts mit Consumer/Provider, Reverse Filter Ports, vzAny, Preferred Group, Taboo, Scope, Isolation, unenforced VRF; Anfrage und Antwort getrennt geprüft.
- 33 deklarative Labs mit Zustandsprüfung; ein Test spielt jede Musterlösung ein und prüft, dass der Ausgangszustand nicht besteht.
- Benutzer mit getrennten Übungswelten, Speicherstände mit Version, Config Rollbacks.

### 2. Was ist nur visuell oder sehr grob simuliert?

- Fabric Discovery: fester Ablauf mit Zeitschritten statt LLDP/DHCP-Protokoll.
- L3Out-Nachbarschaften: Parametervergleich, keine Protokoll-Zustandsmaschine.
- CLI-Ausgaben: Daten echt aus dem Zustand, Format angenähert.
- Multi-Site/NDO: stark vereinfacht, zweite Site mit festen Endpoints.
- Topologie-Ansicht: keine logische Sicht mit EPG/BD/VRF-Overlays und kein hervorgehobener Traffic-Pfad.

### 3. Was war fachlich falsch oder unvollständig? (Stand vor diesem Schnitt)

| Befund | Status |
|---|---|
| Traffic-Ergebnis nur `ok` + Text; kein Verdikt, kein Reason Code, kein Fehlerort, keine strukturierte Policy | **behoben**: `verdict`, `reason`, `failedAt`, `policy`, `refs`, `hint` |
| Ungültige Eingaben lieferten „blockiert“ statt „nicht bewertbar“ | **behoben**: `UNRESOLVED` |
| Subjects mit `vzInTerm`/`vzOutTerm` wurden still als „kein Filter“ gewertet | **behoben**: `UNRESOLVED`/`POLICY_UNSUPPORTED` |
| Jede Freigabe galt als „erreichbar“, auch ohne Dienst am Ziel | **behoben** für Hosts mit `services`; Hosts ohne Liste werden im Ergebnis als „nicht modelliert“ ausgewiesen |
| Lab-Bewertung ohne Trennung von Funktion und Sicherheit; Permit-any konnte Contract-Labs bestehen, wenn Negativtests fehlten | **behoben** für Lab 32 (`policy_scope`, Kategorien); ältere Labs haben teils keine Negativtests |
| Ein Tipp je Aufgabe statt gestufter Hinweise; kein Prüfungsmodus | **behoben**: vier Stufen, Prüfungsmodus ohne Hinweise und Lösung |
| Lab-Generator schrieb Uhrzeit in Lab 25 (nicht reproduzierbar) | **behoben** |
| README versprach „reagiert wie ein echter APIC“ | **behoben**: Referenzprofil mit umgesetzt/vereinfacht/nicht unterstützt |
| Deny-Priorität ohne Spezifität | offen (dokumentiert als Vereinfachung) |
| Endpoint Move als Ereignis fehlt | offen |
| Kein Dark Mode | offen |

### 4. Was bringt zuerst den größten Lernnutzen?

Genau der Abnahmefall: Policy-Drop klar von Netzwerkfehlern trennen, Richtung verstehen, Least Privilege bewerten. Danach die fehlenden Grundlagen-Labs (Same EPG, Same BD) und Troubleshooting-Labs, die genau eine Ursache isolieren.

## Lab-Katalog aus dem Auftrag

| Nr. | Lab | Stand |
|---|---|---|
| 01 | Fabric-Komponenten, physische/logische Sicht | teilweise: Lab 01 (Discovery); logische Sicht fehlt in der UI |
| 02 | Tenant, VRF, BD, Application Profile | vorhanden: Lab 03 |
| 03 | Zwei Endpoints in derselben EPG | geplant; Regel umgesetzt und getestet (`test_same_epg_and_isolation`) |
| 04 | Zwei EPGs in derselben BD | geplant; Engine unterstützt es |
| 05 | Verschiedene BDs, gleiche VRF | vorhanden: Lab 03, 04, 32 |
| 06 | Access-Policy-Kette aufbauen | vorhanden: Lab 02 |
| 07 | Fehlende Domain-Zuordnung | teilweise: Ticket in Lab 07 |
| 08 | VLAN außerhalb des Pools | teilweise: Lab 02/07 (F0467 invalid-vlan) |
| 09 | Fehlerhaftes Static Path Binding | teilweise: Ticket in Lab 07 |
| 10 | Consumer und Provider zuordnen | vorhanden: Lab 04, **Lab 32** |
| 11 | HTTPS erlauben, SSH blockieren | **vorhanden: Lab 32** |
| 12 | ICMP und TCP getrennt testen | **vorhanden: Lab 32**, Lab 04 |
| 13 | Falschen Port bzw. falsche Richtung korrigieren | geplant (Troubleshooting-Variante von Lab 32); Engine und Tests vorhanden |
| 14 | Intra-EPG Isolation | geplant; Regel umgesetzt und getestet |
| 15 | Fehlendes Endpoint Learning | teilweise: Lab 07 |
| 16 | Endpoint Move | **nicht startbar**: Engine fehlt |
| 17 | Interface-Ausfall vs. Policy-Drop | geplant; Disabled Interfaces vorhanden |
| 18 | Mehrere unabhängige Fehler | vorhanden: Lab 07 |
| 19 | L3Out mit unterstütztem Routing-Modell | vorhanden: Lab 06 (OSPF), 09 (eBGP) |
| 20 | Routingfehler vs. fehlender External-EPG-Contract | teilweise: Lab 06 |
| 21 | Fehlender Rückweg | teilweise: Lab 06; Reason `EXT_NO_RETURN_ROUTE` |
| 22 | Preferred Group | geplant; Regel umgesetzt und getestet |
| 23 | vzAny | vorhanden: Lab 04 |
| 24 | Inter-VRF Shared Services | vorhanden: Lab 13 |
| 25 | Fehlerhafte Änderung per Snapshot zurücksetzen | geplant; Config Rollbacks vorhanden |
| 26 | IT-/OT-Segmentierung | geplant |

## Backlog (priorisiert)

**Phase 2 – Lernplattform**

1. Labs 03, 04, 13, 14 aus dem Katalog als eigene kurze Labs mit Negativtests und `policy_scope`.
2. Ältere Policy-Labs (04, 06, 13, 16, 23) um Kategorien, gestufte Hinweise und Least-Privilege-Prüfungen ergänzen; Lösungstexte aus Aufgaben entfernen, wo sie heute stehen.
3. Dienstliste im Host-Dialog der GUI pflegen (heute nur über Labs und API).
4. Prüfungsmodus: Musterlösung erst nach Abgabe zeigen; Zeitlimit optional.
5. `understanding`-Prüfungen (Verständnisfragen mit fester Antwort) in Labs.

**Phase 3 – Troubleshooting**

6. Endpoint Move als Ereignis (alter/neuer Ort, Event, EP-Tracker-Historie) und Lab 16.
7. Lab 17: Interface-Ausfall vs. Policy-Drop.
8. Lab 25: Fehlerhafte Änderung mit Snapshot zurückrollen; Diagnoseprozess nur aus erfassten Aktionen (Traffic-Tests, CLI-Befehle) bewerten.
9. Mehrfachfehler-Labs mit gestuften Hinweisen je Fehler.

**Phase 4 – Erweiterungen**

10. Logische Topologie mit EPG/BD/VRF-Overlays und hervorgehobenem Pfad aus dem Traffic-Ergebnis (Drop-Punkt aus `failedAt`).
11. Dark Mode und Tastaturbedienung prüfen.
12. Lab 26 IT/OT-Segmentierung mit Engineering-, Applikations-, Monitoring- und Management-EPGs und Negativtests für laterale Wege.
13. Deny-Priorität nach Spezifität, Intra-EPG Contracts, Subjects mit getrennten Richtungen.
14. Lint-Altlasten bereinigen (`ruff check --select E9,F`: 14 Befunde in älterem Code, vor allem ungenutzte Importe).
