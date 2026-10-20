# ENCOR 350-401: Prüfungssimulation

Datei: [`encor-pruefungssimulation.html`](encor-pruefungssimulation.html). Im Browser öffnen, sie läuft offline.

- **189 Fragen** in den sechs Domänen des Blueprints, im Prüfungsstil: Einfachauswahl, "Wähle zwei/drei" und 10 Exhibit-Fragen mit `show`-Ausgaben, Routingtabellen, ACLs und Python/REST-Beispielen.
- **Prüfung:** 60 Fragen, 75 Minuten, Zufallsauswahl nach Domänengewicht (Architektur 15 %, Virtualisierung 10 %, Infrastruktur 30 %, Assurance 10 %, Security 20 %, Automation 15 %). Auswertung erst am Ende.
- **Alle Fragen:** kompletter Durchlauf, 180 Minuten.
- **Üben:** eine Domäne mit Feedback und Erklärung nach jeder Frage.
- Die Auswertung zeigt das Ergebnis je Domäne und listet falsche oder offene Fragen mit Erklärung. Die letzten Ergebnisse speichert der Browser lokal.

| Domäne | Fragen |
|---|---:|
| 1 Architektur | 26 |
| 2 Virtualisierung | 18 |
| 3 Infrastruktur | 58 |
| 4 Network Assurance | 20 |
| 5 Security | 37 |
| 6 Automation | 30 |

Hinweise:

- Eigene Übungsfragen, keine Original-Prüfungsfragen. Die Antwortreihenfolge wird bei jedem Start gemischt.
- Der Pool ist begrenzt: bei mehreren Läufen wiederholen sich Fragen. Über 80 % hier ist ein Hinweis, keine Garantie.
- Die Fragen sind nicht Frage für Frage gegen die Cisco-Dokumentation geprüft. Stichprobenartig gegen Quellen bestätigt (Stand 20.10.2026): BGP-Best-Path-Reihenfolge, STP-Kosten lang (1G 20000, 10G 2000) und kurz (100/19/4), HSRP v1/v2 (Multicast, virtuelle MAC, Timer 3/10, Priorität 100, Preempt aus), LISP-UDP 4341/4342, `ntp master` Stratum 8 samt NTP-Authentifizierung, NETCONF-Port 830 (RFC 6242) und DSCP-Werte (EF 46, AF41 34, AF31 26, AF21 18, CS3 24). Nicht per Quelle bestätigt: STP-Kosten kurz für 10G (2), OSPF-Timer und DR-Regeln, VXLAN-Overhead, EIGRP-Protokollnummer. Im Zweifel gilt die Cisco-Doku. Wireless gehört in v1.2 nicht zu 350-401 und kommt hier nicht vor.
