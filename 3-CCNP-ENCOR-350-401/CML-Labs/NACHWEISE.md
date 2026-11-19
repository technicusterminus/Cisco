# ENCOR – Hinweise, Lösungen und Nachweise

Zur zusätzlichen Praxisstrecke gibt es [Hinweise und Prüfschritte für OSPF, eBGP und IP SLA](Routing-Assurance/solutions/NACHWEISE.md).

Öffne diesen Teil erst für einen Hinweis oder zur Abnahme. Die drei Hinweise gehen von der Denkfrage bis zur konkreteren Diagnose. Bei einem Transferlauf bleiben sie geschlossen. Verwende vorhandene Konfigurationen und Fehlerlisten für den Referenzweg. Die Kriterien erlauben andere Lösungswege.

**Technischer Stand:** Die Nachweise sind Abnahmevorgaben. Statische Prüfung, dokumentierter Feature-Support und beobachtete CML-Wirkung werden im [Curriculum](CURRICULUM.md) getrennt erfasst.

## Lab 01 — OSPFv2 über einen ABR

<details><summary>Hinweis 1 · Denkanstoß</summary>

Verfolge ein einzelnes Präfix über die Area-Grenze.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche LSDB und RIB auf beiden Seiten.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe die Summary am ABR und die Netztypen je Link.

</details>

**Nachweis:** Auf R2 show ip ospf neighbor/interface und auf R1 show ip route ospf sowie show ip ospf database summary. O IA und Präfixlänge abgleichen.

**Soll:** R2 verbindet beide Areas. Auf dem Broadcast-LAN erklärst du eine FULL- und gegebenenfalls eine 2-WAY-Beziehung. Auf der Backbone-Seite ist das aggregierte statt jedes Detailpräfix sichtbar.

**Gegenprobe:** Kontrolliere, dass die vom Aggregat nicht erfassten Netze nicht versehentlich verschwinden.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 02 — EIGRP und OSPFv3 getrennt nachweisen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Trenne Adressfamilien und Routing-IDs.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe auf welchem Router die Route von intra zu inter wechselt.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Kontrolliere Area und Interface-Aktivierung auf beiden Seiten.

</details>

**Nachweis:** show ospfv3 neighbor und show ipv6 route ospf; IPv6-Quellping von Lo0. Für EIGRP show ip eigrp topology und RD/FD vergleichen. IPv6-Multi-Area-Filter bleibt eine Lücke.

**Soll:** Die IPv6-Nachbarn stehen in der vorgesehenen Area und beide neuen Loopbacks erscheinen auf R1 als Inter-Area-Ziele. EIGRP und OSPFv3 sind getrennt zu beobachten.

**Gegenprobe:** Kontrolliere, dass ein IPv4-Routingproblem keinen OSPFv3-Ausfall vortäuscht.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 03 — Direktes eBGP und Pfadwahl

<details><summary>Hinweis 1 · Denkanstoß</summary>

Beginne mit dem direkt angeschlossenen Peer.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne TCP-Sitzung, Anzeige des Präfixes und Best-Path-Auswahl.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche advertised-routes und den ersten unterschiedlichen Attributwert.

</details>

**Nachweis:** show ip bgp summary, show ip bgp für das Zielpräfix, show ip route und traceroute vor/nach dem Ausfall.

**Soll:** Alle vorgesehenen Sessions sind Established, das Zielpräfix ist über zwei BGP-Pfade sichtbar und der Best Path entspricht der Präferenz.

**Gegenprobe:** Nach Abschalten des Primärpfades wechselt der ausgewählte Pfad. Fremde Präfixe bleiben außerhalb der vereinbarten Policy.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 04 — PBR mit aktivem Erreichbarkeitsnachweis

<details><summary>Hinweis 1 · Denkanstoß</summary>

Ein erreichbarer Nachbar beweist keinen erreichbaren Dienst.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche Messpfad und weitergeleiteten Clientverkehr.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe Source und Next-Hop des Messverkehrs.

</details>

**Nachweis:** traceroute beider Hosts, show route-map, show track und show ip sla statistics vor, während und nach dem Ausfall.

**Soll:** Der Kontrollclient behält seinen Pfad. Der Policy-Client wechselt beim simulierten Fehler und kehrt nach Wiederherstellung zurück.

**Gegenprobe:** Die Messung muss dem vorgesehenen Provider zugeordnet bleiben, auch wenn Nutzverkehr schon umgeschaltet hat.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 05 — VLAN, Trunk und Bündel am Symptom unterscheiden

<details><summary>Hinweis 1 · Denkanstoß</summary>

Ein physisch aktiver Link bedeutet nicht, dass er VLANs transportiert.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe Bündelbildung und VLAN-Weiterleitung getrennt.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche Modus und Allowed-Liste an beiden Enden. Dynamisches Trunking braucht einen eigenen DTP-Fehlerfall.

</details>

**Nachweis:** show etherchannel summary mit P-Membern, show interfaces trunk mit aktivem VLAN, MAC-Tabelle und Vergleich von Same-VLAN/Gateway-Ping.

**Soll:** Die erwarteten VLANs werden über den logischen Kanal transportiert, und die Pfade innerhalb und zwischen VLANs sind erklärt.

**Gegenprobe:** Ein fehlender Member darf den intakten logischen Pfad im vorgesehenen Bündel nicht unbemerkt verfälschen.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 06 — STP-Entscheidungen und Schutzfunktionen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Lies die Root-Entscheidung vor jeder Änderung.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche Instanz-Mapping und Portrolle.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe Schutzrichtung und Portmodus am Testanschluss.

</details>

**Nachweis:** show spanning-tree root/mst, show interface status err-disabled bzw. show spanning-tree inconsistentports plus Host-Test.

**Soll:** Für jede Instanz kannst du Root und Weiterleitungspfad begründen. Ein unerwünschter BPDU-Test sperrt nur den vorgesehenen Anschluss.

**Gegenprobe:** Die legitime Weiterleitung der Hosts bleibt beim Schutztest erhalten.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 07 — Gateway-Failover beobachten

<details><summary>Hinweis 1 · Denkanstoß</summary>

Beginne am Gateway, das sich der Host tatsächlich merkt.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne Priorität, Präemption und Tracking.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche den virtuellen Gateway pro VLAN auf beiden Routern.

</details>

**Nachweis:** show standby brief bzw. show vrrp brief, show track, Clientverkehr und Rollenvergleich nach Failover.

**Soll:** Clients behalten dieselbe Gateway-Adresse. Die vorgesehene Instanz übernimmt und der Clientpfad funktioniert nach der Konvergenz.

**Gegenprobe:** Eine intakte Kontrollinstanz darf nicht denselben unnötigen Wechsel durchlaufen.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 08 — Zeit, Meldungen und Management interpretieren

<details><summary>Hinweis 1 · Denkanstoß</summary>

Reihenfolge: Erreichbarkeit, Akzeptanz, Auswahl.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche Reach, Stratum und Quelladresse.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe Authentisierung, Source und ID an den beiden Enden.

</details>

**Nachweis:** show ntp associations detail/status, show logging und SNMP-Ereignis/Abfrage getrennt. Bei PTP Domain und Rolle aus dem Exhibit lesen.

**Soll:** Du weist die tatsächlich ausgewählte NTP-Zeitquelle und eine kontrolliert erzeugte Meldung nach. Den PTP-Fall begründest du am Auszug.

**Gegenprobe:** Ein erreichbarer, aber nicht akzeptierter Zeitserver darf nicht als synchronisiert gelten.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 09 — NAT/PAT am Datenverkehr verifizieren

<details><summary>Hinweis 1 · Denkanstoß</summary>

Zeichne die Adresse vor und nach dem Router.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe Richtung und Match getrennt.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche Inside/Outside und die Selektions-ACL.

</details>

**Nachweis:** show ip nat translations und statistics, Auswertung der lokalen/globalen Adressen sowie Ping und Dienstzugriff.

**Soll:** Zwei Innenquellen werden unterscheidbar übersetzt. Der externe Zugriff auf das veröffentlichte Ziel erreicht genau den vorgesehenen Server.

**Gegenprobe:** Verkehr mit einer nicht vorgesehenen Quelle erhält keine Freigabe über die PAT-Regel.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 10 — Transit-ACL und CoPP getrennt belegen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Ist das Ziel der Router oder ein Gerät dahinter?

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe ACL-Richtung und dann die Policy-Klasse.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche Regelreihenfolge und Zähleränderung.

</details>

**Nachweis:** show access-lists und show policy-map control-plane vor/nach getrenntem Transit und gerätebezogenem Verkehr.

**Soll:** Erlaubter Transit erreicht den Dienst. Abgelehnter Verkehr trifft die erwartete Regel. Verkehr an den Router lässt sich der vorgesehenen CoPP-Klasse zuordnen.

**Gegenprobe:** Der Kontrolltest muss belegen, dass legitimer Transit von CoPP unbeeinflusst bleibt.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 11 — Zugriff und AAA-Fallback

<details><summary>Hinweis 1 · Denkanstoß</summary>

Anmeldung und Freigabe von Befehlen sind zwei Nachweise.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche die Methodenliste mit der tatsächlichen VTY-Bindung.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe, ob ein Server überhaupt erreicht wurde und welche Methode danach greift.

</details>

**Nachweis:** show users/show privilege und show aaa servers; getrennte SSH-Sitzungen und fehlgeschlagener Telnet-Test.

**Soll:** Du belegst Zugangserfolg und effektive Autorisierung in getrennten Sitzungen. Die Konsole bleibt als Rückweg verfügbar.

**Gegenprobe:** Telnet soll nach Abschluss abgelehnt werden. Ein wirklicher Server-REJECT ist in diesem Lab nicht prüfbar.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 12 — Multicast vom Empfänger bis zur Quelle

<details><summary>Hinweis 1 · Denkanstoß</summary>

Beginne beim beitretenden Empfänger.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Gehe vom IGMP-Zustand zum RPF-Pfad zurück.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe, ob RP und Quelle über das richtige Interface erreichbar sind.

</details>

**Nachweis:** show ip igmp groups, show ip pim neighbor/rp mapping, show ip mroute und show ip rpf zur Quelle.

**Soll:** Die beiden Empfänger liefern Multicast-Antworten. IGMP, PIM-Nachbarn, Gruppen- und Quellzustand passen zum vorgesehenen Baum.

**Gegenprobe:** Ohne Beitritt eines Empfängers darf dieser Zweig keinen Zustellnachweis liefern. Unicast bleibt als Kontrolltest verfügbar.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 13 — VRF-Trennung mit überlappenden Netzen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Zu welchem Routingkontext gehört der Eingangsport?

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe Zuordnung, Adressen und Tabellen unabhängig.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Kontrolliere, ob die IP-Adresse nach der VRF-Bindung noch vorhanden ist.

</details>

**Nachweis:** show vrf, show ip route vrf und Ping mit expliziter VRF; die jeweiligen Next-Hops und Ports vergleichen.

**Soll:** Beide Zielpfade sind in ihrer jeweiligen VRF erreichbar. Jeder Pfad nutzt die vorgesehene Kundenschnittstelle.

**Gegenprobe:** Eine globale Abfrage oder ein Test aus der falschen VRF darf die Trennung nicht als Erfolg melden.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 14 — GRE/IPsec vom Underlay bis zur SA

<details><summary>Hinweis 1 · Denkanstoß</summary>

Unterscheide Transport, Tunnel und Verschlüsselung.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe das Site-Präfix in der Routingtabelle.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche Source, Peer und die passenden SAs an beiden Enden.

</details>

**Nachweis:** show ip route, show crypto ipsec sa mit Encaps/Decaps vor/nach neuem Verkehr und Peer-IKE-Status.

**Soll:** Das Zielnetz wird über den Tunnel geroutet. Beim kontrollierten Datenfluss steigen passende IPsec-Zähler an beiden Enden.

**Gegenprobe:** Ein erreichbarer öffentlicher Peer oder ein Tunnel mit Status up/up reicht nicht als Verschlüsselungsnachweis.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 15 — LISP-Mapping aus Verkehr erklären

<details><summary>Hinweis 1 · Denkanstoß</summary>

Trenne Standortadresse und Endgeräteadresse.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Frage zuerst, welcher xTR registriert ist.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche Map-Cache und erreichbaren RLOC. Bei fehlendem Feature verwende den Ablauf als beschriftetes Exhibit.

</details>

**Nachweis:** show ip lisp database/map-cache und Status auf MSMR; Underlay- und Host-Ping getrennt prüfen.

**Soll:** Dein Nachweis enthält EID, RLOC und den Eintrag auf dem zuständigen Mapping-/Tunnel-Knoten.

**Gegenprobe:** Der Underlay-Ping darf bei einem Mappingfehler weiterhin funktionieren.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 16 — VLAN-zu-VNI-Mapping im VXLAN

<details><summary>Hinweis 1 · Denkanstoß</summary>

Erst die VTEP-Erreichbarkeit, dann die VNI.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne Peer-Status und VLAN-Mapping.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche NVE-Source, Peer-IP und VLAN/VNI an beiden Leafs.

</details>

**Nachweis:** show nve peers/vni, MAC-Tabelle und Host-Ping. Wenn möglich Link-Capture mit UDP 4789 und erwarteter VNI.

**Soll:** Beide VTEPs erreichen einander, die vereinbarte VNI ist aktiv und der Datenstrom wird am anderen Leaf dem richtigen VLAN zugeordnet.

**Gegenprobe:** Underlay-Erreichbarkeit ohne Overlay darf nicht als Nachweis zählen.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 17 — QoS-Konfiguration und Zähler interpretieren

<details><summary>Hinweis 1 · Denkanstoß</summary>

Beginne mit einem einzelnen Pakettyp.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe erst Klassifizierung, dann Behandlung.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche Service-Policy-Richtung und DSCP im Capture.

</details>

**Nachweis:** show policy-map interface und Capture vor/nach der Markierung, je Versuch nur einen Fluss senden.

**Soll:** Klasse, Richtung, Zähler und DSCP passen je Testfluss zur Aufgabe. Du erklärst Policing, Shaping und Priorität anhand der jeweiligen Konfiguration.

**Gegenprobe:** Der Gaststrom erhält keine priorisierte Behandlung. Virtuelle Rate/Timing-Messung ist kein Hardware-Benchmark.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 18 — NetFlow messen und Spiegelung planen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Cache und Export sind zwei Stationen.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe Flow-Key, Interface-Bindung und Exportziel.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche die Cache-Felder und warte auf den Export-Timer.

</details>

**Nachweis:** show flow monitor MON cache/statistics, show flow exporter EXP statistics und Link-Capture mit UDP 2055 nach Flow-Ablauf. Spiegelung nur auf unterstützendem Image live abnehmen.

**Soll:** Du zeigst getrennte Flow-Datensätze und beobachtest den Export am richtigen Link. Für Spiegelung legst du Quelltyp, Transport und Zieltyp je Verfahren dar.

**Gegenprobe:** Erlaubtes Weiterleiten allein erzeugt ohne Monitorbindung keinen Nachweis im Flow-Cache.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 19 — NETCONF und RESTCONF Ende zu Ende

<details><summary>Hinweis 1 · Denkanstoß</summary>

Transport erreichbar ist nicht gleich Datastore lesbar.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche Authentisierung und Protokollzustand separat.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe HTTPS-Dienst, NETCONF-Listener und YANG-Pfad.

</details>

**Nachweis:** HTTP-Status und Payload, NETCONF-Hello und rpc-reply, show running-config interface Gi2. Prüfe bei Transportfehlern TCP 22/443/830 getrennt.

**Soll:** HTTPS-Abfrage, NETCONF-RPC und die einzige beabsichtigte Description-Änderung sind getrennt belegt. Ordne den API-Fehler eines falschen Pfads ein.

**Gegenprobe:** Mit einer falschen Ressource darf der Client keinen erfolgreichen Write melden. Das Management-Subnetz bleibt isoliert.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 20 — Python, JSON und API-Payloads ohne CML

<details><summary>Hinweis 1 · Denkanstoß</summary>

Trenne Transport, Syntax und Inhalt.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe Statuscode und JSON-Feld unabhängig.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Vergleiche echte Antwort mit erwartetem Schema.

</details>

**Nachweis:** Vorhersage vor Ausführung notieren, JSON mit Parser einlesen, Tests für 401/403/429/503 und Payload-Felder auswerten. SD-WAN Manager eigene Vergleichsaufgabe ergänzen.

**Soll:** Tests und eigene Erklärung passen für gültige und fehlerhafte Antworten.

**Gegenprobe:** Ein Feed mit fehlendem Attribut darf nicht als erfolgreicher Datenabruf zählen.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 21 — Designentscheidungen und Betriebsabläufe begründen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Beginne mit einer Anforderung.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne Datenpfad und Steuerung.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Begründe, wo der Ausfall endet.

</details>

**Nachweis:** Antwort anhand der konkreten Entscheidung, der Rollen und des Fehlerszenarios gegen die vorhandenen Falllösungen prüfen.

**Soll:** Deine Auswahl lässt sich aus Anforderungen herleiten. Bei Catalyst Center unterscheidest du Konfigurationsaufgaben, Monitoring und KI-gestützte Diagnose.

**Gegenprobe:** Nenne je Fall eine Anforderung, bei der dein Entwurf ungeeignet wäre.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 22 — Security-Entscheidungen erklären

<details><summary>Hinweis 1 · Denkanstoß</summary>

Formuliere das zu schützende Gut.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Verfolge den Zugriff von der Identität bis zur Regel.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe, wo die Entscheidung und wo die Durchsetzung stattfinden.

</details>

**Nachweis:** Entscheidungsbegründung mit den Falllösungen vergleichen, z. B. TLS, Policy-Reihenfolge oder TrustSec-SGT und Durchsetzungsort.

**Soll:** Du kannst anhand des Falls Authentisierung, Autorisierung und Durchsetzung unterscheiden und das jeweilige Sicherheitsziel erklären.

**Gegenprobe:** Nenne pro Kontrolle eine Bedingung, die sie nicht abdeckt.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 23 — Abschlusslab Campus und Edge

<details><summary>Hinweis 1 · Denkanstoß</summary>

Zeichne den scheiternden Ende-zu-Ende-Pfad.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe zuerst gemeinsame Ursachen der Symptome.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Isoliere den ersten Übergang, an dem der Kontrollfluss abweicht.

</details>

**Nachweis:** Nutze Flooding-/Trunk-, Adjacency-, NAT-/ACL- und Clientdaten als voneinander unabhängige Belege. Abschlussabnahme mit FAULTS.md nach der Zeitbox.

**Soll:** Hosts, Gateway, Routing und Edge-Funktion erreichen den vereinbarten Endzustand. Mindestens ein Befund pro bearbeitetem Ticket zeigt die Ursache vor und die Wirkung nach dem Fix.

**Gegenprobe:** Weise einen funktionsfähigen Kontrollfluss nach und zeige, dass ein unzulässiger Verkehrsfluss weiterhin blockiert ist.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 24 — WAN- und Overlay-Transfer

<details><summary>Hinweis 1 · Denkanstoß</summary>

Prüfe erst die äußeren Adressen.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne VRF-, Tunnel- und Peer-Kontext.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Suche die erste fehlende Route oder SA im beabsichtigten Pfad.

</details>

**Nachweis:** show ip bgp summary/route im Transport, show ip route vrf und IPsec-SA-Zähler plus kontrollierter Hostverkehr.

**Soll:** Belege den vorgesehenen eBGP-Transport, die geschützten Overlay-Pfade und getrennte Kundenerreichbarkeit.

**Gegenprobe:** Ein Underlay-Ping darf keinen IPsec-Erfolg vortäuschen; Nachweis per SA-Zähler.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 25 — EIGRP-Routen und Alternativen einordnen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Wem gehört welche Distanz?

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne Auswahl der Alternativroute und Installation im RIB.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe die Feasibility Condition für den konkreten Prefix.

</details>

**Nachweis:** show ip eigrp neighbors/topology und show ip route; RD/FD und installierten Next-Hop vor/nach vergleichen.

**Soll:** RD und FD sind am konkreten Präfix nachvollziehbar, und die zusätzliche Route erfüllt die Schleifenbedingung.

**Gegenprobe:** Ein nicht zulässiger Pfad wird durch Variance allein nicht installierbar.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 26 — Interne und externe BGP-Lernwege vergleichen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Wo wurde die Route ursprünglich gelernt?

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche Sessiontyp und Weitergaberegel.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe Loopback-Next-Hop, Client-Rolle und gesendete Community.

</details>

**Nachweis:** show ip bgp summary, Präfixdetails mit Attributen, advertised-routes nach Sitzungstyp.

**Soll:** Du zeigst einen Route-Reflector-Client-Pfad und den Best Path für beide Protokollkontexte.

**Gegenprobe:** Eine unerwünschte Route mit falscher Community wird gemäß Vorgabe nicht als bevorzugt behandelt.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 27 — Redistribution ohne Rückverteilung

<details><summary>Hinweis 1 · Denkanstoß</summary>

Verfolge ein Präfix einmal im Kreis.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne Auswahl, Tagging und Seed-Metrik.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe die Filterreihenfolge an beiden Richtungen.

</details>

**Nachweis:** show ip route für erlaubte und ausgeschlossene Präfixe, Route-Map-Policy und Tags auf den Grenzroutern vergleichen.

**Soll:** Du belegst Route, Ursprung und Tags an zwei Beobachtungspunkten und die gewünschte Erreichbarkeit nach Ausfall eines Übergangs.

**Gegenprobe:** Verbotenes Präfix und Rückverteilung bleiben auch beim Ausfall aus.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 28 — OSPF-Area-Verhalten anhand der LSDB

<details><summary>Hinweis 1 · Denkanstoß</summary>

Entscheide, welche Information an der Grenze gefiltert wird.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche LSDB und RIB.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe Area-Optionen an beiden Enden der gestörten Verbindung.

</details>

**Nachweis:** show ip ospf neighbor/database und show ip route. LSA-Typ, Scope und Default getrennt protokollieren.

**Soll:** Nachbarn erreichen die beabsichtigten Zustände. LSDB und Routentabelle belegen den Wechsel der Area-Policy.

**Gegenprobe:** Ein LSA, der in der eingeschränkten Area fehlen soll, darf dort nicht mehr sichtbar sein.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 29 — PBR nach Quelle und Anwendung interpretieren

<details><summary>Hinweis 1 · Denkanstoß</summary>

Suche am Eingang, an dem der Clientfluss ankommt.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne Match, Sequenz und Next-Hop.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe getrennt Interface-Policy und Router-lokal erzeugten Verkehr.

</details>

**Nachweis:** traceroute von H1/H2, show ip policy und show route-map je isoliertem ICMP/TCP-Test.

**Soll:** Baseline und Policy-Pfad sind für jeden Testfall dokumentiert. Der Pfadwechsel ist an einem Policy-Zähler oder Capture nachvollziehbar.

**Gegenprobe:** Ein unabhängiger H1-Kontrollfluss bleibt auf Provider A, und lokal erzeugter Verkehr erbt die Interface-Policy nicht automatisch.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 30 — Abschluss Routing im kombinierten Netz

<details><summary>Hinweis 1 · Denkanstoß</summary>

Folge einem Präfix vom Ursprung.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Finde die erste Stelle, an der es fehlt oder sich ändert.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Trenne Herkunft, Auswahl und Ankündigung.

</details>

**Nachweis:** Nachbarschaft, LSDB/Topologietabelle, RIB und tatsächlichen Pfad je Präfix vergleichen. Für Filter auch absichtlich ausgeschlossene Präfixe prüfen.

**Soll:** Erreichbarkeit, Präfixursprung und vorgesehene Routingentscheidung sind pro Ticket nachvollziehbar.

**Gegenprobe:** Ein Ersatzpfad darf eine fehlerhafte Nachbarschaft oder unerwünschte Rückverteilung nicht verdecken.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 31 — MST-Regionen und PVST-Grenze

<details><summary>Hinweis 1 · Denkanstoß</summary>

Ziehe zuerst die Regionsgrenze.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche Konfiguration und Instanzzustand.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe Mapping, Revision und Richtung der Root-Wahl.

</details>

**Nachweis:** show spanning-tree mst configuration digest, show spanning-tree mst 1/2, show spanning-tree inconsistentports vor/nach.

**Soll:** Der Digest in der Region, die vorgesehenen Root-Ports und der erwartete Grenzport sind nachvollziehbar.

**Gegenprobe:** Ein abweichender Digest oder ungültiger PVST-Wurzelpfad muss eine erkennbare Abweichung auslösen.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 32 — SSM, Bidir-PIM und Anycast-RP vergleichen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Welche Information braucht der Empfänger vor dem Beitritt?

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Prüfe Unicast-RPF, Gruppenart und RP separat.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe pro Gruppe, ob die erwartete Art von Multicast-Eintrag entsteht.

</details>

**Nachweis:** show ip mroute, show ip igmp groups detail, show ip pim rp mapping, show ip msdp summary/sa-cache und Gruppentest pro Verfahren.

**Soll:** Du weist (S,G) bei SSM, den Shared Tree bei Bidir sowie die RP-/MSDP-Zustände für die Anycast-Gruppe nach.

**Gegenprobe:** Zwei aufeinanderfolgende Gruppenversuche müssen getrennt bleiben. SSM ohne Quelle darf keinen erfolgreichen Zustelltest liefern.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 33 — Diagnose aus Ausgaben und Gegenproben

<details><summary>Hinweis 1 · Denkanstoß</summary>

Vergleiche einen guten und schlechten Fluss.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Ändere pro Versuch nur eine Variable.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe Richtung, Paketgröße und DF getrennt.

</details>

**Nachweis:** Ping/Traceroute mit passender Quelle, Größenvergleich mit DF und gezielte Debug-Ausgabe zusammen protokollieren. Keine globalen Dauerdebugs.

**Soll:** Du grenzt die Fehlerdomäne mit zwei unabhängigen Beobachtungen ein und kannst den Befund angeben, der andere Ursachen ausschließt.

**Gegenprobe:** Wiederhole den Test mit kleinem und großem Paket; Debugs werden beendet und Filter entfernt.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 34 — OSPF-Filter und Netztyp ohne Ratespiel

<details><summary>Hinweis 1 · Denkanstoß</summary>

Notiere die gewünschte Sicht pro Area.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Entscheide, ob die LSA oder nur die Routenauswahl betroffen ist.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Wähle den Filterort aus ABR, ASBR und lokalem Router.

</details>

**Nachweis:** show ip ospf neighbor/interface, show ip ospf database summary/external, show ip route je Beobachtungspunkt.

**Soll:** Die Abnahme zeigt für jede Vorgabe, an welchem Router das Präfix in LSDB und RIB sichtbar sein soll. Du erklärst die Grenze zwischen lokalem RIB-Filter und LSA-Filter.

**Gegenprobe:** Beweise die Abwesenheit genau der ausgeschlossenen Route, während ein erlaubtes Kontrollpräfix weiter vorhanden ist.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 35 — IP SLA zur Umschaltung einsetzen

<details><summary>Hinweis 1 · Denkanstoß</summary>

Messziel und Dienstziel sind unterschiedliche Rollen.

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Vergleiche Ergebnis, Tracking und ausgewählte Route.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Prüfe, ob die Messung beim Failover den Pfad gewechselt hat.

</details>

**Nachweis:** show ip sla statistics, show track und show ip route 0.0.0.0 im Zeitverlauf, dazu Client-Ping oder Traceroute.

**Soll:** SLA-Messwert, Tracking-Zustand, installierte Route und Clientpfad ändern sich passend zum simulierten Ausfall und zur Rückkehr.

**Gegenprobe:** Bleibt nur der erste Hop erreichbar, darf er die Störung hinter dem Provider nicht verdecken.

Den Referenzweg findest du im gleich nummerierten Lab-Ordner. Bei Labs 21 und 22 stehen die Antworten in der Fallstudie.

## Lab 36 — Ereignisgesteuerte Diagnose

<details><summary>Hinweis 1 · Denkanstoß</summary>

Woran erkennt der Router, dass genau eine Nachbarschaft verloren ging?

</details>

<details><summary>Hinweis 2 · Diagnosebereich</summary>

Trenne das OSPF-Ereignis, die Registrierung des Applets und den Erfolg der Dateiausgabe.

</details>

<details><summary>Hinweis 3 · Konkretere Hilfe</summary>

Erfasse eine echte Syslog-Zeile nach einem kontrollierten Verlust des Testpfads. Gleiche Interface-Name und Zustandswechsel mit dem Trigger ab.

</details>

[Denkweg, Musterkonfiguration und Gegenprobe](36-EEM-Applets/solutions/PILOT.md) · [Reparaturtickets und Referenzweg](36-EEM-Applets/solutions/FAULTS.md)
