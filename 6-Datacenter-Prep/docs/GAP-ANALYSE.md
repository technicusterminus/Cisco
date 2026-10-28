# Gap-Analyse (Stand vor dem ersten vertikalen Schnitt der Lernplattform)

Untersucht wurden:

- Architektur: `dcprep/`, ca. 11.000 Zeilen Python
- Oberfläche: `static/`, ca. 5.300 Zeilen JS
- 32 Labs
- 35 Tests
- Persistenz und Benutzerverwaltung
- Dokumentation

## 1. Was funktioniert bereits

- **Eine gemeinsame Wahrheit** gibt es schon. Ein Konfigurationsspeicher (`Store`) mit APIC-Klassenmodell, DN-Logik, Validierung und atomarem POST, dazu eine Engine, die nach jeder Änderung den operativen Zustand vollständig neu berechnet. GUI, REST, CLI, Traffic-Test, Testmatrix und Lab-Bewertung nutzen beide.
- **Konfiguriert ≠ funktionsfähig** ist bereits modelliert. Endpoints werden nur gelernt, wenn die ganze Access-Kette stimmt. Nachbarschaften haben Zustände, Faults entstehen aus Ursachen.
- Der **Traffic-Test** prüft Schritt für Schritt: Endpoint, ARP/Bridging, Gateway, Routing, Leaking, Fabric-Pfad, Policy für Anfrage *und* Antwort (Reverse Filter Ports), Service Graph und L3Out-Rückweg.
- **Policy-Modell**:
  - Implicit Deny, Consumer/Provider, Scope
  - Deny-Filter, Taboo
  - vzAny, Preferred Group, VRF unenforced
  - Intra-EPG Isolation (vereinfacht), ESG
- **32 Labs** mit automatischer Bewertung nach Zustand und Tests „ohne Lösung nicht bestanden, mit Lösung bestanden“.
- **Persistenz**:
  - Benutzer mit getrennten Welten
  - Speicherstände mit Versionsnummer
  - Export und Import
  - Snapshots und Config Rollback
  - Fortschritt pro Lab
- REST-API im APIC-Format (Teilumfang), getestet mit Ansible. Dazu ein Abgleich-Werkzeug gegen einen echten APIC.

## 2. Was nur visuell simuliert ist

- **Keine Datenebene:** Der Traffic-Test berechnet und zeigt eine Entscheidung, es fließen keine Pakete. Das ist dokumentiert.
- Die **Topologie-Grafik** zeigt die Fabric, aber keinen berechneten Pfad. Der Pfad stand nur als Text im Traffic-Test. Im Traffic Inspector gibt es jetzt eine Pfadleiste aus Engine-Daten. Die Overlays in der Topologie fehlen noch.
- **Health Scores** sind aus Faults abgeleitet und vereinfacht, nicht zufällig.
- Der **Ablauf über die Zeit** (Discovery, Upgrades, Fault-Lebenszyklus) richtet sich nach der Wanduhr, nicht nach einer simulierten Uhr.

## 3. Was fachlich falsch oder unvollständig war

| Befund | Wirkung | Stand |
|---|---|---|
| `vzEntry.stateful` wurde ignoriert | Mit Stateful durfte der Provider vom Dienst-Port aus Verbindungen aufbauen | **behoben**, Test R-05 |
| Ergebnis des Traffic-Tests nur `ok` + Text | keine maschinenlesbare Ursache, keine Policy-Referenz, keine Trennung „Pfad kaputt“ vs. „Policy“ | **behoben**: verdict, reason, location, policy, hint, path |
| Kein Modell für Zieldienste | „Policy erlaubt“ wurde mit „Dienst erreichbar“ gleichgesetzt | **behoben**: Feld *Dienste*, `SERVICE_NOT_LISTENING`, getrennt vom Least-Privilege-Check |
| Lab-Bewertung ohne Sicherheits-Kategorie | Ein Permit-any fiel nur auf, wenn zufällig ein negativer Test existierte | **behoben**: Kategorie `security`, Check `exposure` |
| Labs sind Klickanleitungen | Die Lösung steht in der Aufgabe, wenig Transfer | behoben für 02, 03, 04, 07 und die neuen Labs 32 bis 35; übrige Labs offen (B-01) |
| Hinweise einstufig, kein Prüfungsmodus | | **behoben** in der Engine; genutzt von den Labs 02, 03, 04, 07, 32 bis 35 |
| Lab-Generator nicht deterministisch (Zeitstempel in Lab 25) | Generierte Dateien änderten sich bei jedem Lauf | **behoben** |
| Intra-EPG-Contracts nicht ausgewertet | Verkehr innerhalb einer EPG ließ sich nur ganz oder gar nicht erlauben | **behoben**: `fvRsIntraEpg` wird ausgewertet, Lab 38 |
| vzInTerm/vzOutTerm fehlen | „Apply Both Directions“ aus nicht modellierbar | offen (B-06) |
| Endpoint Move und Link-Ausfall nicht als Ereignis | Labs 16, 17 nicht möglich, Link-Probleme erschienen als EP_NOT_LEARNED | **behoben**: Events S9101–S9103, Endpoint-Verlauf, Codes LINK_DOWN/PORT_ADMIN_DOWN, Labs 36 und 37 |
| Prioritäten zwischen vzAny, EPG-Regeln und Taboo vereinfacht | mögliche Fehlaussagen bei überlappenden Regeln | offen, zuerst gegen echtes ACI prüfen |

## 4. Was zuerst den größten Lernnutzen bringt

1. **Der Abnahmefall als neues Lab-Format** (Lab 32): Anforderungen, Least Privilege, getrennte Bewertung, Hinweise, Prüfungsmodus. Er setzt das Muster für alle weiteren Labs. → *umgesetzt*
2. **Traffic Inspector mit Ursache und angewandter Regel**: Hier entsteht der Wechsel vom VLAN/ACL-Denken zum Policy-Modell, wenn sichtbar wird „Routing grün, Policy rot, weil …“. → *umgesetzt*
3. Bestehende Contract- und Access-Labs ins neue Format überführen (B-01) und die fehlenden Grundlagen-Labs ergänzen. → *umgesetzt für 02, 03, 04, 07 sowie neu 33, 34, 35*
4. Ereignisse für Endpoint Move und Link-Ausfall als Grundlage der Troubleshooting-Labs. → *umgesetzt (Labs 36, 37)*
5. OT-Szenario. → *umgesetzt (Lab 40)*
