# Lab E3 – BFD für schnelle Fehlererkennung mit OSPF

**Dauer:** 75 min · **Niveau:** mittel · **Nodes:** 3× iosv, 1× unmanaged_switch

Drei Router mit OSPF, davon zwei über einen Layer-2-Switch verbunden. Fällt ein Port hinter dem Switch aus, merkt der Nachbar das nur über den OSPF-Dead-Timer. Mit BFD sinkt die Erkennungszeit von 40 Sekunden auf unter eine Sekunde. Dazu die BFD-Timer-Aushandlung und die typischen Fehler bei der Konfiguration.

**Lernziele:** Nach diesem Lab kannst du …

- Den Ausfall hinter einem Switch ohne BFD messen und die Dead-Timer-Verzögerung erklären.
- BFD auf Interface-Ebene und als OSPF-Client konfigurieren.
- Mit `show bfd neighbors` und `show bfd neighbors details` Sitzungen, Timer und Clients prüfen.
- Erklären, wie sich die Erkennungszeit aus den Timern beider Seiten ergibt.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::1.8` | Bidirectional Forwarding Detection | 7 |
| `Ziel::1.10.b` | OSPF: Nachbarschaft und Authentisierung | 10 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
   R1 Lo1 10.1.1.1/24              R2 Lo1 10.2.2.2/24
   R1 ──Gi0/0── SW ──Gi0/0── R2
    │ Gi0/1                  Gi0/1 │
    └──── Gi0/0  R3  Gi0/1 ────────┘
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – SW – R2 Gi0/0 | 10.0.12.0/24 (R1 .1, R2 .2) |
| R1 Gi0/1 – R3 Gi0/0 | 10.0.13.0/30 (.1/.2) |
| R2 Gi0/1 – R3 Gi0/1 | 10.0.23.0/30 (R2 .1, R3 .2) |
| LANs (Loopback1) | R1 10.1.1.0/24, R2 10.2.2.0/24 |

Der direkte Weg R1–SW–R2 ist der kürzeste (Kosten 1 je Link), der Umweg über R3 kostet einen Link mehr. Weil R1 und R2 über den Switch verbunden sind, bleibt der Link an R1 **up**, wenn du auf R2 `shutdown` am Gi0/0 eingibst. R1 merkt den Ausfall nur durch ausbleibende Hellos. Genau dafür ist BFD da.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **OSPF aufbauen.** Auf R1, R2 und R3: `router ospf 1` mit eigener `router-id` und `network`-Anweisungen für alle Links und LANs in Area 0.
   - **Prüfen:** `show ip ospf neighbor` auf R1 zeigt R2 und R3 in FULL. `show ip route 10.2.2.0` führt über 10.0.12.2 (direkter Weg).
   - **Denkfrage:** Welche Kosten hat der Weg über R3, und warum wird er jetzt nicht benutzt?
2. **Ausfall ohne BFD messen.** Starte auf R1 `ping 10.2.2.2 source Loopback1 repeat 100000`. Gib auf R2 `shutdown` unter Gi0/0 ein.
   - **Prüfen:** Die Pings brechen ab. R1 behält R2 etwa 40 Sekunden in FULL, erst dann schwenkt die Route auf den Weg über R3. Danach `no shutdown` auf R2 Gi0/0.
   - **Denkfrage:** Warum erkennt R1 den Ausfall nicht sofort am Interface?
3. **BFD-Timer am Interface setzen.** Auf R1, R2 und R3 an jedem Interface mit OSPF-Nachbarn: `bfd interval 300 min_rx 300 multiplier 3`.
   - **Prüfen:** `show bfd neighbors` ist noch leer, weil noch kein Client (OSPF) die Sitzung anfordert.
   - **Denkfrage:** Was legt `interval` fest, was `min_rx`, was `multiplier`?
4. **OSPF als BFD-Client anmelden.** Unter `router ospf 1` auf allen Routern `bfd all-interfaces`.
   - **Prüfen:** `show bfd neighbors` listet pro Link eine Sitzung im Zustand Up, Client OSPF. `show ip ospf interface Gi0/0` nennt BFD.
   - **Denkfrage:** Was ist der Unterschied zwischen `bfd all-interfaces` im Prozess und `ip ospf bfd` am Interface?
5. **Ausfall mit BFD wiederholen.** Starte erneut den Dauer-Ping und gib `shutdown` auf R2 Gi0/0 ein.
   - **Prüfen:** Die Route schwenkt in unter einer Sekunde auf R3 um, höchstens wenige Pings gehen verloren. `show ip ospf neighbor` zeigt R2 nicht mehr.
   - **Denkfrage:** Wie lang ist die Erkennungszeit bei 300 ms und Multiplier 3, und wovon hängt sie ab?
6. **Weitere Clients einordnen.** Dieses Lab nutzt nur OSPF.
   - **Denkfrage:** Wie bindest du BFD an BGP (`neighbor … fall-over bfd`) und an eine statische Route (`ip route static bfd …`)?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Die Kosten sind 1 (R1→R3) + 1 (R3→R2) + 1 (Loopback) = 3 gegen 1 + 1 = 2 über den Switch. Der Weg über R3 hat die höheren Kosten und wird nur als Backup bereitgehalten.
- **Zu 2:** Der Link zum Switch bleibt aktiv, nur die Gegenseite ist weg. R1 sieht Carrier und erkennt den Fehler erst am **Dead-Timer** (Standard bei Broadcast: 40 s, vier Hello-Intervalle à 10 s).
- **Zu 3:** `interval` ist das Sendeintervall der eigenen Pakete, `min_rx` das kürzeste Empfangsintervall, das du akzeptierst, `multiplier` die Zahl verlorener Pakete, bis die Sitzung als down gilt.
- **Zu 4:** `bfd all-interfaces` meldet alle OSPF-Interfaces des Prozesses an, `ip ospf bfd` wirkt nur am Interface. Am Interface lässt sich BFD mit `ip ospf bfd disable` auch gezielt abschalten, selbst wenn der Prozess `all-interfaces` hat. Das ist eine klassische Fehlerquelle.
- **Zu 5:** Die Erkennungszeit ist **Multiplier der Gegenseite × größeres von (eigenes min_rx, Tx-Intervall der Gegenseite)**. Hier 3 × 300 ms = 900 ms. Ist ein Multiplier oder ein Intervall größer, bestimmt der größere Wert das Ergebnis.
- **Zu 6:** BGP: `neighbor <IP> fall-over bfd` (bei Single-Hop-eBGP). Statische Route: `ip route static bfd <Interface> <Next-Hop>` plus die statische Route, die dann nur bei lebender BFD-Sitzung installiert bleibt.

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** Beim Test (R2 Gi0/0 `shutdown`) braucht R1 etwa 40 Sekunden, bis die Route umschwenkt; `show bfd neighbors` auf R1 zeigt keine Sitzung zu R2 im Zustand Up.

**Ticket 2:** Die BFD-Sitzung zwischen R1 und R3 fehlt; auf R1 steht für Gi0/1 keine Sitzung in `show bfd neighbors`.

**Ticket 3:** Der Umschwenk bei Ausfall von R2 Gi0/0 dauert rund 9 Sekunden statt unter einer Sekunde, obwohl die Sitzung Up ist.

**Ticket 4:** Trotz funktionierendem Direktweg läuft der Verkehr von R1 zu 10.2.2.2 über R3.

**Ticket 5:** Zwischen R3 und R2 gibt es keine BFD-Sitzung, auch nachdem R2 BFD im OSPF angemeldet hat.

## Verifikation
```
show ip ospf neighbor
show ip ospf interface brief
show bfd neighbors
show bfd neighbors details
show ip route 10.2.2.0
ping 10.2.2.2 source Loopback1 repeat 100000   ! beim Ausfalltest
```

| Befehl | Das solltest du sehen |
|---|---|
| `show bfd neighbors` auf R1 | zwei Sitzungen (10.0.12.2 und 10.0.13.2) im Zustand Up, Client OSPF |
| `show bfd neighbors details` auf R1 | eigener und empfangener Multiplier 3, Intervall 300 ms |
| `show ip route 10.2.2.0` auf R1 | Next-Hop 10.0.12.2; nach dem Ausfall 10.0.13.2 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. `bfd all-interfaces` steht im OSPF, trotzdem gibt es keine BFD-Sitzung. Was prüfst du?
<details><summary>Antwort</summary>

**Interface-Timer, Gegenseite und Interface-Override.** 1) Hat das Interface `bfd interval …`? 2) Meldet auch die Gegenseite BFD an (`show ip ospf interface`)? 3) Steht am Interface `ip ospf bfd disable`? 4) Ist der OSPF-Nachbar überhaupt FULL? BFD wird erst nach einer aufgebauten Nachbarschaft angefordert.

</details>

2. Was ist der Unterschied zwischen BFD im Asynchronous Mode und im Echo Mode?
<details><summary>Antwort</summary>

**Asynchron schicken sich beide Seiten periodisch Control-Pakete, im Echo-Modus schickt eine Seite Pakete, die der Nachbar nur zurückspiegelt.** Der Echo-Weg prüft den Forwarding-Pfad des Nachbarn, ohne dessen Control Plane zu belasten. Die Control-Pakete laufen dann mit niedrigerer Rate weiter.

</details>

3. Warum ist ein sehr aggressives BFD-Intervall (50 ms) nicht immer eine gute Idee?
<details><summary>Antwort</summary>

**Kurze Timer erhöhen die CPU-Last und machen das Netz anfällig für Flapping.** Ein kurzer Aussetzer oder Last-Spitze lässt die Sitzung fallen, der Routing-Prozess berechnet neu, und das erzeugt oft mehr Instabilität, als es schützt. Auf Hardware mit BFD im Line-Card-Offload geht das, in virtuellen Umgebungen nicht.

</details>

## Prüfungsbezug
- BFD erkennt Ausfälle unabhängig vom Routing-Protokoll in Millisekunden; die Routing-Protokolle melden sich als Clients an.
- Konfiguration: Timer am Interface (`bfd interval … min_rx … multiplier …`), Client im Protokoll (`bfd all-interfaces`, `neighbor … fall-over bfd`).
- Erkennungszeit = Multiplier der Gegenseite × max(eigenes min_rx, Tx der Gegenseite).
- `ip ospf bfd disable` am Interface schlägt `bfd all-interfaces` im Prozess.
- Fehlersuche: `show bfd neighbors [details]`, `show ip ospf interface`, `debug bfd packet` (kurz).

## Hinweis zum Image

BFD ist auf virtuellen Routern nicht mit Hardware vergleichbar: Die Pakete laufen über die CPU des Hosts. Bleibe bei **300 ms** oder mehr, sonst flattern die Sitzungen in der Simulation. Ob dein IOSv-Image BFD mit allen Optionen beherrscht, hängt von der Version ab; die Syntax folgt der IOS-15-Dokumentation und ist hier nicht in einer laufenden Simulation getestet.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
