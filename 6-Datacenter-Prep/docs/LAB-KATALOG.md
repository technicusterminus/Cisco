# Lab-Katalog: Soll und Stand

Die Tabelle vergleicht den geplanten Lernpfad (26 Labs) mit den vorhandenen Lab-Dateien in `labs/`.

**Alle Labs** sind im Anforderungsformat. Jedes Lab hat:

- Anforderungen statt Klickanleitung
- vier Hinweisstufen
- Prüfungsmodus
- Bewertung getrennt nach Funktion und Sicherheit
- Verständnisfragen

Startbar sind nur Labs, die es als Datei gibt. Die Spalte *Stand* gilt für die Lernziele des Soll-Labs:

- **vollständig**: Die Lernziele sind abgedeckt.
- **teilweise**: Ein vorhandenes Lab deckt einen Teil ab.
- **geplant**: Es gibt kein Lab, und die Engine-Unterstützung ist in der Bemerkung angegeben.

| Soll | Thema | Vorhandenes Lab | Stand | Bemerkung |
|---|---|---|---|---|
| 01 | Fabric-Komponenten, physische und logische Sicht | 01 Fabric Discovery | vollständig | Tenant liegt bereit und wirkt erst nach der Discovery; VRF nur auf Leafs mit Endpoints |
| 02 | Tenant, VRF, BD, Application Profile | 03 Tenant, VRF, BD, EPG | vollständig | |
| 03 | Zwei Endpoints in derselben EPG | **33 Zwei Endpoints in derselben EPG** | vollständig | Prüft auch: ohne Contract gelöst |
| 04 | Zwei EPGs in derselben BD | **34 Zwei EPGs in derselben BD** | vollständig | Bridging grün, Policy rot; ICMP-Gegenrichtung als Lernpunkt |
| 05 | Verschiedene BDs im selben VRF | **45 Zwei Bridge Domains, eine VRF** | vollständig | BD in falscher VRF und falsches Gateway-Subnetz; Route Leaking als Abkürzung scheitert |
| 06 | Vollständige Access-Policy-Kette | 02 Access Policies | vollständig | Namen frei wählbar außer der Domain, Fremdgerät an freiem Port |
| 07 | Fehlende Domain-Zuordnung | **44 Access-Diagnose** (Ticket 1), 02 | vollständig | F0467 invalid-vlan, `EP_NOT_LEARNED` |
| 08 | VLAN außerhalb des Pools | **44 Access-Diagnose** (Ticket 3), 07 (Ticket 1) | vollständig | Server-VLAN ist vorgegeben; die Bindung umzubiegen besteht nicht |
| 09 | Fehlerhaftes Static Path Binding | **44 Access-Diagnose** (Ticket 2), 33, 07 | vollständig | falsches VLAN an der Bindung erzeugt keinen Fault, nur einen ungelernten Endpoint; Static Leaf als Abkürzung lernt das Fremdgerät |
| 10 | Consumer und Provider | 04, 32, 35 | vollständig | |
| 11 | HTTPS erlauben, SSH blockieren | **32 Least Privilege** | **vollständig** | Abnahmefall, siehe `tests/test_acceptance.py` |
| 12 | ICMP und TCP getrennt | 04, 32, 34 | vollständig | |
| 13 | Falscher Port, falsche Richtung | **35 Falscher Port, falsche Richtung** | vollständig | zwei unabhängige Fehler, permit any scheitert |
| 14 | Intra-EPG Isolation | **38 Innerhalb einer EPG einschränken** | vollständig | Isolation allein reicht nicht; Intra-EPG-Contract mit Least Privilege |
| 15 | Fehlendes Endpoint Learning | 44 Access-Diagnose (alle Tickets), 07 (Ticket 5) | vollständig | drei Ursachen für `EP_NOT_LEARNED` unterscheiden |
| 16 | Endpoint Move | **36 Endpoint Move nachvollziehen** | vollständig | Endpoint-Verlauf im EP Tracker; alte Bindung als Sicherheitsrisiko |
| 17 | Interface-Ausfall vs. Policy-Drop | **37 Interface-Ausfall oder Policy-Drop?** | vollständig | drei Ursachen: PORT_ADMIN_DOWN, POLICY_IMPLICIT_DENY, LINK_DOWN |
| 18 | Mehrere unabhängige Fehler | 07 Troubleshooting (sechs Tickets) | vollständig | mit Least-Privilege-Nebenbedingung |
| 19 | Einfacher L3Out | 06 L3Out OSPF, 09 eBGP | vollständig | MTU/EXSTART, MP-BGP, App-Netz bleibt intern |
| 20 | Routingfehler vs. fehlender External-EPG-Contract | **41 Routingfehler oder fehlender Contract?** | vollständig | erst ROUTE_MISSING (kein MP-BGP), dann POLICY_IMPLICIT_DENY |
| 21 | Fehlender Rückweg | **42 Fehlender Rückweg** | vollständig | RETURN_ROUTE_MISSING; App-Netz darf nicht angekündigt werden |
| 22 | Preferred Group | **39 Preferred Group für eine Migration** | vollständig | Nicht-Mitglied bleibt geschützt; kein VRF unenforced |
| 23 | vzAny | 04 Contracts und vzAny | vollständig | Lösung pro EPG wird ebenfalls anerkannt (dokumentiert) |
| 24 | Inter-VRF Shared Services | 13 Shared Services | vollständig | Least Privilege in beide Richtungen, Dienst im Provider-Tenant |
| 25 | Fehlerhafte Änderung per Snapshot zurücksetzen | **43 Change mit Snapshot absichern und zurückrollen** | vollständig | bewertet Snapshot nach Lab-Start, eingespielten Change (Audit-Log) und vollständigen Rollback |
| 27 | Contract-Prioritäten (vzAny vs. EPG-Deny) | **46 Contract-Prioritäten: alles offen, ein Paar gesperrt** | vollständig | Priorität 7 vor 17; Deny in der vzAny-Freigabe sperrt alle EPGs und scheitert |
| 26 | IT-/OT-Segmentierung | **40 IT-/OT-Segmentierung einer Fertigungslinie** | vollständig | fünf Zonen, 18 Prüfungen, davon 10 Least-Privilege-Prüfungen inkl. lateraler Kommunikation; didaktisch, ohne Sicherheitsgarantie |

Weitere Labs außerhalb dieses Pfads: 00 (Day 0), 08 (REST-API) und 14 bis 31 (L2Out, Routing-Varianten, AAA, In-Band, ESG, Firmware, Export/Import, Monitoring, DHCP Relay, MCP, Multi-Pod, Remote Leaf, Multi-Site).
