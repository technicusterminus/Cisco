# CCNP ENCOR in CML

Für Lernende mit CCNA-Kenntnissen und CLI-Praxis. Die Referenz ist **350-401 ENCOR v1.2**, seit 19. März 2026, geprüft am 19. November 2026. Nummern und Gewichtungen folgen den Cisco-Zielen. [Blueprint](https://learningcontent.cisco.com/documents/marketing/exam-topics/350-401-ENCORE-v1.2.pdf) · [Cisco Release Notes](https://learningcontent.cisco.com/documents/marketing/exam-topics/CCNP_Enterprise_v1.1_and_1.2_Release_Notes.pdf)

Starte mit [AUFGABEN.md](AUFGABEN.md) oder dem Guide der importierten Variante. [NACHWEISE.md](NACHWEISE.md) enthält gestufte Hinweise, Prüfschritte und Sollbefunde. Die vorhandenen Lab-READMEs sind die geführte Fassung. Die Konfigurationen und Fehlerlisten unter `solutions/` dienen der Abnahme.

## Inventar des Ausgangsstands

Verglichen wurde GitHub-Commit [1bde11b](https://github.com/technicusterminus/Cisco/commit/1bde11b403f211e8b2afec5a996b9b8d32a4a1fc). In jedem der 33 Gerätelabs gehören `topology.yaml`, `topology-repair.yaml`, `README.md`, `solutions/FAULTS.md` und die gerätespezifischen `solutions/*.cfg` zur selben stabilen Nummer. Die 159 Tickets haben nummerngleiche Lösungseinträge. Alle 110 CFG-Dateien sind einem vorhandenen Node zugeordnet. Im Ausgangsstand stimmen Cisco-Hostnames und Node-Labels überein. Keine zwei Labs haben zugleich identische Startkonfigurationen und Verkabelung. Ein Gerät, das nur Infrastruktur liefert, braucht keine zusätzliche Lösungskonfiguration. Lab 20 ist ein lokales Drill-Paket. Labs 21 und 22 sind Fallstudien mit Lösungsschlüssel. [Bestandsübersicht](https://github.com/technicusterminus/Cisco/blob/1bde11b403f211e8b2afec5a996b9b8d32a4a1fc/3-CCNP-ENCOR-350-401/CML-Labs/README.md)

| Lab | Ausgangsbefund und Rolle im Curriculum |
|---|---|
| 01 | OSPFv2, ABR und Summary. Geführt beginnen, Präfix und Netztyp getrennt abnehmen. |
| 02 | Dual Stack. R3-Adresse in der Tabelle korrigiert. OSPFv3 im Pflichtpfad um eine zweite Area erweitert. IPv6-Filter und Summary bleiben offen. |
| 03 | Direkte eBGP-Sitzungen und Best Path. Ausfall mit unabhängigem Pfadnachweis üben. |
| 04 | PBR mit IP SLA. Aktive Messung und Datenpfad unterscheiden. |
| 05 | Trunks und EtherChannel. LACP/PAgP und VLAN-Symptome vorhanden. Gezielte DTP- und statische EtherChannel-Diagnose vertiefen. |
| 06 | RSTP, MST und Guards. VLAN-Trunks als Grundlage vorbereitet. Test-Switch hat eine separate Rolle. |
| 07 | HSRP/VRRP und Tracking. GLBP als Vertiefung, VRRP-Verhalten am konkreten IOSv-Image prüfen. |
| 08 | NTP, Syslog und SNMP. PTP durch einen Konfigurationsauszug ergänzt. Genauigkeitsmessung braucht geeignete Zeitquellen und Plattformen. |
| 09 | NAT und PAT mit unterschiedlichen Flüssen. Topologie und Ausgangsrouting ähneln bewusst Lab 10. |
| 10 | ACLs und CoPP. Transit- und Routerverkehr separat testen. CoPP und Zähler am Image abnehmen. |
| 11 | Lokale AAA und Fallback. Der externe TACACS+-Server fehlt absichtlich. Erfolgreiche Server-Autorisierung und Reject bleiben offen. |
| 12 | PIM und IGMP. Im Ausgangsstand fehlte das zugesagte Routing in der Bauvariante. OSPF vorbereitet, Multicast bleibt Aufgabe. |
| 13 | VRF-Lite. Routing in beiden VRFs nachweisen und Trennung mit Gegenprobe belegen. |
| 14 | GRE/IPsec. Tunnelstatus und IPsec-Zähler getrennt betrachten. |
| 15 | LISP. EIDs/RLOCs und Mapping erklären. IOSv-Unterstützung ist imageabhängig. |
| 16 | VXLAN. OSPF, VTEP-Loopbacks und Transport-MTU sind Voraussetzungen. NVE und VNI bleiben die Übung. |
| 17 | QoS. Imageabhängige MQC-Fähigkeiten. Zähler und Markierung als Ergebnis, Timing als Plattformgrenze. |
| 18 | Flexible NetFlow. Port-Mirroring auf IOSvL2 blockierte die vorgesehene Live-Übung. Separates SPAN/RSPAN/ERSPAN-Exhibit und Link-Capture für FNF. |
| 19 | RESTCONF/NETCONF und EEM. Isolierter Ubuntu-Client ersetzt den vom Rechner nicht direkt erreichbaren NAT-Pfad. SSH-Bootstrap und konkretes CSR-Image abnehmen. |
| 20 | Lokale Python- und JSON-Drills. Controller-Mock übt vorwiegend Catalyst-Center-nahe Abläufe. |
| 21 | Designfälle zu Netzarchitektur, Verfügbarkeit, Overlays, Virtualisierung und Catalyst Center. Erklär- und Entscheidungsaufgaben. |
| 22 | REST-API-Sicherheit und Security-Design als Fälle mit Auswertung. |
| 23 | Integriertes Campus-/Edge-Abschlusslab. Schlechter Ausgangspfad kann mehrere Tickets maskieren. |
| 24 | WAN-/VRF-/IPsec-Transfer. Underlay und Overlay separat abnehmen. |
| 25 | Klassisches EIGRP. Als Vergleichsübung zu OSPF verwenden; Stub und Authentisierung vertiefen. |
| 26 | iBGP/Route Reflector als Vertiefung. Loopback-Routing vorbereitet. Kein Ersatz für direktes eBGP. |
| 27 | Redistribution als Vertiefung. Die IGP-Domänen laufen vor der Aufgabe, die Übergänge bleiben frei. |
| 28 | IPv4-OSPF-Vertiefung. Area-Typen, Summaries und Authentisierung; kein IPv6-Nachweis. |
| 29 | PBR nach Quelle und Anwendung. Im Ausgangsstand fehlten die versprochenen statischen Hin- und Rückwege. |
| 30 | Routing-Transfer mit EIGRP/OSPF/BGP. Alternative Pfade können einzelne Defekte verbergen. |
| 31 | MST/PVST-Übergang. Region, Digest, Root-Port und Boundary getrennt prüfen. Vier Tickets fehlen im separaten Ticket-Trainer. |
| 32 | SSM, Bidir-PIM und MSDP. Vergleich pro Gruppe, Live-Unterstützung je IOSv-Release offen. |
| 33 | Diagnosewerkzeuge mit Routing-Baseline. Exakte Ping- und Traceroute-Zeichen hängen vom Fehlerort ab. |
| 34 | OSPFv2-Filter, Netztypen und MTU. Gefiltertes RIB und LSDB getrennt nachweisen. |
| 35 | IP SLA, Tracking und Jitter. Entfernten Ausfall und Messpfad unterscheiden. |
| 36 | Pilot für EEM-Konstruktion. Fertiges Routing als Ereignisquelle, eigene Policy, unabhängige Verifikation und Gegenprobe. |

## Priorisierter Befund

- **P0 · Lab 12 und 29.** Die Bauanleitungen setzten Routing voraus, das in den Startdateien fehlte. Die Lernaufgaben beginnen jetzt auf der zugesagten Grundlage. [Lab 12, Voraussetzung](https://github.com/technicusterminus/Cisco/blob/1bde11b403f211e8b2afec5a996b9b8d32a4a1fc/3-CCNP-ENCOR-350-401/CML-Labs/12-Multicast-PIM/README.md#L35) · [Lab 29, erster Prüfschritt](https://github.com/technicusterminus/Cisco/blob/1bde11b403f211e8b2afec5a996b9b8d32a4a1fc/3-CCNP-ENCOR-350-401/CML-Labs/29-PBR-Quelle-Anwendung/README.md#L40)
- **P0 · Lab 18 und 19.** IOSvL2 unterstützt kein Port-Mirroring. CML-NAT richtet sich an von Lab-Knoten initiierte Verbindungen. Die überarbeiteten Szenarien verlangen nur nachweisbare Messungen bzw. nutzen einen Client auf demselben Lab-Segment. [Cisco IOSvL2](https://developer.cisco.com/docs/modeling-labs/iosvl2/) · [Cisco External Connectors](https://developer.cisco.com/docs/modeling-labs/external-connectors/)
- **P1 · Tiefe und Verifikation.** OSPFv3 mit Summary/Filter, dynamischer Trunk und statisches Bündel im Reparaturmodus, RSPAN/ERSPAN live sowie echter AAA-Server-REJECT sind offene Vertiefungen. Die Grundübung für jede verbleibende Teilfähigkeit steht in der Matrix. SD-WAN-Manager- und Catalyst-Center-Payloads sind separat zu vergleichen.
- **P2 · Übersicht.** Wiederverwendete Strukturen wie 09/10 und 04/29 sind beabsichtigt. Gleichartige Ausgangstopologien trainieren unterschiedliche Nachweise. Lab 18/19 haben CML-spezifische Varianten; die EVE-Dateierzeugung verwendet die separaten Topologiezuordnungen.

## Reihenfolge

Nach 01, 03 und 35 folgt als zusätzliche CML-Praxis die [Routing-Assurance-Strecke](Routing-Assurance/README.md) (60 Minuten). Sie verknüpft 3.2.b, 3.2.c, 4.1 und 4.4. Der Nachweis umfasst OSPF-Pfadwahl in beiden Richtungen, BGP-Ankündigung und Installation sowie eine aktive Messung mit definiertem Rückweg.

| Abschnitt | Reihenfolge | Voraussetzung und späterer Nachweis |
|---|---|---|
| Geführter Einstieg | 05 → 06 → 07 → 08 → 33 | CCNA, VLAN, IPv4 und CLI. Schichtdiagnose später in 23. |
| Routing | 01 → 02 (IPv6) → 25 → 03 → 28 → 34 | Adressierung, direkte Nachbarn, LSDB/RIB. In 30 mehrere mögliche Ursachen selbst unterscheiden. |
| Policy und Sicherheit | 09 → 10 → 11 → 29 → 04 → 35 | Routing und ACL-Matches. In 23 mehrere Kontroll- und Nutzflüsse unterscheiden. |
| Overlays und Multicast | 13 → 14 → 12 → 32; 15 und 16 als Anschauung mit geeignetem Image | Underlay und Overlay trennen. In 24 nach geänderten Randbedingungen anwenden. |
| Assurance und Automation | 17 → 18 → 20 → 19 → 36; Fälle 21 und 22 verteilen | JSON, SSH, TLS und Diagnose. In 36 selbst ein Applet konstruieren und anschließend zwei fremde reparieren. |
| Transfer und Abschluss | 31 → 24 → 30 → **23** | iBGP/RR (26) und Redistribution (27) vor 30 als Vertiefung. In 23 werden Layer 2, Routing, Redundanz und Security am selben Netz geprüft. |

Die Zeitboxen in den Aufgaben beginnen nach dem Boot. Für die Capstones gelten 100 Minuten (24), 90 Minuten (30) und 110 Minuten (23). Pro Ticket Ursache, Änderung, Prüfergebnis und verbleibende Unsicherheit notieren. Bei Zeitablauf den aktuellen Stand dokumentieren. Die Zeiten sind Trainingswerte.

## Vom Einzelthema zum Betriebsfall

Benutze diese Strecke, wenn du Paketweiterleitung, Routing, Security und Assurance zusammenhängend üben möchtest. Wiederkehrender Fall ist ein Arbeitsplatz, der einen Dienst erreichen soll. In jedem Schritt wird die Erklärung aus dem vorherigen Lab für eine neue Entscheidung benötigt. Die Topologien werden getrennt importiert.

| Etappe | Vorwissen und Auftrag | Übergang in die nächste Etappe |
|---|---|---|
| 1 · Weiterleitung in 05 und 01 | Zeichne einen Weg innerhalb eines VLAN und einen Weg zum entfernten Präfix. Markiere, wann der Host die MAC seines Gateways braucht. Zeige Trunk-Zulassung, OSPF-Nachbar und gewählten Next Hop am passenden Gerät. | Sage für den entfernten Dienst Ein- und Ausgangsinterface am Router voraus. Bei unklarer VLAN-Zuordnung zuerst in 05 den tatsächlichen Access-Port prüfen. |
| 2 · Policy in der [ACL-Werkstatt](10-ACL-CoPP/ACL-Werkstatt/README.md) | Nutze dieselbe Wegbeschreibung für eine Regelentscheidung. Beginne mit einer Quellgruppe, ergänze Dienst und Richtung, repariere anschließend zwei unterscheidbare Fehler. | Erkläre, wie auf demselben Weg ein erlaubter HTTP-Aufbau und ein gesperrter Ping zustande kommen. Belege beide Fälle mit Zählerdifferenzen. |
| 3 · Ankündigung in 03 | Wähle ein konkretes Präfix. Verfolge seine Ankündigung vom Ursprung zum Nachbarn und prüfe seine Installation. Ordne eine BGP-Prefix-List dem Austausch von Routen zu. | Erkläre, an welcher Beobachtung du einen fehlenden Routeneintrag von einer ACL-Ablehnung an einem funktionierenden Pfad unterscheiden würdest. |
| 4 · Messung in der [Routing-Assurance-Strecke](Routing-Assurance/README.md) | Erfasse Dienst und Kontrollziel von derselben Quelle. Vergleiche RIB, FIB und IP SLA erst im Normalbetrieb und dann während einer Störung. | Formuliere zwei Ursachen für einen Timeout und benenne für jede genau einen Test, der sie ausschließt. |
| 5 · Transfer in 23 | Öffne das Campus-Abschlusslab. Wähle den Fluss von H20 zu H10. Bestimme den aktuellen HSRP-Forwarder und prüfe den VLAN- und Gateway-Pfad, bevor du aus ACL-Zählern auf eine Ursache schließt. | Gib einem Kollegen Quelle, Ziel, erste abweichende Beobachtung, minimale Änderung und Gegenprobe. Falls ein vorgelagerter Defekt den Test verdeckt, dokumentiere den Zwischenstand und wiederhole den Fluss nach dessen Behebung. |

**Wiederholung ohne Vorlage.** Am Folgetag bearbeitest du nur den Änderungsauftrag der ACL-Werkstatt. Eine Woche später beginnst du mit dem Störungsfall der Routing-Assurance-Strecke und einer leeren Skizze. Notiere getrennt, was du vorhergesagt hast, welche Messung deine Annahme bestätigt oder widerlegt hat und welchen Hinweis du benötigt hast. Eine richtige Vorhersage bei veränderter Quelle oder geändertem Ziel ist der Nachweis für den Transfer. Wer die Lösung erst nach einem Hinweis findet, wiederholt genau diesen Teil mit einer anderen Quelle.

## Abdeckungsmatrix zum Blueprint

**S** = selbstständiger Auftrag mit Abnahmekriterium. **G** = geführt oder teilweise trainiert. **T** = Theorie/Fallstudie zum verlangten Erklärverb. **X** = Live-Übung im vorhandenen Setup nicht verfügbar. **N** = der genannte Teilschritt fehlt. Statuswerte beziehen sich auf das Curriculum. Technische Laufzeit und persönliche Nachweise stehen darunter.

| Ziel | Verlangte Fähigkeit | Stand und konkreter Nachweis | CML-Laufzeit | Persönlich |
|---|---|---|---|---|
| 1.1.a | Entwürfe erklären | T · 21, Campus-/Fabric-/Cloud-Entscheidung begründen. | Fall/Offline | Offen |
| 1.1.b | Verfügbarkeit erklären | T/S · 21 Verfügbarkeitsfall und SSO; 07/23 Gateway-Failover belegen. | Offen | Offen |
| 1.2.a | SD-WAN-Ebenen erklären | T · 21, Rollen im Verbindungsaufbau zuordnen. | Fall/Offline | Offen |
| 1.2.b | SD-WAN-Nutzen und Grenzen erklären | T · 21, Netzanforderung und Ausschlusskriterium nennen. | Fall/Offline | Offen |
| 1.3.a | SD-Access-Ebenen erklären | T · 21, Fabric-Rollen und Paketpfad; 15/16 illustrieren Teilkonzepte. | Fall/Offline | Offen |
| 1.3.b | Campus-Interop erklären | T · 21, Fabric-Grenze und Übergabe begründen. | Fall/Offline | Offen |
| 1.4 | QoS-Konfiguration interpretieren | S/G · 17, Klassifizierung und Capture; Feature-Support imageabhängig. | Offen | Offen |
| 2.1.a | Hypervisor-Typen beschreiben | T · 21, passende Ausführungsarchitektur begründen. | Fall/Offline | Offen |
| 2.1.b | Virtuelle Maschinen beschreiben | T · 21, Ressourcen- und Durchsatzannahmen bewerten. | Fall/Offline | Offen |
| 2.1.c | Virtual Switching beschreiben | T · 21, Portgruppen, VLANs und Uplinks im Fall erklären. | Fall/Offline | Offen |
| 2.2.a | VRF konfigurieren und verifizieren | S · 13/24, Routingtabelle je VRF und Isolationsprobe. | Offen | Offen |
| 2.2.b | GRE/IPsec konfigurieren und verifizieren | S · 14/24, Tunnelpfad und IPsec-Zähler. | Offen | Offen |
| 2.3.a | LISP beschreiben | S/T · 15, EID→RLOC am Mapping oder am Ersatz-Exhibit. | Offen | Offen |
| 2.3.b | VXLAN beschreiben | S · 16, VLAN/VNI/NVE und Paketpfad erklären. | Offen | Offen |
| 3.1.a | Trunks diagnostizieren | S/G · 05/23 statische Trunks; N für ein gezieltes DTP-Reparaturticket. | Offen | Offen |
| 3.1.b | EtherChannel diagnostizieren | S/G · 05/23 LACP/PAgP und Member/Textbefund; N für eigenen Fehler im dauerhaft statischen Bündel. | Offen | Offen |
| 3.1.c | RSTP/MST und Guards konfigurieren/verifizieren | S · 06/31/23, Root, Region und Guards mit Gegenprobe. | Offen | Offen |
| 3.2.a | EIGRP und OSPF vergleichen | S · 02/25/01, Metriken, Pfade und Areas auf konkreten Routen vergleichen. | Offen | Offen |
| 3.2.b | OSPFv2/v3 konfigurieren | S für IPv4 · 01/34/23/24/30; G für IPv6 · 02, Multi-Area-Nachweis; N für IPv6-Summary/Filter. | Offen | Offen |
| 3.2.c | Direktes eBGP konfigurieren/verifizieren | S · 03/24/30, Session, Präfix und Best Path. 26 ist iBGP-Vertiefung. | Offen | Offen |
| 3.2.d | PBR beschreiben | S · 29/04, RIB und Policy-Pfad getrennt erklären. | Offen | Offen |
| 3.3.a | NTP und PTP interpretieren | S für NTP · 08/23; G/T für PTP · 08, Auszug als Ersatzübung. | Offen; PTP als Exhibit | Offen |
| 3.3.b | NAT/PAT konfigurieren | S · 09/23, Adressübersetzung und kontrollierter Fluss. | Offen | Offen |
| 3.3.c | HSRP/VRRP konfigurieren | S · 07, Failover je Instanz; 23 wiederholt HSRP. | Offen | Offen |
| 3.3.d | Multicast-Verfahren beschreiben | S · 12/32, Zustände für ASM/SSM/Bidir/MSDP, IGMP und RPF erklären. | Offen | Offen |
| 4.1 | Mit Diagnosewerkzeugen eingrenzen | S · 08/33, Hypothese mit Gegenprobe; Schichtdiagnose in 23/30. | Offen | Offen |
| 4.2 | Flexible NetFlow konfigurieren/verifizieren | S · 18, getrennte Nachweise für Cache und Export. | Offen | Offen |
| 4.3 | SPAN/RSPAN/ERSPAN konfigurieren | X/G · 18, Konfigurationsersatz mit Zustands- und Ausgabefragen. Live-Abnahme auf kompatiblem Image offen. | Live-Teil fehlt | Offen |
| 4.4 | IP SLA konfigurieren/verifizieren | S · 04/35, SLA, Track, Pfad und simulierte Störung getrennt belegen. | Offen | Offen |
| 4.5 | Catalyst Center inkl. KI-Workflows beschreiben | T · 21, Betriebsaufgaben und KI-gestützte Diagnose anhand des Falls erklären. | Fall/Offline | Offen |
| 4.6 | NETCONF und RESTCONF konfigurieren/verifizieren | S · 19, HTTPS und RPC sowie für RESTCONF einen Write nachweisen. | Offen | Offen |
| 5.1.a | Lines/lokale Anmeldung konfigurieren/verifizieren | S · 11/23, Benutzer, Zugangsweg und effektive Berechtigung getrennt testen. | Offen | Offen |
| 5.1.b | AAA-Authentisierung/-Autorisierung konfigurieren/verifizieren | S/G · 11 lokal und Fallback; N für erfolgreichen externen TACACS+-Zugriff und serverseitigen Reject im Live-Lab. | Offen | Offen |
| 5.2.a | ACLs konfigurieren/verifizieren | S · 10/23, zulässigen und abgelehnten Fluss verifizieren. | Offen | Offen |
| 5.2.b | CoPP konfigurieren/verifizieren | S/G · 10, Zähler für Geräteverkehr und Kontrollfluss. Live-Parser und Zähler offen. | Offen | Offen |
| 5.3 | REST-API-Sicherheit beschreiben | T · 22; 20 lokaler Token-/Statuscode-Drill als Ergänzung. | Fall/Offline | Offen |
| 5.4.a | Threat Defense beschreiben | T · 22, Erkennung und Durchsetzung im Fall zuordnen. | Fall/Offline | Offen |
| 5.4.b | Endpoint Security beschreiben | T · 22, Posture- und Zugangsentscheidung begründen. | Fall/Offline | Offen |
| 5.4.c | NGFW beschreiben | T · 22, Policy-Reihenfolge und Inspektion erklären. | Fall/Offline | Offen |
| 5.4.d | TrustSec und MACsec beschreiben | T · 22, Klassifikation, Enforcement und Linkschutz erklären. | Fall/Offline | Offen |
| 6.1 | Python interpretieren | S · 20, Ausgabe vorhersagen und am Skript erklären. | Fall/Offline | Offen |
| 6.2 | JSON erstellen | S · 20, Payload erstellen und gegen Tests validieren. | Fall/Offline | Offen |
| 6.3 | YANG-Prinzipien beschreiben | S/T · 20/19, Modell, Schlüssel und Instanzdaten unterscheiden. | Offen | Offen |
| 6.4 | Catalyst-Center-/SD-WAN-Manager-APIs beschreiben | G/T · 20 und 21, Catalyst-Center-naher Mock; N für eigenen SD-WAN-Manager-Vergleichsdrill. | Fall/Offline | Offen |
| 6.5 | REST-Antwortcodes und Payloads interpretieren | S · 19/20, Status und Nutzdaten getrennt prüfen. | Offen | Offen |
| 6.6 | EEM-Applet konstruieren | S · 36, eigene Policy, Registrierung, Auslösung, Datei und Negativfall. | Offen | Offen |
| 6.7 | Agentenbasiert/agentenlos vergleichen | S/T · 20, anhand von Zielgerät, Transport und Zustandspflege vergleichen. | Fall/Offline | Offen |

## Technische und persönliche Abnahme

Die 66 CML-Dateien wurden statisch auf YAML, referenzierte Ports, einheitliche Verkabelung der Varianten und Guide-Zuordnung geprüft. Bei zugewiesenen IPv4-Adressen an beiden Enden gerouteter Direktverbindungen wurde zusätzlich die Subnetzzugehörigkeit verglichen. Für Cisco IOSv, IOSvL2 und die Spezial-Images gilt der dokumentierte Umfang der tatsächlich installierten Image-Version. Bei IOSv sind insbesondere QoS und LISP als imageabhängig einzuplanen. CML-Import und Laufzeit stehen für den Bestand offen. [CML-Imageübersicht](https://developer.cisco.com/docs/modeling-labs/vm-images-for-cml-labs/) · [IOSv-Featureliste](https://developer.cisco.com/docs/modeling-labs/iosv/)

### Start und Reset

1. CML-Version, Node-Definitionen und zugewiesene Images notieren. Das Canvas nutzt Text und Rechtecke. Dokumentationsreferenz für dieses Paket ist CML 2.10. Die bei dir installierte Version ist offen. Bei ausgeblendeten Anmerkungen **Canvas Settings → Annotations** einschalten. [Cisco Workbench](https://developer.cisco.com/docs/modeling-labs/annotations/)
2. Die gewählte YAML als separates Lab importieren. Knoten starten und die für das Lab definierte Ausgangslage prüfen. Bei 19 erst den dokumentierten Client-/SSH-Bootstrap durchführen. Erst anschließend beginnt die Zeitbox.
3. Für einen sauberen Neubeginn im eigenen Trainingslab stoppen, wipen und starten oder unter neuem Namen neu importieren. Lösung und Reparaturvariante getrennt von der laufenden Bearbeitung halten. Bei Tests mit Flash-Dateien Zeitstempel, frischen Dateinamen oder Neu-Import verwenden.

### Bewertungsrubrik

| Bewertung | Bedingung |
|---|---|
| Mit Hilfe gelöst | Mindestens ein Hinweis oder die geführte Befehlsfolge war nötig. |
| Selbstständig gelöst, unzureichend verifiziert | Der Endzustand scheint zu stimmen. Es fehlt ein Sollnachweis oder die Gegenprobe. |
| Selbstständig gelöst und verifiziert | Erfolgskriterien, Vorher-Nachher-Vergleich und Gegenprobe sind nachvollziehbar. |
| Übertragen und erklärt | Der Nachweis gelingt in einem anderen Aufbau oder mit einer geänderten Anforderung. Ursache und Grenzen werden erklärt. |

Für jede Zielnummer aus der Matrix einen Eintrag führen. Der persönliche Status startet überall bei **offen**. Ein Theorieergebnis kann persönlich nachgewiesen sein, obwohl es keinen CML-Lauf gibt.

| Ziel | Curriculum | Technischer Status | Persönlicher Status | Nachweis |
|---|---|---|---|---|
| 6.6 | S · Lab 36 | Statisch geprüft, EEM für IOSv dokumentiert, Laufzeit offen | Offen | Registrierungs- und Ereignisausgabe, frische Datei, Rückkehrprotokoll |
| 4.3 | X/G · Lab 18 | IOSvL2 ohne Port-Mirroring | Offen | Konfigurations-Exhibit; Live-Nachweis auf geeignetem Image nachtragen |
| Je weiteres Ziel | Status und Lab aus der Matrix | Statisch / dokumentiert / Laufzeit offen / in CML verifiziert | Offen bis zur Bewertung | Datum, Image, Befehl/Ausgabe oder Fallbegründung |

[Lab-36-Pilot mit manueller Abnahme](36-EEM-Applets/solutions/PILOT.md) · [Alle Nachweise](NACHWEISE.md)
