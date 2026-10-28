# Lab-Katalog: Soll und Stand

Die Tabelle vergleicht den geplanten Lernpfad (26 Labs) mit den vorhandenen Lab-Dateien in `labs/`.

**Format neu** (Labs 02, 03, 04, 07 und 32 bis 43) heißt, das Lab hat:

- Anforderungen statt Klickanleitung
- vier Hinweisstufen
- Prüfungsmodus
- Bewertung getrennt nach Funktion und Sicherheit
- Verständnisfragen

**Format alt** sind geführte Labs mit Aufgabenschritten und Prüfungen ohne Kategorien. Sie sind voll benutzbar und werden automatisch bewertet. Prüfungsmodus und gestufte Hinweise fehlen ihnen.

Startbar sind nur Labs, die es als Datei gibt. Die Spalte *Stand* gilt für die Lernziele des Soll-Labs:

- **vollständig**: Die Lernziele sind abgedeckt.
- **teilweise**: Ein vorhandenes Lab deckt einen Teil ab.
- **geplant**: Es gibt kein Lab, und die Engine-Unterstützung ist in der Bemerkung angegeben.

| Soll | Thema | Vorhandenes Lab | Stand | Bemerkung |
|---|---|---|---|---|
| 01 | Fabric-Komponenten, physische und logische Sicht | 01 Fabric Discovery | teilweise | Discovery und Rollen, keine eigene Übung zur logischen Sicht |
| 02 | Tenant, VRF, BD, Application Profile | 03 Tenant, VRF, BD, EPG | vollständig (neu) | |
| 03 | Zwei Endpoints in derselben EPG | **33 Zwei Endpoints in derselben EPG** | vollständig (neu) | Prüft auch: ohne Contract gelöst |
| 04 | Zwei EPGs in derselben BD | **34 Zwei EPGs in derselben BD** | vollständig (neu) | Bridging grün, Policy rot; ICMP-Gegenrichtung als Lernpunkt |
| 05 | Verschiedene BDs im selben VRF | 03, 32 | teilweise | Routing grün, Policy rot: im Traffic-Test von Lab 32 sichtbar |
| 06 | Vollständige Access-Policy-Kette | 02 Access Policies | vollständig (neu) | Namen frei wählbar außer der Domain, Fremdgerät an freiem Port |
| 07 | Fehlende Domain-Zuordnung | 02 Access Policies (Domain fehlt im Ausgangszustand) | teilweise (neu) | F0467, `EP_NOT_LEARNED`; ein eigenes Diagnose-Lab fehlt |
| 08 | VLAN außerhalb des Pools | 07 Troubleshooting (Ticket 1) | teilweise (neu) | |
| 09 | Fehlerhaftes Static Path Binding | 33 (fehlende Bindung), 07 (Ticket 2: Port nicht im Selector) | teilweise (neu) | falsches VLAN an der Bindung noch ohne Lab |
| 10 | Consumer und Provider | 04, 32, 35 | vollständig (neu) | |
| 11 | HTTPS erlauben, SSH blockieren | **32 Least Privilege** | **vollständig (neu)** | Abnahmefall, siehe `tests/test_acceptance.py` |
| 12 | ICMP und TCP getrennt | 04, 32, 34 | vollständig (neu) | |
| 13 | Falscher Port, falsche Richtung | **35 Falscher Port, falsche Richtung** | vollständig (neu) | zwei unabhängige Fehler, permit any scheitert |
| 14 | Intra-EPG Isolation | **38 Innerhalb einer EPG einschränken** | vollständig (neu) | Isolation allein reicht nicht; Intra-EPG-Contract mit Least Privilege |
| 15 | Fehlendes Endpoint Learning | 07 Troubleshooting (Ticket 5) | teilweise (neu) | |
| 16 | Endpoint Move | **36 Endpoint Move nachvollziehen** | vollständig (neu) | Endpoint-Verlauf im EP Tracker; alte Bindung als Sicherheitsrisiko |
| 17 | Interface-Ausfall vs. Policy-Drop | **37 Interface-Ausfall oder Policy-Drop?** | vollständig (neu) | drei Ursachen: PORT_ADMIN_DOWN, POLICY_IMPLICIT_DENY, LINK_DOWN |
| 18 | Mehrere unabhängige Fehler | 07 Troubleshooting (sechs Tickets) | vollständig (neu) | mit Least-Privilege-Nebenbedingung |
| 19 | Einfacher L3Out | 06 L3Out OSPF, 09 eBGP | vollständig (alt) | |
| 20 | Routingfehler vs. fehlender External-EPG-Contract | **41 Routingfehler oder fehlender Contract?** | vollständig (neu) | erst ROUTE_MISSING (kein MP-BGP), dann POLICY_IMPLICIT_DENY |
| 21 | Fehlender Rückweg | **42 Fehlender Rückweg** | vollständig (neu) | RETURN_ROUTE_MISSING; App-Netz darf nicht angekündigt werden |
| 22 | Preferred Group | **39 Preferred Group für eine Migration** | vollständig (neu) | Nicht-Mitglied bleibt geschützt; kein VRF unenforced |
| 23 | vzAny | 04 Contracts und vzAny | vollständig (neu) | Lösung pro EPG wird ebenfalls anerkannt (dokumentiert) |
| 24 | Inter-VRF Shared Services | 13 Shared Services | vollständig (alt) | |
| 25 | Fehlerhafte Änderung per Snapshot zurücksetzen | **43 Change mit Snapshot absichern und zurückrollen** | vollständig (neu) | bewertet Snapshot nach Lab-Start, eingespielten Change (Audit-Log) und vollständigen Rollback |
| 26 | IT-/OT-Segmentierung | **40 IT-/OT-Segmentierung einer Fertigungslinie** | vollständig (neu) | fünf Zonen, 18 Prüfungen, davon 10 Least-Privilege-Prüfungen inkl. lateraler Kommunikation; didaktisch, ohne Sicherheitsgarantie |

Weitere vorhandene Labs außerhalb dieses Pfads:

- 00 Day 0
- 05 vPC
- 08 REST-API
- 10 bis 12 (OOB/NTP, Taboo, VMM)
- 14 bis 31: L2Out, Transit Routing, PBR, L3Out-Varianten, AAA, In-Band, ESG, Firmware, Export/Import, Monitoring, DHCP Relay, MCP, Multi-Pod, Remote Leaf, Multi-Site
