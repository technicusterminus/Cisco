# ACI-Referenzprofil und Regelbasis

Datacenter Prep ist ein **eigenständiger didaktischer ACI-Simulator**. Er ist kein APIC und keine Nexus-Emulation und verspricht keine vollständige ACI-Kompatibilität. Diese Seite legt fest, wogegen der Simulator sich messen lässt und was er davon abdeckt.

## 1. Referenzbasis

| | |
|---|---|
| Referenz-Version | APIC 6.0(5h), Switches n9000-16.0(5h). Die Version wird im Simulator angezeigt, z. B. bei `topSystem` und im Firmware-Bereich |
| Dokumentationsbasis | *Cisco APIC Basic Configuration Guide, Release 6.0(x)* · *Cisco APIC Security Configuration Guide* (Contracts, Taboo, Preferred Group, vzAny) · *Cisco APIC Layer 3 Networking Configuration Guide* (L3Out, Shared Services) · *Cisco ACI Contract Guide* (White Paper) · *ACI Fabric Endpoint Learning* (White Paper) · *Cisco APIC REST API Configuration Guide* · *APIC Management Information Model Reference* |
| Stand der Prüfung | **Keine Regel wurde in dieser Umgebung online gegen die Quelle geprüft**, weil `cisco.com` aus der Entwicklungsumgebung gesperrt ist. Die Regeln stammen aus Fachwissen über die genannten Dokumente. Zum Gegenprüfen gibt es `werkzeuge/abgleich.py` (REST-Abgleich mit einem echten APIC) und `werkzeuge/ABGLEICH.md` (Prüfliste). |

Status-Begriffe in dieser Datei:

- **umgesetzt + getestet**: Das Verhalten ist implementiert, und ein automatischer Test hält es fest.
- **umgesetzt**: Das Verhalten ist implementiert, ein eigener Test fehlt.
- **vereinfacht**: Implementiert, aber bewusst gröber als ACI. Die Abweichung ist beschrieben.
- **nicht unterstützt**: Der Simulator lehnt es ab, ignoriert es oder zeigt es nur an. Das ist jeweils angegeben.

## 2. Simulationsumfang

| Bereich | Status | Bemerkung |
|---|---|---|
| Fabric: APIC, Spine, Leaf, Node-ID, Rollen, Links | umgesetzt + getestet | Discovery mit Registrierung (Schritte nach Zeit), Fabric-Links als Topologie |
| Tenant, VRF, BD, Subnet, AP, EPG | umgesetzt + getestet | Defaults siehe Abschnitt 4 |
| Access Policies: VLAN-Pool, Domain, AAEP, Policy Group, Interface-/Switch-Profil, Static Path | umgesetzt + getestet | Die Kette wird vollständig ausgewertet. Fehlt ein Glied, wird der Endpoint nicht gelernt, und es gibt einen Fault |
| vPC, Port-Channel, LACP | umgesetzt | Explicit Protection Group, LACP-Partnerzustand |
| Endpoint Learning (MAC/IP, EPG, Leaf, Interface) | umgesetzt + getestet | stille Hosts, ARP Flooding/Glean, Limit IP Learning |
| Endpoint Move als Ereignis | umgesetzt + getestet | Umstecken eines Hosts ergibt Ereignis S9101 (gebundener Port) bzw. Verlust und neues Lernen. Endpoint-Verlauf je Host im EP Tracker. Event-Codes S91xx sind simulator-spezifisch |
| Link-Ausfall, deaktivierter Port | umgesetzt + getestet | Kabel/NIC-Ausfall als simulator-spezifisches Host-Ereignis (`LINK_DOWN`, Events S9102/S9103). Disabled Interface wie beim APIC über `fabricRsOosPath` (`PORT_ADMIN_DOWN`) |
| Contracts, Subjects, Filter, Consumer/Provider | umgesetzt + getestet | zustandslos, Reverse Filter Ports, Stateful-ACK, Scope, Deny-Aktion |
| Subject ohne „Apply Both Directions“ (vzInTerm/vzOutTerm) | **nicht unterstützt** | Die Klassen gibt es im Modell nicht |
| Intra-EPG Isolation und Intra-EPG-Contract | umgesetzt + getestet | „enforced“ verbietet allen Verkehr innerhalb der EPG. Ein Intra-EPG-Contract (`fvRsIntraEpg`) erlaubt innerhalb der EPG nur, was seine Filter zulassen (`POLICY_INTRA_EPG_CONTRACT`, `_DENY`). Kombination mit Isolation: Der Contract gilt – nicht gegen die Doku geprüft. Erscheint nicht in `show zoning-rule` |
| Preferred Group, vzAny, VRF unenforced, Taboo | umgesetzt | eigene Labs 04 und 11; Prioritäten vereinfacht (Deny vor Permit, keine Priority-Stufen) |
| ESG, uSeg EPG | umgesetzt | Lab 23 |
| Inter-VRF / Shared Services | umgesetzt | Lab 13: Shared-Subnetze und Contract-Scope |
| L3Out OSPF, eBGP, EIGRP, statisch, External EPG, Route Control | umgesetzt | simulierte externe Router mit Nachbarschafts-Zustandsautomat (vereinfacht) |
| Service Graph mit PBR | vereinfacht | nur Firewall mit Redirect, keine Device Packages |
| Multi-Pod, Remote Leaf, Multi-Site (NDO) | vereinfacht | siehe README, Abschnitt *Grenzen* |
| Faults | vereinfacht | echte Codes nur, wo bekannt (z. B. F0467). Simulator-eigene Faults haben das Präfix **S** |
| Datenebene | **nicht unterstützt** | Es fließen keine Pakete. Der Traffic-Test berechnet die Entscheidung aus Konfiguration und Zustand |
| Zieldienst auf Hosts | simulator-spezifisch | Feld *Dienste* (z. B. `tcp/443`). Leer bedeutet: Der Host antwortet auf jedem Port |
| REST-API | Teilumfang | Abfragen und Fehler im APIC-Format. Unbekannte Attribute werden ohne `--strict` angenommen |
| CLI | Teilumfang | Liste unter `help`. Ausgaben kommen aus dem Engine-Zustand, das Layout ist an NX-OS angelehnt und nicht bitgenau. Die Befehlsnamen stammen aus der Cisco-Dokumentation und sind nicht gegen ein Gerät geprüft; `show snapshot`, `show export-config`, `show snmp`, `show logging server` sind in dieser Form nicht belegt und als simulator-spezifisch [S] markiert (`SIM_ONLY_APIC` in `cli.py`). Nicht unterstützte Befehle melden „In der Simulation nicht unterstützt“ mit Diagnoseweg. Nur lesend, keine Shell |

## 3. Connectivity-Engine: Diagnosemodell

Ein Test `src → dst, Protokoll, Port` durchläuft diese Schritte (`trace.py`). Die Reihenfolge ist ein **didaktisches Diagnosemodell**, keine Hardware-Pipeline.

1. Quelle und Ziel auflösen (Host, Router, IP, Gateway) → sonst `UNRESOLVED / INPUT_INVALID`
2. Endpoint der Quelle gelernt. Ist kein Link des Hosts nutzbar → `LINK_DOWN`, `PORT_ADMIN_DOWN`, `PORT_ERR_DISABLED`, `SWITCH_INACTIVE` (Ebene *physical*). Sonst prüft der Schritt Access-Kette, Encap im Pool und Domain an der EPG → `EP_NOT_LEARNED`
3. Endpoint des Ziels gelernt → `EP_NOT_LEARNED`
4. Bridging (gleiches Subnetz): gleiche BD, ARP → `L2_DIFFERENT_BD`, `ARP_UNRESOLVED`
5. Routing (anderes Subnetz): Gateway, BD-Subnetz, VRF, Leaking → `GATEWAY_INVALID`, `ROUTE_MISSING`, `INTERVRF_LEAK_MISSING`
6. Fabric-Pfad (Spine, Pods) → `FABRIC_PATH_DOWN`
7. Policy der Anfrage (`Engine.packet`) → `POLICY_*`
8. Zieldienst (simulator-spezifisch) → `SERVICE_NOT_LISTENING`
9. Policy der Antwort → `POLICY_REPLY_DENIED`
10. Extern: Route auf dem Border Leaf, Klassifizierung im External EPG, Rückweg des externen Routers → `ROUTE_MISSING`, `EXT_EPG_NO_MATCH`, `RETURN_ROUTE_MISSING`

Das Ergebnis hat diese Felder:

- `verdict` (ALLOW, DROP, UNRESOLVED)
- `reason` (Code)
- `location` (Schritt)
- `explain` (deutscher Text)
- `hint` (nächster Diagnoseschritt)
- `policy`: angewandte Regel je Richtung mit Contract, Filter, Entry und Richtung
- `path`: Leafs von Quelle und Ziel
- `steps`: alle Schritte

Alle Reason Codes sind **simulator-spezifisch**.

## 4. Relevante Defaults (aus `model.py`)

| Klasse | Defaults |
|---|---|
| fvCtx | pcEnfPref=enforced, pcEnfDir=ingress, ipDataPlaneLearning=enabled |
| fvBD | unicastRoute=yes, arpFlood=no, unkMacUcastAct=proxy, unkMcastAct=flood, multiDstPktAct=bd-flood, limitIpLearnToSubnets=yes, ipLearning=yes |
| fvSubnet | scope=private, preferred=no, virtual=no, ctrl=nd |
| fvAEPg | pcEnfPref=unenforced (Intra EPG Isolation aus), prefGrMemb=exclude, floodOnEncap=disabled, shutdown=no |
| vzBrCP | scope=context |
| vzSubj | revFltPorts=yes, consMatchT=AtleastOne, provMatchT=AtleastOne |
| vzEntry | etherT=unspecified, prot=unspecified, Ports unspecified, stateful=no, applyToFrag=no |
| fvRsPathAtt | mode=regular, instrImedcy=lazy |

`werkzeuge/abgleich.py --write` vergleicht genau diese Defaults mit einem echten APIC.

## 5. Regelbasis

Jede Regel nennt die Quelle (Dokument) und ihren Status. Die Testreferenz zeigt, wo die Regel automatisch geprüft wird.

| # | Regel | Quelle | Status | Test |
|---|---|---|---|---|
| R-01 | Zwischen zwei verschiedenen EPGs ohne passenden Contract wird verworfen (Whitelist, Implicit Deny). | Security Config Guide, *Contracts* | umgesetzt + getestet | `test_acceptance.TestStartState` |
| R-02 | Innerhalb einer EPG ist Verkehr ohne Contract erlaubt. Intra EPG Isolation „enforced“ verbietet ihn, ein Intra-EPG-Contract erlaubt nur seine Filter. | Security Config Guide, *Intra-EPG Isolation*, *Intra-EPG Contracts* | umgesetzt + getestet | `TestConnectivityCases`, `TestSegmentationLabs` |
| R-03 | Der Consumer baut auf, der Provider bietet den Dienst an. Ein Filter-Entry gilt Consumer → Provider wie definiert. | Contract Guide | umgesetzt + getestet | `test_swapped_roles_fail_function` |
| R-04 | Contracts sind zustandslos. Mit *Reverse Filter Ports* erlaubt das Subject die Gegenrichtung mit vertauschten Ports. Ohne die Option passt die Antwort nicht. | Contract Guide, *Subject* | umgesetzt + getestet | `test_without_reverse_filter_ports_reply_is_dropped` |
| R-05 | *Stateful* am Entry: Provider → Consumer nur TCP mit ACK. | Contract Guide, *Filter Entry* | umgesetzt + getestet (ohne Sequenznummern) | `test_stateful_entry_blocks_provider_syn_from_service_port` |
| R-06 | Ein TCP-Filter gibt kein ICMP frei. Ein Entry mit EtherType/Protokoll *unspecified* passt auf alles. | Contract Guide | umgesetzt + getestet | `test_reference_solution_passes_everything`, `test_permit_any_shortcut_fails_least_privilege` |
| R-07 | Contract-Scope (application-profile, context, tenant, global) begrenzt, zwischen welchen EPGs er wirkt. | Contract Guide, *Scope* | umgesetzt | Lab 13 |
| R-08 | Deny-Filter vor Permit bei gleicher Priorität; ein Taboo Contract an der Ziel-EPG verwirft vor allen Contracts. | Security Config Guide | vereinfacht (keine Priority-Stufen) | Lab 11 |
| R-09 | VRF *unenforced* erlaubt allen Verkehr im VRF. | Basic Config Guide, *VRF* | umgesetzt | Engine |
| R-10 | Preferred Group: Mitglieder untereinander ohne Contract, sofern am VRF (vzAny) aktiviert. | Security Config Guide | umgesetzt | Engine |
| R-11 | Routing zwischen BDs eines VRF braucht Unicast Routing und ein BD-Subnetz als Gateway. Routing ersetzt keine Policy-Freigabe. | Basic Config Guide, *Bridge Domains* | umgesetzt + getestet | `test_https_fails_with_policy_reason_not_network`, `TestConnectivityCases` |
| R-12 | Ein Endpoint wird nur gelernt, wenn Static Path, VLAN im Pool der Domain, Domain an der EPG, AAEP und Interface Policy zusammenpassen; sonst Fault F0467 an der EPG. | Basic Config Guide, *Access Policies*; Fault Reference F0467 | umgesetzt + getestet | `test_broken_access_does_not_count_as_policy_block`, Lab 02/07 |
| R-13 | Gateway antwortet auf ICMP; andere Protokolle zum Pervasive Gateway werden nicht beantwortet. | Basic Config Guide | vereinfacht | Engine |
| R-14 | Zwischen VRFs braucht es Contract mit passendem Scope und Subnetze „Shared between VRFs“. | L3 Networking Config Guide, *Shared Services* | umgesetzt | Lab 13 |
| R-15 | External EPG klassifiziert per Subnetz mit „External Subnets for the External EPG“ (Longest Prefix Match). Der Rückweg braucht ein exportiertes BD-Subnetz (Advertised Externally) beim externen Router. | L3 Networking Config Guide | umgesetzt | Labs 06, 09, 15 |

Unsicherheiten, die beim Abgleich zuerst geprüft werden sollten: R-08 (Prioritäten zwischen vzAny-, EPG- und Taboo-Regeln), R-13 (welche Protokolle das Pervasive Gateway beantwortet), R-02 (Kombination aus Isolation und Intra-EPG-Contract) und die Fault-Codes außer F0467.
