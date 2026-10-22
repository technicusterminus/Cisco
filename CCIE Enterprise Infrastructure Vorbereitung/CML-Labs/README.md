# CCIE Enterprise Infrastructure – Labs (CML)

Diese Labs gehen über ENCOR und ENARSI hinaus. Sie behandeln, was im CCIE-Blueprint dazukommt: BGP mit AS-Pfad-Manipulation und bedingter Ankündigung, Multicast mit Anycast RP und MSDP, OSPF mit Virtual Link und NSSA, MPLS L3VPN mit Shared Services, DMVPN mit IKEv2 und BGP sowie EIGRP im Named Mode. Die Grundlagen übst du mit den Labs aus ENCOR und ENARSI, die Zuordnung steht im [CCIE-README](../README.md#passende-labs-aus-encor-und-enarsi).

**Inhalt:** 6 Labs mit zusammen 30 eingebauten Fehlern zum Reparieren, jedes mit höchstens fünf Geräten. **Andere Plattform:** dieselben Labs für [EVE-NG](../EVE-NG-Labs/).

## So ist jedes Lab aufgebaut

| Datei | Zweck |
|---|---|
| `topology.yaml` | **Bauen:** Topologie mit Basis-Konfiguration (Hostnamen, IP-Adressen, teils das Underlay). Die Funktion des Labs baust du selbst. |
| `topology-repair.yaml` | **Reparieren:** komplett gebaute Topologie mit eingebauten Fehlern. Die Tickets stehen im README, die Auflösung in `solutions/FAULTS.md`. |
| `README.md` | Teil A Aufgaben, Teil B Tickets, Verifikation, Teil C Transferfragen mit Antworten, Prüfungsbezug |
| `solutions/*.cfg` | Musterlösung je Gerät (ohne Basis-Konfiguration) |

## So arbeitest du ein Lab durch

1. **Teil A: Bauen.** Importiere `topology.yaml`, arbeite die Schritte ab und prüfe jeden Schritt mit den Befehlen aus „Prüfen“. Erst am Ende vergleichst du mit `solutions/`.
2. **Teil B: Reparieren.** Am besten an einem anderen Tag. Importiere `topology-repair.yaml` und arbeite die Tickets ab wie im Betrieb: Symptom nachstellen, eingrenzen, beheben, verifizieren. In der Labprüfung zählt Tempo, deshalb mit Zeitlimit: **höchstens 10 Minuten pro Ticket**, dann in `solutions/FAULTS.md` nachsehen. Dort steht pro Ticket zuerst, mit welchem Befehl du den Fehler gefunden hättest, dann Ursache und Lösung.
3. **Teil C: Üben.** Beantworte die Transferfragen erst selbst, dann klappst du die Antwort auf.
4. **Nacharbeiten.** Wiederhole im [Anki-Deck](../Anki/) die Karten zum Ziel des Labs (`tag:Ziel::…`), besonders zu den Fehlern, die du nicht gefunden hast.

## Übersicht

| Lab | Thema | Ziele | Geräte | Fehler | Dauer |
|---|---|---|---|---|---|
| [C1](C1-BGP-AS-Pfad-und-Backup/) | BGP: allowas-in, private AS, GTSM und bedingte Ankündigung | 1.5.c, 1.5.d, 1.5.f | 5 | 5 | 120 min |
| [C2](C2-Multicast-Anycast-RP-MSDP/) | Multicast: Anycast RP mit MSDP, RPF-Umleitung und SSM | 1.6.a, 1.6.b, 1.6.c | 5 | 5 | 110 min |
| [C3](C3-OSPF-Virtual-Link-NSSA/) | OSPF: Virtual Link mit Authentisierung, NSSA, Typ-3-Filter und Netzwerktypen | 1.2.i, 1.4.b, 1.4.c, 1.4.d | 5 | 5 | 110 min |
| [C4](C4-L3VPN-Shared-Services/) | MPLS L3VPN: Shared Services, AS-Override und Route-Target-Design | 3.2.a, 3.2.b | 5 | 5 | 110 min |
| [C5](C5-DMVPN-IKEv2-BGP/) | DMVPN Phase 3 mit IKEv2 und BGP mit dynamischen Nachbarn | 1.5.e, 3.1.b, 3.1.c | 4 | 5 | 120 min |
| [C6](C6-EIGRP-Named-Mode/) | EIGRP Named Mode: SHA-256, Unequal-Cost Load Balancing und Stub mit Leak-Map | 1.2.i, 1.3.b, 1.3.d, 1.3.e, 1.3.f | 4 | 5 | 100 min |

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

## Voraussetzungen und Stand

- **Images:** IOSv (15.x) für alle Geräte, auch für die Hosts im Multicast-Lab. Die Images sind lizenzpflichtig und kommen nicht mit.
- **Geprüft per Skript:** Das YAML lädt, alle Links zeigen auf vorhandene und freie Interfaces, die Adressen an jedem Link liegen im selben Netz, keine Adresse ist doppelt vergeben (außer der gewollten Anycast-Adresse), jede Nachbar-, Peer- und RP-Adresse existiert im Lab, jeder eingebaute Fehler trifft genau eine Konfigurationszeile, und die Tickets passen zur Fehlerliste. **In einer laufenden CML-Instanz sind die Labs noch nicht durchgespielt.** Die Befehle folgen der IOS-15-Dokumentation; die Ausgaben in „Prüfen“ und „So findest du es“ sind aus der Funktionsweise abgeleitet und können in Details abweichen.
- **Wenn ein Befehl nicht durchgeht:** Image-Versionen unterscheiden sich. Prüfe die Syntax in der Cisco-Dokumentation. Das ist gleich eine gute Übung. Eine Korrektur per Issue hilft allen.
- **Nicht dabei:** SD-Access und SD-WAN (Domäne 2) brauchen Controller, die sich mit IOSv nicht nachbauen lassen. Dafür gibt es Karten im Deck und Fragen in der [Prüfungssimulation](../Pruefungssimulation/).

## Selbst ändern oder neu erzeugen

Die Labs entstehen aus den Definitionen in [`../Labs-Quelle`](../Labs-Quelle/). Eine Änderung an einer Definition und `python3 build_labs.py` erzeugen CML-Dateien, EVE-NG-Dateien, Fehlerliste und Diff neu, sie bleiben also immer konsistent.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter und Schlüssel sind reine Lab-Werte.

> Kein offizielles Cisco-Material. Cisco und CCIE sind Marken von Cisco Systems, Inc.
