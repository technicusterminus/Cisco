# CCNA 200-301: Prüfungssimulation

Datei: [`ccna-pruefungssimulation.html`](ccna-pruefungssimulation.html). Im Browser öffnen, sie läuft offline.

## Was drin ist

- **273 Fragen** aus den sechs Domänen, im Stil der Prüfung: Einfachauswahl, „Wähle zwei“, Exhibit-Fragen mit `show`-Ausgaben und **10 Fragen zum Ordnen und Zuordnen**.
- **Jede Erklärung** nennt zuerst die richtige Antwort und dann den Grund. Wo eine falsche Antwort naheliegt, steht dabei, warum sie nicht passt.

## Modi

- **Prüfung:** 60 Fragen in 60 Minuten. Die Auswahl richtet sich nach dem Gewicht der Domänen (20 / 20 / 25 / 10 / 15 / 10 %). Die Auswertung kommt erst am Ende.
- **Alle Fragen:** der komplette Pool unter Zeitdruck.
- **Üben** mit Erklärung direkt nach jeder Frage: pro Domäne, nur Exhibits oder nur Ordnen und Zuordnen.
- **Falsch beantwortete wiederholen:** Jede falsche Antwort, auch aus einer Prüfung, landet auf einer Liste. Eine Frage verschwindet davon, sobald du sie richtig beantwortest.

Die Auswertung zeigt das Ergebnis pro Domäne und listet alle falschen oder offenen Fragen mit Erklärung. Ergebnisse und Wiederholungsliste speichert der Browser lokal.

## Ordnen und Zuordnen

Wie in der echten Prüfung gibt es Fragen, bei denen du Elemente in eine Reihenfolge bringst oder Begriffe zuordnest. Am Rechner ziehst du sie mit der Maus. Auf Tablet und Handy tippst du erst die Karte und dann das Feld an, die Reihenfolge änderst du mit den Pfeilen. Gewertet wird nur die vollständig richtige Lösung.

## So nutzt du sie

1. Erst im Modus **Üben** pro Domäne durcharbeiten und jede Erklärung lesen, auch bei richtigen Antworten.
2. Dann eine **Prüfung** unter Zeitdruck. Danach **Falsch beantwortete wiederholen**, bis die Liste leer ist.
3. Über 80 % in mehreren Läufen ist ein gutes Zeichen. Weil sich die Fragen bei mehreren Läufen wiederholen, ersetzt das aber nicht das Verstehen.

Die Fragen sind eigene Übungsfragen, keine Original-Prüfungsfragen. Antworten und Elemente werden bei jedem Start neu gemischt.

## Eigene Fragen laden

Die Simulation ist zugleich ein Player für eigene Fragenpools. Unter **Eigene Fragen** speicherst du den eingebauten Pool als JSON-Datei. Die nimmst du als Vorlage, ergänzt oder ersetzt Fragen und lädst die Datei mit **Fragenpool laden** wieder. Ergebnisse und Wiederholungsliste eines eigenen Pools werden getrennt gespeichert, der eingebaute Pool bleibt unverändert.

Eine Datei ist ein JSON-Objekt mit `questions` (Pflicht) und optional `title`, `domains` (Nummer → Name), `weights` (Nummer → Prozent) und `examN` (Fragen im Prüfungsmodus). Drei Fragetypen:

```json
{
  "title": "Mein Pool",
  "questions": [
    {"d": 1, "q": "Welcher Port nutzt SSH?", "o": ["22", "23", "443"], "c": [0],
     "e": "22. Telnet nutzt 23."},
    {"d": 1, "t": "order", "q": "Bring DORA in die richtige Reihenfolge.",
     "o": ["Discover", "Offer", "Request", "Acknowledge"], "e": "Erklärung"},
    {"d": 1, "t": "match", "q": "Ordne die Ports zu.", "l": ["SSH", "DNS"],
     "o": ["22", "53"], "c": [0, 1], "e": "Erklärung"}
  ]
}
```

- **Auswahl** (Standard): `o` sind die Antworten, `c` die Indizes der richtigen (mehrere = „Wähle zwei“). `x` nimmt ein Exhibit auf, etwa eine `show`-Ausgabe.
- **Reihenfolge** (`"t": "order"`): `o` steht in der richtigen Reihenfolge, die Simulation mischt selbst.
- **Zuordnung** (`"t": "match"`): `l` sind die Begriffe links, `o` die Karten, `c` gibt für jeden Begriff den Index der passenden Karte an. Gibt es weniger Karten als Begriffe, darf eine Karte mehrfach passen.

In `q`, `o` und `e` sind `<code>` und `<b>` erlaubt. Fehler in der Datei meldet der Player mit der Nummer der Frage.

.vce-Dateien lädt er nicht: Das Format ist proprietär und verschlüsselt, und in Umlauf sind damit fast nur Dumps echter Prüfungsfragen.
