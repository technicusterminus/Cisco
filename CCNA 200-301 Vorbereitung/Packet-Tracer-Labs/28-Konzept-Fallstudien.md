# Lab 28 – Konzept-Fallstudien (ohne Packet Tracer)

Die folgenden Fälle decken Ziele ab, die sich nicht sinnvoll im Simulator üben lassen: **1.1, 1.2, 1.12, 2.8, 5.1, 5.2, 5.4, 6.1, 6.2, 6.3, 6.4**. Jede Aufgabe ist offen formuliert: Antworte schriftlich in eigenen Worten, dann klappe die Musterantwort auf. Es gibt keine einzige richtige Wortwahl, aber die Kernaussagen müssen stimmen.

**Lernziele:** Nach diesen Fällen kannst du …

- VM, Container und VRF sowie Bedrohung, Schwachstelle, Exploit und Risiko unterscheiden.
- Bausteine eines Security-Programms und einer Passwortrichtlinie begründen.
- Traditionelle und controllerbasierte Netze vergleichen und den Nutzen von Automation und KI einschätzen.

| Fall | Ziele |
|---|---|
| 1. Wann VM, wann Container, wann VRF? | 1.12 |
| 2. Bedrohung, Schwachstelle, Exploit, Risiko | 5.1 |
| 3. Security-Programm: Awareness und physischer Zugang | 5.2 |
| 4. Passwortrichtlinie, MFA, Zertifikate, Biometrie | 5.4, 5.3 |
| 5. Management-Zugänge zu Netzwerkgeräten | 2.8, 4.8 |
| 6. Automatisierung im Netzbetrieb | 6.1 |
| 7. Traditionelles Netz vs. controllerbasiertes Netz | 6.2, 6.3 |
| 8. Künstliche Intelligenz im Netzbetrieb | 6.4 |
| 9. Topologie wählen: 2-Tier, 3-Tier, Spine-Leaf, SOHO | 1.2, 1.1 |

## Fall 1: Wann VM, wann Container, wann VRF?

**CCNA-Ziele:** 1.12

Ein Dienstleister betreibt für drei Kunden je eine Webanwendung und ein internes Netz. Kunde A und Kunde B verwenden beide 10.0.0.0/8 intern.

1. Erkläre kurz Hypervisor Typ 1 und Typ 2, Container und VRF.
2. Welche Technik wählst du für (a) die Isolation der Betriebssysteme der Anwendungen, (b) das schnelle Starten vieler gleicher Webdienste, (c) die Trennung der Routingtabellen von A und B im Router?
3. Nenne je einen Nachteil von VMs, Containern und VRFs.

<details><summary>Musterantwort</summary>

1. **Typ 1 läuft auf der Hardware, Typ 2 auf einem Betriebssystem. Container teilen sich den Kernel, eine VRF ist eine eigene Routing-Tabelle.** Beispiele für Typ 1 sind ESXi, KVM und Hyper-V, für Typ 2 VirtualBox und VMware Workstation. Container (Docker, Kubernetes) isolieren nur Prozesse, deshalb starten sie in Sekunden. Eine VRF trennt Routing- und Forwarding-Tabelle innerhalb desselben Routers.
2. **(a) VM, (b) Container, (c) VRF pro Kunde.** Die VM bringt ein eigenes Gast-Betriebssystem mit, das trennt am stärksten. Container sind klein und schnell gestartet, ideal für viele gleiche Webdienste. Mit je einer VRF dürfen A und B beide 10.0.0.0/8 verwenden, ohne sich zu stören.
3. **VM: schwer. Container: schwächer isoliert. VRF: Verbindungen müssen bewusst gebaut werden.** VMs brauchen mehr Ressourcen und starten langsamer. Container teilen den Kernel, eine Lücke dort trifft alle. Zwischen VRFs fließt nichts ohne Route Leaking, und der Betriebsaufwand wächst mit jeder VRF.

</details>

## Fall 2: Bedrohung, Schwachstelle, Exploit, Risiko

**CCNA-Ziele:** 5.1

Auf einem Webserver läuft eine veraltete Version mit bekannter Sicherheitslücke. Ein Angreifer nutzt sie mit einem fertigen Skript und verschlüsselt Daten (Ransomware).

1. Ordne zu: Bedrohung (Threat), Schwachstelle (Vulnerability), Exploit, Risiko, Gegenmaßnahme.
2. Welche Schutzziele (CIA) sind betroffen?
3. Ordne die Angriffe der passenden Maßnahme zu: Phishing, DoS/DDoS, Man-in-the-Middle, ARP-Spoofing, Brute-Force-Passwort, Ransomware.
4. Was heißt *Defense in Depth*? Nenne drei Schichten.

<details><summary>Musterantwort</summary>

1. **Bedrohung = Angreifer mit Ransomware, Schwachstelle = ungepatchte Software, Exploit = das Skript, Risiko = Wahrscheinlichkeit × Schaden.** Die Gegenmaßnahmen sind Patchen, Segmentierung, Backups und Endpoint-Schutz. Ohne Schwachstelle hätte die Bedrohung keinen Ansatzpunkt.
2. **Verfügbarkeit und Integrität, bei Datendiebstahl auch Vertraulichkeit.** Die verschlüsselten Daten sind nicht mehr nutzbar und verändert. Viele Ransomware-Gruppen kopieren die Daten vorher und drohen mit Veröffentlichung.
3. **Jeder Angriff hat seine typische Gegenmaßnahme.** Phishing → Awareness, E-Mail-Filter, MFA. DoS/DDoS → Rate Limiting, Scrubbing/CDN, Redundanz. Man-in-the-Middle → TLS/SSH mit Zertifikatsprüfung. ARP-Spoofing → DAI mit DHCP Snooping. Brute Force → Sperre nach Fehlversuchen, lange Passwörter, MFA. Ransomware → Offline-Backups, Patchen, Segmentierung, Endpoint-Schutz.
4. **Mehrere unabhängige Schutzschichten, damit ein einzelner Fehler nicht reicht.** Beispiele sind Perimeter-Firewall, Segmentierung mit VLANs und ACLs, Endpoint-Schutz, MFA, Monitoring und Awareness.

</details>

## Fall 3: Security-Programm: Awareness und physischer Zugang

**CCNA-Ziele:** 5.2

Die IT eines Mittelstandsunternehmens hatte drei Vorfälle: ein Mitarbeitender klickt auf eine Phishing-Mail, ein Besucher läuft unbegleitet in den Serverraum, ein Notebook geht verloren.

1. Welche Elemente gehören zu einem Security-Programm (User Awareness, Training, physische Zugangskontrolle)?
2. Schlage je Vorfall zwei Maßnahmen vor.
3. Wie misst du, ob die Maßnahmen wirken?

<details><summary>Musterantwort</summary>

1. **Awareness, Training und physische Zugangskontrolle, dazu Richtlinien, Incident Response und Audits.** Awareness heißt regelmäßige Sensibilisierung, etwa mit Phishing-Simulationen. Training richtet sich nach der Rolle, Admins brauchen mehr als Sachbearbeiter. Physische Kontrolle umfasst Badges, Schlösser, Schleusen, Kameras und eine Besucherregelung.
2. **Phishing: Simulationstraining und MFA. Serverraum: Badge mit Protokoll und Begleitpflicht. Notebook: Verschlüsselung und Fernlöschung.** MFA macht ein abgefischtes Passwort wertlos. Ein Badgesystem zeigt, wer wann drin war. Eine verschlüsselte Festplatte macht den Verlust zum Hardwareschaden statt zum Datenleck.
3. **Mit Kennzahlen.** Etwa Klickrate in Simulationen, Meldequote und Zeit bis zur Meldung, unbefugte Zutritte, Auditfeststellungen sowie Zahl und Behebungszeit der Vorfälle.

</details>

## Fall 4: Passwortrichtlinie, MFA, Zertifikate, Biometrie

**CCNA-Ziele:** 5.4, 5.3

Ein Passwort-Audit zeigt: viele Konten nutzen `Sommer2024!`, Admins teilen sich ein Konto, VPN-Zugang geht nur mit Passwort.

1. Welche Elemente enthält eine Passwortrichtlinie (Länge, Komplexität, Ablauf, Wiederverwendung, Sperre, Speicherung)? Was gilt heute als empfohlen (Länge vor Komplexität, kein erzwungener regelmäßiger Wechsel ohne Anlass, Prüfung gegen Leak-Listen)?
2. Erkläre die drei Faktoren und gib ein Beispiel für MFA.
3. Wofür sind Zertifikate gut, und was ist der Nachteil von Biometrie?
4. Welche Maßnahmen würdest du für das VPN und für die Admin-Konten treffen?

<details><summary>Musterantwort</summary>

1. **Länge, Wiederverwendungssperre, Sperre nach Fehlversuchen, sichere Speicherung, Wechsel nur bei Anlass.** Empfohlen sind heute lange Passphrasen ab 12 bis 14 Zeichen, ein Passwortmanager und der Abgleich mit bekannten Leaks. Erzwungene Wechsel ohne Anlass führen zu Mustern wie `Sommer2024!`. Gespeichert wird nur als gesalzener Hash.
2. **Wissen, Besitz, Merkmal. MFA kombiniert mindestens zwei, z. B. Passwort und Authenticator-App.** Wissen ist das Passwort, Besitz ein Token, Smartphone oder eine Smartcard, Merkmal ein Fingerabdruck oder Gesicht. Zwei Faktoren derselben Art zählen nicht als MFA.
3. **Zertifikate beweisen Identität kryptografisch, Biometrie lässt sich nicht widerrufen.** Mit Zertifikat geht kein Passwort über das Netz, und Gerät oder Benutzer sind eindeutig zuordenbar. Dafür brauchst du eine PKI. Ein kompromittierter Fingerabdruck bleibt kompromittiert, und biometrische Verfahren haben Fehlerraten.
4. **VPN mit MFA oder Zertifikat, Admins mit persönlichen Konten über TACACS+.** Das VPN fragt den zweiten Faktor zentral per RADIUS ab. Persönliche Admin-Konten mit Accounting zeigen, wer was geändert hat, und privilegierte Zugänge bekommen zusätzlich MFA.

</details>

## Fall 5: Management-Zugänge zu Netzwerkgeräten

**CCNA-Ziele:** 2.8, 4.8

Du verwaltest 200 Switches. Aktuell wird per Telnet mit einem gemeinsamen Passwort zugegriffen.

1. Vergleiche Console, Telnet, SSH, HTTP/HTTPS (Web-GUI), SNMP, RADIUS/TACACS+ und cloud-managed (Meraki) bezüglich Sicherheit und Einsatz.
2. Entwirf eine Verbesserung in drei Schritten.

<details><summary>Musterantwort</summary>

1. **Console für den Notfall, SSH für die CLI, HTTPS für die GUI, SNMPv3 zur Überwachung, TACACS+/RADIUS für zentrale Anmeldung. Telnet und HTTP nie.** Die Console braucht physischen Zugang und dient der Erstkonfiguration. Telnet und HTTP übertragen alles im Klartext, SSH (Version 2) und HTTPS verschlüsseln. SNMP nur in Version 3 mit Authentisierung und Verschlüsselung. TACACS+ eignet sich besonders für Geräteadministration, weil es einzelne Befehle autorisiert. Cloud-managed Geräte (Meraki) bauen eine ausgehende Verbindung zur Cloud auf und werden dort verwaltet.
2. **Erst SSH, dann zentrale Anmeldung, dann Protokollierung.** (1) SSH einschalten, Telnet abschalten und den Zugriff per Management-ACL oder Management-VRF begrenzen. (2) Anmeldung über TACACS+ oder RADIUS mit persönlichen Konten und einem lokalen Notfallkonto. (3) Accounting und Logging an einen Syslog-Server, regelmäßige Konfigurations-Backups.

</details>

## Fall 6: Automatisierung im Netzbetrieb

**CCNA-Ziele:** 6.1

Ein neuer NTP-Server muss auf 200 Switches eingetragen werden. Bisher loggt sich ein Techniker pro Switch ein und tippt den Befehl. Das dauert 3 Tage, und zuletzt blieben 6 Switches vergessen.

1. Welche Vorteile bringt Automatisierung (Geschwindigkeit, Konsistenz, Nachvollziehbarkeit, Compliance)?
2. Wie erkennst du *Configuration Drift*, und wie verhindert ihn Automatisierung?
3. Nenne zwei Risiken von Automatisierung und eine Gegenmaßnahme.
4. Skizziere den Ablauf mit Ansible oder einem Skript (Inventar, Vorlage, Test, Rollout in Wellen, Verifikation).

<details><summary>Musterantwort</summary>

1. **Schneller, einheitlicher, nachvollziehbar.** Ein Skript erledigt die 200 Switches in Minuten, ohne Tippfehler und ohne vergessene Geräte. Änderungen liegen versioniert im Code, also mit wer, wann und was. Compliance-Prüfungen laufen automatisch, und das Wissen steckt im Code statt in Köpfen.
2. **Drift ist die Abweichung des Ist- vom Sollzustand. Automatisierung erzwingt den Sollzustand immer wieder.** Du erkennst Drift, indem du die laufende Konfiguration regelmäßig mit der Vorlage vergleichst. Ein idempotentes Werkzeug wie Ansible stellt bei jedem Lauf den Sollzustand her und ändert nur, was abweicht.
3. **Ein Fehler wirkt sofort überall, und das Skript selbst wird zum Angriffsziel.** Dagegen helfen Tests im Lab, Rollout in Wellen mit Prüfpunkten, ein Rollback-Plan, Zugangsdaten im Vault und ein Review jeder Änderung.
4. **Inventar → Vorlage → Trockenlauf → Pilot → Wellen → Prüfung.** Die Switchliste ist das Inventar. Das Playbook enthält `ntp server …`. `--check` zeigt, was sich ändern würde. Erst 2 Switches, dann Wellen. Am Ende prüft `show ntp status` jedes Gerät, und das Ergebnis wird protokolliert.

</details>

## Fall 7: Traditionelles Netz vs. controllerbasiertes Netz

**CCNA-Ziele:** 6.2, 6.3

Ein Unternehmen will 50 Standorte mit einem neuen WLAN-Profil und neuer Segmentierung versorgen. Heute läuft alles per CLI pro Gerät. Zur Wahl steht ein controllerbasiertes Netz (z. B. Catalyst Center mit SD-Access).

1. Vergleiche in einer Tabelle: Konfiguration, Management-Ebene, Control Plane, Konsistenz, Fehlersuche/Assurance, Skalierung, Einarbeitung.
2. Erkläre Underlay, Overlay, Fabric.
3. Was heißt Trennung von Control Plane und Data Plane? Nenne Nord- und Südschnittstellen und je ein Protokoll/Beispiel.
4. Ordne zu: REST-API an den Controller, NETCONF zum Switch, CLI per SSH, OpenFlow.

<details><summary>Musterantwort</summary>

1. **Traditionell konfigurierst du jedes Gerät einzeln, controllerbasiert beschreibst du zentral die Absicht.**

| Merkmal | Traditionell | Controllerbasiert |
|---|---|---|
| Konfiguration | CLI pro Gerät | zentral über Absicht und Richtlinien |
| Management | pro Gerät, SNMP | API und GUI am Controller |
| Control Plane | verteilt, jedes Gerät entscheidet selbst | Policy zentral, Fabric-Control per LISP |
| Konsistenz | Abweichungen häufig | einheitlich aus Vorlagen |
| Fehlersuche | manuell, Gerät für Gerät | Assurance mit Telemetrie |
| Skalierung | Aufwand wächst mit jedem Gerät | über Vorlagen |
| Einarbeitung | bekanntes Wissen | neue Fähigkeiten nötig |

2. **Underlay transportiert, Overlay trennt logisch, Fabric ist beides zusammen.** Das Underlay ist das IP-Netz mit Routing und Konnektivität. Das Overlay legt logische Netze darüber, etwa mit VXLAN-Tunneln. Eine Fabric verwaltet Underlay und Overlay als ein automatisiertes Ganzes.
3. **Die Control Plane entscheidet, die Data Plane leitet weiter.** In SDN sitzt die Entscheidungslogik zentral im Controller, die Geräte setzen sie nur um. Die Northbound-Schnittstelle verbindet Controller und Anwendungen, typisch per REST-API. Die Southbound-Schnittstelle verbindet Controller und Geräte, etwa per NETCONF, RESTCONF, SNMP, CLI oder OpenFlow.
4. **REST-API an den Controller = Northbound. NETCONF, CLI per SSH und OpenFlow = Southbound.** Northbound zeigt nach oben zu Anwendungen, Southbound nach unten zu den Geräten.

</details>

## Fall 8: Künstliche Intelligenz im Netzbetrieb

**CCNA-Ziele:** 6.4

Die Betriebsleitung fragt: „Wo kann uns KI im Netzbetrieb helfen, und wo nicht?“

1. Unterscheide prädiktive KI/Machine Learning und generative KI. Gib je zwei Anwendungsfälle im Netzbetrieb.
2. Nenne Chancen und Grenzen/Risiken (Datenqualität, Halluzinationen, Datenschutz, Nachvollziehbarkeit).
3. Eine generative KI schlägt dir eine Konfiguration für ein neues VLAN samt ACL vor. Wie gehst du damit um?

<details><summary>Musterantwort</summary>

1. **Prädiktive KI erkennt Muster und sagt voraus, generative KI erzeugt neue Inhalte.** Prädiktiv: Anomalien im Verkehr erkennen, Kapazität planen, Ausfälle vorhersagen, Ursachen eingrenzen. Generativ: Konfigurationsentwürfe, Skripte und Dokumentation schreiben, Troubleshooting im Dialog unterstützen.
2. **Chancen: schnellere Fehlersuche, weniger Routine, bessere Prognosen. Grenzen: Datenqualität, Halluzinationen, Datenschutz, Nachvollziehbarkeit.** Ein Modell ist nur so gut wie seine Daten. Generative KI erfindet plausible, aber falsche Befehle. Vertrauliche Daten dürfen nicht unkontrolliert an externe Dienste gehen. Die Verantwortung bleibt beim Menschen.
3. **Als Entwurf behandeln, prüfen, testen, kontrolliert einspielen.** Gleiche die Befehle mit der Dokumentation ab, teste im Lab und spiele die Änderung nach Review im Wartungsfenster ein, mit Rollback-Plan. Zugangsdaten und interne Details gehören nicht in öffentliche Dienste.

</details>

## Fall 9: Topologie wählen: 2-Tier, 3-Tier, Spine-Leaf, SOHO

**CCNA-Ziele:** 1.2, 1.1

Drei Szenarien: (A) ein Büro mit 12 Personen, (B) ein Campus mit sechs Gebäuden und 3000 Endgeräten, (C) ein Rechenzentrum mit viel Server-zu-Server-Verkehr.

1. Welche Architektur passt zu A, B, C und warum (SOHO, 2-Tier, 3-Tier, Spine-Leaf)?
2. Welche Rolle haben Router, Layer-2-/Layer-3-Switches, Firewall/IPS, AP, WLC in B?
3. Wie unterscheiden sich On-Premises und Cloud beim WAN-Design?

<details><summary>Musterantwort</summary>

1. **A: SOHO. B: 3-Tier. C: Spine-Leaf.** Für 12 Personen reicht ein Gerät, das Router, Firewall, Switch und WLAN vereint. Sechs Gebäude mit 3000 Endgeräten brauchen Access, Distribution und Core für Skalierung und Fehlerbegrenzung. Im Rechenzentrum ist jeder Leaf mit jedem Spine verbunden: gleiche Latenz zwischen allen Servern, viel Ost-West-Bandbreite, einfache Erweiterung.
2. **Access verbindet, Distribution und Core routen, Router und Firewall bilden den Übergang, der WLC steuert die APs.** Access-Switches (Layer 2, PoE) schließen Endgeräte und APs an. Distribution und Core (Layer 3) routen zwischen VLANs und Gebäuden. Am Netzübergang stehen Router und Firewall, das IPS inspiziert den Verkehr.
3. **On-Premises liegt alles im eigenen Haus, in der Cloud wird die Anbindung zum Anbieter kritisch.** On-Premises verbindest du Standorte über WAN-Router, MPLS oder VPN. Liegen die Dienste in der Cloud, brauchen Internet- oder Direktanbindung Redundanz, Bandbreite und Schutz, oft mit SD-WAN.

</details>

