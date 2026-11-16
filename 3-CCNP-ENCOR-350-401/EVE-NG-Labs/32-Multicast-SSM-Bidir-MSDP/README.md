# Lab 32 – Multicast vertieft: IGMPv3 und SSM, Bidir-PIM, Anycast-RP mit MSDP

**Plattform:** EVE-NG · **Dauer:** 120 min · **Niveau:** schwer

Lab 12 hat PIM Sparse Mode mit einem RP gezeigt. Hier baust du auf demselben Netz nacheinander die drei Verfahren, die das Blueprint zusätzlich nennt: Source-Specific Multicast mit IGMPv3 (kein RP), Bidirectional PIM (nur Shared Tree, kein `(S,G)`) und zwei RPs mit gleicher Adresse, die sich ihre Quellen per MSDP mitteilen. Jedes Verfahren bekommt einen eigenen Gruppenbereich, damit du sie nebeneinander vergleichen kannst.

**Lernziele:** Nach diesem Lab kannst du …

- Für eine Gruppe aus dem Zustand in `show ip mroute` ablesen, ob sie als SSM, Bidir oder Sparse Mode läuft.
- SSM mit IGMPv3 aufbauen und erklären, warum ein Beitritt ohne Quelle im Bereich 232.0.0.0/8 nichts bewirkt.
- Bidir-PIM einrichten und die Rolle des Designated Forwarder (DF) am Ausgang von `show ip pim interface df` zeigen.
- Anycast-RP mit MSDP bauen und am SA-Cache nachweisen, wie ein RP von einer Quelle beim anderen RP erfährt.
- Die vier Verfahren (ASM, SSM, Bidir, Anycast-RP/MSDP) nach RP-Bedarf, Zustand und Einsatzfall einordnen.

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
| SRC | Cisco vIOS Router | Host (vIOS, wie in CML) | 512 |
| REC | Cisco vIOS Router | Host (vIOS, wie in CML) | 512 |

Summe (alle Nodes als vIOS/…): ca. **3.1 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| R1 | Gi0/0 | R2 | Gi0/0 |
| R2 | Gi0/1 | R3 | Gi0/0 |
| R3 | Gi0/1 | R4 | Gi0/0 |
| R1 | Gi0/1 | SRC | Gi0/0 |
| R4 | Gi0/1 | REC | Gi0/0 |

### Hosts: vIOS oder VPCS

Die Hosts müssen vIOS sein: SRC sendet Multicast-Pings, REC tritt Gruppen per IGMPv3 mit Quellangabe bei. Beides kann ein VPCS nicht. In `solutions/REC.cfg` stehen die Beitritte aus Teil A.

## Topologie

```
                    Lo1 10.255.0.100 (Anycast-RP)      Lo1 10.255.0.100 (Anycast-RP)
                    Lo2 10.255.0.200 (Bidir-RP)
  SRC ──── R1 ────────── R2 ═══════ MSDP (Lo0–Lo0) ═══════ R3 ────────── R4 ──── REC
      Gi0/1  Gi0/0   Gi0/0  Gi0/1                      Gi0/0  Gi0/1   Gi0/0  Gi0/1
```

| Link | Netz |
|---|---|
| R1 Gi0/0 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R2 Gi0/1 – R3 Gi0/0 | 10.0.23.0/30 (.1/.2) |
| R3 Gi0/1 – R4 Gi0/0 | 10.0.34.0/30 (.1/.2) |
| R1 Gi0/1 – SRC | 192.168.1.0/24 (R1 .1, SRC .10) |
| R4 Gi0/1 – REC | 192.168.4.0/24 (R4 .1, REC .10) |

Loopback0: R1 10.255.0.1 bis R4 10.255.0.4 (/32). OSPF 1 (Area 0) ist als Unicast-Underlay **fertig konfiguriert**, mit fest gesetzter Router-ID. Die Loopbacks 1 und 2 legst du in Teil A selbst an.

| Gruppenbereich | Verfahren | RP |
|---|---|---|
| 232.0.0.0/8 | SSM | keiner |
| 239.1.0.0/16 | Sparse Mode (ASM) | 10.255.0.100, Anycast auf R2 und R3 |
| 239.2.0.0/16 | Bidir-PIM | 10.255.0.200 auf R2 |

Testgruppen: **232.1.1.1**, **239.1.1.1**, **239.2.1.1**. Quelle ist immer SRC (192.168.1.10), Empfänger REC.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A. Bei **Erst vorhersagen** schreibst du deine Erwartung auf, *bevor* du den Befehl eingibst. Lag die Vorhersage daneben, hast du genau die Stelle gefunden, an der dein Modell noch nicht stimmt. Die Auflösung steht ebenfalls bei den Antworten.

1. **Grundlage.** Setze auf R1 bis R4 `ip multicast-routing` und `ip pim sparse-mode` auf allen Gi-Interfaces und auf Loopback0.
   - **Prüfen:** `show ip pim neighbor` zeigt auf R2 und R3 je zwei Nachbarn. `show ip ospf neighbor` war schon vorher vollständig.
   - **Denkfrage:** PIM selbst tauscht keine Routen aus. Woher nimmt ein Router die Information für den RPF-Check?
2. **SSM einschalten.** Setze auf allen vier Routern `ip pim ssm default`. Stelle R4 Gi0/1 und REC Gi0/0 auf `ip igmp version 3`. REC tritt bei: `ip igmp join-group 232.1.1.1 source 192.168.1.10`.
   - **Erst vorhersagen:** SRC sendet noch nichts. Welche Einträge stehen jetzt schon in `show ip mroute 232.1.1.1` auf R2: `(*,G)`, `(S,G)`, beide oder keiner?
   - **Prüfen:** `show ip igmp groups 232.1.1.1 detail` auf R4 nennt die Quelle 192.168.1.10 im Modus INCLUDE. `show ip mroute 232.1.1.1` zeigt auf R4, R3, R2 und R1 genau einen `(192.168.1.10, 232.1.1.1)`-Eintrag mit Flag `s`, kein `(*,G)`. `ping 232.1.1.1 repeat 5` auf SRC wird von 192.168.4.10 beantwortet.
   - **Denkfrage:** Der Baum steht, bevor die Quelle ein Paket sendet. Warum geht das bei SSM, bei Sparse Mode aber nicht?
3. **SSM-Falle: Beitritt ohne Quelle.** REC tritt zusätzlich `ip igmp join-group 232.2.2.2` bei, also ohne `source`.
   - **Erst vorhersagen:** Entsteht auf R4 ein Multicast-Zustand für 232.2.2.2?
   - **Prüfen:** `show ip mroute 232.2.2.2` auf R4 bleibt leer, ein Ping von SRC an 232.2.2.2 bleibt unbeantwortet. Entferne den Beitritt danach wieder.
   - **Denkfrage:** Was würde passieren, wenn R4 Gi0/1 noch auf IGMPv2 stünde und REC den Beitritt *mit* Quelle sendet?
4. **Bidir-PIM.** Lege auf R2 `interface Loopback2` mit 10.255.0.200/32 und `ip pim sparse-mode` an und nimm die Adresse in OSPF auf. Setze auf allen Routern `ip pim bidir-enable`, `access-list 20 permit 239.2.0.0 0.0.255.255` und `ip pim rp-address 10.255.0.200 20 bidir`. REC tritt `239.2.1.1` bei, SRC sendet `ping 239.2.1.1 repeat 20`.
   - **Erst vorhersagen:** Wie viele `(S,G)`-Einträge für 239.2.1.1 findest du nach dem Ping im ganzen Netz?
   - **Prüfen:** `show ip pim rp mapping` nennt 10.255.0.200 mit dem Zusatz `bidir`. `show ip mroute 239.2.1.1` zeigt überall nur `(*, 239.2.1.1)` mit Flag `B`, auch auf R1 direkt an der Quelle. `show ip pim interface df` listet pro Interface den DF für den RP 10.255.0.200.
   - **Denkfrage:** Bei Bidir gibt es keine Register-Nachricht und keinen RPF-Check gegen die Quelle. Was verhindert dann Schleifen?
5. **Anycast-RP ohne MSDP.** Lege auf R2 **und** R3 `interface Loopback1` mit derselben Adresse 10.255.0.100/32 und `ip pim sparse-mode` an und nimm sie auf beiden in OSPF auf. Setze auf allen Routern `access-list 10 permit 239.1.0.0 0.0.255.255` und `ip pim rp-address 10.255.0.100 10`. REC tritt `239.1.1.1` bei, SRC sendet `ping 239.1.1.1 repeat 10`.
   - **Erst vorhersagen:** Zu welchem der beiden RPs schickt R1 sein Register, zu welchem R4 seinen Join? Antwortet REC auf den Ping?
   - **Prüfen:** `show ip route 10.255.0.100` zeigt auf R1 den Weg über R2, auf R4 den Weg über R3. Der Ping bleibt **unbeantwortet**. R2 kennt `(192.168.1.10, 239.1.1.1)` ohne Empfänger, R3 kennt `(*, 239.1.1.1)` ohne Quelle.
   - **Denkfrage:** Warum ist die Router-ID in OSPF hier fest gesetzt? Was wäre passiert, wenn R2 und R3 sie automatisch gewählt hätten?
6. **MSDP verbindet die RPs.** R2: `ip msdp peer 10.255.0.3 connect-source Loopback0` und `ip msdp originator-id Loopback0`. R3 spiegelbildlich mit Peer 10.255.0.2. Wiederhole den Ping.
   - **Prüfen:** `show ip msdp summary` zeigt den Peer im Zustand `Up`. Während SRC sendet, steht in `show ip msdp sa-cache` auf R3 der Eintrag `(192.168.1.10, 239.1.1.1), RP 10.255.0.2`. Der Ping wird jetzt beantwortet, und R3 hat einen `(S,G)`-Eintrag mit Flag `M`.
   - **Denkfrage:** Wozu dient `originator-id`, und warum zeigt `connect-source` auf Loopback0 und nicht auf die Anycast-Adresse?
7. **RP-Ausfall.** Starte auf SRC `ping 239.1.1.1 repeat 200` und schalte währenddessen auf R3 `interface Loopback1` ab.
   - **Erst vorhersagen:** Welchen RP nutzt R4 danach, und wovon hängt die Dauer der Unterbrechung ab?
   - **Prüfen:** `show ip route 10.255.0.100` auf R4 zeigt nach der OSPF-Konvergenz den Weg über R3 zu R2. Der Ping läuft nach wenigen ausgefallenen Paketen weiter. Schalte Loopback1 danach wieder ein.
   - **Denkfrage:** An welcher Stelle unterscheidet sich das von einem RP-Wechsel per BSR oder Auto-RP?
8. **Vergleichen.** Fülle die Tabelle aus dem Gedächtnis aus, bevor du die Antwort aufklappst: Für **Sparse Mode (ASM)**, **SSM**, **Bidir** jeweils: RP nötig? Welche Einträge (`(*,G)`, `(S,G)`)? Welche IGMP-Version am Empfänger? Typischer Einsatz?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Aus der Unicast-Routing-Tabelle, hier also aus OSPF. Daher der Name *Protocol Independent* Multicast: PIM ist egal, welches Protokoll die Routen liefert. Fehlt die Unicast-Route zur Quelle oder zum RP, scheitert der RPF-Check, und es entsteht kein Baum.
- **Zu 2:** **Nur `(S,G)`.** Bei SSM nennt der Empfänger die Quelle im IGMPv3-Report. R4 kann den Join deshalb sofort Hop für Hop in Richtung Quelle schicken. Bei Sparse Mode kennt der Empfänger-Router die Quelle nicht und muss erst über den RP gehen.
- **Zu 3:** **Nein.** Im SSM-Bereich verwirft der Router jeden Beitritt ohne Quelle, es gibt dort kein `(*,G)`. Mit IGMPv2 am Router-Interface fällt auch der Host auf Version 2 zurück und kann gar keine Quelle mehr nennen. Der Report kommt an, wird aber ignoriert. Das ist einer der häufigsten SSM-Fehler und Ticket-Material.
- **Zu 4:** **Keinen.** Bidir kennt nur den Shared Tree. Daten fließen von der Quelle *aufwärts* zum RP und von dort abwärts, auf denselben `(*,G)`-Einträgen. Schleifen verhindert die DF-Wahl: Pro Segment gewinnt genau ein Router (der mit der besten Unicast-Metrik zum RP), und nur er darf Verkehr in Richtung RP weiterleiten.
- **Zu 5:** R1 registriert bei **R2**, R4 schickt den Join an **R3**: Jeder nimmt den RP, der laut OSPF am nächsten liegt. Die beiden RPs wissen nichts voneinander, also antwortet REC nicht. Zur Router-ID: Ohne feste Vorgabe wählt OSPF die höchste Loopback-Adresse. Das wäre auf R2 *und* R3 die 10.255.0.100 gewesen, also zwei Router mit derselben Router-ID. Anycast-Adressen dürfen nie zur Router-ID werden.
- **Zu 6:** MSDP trägt in jeder Source-Active-Meldung die Adresse des RP, der sie erzeugt hat. Ohne `originator-id` stünde dort die Anycast-Adresse, die beide Router besitzen. Der Empfänger könnte den Absender nicht von sich selbst unterscheiden. Aus demselben Grund läuft die TCP-Sitzung (Port 639) zwischen den eindeutigen Loopback0-Adressen: Ein Paket an 10.255.0.100 käme beim nächstgelegenen RP an, also bei einem selbst.
- **Zu 7:** R4 nutzt **R2**. Die Unterbrechung dauert so lange wie die OSPF-Konvergenz plus der neue Join. Bei BSR oder Auto-RP muss erst der Ausfall des RP per Holdtime erkannt und eine neue Zuordnung verteilt werden. Das dauert deutlich länger. Anycast-RP verlagert die Redundanz ins Unicast-Routing.
- **Zu 8:** **ASM:** RP nötig, erst `(*,G)`, dann `(S,G)`; IGMPv2 genügt; viele unbekannte Quellen. **SSM:** kein RP, nur `(S,G)`; IGMPv3 Pflicht; bekannte Quellen wie IPTV. **Bidir:** RP nötig (als Wurzel, er muss nicht einmal ein echtes Gerät sein), nur `(*,G)`; IGMPv2 genügt; sehr viele Quellen, die zugleich Empfänger sind. **MSDP** ist kein viertes Verfahren, sondern verbindet RPs von Sparse-Mode-Domänen.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** SSM: REC ist 232.1.1.1 mit Quelle 192.168.1.10 beigetreten, bekommt aber nichts. Auf R4 gibt es keinen `(S,G)`-Eintrag für die Gruppe.

**Ticket 2:** Bidir: Der Ping von SRC an 239.2.1.1 bleibt unbeantwortet. Die Gruppe 239.1.1.1 ist davon nicht betroffen, sobald die übrigen Tickets gelöst sind.

**Ticket 3:** Anycast-RP: `show ip msdp summary` zeigt auf R2 und R3 keinen Peer im Zustand `Up`.

**Ticket 4:** Anycast-RP: Auch mit stehender MSDP-Sitzung antwortet REC nicht auf Pings an 239.1.1.1. Der SA-Cache auf R3 bleibt leer, während SRC sendet.

## Verifikation
```
show ip pim neighbor
show ip pim rp mapping
show ip igmp groups 232.1.1.1 detail      ! auf R4
show ip mroute 232.1.1.1
show ip mroute 239.2.1.1
show ip pim interface df
show ip msdp summary
show ip msdp sa-cache
show ip mroute 239.1.1.1
ping 239.1.1.1 repeat 10                  ! auf SRC
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip mroute 232.1.1.1` auf R2 | nur `(192.168.1.10, 232.1.1.1)`, Flag `s`, kein `(*,G)` |
| `show ip mroute 239.2.1.1` auf R1 | nur `(*, 239.2.1.1)`, Flag `B` |
| `show ip pim rp mapping` | 10.255.0.100 für ACL 10, 10.255.0.200 für ACL 20 mit `bidir` |
| `show ip msdp summary` auf R2 und R3 | ein Peer, Zustand `Up` |
| `show ip msdp sa-cache` auf R3, während SRC sendet | `(192.168.1.10, 239.1.1.1), RP 10.255.0.2` |
| Pings von SRC an 232.1.1.1, 239.1.1.1 und 239.2.1.1 | jeweils Antwort von 192.168.4.10 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Ein Empfänger meldet sich per IGMPv2 für 232.5.5.5 an. Die Router haben `ip pim ssm default`. Was passiert?
<details><summary>Antwort</summary>

**Nichts, der Beitritt wird ignoriert.** 232.0.0.0/8 ist der SSM-Bereich. Dort gibt es kein `(*,G)` und keinen RP. Ohne Quellangabe (IGMPv3 INCLUDE) kann der Router keinen Baum bauen. Abhilfe: IGMPv3 auf Host und Router, oder auf dem Router eine SSM-Zuordnung (`ip igmp ssm-map`), die v2-Beitritten eine Quelle zuweist.

</details>

2. In `show ip mroute` steht `(*, 239.2.1.1)` mit Flag `B` und mehreren Interfaces, aber kein `(S,G)`, obwohl gerade zwanzig Quellen senden. Ist das ein Fehler?
<details><summary>Antwort</summary>

**Nein, das ist Bidir-PIM.** Alle Quellen teilen sich den einen `(*,G)`-Eintrag. Genau das ist der Vorteil: Der Zustand im Router wächst nicht mit der Zahl der Quellen. Der Preis ist, dass der Verkehr immer über den Weg zum RP läuft und nie auf einen kürzeren Quellbaum wechselt.

</details>

3. Zwei RPs mit Anycast-Adresse, MSDP-Sitzung ist `Up`, aber der SA-Cache bleibt leer. Nenne zwei mögliche Ursachen.
<details><summary>Antwort</summary>

**(1) Der RP, bei dem die Quelle registriert, erkennt sich nicht als RP** (kein PIM auf dem RP-Interface, falsche Gruppen-ACL), er erzeugt also keine SA. **(2) Es sendet gerade keine Quelle.** SA-Einträge entstehen nur für aktive Quellen und altern nach kurzer Zeit aus. Dazu kommen SA-Filter und ein fehlgeschlagener RPF-Check auf den Peer, wenn es mehrere MSDP-Peers gibt.

</details>

4. Warum prüft Bidir-PIM eingehende Pakete nicht per RPF gegen die Quelle?
<details><summary>Antwort</summary>

**Weil Daten auf dem Shared Tree in beide Richtungen fließen.** Ein Paket von der Quelle zum RP kommt aus Sicht des klassischen RPF-Checks auf dem „falschen“ Interface an. Bidir ersetzt den Check durch den Designated Forwarder: Pro Segment darf nur der DF Pakete in Richtung RP annehmen und weiterleiten.

</details>

## Prüfungsbezug
- SSM: Bereich 232.0.0.0/8, kein RP, nur `(S,G)`, braucht IGMPv3 (oder `ssm-map`).
- Bidir-PIM: nur `(*,G)`, keine Register-Nachricht, kein SPT-Wechsel, Schleifenschutz über den DF pro Segment.
- MSDP: TCP 639 zwischen RPs, Source-Active-Meldungen mit Quelle, Gruppe und erzeugendem RP.
- Anycast-RP: gleiche RP-Adresse auf mehreren Routern, Auswahl und Ausfallschutz über das Unicast-Routing, MSDP gleicht die Quellen ab.
- IGMPv2: Leave und gruppenspezifische Query. IGMPv3: Quellfilter INCLUDE/EXCLUDE, Reports an 224.0.0.22.
- Flags in `show ip mroute`: `s` SSM, `B` Bidir, `T` SPT-Bit, `M` per MSDP gelernt, `A` Kandidat für MSDP-Ankündigung.

## Hinweis zum Image

Die Flags und Zustandsnamen stammen aus der IOS-15-Dokumentation. Zeigt dein IOSv-Image bei Ticket 4 ein anderes Detail (etwa eine andere Debug-Meldung), zählt der Befund: Loopback1 fehlt in `show ip pim interface`. Bidir-PIM läuft in IOSv in Software und reagiert nach einer Änderung manchmal erst nach `clear ip mroute *`.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/32-Multicast-SSM-Bidir-MSDP/`](../../CML-Labs/32-Multicast-SSM-Bidir-MSDP/).
