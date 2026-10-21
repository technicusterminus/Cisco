# CCNP ENCOR 350-401 v1.2 – EVE-NG-Labs

Parallelzweig zu den [CML-Labs](../CML-Labs/) für **EVE-NG**: dieselben 27 Labs mit denselben Aufgaben (Bauen, Reparieren, Üben), Fehlerlisten und Lösungen. Die Geräte (vIOS, vIOS-L2, CSRv, Nexus 9000v) tragen dieselben Interface-Namen wie in CML, deshalb gelten Aufgabentexte und Konfigurationen unverändert. Dazu kommen Node- und Kabeltabellen mit EVE-Templates, der RAM-Bedarf und Konfigurationsdateien zum Einspielen.

**Inhalt:** 27 Labs, 134 eingebaute Fehler. Die Python-/API-Drills und die Fallstudien-Pakete liegen im CML-Zweig und gelten für alle Plattformen: [`20-Python-REST-Drills`](../CML-Labs/20-Python-REST-Drills/), [`21-Design-Fallstudien.md`](../CML-Labs/21-Design-Fallstudien.md), [`22-Security-Szenarien.md`](../CML-Labs/22-Security-Szenarien.md).

## Voraussetzungen

- EVE-NG (Community oder Pro) mit den Images **vIOS** und **vIOS-L2** (aus Ciscos IOSv-/IOSvL2-Paketen), für die Labs 16 und 19 zusätzlich **Nexus 9000v** und **CSRv 1000v**. Die Images sind lizenzpflichtig und kommen nicht mit; Installation nach der EVE-NG-Anleitung.
- RAM: Die Tabelle unten zeigt den Bedarf je Lab als Richtwert; die meisten Labs liegen bei 3 bis 6 GB, Lab 16 (Nexus) und Lab 19 (CSRv) deutlich darüber.

## Arbeiten mit den Dateien

EVE-NG kann Startkonfigurationen nicht als Datei importieren. Pro Lab geht es so:

1. **Lab anlegen.** Neues Lab in EVE-NG, Nodes laut Tabelle „Nodes“ platzieren (Template wie angegeben), Kabel laut Tabelle „Verkabelung“ ziehen. Das Network-Objekt (*Bridge*) steht für den unmanaged Switch aus CML.
2. **Nodes starten**, bis ein Prompt (`Router>`/`Switch>`) erscheint.
3. **Ausgangszustand einspielen.** Entweder per Hand: Konsole öffnen, `enable`, `configure terminal`, Inhalt von `build/<Node>.cfg` einfügen, `end`, `write memory`. Oder mit dem Hilfsskript [`tools/eve_push_configs.py`](tools/eve_push_configs.py), das die Dateien per Telnet-Konsole tippt:
   `python3 tools/eve_push_configs.py <EVE-IP> <Lab-Ordner> --mode build --ports R1=32769 SW1=32770 …`
   Die Telnet-Ports zeigt EVE-NG je Node an. `--dry-run` zeigt nur an, was gesendet würde.
4. **Teil A** selbst bauen und jeden Schritt mit den Befehlen aus „Verifikation“ prüfen. Erst am Ende mit `solutions/<Node>.cfg` vergleichen.
5. **Teil B (Reparieren).** Nodes per Rechtsklick *Wipe* zurücksetzen und `repair/<Node>.cfg` einspielen (`--mode repair`). Tickets wie im Betrieb abarbeiten: Symptom nachstellen, eingrenzen, beheben, verifizieren. Erst nach 20 Minuten ohne Fortschritt in `solutions/FAULTS.md` schauen.
6. **Stand sichern.** Wenn dein Image es unterstützt, speichert *Export CFG* den Zustand als Startkonfiguration im Lab.
7. **Hosts.** Standardmäßig vIOS wie in CML. Alternative VPCS (spart RAM): Zeile aus `vpcs/<Host>.vpc` in der VPCS-Konsole eingeben oder `--vpcs H1=<Port>` nutzen.

## Übersicht

| Lab | Thema | Ziele | Nodes | Fehler | RAM (Richtwert) | Dauer |
|---|---|---|---|---|---|---|
| [01](01-OSPFv2-Multiarea/) | OSPFv2 Multi-Area | 3.2.a, 3.2.b | 4 | 4 | 2.0 GB | 90 min |
| [02](02-EIGRP-OSPFv3/) | EIGRP (Named Mode) und OSPFv3 | 3.2.a, 3.2.b | 3 | 4 | 1.5 GB | 90 min |
| [03](03-eBGP-Policy/) | eBGP Dual-Homing und Policy | 3.2.c | 4 | 5 | 2.0 GB | 90 min |
| [04](04-PBR-IPSLA/) | Policy-Based Routing mit IP SLA | 3.2.d, 4.4 | 6 | 4 | 3.0 GB | 75 min |
| [05](05-VLAN-Trunk-EtherChannel/) | VLANs, Trunks und EtherChannel | 3.1.a, 3.1.b | 7 | 4 | 4.2 GB | 90 min |
| [06](06-STP-MST-Schutz/) | Spanning Tree, MST und Schutzfunktionen | 3.1.c | 7 | 3 | 4.8 GB | 90 min |
| [07](07-FHRP-HSRP-VRRP-GLBP/) | First-Hop-Redundanz: HSRP, VRRP und GLBP | 3.3.c, 1.1.b | 8 | 4 | 4.2 GB | 90 min |
| [08](08-NTP-Syslog-SNMP/) | NTP, Syslog und SNMPv3 | 3.3.a, 4.1 | 3 | 4 | 1.5 GB | 75 min |
| [09](09-NAT-PAT/) | NAT und PAT | 3.3.b | 5 | 4 | 2.5 GB | 75 min |
| [10](10-ACL-CoPP/) | ACLs und Control-Plane Policing | 5.2.a, 5.2.b | 5 | 4 | 2.5 GB | 90 min |
| [11](11-Zugriff-AAA/) | Gerätezugriff und AAA | 5.1.a, 5.1.b | 2 | 4 | 1.0 GB | 75 min |
| [12](12-Multicast-PIM/) | Multicast mit IGMP und PIM Sparse Mode | 3.3.d | 7 | 4 | 3.5 GB | 90 min |
| [13](13-VRF-Lite/) | VRF-Lite mit überlappenden Adressen | 2.2.a | 6 | 4 | 3.0 GB | 75 min |
| [14](14-GRE-IPsec/) | GRE, IPsec und VTI | 2.2.b | 3 | 5 | 1.5 GB | 90 min |
| [15](15-LISP/) | LISP: Map-Server, Map-Resolver, xTR | 2.3.a | 6 | 4 | 3.0 GB | 90 min |
| [16](16-VXLAN/) | VXLAN: VTEP, VNI und Ingress Replication | 2.3.b | 4 | 4 | 17.0 GB | 75 min |
| [17](17-QoS-MQC/) | QoS mit MQC: Markieren, Policing, Shaping, LLQ | 1.4 | 6 | 4 | 3.0 GB | 90 min |
| [18](18-NetFlow-SPAN/) | Flexible NetFlow, SPAN und RSPAN | 4.2, 4.3 | 8 | 4 | 4.5 GB | 75 min |
| [19](19-Programmierbarkeit-EEM/) | RESTCONF, NETCONF, YANG und EEM | 4.6, 6.3, 6.5, 6.6 | 2 | 5 | 4.5 GB | 90 min |
| [23](23-Capstone-Campus-Edge-Troubleshooting/) | Capstone: Campus und Edge, Fehlersuche im Gesamtnetz | 3.1.a, 3.1.b, 3.1.c, 3.2.b, 3.3.a, 3.3.b, 3.3.c, 5.1.a, 5.2.a | 8 | 10 | 4.5 GB | 150 min |
| [24](24-Capstone-WAN-Overlay-Troubleshooting/) | Capstone: WAN, eBGP und IPsec-Overlay, Fehlersuche | 2.2.a, 2.2.b, 3.2.b, 3.2.c | 6 | 9 | 3.0 GB | 150 min |
| [25](25-EIGRP-Klassisch-Summary-Stub/) | EIGRP klassisch: Nachbarschaft, Authentifizierung, Summary und Stub | 3.2.a | 4 | 6 | 2.0 GB | 90 min |
| [26](26-iBGP-RouteReflector-Communities/) | iBGP mit Route Reflector, Local Preference und Communities | 3.2.c | 5 | 6 | 2.5 GB | 100 min |
| [27](27-Redistribution-Routenfilter/) | Redistribution zwischen OSPF und EIGRP mit Tags und Filtern | 3.2.a, 3.2.b | 4 | 6 | 2.0 GB | 100 min |
| [28](28-OSPF-Areatypen-Summary-Auth/) | OSPF vertieft: Area-Typen, Summarisierung und Authentifizierung | 3.2.b | 4 | 6 | 2.0 GB | 100 min |
| [29](29-PBR-Quelle-Anwendung/) | Policy-Based Routing nach Quelle und Anwendung | 3.2.d | 6 | 5 | 3.0 GB | 75 min |
| [30](30-Capstone-Routing-Troubleshooting/) | Capstone: Routing-Fehlersuche (OSPF, EIGRP, BGP, Redistribution) | 3.2.a, 3.2.b, 3.2.c | 5 | 8 | 2.5 GB | 150 min |

## Abdeckung nach Prüfungsziel

Pro Ziel mit Links zu Aufgaben und Lösungen: **[ZIELE.md](ZIELE.md)**.

| Ziel | Thema | Karten | Lab(s) |
|---|---|---|---|
| `1.1.a` | Campus-, Fabric- und Cloud-Design | 26 | 21 |
| `1.1.b` | Redundanz, FHRP und SSO | 22 | 07, 21 |
| `1.2.a` | SD-WAN: Ebenen und Komponenten | 33 | 21 |
| `1.2.b` | SD-WAN: Nutzen und Grenzen | 14 | 21 |
| `1.3.a` | SD-Access: Ebenen und Komponenten | 29 | 21 |
| `1.3.b` | Fabric und klassischer Campus | 13 | 21 |
| `1.4` | QoS-Konfigurationen | 48 | 17 |
| `2.1.a` | Hypervisor-Typen | 10 | 21 |
| `2.1.b` | Virtuelle Maschinen | 10 | 21 |
| `2.1.c` | Virtuelles Switching | 16 | 21 |
| `2.2.a` | VRF | 26 | 13, 24 |
| `2.2.b` | GRE und IPsec | 53 | 14, 24 |
| `2.3.a` | LISP | 18 | 15 |
| `2.3.b` | VXLAN | 14 | 16 |
| `3.1.a` | 802.1Q und Trunks | 31 | 05, 23 |
| `3.1.b` | EtherChannel | 34 | 05, 23 |
| `3.1.c` | RSTP, MST und Schutzfunktionen | 65 | 06, 23 |
| `3.2.a` | EIGRP und OSPF vergleichen | 45 | 01, 02, 25, 27, 30 |
| `3.2.b` | OSPFv2 und OSPFv3 | 86 | 01, 02, 23, 24, 27, 28, 30 |
| `3.2.c` | Direktes eBGP | 61 | 03, 24, 26, 30 |
| `3.2.d` | Policy-based Routing | 16 | 04, 29 |
| `3.3.a` | NTP und PTP | 32 | 08, 23 |
| `3.3.b` | NAT und PAT | 29 | 09, 23 |
| `3.3.c` | HSRP und VRRP | 30 | 07, 23 |
| `3.3.d` | Multicast-Verfahren | 46 | 12 |
| `4.1` | Diagnose, SNMP und Syslog | 40 | 08 |
| `4.2` | Flexible NetFlow | 24 | 18 |
| `4.3` | SPAN, RSPAN und ERSPAN | 22 | 18 |
| `4.4` | IP SLA | 22 | 04 |
| `4.5` | Catalyst Center und KI-Workflows | 22 | 21 |
| `4.6` | NETCONF und RESTCONF | 40 | 19 |
| `5.1.a` | Lines und lokale Anmeldung | 27 | 11, 23 |
| `5.1.b` | AAA | 42 | 11 |
| `5.2.a` | ACLs | 52 | 10, 23 |
| `5.2.b` | CoPP | 21 | 10 |
| `5.3` | REST-API-Sicherheit | 22 | 22 |
| `5.4.a` | Threat Defense | 29 | 22 |
| `5.4.b` | Endpoint Security | 29 | 22 |
| `5.4.c` | Next-Generation Firewall | 22 | 22 |
| `5.4.d` | TrustSec und MACsec | 28 | 22 |
| `6.1` | Python lesen | 49 | 20 |
| `6.2` | JSON erstellen | 19 | 20 |
| `6.3` | YANG | 21 | 19, 20 |
| `6.4` | Controller-APIs | 20 | 20 |
| `6.5` | HTTP-Codes und API-Payloads | 25 | 19, 20 |
| `6.6` | EEM-Applets | 27 | 19 |
| `6.7` | Agentenbasierte und agentenlose Automation | 21 | 20 |

## Stand

- **Geprüft per Skript:** Die Labs entstehen automatisch aus den CML-Labs, mit denselben Geräten, Kabeln, Konfigurationen und Fehlern. Das Skript prüft, dass alle Links auf vorhandene Interfaces zeigen, kein Port doppelt belegt ist und jeder Fehler in der Konfiguration steckt. In einer laufenden EVE-NG-Instanz sind die Labs noch nicht durchgespielt.
- **Templates und RAM** sind Richtwerte. Bei Nexus 9000v kann die Interface-Nummerierung je nach Image abweichen, beim CSRv heißt das erste Interface Gi1 statt Gi0/0.
- **Das Hilfsskript** ist gegen simulierte Telnet-Konsolen getestet (Reihenfolge, NX-OS, VPCS). Klappt es bei dir nicht, füge die Dateien per Copy and Paste ein.
- **Anspruchsvolle Labs:** 15 (LISP braucht ein passendes Image), 16 (Nexus, viel RAM), 19 (CSRv mit Cloud-Anbindung).

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter sind reine Lab-Werte.
