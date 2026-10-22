# CCIE Enterprise Infrastructure – Labs (EVE-NG)

Parallelzweig zu den [CML-Labs](../CML-Labs/) für **EVE-NG**: dieselben 6 Labs mit denselben Aufgaben (Bauen, Reparieren, Üben), Fehlerlisten und Lösungen. Die Geräte (vIOS) tragen dieselben Interface-Namen wie in CML, deshalb gelten Aufgabentexte und Konfigurationen unverändert. Dazu kommen Node- und Kabeltabellen mit EVE-Templates, der RAM-Bedarf und Konfigurationsdateien zum Einspielen.

Diese Labs gehen über ENCOR und ENARSI hinaus. Sie behandeln, was im CCIE-Blueprint dazukommt: BGP mit AS-Pfad-Manipulation und bedingter Ankündigung, Multicast mit Anycast RP und MSDP, OSPF mit Virtual Link und NSSA, MPLS L3VPN mit Shared Services, DMVPN mit IKEv2 und BGP sowie EIGRP im Named Mode. Die Grundlagen übst du mit den Labs aus ENCOR und ENARSI, die Zuordnung steht im [CCIE-README](../README.md#passende-labs-aus-encor-und-enarsi).

**Inhalt:** 6 Labs, 30 eingebaute Fehler.

## Voraussetzungen

- EVE-NG (Community oder Pro) mit dem Image **vIOS** (aus Ciscos IOSv-Paket). Das Image ist lizenzpflichtig und kommt nicht mit; Installation nach der EVE-NG-Anleitung.
- RAM: Die Tabelle unten zeigt den Bedarf je Lab als Richtwert, er liegt bei 2 bis 2.6 GB.

## Arbeiten mit den Dateien

EVE-NG kann Startkonfigurationen nicht als Datei importieren. Pro Lab geht es so:

1. **Lab anlegen.** Neues Lab in EVE-NG, Nodes laut Tabelle „Nodes“ platzieren (Template wie angegeben), Kabel laut Tabelle „Verkabelung“ ziehen.
2. **Nodes starten**, bis ein Prompt (`Router>`) erscheint.
3. **Ausgangszustand einspielen.** Entweder per Hand: Konsole öffnen, `enable`, `configure terminal`, Inhalt von `build/<Node>.cfg` einfügen, `end`, `write memory`. Oder mit dem Hilfsskript [`tools/eve_push_configs.py`](tools/eve_push_configs.py), das die Dateien per Telnet-Konsole tippt:
   `python3 tools/eve_push_configs.py <EVE-IP> <Lab-Ordner> --mode build --ports R1=32769 R2=32770 …`
   Die Telnet-Ports zeigt EVE-NG je Node an. `--dry-run` zeigt nur an, was gesendet würde.
4. **Teil A** selbst bauen und jeden Schritt mit den Befehlen aus „Prüfen“ kontrollieren. Erst am Ende mit `solutions/<Node>.cfg` vergleichen.
5. **Teil B (Reparieren).** Nodes per Rechtsklick *Wipe* zurücksetzen und `repair/<Node>.cfg` einspielen (`--mode repair`). Tickets wie im Betrieb abarbeiten, mit Zeitlimit: höchstens 10 Minuten pro Ticket, dann in `solutions/FAULTS.md` nachsehen.
6. **Stand sichern.** Wenn dein Image es unterstützt, speichert *Export CFG* den Zustand als Startkonfiguration im Lab.

## Übersicht

| Lab | Thema | Ziele | Geräte | Fehler | RAM (Richtwert) | Dauer |
|---|---|---|---|---|---|---|
| [C1](C1-BGP-AS-Pfad-und-Backup/) | BGP: allowas-in, private AS, GTSM und bedingte Ankündigung | 1.5.c, 1.5.d, 1.5.f | 5 | 5 | 2.6 GB | 120 min |
| [C2](C2-Multicast-Anycast-RP-MSDP/) | Multicast: Anycast RP mit MSDP, RPF-Umleitung und SSM | 1.6.a, 1.6.b, 1.6.c | 5 | 5 | 2.6 GB | 110 min |
| [C3](C3-OSPF-Virtual-Link-NSSA/) | OSPF: Virtual Link mit Authentisierung, NSSA, Typ-3-Filter und Netzwerktypen | 1.2.i, 1.4.b, 1.4.c, 1.4.d | 5 | 5 | 2.6 GB | 110 min |
| [C4](C4-L3VPN-Shared-Services/) | MPLS L3VPN: Shared Services, AS-Override und Route-Target-Design | 3.2.a, 3.2.b | 5 | 5 | 2.6 GB | 110 min |
| [C5](C5-DMVPN-IKEv2-BGP/) | DMVPN Phase 3 mit IKEv2 und BGP mit dynamischen Nachbarn | 1.5.e, 3.1.b, 3.1.c | 4 | 5 | 2.0 GB | 120 min |
| [C6](C6-EIGRP-Named-Mode/) | EIGRP Named Mode: SHA-256, Unequal-Cost Load Balancing und Stub mit Leak-Map | 1.2.i, 1.3.b, 1.3.d, 1.3.e, 1.3.f | 4 | 5 | 2.0 GB | 100 min |

## Abdeckung nach Prüfungsziel

| Ziel | Thema | Karten | Lab |
|---|---|---|---|
| `1.2.i` | Authentisierung von Routing-Protokollen | 5 | [C3](C3-OSPF-Virtual-Link-NSSA/), [C6](C6-EIGRP-Named-Mode/) |
| `1.3.b` | EIGRP: Metrik und Wide Metrics | 4 | [C6](C6-EIGRP-Named-Mode/) |
| `1.3.d` | EIGRP: Load Balancing | 3 | [C6](C6-EIGRP-Named-Mode/) |
| `1.3.e` | EIGRP: Named Mode | 4 | [C6](C6-EIGRP-Named-Mode/) |
| `1.3.f` | EIGRP: Optimierung, Stub, LFA und Leak-Maps | 4 | [C6](C6-EIGRP-Named-Mode/) |
| `1.4.b` | OSPF: Netzwerktypen, LSA-Typen und Area-Typen | 10 | [C3](C3-OSPF-Virtual-Link-NSSA/) |
| `1.4.c` | OSPF: Pfadwahl und Summarization | 5 | [C3](C3-OSPF-Virtual-Link-NSSA/) |
| `1.4.d` | OSPF: Betrieb, Router-ID, DR/BDR und Absicherung | 7 | [C3](C3-OSPF-Virtual-Link-NSSA/) |
| `1.5.c` | BGP: Policies, Communities und Anbindungsdesigns | 6 | [C1](C1-BGP-AS-Pfad-und-Backup/) |
| `1.5.d` | BGP: AS-Path-Manipulation | 5 | [C1](C1-BGP-AS-Pfad-und-Backup/) |
| `1.5.e` | BGP: Konvergenz und Skalierung | 6 | [C5](C5-DMVPN-IKEv2-BGP/) |
| `1.5.f` | BGP: Soft Reconfiguration, Route Refresh und Schutz | 4 | [C1](C1-BGP-AS-Pfad-und-Backup/) |
| `1.6.a` | Multicast auf Layer 2: IGMP, MLD und Snooping | 9 | [C2](C2-Multicast-Anycast-RP-MSDP/) |
| `1.6.b` | RPF-Prüfung | 4 | [C2](C2-Multicast-Anycast-RP-MSDP/) |
| `1.6.c` | PIM: Dense, Sparse, RP, Bidir, SSM und Anycast RP | 15 | [C2](C2-Multicast-Anycast-RP-MSDP/) |
| `3.1.b` | IPsec und IKE | 5 | [C5](C5-DMVPN-IKEv2-BGP/) |
| `3.1.c` | DMVPN | 9 | [C5](C5-DMVPN-IKEv2-BGP/) |
| `3.2.a` | MPLS und LDP | 8 | [C4](C4-L3VPN-Shared-Services/) |
| `3.2.b` | MPLS L3VPN | 11 | [C4](C4-L3VPN-Shared-Services/) |

## Stand

- **Geprüft per Skript:** Die Labs entstehen aus derselben Definition wie die CML-Labs, mit denselben Geräten, Kabeln, Konfigurationen und Fehlern. Das Skript prüft Verkabelung, Adressen und Fehlermuster. In einer laufenden EVE-NG-Instanz sind die Labs noch nicht durchgespielt.
- **Templates und RAM** sind Richtwerte.
- **Das Hilfsskript** stammt aus dem ENCOR-Paket und ist gegen simulierte Telnet-Konsolen getestet. Klappt es bei dir nicht, füge die Dateien per Copy and Paste ein.
- **Hosts:** SRC und RCV im Multicast-Lab C2 bleiben vIOS, weil VPCS keinen Multicast-Gruppen beitreten kann.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter und Schlüssel sind reine Lab-Werte.

> Kein offizielles Cisco-Material. Cisco und CCIE sind Marken von Cisco Systems, Inc.
