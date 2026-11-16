# Lab 35 – IP SLA vertieft: Tracking mit Floating Static, UDP-Jitter mit Responder, TCP-Connect

**Dauer:** 90 min · **Niveau:** mittel · **Nodes:** 5× iosv

Lab 04 nutzt IP SLA nur als Zulieferer für PBR. Ziel 4.4 verlangt, IP SLA selbst zu konfigurieren und zu prüfen. Hier baust du einen Standort mit zwei Providern: Eine Messung überwacht den Weg über ISP1 und schaltet bei einem Ausfall *hinter* dem Provider-Router auf ISP2 um. Dabei läufst du absichtlich in die zwei klassischen Fehler (Messung nicht gestartet, Messung folgt der Umschaltung). Danach misst du Jitter und Paketverlust mit einem Responder und die Antwortzeit eines TCP-Dienstes.

**Lernziele:** Nach diesem Lab kannst du …

- Eine IP-SLA-Messung anlegen, starten und ihren Zustand in `show ip sla statistics` lesen.
- Eine statische Route per `track` an eine Messung binden und mit einer Floating Static Route absichern.
- Begründen, warum das Messziel fest über den überwachten Weg geroutet sein muss.
- UDP-Jitter mit `ip sla responder` einrichten und Jitter, Verlust und Laufzeit je Richtung ablesen.
- `reachability` und `state` beim Tracking unterscheiden und Schwellwerte (`threshold`, `timeout`, `frequency`) einordnen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::4.4` | IP SLA | 22 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
                    ┌──── R2 (ISP1) ────┐
              Gi0/1 │ Gi0/0       Gi0/1 │ Gi0/0
  H1 ──── R1 ───────┤                   ├─────── R4   Lo0 10.255.0.4 (Dienst)
     Gi0/0    Gi0/2 │ Gi0/0       Gi0/1 │ Gi0/1       Lo1 10.255.1.4 (Messziel)
                    └──── R3 (ISP2) ────┘
```

| Link | Netz |
|---|---|
| H1 – R1 Gi0/0 | 192.168.1.0/24 (H1 .10, R1 .1) |
| R1 Gi0/1 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R1 Gi0/2 – R3 Gi0/0 | 10.0.13.0/30 (.1/.2) |
| R2 Gi0/1 – R4 Gi0/0 | 10.0.24.0/30 (.1/.2) |
| R3 Gi0/1 – R4 Gi0/1 | 10.0.34.0/30 (.1/.2) |

R2, R3 und R4 sind **fertig konfiguriert** (statische Routen). R4 steht für das Internet: Loopback0 10.255.0.4 ist der Dienst, den H1 erreichen will, Loopback1 10.255.1.4 dient nur als Messziel. Telnet auf R4 ist offen (Passwort `cisco`). R1 hat noch keine Route nach außen, das ist deine Aufgabe.

**Ausfall simulieren:** `shutdown` auf **R4 Gi0/0**. Der Link R1–R2 bleibt dabei up, R1 merkt also von sich aus nichts. Genau diesen Fall soll IP SLA abdecken.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A. Bei **Erst vorhersagen** schreibst du deine Erwartung auf, *bevor* du den Befehl eingibst. Lag die Vorhersage daneben, hast du genau die Stelle gefunden, an der dein Modell noch nicht stimmt. Die Auflösung steht ebenfalls bei den Antworten.

1. **Das Problem sehen.** Setze auf R1 `ip route 0.0.0.0 0.0.0.0 10.0.12.2` und als Ersatz `ip route 0.0.0.0 0.0.0.0 10.0.13.2 10`. Prüfe `ping 10.255.0.4` von H1. Schalte dann R4 Gi0/0 ab.
   - **Erst vorhersagen:** Schaltet R1 auf ISP2 um?
   - **Prüfen:** Vor dem Ausfall geht der Ping. Danach nicht mehr: `show ip route 0.0.0.0` auf R1 zeigt weiter 10.0.12.2, Gi0/1 ist up/up. Schalte R4 Gi0/0 wieder ein.
   - **Denkfrage:** Unter welcher Bedingung nimmt ein Router eine statische Route mit Next-Hop-Adresse aus der Tabelle?
2. **Messung anlegen und starten.** Auf R1: `ip sla 1`, darin `icmp-echo 10.255.1.4 source-interface GigabitEthernet0/1`, `threshold 500`, `timeout 1000`, `frequency 5`. Sieh dir `show ip sla summary` an, **bevor** du `ip sla schedule 1 life forever start-time now` setzt.
   - **Erst vorhersagen:** In welchem Zustand steht die Messung ohne `schedule`?
   - **Prüfen:** Ohne `schedule`: Zustand `Pending`, keine Messwerte. Mit `schedule`: `Active`. Der Return Code ist aber noch `Timeout` oder `No connection`, denn R1 hat keine brauchbare Route zum Messziel.
   - **Denkfrage:** `frequency`, `timeout` und `threshold` stehen in einer festen Größenbeziehung. In welcher, und in welcher Einheit ist jeder Wert?
3. **Messziel festnageln.** Setze auf R1 `ip route 10.255.1.4 255.255.255.255 10.0.12.2`.
   - **Prüfen:** `show ip sla statistics 1` zeigt `Latest operation return code: OK` und einen steigenden Zähler bei den Erfolgen.
   - **Denkfrage:** Diese Host-Route wirkt jetzt überflüssig, die Default-Route zeigt ja ohnehin auf ISP1. Hebe dir die Frage für Schritt 5 auf.
4. **Route an die Messung binden.** `track 1 ip sla 1 reachability`. Ersetze die erste Default-Route durch `ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1`. Starte auf H1 `ping 10.255.0.4 repeat 1000` und schalte R4 Gi0/0 ab.
   - **Erst vorhersagen:** Wie viele Pings gehen ungefähr verloren, bis ISP2 übernimmt?
   - **Prüfen:** Nach wenigen Sekunden meldet R1 `%TRACK-…-STATE: 1 ip sla 1 reachability Up -> Down`. `show ip route 0.0.0.0` zeigt 10.0.13.2 mit Distanz 10. Der Ping läuft weiter. Schalte R4 Gi0/0 wieder ein und beobachte die Rückkehr.
   - **Denkfrage:** Woraus setzt sich die Umschaltzeit zusammen?
5. **Die Falle: Messung folgt der Umschaltung.** Entferne die Host-Route aus Schritt 3 (`no ip route 10.255.1.4 255.255.255.255 10.0.12.2`). Schalte R4 Gi0/0 erneut ab und beobachte R1 eine Minute lang.
   - **Erst vorhersagen:** Was passiert mit `track 1`, sobald die Default-Route auf ISP2 zeigt?
   - **Prüfen:** Das Log zeigt abwechselnd `Up -> Down` und `Down -> Up`, die Default-Route springt alle paar Sekunden. Setze die Host-Route wieder und schalte R4 Gi0/0 ein.
   - **Denkfrage:** Erkläre den Kreislauf in drei Sätzen.
6. **Flattern dämpfen.** Setze unter `track 1` den Befehl `delay down 10 up 30`.
   - **Prüfen:** `show track 1` nennt beide Verzögerungen. Bei einem kurzen Ausfall unter 10 Sekunden bleibt die Route stehen.
   - **Denkfrage:** Warum wählt man die Verzögerung für `up` meist länger als für `down`?
7. **UDP-Jitter mit Responder.** Auf R1: `ip sla 2` mit `udp-jitter 10.255.1.4 16384 num-packets 20 interval 20`, `threshold 500`, `frequency 30`, dazu der `schedule`. Sieh dir das Ergebnis an und setze **erst dann** auf R4 `ip sla responder`.
   - **Erst vorhersagen:** Was meldet die Messung, solange der Responder fehlt?
   - **Prüfen:** Ohne Responder: Return Code `No connection`. Mit Responder: `OK`, und `show ip sla statistics 2` zeigt Laufzeit, Jitter und Paketverlust getrennt nach Richtung (SD = Source to Destination, DS = zurück). `show ip sla responder` auf R4 zählt die Kontrollnachrichten.
   - **Denkfrage:** Warum braucht `udp-jitter` einen Responder, `icmp-echo` aber nicht? Welchen Vorteil hat der Responder für die Genauigkeit?
8. **TCP-Connect.** Auf R1: `ip sla 3` mit `tcp-connect 10.255.1.4 23 control disable`, `frequency 30`, dazu der `schedule`.
   - **Prüfen:** `show ip sla statistics 3` zeigt `OK` und die Dauer des Verbindungsaufbaus.
   - **Denkfrage:** Wozu dient `control disable` hier?
9. **`state` gegen `reachability`.** Lege `track 2 ip sla 2 state` an. Setze dann in `ip sla 2` testweise `threshold 1`. (Dazu musst du die Messung stoppen: `no ip sla schedule 2 …`, ändern, neu starten.)
   - **Erst vorhersagen:** Die Jitter-Messung funktioniert weiter. Welchen Zustand zeigt `track 2`?
   - **Prüfen:** `show ip sla statistics 2`: Return Code `Over threshold`. `show track 2`: `Down`. Ein `track … reachability` auf dieselbe Messung bliebe `Up`. Setze `threshold 500` zurück.
   - **Denkfrage:** Wann nimmst du `state`, wann `reachability`?
10. **Melden lassen.** Setze `ip sla logging traps` und `ip sla reaction-configuration 1 react timeout threshold-type immediate action-type trapOnly`. Schalte R4 Gi0/0 kurz ab.
   - **Prüfen:** Im Log von R1 erscheint eine `%RTT-…`-Meldung zur Messung 1. `show ip sla reaction-configuration 1` nennt Reaktion und Schwelltyp.

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** **Nein.** Eine statische Route bleibt in der Tabelle, solange der Next-Hop rekursiv auflösbar ist, also solange das Ausgangs-Interface up ist. Ein Ausfall einen Hop weiter verändert daran nichts. Der Router braucht eine Messung, die den ganzen Weg prüft.
- **Zu 2:** **`Pending`.** Eine Messung ohne `schedule` läuft nie. Das ist der häufigste IP-SLA-Fehler überhaupt. Zu den Werten: `frequency` in Sekunden, `timeout` und `threshold` in Millisekunden. Es gilt threshold ≤ timeout < frequency. `timeout` entscheidet über Erfolg oder Misserfolg, `threshold` nur darüber, ob ein Erfolg als „zu langsam“ gilt.
- **Zu 4:** Rund **zwei bis drei Pings** bei einem Ping pro Sekunde und ohne `delay`: bis zu 5 Sekunden bis zur nächsten Messung, 1 Sekunde Timeout, dann reagiert das Track-Objekt und die Routing-Tabelle wird neu berechnet. Wer schneller umschalten will, senkt `frequency` und `timeout`, zahlt dafür aber mit mehr Fehlalarmen.
- **Zu 5:** Die Messung fällt aus, `track 1` geht Down, die Default-Route wechselt auf ISP2. Ohne Host-Route erreicht die Messung ihr Ziel jetzt über ISP2 und ist erfolgreich, `track 1` geht Up, die Default-Route wechselt zurück auf den kaputten ISP1. Dort fällt die Messung wieder aus, und alles beginnt von vorn. Die Host-Route zwingt die Messung dauerhaft auf den Weg, den sie überwachen soll. Deshalb nimmt man ein eigenes Messziel und nicht die Adresse des eigentlichen Dienstes.
- **Zu 6:** Ein Ausfall soll schnell erkannt werden, die Rückkehr aber erst gelten, wenn der Weg eine Weile stabil ist. Sonst pendelt der Verkehr bei einer wackligen Leitung ständig hin und her, und jede Umschaltung kostet Verbindungen.
- **Zu 7:** **`No connection`.** `udp-jitter` handelt vor jeder Messung über die Kontrollverbindung (UDP 1967) aus, auf welchem Port der Responder lauschen soll. Ohne Responder antwortet niemand auf dem UDP-Port. `icmp-echo` beantwortet jedes IP-Gerät von sich aus. Der Responder setzt außerdem Zeitstempel beim Empfang und beim Senden. So lässt sich seine eigene Bearbeitungszeit herausrechnen und die Laufzeit je Richtung bestimmen.
- **Zu 8:** Port 23 beantwortet der Telnet-Dienst von R4 selbst. `control disable` schaltet die Kontrollverbindung zum Responder ab, die sonst vorab versucht würde. So misst du auch gegen Geräte, die gar kein Cisco-Router sind, etwa einen Webserver auf Port 443.
- **Zu 9:** **`Down`.** `reachability` ist Up bei den Return Codes `OK` und `Over threshold`, `state` nur bei `OK`. Nimm `reachability`, wenn es um „Weg da oder nicht“ geht, etwa für eine Ersatzroute. Nimm `state`, wenn auch ein zu langsamer Weg als Ausfall zählen soll, etwa für Sprachverkehr.

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** Der gesamte Verkehr von H1 läuft über ISP2, obwohl ISP1 in Ordnung ist. `show track 1` auf R1 steht auf `Down`.

**Ticket 2:** Sobald Ticket 1 gelöst ist: `show ip route 0.0.0.0` auf R1 zeigt zwei Next-Hops. Ein Teil der Verbindungen läuft weiter über ISP2.

**Ticket 3:** Die Jitter-Messung (IP SLA 2) liefert seit dem letzten Wartungsfenster nur `No connection`.

**Ticket 4:** Sobald Ticket 3 gelöst ist: `show track 2` bleibt `Down`, obwohl die Jitter-Messung Werte liefert.

## Verifikation
```
show ip sla summary
show ip sla configuration 1
show ip sla statistics [1|2|3]
show track
show ip route 0.0.0.0
show ip route track-table
show ip sla responder                 ! auf R4
show ip sla reaction-configuration 1
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip sla summary` | Messungen 1 bis 3 `Active`, Return Code `OK` |
| `show track 1` | `Reachability is Up`, Verzögerung 10/30 Sekunden |
| `show ip route 0.0.0.0` im Normalfall | nur 10.0.12.2, Distanz 1 |
| dasselbe bei abgeschaltetem R4 Gi0/0 | nur 10.0.13.2, Distanz 10 |
| `show ip sla statistics 2` | Jitter und Verlust für SD und DS, Return Code `OK` |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Eine Messung zeigt `Latest operation return code: Timeout`, obwohl ein Ping von der Konsole an dasselbe Ziel geht. Was prüfst du?
<details><summary>Antwort</summary>

**Die Quelle.** Der Ping von der Konsole nimmt die Adresse des Ausgangs-Interface. Die Messung nimmt, was unter `source-interface` oder `source-ip` steht. Hat die Gegenseite keine Rückroute zu dieser Adresse, oder ist die Messung in einer VRF (`vrf …` in der Messung fehlt), scheitert nur die Messung.

</details>

2. Warum lässt sich eine laufende Messung nicht ändern?
<details><summary>Antwort</summary>

**Weil ihre Parameter mit dem Start festgeschrieben werden.** Erst `no ip sla schedule N` (oder die Messung löschen), dann ändern, dann neu starten. In der Prüfung zeigt ein Exhibit oft genau die Fehlermeldung dazu.

</details>

3. HSRP soll die Priorität senken, wenn der Uplink zwar up ist, das Internet aber nicht erreichbar. Welche Bausteine brauchst du?
<details><summary>Antwort</summary>

**IP SLA, Track-Objekt, HSRP-Tracking.** `ip sla` misst ein Ziel hinter dem Uplink, `track 1 ip sla 1 reachability` übersetzt das Ergebnis in Up/Down, `standby 1 track 1 decrement 20` senkt die Priorität. Dazu `preempt` auf dem Partner, sonst übernimmt er nicht.

</details>

4. Welche Messung nimmst du für Sprachqualität, und was liefert sie zusätzlich, wenn du einen Codec angibst?
<details><summary>Antwort</summary>

**`udp-jitter` mit `codec`**, etwa `udp-jitter … codec g711ulaw`. Sie wählt Paketgröße und Abstand passend zum Codec und berechnet aus Laufzeit, Jitter und Verlust die Kennzahlen **MOS** und **ICPIF**.

</details>

## Prüfungsbezug
- Ablauf: Messung definieren, mit `ip sla schedule` starten, mit `show ip sla statistics` prüfen. Ohne Schedule `Pending`.
- Einheiten: `frequency` Sekunden, `timeout` und `threshold` Millisekunden; threshold ≤ timeout < frequency.
- Tracking: `track N ip sla M reachability` (OK oder Over threshold) gegen `state` (nur OK); `delay down/up`.
- Floating Static: Ersatzroute mit höherer Distanz, Hauptroute mit `track`.
- Responder: `ip sla responder` auf dem Ziel, Kontrollverbindung UDP 1967; nötig für `udp-jitter`, optional für `tcp-connect` und `udp-echo`.
- Messarten: icmp-echo, udp-jitter, udp-echo, tcp-connect, http, dns, path-echo.

## Hinweis zum Image

In einer virtuellen Umgebung bleibt die Gegenseite eines Links up, wenn du ein Interface abschaltest. Deshalb simulierst du den Ausfall auf R4 und nicht auf R2. Die genauen Texte der Return Codes und der `%TRACK`-Meldungen können je nach IOSv-Version leicht abweichen.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
