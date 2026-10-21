# Lab 11 – Gerätezugriff und AAA

**Dauer:** 75 min · **Niveau:** mittel · **Nodes:** 2× iosv

Lines, lokale Benutzer, Privilege Levels, Login-Härtung und AAA mit TACACS+ (Server absichtlich nicht erreichbar, damit du das Fallback-Verhalten siehst). Der „Admin-PC“ R2 meldet sich per Telnet am Gerät R1 an.

**Lernziele:** Nach diesem Lab kannst du …

- Den Gerätezugang mit lokalen Benutzern, SSH und Line-Einstellungen absichern.
- AAA mit Methodenlisten für Anmeldung und Exec-Autorisierung aufbauen.
- Erklären, wann ein Fallback auf `local` greift und wann nicht.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::5.1.a` | Lines und lokale Anmeldung | 27 |
| `Ziel::5.1.b` | AAA | 42 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
 R2 (Admin-PC)  10.0.12.2/30 ─────── 10.0.12.1/30  R1 (Device under Test)
                                                    TACACS+ 10.0.12.99 (nicht vorhanden)
```

| Gerät | Interface | Adresse |
|---|---|---|
| R1 | Gi0/0 / Lo0 | 10.0.12.1/30 / 1.1.1.1/32 |
| R2 | Gi0/0 / Lo0 | 10.0.12.2/30 / 2.2.2.2/32 |

Telnet wird für die Tests genutzt, weil sich vty-Verhalten damit am einfachsten prüfen lässt. SSH baust du in Aufgabe 6 zusätzlich auf (RSA-Schlüssel erzeugst du selbst, sie sind nicht Teil der Konfigurationsdatei).

## Teil A – Bauen

1. **Lines.** Console: `logging synchronous`, `exec-timeout 5 0`. vty 0 4: `transport input ssh` später, jetzt `telnet`. Was bewirkt `privilege level 15` an einer Line, und warum ist ein Passwort `login` auf vty ohne Benutzername ein Auditproblem?
2. **Lokale Benutzer.** `username admin privilege 15 algorithm-type scrypt secret …`, `username helpdesk privilege 5 …`. Vergleiche Typ 0/5/7/8/9 (Klartext, MD5, reversibel, PBKDF2-SHA256, scrypt). Warum ist Typ 7 kein Schutz?
3. **AAA-Modell.** `aaa new-model`, `aaa authentication login default local`. Was ändert sich für alle Lines durch `aaa new-model` (Gefahr des Aussperrens, deshalb zweite Session offen lassen)?
4. **TACACS+ mit Fallback.** Definiere `tacacs server TAC1` (10.0.12.99, key, timeout 2) und `aaa group server tacacs+ TACGRP`. Methodenliste `VTY_LIST`: `group TACGRP local`. Wende sie auf vty an (`login authentication VTY_LIST`). Melde dich von R2 an: Beobachte die Wartezeit und das Fallback auf lokale Benutzer. Wie unterscheidet sich eine Methodenliste mit `none` am Ende (gefährlich!) von `local`?
5. **Autorisierung und Accounting.** `aaa authorization exec VTY_LIST group TACGRP local` (Privilege vom Server/aus lokalem Benutzer), `aaa authorization commands 15 VTY_LIST group TACGRP local`, `aaa accounting exec default start-stop group TACGRP`. Was passiert ohne Exec-Authorization (Benutzer landet im User-EXEC, Privileg 1)? Wann nutzt man Command Authorization (TACACS+) statt Privilege Levels?
6. **Härtung.** `login block-for 60 attempts 3 within 30`, `login on-failure log`, `ip domain-name`, RSA 2048 erzeugen, `ip ssh version 2`, `transport input ssh`, `exec-timeout 5 0`, `banner login`. Prüfe `show login failures` nach drei Fehlversuchen.
7. **TACACS+ vs. RADIUS.** Vergleiche Transport (TCP 49 vs. UDP 1812/1813), Verschlüsselung (ganzes Paket vs. nur Passwort), Trennung von AAA (TACACS+ getrennt, RADIUS kombiniert), typische Einsätze (Gerätezugriff vs. 802.1X/VPN).
8. **Privilege Levels.** Gib `helpdesk` (Level 5) nur `show ip interface brief` und `ping`: `privilege exec level 5 show ip interface brief`. Vergleiche das mit Command Authorization und RBAC-Views (`parser view`).

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Solange TACACS+ nicht erreichbar ist (das ist hier immer der Fall), kann sich niemand per Telnet anmelden, auch `admin` nicht.

**Ticket 2:** Login per Telnet klappt, aber `admin` landet in `R1>` statt `R1#`.

**Ticket 3:** Telnet-Anmeldung schlägt für alle Benutzer fehl, im Log steht `no method list`.

**Ticket 4:** Audit-Befund: untätige vty-Sitzungen laufen nie ab.

## Verifikation

```
show aaa servers
show aaa method-lists authentication
show running-config | section aaa|line vty|username
show users
show login failures
telnet 10.0.12.1               ! von R2 aus
```
Erwartet: Anmeldung von R2 mit `admin` landet in `R1#` (Privileg 15), `helpdesk` in `R1>` mit eingeschränkten Befehlen; nach TACACS-Timeout greift lokal.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Warum landet ein lokaler Benutzer mit `privilege 15` trotzdem in `R1>`?
<details><summary>Antwort</summary>

**Weil die Exec-Autorisierung fehlt.** Mit `aaa new-model` übernimmt der Router das Privileg des Benutzers nur, wenn `aaa authorization exec …` gesetzt und an die Line gebunden ist. Sonst gilt das Standardprivileg der Line, also 1.

</details>

2. Der TACACS+-Server antwortet `reject`, der Benutzer existiert lokal. Greift das Fallback?
<details><summary>Antwort</summary>

**Nein.** Der Router geht nur zur nächsten Methode, wenn der Server nicht antwortet. Ein „reject“ ist eine gültige Antwort, und dabei bleibt es. Merke: Fallback nur bei Schweigen, nicht bei Nein.

</details>

3. Wann ist RADIUS die bessere Wahl?
<details><summary>Antwort</summary>

**Für den Netzzugang, also 802.1X, VPN und WLAN.** RADIUS transportiert EAP und Attribute wie VLAN oder dACL. Für die Administration von Geräten mit Autorisierung einzelner Befehle nimmt man meist TACACS+.

</details>

## Prüfungsbezug

`aaa new-model` aktiviert AAA, Methodenlisten werden der Reihe nach probiert, nur bei Nichterreichbarkeit (nicht bei Ablehnung) wird die nächste Methode genutzt. TACACS+ TCP 49, RADIUS UDP 1812/1813. Authentication ≠ Authorization ≠ Accounting. Passwort-Typen: 5 = MD5, 7 = reversibel, 8 = PBKDF2-SHA256, 9 = scrypt.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
