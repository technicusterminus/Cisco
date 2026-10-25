# Antworten Aufgabe 1 (Ausgaben, tatsächlich ausgeführt)

Erst selbst vorhersagen, dann `python3 ex01_predict/pN.py` ausführen und vergleichen. Unter jeder Ausgabe steht, warum sie so aussieht.

## p1

```
[30, 40, 50]
[50, 60]
5 190
```
**Warum:** Nach `append(60)` und `remove(20)` ist die Liste `[10, 30, 40, 50, 60]`. `remove` löscht den Wert 20, nicht die Position 20. `[1:4]` liefert die Indizes 1 bis 3, denn das Ende eines Slice ist exklusiv. `[-2:]` sind die letzten beiden Elemente. Fünf Elemente ergeben zusammen 190.

## p2

```
name -> SW1
vlans -> [10, 20, 30]
mgmt -> 10.0.0.1
unbekannt
True False
```
**Warum:** `sw["vlans"]` ist dieselbe Liste wie im Dictionary, `append` ändert sie also direkt. `get("model", "unbekannt")` liefert den Default, weil der Schlüssel fehlt, statt einen `KeyError` zu werfen. `in` prüft bei Dictionaries nur die Schlüssel: `"mgmt"` ist einer, `"SW1"` ist nur ein Wert.

## p3

```
R1:830
    R1|830   |000830
Status: UP
10-0-0-1
```
**Warum:** `>6` füllt auf 6 Zeichen und schiebt den Text nach rechts, `<6` nach links. `06d` füllt eine Zahl mit führenden Nullen auf 6 Stellen. Der bedingte Ausdruck `'UP' if up else 'DOWN'` wählt den Text, und `join` setzt den Bindestrich zwischen die Teile.

## p4

```
<class 'dict'> True
['10.0.0.1', '10.0.0.2']
{"name": "USERS", "vlan": 10}
```
**Warum:** `json.loads` macht aus einem JSON-Objekt ein `dict` und aus `true` den Python-Wert `True`. Die List-Comprehension läuft durch die Liste `address` und nimmt aus jedem Eintrag `ip`. `json.dumps` liefert einen String mit doppelten Anführungszeichen, `sort_keys=True` sortiert die Schlüssel, deshalb steht `name` vor `vlan`.

## p5

```
fertig a
5.0
fertig b
fehlt
fertig a
Typ
```
**Warum:** `finally` läuft immer, auch wenn `try` oder `except` schon `return` erreicht haben. Es läuft, bevor die Funktion zurückkehrt, deshalb steht `fertig …` vor dem Ergebnis. Fall b löst einen `KeyError` aus (Schlüssel fehlt), Fall c einen `TypeError` (`"x" / 2` geht nicht).

## p6

```
['sw1', 'sw3']
{'sw1': 24, 'sw2': 48, 'sw3': 48}
96
```
**Warum:** Die erste Comprehension filtert nach Status und behält nur die Namen. `{k: v for ...}` baut ein Dictionary aus Name und Portzahl. `sum` addiert nur die Geräte mit mehr als 24 Ports: 48 + 48 = 96.

## p7

```
[10]
[10, 20]
[30]
```
**Warum:** Der Default `liste=[]` wird nur einmal angelegt, wenn Python die Funktion definiert. Jeder Aufruf ohne zweites Argument arbeitet mit derselben Liste, deshalb steht beim zweiten Aufruf schon 10 drin. Der dritte Aufruf bekommt eine eigene, neue Liste. Richtig ist `liste=None` und in der Funktion `if liste is None: liste = []`.

## p8

```
3
['GigabitEthernet0/0', 'Loopback0']
{'name': 'GigabitEthernet0/1', 'ip': 'unassigned', 'up': False}
```
**Warum:** `splitlines()[1:]` überspringt die Kopfzeile. `split()` ohne Argument trennt an beliebig viel Leerraum, deshalb stören die breiten Spalten nicht. `status == "up"` ergibt direkt `True` oder `False`. `rows[1]` ist die zweite Datenzeile, weil die Zählung bei 0 beginnt.

