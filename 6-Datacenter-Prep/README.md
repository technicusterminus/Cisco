# Datacenter Prep

Eine Trainingsumgebung für Cisco ACI mit simuliertem APIC, der wie ein echter APIC reagiert. Die Oberfläche hat dieselbe Struktur wie die APIC-GUI (Menüs, Untermenüs, Navigationsbaum, Tabs, Rechtsklick-Menüs und Wizards), die REST-API spricht das APIC-Format, und eine Policy-Engine rechnet nach jeder Änderung aus, was in der Fabric passiert: Discovery, Deployment auf den Leafs, gelernte Endpoints, OSPF- und BGP-Nachbarschaften, Routen, Zoning-Rules und Faults.

Er läuft ohne Installation mit Python 3.8 oder neuer, ohne zusätzliche Pakete, offline im Browser.

## Schnellstart

```sh
cd 6-Datacenter-Prep
python3 -m dcprep          # oder ./start.sh, unter Windows start.bat
```

Dann im Browser **http://localhost:8080** öffnen und mit **admin / admin** anmelden (Domain *DefaultAuth*). Mit Login-Domains lautet der Benutzername per REST `apic#<Domain>\\<user>`.

| Option | Wirkung |
|---|---|
| `--host 0.0.0.0` | aus dem Netz erreichbar (z. B. wenn Datacenter Prep in einer VM läuft). Standard: nur `127.0.0.1` |
| `--port 9000` | anderer Port (Standard 8080) |
| `--https` | HTTPS auf Port 8443 mit selbstsigniertem Zertifikat (braucht `openssl`) |
| `--password geheim` | Passwort für `admin` bei einer frischen Installation |
| `--discovery 5` | Sekunden pro Discovery-Schritt bei einer frischen Installation (später unter *Simulation > Einstellungen*) |
| `--data pfad` | Ablage für Zustand und Snapshots (Standard `data/`) |
| `--strict` | unbekannte Attribute ablehnen statt annehmen (siehe REST-API) |

Mit Docker: `docker build -t dcprep .` und `docker run -d -p 8080:8080 -v dcprep-data:/app/data dcprep`.

Der Zustand bleibt beim Beenden erhalten. Beim ersten Start ist die Fabric fertig registriert und leer konfiguriert. Unter *Simulation > Einstellungen* lässt sie sich zurücksetzen: auf „Fabric leer“ zum Üben der Discovery oder auf den **Werkszustand (Day 0)**. Dann startet der APIC mit dem Setup-Dialog an der Konsole (Fabric-Name, Controller-Anzahl, Pod-ID, TEP-Pool, Infra-VLAN, GIPo, OOB, Admin-Passwort), und GUI und REST-API sind erst danach erreichbar. Dasselbe erreichst du in der APIC-CLI mit `acidiag touch clean` und `acidiag reboot`. Lab 00 führt durch diesen Ablauf.

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
| Disabled Interfaces | Deaktivierte Ports gehen admin-down, Endpoints und Nachbarschaften dahinter fallen weg. |
| Faults, Events, Audit Log | Faults mit Code, Severity und Beschreibung am Objekt, Health Scores. Events bei Zustandswechseln (Switch aktiv, Endpoint gelernt, Nachbarschaft, Fault ausgelöst oder behoben). Jede Änderung im Audit Log mit Benutzer, altem und neuem Wert. |

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

## Speichern und Laden

Über **💾** oben rechts oder unter *Simulation > Speichern & Laden* sicherst du den kompletten Zustand als **Spielstand**: Konfiguration, simulierte Hosts, Router, vCenter und Firewalls, das Day-0-Setup, das aktive Lab und den Fortschritt der Prüfungen. Spielstände lassen sich laden, löschen, als Datei herunterladen und auf einem anderen Rechner wieder hochladen.

Beim Wechsel zu einem anderen Lab sichert Datacenter Prep das laufende Lab automatisch als `auto-<lab>`. Unter *Simulation > Labs* steht dann bei diesem Lab **Fortsetzen** (letzter Spielstand) neben **Neu starten**.

Davon getrennt gibt es wie beim echten APIC die **Config Rollbacks** (*Admin > Config Rollbacks*): Sie setzen nur die Konfiguration zurück, die simulierte Umgebung bleibt, wie sie ist.

## Labs

Unter *Simulation > Labs* laden. Jedes Lab setzt die Konfiguration auf einen Startzustand, bringt Hosts und Router mit und prüft das Ergebnis per Knopfdruck. Die Musterlösung lässt sich einblenden.

| Lab | Thema | Dauer |
|---|---|---|
| 00 | Day 0: APIC-Ersteinrichtung mit Setup-Dialog | 20 min |
| 01 | Fabric Discovery und BGP Route Reflector | 20 min |
| 02 | Access Policies: vom VLAN-Pool zum Switch-Profil, Fault F0467 | 30 min |
| 03 | Tenant, VRF, Bridge Domains und EPGs | 30 min |
| 04 | Contracts, Filter und vzAny | 35 min |
| 05 | vPC mit LACP für einen Datenbankserver | 35 min |
| 06 | L3Out mit OSPF ins WAN (MTU-Problem, MP-BGP) | 45 min |
| 07 | Troubleshooting: sechs Tickets | 45 min |
| 08 | Automatisierung über die REST-API | 30 min |
| 09 | L3Out mit eBGP über Sub-Interface | 45 min |
| 10 | OOB-Management und NTP | 30 min |
| 11 | Static Leaf und Taboo Contracts | 25 min |
| 12 | VMM-Integration mit VMware vCenter | 40 min |
| 13 | Shared Services: Route Leaking zwischen Tenants | 35 min |
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

## CLI

Über **CLI** oben rechts oder unter *Fabric > Inventory > Switch > CLI*. Mit `ssh leaf101` wechselst du vom APIC zum Switch, mit `exit` zurück.

| APIC | Leaf/Spine |
|---|---|
| `acidiag fnvread`, `acidiag avread`, `cat /data/data_admin/sam_exported.config` | `show version`, `show lldp neighbors`, `show cdp neighbors`, `show interface status`, `show interface eth1/x` |
| `show controller`, `show switch`, `show fabric membership`, `show version` | `show vlan extended`, `show mac address-table`, `show endpoint [vrf T:V] [ip x]`, `show system internal epm endpoint ip x` |
| `moquery -c fvBD`, `moquery -c fvAEPg -f 'fv.AEPg.name=="Web"'`, `moquery -d uni/tn-common` | `show vrf`, `show ip interface brief vrf T:V`, `show ip arp vrf T:V`, `show ip route vrf T:V` (inklusive geleakter Routen) |
| `show tenant`, `show bridge-domain`, `show epg`, `show endpoints [ip x]`, `show faults [detail]` | `show zoning-rule`, `show zoning-filter`, `contract_parser.py`, `show service redir info` |
| `show vmware domain name <Domain>` | `show ip ospf neighbors vrf T:V`, `show ip ospf interface brief vrf T:V`, `show bgp ipv4 unicast [summary\|neighbors] vrf T:V` |
| | `show ip eigrp neighbors vrf T:V`, `show bfd neighbors vrf T:V`, `show track` |
| `acidiag touch clean`, `acidiag reboot` (Werkszustand) | `iping -V T:V <ip>` (Ping vom Leaf, weckt stille Hosts per Glean), `show vpc brief`, `show port-channel summary`, `show ntp peer-status` |
| | Underlay: `show ip route vrf overlay-1`, `show isis adjacency vrf overlay-1`, `show bgp vpnv4 unicast summary vrf overlay-1`, auf Spines `show coop internal info ip-db` |

## Faults

**F0467** (EPG- oder L3Out-Deployment fehlgeschlagen) entspricht dem echten APIC, auch mit den Gründen `invalid-vlan`, `invalid-path` und `encap-already-in-use`. Für alles andere vergibt Datacenter Prep eigene Codes mit **S** davor, damit du sie nicht mit echten APIC-Codes verwechselst:

| Code | Bedeutung |
|---|---|
| S0101 | Cluster-Größe aus dem Setup passt nicht zur Anzahl der APICs (nicht Fully Fit) |
| S0134 | Node ID doppelt vergeben |
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
| S1690 | Service Graph nicht gerendert (Device Selection Policy, Connector, PBR Policy oder Cluster Interface fehlerhaft) |
| S3089 | Router ID am L3Out-Node fehlt |

## In EVE-NG oder CML

Datacenter Prep ist ein Webserver, kein Image mit echtem Datenverkehr. Du kannst ihn
- direkt auf deinem Rechner starten (am einfachsten),
- auf einer Linux-VM oder einem Linux-Knoten in EVE-NG oder CML starten (`./start.sh --host 0.0.0.0`) und die GUI über das Management-Netz öffnen,
- als Docker-Container betreiben.

Die externen Router, Hosts und Pakete sind simuliert. Ein echter Router aus CML oder EVE-NG kann keine OSPF-Nachbarschaft zu Datacenter Prep aufbauen. Du kannst aber Ansible, Python oder Postman aus deinem Lab heraus gegen die REST-API laufen lassen.

## Grenzen

Nicht simuliert: VMM für Kubernetes, Microsoft und OpenStack, Multi-Pod und Multi-Site, Service Graphs ohne PBR (Firewall als Gateway), Managed Devices (Device Packages), Set Rules und Route-Profile mit Community/Tag, uSeg-EPGs, Multicast, QoS, SNMP und Syslog, Monitoring-Policies, Firmware-Upgrades. Die Pakete fließen nicht wirklich: Der Traffic-Test berechnet anhand von Konfiguration und Zustand, ob ein Paket und seine Antwort ankommen würden, und begründet jeden Schritt.

## Aufbau des Ordners

| Pfad | Inhalt |
|---|---|
| `dcprep/model.py` | Klassenmodell (Management Information Tree), DN-Logik, Validierung, atomarer POST |
| `dcprep/query.py` | Abfragen und Filter im APIC-Format |
| `dcprep/engine.py` | Policy-Engine: Discovery, Access Policies, Deployment, Endpoints, L3Out, Contracts, Faults |
| `dcprep/trace.py` | Traffic-Test |
| `dcprep/cli.py` | CLI-Emulation |
| `dcprep/server.py` | HTTP-Server, REST-API, Simulator-API, Labs, Snapshots |
| `static/` | Weboberfläche (ohne Build-Schritt): `app.js` Navigation und Tabs, `specs.js` Formulare, Wizards und Baumstruktur je Klasse, `forms.js` Steuerelemente und Wizard, `views*.js` Spezialseiten, `visore.html` |
| `labs/`, `Labs-Quelle/` | Lab-Dateien und ihr Generator |
| `beispiele/` | Ansible, curl, Python, Terraform |
| `tests/` | `python3 -m unittest discover -s tests` |

> Kein offizielles Cisco-Material. Cisco, ACI, APIC und Nexus sind Marken von Cisco Systems, Inc.

## Hinweis zu Marken und Herkunft

Datacenter Prep ist ein unabhängiges Trainingswerkzeug und kein Produkt von Cisco Systems. Es enthält keine Cisco-Software, keine Firmware und keine Grafiken von Cisco; Code, Oberfläche, Texte und Labs sind eigenständig erstellt. Begriffe und Klassennamen werden verwendet, um zu beschreiben, wofür geübt wird, und um Werkzeuge wie Ansible und Terraform anbinden zu können. Cisco, Cisco ACI, APIC und NX-OS sind Marken von Cisco Systems, Inc.; ihre Nennung dient nur der Beschreibung. Die Simulation bildet das Verhalten vereinfacht nach und ist kein Ersatz für die offizielle Dokumentation.
