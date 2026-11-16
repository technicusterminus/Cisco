# Lab 36 – EEM-Applets: Ereignisse, Aktionen und die typischen Fallen

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel

Ziel 6.6 verlangt, ein EEM-Applet zu konstruieren, das konfiguriert, Fehler eingrenzt oder Daten sammelt. Lab 19 zeigt zwei Applets am Rand. Hier baust du sechs kleine Applets, eines je Ereignistyp, und lernst dabei die Stellen kennen, an denen Applets in der Praxis und in Prüfungs-Exhibits scheitern: fehlendes `enable`, die Sortierung der Aktionsnummern, Muster, die nie treffen, und die Bedeutung von `sync` und `skip`.

**Lernziele:** Nach diesem Lab kannst du …

- Ein Applet aus Ereignis (`event`) und nummerierten Aktionen (`action`) aufbauen und von Hand starten.
- Die Ereignistypen `none`, `syslog`, `cli` und `timer` passend zur Aufgabe wählen.
- Vorhersagen, in welcher Reihenfolge Aktionen laufen und in welchem Modus ein `cli command` ankommt.
- Bei `event cli` die Wirkung von `sync yes`, `sync no`, `skip` und `_exit_status` erklären.
- Ein Applet mit `show event manager …` und `debug event manager action cli` prüfen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::6.6` | EEM-Applets | 29 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **1.0 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R1 | Gi0/1 | R2 | Gi0/1 |

## Topologie

```
           Gi0/0  10.0.12.0/30  Gi0/0
      R1 ══════════════════════════════ R2
         ──────────────────────────────
           Gi0/1  10.0.21.0/30  Gi0/1      (Testlink für FLAPGUARD)
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R1 Gi0/1 – R2 Gi0/1 | 10.0.21.0/30 (.1/.2) |

Loopback0: R1 10.255.0.1, R2 10.255.0.2. OSPF 1 (Area 0) läuft **fertig konfiguriert** auf beiden Links, Netztyp Point-to-Point. Alle Applets baust du auf **R1**. R2 dient nur dazu, Ereignisse auszulösen: `clear ip ospf process` auf R2 lässt auf R1 beide Nachbarschaften kurz abreißen.

| Applet | Ereignis | Aufgabe |
|---|---|---|
| REPORT | `none` (von Hand) | OSPF-Nachbarn ausgeben |
| OSPF-DOWN | `syslog` | bei Nachbarverlust Daten in eine Datei sammeln |
| FLAPGUARD | `syslog` mit Zähler | flatternden Link abschalten |
| NO-DEBUG-ALL | `cli`, asynchron | einen gefährlichen Befehl sperren |
| BACKUP | `cli`, synchron | vor `write memory` eine Kopie ablegen |
| HEARTBEAT | `timer` | regelmäßig ein Lebenszeichen ins Log |

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A. Bei **Erst vorhersagen** schreibst du deine Erwartung auf, *bevor* du den Befehl eingibst. Lag die Vorhersage daneben, hast du genau die Stelle gefunden, an der dein Modell noch nicht stimmt. Die Auflösung steht ebenfalls bei den Antworten.

1. **Erstes Applet von Hand starten.** Lege `event manager applet REPORT` an mit `event none`, `action 1.0 cli command "enable"`, `action 2.0 cli command "show ip ospf neighbor"` und `action 3.0 puts "$_cli_result"`. Starte es mit `event manager run REPORT`.
   - **Prüfen:** Die Nachbartabelle erscheint auf der Konsole. `show event manager policy registered` listet REPORT mit dem Ereignistyp `none`.
   - **Denkfrage:** Was steht in `$_cli_result`, wenn mehrere `cli command`-Aktionen vorausgegangen sind?
2. **Die `enable`-Falle.** Ändere Aktion 2.0 auf `show running-config | include ^hostname` und entferne Aktion 1.0. Starte das Applet. Schalte dann `debug event manager action cli` ein und starte es noch einmal.
   - **Erst vorhersagen:** Welche Ausgabe liefert das Applet ohne `enable`?
   - **Prüfen:** Statt des Hostnamens erscheint eine Fehlermeldung des Parsers. Das Debug zeigt den Prompt `R1>`: Das Applet arbeitet im User-EXEC-Modus. Mit Aktion 1.0 erscheint `hostname R1`. Stelle den Stand aus Schritt 1 wieder her, `undebug all`.
   - **Denkfrage:** Auf einem Router mit AAA-Autorisierung für Befehle reicht `enable` nicht. Was braucht das Applet dort zusätzlich?
3. **Auf Syslog reagieren.** Setze global `file prompt quiet`. Lege OSPF-DOWN an: `event syslog pattern "OSPF-5-ADJCHG.*from FULL to"`, danach `enable`, zwei `show`-Befehle mit `| append flash:ospf-down.txt` und eine Syslog-Aktion mit `priority warnings`. Löse es aus: `clear ip ospf process` auf R2.
   - **Erst vorhersagen:** Wie oft läuft das Applet bei einem einzigen `clear` auf R2?
   - **Prüfen:** Im Log von R1 steht die EEM-Meldung zweimal, einmal je Link. `more flash:ospf-down.txt` zeigt die gesammelten Ausgaben. `show event manager history events` listet die Läufe mit Zeit und Ereignistyp.
   - **Denkfrage:** Das Muster ist ein regulärer Ausdruck. Was wäre passiert, wenn du `Gi0/1` statt `GigabitEthernet0/1` in ein Muster geschrieben hättest?
4. **Zählen und eingreifen.** Lege FLAPGUARD an: `event syslog pattern "OSPF-5-ADJCHG.*GigabitEthernet0/1 from FULL to" occurs 3 period 300`. Aktionen 1.0 bis 5.0: `enable`, `configure terminal`, `interface GigabitEthernet0/1`, `shutdown`, `end`. Aktion 6.0: Syslog mit `priority critical`. Führe auf R2 dreimal `clear ip ospf process` aus und warte jeweils, bis die Nachbarn wieder FULL sind.
   - **Erst vorhersagen:** Nach dem wievielten `clear` greift das Applet ein, und was passiert mit dem Link Gi0/0?
   - **Prüfen:** Nach dem dritten Abriss ist R1 Gi0/1 `administratively down`, im Log steht die kritische Meldung. Gi0/0 bleibt in Betrieb. Schalte Gi0/1 danach wieder ein.
   - **Denkfrage:** Warum ist ein Applet, das selbst in die Konfiguration eingreift, riskanter als eines, das nur Daten sammelt?
5. **Die Nummern-Falle.** Benenne in FLAPGUARD die Aktion `4.0` (`shutdown`) testweise in `10.0` um: `no action 4.0`, dann `action 10.0 cli command "shutdown"`. Sieh dir das Applet mit `show running-config | section FLAPGUARD` an.
   - **Erst vorhersagen:** An welcher Stelle der Reihenfolge steht Aktion 10.0?
   - **Prüfen:** Die Konfiguration zeigt die Reihenfolge 1.0, 10.0, 2.0, 3.0, 5.0, 6.0. `shutdown` käme direkt nach `enable` im EXEC-Modus an und würde abgelehnt. Stelle `action 4.0` wieder her und lösche `action 10.0`.
   - **Denkfrage:** Wie nummerierst du, damit das nie passiert?
6. **Einen Befehl sperren.** Lege NO-DEBUG-ALL an: `event cli pattern "^debug all" sync no skip yes` und eine Syslog-Aktion. Gib danach `debug all` ein.
   - **Erst vorhersagen:** Wird `debug all` ausgeführt?
   - **Prüfen:** Im Log steht die EEM-Meldung, `show debugging` bleibt leer. Der Befehl wurde verworfen.
   - **Denkfrage:** Was bedeuten `sync no` und `skip yes` genau? Und warum greift das Muster auch, wenn jemand nur `deb all` tippt?
7. **Vor dem Speichern sichern.** Lege BACKUP an: `event cli pattern "^write memory" sync yes`, Aktionen: `enable`, `copy running-config flash:backup.cfg`, eine Syslog-Meldung und zuletzt `action 4.0 set _exit_status "1"`. Gib `write memory` ein.
   - **Erst vorhersagen:** Löst auch `copy running-config startup-config` das Applet aus?
   - **Prüfen:** `dir flash:` zeigt `backup.cfg` mit aktuellem Zeitstempel, danach läuft das eigentliche `write memory` („Building configuration…“). `copy running-config startup-config` löst das Applet **nicht** aus.
   - **Denkfrage:** Was passiert bei `sync yes`, wenn `_exit_status` am Ende 0 ist oder gar nicht gesetzt wird?
8. **Zeitgesteuert.** Lege HEARTBEAT an: `event timer watchdog time 300` und eine Syslog-Aktion. Setze die Zeit zum Testen kurz auf 30.
   - **Prüfen:** Alle 30 Sekunden erscheint die Meldung. `show event manager policy registered` nennt den Timer. Stelle 300 wieder ein.
   - **Denkfrage:** Worin unterscheiden sich `watchdog`, `countdown` und `cron`?
9. **Einordnen.** Entscheide für drei Aufgaben, ob EEM das richtige Werkzeug ist, bevor du die Antwort aufklappst: (a) Bei jedem BGP-Nachbarverlust sofort `show ip bgp summary` auf dem betroffenen Router sichern. (b) Auf 400 Switches eine neue NTP-Konfiguration ausrollen. (c) Einmal pro Nacht die Konfiguration aller Router auf einen zentralen Server kopieren.

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Immer nur die Ausgabe des **letzten** `cli command`. Wer mehrere Ausgaben braucht, wertet sie nach jedem Befehl aus oder schreibt sie mit `| append` in eine Datei.
- **Zu 2:** Eine **Fehlermeldung**: `show running-config` gibt es im User-EXEC-Modus nicht. Jedes Applet öffnet eine eigene VTY-Sitzung auf Privilegstufe 1, deshalb ist `enable` fast immer Aktion 1. Mit AAA-Autorisierung braucht das Applet einen Benutzer, dem die Befehle erlaubt sind: `event manager session cli username <Name>`. Ohne ihn scheitern die Befehle an der Autorisierung, oft erst nach einem langen Timeout.
- **Zu 3:** **Zweimal**, denn R1 verliert zwei Nachbarschaften und schreibt zwei Meldungen. Syslog-Meldungen nennen Interfaces immer mit vollem Namen. Ein Muster mit `Gi0/1` trifft nie, das Applet bleibt stumm, und nichts weist auf den Fehler hin. Prüfe ein Muster immer gegen eine echte Zeile aus `show logging`.
- **Zu 4:** Nach dem **dritten** Abriss auf Gi0/1 innerhalb von 300 Sekunden. Gi0/0 bleibt unberührt, weil das Muster den Interface-Namen enthält. Zum Risiko: Ein Applet mit Eingriff kann sich selbst auslösen, im falschen Moment zuschlagen oder die Störung vergrößern (hier: Wenn beide Links flattern und beide Applets abschalten, ist der Standort offline). Sammeln ist ungefährlich, Eingreifen braucht Grenzen wie `occurs`, `period` und `ratelimit`.
- **Zu 5:** **Zwischen 1.0 und 2.0.** EEM sortiert die Bezeichner als Zeichenketten, nicht als Zahlen: „10.0“ kommt vor „2.0“. Nummeriere mit führenden Nullen (010, 020, 030) oder bleibe einstellig mit Lücken. In Exhibits ist das eine beliebte Falle.
- **Zu 6:** **Nein.** `sync no` heißt: Das Applet läuft unabhängig vom Befehl, und `skip` entscheidet allein, ob der Befehl ausgeführt wird (`skip yes` = verwerfen). Bei `sync yes` wartet die CLI auf das Applet, und dessen `_exit_status` entscheidet. Das Muster wird gegen den **vollständig ausgeschriebenen** Befehl geprüft. `deb all` wird vor dem Vergleich zu `debug all` ergänzt.
- **Zu 7:** **Nein**, das Muster passt nur auf `write memory`. Wer beide Wege abdecken will, braucht ein zweites Applet oder ein Muster mit Alternative. Zu `_exit_status`: Bei 0 oder ohne Zuweisung wird der ursprüngliche Befehl **nicht** ausgeführt, bei 1 schon. Ein synchrones Applet ohne diese Zeile schluckt also den Befehl. Beachte auch: Die Syslog-Meldung behauptet nur, dass gesichert wurde. Ob `copy` Erfolg hatte, prüft das Applet nicht.
- **Zu 8:** `watchdog` läuft alle N Sekunden immer wieder. `countdown` läuft einmal nach N Sekunden. `cron` läuft zu festen Zeiten nach Cron-Schreibweise, etwa `cron-entry "0 2 * * *"` für täglich 2 Uhr.
- **Zu 9:** (a) **EEM.** Das Ereignis entsteht auf dem Gerät, die Reaktion muss sofort und auch ohne Verbindung zur Zentrale erfolgen. (b) **Nicht EEM**, sondern ein agentenloses Werkzeug wie Ansible oder der Controller: Das ist eine zentrale, einmalige Änderung mit Kontrolle über den Erfolg. (c) **Beides möglich**, zentral ist besser: Ein Applet mit `timer cron` kann kopieren, aber 400 Applets muss jemand pflegen. Eine zentrale Sicherung sieht außerdem, welches Gerät sich nicht gemeldet hat.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Nach `write memory` meldet das Log „Sicherung … angestossen“, aber `dir flash:` zeigt keine `backup.cfg`.

**Ticket 2:** Gi0/1 flattert im Test dreimal in fünf Minuten. FLAPGUARD schreibt seine kritische Meldung, das Interface bleibt aber in Betrieb.

**Ticket 3:** OSPF-DOWN löst nie aus. `show event manager history events` enthält keinen Lauf dieses Applets, obwohl Nachbarschaften abreißen.

**Ticket 4:** Wer `debug all` eingibt, bekommt die Sperrmeldung im Log. `show debugging` zeigt danach trotzdem alle Debugs als aktiv.

## Verifikation
```
show event manager policy registered
show event manager history events
show event manager statistics policy
event manager run REPORT
debug event manager action cli
dir flash:
more flash:ospf-down.txt
```

| Befehl | Das solltest du sehen |
|---|---|
| `show event manager policy registered` | sechs Applets mit den Ereignistypen none, syslog (2×), cli (2×), timer watchdog |
| `event manager run REPORT` | die OSPF-Nachbartabelle |
| `debug all` | Sperrmeldung im Log, `show debugging` bleibt leer |
| `write memory` | `flash:backup.cfg` entsteht, danach wird normal gespeichert |
| dreimal `clear ip ospf process` auf R2 | R1 Gi0/1 `administratively down`, kritische Meldung im Log |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Ein Applet enthält `event cli pattern "^reload" sync yes` und nur eine Syslog-Aktion. Was passiert, wenn jemand `reload` eingibt?
<details><summary>Antwort</summary>

**Der Router startet nicht neu.** Bei `sync yes` entscheidet `_exit_status`. Er wird nie auf 1 gesetzt, also verwirft EEM den Befehl. Das kann Absicht sein (Sperre) oder ein Versehen, das im Notfall teuer wird. Abschalten lässt es sich mit `no event manager applet …` oder vorübergehend mit `event manager scheduler suspend`.

</details>

2. Warum löst ein Applet mit `event syslog pattern "changed state to down"` manchmal in einer Schleife aus?
<details><summary>Antwort</summary>

**Weil seine eigene Aktion wieder eine passende Meldung erzeugt.** Schaltet das Applet ein Interface ab, schreibt der Router erneut „changed state to down“. Abhilfe: das Muster enger fassen (Interface-Name, Mnemonic), `ratelimit` setzen oder nur sammeln statt eingreifen.

</details>

3. Womit löst du ein Applet aus, wenn sich der Zustand einer IP-SLA-Messung ändert?
<details><summary>Antwort</summary>

**Mit `event track N state down`** (oder `up`, `any`). Das Track-Objekt übersetzt die Messung in Up/Down, EEM reagiert darauf. So lässt sich etwa beim Ausfall eines Providers eine Konfiguration umstellen oder eine Meldung absetzen.

</details>

4. Worin unterscheidet sich ein Applet von einem Tcl-Skript in EEM?
<details><summary>Antwort</summary>

**Ein Applet steht vollständig in der Konfiguration, ein Tcl-Skript ist eine Datei.** Applets reichen für Abläufe mit wenigen Schritten und einfachen Bedingungen (`if`, `while`, `regexp`). Tcl-Policies können mehr, müssen aber auf dem Gerät liegen und registriert werden (`event manager policy`). ENCOR fragt Applets ab.

</details>

## Prüfungsbezug
- Aufbau: `event manager applet NAME`, genau ein `event`, beliebig viele `action <Bezeichner> …`.
- Aktionen laufen in **Zeichenketten-Reihenfolge** der Bezeichner: 1.0, 10.0, 2.0.
- `cli command` startet im User-EXEC: erst `enable`, dann `configure terminal`.
- Ereignisse: `syslog pattern`, `cli pattern`, `timer watchdog|countdown|cron`, `track`, `interface`, `snmp`, `none`.
- `event cli`: `sync yes` wartet und wertet `_exit_status` aus (1 = ausführen), `sync no` braucht `skip yes|no`.
- Prüfen: `show event manager policy registered`, `show event manager history events`, `debug event manager action cli`.

## Hinweis zum Image

Auf IOSv heißt das Dateisystem `flash0:`. `flash:` ist dort ein Alias und funktioniert in den meisten Versionen. Meldet dein Image einen Fehler, ersetze in den Applets `flash:` durch `flash0:`.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/36-EEM-Applets/`](../../CML-Labs/36-EEM-Applets/).
