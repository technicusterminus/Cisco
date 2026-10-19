# Antworten Aufgabe 1 (Ausgaben, tatsächlich ausgeführt)

Erst selbst vorhersagen, dann `python3 ex01_predict/pN.py` ausführen und vergleichen. Hinweise zu den Fallen stehen jeweils darunter.

## p1

```
[30, 40, 50]
[50, 60]
5 190
```
`remove(20)` entfernt das Element, nicht den Index; Slices enden exklusiv.

## p2

```
name -> SW1
vlans -> [10, 20, 30]
mgmt -> 10.0.0.1
unbekannt
True False
```
`dict.get` mit Default; `in` prüft bei Dictionaries die Schlüssel, nicht die Werte.

## p3

```
R1:830
    R1|830   |000830
Status: UP
10-0-0-1
```
`>6` rechtsbündig, `<6` linksbündig, `06d` mit führenden Nullen.

## p4

```
<class 'dict'> True
['10.0.0.1', '10.0.0.2']
{"name": "USERS", "vlan": 10}
```
JSON `true` wird zu Python `True`; `sort_keys` sortiert Schlüssel alphabetisch, die Ausgabe ist ein String.

## p5

```
fertig a
5.0
fertig b
fehlt
fertig a
Typ
```
`finally` läuft immer, auch nach `return`; die Zeile `fertig …` erscheint daher vor dem Ergebnis des jeweiligen `print`.

## p6

```
['sw1', 'sw3']
{'sw1': 24, 'sw2': 48, 'sw3': 48}
96
```
Dictionary-Comprehension mit `{k: v for ...}`; Generator in `sum(...)`.

## p7

```
[10]
[10, 20]
[30]
```
Mutable Default-Argument: Die Liste wird nur einmal angelegt und bei jedem Aufruf wiederverwendet (klassischer Bug).

## p8

```
3
['GigabitEthernet0/0', 'Loopback0']
{'name': 'GigabitEthernet0/1', 'ip': 'unassigned', 'up': False}
```
`split()` ohne Argument trennt an Leerraum; die Kopfzeile wird durch `[1:]` übersprungen.

