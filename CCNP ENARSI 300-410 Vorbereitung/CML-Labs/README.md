# CCNP ENARSI 300-410 – Labs (CML)

Diese Labs ergänzen das [Anki-Deck](../Anki/) zum Thema **VPN, Security und Services**, für die es im ENCOR-Paket keine eigenen Labs gibt: DMVPN Phase 3, MPLS L3VPN, BFD, uRPF, DHCP-Relay und IPv6 First Hop Security. Alle anderen ENARSI-Themen (EIGRP, OSPF, BGP, Redistribution, PBR, VRF-Lite, AAA, ACL, CoPP, SNMP, Syslog, NetFlow …) übst du mit den [ENCOR-Labs](../README.md#passende-labs-aus-dem-encor-paket).

**Inhalt:** 6 Labs mit zusammen 29 eingebauten Fehlern zum Reparieren. **Andere Plattform:** dieselben Labs für [EVE-NG](../EVE-NG-Labs/). Packet Tracer ist hier nicht dabei, weil es DMVPN, MPLS, BFD und uRPF nicht ausreichend abbildet.

## So ist jedes Lab aufgebaut

| Datei | Zweck |
|---|---|
| `topology.yaml` | **Bauen:** Topologie mit Basis-Konfiguration (Hostnamen, IP-Adressen). Das Routing und die Funktion baust du selbst. |
| `topology-repair.yaml` | **Reparieren:** komplett gebaute Topologie mit eingebauten Fehlern. Die Tickets stehen im README, die Auflösung in `solutions/FAULTS.md`. |
| `README.md` | Teil A Aufgaben, Teil B Tickets, Verifikation, Teil C Transferfragen mit Antworten, Prüfungsbezug |
| `solutions/*.cfg` | Musterlösung je Gerät (ohne Basis-IP-Adressen) |

## So arbeitest du ein Lab durch

1. **Teil A: Bauen.** Importiere `topology.yaml`, arbeite die Schritte ab und prüfe jeden Schritt mit den Befehlen aus „Prüfen“. Erst am Ende vergleichst du mit `solutions/`.
2. **Teil B: Reparieren.** Am besten an einem anderen Tag. Importiere `topology-repair.yaml`, lies das Ticket und gehe vor wie im Betrieb: Symptom nachstellen, eingrenzen, beheben, verifizieren. Erst nach 20 Minuten ohne Fortschritt in `solutions/FAULTS.md` schauen. Dort steht pro Ticket zuerst, mit welchem Befehl du den Fehler gefunden hättest, dann Ursache und Lösung.
3. **Teil C: Üben.** Beantworte die Transferfragen erst selbst, dann klappst du die Antwort auf.
4. **Nacharbeiten.** Wiederhole im Anki-Deck die Karten zum Ziel des Labs (`tag:Ziel::…`), besonders zu den Fehlern, die du nicht gefunden hast.

## Übersicht

| Lab | Thema | Ziele | Geräte | Fehler | Dauer |
|---|---|---|---|---|---|
| [E1](E1-DMVPN-Phase3/) | DMVPN Phase 3 mit EIGRP | 2.3, 2.3.a, 2.3.b, 2.3.d, 2.3.e | 4 | 5 | 90 min |
| [E2](E2-MPLS-L3VPN/) | MPLS L3VPN mit LDP und MP-BGP | 2.1, 2.2 | 5 | 5 | 100 min |
| [E3](E3-BFD-OSPF/) | BFD für schnelle Fehlererkennung mit OSPF | 1.8, 1.10.b | 4 | 5 | 75 min |
| [E4](E4-uRPF/) | Unicast Reverse Path Forwarding: Strict, Loose, ACL | 3.2.c | 3 | 4 | 75 min |
| [E5](E5-DHCP-Relay/) | DHCP-Server und DHCP-Relay über mehrere Router | 4.4 | 5 | 5 | 75 min |
| [E6](E6-IPv6-First-Hop-Security/) | IPv6 First Hop Security: RA Guard und DHCPv6 Guard | 3.4 | 4 | 5 | 90 min |

## Abdeckung nach Prüfungsziel

| Ziel | Thema | Karten | Lab |
|---|---|---|---|
| `1.8` | Bidirectional Forwarding Detection | 7 | [E3](E3-BFD-OSPF/) |
| `1.10.b` | OSPF: Nachbarschaft und Authentisierung | 10 | [E3](E3-BFD-OSPF/) |
| `2.1` | MPLS: Fehlersuche | 23 | [E2](E2-MPLS-L3VPN/) |
| `2.2` | MPLS L3VPN: Fehlersuche | 19 | [E2](E2-MPLS-L3VPN/) |
| `2.3` | DMVPN: Fehlersuche | 16 | [E1](E1-DMVPN-Phase3/) |
| `2.3.a` | DMVPN: GRE und mGRE | 5 | [E1](E1-DMVPN-Phase3/) |
| `2.3.b` | DMVPN: NHRP | 8 | [E1](E1-DMVPN-Phase3/) |
| `2.3.d` | DMVPN: Dynamische Nachbarn | 6 | [E1](E1-DMVPN-Phase3/) |
| `2.3.e` | DMVPN: Spoke-to-Spoke | 6 | [E1](E1-DMVPN-Phase3/) |
| `3.2.c` | uRPF: Fehlersuche | 10 | [E4](E4-uRPF/) |
| `3.4` | IPv6 First Hop Security: Feinheiten | 13 | [E6](E6-IPv6-First-Hop-Security/) |
| `4.4` | DHCP: Fehlersuche | 20 | [E5](E5-DHCP-Relay/) |

## Voraussetzungen und Stand

- **Images:** IOSv (15.x) für alle Labs, zusätzlich IOSvL2 für Lab E6. Die Images sind lizenzpflichtig und kommen nicht mit.
- **Geprüft per Skript:** Das YAML lädt, alle Links zeigen auf vorhandene und freie Interfaces, jeder eingebaute Fehler trifft genau eine Konfigurationszeile, die Tickets passen zur Fehlerliste, und die Adressen an jedem Link liegen im selben Subnetz. **In einer laufenden CML-Instanz sind die Labs noch nicht durchgespielt.** Die Befehle folgen der IOS-15-Dokumentation; die Ausgaben in „Prüfen“ und „So findest du es“ sind aus der Funktionsweise abgeleitet und können in Details abweichen.
- **Wenn ein Befehl nicht durchgeht:** Image-Versionen unterscheiden sich. Prüfe die Syntax in der Cisco-Dokumentation. Das ist gleich eine gute Übung. Eine Korrektur per Issue hilft allen.
- **Sonderfälle:** E3 (BFD) bleibt bei 300 ms, weil virtuelle Router keine kürzeren Timer stabil schaffen. E6 (IPv6 FHS) hängt am Switch-Image: Kennt dein IOSvL2 RA Guard oder DHCPv6 Guard nicht, lies das Lab als Konfigurations- und Denkaufgabe.

## Selbst ändern oder neu erzeugen

Die Labs entstehen aus den Definitionen in [`../Labs-Quelle`](../Labs-Quelle/). Eine Änderung an einer Definition und `python3 build_labs.py` erzeugen CML-Dateien, EVE-NG-Dateien, Fehlerliste und Diff neu, sie bleiben also immer konsistent.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter sind reine Lab-Werte.

> Kein offizielles Cisco-Material. Cisco, CCNP und ENARSI sind Marken von Cisco Systems, Inc.
