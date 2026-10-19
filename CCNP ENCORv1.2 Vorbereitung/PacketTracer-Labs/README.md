# CCNP ENCOR 350-401 v1.2 – Packet-Tracer-Labs

Parallelzweig zu den [CML-Labs](../CML-Labs/): dieselben Themen, Aufgaben (Bauen, Reparieren, Üben) und Fehlerlisten, soweit Packet Tracer sie darstellen kann. Packet Tracer ist kostenlos, startet in Sekunden und eignet sich gut für Layer 2/3, Routing, NAT, ACLs, HSRP, GRE und Grundlagen. Bei LISP, VXLAN, Multicast, NetFlow, EEM, NETCONF/RESTCONF oder IPsec-VTI stößt es an Grenzen. Dort verweist jedes Lab auf CML bzw. EVE-NG.

**Inhalt:** 23 Labs mit Konfigurationen und 117 eingebauten Fehlern, 4 Labs als Verweis (in Packet Tracer nicht darstellbar). Die Python-/API-Drills und die Fallstudien-Pakete liegen im CML-Zweig und gelten für alle Plattformen: [`20-Python-REST-Drills`](../CML-Labs/20-Python-REST-Drills/), [`21-Design-Fallstudien.md`](../CML-Labs/21-Design-Fallstudien.md), [`22-Security-Szenarien.md`](../CML-Labs/22-Security-Szenarien.md).

## Arbeiten mit den Dateien

Packet-Tracer-Dateien (`.pkt`) liegen nicht bei: Ich kann sie ohne Packet Tracer weder erzeugen noch prüfen. Dafür beschreibt jedes Lab Geräte, Modelle, Ports und Kabel in Tabellen und liefert die Konfigurationen als Textdateien. Der Aufbau dauert pro Lab etwa 5 bis 10 Minuten; speichere ihn danach als eigene `.pkt`.

1. **Topologie bauen.** Geräte laut Tabelle „Geräte“ platzieren, Kabel laut Tabelle „Verkabelung“ von Hand wählen und auf die genannten Ports stecken.
2. **Ausgangszustand laden.** Pro Gerät: *CLI*-Tab → `enable` → `configure terminal`, dann den Inhalt von `build/<Gerät>.txt` einfügen. Lange Dateien in Blöcken einfügen, falls Zeilen verloren gehen, danach `end` und `write memory`.
3. **Endgeräte** (PC-PT) setzen: *Desktop* → *IP Configuration* mit den Werten aus der Adresstabelle.
4. **Teil A** selbst bauen, danach mit `solutions/<Gerät>.cfg` vergleichen.
5. **Teil B (Reparieren).** Geräte zurücksetzen (`erase startup-config`, `reload`), dann `repair/<Gerät>.txt` einfügen. Tickets abarbeiten, Auflösung in `solutions/FAULTS.md`.
6. **Teil C** (Transferfragen) erst selbst beantworten, dann aufklappen.

**Gerätemodelle und Portnamen.** Router sind 2911 (nur drei Ports `Gi0/0` bis `Gi0/2`: Alle Labs sind darauf ausgelegt), Layer-2/3-Switches sind 3560-24PS (`Fa0/1` bis `Fa0/24`, `Gi0/1`/`Gi0/2`), Hosts sind PC-PT. Die CML-Switches haben Gigabit-Ports (`Gi0/0` bis `Gi3/3`). Umrechnung: **`GiX/Y` → `Fa0/(X·4+Y+1)`**, z. B. `Gi0/0` → `Fa0/1`, `Gi1/0` → `Fa0/5`. In den Aufgabentexten und Konfigurationen ist das schon umgesetzt.

Voraussetzung: Cisco Packet Tracer 8.2 oder neuer (kostenlos über Cisco Networking Academy).

## Übersicht

Eignung: **geeignet** = alle verwendeten Funktionen gibt es in PT; **teilweise** = einzelne Teile oder Tickets lassen sich in PT nicht prüfen (im Lab-README markiert); **nicht geeignet** = Verweis auf CML/EVE-NG.

| Lab | Thema | Ziele | Geräte | Fehler | Eignung | Dauer |
|---|---|---|---|---|---|---|
| [01](01-OSPFv2-Multiarea/) | OSPFv2 Multi-Area | 3.2.a, 3.2.b | 5 | 4 | geeignet | 90 min |
| [02](02-EIGRP-OSPFv3/) | EIGRP (Named Mode) und OSPFv3 | 3.2.a, 3.2.b | 3 | 4 | teilweise | 90 min |
| [03](03-eBGP-Policy/) | eBGP Dual-Homing und Policy | 3.2.c | 4 | 5 | geeignet | 90 min |
| [04](04-PBR-IPSLA/) | Policy-Based Routing mit IP SLA | 3.2.d, 4.4 | 7 | 4 | teilweise | 75 min |
| [05](05-VLAN-Trunk-EtherChannel/) | VLANs, Trunks und EtherChannel | 3.1.a, 3.1.b | 7 | 4 | geeignet | 90 min |
| [06](06-STP-MST-Schutz/) | Spanning Tree, MST und Schutzfunktionen | 3.1.c | 7 | 3 | teilweise | 90 min |
| [07](07-FHRP-HSRP-VRRP-GLBP/) | First-Hop-Redundanz: HSRP, VRRP und GLBP | 3.3.c, 1.1.b | 8 | 4 | teilweise | 90 min |
| [08](08-NTP-Syslog-SNMP/) | NTP, Syslog und SNMPv3 | 3.3.a, 4.1 | 3 | 4 | teilweise | 75 min |
| [09](09-NAT-PAT/) | NAT und PAT | 3.3.b | 6 | 4 | geeignet | 75 min |
| [10](10-ACL-CoPP/) | ACLs und Control-Plane Policing | 5.2.a, 5.2.b | 6 | 4 | teilweise | 90 min |
| [11](11-Zugriff-AAA/) | Gerätezugriff und AAA | 5.1.a, 5.1.b | 2 | 4 | geeignet | 75 min |
| [12](12-Multicast-PIM/) | Multicast mit IGMP und PIM Sparse Mode | 3.3.d | – | – | **nicht geeignet** | 90 min |
| [13](13-VRF-Lite/) | VRF-Lite mit überlappenden Adressen | 2.2.a | 6 | 4 | teilweise | 75 min |
| [14](14-GRE-IPsec/) | GRE, IPsec und VTI | 2.2.b | 3 | 5 | teilweise | 90 min |
| [15](15-LISP/) | LISP: Map-Server, Map-Resolver, xTR | 2.3.a | – | – | **nicht geeignet** | 90 min |
| [16](16-VXLAN/) | VXLAN: VTEP, VNI und Ingress Replication | 2.3.b | – | – | **nicht geeignet** | 75 min |
| [17](17-QoS-MQC/) | QoS mit MQC: Markieren, Policing, Shaping, LLQ | 1.4 | 7 | 4 | teilweise | 90 min |
| [18](18-NetFlow-SPAN/) | Flexible NetFlow, SPAN und RSPAN | 4.2, 4.3 | 8 | 4 | teilweise | 75 min |
| [19](19-Programmierbarkeit-EEM/) | RESTCONF, NETCONF, YANG und EEM | 4.6, 6.3, 6.5, 6.6 | – | – | **nicht geeignet** | 90 min |
| [23](23-Capstone-Campus-Edge-Troubleshooting/) | Capstone: Campus und Edge, Fehlersuche im Gesamtnetz | 3.1.a, 3.1.b, 3.1.c, 3.2.b, 3.3.a, 3.3.b, 3.3.c, 5.1.a, 5.2.a | 8 | 10 | geeignet | 150 min |
| [24](24-Capstone-WAN-Overlay-Troubleshooting/) | Capstone: WAN, eBGP und IPsec-Overlay, Fehlersuche | 2.2.a, 2.2.b, 3.2.b, 3.2.c | 6 | 9 | teilweise | 150 min |
| [25](25-EIGRP-Klassisch-Summary-Stub/) | EIGRP klassisch: Nachbarschaft, Authentifizierung, Summary und Stub | 3.2.a | 4 | 6 | geeignet | 90 min |
| [26](26-iBGP-RouteReflector-Communities/) | iBGP mit Route Reflector, Local Preference und Communities | 3.2.c | 5 | 6 | geeignet | 100 min |
| [27](27-Redistribution-Routenfilter/) | Redistribution zwischen OSPF und EIGRP mit Tags und Filtern | 3.2.a, 3.2.b | 4 | 6 | geeignet | 100 min |
| [28](28-OSPF-Areatypen-Summary-Auth/) | OSPF vertieft: Area-Typen, Summarisierung und Authentifizierung | 3.2.b | 4 | 6 | geeignet | 100 min |
| [29](29-PBR-Quelle-Anwendung/) | Policy-Based Routing nach Quelle und Anwendung | 3.2.d | 7 | 5 | geeignet | 75 min |
| [30](30-Capstone-Routing-Troubleshooting/) | Capstone: Routing-Fehlersuche (OSPF, EIGRP, BGP, Redistribution) | 3.2.a, 3.2.b, 3.2.c | 5 | 8 | geeignet | 150 min |

## Abdeckung nach Prüfungsziel

Pro Ziel mit Links zu Aufgaben und Lösungen: **[ZIELE.md](ZIELE.md)**. In Packet Tracer sind 13 von 47 Zielen vollständig, 9 teilweise übbar; 25 Ziele laufen nur über CML/EVE-NG oder die Fallstudien- und Python-Pakete.

| Ziel | Thema | Karten | Labs (Eignung) |
|---|---|---|---|
| `1.1.a` | Campus-, Fabric- und Cloud-Design | 26 | 21 (CML-Paket) |
| `1.1.b` | Redundanz, FHRP und SSO | 22 | 07 (teilweise), 21 (CML-Paket) |
| `1.2.a` | SD-WAN: Ebenen und Komponenten | 33 | 21 (CML-Paket) |
| `1.2.b` | SD-WAN: Nutzen und Grenzen | 14 | 21 (CML-Paket) |
| `1.3.a` | SD-Access: Ebenen und Komponenten | 29 | 21 (CML-Paket) |
| `1.3.b` | Fabric und klassischer Campus | 13 | 21 (CML-Paket) |
| `1.4` | QoS-Konfigurationen | 48 | 17 (teilweise) |
| `2.1.a` | Hypervisor-Typen | 10 | 21 (CML-Paket) |
| `2.1.b` | Virtuelle Maschinen | 10 | 21 (CML-Paket) |
| `2.1.c` | Virtuelles Switching | 16 | 21 (CML-Paket) |
| `2.2.a` | VRF | 26 | 13 (teilweise), 24 (teilweise) |
| `2.2.b` | GRE und IPsec | 53 | 14 (teilweise), 24 (teilweise) |
| `2.3.a` | LISP | 18 | – |
| `2.3.b` | VXLAN | 14 | – |
| `3.1.a` | 802.1Q und Trunks | 31 | 05 (geeignet), 23 (geeignet) |
| `3.1.b` | EtherChannel | 34 | 05 (geeignet), 23 (geeignet) |
| `3.1.c` | RSTP, MST und Schutzfunktionen | 65 | 06 (teilweise), 23 (geeignet) |
| `3.2.a` | EIGRP und OSPF vergleichen | 45 | 01 (geeignet), 02 (teilweise), 25 (geeignet), 27 (geeignet), 30 (geeignet) |
| `3.2.b` | OSPFv2 und OSPFv3 | 86 | 01 (geeignet), 02 (teilweise), 23 (geeignet), 24 (teilweise), 27 (geeignet), 28 (geeignet), 30 (geeignet) |
| `3.2.c` | Direktes eBGP | 61 | 03 (geeignet), 24 (teilweise), 26 (geeignet), 30 (geeignet) |
| `3.2.d` | Policy-based Routing | 16 | 04 (teilweise), 29 (geeignet) |
| `3.3.a` | NTP und PTP | 32 | 08 (teilweise), 23 (geeignet) |
| `3.3.b` | NAT und PAT | 29 | 09 (geeignet), 23 (geeignet) |
| `3.3.c` | HSRP und VRRP | 30 | 07 (teilweise), 23 (geeignet) |
| `3.3.d` | Multicast-Verfahren | 46 | – |
| `4.1` | Diagnose, SNMP und Syslog | 40 | 08 (teilweise) |
| `4.2` | Flexible NetFlow | 24 | 18 (teilweise) |
| `4.3` | SPAN, RSPAN und ERSPAN | 22 | 18 (teilweise) |
| `4.4` | IP SLA | 22 | 04 (teilweise) |
| `4.5` | Catalyst Center und KI-Workflows | 22 | 21 (CML-Paket) |
| `4.6` | NETCONF und RESTCONF | 40 | – |
| `5.1.a` | Lines und lokale Anmeldung | 27 | 11 (geeignet), 23 (geeignet) |
| `5.1.b` | AAA | 42 | 11 (geeignet) |
| `5.2.a` | ACLs | 52 | 10 (teilweise), 23 (geeignet) |
| `5.2.b` | CoPP | 21 | 10 (teilweise) |
| `5.3` | REST-API-Sicherheit | 22 | 22 (CML-Paket) |
| `5.4.a` | Threat Defense | 29 | 22 (CML-Paket) |
| `5.4.b` | Endpoint Security | 29 | 22 (CML-Paket) |
| `5.4.c` | Next-Generation Firewall | 22 | 22 (CML-Paket) |
| `5.4.d` | TrustSec und MACsec | 28 | 22 (CML-Paket) |
| `6.1` | Python lesen | 49 | 20 (CML-Paket) |
| `6.2` | JSON erstellen | 19 | 20 (CML-Paket) |
| `6.3` | YANG | 21 | 20 (CML-Paket) |
| `6.4` | Controller-APIs | 20 | 20 (CML-Paket) |
| `6.5` | HTTP-Codes und API-Payloads | 25 | 20 (CML-Paket) |
| `6.6` | EEM-Applets | 27 | – |
| `6.7` | Agentenbasierte und agentenlose Automation | 21 | 20 (CML-Paket) |

## Ehrlicher Hinweis zum Test-Stand

- **Nicht in Packet Tracer ausgeführt.** Die Labs entstehen automatisch aus den CML-Labs (Geräte, Verkabelung, Konfigurationen, Fehler). Geprüft ist per Skript: Ports existieren am gewählten Modell, kein Port doppelt, Router-Link-Subnetze passen, jedes Fehlermuster kommt in der Konfiguration vor.
- **Funktionsliste = Kenntnisstand.** Was Packet Tracer 8.x unterstützt, habe ich nach bestem Wissen eingetragen; einzelne Einträge (z. B. HSRP Version 2, VRF, MST, NTP-Authentifizierung) können je nach Version abweichen. Wird ein Befehl nicht akzeptiert, ist das ein Limit der Software, kein Fehler von dir.
- **Abweichendes Verhalten.** Packet Tracer simuliert vereinfacht: Timer, `debug`-Ausgaben, Zähler und einzelne `show`-Befehle unterscheiden sich vom echten IOS. Für die Prüfungsvorbereitung zählen die Konzepte; für exakte Ausgaben sind CML oder EVE-NG näher an der Realität.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter sind reine Lab-Werte.
