# CCNA 200-301 v1.1 – Packet-Tracer-Labs

Hands-on-Übungen zu **allen 53 Prüfungszielen** der CCNA 200-301 v1.1 (6 Prüfungsbereiche). Jedes Lab hat drei Teile: **Bauen** (Aufgaben Schritt für Schritt), **Reparieren** (fertige Konfiguration mit eingebauten Fehlern und Tickets) und **Üben** (Transferfragen mit aufklappbaren Antworten). Pro Prüfungsziel gibt es eine Zuordnung zu Aufgaben und Lösungen in **[ZIELE.md](ZIELE.md)**.

**Inhalt:** 26 Packet-Tracer-Labs (95 eingebaute Fehler zum Reparieren), ein Python-/JSON-/REST-Paket mit automatischen Tests (Lab 27) und ein Paket Konzept-Fallstudien (Lab 28).

## Arbeiten mit den Dateien

Packet-Tracer-Dateien (`.pkt`) liegen nicht bei: Ich kann sie ohne Packet Tracer weder erzeugen noch prüfen. Dafür beschreibt jedes Lab Geräte, Modelle, Ports und Kabel in Tabellen und liefert die Konfigurationen als Textdateien. Der Aufbau dauert pro Lab etwa 5 bis 10 Minuten; speichere ihn danach als eigene `.pkt`.

1. **Topologie bauen.** Geräte laut Tabelle „Geräte“ platzieren (Modelle wie angegeben), Kabel laut Tabelle „Verkabelung“ **von Hand** wählen (Straight-Through, Cross-Over; das trainiert Ziel 1.3) und auf die genannten Ports stecken.
2. **Ausgangszustand laden.** Pro Gerät: *CLI*-Tab → `enable` → `configure terminal`, dann den Inhalt von `build/<Gerät>.txt` einfügen. Lange Dateien in Blöcken einfügen, falls Zeilen verloren gehen, und danach `end` und `write memory`.
3. **Endgeräte** (PC, Laptop, Server) setzen: *Desktop* → *IP Configuration* mit den Werten aus der Tabelle „Adressplan“.
4. **Teil A** bearbeiten: Du ergänzt die Konfiguration selbst. Vergleiche danach mit `solutions/<Gerät>.cfg`.
5. **Teil B (Reparieren).** Alle Geräte zurücksetzen (`erase startup-config`, `reload`, oder Geräte neu platzieren), dann `repair/<Gerät>.txt` einfügen und die Endgeräte laut Tabelle im README einstellen. Die Tickets abarbeiten, die Auflösung steht in `solutions/FAULTS.md`.
6. **Teil C** (Transferfragen) erst selbst beantworten, dann aufklappen.

Voraussetzung: Cisco Packet Tracer 8.2 oder neuer (kostenlos über Cisco Networking Academy).

## Übersicht

| Lab | Thema | Ziele | Geräte | Fehler/Analysen | Dauer | Niveau |
|---|---|---|---|---|---|---|
| [01](01-Komponenten-Topologien-Kabel/) | Netzwerkkomponenten, Topologien und Verkabelung | 1.1, 1.2, 1.3 | 8 | 0 | 60 min | leicht |
| [02](02-Schnittstellenprobleme/) | Schnittstellen- und Kabelprobleme (Duplex, Speed, Fehler) | 1.4, 1.3 | 5 | 4 | 60 min | leicht |
| [03](03-MAC-Tabelle-Switching/) | Switching-Konzepte: MAC-Lernen, Aging, Flooding | 1.13, 1.1 | 6 | 3 | 60 min | leicht |
| [04](04-TCP-UDP/) | TCP und UDP: Verbindungsaufbau, Ports, Dienste | 1.5, 5.6 | 5 | 3 | 75 min | leicht |
| [05](05-IPv4-VLSM/) | IPv4-Adressierung, VLSM und private Bereiche | 1.6, 1.7, 1.10, 3.3 | 5 | 4 | 90 min | mittel |
| [06](06-IPv6/) | IPv6: Adressen, Adresstypen und EUI-64 | 1.8, 1.9, 3.3 | 4 | 4 | 90 min | mittel |
| [07](07-VLAN-InterVLAN/) | VLANs, Trunks und Inter-VLAN-Routing | 2.1, 2.2 | 7 | 5 | 90 min | mittel |
| [08](08-Trunking-DTP-CDP-LLDP/) | Trunks, Native VLAN, DTP und CDP/LLDP | 2.2, 2.3, 2.1 | 5 | 4 | 75 min | mittel |
| [09](09-EtherChannel-LACP/) | EtherChannel mit LACP | 2.4, 2.2 | 4 | 4 | 75 min | mittel |
| [10](10-RapidPVST-Schutz/) | Rapid PVST+: Root Bridge, Port-Rollen und Schutzfunktionen | 2.5 | 5 | 4 | 90 min | mittel |
| [11](11-Wireless-Architektur-WLC-AP/) | Wireless-Architekturen: WLC, Lightweight-AP und DHCP | 2.6, 2.7, 1.11 | 5 | 3 | 75 min | mittel |
| [12](12-WLAN-GUI-WPA2/) | WLAN per GUI: SSID, Kanäle, WPA2-PSK und Fehleranalyse | 1.11, 2.9, 5.9, 5.10 | 4 | 5 | 75 min | leicht |
| [13](13-Geraetezugriff-SSH/) | Gerätezugriff: lokale Passwörter, Passwortrichtlinie und SSH | 5.3, 5.4, 4.8, 2.8 | 3 | 4 | 75 min | leicht |
| [14](14-Routing-Tabelle-Longest-Match/) | Routing-Tabelle lesen und die Weiterleitungsentscheidung vorhersagen | 3.1, 3.2, 3.3 | 4 | 4 | 75 min | mittel |
| [15](15-Statisches-Routing-Floating/) | Statisches Routing: Default, Netz, Host, Floating (IPv4 und IPv6) | 3.3, 3.1 | 4 | 4 | 90 min | mittel |
| [16](16-OSPFv2-SingleArea/) | OSPFv2 Single Area: Nachbarn, DR/BDR, Router-ID | 3.4, 3.1 | 8 | 5 | 90 min | mittel |
| [17](17-FHRP-HSRP/) | First Hop Redundancy: HSRP mit Preempt und Tracking | 3.5 | 6 | 4 | 75 min | mittel |
| [18](18-DHCP-DNS-Relay/) | DHCP (Router, Server, Relay) und DNS | 4.3, 4.6, 1.10 | 7 | 4 | 90 min | mittel |
| [19](19-NAT-PAT/) | Inside Source NAT: statisch, Pool und PAT | 4.1 | 6 | 4 | 75 min | mittel |
| [20](20-NTP-Syslog-SNMP/) | NTP, Syslog und SNMP | 4.2, 4.4, 4.5 | 5 | 4 | 75 min | mittel |
| [21](21-TFTP-FTP/) | TFTP und FTP: Konfigurations- und Image-Sicherung | 4.9, 1.5 | 4 | 3 | 60 min | leicht |
| [22](22-QoS-MQC/) | QoS: Klassifizierung, Markierung, Queuing, Policing und Shaping | 4.7 | 4 | 3 | 90 min | schwer |
| [23](23-ACL/) | Access Control Lists: Standard, Extended, Named | 5.6, 2.8 | 6 | 5 | 90 min | mittel |
| [24](24-Layer2-Security/) | Layer-2-Sicherheit: Port Security, DHCP Snooping, DAI | 5.7 | 5 | 4 | 90 min | mittel |
| [25](25-IPsec-Site-to-Site/) | IPsec Site-to-Site-VPN | 5.5 | 5 | 5 | 90 min | schwer |
| [26](26-AAA-RADIUS/) | AAA: Authentisierung mit RADIUS und lokalem Fallback | 5.8, 2.8, 5.3 | 4 | 4 | 75 min | mittel |
| [27](27-Automation-JSON-REST) | Automatisierung: JSON, REST, Ansible/Terraform (lokal, mit Tests) | 6.5, 6.6, 6.7 | – | – | – | – |
| [28](28-Konzept-Fallstudien.md) | Konzept-Fallstudien: Virtualisierung, Security, Automatisierung, Controller, KI | 1.1, 1.2, 1.12, 2.8, 4.8, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4 | – | – | – | – |

## Abdeckung nach Prüfungsziel

Die komplette Tabelle mit Links zu Aufgaben und Lösungen steht in [ZIELE.md](ZIELE.md).

| Bereich | Ziele | Labs |
|---|---|---|
| 1 – Network Fundamentals (20 %) | 1.1 bis 1.13 | 01, 02, 03, 04, 05, 06, 11, 12, 18, 21, 28 |
| 2 – Network Access (20 %) | 2.1 bis 2.9 | 07, 08, 09, 10, 11, 12, 13, 23, 26, 28 |
| 3 – IP Connectivity (25 %) | 3.1 bis 3.5 | 05, 06, 14, 15, 16, 17 |
| 4 – IP Services (10 %) | 4.1 bis 4.9 | 13, 18, 19, 20, 21, 22, 28 |
| 5 – Security Fundamentals (15 %) | 5.1 bis 5.10 | 04, 12, 13, 23, 24, 25, 26, 28 |
| 6 – Automation and Programmability (10 %) | 6.1 bis 6.7 | 27, 28 |

## Empfohlene Reihenfolge

1. **Fundamente (Bereich 1):** 01 → 02 → 03 → 04 → 05 → 06
2. **Netzwerkzugang (Bereich 2):** 07 → 08 → 09 → 10 → 11 → 12
3. **IP-Konnektivität (Bereich 3):** 14 → 15 → 16 → 17
4. **IP-Dienste (Bereich 4):** 18 → 19 → 20 → 21 → 22
5. **Sicherheit (Bereich 5):** 13 → 23 → 24 → 26 → 25
6. **Automatisierung (Bereich 6):** 27 → 28

Faustregel: Teil A am ersten Tag, Teil B (Reparieren) am nächsten Tag ohne Blick in die Lösung, danach Teil C und die Prüfungsfragen.

## Ehrlicher Hinweis zum Teststand

- **Python-Paket (Lab 27):** Die Tests und Prüfskripte wurden mit den Musterlösungen ausgeführt (grün), die unfertigen Vorlagen schlagen absichtlich fehl.
- **Packet-Tracer-Labs (01–26):** Die Konfigurationen sind per Skript erzeugt und automatisch auf folgende Punkte geprüft: Jeder verwendete Port existiert am angegebenen Gerätemodell, kein Port ist doppelt belegt, die Adressen von Router-zu-Router-Links liegen im selben Subnetz, jedes eingebaute Fehlermuster kommt in der Konfiguration vor. **Ich habe die Labs nicht in Packet Tracer gestartet.** Befehle sind für IOS 15.x geschrieben, wie Packet Tracer es nachbildet; einzelne Befehle, Portnamen oder Verhalten können in deiner Version abweichen.
- **Mit grösserem Risiko:** Lab 11 und 12 (WLC/LAP und GUI, Menünamen je nach Version), Lab 08 (LLDP), Lab 22 (QoS-MQC wird in Packet Tracer nur teilweise simuliert), Lab 24 (Dynamic ARP Inspection fehlt je nach Version), Lab 25 (IPsec braucht die Security-Lizenz am 2911).
- Wenn etwas nicht läuft: Fehlermeldung als Lernanlass behandeln, mit der Cisco-Dokumentation gegenprüfen und gern eine Korrektur melden.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen (RFC 1918, 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32), Passwörter sind reine Lab-Werte. Es stecken keine echten Netzdaten drin.
