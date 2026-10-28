# Abgleich mit echtem ACI

Datacenter Prep bildet das Verhalten eines APIC nach, ist aber nie gegen einen echten APIC geprüft worden. Ein grünes Ergebnis im Simulator heißt deshalb nur: Es stimmt mit dem Modell überein. Diese Seite beschreibt, wie du das Modell gegen echtes ACI prüfst. Sie beginnt mit dem automatischen Teil und listet danach alles, was nur von Hand geht, nach Risiko sortiert.

## 1. Automatisch: `werkzeuge/abgleich.py`

Das Skript schickt dieselben REST-Abfragen an Datacenter Prep und an einen echten APIC und vergleicht die Antworten. Es braucht nur Python.

```sh
python3 start.py --no-browser &          # Datacenter Prep auf localhost:8080

# nur lesen, ändert nichts am APIC:
python3 werkzeuge/abgleich.py --apic https://sandboxapicdc.cisco.com --apic-user admin --insecure

# mit Test-Tenant (wird angelegt, geprüft und wieder gelöscht), nur Lab oder Sandbox:
python3 werkzeuge/abgleich.py --apic https://apic.lab.local --apic-user admin --insecure --write
```

Als echter APIC eignen sich die kostenlose **Cisco DevNet Sandbox** (*ACI Simulator Always-On* oder eine reservierbare ACI-Sandbox, Zugangsdaten stehen auf der Sandbox-Seite) oder ein **ACI-Simulator-Image** im eigenen Lab. Die Sandbox ist selbst ein APIC-Simulator ohne Datenebene. Für Defaults, Fehlercodes, Relationen und Faults ist sie trotzdem maßgeblich.

| Bereich | Was geprüft wird |
|---|---|
| Login | Felder der `aaaLogin`-Antwort |
| Klassen | 32 Klassen: gibt es sie, und welche Attribute hat ein Objekt |
| Fehler (lesend) | unbekannte Klasse, fehlender DN, kaputter Filter, falscher Parameter, ohne Login |
| Abfragen | `query-target`, `target-subtree-class`, `eq`, `wcard`, `rsp-subtree`, `count`, `page-size`, `order-by` |
| Defaults (`--write`) | alle Attributwerte von Tenant, VRF, BD, Subnet, AP, EPG, Filter, Entry, Contract, Subject, Static Port |
| Auto-Objekte (`--write`) | welche Kinder der APIC von selbst anlegt (z. B. `vzAny`, `fvRsCtx`) |
| Relationen (`--write`) | `state`, `tCl` und `tDn` bei vorhandenem Ziel, fehlendem Ziel und leerem Namen (Auflösung nach `common`) |
| Faults (`--write`) | Fault-Codes im Test-Tenant (Static Port ohne Domain, BD fehlt) |
| Fehler (schreibend) | ungültiger Enum, ungültige IP, unbekannte Klasse, unbekanntes Attribut, falscher Eltern-Knoten, Naming, fehlende Eltern, Atomarität, DELETE ins Leere |

Ergebnis: eine Tabelle auf der Konsole, `abgleich-bericht.md` zum Lesen und `abgleich-rohdaten.json` mit beiden Antworten. Jede Prüfung landet in einer von drei Gruppen:

- **gleich**
- **unvollständig**: Der APIC hat Attribute, die der Simulator nicht kennt. Das ist meist harmlos, zeigt aber Lücken.
- **abweichend**: Werte, Codes oder Struktur unterscheiden sich. Das sind die Fehler im Modell.

Den Bericht kannst du als Issue anhängen. Aus ihm lässt sich Datacenter Prep gezielt korrigieren.

Erwartete Unterschiede, die kein Fehler sind:

- Ohne `--strict` nimmt der Simulator unbekannte Attribute an, damit Ansible und Terraform durchlaufen. Der APIC lehnt sie mit `121` ab.
- `tn-common` und ein neuer Tenant haben auf dem APIC mehr automatische Kinder (Monitoring- und Service-Container), die der Simulator weglässt.
- Ob Klassen wie `lldpAdjEp` oder `fvCEp` Instanzen haben, hängt von der Fabric ab. Ohne Instanz wird nur geprüft, ob es die Klasse gibt.

## 2. Von Hand: Prüfliste nach Risiko

**Risiko** bedeutet hier: Wenn der Simulator an dieser Stelle falsch liegt, lernst du etwas Falsches, das in einem echten Design Ausfälle verursacht. Die Spalte *Erwartetes Verhalten* beschreibt, wie es laut Cisco-Dokumentation sein soll und wie es der Simulator nachbilden soll. Prüfe jeden Punkt in beiden Umgebungen. Hast du einen Punkt am echten ACI geprüft, trägst du ihn in die Spalte *geprüft* ein (Datum, Version) und meldest Abweichungen.

### Hoch: Datenebene und Policy-Entscheidungen

| # | Erwartetes Verhalten | So prüfst du es am echten ACI | geprüft |
|---|---|---|---|
| H1 | Zwischen EPGs ohne Contract fließt nichts. Innerhalb einer EPG fließt alles (ohne Intra-EPG Isolation). | zwei Hosts in verschiedenen EPGs, Ping; `show zoning-rule` auf dem Leaf | |
| H2 | Ein Contract mit *Apply both directions* und *Reverse filter ports* erlaubt die Antwort. Ohne *Reverse* wird die Antwort verworfen. | TCP 80 mit beiden Optionen testen, `show zoning-rule` vergleichen | |
| H3 | vzAny als Consumer und Provider erlaubt alles im VRF. Ein Deny in einer spezifischeren Regel gewinnt gegen ein Permit über vzAny (Priorität nach Spezifität). | vzAny-Contract plus Taboo oder Deny-Filter, Reihenfolge in `show zoning-rule` | |
| H4 | *Preferred Group*: Mitglieder untereinander ohne Contract, Nicht-Mitglieder brauchen weiter einen Contract. | zwei Mitglieds-EPGs und eine Nicht-Mitglieds-EPG | |
| H5 | *Policy Enforcement unenforced* am VRF erlaubt alles. | VRF umstellen, Ping zwischen EPGs | |
| H6 | L3Out: Die externe EPG klassifiziert per Subnet mit *External Subnets for External EPG*. 0.0.0.0/0 trifft alles. Ein spezifischeres Subnet gewinnt (Longest Prefix Match bei der Klassifizierung). | zwei externe EPGs mit /0 und /24, Verkehr von einer Adresse im /24 | |
| H7 | Shared L3Out und VRF-Leaking: Das Subnet muss in der BD oder unter der EPG *Shared between VRFs* sein, und der Contract-Scope muss *tenant* oder *global* sein. | Leaking zwischen zwei VRFs, `show ip route vrf` auf dem Leaf | |
| H8 | Bridge-Domain-Optionen: *Unicast Routing* aus → kein Gateway, *L2 Unknown Unicast* Flood oder Proxy, *ARP Flooding*, *Limit IP Learning to Subnet*. | jede Option einzeln, Endpoint-Lernen mit `show endpoint` | |
| H9 | Endpoint-Lernen und Move-Erkennung (MAC, IP, GARP). Ein Endpoint auf einer falschen VLAN-Encap wird nicht gelernt (F0467). | Host mit falscher Encap anschließen | |
| H10 | PBR-Service-Graph: Umleitung auf die Firewall nur für passende Filter, Rückweg symmetrisch. | PBR mit einem Filter, Traffic mit anderem Port | |

### Mittel: Deployment und Faults

| # | Erwartetes Verhalten | So prüfst du es am echten ACI | geprüft |
|---|---|---|---|
| M1 | Eine EPG wird auf einen Leaf erst deployt, wenn es einen Static Port oder eine VMM-Domain-Nutzung gibt. Bei *Resolution/Deployment Immediacy On Demand* passiert das erst mit einem gelernten Endpoint. | `show vlan extended` vor und nach dem Host | |
| M2 | Die Kette VLAN-Pool → Domain → AEP → Interface Policy Group → Interface Profile → Switch Profile muss vollständig sein, sonst gibt es einen Fault (meist F0467) und die EPG wird nicht deployt. | ein Glied weglassen, Fault-Code notieren | |
| M3 | VLAN-Überlappung zwischen Pools derselben AEP erzeugt einen Fault und unvorhersehbares Verhalten. | zwei Domains mit überlappendem Pool an einer AEP | |
| M4 | vPC: Beide Leafs brauchen eine vPC Explicit Protection Group. Ein Port-Channel ohne LACP-Partner bleibt down (suspended). | Server mit und ohne LACP | |
| M5 | OSPF im L3Out: MTU-Mismatch → EXSTART, Area-Typ-Mismatch → keine Adjacency. | MTU einseitig ändern | |
| M6 | BGP im L3Out: Peer braucht Loopback oder Interface als Quelle passend zur Konfiguration, eBGP-Multihop für Loopback-Peering. | Peering über Loopback ohne Multihop | |
| M7 | Fault-Lebenszyklus: *soaking* → *raised* → *retaining*, Dauer und Severity. | Fault auslösen und beheben, Zeiten notieren | |
| M8 | Config Rollback setzt nur die Policy zurück, nicht die gelernten Endpoints. | Snapshot, Änderung, Rollback | |
| M9 | Multi-Pod: Discovery über IPN mit DHCP Relay, OSPF zum IPN, MTU 9150 im IPN nötig. | IPN mit 1500 Byte MTU | |
| M10 | Remote Leaf: Erreichbarkeit der APIC-TEPs und der Spine-Proxy-Adressen über das WAN. | ein Präfix nicht routen | |

### Niedrig: Darstellung und Bedienung

| # | Erwartetes Verhalten | So prüfst du es am echten ACI | geprüft |
|---|---|---|---|
| N1 | Menüstruktur, Namen der Wizards und Felder | Seite für Seite vergleichen | |
| N2 | Ausgabeformat der CLI (`show zoning-rule`, `show endpoint`, `show vpc`) | Ausgaben nebeneinanderlegen | |
| N3 | Health Score (Berechnung ist vereinfacht) | Health eines Tenants mit und ohne Faults | |
| N4 | Upgrade-Ablauf (Firmware-Gruppen, Reihenfolge) | Release Notes und Upgrade-Guide der Version | |
| N5 | Kapazitätsgrenzen im Capacity Dashboard (fest für N9K-C93180YC-FX) | Verified Scalability Guide der Version | |

## 3. Abweichungen melden

Am nützlichsten ist eine Meldung mit:

- APIC-Version
- Prüfnummer (z. B. `H3`) oder Bericht von `abgleich.py`
- erwartetem Verhalten (echtes ACI) und Verhalten im Simulator
- falls vorhanden, CLI-Ausgabe oder JSON

Jede bestätigte Abweichung bekommt einen Test in `tests/`, damit sie nicht zurückkommt.
