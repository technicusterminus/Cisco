# Lab C4 – MPLS L3VPN: Shared Services, AS-Override und Route-Target-Design

**Plattform:** EVE-NG · **Dauer:** 110 min · **Niveau:** schwer

Ein Provider verbindet zwei Standorte von Kunde A, die beide AS 65100 nutzen, und stellt einen Shared-Services-Server bereit, den Kunde A und Kunde B erreichen dürfen. Untereinander müssen A und B getrennt bleiben. Du entwirfst die Route Targets so, dass genau das herauskommt, und löst das Problem mit dem gleichen Kunden-AS per `as-override`. Core, LDP und die VPNv4-Sitzung sind vorgegeben.

**Lernziele:** Nach diesem Lab kannst du …

- Ein Route-Target-Design für Shared Services entwerfen: wer exportiert was, wer importiert was.
- Erklären, warum importierte Routen nicht weiter exportiert werden und Kunden deshalb getrennt bleiben.
- PE-CE-eBGP mit gleichem Kunden-AS an mehreren Standorten per `as-override` lösen.
- VPN-Fehler mit `show bgp vpnv4 unicast all <Präfix>` am Route Target festmachen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.2.a` | MPLS und LDP | 8 |
| `Ziel::3.2.b` | MPLS L3VPN | 11 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| CEA1 | Cisco vIOS Router |  | 512 |
| PE1 | Cisco vIOS Router |  | 512 |
| PE2 | Cisco vIOS Router |  | 512 |
| CEA2 | Cisco vIOS Router |  | 512 |
| CES | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.6 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| CEA1 | Gi0/0 | PE1 | Gi0/1 |
| PE1 | Gi0/0 | PE2 | Gi0/0 |
| PE2 | Gi0/1 | CEA2 | Gi0/0 |
| PE2 | Gi0/2 | CES | Gi0/0 |

## Topologie

```
  CEA1  AS 65100                                                CEA2  AS 65100
  Lo1 10.100.1.1/24                                             Lo1 10.100.2.1/24
    | Gi0/0                                                       | Gi0/0
    | Gi0/1  VRF A                                       VRF A    | Gi0/1
   PE1  AS 64500  Gi0/0 ------------- MPLS ------------- Gi0/0  PE2  AS 64500
   Lo0 10.255.0.1                                               Lo0 10.255.0.2
   Lo10 10.110.1.1/24 = LAN von Kunde B (VRF B)                   | Gi0/2  VRF SHARED
                                                                  | Gi0/0
                                                                CES  AS 65200
                                                                Lo1 10.200.0.1/24 = Shared Services
```

| Link | Netz |
|---|---|
| PE1 Gi0/0 – PE2 Gi0/0 (Core, OSPF und LDP) | 10.0.12.0/30 (.1/.2) |
| PE1 Gi0/1 – CEA1 Gi0/0 (VRF A) | 192.168.11.0/30 (PE .1, CE .2) |
| PE2 Gi0/1 – CEA2 Gi0/0 (VRF A) | 192.168.12.0/30 (PE .1, CE .2) |
| PE2 Gi0/2 – CES Gi0/0 (VRF SHARED) | 192.168.13.0/30 (PE .1, CE .2) |
| Kundennetze | A: 10.100.1.0/24 und 10.100.2.0/24, B: 10.110.1.0/24 (Loopback10 auf PE1), Shared: 10.200.0.0/24 |

Vorgegeben sind OSPF und LDP im Core sowie die iBGP-Sitzung für VPNv4 zwischen PE1 und PE2. Kunde B hat in diesem Lab keinen eigenen Router: Loopback10 auf PE1 in VRF B steht für sein LAN. Das Route-Target-Schema: Kunde A 64500:100, Kunde B 64500:200, Shared Services 64500:999.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Core prüfen.** `show mpls ldp neighbor` und `show bgp vpnv4 unicast all summary` auf beiden PEs.
   - **Prüfen:** LDP-Nachbar und VPNv4-Sitzung stehen, noch ohne Präfixe.
   - **Denkfrage:** PE1 und PE2 sind direkt verbunden. Wie viele Labels trägt ein VPN-Paket auf dem Link zwischen ihnen?
2. **VRF A.** Auf PE1 und PE2 `vrf definition A` mit `rd 64500:100` und unter `address-family ipv4` Export und Import 64500:100. Hänge das CE-Interface in die VRF: `vrf forwarding A`, danach die IP-Adresse (PE1 192.168.11.1/30, PE2 192.168.12.1/30).
   - **Prüfen:** `show vrf` zeigt A mit dem CE-Interface, `ping vrf A 192.168.11.2` von PE1 klappt.
   - **Denkfrage:** Warum musst du die IP-Adresse nach `vrf forwarding` neu setzen?
3. **PE-CE mit eBGP.** CEA1 und CEA2: `router bgp 65100`, Loopback1-Netz per `network`, Nachbar ist der PE mit `remote-as 64500`. PE1 und PE2: unter `router bgp 64500` → `address-family ipv4 vrf A` den CE mit `remote-as 65100` eintragen und aktivieren.
   - **Prüfen:** PE1 kennt in VRF A beide Kundennetze (`show ip route vrf A`). CEA2 kennt 10.100.1.0/24 aber **nicht**.
   - **Denkfrage:** Warum fehlt das Netz auf CEA2, obwohl PE2 es in der VRF hat?
4. **AS-Override.** Auf PE1 und PE2 `neighbor … as-override` für den jeweiligen CE.
   - **Prüfen:** CEA2 hat 10.100.1.0/24 mit dem AS-Pfad `64500 64500`. `ping 10.100.1.1 source Loopback1` von CEA2 klappt.
   - **Denkfrage:** Welche Gefahr entsteht durch `as-override`, wenn ein Standort an zwei PEs hängt, und was hilft dagegen?
5. **Shared Services.** PE2: `vrf definition SHARED` mit `rd 64500:999`, Export 64500:999, Import 64500:999, 64500:100 und 64500:200. Gi0/2 in SHARED (192.168.13.1/30), eBGP zu CES (AS 65200). CES: `router bgp 65200`, kündigt 10.200.0.0/24 an. In VRF A auf beiden PEs zusätzlich `route-target import 64500:999`.
   - **Prüfen:** CEA1 und CEA2 erreichen 10.200.0.1. CES kennt 10.100.1.0/24 und 10.100.2.0/24.
   - **Denkfrage:** SHARED importiert die Netze von Kunde A. Warum landen sie trotzdem nicht bei Kunde B?
6. **Kunde B.** PE1: `vrf definition B` mit `rd 64500:200`, Export und Import 64500:200 und Import 64500:999. `interface Loopback10` mit `vrf forwarding B` und 10.110.1.1/24, unter `address-family ipv4 vrf B` `redistribute connected`.
   - **Prüfen:** `ping vrf B 10.200.0.1 source Loopback10` auf PE1 klappt. CEA1 hat keine Route zu 10.110.1.0/24.
   - **Denkfrage:** Was müsste gelten, damit Kunde A und Kunde B dieselben privaten Adressen nutzen dürfen?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** **Nur eins, das VPN-Label.** PE2 vergibt für seine Loopback implicit-null, deshalb entfernt PE1 als vorletzter Hop das Transport-Label (Penultimate Hop Popping). Mit einem P-Router dazwischen stünden auf dem ersten Link zwei Labels im Paket.
- **Zu 2:** **Weil `vrf forwarding` alle IP-Adressen vom Interface entfernt**, sie gehören danach in eine andere Routing-Tabelle. IOS meldet das auch. Deshalb immer erst die VRF, dann die Adresse.
- **Zu 3:** **Weil der AS-Pfad 65100 enthält, den AS von CEA2.** PE2 gibt die Route mit `64500 65100` weiter, CEA2 verwirft sie wegen des eigenen AS. Das ist derselbe Schleifenschutz wie im Internet.
- **Zu 4:** **Es kann eine Schleife entstehen.** Eine Route von Standort 1 geht über den ersten PE ins VPN und kommt über den zweiten PE zu Standort 1 zurück; weil 65100 ersetzt wurde, erkennt der CE sie nicht. Abhilfe ist Site of Origin (SoO): Der PE markiert die Routen eines Standorts und schickt sie nicht an einen Nachbarn mit derselben Markierung zurück.
- **Zu 5:** **Weil ein PE das Export-RT einer VRF nur an Routen hängt, die in dieser VRF entstanden sind.** Importierte Routen behalten ihre RTs und werden nicht neu exportiert. Kunde B importiert 64500:200 und 64500:999, aber nicht 64500:100.
- **Zu 6:** **Sie dürfen sich nicht in dem überschneiden, was SHARED importiert.** Der Shared-Server braucht eindeutige Ziele für seine Antworten. Überlappende Kundennetze gehen nur mit NAT vor den Shared Services oder mit getrennten Shared-VRFs pro Kunde.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** PE1 lernt von CEA1 kein einziges Präfix, obwohl die BGP-Sitzung steht.

**Ticket 2:** CEA2 erreicht das Netz von CEA1 (10.100.1.0/24) nicht.

**Ticket 3:** CEA1 hat keine Route zu 10.100.2.0/24, und auch der Shared-Server CES kennt das Netz von CEA2 nicht.

**Ticket 4:** CEA1 erreicht den Shared-Server 10.200.0.1 nicht, CEA2 schon.

**Ticket 5:** Kunde B erreicht den Shared-Server nicht: `ping vrf B 10.200.0.1 source Loopback10` auf PE1 scheitert, obwohl PE1 in VRF B eine Route zu 10.200.0.0/24 hat.

## Verifikation
```
show mpls ldp neighbor
show bgp vpnv4 unicast all summary
show bgp vpnv4 unicast all
show bgp vpnv4 unicast all 10.200.0.0
show ip route vrf A
show ip route vrf SHARED
show vrf detail
ping 10.200.0.1 source Loopback1           ! auf CEA1 und CEA2
ping vrf B 10.200.0.1 source Loopback10    ! auf PE1
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip route vrf A` auf PE1 | 10.100.1.0/24 vom CE, 10.100.2.0/24 und 10.200.0.0/24 über 10.255.0.2 |
| `show ip bgp` auf CEA2 | 10.100.1.0/24 mit AS-Pfad `64500 64500`, 10.200.0.0/24 mit `64500 65200` |
| `show ip bgp` auf CES | 10.100.1.0/24, 10.100.2.0/24 und 10.110.1.0/24 |
| `ping 10.110.1.1 source Loopback1` auf CEA1 | scheitert: Kunde A und Kunde B bleiben getrennt |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Wann nimmst du beim PE-CE-Routing `allowas-in` auf dem CE statt `as-override` auf dem PE?
<details><summary>Antwort</summary>

**Wenn der Provider-Router nicht angefasst werden kann oder soll.** `allowas-in` ist Sache des Kunden, `as-override` Sache des Providers. Beide schwächen den Schleifenschutz; bei mehrfach angebundenen Standorten gehört SoO dazu.

</details>

2. Wofür braucht es die RD, wenn doch das RT über den Import entscheidet?
<details><summary>Antwort</summary>

**Die RD macht Präfixe in VPNv4 eindeutig, das RT steuert Import und Export.** Zwei Kunden mit 10.1.0.0/24 werden durch unterschiedliche RDs zu zwei verschiedenen VPNv4-Präfixen. Unterschiedliche RDs pro PE für dieselbe VRF erlauben zudem Multipath über mehrere PEs, weil ein Route Reflector sonst nur den besten Pfad weitergibt.

</details>

3. Ein PE, der kein Route Reflector ist, verwirft VPNv4-Routen, deren RT er nicht importiert. Was passiert, wenn du später ein Import-RT ergänzt?
<details><summary>Antwort</summary>

**Er fordert die Routen per Route Refresh neu an.** Die automatische Route-Target-Filterung spart Speicher; nach einer neuen Import-Regel holt IOS die fehlenden Routen selbst nach, ein Reset der Sitzung ist nicht nötig.

</details>

4. PE-CE mit OSPF statt BGP: Warum erscheinen die Netze von Standort 1 an Standort 2 als O IA und nicht als O E2, und wozu dient ein Sham Link?
<details><summary>Antwort</summary>

**Weil der PE OSPF-Routen aus derselben OSPF-Domäne (gleiche Domain-ID) als Inter-Area-Routen (Typ 3) einspeist.** Gibt es zusätzlich einen Backdoor-Link zwischen den Standorten in derselben Area, gewinnt dieser als Intra-Area-Route immer. Ein Sham Link zwischen den PEs macht den Weg über das VPN zu einem Intra-Area-Link, dann entscheiden die Kosten.

</details>

## Prüfungsbezug
- RD macht Präfixe eindeutig, RT steuert Import und Export. Shared Services: zusätzliche Import-RTs auf beiden Seiten.
- Importierte Routen werden nicht neu exportiert, deshalb bleiben Kunden trotz gemeinsamer Shared-VRF getrennt.
- Gleicher Kunden-AS an mehreren Standorten: `as-override` (PE) oder `allowas-in` (CE), bei Mehrfachanbindung mit SoO.
- Fehlersuche Schicht für Schicht: IGP und LDP, VPNv4-Sitzung, RTs (`show bgp vpnv4 unicast all <Präfix>`), VRF-Routing, PE-CE.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-Konfiguration)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
