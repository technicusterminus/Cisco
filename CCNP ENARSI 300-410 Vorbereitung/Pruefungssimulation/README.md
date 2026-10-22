# ENARSI 300-410: Prüfungssimulation

Datei: [`enarsi-pruefungssimulation.html`](enarsi-pruefungssimulation.html). Im Browser öffnen, sie läuft offline.

## Was drin ist

- **179 Fragen** aus den vier Domänen des Blueprints, im Prüfungsstil: Einfachauswahl, „Wähle zwei“, **23 Exhibit-Fragen** mit `show`-Ausgaben und Logmeldungen sowie **8 Fragen zum Ordnen und Zuordnen**.
- Der Schwerpunkt liegt wie in der Prüfung auf **Troubleshooting**: Viele Fragen geben ein Symptom oder eine Ausgabe vor und fragen nach der Ursache.
- **Jede Erklärung** nennt zuerst die richtige Antwort, dann den Grund.

| Domäne | Gewicht im Blueprint | Fragen |
|---|---:|---:|
| 1 Layer-3-Technologien (Routing-Grundlagen, EIGRP, OSPF, BGP) | 35 % | 66 |
| 2 VPN-Technologien (MPLS, L3VPN, DMVPN) | 20 % | 35 |
| 3 Infrastruktur-Security (AAA, ACLs, uRPF, CoPP, IPv6 First Hop Security) | 20 % | 33 |
| 4 Infrastruktur-Services (SNMP, Logging, DHCP, IP SLA, NetFlow, NTP, Catalyst Center) | 25 % | 45 |

## Modi

- **Prüfung:** 55 Fragen in 90 Minuten. Die Auswahl richtet sich nach dem Gewicht der Domänen. Die Auswertung kommt erst am Ende.
- **Alle Fragen:** der komplette Pool unter Zeitdruck.
- **Üben** mit Erklärung direkt nach jeder Frage: pro Domäne, nur Exhibits oder nur Ordnen und Zuordnen.
- **Falsch beantwortete wiederholen:** Jede falsche Antwort landet auf einer Liste und verschwindet davon, sobald du sie richtig beantwortest.

Die Auswertung zeigt das Ergebnis pro Domäne und listet alle falschen oder offenen Fragen mit Erklärung. Ergebnisse und Wiederholungsliste speichert der Browser lokal.

## So nutzt du sie

1. Erst im Modus **Üben** pro Domäne durcharbeiten und jede Erklärung lesen, auch bei richtigen Antworten.
2. Dann eine **Prüfung** unter Zeitdruck. Danach **Falsch beantwortete wiederholen**, bis die Liste leer ist.
3. Bei jeder falschen Exhibit-Frage das Szenario im Lab nachbauen. Die eigenen Labs ([CML](../CML-Labs/), [EVE-NG](../EVE-NG-Labs/)) decken DMVPN, MPLS L3VPN, BFD, uRPF, DHCP-Relay und IPv6 First Hop Security ab.

Die Fragen sind eigene Übungsfragen, keine Original-Prüfungsfragen. Antworten und Elemente werden bei jedem Start neu gemischt. Der Pool ist kleiner als der von ENCOR, ein Ergebnis über 80 % zeigt dir Lücken, ersetzt aber nicht die Karten und Labs.

## Eigene Fragen laden

Die Simulation ist zugleich ein Player für eigene Fragenpools. Unter **Eigene Fragen** speicherst du den eingebauten Pool als JSON-Datei. Die nimmst du als Vorlage, ergänzt oder ersetzt Fragen und lädst die Datei mit **Fragenpool laden** wieder. Ergebnisse und Wiederholungsliste eines eigenen Pools werden getrennt gespeichert, der eingebaute Pool bleibt unverändert.

Eine Datei ist ein JSON-Objekt mit `questions` (Pflicht) und optional `title`, `domains` (Nummer → Name), `weights` (Nummer → Prozent) und `examN` (Fragen im Prüfungsmodus). Drei Fragetypen:

```json
{
  "title": "Mein Pool",
  "questions": [
    {"d": 1, "q": "Welcher Port nutzt SSH?", "o": ["22", "23", "443"], "c": [0],
     "e": "22. Telnet nutzt 23."},
    {"d": 1, "t": "order", "q": "Bring DORA in die richtige Reihenfolge.",
     "o": ["Discover", "Offer", "Request", "Acknowledge"], "e": "Erklärung"},
    {"d": 1, "t": "match", "q": "Ordne die Ports zu.", "l": ["SSH", "DNS"],
     "o": ["22", "53"], "c": [0, 1], "e": "Erklärung"}
  ]
}
```

- **Auswahl** (Standard): `o` sind die Antworten, `c` die Indizes der richtigen (mehrere = „Wähle zwei“). `x` nimmt ein Exhibit auf, etwa eine `show`-Ausgabe.
- **Reihenfolge** (`"t": "order"`): `o` steht in der richtigen Reihenfolge, die Simulation mischt selbst.
- **Zuordnung** (`"t": "match"`): `l` sind die Begriffe links, `o` die Karten, `c` gibt für jeden Begriff den Index der passenden Karte an. Gibt es weniger Karten als Begriffe, darf eine Karte mehrfach passen.

In `q`, `o` und `e` sind `<code>` und `<b>` erlaubt. Fehler in der Datei meldet der Player mit der Nummer der Frage.

.vce-Dateien lädt er nicht: Das Format ist proprietär und verschlüsselt, und in Umlauf sind damit fast nur Dumps echter Prüfungsfragen.
