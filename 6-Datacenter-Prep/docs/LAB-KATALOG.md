# Lab-Katalog: Soll und Stand

Die Tabelle vergleicht den geplanten Lernpfad (26 Labs) mit den vorhandenen Lab-Dateien in `labs/`.

**Format neu** (bisher nur Lab 32) heißt, das Lab hat:

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
| 02 | Tenant, VRF, BD, Application Profile | 03 Tenant, VRF, BD, EPG | vollständig (alt) | |
| 03 | Zwei Endpoints in derselben EPG | – | geplant | Engine: `POLICY_SAME_EPG`, getestet |
| 04 | Zwei EPGs in derselben BD | – | geplant | Engine unterstützt es (Bridging + Implicit Deny) |
| 05 | Verschiedene BDs im selben VRF | 03, 32 | teilweise | Routing grün, Policy rot: im Traffic-Test von Lab 32 sichtbar |
| 06 | Vollständige Access-Policy-Kette | 02 Access Policies | vollständig (alt) | |
| 07 | Fehlende Domain-Zuordnung | 07 Troubleshooting (ein Ticket) | teilweise | F0467, `EP_NOT_LEARNED` |
| 08 | VLAN außerhalb des Pools | 07 Troubleshooting | teilweise | |
| 09 | Fehlerhaftes Static Path Binding | 07 Troubleshooting | teilweise | |
| 10 | Consumer und Provider | 04, **32** | vollständig | Lab 32 im neuen Format |
| 11 | HTTPS erlauben, SSH blockieren | **32 Least Privilege** | **vollständig (neu)** | Abnahmefall, siehe `tests/test_acceptance.py` |
| 12 | ICMP und TCP getrennt | 04, 32 | vollständig | |
| 13 | Falscher Port, falsche Richtung | – | geplant | Engine: `POLICY_IMPLICIT_DENY`, `POLICY_REPLY_DENIED`, getestet |
| 14 | Intra-EPG Isolation | – | geplant | Engine vereinfacht: Intra-EPG-Contracts fehlen (B-05) |
| 15 | Fehlendes Endpoint Learning | 07 Troubleshooting | teilweise | |
| 16 | Endpoint Move | – | geplant | **nicht unterstützt**, Engine-Arbeit nötig (B-03) |
| 17 | Interface-Ausfall vs. Policy-Drop | – | geplant | Link-Zustand als Ereignis fehlt (B-04) |
| 18 | Mehrere unabhängige Fehler | 07 Troubleshooting (sechs Tickets) | vollständig (alt) | |
| 19 | Einfacher L3Out | 06 L3Out OSPF, 09 eBGP | vollständig (alt) | |
| 20 | Routingfehler vs. fehlender External-EPG-Contract | 06, 09 | teilweise | Codes `ROUTE_MISSING`, `EXT_EPG_NO_MATCH`, `POLICY_*` |
| 21 | Fehlender Rückweg | 06 | teilweise | `RETURN_ROUTE_MISSING` |
| 22 | Preferred Group | – | geplant | Engine umgesetzt, ohne eigenes Lab |
| 23 | vzAny | 04 Contracts und vzAny | vollständig (alt) | |
| 24 | Inter-VRF Shared Services | 13 Shared Services | vollständig (alt) | |
| 25 | Fehlerhafte Änderung per Snapshot zurücksetzen | – (Config Rollback vorhanden, Lab 25 ist Export/Import) | geplant | |
| 26 | IT-/OT-Segmentierung | – | geplant | Phase 4, mit negativen Tests für laterale Kommunikation |

Weitere vorhandene Labs außerhalb dieses Pfads:

- 00 Day 0
- 05 vPC
- 08 REST-API
- 10 bis 12 (OOB/NTP, Taboo, VMM)
- 14 bis 31: L2Out, Transit Routing, PBR, L3Out-Varianten, AAA, In-Band, ESG, Firmware, Export/Import, Monitoring, DHCP Relay, MCP, Multi-Pod, Remote Leaf, Multi-Site
