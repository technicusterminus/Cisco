# Lab 12 – Multicast mit IGMP und PIM Sparse Mode

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel bis schwer

Multicast-Verteilung über ein Routernetz: IGMP, PIM-SM mit statischem RP, Auto-RP/BSR im Vergleich, SSM, RPF-Check und typische Fehler. Quelle und Empfänger sind IOS-Hosts.

**Lernziele:** Nach diesem Lab kannst du …

- Multicast mit IGMP und PIM Sparse Mode aufbauen.
- Die Rolle des Rendezvous Points und den Wechsel auf den Shortest Path Tree erklären.
- Multicast-Fehler mit `show ip mroute`, `show ip pim neighbor` und der RPF-Prüfung eingrenzen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.3.d` | Multicast-Verfahren | 46 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| R4 | Cisco vIOS Router |  | 512 |
| SRC | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| REC1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| REC2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **3.5 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R2 | Gi0/1 | R3 | Gi0/0 |
| R2 | Gi0/2 | R4 | Gi0/0 |
| R1 | Gi0/1 | SRC | Gi0/0 |
| R3 | Gi0/1 | REC1 | Gi0/0 |
| R4 | Gi0/1 | REC2 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
  SRC ── R1 ──── R2 (RP, Lo0 10.255.0.2) ──── R3 ── REC1
        .1 Gi0/0   │  Gi0/1      Gi0/0
                   └── Gi0/2 ── R4 ── REC2
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R2 Gi0/1 – R3 Gi0/0 | 10.0.23.0/30 (.1/.2) |
| R2 Gi0/2 – R4 Gi0/0 | 10.0.24.0/30 (.1/.2) |
| R1 Gi0/1 – SRC | 192.168.1.0/24 (R1 .1, SRC .10) |
| R3 Gi0/1 – REC1 | 192.168.3.0/24 (R3 .1, REC1 .10) |
| R4 Gi0/1 – REC2 | 192.168.4.0/24 (R4 .1, REC2 .10) |

Loopbacks: R1 10.255.0.1, R2 10.255.0.2 (RP), R3 10.255.0.3, R4 10.255.0.4 (jeweils /32). OSPF 1 (Area 0) als Unicast-Underlay ist vorhanden. Multicast-Gruppe für Tests: **239.1.1.1**.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Multicast einschalten.** Setze auf allen Routern `ip multicast-routing`. Aktiviere `ip pim sparse-mode` auf allen Interfaces, auch auf den LANs und der Loopback des RP.
   - **Prüfen:** `show ip pim neighbor` zeigt auf R2 drei Nachbarn.
2. **Statischer RP.** Setze auf allen Routern `ip pim rp-address 10.255.0.2`.
   - **Prüfen:** `show ip pim rp mapping` nennt überall 10.255.0.2.
   - **Denkfrage:** Warum ist der RP eine Loopback-Adresse? Was passiert, wenn der RP ausfällt?
3. **Empfänger anmelden.** Setze auf REC1 und REC2 unter `interface Gi0/0` den Befehl `ip igmp join-group 239.1.1.1`.
   - **Prüfen:** `show ip igmp groups` auf R3 und R4 zeigt die Gruppe. `show ip mroute 239.1.1.1` auf R2 zeigt einen Eintrag `(*, 239.1.1.1)`.
   - **Denkfrage:** Woher weiß R2 von den Empfängern? Welche Aufgabe hat der IGMP-Querier?
4. **Quelle starten.** Sende auf SRC `ping 239.1.1.1 repeat 100`.
   - **Prüfen:** REC1 und REC2 antworten (die Antwort kommt per Unicast zurück). `show ip mroute` auf R3 zeigt nach kurzer Zeit einen Eintrag `(192.168.1.10, 239.1.1.1)` mit dem Flag `T`.
   - **Denkfrage:** Was passiert der Reihe nach zwischen R1, dem RP und R3, bis das Flag `T` erscheint?
5. **RPF-Check stören.** Setze auf R3 eine statische Route zu 192.168.1.0/24 über ein falsches Interface. Lies `show ip rpf 192.168.1.10` und kurz `debug ip mpacket`. Entferne die Route danach wieder.
   - **Prüfen:** Die Multicast-Pakete kommen bei REC1 nicht mehr an, und das Debug meldet „RPF failed“.
   - **Denkfrage:** Was prüft der RPF-Check genau?
6. **Auf dem Shared Tree bleiben.** Setze auf R3 `ip pim spt-threshold infinity`.
   - **Prüfen:** `show ip mroute` auf R3 zeigt keinen `(S,G)`-Eintrag mit `T` mehr, die Daten kommen über den RP.
   - **Denkfrage:** Wann ist das sinnvoll?
7. **BSR statt statischem RP.** Entferne `ip pim rp-address` und setze auf R2 `ip pim bsr-candidate Loopback0` und `ip pim rp-candidate Loopback0`.
   - **Prüfen:** `show ip pim rp mapping` auf R3 zeigt den RP mit der Info „learned via bootstrap“.
   - **Denkfrage:** Was unterscheidet BSR von Auto-RP?
8. **Source-Specific Multicast.** Setze `ip pim ssm default` auf allen Routern, `ip igmp version 3` auf R3 Gi0/1 und auf REC1 `ip igmp join-group 232.1.1.1 source 192.168.1.10`.
   - **Prüfen:** `show ip mroute 232.1.1.1` auf R3 zeigt direkt einen `(S,G)`-Eintrag ohne `(*,G)`.
   - **Denkfrage:** Warum braucht SSM keinen RP?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 2:** Eine Loopback ist immer up und über jeden verfügbaren Weg erreichbar. Fällt der RP aus, finden neue Quellen und Empfänger nicht mehr zueinander. Bestehende Shortest Path Trees laufen weiter. Für Redundanz gibt es Anycast-RP mit MSDP.
- **Zu 3:** REC1 meldet sich per IGMP bei R3. R3 schickt daraufhin einen PIM-Join Richtung RP, und so entsteht `(*,G)` auf dem Weg bis R2. Der IGMP-Querier fragt im LAN regelmäßig nach, ob es noch Empfänger gibt. Bei IGMPv2 übernimmt das der Router mit der niedrigsten IP.
- **Zu 4:** R1 sieht die Quelle und schickt die ersten Pakete in Register-Nachrichten per Unicast an den RP. Der RP packt sie aus und schickt sie den Shared Tree hinunter. Er baut außerdem einen `(S,G)`-Baum zu R1 auf. R3 erhält die ersten Pakete, erfährt so die Quelle und baut einen direkten `(S,G)`-Baum zur Quelle. Sobald Daten darüber ankommen, setzt er das Flag `T`.
- **Zu 5:** Der Router schaut in der Unicast-Tabelle nach, über welches Interface er die Quelle erreicht. Nur Multicast-Pakete, die auf genau diesem Interface ankommen, leitet er weiter. Alle anderen verwirft er. So verhindert Multicast Schleifen.
- **Zu 6:** Wenn es viele Quellen mit wenig Verkehr gibt, spart das Einträge und Zustände in den Routern. Oder wenn der RP ohnehin auf dem besten Weg liegt.
- **Zu 7:** BSR ist Teil des PIMv2-Standards und verteilt die RP-Informationen in PIM-Nachrichten von Router zu Router. Auto-RP ist eine Cisco-Lösung mit den Gruppen 224.0.1.39 (Kandidaten) und 224.0.1.40 (Mapping Agent). Sie braucht Dense Mode oder `ip pim autorp listener`.
- **Zu 8:** Der Empfänger nennt per IGMPv3 die Quelle gleich mit. Der Router kann sofort einen Baum direkt zur Quelle bauen. Der RP wird nur gebraucht, um unbekannte Quellen und Empfänger zusammenzubringen.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** R3 hat keinen PIM-Nachbarn zu R2; REC1 bekommt keine Pakete, REC2 funktioniert.

**Ticket 2:** REC2 empfängt keine Pakete, `show ip pim rp mapping` auf R4 zeigt einen anderen RP als auf den übrigen Routern.

**Ticket 3:** Weder REC1 noch REC2 empfangen etwas, obwohl alle Join-Zustände stehen. Auf R1 gibt es keine `(S,G)`-Einträge.

**Ticket 4:** Der RP zeigt `(*,G)`-Einträge nicht und Multicast wird auf R2 nicht weitergeleitet.

## Verifikation
```
show ip pim neighbor
show ip pim rp mapping
show ip igmp groups
show ip mroute [239.1.1.1]
show ip rpf 192.168.1.10
show ip mfib
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip mroute 239.1.1.1` auf R2 | `(*, 239.1.1.1)` mit RP 10.255.0.2 und `(192.168.1.10, 239.1.1.1)` |
| Ping von SRC an 239.1.1.1 | Antworten von REC1 und REC2 |
| `show ip rpf 192.168.1.10` auf R3 | RPF-Interface = Uplink zu R2 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Welche MAC-Adresse gehört zur Gruppe 239.1.1.1?
<details><summary>Antwort</summary>

**01-00-5E-01-01-01.** Die unteren 23 Bit der Gruppenadresse werden an das feste Präfix 01-00-5E angehängt. 239.1.1.1 endet auf 1.1.1, also 01.01.01. Weil 5 Bit verloren gehen, teilen sich 32 Gruppen dieselbe MAC.

</details>

2. Warum sieht ein Empfänger-Router nach dem ersten Datenpaket `(S,G)` mit Flag `T`?
<details><summary>Antwort</summary>

**Er ist auf den Shortest Path Tree zur Quelle gewechselt.** Zuerst kommen die Daten über den RP (Shared Tree, `(*,G)`). Danach baut der letzte Router einen direkten Baum zur Quelle auf. Das Flag `T` zeigt, dass Daten auf diesem Baum ankommen.

</details>

3. Was löst ein `RPF failed` aus?
<details><summary>Antwort</summary>

**Ein Paket kommt auf einem anderen Interface an als dem Rückweg zur Quelle.** Der Router prüft per Unicast-Routing, über welches Interface er die Quelle erreicht. Kommt das Paket woanders an, verwirft er es. Ursachen: asymmetrisches Routing, fehlende Route oder ein falsches statisches `ip mroute`.

</details>

## Prüfungsbezug
- Bereiche: 224.0.0.0/24 lokal, 232.0.0.0/8 SSM, 239.0.0.0/8 administrativ.
- PIM-SM: Shared Tree `(*,G)` zum RP, Quellbaum `(S,G)`, Register- und Join-Nachrichten.
- Der RPF-Check prüft das Eingangs-Interface gegen den Unicast-Rückweg zur Quelle.
- IGMPv2: Querier und General Query. IGMPv3: Quellfilter, nötig für SSM.
- Multicast-MAC: 01-00-5E plus die unteren 23 Bit der Gruppenadresse.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/12-Multicast-PIM/`](../../CML-Labs/12-Multicast-PIM/).
