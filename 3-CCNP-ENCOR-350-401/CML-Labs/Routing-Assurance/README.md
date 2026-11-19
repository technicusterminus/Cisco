# Routing Assurance mit OSPF, eBGP und IP SLA

**Drei IOSv-Router, etwa 60 Minuten.** Du betreust zwei Dienste eines Providers. Zuerst misst du den Normalbetrieb und einen internen Pfadwechsel. Danach grenzt du einen einzelnen Dienstausfall ein. Die beiden CML-Dateien sind unabhängige Startstände. Die Zeitbox beginnt nach dem Boot.

| Verbindung oder Rolle | Adressen |
|---|---|
| PROBE – EDGE, Transit A | Gi0/0 auf beiden Seiten, 10.0.0.1 und 10.0.0.2/30 |
| PROBE – EDGE, Transit B | Gi0/1 auf beiden Seiten, 10.0.0.5 und 10.0.0.6/30 |
| Messquelle und Unternehmensgrenze | PROBE Lo0 10.255.0.1/32, EDGE Lo0 10.255.0.2/32, AS 65010 |
| EDGE – ISP | EDGE Gi0/2 192.0.2.1/30, ISP Gi0/0 192.0.2.2/30, ISP AS 65020 |
| Dienst und unabhängiges Kontrollziel | ISP Lo0 203.0.113.10/32, ISP Lo1 198.51.100.10/32 |

## 1. OSPF-Pfad vorhersagen und belegen · 15 Minuten

Importiere [Normalbetrieb](topology.yaml). OSPFv2, Adressen und beide Providerdienste sind vorbereitet. Auf PROBE sind zwei FULL-Nachbarschaften zur selben Router-ID beabsichtigt. Ordne sie den Transitinterfaces zu. Lies die OSPF-Kosten beider Links ab. Sage für ein Paket an die EDGE-Loopback Ausgangsinterface und Next Hop voraus. Prüfe die Vorhersage mit Routingtabelle, CEF und einem Ping von Loopback0. Verändere nur die Ausgangskosten auf PROBE so, dass Transit B gewinnt. Notiere, ob EDGE seinen Rückweg ebenfalls wechselt, und begründe das anhand seiner eigenen Routingtabelle. Stelle die ursprünglichen Kosten wieder her.

## 2. eBGP-Dienst anbinden und überwachen · 25 Minuten

ISP ist für das Peering vorbereitet. Richte auf EDGE direktes eBGP zu ISP ein. Importiere die beiden Dienstpräfixe und kündige genau die Messquelle als /32 an. PROBE erhält bereits eine OSPF-Default-Route von EDGE. Erkläre anhand deiner Ausgangsmessung, welche Aussage diese Default-Route über die Erreichbarkeit des Dienstes erlaubt.

Prüfe auf EDGE den Empfang und die Installation beider /32 sowie auf ISP den Rückweg zur Messquelle. Pinge beide Dienste von PROBE mit Quelle Loopback0. Richte auf PROBE eine dauerhafte IP-SLA-ICMP-Messung zum ersten Dienst im Abstand von fünf Sekunden mit derselben Quelladresse ein.

Nimm auf PROBE Transit A kurz außer Betrieb. Warte, bis die Route über Transit B und ein neuer SLA-Messwert vorliegen. Vergleiche Ausgangsinterface, BGP-Sitzungsdauer und SLA-Status vor und nach dem Wechsel. Stelle Transit A wieder her. Ein kurzzeitiger Verlust kann zwischen zwei Messungen liegen. Dokumentiere ausschließlich beobachtete Ausfälle.

## 3. Störung unabhängig diagnostizieren · 20 Minuten

Importiere [Störungsfall](topology-repair.yaml) als neues Lab. Die Messung ist bereits eingerichtet. Das Monitoring meldet einen Ausfall von 203.0.113.10. Das Kontrollziel 198.51.100.10 muss von derselben Quelle weiterhin antworten. Für eingehende Providerankündigungen gilt eine Freigabeliste. Nur die beiden dokumentierten Dienste sind zulässig.

1. Reproduziere beide Ergebnisse. Sichere den letzten SLA-Rückgabecode. Formuliere zwei mögliche Ursachen und je eine Beobachtung, die sie unterscheidet.
2. Grenze ein, an welcher Stelle der betroffene Präfix verloren geht. Belege deine Diagnose auf beiden Seiten der AS-Grenze. Prüfe Hin- und Rückweg separat.
3. Stelle beide Dienste unter Beibehaltung der Freigabeliste und der bestehenden BGP-Sitzung wieder her. Belege den Erfolg mit einem neuen SLA-Ergebnis, dem Kontroll-Ping und dem installierten Präfix.

**Abgabe:** Halte pro Versuch Zeitpunkt, Messquelle, Ziel, Vorhersage, Beobachtung und Schlussfolgerung fest. Für den Pfadwechsel genügt ein Vorher/Nachher-Paar. Für die Störung gehören auch der erste abweichende Befund und die Gegenprobe nach der Reparatur dazu.

[Gestufte Hinweise und Musterabnahme](solutions/NACHWEISE.md)
