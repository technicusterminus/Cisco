# Fehlerliste – Lab 36 – EEM-Applets: Ereignisse, Aktionen und die typischen Fallen

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Nach `write memory` meldet das Log „Sicherung … angestossen“, aber `dir flash:` zeigt keine `backup.cfg`.
- **So findest du es:** `show running-config | section applet BACKUP`: Die erste CLI-Aktion ist schon `copy`. `debug event manager action cli` zeigt beim Lauf den Prompt `R1>` und eine Ablehnung des Befehls.
- **Ursache:** Ohne `enable` läuft `copy` im User-EXEC-Modus und wird abgelehnt. Das Applet prüft das Ergebnis nicht und meldet trotzdem Erfolg.
- **Fix:** `action 1.0 cli command "enable"` im Applet BACKUP ergänzen.
- **Eingebaut:**

```diff
- action 1.0 cli command "enable"
```

## Ticket 2 (R1)

- **Symptom:** Gi0/1 flattert im Test dreimal in fünf Minuten. FLAPGUARD schreibt seine kritische Meldung, das Interface bleibt aber in Betrieb.
- **So findest du es:** `show running-config | section applet FLAPGUARD`: Die Aktionen stehen in der Reihenfolge 1.0, 10.0, 2.0, 3.0, 5.0, 6.0. `shutdown` läuft vor `configure terminal`.
- **Ursache:** EEM sortiert Aktionsbezeichner als Zeichenketten. „10.0“ liegt zwischen „1.0“ und „2.0“, der Befehl landet im EXEC-Modus und wird abgelehnt.
- **Fix:** `no action 10.0`, dann `action 4.0 cli command "shutdown"`.
- **Eingebaut:**

```diff
- action 4.0 cli command "shutdown"
+ action 10.0 cli command "shutdown"
```

## Ticket 3 (R1)

- **Symptom:** OSPF-DOWN löst nie aus. `show event manager history events` enthält keinen Lauf dieses Applets, obwohl Nachbarschaften abreißen.
- **So findest du es:** Vergleiche das Muster in `show event manager policy registered` mit einer echten Zeile aus `show logging`: Die Meldung heißt `%OSPF-5-ADJCHG`, das Muster sucht `ADJCHANGE`.
- **Ursache:** Das Muster trifft keine Syslog-Zeile. Ein Applet mit falschem Muster erzeugt keinen Fehler, es bleibt einfach stumm.
- **Fix:** Im Applet OSPF-DOWN: `event syslog pattern "OSPF-5-ADJCHG.*from FULL to"`.
- **Eingebaut:**

```diff
- event syslog pattern "OSPF-5-ADJCHG.*from FULL to"
+ event syslog pattern "OSPF-5-ADJCHANGE.*from FULL to"
```

## Ticket 4 (R1)

- **Symptom:** Wer `debug all` eingibt, bekommt die Sperrmeldung im Log. `show debugging` zeigt danach trotzdem alle Debugs als aktiv.
- **So findest du es:** `show running-config | section applet NO-DEBUG-ALL`: Das Ereignis endet auf `skip no`.
- **Ursache:** Bei `sync no` entscheidet allein `skip`, ob der Befehl läuft. Mit `skip no` wird er ausgeführt, das Applet schreibt nur nebenher seine Meldung.
- **Fix:** `event cli pattern "^debug all" sync no skip yes`, danach `undebug all`.
- **Eingebaut:**

```diff
- event cli pattern "^debug all" sync no skip yes
+ event cli pattern "^debug all" sync no skip no
```
