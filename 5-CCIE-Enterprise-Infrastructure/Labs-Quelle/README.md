# Labs-Quelle

Aus diesen Dateien entstehen die CCIE-Labs in [`CML-Labs`](../CML-Labs/) und [`EVE-NG-Labs`](../EVE-NG-Labs/).

| Datei | Inhalt |
|---|---|
| `lab_c1.py` … `lab_c6.py` | eine Lab-Definition je Datei: Geräte, Basis- und Musterkonfiguration, Links, Aufgaben (Teil A), Tickets (Teil B), Transferfragen (Teil C), Fehler |
| `lablib.py` | erzeugt aus einer Definition CML-YAML, EVE-NG-Dateien, READMEs und Fehlerliste und prüft sie |
| `build_labs.py` | liest alle `lab_c*.py`, schreibt alle Dateien und die beiden Übersichts-READMEs |

```
pip install pyyaml
python3 build_labs.py
```

## Wie ein Fehler beschrieben wird

Ein Fehler ist eine Änderung an der fertigen Konfiguration eines Geräts. Daraus entstehen die Reparatur-Topologie, die Fehlerliste und der Diff, sie können also nicht auseinanderlaufen.

```python
dict(node="R2", old=" bfd all-interfaces", new=None,          # Zeile entfernen
     find="…", cause="…", fix="…")
dict(node="R3", old=" tunnel key 100", new=" tunnel key 101")  # Zeile ersetzen
dict(node="R1", old=None, new=" ip ospf cost 10", ctx="interface GigabitEthernet0/0", nth=1)  # nach der 2. Zeile ctx einfügen
```

`nth` zählt Treffer (ab 0), falls eine Zeile mehrfach vorkommt. `ctx` begrenzt die Suche auf den Bereich ab einer eindeutigen Zeile.

Der Build bricht ab, wenn eine Zeile nicht gefunden wird, ein Link ein Interface doppelt belegt oder die Zahl der Tickets nicht zur Zahl der Fehler passt.
