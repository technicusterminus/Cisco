# Antworten Aufgabe 1

1. object `{…}` (z. B. `device`), array `[…]` (`interfaces`), string (`"SW-LAB1"`), number (`86400`, `10`), boolean (`true`/`false`), null (`"ipv4": null`).
2. `SW-LAB1`; `d["device"]["hostname"]`.
3. `2`; Pfad `device` → `location` → `floor` (drei Ebenen).
4. 5 Interfaces, davon 4 mit `enabled: true`.
5. `[10, 20, 99]`; `allowed_vlans` ist ein **Array** von Zahlen.
6. `null` = kein Wert/nicht gesetzt; `""` ist ein vorhandener, aber leerer String. Beim Auswerten ist der Unterschied wichtig: `null` hat keine Felder (`None["address"]` wirft einen Fehler).
7. `192.168.10.1` und `255.255.255.0`; Schlüssel `address` und `mask` im Objekt `ipv4`.
8. `{}` = Objekt (ungeordnete Schlüssel–Wert-Paare), `[]` = Array (geordnete Liste). JSON erlaubt nur doppelte Anführungszeichen, keine Kommentare, keine abschliessenden Kommas.
9. Ungültig sind (a) abschliessendes Komma, (b) einfache Anführungszeichen, (d) `True` (muss `true` sein). Gültig: (c) und (e).
10. Siehe `solutions/ex01_extract.py`.
11. Fehler in `broken.json`: einfache Anführungszeichen (`'SW-LAB2'`), `True` statt `true`, abschliessendes Komma nach `"vlan": 20`, fehlendes Komma zwischen `"Gi1/0/3"` und `"enabled"`, fehlendes Komma nach der `ports`-Liste. Korrigierte Fassung: `solutions/ex01_broken_fixed.json`.
