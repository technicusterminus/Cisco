# Lab 18 – Flexible NetFlow, SPAN und RSPAN

**Plattform:** EVE-NG · **Dauer:** 75 min · **Niveau:** mittel

Verkehr sichtbar machen: Flexible NetFlow auf einem Router (Record, Exporter, Monitor), lokales SPAN und RSPAN über einen Trunk zwischen zwei Switches. ERSPAN wird als Konfigurationsübung ohne CML-Test behandelt.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::4.2` | Flexible NetFlow | 24 |
| `Ziel::4.3` | SPAN, RSPAN und ERSPAN | 22 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| SW1 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| SW2 | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| R1 | Cisco vIOS Router |  | 512 |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| SRV | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| ANA1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| ANA2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **4.5 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **2.0 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| SW1 | Gi0/0 | R1 | Gi0/0 |
| R1 | Gi0/1 | SRV | Gi0/0 |
| SW1 | Gi0/1 | SW2 | Gi0/0 |
| SW1 | Gi1/0 | H1 | Gi0/0 |
| SW1 | Gi1/1 | H2 | Gi0/0 |
| SW1 | Gi1/2 | ANA1 | Gi0/0 |
| SW2 | Gi1/1 | ANA2 | Gi0/0 |


### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte mit `no ip routing` (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ping <ziel> -c 100` statt `ping … repeat 100`, `show ip` statt `show ip interface brief`, `trace <ziel>` statt `traceroute`. Was ein VPCS nicht kann (Telnet/SSH-Client, Multicast-Beitritt, IP SLA), machst du mit vIOS-Hosts.

## Topologie

```
 H1 ─┐                                        ┌─ ANA2 (RSPAN-Ziel)
     SW1 ── Gi0/0 ── R1 ── Gi0/1 ── SRV        SW2
 H2 ─┘      │ Gi0/1 ────────────────────────── Gi0/0
            └ Gi1/2 ── ANA1 (lokales SPAN-Ziel)
```

| Gerät | Interface | Adresse |
|---|---|---|
| R1 | Gi0/0 / Gi0/1 | 10.10.10.1/24 / 10.20.20.1/24 |
| H1 / H2 | Gi0/0 | 10.10.10.11 / 10.10.10.12 |
| SRV | Gi0/0 | 10.20.20.10 |
| ANA1 / ANA2 | Gi0/0 | Sniffer-Hosts (passiv) |

SW1 Port-Belegung: Gi0/0 → R1 (Access VLAN 10), Gi0/1 → SW2 (Trunk), Gi1/0 → H1, Gi1/1 → H2, Gi1/2 → ANA1. SW2: Gi0/0 → SW1 (Trunk), Gi1/1 → ANA2.

## Teil A – Bauen

**Teil 1 – Flexible NetFlow auf R1**

1. **Record.** `flow record REC`: `match ipv4 source address`, `match ipv4 destination address`, `match ipv4 protocol`, `match transport source-port`, `match transport destination-port`, `collect counter bytes`, `collect counter packets`. Was ist ein Flow (Key-Felder, Siebener-Tupel)?
2. **Exporter.** `flow exporter EXP`: `destination 10.20.20.10`, `transport udp 2055`, `source Gi0/1`, `export-protocol netflow-v9`. Wozu Templates in v9/IPFIX?
3. **Monitor und Anwendung.** `flow monitor MON` (record + exporter), `interface Gi0/0` → `ip flow monitor MON input` (und `output`). Erzeuge Traffic (Ping H1 → SRV, `telnet`) und lies `show flow monitor MON cache`.
4. **Vergleich.** Traditional NetFlow (`ip flow ingress`) vs. Flexible NetFlow (frei definierbare Records), NetFlow vs. sFlow (Sampling) vs. IPFIX (IETF).

**Teil 2 – Lokales SPAN**

5. Auf SW1 `monitor session 1 source interface Gi1/0 both`, `destination interface Gi1/2`. Prüfe `show monitor session 1`. Was passiert mit dem Ziel-Port (nimmt keinen normalen Verkehr mehr, kein STP)?

**Teil 3 – RSPAN**

6. VLAN 999 als `remote-span` auf **beiden** Switches, im Trunk erlaubt. SW1: `monitor session 2 source interface Gi1/1 both`, `destination remote vlan 999`. SW2: `monitor session 2 source remote vlan 999`, `destination interface Gi1/1`. Prüfe die Sicht auf ANA2.
7. **Konzept.** Vergleiche SPAN, RSPAN (Layer 2, ein VLAN), ERSPAN (GRE, geroutet). Gib die ERSPAN-Konfiguration (IOS-XE) an: `monitor session 3 type erspan-source / source interface Gi1 both / destination / erspan-id 10 / ip address 10.1.1.1 / origin ip address 10.1.1.2`.

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** `show flow monitor MON cache` ist leer, obwohl Verkehr läuft; der Exporter zählt keine Pakete.

**Ticket 2:** Im Flow-Cache stehen nur noch Einträge je Host-Paar und Protokoll, Anwendungen (Ports) lassen sich nicht unterscheiden.

**Ticket 3:** ANA2 sieht nichts vom RSPAN-Verkehr von H2, lokales SPAN auf SW1 funktioniert.

**Ticket 4:** ANA1 sieht H1-Verkehr nicht, `show monitor session 1` zeigt ein anderes Ziel.

## Verifikation

```
show flow monitor MON cache
show flow exporter EXP statistics
show monitor session all
show vlan remote-span
```
Erwartet: Cache mit Flows H1 → SRV, Exporter-Statistik zählt Flow-Records, ANA1 sieht H1-Verkehr, ANA2 sieht H2-Verkehr per RSPAN.

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Welche zwei Felder sind in NetFlow zwingend Key-Felder und welche sind Non-Key?
<details><summary>Antwort</summary>

Key: z. B. Quell-/Ziel-IP, Protokoll, Ports (bestimmen den Flow). Non-Key (`collect`): Zähler wie Bytes/Pakete, Zeitstempel, Flags.

</details>

2. RSPAN-Session steht, aber ANA2 sieht nichts. Typische Ursachen?
<details><summary>Antwort</summary>

Das Remote-VLAN fehlt als `remote-span`, ist im Trunk nicht erlaubt, oder Quell-/Ziel-Session ist falsch gesetzt (`source remote vlan` fehlt auf dem Ziel-Switch).

</details>

3. Warum kann man das Gerät bei hoher Last im SPAN-Betrieb falsch interpretieren?
<details><summary>Antwort</summary>

SPAN-Kopien haben niedrigere Priorität; bei Überlast werden Pakete verworfen. NetFlow liefert Statistik, kein vollständiges Abbild.

</details>

## Prüfungsbezug

Flow = Paketfolge mit gleichen Key-Feldern. Flexible NetFlow nutzt Record/Exporter/Monitor. NetFlow v9 und IPFIX sind template-basiert. SPAN: Quelle(Ports/VLANs), Ziel-Port; RSPAN über spezielles Remote-VLAN; ERSPAN kapselt per GRE zu einem IP-Ziel. Ein SPAN-Ziel-Port nimmt keinen normalen Verkehr entgegen.

## Lösungen

- `solutions/<Node>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)

Die gleiche Topologie gibt es als CML-Import: [`../../CML-Labs/18-NetFlow-SPAN/`](../../CML-Labs/18-NetFlow-SPAN/).
