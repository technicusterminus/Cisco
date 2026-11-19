# ENCOR – Aufgaben ohne Befehlsliste

Für Ziel 5.2.a gibt es die [ACL-Werkstatt mit Dienstmatrix und Transferauftrag](10-ACL-CoPP/ACL-Werkstatt/README.md).

Die [Zusatzaufgaben zur Routing Assurance](Routing-Assurance/README.md) verbinden OSPF-Pfadwechsel, eBGP und aktives Dienstmonitoring in zwei CML-Startständen.

Wähle die Bau- oder Reparaturvariante nach Lernstufe. Die Angaben sind Trainingszeiten ab betriebsbereiter Topologie. Prüfkriterien gelten unabhängig vom Lösungsweg. Hinweise, konkrete Nachweise und Lösungspfade stehen in [NACHWEISE.md](NACHWEISE.md).

## Lab 01 — OSPFv2 über einen ABR

**Stufe:** Geführt · **Zeitbox:** 50 Minuten

**Blueprint:** 3.2.b; Vergleich für 3.2.a.

**Voraussetzung:** IPv4-Subnetze, OSPF-Nachbarzustände

**Start:** IPv4-Adressen, Loopbacks und die externen Testnetze sind vorgegeben.

**Auftrag:** Verbinde die Backbone-Seite R1/R2 mit dem LAN auf der anderen Seite von R2. Fasse die dafür vorgesehenen Netze zusammen und begründe, welche Interfaces passiv sein dürfen.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** R2 verbindet beide Areas. Auf dem Broadcast-LAN erklärst du eine FULL- und gegebenenfalls eine 2-WAY-Beziehung. Auf der Backbone-Seite ist das aggregierte statt jedes Detailpräfix sichtbar.

**Gegenprobe:** Kontrolliere, dass die vom Aggregat nicht erfassten Netze nicht versehentlich verschwinden.

**Wiederholung oder Transfer:** 28 und 34, anschließend 23

## Lab 02 — EIGRP und OSPFv3 getrennt nachweisen

**Stufe:** Geführt · **Zeitbox:** 65 Minuten

**Blueprint:** 3.2.a, 3.2.b.

**Voraussetzung:** 01, IPv6-Link-Local und Loopbacks

**Start:** IPv4 und IPv6 sind auf den Transitinterfaces und Loopbacks adressiert.

**Auftrag:** Richte OSPFv3 für die IPv6-Erreichbarkeit der Loopbacks ein und erweitere um eine zweite Area. Vergleiche zum Schluss den ausgewählten IPv4-Pfad nach EIGRP mit dem IPv6-Pfad. EIGRP Named Mode ist die Vertiefung.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Die IPv6-Nachbarn stehen in der vorgesehenen Area und beide neuen Loopbacks erscheinen auf R1 als Inter-Area-Ziele. EIGRP und OSPFv3 sind getrennt zu beobachten.

**Gegenprobe:** Kontrolliere, dass ein IPv4-Routingproblem keinen OSPFv3-Ausfall vortäuscht.

**Wiederholung oder Transfer:** 34 für Filterprinzipien, 30 zum Routingvergleich

## Lab 03 — Direktes eBGP und Pfadwahl

**Stufe:** Selbstständig · **Zeitbox:** 55 Minuten

**Blueprint:** 3.2.c.

**Voraussetzung:** IPv4-Next-Hop, /30-Links, BGP-Attribute

**Start:** Vier Router mit direkten Transportlinks und vorgegebenen AS-Rollen.

**Auftrag:** Stelle die direkten Nachbarschaften her und erreiche die Zielnetze über beide Anbieter. Setze eine nachvollziehbare Primärpräferenz und belege den Wechsel beim Ausfall.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Alle vorgesehenen Sessions sind Established, das Zielpräfix ist über zwei BGP-Pfade sichtbar und der Best Path entspricht der Präferenz.

**Gegenprobe:** Nach Abschalten des Primärpfades wechselt der ausgewählte Pfad. Fremde Präfixe bleiben außerhalb der vereinbarten Policy.

**Wiederholung oder Transfer:** 24 und 30

## Lab 04 — PBR mit aktivem Erreichbarkeitsnachweis

**Stufe:** Selbstständig · **Zeitbox:** 45 Minuten

**Blueprint:** 3.2.d, 4.4.

**Voraussetzung:** 29, statische Routen, ACL-Matches

**Start:** Das Unicast-Netz nutzt einen Standardpfad. Für die Messung stehen Testziele im Providernetz zur Verfügung.

**Auftrag:** Leite nur den vorgesehenen Client über den Ersatzanbieter, solange der dortige Pfad erreichbar ist. Binde die Auswahl an einen aktiven Test und reproduziere einen Fehler hinter dem ersten Hop.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Der Kontrollclient behält seinen Pfad. Der Policy-Client wechselt beim simulierten Fehler und kehrt nach Wiederherstellung zurück.

**Gegenprobe:** Die Messung muss dem vorgesehenen Provider zugeordnet bleiben, auch wenn Nutzverkehr schon umgeschaltet hat.

**Wiederholung oder Transfer:** 35 und 24

## Lab 05 — VLAN, Trunk und Bündel am Symptom unterscheiden

**Stufe:** Geführt · **Zeitbox:** 60 Minuten

**Blueprint:** 3.1.a, 3.1.b.

**Voraussetzung:** VLAN-Tags, Access-Port, LACP-Grundlagen

**Start:** Hosts und Links sind vorhanden. VLAN-Zuordnung und Trunk-Pfade sind Arbeitsgegenstand.

**Auftrag:** Baue die logischen Verbindungen und einen funktionierenden VLAN-Pfad zum Gateway. Arbeite anschließend mindestens zwei Tickets mit unterschiedlichen Fehlerschichten ab.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Die erwarteten VLANs werden über den logischen Kanal transportiert, und die Pfade innerhalb und zwischen VLANs sind erklärt.

**Gegenprobe:** Ein fehlender Member darf den intakten logischen Pfad im vorgesehenen Bündel nicht unbemerkt verfälschen.

**Wiederholung oder Transfer:** 06 und 23

## Lab 06 — STP-Entscheidungen und Schutzfunktionen

**Stufe:** Geführt · **Zeitbox:** 60 Minuten

**Blueprint:** 3.1.c.

**Voraussetzung:** 05, Bridge-ID, redundante Layer-2-Pfade

**Start:** VLANs und Trunks zwischen SW1–SW4 sind vorbereitet. SW5 bleibt bis zum Schutztest abgeschaltet.

**Auftrag:** Wähle beabsichtigte Roots für die VLANs, ordne die VLANs anschließend MST-Instanzen zu und prüfe zwei Schutzfunktionen mit getrennten Testfällen.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Für jede Instanz kannst du Root und Weiterleitungspfad begründen. Ein unerwünschter BPDU-Test sperrt nur den vorgesehenen Anschluss.

**Gegenprobe:** Die legitime Weiterleitung der Hosts bleibt beim Schutztest erhalten.

**Wiederholung oder Transfer:** 31 und 23

## Lab 07 — Gateway-Failover beobachten

**Stufe:** Geführt · **Zeitbox:** 55 Minuten

**Blueprint:** 3.3.c; FHRP-Anteil von 1.1.b.

**Voraussetzung:** 05, IPv4-Default-Gateway, VLANs

**Start:** Redundantes Gateway-Paar und Upstream sind verkabelt. VLANs und Protokollparameter werden nach Aufgabe ergänzt.

**Auftrag:** Stelle für die vorgesehenen VLANs Gateway-Redundanz her. Löse einen Upstream-Ausfall aus und beobachte Übernahme und Rückkehr. HSRP und VRRP sind der Kern, GLBP ist Vertiefung.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Clients behalten dieselbe Gateway-Adresse. Die vorgesehene Instanz übernimmt und der Clientpfad funktioniert nach der Konvergenz.

**Gegenprobe:** Eine intakte Kontrollinstanz darf nicht denselben unnötigen Wechsel durchlaufen.

**Wiederholung oder Transfer:** 23

## Lab 08 — Zeit, Meldungen und Management interpretieren

**Stufe:** Geführt · **Zeitbox:** 45 Minuten

**Blueprint:** 3.3.a, 4.1.

**Voraussetzung:** IP-Erreichbarkeit, Stratum- und Severity-Grundlagen

**Start:** Statisches Routing und Management-Quelladressen sind dokumentiert.

**Auftrag:** Lies den Zeitpfad und diagnostiziere ein NTP- oder Logging-Symptom. Erkläre an der PTP-Ersatzübung, wann Domain und Profil die Synchronisation verhindern.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Du weist die tatsächlich ausgewählte NTP-Zeitquelle und eine kontrolliert erzeugte Meldung nach. Den PTP-Fall begründest du am Auszug.

**Gegenprobe:** Ein erreichbarer, aber nicht akzeptierter Zeitserver darf nicht als synchronisiert gelten.

**Wiederholung oder Transfer:** 33 und 23

## Lab 09 — NAT/PAT am Datenverkehr verifizieren

**Stufe:** Selbstständig · **Zeitbox:** 45 Minuten

**Blueprint:** 3.3.b.

**Voraussetzung:** Private/öffentliche Adressen, ACL-Matches, Routing

**Start:** Innen-LAN, ISP und DMZ sind vorgegeben. Zwei Clients und ein veröffentlichter Dienst liefern getrennte Testfälle.

**Auftrag:** Erzeuge PAT für interne Clients und eine stabile Übersetzung für den vorgegebenen Server. Prüfe einen Fluss in jede zulässige Richtung.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Zwei Innenquellen werden unterscheidbar übersetzt. Der externe Zugriff auf das veröffentlichte Ziel erreicht genau den vorgesehenen Server.

**Gegenprobe:** Verkehr mit einer nicht vorgesehenen Quelle erhält keine Freigabe über die PAT-Regel.

**Wiederholung oder Transfer:** 23

## Lab 10 — Transit-ACL und CoPP getrennt belegen

**Stufe:** Selbstständig · **Zeitbox:** 55 Minuten

**Blueprint:** 5.2.a, 5.2.b.

**Voraussetzung:** IPv4-ACLs, Routerzugriff, Kontroll- und Datenebene

**Start:** Clients, R1 und ein Server liefern erlaubte und abzulehnende Ströme. Das Routing ist vorgegeben.

**Auftrag:** Setze die Verkehrsregeln an der vorgesehenen Schnittstelle um und schütze den gerätebezogenen Verkehr separat. Nutze normale Lab-Tests mit niedriger Last.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Erlaubter Transit erreicht den Dienst. Abgelehnter Verkehr trifft die erwartete Regel. Verkehr an den Router lässt sich der vorgesehenen CoPP-Klasse zuordnen.

**Gegenprobe:** Der Kontrolltest muss belegen, dass legitimer Transit von CoPP unbeeinflusst bleibt.

**Wiederholung oder Transfer:** 23 für ACLs

## Lab 11 — Zugriff und AAA-Fallback

**Stufe:** Selbstständig · **Zeitbox:** 45 Minuten

**Blueprint:** 5.1.a, 5.1.b (lokal und Fallback).

**Voraussetzung:** Console, VTY und SSH-Grundlagen

**Start:** Zwei Router, lokaler Testbenutzer und ein bewusst nicht erreichbarer AAA-Endpunkt als Szenario.

**Auftrag:** Stelle lokalen und abgesicherten Fernzugriff her. Belege mit zwei Benutzern unterschiedliche Berechtigungen und dokumentiere, wie der Gerätezugriff bei einem nicht erreichbaren AAA-Server reagiert.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Du belegst Zugangserfolg und effektive Autorisierung in getrennten Sitzungen. Die Konsole bleibt als Rückweg verfügbar.

**Gegenprobe:** Telnet soll nach Abschluss abgelehnt werden. Ein wirklicher Server-REJECT ist in diesem Lab nicht prüfbar.

**Wiederholung oder Transfer:** 23 für Zugang, Server-AAA bleibt Ausbau

## Lab 12 — Multicast vom Empfänger bis zur Quelle

**Stufe:** Geführt · **Zeitbox:** 55 Minuten

**Blueprint:** 3.3.d.

**Voraussetzung:** 01, Unicast-Erreichbarkeit und Routingtabelle

**Start:** Die OSPF-Unterlage und zwei Empfänger-LANs stehen bereit. Pinge zuerst die Empfänger per Unicast.

**Auftrag:** Führe einen Empfängerbeitritt und eine Quelle im PIM-SM-Netz zusammen. Stelle den Weg über den RP dar und erkläre, wo ein RPF-Fehler die Zustellung unterbricht.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Die beiden Empfänger liefern Multicast-Antworten. IGMP, PIM-Nachbarn, Gruppen- und Quellzustand passen zum vorgesehenen Baum.

**Gegenprobe:** Ohne Beitritt eines Empfängers darf dieser Zweig keinen Zustellnachweis liefern. Unicast bleibt als Kontrolltest verfügbar.

**Wiederholung oder Transfer:** 32

## Lab 13 — VRF-Trennung mit überlappenden Netzen

**Stufe:** Selbstständig · **Zeitbox:** 55 Minuten

**Blueprint:** 2.2.a.

**Voraussetzung:** IPv4-Routing und separate Routingtabellen

**Start:** Zwei Kunden haben dieselben Adressen. Die Zuordnung der Ports zu beiden Kunden steht in der Topologie.

**Auftrag:** Verbinde die Sites je Kunde über eine eigene VRF. Zeige anhand des gleichen Zielpräfixes, warum die Standorte trotzdem getrennt sind.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Beide Zielpfade sind in ihrer jeweiligen VRF erreichbar. Jeder Pfad nutzt die vorgesehene Kundenschnittstelle.

**Gegenprobe:** Eine globale Abfrage oder ein Test aus der falschen VRF darf die Trennung nicht als Erfolg melden.

**Wiederholung oder Transfer:** 24

## Lab 14 — GRE/IPsec vom Underlay bis zur SA

**Stufe:** Selbstständig · **Zeitbox:** 60 Minuten

**Blueprint:** 2.2.b.

**Voraussetzung:** IPv4-Next-Hop und Tunnelendpunkte

**Start:** Transport-Routing und Site-Loopbacks sind gesetzt. Die Overlay-Verbindung ist Arbeitsgegenstand.

**Auftrag:** Baue zwischen den Sites den vorgesehenen GRE/IPsec-Pfad und weise Routing über den Tunnel sowie verschlüsselten Verkehr nach. Vergleiche mit dem VTI-Ansatz als Vertiefung.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Das Zielnetz wird über den Tunnel geroutet. Beim kontrollierten Datenfluss steigen passende IPsec-Zähler an beiden Enden.

**Gegenprobe:** Ein erreichbarer öffentlicher Peer oder ein Tunnel mit Status up/up reicht nicht als Verschlüsselungsnachweis.

**Wiederholung oder Transfer:** 24

## Lab 15 — LISP-Mapping aus Verkehr erklären

**Stufe:** Selbstständig · **Zeitbox:** 45 Minuten

**Blueprint:** 2.3.a.

**Voraussetzung:** IP-Underlay und Routingtabelle, LISP-Grundbegriffe

**Start:** Zwei Sites, ein Transitnetz und ein Mapping-Knoten. LISP-Unterstützung des geladenen IOSv-Images ist Voraussetzung.

**Auftrag:** Verfolge für den vorgesehenen Datenstrom den Übergang von EID zu RLOC. Erkläre Registrierung, Auflösung und was bei einem fehlenden Mapping sichtbar wird.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Dein Nachweis enthält EID, RLOC und den Eintrag auf dem zuständigen Mapping-/Tunnel-Knoten.

**Gegenprobe:** Der Underlay-Ping darf bei einem Mappingfehler weiterhin funktionieren.

**Wiederholung oder Transfer:** 21: SD-Access-Fallstudie

## Lab 16 — VLAN-zu-VNI-Mapping im VXLAN

**Stufe:** Selbstständig · **Zeitbox:** 55 Minuten

**Blueprint:** 2.3.b.

**Voraussetzung:** IPv4-Underlay, VLANs, NX-OS-Grundlagen

**Start:** Die VTEP-Loopbacks und das geroutete Underlay sind vorbereitet. Die Hosts liegen im selben IP-Subnetz an verschiedenen Leafs.

**Auftrag:** Stelle eine Layer-2-Verbindung über das VXLAN-Overlay her. Weise das richtige Mapping, die Peer-Beziehung und den tatsächlichen Datenverkehr nach.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Beide VTEPs erreichen einander, die vereinbarte VNI ist aktiv und der Datenstrom wird am anderen Leaf dem richtigen VLAN zugeordnet.

**Gegenprobe:** Underlay-Erreichbarkeit ohne Overlay darf nicht als Nachweis zählen.

**Wiederholung oder Transfer:** 21: Fabric-Fallstudie, 24: Underlay/Overlay-Diagnose

## Lab 17 — QoS-Konfiguration und Zähler interpretieren

**Stufe:** Selbstständig · **Zeitbox:** 50 Minuten

**Blueprint:** 1.4.

**Voraussetzung:** DSCP, Layer-3-Pfade, Ein- und Ausgangssicht

**Start:** Drei Quellen erzeugen unterschiedliche Traffic-Klassen. Das Routing ist bereit. Feature-Umfang des IOSv-Images prüfen.

**Auftrag:** Ordne vorab die drei Testflüsse den Klassen zu. Stelle die vorgesehene Markierungs- und Servicepolitik her und vergleiche Vorhersage und Messung.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Klasse, Richtung, Zähler und DSCP passen je Testfluss zur Aufgabe. Du erklärst Policing, Shaping und Priorität anhand der jeweiligen Konfiguration.

**Gegenprobe:** Der Gaststrom erhält keine priorisierte Behandlung. Virtuelle Rate/Timing-Messung ist kein Hardware-Benchmark.

**Wiederholung oder Transfer:** 18 bei Messnachweisen, alternativ QoS-Exhibit

## Lab 18 — NetFlow messen und Spiegelung planen

**Stufe:** Selbstständig · **Zeitbox:** 50 Minuten

**Blueprint:** 4.2; 4.3 als Ersatzübung.

**Voraussetzung:** Transportports, VLAN-Trunks, Beobachtungspunkte

**Start:** H1 und H2 erreichen SRV über R1. Die IOSvL2-Switches übernehmen Switching; die Spiegelungsaufgaben sind eine Ersatzübung.

**Auftrag:** Richte auf R1 einen Flow-Monitor ein, der ICMP und TCP unterscheiden kann. Weise Cache und Export getrennt nach. Entwirf danach je eine lokale, Remote- und ERSPAN-Session für die Vorgaben im README.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Du zeigst getrennte Flow-Datensätze und beobachtest den Export am richtigen Link. Für Spiegelung legst du Quelltyp, Transport und Zieltyp je Verfahren dar.

**Gegenprobe:** Erlaubtes Weiterleiten allein erzeugt ohne Monitorbindung keinen Nachweis im Flow-Cache.

**Wiederholung oder Transfer:** 33 für methodische Diagnose

## Lab 19 — NETCONF und RESTCONF Ende zu Ende

**Stufe:** Selbstständig · **Zeitbox:** 65 Minuten

**Blueprint:** 4.6, 6.5; YANG-Anwendung für 6.3.

**Voraussetzung:** SSH, HTTPS, 20 für JSON/YANG

**Start:** API-CLIENT 192.0.2.2 und CSR1 192.0.2.1 teilen ein isoliertes Netz. IPv4, lokaler Benutzer und AAA-Basis stehen bereit.

Warte auf cloud-init. Linux-Konsole: `cisco` / `cisco`. CSR1: `admin` / `Lab#2026!`. Prüfe, ob Gi1 und Gi2 betriebsbereit sind und CSR1 einen lokalen RSA-Schlüssel für SSH hat. Details stehen im Abschnitt Topologie des Lab-README. Der RESTCONF-Client auf API-CLIENT liegt unter `/opt/encor/restconf.py`.

**Auftrag:** Aktiviere beide Schnittstellen auf CSR1. Lies dieselbe Interface-Konfiguration aus beiden Protokollen und ändere anschließend die Beschreibung genau eines Interfaces über RESTCONF. EEM-Konstruktion trainierst du vertieft in Lab 36.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** HTTPS-Abfrage, NETCONF-RPC und die einzige beabsichtigte Description-Änderung sind getrennt belegt. Ordne den API-Fehler eines falschen Pfads ein.

**Gegenprobe:** Mit einer falschen Ressource darf der Client keinen erfolgreichen Write melden. Das Management-Subnetz bleibt isoliert.

**Wiederholung oder Transfer:** 36 für EEM, 20 für API-Interpretation

## Lab 20 — Python, JSON und API-Payloads ohne CML

**Stufe:** Selbstständig · **Zeitbox:** 55 Minuten

**Blueprint:** 6.1–6.3, 6.5, 6.7; Catalyst-Center-Teil von 6.4.

**Voraussetzung:** Python-Datentypen, JSON, HTTP-Grundlagen

**Start:** Lokaler Mock und Tests aus dem vorhandenen Drill-Paket.

**Auftrag:** Sage zwei Python-Ausgaben voraus, erstelle den JSON-Request und erkläre den Aufbau zweier API-Antworten. Vergleiche bei einem Ausfall Authentisierung, Berechtigung und Dienststatus.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Tests und eigene Erklärung passen für gültige und fehlerhafte Antworten.

**Gegenprobe:** Ein Feed mit fehlendem Attribut darf nicht als erfolgreicher Datenabruf zählen.

**Wiederholung oder Transfer:** 19

## Lab 21 — Designentscheidungen und Betriebsabläufe begründen

**Stufe:** Selbstständig · **Zeitbox:** 55 Minuten

**Blueprint:** 1.1.a–b, 1.2.a–b, 1.3.a–b, 2.1.a–c, 4.5.

**Voraussetzung:** Campus-Layer, Betriebsanforderungen und Cloud-Grundbegriffe

**Start:** Fallstudienpaket ohne CML-Provisionierung.

**Auftrag:** Wähle zwei Fälle aus Architektur und einen aus Assurance. Zeichne je einen Datenpfad und erkläre Rollen, Alternative sowie eine Ausfallgrenze.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Deine Auswahl lässt sich aus Anforderungen herleiten. Bei Catalyst Center unterscheidest du Konfigurationsaufgaben, Monitoring und KI-gestützte Diagnose.

**Gegenprobe:** Nenne je Fall eine Anforderung, bei der dein Entwurf ungeeignet wäre.

**Wiederholung oder Transfer:** 23 und 24, jeweils anschließend den Entwurf erklären

## Lab 22 — Security-Entscheidungen erklären

**Stufe:** Selbstständig · **Zeitbox:** 50 Minuten

**Blueprint:** 5.3, 5.4.a–d.

**Voraussetzung:** ACLs, AAA und TLS-Grundbegriffe

**Start:** Fallstudienpaket mit API, Endpoint, Firewall, TrustSec und MACsec.

**Auftrag:** Bearbeite einen API-Fall sowie zwei Designfälle. Ordne mindestens zwei Kontrollen ihrem Einsatzort zu und erkläre, welches Signal ihre Wirkung belegt.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Du kannst anhand des Falls Authentisierung, Autorisierung und Durchsetzung unterscheiden und das jeweilige Sicherheitsziel erklären.

**Gegenprobe:** Nenne pro Kontrolle eine Bedingung, die sie nicht abdeckt.

**Wiederholung oder Transfer:** 10, 11 und 23 für Geräteebene

## Lab 23 — Abschlusslab Campus und Edge

**Stufe:** Transfer · **Zeitbox:** 110 Minuten

**Blueprint:** 3.1.a–c, 3.2.b (IPv4), 3.3.a (NTP), 3.3.b–c, 5.1.a, 5.2.a.

**Voraussetzung:** 05–11, 01, 33 und idealerweise 31

**Start:** Starte die Reparaturvariante. Campus, Gateway-Paar, Edge und ISP sind als Szenario gegeben.

**Auftrag:** Bearbeite die Tickets schichtweise, priorisiere Abhängigkeiten und dokumentiere je Ursache die kleinste wirksame Änderung. Wähle deine Nachweise selbst.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Hosts, Gateway, Routing und Edge-Funktion erreichen den vereinbarten Endzustand. Mindestens ein Befund pro bearbeitetem Ticket zeigt die Ursache vor und die Wirkung nach dem Fix.

**Gegenprobe:** Weise einen funktionsfähigen Kontrollfluss nach und zeige, dass ein unzulässiger Verkehrsfluss weiterhin blockiert ist.

**Wiederholung oder Transfer:** 24 als Gegenprobe mit anderer Architektur

## Lab 24 — WAN- und Overlay-Transfer

**Stufe:** Transfer · **Zeitbox:** 100 Minuten

**Blueprint:** 2.2.a–b, 3.2.b (IPv4), 3.2.c.

**Voraussetzung:** 03, 13, 14 und 01

**Start:** Reparaturvariante mit Provider, Transport, Overlay und Kundenendpunkten.

**Auftrag:** Stelle die Startsymptome nach, sortiere Transport und Overlay und stelle die Site-Pfade wieder her. Begründe, warum jede Bedienhandlung den kleinstmöglichen Bereich betrifft.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Belege den vorgesehenen eBGP-Transport, die geschützten Overlay-Pfade und getrennte Kundenerreichbarkeit.

**Gegenprobe:** Ein Underlay-Ping darf keinen IPsec-Erfolg vortäuschen; Nachweis per SA-Zähler.

**Wiederholung oder Transfer:** 30 für Routing unter geänderten Randbedingungen

## Lab 25 — EIGRP-Routen und Alternativen einordnen

**Stufe:** Selbstständig · **Zeitbox:** 40 Minuten

**Blueprint:** 3.2.a (EIGRP-Anteil).

**Voraussetzung:** 01, IGP- und Metrikgrundlagen

**Start:** Vier IOSv-Router, vorgegebene Linkadressen und eindeutige Rollen.

**Auftrag:** Ermittle Successor und möglichen Alternativpfad. Verändere eine Eigenschaft im Lab und vergleiche Ergebnis und Vorhersage. Erkläre die Abweichung zu OSPF.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** RD und FD sind am konkreten Präfix nachvollziehbar, und die zusätzliche Route erfüllt die Schleifenbedingung.

**Gegenprobe:** Ein nicht zulässiger Pfad wird durch Variance allein nicht installierbar.

**Wiederholung oder Transfer:** 27 und 30

## Lab 26 — Interne und externe BGP-Lernwege vergleichen

**Stufe:** Selbstständig · **Zeitbox:** 50 Minuten

**Blueprint:** Vertiefung zu 3.2.c; direktes eBGP ergänzend, iBGP kein eigenes Blueprint-Ziel.

**Voraussetzung:** 03, OSPF-Routen zu Loopbacks

**Start:** OSPF-Underlay steht, BGP ist Aufgabe. Interne Router und ISP-Rollen sind bekannt.

**Auftrag:** Verteile die beiden extern gelernten Routen intern und steuere genau die beabsichtigte Präferenz. Erkläre den Unterschied zwischen direktem eBGP und der internen Reflektion.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Du zeigst einen Route-Reflector-Client-Pfad und den Best Path für beide Protokollkontexte.

**Gegenprobe:** Eine unerwünschte Route mit falscher Community wird gemäß Vorgabe nicht als bevorzugt behandelt.

**Wiederholung oder Transfer:** 30; iBGP/RR ist Vertiefung

## Lab 27 — Redistribution ohne Rückverteilung

**Stufe:** Selbstständig · **Zeitbox:** 55 Minuten

**Blueprint:** Vertiefung zu 3.2.a–b; Redistribution kein eigenes Blueprint-Ziel.

**Voraussetzung:** 01, 25 und Route-Maps

**Start:** Die internen OSPF- und EIGRP-Domänen laufen eigenständig. Die beiden Übergänge sind bekannt.

**Auftrag:** Übernimm die vereinbarten Präfixe zwischen den Domänen, verhindere Rückverteilung und schließe das lokal verbleibende Kundennetz aus.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Du belegst Route, Ursprung und Tags an zwei Beobachtungspunkten und die gewünschte Erreichbarkeit nach Ausfall eines Übergangs.

**Gegenprobe:** Verbotenes Präfix und Rückverteilung bleiben auch beim Ausfall aus.

**Wiederholung oder Transfer:** 30; Redistribution ist Vertiefung

## Lab 28 — OSPF-Area-Verhalten anhand der LSDB

**Stufe:** Selbstständig · **Zeitbox:** 50 Minuten

**Blueprint:** 3.2.b (IPv4).

**Voraussetzung:** 01, 02 für die Protokollfamilien

**Start:** IPv4-Links und Loopbacks stehen bereit. Die Area-Grenzen werden nach Vorgabe eingerichtet.

**Auftrag:** Vergleiche eine normale Area mit einer eingeschränkten Area. Belege die Auswirkung auf LSAs, Default und erlaubte Übergänge. Stub/NSSA und Authentisierung sind Vertiefung.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Nachbarn erreichen die beabsichtigten Zustände. LSDB und Routentabelle belegen den Wechsel der Area-Policy.

**Gegenprobe:** Ein LSA, der in der eingeschränkten Area fehlen soll, darf dort nicht mehr sichtbar sein.

**Wiederholung oder Transfer:** 34 und 30

## Lab 29 — PBR nach Quelle und Anwendung interpretieren

**Stufe:** Selbstständig · **Zeitbox:** 45 Minuten

**Blueprint:** 3.2.d.

**Voraussetzung:** ACLs und statisches IPv4-Routing

**Start:** Der Standardpfad über Provider A und Rückwege sind vorkonfiguriert. H1 und H2 sind Testquellen.

**Auftrag:** Lenke den vorgegebenen Quellverkehr und den vorgesehenen TCP-Verkehr über Provider B. Unterscheide die RIB von der tatsächlich weitergeleiteten Auswahl.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Baseline und Policy-Pfad sind für jeden Testfall dokumentiert. Der Pfadwechsel ist an einem Policy-Zähler oder Capture nachvollziehbar.

**Gegenprobe:** Ein unabhängiger H1-Kontrollfluss bleibt auf Provider A, und lokal erzeugter Verkehr erbt die Interface-Policy nicht automatisch.

**Wiederholung oder Transfer:** 04

## Lab 30 — Abschluss Routing im kombinierten Netz

**Stufe:** Transfer · **Zeitbox:** 90 Minuten

**Blueprint:** 3.2.a, 3.2.b (IPv4), 3.2.c.

**Voraussetzung:** 01, 03, 25, 27 und 34

**Start:** Reparaturvariante mit Provider und internen Routingdomänen.

**Auftrag:** Rekonstruiere schrittweise die Pfade vom Provider zu den internen Netzen. Bearbeite die Tickets in begründeter Reihenfolge und wähle pro Mechanismus den stärksten Nachweis.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Erreichbarkeit, Präfixursprung und vorgesehene Routingentscheidung sind pro Ticket nachvollziehbar.

**Gegenprobe:** Ein Ersatzpfad darf eine fehlerhafte Nachbarschaft oder unerwünschte Rückverteilung nicht verdecken.

**Wiederholung oder Transfer:** 24 und 23 für andere Architekturgrenzen

## Lab 31 — MST-Regionen und PVST-Grenze

**Stufe:** Selbstständig · **Zeitbox:** 65 Minuten

**Blueprint:** 3.1.c.

**Voraussetzung:** 06, Bridge-ID und MST-Instanzen

**Start:** Access und Distribution sind verkabelt, VLANs und Ausgangsmodus sind dokumentiert.

**Auftrag:** Baue die vereinbarte MST-Region auf, verteile die Roots je Instanz und diagnostiziere einen Übergang zur PVST-Seite.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Der Digest in der Region, die vorgesehenen Root-Ports und der erwartete Grenzport sind nachvollziehbar.

**Gegenprobe:** Ein abweichender Digest oder ungültiger PVST-Wurzelpfad muss eine erkennbare Abweichung auslösen.

**Wiederholung oder Transfer:** 23

## Lab 32 — SSM, Bidir-PIM und Anycast-RP vergleichen

**Stufe:** Selbstständig · **Zeitbox:** 70 Minuten

**Blueprint:** 3.3.d.

**Voraussetzung:** 12, RPF und OSPF-Underlay

**Start:** Das Unicast-Underlay läuft. Quelle und Empfänger sind vorgegeben, die Verfahren nutzen getrennte Testgruppen.

**Auftrag:** Stelle je Gruppe das vorgesehene Verfahren her und erkläre ihre Unterschiede anhand der Gruppenzustände. Für getrennte RPs prüfe den Austausch von Quelleninformationen.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Du weist (S,G) bei SSM, den Shared Tree bei Bidir sowie die RP-/MSDP-Zustände für die Anycast-Gruppe nach.

**Gegenprobe:** Zwei aufeinanderfolgende Gruppenversuche müssen getrennt bleiben. SSM ohne Quelle darf keinen erfolgreichen Zustelltest liefern.

**Wiederholung oder Transfer:** 12 als Vergleich, 33 als Methoden-Transfer

## Lab 33 — Diagnose aus Ausgaben und Gegenproben

**Stufe:** Geführt · **Zeitbox:** 50 Minuten

**Blueprint:** 4.1.

**Voraussetzung:** IPv4-Weiterleitung, 08 und OSPF-Basics

**Start:** OSPF und Unicast-Pfade stehen für den Referenzversuch bereit. H1 misst gegen SRV.

**Auftrag:** Erfasse einen funktionierenden Kontrollfluss. Grenze einen stillen Paketverlust und einen MTU-Fall ein. Wähle danach einen begrenzten Debug-Test und räume dessen Zustand wieder auf.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Du grenzt die Fehlerdomäne mit zwei unabhängigen Beobachtungen ein und kannst den Befund angeben, der andere Ursachen ausschließt.

**Gegenprobe:** Wiederhole den Test mit kleinem und großem Paket; Debugs werden beendet und Filter entfernt.

**Wiederholung oder Transfer:** 23 und 30

## Lab 34 — OSPF-Filter und Netztyp ohne Ratespiel

**Stufe:** Selbstständig · **Zeitbox:** 65 Minuten

**Blueprint:** 3.2.b (IPv4).

**Voraussetzung:** 01, 28 und LSDB/RIB-Unterschied

**Start:** IPv4-Links und Zielpräfixe sind gesetzt. Der gewünschte Präfixzustand pro Area steht in der Aufgabentabelle des Lab-README.

**Auftrag:** Stelle die beabsichtigte Sicht auf Präfixe pro Area her. Reproduziere danach einen Nachbarschafts- oder Netztypfehler aus der Reparaturvariante und grenze ihn ein.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** Die Abnahme zeigt für jede Vorgabe, an welchem Router das Präfix in LSDB und RIB sichtbar sein soll. Du erklärst die Grenze zwischen lokalem RIB-Filter und LSA-Filter.

**Gegenprobe:** Beweise die Abwesenheit genau der ausgeschlossenen Route, während ein erlaubtes Kontrollpräfix weiter vorhanden ist.

**Wiederholung oder Transfer:** 30

## Lab 35 — IP SLA zur Umschaltung einsetzen

**Stufe:** Selbstständig · **Zeitbox:** 55 Minuten

**Blueprint:** 4.4.

**Voraussetzung:** 04 oder statische Routen und Tracking

**Start:** Die Provider haben die vorgesehenen Rückwege. R1 erhält erst in der Aufgabe seine Ausfalllogik.

**Auftrag:** Wähle ein Messziel und einen Beobachtungspunkt, der einen entfernten Ausfall erkennt. Bewirke eine vorhersagbare Umschaltung und Rückkehr. Jitter und Responder sind der zweite Testfall.

**Grenzen:** Behalte Adressplan und bereitgestellte Infrastruktur bei. Nimm für Gegenproben vorübergehend erzeugte Fehler zurück.

**Erfolgskriterium:** SLA-Messwert, Tracking-Zustand, installierte Route und Clientpfad ändern sich passend zum simulierten Ausfall und zur Rückkehr.

**Gegenprobe:** Bleibt nur der erste Hop erreichbar, darf er die Störung hinter dem Provider nicht verdecken.

**Wiederholung oder Transfer:** 24, zusätzlich Diagnose in 33

## Lab 36 — Ereignisgesteuerte Diagnose

**Stufe:** Selbstständig · **Zeitbox:** 35 Minuten · **Ziel:** 6.6

**Voraussetzung:** Du kannst eine OSPF-Nachbarschaft im Gerät erkennen und den Zeitpunkt einer Zustandsänderung im Syslog finden.

**Start:** Importiere `topology.yaml`. R1 und R2 haben zwei OSPF-Pfade. Beide Nachbarschaften müssen stabil sein. Gi0/0 ist der Kontrollpfad, Gi0/1 der Testpfad.

**Auftrag:** Erstelle auf R1 ein eigenes EEM-Applet. Beim Verlust der zuvor vollständigen OSPF-Nachbarschaft über Gi0/1 soll R1 automatisch eine Diagnose mit der Nachbartabelle und die Zustandsänderung lokal dokumentieren. Verwende je einen eindeutigen Namen für Applet, Datei und Meldung.

**Grenzen:** Das Applet liest und protokolliert. Es verändert keine Interfaces, kein Routing und keine gespeicherte Konfiguration. Auslöser und Rückkehr in den Normalzustand erzeugst du im isolierten Lab manuell.

**Erfolgskriterien:**

1. Das eigene Applet ist vor dem Test registriert. Die beiden Nachbarschaften sind vollständig.
2. Nach Abschalten des Testpfads siehst du einen neuen Applet-Lauf und einen eindeutig zuordenbaren Logeintrag. Der Kontrollpfad bleibt aktiv.
3. Eine neu erzeugte lokale Datei enthält die tatsächliche Nachbartabelle nach dem Ereignis. Der funktionierende Kontrollpfad ist darin erkennbar.
4. Nach Wiederherstellung von Gi0/1 stehen beide Nachbarschaften wieder. Die Rückkehr in den Zustand FULL erzeugt keinen zweiten Diagnose-Lauf.
5. Erkläre den Unterschied zwischen einer registrierten Policy, einem ausgelösten Lauf und einer erfolgreichen Aktion.

**Transfer:** Öffne anschließend `topology-repair.yaml` als separates Lab. Diagnostiziere zwei Applets mit unterschiedlichen Fehlerbildern und belege jede Reparatur mit einem gezielten Ereignis sowie einem unabhängigen Wirkungsnachweis. Orientiere dich an den Symptomen im Guide.
