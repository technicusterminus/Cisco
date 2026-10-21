# Lab 22 – Security-Szenarien: REST-API, Threat Defense, Endpoint, NGFW, TrustSec/MACsec

**Dauer:** ca. 2,5 h · **Art:** Fallstudien ohne CML (Papier-/Denkaufgaben mit Lösungsschlüssel)

Szenarien zu den Security-Themen, die sich nicht sinnvoll im CML nachstellen lassen. Du bewertest Entwürfe, liest Konfigurationen und begründest Entscheidungen.

**Lernziele:** Nach diesen Fällen kannst du …

- REST-Zugriffe sicher gestalten: Tokens, TLS und keine Passwörter im Code.
- Threat Defense, Endpoint Security und NGFW einordnen und ihre Aufgaben unterscheiden.
- TrustSec (SGT klassifizieren, verteilen, durchsetzen) und MACsec mit MKA erklären.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::5.3` | REST-API-Sicherheit | 22 |
| `Ziel::5.4.a` | Threat Defense | 29 |
| `Ziel::5.4.b` | Endpoint Security | 29 |
| `Ziel::5.4.c` | Next-Generation Firewall | 22 |
| `Ziel::5.4.d` | TrustSec und MACsec | 28 |

Warum ohne CML? Threat Defense, Endpoint-Schutz, Next-Generation-Firewalls und TrustSec brauchen ISE, Firewalls, Lizenzen oder Hardware, die sich in einer kostenfreien Lab-Umgebung nicht sinnvoll nachbauen lassen. Du übst hier stattdessen das, was die Prüfung fragt: Komponenten zuordnen, Entwürfe begründen, Konfigurationen lesen und Schwachstellen finden.

## Fall 1: Ein API-Skript im Git-Repository

**Szenario.** Ein Teamkollege veröffentlicht ein Python-Skript, das mit `requests.get(url, auth=('admin','Lab#2026!'), verify=False)` einen Controller abfragt. Das Skript liegt in einem Team-Repository.

**Aufgaben**

1. Nenne fünf Sicherheitsmängel.
2. Wie sähe eine bessere Variante aus (Secrets, TLS-Prüfung, Token, Rechte)?
3. Welcher HTTP-Statuscode erscheint bei fehlendem/ungültigem Token (401) und bei fehlender Berechtigung (403)?

<details><summary>Lösungsschlüssel</summary>

1. **Passwort im Code, keine Zertifikatsprüfung, Admin-Konto, Basic Auth bei jedem Aufruf, kein Schutz der Logs.** Das Passwort steht für jeden mit Repo-Zugriff lesbar und bleibt in der Git-Historie. `verify=False` öffnet die Tür für Man-in-the-Middle. Ein Admin-Konto verletzt Least Privilege. Basic Auth schickt das Passwort bei jedem Aufruf mit. Ohne Fehler- und Timeout-Behandlung landen Geheimnisse schnell in Logs.
2. **Secrets aus dem Tresor, Zertifikat prüfen, Token nutzen, minimale Rechte.** Zugangsdaten kommen aus Umgebungsvariablen oder einem Secret Store wie Vault. `verify` zeigt auf das CA-Bundle. Das Skript holt einmal einen Token und verwendet ihn wieder. Ein Service-Account mit Read-only-Rolle reicht für Abfragen. Timeouts und Rate-Limits gehören dazu.
3. **401 bei fehlendem oder ungültigem Token, 403 bei fehlender Berechtigung.** 401 heißt: Wer bist du? 403 heißt: Ich weiß, wer du bist, aber das darfst du nicht.

</details>

## Fall 2: REST-API-Authentifizierungsverfahren vergleichen

**Szenario.** Für eine neue Automationsplattform stehen Basic Auth, API-Key, Bearer-Token (JWT/OAuth 2.0) und mTLS zur Wahl.

**Aufgaben**

1. Ordne zu: Wer hält welches Geheimnis, wie lange gültig, wie widerrufbar?
2. Welches Verfahren eignet sich für Dienst-zu-Dienst, welches für Nutzer mit Delegation (OAuth-Scopes)?
3. Wozu dienen Rate-Limiting, Eingabevalidierung und Audit-Logging an einer API?

<details><summary>Lösungsschlüssel</summary>

1. **Basic schickt das Passwort jedes Mal, API-Key ist statisch, Bearer-Token ist kurzlebig, mTLS bindet an ein Zertifikat.** Basic Auth ist nur über TLS vertretbar und schwer zu widerrufen, ohne das Passwort zu ändern. Ein API-Key läuft nicht ab und muss rotiert werden. Ein Bearer-Token hat Scopes, läuft ab und lässt sich widerrufen. Bei mTLS hält der Client ein Zertifikat, das ist die stärkste Bindung.
2. **Dienst-zu-Dienst: OAuth 2.0 Client Credentials oder mTLS. Nutzer mit Delegation: OAuth 2.0 Authorization Code mit Scopes.** Beim Dienst gibt es keinen Menschen, der zustimmt. Beim Nutzer erlaubt der Scope, nur einen Teil seiner Rechte weiterzugeben.
3. **Missbrauch bremsen, Fehleingaben abfangen, Zugriffe nachvollziehen.** Rate-Limiting stoppt Brute Force und Überlast (Antwort 429). Eingabevalidierung verhindert Injection und Fehler (400). Audit-Logging zeigt im Nachhinein, wer was getan hat.

</details>

## Fall 3: Bedrohungsabwehr im Netz (Threat Defense)

**Szenario.** Ein Mitarbeiter öffnet einen präparierten Link. Ein Download-Trojaner startet, kontaktiert einen Command-and-Control-Server und scannt das interne Netz.

**Aufgaben**

1. Welche Schutzschichten greifen an welcher Stelle: DNS-Security, Web-/URL-Filter, IPS, Datei-Reputation/Sandboxing, Segmentierung, Endpoint-Schutz?
2. Was unterscheidet IDS und IPS (Inline, Aktion Block/Drop)? Wie funktionieren signaturbasierte und verhaltensbasierte Erkennung?
3. Wie hilft Threat Intelligence (Talos) und die Korrelation mehrerer Quellen (XDR)?

<details><summary>Lösungsschlüssel</summary>

1. **Jede Schicht stoppt einen anderen Schritt des Angriffs.** Der URL-Filter blockt den Downloadlink, die Datei-Sandbox erkennt den Trojaner. DNS-Security verhindert, dass er seine C2-Domain auflöst. Das IPS erkennt Exploits und den Scan. Segmentierung begrenzt die Ausbreitung, und der Endpoint-Schutz beendet den Prozess.
2. **Das IDS meldet nur, das IPS sitzt inline und verwirft.** Das IDS sieht eine Kopie des Verkehrs, das IPS liegt im Datenweg. Signaturen erkennen bekannte Muster, verhaltensbasierte Erkennung fällt bei Abweichungen vom Normalen an, auch bei neuen Angriffen.
3. **Threat Intelligence liefert das Wissen, XDR setzt die Einzelteile zusammen.** Talos liefert Reputationsdaten und Signaturen. XDR verbindet Ereignisse von Endpunkt, Netz, E-Mail und Cloud zu einem einzigen Vorfall.

</details>

## Fall 4: Endpoint Security und Zugangskontrolle

**Szenario.** Laptops sollen nur ins Netz, wenn sie einen aktuellen Virenschutz und Patchstand haben. Gäste dürfen nur ins Internet.

**Aufgaben**

1. Welche Rolle haben 802.1X, ISE, Posture und MDM? Welcher Ablauf entsteht von der Anmeldung bis zur Zuweisung von VLAN/SGT/dACL?
2. Was leistet ein EDR gegenüber klassischem Virenschutz (Verhaltensüberwachung, Rückwärts-Analyse, Isolation)?
3. Wie behandelst du Geräte ohne Supplicant (IoT, Drucker): MAB, Profiling?

<details><summary>Lösungsschlüssel</summary>

1. **Der Laptop meldet sich per 802.1X am Switch an, ISE prüft Identität und Zustand und schickt VLAN, SGT oder dACL zurück.** Der Supplicant auf dem Laptop spricht mit dem Switch (Authenticator), der Switch fragt ISE per RADIUS. ISE prüft die Posture, MDM liefert dazu den Gerätezustand. Ist der Laptop nicht konform, landet er in Quarantäne und bekommt nur Zugang zur Aktualisierung.
2. **EDR beobachtet laufend, speichert Telemetrie und kann eingreifen.** Klassischer Virenschutz prüft vor allem Signaturen. EDR überwacht Prozesse und Dateien, erlaubt die Analyse im Nachhinein und kann ein Gerät isolieren oder einen Prozess stoppen.
3. **MAB mit Profiling und eingeschränkter Policy.** MAC Authentication Bypass nutzt die MAC-Adresse als Identität. ISE erkennt den Gerätetyp aus DHCP, CDP oder LLDP und weist eine passende, enge Policy zu, weil eine MAC leicht zu fälschen ist.

</details>

## Fall 5: Next-Generation Firewall: Regelwerk lesen

**Szenario.** Eine Secure Firewall (FTD, vom FMC verwaltet) hat folgende Access-Control-Regeln in dieser Reihenfolge: (1) Block `Social-Media` (Anwendung), (2) Allow `Web-Browsing` mit IPS und Dateirichtlinie, (3) Allow `Any` zu `DNS`, (4) Default Action: Block.

**Aufgaben**

1. Wie wird ein HTTPS-Aufruf auf eine Social-Media-Seite behandelt, wenn SSL-Entschlüsselung aus ist, und wie, wenn sie aktiv ist? Warum ist Application Visibility ohne Entschlüsselung eingeschränkt?
2. Welche Funktionen unterscheiden eine NGFW von einer zustandsbehafteten Firewall (AVC, URL-Filter, IPS, Malware-Schutz, Identity)?
3. Welche Rolle spielen Prefilter-Regeln, NAT-Policy und Default Action in der Verarbeitungsreihenfolge?

<details><summary>Lösungsschlüssel</summary>

1. **Ohne Entschlüsselung oft nur über SNI und Zertifikat erkennbar, mit Entschlüsselung sicher geblockt.** Ohne SSL-Inspektion sieht die Firewall nur IP-Adressen, den Servernamen (SNI) und das Zertifikat. Das reicht für viele bekannte Seiten, aber nicht für Details innerhalb einer Anwendung. Mit Entschlüsselung erkennt sie die Anwendung im Klartext und setzt Regel 1 zuverlässig durch.
2. **Die NGFW versteht Anwendungen und Benutzer, nicht nur Ports.** Dazu kommen URL-Filter, IPS (Snort), Datei- und Malware-Schutz und optional SSL-Inspektion. Eine zustandsbehaftete Firewall prüft nur Adressen, Ports und Verbindungszustand.
3. **Prefilter zuerst, dann NAT, dann die Access-Control-Regeln von oben nach unten, zuletzt die Default Action.** Der Prefilter entscheidet früh und ohne tiefe Inspektion, etwa für Tunnel oder Fastpath. Die Default Action greift nur, wenn keine Regel passt.

</details>

## Fall 6: TrustSec: SGT klassifizieren, verteilen, durchsetzen

**Szenario.** Zwei Switches (Access und Distribution) sollen Verkehr zwischen `Employees (SGT 10)` und `Servers (SGT 20)` per SGACL steuern. Ein Teil der Switches kann keine Inline-Tags.

**Aufgaben**

1. Beschreibe Classification (statisch, dynamisch über 802.1X/ISE), Propagation (Inline Tagging, SXP) und Enforcement (SGACL).
2. Warum nutzt man SXP (TCP 64999), und wo setzt man Enforcement sinnvoll (nah am Ziel)?
3. Lies die Konfiguration: `cts role-based sgt-map 10.1.1.10 sgt 20`, `cts role-based enforcement`, `cts sxp enable`. Was bewirkt jede Zeile?

<details><summary>Lösungsschlüssel</summary>

1. **Classification vergibt die SGT, Propagation transportiert sie, Enforcement prüft sie.** Die SGT entsteht statisch (IP-SGT, VLAN-SGT) oder dynamisch durch ISE nach der Anmeldung. Sie reist inline im Frame (Cisco Metadata) oder per SXP als IP-SGT-Zuordnung. Am Ziel prüft eine SGACL das Paar aus Quell- und Ziel-SGT.
2. **SXP überbrückt Geräte ohne Inline-Tagging, durchgesetzt wird nah am Ziel.** SXP schickt IP-SGT-Tabellen per TCP 64999 an ein Gerät, das taggen oder durchsetzen kann. Nah am geschützten Server kennt der Switch die Ziel-SGT, deshalb liegt Enforcement dort.
3. **Statische Zuordnung, Enforcement an, SXP an.** `cts role-based sgt-map 10.1.1.10 sgt 20` ordnet die Adresse 10.1.1.10 der SGT 20 zu. `cts role-based enforcement` schaltet die SGACL-Prüfung global ein. `cts sxp enable` startet den SXP-Dienst.

</details>

## Fall 7: MACsec und MKA zwischen zwei Switches

**Szenario.** Zwei Switches in getrennten Gebäuden sind über eine Dark-Fiber-Strecke verbunden. Der Verkehr soll auf Layer 2 verschlüsselt werden, ohne IPsec.

**Aufgaben**

1. Beschreibe MACsec (IEEE 802.1AE): Hop-by-Hop-Verschlüsselung, Integrität, Replay-Schutz, Overhead (SecTAG + ICV, bis zu 32 Byte), EtherType 0x88E5.
2. Wozu dient MKA (MACsec Key Agreement, 802.1X-2010)? Wie ist die Schlüsselhierarchie (CAK → SAK)?
3. Lies die Konfiguration: `key chain MKA macsec / key 01 / cryptographic-algorithm aes-128-cmac / key-string …`, `mka policy POL / macsec-cipher-suite gcm-aes-128`, `interface Gi1/0/1 / macsec / mka policy POL / mka pre-shared-key key-chain MKA`.
4. Wie vergleichst du MACsec und IPsec (Layer, Ende-zu-Ende vs. Hop-by-Hop, Overhead, Hardwareunterstützung)?

<details><summary>Lösungsschlüssel</summary>

1. **MACsec verschlüsselt und schützt Ethernet-Frames von Link zu Link.** Es sichert Vertraulichkeit, Integrität und schützt vor Replay. Der Overhead beträgt bis zu 32 Byte: SecTAG 8 bzw. 16 Byte (mit SCI) plus 16 Byte ICV. Der EtherType ist 0x88E5.
2. **MKA leitet aus dem CAK den Sitzungsschlüssel SAK ab und erneuert ihn regelmäßig.** Der Connectivity Association Key kommt per Pre-Shared Key oder aus 802.1X/EAP. Mit dem SAK werden die Frames tatsächlich verschlüsselt.
3. **Key Chain = CAK, MKA-Policy = Cipher, Interface = Aktivierung.** Die Key Chain trägt den CAK mit AES-128-CMAC. Die MKA-Policy legt GCM-AES-128 für die Daten fest. Am Interface schaltet `macsec` die Verschlüsselung ein, und die Key Chain wird als Pre-Shared Key verknüpft.
4. **MACsec: Layer 2, Hop-by-Hop, Line-Rate in Hardware. IPsec: Layer 3, Ende-zu-Ende, mehr Overhead.** MACsec schützt nur den einzelnen Link, dafür ohne Leistungsverlust. IPsec schützt über beliebig viele Router hinweg, braucht aber mehr Overhead und meist eine Crypto-Engine.

</details>

## Fall 8: Defense in Depth: Entwurf für ein Rechenzentrum

**Szenario.** Ein Rechenzentrum mit Webserver, Anwendungsserver und Datenbank soll gegen externe und interne Angriffe geschützt werden.

**Aufgaben**

1. Schlage eine Segmentierung vor (Zonen, VRFs, SGTs) und platziere NGFW, IPS, WAF, Endpoint-Schutz.
2. Wie schützt du die Verwaltungsebene (AAA, MFA, Jump Host, Out-of-Band-Netz)?
3. Welche Protokollierung/Telemetrie brauchst du für die Erkennung (Syslog, NetFlow, Endpoint-Telemetrie, SIEM)?

<details><summary>Lösungsschlüssel</summary>

1. **Zonen für Web, Anwendung, Datenbank und Management, dazwischen NGFW mit IPS.** Die Zonen trennst du per VRF oder SGT. Die WAF steht vor dem Webserver, EDR läuft auf allen Servern. Innerhalb einer Zone begrenzt Mikrosegmentierung per SGT oder ACL die Ausbreitung.
2. **AAA mit MFA, Jump Host und eigenes Out-of-Band-Netz.** Administratoren melden sich per TACACS+ mit zweitem Faktor an und arbeiten nur über einen Jump Host. Least Privilege und Command Authorization begrenzen, was ein gestohlenes Konto anrichten kann.
3. **Syslog, NetFlow und Endpoint-Telemetrie, zusammengeführt im SIEM oder XDR.** Erst die Korrelation macht aus Einzelmeldungen einen erkannten Angriff. Dazu gehören festgelegte Alarmierungswege.

</details>

