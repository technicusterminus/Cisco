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

1. **2,4 : 1, also sehr komfortabel.** 48 × 1 Gbit/s ergeben 48 Gbit/s Nutzerbandbreite, die Uplinks liefern 2 × 10 = 20 Gbit/s. Üblich sind am Access bis etwa 20 : 1, weil nie alle Nutzer gleichzeitig Volllast senden.
2. **160 Gbit/s zur Distribution, für 4 : 1 reichen 40 Gbit/s zum Core.** 8 Switches × 20 Gbit/s = 160 Gbit/s, geteilt durch 4 ergibt 40 Gbit/s. Praktisch nimmst du zwei 40-Gbit/s-Uplinks, damit ein Ausfall nicht sofort überlastet. Das ergibt 80 Gbit/s und damit 2 : 1.
3. **3-Tier.** Sechs Gebäude brauchen je ein Distribution-Paar, und ein eigener Core verbindet sie, ohne dass jede Distribution mit jeder verkabelt werden muss. Fehler bleiben im Gebäude, und ein siebtes Gebäude hängst du einfach an den Core. Collapsed Core lohnt sich bei wenigen Gebäuden auf engem Raum.
4. **Kleine Layer-2-Domänen, Redundanz auf Gerät und Pfad, modulare Bausteine.** Routed Access oder Layer 2 höchstens pro Gebäude begrenzt die Failure Domain. Doppelte Geräte und Links verhindern Single Points of Failure. Klare Schnittstellen zwischen Access, Distribution und Core machen Erweiterungen planbar.

</details>

## Fall 2: Verfügbarkeit rechnen und Ausfalldomänen erkennen

**Szenario.** Ein Standort hängt an einem einzelnen WAN-Router (99,9 % Verfügbarkeit) und einem einzelnen Core-Switch (99,9 %). Die Geschäftsleitung fordert 99,99 %.

**Aufgaben**

1. Wie hoch ist die Gesamtverfügbarkeit in Reihe (ein Pfad)? Wie viele Minuten Ausfall pro Jahr sind das?
2. Wie ändert sich das, wenn beide Komponenten doppelt (parallel) vorhanden sind? Rechne je Stufe `1 − (1 − a)²`.
3. Welche Techniken nutzt du für Gerätefehler (FHRP, StackWise, SSO/NSF), Linkfehler (EtherChannel, ECMP) und Standortfehler (Dual-Site)?
4. Wo steckt trotz doppelter Geräte noch ein Single Point of Failure (Stromversorgung, gemeinsames Gehäuse, Software-Bug, gemeinsame Glasfaserstrecke)?

<details><summary>Lösungsschlüssel</summary>

1. **99,80 %, also rund 17,5 Stunden Ausfall im Jahr.** In Reihe multiplizierst du: 0,999 × 0,999 = 0,998001. Die Ausfallzeit ist 0,1999 % von 525 600 Minuten, das sind etwa 1050 Minuten.
2. **Rund 99,9998 %, etwa eine Minute Ausfall im Jahr.** Je Stufe parallel: 1 − 0,001² = 0,999999. Beide Stufen in Reihe: 0,999999² ≈ 0,999998. Gefordert waren 99,99 % (52,6 min/Jahr), das ist deutlich übertroffen.
3. **Gerät: FHRP, StackWise/VSS, SSO/NSF. Link: EtherChannel, ECMP. Standort: zweiter Standort, getrennte Provider.** Jede Technik deckt nur ihre Fehlerart ab, deshalb brauchst du alle drei Ebenen.
4. **Überall, wo sich die doppelten Geräte etwas teilen.** Typisch sind dieselbe Stromversorgung, derselbe Kabelkanal oder dieselbe Glasfaserstrecke, ein Software-Fehler, der beide identischen Geräte trifft, und ein gemeinsamer Controller.

</details>

## Fall 3: Branch mit zwei Internetleitungen: DMVPN oder SD-WAN?

**Szenario.** Ein Unternehmen betreibt 120 Filialen mit je zwei Internetanschlüssen. Gefordert: Sprache muss bei Verlust >1 % oder Latenz >150 ms automatisch auf den anderen Anschluss wechseln, Zero-Touch-Rollout neuer Filialen, zentrale Richtlinien.

**Aufgaben**

1. Ordne die SD-WAN-Komponenten den Ebenen zu: Orchestration, Management, Control Plane, Data Plane (WAN Edge, Controller, Manager, Validator).
2. Wie erreicht SD-WAN den Wechsel bei Verlust/Latenz (BFD-Messung, Application-Aware Routing/SLA-Klassen)? Welche Rolle spielt OMP und TLOC?
3. Welche Vorteile bringt SD-WAN gegenüber einem klassischen Hub-and-Spoke mit statisch konfigurierten VPNs?

<details><summary>Lösungsschlüssel</summary>

1. **Validator = Orchestration, Manager = Management, Controller = Control Plane, WAN Edge = Data Plane.** Der Validator (früher vBond) übernimmt Erstkontakt und Authentifizierung. Der Manager (vManage) verwaltet Konfiguration, Monitoring und Policies. Der Controller (vSmart) verteilt per OMP Routen und Policies. Die WAN Edges (cEdge/vEdge) leiten die Daten weiter.
2. **BFD misst jeden Tunnel, Application-Aware Routing wechselt bei verletztem SLA.** Die Edges messen über BFD Verlust, Latenz und Jitter. Eine App-Route-Policy legt SLA-Klassen fest, etwa 1 % Verlust und 150 ms für Sprache. Wird die Grenze überschritten, wählt die Edge den anderen Pfad. OMP transportiert Routen, TLOCs und Policies zwischen Edges und Controller. Ein TLOC ist der Endpunkt eines Tunnels: Adresse, Farbe und Encapsulation.
3. **Transportunabhängig, zentral gesteuert, Zero-Touch.** Du mischst MPLS, Internet und LTE frei, änderst Richtlinien an einer Stelle für alle 120 Filialen und bringst neue Filialen ohne Vor-Ort-Konfiguration ans Netz. Dazu kommen die Pfadwahl nach Anwendung und Segmentierung per VPN.

</details>

## Fall 4: Wann passt SD-WAN nicht?

**Szenario.** Drei Standorte: (A) kleines Büro mit einem einzigen Anschluss, kein Wachstum; (B) Fabrik mit strikt getrenntem OT-Netz, keine Internetanbindung; (C) 400 Filialen, wechselnde Provider, Cloud-Anwendungen.

**Aufgaben**

1. Beurteile für jeden Standort, ob SD-WAN sinnvoll ist, und begründe.
2. Nenne drei Grenzen/Risiken von SD-WAN (Lizenzkosten, Abhängigkeit vom Controller, Aufwand für Policy-Design, Fehlerbild bei Controller-Ausfall).

<details><summary>Lösungsschlüssel</summary>

1. **A nein, B nein, C ja.** A hat nur einen Anschluss, es gibt also keinen Pfad zur Auswahl. B hat keinen Transport und muss isoliert bleiben. C profitiert von Skalierung, wechselnden Providern und direktem Cloud-Zugriff.
2. **Kosten, Komplexität und die Abhängigkeit vom Controller.** Lizenzen und Betrieb kosten Geld. Policy-Design und Fehlersuche werden schwieriger, weil Overlay und Underlay zusammenspielen. Fällt der Controller aus, laufen bestehende Tunnel weiter, aber Änderungen sind nicht möglich. Außerdem unterscheidet sich der Funktionsumfang je Plattform.

</details>

## Fall 5: SD-Access: Komponenten und Verantwortlichkeiten

**Szenario.** Ein Campus soll auf Cisco SD-Access umgestellt werden: Edge-Switches mit Catalyst 9300, Border zum Rechenzentrum, Cisco ISE vorhanden.

**Aufgaben**

1. Beschreibe die Rollen Catalyst Center, ISE, Fabric Control Plane Node, Border Node, Edge Node, Intermediate Node.
2. Welche Protokolle/Technologien übernehmen Control Plane (LISP), Data Plane (VXLAN) und Policy Plane (SGT/TrustSec)? Wo liegt der Anycast-Gateway?
3. Was passiert, wenn ein Endgerät an einem Edge angeschlossen und per 802.1X authentifiziert wird (Ablauf: Registrierung beim Control Plane, VN/SGT-Zuweisung)?

<details><summary>Lösungsschlüssel</summary>

1. **Catalyst Center plant und automatisiert, ISE entscheidet über Zugang, die Fabric-Rollen transportieren.** Catalyst Center deckt Design, Policy, Automation und Assurance ab. ISE authentifiziert und vergibt die SGT. Der Control Plane Node ist LISP-Map-Server und -Resolver, also die Datenbank, wo welcher Host steht. Der Border Node verbindet die Fabric mit der Außenwelt. Der Edge Node schließt Endgeräte an, ist Anycast-Gateway und kapselt in VXLAN. Der Intermediate Node routet nur im Underlay.
2. **Control Plane LISP, Data Plane VXLAN, Policy Plane SGT/TrustSec. Das Anycast-Gateway liegt auf jedem Edge.** Der VXLAN-Header trägt neben der VNI auch die SGT. Durchgesetzt wird per SGACL. Weil jedes Edge dieselbe Gateway-IP und -MAC hat, behält ein Endgerät sein Gateway, egal wo es steckt.
3. **Authentifizieren, VN und SGT zuweisen, beim Control Plane registrieren.** Der Edge fragt ISE, bekommt VN/VLAN und SGT und meldet die EID (MAC/IP) des Geräts beim Control Plane Node an. Will ein anderer Edge das Gerät erreichen, fragt er per Map-Request nach dem RLOC und kapselt den Verkehr per VXLAN dorthin.

</details>

## Fall 6: Fabric oder klassischer Campus?

**Szenario.** Ein Krankenhaus mit häufig umziehenden Endgeräten (Geräte, Laptops), strengen Segmentierungsanforderungen und kleiner Netzwerkmannschaft.

**Aufgaben**

1. Gib drei Argumente für SD-Access und drei dagegen.
2. Welche Alternativen gibt es, falls SD-Access (noch) nicht passt (EVPN-VXLAN-Campus, klassisches Design mit TrustSec/ISE)?

<details><summary>Lösungsschlüssel</summary>

1. **Dafür: Policy folgt dem Gerät, Segmentierung per VN, Automatisierung. Dagegen: Voraussetzungen, Migration, Komplexität.** Die SGT wandert mit dem umziehenden Gerät, die Regeln gelten überall gleich, und Catalyst Center entlastet das kleine Team. Dagegen sprechen Lizenz- und Hardwarevoraussetzungen, Migrationsaufwand mit neuen Skills, schwierigere Fehlersuche im Overlay und die Abhängigkeit von Catalyst Center und ISE.
2. **Klassischer Campus mit TrustSec/ISE oder ein EVPN-VXLAN-Campus.** Die erste Variante bringt die SGT-Segmentierung ohne Fabric. Die zweite ist ein offener Fabric-Ansatz ohne Catalyst Center.

</details>

## Fall 7: Hypervisor-Typen und Virtual Switching

**Szenario.** Auf einem ESXi-Host laufen zwei VMs im VLAN 10 und eine im VLAN 20, Uplinks gehen mit zwei NICs an ein Switch-Paar.

**Aufgaben**

1. Klassifiziere ESXi, Hyper-V, KVM, VirtualBox und VMware Workstation als Typ-1 oder Typ-2.
2. Wie arbeitet der Standard-vSwitch (Layer 2, Portgruppen mit VLAN-ID, Uplinks)? Nimmt er an STP teil? Wohin müssen die Uplinks (Trunk, PortFast)?
3. NIC-Teaming `Route based on IP hash`: Was muss auf dem physischen Switch konfiguriert sein, und was passiert sonst (MAC-Flapping)?
4. Warum nutzt man für virtuelle Router paravirtualisierte vNICs (VMXNET3/virtio) und reserviert vCPU/RAM (Overcommitment)?

<details><summary>Lösungsschlüssel</summary>

1. **Typ 1: ESXi, Hyper-V, KVM. Typ 2: VirtualBox, VMware Workstation.** Typ 1 läuft direkt auf der Hardware, Typ 2 als Programm auf einem Betriebssystem. KVM ordnet man meist Typ 1 zu, weil es Teil des Linux-Kernels ist.
2. **Ein Layer-2-Switch in Software, ohne STP. Die Uplinks sind Trunks, die physischen Ports Edge-Ports.** Portgruppen tragen die VLAN-IDs. Der Standard-vSwitch nimmt nicht an STP teil und leitet keine BPDUs weiter, er bildet aber auch keine Schleife. Deshalb betreibst du die Switch-Ports als Trunk mit PortFast und BPDU Guard.
3. **Ein statischer EtherChannel (`mode on`) auf dem physischen Switch.** Der Standard-vSwitch spricht kein LACP. Fehlt der Channel, sieht der Switch dieselbe MAC auf mehreren Ports und meldet MAC-Flapping.
4. **Wegen Durchsatz und gleichmäßiger Latenz.** Paravirtualisierte vNICs sparen Hypervisor-CPU und schaffen mehr als emulierte Karten wie E1000. Paketverarbeitung leidet unter Overcommitment, weil die VM auf CPU-Zeit warten muss. Reservierungen verhindern Latenz und Jitter.

</details>

## Fall 8: Virtuelle Maschinen: Ressourcen und Netzanbindung

**Szenario.** Eine virtuelle Firewall soll 5 Gbit/s Durchsatz liefern. Der Host hat zwei 10G-NICs, vier VMs laufen darauf.

**Aufgaben**

1. Welche Komponenten gehören zu einer VM (vCPU, RAM, vNIC, virtuelle Disk, Snapshots)? Was ist ein Snapshot nicht (ein Backup)?
2. Wann hilft SR-IOV oder PCI-Passthrough? Welche Funktionen gehen dabei verloren (vMotion, vSwitch-Funktionen)?
3. Skizziere den Datenpfad VM → vNIC → vSwitch → pNIC → Access-Switch.

<details><summary>Lösungsschlüssel</summary>

1. **vCPU, RAM, vNIC, virtuelle Disk und Konfigurationsdatei. Ein Snapshot ist kein Backup.** Ein Snapshot hält nur den Zustand zu einem Zeitpunkt fest und hängt an der Basis-Disk. Geht die verloren, ist auch der Snapshot wertlos.
2. **Wenn Durchsatz und Latenz wichtiger sind als Flexibilität.** SR-IOV und Passthrough umgehen den vSwitch. Dafür verlierst du Live-Migration (vMotion) und die vSwitch-Funktionen wie Port Mirroring oder Policies.
3. **VM → vNIC → vSwitch/Portgruppe (VLAN-Tag) → Uplink-pNIC → Trunk zum Access-Switch.** Das VLAN-Tag setzt die Portgruppe, die VM selbst sendet ungetaggt.

</details>

## Fall 9: Catalyst Center: Automation und Assurance

**Szenario.** Ein Betreiber will 300 Switches mit Day-0-Provisioning (PnP), Software-Image-Management und einer einheitlichen Sicht auf den Netzzustand betreiben.

**Aufgaben**

1. Welche Funktionsbereiche von Catalyst Center (Design, Policy, Provision, Assurance, Platform/API) decken diese Anforderungen ab?
2. Was sind Health Scores, Path Trace und Issues, und wie hilft die KI-gestützte Ursachenanalyse (AI Network Analytics, Machine Reasoning)?
3. Wie integrierst du Catalyst Center in eigene Automation (REST-API mit Token, Intent API, Event-Webhooks)?

<details><summary>Lösungsschlüssel</summary>

1. **Design, Provision, Policy, Assurance und Platform.** Design legt Hierarchie und Einstellungen fest. Provision deckt PnP, Templates und Image-Management (SWIM) ab. Policy steuert Segmentierung, Assurance zeigt den Zustand, Platform öffnet die APIs.
2. **Health Score bewertet, Path Trace verfolgt, Issues melden. Die KI findet Muster und Ursachen.** Der Health Score fasst die Gesundheit je Gerät, Client oder Anwendung zusammen. Path Trace zeigt Hop für Hop den Weg zwischen zwei Endpunkten mit Routing und ACLs. Issues sind erkannte Probleme mit Empfehlung. AI Network Analytics lernt das Normalverhalten und korreliert Abweichungen, die Machine Reasoning Engine leitet logische Ursachenketten ab.
3. **Token holen, dann die Intent API aufrufen, Ereignisse per Webhook empfangen.** Den Token bekommst du per POST auf `/dna/system/api/v1/auth/token`. Jeder weitere Aufruf trägt ihn im Header `X-Auth-Token`. Webhooks melden Ereignisse an externe Systeme. Die Drills in Lab 20 üben das an einer Mock-API.

</details>

## Fall 10: Cloud oder On-Premises? Entwurf einer hybriden Anbindung

**Szenario.** Ein Unternehmen verlagert Anwendungen in die Public Cloud, behält aber ein Rechenzentrum. Mitarbeiter greifen aus Filialen zu.

**Aufgaben**

1. Nenne Entscheidungskriterien für Cloud vs. On-Premises (Latenz, Compliance, Kosten, Skalierung, Betriebsmodell).
2. Wie bindest du die Cloud an (Internet-VPN, dedizierte Leitung/Direct Connect, SD-WAN-Cloud-Onramp)?

<details><summary>Lösungsschlüssel</summary>

1. **Latenz, Compliance, Kosten, Skalierung und Betriebsmodell.** Dazu gehören Datenschutz, die Frage Capex oder Opex, Elastizität, vorhandene Skills und Abhängigkeiten zwischen den Anwendungen.
2. **IPsec-VPN über Internet, dedizierte Leitung oder SD-WAN mit Cloud-Onramp.** Das VPN ist günstig, aber in der Qualität schwankend. Die dedizierte Leitung ist planbar und teurer. Cloud-Onramp lässt die Filialen direkt und mit Pfadwahl in die Cloud.

</details>

