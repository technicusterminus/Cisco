# Lab 36 – Lösung und Abnahme der selbstständigen Aufgabe

## Reproduzierbarer Start

Importiere `topology.yaml` als neues Lab und starte R1 und R2. Nimm beide Konsolen erst nach dem Boot in Betrieb. Bei einer Wiederholung Stop/Wipe/Start verwenden oder die YAML als neues Lab importieren. Damit überprüfst du die bereitgestellte Konfiguration erneut. Bei persistenten Artefakten verwende einen frischen Applet- und Dateinamen. Stop/Start allein ist kein definierter Reset.

## Denkweg und Musterlösung

1. Stelle mit `show ip ospf neighbor` auf R1 fest, welche Nachbarn bzw. lokalen Interfaces den Kontroll- und den Testpfad bilden. Erfasse die Boot-Zeit und die beiden vollständigen Adjacencies vor der Änderung.
2. Schalte Gi0/1 im Lab kurz auf R1 ab. Lies mit `show logging | include OSPF-5-ADJCHG` den vollständigen Interface-Namen und die Richtung des Zustandswechsels. Stelle den Link wieder her und warte auf FULL. Das Muster wird gegen den tatsächlichen Syslog-Text entworfen.
3. Registriere einen Syslog-Trigger und einen lesenden CLI-Ablauf. Der Mitschnitt wird überschrieben, sodass ein alter Anhang keinen Erfolg vortäuschen kann.

```text
event manager applet ENCOR-ADJ-SNAPSHOT
 event syslog pattern "OSPF-5-ADJCHG.*GigabitEthernet0/1 from FULL to "
 action 010 cli command "enable"
 action 020 cli command "show ip ospf neighbor | redirect flash:encor-adj-snapshot.txt"
 action 030 syslog msg "ENCOR-ADJ-SNAPSHOT ausgelöst"
```

Eine Auslösung mit dem passenden lokalen Linkereignis ist ebenfalls zulässig, wenn sie in deinem getesteten Szenario genau den vereinbarten Verlust erkennt, Rückkehrereignisse ausfiltert und du dokumentierst, wie du das belegt hast.

## Prüfschritte

| Kriterium | Nachweis | Erwartung und Diagnose bei Abweichung |
|---|---|---|
| Infrastruktur | `show ip ospf neighbor` auf R1 | Vor dem Versuch FULL auf Gi0/0 und Gi0/1. Erst die Ausgangslage klären, falls hier bereits ein Pfad fehlt. |
| Registrierung | `show event manager policy registered` | Das eigene Applet ist mit einem Ereignis registriert. Fehlt es, Ereigniskonfiguration und Konfigurationsmodus kontrollieren. |
| Auslösung | Gi0/1 auf R1 per Konsole abschalten. Log und `show event manager history events` vergleichen. | Ein zeitlich passender OSPF-Übergang und ein neuer Lauf des eigenen Applets. OSPF-Ereignis ohne EEM-Lauf deutet auf das Muster. |
| Wirkung | `dir flash:` und `more flash:encor-adj-snapshot.txt`, daneben `show ip ospf neighbor` | Datei wurde bei diesem Versuch geschrieben und enthält den Kontrollpfad. Eine Syslog-Zeile allein belegt keinen erfolgreichen CLI-Lauf. Bei fehlender Datei CLI-Modus, Dateipfad und Meldungen prüfen. |
| Negativfall und Rückkehr | Testpfad wieder aktivieren. Nach FULL den letzten EEM-Lauf, die Datei und beide Adjacencies erneut ansehen. | Die Rückkehr produziert keinen neuen Snapshot. Die beiden Nachbarschaften sind FULL. Ein dritter Lauf bei einem abweichenden Ereignis zeigt einen zu breiten Trigger. |

**Status:** Konfiguration und Aufgabenfilter sind statisch geprüft. Cisco dokumentiert EEM für IOSv und das Syslog-Ereignis für Cisco IOS. Der Lauf mit dem konkret installierten IOSv-Image ist offen. [IOSv](https://developer.cisco.com/docs/modeling-labs/iosv/) · [EEM-Befehlsreferenz](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/eem/command/eem-cr-book/eem-cr-e1.html)
