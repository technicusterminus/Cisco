# Hinweise und Abnahme

**Erster Hinweis.** Sprich den ersten Paketkopf laut aus. Bei einer ausgehenden HTTP-Anfrage wählt der Client seinen Quellport, der Serverdienst bestimmt den Zielport. Ein Echo Request trägt ICMP statt TCP. Verfolge erst danach den Eintritt in R1.

**Zweiter Hinweis.** `show ip interface GigabitEthernet0/0` bzw. `GigabitEthernet0/2` zeigt die gebundene Liste und Richtung. `show ip access-lists` liefert Reihenfolge und Treffer. Vergleiche zwei Ablesungen bei genau einem neuen Test. Die IOS-Pingfunktion sendet häufig mehrere Echo Requests, TCP kann wiederholen.

## Standard-ACL

Der Achterblock beginnt bei .8. Die drei niederwertigen Bits dürfen variieren, die Wildcard lautet 0.0.0.7. .8 und .15 treffen zu, .7 und .16 fallen heraus. Dies ist eine Adressauswahl innerhalb des angeschlossenen /24. Die Bindung an Gi0/2 ausgehend erfasst die zur DMZ weitergeleiteten Pakete aus LAN und ISP.

```text
ip access-list standard DMZ-QUELLEN
 10 permit 192.168.10.8 0.0.0.7
 20 deny any
 exit
interface GigabitEthernet0/2
 ip access-group DMZ-QUELLEN out
```

Die abschließende explizite Ablehnung macht die negative Gegenprobe zählbar. Beide PC-Pings zum Server treffen Sequenz 10. Der ISP-Ping trifft 20. Der Kontroll-Ping zum ISP verlässt Gi0/1. Vor der nächsten Stufe unter Gi0/2 `no ip access-group DMZ-QUELLEN out` eingeben.

## Extended-ACL

```text
ip access-list extended LAN-DMZ
 10 permit tcp 192.168.10.8 0.0.0.7 host 172.16.0.10 eq 80
 15 permit icmp host 192.168.10.11 host 172.16.0.10 echo
 20 deny ip any 172.16.0.0 0.0.0.255
 40 permit ip any any
 exit
interface GigabitEthernet0/0
 ip access-group LAN-DMZ in
```

In der Reihenfolge der sechs Tests ergeben sich **10, 10, 15, 20, 40, keine**. Eine Serverantwort auf HTTP betritt R1 über Gi0/2 und verlässt ihn über Gi0/0. Quelle ist jetzt TCP 80, das Ziel der temporäre Port des Clients. Die LAN-Eingangsliste sieht diese Antwort nicht. Die letzte Permit-Regel erhält die Erreichbarkeit anderer Ziele. Ohne sie würde das implizite Deny auch den Kontroll-Ping erfassen.

## Reparatur und Transfer

1. In der Reparaturdatei prüft Sequenz 10 beim TCP-Aufbau den Quellport 80. Eine neue HTTP-Anfrage trifft daher die DMZ-Ablehnung 20. Unter `ip access-list extended LAN-DMZ` die korrekte HTTP-Regel zunächst mit Sequenz 9 einfügen, dann die falsche Zeile mit `no 10` entfernen. Beide HTTP-Tests gelingen jetzt. PC1s Ping bleibt gesperrt.
2. Die inhaltlich passende ICMP-Ausnahme steht an Position 30 hinter der DMZ-Ablehnung. Füge sie an Position 15 ein und entferne 30. Der PC1-Ping erhöht nun den Permit-Zähler, der PC2-Ping weiter den Deny-Zähler. Eine andere Nummerierung mit derselben wirksamen Reihenfolge ist gleichwertig.
3. Für den Transfer vor die HTTP-Freigabe die Regel `5 deny tcp host 192.168.10.12 host 172.16.0.10 eq 80` setzen. Eine neue PC2-Verbindung zu TCP 80 erhöht 5, eine neue PC1-Verbindung weiterhin die HTTP-Freigabe. Die weiteren vier Tests behalten ihr Ergebnis. Mit `no 5` die Ausnahme zurücknehmen und den erneuten TCP-Aufbau von PC2 nachweisen.

**Rückkehr zum Start.** Beide YAML-Dateien lassen sich separat neu importieren. Für die unbelastete Ausgangsmessung die Bauvariante verwenden. Hinweise und erwartete Ergebnisse sind statisch aus Paketwegen und Regeln abgeleitet. Die Messwerte kommen aus deinem IOSv-Lauf.
