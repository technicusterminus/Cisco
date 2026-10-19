# Aufgabe 1 – JSON lesen (Ziel 6.7)

Datei: [`interfaces.json`](interfaces.json). Beantworte die Fragen ohne Hilfsmittel, prüfe dann mit Python (`python3 -c "import json; d=json.load(open('interfaces.json')); ..."`).

1. Welche **Datentypen** kommen vor (object, array, string, number, boolean, null)? Gib je ein Beispiel aus der Datei.
2. Wie lautet der Hostname, und wie greifst du in Python darauf zu (`d[...]...`)?
3. Welche Stockwerk-Nummer steht in der Datei, und wie tief ist der Pfad geschachtelt?
4. Wie viele Interfaces sind in `interfaces` enthalten, wie viele davon haben `enabled: true`?
5. Welche VLANs sind auf dem Trunk erlaubt? Ist `allowed_vlans` ein Objekt oder ein Array?
6. Was bedeutet `"ipv4": null`, und worin unterscheidet es sich von `"description": ""`?
7. Welche IP-Adresse hat `Vlan10`, und welche Maske? Wie lauten die Schlüssel (Key–Value-Paare)?
8. Erkläre den Unterschied zwischen `{}` und `[]`, und warum JSON keine Kommentare und keine einfachen Anführungszeichen erlaubt.
9. Welche der folgenden Zeilen sind in JSON **ungültig**? (a) `{"vlan": 10,}` (b) `{'vlan': 10}` (c) `{"vlan": "10"}` (d) `{"enabled": True}` (e) `{"a": [1, 2, 3]}`
10. **Praxis:** Schreibe die Funktionen in `extract.py` so, dass `python3 -m unittest -v test_ex01` grün wird.
11. **Reparatur:** `broken.json` ist kaputt. Behebe die Fehler, bis `python3 check_json.py` „OK“ meldet.
