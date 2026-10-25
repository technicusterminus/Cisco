# Lab E1 – DMVPN Phase 3 mit EIGRP

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** schwer

Ein Hub und zwei Spokes bauen über einen simulierten Internet-Router ein DMVPN auf: mGRE, NHRP-Registrierung, EIGRP über den Tunnel und Phase 3 mit NHRP-Redirect und Shortcut. Du siehst, wie aus einer Summary-Route über den Hub eine direkte Spoke-to-Spoke-Verbindung wird.

**Lernziele:** Nach diesem Lab kannst du …

- Einen mGRE-Tunnel mit NHRP auf Hub und Spokes aufbauen und die Registrierung mit `show dmvpn` prüfen.
- EIGRP über das DMVPN betreiben und erklären, warum der Hub in Phase 3 eine Summary-Route sendet.
- Mit `show ip route nhrp` und `traceroute` nachweisen, dass ein Spoke-to-Spoke-Shortcut entstanden ist.
- Typische Fehler (Tunnel Key, NBMA-Adresse, Redirect, Shortcut, Summary) an ihrem Symptom erkennen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::2.3` | DMVPN: Fehlersuche | 16 |
| `Ziel::2.3.a` | DMVPN: GRE und mGRE | 5 |
| `Ziel::2.3.b` | DMVPN: NHRP | 8 |
| `Ziel::2.3.d` | DMVPN: Dynamische Nachbarn | 6 |
| `Ziel::2.3.e` | DMVPN: Spoke-to-Spoke | 6 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| HUB | Cisco vIOS Router |  | 512 |
| ISP | Cisco vIOS Router |  | 512 |
| S1 | Cisco vIOS Router |  | 512 |
| S2 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.0 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| HUB | Gi0/0 | ISP | Gi0/0 |
| S1 | Gi0/0 | ISP | Gi0/1 |
| S2 | Gi0/0 | ISP | Gi0/2 |

## Topologie

```
              Internet (ISP)
        ┌────────────┼────────────┐
   Gi0/0│       Gi0/1│       Gi0/2│
      HUB           S1           S2
   Lo1 10.10.0.1  Lo1 10.10.1.1  Lo1 10.10.2.1
        └──── Tunnel0 172.16.0.0/24 (mGRE) ────┘
```

| Link | Netz |
|---|---|
| HUB Gi0/0 – ISP Gi0/0 | 198.51.100.0/30 (HUB .1, ISP .2) |
| S1 Gi0/0 – ISP Gi0/1 | 198.51.100.4/30 (S1 .5, ISP .6) |
| S2 Gi0/0 – ISP Gi0/2 | 198.51.100.8/30 (S2 .9, ISP .10) |
| Tunnel0 (Overlay) | 172.16.0.0/24 (HUB .1, S1 .2, S2 .3) |
| LANs (Loopback1) | 10.10.0.0/24 (HUB), 10.10.1.0/24 (S1), 10.10.2.0/24 (S2) |

Der ISP-Router kennt nur seine drei /30-Netze (das „Internet“ kennt keine privaten Adressen). HUB und Spokes haben Default-Routen zum ISP und erreichen sich so über die NBMA-Adressen (198.51.100.x). Die LANs sind Loopback1-Interfaces; du testest mit `ping … source Loopback1`. Verschlüsselung (IPsec) ist hier bewusst weggelassen, damit die NHRP-Logik im Vordergrund steht.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Underlay prüfen.** Die Interfaces und Default-Routen sind gesetzt. Pinge vom HUB die NBMA-Adressen der Spokes (198.51.100.5 und .9) und von S1 die von S2.
   - **Prüfen:** Alle Pings gehen durch. Ohne funktionierendes Underlay gibt es kein DMVPN.
2. **Hub-Tunnel bauen.** Auf dem HUB: `interface Tunnel0` mit `ip address 172.16.0.1 255.255.255.0`, `tunnel source GigabitEthernet0/0`, `tunnel mode gre multipoint` und `tunnel key 100`. Dazu `ip nhrp network-id 100`, `ip nhrp authentication DMVPN` und `ip nhrp map multicast dynamic`.
   - **Prüfen:** `show interfaces Tunnel0` meldet up/up, `show dmvpn` zeigt noch keine Spokes.
   - **Denkfrage:** Wozu dient `map multicast dynamic`, und was würde ohne diese Zeile mit EIGRP passieren?
3. **Spokes anbinden.** Auf S1 und S2: derselbe Tunnel mit eigener Tunnel-IP (172.16.0.2 und .3), `tunnel mode gre multipoint`, `tunnel key 100`, gleiche NHRP-ID und Authentication. Statt `map multicast dynamic` trägst du den Hub ein: `ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast`.
   - **Prüfen:** `show dmvpn` auf dem HUB listet zwei Spokes im Zustand UP, Attribut `D` (dynamisch). Auf den Spokes steht der Hub mit Attribut `S` (statisch).
   - **Denkfrage:** Welche Adresse ist die NBMA-Adresse und welche die Tunnel-Adresse? Warum braucht ein Spoke beide für den Hub?
4. **EIGRP über den Tunnel.** Auf allen drei Routern `router eigrp 100` mit `network 172.16.0.0 0.0.0.255`, dem jeweiligen LAN (Loopback1) und `no auto-summary`.
   - **Prüfen:** `show ip eigrp neighbors` auf dem HUB zeigt zwei Nachbarn. Auf S1 steht die Route 10.10.0.0/24, aber (wegen Split Horizon) noch nicht 10.10.2.0/24.
   - **Denkfrage:** Warum lernt S1 die LAN-Route von S2 nicht, und warum ist das in Phase 3 sogar gewollt?
5. **Phase 3 einschalten.** Auf dem HUB: `ip summary-address eigrp 100 10.10.0.0 255.255.0.0` am Tunnel und `ip nhrp redirect`. Auf den Spokes: `ip nhrp shortcut`. Pinge danach von S1 `ping 10.10.2.1 source Loopback1 repeat 10`.
   - **Prüfen:** Vorher: `show ip route 10.10.2.1` auf S1 zeigt die Summary über 172.16.0.1. Nach dem Ping: `show ip route nhrp` zeigt 10.10.2.0/24 über 172.16.0.3, und `traceroute 10.10.2.1 source Loopback1` geht direkt zu 172.16.0.3.
   - **Denkfrage:** Welche Rolle spielen Redirect (Hub) und Shortcut (Spoke), und wer schickt wem die Resolution Request?
6. **MTU und MSS.** Setze am Tunnel `ip mtu 1400` und `ip tcp adjust-mss 1360` auf allen drei Routern.
   - **Prüfen:** `show interfaces Tunnel0 | include MTU` zeigt 1400.
   - **Denkfrage:** Warum fragmentiert ein GRE-Tunnel ohne diese Werte große Pakete, und was kommt mit IPsec noch dazu?
7. **Schutz einordnen.** IPsec ist in diesem Lab nicht konfiguriert.
   - **Denkfrage:** Welche Zeile würdest du am Tunnel ergänzen (`tunnel protection ipsec profile …`), und welcher Zustand in `show dmvpn` zeigt, dass die IPsec-Phase hängt?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** Der Hub ist nicht vorab konfiguriert, wer sich registriert: Er lernt die Spokes dynamisch. Mit `map multicast dynamic` nimmt er jeden registrierten Spoke in die Multicast-Replikationsliste auf. Ohne die Zeile gehen EIGRP-Hellos (224.0.0.10) nicht zu den Spokes, es entstehen keine Nachbarschaften.
- **Zu 3:** Die **NBMA-Adresse** (198.51.100.1) ist die öffentliche Underlay-Adresse, an die das GRE-Paket gesendet wird. Die **Tunnel-Adresse** (172.16.0.1) ist die Overlay-Adresse. Der Spoke braucht beide, weil er nur so die Zuordnung Overlay → Underlay kennt (statische NHRP-Zuordnung zum Hub).
- **Zu 4:** EIGRP sendet auf dem Tunnel-Interface wegen Split Horizon keine Routen zurück, die es dort gelernt hat. Der Hub gibt S2s LAN also nicht an S1 weiter. In Phase 3 ist das egal und sogar gewollt, weil der Hub ohnehin eine Summary sendet und Details über NHRP nachgeladen werden.
- **Zu 5:** Der **Hub** bemerkt, dass ein Paket am selben Tunnel wieder hinausgeht, und schickt dem sendenden Spoke einen *NHRP Traffic Indication* (Redirect). Der **Spoke** mit `shortcut` fragt daraufhin per Resolution Request den NBMA-Eintrag des Ziel-Spokes ab (die Anfrage läuft über den Hub, die Antwort kommt direkt vom Ziel-Spoke) und installiert eine NHRP-Route (`H`) für das Zielnetz.
- **Zu 6:** GRE fügt 24 Byte hinzu (äußerer IP-Header 20 + GRE 4), mit Tunnel Key sind es 28. Ein 1500-Byte-Paket passt dann nicht mehr in 1500 Byte. `ip mtu 1400` und `adjust-mss 1360` halten TCP unter der Grenze. Mit IPsec kommen ESP-Header, IV und Padding hinzu, daher der Puffer.
- **Zu 7:** `tunnel protection ipsec profile <Name>` am Tunnel, mit ISAKMP-Profil und IPsec-Profil (Transform Set im *Transport Mode*). In `show dmvpn` steht der Peer im Zustand `IKE` oder `IPsec`, wenn die Verschlüsselung noch hängt, erst bei `UP` ist beides durch.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** S1 hat keinen EIGRP-Nachbarn zum Hub; der Tunnel ist up/up, aber `show dmvpn` auf dem Hub listet S1 nicht.

**Ticket 2:** S2 hat keinen EIGRP-Nachbarn zum Hub; `show dmvpn` auf S2 zeigt den Hub nicht als UP.

**Ticket 3:** Der Verkehr zwischen S1 und S2 läuft, geht aber immer über den Hub; `show ip route nhrp` ist auf beiden Spokes leer.

**Ticket 4:** Von S1 zu S2 geht der Verkehr direkt, in der Gegenrichtung aber immer noch über den Hub.

**Ticket 5:** S1 erreicht das LAN von S2 nicht; die Traceroute endet beim ISP.

## Verifikation
```
show dmvpn
show ip nhrp
show ip nhrp nhs detail           ! auf den Spokes
show ip eigrp neighbors
show ip route eigrp
show ip route nhrp                 ! Shortcut-Routen (H)
ping 10.10.2.1 source Loopback1 repeat 10    ! auf S1
traceroute 10.10.2.1 source Loopback1
show interfaces Tunnel0 | include Key|MTU
```

| Befehl | Das solltest du sehen |
|---|---|
| `show dmvpn` auf dem HUB | zwei Spokes im Zustand UP, Attribut `D` |
| `show dmvpn` auf einem Spoke | der Hub mit Attribut `S`; nach einem Ping zum anderen Spoke zusätzlich ein Eintrag mit `D` |
| `show ip route nhrp` auf S1 nach dem Ping | `H 10.10.2.0/24` über 172.16.0.3 |
| `traceroute` von S1 nach 10.10.2.1 | erster Versuch über 172.16.0.1, danach direkt über 172.16.0.3 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Was ändert sich zwischen Phase 2 und Phase 3?
<details><summary>Antwort</summary>

**In Phase 3 sendet der Hub eine Summary, und die Spokes bekommen den direkten Weg per NHRP-Redirect/Shortcut.** In Phase 2 muss der Hub die Spoke-Routen unverändert (mit Original-Next-Hop, `no ip next-hop-self eigrp`) weitergeben, die Spokes lernen alle Details und lösen den Next-Hop per NHRP-Resolution auf. Phase 3 skaliert besser, weil die Routing-Tabelle klein bleibt und Summarization möglich ist.

</details>

2. `show dmvpn` auf dem Spoke zeigt den Hub im Zustand `NHRP`. Wo suchst du?
<details><summary>Antwort</summary>

**Bei der NHRP-Registrierung und beim Underlay.** `NHRP` heißt: Der Eintrag existiert, aber die Registrierung wurde nicht bestätigt. Prüfe NBMA-Adresse, Tunnel Key, `network-id`, Authentication und ob das Underlay-GRE (IP-Protokoll 47) durchkommt.

</details>

3. Warum kann es zu Problemen kommen, wenn zwei Spokes hinter NAT sitzen?
<details><summary>Antwort</summary>

**Weil NAT die NBMA-Adresse verändert, die der Hub lernt.** DMVPN kommt damit klar, wenn nur ein Spoke hinter NAT sitzt und IPsec NAT-Traversal (UDP 4500) nutzt. Zwei Spokes hinter jeweils eigenem NAT können sich oft nicht direkt erreichen, dann bleibt der Verkehr über den Hub.

</details>

## Prüfungsbezug
- Phase 1: Hub-and-Spoke, p2p-GRE auf den Spokes. Phase 2: Spoke-to-Spoke, Hub ohne Summary. Phase 3: Redirect und Shortcut, Summary möglich.
- Hub: `ip nhrp map multicast dynamic`, `ip nhrp redirect`. Spoke: `ip nhrp nhs … nbma … multicast`, `ip nhrp shortcut`.
- Fehlersuche von unten: Underlay-Ping, GRE (Key, Source), NHRP (ID, Authentication, NBMA), IPsec, Routing.
- Zustände in `show dmvpn`: NHRP, IKE, IPsec, UP. Attribute: S statisch, D dynamisch, T1 Route installiert, T2 Next-Hop-Override (Shortcut).
- EIGRP über DMVPN: Split Horizon am Hub-Tunnel beachten, bei Phase 2 `no ip next-hop-self eigrp`.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
