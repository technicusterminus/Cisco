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

1. Typ 1 läuft direkt auf der Hardware (ESXi, KVM, Hyper-V), Typ 2 als Programm auf einem Betriebssystem (VirtualBox, VMware Workstation). Container teilen sich den Kernel des Hosts und isolieren Prozesse (Docker, Kubernetes). Eine VRF ist eine eigene Routingtabelle (und Forwardingtabelle) im selben Router.
2. (a) VM (eigenes Gast-OS), (b) Container (klein, in Sekunden gestartet), (c) VRF pro Kunde, überlappende Adressen sind dann möglich.
3. VM: größerer Ressourcenverbrauch und längere Startzeit. Container: schwächere Isolation (gemeinsamer Kernel). VRF: Verbindung zwischen VRFs braucht ein bewusstes Leaken (Route Leaking), Konfigurations- und Betriebsaufwand wächst.

</details>

## Fall 2: Bedrohung, Schwachstelle, Exploit, Risiko

**CCNA-Ziele:** 5.1

Auf einem Webserver läuft eine veraltete Version mit bekannter Sicherheitslücke. Ein Angreifer nutzt sie mit einem fertigen Skript und verschlüsselt Daten (Ransomware).

1. Ordne zu: Bedrohung (Threat), Schwachstelle (Vulnerability), Exploit, Risiko, Gegenmaßnahme.
2. Welche Schutzziele (CIA) sind betroffen?
3. Ordne die Angriffe der passenden Maßnahme zu: Phishing, DoS/DDoS, Man-in-the-Middle, ARP-Spoofing, Brute-Force-Passwort, Ransomware.
4. Was heißt *Defense in Depth*? Nenne drei Schichten.

<details><summary>Musterantwort</summary>

1. Bedrohung: Angreifer/Ransomware. Schwachstelle: die ungepatchte Software. Exploit: das Skript, das die Lücke ausnutzt. Risiko: Wahrscheinlichkeit × Schaden (Datenverlust, Ausfall). Gegenmaßnahme: Patchen, Segmentierung, Backups, Endpoint-Schutz.
2. Verfügbarkeit und Integrität (Verschlüsselung der Daten), bei Datendiebstahl auch Vertraulichkeit.
3. Phishing → Awareness, E-Mail-Filter, MFA. DoS/DDoS → Rate Limiting, Scrubbing/CDN, Redundanz. Man-in-the-Middle → TLS/SSH, Zertifikatsprüfung, DAI. ARP-Spoofing → DAI und DHCP Snooping. Brute-Force → Lockout, starke Passwörter, MFA. Ransomware → Backups (offline), Patching, Segmentierung, Endpoint-Schutz.
4. Mehrere unabhängige Schutzschichten, damit ein Fehler nicht genügt: z. B. Perimeter-Firewall, Segmentierung/VLANs/ACLs, Endpoint-Schutz, Authentisierung (MFA), Monitoring/Logging, Awareness.

</details>

## Fall 3: Security-Programm: Awareness und physischer Zugang

**CCNA-Ziele:** 5.2

Die IT eines Mittelstandsunternehmens hatte drei Vorfälle: ein Mitarbeitender klickt auf eine Phishing-Mail, ein Besucher läuft unbegleitet in den Serverraum, ein Notebook geht verloren.

1. Welche Elemente gehören zu einem Security-Programm (User Awareness, Training, physische Zugangskontrolle)?
2. Schlage je Vorfall zwei Maßnahmen vor.
3. Wie misst du, ob die Maßnahmen wirken?

<details><summary>Musterantwort</summary>

1. User Awareness (regelmäßige Sensibilisierung, Phishing-Simulationen), Training (rollenbasiert, z. B. für Admins), physische Zugangskontrolle (Badges, Schlösser, Mantraps, Kameras, Besucherregelung), dazu Richtlinien, Incident Response und Audits.
2. Phishing: Awareness-Training mit Simulation, Mailfilter plus MFA. Serverraum: Badgesystem mit Protokoll, Besucher nur begleitet, Kamera/Alarm. Notebook: Festplattenverschlüsselung, Fernlöschung/MDM, Meldeprozess.
3. Kennzahlen: Klickrate in Simulationen, Meldequote, Zeit bis zur Meldung, Zahl unbefugter Zutritte, Auditfeststellungen, Vorfallzahlen und Behebungszeit.

</details>

## Fall 4: Passwortrichtlinie, MFA, Zertifikate, Biometrie

**CCNA-Ziele:** 5.4, 5.3

Ein Passwort-Audit zeigt: viele Konten nutzen `Sommer2024!`, Admins teilen sich ein Konto, VPN-Zugang geht nur mit Passwort.

1. Welche Elemente enthält eine Passwortrichtlinie (Länge, Komplexität, Ablauf, Wiederverwendung, Sperre, Speicherung)? Was gilt heute als empfohlen (Länge vor Komplexität, kein erzwungener regelmässiger Wechsel ohne Anlass, Prüfung gegen Leak-Listen)?
2. Erkläre die drei Faktoren und gib ein Beispiel für MFA.
3. Wofür sind Zertifikate gut, und was ist der Nachteil von Biometrie?
4. Welche Maßnahmen würdest du für das VPN und für die Admin-Konten treffen?

<details><summary>Musterantwort</summary>

1. Länge (≥ 12–14 Zeichen), Komplexität bzw. Passphrasen, Wiederverwendungssperre, Sperre nach Fehlversuchen, sichere Speicherung (gesalzene Hashes), Ablauf nur bei Verdacht/Kompromittierung. Empfohlen werden lange Passphrasen, Passwortmanager und der Abgleich mit bekannten Leaks.
2. Wissen (Passwort), Besitz (Token, Smartphone-App, Smartcard), Merkmal (Fingerabdruck, Gesicht). MFA kombiniert mindestens zwei, z. B. Passwort + Authenticator-App.
3. Zertifikate beweisen die Identität kryptografisch (kein Passwort über das Netz), Gerät und Benutzer sind zuordenbar; sie brauchen eine PKI und Lebenszyklusverwaltung. Biometrie ist nicht widerrufbar (ein kompromittiertes Merkmal bleibt kompromittiert) und hat Fehlerraten.
4. VPN: MFA oder Zertifikat plus Passwort, zentrale Authentisierung per RADIUS. Admins: persönliche Konten statt Sammelkonto, TACACS+/RADIUS mit Accounting, privilegierte Zugänge mit MFA und Protokollierung.

</details>

## Fall 5: Management-Zugänge zu Netzwerkgeräten

**CCNA-Ziele:** 2.8, 4.8

Du verwaltest 200 Switches. Aktuell wird per Telnet mit einem gemeinsamen Passwort zugegriffen.

1. Vergleiche Console, Telnet, SSH, HTTP/HTTPS (Web-GUI), SNMP, RADIUS/TACACS+ und cloud-managed (Meraki) bezüglich Sicherheit und Einsatz.
2. Entwirf eine Verbesserung in drei Schritten.

<details><summary>Musterantwort</summary>

1. Console: lokal, Notfall/Erstkonfiguration, physischer Zugang nötig. Telnet: Klartext, nicht verwenden. SSH: verschlüsselt, Standard für CLI-Zugriff (Version 2). HTTP: Klartext, HTTPS: verschlüsselte Web-GUI. SNMP: Überwachung (v3 für Sicherheit). RADIUS/TACACS+: zentrale Authentisierung/Autorisierung/Accounting (TACACS+ für Geräteadministration). Cloud-managed: Verwaltung über eine Cloud-Plattform, Geräte bauen eine ausgehende Verbindung auf.
2. (1) SSH statt Telnet, Telnet abschalten, Management-ACL/Management-VRF. (2) Zentrale Anmeldung über TACACS+/RADIUS mit persönlichen Konten und lokalem Notfallkonto. (3) Accounting/Logging an einen Syslog-Server, regelmäßige Konfigurations-Backups.

</details>

## Fall 6: Automatisierung im Netzbetrieb

**CCNA-Ziele:** 6.1

Ein neuer NTP-Server muss auf 200 Switches eingetragen werden. Bisher loggt sich ein Techniker pro Switch ein und tippt den Befehl. Das dauert 3 Tage, und zuletzt blieben 6 Switches vergessen.

1. Welche Vorteile bringt Automatisierung (Geschwindigkeit, Konsistenz, Nachvollziehbarkeit, Compliance)?
2. Wie erkennst du *Configuration Drift*, und wie verhindert ihn Automatisierung?
3. Nenne zwei Risiken von Automatisierung und eine Gegenmaßnahme.
4. Skizziere den Ablauf mit Ansible oder einem Skript (Inventar, Vorlage, Test, Rollout in Wellen, Verifikation).

<details><summary>Musterantwort</summary>

1. Schneller und wiederholbar, weniger Tippfehler, einheitlicher Zustand, Änderungen sind im Code versioniert (wer/wann/was), Audits und Compliance-Prüfungen lassen sich automatisieren, Wissen liegt im Code statt in Köpfen.
2. Drift = Abweichung der Ist- von der Soll-Konfiguration durch Handarbeit. Automatisierung erzwingt den Sollzustand idempotent und vergleicht regelmäßig.
3. Risiken: ein Fehler wirkt breit und schnell; Skripte werden zur Sicherheitslücke (Zugangsdaten). Gegenmaßnahmen: Test im Lab, Rollout in Wellen mit Prüfpunkten, Rollback, Secrets im Vault, Review der Änderungen.
4. Inventar (Switchliste) → Playbook/Vorlage mit `ntp server …` → Trockenlauf (`--check`) und Test auf 2 Switches → Rollout in Wellen → Verifikation (`show ntp status`) → Ergebnis protokollieren.

</details>

## Fall 7: Traditionelles Netz vs. controllerbasiertes Netz

**CCNA-Ziele:** 6.2, 6.3

Ein Unternehmen will 50 Standorte mit einem neuen WLAN-Profil und neuer Segmentierung versorgen. Heute läuft alles per CLI pro Gerät. Zur Wahl steht ein controllerbasiertes Netz (z. B. Catalyst Center mit SD-Access).

1. Vergleiche in einer Tabelle: Konfiguration, Management-Ebene, Control Plane, Konsistenz, Fehlersuche/Assurance, Skalierung, Einarbeitung.
2. Erkläre Underlay, Overlay, Fabric.
3. Was heißt Trennung von Control Plane und Data Plane? Nenne Nord- und Südschnittstellen und je ein Protokoll/Beispiel.
4. Ordne zu: REST-API an den Controller, NETCONF zum Switch, CLI per SSH, OpenFlow.

<details><summary>Musterantwort</summary>

1. Traditionell: Konfiguration pro Gerät (CLI), Management pro Gerät/SNMP, verteilte Control Plane (jedes Gerät hat Routing/STP), Abweichungen häufig, Fehlersuche manuell. Controllerbasiert: Konfiguration über Absicht/Richtlinien zentral, Management per API/GUI, Control Plane teils zentralisiert (Policy) bzw. Fabric-Control (LISP), konsistent, Assurance mit Telemetrie, skaliert über Vorlagen, braucht neue Fähigkeiten.
2. Underlay: physisches/IP-Transportnetz (Routing, Konnektivität). Overlay: logisches Netz darüber (VXLAN-Tunnel, Segmentierung). Fabric: Underlay + Overlay als einheitliches, automatisch verwaltetes Netz.
3. Control Plane entscheidet (Wege, Policy), Data Plane leitet Pakete weiter. In SDN sitzt die Entscheidungslogik zentral im Controller, die Geräte leiten nur weiter. Nordschnittstelle (Controller ↔ Anwendungen/Orchestrierung): REST-API. Südschnittstelle (Controller ↔ Geräte): NETCONF, RESTCONF, SNMP, CLI, OpenFlow.
4. REST-API an den Controller = Northbound. NETCONF zum Switch, CLI per SSH und OpenFlow = Southbound.

</details>

## Fall 8: Künstliche Intelligenz im Netzbetrieb

**CCNA-Ziele:** 6.4

Die Betriebsleitung fragt: „Wo kann uns KI im Netzbetrieb helfen, und wo nicht?“

1. Unterscheide prädiktive KI/Machine Learning und generative KI. Gib je zwei Anwendungsfälle im Netzbetrieb.
2. Nenne Chancen und Grenzen/Risiken (Datenqualität, Halluzinationen, Datenschutz, Nachvollziehbarkeit).
3. Eine generative KI schlägt dir eine Konfiguration für ein neues VLAN samt ACL vor. Wie gehst du damit um?

<details><summary>Musterantwort</summary>

1. Prädiktiv/ML: Muster erkennen und vorhersagen (Anomalieerkennung im Verkehr, Kapazitätsplanung, Ausfallvorhersage, Root-Cause-Analyse). Generativ: neue Inhalte erzeugen (Konfigurationsentwürfe, Skripte, Dokumentation, Erklärungen, Assistenten für Troubleshooting in natürlicher Sprache).
2. Chancen: schnellere Fehlereingrenzung, weniger Routinearbeit, bessere Prognosen. Grenzen: Ergebnisse nur so gut wie die Daten, Halluzinationen (plausible, aber falsche Befehle), vertrauliche Daten dürfen nicht unkontrolliert an externe Dienste, Entscheidungen schwer nachvollziehbar, Verantwortung bleibt beim Menschen.
3. Als Entwurf behandeln: Befehle gegen die Dokumentation prüfen, im Lab testen, Änderung per Review und Wartungsfenster einspielen, Rollback bereithalten, keine Zugangsdaten oder interne Details in öffentliche Dienste geben.

</details>

## Fall 9: Topologie wählen: 2-Tier, 3-Tier, Spine-Leaf, SOHO

**CCNA-Ziele:** 1.2, 1.1

Drei Szenarien: (A) ein Büro mit 12 Personen, (B) ein Campus mit sechs Gebäuden und 3000 Endgeräten, (C) ein Rechenzentrum mit viel Server-zu-Server-Verkehr.

1. Welche Architektur passt zu A, B, C und warum (SOHO, 2-Tier, 3-Tier, Spine-Leaf)?
2. Welche Rolle haben Router, Layer-2-/Layer-3-Switches, Firewall/IPS, AP, WLC in B?
3. Wie unterscheiden sich On-Premises und Cloud beim WAN-Design?

<details><summary>Musterantwort</summary>

1. A: SOHO (ein Router/Firewall mit integrierter Switch- und WLAN-Funktion, Internet). B: 3-Tier oder 2-Tier mit Collapsed Core je Gebäude/Verteiler, je nach Größe; bei sechs Gebäuden und 3000 Endgeräten typisch 3-Tier (Access, Distribution, Core) für Skalierung und Fehlerbegrenzung. C: Spine-Leaf, weil jeder Leaf mit jedem Spine verbunden ist: gleichmäßige Latenz, viel Ost-West-Bandbreite, einfache Erweiterung.
2. Access-Switches (L2, PoE) verbinden Endgeräte und APs; Distribution/Core (L3) routen zwischen VLANs und Gebäuden; Router/Firewall am Netzübergang, IPS inspiziert, WLC steuert die APs.
3. On-Prem: Hardware und Betrieb liegen im eigenen Haus, Anbindung über WAN-Router, MPLS/VPN. Cloud: Dienste liegen beim Anbieter, das Internet bzw. Direktanbindungen werden kritisch (Redundanz, Bandbreite, Sicherheit, SD-WAN).

</details>

