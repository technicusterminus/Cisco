# Lab 22 – Security-Szenarien: REST-API, Threat Defense, Endpoint, NGFW, TrustSec/MACsec

**Dauer:** ca. 2,5 h · **Art:** Fallstudien ohne CML (Papier-/Denkaufgaben mit Lösungsschlüssel)

Szenarien zu den Security-Themen, die sich nicht sinnvoll im CML nachstellen lassen. Du bewertest Entwürfe, liest Konfigurationen und begründest Entscheidungen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::5.3` | REST-API-Sicherheit | 22 |
| `Ziel::5.4.a` | Threat Defense | 29 |
| `Ziel::5.4.b` | Endpoint Security | 29 |
| `Ziel::5.4.c` | Next-Generation Firewall | 22 |
| `Ziel::5.4.d` | TrustSec und MACsec | 28 |

Warum ohne CML? SD-WAN, SD-Access, Hypervisor und Next-Generation-Firewalls brauchen Controller, Lizenzen oder Hardware, die sich in einer kostenfreien Lab-Umgebung nicht sinnvoll nachbauen lassen. Du übst hier stattdessen das, was die Prüfung fragt: Komponenten zuordnen, Entwurf begründen, Konfigurationen und Ausgaben lesen, Fehler im Entwurf finden.

## Fall 1: Ein API-Skript im Git-Repository

**Szenario.** Ein Teamkollege veröffentlicht ein Python-Skript, das mit `requests.get(url, auth=('admin','Lab#2026!'), verify=False)` einen Controller abfragt. Das Skript liegt in einem Team-Repository.

**Aufgaben**

1. Nenne fünf Sicherheitsmängel.
2. Wie sähe eine bessere Variante aus (Secrets, TLS-Prüfung, Token, Rechte)?
3. Welcher HTTP-Statuscode erscheint bei fehlendem/ungültigem Token (401) und bei fehlender Berechtigung (403)?

<details><summary>Lösungsschlüssel</summary>

1. Klartext-Zugangsdaten im Code/Repository, `verify=False` (keine Zertifikatsprüfung → Man-in-the-Middle), Admin-Konto statt Least Privilege, Basic Auth bei jedem Aufruf (Passwort ständig unterwegs), keine Fehler-/Timeout-Behandlung und kein Logging-Schutz (Geheimnisse landen in Logs).
2. Secrets per Umgebungsvariable oder Secret Store/Vault, Zertifikat prüfen (`verify=<CA-Bundle>`), Token holen und wiederverwenden, Service-Account mit minimaler Rolle (read-only, wo möglich), Timeouts und Rate-Limit beachten.
3. 401 = nicht authentifiziert, 403 = authentifiziert, aber nicht berechtigt.

</details>

## Fall 2: REST-API-Authentifizierungsverfahren vergleichen

**Szenario.** Für eine neue Automationsplattform stehen Basic Auth, API-Key, Bearer-Token (JWT/OAuth 2.0) und mTLS zur Wahl.

**Aufgaben**

1. Ordne zu: Wer hält welches Geheimnis, wie lange gültig, wie widerrufbar?
2. Welches Verfahren eignet sich für Dienst-zu-Dienst, welches für Nutzer mit Delegation (OAuth-Scopes)?
3. Wozu dienen Rate-Limiting, Eingabevalidierung und Audit-Logging an einer API?

<details><summary>Lösungsschlüssel</summary>

1. Basic: Passwort bei jedem Aufruf (nur über TLS, schwer widerrufbar). API-Key: statisches Geheimnis, einfach, ohne Ablauf (Rotation nötig). Bearer-Token: kurzlebig, Scopes/Claims, widerrufbar. mTLS: Client-Zertifikat, starke Bindung.
2. Dienst-zu-Dienst: OAuth2 Client Credentials oder mTLS. Nutzerdelegation: OAuth2 Authorization Code mit Scopes.
3. Rate-Limiting schützt vor Missbrauch/Brute Force (429), Validierung verhindert Injection/Fehler (400), Audit-Logging macht Zugriffe nachvollziehbar.

</details>

## Fall 3: Bedrohungsabwehr im Netz (Threat Defense)

**Szenario.** Ein Mitarbeiter öffnet einen präparierten Link. Ein Download-Trojaner startet, kontaktiert einen Command-and-Control-Server und scannt das interne Netz.

**Aufgaben**

1. Welche Schutzschichten greifen an welcher Stelle: DNS-Security, Web-/URL-Filter, IPS, Datei-Reputation/Sandboxing, Segmentierung, Endpoint-Schutz?
2. Was unterscheidet IDS und IPS (Inline, Aktion Block/Drop)? Wie funktionieren signaturbasierte und verhaltensbasierte Erkennung?
3. Wie hilft Threat Intelligence (Talos) und die Korrelation mehrerer Quellen (XDR)?

<details><summary>Lösungsschlüssel</summary>

1. DNS-Security blockt die C2-Domain, URL-Filter/Reputation den Downloadlink, Datei-Sandbox erkennt Schadcode, IPS erkennt Exploit-/Scan-Muster, Segmentierung begrenzt laterale Bewegung, Endpoint-Schutz stoppt den Prozess.
2. IDS beobachtet (Out-of-Band, Alarm), IPS sitzt inline und kann verwerfen. Signaturen erkennen bekannte Muster, Verhalten/Heuristik auffällige Abweichungen.
3. Threat Intelligence liefert Reputationsdaten und Signaturen, XDR korreliert Ereignisse von Endpunkt, Netz, E-Mail und Cloud zu einem Vorfall.

</details>

## Fall 4: Endpoint Security und Zugangskontrolle

**Szenario.** Laptops sollen nur ins Netz, wenn sie einen aktuellen Virenschutz und Patchstand haben. Gäste dürfen nur ins Internet.

**Aufgaben**

1. Welche Rolle haben 802.1X, ISE, Posture und MDM? Welcher Ablauf entsteht von der Anmeldung bis zur Zuweisung von VLAN/SGT/dACL?
2. Was leistet ein EDR gegenüber klassischem Virenschutz (Verhaltensüberwachung, Rückwärts-Analyse, Isolation)?
3. Wie behandelst du Geräte ohne Supplicant (IoT, Drucker): MAB, Profiling?

<details><summary>Lösungsschlüssel</summary>

1. Endgerät (Supplicant) authentifiziert sich per 802.1X am Switch (Authenticator), der Switch fragt ISE (RADIUS). ISE prüft Identität und Posture (Compliance), MDM liefert den Gerätezustand. Ergebnis: VLAN, SGT oder dACL, bei Nichtkonformität Quarantäne/Remediation.
2. EDR überwacht Prozesse und Dateien kontinuierlich, speichert Telemetrie für nachträgliche Analyse und kann Geräte isolieren oder Prozesse stoppen. Klassischer AV prüft vor allem Signaturen.
3. MAB (MAC Authentication Bypass) mit Profiling (ISE erkennt Gerätetyp aus DHCP/CDP/LLDP) und Zuweisung einer eingeschränkten Policy.

</details>

## Fall 5: Next-Generation Firewall: Regelwerk lesen

**Szenario.** Eine Secure Firewall (FTD, vom FMC verwaltet) hat folgende Access-Control-Regeln in dieser Reihenfolge: (1) Block `Social-Media` (Anwendung), (2) Allow `Web-Browsing` mit IPS und Dateirichtlinie, (3) Allow `Any` zu `DNS`, (4) Default Action: Block.

**Aufgaben**

1. Wie wird ein HTTPS-Aufruf auf eine Social-Media-Seite behandelt, wenn SSL-Entschlüsselung aus ist, und wie, wenn sie aktiv ist? Warum ist Application Visibility ohne Entschlüsselung eingeschränkt?
2. Welche Funktionen unterscheiden eine NGFW von einer zustandsbehafteten Firewall (AVC, URL-Filter, IPS, Malware-Schutz, Identity)?
3. Welche Rolle spielen Prefilter-Regeln, NAT-Policy und Default Action in der Verarbeitungsreihenfolge?

<details><summary>Lösungsschlüssel</summary>

1. Ohne Entschlüsselung sieht die Firewall nur SNI/Zertifikat und IP, Anwendungserkennung ist begrenzt. Mit Entschlüsselung erkennt sie die Anwendung im Klartext und kann Regel 1 durchsetzen.
2. NGFW bewertet Anwendungen (nicht nur Ports), kennt Benutzeridentitäten, hat URL-Filter, IPS (Snort), Datei-/Malware-Schutz und optionales SSL-Inspect.
3. Prefilter filtert früh (Fastpath/Block ohne Inspektion), NAT-Policy übersetzt Adressen, danach greift die Access-Control-Policy von oben nach unten; die Default Action steht am Ende.

</details>

## Fall 6: TrustSec: SGT klassifizieren, verteilen, durchsetzen

**Szenario.** Zwei Switches (Access und Distribution) sollen Verkehr zwischen `Employees (SGT 10)` und `Servers (SGT 20)` per SGACL steuern. Ein Teil der Switches kann keine Inline-Tags.

**Aufgaben**

1. Beschreibe Classification (statisch, dynamisch über 802.1X/ISE), Propagation (Inline Tagging, SXP) und Enforcement (SGACL).
2. Warum nutzt man SXP (TCP 64999), und wo setzt man Enforcement sinnvoll (nah am Ziel)?
3. Lies die Konfiguration: `cts role-based sgt-map 10.1.1.10 sgt 20`, `cts role-based enforcement`, `cts sxp enable`. Was bewirkt jede Zeile?

<details><summary>Lösungsschlüssel</summary>

1. Classification: dem Verkehr eine SGT zuweisen (IP-SGT-Mapping statisch, VLAN-SGT, oder dynamisch per ISE-Autorisierung). Propagation: SGT wandert im Frame (Cisco-Metadata-Header, inline) oder per SXP als IP-SGT-Zuordnung. Enforcement: SGACL am Ziel prüft SGT-Paar (Quelle/Ziel).
2. SXP überträgt IP-SGT-Tabellen zu Geräten ohne Inline-Tagging (TCP 64999). Durchsetzung am Ziel-Switch/der Firewall nahe dem geschützten Server.
3. Erste Zeile: statische Zuordnung 10.1.1.10 → SGT 20. Zweite: globales SGACL-Enforcement einschalten. Dritte: SXP-Dienst aktivieren.

</details>

## Fall 7: MACsec und MKA zwischen zwei Switches

**Szenario.** Zwei Switches in getrennten Gebäuden sind über eine Dark-Fiber-Strecke verbunden. Der Verkehr soll auf Layer 2 verschlüsselt werden, ohne IPsec.

**Aufgaben**

1. Beschreibe MACsec (IEEE 802.1AE): Hop-by-Hop-Verschlüsselung, Integrität, Replay-Schutz, Overhead (SecTAG 16 + ICV 16 = 32 Byte), EtherType 0x88E5.
2. Wozu dient MKA (MACsec Key Agreement, 802.1X-2010)? Wie ist die Schlüsselhierarchie (CAK → SAK)?
3. Lies die Konfiguration: `key chain MKA macsec / key 01 / cryptographic-algorithm aes-128-cmac / key-string …`, `mka policy POL / macsec-cipher-suite gcm-aes-128`, `interface Gi1/0/1 / macsec / mka policy POL / mka pre-shared-key key-chain MKA`.
4. Wie vergleichst du MACsec und IPsec (Layer, Ende-zu-Ende vs. Hop-by-Hop, Overhead, Hardwareunterstützung)?

<details><summary>Lösungsschlüssel</summary>

1. MACsec verschlüsselt und authentisiert Ethernet-Frames zwischen direkt verbundenen Geräten, mit Replay-Schutz. Overhead 32 Byte (SecTAG + ICV), EtherType 0x88E5.
2. MKA verhandelt zwischen den Peers einen Sitzungsschlüssel (SAK) aus dem Connectivity Association Key (CAK, hier per Pre-Shared Key oder über 802.1X/EAP). Der SAK wird regelmäßig erneuert.
3. Der Key Chain trägt den CAK (CMAC-AES-128), die MKA-Policy legt GCM-AES-128 als Cipher fest, am Interface wird MACsec aktiviert und der Pre-Shared Key verknüpft.
4. MACsec arbeitet auf Layer 2, schützt nur den Link (Hop-by-Hop) und läuft in der Hardware mit Line-Rate. IPsec schützt Ende-zu-Ende über Layer 3, hat größeren Overhead und braucht meist Crypto-Engines.

</details>

## Fall 8: Defense in Depth: Entwurf für ein Rechenzentrum

**Szenario.** Ein Rechenzentrum mit Webserver, Anwendungsserver und Datenbank soll gegen externe und interne Angriffe geschützt werden.

**Aufgaben**

1. Schlage eine Segmentierung vor (Zonen, VRFs, SGTs) und platziere NGFW, IPS, WAF, Endpoint-Schutz.
2. Wie schützt du die Verwaltungsebene (AAA, MFA, Jump Host, Out-of-Band-Netz)?
3. Welche Protokollierung/Telemetrie brauchst du für die Erkennung (Syslog, NetFlow, Endpoint-Telemetrie, SIEM)?

<details><summary>Lösungsschlüssel</summary>

1. Zonen: DMZ (Web), Application, Database, Management, getrennt per VRF/SGT. NGFW/IPS zwischen den Zonen, WAF vor dem Webserver, EDR auf den Servern, Mikrosegmentierung per SGT/ACL.
2. AAA (TACACS+), MFA für Administratoren, Jump Host, Out-of-Band-Managementnetz, Least Privilege und Command Authorization.
3. Syslog und NetFlow (Netz), Endpoint-Telemetrie, zentrale Korrelation im SIEM/XDR mit definierten Alarmierungswegen.

</details>

