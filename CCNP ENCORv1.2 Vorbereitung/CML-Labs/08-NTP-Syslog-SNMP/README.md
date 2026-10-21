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

1. **Uhr und Zeitzone.** Setze auf R1 `clock set`, `clock timezone CET 1`, `clock summer-time CEST recurring last Sun Mar 2:00 last Sun Oct 3:00`. Warum ist korrekte Zeit für Syslog, Zertifikate (IPsec/PKI) und Forensik wichtig?
2. **NTP-Master.** R1 wird mit `ntp master 3` zur Zeitquelle (Stratum 3). Wann ist `ntp master` sinnvoll, wann gefährlich (Mehrfachquellen, Zeitsprünge)? Wie unterscheidet sich ein **Server** von einem **Peer** (symmetrisch)?
3. **Hierarchie.** R2 `ntp server 10.0.12.1`, R3 `ntp server 10.0.23.1`. Beobachte Stratum, Reach, Delay, Offset und Jitter in `show ntp associations detail`. Erwarteter Stratum von R2 und R3?
4. **Authentifizierung.** Überall `ntp authenticate`, `ntp authentication-key 1 md5 NtpKey123`, `ntp trusted-key 1`; Clients mit `ntp server … key 1`. Teste einen falschen Key. Warum schützt das vor Zeitspoofing, und welche Alternative (NTPv4 mit SHA/CMAC, NTS) gibt es?
5. **Quell-Interface.** Setze `ntp source Loopback0` auf R2, R3. Warum stabilere Absender-Adresse?
6. **Syslog.** Aktiviere `logging buffered 16384 informational`, `logging source-interface Loopback0`, `logging host` (Ziel ist 10.0.23.99, nur zur Vorbereitung). Wie ist `%FACILITY-SEVERITY-MNEMONIC` aufgebaut? Welche Level gibt es (0 emergencies … 7 debugging) und welches ist `%LINK-3-UPDOWN`?
7. **SNMPv3.** Gruppe `MON` mit `priv`, Benutzer `monitor` mit `auth sha` und `priv aes 128`, View nur für `iso`. Prüfe `show snmp user` und `show snmp group`. Vergleiche v1/v2c (Community, Klartext) mit v3 (USM + VACM).
8. **Timestamps.** Setze `service timestamps log datetime msec localtime show-timezone year`. Warum ist `service timestamps debug` getrennt?
9. **PTP (Konzept).** Beschreibe Aufgaben von Grandmaster, Boundary Clock, Transparent Clock, Sync/Follow_Up/Delay_Req. Warum erreicht PTP Nanosekunden, NTP nur Millisekunden (Hardware-Timestamping)?

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
Erwartet: `Clock is synchronized, stratum 4` auf R2, `stratum 5` auf R3, Assoziation mit `*` (Sys.Peer) und `~`.

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

Stratum steigt pro Hop um 1. NTP nutzt UDP 123, Authentifizierung per MD5/SHA über Key-ID. `ntp master` kann die eigene Uhr als Quelle ausgeben. Syslog: UDP 514, Severity 0–7. SNMPv3 hat Sicherheitsstufen noAuthNoPriv, authNoPriv, authPriv. PTP (IEEE 1588): Grandmaster, Best Master Clock Algorithm, Hardware-Timestamps.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
