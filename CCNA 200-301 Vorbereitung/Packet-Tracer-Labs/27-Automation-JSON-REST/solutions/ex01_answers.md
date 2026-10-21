# Antworten Aufgabe 1

1. **Alle sechs kommen vor.** Objekt `{…}`: `device`. Array `[…]`: `interfaces`. String: `"SW-LAB1"`. Number: `86400` (Uptime) oder `10` (VLAN). Boolean: `true` und `false` bei `enabled`. Null: `"ipv4": null`.
2. **`SW-LAB1`, in Python `d["device"]["hostname"]`.** Jede Ebene eines Objekts öffnest du mit dem Schlüssel in eckigen Klammern.
3. **`2`, drei Ebenen tief: `device` → `location` → `floor`.** In Python also `d["device"]["location"]["floor"]`.
4. **5 Interfaces, davon 4 mit `enabled: true`.** Nur `GigabitEthernet1/0/3` steht auf `false`. In Python: `sum(i["enabled"] for i in d["interfaces"])`, denn `True` zählt als 1.
5. **10, 20 und 99. `allowed_vlans` ist ein Array.** Die eckigen Klammern verraten es: eine geordnete Liste von Zahlen, ohne Schlüssel.
6. **`null` heißt „kein Wert“, `""` ist ein vorhandener, aber leerer Text.** Der Unterschied zählt beim Auswerten: `d[...]["ipv4"]` ist in Python `None`, und `None["address"]` wirft einen Fehler. Prüfe also erst, ob ein Wert da ist.
7. **`192.168.10.1` mit Maske `255.255.255.0`.** Sie stehen im Objekt `ipv4` unter den Schlüsseln `address` und `mask`.
8. **`{}` ist ein Objekt aus Schlüssel-Wert-Paaren, `[]` eine geordnete Liste.** JSON ist bewusst streng, damit jedes Programm es gleich liest. Deshalb gibt es nur doppelte Anführungszeichen, keine Kommentare und kein Komma nach dem letzten Element.
9. **Ungültig sind (a), (b) und (d).** (a) hat ein Komma nach dem letzten Element. (b) nutzt einfache Anführungszeichen. (d) schreibt `True` wie in Python, JSON verlangt `true`. (c) ist gültig, `"10"` ist eben ein String. (e) ist ein gültiges Array.
10. **Siehe `solutions/ex01_extract.py`.**
11. **Fünf Fehler.** Einfache Anführungszeichen um `'SW-LAB2'`, `True` statt `true`, ein Komma nach `"vlan": 20`, ein fehlendes Komma zwischen `"Gi1/0/3"` und `"enabled"` und ein fehlendes Komma nach der `ports`-Liste. Die korrigierte Fassung steht in `solutions/ex01_broken_fixed.json`.
