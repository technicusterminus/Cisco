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
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Lines einrichten.** Setze an der Konsole `logging synchronous` und `exec-timeout 5 0`. Erlaube an `line vty 0 4` vorerst `transport input telnet`, SSH kommt in Schritt 6.
   - **Denkfrage:** Was bewirkt `privilege level 15` an einer Line? Und warum ist ein reines Line-Passwort mit `login` ohne Benutzernamen ein Problem bei einem Audit?
2. **Lokale Benutzer.** Lege `username admin privilege 15 algorithm-type scrypt secret …` und `username helpdesk privilege 5 algorithm-type scrypt secret …` an.
   - **Prüfen:** `show running-config | include username` zeigt bei beiden ein `secret 9`.
   - **Denkfrage:** Was unterscheidet die Passworttypen 0, 5, 7, 8 und 9? Warum ist Typ 7 kein echter Schutz?
3. **AAA einschalten.** Setze `aaa new-model` und `aaa authentication login default local`. Halte vorher eine zweite Sitzung offen.
   - **Prüfen:** Eine neue Anmeldung per Telnet von R2 fragt jetzt nach Benutzername und Passwort.
   - **Denkfrage:** Warum sollst du beim Einschalten von AAA eine zweite Sitzung offen halten?
4. **TACACS+ mit Fallback.** Lege `tacacs server TAC1` an (Adresse 10.0.12.99, Schlüssel, `timeout 2`) und die Gruppe `aaa group server tacacs+ TACGRP`. Die Methodenliste `aaa authentication login VTY_LIST group TACGRP local` bindest du mit `login authentication VTY_LIST` an die vty-Lines. Den Server gibt es nicht, das ist Absicht.
   - **Prüfen:** Melde dich von R2 an. Die Anmeldung dauert ein paar Sekunden, dann klappt sie mit dem lokalen Benutzer.
   - **Denkfrage:** Warum klappt die Anmeldung trotz fehlendem Server? Und warum ist `none` am Ende einer Methodenliste gefährlich?
5. **Autorisierung und Accounting.** Setze `aaa authorization exec VTY_LIST group TACGRP local` und an den vty-Lines `authorization exec VTY_LIST`. Dazu `aaa accounting exec default start-stop group TACGRP`.
   - **Prüfen:** `admin` landet nach der Anmeldung direkt in `R1#`, `helpdesk` in `R1>`.
   - **Denkfrage:** Was passiert ohne die Exec-Autorisierung? Wann lohnt sich Befehlsautorisierung per TACACS+ statt Privilege Levels?
6. **Härten.** Setze `login block-for 60 attempts 3 within 30`, `login on-failure log`, einen `ip domain-name`, erzeuge einen RSA-Schlüssel mit 2048 Bit, setze `ip ssh version 2` und `transport input ssh`. Ergänze ein `banner login`.
   - **Prüfen:** Nach drei falschen Anmeldungen zeigt `show login failures` die Versuche, und `show login` meldet die Sperre. SSH von R2 auf R1 klappt, Telnet nicht mehr.
7. **TACACS+ und RADIUS vergleichen.** Fülle für beide aus: Transport, was verschlüsselt wird, ob die drei A getrennt sind, typischer Einsatz.
8. **Privilege Levels.** Gib Level 5 zusätzlich `show ip interface brief` und `ping`: `privilege exec level 5 show ip interface brief` und `privilege exec level 5 ping`.
   - **Prüfen:** Als `helpdesk` funktionieren diese beiden Befehle, `configure terminal` nicht.
   - **Denkfrage:** Was wäre die modernere Alternative zu Privilege Levels?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Mit `privilege level 15` landet jeder, der sich an dieser Line anmeldet, sofort im privilegierten Modus. Bei einem Line-Passwort ohne Benutzername teilen sich alle dasselbe Passwort. Im Log steht dann nicht, wer etwas geändert hat.
- **Zu 2:** Typ 0 ist Klartext. Typ 7 ist nur verschleiert und lässt sich in Sekunden zurückrechnen. Typ 5 ist ein MD5-Hash, heute zu schwach. Typ 8 (PBKDF2 mit SHA-256) und Typ 9 (scrypt) sind die sicheren Varianten.
- **Zu 3:** Mit `aaa new-model` gelten sofort neue Regeln für alle Lines. Ist die Methodenliste falsch, kommst du nicht mehr hinein. Die offene Sitzung ist deine Rettung.
- **Zu 4:** Der Server antwortet nicht, also nimmt der Router nach dem Timeout die nächste Methode, `local`. Würde der Server antworten und ablehnen, gäbe es kein Fallback. `none` am Ende lässt jeden ohne Prüfung hinein, sobald die anderen Methoden nicht antworten.
- **Zu 5:** Ohne Exec-Autorisierung übernimmt der Router das Privileg des Benutzers nicht. Alle landen in `R1>` mit Level 1. Befehlsautorisierung per TACACS+ lohnt sich, wenn viele Admins mit unterschiedlichen Rechten arbeiten. Jeder Befehl wird zentral geprüft und protokolliert.
- **Zu 7:** TACACS+: TCP 49, verschlüsselt das ganze Paket, trennt Authentisierung, Autorisierung und Accounting, typisch für die Verwaltung von Geräten. RADIUS: UDP 1812/1813, verschlüsselt nur das Passwort, fasst Authentisierung und Autorisierung zusammen, typisch für den Netzzugang (802.1X, VPN, WLAN).
- **Zu 8:** Rollenbasierte CLI-Views (`parser view`) oder Befehlsautorisierung über TACACS+. Beide sind feiner und übersichtlicher als nummerierte Level.

</details>

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
telnet 10.0.12.1               ! von R2 aus (vor Schritt 6)
```

| Test | Das solltest du sehen |
|---|---|
| Anmeldung als `admin` von R2 | nach kurzer Wartezeit `R1#` (Fallback auf lokal) |
| Anmeldung als `helpdesk` | `R1>`, nur die freigegebenen Befehle |
| `show aaa servers` | TAC1 mit Status DEAD bzw. ohne Antworten |

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
- `aaa new-model` schaltet AAA ein. Methodenlisten werden der Reihe nach probiert.
- Die nächste Methode greift nur, wenn der Server nicht antwortet, nicht wenn er ablehnt.
- TACACS+: TCP 49. RADIUS: UDP 1812/1813.
- Authentisierung, Autorisierung und Accounting sind drei getrennte Schritte.
- Passworttypen: 5 = MD5, 7 = umkehrbar, 8 = PBKDF2-SHA-256, 9 = scrypt.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
