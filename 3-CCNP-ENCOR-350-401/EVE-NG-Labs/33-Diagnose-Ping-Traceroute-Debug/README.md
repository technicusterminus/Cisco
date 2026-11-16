# Lab 33 – Diagnose: Ping und Traceroute lesen, Debug und Conditional Debug sicher einsetzen

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel

Ziel 4.1 verlangt, Netzprobleme mit Debugs, Conditional Debugs, Traceroute, Ping, SNMP und Syslog einzugrenzen. SNMP und Syslog übst du in Lab 08. Hier geht es um die Werkzeuge an der Konsole: Du lernst, die Zeichen von Ping und Traceroute als Befund zu lesen, eine MTU-Engstelle auszumessen und Debug-Ausgaben so einzugrenzen, dass sie den Router nicht lahmlegen. Das Netz ist fertig geroutet, damit die Werkzeuge im Mittelpunkt stehen.

**Lernziele:** Nach diesem Lab kannst du …

- Aus `!`, `.`, `U`, `M` und `!A`, `!H`, `*` ablesen, welches Gerät geantwortet hat und warum.
- Mit erweitertem Ping (Quelle, Größe, DF-Bit, Sweep) die Pfad-MTU bestimmen.
- Erklären, warum ein Ping durchgeht, während Traceroute scheitert, und umgekehrt.
- Debug-Ausgaben in den Puffer statt auf die Konsole lenken, per ACL filtern und mit `debug condition` auf ein Interface begrenzen.
- Für ein Symptom zuerst das passende Werkzeug wählen, statt alles einzuschalten.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::4.1` | Diagnose, SNMP und Syslog | 40 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML) | 512 |
| SRV | Cisco vIOS Router | Host (vIOS, wie in CML) | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.6 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| H1 | Gi0/0 | R1 | Gi0/0 |
| R1 | Gi0/1 | R2 | Gi0/0 |
| R2 | Gi0/1 | R3 | Gi0/0 |
| R3 | Gi0/1 | SRV | Gi0/0 |

### Hosts: vIOS oder VPCS

Nimm für H1 und SRV vIOS. Du brauchst auf H1 den erweiterten Ping mit DF-Bit und die IOS-Zeichen von Ping und Traceroute; ein VPCS zeigt sie anders an.

## Topologie

```
                                    MTU 1400
  H1 ──── R1 ──────────── R2 ════════════════ R3 ──── SRV
     Gi0/0   Gi0/1    Gi0/0   Gi0/1       Gi0/0   Gi0/1
  .10      .1                                    .1      .10
```

| Link | Netz |
|---|---|
| H1 – R1 Gi0/0 | 192.168.1.0/24 (H1 .10, R1 .1) |
| R1 Gi0/1 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R2 Gi0/1 – R3 Gi0/0 | 10.0.23.0/30 (.1/.2), `ip mtu 1400` auf beiden Seiten |
| R3 Gi0/1 – SRV | 192.168.3.0/24 (R3 .1, SRV .10) |

Loopback0: R1 10.255.0.1, R2 10.255.0.2, R3 10.255.0.3 (/32). OSPF 1 (Area 0) ist **fertig konfiguriert**. Der Link R2–R3 steht für eine Strecke mit kleinerer MTU, etwa einen Tunnel oder eine Provider-Leitung. H1 und SRV sind IOS-Geräte mit `no ip routing`.

**Regel für dieses Lab:** Jedes Debug endet mit `undebug all`. Prüfe mit `show debugging`, dass nichts mehr läuft, bevor du den nächsten Schritt beginnst.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A. Bei **Erst vorhersagen** schreibst du deine Erwartung auf, *bevor* du den Befehl eingibst. Lag die Vorhersage daneben, hast du genau die Stelle gefunden, an der dein Modell noch nicht stimmt. Die Auflösung steht ebenfalls bei den Antworten.

1. **Ping-Zeichen lesen.** Sende von H1 drei Pings: an SRV (`ping 192.168.3.10`), an einen Host, den es im Server-Netz nicht gibt (`ping 192.168.3.99`), und an ein Netz, das niemand kennt (`ping 10.99.99.99`).
   - **Erst vorhersagen:** Welche Zeichen erwartest du beim zweiten und beim dritten Ping, `.` oder `U`? Und welches Gerät erzeugt sie?
   - **Prüfen:** Erster Ping `!!!!!`. Zweiter Ping `.....`. Dritter Ping `U.U.U`.
   - **Denkfrage:** Warum wechseln sich beim dritten Ping `U` und `.` ab, statt fünfmal `U` zu zeigen?
2. **Pfad-MTU ausmessen.** Sende von R1 `ping 192.168.3.10 source Loopback0 size 1500 df-bit`. Starte danach den erweiterten Ping (nur `ping` eingeben) mit DF-Bit und einem Sweep von 1390 bis 1410 in Einerschritten.
   - **Erst vorhersagen:** Welches Zeichen zeigt der erste Ping, und von welcher Adresse kommt die Meldung dazu?
   - **Prüfen:** Der erste Ping zeigt `M.M.M`. Im Sweep sind die Größen bis 1400 erfolgreich, ab 1401 erscheint `M`. `debug ip icmp` auf R1 zeigt während des Pings die Meldung „frag. needed and DF set“ von 10.0.12.2.
   - **Denkfrage:** Was steht in der ICMP-Meldung, damit der Absender seine Paketgröße anpassen kann? Was passiert mit TCP-Verbindungen, wenn ein Gerät auf dem Weg diese Meldung unterdrückt?
3. **Traceroute lesen.** Führe auf H1 `traceroute 192.168.3.10` aus.
   - **Erst vorhersagen:** Wie viele Zeilen erscheinen, und warum zeigt die letzte Zeile meist `x msec * y msec` mit einem Stern in der Mitte?
   - **Prüfen:** Vier Zeilen: 192.168.1.1, 10.0.12.2, 10.0.23.2, 192.168.3.10. Die letzte Zeile enthält einen Stern.
   - **Denkfrage:** Welche Pakete sendet IOS bei Traceroute, und mit welcher ICMP-Meldung antworten die Router unterwegs, mit welcher das Ziel?
4. **Ping geht, Traceroute nicht.** Lege auf R3 die ACL `TRANSIT` an und binde sie auf Gi0/0 eingehend: `permit ospf any any`, `permit icmp any any`, `permit tcp any any`, `deny ip any any log`. Wiederhole Ping und Traceroute von H1 zu SRV.
   - **Erst vorhersagen:** Bis zu welchem Hop kommt Traceroute, und welches Zeichen steht dort?
   - **Prüfen:** Der Ping geht durch. Traceroute zeigt die Hops 1 und 2 und in Zeile 3 `!A` von 10.0.23.2. `show access-lists TRANSIT` zählt Treffer auf der `deny`-Zeile. Füge danach mit einer Sequenznummer **vor** dem `deny` die Zeile `permit udp any any range 33434 33534` ein und prüfe, dass Traceroute wieder vier Zeilen zeigt.
   - **Denkfrage:** Windows sendet bei `tracert` ICMP Echo statt UDP. Was hätte ein Windows-Client mit der ersten Fassung der ACL gesehen?
5. **Debug sicher einschalten.** Setze auf R1 bis R3 `service timestamps debug datetime msec`, `logging buffered 16384 debugging` und `logging console informational`. Schalte auf R3 `debug ip icmp` ein und pinge von R1 die 10.255.0.3. Lies das Ergebnis mit `show logging`, dann `undebug all`.
   - **Erst vorhersagen:** Erscheinen die Debug-Zeilen jetzt noch auf der Konsole von R3?
   - **Prüfen:** Auf der Konsole erscheint nichts. `show logging` zeigt die Zeilen „ICMP: echo reply sent“ mit Zeitstempel in Millisekunden. `show debugging` ist nach `undebug all` leer.
   - **Denkfrage:** Warum ist die Konsole der gefährlichste Ort für Debug-Ausgaben? Auf welchem Weg siehst du Debugs in einer SSH-Sitzung?
6. **Debug per ACL filtern.** Lege auf R3 `access-list 199 permit icmp host 192.168.1.10 host 10.255.0.3` an und schalte `debug ip packet 199 detail` ein. Pinge von H1 zuerst die 10.255.0.3, dann SRV (192.168.3.10). Danach `undebug all`.
   - **Erst vorhersagen:** Für welchen der beiden Pings zeigt R3 Debug-Zeilen?
   - **Prüfen:** Nur der Ping an 10.255.0.3 erscheint in `show logging`, mit ICMP-Typ 8. Der Ping an SRV läuft durch R3 hindurch und taucht nicht auf.
   - **Denkfrage:** Die ACL hätte den zweiten Ping ohnehin nicht erfasst. Aber selbst mit `debug ip packet` ohne ACL wäre er nicht erschienen. Warum?
7. **Conditional Debug.** R2 hat zwei OSPF-Nachbarn. Setze auf R2 zuerst die Bedingung `debug condition interface GigabitEthernet0/0`, prüfe sie mit `show debug condition` und schalte erst dann `debug ip ospf hello` ein. Lies nach 30 Sekunden `show logging`. Räume auf mit `undebug all` und `no debug condition all`.
   - **Erst vorhersagen:** Von welchen Nachbarn siehst du Hello-Meldungen, und was fragt der Router beim Löschen der Bedingung?
   - **Prüfen:** `show debug condition` listet „Condition 1: interface Gi0/0“. Im Puffer stehen nur Hellos auf Gi0/0. Beim Löschen warnt der Router, dass ohne Bedingung eine Flut von Meldungen folgen kann, und verlangt eine Bestätigung.
   - **Denkfrage:** Warum setzt du die Bedingung vor dem Debug und nimmst sie erst nach `undebug all` wieder weg?
8. **Werkzeug wählen.** Ordne jedem Symptom das Werkzeug zu, mit dem du anfängst, bevor du die Antwort aufklappst: (a) „Kleine Dateien gehen, große Downloads hängen.“ (b) „Seit heute Morgen ist der Standort langsam.“ (c) „Der OSPF-Nachbar kommt nicht hoch.“ (d) „Ein Server ist von einem VLAN aus erreichbar, vom anderen nicht.“ (e) „Die CPU des Routers steht auf 99 %.“

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Der zweite Ping zeigt **`.`**, der dritte **`U`**. Beim zweiten kennt jeder Router das Netz 192.168.3.0/24. R3 fragt per ARP nach .99, bekommt keine Antwort und verwirft das Paket stumm. Der Absender merkt nur den Timeout. Beim dritten hat schon R1 keine Route und schickt *Destination Unreachable* zurück. IOS begrenzt solche Meldungen auf eine pro 500 ms (`ip icmp rate-limit unreachable`), deshalb bleibt jede zweite aus.
- **Zu 2:** **`M`**, gesendet von R2 (10.0.12.2). Die Meldung ist ICMP Typ 3 Code 4 (*Fragmentation needed and DF set*) und enthält die MTU des nächsten Hops, hier 1400. Daraus berechnet der Absender die neue Paketgröße (Path MTU Discovery). Unterdrückt ein Gerät die Meldung, senden TCP-Verbindungen weiter zu große Segmente mit DF-Bit, die spurlos verschwinden: Verbindungsaufbau und kleine Pakete gehen, große Übertragungen hängen (*PMTUD Black Hole*).
- **Zu 3:** **Vier Zeilen**, eine je Router und eine für das Ziel. IOS sendet je Hop drei UDP-Pakete an hohe Ports ab 33434 und erhöht die TTL von 1 an. Router unterwegs antworten mit *Time Exceeded* (Typ 11). Das Ziel antwortet mit *Port Unreachable* (Typ 3 Code 3), weil auf dem Port nichts lauscht. Diese Antwort unterliegt wieder der Begrenzung auf eine Meldung pro 500 ms, daher geht die mittlere der drei Proben verloren.
- **Zu 4:** Traceroute endet in **Zeile 3 mit `!A`** (*administratively prohibited*): R3 prüft die ACL, bevor es die TTL auswertet, und verwirft die UDP-Probe. Ein Windows-Client mit `tracert` wäre durchgekommen, weil `permit icmp any any` seine Echo-Pakete erlaubt. Dasselbe Netz liefert also je nach Werkzeug ein anderes Bild. `!H` hieße *Host unreachable* (keine Route), `!N` *Network unreachable*, `*` keine Antwort.
- **Zu 5:** **Nein.** `logging console informational` lässt nur Stufe 0 bis 6 auf die Konsole, Debug ist Stufe 7. Die Konsole ist langsam (9600 Baud) und wird Zeichen für Zeichen von der CPU bedient: Eine Debug-Flut blockiert den Router, bis er nicht mehr bedienbar ist. In einer SSH-Sitzung brauchst du `terminal monitor`, sonst siehst du gar nichts. Der Puffer ist der sichere Weg.
- **Zu 6:** Nur für den Ping an **10.255.0.3**. `debug ip packet` zeigt Pakete, die der Router im Prozess verarbeitet: Verkehr an ihn selbst oder von ihm. Durchgeleitete Pakete schaltet CEF, ohne dass der Prozess sie sieht. Wer Transitverkehr sehen will, nimmt NetFlow, einen Mitschnitt (EPC, SPAN) oder ACL-Zähler, nicht `debug ip packet`.
- **Zu 7:** Nur von dem Nachbarn auf **Gi0/0**. Die Reihenfolge schützt dich: Ist das Debug zuerst aktiv, läuft es für einen Moment ungefiltert. Aus demselben Grund fragt der Router beim Löschen der Bedingung nach, denn ein noch laufendes Debug wäre danach wieder unbegrenzt.
- **Zu 8:** (a) **Ping mit Größe und DF-Bit**, Verdacht MTU. (b) **Syslog und Schnittstellenzähler**, dann NetFlow: erst feststellen, was sich geändert hat. (c) **`show ip ospf interface` und `show ip ospf neighbor`**, erst danach gezielt `debug ip ospf adj` mit Bedingung. (d) **Traceroute von beiden Quellen** und ACL-Zähler: Wo trennen sich die Wege? (e) **`show processes cpu sorted`**, auf keinen Fall ein Debug: Ein Debug erhöht die Last weiter. Grundregel: erst `show`, dann eingegrenztes `debug`.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** H1 erreicht SRV nicht. Der Ping von H1 zeigt `U.U.U`.

**Ticket 2:** Der Ping von H1 zu SRV geht, aber Traceroute bricht in Zeile 3 mit `!A` ab. Das Monitoring meldet den Standort deshalb als gestört.

**Ticket 3:** Anwender melden: Anmelden am Server geht, große Dateien übertragen hängt. `ping 192.168.3.10 size 1500 df-bit` von H1 zeigt nur Punkte, kein `M`.

**Ticket 4:** Auf R1 läuft `debug ip icmp` laut `show debugging`, aber `show logging` zeigt keine einzige Debug-Zeile.

## Verifikation
```
ping 192.168.3.10                        ! auf H1
ping 192.168.3.10 size 1500 df-bit       ! auf H1
traceroute 192.168.3.10                  ! auf H1
show access-lists TRANSIT                ! auf R3
show ip interface Gi0/0 | include unreach
show logging
show debugging
show debug condition
```

| Befehl | Das solltest du sehen |
|---|---|
| Ping H1 → SRV | `!!!!!` |
| Ping H1 → SRV mit 1500 Byte und DF-Bit | `M.M.M`, Meldung von 10.0.12.2 |
| Traceroute H1 → SRV | vier Zeilen, kein `!A` |
| `show logging` auf R1 bis R3 | „Buffer logging: level debugging“, „Console logging: level informational“ |
| `show debugging` am Ende | leer |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Ein Ping zeigt `.!!!!`. Ist das ein Fehler?
<details><summary>Antwort</summary>

**Meist nicht.** Das erste Paket geht verloren, während ein Gerät auf dem Weg die MAC-Adresse per ARP auflöst. Beim zweiten Versuch steht `!!!!!`. Bleibt der erste Punkt bei jeder Wiederholung, liegt es nicht an ARP.

</details>

2. Traceroute zeigt in Zeile 4 `* * *`, in Zeile 5 antwortet das Ziel. Was schließt du daraus?
<details><summary>Antwort</summary>

**Hop 4 leitet weiter, antwortet aber nicht selbst.** Er sendet kein *Time Exceeded*, etwa wegen `no ip unreachables`, einer ACL für eigene ICMP-Meldungen oder CoPP. Solange spätere Hops antworten, ist das kein Ausfall. Ein Fehler wäre es erst, wenn ab einer Zeile nur noch Sterne kommen.

</details>

3. Du willst auf einem produktiven Router sehen, warum eine OSPF-Nachbarschaft auf Gi0/2 flattert. Welche Schritte in welcher Reihenfolge?
<details><summary>Antwort</summary>

**(1)** `show`-Befehle und Syslog zuerst. **(2)** `logging buffered … debugging`, Konsole begrenzen. **(3)** `debug condition interface Gi0/2`, mit `show debug condition` prüfen. **(4)** `debug ip ospf adj`. **(5)** Auswerten mit `show logging`. **(6)** `undebug all`, dann `no debug condition all`. Dazu vorher ein Rückweg: Sitzung mit `terminal monitor` und die Möglichkeit, `u all` blind zu tippen.

</details>

4. Was ändert `logging trap warnings`?
<details><summary>Antwort</summary>

**Nur, was an den Syslog-Server geht.** Jedes Ziel hat eine eigene Stufe: `logging console`, `logging monitor` (VTY), `logging buffered`, `logging trap` (Server). Die Stufe ist eine Obergrenze: `warnings` (4) schickt 0 bis 4. Merkhilfe für 0 bis 7: Emergency, Alert, Critical, Error, Warning, Notification, Informational, Debugging.

</details>

## Prüfungsbezug
- Ping-Zeichen: `!` Antwort, `.` Timeout, `U` Unreachable, `M` Fragmentierung nötig, `Q` Source Quench, `?` unbekannt.
- Traceroute in IOS: UDP ab Port 33434, TTL steigt; unterwegs *Time Exceeded*, am Ziel *Port Unreachable*. `!A` ACL, `!H` Host, `!N` Netz.
- Erweiterter Ping: Quelle, Größe, DF-Bit, Sweep, Wiederholungen; damit prüfst du Rückweg und MTU.
- Debug: Stufe 7. Ziele einzeln begrenzen (`console`, `monitor`, `buffered`, `trap`). `terminal monitor` für VTY.
- Conditional Debug: `debug condition interface …`, `show debug condition`, Bedingung vor dem Debug setzen.
- `debug ip packet` zeigt nur prozessgeschaltete Pakete, mit ACL einschränken.

## Hinweis zum Image

Welche Debugs eine Bedingung aus `debug condition` beachten, hängt vom Image ab. Zeigt dein IOSv in Schritt 7 trotz Bedingung Hellos beider Nachbarn, dann ist der Ablauf (Bedingung setzen, prüfen, Debug, aufräumen) trotzdem das, was die Prüfung abfragt. Die Filterung per ACL aus Schritt 6 funktioniert in jedem Image. Auf IOS XE heißt das neuere Verfahren `debug platform condition`.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/33-Diagnose-Ping-Traceroute-Debug/`](../../CML-Labs/33-Diagnose-Ping-Traceroute-Debug/).
