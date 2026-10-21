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

1. **Underlay prüfen.** xTR1 → `ping 10.0.2.1 source 10.0.1.1` und `ping 10.0.99.1` müssen gehen. H1 → H2 geht noch nicht: Warum nicht (EIDs im Core unbekannt)?
2. **Map-Server/Map-Resolver.** Auf dem MSMR: `router lisp`, `site SITE1/SITE2` mit `authentication-key`, `eid-prefix`; `ipv4 map-server`, `ipv4 map-resolver`. Welche Aufgaben haben Map-Server (nimmt Registrierungen an) und Map-Resolver (beantwortet Anfragen)?
3. **xTR-Konfiguration.** `locator-set` mit dem RLOC, `eid-table default instance-id 0` mit `database-mapping <EID-Netz> locator-set …`, `ipv4 itr map-resolver`, `ipv4 etr map-server … key …`, `ipv4 itr`, `ipv4 etr`. Was ist ITR, was ETR, was PITR/PETR?
4. **Registrierung prüfen.** Auf dem MSMR `show ip lisp site` (registriert: `yes`), `show lisp site detail`. Auf den xTRs `show ip lisp database`.
5. **Datenverkehr.** H1 pingt H2: Der erste Ping scheitert oft (Map-Request/Reply nötig), danach läuft er. Prüfe `show ip lisp map-cache` auf xTR1: Eintrag 192.168.2.0/24 mit RLOC 10.0.2.1. Beschreibe den Ablauf: Map-Request → Map-Reply, Encapsulation (LISP-UDP 4341/4342), Decapsulation.
6. **Negative Map-Replies.** Pinge von H1 eine nicht existierende EID (z. B. 192.168.99.1). Was zeigt der Map-Cache (Negative Cache Entry), warum ist das effizient?
7. **Anwendungsbezug.** Erkläre den Zusammenhang mit SD-Access (Control Plane = LISP Map-Server, Fabric Edge = xTR, Border = PxTR) und mit Host-Mobilität.

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** SITE2 wird auf dem MSMR nie als registriert angezeigt, H1 erreicht H2 nicht (Map-Reply negativ).

**Ticket 2:** xTR1 registriert sein EID-Netz nicht beim MSMR (SITE1 `no`), Rückverkehr von H2 funktioniert nicht.

**Ticket 3:** Der MSMR zeigt SITE2 nicht registriert, im Log `EID-prefix not configured`.

**Ticket 4:** H1 erreicht H2 nie, `show ip lisp map-cache` ist leer (keine Map-Requests).

## Verifikation

```
show ip lisp site                ! auf MSMR
show ip lisp                      ! auf xTR
show ip lisp database
show ip lisp map-cache
show ip lisp forwarding eid remote
debug lisp control-plane all      ! kurz
```
Erwartet: Beide Sites registriert, `map-cache` auf xTR1 mit 192.168.2.0/24, Ping H1 ↔ H2 nach dem ersten Verlust erfolgreich.

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

LISP: EID = Endpunktadresse, RLOC = Router-Locator im Underlay. Map-Request/Map-Reply vs. Map-Register/Map-Notify. LISP-Daten UDP 4341, Control UDP 4342. ITR kapselt, ETR entkapselt, xTR = beides. SD-Access nutzt LISP als Control Plane (Host Tracking Database).

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
