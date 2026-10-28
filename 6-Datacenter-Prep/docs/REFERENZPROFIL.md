# ACI-Referenzprofil

Datacenter Prep ist ein eigenständiger, didaktischer ACI-Simulator. Er ist kein APIC und keine Nexus-Emulation. Dieses Profil sagt, wogegen das Verhalten geprüft ist, was fachlich umgesetzt ist, was bewusst vereinfacht ist und was fehlt.

## Dokumentationsbasis

| Bereich | Bezug |
|---|---|
| Objektmodell, Klassennamen, Attribute | APIC Management Information Model, Release 6.0(x); Klassen wie `fvTenant`, `fvAEPg`, `vzBrCP`, `vzSubj`, `vzEntry` |
| Contracts | [Cisco ACI Contract Guide](https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-743951.html) (White Paper c11-743951) |
| Bedienung, Begriffe | Cisco APIC Basic Configuration Guide, Release 6.0(x); Cisco APIC Layer 3 Networking Configuration Guide, Release 6.0(x) |
| Firmware-Stand in Labs | APIC 6.0(5h) bzw. 6.0(6c) als Beispielversionen |

Einzelregeln mit Quelle stehen in der [Regelbasis](REGELBASIS.md). Wo eine Regel nicht gegen die Dokumentation geprüft werden konnte, steht das dort.

## Status der Funktionen

**Umgesetzt** heißt: Die Engine wertet es aus, und Tests prüfen es. **Vereinfacht** heißt: Die Engine wertet es aus, aber gröber als ein echtes System. **Nicht unterstützt** heißt: Die Konfiguration wird höchstens gespeichert. Ein Traffic-Test, der davon abhängt, endet mit `UNRESOLVED`, soweit der Simulator das erkennt.

### Policy und Connectivity (Kern der Lernplattform)

| Funktion | Status | Anmerkung |
|---|---|---|
| Implicit Deny zwischen EPGs im enforced VRF | umgesetzt | Reason `POLICY_IMPLICIT_DENY` |
| Verkehr innerhalb einer EPG ohne Contract | umgesetzt | |
| Intra-EPG Isolation (`pcEnfPref=enforced` an der EPG) | umgesetzt | Reason `POLICY_INTRA_EPG_ISOLATION` |
| Intra-EPG Contract (`fvRsIntraEpg`) | nicht unterstützt | wird gespeichert, nicht ausgewertet |
| Consumer/Provider, Subject mit *Apply Both Directions* und *Reverse Filter Ports* | umgesetzt | Anfrage und Antwort werden getrennt geprüft |
| Subject mit getrennten Filtern je Richtung (`vzInTerm`/`vzOutTerm`) | nicht unterstützt | Traffic-Test meldet `UNRESOLVED` / `POLICY_UNSUPPORTED` |
| Filter-Entries: EtherType, IP-Protokoll, Quell-/Ziel-Portbereiche, benannte Ports (`http`, `https`, `dns` …) | umgesetzt | |
| TCP-Flag `est` (Stateful-Option) | vereinfacht | Antwort mit ACK passt, Verbindungsaufbau nicht |
| Deny-Filter im Contract | vereinfacht | Deny gewinnt immer vor Permit; echte Priorität hängt von der Spezifität ab |
| Contract-Scope (Application Profile, VRF, Tenant, Global) | umgesetzt | |
| vzAny als Consumer/Provider | umgesetzt | |
| Preferred Group | umgesetzt | Mitglieder ohne Contract erlaubt, Nicht-Mitglieder brauchen Contracts |
| Unenforced VRF | umgesetzt | alles erlaubt |
| Taboo Contracts | umgesetzt | |
| Shared Services (Inter-VRF) | vereinfacht | Contract-Scope, Provider-Subnetz an der EPG, Consumer-Subnetz *Shared between VRFs*; keine pcTag-Zuteilungsdetails |
| ESG, uSeg EPG | vereinfacht | Selektoren nach IP/MAC/EPG |
| Contracts sind zustandslos | umgesetzt | Kein Firewall-Zustand; die Antwort braucht eine eigene Regel |
| Dienste auf Hosts | vereinfacht | Hosts mit `services` (z. B. `tcp/443`) antworten nur dort; Hosts ohne Liste gelten als „alle Ports offen“ und der Traffic-Test sagt das ausdrücklich |

### Weitere Bereiche

| Bereich | Status |
|---|---|
| Access-Policy-Kette (VLAN Pool → Domain → AAEP → Policy Group → Interface/Switch Profile → Static Path) | umgesetzt |
| Endpoint Learning (MAC, IP nur mit Unicast Routing und passendem BD-Subnetz) | umgesetzt |
| Endpoint Move als eigenes Ereignis | nicht unterstützt (siehe Backlog) |
| Fabric Discovery und Registrierung | vereinfacht: Ablauf mit festen Schritten, Dauer einstellbar |
| L3Out mit OSPF, eBGP, EIGRP, Static; External EPG; Route Control | vereinfacht: Nachbarschaften nach Parametern, keine Protokoll-Zustandsmaschinen |
| VMM, Service Graph mit PBR, Multi-Pod, Remote Leaf, Multi-Site | vereinfacht, je eigener Abschnitt im README |
| Faults | `F0467` entspricht dem APIC; alle anderen Codes beginnen mit **S** und sind simulator-spezifisch |
| Health Scores | aus den Faults berechnet (feste Abzüge je Severity), nicht zufällig |
| CLI | echte Befehlsnamen, Ausgaben aus dem gemeinsamen Zustand im Stil von NX-OS/APIC; das Ausgabeformat ist angenähert, nicht bitgenau |
| REST-API | Teilumfang des APIC-Formats (Login, `mo`/`class`-Abfragen mit Filtern, POST/DELETE); keine vollständige Kompatibilität |

## Relevante Defaultwerte

| Objekt | Attribut | Default im Simulator | Bedeutung |
|---|---|---|---|
| `fvCtx` | `pcEnfPref` | `enforced` | Policy wird durchgesetzt |
| `fvAEPg` | `pcEnfPref` | `unenforced` | keine Intra-EPG-Isolation |
| `fvAEPg` | `prefGrMemb` | `exclude` | nicht in der Preferred Group |
| `vzBrCP` | `scope` | `context` | Contract gilt im VRF |
| `vzSubj` | `revFltPorts` | `yes` | Antwort mit getauschten Ports erlaubt |
| `vzEntry` | `etherT`, `prot`, Ports | `unspecified` | passt auf alles, was nicht eingeschränkt ist |
| `fvBD` | `unicastRoute` | `yes` | ACI routet und lernt IPs |
| `fvBD` | `arpFlood` | `no` | ARP wird gezielt zugestellt |

## Determinismus

- Gleicher Ausgangszustand und gleiche Aktionen ergeben denselben Endzustand. Die Engine rechnet den operativen Zustand nach jeder Änderung vollständig neu aus.
- Zufall gibt es in der Engine nicht. Health Scores folgen aus den Faults.
- Zeit wirkt nur bei Discovery und Firmware-Upgrade. Die Dauer ist einstellbar; bei 0 Sekunden ist der Ablauf sofort und reproduzierbar. Tests laufen mit 0 Sekunden.
- Der Lab-Generator erzeugt bei jedem Lauf dieselben Dateien.

## Was ausdrücklich nicht behauptet wird

- Keine vollständige ACI- oder APIC-Kompatibilität.
- Keine bitgenaue Hardware-Pipeline. Die Reihenfolge der Prüfungen im Traffic-Test ist ein Diagnosemodell.
- Keine Sicherheits- oder Verfügbarkeitsaussage für reale Netze.
