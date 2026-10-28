# Fachliche Regelbasis der Connectivity-Engine

Jede Regel nennt, wo sie im Code steht, womit sie geprüft ist und auf welche Quelle sie sich stützt. „Nicht verifiziert“ heißt: Die Regel ist plausibel umgesetzt, aber gegen keine offizielle Quelle geprüft.

Quelle **[CG]**: [Cisco ACI Contract Guide](https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-743951.html), Abschnitte „How contracts work“, „Subjects and filters“, „show zoning-rule“, „vzAny“, „Preferred group“, „Unenforced mode“.

## Regeln

| # | Regel | Code | Test | Quelle |
|---|---|---|---|---|
| R1 | Ohne Contract keine Unicast-Kommunikation zwischen EPGs (Implicit Deny), außer VRF unenforced oder beide in der Preferred Group | `Engine.packet` | `test_start_state`, `test_wrong_port` | [CG]: „Without a contract between EPGs, no unicast communication is possible between those EPGs“ |
| R2 | Innerhalb einer EPG ist kein Contract nötig | `Engine.packet` | `test_same_epg_and_isolation` | [CG]: „A contract is not required to allow communication between endpoints in the same EPG“ |
| R3 | Intra-EPG Isolation verbietet Verkehr innerhalb der EPG | `Engine.packet` | `test_same_epg_and_isolation` | [CG] Tabelle 1: „Deny communication between endpoints in the EPG“ |
| R4 | Der Consumer baut zum Provider auf; die Filter gelten Consumer → Provider | `Engine.packet` | `test_swapped_consumer_provider`, `test_provider_cannot_initiate` | [CG] „Subjects and filters“ |
| R5 | *Apply Both Directions* + *Reverse Filter Ports* (beide Default): Rückrichtung mit getauschten Ports | `Engine.packet`, `trace._policy` | `test_solution_passes` | [CG]: „with source and destination ports reversed for the provider-to-consumer direction“ |
| R6 | Ohne *Reverse Filter Ports* passt die Antwort (Quell-Port 443) nicht auf den Filter (Ziel-Port 443) | `Engine._entry_match` | `test_reply_needs_reverse_ports` | aus R5 abgeleitet |
| R7 | Contracts filtern zustandslos; die Antwort braucht eine eigene passende Regel | `trace._policy` prüft Anfrage und Antwort getrennt | `test_reply_needs_reverse_ports` | [CG]: „Zoning-rule entries are used to perform stateless filtering“ |
| R8 | Ein Filter-Entry passt nur auf sein IP-Protokoll: ein TCP-Filter gibt kein ICMP frei | `Engine._entry_match` | `test_icmp_not_permitted_by_tcp_filter`, `test_wrong_protocol` | [CG] „Create a filter“ (Entry-Felder); ICMP als eigenes Protokoll nicht wörtlich belegt |
| R9 | EtherType *unspecified* passt auf allen Verkehr | `Engine._entry_match`, `assess._entry_ok` | `test_permit_any_fails_security` | [CG]: „If EtherType is ‚Unspecified,‘ … this filter matches all EtherTypes“ |
| R10 | vzAny steht für alle EPGs im VRF; als Consumer und Provider entsteht eine Any-to-any-Regel | `Engine._classes`, `Engine.packet` | `test_vzany_provider_is_too_wide`, `test_vzany_consumer_is_too_wide` | [CG] „vzAny“ |
| R11 | Unenforced VRF: alle EPGs dürfen alles | `Engine.packet` | `test_unenforced_vrf_is_too_wide` | [CG] „Unenforced mode“ |
| R12 | Preferred Group: Mitglieder brauchen untereinander keinen Contract; Default *Excluded* | `Engine.packet` | `test_preferred_group` | [CG] „Preferred group“ |
| R13 | Deny-Regeln haben Vorrang vor Permit | `Engine.packet` | `test_deny_filter_wins` | [CG] („deny rules, which have higher priority“); die Prioritätsstufen nach Spezifität sind **vereinfacht** |
| R14 | Routing (Gateway, Pervasive Route) ersetzt keine Policy-Freigabe | `trace.run`: Routing-Schritte vor `_policy` | `test_start_state` (Gateway ok, Policy-Drop) | Modellannahme, [CG] R1 |
| R15 | Ein Contract ersetzt keine Anbindung: Ohne gelernten Endpoint kein Verkehr | `trace._host_checks` | `test_missing_access_path` | Modellannahme |
| R16 | Eine Freigabe ersetzt keinen Dienst: Der Zielport muss offen sein | `trace._service_available` | `test_permit_does_not_create_service` | simulator-spezifisch (Hosts mit `services`) |
| R17 | Subjects mit getrennten Filtern je Richtung werden nicht ausgewertet | `Engine.packet` (`unsupported`) | `test_unsupported_unidirectional_subject` | ehrliche Grenze, kein Cisco-Verhalten |

## Diagnosemodell des Traffic-Tests

Die Reihenfolge ist ein Lernmodell, keine Hardware-Pipeline:

1. Eingabe gültig? (sonst `UNRESOLVED`)
2. Quelle und Ziel als Endpoint gelernt? (Access-Kette, Encap, Domain, Static Path)
3. Bridging oder Routing? Gleiches Subnetz: gleiche BD und ARP. Sonst Gateway, IP-Learning, Route Leaking, Zielsubnetz
4. Fabric-Pfad zwischen den Leafs (Spine, IPN, WAN)
5. Policy für die Anfrage (Consumer → Provider)
6. Service Graph, falls am Subject
7. Zieldienst erreichbar?
8. Policy für die Antwort
9. Extern: Klassifizierung im External EPG, Route am Border Leaf, Rückweg vom externen Router

## Ergebnisformat

`trace.run` liefert:

| Feld | Inhalt |
|---|---|
| `verdict` | `ALLOW`, `DROP` oder `UNRESOLVED` |
| `reason` | Reason Code (simulator-spezifisch, siehe unten) |
| `explanation` | deutsche Erklärung am Fehlerort |
| `failedAt` | Schritt, Titel und Ebene (`endpoint`, `l2`, `l3`, `fabric`, `policy`, `service`, `external` …) |
| `policy` | angewendete Policy für Anfrage und Antwort: Art (`contract`, `implicit-deny`, `same-epg` …), Contract, Subject, Filter, Entry, Richtung |
| `refs` | beteiligte Objekte (DNs) |
| `hint` | nächster sinnvoller Prüfschritt |
| `steps` | alle Prüfungen mit Ergebnis |
| `ok` | wie bisher: `true` nur bei `ALLOW` |

## Reason Codes

Die Codes sind Eigenbezeichnungen des Simulators und keine Cisco-Codes.

| Code | Bedeutung |
|---|---|
| `ALLOWED` | Anfrage und Antwort kommen an |
| `INPUT_INVALID`, `INPUT_PORT_MISSING` | Eingabe nicht bewertbar (`UNRESOLVED`) |
| `EP_NOT_LEARNED` | Endpoint nicht gelernt (Access-Kette, Encap, Domain, Path) |
| `L2_LOOP`, `L2_DIFFERENT_BD`, `ARP_UNRESOLVED` | Layer-2-Probleme |
| `GATEWAY`, `IP_NOT_LEARNED`, `NO_ROUTE`, `ROUTE_LEAK_MISSING` | Layer-3-Probleme |
| `FABRIC_PATH_DOWN` | kein Pfad zwischen den Leafs |
| `POLICY_IMPLICIT_DENY`, `POLICY_DENY_FILTER`, `POLICY_TABOO`, `POLICY_INTRA_EPG_ISOLATION`, `POLICY_ESG_EPG` | Policy verwirft die Anfrage |
| `POLICY_REPLY_DENY` | Anfrage erlaubt, Antwort verworfen |
| `POLICY_UNSUPPORTED` | Konfiguration nutzt nicht ausgewertete Funktion (`UNRESOLVED`) |
| `SERVICE_GRAPH` | Service Graph, PBR oder Firewall |
| `SERVICE_UNAVAILABLE` | Netz erlaubt, Dienst am Ziel nicht offen |
| `EXT_CLASSIFICATION`, `EXT_ROUTER`, `EXT_NO_RETURN_ROUTE` | externe Kommunikation |
| `OTHER` | Fehlerort ohne eigenen Code; Details im Schritt |
