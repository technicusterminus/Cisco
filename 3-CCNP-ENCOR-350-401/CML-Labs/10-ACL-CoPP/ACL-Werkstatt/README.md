# ACL-Werkstatt · Vom Paket zur Regel

**ENCOR 5.2.a · IPv4 · 55 Minuten plus Wiederholung.** Im Betrieb meldet ein Team „Der Server geht nicht“. Du sollst genauer sagen können, für welche Quelle, welches Protokoll und welchen Dienst das gilt. Routen, Rückwege und HTTP-Dienst sind vorbereitet. Halte die Konsolen von PC1, PC2 und R1 offen. CoPP folgt anschließend im [Hauptlab](../README.md).

| Station | Was du wissen musst |
|---|---|
| PC1 / PC2 | 192.168.10.11 / .12 im gleichen /24, Gateway 192.168.10.1 |
| R1 | Gi0/0 zum LAN, Gi0/1 zum ISP, Gi0/2 zur DMZ |
| SRV | 172.16.0.10, hört auf TCP-Port 80 |
| ISP | 203.0.113.2 am Übergang, 8.8.8.8 als internes Kontrollziel des Labs |

## 1 · Einen Paketweg erklären (8 min)

Starte [die offene Bauvariante](topology.yaml). Zeichne für PC1 → SRV den Hin- und Rückweg. Am ersten Paket des TCP-Verbindungsaufbaus ist die Quelle PC1 mit einem temporären TCP-Port und das Ziel SRV mit Port 80. Das Paket kommt an R1 auf Gi0/0 an und verlässt ihn auf Gi0/2. Ergänze die vier Angaben für die Antwort des Servers selbst.

Prüfe von beiden PCs den Ping zu SRV und öffne jeweils mit `telnet 172.16.0.10 80` eine neue TCP-Verbindung. Ein `Open` belegt den TCP-Aufbau. Für einen eigenen HTTP-Nachweis tippe `GET / HTTP/1.0` und zweimal Enter. Auch ein HTTP-Fehlercode belegt eine Serverantwort. Schließe jede Verbindung vor der Wiederholung. Prüfe außerdem den Ping von PC2 zu 8.8.8.8 und vom ISP zu SRV mit Quelle 203.0.113.2. Erst wenn die Ausgangsproben funktionieren, kannst du einen späteren Unterschied dem Filter zuschreiben.

## 2 · Eine Quellgruppe begrenzen (10 min)

Nur Quellen aus **192.168.10.8 bis einschließlich .15** dürfen zur DMZ. Verkehr zum ISP soll weiterlaufen. Leite Netzadresse und Wildcard für genau diesen Block ab. Prüfe auf Papier, wie die Regel über .7, .8, .15 und .16 entscheidet. Die LAN-Geräte behalten ihre /24-Maske.

Setze die Vorgabe auf R1 mit einer benannten **Standard-ACL** um. Wähle Interface und Richtung. Begründe anhand des Paketwegs, weshalb die Quellregel dort genau die DMZ schützt. Prüfe die beiden PC-Pings zu SRV, den ISP-Ping zu SRV und PC2 → 8.8.8.8. Lies auf R1 Bindung und Treffer ab. Erkläre, warum diese ACL für PC2 keinen Unterschied zwischen Ping und HTTP machen kann.

## 3 · Eine Anforderung in Regeln übersetzen (17 min)

Löse die Standard-ACL vom Interface. Die nächste Änderung gilt für **aus dem LAN kommenden Verkehr**. In Richtung SRV darf der Achterblock HTTP nutzen. Einen Echo Request zu SRV darf ausschließlich PC1 senden. Jeder andere LAN-Zugriff zur gesamten DMZ ist gesperrt. Andere Ziele bleiben erreichbar. Entwirf eine benannte **Extended-ACL**. Trage vor dem Konfigurieren für jeden Test Interface, Richtung und die erwartete erste passende Regel ein.

| Quelle | Ziel und neuer Test | Soll |
|---|---|---|
| PC1 | SRV, TCP 80 | erlaubt |
| PC2 | SRV, TCP 80 | erlaubt |
| PC1 | SRV, ICMP Echo | erlaubt |
| PC2 | SRV, ICMP Echo | gesperrt |
| PC2 | 8.8.8.8, ICMP Echo | erlaubt |
| ISP, Quelle 203.0.113.2 | SRV, ICMP Echo | erlaubt |

Führe jeden Test einzeln aus. Vergleiche davor und danach die Treffer der angewendeten ACL. Notiere beim letzten Test, weshalb der Ping gelingt, ohne einen Zähler der LAN-ACL zu erhöhen. Ein Timeout allein beweist keine ACL-Sperre. Bei einem fehlgeschlagenen Test suche zuerst nach einer funktionierenden Vergleichsverbindung und der ersten Regel, deren Zähler steigt.

## 4 · Zwei Störungen trennen (12 min)

Öffne [die Reparaturvariante](topology-repair.yaml) als eigenes Lab. Das Soll aus Stufe 3 gilt. HTTP von beiden PCs und der Diagnose-Ping von PC1 fallen aus. Repariere einen Dienst und teste beide, bevor du den nächsten Fehler anfasst. Deine Änderung darf PC2 den Diagnose-Ping nicht freigeben. Halte für jeden Fehler Ausgangsbefund, erste passende Regel, minimale Änderung und Gegenprobe fest.

## 5 · Transfer ohne Vorlage (8 min, am Folgetag wiederholen)

Der Fachbereich zieht **nur die HTTP-Freigabe für PC2** zurück. Alle übrigen Ergebnisse der Matrix bleiben gleich. Starte mit deiner funktionierenden Policy. Formuliere die erforderliche Ausnahme, sage die betroffenen Zähler voraus, setze die Änderung um und prüfe die gesamte Matrix erneut. Nimm die Ausnahme danach zurück und stelle den vorherigen Dienstzustand nachweisbar wieder her.

**Selbstabnahme.** Du beherrschst das Lernziel, wenn du am Folgetag ohne Lösung (1) den Achterblock samt Randadressen erklären, (2) beide Filterpositionen am Paketweg begründen, (3) alle sechs Flüsse vorhersagen und (4) eine enge Änderung samt Rücknahme mit Zählerdifferenzen und neuen Verbindungen belegen kannst. Hakt nur ein Punkt, wiederhole die zugehörige Stufe. Eine korrekte Konfiguration ohne erklärbaren Paketweg ist ein Anlass, Stufe 1 erneut zu bearbeiten.

[Gestufte Hinweise, Referenzkonfiguration und Gegenproben](LOESUNG.md)
