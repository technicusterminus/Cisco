# Hinweise und Musterabnahme

## OSPF

**Hinweis 1.** Vergleiche für dieselbe Router-ID Interface, Kosten und Next Hop. **Hinweis 2.** Auf PROBE helfen `show ip ospf neighbor`, `show ip ospf interface brief`, `show ip route 10.255.0.2` und `show ip cef 10.255.0.2`. Prüfe auf EDGE die Route zu 10.255.0.1.

**Abnahme.** Ab Werk bevorzugt PROBE Gi0/0 über 10.0.0.2 (Ausgangskosten 10 gegenüber 100). Setze auf PROBE unter Gi0/0 `ip ospf cost 200`. Nach Konvergenz gewinnt Gi0/1 über 10.0.0.6. EDGE bevorzugt auf dem Rückweg weiterhin Gi0/0, weil seine eigenen Ausgangskosten unverändert sind. Anschließend auf PROBE Gi0/0 wieder `ip ospf cost 10` setzen.

## eBGP und aktiver Diensttest

**Hinweis 1.** Kontrolliere zuerst die direkt angeschlossene Nachbaradresse, danach die Herkunft der Messquellenroute auf EDGE. **Hinweis 2.** Das BGP-network benötigt einen exakten RIB-Eintrag. Der OSPF-Eintrag für die PROBE-Loopback erfüllt diese Voraussetzung.

Auf EDGE im Konfigurationsmodus:

```text
router bgp 65010
 bgp router-id 10.255.0.2
 neighbor 192.0.2.2 remote-as 65020
 network 10.255.0.1 mask 255.255.255.255
```

Auf PROBE im Konfigurationsmodus:

```text
ip sla 10
 icmp-echo 203.0.113.10 source-interface Loopback0
 frequency 5
 exit
ip sla schedule 10 life forever start-time now
```

**Abnahme.** Auf EDGE zeigt `show ip bgp summary` einen Präfixzähler für ISP. Prüfe beide Dienst-/32 einzeln mit `show ip bgp` und `show ip route`. Auf ISP führt die Route zu 10.255.0.1 über 192.0.2.1. Auf PROBE liefern `ping 203.0.113.10 source Loopback0` und der entsprechende Ping zu 198.51.100.10 Antworten. `show ip sla statistics 10` zeigt für eine neue Operation OK. Die von EDGE dauerhaft angekündigte Default-Route bestand schon vor der BGP-Konfiguration.

Beim Shutdown von PROBE Gi0/0 bleibt die zweite OSPF-Adjazenz bestehen. PROBE erreicht EDGE über Gi0/1. Die eBGP-Sitzung am separaten Providerlink läuft weiter. Zeitstempel der Messungen und `show logging` helfen bei der Einordnung. Nach `no shutdown` und vollständiger Konvergenz muss Gi0/0 wieder bevorzugt werden.

## Störungsfall

**Hinweis 1.** Liefert der Ping zum Kontrollziel von derselben Quelle eine Antwort, funktionieren ein Pfad durch beide AS und der Rückweg zur Messquelle. Prüfe als Nächstes den Unterschied zwischen den beiden Zielpräfixen.

**Hinweis 2.** Vergleiche auf ISP `show ip bgp neighbors 192.0.2.1 advertised-routes` mit `show ip bgp 203.0.113.10` auf EDGE. Untersuche dort Nachbarkonfiguration und `show ip prefix-list SERVICES`. Eine Abfrage von ungefilterten received-routes ist für diese Diagnose entbehrlich.

**Ursache.** ISP kündigt beide /32 an. Auf EDGE lässt die eingehende Liste nur das Kontrollziel zu. Die implizite Ablehnung trifft den überwachten Dienst. EDGE besitzt keinen alternativen Pfad zu diesem Ziel. Die Gegenrichtung zur PROBE-Loopback ist intakt.

**Reparatur.** Auf EDGE im Konfigurationsmodus `ip prefix-list SERVICES seq 10 permit 203.0.113.10/32` ergänzen. Anschließend im EXEC-Modus mit `clear ip bgp 192.0.2.2 soft in` eine weiche Neubewertung auslösen. Auf EDGE beide installierten /32 und die fortlaufende Sitzungsdauer prüfen. Auf PROBE nach einer neuen Operation deren Uhrzeit und OK-Status sichern und das Kontrollziel erneut mit Quelle Loopback0 testen. Die Liste muss weiterhin genau die beiden /32 erlauben.

**Stand.** Startkonfigurationen und erwartete Pfade sind statisch geprüft. Laufzeit, Konvergenzzeiten und tatsächliche SLA-Messwerte sind beim Import mit dem eingesetzten IOSv-Image zu erheben.
