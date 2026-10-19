# CML-Labs zum CCNP ENCOR (350-401 v1.2)

Sechs Labs für **Cisco Modeling Labs 2.x**, jeweils mit Topologie-Datei, Startkonfiguration, deutschen Aufgaben, Verifikation und Musterlösung. Sie ergänzen das Anki-Deck „Kompendium“ im Ordner darüber: Die Karten fragen das Wissen ab, die Labs lassen dich es anwenden.

| Lab | Thema | Blueprint | Nodes |
|---|---|---|---|
| [01 OSPF Multi-Area](01-OSPF-Multiarea/) | DR/BDR, Summarization, Stub/NSSA, Auth, Timer | 3.2.a, 3.2.b | 4× IOSv |
| [02 eBGP-Policy](02-eBGP-Policy/) | Dual-Homing, Local-Pref, Prepending, MED, No-Transit | 3.2.c | 4× IOSv |
| [03 Campus L2/HSRP](03-Campus-L2-FHRP/) | VLAN, Trunk, LACP, Rapid-PVST, Guards, HSRP | 3.1.a–c, 1.2 | 4× IOSvL2, 2× IOSv |
| [04 VRF/GRE/IPsec](04-VRF-GRE-IPsec/) | VRF-Lite, GRE pro VRF, OSPF pro VRF, Tunnel Protection | 2.2.a/b, 5.x | 3× IOSv |
| [05 NAT/ACL/Security](05-NAT-ACL-Security/) | PAT, Static NAT, ACL, SSH/AAA, uRPF | 3.3.b, 5.x | 2× IOSv + 3 Hosts |
| [06 Automation/Assurance](06-Automation-Assurance/) | RESTCONF, NETCONF, IP SLA, SNMPv3, SPAN, EEM | 4.x, 6.x | CSR1000v, IOSv, IOSvL2 |

## Benutzung

1. In CML: **Import** → `topology.yaml` des Labs wählen.
2. Nodes starten (die Startkonfiguration enthält nur Hostnamen und IP-Adressen).
3. Aufgaben in der `README.md` des Labs abarbeiten, erst danach in `solutions/` schauen.

## Ehrlicher Hinweis

Die Topologie-Dateien sind per Skript erzeugt und auf Konsistenz geprüft (Links, Interfaces, YAML), aber **nicht in einer echten CML-Instanz getestet**. Je nach CML-Version und installierten Images können Node-Definitionen oder Interface-Zuordnungen abweichen. Falls ein Import scheitert, lege die Nodes manuell nach dem ASCII-Bild und den Adresstabellen im README an. Die Musterlösungen sind nach bestem Wissen geschrieben, aber ebenfalls ungetestet: Behandle Abweichungen als Lernanlass und gleiche mit der Cisco-Dokumentation ab.

Es stecken keine echten Netzdaten drin, alle Adressen stammen aus Privat- oder Dokumentationsbereichen.
