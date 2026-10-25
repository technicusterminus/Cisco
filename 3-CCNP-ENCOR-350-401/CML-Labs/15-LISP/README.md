# Lab 15 – LISP: Map-Server, Map-Resolver, xTR

**Dauer:** 90 min · **Niveau:** schwer · **Nodes:** 6× iosv

Trennung von Identität (EID) und Ort (RLOC): zwei xTR-Standorte, ein kombinierter Map-Server/Map-Resolver und ein „Internet“-Core, der nur RLOCs kennt. Hinweis: Setzt voraus, dass dein IOSv-Image LISP unterstützt (klassisches IOS 15.x, `router lisp`).

**Lernziele:** Nach diesem Lab kannst du …

- LISP mit Map-Server, Map-Resolver und xTRs aufbauen.
- Erklären, wie EID und RLOC zusammenhängen und wie ein Map-Request abläuft.
- Registrierungsfehler auf dem Map-Server finden.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::2.3.a` | LISP | 18 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
 H1 ─ xTR1 ═══════ CORE ═══════ xTR2 ─ H2
 192.168.1.10   RLOC 10.0.1.1   │ 10.0.2.1   192.168.2.10
                                └── MSMR (10.0.99.1)
```

| Gerät | Interface | Adresse |
|---|---|---|
| xTR1 | Gi0/0 (LAN) / Gi0/1 (WAN, RLOC) | 192.168.1.1/24 / 10.0.1.1/30 |
| xTR2 | Gi0/0 (LAN) / Gi0/1 (WAN, RLOC) | 192.168.2.1/24 / 10.0.2.1/30 |
| CORE | Gi0/0 / Gi0/1 / Gi0/2 | 10.0.1.2/30 / 10.0.2.2/30 / 10.0.99.2/30 |
| MSMR | Gi0/0 | 10.0.99.1/30 |
| H1 / H2 | Gi0/0 | 192.168.1.10 / 192.168.2.10 |

Der CORE kennt nur die drei /30-Netze (RLOC-Space). Die EID-Netze 192.168.x.0/24 sind dort **nicht** geroutet. xTRs haben eine Default-Route zum CORE, der MSMR ebenfalls.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Underlay prüfen.** Pinge auf xTR1 `ping 10.0.2.1 source 10.0.1.1` und `ping 10.0.99.1`. Danach pingt H1 seinen Kollegen H2.
   - **Prüfen:** Die beiden Pings von xTR1 klappen, der Ping von H1 zu H2 nicht.
   - **Denkfrage:** Warum erreicht H1 seinen Kollegen H2 noch nicht?
2. **Map-Server und Map-Resolver.** Konfiguriere auf dem MSMR `router lisp` mit `site SITE1` und `site SITE2`, jeweils mit `authentication-key` und `eid-prefix`. Schalte `ipv4 map-server` und `ipv4 map-resolver` ein.
   - **Denkfrage:** Was macht der Map-Server, was der Map-Resolver?
3. **xTRs konfigurieren.** Lege auf jedem xTR an: ein `locator-set` mit der eigenen RLOC-Adresse, unter `eid-table default instance-id 0` ein `database-mapping` für das eigene LAN, dazu `ipv4 itr map-resolver 10.0.99.1`, `ipv4 etr map-server 10.0.99.1 key …`, `ipv4 itr` und `ipv4 etr`.
   - **Denkfrage:** Was ist ein ITR, ein ETR, ein PITR und ein PETR?
4. **Registrierung prüfen.**
   - **Prüfen:** `show lisp site` auf dem MSMR zeigt beide Sites mit „yes“. `show ip lisp database` auf den xTRs zeigt das eigene EID-Netz mit dem RLOC.
5. **Daten senden.** Pinge von H1 zu H2.
   - **Prüfen:** Der erste Ping geht oft verloren, danach klappt es. `show ip lisp map-cache` auf xTR1 zeigt 192.168.2.0/24 mit RLOC 10.0.2.1.
   - **Denkfrage:** Was passiert zwischen dem ersten Paket von H1 und dem Eintrag im Map-Cache?
6. **Unbekanntes Ziel.** Pinge von H1 eine Adresse, die es nirgends gibt, z. B. 192.168.99.1.
   - **Prüfen:** `show ip lisp map-cache` zeigt dafür einen negativen Eintrag.
   - **Denkfrage:** Warum lohnt es sich, auch ein „gibt es nicht“ zu speichern?
7. **Bezug zu SD-Access.**
   - **Denkfrage:** Welche LISP-Rollen findest du in SD-Access wieder, und wie hilft LISP bei wandernden Hosts?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Der Core kennt nur die RLOC-Netze. Die EID-Netze der Hosts sind dort nicht geroutet. Ohne LISP weiß niemand, hinter welchem xTR 192.168.2.10 liegt.
- **Zu 2:** Der Map-Server nimmt die Registrierungen der ETRs an und speichert, welches EID-Netz hinter welchem RLOC liegt. Der Map-Resolver nimmt die Anfragen der ITRs an und leitet sie weiter. Die Antwort kommt am Ende vom zuständigen ETR.
- **Zu 3:** Der ITR (Ingress) verpackt Verkehr, der seine Site verlässt. Der ETR (Egress) packt ankommenden Verkehr aus und registriert seine EIDs. Ein xTR ist beides. PITR und PETR verbinden LISP-Sites mit Netzen ohne LISP: Der PITR nimmt Verkehr von außen an und verpackt ihn, der PETR packt Verkehr zu Zielen ohne LISP aus.
- **Zu 5:** xTR1 hat keinen Cache-Eintrag und schickt einen Map-Request an den Map-Resolver. Der leitet ihn über den Map-Server an xTR2. xTR2 antwortet mit einem Map-Reply direkt an xTR1. xTR1 speichert das Mapping und verpackt die Pakete ab jetzt in UDP 4341 an 10.0.2.1. xTR2 packt sie aus und stellt sie H2 zu.
- **Zu 6:** Ohne den Eintrag würde xTR1 bei jedem Paket erneut nachfragen. Der negative Eintrag sagt für eine Weile: „Gibt es nicht, mach dies oder das damit“, z. B. verwerfen oder an einen PETR schicken.
- **Zu 7:** Der Control Plane Node in SD-Access ist Map-Server und Map-Resolver. Fabric Edges sind xTRs, Border Nodes sind PxTRs. Zieht ein Host um, registriert der neue Edge die EID mit seinem RLOC. Die Adresse des Hosts bleibt gleich, nur das Mapping ändert sich.

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** SITE2 wird auf dem MSMR nie als registriert angezeigt, H1 erreicht H2 nicht (Map-Reply negativ).

**Ticket 2:** xTR1 registriert sein EID-Netz nicht beim MSMR (SITE1 `no`), Rückverkehr von H2 funktioniert nicht.

**Ticket 3:** Der MSMR zeigt SITE2 nicht registriert, im Log `EID-prefix not configured`.

**Ticket 4:** H1 erreicht H2 nie, `show ip lisp map-cache` ist leer (keine Map-Requests).

## Verifikation
```
show lisp site                   ! auf MSMR
show ip lisp                     ! auf xTR
show ip lisp database
show ip lisp map-cache
show ip lisp forwarding eid remote
debug lisp control-plane all     ! kurz
```

| Befehl | Das solltest du sehen |
|---|---|
| `show lisp site` auf dem MSMR | SITE1 und SITE2 registriert (yes) |
| `show ip lisp map-cache` auf xTR1 | 192.168.2.0/24 mit RLOC 10.0.2.1 |
| Ping H1 → H2 | nach dem ersten Verlust erfolgreich |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Welchen Port verwendet LISP für Control-Plane und Data-Plane?
<details><summary>Antwort</summary>

**Control Plane UDP 4342, Daten UDP 4341.**

</details>

2. Was bedeutet ein Negative Map-Cache-Eintrag?
<details><summary>Antwort</summary>

**Für dieses Ziel gibt es kein Mapping.** Das Mapping-System hat geantwortet, dass zu dem Präfix kein EID-zu-RLOC-Eintrag existiert. Der ITR merkt sich das samt Aktion, z. B. Weiterleiten über einen PITR oder Verwerfen, und fragt nicht sofort erneut.

</details>

3. Wozu dient ein PITR?
<details><summary>Antwort</summary>

**Er verbindet Nicht-LISP-Netze mit LISP-Sites.** Der PITR nimmt Verkehr aus dem Internet an und kapselt ihn zur LISP-Site. Die Gegenrichtung übernimmt der PETR: Er entkapselt Verkehr aus der LISP-Site zu Zielen ohne LISP.

</details>

## Prüfungsbezug
- EID = Adresse des Endgeräts, RLOC = Adresse des Routers im Underlay.
- Map-Request/Map-Reply für Anfragen, Map-Register/Map-Notify für Registrierungen.
- LISP-Daten UDP 4341, Control Plane UDP 4342.
- Der ITR verpackt, der ETR packt aus, ein xTR macht beides.
- SD-Access nutzt LISP als Control Plane.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
