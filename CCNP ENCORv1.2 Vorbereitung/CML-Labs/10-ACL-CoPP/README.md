# Lab 10 – ACLs und Control-Plane Policing

**Dauer:** 90 min · **Niveau:** mittel · **Nodes:** 1× unmanaged_switch, 5× iosv

Layer-3/4-Filter mit Standard-, Extended- und benannten ACLs, `established`, Logging und vty-Schutz, dazu CoPP (MQC auf der Control-Plane) zur Begrenzung von ICMP und Management-Verkehr.

**Lernziele:** Nach diesem Lab kannst du …

- Standard- und Extended-ACLs richtig aufbauen und platzieren.
- Die Richtung (in/out) einer ACL am Interface begründen.
- Control-Plane Policing einrichten und an den Zählern prüfen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::5.2.a` | ACLs | 52 |
| `Ziel::5.2.b` | CoPP | 21 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
 PC1 ─┐
      ├─ SW ── R1 (Gi0/0 inside) ──Gi0/1── ISP (Lo0 8.8.8.8)
 PC2 ─┘        └ Gi0/2 ─ SRV (DMZ)
```

| Gerät | Interface | Adresse |
|---|---|---|
| R1 | Gi0/0 / Gi0/1 / Gi0/2 | 192.168.10.1/24 / 203.0.113.1/30 / 172.16.0.1/24 |
| ISP | Gi0/0 / Lo0 | 203.0.113.2/30 / 8.8.8.8/32 |
| PC1/PC2 | – | 192.168.10.11/.12 |
| SRV | – | 172.16.0.10 (HTTP an) |

Alle Netze sind ohne NAT erreichbar (der ISP routet das Kundennetz statisch zurück). Die vty-Lines von R1 erlauben Telnet nur für dieses Lab, in Produktion immer SSH.

## Teil A – Bauen

1. **Ausgangslage.** Alles ist erreichbar: PC1 → SRV (HTTP), PC1 → 8.8.8.8, ISP → PC1.
2. **Standard-ACL für vty.** `ip access-list standard MGMT` (nur 192.168.10.0/24), `line vty 0 4` → `access-class MGMT in`. Teste Telnet von PC1 (erlaubt) und vom ISP (blockiert). Warum gehört `access-class` an die Line und nicht an ein Interface?
3. **Extended ACL inbound am Edge.** Auf Gi0/1 inbound nur erlauben: ICMP echo-reply, `established` TCP, TCP 80 zu SRV, UDP-DNS-Antworten (src 53). Am Ende explizit `deny ip any any log`. Wie wirkt die implizite Deny-Regel, wann ist ein explizites `deny … log` nützlich?
4. **Richtung und Ort.** Welche Wirkung hat dieselbe ACL `out` an Gi0/1? Welche Faustregel gilt für Standard- (nah am Ziel) und Extended-ACLs (nah an der Quelle)?
5. **DMZ-Regeln.** SRV (DMZ) darf nicht ins LAN initiieren (Gi0/2 inbound `deny ip 172.16.0.0 0.0.0.255 192.168.10.0 0.0.0.255`), LAN → DMZ nur TCP 80 und ICMP (Gi0/0 inbound).
6. **ACL-Reihenfolge & Zähler.** Verschiebe eine Zeile mit Sequenznummern (`ip access-list extended … / 15 permit …`). Lies `show access-lists`: Matches pro Zeile. Wie findest du Shadowed Rules?
7. **CoPP.** Baue `class-map` für ICMP (ACL), für Management (Telnet/SSH von LAN) und OSPF/BGP, `policy-map COPP` mit `police rate 64000 bps conform transmit exceed drop` für ICMP, anschließend `control-plane` → `service-policy input COPP`. Teste Pings vom ISP mit `repeat 500 size 1500` und beobachte `show policy-map control-plane`.
8. **Diskussion.** Warum CoPP nicht für Transitverkehr wirkt (nur Control Plane), und worin liegt der Unterschied zu CoPP-Alternativen (CPPr, Port-Filtering)?

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Seit der ACL am Edge funktioniert aus dem LAN nichts mehr (kein Ping nach 8.8.8.8, kein HTTP von außen), Zähler der ersten Zeile steigt.

**Ticket 2:** SRV kann trotz `deny` ins LAN pingen.

**Ticket 3:** `show policy-map control-plane` zeigt bei `CM-ICMP` null Treffer, Ping-Flut wird nicht begrenzt.

**Ticket 4:** Telnet von PC1 auf R1 wird sofort getrennt, obwohl PC1 im Management-Netz liegen soll.

## Verifikation

```
show access-lists
show ip interface Gi0/1 | include access list
show policy-map control-plane
show class-map
telnet 192.168.10.1                 ! von PC1 und vom ISP
```
Erwartet: ACL-Zähler steigen bei Tests, CoPP zeigt `conformed`/`exceeded`, Telnet vom ISP bricht ab.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Eine ACL hat als letzte Zeile `permit ip any any`, ganz oben aber `deny ip any any`. Was passiert?
<details><summary>Antwort</summary>

**Alles wird verworfen.** Eine ACL hört beim ersten Treffer auf. `deny ip any any` passt auf jedes Paket, die Zeilen darunter werden nie erreicht.

</details>

2. Wie unterscheidet sich `established` von einer zustandsbehafteten Firewall?
<details><summary>Antwort</summary>

**`established` prüft nur Flags im Paket, eine Firewall kennt die Verbindung.** Die ACL lässt jedes TCP-Paket mit gesetztem ACK oder RST durch, auch ein gefälschtes. Eine zustandsbehaftete Firewall merkt sich jede Verbindung und lässt nur echte Antworten zurück.

</details>

3. Warum verwirft CoPP den Transit-Ping nicht?
<details><summary>Antwort</summary>

**Weil CoPP nur Verkehr an den Router selbst prüft.** Ein Transit-Ping geht durch die Data Plane und erreicht die Control Plane nie.

</details>

## Prüfungsbezug

ACL werden von oben nach unten ausgewertet, die erste Übereinstimmung gewinnt, am Ende steht ein implizites `deny any`. Standard-ACLs filtern nur nach Quelle, Extended nach Protokoll/Ports. `established` prüft ACK/RST-Flags (kein Zustandsmodell). `access-class` für Lines, `ip access-group` für Interfaces. CoPP schützt nur den Control Plane (Verkehr zum Router), nicht den Transit.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
