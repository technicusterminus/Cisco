# Lab 03 – eBGP Dual-Homing und Policy

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel bis schwer

Kunde mit zwei Providern: eBGP-Sessions, Best-Path-Auswahl, Local-Preference, AS-Path-Prepending, MED, No-Transit-Filter und Soft-Reset. Private AS-Nummern dienen nur der Übung.

**Lernziele:** Nach diesem Lab kannst du …

- Eine eBGP-Anbindung an zwei Provider aufbauen und Präfixe gezielt ankündigen.
- Mit Route-Maps und Local Preference den Ausgang steuern.
- Verhindern, dass das eigene AS zum Transit zwischen den Providern wird.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.2.c` | Direktes eBGP | 61 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| R4 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.0 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R1 | Gi0/1 | R3 | Gi0/0 |
| R2 | Gi0/1 | R4 | Gi0/0 |
| R3 | Gi0/1 | R4 | Gi0/1 |


## Topologie

```
          AS 65010                 AS 65100
        ┌── R2 ──────────┐
 AS 65001│  Gi0/0   Gi0/1│
   R1 ───┤               ├── R4  (Internet, 198.51.100.0/24)
        │  Gi0/0   Gi0/1│
        └── R3 ──────────┘
          AS 65020
```

| Link | Netz | Seiten |
|---|---|---|
| R1–R2 | 10.12.0.0/30 | R1 .1 / R2 .2 |
| R1–R3 | 10.13.0.0/30 | R1 .1 / R3 .2 |
| R2–R4 | 10.24.0.0/30 | R2 .1 / R4 .2 |
| R3–R4 | 10.34.0.0/30 | R3 .1 / R4 .2 |

R1 = Kunde (AS 65001) mit **203.0.113.0/24** (statisch Null0). R2 = ISP-A (AS 65010), R3 = ISP-B (AS 65020), R4 = Internet (AS 65100) mit **198.51.100.0/24** (Lo1). Router-IDs: R1 1.1.1.1, R2 **20.20.20.20**, R3 3.3.3.3, R4 4.4.4.4. Die Absicht: Ohne Policy herrscht Gleichstand bis zu den letzten Tie-Breakern (ältester eBGP-Pfad, dann niedrigere Router-ID). Dabei gewinnt leicht ISP-B, also das Gegenteil des Ziels.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **eBGP-Sessions aufbauen.** Verbinde R1–R2, R1–R3, R2–R4 und R3–R4 über die direkten Interface-Adressen. Setze die Router-IDs wie oben mit `bgp router-id`.
   - **Prüfen:** `show ip bgp summary` zeigt bei jedem Nachbarn eine Zahl in der letzten Spalte, also Established.
2. **Präfixe ankündigen.** R1 kündigt 203.0.113.0/24 an, R4 kündigt 198.51.100.0/24 an. Beide Präfixe brauchen eine passende Route in der Routing-Tabelle.
   - **Prüfen:** `show ip bgp 198.51.100.0` auf R1 zeigt zwei Pfade.
   - **Denkfrage:** Welcher Pfad gewinnt auf R1, und an welcher Stelle der Best-Path-Auswahl fällt die Entscheidung?
3. **Ausgehenden Verkehr steuern.** R1 soll über ISP-A (R2) senden. Setze dazu per Route-Map eingehend auf die Routen von R2 `local-preference 200`.
   - **Prüfen:** `show ip bgp` auf R1 zeigt beim Pfad über 10.12.0.2 LocPrf 200 und das Zeichen `>`.
   - **Denkfrage:** Warum wirkt Local Preference nur im eigenen AS, und wie erfahren andere Router im AS davon?
4. **Eingehenden Verkehr steuern.** R1 hängt bei der Ankündigung an R3 die eigene AS dreimal vorne an (AS-Path-Prepending).
   - **Prüfen:** `show ip bgp 203.0.113.0` auf R4 zeigt den Pfad über R3 mit `65020 65001 65001 65001 65001` und wählt den kürzeren über R2.
   - **Denkfrage:** Warum steuert Prepending nur den Verkehr, der zu dir hereinkommt?
5. **MED ausprobieren.** Entferne das Prepending. Setze stattdessen `metric 50` Richtung R2 und `metric 100` Richtung R3.
   - **Prüfen:** Auf R4 ändert sich die Pfadwahl nicht.
   - **Denkfrage:** Warum nicht, und was würde `bgp always-compare-med` ändern?
6. **Kein Transit.** R1 darf keine Routen von einem Provider an den anderen weitergeben. Erlaube ausgehend nur lokal erzeugte Routen: `ip as-path access-list 1 permit ^$` in einer Route-Map Richtung R2 und R3.
   - **Prüfen:** `show ip bgp neighbors 10.12.0.2 advertised-routes` auf R1 zeigt nur noch 203.0.113.0/24.
7. **Ohne Abbruch neu anwenden.** Ändere eine Route-Map und wende sie mit `clear ip bgp * soft in` bzw. `soft out` an.
   - **Prüfen:** In `show ip bgp summary` läuft die Up-Zeit der Sessions weiter.
   - **Denkfrage:** Warum ist ein hartes `clear ip bgp *` im Betrieb ein Fehler?
8. **Optional: Schutzfilter.** Begrenze mit `neighbor … maximum-prefix 100 80` die Anzahl der Präfixe und baue eine Prefix-List gegen private und reservierte Netze (Bogons).

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** Bis einschließlich AS-Pfad-Länge herrscht Gleichstand: beide Pfade mit Weight 0, Local Preference 100, AS-Pfad aus zwei AS. Origin und MED sind gleich, beide Pfade kommen per eBGP. Dann wählt IOS den älteren eBGP-Pfad und erst danach die niedrigere Router-ID. Welcher Provider gewinnt, hängt also davon ab, welche Session zuerst stand. Genau deshalb setzt man eine Policy.
- **Zu 3:** Local Preference wird nur per iBGP weitergegeben, nie an eBGP-Nachbarn. Sie gilt also für alle Router im eigenen AS, und alle wählen damit denselben Ausgang.
- **Zu 4:** Prepending verändert, was die anderen über dich sehen. Ihr Weg zu dir wird länger, also wählen sie einen anderen. Deinen eigenen Ausgang beeinflusst das nicht.
- **Zu 5:** IOS vergleicht MED standardmäßig nur zwischen Pfaden aus demselben Nachbar-AS. R4 bekommt die Pfade aber von AS 65010 und AS 65020. Mit `bgp always-compare-med` auf R4 würde MED auch über AS-Grenzen hinweg verglichen.
- **Zu 7:** Ein hartes Clear baut alle Sessions ab. Alle Routen verschwinden und müssen neu gelernt werden, das bedeutet einen Ausfall. Soft Reset (Route Refresh) verschickt nur die Updates neu.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Die Session R1–R2 kommt nicht hoch (Idle/Active), das Log meldet eine falsche Nachbar-AS.

**Ticket 2:** R1 wählt zu 198.51.100.0/24 den Pfad über ISP-B, obwohl ISP-A bevorzugt sein soll (LocPrf überall 100).

**Ticket 3:** Auf R2 erscheint 198.51.100.0/24 zusätzlich mit AS-Path `65001 65020 65100`, R1 wird zum Transit.

**Ticket 4:** Weder R2 noch R3 lernen 198.51.100.0/24, R1 hat keine Internet-Route.

**Ticket 5:** Der Kundenbereich 203.0.113.0/24 ist aus dem Internet nicht erreichbar, R2/R3 sehen kein Präfix von R1.

## Verifikation
```
show ip bgp summary
show ip bgp
show ip bgp 198.51.100.0/24
show ip bgp neighbors 10.12.0.2 advertised-routes
show route-map
show ip bgp regexp ^65010
```

| Nach Schritt | Das solltest du sehen |
|---|---|
| 3 | R1 wählt zu 198.51.100.0/24 den Next-Hop 10.12.0.2 mit LocPrf 200 |
| 4 | R4 wählt zu 203.0.113.0/24 den Pfad über R2 |
| 6 | R2 und R3 bekommen von R1 nur 203.0.113.0/24 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Warum bleibt eine eBGP-Session in `Active`?
<details><summary>Antwort</summary>

**Weil TCP nicht zustande kommt oder die OPEN-Nachricht abgelehnt wird.** Active heißt: Der Router versucht aktiv, die Sitzung aufzubauen, bekommt aber keine. Typische Ursachen: falsche Nachbar-IP oder AS, keine Route oder eine ACL für TCP 179, fehlendes `ebgp-multihop` beim Peering über Loopbacks, falsches Passwort.

</details>

2. Wann nutzt man `next-hop-self` in iBGP?
<details><summary>Antwort</summary>

**Wenn der eBGP-Next-Hop im IGP nicht bekannt ist.** iBGP gibt den Next-Hop unverändert weiter. Kennt der iBGP-Nachbar ihn nicht, ist die Route für ihn unbrauchbar und wird nicht installiert. Mit `next-hop-self` trägt der Rand-Router sich selbst als Next-Hop ein.

</details>

3. Was passiert mit AS-Pfaden, wenn R1 ISP-B-Routen an ISP-A schickt?
<details><summary>Antwort</summary>

**ISP-A würde sie annehmen, und R1 würde Transit für fremden Verkehr.** Der AS-Pfad ist gültig, also gibt es keinen Grund zum Verwerfen. Das verhindert nur ein Ausgangsfilter, der nur eigene Routen erlaubt, z. B. AS-Path `^$` oder eine Prefix-List.

</details>

## Prüfungsbezug
- Best Path: Weight → Local Preference → lokal erzeugt → AS-Pfad-Länge → Origin → MED → eBGP vor iBGP → IGP-Metrik zum Next-Hop → ältester eBGP-Pfad → niedrigste Router-ID.
- Den eigenen Ausgang steuern Local Preference und Weight, den Eingang Prepending und MED.
- `network` kündigt nur an, was mit genau dieser Maske in der Routing-Tabelle steht.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/03-eBGP-Policy/`](../../CML-Labs/03-eBGP-Policy/).
