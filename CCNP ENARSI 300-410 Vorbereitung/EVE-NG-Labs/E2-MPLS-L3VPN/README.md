# Lab E2 – MPLS L3VPN mit LDP und MP-BGP

**Plattform:** EVE-NG · **Dauer:** 100 min · **Niveau:** schwer

Ein kleines Provider-Netz (PE1, P, PE2) verbindet zwei Standorte eines Kunden per MPLS L3VPN: OSPF und LDP im Core, VRF mit Route Distinguisher und Route Targets auf den PEs, eBGP zu den Kunden-Routern (CE) und VPNv4 zwischen den PEs. Dazu die typische Fehlersuche, wenn die BGP-Sitzung steht, aber kein Verkehr fließt.

**Lernziele:** Nach diesem Lab kannst du …

- Core-Underlay mit OSPF und LDP aufbauen und Label-Bindings prüfen.
- Eine VRF mit RD und Route Targets anlegen und PE-CE-Routing per eBGP in der VRF betreiben.
- VPNv4 zwischen den PEs konfigurieren und erklären, was RD und RT jeweils tun.
- Mit `show mpls ldp neighbor`, `show vrf detail` und `show bgp vpnv4 unicast all` die Ebene eines Fehlers eingrenzen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::2.1` | MPLS: Fehlersuche | 23 |
| `Ziel::2.2` | MPLS L3VPN: Fehlersuche | 19 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| CE1 | Cisco vIOS Router |  | 512 |
| PE1 | Cisco vIOS Router |  | 512 |
| P | Cisco vIOS Router |  | 512 |
| PE2 | Cisco vIOS Router |  | 512 |
| CE2 | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.6 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| CE1 | Gi0/0 | PE1 | Gi0/1 |
| PE1 | Gi0/0 | P | Gi0/0 |
| P | Gi0/1 | PE2 | Gi0/0 |
| PE2 | Gi0/1 | CE2 | Gi0/0 |

## Topologie

```
 CE1 ─── PE1 ─────── P ─────── PE2 ─── CE2
 AS65001  \_______ AS 65000 _______/  AS65002
  Lo1 10.100.1.1/24                Lo1 10.100.2.1/24
```

| Link | Netz |
|---|---|
| CE1 Gi0/0 – PE1 Gi0/1 | 192.168.1.0/30 (PE1 .1, CE1 .2), in der VRF CUST-A |
| PE1 Gi0/0 – P Gi0/0 | 10.0.12.0/30 (.1/.2) |
| P Gi0/1 – PE2 Gi0/0 | 10.0.23.0/30 (.1/.2) |
| PE2 Gi0/1 – CE2 Gi0/0 | 192.168.2.0/30 (PE2 .1, CE2 .2), in der VRF CUST-A |
| Loopback0 | PE1 10.255.0.1/32, P 10.255.0.2/32, PE2 10.255.0.3/32 |
| Kunden-LANs (Loopback1) | CE1 10.100.1.0/24, CE2 10.100.2.0/24 |

Der Provider ist AS 65000, die Kunden-Router CE1 und CE2 sind AS 65001 und 65002. Die Interfaces zu den CEs stehen in der Ausgangslage **ohne IP-Adresse**: Erst kommt `vrf forwarding`, dann die Adresse, sonst löscht IOS die Adresse wieder. Der P-Router führt nur Core-Routen und Labels, kein BGP und keine VRF.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Core-Underlay mit OSPF.** Auf PE1, P und PE2: `router ospf 1` mit `router-id` gleich Loopback0 und `network`-Anweisungen für die Loopback0-/32 und die Core-Links in Area 0.
   - **Prüfen:** `show ip route ospf` auf PE1 enthält 10.255.0.2/32 und 10.255.0.3/32. `ping 10.255.0.3 source Loopback0` geht durch.
   - **Denkfrage:** Warum müssen die Loopbacks als /32 im IGP stehen, und was passiert bei einer Summary?
2. **LDP einschalten.** Auf den Core-Interfaces `mpls ip`, global `mpls label protocol ldp` und `mpls ldp router-id Loopback0 force`.
   - **Prüfen:** `show mpls ldp neighbor` zeigt auf dem P zwei Nachbarn, auf den PEs einen. `show mpls forwarding-table` listet Labels für die Loopbacks.
   - **Denkfrage:** Warum läuft die LDP-Sitzung zwischen den Loopbacks (Transport-Adresse) und nicht zwischen den Link-Adressen?
3. **VRF auf den PEs anlegen.** `vrf definition CUST-A` mit `rd 65000:100` und im `address-family ipv4` `route-target export 65000:100` und `route-target import 65000:100`. Dann am CE-Interface erst `vrf forwarding CUST-A`, danach die IP-Adresse.
   - **Prüfen:** `show vrf` listet CUST-A mit dem Interface. `ping vrf CUST-A 192.168.1.2` geht durch.
   - **Denkfrage:** Was passiert mit der IP-Adresse, wenn du `vrf forwarding` nachträglich setzt?
4. **PE-CE-Routing mit eBGP.** Auf den PEs im `address-family ipv4 vrf CUST-A` den CE als Nachbarn eintragen und aktivieren. Auf den CEs `router bgp` mit dem PE als Nachbar (AS 65000) und `network` für das LAN (Loopback1).
   - **Prüfen:** `show bgp vpnv4 unicast vrf CUST-A summary` auf den PEs: CE-Nachbar Established. Die PE-VRF enthält das Kunden-LAN (`show ip route vrf CUST-A`).
   - **Denkfrage:** Warum sitzt der CE-Nachbar im VRF-Address-Family und nicht unter dem globalen BGP?
5. **VPNv4 zwischen den PEs.** Auf PE1 und PE2: `router bgp 65000`, `no bgp default ipv4-unicast`, Nachbar = Loopback0 des anderen PE (`remote-as 65000`, `update-source Loopback0`). Im `address-family vpnv4` den Nachbarn aktivieren und `send-community extended`.
   - **Prüfen:** `show bgp vpnv4 unicast all summary` zeigt den Nachbarn Established mit empfangenen Präfixen. `show ip route vrf CUST-A` auf PE1 enthält 10.100.2.0/24 als BGP-Route.
   - **Denkfrage:** Was unterscheidet Route Distinguisher und Route Target, und warum braucht VPNv4 beide?
6. **Ende zu Ende.** Auf CE1: `ping 10.100.2.1 source Loopback1` und `traceroute 10.100.2.1 source Loopback1`.
   - **Prüfen:** Der Ping geht durch. Die Traceroute zeigt PE1, P (mit `[MPLS: Label … ]`), PE2, CE2.
   - **Denkfrage:** Warum braucht der P-Router keine Routen zu den Kundennetzen, und wie viele Labels trägt das Paket zwischen PE1 und P?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** LDP vergibt Labels nur für Präfixe, die **exakt** in der Routing-Tabelle stehen. Der BGP-Next-Hop eines VPNv4-Präfixes ist die /32-Loopback des PE. Steht sie nur als Summary (zum Beispiel /24) im IGP, gibt es kein Label für die /32, und der Transport-LSP bricht ab.
- **Zu 2:** LDP-Hellos laufen auf den Link-Adressen (Multicast 224.0.0.2). Die TCP-Sitzung selbst baut sich zur **Transport-Adresse** auf, standardmäßig die LDP-Router-ID. Mit `router-id Loopback0 force` ist das die stabile Loopback. Sie muss im IGP erreichbar sein, sonst kommt die Sitzung nicht hoch.
- **Zu 3:** IOS löscht die IP-Adresse eines Interfaces, wenn du `vrf forwarding` setzt oder änderst (Meldung „Removing all IP addresses“). Reihenfolge: erst VRF, dann Adresse.
- **Zu 4:** Die Kundenroute gehört in die Routing-Tabelle der VRF, nicht in die globale. Der VRF-Address-Family hält pro VRF eine eigene BGP-Tabelle und eigene Nachbarn. Das globale BGP ist für die PE-PE-Sitzung.
- **Zu 5:** Der **RD** macht ein IPv4-Präfix im Provider-Netz eindeutig (RD + Präfix = VPNv4-Präfix), damit überlappende Kundenadressen nebeneinander existieren. Das **RT** steuert, welche Routen eine VRF exportiert und importiert (Topologie des VPN). Die Eindeutigkeit allein sagt nichts darüber, wer die Route sehen darf.
- **Zu 6:** Der P-Router schaltet nur nach dem äußeren (Transport-)Label. Er kennt keine Kundenpräfixe. Zwischen PE1 und P trägt das Paket **zwei Labels**: das Transport-Label (für den LSP zu PE2) und das VPN-Label (bestimmt die VRF auf PE2). Wegen Penultimate Hop Popping entfernt der P das Transport-Label, PE2 sieht nur noch das VPN-Label.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** Die BGP-Sitzung zwischen PE1 und PE2 kommt nicht hoch; `show bgp vpnv4 unicast all summary` zeigt den Nachbarn dauerhaft in Active oder Idle.

**Ticket 2:** CE2 lernt 10.100.1.0/24 nicht, obwohl PE1 die Route von CE1 hat und die VPNv4-Sitzung steht.

**Ticket 3:** CE1 lernt 10.100.2.0/24 nicht, obwohl PE2 die Route von CE2 hat und die VPNv4-Sitzung steht.

**Ticket 4:** Alle Routen sind da, aber `ping 10.100.2.1 source Loopback1` von CE1 scheitert; die Traceroute zeigt nach PE1 nur noch Sterne.

**Ticket 5:** Die eBGP-Sitzung zwischen CE2 und PE2 steht nicht; CE2 meldet Active, PE2 hat keine Route aus dem Kundennetz.

## Verifikation
```
show mpls ldp neighbor
show mpls interfaces
show mpls forwarding-table
show vrf detail CUST-A
show bgp vpnv4 unicast all summary
show bgp vpnv4 unicast all
show ip route vrf CUST-A
show ip cef vrf CUST-A 10.100.2.0
traceroute 10.100.2.1 source Loopback1     ! von CE1
```

| Befehl | Das solltest du sehen |
|---|---|
| `show mpls ldp neighbor` auf dem P | zwei Nachbarn (10.255.0.1 und 10.255.0.3), State: Oper |
| `show bgp vpnv4 unicast all summary` auf PE1 | 10.255.0.3 mit Zahl im Feld State/PfxRcd (nicht Active) |
| `show ip route vrf CUST-A` auf PE1 | 10.100.1.0/24 über BGP vom CE1, 10.100.2.0/24 über BGP vom PE2 (10.255.0.3) |
| `traceroute` von CE1 nach 10.100.2.1 | PE1, P mit `[MPLS: Label …]`, PE2, CE2 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Die VPNv4-Sitzung steht und beide PEs haben die Routen, aber der Ping zwischen den CEs scheitert. Was prüfst du?
<details><summary>Antwort</summary>

**Den Transport-LSP.** BGP steht über das IGP, Pakete der VPN brauchen aber Labels. `show mpls ldp neighbor` auf jedem Core-Router, `show mpls forwarding-table` und `show ip cef <Loopback des Ziel-PE>` (Label vorhanden?), `traceroute` und `show mpls interfaces`. Meist fehlt `mpls ip` an einem Interface oder ein LDP-Nachbar.

</details>

2. Zwei Kunden nutzen beide 10.1.1.0/24. Was sorgt dafür, dass VPNv4 beide Präfixe unterscheiden kann, und was, dass sie sich nicht mischen?
<details><summary>Antwort</summary>

**Der RD macht sie eindeutig, die RTs trennen sie.** Mit unterschiedlichen RDs sind es zwei verschiedene VPNv4-Präfixe. Mit unterschiedlichen RTs importiert jede VRF nur die Routen ihres Kunden.

</details>

3. Was ändert sich, wenn die PEs über einen Route Reflector sprechen sollen, der selbst keine VRF hat?
<details><summary>Antwort</summary>

**Der RR muss die VPNv4-Routen ohne Import-RT behalten.** Normalerweise verwirft ein Router VPNv4-Routen, deren RT keine lokale VRF importiert (`bgp default route-target filter`). Ein RR braucht deshalb `no bgp default route-target filter`, damit er alle Routen annimmt und weitergibt.

</details>

## Prüfungsbezug
- Reihenfolge der Fehlersuche: IGP → LDP → BGP VPNv4 → VRF (RD/RT) → PE-CE-Routing.
- Typisch: BGP-Sitzung steht, Ping scheitert → Transport-LSP (LDP, `mpls ip`, /32 im IGP) prüfen.
- RT-Filter: Ohne passenden Import-RT landet eine VPNv4-Route nicht in der VRF (und wird ohne `no bgp default route-target filter` nicht einmal gehalten).
- VPNv4 braucht `send-community extended`, sonst gehen die RTs verloren.
- Zwei Labels im Core: Transport (LDP) außen, VPN-Label (MP-BGP) innen; PHP entfernt das äußere Label am vorletzten Hop.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
