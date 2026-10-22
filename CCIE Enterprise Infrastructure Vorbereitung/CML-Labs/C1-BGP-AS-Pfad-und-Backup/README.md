# Lab C1 – BGP: allowas-in, private AS, GTSM und bedingte Ankündigung

**Dauer:** 120 min · **Niveau:** schwer · **Nodes:** 5× iosv

Ein Unternehmen mit dem privaten AS 65001 hängt mit Zentrale (HQ) und Filiale (BR) am Provider ISP1, die Zentrale zusätzlich an ISP2 als Backup. Weil beide Standorte denselben AS nutzen, verwirft die Filiale die Routen der Zentrale. Du löst das mit `allowas-in`, entfernst den privaten AS beim Provider, schützt eine Sitzung mit GTSM und kündigst das Netz der Zentrale bei ISP2 nur an, wenn ISP1 ausfällt.

**Lernziele:** Nach diesem Lab kannst du …

- Erklären, warum ein eBGP-Router Routen mit dem eigenen AS im Pfad verwirft, und das mit `allowas-in` gezielt lösen.
- Private AS-Nummern beim Provider mit `remove-private-as` entfernen und das im AS-Pfad nachweisen.
- Eine Backup-Ankündigung mit `advertise-map` und `non-exist-map` bauen und den Umschwenk messen.
- Eine eBGP-Sitzung mit GTSM (`ttl-security`) schützen und erklären, warum beide Seiten es brauchen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::1.5.c` | BGP: Policies, Communities und Anbindungsdesigns | 6 |
| `Ziel::1.5.d` | BGP: AS-Path-Manipulation | 5 |
| `Ziel::1.5.f` | BGP: Soft Reconfiguration, Route Refresh und Schutz | 4 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
   BR  AS 65001                            NET  AS 64600
   Lo1 203.0.113.1/24                      Lo1 192.0.2.1/24
        | Gi0/0                      Gi0/0 /          \ Gi0/1
        |                                 /            \
        | Gi0/1                    Gi0/2 /              \ Gi0/1
   ISP1  AS 64501 ----------------------+          ISP2  AS 64502
        | Gi0/0                                          | Gi0/0
        |                                                |
        | Gi0/0                                          | Gi0/1
        +------------------- HQ  AS 65001 ---------------+
                             Lo1 198.51.100.1/24
```

| Link | Netz |
|---|---|
| HQ Gi0/0 – ISP1 Gi0/0 | 10.0.11.0/30 (ISP1 .1, HQ .2) |
| HQ Gi0/1 – ISP2 Gi0/0 | 10.0.12.0/30 (ISP2 .1, HQ .2) |
| BR Gi0/0 – ISP1 Gi0/1 | 10.0.21.0/30 (ISP1 .1, BR .2) |
| ISP1 Gi0/2 – NET Gi0/0 | 10.0.31.0/30 (ISP1 .1, NET .2) |
| ISP2 Gi0/1 – NET Gi0/1 | 10.0.32.0/30 (ISP2 .1, NET .2) |
| Netze der Standorte (Loopback1) | HQ 198.51.100.0/24, BR 203.0.113.0/24, NET 192.0.2.0/24 |

HQ und BR gehören zum selben Unternehmen und nutzen denselben privaten AS 65001, haben aber keine direkte Verbindung: Ihr Verkehr läuft über ISP1. NET steht für das Internet. ISP1 ist der Hauptprovider der Zentrale, ISP2 nur Backup. Ausgehend soll HQ ISP1 bevorzugen. Eingehend soll ISP2 das Netz 198.51.100.0/24 nur kennen, wenn ISP1 ausgefallen ist. Als Merker dafür schickt ISP1 der Zentrale eine Default-Route: Solange sie da ist, steht die Verbindung zu ISP1.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **eBGP-Sitzungen aufbauen.** Konfiguriere die Sitzungen laut Skizze: HQ (`router bgp 65001`) zu ISP1 und ISP2, BR (`router bgp 65001`) zu ISP1, ISP1 (`router bgp 64501`) zu HQ, BR und NET, ISP2 (`router bgp 64502`) zu HQ und NET, NET (`router bgp 64600`) zu ISP1 und ISP2. Setze überall eine `bgp router-id` und kündige mit `network` die Loopback1-Netze von HQ, BR und NET an.
   - **Prüfen:** `show ip bgp summary` zeigt auf ISP1 drei, auf ISP2 und NET je zwei Nachbarn mit einer Präfixzahl statt Active oder Idle. NET kennt 198.51.100.0/24 und 203.0.113.0/24.
   - **Denkfrage:** BR hat eine Sitzung zu ISP1, und ISP1 kennt 198.51.100.0/24. Warum steht das Netz trotzdem nicht in `show ip bgp` auf BR?
2. **Eigenen AS im Pfad zulassen.** Auf BR `neighbor 10.0.21.1 allowas-in 1`, auf HQ `neighbor 10.0.11.1 allowas-in 1`.
   - **Prüfen:** BR hat 198.51.100.0/24 mit dem AS-Pfad `64501 65001`, HQ hat 203.0.113.0/24 über ISP1. `ping 198.51.100.1 source Loopback1` auf BR klappt.
   - **Denkfrage:** Was zählt die Zahl hinter `allowas-in`, und welches Risiko gehst du damit ein?
3. **Privaten AS beim Provider entfernen.** Auf ISP1 `neighbor 10.0.31.2 remove-private-as`, auf ISP2 `neighbor 10.0.32.2 remove-private-as`. Danach auf ISP1 und ISP2 `clear ip bgp * soft out`.
   - **Prüfen:** `show ip bgp 198.51.100.0` auf NET zeigt die Pfade `64501` und `64502`, beide ohne 65001.
   - **Denkfrage:** Warum entfernt ISP1 den privaten AS nur in Richtung NET und nicht auch in Richtung BR?
4. **Ausgehend ISP1 bevorzugen und Transit verhindern.** Auf HQ: `route-map LP-ISP1 permit 10` mit `set local-preference 200`, als `neighbor 10.0.11.1 route-map LP-ISP1 in`. Dazu ein Ausgangsfilter zu beiden Providern: `ip prefix-list OWN seq 5 permit 198.51.100.0/24` und `neighbor … prefix-list OWN out`. Danach `clear ip bgp * soft`.
   - **Prüfen:** `show ip bgp 192.0.2.0` auf HQ: bester Pfad über 10.0.11.1 mit LocPrf 200.
   - **Denkfrage:** Warum braucht HQ den Ausgangsfilter, obwohl es nur ein eigenes Netz hat?
5. **Default-Route von ISP1 als Merker.** Auf ISP1 `neighbor 10.0.11.2 default-originate`.
   - **Prüfen:** HQ hat 0.0.0.0/0 nur von ISP1 (`show ip bgp 0.0.0.0`).
   - **Denkfrage:** Warum darf ISP2 der Zentrale keine Default-Route schicken, wenn sie als Merker für ISP1 dienen soll?
6. **Backup nur bei Ausfall ankündigen.** Auf HQ: `ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0`, `route-map ISP1-DEFAULT permit 10` mit `match ip address prefix-list DEFAULT` und `route-map ADV-BACKUP permit 10` mit `match ip address prefix-list OWN`. Dann `neighbor 10.0.12.1 advertise-map ADV-BACKUP non-exist-map ISP1-DEFAULT`.
   - **Prüfen:** `show ip bgp neighbors 10.0.12.1 | include Condition` zeigt den Status *Withdraw*. ISP2 hat 198.51.100.0/24 nicht mehr von HQ, NET kennt das Netz nur über ISP1.
   - **Denkfrage:** Warum dauert es nach einem Ausfall bis zu einer Minute, bis die Backup-Route erscheint?
7. **Ausfall testen.** Auf HQ unter `interface GigabitEthernet0/0` `shutdown`. Warte bis zu 60 Sekunden.
   - **Prüfen:** Der Status springt auf *Advertise*, NET erreicht 198.51.100.1 über ISP2 (`traceroute 198.51.100.1 source Loopback1` auf NET). Danach `no shutdown`, der Status geht zurück auf *Withdraw*.
   - **Denkfrage:** Wie kommt der Verkehr von BR zur Zentrale, solange der Link HQ–ISP1 ausgefallen ist?
8. **GTSM zu ISP2.** Auf HQ `neighbor 10.0.12.1 ttl-security hops 1`, auf ISP2 `neighbor 10.0.12.2 ttl-security hops 1`.
   - **Prüfen:** Die Sitzung baut sich nach dem Reset wieder auf. `show ip bgp neighbors 10.0.12.1` auf HQ nennt eine minimale eingehende TTL von 254.
   - **Denkfrage:** Was passiert, wenn nur eine Seite `ttl-security` konfiguriert?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** **Weil der eigene AS 65001 schon im AS-Pfad steht.** Das ist der Schleifenschutz von eBGP: BR sieht `64501 65001` und verwirft die Route beim Empfang. ISP1 schickt sie trotzdem, entschieden wird beim Empfänger. `show ip bgp neighbors 10.0.21.1` auf BR führt solche Präfixe bei den abgelehnten als AS-Pfad-Schleife.
- **Zu 2:** **Wie oft der eigene AS im Pfad stehen darf, hier einmal.** Das Risiko: Der Schleifenschutz ist für diesen Nachbarn teilweise aus. Kommt eine eigene Route über einen Umweg zurück, in dem 65001 nur einmal steht, nimmt BR sie an. Deshalb so klein wie möglich und nur bei den Nachbarn, die es brauchen.
- **Zu 3:** **Weil der private AS nur das Internet nicht erreichen soll, im Provider-Netz aber gebraucht wird.** Gegenüber BR ist 65001 ein gültiger Kunden-AS. Würde ISP1 ihn auch dort entfernen, bräuchte BR zwar kein `allowas-in` mehr, verlöre aber den Schleifenschutz für diese Routen. Ohne `all` entfernt `remove-private-as` private AS übrigens nur, wenn der Pfad ausschließlich aus privaten AS besteht.
- **Zu 4:** **Damit HQ kein Transit-AS wird.** Ohne Filter würde HQ die Routen von ISP1 an ISP2 weitergeben und umgekehrt, dazu das Netz der Filiale. Fällt beim Provider ein Link aus, liefe fremder Verkehr über die Zentrale. Der Filter lässt nur 198.51.100.0/24 hinaus.
- **Zu 5:** **Weil die Bedingung genau dann greifen soll, wenn die Verbindung zu ISP1 fehlt.** Bekäme HQ auch von ISP2 eine Default-Route, stünde 0.0.0.0/0 nach einem Ausfall von ISP1 weiter in der BGP-Tabelle, und die Backup-Ankündigung würde nie ausgelöst.
- **Zu 6:** **Weil der BGP-Scanner die Bedingungen nur periodisch prüft, standardmäßig alle 60 Sekunden.** Schneller wird der Umschwenk nicht über die Bedingung, sondern über die Erkennung des Ausfalls selbst: Ein Link-Down beendet die eBGP-Sitzung sofort (Fast External Fallover), bei einem Ausfall hinter einem Switch helfen BFD oder kürzere Timer.
- **Zu 7:** **Über ISP1, NET und ISP2.** BR hat 198.51.100.0/24 jetzt mit dem Pfad `64501 64600 64502`: ISP1 lernt das Netz von NET, und den privaten AS 65001 hat ISP2 entfernt. Weil 65001 nicht mehr im Pfad steht, bräuchte BR dafür nicht einmal `allowas-in`.
- **Zu 8:** **Die Sitzung kommt nicht zustande.** Die Seite mit `ttl-security hops 1` erwartet Pakete mit einer TTL von mindestens 254, die andere sendet eBGP standardmäßig mit TTL 1. Die Pakete werden verworfen, bevor BGP sie sieht. GTSM gehört deshalb immer auf beide Seiten, und es schließt `ebgp-multihop` für denselben Nachbarn aus.

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** BR erreicht das Netz der Zentrale nicht: `ping 198.51.100.1 source Loopback1` scheitert, und `show ip bgp` auf BR enthält 198.51.100.0/24 nicht, obwohl ISP1 das Netz kennt.

**Ticket 2:** Die BGP-Sitzung zwischen HQ und ISP2 bleibt down, obwohl `ping 10.0.12.1` von HQ klappt.

**Ticket 3:** Der Internet-Router NET sieht 198.51.100.0/24 und 203.0.113.0/24 mit dem privaten AS 65001 im Pfad.

**Ticket 4:** ISP2 bekommt 198.51.100.0/24 von HQ, obwohl ISP1 läuft. NET hat das Netz von beiden Providern in der BGP-Tabelle.

**Ticket 5:** Ausfalltest: Nach `shutdown` auf HQ Gi0/0 erreicht NET das Netz 198.51.100.0/24 auch nach zwei Minuten nicht. ISP2 bekommt die Backup-Route nie.

## Verifikation
```
show ip bgp summary
show ip bgp
show ip bgp 198.51.100.0
show ip bgp neighbors 10.0.12.1 | include Condition|TTL
ping 198.51.100.1 source Loopback1          ! auf BR und NET
traceroute 198.51.100.1 source Loopback1    ! auf NET, auch beim Ausfalltest
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip bgp 198.51.100.0` auf BR | Pfad `64501 65001`, gültig und best |
| `show ip bgp 198.51.100.0` auf NET | ein Pfad über ISP1 mit AS-Pfad `64501`, ohne 65001 |
| `show ip bgp 192.0.2.0` auf HQ | bester Pfad über 10.0.11.1 mit LocPrf 200 |
| `show ip bgp neighbors 10.0.12.1` auf HQ | Condition-Map mit Status Withdraw, GTSM mit minimaler TTL 254 |
| Ausfalltest (`shutdown` auf HQ Gi0/0) | nach höchstens 60 s Status Advertise, NET erreicht 198.51.100.1 über ISP2 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Zwei Standorte im selben AS sollen sich über einen Provider erreichen. Welche drei Lösungen gibt es, und wo werden sie konfiguriert?
<details><summary>Antwort</summary>

**`allowas-in` beim Kunden, `as-override` beim Provider oder eine Default-Route statt der Kundenrouten.** `allowas-in` lässt den eigenen AS im Pfad zu. Mit `as-override` ersetzt der Provider-Router den Kunden-AS durch seinen eigenen, typisch im MPLS-L3VPN. Mit einer Default-Route braucht der Standort die Routen des anderen gar nicht. Die ersten beiden schwächen den Schleifenschutz, bei mehrfach angebundenen Standorten gehört Site of Origin (SoO) dazu.

</details>

2. Ein Router soll nach einer Firmenübernahme vorübergehend unter dem alten AS 65002 mit einem Provider sprechen, intern aber AS 65001 sein. Wie löst du das?
<details><summary>Antwort</summary>

**Mit `neighbor … local-as 65002`, meist mit `no-prepend replace-as`.** Der Router meldet sich beim Nachbarn als 65002. `no-prepend` verhindert, dass 65002 in empfangene Routen eingefügt wird, `replace-as` ersetzt in gesendeten Routen den echten AS durch 65002. Mit `dual-as` akzeptiert der Router beide AS-Nummern, so kann der Provider in Ruhe umstellen.

</details>

3. HQ könnte das Netz bei ISP2 auch dauerhaft mit `as-path prepend` ankündigen. Was ist der Unterschied zur bedingten Ankündigung?
<details><summary>Antwort</summary>

**Prepending macht ISP2 nur unattraktiver, die bedingte Ankündigung versteckt den Weg ganz.** Mit Prepending sieht das Internet beide Wege. Provider, die Kundenrouten per Local Preference bevorzugen, schicken trotzdem über ISP2. Dafür schwenkt der Verkehr nach einem Ausfall sofort um. Die bedingte Ankündigung garantiert, dass ISP2 nur im Fehlerfall Verkehr bekommt, braucht dafür aber bis zu einer Scanner-Runde.

</details>

4. Was unterscheidet `remove-private-as` von `remove-private-as all replace-as`?
<details><summary>Antwort</summary>

**Ohne Zusatz entfernt IOS private AS nur, wenn der Pfad ausschließlich aus privaten AS besteht.** `all` entfernt sie auch aus gemischten Pfaden, `replace-as` ersetzt sie durch den eigenen AS, damit die Pfadlänge für die Best-Path-Wahl erhalten bleibt.

</details>

## Prüfungsbezug
- Schleifenschutz in eBGP: Steht der eigene AS im Pfad, wird die Route verworfen. Lösungen: `allowas-in` (Kunde), `as-override` (Provider).
- `remove-private-as [all] [replace-as]` entfernt private AS (64512 bis 65534) vor der Weitergabe ins Internet.
- Bedingte Ankündigung: `neighbor … advertise-map A non-exist-map B` (oder `exist-map`), geprüft vom BGP-Scanner, standardmäßig alle 60 s.
- GTSM: `ttl-security hops n` auf beiden Seiten, schließt `ebgp-multihop` aus.
- Local Preference wirkt nur im eigenen AS und wird auf eingehende Routen gesetzt (`route-map … in`).

## Hinweis zum Image

Die bedingte Ankündigung reagiert erst mit der nächsten Runde des BGP-Scanners. Warte beim Ausfalltest bis zu 60 Sekunden, bevor du einen Fehler vermutest.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-Konfiguration)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
