# Übung 2: Ping und Traceroute

## Aufgabe A: Ping-Reihe

Führe nacheinander aus und notiere, ob es klappt:

```
ping 127.0.0.1
ping <deine eigene IP>
ping <dein Gateway>
ping 8.8.8.8
ping www.example.com
```

Wo bricht es ab, wenn du das WLAN trennst? Was passiert, wenn du das Gateway absichtlich falsch einträgst (nur in einer VM oder wenn du zurückstellen kannst)?

## Aufgabe B: Traceroute

```
tracert 8.8.8.8          (Windows)
traceroute 8.8.8.8       (Linux/macOS)
```

1. Wie viele Hops siehst du?
2. Was ist der erste Hop? (Tipp: dein Gateway.)
3. Was bedeuten Sternchen `* * *`?
4. Wie ändert sich die Zeit pro Hop, je weiter das Ziel ist?

<details><summary>Lösungshinweise</summary>

- Erste Zeile = dein Router. Danach der Provider.
- `* * *`: Der Hop antwortet nicht auf ICMP (gefiltert), der Weg geht trotzdem weiter.
- Die Zeit wächst meist mit der Entfernung, kleine Sprünge sind normal.
</details>

## Merke

Ping benutzt ICMP. Ein fehlgeschlagener Ping heißt nicht immer „Gerät kaputt“, manche Ziele blocken ICMP.
