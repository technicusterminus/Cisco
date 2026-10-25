# Lab 08 – NTP, Syslog und SNMPv3

**Dauer:** 75 min · **Niveau:** leicht bis mittel · **Nodes:** 3× iosv

Management-Plane-Grundlagen: authentifizierte NTP-Hierarchie (Stratum, Server/Peer), Syslog mit Severity und Quell-Interface, SNMPv3 mit authPriv. PTP wird konzeptionell behandelt (Hardwareunterstützung nötig).

**Lernziele:** Nach diesem Lab kannst du …

- NTP mit Authentisierung aufbauen und den Synchronisationszustand lesen.
- Syslog-Level gezielt einstellen.
- SNMPv3 mit authPriv einrichten.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.3.a` | NTP und PTP | 32 |
| `Ziel::4.1` | Diagnose, SNMP und Syslog | 40 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
 R1 (NTP Master, Stratum 3) ──── R2 (Client, Stratum 4) ──── R3 (Client, Stratum 5)
   10.0.12.0/30                       10.0.23.0/30
```

| Gerät | Lo0 | Links |
|---|---|---|
| R1 | 1.1.1.1/32 | Gi0/0 10.0.12.1/30 |
| R2 | 2.2.2.2/32 | Gi0/0 10.0.12.2/30, Gi0/1 10.0.23.1/30 |
| R3 | 3.3.3.3/32 | Gi0/0 10.0.23.2/30 |

Routing: statisch vorgegeben (jeder Router kennt alle Loopbacks). NTP-Synchronisation dauert einige Minuten, geduldig prüfen mit `show ntp associations`.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Uhr und Zeitzone.** Setze auf R1 die Uhr mit `clock set`, dazu `clock timezone CET 1` und `clock summer-time CEST recurring last Sun Mar 2:00 last Sun Oct 3:00`.
   - **Prüfen:** `show clock detail` zeigt Datum, Uhrzeit und Zeitzone.
   - **Denkfrage:** Warum ist eine korrekte Uhrzeit für Syslog, Zertifikate und Forensik so wichtig?
2. **NTP-Master.** Mache R1 mit `ntp master 3` zur Zeitquelle mit Stratum 3.
   - **Denkfrage:** Wann ist `ntp master` sinnvoll, wann gefährlich? Was ist der Unterschied zwischen `ntp server` und `ntp peer`?
3. **Hierarchie aufbauen.** R2 bekommt `ntp server 10.0.12.1`, R3 bekommt `ntp server 10.0.23.1`. Warte ein paar Minuten.
   - **Prüfen:** `show ntp associations detail` zeigt Stratum, Reach, Delay, Offset und Jitter. In der Liste trägt die gewählte Quelle ein `*`.
   - **Denkfrage:** Welches Stratum erwartest du auf R2 und R3?
4. **Authentisierung.** Setze auf allen Routern `ntp authenticate`, `ntp authentication-key 1 md5 NtpKey123` und `ntp trusted-key 1`. Die Clients bekommen `ntp server … key 1`. Teste danach einen falschen Schlüssel.
   - **Prüfen:** Mit falschem Schlüssel zeigt `show ntp associations detail` „authenticated: no“ bzw. keine Synchronisation mehr.
   - **Denkfrage:** Wogegen schützt die Authentisierung?
5. **Quell-Interface.** Setze auf R2 und R3 `ntp source Loopback0`.
   - **Denkfrage:** Warum ist eine Loopback als Absender stabiler?
6. **Syslog.** Aktiviere `logging buffered 16384 informational`, `logging source-interface Loopback0` und `logging host 10.0.23.99` (nur zur Übung, dort läuft kein Server).
   - **Prüfen:** Schalte ein Interface kurz aus und an. `show logging` zeigt die Meldungen.
   - **Denkfrage:** Wie ist eine Meldung wie `%LINK-3-UPDOWN` aufgebaut, und welches Level hat sie?
7. **SNMPv3.** Lege eine Gruppe `MON` mit Sicherheitsstufe `priv` an und einen Benutzer `monitor` mit `auth sha` und `priv aes 128`. Die View erlaubt nur `iso`.
   - **Prüfen:** `show snmp user` und `show snmp group` zeigen Benutzer und Gruppe.
   - **Denkfrage:** Was macht SNMPv3 anders als v1 und v2c?
8. **Zeitstempel.** Setze `service timestamps log datetime msec localtime show-timezone year`.
   - **Prüfen:** Neue Log-Meldungen tragen Datum, Millisekunden und Zeitzone.
   - **Denkfrage:** Warum gibt es für Debug-Meldungen eine eigene Einstellung?
9. **PTP verstehen.** Beschreibe ohne Konfiguration die Rollen Grandmaster, Boundary Clock und Transparent Clock sowie die Nachrichten Sync, Follow_Up und Delay_Req.
   - **Denkfrage:** Warum erreicht PTP Nanosekunden, NTP nur Millisekunden?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Nur mit gleicher Zeit lassen sich Meldungen verschiedener Geräte in die richtige Reihenfolge bringen. Zertifikate haben ein Gültigkeitsfenster. Geht die Uhr falsch, scheitern IPsec und HTTPS. Bei einem Vorfall brauchst du eine belastbare Zeitleiste.
- **Zu 2:** Sinnvoll ist `ntp master`, wenn es keine externe Zeitquelle gibt, etwa im Labor oder in einem isolierten Netz. Gefährlich wird es, wenn die Uhr falsch geht und alle anderen die falsche Zeit übernehmen. Bei `ntp server` holt sich der Router die Zeit nur. Bei `ntp peer` können sich beide gegenseitig synchronisieren.
- **Zu 3:** R2 Stratum 4, R3 Stratum 5. Jede Stufe zählt eins hoch.
- **Zu 4:** Der Client übernimmt nur Zeit von Servern, die den Schlüssel kennen. Ein Angreifer kann so keine falsche Zeit einschleusen. Neuere Verfahren nutzen SHA-basierte Schlüssel oder NTS.
- **Zu 5:** Eine Loopback ist immer up, unabhängig davon, welches physische Interface gerade funktioniert. Server und ACLs können sich auf eine feste Adresse verlassen.
- **Zu 6:** Aufbau: `%FACILITY-SEVERITY-MNEMONIC`. Bei `%LINK-3-UPDOWN` ist LINK die Quelle, 3 das Level (Error) und UPDOWN die Art der Meldung. Die Level reichen von 0 (Emergency) bis 7 (Debug).
- **Zu 7:** v1 und v2c senden die Community im Klartext. v3 hat Benutzer mit Anmeldung und Verschlüsselung (USM) und regelt per View, wer welche Daten sehen darf (VACM).
- **Zu 8:** Debug- und Log-Meldungen haben getrennte Einstellungen für Zeitstempel. Bei Debugs will man oft die Uptime oder Millisekunden sehen, unabhängig vom Log-Format.
- **Zu 9:** Die Grandmaster ist die beste Uhr im Netz, gewählt über den Best Master Clock Algorithm. Eine Boundary Clock synchronisiert sich auf einem Port und gibt die Zeit auf den anderen weiter. Eine Transparent Clock leitet nur weiter und trägt die Zeit ein, die das Paket bei ihr verbracht hat. Sync und Follow_Up liefern die Zeit der Master-Uhr, Delay_Req und Delay_Resp messen die Laufzeit. PTP stempelt die Pakete in der Hardware der Netzwerkkarte. NTP stempelt in Software, und die Verzögerung im Betriebssystem kostet Genauigkeit.

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Weder R2 noch R3 synchronisieren; `show ntp associations` zeigt auf R2 `~` und Stratum 16 (R1 selbst hat keine Quelle).

**Ticket 2:** R2 hat eine Assoziation mit R1, aber sie wird nie als Sys.Peer gewählt; `authenticated` steht auf `no`.

**Ticket 3:** R3 bleibt unsynchronisiert, `show ntp associations` zeigt Reach 0 zu 10.0.23.10.

**Ticket 4:** In `show logging` auf R2 fehlen Link-Up-Meldungen (`%LINEPROTO-5-UPDOWN`), obwohl der Link geflappt hat.

## Verifikation
```
show clock detail
show ntp status
show ntp associations detail
show logging
show snmp user
show snmp group
show running-config | include ntp|logging|snmp
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ntp status` auf R2 | „Clock is synchronized, stratum 4“ |
| `show ntp status` auf R3 | „Clock is synchronized, stratum 5“ |
| `show ntp associations` | `*` vor der gewählten Quelle, `~` vor jedem konfigurierten Server |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. R2 zeigt `Clock is unsynchronized`, obwohl `ntp server` gesetzt ist. Die ersten Prüfungen?
<details><summary>Antwort</summary>

**Zuerst `show ntp associations`.** Steht Reach auf 0, kommt keine Antwort: Erreichbarkeit und ACL für UDP 123 prüfen. Kommen Antworten, aber ohne Sync, sind Authentisierung (`trusted-key`, Key-ID, Passwort) oder Stratum 16 beim Server die üblichen Ursachen.

</details>

2. Was bedeutet Stratum 16?
<details><summary>Antwort</summary>

**Die Uhr ist nicht synchronisiert.** Ein Server mit Stratum 16 gilt als ungültige Zeitquelle. Kein Client übernimmt seine Zeit.

</details>

3. Wieso `authPriv` und nicht `authNoPriv`?
<details><summary>Antwort</summary>

**Weil authNoPriv nur Herkunft und Unverfälschtheit schützt, nicht den Inhalt.** authPriv verschlüsselt zusätzlich die Nutzdaten. Wer mitliest, sieht dann keine Werte mehr.

</details>

## Prüfungsbezug
- Das Stratum steigt pro Stufe um 1. Stratum 16 heißt: nicht synchronisiert.
- NTP nutzt UDP 123. Authentisierung per Schlüssel-ID, `trusted-key` nicht vergessen.
- `ntp master` gibt die eigene Uhr als Quelle aus.
- Syslog: UDP 514, Level 0 bis 7.
- SNMPv3: noAuthNoPriv, authNoPriv, authPriv.
- PTP (IEEE 1588): Grandmaster, Best Master Clock Algorithm, Zeitstempel in Hardware.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
