# CCNP ENARSI 300-410 – Labs (EVE-NG)

Parallelzweig zu den [CML-Labs](../CML-Labs/) für **EVE-NG**: dieselben 6 Labs mit denselben Aufgaben (Bauen, Reparieren, Üben), Fehlerlisten und Lösungen. Die Geräte (vIOS, vIOS-L2) tragen dieselben Interface-Namen wie in CML, deshalb gelten Aufgabentexte und Konfigurationen unverändert. Dazu kommen Node- und Kabeltabellen mit EVE-Templates, der RAM-Bedarf und Konfigurationsdateien zum Einspielen.

**Inhalt:** 6 Labs, 29 eingebaute Fehler. Welche ENARSI-Themen die ENCOR-Labs abdecken, steht in der [ENARSI-Übersicht](../README.md#passende-labs-aus-dem-encor-paket).

## Voraussetzungen

- EVE-NG (Community oder Pro) mit den Images **vIOS** und für Lab E6 **vIOS-L2** (aus Ciscos IOSv-/IOSvL2-Paketen). Die Images sind lizenzpflichtig und kommen nicht mit; Installation nach der EVE-NG-Anleitung.
- RAM: Die Tabelle unten zeigt den Bedarf je Lab als Richtwert, er liegt bei 1.5 bis 3 GB.

## Arbeiten mit den Dateien

EVE-NG kann Startkonfigurationen nicht als Datei importieren. Pro Lab geht es so:

1. **Lab anlegen.** Neues Lab in EVE-NG, Nodes laut Tabelle „Nodes“ platzieren (Template wie angegeben), Kabel laut Tabelle „Verkabelung“ ziehen. Das Network-Objekt (*Bridge*) steht für den unmanaged Switch aus CML.
2. **Nodes starten**, bis ein Prompt (`Router>`/`Switch>`) erscheint.
3. **Ausgangszustand einspielen.** Entweder per Hand: Konsole öffnen, `enable`, `configure terminal`, Inhalt von `build/<Node>.cfg` einfügen, `end`, `write memory`. Oder mit dem Hilfsskript [`tools/eve_push_configs.py`](tools/eve_push_configs.py), das die Dateien per Telnet-Konsole tippt:
   `python3 tools/eve_push_configs.py <EVE-IP> <Lab-Ordner> --mode build --ports R1=32769 R2=32770 …`
   Die Telnet-Ports zeigt EVE-NG je Node an. `--dry-run` zeigt nur an, was gesendet würde.
4. **Teil A** selbst bauen und jeden Schritt mit den Befehlen aus „Prüfen“ kontrollieren. Erst am Ende mit `solutions/<Node>.cfg` vergleichen.
5. **Teil B (Reparieren).** Nodes per Rechtsklick *Wipe* zurücksetzen und `repair/<Node>.cfg` einspielen (`--mode repair`). Tickets wie im Betrieb abarbeiten. Erst nach 20 Minuten ohne Fortschritt in `solutions/FAULTS.md` schauen.
6. **Stand sichern.** Wenn dein Image es unterstützt, speichert *Export CFG* den Zustand als Startkonfiguration im Lab.
7. **Hosts.** Standardmäßig vIOS wie in CML. Alternative VPCS (spart RAM) nur dort, wo das Lab es erlaubt: Zeile aus `vpcs/<Host>.vpc` in der VPCS-Konsole eingeben.

## Übersicht

| Lab | Thema | Ziele | Geräte | Fehler | RAM (Richtwert) | Dauer |
|---|---|---|---|---|---|---|
| [E1](E1-DMVPN-Phase3/) | DMVPN Phase 3 mit EIGRP | 2.3, 2.3.a, 2.3.b, 2.3.d, 2.3.e | 4 | 5 | 2.0 GB | 90 min |
| [E2](E2-MPLS-L3VPN/) | MPLS L3VPN mit LDP und MP-BGP | 2.1, 2.2 | 5 | 5 | 2.6 GB | 100 min |
| [E3](E3-BFD-OSPF/) | BFD für schnelle Fehlererkennung mit OSPF | 1.8, 1.10.b | 4 | 5 | 1.5 GB | 75 min |
| [E4](E4-uRPF/) | Unicast Reverse Path Forwarding: Strict, Loose, ACL | 3.2.c | 3 | 4 | 1.5 GB | 75 min |
| [E5](E5-DHCP-Relay/) | DHCP-Server und DHCP-Relay über mehrere Router | 4.4 | 5 | 5 | 2.6 GB | 75 min |
| [E6](E6-IPv6-First-Hop-Security/) | IPv6 First Hop Security: RA Guard und DHCPv6 Guard | 3.4 | 4 | 5 | 2.3 GB | 90 min |

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

## Stand

- **Geprüft per Skript:** Die Labs entstehen aus derselben Definition wie die CML-Labs, mit denselben Geräten, Kabeln, Konfigurationen und Fehlern. Das Skript prüft, dass alle Links auf vorhandene Interfaces zeigen, kein Port doppelt belegt ist und jeder Fehler in der Konfiguration steckt. In einer laufenden EVE-NG-Instanz sind die Labs noch nicht durchgespielt.
- **Templates und RAM** sind Richtwerte.
- **Das Hilfsskript** stammt aus dem ENCOR-Paket und ist gegen simulierte Telnet-Konsolen getestet. Klappt es bei dir nicht, füge die Dateien per Copy and Paste ein.
- **Sonderfälle:** Lab E3 bleibt bei BFD-Timern ab 300 ms; Lab E6 braucht vIOS-L2 mit RA Guard und DHCPv6 Guard und vIOS-Hosts (kein VPCS).

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter sind reine Lab-Werte.

> Kein offizielles Cisco-Material. Cisco, CCNP und ENARSI sind Marken von Cisco Systems, Inc.
