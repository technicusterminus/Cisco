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
| Subject ohne „Apply Both Directions“ (vzInTerm/vzOutTerm) | umgesetzt | `vzInTerm` (`intmnl`, Consumer → Provider) und `vzOutTerm` (`outtmnl`, Provider → Consumer) mit `vzRsFiltAtt`; je Richtung eigene Filter ohne Port-Tausch, in `show zoning-rule` als `uni-dir` |
| Intra-EPG Isolation und Intra-EPG-Contract | umgesetzt + getestet | „enforced“ verbietet allen Verkehr innerhalb der EPG. Ein Intra-EPG-Contract (`fvRsIntraEpg`) erlaubt innerhalb der EPG nur, was seine Filter zulassen (`POLICY_INTRA_EPG_CONTRACT`, `_DENY`). Kombination mit Isolation: Der Contract gilt – nicht gegen die Doku geprüft. Erscheint nicht in `show zoning-rule` |
| Preferred Group, vzAny, VRF unenforced, Taboo | umgesetzt | eigene Labs 04 und 11; Zoning-Rule-Prioritäten nach Contract Guide (siehe R-08) |
| ESG, uSeg EPG | umgesetzt | Lab 23 |
| Inter-VRF / Shared Services | umgesetzt | Lab 13: Shared-Subnetze und Contract-Scope |
| L3Out OSPF, eBGP, EIGRP, statisch, External EPG, Route Control | umgesetzt | simulierte externe Router mit Nachbarschafts-Zustandsautomat (vereinfacht) |
| Service Graph mit PBR | vereinfacht | nur Firewall mit Redirect, keine Device Packages |
| Multi-Pod, Remote Leaf, Multi-Site (NDO) | vereinfacht | siehe README, Abschnitt *Grenzen* |
| Faults | vereinfacht | echter Code nur F0467 (belegt). Alle anderen Faults, auch der Test-Fault aus dem Monitoring (S9100), haben das Präfix **S** und sind simulator-spezifisch |
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

Codes der Policy-Entscheidung (Schritt *Policy Anfrage* / *Policy Antwort*):

| Code | Bedeutung |
|---|---|
| `POLICY_CONTRACT_PERMIT` | ein Contract-Filter erlaubt (Regel mit Priorität im Text, z. B. `fully_qual(7)`) |
| `POLICY_DENY_RULE` | ein Filter mit Aktion deny gewinnt (gleiche oder höhere Priorität) |
| `POLICY_IMPLICIT_DENY` | keine passende Regel, implizites Deny (oder Deny der Preferred Group für Nicht-Mitglieder) |
| `POLICY_REPLY_DENIED` | Anfrage erlaubt, Antwort nicht (zustandslose Contracts) |
| `POLICY_TABOO` | Taboo Contract an der Ziel-EPG |
| `POLICY_PREFERRED_GROUP` | beide Seiten in der Preferred Group, kein Contract mit höherer Priorität |
| `POLICY_VRF_UNENFORCED` | VRF unenforced |
| `POLICY_SAME_EPG` | Quelle und Ziel in derselben EPG |
| `POLICY_INTRA_EPG_ISOLATION` / `POLICY_INTRA_EPG_CONTRACT` / `POLICY_INTRA_EPG_CONTRACT_DENY` | Intra-EPG Isolation bzw. Intra-EPG-Contract |
| `POLICY_ESG_EPG_MIX` | Contract zwischen ESG und EPG (nicht möglich) |
| `POLICY_TRANSIT_DENIED` | Transit Routing ohne passenden Contract zwischen den External EPGs |
| `POLICY_IMPLICIT_PROTOCOL` | implizit erlaubtes Protokoll (DHCP, R-16) |
| `POLICY_IMPLICIT_CLASS1` | Quelle/Ziel als Class-ID 1 klassifiziert (L3Out-Interface-Subnetz, R-19) |

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
| R-08 | Zuerst entscheidet die Zoning-Rule-Priorität (kleinere Zahl gewinnt): EPG-to-EPG `fully_qual(7)` / mit any-Filter `src_dst_any(9)`, EPG-to-vzAny 13/15, vzAny-to-EPG 14/16, vzAny-to-vzAny 17/21, ESG-to-vzAny und vzAny-to-ESG sowie Inter-VRF-Provider-EPG (globaler pcTag) ↔ vzAny im Consumer-VRF `shsrc_any_filt_perm(10)` / `shsrc_any_any_perm(11)` (für vzAny → globale Provider-EPG nennt Table 8 keine eigene Zeile; angenommen wie ESG, gleiche Begründung: globaler pcTag); Taboo `black_list(5)` vor allen Contracts. Erst bei gleicher Priorität gewinnt Deny, auch gegen einen spezifischeren Permit-Filter. Zwischen Permit und Redirect entscheidet die Filter-Priorität (Table 23), bei Gleichstand Redirect. | Contract Guide, *Contract priorities* (Table 8, Table 23) | umgesetzt + getestet; nicht modelliert: Rule Expansion für Inter-VRF vzAny-to-ESG (Appendix, ab 6.1(2)), Wirkung von `priorityOverride` (Werte `level1`–`level3` belegt, Zuordnung zu lowest/medium/highest nicht belegt) | `TestContractPriorities`, `test_lab23_esg_vzany_rules_use_priority_10`, Lab 11 |
| R-09 | VRF *unenforced* erlaubt allen Verkehr im VRF. | Basic Config Guide, *VRF* | umgesetzt | Engine |
| R-10 | Preferred Group: Mitglieder untereinander ohne Contract, sofern am VRF (vzAny) aktiviert (`grp_any_any_any_permit(20)`). Contracts mit höherer Priorität (z. B. Deny 7) gewinnen. Ist eine Seite kein Mitglied, verwerfen `grp_src_any_any_deny(18)` / `grp_any_dest_any_deny(19)` alles, was nicht mit Priorität ≤ 17 erlaubt ist. | Contract Guide, *Preferred group*, Table 8 | umgesetzt + getestet | `TestContractPriorities` |
| R-11 | Routing zwischen BDs eines VRF braucht Unicast Routing und ein BD-Subnetz als Gateway. Routing ersetzt keine Policy-Freigabe. | Basic Config Guide, *Bridge Domains* | umgesetzt + getestet | `test_https_fails_with_policy_reason_not_network`, `TestConnectivityCases` |
| R-12 | Ein Endpoint wird nur gelernt, wenn Static Path, VLAN im Pool der Domain, Domain an der EPG, AAEP und Interface Policy zusammenpassen; sonst Fault F0467 an der EPG mit Ursache `invalid-vlan`, `invalid-path` oder `encap-already-in-use`. Text im Format des TechNote: `Configuration failed for <EPG-DN> node <id> <port> due to <Titel>, debug message: <cause>: <Text>;` (belegt sind die drei Texte; weitere Unterfälle wie fehlendes Encap oder Port im Port-Channel sind simulator-spezifisch formuliert). Der Simulator hängt den Fault an die EPG (im APIC: unter `uni/epp/fv-[…]/node-…/stpathatt-[…]/nwissues`, sichtbar im Tab Faults der EPG). `show vlan encap-id <n> extended` ist leer, solange das Encap nicht deployed ist. | Basic Config Guide, *Access Policies*; Cisco TechNote 220876 *Troubleshoot Address ACI Fault Code F0467* | umgesetzt + getestet | `test_broken_access_does_not_count_as_policy_block`, `test_f0467_texts_follow_technote`, Lab 02/07/44 |
| R-13 | Gateway antwortet auf ICMP; andere Protokolle zum Pervasive Gateway werden nicht beantwortet. | Basic Config Guide | vereinfacht | Engine |
| R-14 | Zwischen VRFs braucht es Contract mit passendem Scope und Subnetze „Shared between VRFs“. Der Provider bekommt einen globalen pcTag (< 16384). `show zoning-rule`: Contract-Regeln und `provider → 0 shsrc_any_any_deny(12)` im Consumer-VRF, im Provider-VRF nur `provider → 14 permit_override src_dst_any(9)` (Contract Guide, *Consumer VRF enforcement*). vzAny kann bei Inter-VRF-Contracts nur Consumer sein (dann leakt die Route, `test_lab13_vzany_consumes_inter_vrf_contract`); als Provider leakt nichts, der Traffic Inspector nennt den Grund (`test_lab13_vzany_cannot_provide_inter_vrf_contract`). | L3 Networking Config Guide, *Shared Services* | umgesetzt | Lab 13 |
| R-15 | External EPG klassifiziert per Subnetz mit „External Subnets for the External EPG“ (Longest Prefix Match). Der Rückweg braucht ein exportiertes BD-Subnetz (Advertised Externally) beim externen Router. | L3 Networking Config Guide | umgesetzt | Labs 06, 09, 15 |
| R-16 | DHCPv4 (UDP 68 → 67 und 67 → 68) ist ohne Contract erlaubt; Deny, Redirect und Taboo greifen nicht. Reason Code `POLICY_IMPLICIT_PROTOCOL` (simulator-spezifisch). Nicht modelliert: Abschalten der impliziten DHCP-Regel, die übrigen implizit erlaubten Protokolle (OSPF, EIGRP, PIM, IGMP, ND), weil der Traffic-Test nur ICMP/TCP/UDP kennt. | Contract Guide, *FAQ* | umgesetzt + getestet | `test_dhcp_is_implicitly_permitted` |
| R-17 | Directive `log` an der Filter-Relation: `show zoning-rule` zeigt `deny,log` bzw. `log,permit`; die Priorität ändert sich nicht; bei gleicher Priorität gewinnt Deny+Log vor Deny. Paket- und Flow-Logs (`show logging ip access-list`) sind nicht modelliert. | Contract Guide, *Log*, *Priorities between actions* | umgesetzt + getestet | `test_log_directive_in_zoning_rule_and_decision` |
| R-18 | `show zoning-rule` (auch mit `src-epg`, `dst-epg`, `scope`, `contract <Tenant:Contract>`; Spalte Name als `Tenant:Contract`), `show zoning-filter` und `show system internal policy-mgr stats` (Zeilenformat des Guide; Pkts zählt Treffer aus Traffic-Tests, Ingress/Egress/RevPkts bleiben 0) folgen den Beispielen des Contract Guide: implizite Regeln (any_any_any(21), implarp, 0 → 15, 0 → BD-pcTag any_dest_any(16)), VRF unenforced nur eine Permit-Regel, Preferred Group mit grp_any_any_any_permit(20) und grp_src/any_dest-Denies (18/19) für Nicht-Mitglieder, Intra-EPG Isolation/Contract mit class-eq-deny(2) und class-eq-filter(1), Taboo black_list(5), Reverse Filter Ports mit eigener Filter-ID (Ports vertauscht, Prio sport; bei Stateful TcpRules ack). Rule-IDs, pcTags und Scopes vergibt der Simulator; die Prio-Bezeichnung für Entries mit Quell- *und* Ziel-Port ist nicht belegt (angezeigt: dport). | Contract Guide, *show zoning-rule*, *show zoning-filter*, *Implicit rules*, *Preferred group*, *Microsegmentation*, *Taboo* | umgesetzt + getestet | `test_zoning_tables_follow_contract_guide` |
| R-19 | Ein External EPG mit 0.0.0.0/0 (import-security) nutzt in `show zoning-rule` Sonder-Class-IDs: als Ziel 15, als Quelle die Class-ID des VRF; beide Regeln uni-dir. Hat das External EPG weitere Subnetze, gibt es zusätzlich Regeln mit seinem eigenen pcTag. Passt das External EPG nur über 0.0.0.0/0, gilt die Interface-Adresse eines simulierten Routers im L3Out-Interface-Subnetz als Class-ID 1: Anfragen von ihr sind implizit erlaubt (Regel 1 → 0); Antworten nur, wenn das Ziel am selben Leaf hängt, sonst greift die Regel zu Class-ID 15. Ziel-Richtung (Host → Router-Adresse) nur am selben Leaf implizit erlaubt. Reason Code `POLICY_IMPLICIT_CLASS1` (simulator-spezifisch). Abhilfe wie im Guide: Interface-Subnetz ins External EPG aufnehmen (Musterlösung Lab 09). Nicht modelliert: Abhängigkeit vom Endpoint-Lernzustand. | Contract Guide, *L3Out EPG with 0.0.0.0/0 subnet* (Figures 125–132), *FAQ* (Implicit rule 1 → 0) | umgesetzt + getestet | `test_lab09_default_route_external_epg_uses_special_class_ids`, `test_lab09_transfer_subnet_is_class1_without_explicit_subnet` |
| R-20 | Rogue EP Control (`epControlP`, `uni/infra/epCtrlP-default`; Defaults 60 s, Faktor 4, Hold 1800 s): springende Endpoints werden als rogue markiert und statisch gehalten, nur für sie pausiert das Lernen. Kein Port wird abgeschaltet, das Lernen im BD bleibt an; Ep Loop Protection greift bei aktiver Rogue EP Control nicht. Die Schleife selbst bricht Rogue EP Control nicht. Fault mit S-Code S2536 (Paper nennt keinen Code). Nicht modelliert: Zählung pro Leaf und getrennt nach MAC/IP, Hold-Timer-Ablauf, Rogue/COOP Exception List. Die Defaults der Paper-Tabelle weichen von anderen Quellen (net-as-code: 30 s, Faktor 10) ab; verwendet sind die Werte aus dem Cisco-Paper. | Cisco White Paper *ACI Fabric Endpoint Learning*, *Rogue EP Control*, *Ep Loop Protection*; Klasse/Attribute: aci-go-client `ep_control_p.go` | umgesetzt + getestet | `test_lab28_rogue_ep_control_quarantines_endpoints_only` |

Fault-Lebenszyklus: Der Simulator kennt `lc` = soaking, raised und retaining (Severity cleared). Die Zwischenzustände soaking-clearing und raised-clearing sowie das Clearing-Intervall fehlen; Standarddauern sind 0, die APIC-Defaults sind nicht gegen ein Gerät geprüft.

Mit dem *Cisco ACI Contract Guide* (White Paper, Stand Oktober 2026, vom Benutzer bereitgestellt) gegengeprüft: R-02 (Intra-EPG-Contract bringt `class-eq-deny(2)` mit), R-03 bis R-06, R-08, R-10, die impliziten Regeln in `show zoning-rule` und die Richtungsangaben `bi-dir` / `uni-dir-ignore` / `uni-dir`. Unsicherheiten, die beim Abgleich zuerst geprüft werden sollten: R-13 (welche Protokolle das Pervasive Gateway beantwortet), die Wirkung von `priorityOverride` und die Fault-Codes außer F0467.
