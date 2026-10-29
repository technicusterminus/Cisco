# Labs schreiben

Labs entstehen aus `Labs-Quelle/build_labs.py`. Den Generator startest du mit `python3 Labs-Quelle/build_labs.py`; er schreibt `labs/*.json`. Bearbeite die JSON-Dateien nicht von Hand. Vorlage für das neue Format ist **Lab 32** (`32-https-least-privilege`).

## Aufbau

```python
lab(id='33-beispiel', title='33 Titel', topic='Policy / Contracts', level='Einstieg', duration='20 min',
    fabric='discovered',              # Ausgangszustand der Fabric: discovered | empty | factory
    kind='requirements', modes=['guided', 'exam'],   # kind 'troubleshooting' fuer Labs mit kaputtem Ausgangszustand
    prerequisites=['…'], tools=['…'], goals=['…'],
    intro='Szenario, ohne Lösung',      # Markdown
    requirements=['Was am Ende gelten muss', '… auch was verboten bleibt'],
    limits=['Fachliche Grenzen dieses Szenarios'],
    hints=['Stufe 1: Konzept', 'Stufe 2: beteiligte Objekte', 'Stufe 3: konkreter Prüfschritt', 'Stufe 4: Lösung mit Erklärung'],
    cause='Warum der Ausgangszustand scheitert',
    config=[SERVER_ACCESS, shop_tenant()],   # Ausgangskonfiguration (APIC-JSON-Bäume, POST auf uni)
    hosts=[dict(WEB1, services=['tcp/22'])],  # simulierte Welt: hosts, routers, vcenters, devices, aaa, switches
    tasks=[],                                 # leer im Anforderungsformat
    checks=[...], questions=[...], solution='Markdown mit Erklärung')
```

Dazu gehört immer ein Eintrag in `SOLUTIONS['33-beispiel'] = [[dn, body], …]`. Sonderziele:

- `#snapshot` (`{op, name}`) und `#change` (`[dn, body]`, mit Audit-Eintrag)
- `#setup`
- `#ipn`
- `#ndo`
- `#monitor-test`

## Prüfungen (`checks`)

Jede Prüfung hat `desc`, `type` und `category`. Die Kategorie ist `function` (Standard) oder `security`. Ein Lab gilt als bestanden, wenn **alle** Prüfungen bestanden sind. Die Oberfläche zeigt Funktion und Sicherheit getrennt.

| Typ | Parameter | Wertet aus |
|---|---|---|
| `traffic` | `src`, `dst`, `proto`, `port`, `expect`, optional `reason` (Präfix, z. B. `POLICY_`), `via` | Connectivity-Engine. Mit `reason` zählt ein Block nur aus diesem Grund (z. B. „durch Policy“, nicht „Pfad kaputt“) |
| `exposure` | `src`, `dst`, `allow` (z. B. `['tcp/443']`), optional `probes` | Least Privilege: Die Policy darf für keinen anderen typischen Dienst eine neue Verbindung erlauben. Gewertet wird die Policy-Entscheidung, unabhängig vom Dienstmodell |
| `endpoint` | `host`, optional `epg`, `pathType` (`port`, `pc`, `vpc`), `expect` | Endpoint gelernt, optional über einen bestimmten Pfadtyp (z. B. vPC statt Einzelport). `expect=False`: darf nicht gelernt sein (Fremdgerät) |
| `exists` / `class` | `dn` bzw. `cls`, `attrs`, `under`; bei `class` zusätzlich `expect` (False = darf es nicht geben) oder `max` (höchstens so viele) | Objekt mit Attributen vorhanden. Nur verwenden, wenn die Aufgabe das Objekt wirklich verlangt, sonst lieber Verhalten prüfen |
| `nofaults` | `under`, optional `code` | keine Faults |
| `router`, `learned`, `route`, `bfd`, `bgptimer` | siehe vorhandene Labs | externe Nachbarschaften und Routen |
| `snapshot` | `prefix` | Ein Config-Snapshot mit diesem Namensanfang wurde nach dem Lab-Start angelegt |
| `audited` | `dn`, optional `contains`, `expect` | Eine Änderung an diesem DN steht seit dem Lab-Start im Audit-Log (z. B. „Change wurde eingespielt“) |
| weitere | `node`, `ntp`, `graph`, `login`, `rbac`, `firmware`, `job`, `mon`, `snmp`, `dhcp`, `loop`, `msite`, `ipnadj`, `inb`, `vmm`, `setup` | siehe `Sim.check_lab` |

Regeln für gute Prüfungen:

- **Verhalten prüfen, nicht Klicks.** Prüfe lieber Traffic und Exposure als Objektnamen. Dann werden gleichwertige Lösungen anerkannt (anderer Contract-Name, Filter in common, Scope tenant).
- **Negative Tests sind Pflicht:** Für jede Freigabe gibt es mindestens eine Prüfung, was blockiert bleiben muss, mit `reason='POLICY_'`.
- **Least Privilege** mit `exposure` in beide Richtungen.
- **Leitplanken:** Prüfe, dass das, was nicht verändert werden soll (z. B. Routing), weiter funktioniert.

## Hinweise und Lösung

- Szenario (`intro`), Anforderungen und die **Beschreibungen der Prüfungen** sind ab Start sichtbar, auch im Prüfungsmodus. Sie nennen keine Lösung (keine Rollen wie „Web konsumiert“, keine falschen Werte aus dem Ausgangszustand). `TestRequirementLabs` prüft das für jedes Lab im neuen Format anhand einer Liste verbotener Begriffe. Neue Labs gehören in diese Liste.
- Zu den Hinweisstufen:
  1. Konzept
  2. Objekte und Diagnoseebene
  3. konkreter Prüfschritt
  4. Lösung mit Begründung
- Hinweise werden nur gelesen. Sie ändern nie die Konfiguration, und das ist getestet. Die Oberfläche zählt, wie viele Stufen genutzt wurden.
- Im Prüfungsmodus (`exam`) gibt es keine Hinweise, keine Lösung und keine Diagnosetexte in der Bewertung.

## Verständnisfragen

```python
questions=[{'id': 'q1', 'q': 'Frage', 'options': ['A', 'B', 'C'], 'answer': 1, 'explain': 'Begründung'}]
```

Die Fragen zählen nicht zum Bestehen und werden getrennt ausgewiesen. Die Erklärung erscheint erst nach dem Antworten und nicht im Prüfungsmodus.

## Tests

- `TestLabs.test_all_labs_solvable` prüft jedes Lab automatisch: Ohne Lösung ist es nicht bestanden, mit Lösung vollständig bestanden.
- Für Labs im neuen Format schreibst du zusätzlich Tests wie in `tests/test_acceptance.py`:
  - gleichwertige Lösungen
  - Abkürzungen (permit any, zu weite Ports)
  - vertauschte Rollen
  - Reset
- Der Generator muss deterministisch bleiben (keine Zeitstempel oder Zufallswerte in den Lab-Dateien).
