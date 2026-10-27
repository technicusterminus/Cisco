# ACI-Simulator

Ein Cisco-ACI-Simulator, der wie ein echter APIC reagiert. Die Oberfläche ist wie die APIC-GUI aufgebaut (Menüs, Navigationsbaum, Formulare), die REST-API spricht das APIC-Format, und eine Policy-Engine rechnet nach jeder Änderung aus, was in der Fabric passiert: Discovery, Deployment auf den Leafs, gelernte Endpoints, OSPF- und BGP-Nachbarschaften, Routen, Zoning-Rules und Faults.

Er läuft ohne Installation mit Python 3.8 oder neuer, ohne zusätzliche Pakete, offline im Browser.

## Schnellstart

```sh
cd 6-ACI-Simulator
python3 -m aci_sim          # oder ./start.sh, unter Windows start.bat
```

Dann im Browser **http://localhost:8080** öffnen und mit **admin / admin** anmelden.

| Option | Wirkung |
|---|---|
| `--host 0.0.0.0` | aus dem Netz erreichbar (z. B. wenn der Simulator in einer VM läuft). Standard: nur `127.0.0.1` |
| `--port 9000` | anderer Port (Standard 8080) |
| `--https` | HTTPS auf Port 8443 mit selbstsigniertem Zertifikat (braucht `openssl`) |
| `--password geheim` | Passwort für `admin` bei einer frischen Installation |
| `--discovery 5` | Sekunden pro Discovery-Schritt bei einer frischen Installation (später unter *Simulation > Einstellungen*) |
| `--data pfad` | Ablage für Zustand und Snapshots (Standard `data/`) |
| `--strict` | unbekannte Attribute ablehnen statt annehmen (siehe REST-API) |

Mit Docker: `docker build -t aci-sim .` und `docker run -d -p 8080:8080 -v aci-sim-data:/app/data aci-sim`.

Der Zustand bleibt beim Beenden erhalten. Beim ersten Start ist die Fabric fertig registriert und leer konfiguriert. Unter *Simulation > Einstellungen* lässt sie sich zurücksetzen, auch auf „Fabric leer“ zum Üben der Discovery.

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
| Faults | Faults mit Code, Severity und Beschreibung am betroffenen Objekt, Health Scores für Tenants, EPGs und Knoten. |

## Die Oberfläche

Die Menüs entsprechen dem APIC:

| Menü | Inhalt |
|---|---|
| System | Dashboard, Faults, System Settings > BGP Route Reflector |
| Tenants | ALL TENANTS, Add Tenant, Baum je Tenant: Application Profiles, Networking (BDs, VRFs, L3Outs), Contracts (Standard, Filters), Policies |
| Fabric | Inventory (Topologie, Pod 1 mit Switches und Interfaces, Fabric Membership), Access Policies (Switches, Interfaces, Policies, Domains, Pools) |
| Admin | AAA (lokale Benutzer), Config Rollbacks (Snapshots), Import/Export (JSON) |
| Operations | Visibility & Troubleshooting (Traffic-Test Schritt für Schritt), EP Tracker |
| **Simulation** | gibt es nur im Simulator: Topologie und simulierte Hosts, externe Router, Labs, Einstellungen |

Oben rechts: Fault-Zähler, **CLI** (APIC und alle Switches), **API Inspector** (zeigt jeden REST-Aufruf der GUI mit Payload und Antwort) und **Visore** (Object Store Browser). Jedes Objekt lässt sich als JSON speichern (*Save as*) und per *Post* einspielen.

Der Simulator bildet Aufbau, Begriffe und Arbeitsabläufe der APIC-GUI nach. Er ist kein Abbild der Cisco-Software, Layout und Grafik sind eigenständig.

## Labs

Unter *Simulation > Labs* laden. Jedes Lab setzt die Konfiguration auf einen Startzustand, bringt Hosts und Router mit und prüft das Ergebnis per Knopfdruck. Die Musterlösung lässt sich einblenden.

| Lab | Thema | Dauer |
|---|---|---|
| 01 | Fabric Discovery und BGP Route Reflector | 20 min |
| 02 | Access Policies: vom VLAN-Pool zum Switch-Profil, Fault F0467 | 30 min |
| 03 | Tenant, VRF, Bridge Domains und EPGs | 30 min |
| 04 | Contracts, Filter und vzAny | 35 min |
| 05 | vPC mit LACP für einen Datenbankserver | 35 min |
| 06 | L3Out mit OSPF ins WAN (MTU-Problem, MP-BGP) | 45 min |
| 07 | Troubleshooting: sechs Tickets | 45 min |
| 08 | Automatisierung über die REST-API | 30 min |
| 09 | L3Out mit eBGP über Sub-Interface | 45 min |

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

Ansible und Terraform senden viele echte APIC-Attribute und Relationen, die der Simulator nicht auswertet (QoS, Monitoring, STP …). Er nimmt sie an und speichert sie, damit die Tools durchlaufen. Mit `--strict` lehnt er unbekannte Attribute wie ein APIC mit Fehler 121 ab. XML, WebSocket-Subscriptions und die Zertifikats-Signatur werden nicht unterstützt (bei Zertifikats-Login prüft der Simulator die Signatur nicht).

Für Ansible: `use_ssl: false` und `port: 8080` setzen, siehe `beispiele/ansible-inventory.yml`.

## CLI

Über **CLI** oben rechts oder unter *Fabric > Inventory > Switch > CLI*. Mit `ssh leaf101` wechselst du vom APIC zum Switch, mit `exit` zurück.

| APIC | Leaf/Spine |
|---|---|
| `acidiag fnvread` | `show version`, `show lldp neighbors`, `show interface status` |
| `moquery -c fvBD`, `moquery -c fvAEPg -f 'fv.AEPg.name=="Web"'`, `moquery -d uni/tn-common` | `show vlan extended`, `show endpoint [vrf T:V] [ip x]`, `show vrf` |
| `show switch`, `show controller`, `show tenant`, `show version` | `show ip route vrf T:V`, `show zoning-rule [scope N]` |
| | `show ip ospf neighbors vrf T:V`, `show bgp ipv4 unicast summary vrf T:V`, `show vpc brief`, `show port-channel summary` |

## Faults

**F0467** (EPG- oder L3Out-Deployment fehlgeschlagen) entspricht dem echten APIC, auch mit den Gründen `invalid-vlan`, `invalid-path` und `encap-already-in-use`. Für alles andere vergibt der Simulator eigene Codes mit **S** davor, damit du sie nicht mit echten APIC-Codes verwechselst:

| Code | Bedeutung |
|---|---|
| S0134 | Node ID doppelt vergeben |
| S0468 | L3Out-Interface unvollständig (Node fehlt im Node Profile, keine IP) |
| S0475, S0476 | vPC Protection Group unvollständig oder Node doppelt |
| S0477 | vPC Policy Group auf Leaf ohne vPC-Partner |
| S0523 | EPG ohne gültige Bridge Domain |
| S0841 | Port in mehreren Interface Selectors mit verschiedenen Policy Groups |
| S0956 | BD oder L3Out ohne gültiges VRF |
| S1123 | Relation lässt sich nicht auflösen (Ziel fehlt) |
| S3089 | Router ID am L3Out-Node fehlt |

## In EVE-NG oder CML

Der Simulator ist ein Webserver, kein Image mit echtem Datenverkehr. Du kannst ihn
- direkt auf deinem Rechner starten (am einfachsten),
- auf einer Linux-VM oder einem Linux-Knoten in EVE-NG oder CML starten (`./start.sh --host 0.0.0.0`) und die GUI über das Management-Netz öffnen,
- als Docker-Container betreiben.

Die externen Router, Hosts und Pakete sind simuliert. Ein echter Router aus CML oder EVE-NG kann keine OSPF-Nachbarschaft zum Simulator aufbauen. Du kannst aber Ansible, Python oder Postman aus deinem Lab heraus gegen die REST-API laufen lassen.

## Grenzen

Nicht simuliert: VMM (vCenter, Kubernetes), Multi-Pod und Multi-Site, Service Graphs und PBR, Route Leaking zwischen VRFs (Shared Services), Taboo Contracts, Route-Maps und Import/Export Route Control, Multicast, QoS, Monitoring- und Fabric-Policies außer dem BGP Route Reflector, Firmware-Upgrades. Die Pakete fließen nicht wirklich: Der Traffic-Test berechnet anhand von Konfiguration und Zustand, ob ein Paket und seine Antwort ankommen würden, und begründet jeden Schritt.

## Aufbau des Ordners

| Pfad | Inhalt |
|---|---|
| `aci_sim/model.py` | Klassenmodell (Management Information Tree), DN-Logik, Validierung, atomarer POST |
| `aci_sim/query.py` | Abfragen und Filter im APIC-Format |
| `aci_sim/engine.py` | Policy-Engine: Discovery, Access Policies, Deployment, Endpoints, L3Out, Contracts, Faults |
| `aci_sim/trace.py` | Traffic-Test |
| `aci_sim/cli.py` | CLI-Emulation |
| `aci_sim/server.py` | HTTP-Server, REST-API, Simulator-API, Labs, Snapshots |
| `static/` | Weboberfläche (ohne Build-Schritt) und Visore |
| `labs/`, `Labs-Quelle/` | Lab-Dateien und ihr Generator |
| `beispiele/` | Ansible, curl, Python, Terraform |
| `tests/` | `python3 -m unittest discover -s tests` |

> Kein offizielles Cisco-Material. Cisco, ACI, APIC und Nexus sind Marken von Cisco Systems, Inc.
