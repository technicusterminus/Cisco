# Lab C5 – DMVPN Phase 3 mit IKEv2 und BGP mit dynamischen Nachbarn

**Plattform:** EVE-NG · **Dauer:** 120 min · **Niveau:** schwer

Ein Hub und zwei Spokes bauen über einen Internet-Router ein DMVPN auf, diesmal geschützt mit IPsec und IKEv2. Das Routing läuft über iBGP: Der Hub nimmt Spokes über einen Listen-Range ohne einzelne Nachbar-Einträge an und gibt ihnen nur eine Zusammenfassung. Die direkten Wege zwischen den Spokes entstehen per NHRP-Redirect und -Shortcut, jeweils mit eigener IPsec-Verbindung.

**Lernziele:** Nach diesem Lab kannst du …

- IKEv2 mit Proposal, Policy, Keyring und Profil aufbauen und an ein DMVPN-Tunnelinterface binden.
- Die Reihenfolge IKEv2, IPsec, NHRP verstehen und Fehler in der richtigen Schicht suchen.
- BGP mit `bgp listen range` und Peer-Group betreiben und erklären, warum hier kein Route Reflector nötig ist.
- Phase 3 mit Summary, Redirect und Shortcut nachweisen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::1.5.e` | BGP: Konvergenz und Skalierung | 6 |
| `Ziel::3.1.b` | IPsec und IKE | 5 |
| `Ziel::3.1.c` | DMVPN | 9 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| HUB | Cisco vIOS Router |  | 512 |
| INET | Cisco vIOS Router |  | 512 |
| S1 | Cisco vIOS Router |  | 512 |
| S2 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.0 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| HUB | Gi0/0 | INET | Gi0/0 |
| S1 | Gi0/0 | INET | Gi0/1 |
| S2 | Gi0/0 | INET | Gi0/2 |

## Topologie

```
                 HUB   Lo1 10.10.100.1/24, Tunnel0 172.16.0.1
                  | Gi0/0  198.51.100.1
                  |
                  | Gi0/0  198.51.100.2
                 INET  (Internet, nur Underlay)
         Gi0/1  /      \  Gi0/2
       .6      /        \      .10
       .5     /          \     .9
         Gi0/0            Gi0/0
        S1                    S2
   Lo1 10.10.1.1/24       Lo1 10.10.2.1/24
   Tunnel0 172.16.0.2     Tunnel0 172.16.0.3
```

| Link | Netz |
|---|---|
| HUB Gi0/0 – INET Gi0/0 | 198.51.100.0/30 (HUB .1, INET .2) |
| S1 Gi0/0 – INET Gi0/1 | 198.51.100.4/30 (S1 .5, INET .6) |
| S2 Gi0/0 – INET Gi0/2 | 198.51.100.8/30 (S2 .9, INET .10) |
| Tunnel0 (DMVPN) | 172.16.0.0/24 (HUB .1, S1 .2, S2 .3) |
| LANs (Loopback1) | HUB 10.10.100.0/24, S1 10.10.1.0/24, S2 10.10.2.0/24 |
| BGP | AS 65000 auf allen drei Routern (iBGP) |

Die Underlay-Adressen und Default-Routen Richtung INET sind vorgegeben, INET selbst braucht keine Routen. Alles, was durch den Tunnel geht, ist mit IPsec geschützt: Spoke-zu-Hub ab dem Start, Spoke-zu-Spoke, sobald NHRP den direkten Weg aufbaut. Pre-Shared Key, Proposal und Profilnamen sind auf allen Routern gleich.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Underlay prüfen.** Pinge vom HUB 198.51.100.5 und 198.51.100.9.
   - **Prüfen:** Beide Pings klappen.
   - **Denkfrage:** Welche Adressen und Routen muss ein Spoke kennen, bevor der Tunnel steht?
2. **IKEv2 und IPsec-Profil.** Auf HUB, S1 und S2 identisch: `crypto ikev2 proposal PROP` (`encryption aes-cbc-256`, `integrity sha256`, `group 14`), `crypto ikev2 policy POL` mit `proposal PROP`, `crypto ikev2 keyring KR` mit `peer ANY`, `address 0.0.0.0 0.0.0.0` und `pre-shared-key DMVPN-Lab-Key`, `crypto ikev2 profile IKEV2-DMVPN` mit `match identity remote address 0.0.0.0`, `authentication remote pre-share`, `authentication local pre-share` und `keyring local KR`. Dazu `crypto ipsec transform-set TS esp-aes 256 esp-sha256-hmac` mit `mode transport` und `crypto ipsec profile IPSEC-DMVPN` mit `set transform-set TS` und `set ikev2-profile IKEV2-DMVPN`.
   - **Prüfen:** `show crypto ikev2 proposal` und `show crypto ipsec profile` zeigen die Einträge auf allen drei Routern.
   - **Denkfrage:** Warum nimmt man bei DMVPN den Transport Mode?
3. **Hub-Tunnel.** Auf dem HUB `interface Tunnel0` mit 172.16.0.1/24, `tunnel source GigabitEthernet0/0`, `tunnel mode gre multipoint`, `ip nhrp network-id 1`, `ip nhrp map multicast dynamic`, `no ip redirects`, `ip mtu 1400`, `ip tcp adjust-mss 1360` und `tunnel protection ipsec profile IPSEC-DMVPN`.
   - **Prüfen:** `show interface Tunnel0` ist up/up.
   - **Denkfrage:** Warum braucht der Hub keine statische NHRP-Zuordnung zu den Spokes?
4. **Spokes anbinden.** Auf S1 und S2 derselbe Tunnel mit eigener Adresse (172.16.0.2 und .3), statt `map multicast dynamic` aber `ip nhrp nhs 172.16.0.1 nbma 198.51.100.1 multicast`.
   - **Prüfen:** `show crypto ikev2 sa` auf jedem Spoke zeigt eine SA zum Hub im Status READY. `show dmvpn` auf dem HUB listet beide Spokes im Zustand UP.
   - **Denkfrage:** In welcher Reihenfolge laufen IKEv2, IPsec und NHRP ab, wenn ein Spoke startet?
5. **BGP mit dynamischen Nachbarn.** HUB: `router bgp 65000` mit `neighbor SPOKES peer-group`, `neighbor SPOKES remote-as 65000`, `bgp listen range 172.16.0.0/24 peer-group SPOKES`, `network 10.10.100.0 mask 255.255.255.0` und `aggregate-address 10.10.0.0 255.255.0.0 summary-only`. Spokes: `router bgp 65000`, eigenes LAN per `network`, Nachbar 172.16.0.1 mit `remote-as 65000`.
   - **Prüfen:** `show ip bgp summary` auf dem HUB zeigt zwei dynamisch angelegte Nachbarn (mit `*` markiert). Jeder Spoke hat 10.10.0.0/16 über 172.16.0.1, aber keine Netze der anderen Spokes.
   - **Denkfrage:** Der Hub ist kein Route Reflector. Warum reicht das hier trotzdem?
6. **Phase 3.** HUB: `ip nhrp redirect` am Tunnel. S1 und S2: `ip nhrp shortcut`. Dann auf S1 zweimal `traceroute 10.10.2.1 source Loopback1`.
   - **Prüfen:** Der erste Traceroute geht über 172.16.0.1, der zweite direkt zu 172.16.0.3. `show ip route nhrp` auf S1 zeigt 10.10.2.0/24 über 172.16.0.3, `show crypto ikev2 sa` eine zusätzliche SA zu 198.51.100.9.
   - **Denkfrage:** Wozu die Zusammenfassung auf dem Hub, wenn NHRP die direkten Wege ohnehin selbst findet?
7. **Schutz prüfen.** Auf S1 `show crypto ipsec sa peer 198.51.100.9`, während Pings zwischen den Spoke-LANs laufen.
   - **Prüfen:** Die Zähler für verschlüsselte und entschlüsselte Pakete steigen.
   - **Denkfrage:** Was passiert mit dem direkten Weg, wenn eine Weile kein Verkehr zwischen S1 und S2 fließt?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** **Nur die NBMA-Adresse des Hubs (198.51.100.1) und einen Weg dorthin**, hier die Default-Route. Die Tunnel- und NBMA-Adressen der anderen Spokes lernt er über NHRP, die LANs über BGP.
- **Zu 2:** **Weil GRE schon einen äußeren IP-Header mit den NBMA-Adressen mitbringt.** Der Transport Mode schützt das GRE-Paket, ohne einen zweiten äußeren IP-Header hinzuzufügen, und spart so 20 Byte pro Paket. Tunnel Mode funktioniert auch, kostet aber mehr Overhead.
- **Zu 3:** **Weil die Spokes sich selbst registrieren.** Jeder Spoke meldet dem Hub per NHRP Registration Request seine Tunnel- und NBMA-Adresse. `ip nhrp map multicast dynamic` nimmt die registrierten Spokes zusätzlich in die Liste für Multicast auf, etwa für die Hellos eines IGP.
- **Zu 4:** **Erst IKEv2 (IKE_SA_INIT, dann IKE_AUTH mit dem Pre-Shared Key), daraus die IPsec-SA, dann die NHRP-Registrierung durch den geschützten Tunnel.** Scheitert IKE, kommt keine Registrierung an. Deshalb zuerst `show crypto ikev2 sa`, dann `show crypto ipsec sa`, dann `show dmvpn`.
- **Zu 5:** **Weil der Hub die Routen der Spokes gar nicht weitergeben muss.** Er fasst alles zu 10.10.0.0/16 zusammen, und dieses Aggregat erzeugt er selbst. Selbst erzeugte Routen gibt ein iBGP-Router an alle iBGP-Nachbarn weiter. Nur wenn die Spokes die spezifischen Netze der anderen Spokes bräuchten, müsste der Hub sie als Route Reflector spiegeln.
- **Zu 6:** **Damit die Spokes klein bleiben.** Jeder Spoke braucht nur 10.10.0.0/16 Richtung Hub. Die direkten Wege legt NHRP bei Bedarf als spezifischere Route an (`H` in der Routing-Tabelle), und sie verfallen wieder. Ohne Summary müsste jeder Spoke alle Spoke-Netze kennen, bei hunderten Standorten eine große BGP-Tabelle.
- **Zu 7:** **Er verfällt.** Der NHRP-Eintrag und die Shortcut-Route laufen nach der NHRP-Haltezeit ab (`ip nhrp holdtime`), mit ihnen verschwindet auch die direkte IPsec-Verbindung. Das nächste Paket geht wieder zuerst über den Hub, bis Redirect und Shortcut den direkten Weg neu aufbauen.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** S1 ist nicht im DMVPN: `show dmvpn` auf S1 zeigt den Hub nicht im Zustand UP. Das Underlay ist in Ordnung.

**Ticket 2:** S2 taucht in `show dmvpn` auf dem Hub nicht auf. `ping 198.51.100.1 source GigabitEthernet0/0` von S2 klappt.

**Ticket 3:** Die Tunnel stehen und beide Spokes sind registriert, aber keiner hat eine BGP-Sitzung zum Hub. Die Spokes kennen 10.10.0.0/16 nicht.

**Ticket 4:** Verkehr zwischen den Spokes läuft dauerhaft über den Hub: `traceroute 10.10.2.1 source Loopback1` von S1 zeigt auch beim dritten Versuch 172.16.0.1 als ersten Hop.

**Ticket 5:** Von S2 zu S1 entsteht nach dem ersten Paket ein direkter Weg, von S1 zu S2 bleibt der Verkehr beim Hub.

## Verifikation
```
show crypto ikev2 sa
show crypto ipsec sa
show dmvpn
show ip nhrp
show ip bgp summary
show ip route nhrp
traceroute 10.10.2.1 source Loopback1   ! auf S1, zweimal
```

| Befehl | Das solltest du sehen |
|---|---|
| `show dmvpn` auf dem HUB | zwei Spokes im Zustand UP |
| `show crypto ikev2 sa` auf S1 | SA zum Hub im Status READY, nach Spoke-Verkehr auch zu 198.51.100.9 |
| `show ip bgp summary` auf dem HUB | zwei dynamische Nachbarn (mit `*`) mit je einem Präfix |
| `show ip route nhrp` auf S1 | 10.10.2.0/24 über 172.16.0.3 nach dem ersten Traceroute |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Warum stört ein fehlendes `ip nhrp map multicast dynamic` auf dem Hub in diesem Lab nicht, mit OSPF oder EIGRP über DMVPN aber schon?
<details><summary>Antwort</summary>

**BGP läuft per Unicast über TCP.** OSPF und EIGRP schicken ihre Hellos an Multicast-Adressen. Ohne Multicast-Zuordnung erreichen die Hellos des Hubs die Spokes nicht, und es entsteht keine Nachbarschaft.

</details>

2. Welche Rolle spielt `ip nhrp network-id`, und muss sie auf allen Routern gleich sein?
<details><summary>Antwort</summary>

**Sie ist nur lokal bedeutsam.** Sie ordnet ein Tunnel-Interface einer NHRP-Instanz zu. Unterschiedliche Werte auf Hub und Spokes stören nicht; gleiche Werte auf zwei Tunneln desselben Routers würden sie zu einem NHRP-Netz zusammenführen.

</details>

3. Wie begrenzt du das Risiko, wenn der Hub BGP-Sitzungen aus einem ganzen Bereich annimmt?
<details><summary>Antwort</summary>

**Mit einem engen Bereich, einem Passwort für die Peer-Group und `bgp listen limit`.** Der Hub nimmt jede Verbindung aus dem Bereich an. `bgp listen limit` begrenzt die Zahl der dynamischen Nachbarn (Standard 100), ein Passwort hält fremde Geräte fern, die zufällig eine Tunneladresse haben.

</details>

4. Was ändert sich am Spoke, wenn ein zweiter Hub dazukommt (Dual Hub, Single Cloud)?
<details><summary>Antwort</summary>

**Der Spoke registriert sich bei beiden Hubs und hat zu beiden eine BGP-Sitzung.** Er trägt zwei `ip nhrp nhs`-Zeilen. Welcher Hub bevorzugt wird, steuerst du per BGP, etwa über Local Preference oder ein kürzeres Aggregat vom primären Hub.

</details>

## Prüfungsbezug
- DMVPN Phase 3: Hub mit `ip nhrp redirect`, Spokes mit `ip nhrp shortcut`; der Hub darf zusammenfassen.
- Schutz mit IKEv2: Proposal, Policy, Keyring, Profil, Transform-Set (Transport Mode), IPsec-Profil, `tunnel protection`.
- Fehlersuche von unten: Underlay-Ping, `show crypto ikev2 sa`, `show crypto ipsec sa`, `show dmvpn`, Routing, `show ip route nhrp`.
- BGP über DMVPN: `bgp listen range` mit Peer-Group, die Sitzung geht immer vom Spoke aus.

## Hinweis zum Image

IOSv verschlüsselt in Software, für Pings und Traceroutes reicht das. `ip nhrp nhs … nbma … multicast` und `keyring local` brauchen IOS 15.2 oder neuer. Die Meldungen von `debug crypto ikev2` unterscheiden sich je nach Version im Wortlaut.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-Konfiguration)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
