# CCIE Enterprise Infrastructure: Prüfungssimulation

Datei: [`ccie-pruefungssimulation.html`](ccie-pruefungssimulation.html). Im Browser öffnen, sie läuft offline.

## Was drin ist

- **175 Fragen** zu den fünf Domänen des Blueprints, im Prüfungsstil: Einfachauswahl, „Wähle zwei“, **9 Exhibit-Fragen** mit `show`-Ausgaben und Logmeldungen sowie **14 Fragen zum Ordnen und Zuordnen**.
- Der Schwerpunkt liegt auf Verständnis und Troubleshooting: Viele Fragen geben ein Symptom vor und fragen nach der Ursache oder der passenden Funktion.
- **Jede Erklärung** nennt zuerst die richtige Antwort, dann den Grund.

| Domäne | Gewicht in der Labprüfung | Fragen |
|---|---:|---:|
| 1 Network Infrastructure (Switching, EIGRP, OSPF, BGP, Multicast) | 30 % | 84 |
| 2 Software Defined Infrastructure (SD-Access, SD-WAN) | 25 % | 16 |
| 3 Transport Technologies (GRE, IPsec, DMVPN, MPLS, L3VPN, VXLAN/EVPN) | 15 % | 20 |
| 4 Security und Services (AAA, 802.1X, MACsec, CoPP, QoS, FHRP, NAT, SPAN) | 15 % | 34 |
| 5 Automation und Programmierbarkeit (YANG, NETCONF, RESTCONF, EEM, Python, Ansible) | 15 % | 21 |

## Modi

- **Prüfung:** 60 Fragen in 90 Minuten, zufällig aus dem ganzen Pool. Die Auswertung kommt erst am Ende.
- **Alle Fragen:** der komplette Pool unter Zeitdruck.
- **Üben** mit Erklärung direkt nach jeder Frage: pro Domäne, nur Exhibits oder nur Ordnen und Zuordnen.
- **Falsch beantwortete wiederholen:** Jede falsche Antwort landet auf einer Liste und verschwindet davon, sobald du sie richtig beantwortest.

Die Labprüfung gewichtet die Domänen mit 30, 25, 15, 15 und 15 %. Der Prüfungsmodus zieht trotzdem ungewichtet aus dem ganzen Pool: Domäne 2 (SD-Access, SD-WAN) hat erst 16 Fragen, mit Gewichtung kämen in jedem Lauf fast dieselben.

## Wichtig zur Einordnung

Der Pool prüft **Theorie und Troubleshooting**, nicht das Lab. Im echten CCIE-Lab konfigurierst du unter Zeitdruck ein ganzes Netz, das übt keine Quizfrage. Nutze die Simulation, um Lücken im Wissen zu finden, und trainiere das Lab separat mit eigenen Topologien.

## So nutzt du sie

1. Erst im Modus **Üben** pro Domäne durcharbeiten und jede Erklärung lesen, auch bei richtigen Antworten.
2. Dann eine **Prüfung** unter Zeitdruck. Danach **Falsch beantwortete wiederholen**, bis die Liste leer ist.
3. Bei jeder falschen Exhibit-Frage das Szenario im Lab nachbauen.

Die Fragen sind eigene Übungsfragen, keine Original-Prüfungsfragen. Antworten und Elemente werden bei jedem Start neu gemischt.

## Eigene Fragen laden

Der Player nimmt auch eigene Fragenpools als JSON-Datei. Das Format ist in der [ENARSI-Simulation](../../CCNP%20ENARSI%20300-410%20Vorbereitung/Pruefungssimulation/README.md#eigene-fragen-laden) beschrieben. Unter **Eigene Fragen** speicherst du den eingebauten Pool als Vorlage. Ergebnisse eines eigenen Pools werden getrennt gespeichert.
