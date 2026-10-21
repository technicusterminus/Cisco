# Lab 21 – Design-Fallstudien: Campus, WAN, SD-WAN, SD-Access, Virtualisierung, Catalyst Center

**Dauer:** ca. 3 h · **Art:** Fallstudien ohne CML (Papier-/Denkaufgaben mit Lösungsschlüssel)

Zehn Fälle zu Architektur, Virtualisierung und Controller-Betrieb. Beantworte jeden Fall schriftlich, bevor du den Schlüssel aufklappst.

**Lernziele:** Nach diesen Fällen kannst du …

- Einen Campus-Entwurf (2-Tier oder 3-Tier) mit Oversubscription und Verfügbarkeit begründen.
- SD-WAN und SD-Access in Ebenen und Komponenten zerlegen und ihre Grenzen nennen.
- Hypervisor-Typen, virtuelles Switching und die Rolle von Catalyst Center erklären.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::1.1.a` | Campus-, Fabric- und Cloud-Design | 26 |
| `Ziel::1.1.b` | Redundanz, FHRP und SSO | 22 |
| `Ziel::1.2.a` | SD-WAN: Ebenen und Komponenten | 33 |
| `Ziel::1.2.b` | SD-WAN: Nutzen und Grenzen | 14 |
| `Ziel::1.3.a` | SD-Access: Ebenen und Komponenten | 29 |
| `Ziel::1.3.b` | Fabric und klassischer Campus | 13 |
| `Ziel::2.1.a` | Hypervisor-Typen | 10 |
| `Ziel::2.1.b` | Virtuelle Maschinen | 10 |
| `Ziel::2.1.c` | Virtuelles Switching | 16 |
| `Ziel::4.5` | Catalyst Center und KI-Workflows | 22 |

Warum ohne CML? SD-WAN, SD-Access, Hypervisor und Next-Generation-Firewalls brauchen Controller, Lizenzen oder Hardware, die sich in einer kostenfreien Lab-Umgebung nicht sinnvoll nachbauen lassen. Du übst hier stattdessen das, was die Prüfung fragt: Komponenten zuordnen, Entwurf begründen, Konfigurationen und Ausgaben lesen, Fehler im Entwurf finden.

## Fall 1: Campus mit sechs Gebäuden: 2-Tier oder 3-Tier?

**Szenario.** Ein Campus hat sechs Gebäude mit je ca. 400 Nutzern. Alle Gebäude sind per Glasfaser höchstens 2 km vom Rechenzentrum entfernt. Jedes Gebäude hat 8 Access-Switches (48 × 1G Kupfer, 2 × 10G Uplinks).

**Aufgaben**

1. Berechne die Oversubscription eines Access-Switches (Nutzerports : Uplink). Ist das für den Access-Layer üblich?
2. Pro Gebäude gibt es 8 Access-Switches an einem Distribution-Paar. Wie viel Bandbreite läuft rechnerisch von den Access-Switches zur Distribution (nur Uplinks), und welche Uplinks zum Core brauchst du für 4:1 Oversubscription?
3. Wähle 2-Tier (Collapsed Core) oder 3-Tier und begründe mit Anzahl der Gebäude, Entfernung, Wachstum und Betrieb.
4. Nenne drei Entwurfsprinzipien, die du beim Layer-2-/Layer-3-Übergang anwendest (Failure Domain begrenzen, Routed Access, Modularität).

<details><summary>Lösungsschlüssel</summary>

1. 48 × 1 Gbit/s = 48 Gbit/s Nutzerbandbreite auf 20 Gbit/s Uplink → **2,4 : 1**. Für Access üblich sind etwa 20 : 1 (Access → Distribution), das Ergebnis ist komfortabel.
2. 8 Switches × 20 Gbit/s = 160 Gbit/s. Für 4 : 1 gegenüber dem Core genügen rechnerisch 40 Gbit/s, praktisch zwei 40-Gbit/s-Uplinks (80 Gbit/s, 2 : 1) wegen Redundanz.
3. Bei sechs Gebäuden und 2 km spricht viel für **3-Tier** (Distribution je Gebäude, Core für die Verbindung): Skalierung, Fehlerbegrenzung, Verkabelung. Collapsed Core genügt bei kleineren Campus (wenige Gebäude, kurze Wege).
4. Layer-2-Domänen klein halten (Routed Access oder pro Gebäude), Redundanz per Gerät und Pfad, modulare Bausteine mit klaren Schnittstellen (Access/Distribution/Core).

</details>

## Fall 2: Verfügbarkeit rechnen und Ausfalldomänen erkennen

**Szenario.** Ein Standort hängt an einem einzelnen WAN-Router (99,9 % Verfügbarkeit) und einem einzelnen Core-Switch (99,9 %). Die Geschäftsleitung fordert 99,99 %.

**Aufgaben**

1. Wie hoch ist die Gesamtverfügbarkeit in Reihe (ein Pfad)? Wie viele Minuten Ausfall pro Jahr sind das?
2. Wie ändert sich das, wenn beide Komponenten doppelt (parallel) vorhanden sind? Rechne je Stufe `1 − (1 − a)²`.
3. Welche Techniken nutzt du für Gerätefehler (FHRP, StackWise, SSO/NSF), Linkfehler (EtherChannel, ECMP) und Standortfehler (Dual-Site)?
4. Wo steckt trotz doppelter Geräte noch ein Single Point of Failure (Stromversorgung, gemeinsames Gehäuse, Software-Bug, gemeinsame Glasfaserstrecke)?

<details><summary>Lösungsschlüssel</summary>

1. Reihenschaltung: 0,999 × 0,999 = 0,998001 → 99,80 %. Ausfall ≈ 0,1999 % × 525 600 min ≈ **1050 min/Jahr ≈ 17,5 h**.
2. Je Stufe parallel: 1 − 0,001² = 0,999999. Beide Stufen in Reihe: 0,999999² ≈ **99,9998 %** (ca. 1 min/Jahr). Die Forderung 99,99 % (52,6 min/Jahr) wird übertroffen.
3. Gerät: FHRP (HSRP/VRRP), StackWise/VSS, SSO/NSF innerhalb des Chassis. Link: EtherChannel, ECMP. Standort: Dual-Site, Anycast-Dienste, getrennte Provider.
4. Gemeinsame Stromversorgung, derselbe Kabelkanal/dieselbe Glasfaserstrecke, derselbe Software-Fehler auf beiden identischen Geräten, gemeinsames Management (zentraler Controller).

</details>

## Fall 3: Branch mit zwei Internetleitungen: DMVPN oder SD-WAN?

**Szenario.** Ein Unternehmen betreibt 120 Filialen mit je zwei Internetanschlüssen. Gefordert: Sprache muss bei Verlust >1 % oder Latenz >150 ms automatisch auf den anderen Anschluss wechseln, Zero-Touch-Rollout neuer Filialen, zentrale Richtlinien.

**Aufgaben**

1. Ordne die SD-WAN-Komponenten den Ebenen zu: Orchestration, Management, Control Plane, Data Plane (WAN Edge, Controller, Manager, Validator).
2. Wie erreicht SD-WAN den Wechsel bei Verlust/Latenz (BFD-Messung, Application-Aware Routing/SLA-Klassen)? Welche Rolle spielt OMP und TLOC?
3. Welche Vorteile bringt SD-WAN gegenüber einem klassischen Hub-and-Spoke mit statisch konfigurierten VPNs?

<details><summary>Lösungsschlüssel</summary>

1. **Validator** (früher vBond) = Orchestration (Erstkontakt, Authentifizierung, Zuordnung). **Manager** (vManage) = Management Plane (Konfiguration, Monitoring, Policies). **Controller** (vSmart) = Control Plane (OMP, verteilt Routen/Policies). **WAN Edge** (cEdge/vEdge) = Data Plane.
2. WAN Edges messen die Pfadqualität per **BFD** je Tunnel (Verlust, Latenz, Jitter). Eine App-Route-Policy definiert SLA-Klassen: Verletzt der aktuelle Pfad die Grenzen, wählt die Edge einen anderen Pfad. **OMP** transportiert Routen, TLOCs und Policies zwischen Edges und Controller. **TLOC** (Transport Locator) = Endpunkt eines Overlay-Tunnels (Edge-Adresse + Farbe + Encapsulation).
3. Transportunabhängig (MPLS, Internet, LTE), zentrale Richtlinien, Zero-Touch-Provisioning, applikationsbewusste Pfadwahl, Segmentierung per VPNs.

</details>

## Fall 4: Wann passt SD-WAN nicht?

**Szenario.** Drei Standorte: (A) kleines Büro mit einem einzigen Anschluss, kein Wachstum; (B) Fabrik mit strikt getrenntem OT-Netz, keine Internetanbindung; (C) 400 Filialen, wechselnde Provider, Cloud-Anwendungen.

**Aufgaben**

1. Beurteile für jeden Standort, ob SD-WAN sinnvoll ist, und begründe.
2. Nenne drei Grenzen/Risiken von SD-WAN (Lizenzkosten, Abhängigkeit vom Controller, Aufwand für Policy-Design, Fehlerbild bei Controller-Ausfall).

<details><summary>Lösungsschlüssel</summary>

1. A: eher nein (Mehrwert gering, ein Pfad), B: nein (kein Transport, Isolationsanforderung), C: ja (Skalierung, Transportunabhängigkeit, Cloud-Zugriff).
2. Kosten (Lizenz, Betrieb), Komplexität des Policy-Designs und der Fehlersuche (Overlay + Underlay), Abhängigkeit von Controller-Erreichbarkeit (bestehende Tunnel laufen weiter, Änderungen nicht), Reifegrad von Funktionen je Plattform.

</details>

## Fall 5: SD-Access: Komponenten und Verantwortlichkeiten

**Szenario.** Ein Campus soll auf Cisco SD-Access umgestellt werden: Edge-Switches mit Catalyst 9300, Border zum Rechenzentrum, Cisco ISE vorhanden.

**Aufgaben**

1. Beschreibe die Rollen Catalyst Center, ISE, Fabric Control Plane Node, Border Node, Edge Node, Intermediate Node.
2. Welche Protokolle/Technologien übernehmen Control Plane (LISP), Data Plane (VXLAN) und Policy Plane (SGT/TrustSec)? Wo liegt der Anycast-Gateway?
3. Was passiert, wenn ein Endgerät an einem Edge angeschlossen und per 802.1X authentifiziert wird (Ablauf: Registrierung beim Control Plane, VN/SGT-Zuweisung)?

<details><summary>Lösungsschlüssel</summary>

1. **Catalyst Center** = Design, Policy, Automation, Assurance; **ISE** = Authentifizierung/Autorisierung, SGT-Zuweisung; **Control Plane Node** = LISP-Map-Server/-Resolver (Host-Tracking-Datenbank); **Border Node** = Verbindung ins Außen (Fabric-Edge zu Nicht-Fabric); **Edge Node** = Anschluss der Endgeräte, Anycast-Gateway, VXLAN-Kapselung; **Intermediate Node** = reines Layer-3-Underlay.
2. Control Plane: **LISP**; Data Plane: **VXLAN** (Fabric-Header trägt VNI und SGT/GPO); Policy: **SGT/TrustSec** (SGACL-Durchsetzung). Der Anycast-Gateway liegt auf jedem Edge (gleiche IP/MAC im Fabric).
3. Der Edge authentifiziert über ISE, erhält VN/VLAN und SGT, registriert die Endpunkt-EID (MAC/IP) beim Control Plane Node. Andere Edges fragen bei Bedarf den Control Plane Node nach dem RLOC (Map-Request) und kapseln per VXLAN.

</details>

## Fall 6: Fabric oder klassischer Campus?

**Szenario.** Ein Krankenhaus mit häufig umziehenden Endgeräten (Geräte, Laptops), strengen Segmentierungsanforderungen und kleiner Netzwerkmannschaft.

**Aufgaben**

1. Gib drei Argumente für SD-Access und drei dagegen.
2. Welche Alternativen gibt es, falls SD-Access (noch) nicht passt (EVPN-VXLAN-Campus, klassisches Design mit TrustSec/ISE)?

<details><summary>Lösungsschlüssel</summary>

1. Dafür: einheitliche Policy bei Mobilität (SGT folgt dem Endgerät), Segmentierung per VN, Automatisierung/Assurance durch Catalyst Center. Dagegen: Lizenz-/Hardwarevoraussetzungen, Migrationsaufwand und neue Skills, Komplexität bei Fehlersuche (Overlay), Abhängigkeit von Catalyst Center und ISE.
2. Klassisches Campus mit TrustSec/ISE (SGT ohne Fabric), EVPN-VXLAN-Campus als offener Fabric-Ansatz.

</details>

## Fall 7: Hypervisor-Typen und Virtual Switching

**Szenario.** Auf einem ESXi-Host laufen zwei VMs im VLAN 10 und eine im VLAN 20, Uplinks gehen mit zwei NICs an ein Switch-Paar.

**Aufgaben**

1. Klassifiziere ESXi, Hyper-V, KVM, VirtualBox und VMware Workstation als Typ-1 oder Typ-2.
2. Wie arbeitet der Standard-vSwitch (Layer 2, Portgruppen mit VLAN-ID, Uplinks)? Nimmt er an STP teil? Wohin müssen die Uplinks (Trunk, PortFast)?
3. NIC-Teaming `Route based on IP hash`: Was muss auf dem physischen Switch konfiguriert sein, und was passiert sonst (MAC-Flapping)?
4. Warum nutzt man für virtuelle Router paravirtualisierte vNICs (VMXNET3/virtio) und reserviert vCPU/RAM (Overcommitment)?

<details><summary>Lösungsschlüssel</summary>

1. Typ 1: ESXi, Hyper-V, KVM (meist so eingeordnet). Typ 2: VirtualBox, VMware Workstation.
2. Layer-2-Switch in Software; Portgruppen tragen VLAN-IDs; Uplinks sind Trunks. Der Standard-vSwitch führt kein STP aus und leitet keine BPDUs weiter, daher werden physische Ports typischerweise als Trunk mit PortFast betrieben (mit BPDU Guard).
3. Statischer EtherChannel (`mode on`, kein LACP) am physischen Switch. Ohne ihn sieht der Switch dieselbe MAC auf mehreren Ports (MAC-Flapping).
4. Paravirtualisierte vNICs sparen Hypervisor-CPU und bieten mehr Durchsatz als emulierte (E1000). Echtzeit-Paketverarbeitung leidet unter Overcommitment (Latenz/Jitter), deshalb Reservierungen.

</details>

## Fall 8: Virtuelle Maschinen: Ressourcen und Netzanbindung

**Szenario.** Eine virtuelle Firewall soll 5 Gbit/s Durchsatz liefern. Der Host hat zwei 10G-NICs, vier VMs laufen darauf.

**Aufgaben**

1. Welche Komponenten gehören zu einer VM (vCPU, RAM, vNIC, virtuelle Disk, Snapshots)? Was ist ein Snapshot nicht (ein Backup)?
2. Wann hilft SR-IOV oder PCI-Passthrough? Welche Funktionen gehen dabei verloren (vMotion, vSwitch-Funktionen)?
3. Skizziere den Datenpfad VM → vNIC → vSwitch → pNIC → Access-Switch.

<details><summary>Lösungsschlüssel</summary>

1. vCPU, RAM, vNIC, virtuelle Disks, Konfigurationsdatei. Ein Snapshot hält den Zustand zu einem Zeitpunkt, ist aber kein Backup (abhängig vom Basis-Disk, wächst, kein Schutz bei Datenverlust).
2. SR-IOV/Passthrough umgehen den vSwitch: weniger Latenz, höherer Durchsatz. Nachteile: eingeschränkte Mobilität (kein Live-Migrate), keine vSwitch-Features (Port Mirroring, Policy).
3. Frame der VM → vNIC → vSwitch/Portgruppe (VLAN-Tag) → Uplink-pNIC → Trunk zum Access-Switch.

</details>

## Fall 9: Catalyst Center: Automation und Assurance

**Szenario.** Ein Betreiber will 300 Switches mit Day-0-Provisioning (PnP), Software-Image-Management und einer einheitlichen Sicht auf den Netzzustand betreiben.

**Aufgaben**

1. Welche Funktionsbereiche von Catalyst Center (Design, Policy, Provision, Assurance, Platform/API) decken diese Anforderungen ab?
2. Was sind Health Scores, Path Trace und Issues, und wie hilft die KI-gestützte Ursachenanalyse (AI Network Analytics, Machine Reasoning)?
3. Wie integrierst du Catalyst Center in eigene Automation (REST-API mit Token, Intent API, Event-Webhooks)?

<details><summary>Lösungsschlüssel</summary>

1. Design (Hierarchie, Einstellungen), Provision (PnP, Templates, SWIM), Policy (SD-Access/Segmentierung), Assurance (Health, Issues), Platform (APIs).
2. Health Score: aggregierte Gesundheit je Gerät/Client/Anwendung. Path Trace: Hop-für-Hop-Analyse zwischen zwei Endpunkten inkl. ACL-/Routing-Sicht. Issues: erkannte Probleme mit Handlungsempfehlungen. KI-Analyse: Baselining und Korrelation (AI Network Analytics) sowie logische Ursachenketten (Machine Reasoning Engine).
3. Authentifizierung per Token (POST auf /dna/system/api/v1/auth/token), danach Intent-API-Aufrufe mit Header `X-Auth-Token`, Ereignisse per Webhook an externe Systeme. Siehe Drills in Lab 20 (Mock-API).

</details>

## Fall 10: Cloud oder On-Premises? Entwurf einer hybriden Anbindung

**Szenario.** Ein Unternehmen verlagert Anwendungen in die Public Cloud, behält aber ein Rechenzentrum. Mitarbeiter greifen aus Filialen zu.

**Aufgaben**

1. Nenne Entscheidungskriterien für Cloud vs. On-Premises (Latenz, Compliance, Kosten, Skalierung, Betriebsmodell).
2. Wie bindest du die Cloud an (Internet-VPN, dedizierte Leitung/Direct Connect, SD-WAN-Cloud-Onramp)?

<details><summary>Lösungsschlüssel</summary>

1. Latenz-/Datenschutzanforderungen, Compliance, Kostenstruktur (Capex/Opex), Elastizität, vorhandene Skills, Abhängigkeiten.
2. IPsec-VPN über Internet (günstig, schwankende Qualität), dedizierte Leitung (planbar, teurer), SD-WAN mit Cloud-Onramp für direkten Zugriff aus den Filialen.

</details>

