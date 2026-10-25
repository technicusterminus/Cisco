# Lab E5 – DHCP-Server und DHCP-Relay über mehrere Router

**Plattform:** EVE-NG · **Dauer:** 75 min · **Niveau:** mittel

Ein zentraler DHCP-Server (R2) versorgt zwei LANs hinter zwei Relay-Routern. Du baust Pools, Ausschlüsse und `ip helper-address` auf, verfolgst den Ablauf mit `debug ip dhcp server packet` und lernst, wie giaddr den Pool bestimmt, warum der Server eine Route zum Relay braucht und was Option 82 ändert.

**Lernziele:** Nach diesem Lab kannst du …

- Einen DHCP-Server mit Pools, ausgeschlossenen Adressen und Optionen konfigurieren.
- Auf einem Router `ip helper-address` setzen und die Rolle von giaddr bei der Pool-Auswahl erklären.
- Den DHCP-Ablauf (Discover, Offer, Request, Ack) mit Debug und Bindings nachvollziehen.
- Typische Fehler (Relay fehlt, falscher Server, falscher Pool, Ausschluss, fehlende Rückroute) am Symptom erkennen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::4.4` | DHCP: Fehlersuche | 20 |

**So arbeitest du:** Importiere [`EVE-Import.zip`](EVE-Import.zip) in EVE-NG (siehe [Import in EVE-NG](../README.md#import-in-eve-ng)). Das Lab *Bauen* ist Teil A, das Lab *Reparieren* ist Teil B, Teil C = Üben. Ohne Import liegen die Konfigurationen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Manuell aufbauen](../README.md#manuell-aufbauen-ohne-import)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| R1 | Cisco vIOS Router |  | 512 |
| R2 | Cisco vIOS Router |  | 512 |
| R3 | Cisco vIOS Router |  | 512 |
| H2 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.6 GB RAM**. Mit VPCS statt vIOS-Hosts: ca. **1.5 GB**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| H1 | Gi0/0 | R1 | Gi0/0 |
| R1 | Gi0/1 | R2 | Gi0/0 |
| R2 | Gi0/1 | R3 | Gi0/0 |
| R3 | Gi0/1 | H2 | Gi0/0 |

### Hosts: vIOS oder VPCS

Die Hosts sind in den Aufgaben IOS-Geräte (Dateien `build/<Host>.cfg`). Willst du RAM sparen, nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. Dann gelten VPCS-Befehle: `ip dhcp` startet die Anfrage (`ip dhcp -r` gibt die Adresse frei), `show ip` zeigt das Ergebnis, `trace <ziel>` statt `traceroute`.

## Topologie

```
   H1 ── R1 ── R2 (DHCP-Server) ── R3 ── H2
   LAN1       10.0.12.0/30   10.0.23.0/30      LAN2
 10.1.1.0/24                                 10.1.2.0/24
```

| Link | Netz |
|---|---|
| H1 – R1 Gi0/0 | 10.1.1.0/24 (R1 .1, Clients per DHCP) |
| R1 Gi0/1 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R2 Gi0/1 – R3 Gi0/0 | 10.0.23.0/30 (R2 .1, R3 .2) |
| R3 Gi0/1 – H2 | 10.1.2.0/24 (R3 .1, Clients per DHCP) |

R2 ist der DHCP-Server für beide LANs, R1 und R3 sind Relay-Router. R1 und R3 haben eine Default-Route zu R2, R2 hat statische Routen zu den beiden LANs. H1 und H2 sind IOS-Geräte mit `ip address dhcp` am Gi0/0 und noch ohne Adresse. Ziel: H1 bekommt eine Adresse aus 10.1.1.0/24, H2 aus 10.1.2.0/24, jeweils mit Gateway, DNS-Server und Domäne.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Ausgangslage prüfen.** Auf H1: `show ip interface brief`. Auf R2: `ping 10.1.1.1` und `ping 10.1.2.1`.
   - **Prüfen:** H1 hat keine Adresse (unassigned). Die Pings von R2 zu den Relay-Adressen gehen durch.
   - **Denkfrage:** Warum kann H1 ohne Relay nie einen Server in einem anderen Netz erreichen?
2. **Server konfigurieren.** Auf R2: `ip dhcp excluded-address 10.1.1.1 10.1.1.10` (und für 10.1.2.1–10.1.2.10), dann die Pools `LAN1` und `LAN2` mit `network`, `default-router`, `dns-server 192.0.2.53`, `domain-name lab.example` und `lease 0 8`.
   - **Prüfen:** `show ip dhcp pool` listet beide Pools mit Netz und 0 Leases.
   - **Denkfrage:** Warum schließt man Adressen aus, statt den Pool kleiner zu machen?
3. **Relay auf R1.** Unter Gi0/0 (LAN-Seite) von R1: `ip helper-address 10.0.12.2`. Auf H1: `shutdown`, `no shutdown`.
   - **Prüfen:** H1 bekommt 10.1.1.11 mit Gateway 10.1.1.1. `show ip dhcp binding` auf R2 listet den Eintrag.
   - **Denkfrage:** Welche Adresse trägt R1 als giaddr in das weitergeleitete Paket ein, und was macht R2 damit?
4. **Relay auf R3.** Unter Gi0/1 von R3: `ip helper-address 10.0.23.1`. Auf H2 das Interface aus- und einschalten.
   - **Prüfen:** H2 bekommt 10.1.2.11 mit Gateway 10.1.2.1.
   - **Denkfrage:** Welche Adressen von R2 könntest du auf R3 als Helper eintragen, und welche ist die sauberste Wahl?
5. **Ablauf beobachten.** Auf R2: `debug ip dhcp server packet`. Auf H1 das Interface aus- und einschalten.
   - **Prüfen:** Du siehst DHCPDISCOVER, DHCPOFFER, DHCPREQUEST und DHCPACK mit giaddr 10.1.1.1. Schalte das Debugging danach mit `undebug all` aus.
   - **Denkfrage:** Welche der vier Nachrichten sind Broadcasts, und wer macht aus dem Broadcast einen Unicast?
6. **Option 82.** Setze testweise auf R1 unter Gi0/0 `ip dhcp relay information option`.
   - **Prüfen:** Der Client bekommt weiterhin eine Adresse. Auf R2 zeigt `debug ip dhcp server packet` die zusätzlichen Informationen.
   - **Denkfrage:** Was passiert, wenn ein Switch mit DHCP Snooping Option 82 einfügt und der Router sie als Relay oder Server erhält? Was ändert `ip dhcp relay information trusted`?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Ein DHCPDISCOVER ist ein Broadcast (255.255.255.255) und endet am Router. Das Relay wandelt ihn in einen Unicast an den Server um.
- **Zu 2:** Ausschlüsse halten Adressen für statische Geräte (Gateway, Drucker, Server) frei, ohne das Netz des Pools zu zerstückeln. Der Pool bleibt ein zusammenhängendes Netz, das Verwalten ist übersichtlicher.
- **Zu 3:** R1 trägt die IP-Adresse des Interfaces ein, an dem die Anfrage ankam (10.1.1.1), als **giaddr**. R2 wählt anhand von giaddr den passenden Pool (10.1.1.0/24) und schickt Offer und Ack als Unicast an giaddr zurück. Dafür braucht R2 eine Route dorthin.
- **Zu 4:** Jede Adresse von R2, die R3 erreicht, funktioniert: 10.0.23.1 (am direkten Link) oder 10.0.12.2 (über die Default-Route zu R2). Am saubersten ist eine Loopback-Adresse des Servers, die auch bei einem Link-Ausfall erreichbar bleibt. Hier nimmt das Lab die direkte Adresse 10.0.23.1.
- **Zu 5:** Discover und (je nach Client-Zustand) Request sind Broadcasts im LAN, das Relay macht daraus Unicasts an den Server. Offer und Ack gehen vom Server unicast an giaddr, das Relay liefert sie im LAN an den Client (Unicast oder Broadcast, je nach Broadcast-Flag des Clients).
- **Zu 6:** Option 82 (Relay Agent Information) trägt zum Beispiel Switch und Port. Fügt ein Snooping-Switch sie ein, hat das Paket aber giaddr 0.0.0.0. Ein Router verwirft solche Pakete standardmäßig. `ip dhcp relay information trusted` (am Interface) oder `ip dhcp relay information trust-all` erlaubt sie, sonst bekommt der Client keine Adresse.

</details>

## Teil B – Reparieren

Öffne das importierte Lab *Reparieren* und starte alle Nodes. Ohne Import: Nodes zurücksetzen (Rechtsklick → *Wipe*) und `repair/<Node>.cfg` einspielen. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** H1 bekommt keine Adresse; auf R2 zeigt `debug ip dhcp server packet` keine Anfragen aus 10.1.1.1.

**Ticket 2:** H2 bekommt keine Adresse; auf R2 zeigt `debug ip dhcp server packet` keine Anfragen aus 10.1.2.1.

**Ticket 3:** R2 empfängt die Anfragen von R3 (giaddr 10.1.2.1), H2 bekommt trotzdem keine Adresse; im Debug steht „there is no address pool for 10.1.2.1“.

**Ticket 4:** R2 empfängt die Anfragen von R1, H1 bekommt trotzdem keine Adresse; die Bindings bleiben leer.

**Ticket 5:** R2 sendet das DHCPOFFER für H2 (Debug zeigt es), H2 bekommt es trotzdem nicht.

## Verifikation
```
show ip dhcp pool
show ip dhcp binding
show ip dhcp server statistics
show ip interface GigabitEthernet0/0 | include Helper
show ip interface brief                ! auf H1/H2
debug ip dhcp server packet     ! kurz, danach undebug all
show ip route 10.1.2.1                 ! auf R2: Rückweg zum Relay
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip interface brief` auf H1 / H2 | 10.1.1.11 / 10.1.2.11 (erste Adresse nach dem Ausschluss) |
| `show ip dhcp binding` auf R2 | zwei Bindings (H1, H2) mit Lease-Ende |
| `show ip dhcp server statistics` auf R2 | Discover/Offer/Request/Ack zählen hoch |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Ein Client bekommt keine Adresse. In welcher Reihenfolge prüfst du?
<details><summary>Antwort</summary>

**Von der Anfrage bis zur Antwort.** 1) Kommt die Anfrage am Relay an (Link, VLAN)? 2) Steht der Helper am Eingangs-Interface und zeigt auf den Server? 3) Erreicht der Relay den Server (Ping, Route)? 4) Trifft giaddr einen Pool, und sind Adressen frei (Pool, Ausschlüsse, Bindings)? 5) Kommt die Antwort zurück (Route zum giaddr)?

</details>

2. Warum ist die Adresse in giaddr wichtig, und was passiert, wenn der Relay mehrere IPs am Interface hat?
<details><summary>Antwort</summary>

**giaddr wählt den Pool und das Ziel der Antwort.** Hat das Interface Secondary-Adressen, nutzt der Relay die primäre Adresse als giaddr. Mit `ip dhcp smart-relay` wechselt er auf die Secondary-Adressen, wenn der Server auf die Anfragen nicht antwortet (zum Beispiel Pool voll). Der Server braucht dann auch für das Secondary-Netz einen Pool.

</details>

3. Was leitet `ip helper-address` außer DHCP noch weiter, und wie schaltest du das ab?
<details><summary>Antwort</summary>

**Mehr UDP-Broadcasts: TFTP (69), DNS (53), TACACS (49), Time (37), NetBIOS (137/138).** Mit `no ip forward-protocol udp <Port>` schaltest du einzelne ab. DHCP selbst (67/68) bleibt, solange der Helper steht.

</details>

## Prüfungsbezug
- DHCP-Ablauf: Discover (Broadcast), Offer, Request, Ack. Das Relay macht aus dem Broadcast einen Unicast und setzt giaddr.
- Server wählt den Pool nach giaddr, Antwort geht an giaddr: Rückweg (Route) muss stimmen.
- `ip helper-address` steht auf dem **Client-seitigen** Interface und zeigt auf den Server.
- Option 82 und `ip dhcp relay information trusted/trust-all` bei Snooping-Switches mit giaddr 0.
- Fehlersuche: `show ip dhcp binding/pool/conflict/server statistics`, `debug ip dhcp server packet/events`.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
