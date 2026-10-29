# Datacenter Prep

Eine didaktische Trainingsumgebung für Cisco ACI. Ein simulierter APIC bildet das Verhalten eines APIC im dokumentierten Umfang nach. Er ist kein echter APIC, keine Nexus-Emulation und nicht vollständig kompatibel (siehe [Referenzprofil](docs/REFERENZPROFIL.md)). Die Oberfläche hat dieselbe Struktur wie die APIC-GUI (Menüs, Untermenüs, Navigationsbaum, Tabs, Rechtsklick-Menüs und Wizards), die REST-API spricht das APIC-Format, und eine Policy-Engine rechnet nach jeder Änderung aus, was in der Fabric passiert: Discovery, Deployment auf den Leafs, gelernte Endpoints, OSPF- und BGP-Nachbarschaften, Routen, Zoning-Rules und Faults.

Er läuft ohne Installation mit Python 3.8 oder neuer, ohne zusätzliche Pakete, offline im Browser.

## Schnellstart

Es gibt genau eine Startdatei: **`start.py`**.

```sh
cd 6-Datacenter-Prep
python3 start.py           # Windows: Doppelklick auf start.bat (oder py start.py)
```

Der Browser öffnet sich von selbst auf **http://localhost:8080** (ist der Port belegt, nimmt `start.py` den nächsten freien und zeigt ihn an). Dort wählst du auf der Startseite **„Wer übt heute?“** deinen Benutzer oder legst einen neuen an. Danach meldest du dich am simulierten APIC mit **admin / admin** an (Domain *DefaultAuth*). Mit Login-Domains lautet der Benutzername per REST `apic#<Domain>\\<user>`. Beenden mit **Strg+C**, alle Übungswelten bleiben gespeichert.

| Option | Wirkung |
|---|---|
| `--host 0.0.0.0` | aus dem Netz erreichbar (z. B. VM oder Schulungsraum). Standard: nur `127.0.0.1`. Dann allen Benutzern ein Passwort geben |
| `--port 9000` | fester Port (Standard 8080, belegt → nächster freier) |
| `--no-browser` | Browser nicht automatisch öffnen |
| `--https` | HTTPS auf Port 8443 mit selbstsigniertem Zertifikat (braucht `openssl`) |
| `--password geheim` | APIC-Passwort für `admin` in neu angelegten Übungswelten |
| `--discovery 5` | Sekunden pro Discovery-Schritt in neuen Übungswelten (später unter *Simulation > Einstellungen*) |
| `--data pfad` | Datenverzeichnis (Standard `data/`) |
| `--strict` | unbekannte Attribute ablehnen statt annehmen (siehe REST-API) |
| `--users` | Benutzer auflisten und beenden |
| `--set-password NAME` | Passwort eines Benutzers neu setzen, z. B. ein vergessenes Verwalter-Passwort, und beenden |

`python3 -m dcprep` startet dasselbe ohne Browser. `start.sh` gibt es nicht mehr.

Mit Docker: `docker build -t dcprep .` und `docker run -d -p 8080:8080 -v dcprep-data:/app/data dcprep`.

Beim ersten Start ist die Fabric fertig registriert und leer konfiguriert. Unter *Simulation > Einstellungen* lässt sie sich zurücksetzen: auf „Fabric leer“ zum Üben der Discovery oder auf den **Werkszustand (Day 0)**. Dann startet der APIC mit dem Setup-Dialog an der Konsole (Fabric-Name, Controller-Anzahl, Pod-ID, TEP-Pool, Infra-VLAN, GIPo, OOB, Admin-Passwort), und GUI und REST-API sind erst danach erreichbar. Dasselbe erreichst du in der APIC-CLI mit `acidiag touch clean` und `acidiag reboot`. Lab 00 führt durch diesen Ablauf.

## Was simuliert wird

**Fabric:** 1 APIC, 2 Spines (N9K-C9332C), 4 Leafs (N9K-C93180YC-FX). Uplinks eth1/49 und eth1/50, der APIC hängt an leaf101 und leaf102 auf eth1/48.

| Bereich | Verhalten wie beim APIC |
|---|---|
| Fabric Discovery | Switches erscheinen per LLDP der Reihe nach unter *Nodes Pending Registration* (erst die Leafs am APIC, dann die Spines, dann die übrigen Leafs). Nach der Registrierung sind sie erst *discovering*, dann *active*. |
| Access Policies | Die Kette VLAN Pool → Domain → AAEP → Policy Group → Interface Profile → Switch Profile wird pro Port aufgelöst, inklusive Static/Dynamic Allocation, PC und vPC mit Explicit Protection Group. |
| Tenant | VRF, Bridge Domain, Subnetze, Application Profile, EPG, Domains, Static Ports (Trunk, 802.1P, untagged). Relationen ohne Namen lösen wie beim APIC auf `default` im Tenant common auf. |
| Endpoints | Simulierte Hosts senden mit VLAN, MAC und IP. Die Fabric lernt sie nur, wenn Port, VLAN, Domain und Binding zusammenpassen. Ohne Unicast Routing oder außerhalb der BD-Subnetze lernt die ACI keine IP. |
| LACP | Host-Bonding (LACP active/passive, statisch) gegen die Port Channel Policy. Bei Mismatch werden Links suspendiert. |
| Contracts | Provider/Consumer, Subjects, Filter mit Ports, Reverse Filter Ports, Deny, `est`, Scope (VRF, AP, Tenant, Global), vzAny, Preferred Group, Intra-EPG-Isolation, unenforced VRF. Anfrage und Antwort werden getrennt geprüft. |
| L3Out | Routed Interface, Sub-Interface und SVI, Static Routes, OSPF (Area, Area Type, Hello/Dead, MTU, Netzwerktyp) und eBGP (Peer, Remote-AS, Local-AS, Fabric-AS). External EPGs klassifizieren nach Subnetz. BD-Subnetze werden nur mit *Advertised Externally* und L3Out-Verknüpfung angekündigt. |
| MP-BGP | Externe Routen erreichen die anderen Leafs nur mit BGP Route Reflector Policy (Fabric-AS und Spine als RR). |
| Taboo Contracts, Static Leafs | Taboos sperren passenden Verkehr trotz Contract. Ein Static Leaf deployt die EPG auf allen Ports des Leafs, deren Access Policy die Domain hat. |
| Management und NTP | Static Node Management Addresses setzen die OOB-Adresse der Switches. NTP synchronisiert erst, wenn Date and Time Policy, Pod Policy Group, Pod Profile und Management-Adresse zusammenpassen. |
| VMM (vCenter) | Simuliertes vCenter mit ESXi-Hosts und VMs (Menü *Simulation > vCenter*). Die VMM Domain verbindet sich nur mit richtiger IP, Datacenter und Credentials. Der APIC legt je EPG eine Port Group `Tenant|AP|EPG` mit einem VLAN aus dem dynamischen Pool an. LLDP oder CDP zwischen ESXi und Leaf, Resolution Immediacy (Pre-provision, Immediate, On Demand). VMs werden als Endpoint mit Learning Source *learned,vmm* gelernt. |
| Shared Services | Route Leaking zwischen VRFs und Tenants: Contract mit Scope Tenant oder Global, exportierter Contract (Imported Contract, *Consumed Contract Interface*), Provider-Subnetz an der EPG und Consumer-Subnetz mit *Shared between VRFs*. Shared L3Out über External-EPG-Subnetze mit *Shared Route Control* und *Shared Security Import*. |
| L2Out und stille Hosts | External Bridged Domain, L2Out mit Encap, Paths und External EPG an einer Bridge Domain. Stille Hosts (*Stiller Host* im Host-Dialog) lernt die ACI erst, wenn sie per ARP Flooding oder ARP Glean (Unicast Routing mit BD-Subnetz) gefragt werden. |
| L3Out in der Praxis | SVI auf vPC (Side A/B, Secondary IP, Nachbarschaft zu beiden Border Leafs, LACP zum Router), Floating SVI mit Anchor Node und Floating IP, EIGRP, BFD (OSPF, EIGRP, BGP, Static), eBGP über Loopbacks mit Multihop-TTL, MD5-Passwort, BGP Timers Policy am VRF, Route Summarization (BGP/OSPF), Static Routes mit Preference und IP SLA Track. |
| AAA und RBAC | TACACS+-, RADIUS- und LDAP-Provider mit Provider Groups, Login-Domains, Default- und Console-Authentication, Fallback auf lokal bei Serverausfall, Cisco AV-Pair (`shell:domains=...`) und Remote User Login Policy. Security Domains an Tenants, lokale Benutzer mit Domain, Rolle und Read/Write. Die REST-API filtert Lesezugriffe und lehnt Schreibzugriffe ohne Recht mit 403 ab. Simulierte AAA-Server unter *Simulation > AAA-Server*, Login-Protokoll unter *Admin > AAA*. |
| In-Band-Management | In-Band EPG mit VLAN und BD inb, Static Node Addresses, Prüfung der Access Policy auf den APIC-Ports (Fault S0211). AAA-Provider und NTP können das In-Band EPG nutzen. |
| ESG und uSeg | Endpoint Security Groups mit EPG- und IP-Selektoren (danach zählen nur noch die ESG-Contracts, ESG↔EPG ist nicht möglich), uSeg EPGs mit IP- und MAC-Attributen in derselben BD und Domain. |
| Route Control und Transit Routing | Export und Import Route Control Subnets am External EPG (exakt oder *Aggregate*), Route Control Enforcement *Import* am L3Out, Route-Profile `default-export` und `default-import` mit Contexts und Match Rules. Routen eines L3Outs gehen nur mit Export Route Control an ein anderes L3Out (Transit Routing). |
| Service Graph mit PBR | L4-L7 Device (Concrete Device, Cluster Interfaces mit Encap), Service Graph Template mit Function Node (Routing Mode Redirect), Device Selection Policy und PBR Policies. Die ACI legt Shadow-EPGs auf den Firewall-Ports an, lernt die Firewall-Interfaces und leitet den Verkehr um. Die simulierte Firewall (*Simulation > L4-L7 Geräte*) hat ein eigenes Regelwerk. Falsche MAC, fehlendes VLAN oder fehlende Device Selection Policy führen zu nachvollziehbaren Fehlern. Bei gleicher Priorität gewinnt Redirect vor Permit. |
| Firmware-Upgrade | Images per SCP/HTTP vom simulierten Fileserver ins Firmware Repository laden, APIC-Upgrade (Controller first, der APIC nimmt währenddessen keine Konfiguration an), Upgrade Groups mit Node Blocks und Upgrade Policy. Die Switches einer Gruppe laden gleichzeitig neu: Endpoints dahinter fallen weg, ohne aktiven Spine gibt es keinen Pfad zwischen den Leafs. Warnung und Fault, wenn beide vPC-Peers oder alle Spines in einer Gruppe sind. |
| Config Export und Import | Remote Location (SCP/SFTP/FTP mit Management EPG), Export Policy für die ganze Fabric oder einen Target DN, als Datei oder Snapshot (erscheint unter *Config Rollbacks*). Global AES Encryption entscheidet, ob Passwörter und Keys im Export stehen. Import mit Merge oder Replace und Atomic oder Best Effort, Jobs mit Ergebnis. |
| Monitoring | SNMP Policy mit Community und Client Group über die Pod Policy Group (snmpwalk vom simulierten Manager), Destination Groups für Syslog, SNMP-Traps und Callhome, Sources in der Common Policy mit Min Severity und Include. Neue Faults, Events und Audit-Einträge kommen beim simulierten Syslog-Server, SNMP-Manager oder Mailserver an (*Simulation > Fileserver & Monitoring*, dort auch Test-Faults und snmpwalk). Faults eines Switches brauchen dessen Management-Adresse. |
| DHCP Relay | DHCP Relay Policy (Tenant oder infra) mit Provider-EPG und Server-Adresse, DHCP Relay Label am BD. Hosts mit *IP per DHCP* bekommen eine Adresse aus dem Scope des simulierten DHCP-Servers, mit dem BD-Gateway als giaddr. |
| MCP und Loop Protection | Legacy-Switches mit mehreren Links (*Simulation > Legacy-Switches*) bilden Schleifen: Broadcast-Storm und Endpoint-Flapping im BD. MCP (global mit Key, *PDU per VLAN*, MCP Interface Policy) error-disabled einen Port, Endpoint Loop Protection schaltet Port oder BD-Learning ab. |
| QoS-Klassen | QOS Class Policies level1–level6 mit MTU und Scheduling, Zuordnung über die QoS Class der EPG (`show qos classes`). Die Klassen beeinflussen den Traffic-Test nicht. |
| Multi-Pod | Topologie mit Pod 2 (spine203/204, leaf105/106) und IPN-Routern (Lab 29). Pod Fabric Setup Policy mit TEP Pool je Pod, Infra-L3Out im Tenant infra (VRF overlay-1, Sub-Interfaces vlan-4, OSPF, BGP), Fabric External Connection Policy mit Data Plane TEP. Die Pod-2-Spines erscheinen erst, wenn ihr DHCP Discover per Relay im IPN beim APIC ankommt, die Pod-2-Leafs erst mit OSPF zwischen Pod-2-Spines und IPN. MTU-Mismatch lässt OSPF in EXSTART, IPN-MTU unter 9150 verwirft VXLAN, ohne PIM Bidir fehlt BUM zwischen den Pods. Wizard *Fabric > Inventory > Quick Start > Add Pod*, Simulation unter *IPN & WAN*. |
| Remote Leaf | Remote Leaf hinter einem WAN-Router (Lab 30): Remote Pool, External TEP Pool, Registrierung als *remote-leaf-wan* mit Remote Pool ID, Uplink im Infra-L3Out, DHCP Relay am WAN-Router, WAN-MTU für VXLAN. Wizard *Add Remote Leaf*. |
| Multi-Site | Vereinfachter Nexus Dashboard Orchestrator mit simulierter zweiter Site DC-HAM (Lab 31, *Simulation > Multi-Site (NDO)*): Site onboarden (APIC-Login, Site ID), Infra Configuration (ISN-Interfaces der Spines, OSPF, BGP-EVPN Router-ID, Overlay Unicast TEP) und Templates mit VRF, BD (L2 Stretch, Intersite BUM), EPGs und Contracts. Der NDO legt im APIC das L3Out *intersite*, die Site ID und die Template-Objekte mit `annotation: orchestrator:msc` an. Der Traffic-Test prüft ISN, Stretch und Contracts bis zum Host in DC-HAM. |
| Disabled Interfaces | Deaktivierte Ports gehen admin-down, Endpoints und Nachbarschaften dahinter fallen weg. |
| Faults, Events, Audit Log | Faults mit Code, Severity und Beschreibung am Objekt, Health Scores. Events bei Zustandswechseln (Switch aktiv, Endpoint gelernt, Nachbarschaft, Fault ausgelöst oder behoben). Jede Änderung im Audit Log mit Benutzer, altem und neuem Wert. |

## Eigene, große Strukturen aufbauen und testen

| Werkzeug | Wo | Was es tut |
|---|---|---|
| Topologie-Editor | *Simulation > Topologie & Hosts > ⚙ Topologie* | 1–4 Pods mit je 1–6 Spines und 1–40 Leafs, dazu bis zu 8 Remote Leafs. Auf Wunsch werden alle Switches registriert und die Multi-Pod-Grundkonfiguration (TEP Pools, Infra-L3Out, Data Plane TEPs, DHCP Relay im IPN) gleich mit angelegt. Node-IDs: Pod 1 leaf101…/spine201…, Pod 2 leaf1101…/spine1201…, Pod 3 2101…/2201…, Pod 4 3101…/3201…, Remote Leafs 3901…. Die Konfiguration bleibt beim Umbau erhalten. |
| Hosts in Masse | *Simulation > Topologie & Hosts > + Hosts (CSV/Vorlage)* | CSV `name,mac,ip,gw,vlan,leaf,port[,leaf2,port2,bond]` oder Vorlage (Präfix, Anzahl, Leafs, Ports, Netz, optional dual-homed per vPC). Atomar: Bei einem Fehler (belegter Port, doppelter Name, falsche IP) wird nichts übernommen. |
| Testmatrix | *Simulation > Testmatrix* | Alle Hosts oder eine EPG gegen alle, mit ICMP/TCP/UDP und Port. Jede Zelle öffnet den Traffic-Test mit Begründung. |
| Erwartungen | *Simulation > Testmatrix* | Soll-Regeln wie „`EPG:Shop/Webshop/Web` → `EPG:Shop/Webshop/App` tcp/8080 erlaubt“. Anlegen, als CSV importieren oder eine Matrix als Baseline übernehmen, dann nach jeder Änderung mit einem Klick prüfen – ein Regressionstest für das Design. EPG-Angaben werden auf alle dort gelernten Hosts aufgelöst. |
| Abdeckung | *Admin > Import/Export > Abdeckung (Coverage)* | Zeigt für die aktuelle oder eine importierte Konfiguration je Klasse, ob die Simulation sie **auswertet**, nur die **Attribute prüft** oder sie nur **speichert**, und welche unbekannten Attribute mitgekommen sind. So siehst du, wie belastbar ein Testergebnis für eine echte APIC-Konfiguration ist. |

Die Engine rechnet auch große Konfigurationen schnell neu: 50 Tenants mit je 20 EPGs (rund 11.000 Objekte) in etwa 0,1 Sekunden, ein Fluss im Traffic-Test dauert etwa 1 ms.

## Die Oberfläche

Menüs und Untermenüs wie beim APIC:

| Menü | Inhalt |
|---|---|
| System | QuickStart, Dashboard, Controllers, System Settings (BGP Route Reflector), Faults, Events, Audit Log, Active Sessions |
| Tenants | ALL TENANTS, Add Tenant, Tenant Search und je Tenant der Baum: Application Profiles (EPGs mit Domains, Static Ports, Static Leafs, Contracts, Subnets), Networking (Bridge Domains, VRFs, L2Outs, L3Outs mit Route Maps), Contracts (Standard, Taboos, Imported, Filters), Policies (OSPF Interface, Match Rules, L4-L7 Policy-Based Redirect), Services > L4-L7 (Service Graph Templates, Devices, Device Selection Policies, Deployed Graph Instances), im Tenant mgmt die Node Management Addresses |
| Fabric | Inventory (Topologie, Pod 1 mit jedem Switch: Physical/PC/VPC Interfaces, LLDP, OSPF, BGP, NTP; Fabric Membership; Disabled Interfaces), Fabric Policies (Pods, Date and Time), Access Policies (Quick Start, Interface Configuration, Switches, Interfaces, Policies, Pools, Physical, External Bridged und L3 Domains) |
| Virtual Networking | VMM Domains > VMware: vCenter Domain mit Controllern, Credentials und vSwitch Policy; Operational zeigt Verbindung, Port Groups und Hypervisors |
| Admin | AAA (Authentication, Login Domains, Security Domains, Local Users, TACACS+/RADIUS/LDAP, Login-Protokoll), Firmware, Config Rollbacks, Import/Export |
| Operations | Visibility & Troubleshooting (Traffic-Test), Capacity Dashboard, EP Tracker |
| **Simulation** | gibt es nur hier: Topologie und simulierte Hosts, externe Router, vCenter (ESXi-Hosts und VMs), L4-L7 Geräte (Firewalls), Labs, Einstellungen |

Wie beim APIC:
- **Tabs im Arbeitsbereich:** Summary, Policy (mit Untertabs, z. B. beim BD *General*, *L3 Configurations*, *Advanced/Troubleshooting*), Operational (Client End-Points, Deployed Leaves, Contracts, Neighbors, Routes), Stats, Health, Faults, History (Events und Audit Log).
- **Rechtsklick im Baum** und **Actions-Menü** (⚙): *Create Bridge Domain*, *Deploy Static EPG on PC, VPC, or Interface*, *Add Consumed Contract*, *Delete*, *Save as …*, *Post …*, *Open In Object Store Browser* usw.
- **Wizards:** Create Tenant (mit VRFs), Create VRF (optional mit BD), Create Bridge Domain (3 Schritte, Subnetz-Tabelle), Create Application EPG (Domains, Static Paths und Static Leafs), Create Filter (Entries-Tabelle), Create Contract (Subjects mit Filtern), Create L3Out (Identity, Nodes and Interfaces, Protocols, External EPG), Create L2Out, Create vCenter Domain, *Export Contract*, Create L4-L7 Devices, Create L4-L7 Service Graph Template, *Apply L4-L7 Service Graph Template*, Create Match Rule, Create VLAN Pool, Leaf Profile, Interface Profile und *Configure Interface, PC, and VPC*.
- **Interfaces deaktivieren** und wieder aktivieren (Inventory > Switch > Interfaces > Physical Interfaces).

Oben rechts: Fault-Zähler, **CLI** (APIC und alle Switches), **API Inspector** (zeigt jeden REST-Aufruf der GUI mit Payload und Antwort) und **Visore** (Object Store Browser).

Datacenter Prep bildet Aufbau, Begriffe und Arbeitsabläufe der APIC-GUI nach. Layout und Grafik sind eigenständig, Bereiche ohne Funktion (z. B. L4-L7, SNMP, Kubernetes) sind als Menüpunkt vorhanden und so gekennzeichnet.

## Benutzer und Übungswelten

Jeder Benutzer hat eine eigene, vollständig getrennte **Übungswelt**: eigene Fabric-Konfiguration, eigene Labs, Speicherstände, Snapshots und eigenen Fortschritt (`data/users/<name>/`). Das ist unabhängig von den simulierten APIC-Benutzern (admin, TACACS+ usw.).

- Beim ersten Start gibt es den Benutzer **standard** ohne Passwort. Er ist **Verwalter**. Eine Welt aus einer älteren Version (`data/state.json`, Spielstände, Snapshots) wird automatisch zu ihm übernommen.
- Neue Benutzer legst du auf der Startseite an (Name, Passwort optional). Ein Verwalter kann das Selbst-Anlegen abschalten und legt Benutzer dann in der **Benutzerverwaltung** an.
- Über **👤 Name ▾** oben rechts: Benutzer wechseln, Passwort ändern, die eigene Übungswelt komplett zurücksetzen, das eigene Konto löschen und – als Verwalter – die Benutzerverwaltung (Passwort neu setzen, Rolle, Welt zurücksetzen, löschen).
- Die Anmeldung gilt 30 Tage im Browser. Passwörter werden gesalzen mit PBKDF2 gespeichert.

## Labs und Speicherstände

Unter *Simulation > Labs & Stände* hat jedes Lab (und das **freie Üben**) einen Status – *neu*, *angefangen*, *x / y* Prüfungen, *✓ bestanden* – und eigene Speicherstände:

- **▶ Starten / Fortsetzen**: Fortsetzen lädt den automatisch gesicherten letzten Stand des Labs oder deinen neuesten eigenen Stand. Beim Wechsel in ein anderes Lab wird das laufende Lab automatisch als `auto-<lab>` gesichert (freies Üben als `auto-frei`).
- **Stände ▾**: alle Speicherstände des Labs mit Fortschritt – **Laden**, **Herunterladen**, **Löschen**, oder **Alle Stände dieses Labs löschen**.
- **↺ Default**: startet das Lab neu im Ausgangszustand und verwirft den automatischen Stand. Optional werden auch alle eigenen Stände und der Fortschritt dieses Labs gelöscht.
- **💾** (oben rechts oder im Lab) speichert einen benannten Stand. Ein Stand enthält alles: Konfiguration, simulierte Hosts, Router, vCenter und Firewalls, Day-0-Setup, aktives Lab und Prüfergebnisse. Als Datei heruntergeladene Stände lassen sich auf einem anderen Rechner oder bei einem anderen Benutzer wieder hochladen.

Der Fortschritt („bestanden“) bleibt erhalten, auch wenn du ein Lab danach weiter veränderst; er verschwindet nur mit *↺ Default* und Häkchen oder beim Zurücksetzen der ganzen Übungswelt.

Davon getrennt gibt es wie beim echten APIC die **Config Rollbacks** (*Admin > Config Rollbacks*): Sie setzen nur die Konfiguration zurück, die simulierte Umgebung bleibt, wie sie ist.

## Labs

Unter *Simulation > Labs & Stände* laden. Jedes Lab setzt die Konfiguration auf einen Startzustand, bringt Hosts und Router mit und prüft das Ergebnis per Knopfdruck. Die Musterlösung lässt sich einblenden.

| Lab | Thema | Dauer |
|---|---|---|
| 00 | Day 0: APIC-Ersteinrichtung mit Setup-Dialog | 20 min |
| 01 | Fabric Discovery: physische und logische Sicht (neues Format) | 30 min |
| 02 | Access Policies: vom VLAN zum Port, Fault F0467 (neues Format) | 30 min |
| 03 | Tenant, VRF, Bridge Domains und EPGs (neues Format) | 30 min |
| 04 | Contracts, Filter und vzAny (neues Format) | 35 min |
| 05 | vPC mit LACP für einen Datenbankserver (neues Format) | 35 min |
| 06 | L3Out mit OSPF ins WAN (MTU-Problem, MP-BGP; neues Format) | 45 min |
| 07 | Troubleshooting: sechs Tickets (neues Format) | 45 min |
| 08 | Automatisierung über die REST-API | 30 min |
| 09 | L3Out mit eBGP über Sub-Interface | 45 min |
| 10 | OOB-Management und NTP | 30 min |
| 11 | Static Leaf und Taboo Contracts (neues Format) | 25 min |
| 12 | VMM-Integration mit VMware vCenter | 40 min |
| 13 | Shared Services: Route Leaking zwischen Tenants (neues Format) | 35 min |
| 14 | L2Out und Migration: stille Hosts und ARP Flooding | 40 min |
| 15 | Transit Routing und Route Control | 40 min |
| 16 | Service Graph mit Policy-Based Redirect (Firewall) | 45 min |
| 17 | L3Out: SVI auf vPC mit Secondary IP und BFD | 40 min |
| 18 | eBGP über Loopbacks: Multihop, MD5, Timer und Summarization | 40 min |
| 19 | EIGRP und Static Route mit IP SLA Track | 40 min |
| 20 | Floating SVI für einen virtuellen Router | 30 min |
| 21 | AAA: TACACS+, Login-Domain und RBAC | 35 min |
| 22 | In-Band-Management | 35 min |
| 23 | Endpoint Security Groups und uSeg EPGs | 35 min |
| 24 | Firmware-Upgrade mit Upgrade Groups | 35 min |
| 25 | Config Export und Import | 30 min |
| 26 | Monitoring: SNMP, Syslog und Callhome | 40 min |
| 27 | DHCP Relay | 25 min |
| 28 | Loop Protection mit MCP und QoS-Klassen | 30 min |
| 29 | Multi-Pod mit Inter-Pod Network | 50 min |
| 30 | Remote Leaf in der Filiale | 40 min |
| 31 | Multi-Site mit dem Nexus Dashboard Orchestrator | 45 min |
| 32 | **Least Privilege: HTTPS von WEB zu APP** (neues Format, Abnahmefall) | 25 min |
| 33 | Zwei Endpoints in derselben EPG (neues Format) | 15 min |
| 34 | Zwei EPGs in derselben Bridge Domain: Bridging ist nicht Policy (neues Format) | 20 min |
| 35 | Falscher Port, falsche Richtung: eine kaputte Freigabe reparieren (neues Format) | 20 min |
| 36 | Endpoint Move nachvollziehen: Verlauf lesen, alte Bindung entfernen (neues Format) | 25 min |
| 37 | Interface-Ausfall oder Policy-Drop? Drei Tickets, drei Ursachen (neues Format) | 25 min |
| 38 | Innerhalb einer EPG einschränken: Isolation und Intra-EPG-Contract (neues Format) | 20 min |
| 39 | Preferred Group für eine Migration (neues Format) | 20 min |
| 40 | IT-/OT-Segmentierung einer Fertigungslinie: fünf Zonen, laterale Bewegung verhindern (neues Format, didaktisch) | 60 min |
| 41 | Routingfehler oder fehlender Contract? Externer Verkehr Schritt für Schritt (neues Format) | 25 min |
| 42 | Fehlender Rückweg: nur ankündigen, was außen gebraucht wird (neues Format) | 20 min |
| 43 | Change mit Snapshot absichern und zurückrollen (neues Format) | 20 min |
| 44 | Access-Diagnose: drei Server, drei Ursachen (Domain, VLAN Pool, Static Port; neues Format) | 30 min |
| 45 | Zwei Bridge Domains, eine VRF: Routing ohne L3Out (neues Format) | 20 min |

**Neues Lab-Format** (Labs 01 bis 07, 11, 13 und 32 bis 45): Statt einer Klickanleitung gibt es Anforderungen. Der Rest im Überblick:

- **Hinweise** in vier Stufen: Konzept, Objekte, Prüfschritt, Lösung. Die Oberfläche zählt, wie viele genutzt wurden.
- **Bewertung** getrennt nach *Funktion* und *Sicherheit / Least Privilege*. Eine Permit-any-Abkürzung funktioniert zwar, besteht aber nicht.
- **Verständnisfragen** werden getrennt gezählt.
- **Geführter Modus** oder **Prüfungsmodus** (ohne Hinweise, Lösung und Diagnosetexte), wählbar beim Start.
- **Diagnoseprotokoll** auf der Lab-Karte: alle Traffic-Tests, CLI-Befehle, Hinweise und Prüfläufe der Sitzung mit Ergebnis. Es dient dem Nachvollziehen und wird nicht bewertet.

Den Stand gegenüber dem geplanten Lernpfad zeigt [docs/LAB-KATALOG.md](docs/LAB-KATALOG.md), wie man Labs schreibt [docs/LAB-AUTHORING.md](docs/LAB-AUTHORING.md).

**Traffic Inspector** (*Operations > Visibility & Troubleshooting*): Jeder Test liefert ein Ergebnis aus der gemeinsamen Connectivity-Engine, dieselbe, die auch die Labs bewertet:

- **ALLOW**, **DROP** oder **UNRESOLVED**
- maschinenlesbarer Reason Code (z. B. `POLICY_IMPLICIT_DENY`, `POLICY_REPLY_DENIED`, `EP_NOT_LEARNED`, `LINK_DOWN`, `PORT_ADMIN_DOWN`, `SERVICE_NOT_LISTENING`)
- Fehlerort, Erklärung und nächster Diagnoseschritt
- angewandte Regel für Anfrage und Antwort (Contract, Filter, Richtung) und der Pfad über die Leafs

Reason Codes und das Dienstmodell der Hosts (Feld *Dienste*) sind simulator-spezifisch.

Unter **Pfad in der Topologie** zeigt der Traffic Inspector denselben Test in der Fabric-Grafik: erreichte Abschnitte blau, die Stelle, an der der Test endet, rot mit ✖. Die **Policy-Matrix** (*Operations > Policy-Matrix*) zeigt je VRF für jedes EPG-Paar, welche typischen Dienste die Policy für eine neue Verbindung erlaubt – berechnet mit derselben Entscheidung wie Traffic Inspector und Lab-Bewertung.

**Ereignisse:** In der Hosttabelle (*Simulation > Topologie & Hosts*) lässt sich der Link eines Hosts trennen und wieder verbinden; ein umgesteckter Host (anderer Port im Host-Dialog) ist ein Endpoint Move. Der **EP Tracker** zeigt pro Host den Verlauf: gelernt, umgezogen, nicht mehr gelernt, Link down/up. Die Event-Codes S9101–S9103 sind simulator-spezifisch.

Die Lab-Dateien entstehen aus `Labs-Quelle/build_labs.py` (`python3 Labs-Quelle/build_labs.py`). Die Tests prüfen für jedes Lab, dass es ohne Lösung nicht bestanden und mit Musterlösung vollständig bestanden ist.

## REST-API und Automatisierung

Die API entspricht dem APIC:

- `POST /api/aaaLogin.json`, `aaaRefresh.json`, `aaaLogout.json`, Cookie `APIC-cookie`
- `GET /api/mo/<dn>.json` und `/api/class/<klasse>.json`, auch mit `/api/node/...` und Klassen unter einem DN (`/api/node/class/topology/pod-1/node-101/l1PhysIf.json`)
- Parameter `query-target`, `target-subtree-class`, `query-target-filter` (`eq`, `ne`, `wcard`, `gt`, `lt`, `bw`, `and`, `or`, `not`), `rsp-subtree`, `rsp-subtree-class`, `rsp-subtree-include` (`faults`, `no-scoped`, `count`, `health`), `rsp-prop-include`, `order-by`, `page`, `page-size`
- `POST /api/mo/<dn>.json` mit Objektbaum, `status: deleted`, `DELETE /api/mo/<dn>.json`. Ein POST ist atomar: Ein Fehler irgendwo im Baum verwirft alles.
- Fehler im APIC-Format, z. B. `801` (ungültiger Wert), `122` (unbekannte Klasse), `102` (Eltern fehlen), `103` (Naming), `403` (nicht angemeldet)

Beispiele in [`beispiele/`](beispiele/):

| Datei | Stand |
|---|---|
| `ansible-tenant.yml` | getestet mit `ansible` 14.5 (`cisco.aci` 2.13): 26 Tasks (Access Policies, Tenant, Static Ports, Contracts), zweiter Lauf `changed=0` |
| `curl-tenant.sh` | getestet |
| `python-tenant.py` | getestet, nur Standardbibliothek |
| `terraform/main.tf` | nicht getestet, weil hier keine Terraform-Registry erreichbar war |

Ansible und Terraform senden viele echte APIC-Attribute und Relationen, die Datacenter Prep nicht auswertet (QoS, Monitoring, STP …). Er nimmt sie an und speichert sie, damit die Tools durchlaufen. Mit `--strict` lehnt er unbekannte Attribute wie ein APIC mit Fehler 121 ab. XML, WebSocket-Subscriptions und die Zertifikats-Signatur werden nicht unterstützt (bei Zertifikats-Login wird die Signatur nicht geprüft).

Für Ansible: `use_ssl: false` und `port: 8080` setzen, siehe `beispiele/ansible-inventory.yml`.

Welche Übungswelt ein REST-Aufruf trifft: Von diesem Rechner aus ohne weitere Angaben die des zuletzt angemeldeten Benutzers. Gezielt wählst du sie mit den Headern `X-DCPrep-User: Anna` (und `X-DCPrep-Password`, falls gesetzt). Ein APIC-Token gilt immer nur in der Welt, in der es ausgestellt wurde.

## CLI

Über **CLI** oben rechts oder unter *Fabric > Inventory > Switch > CLI*. Mit `ssh leaf101` wechselst du vom APIC zum Switch, mit `exit` zurück.

Die CLI ist nur lesend und führt nie Shell-Befehle aus. Die Befehle in der Tabelle gibt es so auf APIC bzw. Leaf (nach Cisco-Dokumentation, nicht gegen ein Gerät geprüft); die Ausgabe kommt aus der Engine und ist im Format vereinfacht. Mit **[S]** markierte Befehle sind simulator-spezifisch. Ein nicht unterstützter Befehl meldet „In der Simulation nicht unterstützt“ – das ist eine Grenze des Simulators, keine Aussage über das echte Gerät – und nennt einen unterstützten Weg (z. B. `moquery` statt `show running-config`, Traffic Inspector statt `ping`). Die REST-Antwort von `POST /sim/cli` enthält dazu `kind`: `device`, `sim` oder `unsupported`.

| APIC | Leaf/Spine |
|---|---|
| `acidiag fnvread`, `acidiag avread`, `cat /data/data_admin/sam_exported.config` | `show version`, `show lldp neighbors`, `show cdp neighbors`, `show interface status`, `show interface eth1/x` |
| `show controller`, `show switch`, `show fabric membership`, `show version` | `show vlan extended`, `show mac address-table`, `show endpoint [vrf T:V] [ip x]`, `show system internal epm endpoint ip x` |
| `moquery -c fvBD`, `moquery -c fvAEPg -f 'fv.AEPg.name=="Web"'`, `moquery -d uni/tn-common` | `show vrf`, `show ip interface brief vrf T:V`, `show ip arp vrf T:V`, `show ip route vrf T:V` (inklusive geleakter Routen) |
| `show tenant`, `show bridge-domain`, `show epg`, `show endpoints [ip x]`, `show faults [detail]` | `show zoning-rule`, `show zoning-filter`, `contract_parser.py`, `show service redir info` |
| `show vmware domain name <Domain>` | `show ip ospf neighbors vrf T:V`, `show ip ospf interface brief vrf T:V`, `show bgp ipv4 unicast [summary\|neighbors] vrf T:V` |
| | `show ip eigrp neighbors vrf T:V`, `show bfd neighbors vrf T:V`, `show track` |
| `acidiag touch clean`, `acidiag reboot` (Werkszustand) | `iping -V T:V <ip>` (Ping vom Leaf, weckt stille Hosts per Glean), `show vpc brief`, `show port-channel summary`, `show ntp peer-status` |
| `show firmware upgrade status`, `show firmware repository` | `show mcp internal info interface all`, `show interface status err-disabled` |
| `show snmp`, `show logging server`, `show snapshot` (Export-/Import-Jobs) – simulator-spezifisch [S] | `show ip dhcp relay`, `show qos classes` |
| | Spine/Remote Leaf: `show ip ospf neighbors vrf overlay-1` (OSPF zum IPN, ISN oder WAN) |
| | Underlay: `show ip route vrf overlay-1`, `show isis adjacency vrf overlay-1`, `show bgp vpnv4 unicast summary vrf overlay-1`, auf Spines `show coop internal info ip-db` |

## Faults

**F0467** (EPG- oder L3Out-Deployment fehlgeschlagen) entspricht dem echten APIC, auch mit den Gründen `invalid-vlan`, `invalid-path` und `encap-already-in-use`. Für alles andere vergibt Datacenter Prep eigene Codes mit **S** davor, damit du sie nicht mit echten APIC-Codes verwechselst:

| Code | Bedeutung |
|---|---|
| S0101 | Cluster-Größe aus dem Setup passt nicht zur Anzahl der APICs (nicht Fully Fit) |
| S0134 | Node ID doppelt vergeben |
| S0135 | Registrierte Pod ID passt nicht zum Pod, in dem der Switch hängt |
| S0136 | Remote Leaf nicht als remote-leaf-wan mit Remote Pool registriert |
| S0211 | In-Band-VLAN nicht auf den APIC-Ports erlaubt (Access Policy fehlt) |
| S0468 | L3Out-Interface unvollständig (Node fehlt im Node Profile, keine IP) |
| S0475, S0476 | vPC Protection Group unvollständig oder Node doppelt |
| S0477 | vPC Policy Group auf Leaf ohne vPC-Partner |
| S0523 | EPG ohne gültige Bridge Domain |
| S0606 | Verbindung zum vCenter fehlgeschlagen (IP, Credentials oder Datacenter falsch) |
| S0607 | VMM Domain ohne dynamischen VLAN-Bereich |
| S0841 | Port in mehreren Interface Selectors mit verschiedenen Policy Groups |
| S0956 | BD oder L3Out ohne gültiges VRF |
| S1123 | Relation lässt sich nicht auflösen (Ziel fehlt) |
| S0721 | DHCP Relay Label ohne passende DHCP Relay Policy |
| S1801 | Beide vPC-Peers in derselben Upgrade Group |
| S1802 | Alle Spines in derselben Upgrade Group |
| S1803 | Node in mehreren Upgrade Groups |
| S2533 | Schleife von MCP erkannt (Port error-disabled) |
| S2534 | Layer-2-Schleife im BD (Broadcast-Storm, Endpoint-Flapping) |
| S2535 | Endpoint Loop Protection hat einen Port abgeschaltet |
| S1690 | Service Graph nicht gerendert (Device Selection Policy, Connector, PBR Policy oder Cluster Interface fehlerhaft) |
| S3089 | Router ID am L3Out-Node fehlt |

## In EVE-NG oder CML

Datacenter Prep ist ein Webserver, kein Image mit echtem Datenverkehr. Du kannst ihn
- direkt auf deinem Rechner starten (am einfachsten),
- auf einer Linux-VM oder einem Linux-Knoten in EVE-NG oder CML starten (`python3 start.py --host 0.0.0.0 --no-browser`) und die GUI über das Management-Netz öffnen,
- als Docker-Container betreiben.

Die externen Router, Hosts und Pakete sind simuliert. Ein echter Router aus CML oder EVE-NG kann keine OSPF-Nachbarschaft zu Datacenter Prep aufbauen. Du kannst aber Ansible, Python oder Postman aus deinem Lab heraus gegen die REST-API laufen lassen.

## Abgleich mit echtem ACI

Das Verhalten ist nachgebildet und nicht gegen einen echten APIC geprüft. Dafür gibt es zwei Werkzeuge:

- **`werkzeuge/abgleich.py`** schickt dieselben rund 80 REST-Prüfungen an Datacenter Prep und an einen echten APIC (z. B. die Cisco DevNet Sandbox) und listet jede Abweichung auf. Geprüft werden Defaults, Fehlercodes, automatisch angelegte Objekte, Relationen, Faults und das Abfrage-Verhalten. Ohne `--write` liest das Skript nur. Mit `--write` legt es einen Test-Tenant an und löscht ihn danach wieder.

  ```sh
  python3 werkzeuge/abgleich.py --apic https://sandboxapicdc.cisco.com --apic-user admin --insecure
  ```

- **[`werkzeuge/ABGLEICH.md`](werkzeuge/ABGLEICH.md)** ist die Prüfliste für alles, was sich per REST nicht vergleichen lässt (Datenebene, Deployment, Protokolle), nach Risiko sortiert.

## Grenzen

Nicht simuliert: VMM für Kubernetes, Microsoft und OpenStack, vPC über Pods hinweg, Remote-Leaf-vPC, Stretched Fabric, GOLF und SR-MPLS, die vollständige NDO-Oberfläche (der NDO ist vereinfacht, die zweite Site hat nur feste Endpoints), Service Graphs ohne PBR (Firewall als Gateway), Managed Devices (Device Packages), Set Rules und Route-Profile mit Community/Tag, Multicast, Custom QoS Policies und die Wirkung von QoS auf den Datenverkehr, SNMPv3, Scheduler für Exporte und Upgrades, DHCP über L3Out. Nicht unterstützt sind außerdem Subjects ohne „Apply Both Directions“ (siehe [Backlog](docs/BACKLOG.md)). Die Pakete fließen nicht wirklich: Der Traffic-Test berechnet anhand von Konfiguration und Zustand, ob ein Paket und seine Antwort ankommen würden, und begründet jeden Schritt.

## Aufbau des Ordners

| Pfad | Inhalt |
|---|---|
| `dcprep/model.py` | Klassenmodell (Management Information Tree), DN-Logik, Validierung, atomarer POST |
| `dcprep/query.py` | Abfragen und Filter im APIC-Format |
| `dcprep/multipod.py` | Multi-Pod und Remote Leaf: IPN/WAN-Adjacencies, Discovery über DHCP Relay, Datenpfad zwischen Pods |
| `dcprep/msite.py` | Multi-Site: vereinfachter NDO, zweite Site, Infra- und Template-Deployment |
| `dcprep/flows.py` | Testmatrix und Erwartungen |
| `dcprep/coverage.py` | Abdeckungsbericht |
| `dcprep/ops.py` | Betriebsthemen: Firmware-Upgrade, MCP und Schleifen, DHCP Relay, Monitoring, Config Export/Import |
| `dcprep/engine.py` | Policy-Engine: Discovery, Access Policies, Deployment, Endpoints, L3Out, Contracts, Faults |
| `dcprep/trace.py` | Traffic-Test |
| `dcprep/cli.py` | CLI-Emulation |
| `start.py`, `start.bat` | Startdatei (Windows: Doppelklick auf `start.bat`) |
| `dcprep/users.py` | Benutzer, Sitzungen, getrennte Übungswelten |
| `dcprep/server.py` | HTTP-Server, REST-API, Simulator-API, Labs, Speicherstände, Snapshots |
| `static/` | Weboberfläche (ohne Build-Schritt): `app.js` Navigation und Tabs, `specs.js` Formulare, Wizards und Baumstruktur je Klasse, `forms.js` Steuerelemente und Wizard, `views*.js` Spezialseiten, `visore.html` |
| `labs/`, `Labs-Quelle/` | Lab-Dateien und ihr Generator |
| `beispiele/` | Ansible, curl, Python, Terraform |
| `werkzeuge/` | `abgleich.py` und `ABGLEICH.md`: Abgleich mit echtem ACI |
| `tests/` | `python3 -m unittest discover -s tests` (Unit, Integration, Abnahmefall `test_acceptance.py`), GUI: `node tests/gui/smoke.js`, `node tests/gui/acceptance.js` und `node tests/gui/troubleshooting.js` (brauchen Playwright) |
| `docs/` | [Architektur](docs/ARCHITEKTUR.md), [Referenzprofil und Regelbasis](docs/REFERENZPROFIL.md), [Lab-Katalog](docs/LAB-KATALOG.md), [Labs schreiben](docs/LAB-AUTHORING.md), [Gap-Analyse](docs/GAP-ANALYSE.md), [Backlog](docs/BACKLOG.md) |
| `CLAUDE.md` | Projektkonventionen und Prüfkommandos |

> Kein offizielles Cisco-Material. Cisco, ACI, APIC und Nexus sind Marken von Cisco Systems, Inc.

## Hinweis zu Marken und Herkunft

Datacenter Prep ist ein unabhängiges Trainingswerkzeug und kein Produkt von Cisco Systems. Es enthält keine Cisco-Software, keine Firmware und keine Grafiken von Cisco; Code, Oberfläche, Texte und Labs sind eigenständig erstellt. Begriffe und Klassennamen werden verwendet, um zu beschreiben, wofür geübt wird, und um Werkzeuge wie Ansible und Terraform anbinden zu können. Cisco, Cisco ACI, APIC und NX-OS sind Marken von Cisco Systems, Inc.; ihre Nennung dient nur der Beschreibung. Die Simulation bildet das Verhalten vereinfacht nach und ist kein Ersatz für die offizielle Dokumentation.
