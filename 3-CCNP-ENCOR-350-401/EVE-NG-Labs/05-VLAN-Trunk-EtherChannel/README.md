# Lab 05 – VLANs, Trunks und EtherChannel

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** leicht bis mittel

Drei Switches, Router-on-a-Stick und drei Hosts: 802.1Q-Trunks (Native VLAN, Allowed VLANs, DTP, VTP) und EtherChannel mit LACP, PAgP und statischem Modus.

**Lernziele:** Nach diesem Lab kannst du …

- VLANs, 802.1Q-Trunks und Router-on-a-Stick aufbauen.
- EtherChannel mit LACP bündeln und Modus-Fehler erkennen.
- Mit `show interfaces trunk` und `show etherchannel summary` systematisch Layer 2 prüfen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.1.a` | 802.1Q und Trunks | 31 |
| `Ziel::3.1.b` | EtherChannel | 34 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| SW1 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW2 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW3 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| R1 | Cisco vIOS Router |  | 512 |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H3 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **4.2 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.8 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| SW1 | Gi0/0 | SW2 | Gi0/0 |
| SW1 | Gi0/1 | SW2 | Gi0/1 |
| SW1 | Gi0/2 | SW3 | Gi0/0 |
| SW1 | Gi0/3 | SW3 | Gi0/1 |
| SW1 | Gi1/0 | R1 | Gi0/0 |
| SW2 | Gi1/0 | H1 | Gi0/0 |
| SW3 | Gi1/0 | H2 | Gi0/0 |
| SW3 | Gi1/1 | H3 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
                      ┌── Po1 (LACP, 2 Links) ── SW2 ── H1 (VLAN10)
 R1 ══trunk══ SW1 ════┤
                      └── Po2 (PAgP, 2 Links) ── SW3 ──┬── H2 (VLAN20)
                                                       └── H3 (VLAN10)
```

| VLAN | Name | Subnetz | Gateway (R1 Subinterface) |
|---|---|---|---|
| 10 | USERS | 10.10.10.0/24 | .1 (`Gi0/0.10`) |
| 20 | SERVERS | 10.10.20.0/24 | .1 (`Gi0/0.20`) |
| 99 | NATIVE | – | ungenutzt |

H1 10.10.10.11 (SW2 Gi1/0), H2 10.10.20.12 (SW3 Gi1/0), H3 10.10.10.13 (SW3 Gi1/1). Verkabelung: SW1 Gi0/0–0/1 ↔ SW2 Gi0/0–0/1, SW1 Gi0/2–0/3 ↔ SW3 Gi0/0–0/1, SW1 Gi1/0 ↔ R1 Gi0/0.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **VLANs anlegen.** Lege auf allen Switches VLAN 10 (USERS), 20 (SERVERS) und 99 (NATIVE) an. Stelle VTP auf `vtp mode transparent`.
   - **Prüfen:** `show vlan brief` zeigt die drei VLANs, `show vtp status` den Modus Transparent.
   - **Denkfrage:** Warum ist ein neuer Switch im VTP-Modus Server oder Client gefährlich?
2. **Trunk zum Router.** Mache SW1 Gi1/0 zum festen Trunk (`switchport trunk encapsulation dot1q`, `switchport mode trunk`, `switchport nonegotiate`), mit Native VLAN 99 und den erlaubten VLANs 10 und 20. R1 bekommt die Subinterfaces `Gi0/0.10` und `Gi0/0.20` mit `encapsulation dot1Q` und je einer IP-Adresse.
   - **Prüfen:** `show interfaces trunk` auf SW1 listet den Trunk. Später pingt H1 sein Gateway 10.10.10.1.
3. **EtherChannel mit LACP.** Bündle die beiden Links SW1–SW2 zu Po1: SW1 `channel-group 1 mode active`, SW2 `mode passive`. Konfiguriere Po1 als Trunk (VLAN 10 und 20, Native 99).
   - **Prüfen:** `show etherchannel summary` zeigt `Po1(SU)` und beide Ports mit `(P)`.
   - **Denkfrage:** Welche Modus-Paare bilden einen Channel: active/passive, passive/passive, on/active?
4. **EtherChannel mit PAgP.** Bündle SW1–SW3 zu Po2: SW1 `mode desirable`, SW3 `mode auto`.
   - **Prüfen:** `show etherchannel summary` zeigt `Po2(SU)` mit Protokoll PAgP.
   - **Denkfrage:** Was unterscheidet PAgP von LACP?
5. **Hosts anschließen.** Konfiguriere die Ports von H1 (VLAN 10), H2 (VLAN 20) und H3 (VLAN 10) als Access-Ports mit `spanning-tree portfast`.
   - **Prüfen:** H1 pingt H3 (gleiches VLAN, nur über Layer 2) und H2 (anderes VLAN, über R1).
6. **Lastverteilung.** Setze `port-channel load-balance src-dst-ip`.
   - **Prüfen:** `show etherchannel load-balance` zeigt die neue Methode.
   - **Denkfrage:** Warum nutzt eine einzelne Verbindung immer nur einen Link des Bündels?
7. **Native VLAN falsch setzen.** Stelle auf SW3 an Po2 bewusst Native VLAN 1 ein.
   - **Prüfen:** Das Log meldet `%CDP-4-NATIVE_VLAN_MISMATCH`. Stelle danach wieder 99 ein.
   - **Denkfrage:** Welchen Angriff erschwert ein ungenutztes Native VLAN?
8. **Trunks ausdünnen.** Erlaube auf jedem Trunk nur die VLANs, die dahinter wirklich gebraucht werden.
   - **Prüfen:** `show interfaces trunk` hat drei Blöcke: allowed, allowed and active, forwarding. Achte darauf, dass jedes benötigte VLAN in allen dreien steht.

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Hat der neue Switch eine höhere Revisionsnummer, übernehmen alle anderen seine VLAN-Datenbank. Fehlen dort VLANs, verschwinden sie im ganzen Netz, und die Ports darin gehen offline. Im Modus Transparent gleicht ein Switch nichts ab.
- **Zu 3:** active/active und active/passive bilden einen Channel. passive/passive nicht, weil keine Seite anfängt. on/active auch nicht: `on` sendet keine LACP-Nachrichten.
- **Zu 4:** PAgP ist Cisco-eigen und kennt die Modi desirable und auto. LACP ist der IEEE-Standard (802.3ad) mit active und passive. Beide bündeln bis zu 8 aktive Links. LACP kann zusätzlich bis zu 8 Ports als Reserve halten.
- **Zu 6:** Der Switch berechnet aus den gewählten Feldern einen Hash, und der bestimmt den Link. Gleiche Verbindung, gleicher Hash, gleicher Link. So kommen die Pakete einer Verbindung nie in falscher Reihenfolge an.
- **Zu 7:** Double Tagging (VLAN Hopping): Ein Angreifer im Native VLAN schickt einen Frame mit zwei Tags. Der erste Switch entfernt das äußere Tag, der nächste leitet nach dem inneren weiter. Ist das Native VLAN ein ungenutztes VLAN wie 99, sitzt kein Angreifer darin.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Po1 kommt nicht hoch: Auf SW1 sind die Ports `s` (suspended), H1 hat keine Verbindung.

**Ticket 2:** H2 (VLAN 20) hat weder Gateway noch Verbindung, H3 (VLAN 10) funktioniert.

**Ticket 3:** Alle Hosts in VLAN 20 erreichen ihr Gateway 10.10.20.1 nicht, VLAN 10 ist in Ordnung.

**Ticket 4:** H3 (10.10.10.13) erreicht weder H1 noch das Gateway.

## Verifikation
```
show vlan brief
show interfaces trunk
show etherchannel summary
show etherchannel load-balance
show lacp neighbor
show pagp neighbor
show vtp status
```

| Befehl | Das solltest du sehen |
|---|---|
| `show etherchannel summary` auf SW1 | `Po1(SU)` mit `Gi0/0(P) Gi0/1(P)` (LACP), `Po2(SU)` mit PAgP |
| Ping von jedem Host | jeder Host erreicht sein Gateway, H1 erreicht H2 über R1 |
| `show interfaces trunk` | Native VLAN 99 auf allen Trunks |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Zwei Switches stehen auf `dynamic auto`. Entsteht ein Trunk?
<details><summary>Antwort</summary>

**Nein, es entsteht kein Trunk.** `dynamic auto` wartet nur und fragt selbst nicht. Zwei wartende Seiten bleiben Access-Ports. Mindestens eine Seite muss `dynamic desirable` oder `trunk` sein.

</details>

2. Ein Port ist in einem Channel gelistet, aber als `s` (suspended) markiert. Typische Ursache?
<details><summary>Antwort</summary>

**Die Parameter oder der Modus passen nicht zur Gegenseite.** Zum Beispiel `on` gegen `active`, eine andere VLAN-Liste oder andere Speed- und Duplex-Werte. Der Switch nimmt den Port dann nicht ins Bündel auf.

</details>

3. Wozu `switchport nonegotiate`?
<details><summary>Antwort</summary>

**Es schaltet DTP ab, also das Aushandeln eines Trunks.** So kann ein angeschlossenes Gerät keinen Trunk erzwingen. Voraussetzung: Der Port steht fest auf `access` oder `trunk`.

</details>

## Prüfungsbezug
- LACP: active/active und active/passive bilden einen Channel, passive/passive nicht.
- PAgP: desirable/desirable und desirable/auto bilden einen Channel.
- `on` verhandelt nichts und passt nur zu `on`.
- Speed, Duplex, Trunk-Modus, Native VLAN und erlaubte VLANs müssen auf allen Mitgliedsports gleich sein.
- DTP: auto/auto ergibt Access, desirable baut einen Trunk auf, `switchport nonegotiate` schaltet DTP ab.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/05-VLAN-Trunk-EtherChannel/`](../../CML-Labs/05-VLAN-Trunk-EtherChannel/).
