# Labs schreiben

Labs sind deklarativ. Die Quelle ist `Labs-Quelle/build_labs.py`; daraus entstehen die Dateien in `labs/`. Nie die JSON-Dateien direkt bearbeiten.

```sh
python3 Labs-Quelle/build_labs.py
python3 -m unittest discover -s tests
```

Der Generator ist deterministisch: Zwei Läufe ergeben dieselben Dateien.

## Felder

| Feld | Pflicht | Inhalt |
|---|---|---|
| `id`, `title` | ja | `NN-kurzname`, Titel mit Nummer |
| `level`, `duration`, `topic` | ja | Schwierigkeit (Einstieg, Mittel, Fortgeschritten), Dauer, Thema |
| `goals` | ja | Lernziele |
| `fabric` | ja | Ausgangszustand der Fabric: `discovered`, `empty`, `factory` |
| `config` | ja | APIC-JSON-Bäume, die nach dem Reset per POST an `uni` gehen |
| `hosts`, `routers`, … | nein | simulierte Umgebung; Hosts können `services` (`["tcp/443"]`) und `icmp: false` haben |
| `intro`, `tasks` | ja | Ausgangslage und Aufgaben. **Die Lösung darf hier nicht stehen** (Test `test_solution_not_in_task_text` für Lab 32) |
| `hints` | empfohlen | vier Stufen: 1 Konzept, 2 betroffene Objekte, 3 konkreter Prüfschritt, 4 Lösung mit Erklärung |
| `limits` | empfohlen | fachliche Grenzen des Szenarios |
| `checks` | ja | Prüfungen auf den Endzustand (siehe unten) |
| `solution` | ja | Musterlösung als Text |
| `SOLUTIONS[id]` | ja | Musterlösung als Liste `[url, baum]`; der Test spielt sie ein und erwartet alle Prüfungen grün |

## Prüfungen

Jede Prüfung liest nur den Zustand. Klickreihenfolge, Objektnamen und Bedienweg spielen keine Rolle, solange die Aufgabe keine Namen fordert.

| `type` | Parameter | Bestanden, wenn |
|---|---|---|
| `traffic` | `src`, `dst`, `proto`, `port`, `expect`, optional `reason`, `via` | Verdikt passt zu `expect`; `UNRESOLVED` zählt nie als bestanden |
| `policy_scope` | `src`, `dst` (Hosts), `allow` (`["tcp/443", "icmp"]`) | alles, was zwischen den EPGs der Hosts Verkehr erlaubt, ist höchstens so breit wie `allow`; pauschale Freigaben (unenforced VRF, Preferred Group, gleiche EPG) fallen durch |
| `endpoint` | `host`, `epg` | Host gelernt, optional in dieser EPG |
| `exists`, `class` | `dn`/`cls`, `attrs` | Objekt mit diesen Attributen vorhanden |
| `nofaults` | `under`, `code` | keine passenden Faults |
| weitere | siehe `server.check_lab` | Router, Routen, NTP, VMM, Firmware … |

### Kategorien

Jede Prüfung hat eine Kategorie: `functional`, `security`, `understanding`, `diagnosis`. Ohne Angabe gilt: `traffic` mit `expect: false` und `policy_scope` sind `security`, alles andere `functional`. Die Bewertung zeigt jede Kategorie getrennt.

### Gute Labs

- Mindestens ein Negativtest je Freigabe: anderer Port, anderes Protokoll (ICMP), Gegenrichtung, laterale EPG.
- Bei Least Privilege eine `policy_scope`-Prüfung, damit Permit-any nicht besteht.
- Gleichwertige Lösungen zulassen: keine Namen prüfen, wenn die Aufgabe keine verlangt.
- Dienste der Hosts angeben (`services`), damit ein Drop am Dienst nicht wie ein Policy-Drop aussieht.

## Tests für ein neues Lab

`test_all_labs_solvable` prüft automatisch: ohne Lösung nicht bestanden, mit `SOLUTIONS[id]` alles bestanden. Für Least-Privilege-Labs zusätzlich Tests für Permit-any und mindestens eine gleichwertige Lösung schreiben, wie in `tests/test_least_privilege.py`.
