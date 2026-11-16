def base(n, peer):
    return f"""interface Loopback0
 ip address 10.255.0.{n} 255.255.255.255
 ip ospf 1 area 0
interface GigabitEthernet0/0
 ip address 10.0.12.{n} 255.255.255.252
 ip ospf network point-to-point
 ip ospf 1 area 0
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.21.{n} 255.255.255.252
 ip ospf network point-to-point
 ip ospf 1 area 0
 no shutdown
router ospf 1
 router-id 10.255.0.{n}"""


SOL = r'''
file prompt quiet
event manager applet REPORT
 event none
 action 1.0 cli command "enable"
 action 2.0 cli command "show ip ospf neighbor"
 action 3.0 puts "$_cli_result"
event manager applet OSPF-DOWN
 event syslog pattern "OSPF-5-ADJCHG.*from FULL to"
 action 1.0 cli command "enable"
 action 2.0 cli command "show ip ospf neighbor | append flash:ospf-down.txt"
 action 3.0 cli command "show ip interface brief | append flash:ospf-down.txt"
 action 4.0 syslog priority warnings msg "EEM: OSPF-Nachbar verloren, Daten in flash:ospf-down.txt"
event manager applet FLAPGUARD
 event syslog pattern "OSPF-5-ADJCHG.*GigabitEthernet0/1 from FULL to" occurs 3 period 300
 action 1.0 cli command "enable"
 action 2.0 cli command "configure terminal"
 action 3.0 cli command "interface GigabitEthernet0/1"
 action 4.0 cli command "shutdown"
 action 5.0 cli command "end"
 action 6.0 syslog priority critical msg "EEM: Gi0/1 flattert, Interface abgeschaltet"
event manager applet NO-DEBUG-ALL
 event cli pattern "^debug all" sync no skip yes
 action 1.0 syslog priority warnings msg "EEM: debug all ist auf diesem Geraet gesperrt"
event manager applet BACKUP
 event cli pattern "^write memory" sync yes
 action 1.0 cli command "enable"
 action 2.0 cli command "copy running-config flash:backup.cfg"
 action 3.0 syslog msg "EEM: Sicherung nach flash:backup.cfg angestossen"
 action 4.0 set _exit_status "1"
event manager applet HEARTBEAT
 event timer watchdog time 300
 action 1.0 syslog msg "EEM: Heartbeat"'''

LAB = dict(
    slug="36-EEM-Applets", num="36",
    title="EEM-Applets: Ereignisse, Aktionen und die typischen Fallen", minutes=90, level="mittel",
    summary=("Ziel 6.6 verlangt, ein EEM-Applet zu konstruieren, das konfiguriert, Fehler eingrenzt oder Daten sammelt. "
             "Lab 19 zeigt zwei Applets am Rand. Hier baust du sechs kleine Applets, eines je Ereignistyp, und lernst "
             "dabei die Stellen kennen, an denen Applets in der Praxis und in Prüfungs-Exhibits scheitern: fehlendes "
             "`enable`, die Sortierung der Aktionsnummern, Muster, die nie treffen, und die Bedeutung von `sync` und `skip`."),
    goals=["Ein Applet aus Ereignis (`event`) und nummerierten Aktionen (`action`) aufbauen und von Hand starten.",
           "Die Ereignistypen `none`, `syslog`, `cli` und `timer` passend zur Aufgabe wählen.",
           "Vorhersagen, in welcher Reihenfolge Aktionen laufen und in welchem Modus ein `cli command` ankommt.",
           "Bei `event cli` die Wirkung von `sync yes`, `sync no`, `skip` und `_exit_status` erklären.",
           "Ein Applet mit `show event manager …` und `debug event manager action cli` prüfen."],
    tags=[("6.6", "EEM-Applets", 29)],
    diagram="""
           Gi0/0  10.0.12.0/30  Gi0/0
      R1 ══════════════════════════════ R2
         ──────────────────────────────
           Gi0/1  10.0.21.0/30  Gi0/1      (Testlink für FLAPGUARD)
""",
    nets=[("R1 Gi0/0 – R2 Gi0/0", "10.0.12.0/30 (.1/.2)"), ("R1 Gi0/1 – R2 Gi0/1", "10.0.21.0/30 (.1/.2)")],
    topo_text=("Loopback0: R1 10.255.0.1, R2 10.255.0.2. OSPF 1 (Area 0) läuft **fertig konfiguriert** auf beiden Links, "
               "Netztyp Point-to-Point. Alle Applets baust du auf **R1**. R2 dient nur dazu, Ereignisse auszulösen: "
               "`clear ip ospf process` auf R2 lässt auf R1 beide Nachbarschaften kurz abreißen.\n\n"
               "| Applet | Ereignis | Aufgabe |\n|---|---|---|\n"
               "| REPORT | `none` (von Hand) | OSPF-Nachbarn ausgeben |\n"
               "| OSPF-DOWN | `syslog` | bei Nachbarverlust Daten in eine Datei sammeln |\n"
               "| FLAPGUARD | `syslog` mit Zähler | flatternden Link abschalten |\n"
               "| NO-DEBUG-ALL | `cli`, asynchron | einen gefährlichen Befehl sperren |\n"
               "| BACKUP | `cli`, synchron | vor `write memory` eine Kopie ablegen |\n"
               "| HEARTBEAT | `timer` | regelmäßig ein Lebenszeichen ins Log |"),
    steps=[
        dict(t="Erstes Applet von Hand starten.", body="Lege `event manager applet REPORT` an mit `event none`, `action 1.0 cli command \"enable\"`, `action 2.0 cli command \"show ip ospf neighbor\"` und `action 3.0 puts \"$_cli_result\"`. Starte es mit `event manager run REPORT`.",
             check="Die Nachbartabelle erscheint auf der Konsole. `show event manager policy registered` listet REPORT mit dem Ereignistyp `none`.",
             think="Was steht in `$_cli_result`, wenn mehrere `cli command`-Aktionen vorausgegangen sind?"),
        dict(t="Die `enable`-Falle.", body="Ändere Aktion 2.0 auf `show running-config | include ^hostname` und entferne Aktion 1.0. Starte das Applet. Schalte dann `debug event manager action cli` ein und starte es noch einmal.",
             predict="Welche Ausgabe liefert das Applet ohne `enable`?",
             check="Statt des Hostnamens erscheint eine Fehlermeldung des Parsers. Das Debug zeigt den Prompt `R1>`: Das Applet arbeitet im User-EXEC-Modus. Mit Aktion 1.0 erscheint `hostname R1`. Stelle den Stand aus Schritt 1 wieder her, `undebug all`.",
             think="Auf einem Router mit AAA-Autorisierung für Befehle reicht `enable` nicht. Was braucht das Applet dort zusätzlich?"),
        dict(t="Auf Syslog reagieren.", body="Setze global `file prompt quiet`. Lege OSPF-DOWN an: `event syslog pattern \"OSPF-5-ADJCHG.*from FULL to\"`, danach `enable`, zwei `show`-Befehle mit `| append flash:ospf-down.txt` und eine Syslog-Aktion mit `priority warnings`. Löse es aus: `clear ip ospf process` auf R2.",
             predict="Wie oft läuft das Applet bei einem einzigen `clear` auf R2?",
             check="Im Log von R1 steht die EEM-Meldung zweimal, einmal je Link. `more flash:ospf-down.txt` zeigt die gesammelten Ausgaben. `show event manager history events` listet die Läufe mit Zeit und Ereignistyp.",
             think="Das Muster ist ein regulärer Ausdruck. Was wäre passiert, wenn du `Gi0/1` statt `GigabitEthernet0/1` in ein Muster geschrieben hättest?"),
        dict(t="Zählen und eingreifen.", body="Lege FLAPGUARD an: `event syslog pattern \"OSPF-5-ADJCHG.*GigabitEthernet0/1 from FULL to\" occurs 3 period 300`. Aktionen 1.0 bis 5.0: `enable`, `configure terminal`, `interface GigabitEthernet0/1`, `shutdown`, `end`. Aktion 6.0: Syslog mit `priority critical`. Führe auf R2 dreimal `clear ip ospf process` aus und warte jeweils, bis die Nachbarn wieder FULL sind.",
             predict="Nach dem wievielten `clear` greift das Applet ein, und was passiert mit dem Link Gi0/0?",
             check="Nach dem dritten Abriss ist R1 Gi0/1 `administratively down`, im Log steht die kritische Meldung. Gi0/0 bleibt in Betrieb. Schalte Gi0/1 danach wieder ein.",
             think="Warum ist ein Applet, das selbst in die Konfiguration eingreift, riskanter als eines, das nur Daten sammelt?"),
        dict(t="Die Nummern-Falle.", body="Benenne in FLAPGUARD die Aktion `4.0` (`shutdown`) testweise in `10.0` um: `no action 4.0`, dann `action 10.0 cli command \"shutdown\"`. Sieh dir das Applet mit `show running-config | section FLAPGUARD` an.",
             predict="An welcher Stelle der Reihenfolge steht Aktion 10.0?",
             check="Die Konfiguration zeigt die Reihenfolge 1.0, 10.0, 2.0, 3.0, 5.0, 6.0. `shutdown` käme direkt nach `enable` im EXEC-Modus an und würde abgelehnt. Stelle `action 4.0` wieder her und lösche `action 10.0`.",
             think="Wie nummerierst du, damit das nie passiert?"),
        dict(t="Einen Befehl sperren.", body="Lege NO-DEBUG-ALL an: `event cli pattern \"^debug all\" sync no skip yes` und eine Syslog-Aktion. Gib danach `debug all` ein.",
             predict="Wird `debug all` ausgeführt?",
             check="Im Log steht die EEM-Meldung, `show debugging` bleibt leer. Der Befehl wurde verworfen.",
             think="Was bedeuten `sync no` und `skip yes` genau? Und warum greift das Muster auch, wenn jemand nur `deb all` tippt?"),
        dict(t="Vor dem Speichern sichern.", body="Lege BACKUP an: `event cli pattern \"^write memory\" sync yes`, Aktionen: `enable`, `copy running-config flash:backup.cfg`, eine Syslog-Meldung und zuletzt `action 4.0 set _exit_status \"1\"`. Gib `write memory` ein.",
             predict="Löst auch `copy running-config startup-config` das Applet aus?",
             check="`dir flash:` zeigt `backup.cfg` mit aktuellem Zeitstempel, danach läuft das eigentliche `write memory` („Building configuration…“). `copy running-config startup-config` löst das Applet **nicht** aus.",
             think="Was passiert bei `sync yes`, wenn `_exit_status` am Ende 0 ist oder gar nicht gesetzt wird?"),
        dict(t="Zeitgesteuert.", body="Lege HEARTBEAT an: `event timer watchdog time 300` und eine Syslog-Aktion. Setze die Zeit zum Testen kurz auf 30.",
             check="Alle 30 Sekunden erscheint die Meldung. `show event manager policy registered` nennt den Timer. Stelle 300 wieder ein.",
             think="Worin unterscheiden sich `watchdog`, `countdown` und `cron`?"),
        dict(t="Einordnen.", body="Entscheide für drei Aufgaben, ob EEM das richtige Werkzeug ist, bevor du die Antwort aufklappst: (a) Bei jedem BGP-Nachbarverlust sofort `show ip bgp summary` auf dem betroffenen Router sichern. (b) Auf 400 Switches eine neue NTP-Konfiguration ausrollen. (c) Einmal pro Nacht die Konfiguration aller Router auf einen zentralen Server kopieren.")],
    answers=[
        ("1", "Immer nur die Ausgabe des **letzten** `cli command`. Wer mehrere Ausgaben braucht, wertet sie nach jedem Befehl aus oder schreibt sie mit `| append` in eine Datei."),
        ("2", "Eine **Fehlermeldung**: `show running-config` gibt es im User-EXEC-Modus nicht. Jedes Applet öffnet eine eigene VTY-Sitzung auf Privilegstufe 1, deshalb ist `enable` fast immer Aktion 1. Mit AAA-Autorisierung braucht das Applet einen Benutzer, dem die Befehle erlaubt sind: `event manager session cli username <Name>`. Ohne ihn scheitern die Befehle an der Autorisierung, oft erst nach einem langen Timeout."),
        ("3", "**Zweimal**, denn R1 verliert zwei Nachbarschaften und schreibt zwei Meldungen. Syslog-Meldungen nennen Interfaces immer mit vollem Namen. Ein Muster mit `Gi0/1` trifft nie, das Applet bleibt stumm, und nichts weist auf den Fehler hin. Prüfe ein Muster immer gegen eine echte Zeile aus `show logging`."),
        ("4", "Nach dem **dritten** Abriss auf Gi0/1 innerhalb von 300 Sekunden. Gi0/0 bleibt unberührt, weil das Muster den Interface-Namen enthält. Zum Risiko: Ein Applet mit Eingriff kann sich selbst auslösen, im falschen Moment zuschlagen oder die Störung vergrößern (hier: Wenn beide Links flattern und beide Applets abschalten, ist der Standort offline). Sammeln ist ungefährlich, Eingreifen braucht Grenzen wie `occurs`, `period` und `ratelimit`."),
        ("5", "**Zwischen 1.0 und 2.0.** EEM sortiert die Bezeichner als Zeichenketten, nicht als Zahlen: „10.0“ kommt vor „2.0“. Nummeriere mit führenden Nullen (010, 020, 030) oder bleibe einstellig mit Lücken. In Exhibits ist das eine beliebte Falle."),
        ("6", "**Nein.** `sync no` heißt: Das Applet läuft unabhängig vom Befehl, und `skip` entscheidet allein, ob der Befehl ausgeführt wird (`skip yes` = verwerfen). Bei `sync yes` wartet die CLI auf das Applet, und dessen `_exit_status` entscheidet. Das Muster wird gegen den **vollständig ausgeschriebenen** Befehl geprüft. `deb all` wird vor dem Vergleich zu `debug all` ergänzt."),
        ("7", "**Nein**, das Muster passt nur auf `write memory`. Wer beide Wege abdecken will, braucht ein zweites Applet oder ein Muster mit Alternative. Zu `_exit_status`: Bei 0 oder ohne Zuweisung wird der ursprüngliche Befehl **nicht** ausgeführt, bei 1 schon. Ein synchrones Applet ohne diese Zeile schluckt also den Befehl. Beachte auch: Die Syslog-Meldung behauptet nur, dass gesichert wurde. Ob `copy` Erfolg hatte, prüft das Applet nicht."),
        ("8", "`watchdog` läuft alle N Sekunden immer wieder. `countdown` läuft einmal nach N Sekunden. `cron` läuft zu festen Zeiten nach Cron-Schreibweise, etwa `cron-entry \"0 2 * * *\"` für täglich 2 Uhr."),
        ("9", "(a) **EEM.** Das Ereignis entsteht auf dem Gerät, die Reaktion muss sofort und auch ohne Verbindung zur Zentrale erfolgen. (b) **Nicht EEM**, sondern ein agentenloses Werkzeug wie Ansible oder der Controller: Das ist eine zentrale, einmalige Änderung mit Kontrolle über den Erfolg. (c) **Beides möglich**, zentral ist besser: Ein Applet mit `timer cron` kann kopieren, aber 400 Applets muss jemand pflegen. Eine zentrale Sicherung sieht außerdem, welches Gerät sich nicht gemeldet hat.")],
    nodes=[dict(name="R1", type="router", x=100, y=200, base=base(1, 2), sol=SOL),
           dict(name="R2", type="router", x=500, y=200, base=base(2, 1), sol="")],
    links=[("R1", "Gi0/0", "R2", "Gi0/0"), ("R1", "Gi0/1", "R2", "Gi0/1")],
    tickets=["Nach `write memory` meldet das Log „Sicherung … angestossen“, aber `dir flash:` zeigt keine `backup.cfg`.",
             "Gi0/1 flattert im Test dreimal in fünf Minuten. FLAPGUARD schreibt seine kritische Meldung, das Interface bleibt aber in Betrieb.",
             "OSPF-DOWN löst nie aus. `show event manager history events` enthält keinen Lauf dieses Applets, obwohl Nachbarschaften abreißen.",
             "Wer `debug all` eingibt, bekommt die Sperrmeldung im Log. `show debugging` zeigt danach trotzdem alle Debugs als aktiv."],
    faults=[
        dict(node="R1", ctx="event manager applet BACKUP", old=' action 1.0 cli command "enable"', new=None,
             find="`show running-config | section applet BACKUP`: Die erste CLI-Aktion ist schon `copy`. `debug event manager action cli` zeigt beim Lauf den Prompt `R1>` und eine Ablehnung des Befehls.",
             cause="Ohne `enable` läuft `copy` im User-EXEC-Modus und wird abgelehnt. Das Applet prüft das Ergebnis nicht und meldet trotzdem Erfolg.",
             fix="`action 1.0 cli command \"enable\"` im Applet BACKUP ergänzen.",
             inject=["event manager applet BACKUP", "no action 1.0"],
             revert=["event manager applet BACKUP", 'action 1.0 cli command "enable"'],
             kick=[("R1", "delete /force flash:backup.cfg"), ("R1", "write memory")],
             probe=("R1", "dir flash:", r"backup\.cfg"), settle=10),
        dict(node="R1", old=' action 4.0 cli command "shutdown"', new=' action 10.0 cli command "shutdown"',
             find="`show running-config | section applet FLAPGUARD`: Die Aktionen stehen in der Reihenfolge 1.0, 10.0, 2.0, 3.0, 5.0, 6.0. `shutdown` läuft vor `configure terminal`.",
             cause="EEM sortiert Aktionsbezeichner als Zeichenketten. „10.0“ liegt zwischen „1.0“ und „2.0“, der Befehl landet im EXEC-Modus und wird abgelehnt.",
             fix="`no action 10.0`, dann `action 4.0 cli command \"shutdown\"`.",
             inject=["event manager applet FLAPGUARD", "no action 4.0", 'action 10.0 cli command "shutdown"'],
             revert=["event manager applet FLAPGUARD", "no action 10.0", 'action 4.0 cli command "shutdown"'],
             probe=("R1", "show running-config | section applet FLAPGUARD", r'action 3\.0[^\n]*\n\s*action 4\.0 cli command "shutdown"'),
             settle=2),
        dict(node="R1", old=' event syslog pattern "OSPF-5-ADJCHG.*from FULL to"', new=' event syslog pattern "OSPF-5-ADJCHANGE.*from FULL to"',
             find="Vergleiche das Muster in `show event manager policy registered` mit einer echten Zeile aus `show logging`: Die Meldung heißt `%OSPF-5-ADJCHG`, das Muster sucht `ADJCHANGE`.",
             cause="Das Muster trifft keine Syslog-Zeile. Ein Applet mit falschem Muster erzeugt keinen Fehler, es bleibt einfach stumm.",
             fix="Im Applet OSPF-DOWN: `event syslog pattern \"OSPF-5-ADJCHG.*from FULL to\"`.",
             inject=["event manager applet OSPF-DOWN", 'event syslog pattern "OSPF-5-ADJCHANGE.*from FULL to"'],
             revert=["event manager applet OSPF-DOWN", 'event syslog pattern "OSPF-5-ADJCHG.*from FULL to"'],
             probe=("R1", "show event manager policy registered", r"ADJCHG"), settle=2),
        dict(node="R1", old=' event cli pattern "^debug all" sync no skip yes', new=' event cli pattern "^debug all" sync no skip no',
             find="`show running-config | section applet NO-DEBUG-ALL`: Das Ereignis endet auf `skip no`.",
             cause="Bei `sync no` entscheidet allein `skip`, ob der Befehl läuft. Mit `skip no` wird er ausgeführt, das Applet schreibt nur nebenher seine Meldung.",
             fix="`event cli pattern \"^debug all\" sync no skip yes`, danach `undebug all`.",
             inject=["event manager applet NO-DEBUG-ALL", 'event cli pattern "^debug all" sync no skip no'],
             revert=["event manager applet NO-DEBUG-ALL", 'event cli pattern "^debug all" sync no skip yes'],
             probe=("R1", "show running-config | section applet NO-DEBUG-ALL", r"skip yes"), settle=2)],
    verify=["show event manager policy registered", "show event manager history events", "show event manager statistics policy",
            "event manager run REPORT", "debug event manager action cli", "dir flash:", "more flash:ospf-down.txt"],
    verify_table=[("`show event manager policy registered`", "sechs Applets mit den Ereignistypen none, syslog (2×), cli (2×), timer watchdog"),
                  ("`event manager run REPORT`", "die OSPF-Nachbartabelle"),
                  ("`debug all`", "Sperrmeldung im Log, `show debugging` bleibt leer"),
                  ("`write memory`", "`flash:backup.cfg` entsteht, danach wird normal gespeichert"),
                  ("dreimal `clear ip ospf process` auf R2", "R1 Gi0/1 `administratively down`, kritische Meldung im Log")],
    checks=[("R1", "show event manager policy registered", r"(?s)REPORT.*OSPF-DOWN.*FLAPGUARD.*NO-DEBUG-ALL.*BACKUP.*HEARTBEAT"),
            ("R1", "event manager run REPORT", r"10\.255\.0\.2"), ("R1", "show ip ospf neighbor", r"FULL")],
    settle=60,
    teilc=[("Ein Applet enthält `event cli pattern \"^reload\" sync yes` und nur eine Syslog-Aktion. Was passiert, wenn jemand `reload` eingibt?",
            "**Der Router startet nicht neu.** Bei `sync yes` entscheidet `_exit_status`. Er wird nie auf 1 gesetzt, also verwirft EEM den Befehl. Das kann Absicht sein (Sperre) oder ein Versehen, das im Notfall teuer wird. Abschalten lässt es sich mit `no event manager applet …` oder vorübergehend mit `event manager scheduler suspend`."),
           ("Warum löst ein Applet mit `event syslog pattern \"changed state to down\"` manchmal in einer Schleife aus?",
            "**Weil seine eigene Aktion wieder eine passende Meldung erzeugt.** Schaltet das Applet ein Interface ab, schreibt der Router erneut „changed state to down“. Abhilfe: das Muster enger fassen (Interface-Name, Mnemonic), `ratelimit` setzen oder nur sammeln statt eingreifen."),
           ("Womit löst du ein Applet aus, wenn sich der Zustand einer IP-SLA-Messung ändert?",
            "**Mit `event track N state down`** (oder `up`, `any`). Das Track-Objekt übersetzt die Messung in Up/Down, EEM reagiert darauf. So lässt sich etwa beim Ausfall eines Providers eine Konfiguration umstellen oder eine Meldung absetzen."),
           ("Worin unterscheidet sich ein Applet von einem Tcl-Skript in EEM?",
            "**Ein Applet steht vollständig in der Konfiguration, ein Tcl-Skript ist eine Datei.** Applets reichen für Abläufe mit wenigen Schritten und einfachen Bedingungen (`if`, `while`, `regexp`). Tcl-Policies können mehr, müssen aber auf dem Gerät liegen und registriert werden (`event manager policy`). ENCOR fragt Applets ab.")],
    exam=["Aufbau: `event manager applet NAME`, genau ein `event`, beliebig viele `action <Bezeichner> …`.",
          "Aktionen laufen in **Zeichenketten-Reihenfolge** der Bezeichner: 1.0, 10.0, 2.0.",
          "`cli command` startet im User-EXEC: erst `enable`, dann `configure terminal`.",
          "Ereignisse: `syslog pattern`, `cli pattern`, `timer watchdog|countdown|cron`, `track`, `interface`, `snmp`, `none`.",
          "`event cli`: `sync yes` wartet und wertet `_exit_status` aus (1 = ausführen), `sync no` braucht `skip yes|no`.",
          "Prüfen: `show event manager policy registered`, `show event manager history events`, `debug event manager action cli`."],
    caveat=("Auf IOSv heißt das Dateisystem `flash0:`. `flash:` ist dort ein Alias und funktioniert in den meisten Versionen. "
            "Meldet dein Image einen Fehler, ersetze in den Applets `flash:` durch `flash0:`."),
)
