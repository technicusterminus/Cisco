# Lab 31 – MST vertieft: Regionen, Instanzen, Pfadkosten und PVST-Interop

**Dauer:** 100 min · **Niveau:** schwer · **Nodes:** 3× iosv, 5× iosvl2

Vier Switches bilden eine MST-Region, ein Legacy-Switch bleibt bei Rapid-PVST. Du planst die Region, legst die Root je Instanz fest, steuerst Pfade pro Instanz und siehst, wie MST an der Regionsgrenze mit PVST+ zusammenarbeitet – und wann nicht.

Voraussetzung: Lab 06 (STP-Grundlagen, Schutzfunktionen). Trunks und VLANs sind in diesem Lab schon gebaut, es geht nur um Spanning Tree.

**Lernziele:** Nach diesem Lab kannst du …

- eine MST-Region so planen und einführen, dass sie nicht auseinanderfällt,
- Root, Pfadkosten und Port-Prioritäten pro Instanz unabhängig voneinander steuern,
- erklären, was die IST (Instanz 0) und die CIST sind und welche VLANs dort landen,
- Boundary-Ports erkennen und die Regeln der PVST-Simulation anwenden.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.1.c` | RSTP, MST und Schutzfunktionen | 65 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
        DS1 ──────────── DS2 ──────────┐ Gi0/3
         │  ╲          ╱  │            │
         │    ╲      ╱    │            │
         │      ╲  ╱      │            │
         │      ╱  ╲      │            │
         │    ╱      ╲    │            │
        AS1            AS2 ────────── LEG1      Rapid-PVST (Legacy)
         │              │   Gi0/2      │
        H1 (VLAN 10)   H2 (VLAN 20)   H3 (VLAN 10)

        DS1, DS2, AS1, AS2: Region CAMPUS (nach Teil A)
```

| Link | Ports |
|---|---|
| DS1–DS2 | Gi0/0 ↔ Gi0/0 |
| DS1–AS1 | Gi0/1 ↔ Gi0/0 |
| DS1–AS2 | Gi0/2 ↔ Gi0/0 |
| DS2–AS1 | Gi0/1 ↔ Gi0/1 |
| DS2–AS2 | Gi0/2 ↔ Gi0/1 |
| AS2–LEG1 | Gi0/2 ↔ Gi0/0 |
| DS2–LEG1 | Gi0/3 ↔ Gi0/1 |
| H1 / H2 / H3 | AS1 Gi1/0 (VLAN 10) / AS2 Gi1/0 (VLAN 20) / LEG1 Gi1/0 (VLAN 10) |

Alle Links zwischen Switches sind 802.1Q-Trunks (alle VLANs erlaubt, Native VLAN 1). VLANs 10 (USERS), 20 (SERVERS) und 30 (VOICE) sind überall angelegt. DS1 routet zwischen den VLANs (SVIs .1). Hosts: H1 10.10.10.11, H2 10.10.20.12, H3 10.10.10.13 (/24). Alle Switches starten mit Rapid-PVST.

**Zielbild:**

| Instanz | VLANs | Root | Backup-Root |
|---|---|---|---|
| 0 (IST) | alle nicht zugeordneten, u. a. 1 | DS1 (4096) | DS2 (8192) |
| 1 | 10, 30 | DS1 (4096) | DS2 (8192) |
| 2 | 20 | DS2 (4096) | DS1 (8192) |

Region: Name `CAMPUS`, Revision 1. LEG1 bleibt bei Rapid-PVST mit Standardprioritäten.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Ausgangslage lesen.** Auf DS1 `show spanning-tree summary` und `show spanning-tree root`.
   - **Prüfen:** H1 pingt H2 und H3. Wie viele Spanning-Tree-Instanzen laufen auf jedem Switch?
   - **Denkfrage:** Wie viele Instanzen bräuchte Rapid-PVST bei 300 VLANs, und warum ist das ein Problem?
2. **Region konfigurieren, noch nicht aktivieren.** Lege auf DS1, DS2, AS1 und AS2 die Region an: `spanning-tree mst configuration`, `name CAMPUS`, `revision 1`, `instance 1 vlan 10,30`, `instance 2 vlan 20`. Schalte den Modus noch **nicht** um.
   - **Prüfen:** `show spanning-tree mst configuration digest` zeigt auf allen vier denselben Digest.
   - **Denkfrage:** Warum erst die Region überall gleich anlegen und dann umschalten?
3. **Auf MST umschalten.** Setze auf den vier Switches `spanning-tree mode mst`. LEG1 bleibt bei Rapid-PVST.
   - **Prüfen:** `show spanning-tree mst` auf AS1: keine Boundary-Ports zu DS1 und DS2. Auf AS2 Gi0/2 und DS2 Gi0/3 steht in der Spalte Type ein Boundary-Hinweis (`Bound(PVST)`).
4. **Root je Instanz.** Setze die Prioritäten nach dem Zielbild: DS1 `spanning-tree mst 0-1 priority 4096` und `spanning-tree mst 2 priority 8192`, DS2 umgekehrt.
   - **Prüfen:** `show spanning-tree mst 1` auf AS1: Root ist DS1, Root-Port Gi0/0. `show spanning-tree mst 2` auf AS1: Root ist DS2, Root-Port Gi0/1.
   - **Denkfrage:** Warum gibt es in MST keine Extended System ID pro VLAN in der Priorität, sondern pro Instanz?
5. **Pfade pro Instanz steuern.** Setze auf AS1 an Gi0/1 `spanning-tree mst 2 cost 200000`.
   - **Prüfen:** `show spanning-tree mst 2` auf AS1: Der Root-Port wechselt auf Gi0/0 (über DS1). `show spanning-tree mst 1` bleibt unverändert.
   - Nimm die Änderung danach mit `no spanning-tree mst 2 cost` zurück.
   - **Denkfrage:** Welche Pfadkosten verwendet MST für 1 Gbit/s, und warum unterscheidet sich das von Rapid-PVST mit Standardeinstellung?
6. **IST beobachten.** Lege auf allen fünf Switches VLAN 40 an, ohne es einer Instanz zuzuordnen.
   - **Prüfen:** `show spanning-tree mst 0` zeigt VLAN 40 (und VLAN 1) in Instanz 0.
   - **Denkfrage:** Warum ordnen viele Designs gleich ganze VLAN-Bereiche zu (z. B. `instance 1 vlan 10,30,100-199`), auch wenn es die VLANs noch nicht gibt?
7. **Grenze zur Legacy-Welt.** Auf LEG1 `show spanning-tree vlan 10` und `show spanning-tree vlan 20`.
   - **Prüfen:** LEG1 sieht in beiden VLANs **DS1** als Root, und einer seiner beiden Uplinks ist Alternate – in allen VLANs derselbe.
   - **Denkfrage:** DS2 ist Root für Instanz 2 (VLAN 20). Warum sieht LEG1 trotzdem DS1 als Root für VLAN 20?
8. **PVST-Simulation verletzen (Experiment).** Setze auf LEG1 `spanning-tree vlan 20 priority 0`.
   - **Prüfen:** AS2 und DS2 melden `%SPANTREE-2-PVSTSIM_FAIL`. `show spanning-tree inconsistentports` zeigt die Boundary-Ports als *PVST Sim. Inconsistent*. H3 ist nicht mehr erreichbar.
   - Nimm die Änderung mit `no spanning-tree vlan 20 priority` zurück. Die Ports erholen sich von selbst.
   - **Denkfrage:** Welche Regel hat LEG1 verletzt?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Rapid-PVST rechnet für jedes VLAN eine eigene Instanz mit eigenen BPDUs. Bei 300 VLANs sind das 300 Topologien, die CPU und BPDU-Last steigen, obwohl es meist nur zwei oder drei sinnvolle Weg-Varianten gibt. MST fasst VLANs mit gleichem Weg zu einer Instanz zusammen.
- **Zu 2:** Aus Name, Revision und VLAN-Zuordnung bildet MST einen Digest. Switches erkennen sich nur bei gleichem Digest als eine Region. Schaltest du um, während die Zuordnung noch nicht überall gleich ist, entstehen kurz mehrere Regionen mit Boundary-Ports und zusätzlicher Konvergenz.
- **Zu 4:** In MST gibt es pro Instanz eine Topologie. Die Extended System ID ist deshalb die Instanznummer (Instanz 2 mit Priorität 4096 meldet 4098). Prioritäten gehen weiterhin in Schritten von 4096.
- **Zu 5:** MST nutzt immer die langen Pfadkosten (802.1t): 1 Gbit/s = 20 000. Rapid-PVST nutzt standardmäßig die kurzen Kosten (1 Gbit/s = 4), bis `spanning-tree pathcost method long` gesetzt ist. Kosten pro Instanz (`spanning-tree mst <n> cost`) wirken nur auf diese Instanz.
- **Zu 6:** Jede Änderung der Zuordnung ändert den Digest. Bis alle Switches angepasst sind, zerfällt die Region. Wer Bereiche vorab zuordnet, legt neue VLANs später nur an, ohne die Region anzufassen.
- **Zu 7:** Nach außen wirkt eine MST-Region wie ein einziger großer Switch. An der Grenze gilt nur die CIST, also die Sicht von Instanz 0 mit DS1 als Root. Die Boundary-Ports senden diese Information als PVST+-BPDUs in jedes VLAN (PVST-Simulation). Die interne Lastverteilung nach Instanzen sieht LEG1 nicht.
- **Zu 8:** Liegt die CIST-Root in der MST-Region, müssen alle PVST+-BPDUs, die an der Grenze ankommen, schlechter sein als die CIST-Root. LEG1 meldet für VLAN 20 die Bridge-ID 0 + 20, besser als DS1 (4096). Die Region kann einem einzelnen VLAN keine andere Root geben, also blockiert sie den Boundary-Port.

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **4 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen, dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

**Ticket 1:** Auf AS2 zeigt `show spanning-tree mst` Boundary-Ports zu DS1 und DS2, und AS2 hält sich für Instanz 2 selbst für die Root.

**Ticket 2:** Die Lastverteilung fehlt: Auch VLAN 20 läuft über DS1, `show spanning-tree mst 2` zeigt DS1 als Root.

**Ticket 3:** VLAN 10 von H1 läuft über DS2 zur Root DS1, obwohl AS1 einen direkten Uplink zu DS1 hat. Instanz 2 ist unauffällig.

**Ticket 4:** H3 erreicht weder sein Gateway noch H1. AS2 und DS2 haben Ports im Zustand `BKN*`.

## Verifikation
```
show spanning-tree mst configuration
show spanning-tree mst configuration digest
show spanning-tree mst
show spanning-tree mst 1
show spanning-tree mst 2 detail
show spanning-tree mst interface GigabitEthernet0/2
show spanning-tree inconsistentports
show spanning-tree vlan 10        (auf LEG1)
```

| Befehl | Das solltest du sehen |
|---|---|
| `show spanning-tree mst configuration digest` | auf DS1, DS2, AS1, AS2 derselbe Digest |
| `show spanning-tree mst` | DS1 Root für Instanz 0 und 1, DS2 Root für Instanz 2 |
| `show spanning-tree mst 1` auf AS1 | Root-Port Gi0/0, Gi0/1 Alternate |
| `show spanning-tree mst 2` auf AS1 | Root-Port Gi0/1, Gi0/0 Alternate |
| `show spanning-tree mst` auf AS2 | nur Gi0/2 (zu LEG1) als Boundary-Port |
| `show spanning-tree inconsistentports` | leer |
| `show spanning-tree vlan 10` auf LEG1 | Root ist DS1, ein Uplink Alternate |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Zwei Switches haben denselben Region-Namen und dieselbe Revision, aber VLAN 30 ist auf einem Switch Instanz 1, auf dem anderen nicht zugeordnet. Gehören sie zur selben Region?
<details><summary>Antwort</summary>

**Nein.** Die VLAN-Zuordnung geht in den Digest ein. Ein Unterschied in nur einem VLAN reicht für zwei Regionen.

</details>

2. Was ist der Unterschied zwischen IST und CIST?
<details><summary>Antwort</summary>

**Die IST ist Instanz 0 innerhalb einer Region, die CIST spannt den Baum über alle Regionen und Nicht-MST-Bridges.** Innerhalb der Region ist die IST der Teil der CIST. Zwischen Regionen und zu RSTP/PVST+ gilt nur die CIST.

</details>

3. Lohnt sich in diesem Netz eine dritte Instanz für VLAN 30?
<details><summary>Antwort</summary>

**Nein.** Mit zwei Distribution-Switches gibt es zwei sinnvolle Root-Platzierungen und damit zwei Wege. Eine dritte Instanz mit derselben Root wie Instanz 1 kostet BPDU-Last und Konfiguration, ohne einen anderen Weg zu bringen. Instanzen plant man nach Wegen, nicht nach VLANs.

</details>

4. Die CIST-Root liegt **außerhalb** der Region, in der PVST+-Welt. Was muss dann für die PVST+-Prioritäten gelten?
<details><summary>Antwort</summary>

**Die Root für VLAN 1 außerhalb muss gleichzeitig Root aller anderen VLANs sein, ihre Priorität in den anderen VLANs muss also mindestens so gut sein wie in VLAN 1.** Die Region folgt an der Grenze nur einer Root. Sonst meldet die Grenze ebenfalls PVST Sim. Inconsistent. Empfehlung: die CIST-Root in die MST-Region legen.

</details>

5. Wo würdest du Root Guard in diesem Netz setzen?
<details><summary>Antwort</summary>

**An den Boundary-Ports Richtung LEG1 (AS2 Gi0/2, DS2 Gi0/3) und an den Distribution-Ports Richtung Access.** So kann weder LEG1 noch ein Access-Switch die Root an sich ziehen. Ein Port mit superiorer BPDU geht dann auf root-inconsistent statt die Topologie umzubauen.

</details>

## Prüfungsbezug
- Eine Region = gleicher Name, gleiche Revision, gleiche VLAN-Zuordnung (Digest).
- Instanz 0 (IST) trägt alle nicht zugeordneten VLANs und als einzige BPDUs nach außen.
- MST nutzt lange Pfadkosten (1 Gbit/s = 20 000); Priorität, Kosten und Port-Priorität gibt es pro Instanz.
- An der Grenze zu PVST+ gilt nur die CIST; PVST-Simulation verlangt eine konsistente Root für alle VLANs.
- Befehle: `spanning-tree mst configuration`, `spanning-tree mst <n> priority`, `spanning-tree mst <n> cost`, `show spanning-tree mst configuration digest`, `show spanning-tree inconsistentports`.

## Hinweis zur Plattform

Die Topologien sind als CML-Import geschrieben (IOSv und IOSvL2) und auf gültiges YAML sowie konsistente Links geprüft, aber nicht in einer laufenden CML-Instanz durchgespielt. Meldungstexte wie `PVSTSIM_FAIL` und die Type-Spalte (`Bound(PVST)`, `PVST_Inc`) können je nach IOSvL2-Version leicht abweichen. Das Verhalten (Port blockiert, `show spanning-tree inconsistentports`) ist dasselbe.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A, ohne die Basis aus der Topologie und ohne die zurückgenommenen Experimente (Schritte 5 und 8)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
