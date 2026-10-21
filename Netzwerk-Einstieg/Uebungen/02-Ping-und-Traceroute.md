# Übung 2: Ping und Traceroute

**Ziel:** Du prüfst Schritt für Schritt, wie weit deine Verbindung reicht, und verfolgst den Weg ins Internet.

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

- **Aufgabe A:** Die Reihe testet von nah nach fern. Ohne WLAN scheitert es ab dem Gateway. Mit falschem Gateway klappen Loopback und eigene IP, alles außerhalb deines Subnetzes nicht.
- **Erster Hop = dein Router (Gateway).** Danach folgen die Router deines Providers.
- **`* * *` heißt: Dieser Router antwortet nicht.** Oft filtert er ICMP. Der Weg geht trotzdem weiter, wenn spätere Hops wieder antworten.
- **Die Zeit wächst meist mit der Entfernung.** Kleine Sprünge sind normal, weil Router Ping-Antworten nur nebenbei bearbeiten.

</details>

## Merke

Ping benutzt ICMP. Ein fehlgeschlagener Ping heißt nicht immer „Gerät kaputt“, manche Ziele blocken ICMP.
