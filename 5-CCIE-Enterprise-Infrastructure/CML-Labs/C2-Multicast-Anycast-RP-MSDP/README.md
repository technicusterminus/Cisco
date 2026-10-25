# Lab C2 – Multicast: Anycast RP mit MSDP, RPF-Umleitung und SSM

**Dauer:** 110 min · **Niveau:** schwer · **Nodes:** 5× iosv

Zwei Rendezvous Points teilen sich eine Anycast-Adresse und tauschen ihre aktiven Quellen per MSDP aus. Der kürzeste Unicast-Weg zur Quelle führt über eine Firewall-Strecke ohne Multicast, deshalb scheitert die RPF-Prüfung, bis eine statische Mroute den Weg umlenkt. Dazu kommt Source-Specific Multicast mit IGMPv3, das ganz ohne RP auskommt.

**Lernziele:** Nach diesem Lab kannst du …

- Anycast RP mit MSDP aufbauen und erklären, warum zwei RPs ohne MSDP nichts voneinander wissen.
- Eine RPF-Fehlentscheidung mit `show ip rpf` erkennen und mit `ip mroute` beheben, ohne das Unicast-Routing anzufassen.
- SSM mit IGMPv3 konfigurieren und den Unterschied zu ASM in `show ip mroute` zeigen.
- Multicast-Fehler Schicht für Schicht eingrenzen: PIM-Nachbarn, RP, MSDP, RPF, IGMP.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::1.6.a` | Multicast auf Layer 2: IGMP, MLD und Snooping | 9 |
| `Ziel::1.6.b` | RPF-Prüfung | 4 |
| `Ziel::1.6.c` | PIM: Dense, Sparse, RP, Bidir, SSM und Anycast RP | 15 |

**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere `topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen.

## Topologie

```
  SRC 10.1.1.10
     | Gi0/0
     | Gi0/0   10.1.1.0/24
     R1 Gi0/1 ---------------------- Gi0/0 R2   RP, Lo1 10.255.255.255
      \                                    | Gi0/1
       \ Gi0/2  Firewall-Strecke:          |
        \       Kosten 100, kein PIM       | Gi0/1
         +--------------------------- Gi0/0 R3   RP, Lo1 10.255.255.255
                                           | Gi0/2
                                           | Gi0/0   10.3.3.0/24
                                         RCV 10.3.3.10
```

| Link | Netz |
|---|---|
| SRC Gi0/0 – R1 Gi0/0 | 10.1.1.0/24 (R1 .1, SRC .10) |
| R1 Gi0/1 – R2 Gi0/0 | 10.0.12.0/30 (.1/.2) |
| R1 Gi0/2 – R3 Gi0/0 (Firewall-Strecke) | 10.0.13.0/30 (.1/.2) |
| R2 Gi0/1 – R3 Gi0/1 | 10.0.23.0/30 (R2 .1, R3 .2) |
| R3 Gi0/2 – RCV Gi0/0 | 10.3.3.0/24 (R3 .1, RCV .10) |
| Loopback0 | R1 10.0.0.1, R2 10.0.0.2, R3 10.0.0.3 (/32) |
| Loopback1 (Anycast RP) | 10.255.255.255/32 auf R2 und R3 |

OSPF ist vorgegeben. Die Strecke R1–R3 läuft über eine Firewall, die kein Multicast weiterleitet: Dort bleibt PIM aus. R1 hat an Gi0/2 die OSPF-Kosten 100 und erreicht die RP-Adresse deshalb über R2. R3 dagegen sieht an seinem Gi0/0 die normalen Kosten und erreicht die Quelle direkt über die Firewall-Strecke. Diese Asymmetrie ist gewollt. SRC und RCV sind IOS-Hosts ohne Routing.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Unicast prüfen.** Auf R1 `show ip route 10.255.255.255`, auf R3 `show ip route 10.1.1.0`.
   - **Prüfen:** R1 erreicht die RP-Adresse über R2 (Gi0/1). R3 erreicht das Netz der Quelle direkt über Gi0/0.
   - **Denkfrage:** Warum bevorzugt R1 für die RP-Adresse R2, obwohl auch R3 sie trägt, und warum wählt R3 für den Rückweg trotzdem den direkten Link zu R1?
2. **Multicast-Routing und PIM.** Auf R1, R2 und R3 `ip multicast-routing`. `ip pim sparse-mode` auf R1 Gi0/0 und Gi0/1, auf R2 Gi0/0, Gi0/1 und Loopback1, auf R3 Gi0/1, Gi0/2 und Loopback1. Die Firewall-Strecke (R1 Gi0/2, R3 Gi0/0) bleibt ohne PIM.
   - **Prüfen:** `show ip pim neighbor`: R1 sieht R2, R2 sieht R1 und R3, R3 sieht R2.
   - **Denkfrage:** Warum bekommt Loopback1 mit der RP-Adresse PIM, Loopback0 aber nicht?
3. **Anycast RP.** Auf allen drei Routern `ip pim rp-address 10.255.255.255`.
   - **Prüfen:** `show ip pim rp mapping` zeigt 10.255.255.255 als statischen RP für 224.0.0.0/4.
   - **Denkfrage:** Was passiert ohne weitere Maßnahmen, wenn SRC bei R2 registriert und RCV hinter R3 sitzt?
4. **MSDP zwischen den RPs.** R2: `ip msdp peer 10.0.0.3 connect-source Loopback0` und `ip msdp originator-id Loopback0`. R3 spiegelbildlich mit `ip msdp peer 10.0.0.2 connect-source Loopback0`.
   - **Prüfen:** `show ip msdp summary` zeigt den Peer im Zustand Up.
   - **Denkfrage:** Wozu dient `originator-id`, wenn beide RPs dieselbe RP-Adresse haben?
5. **Empfänger anmelden.** Auf R3 unter Gi0/2 `ip igmp version 3`. Auf RCV unter Gi0/0 `ip igmp version 3` und `ip igmp join-group 239.1.1.1`. Dann auf SRC `ping 239.1.1.1 repeat 20`.
   - **Prüfen:** Die Pings bleiben unbeantwortet, bis auf höchstens das erste Paket. `show ip msdp sa-cache` auf R3 kennt die Quelle 10.1.1.10, der Verkehr kommt trotzdem nicht an.
   - **Denkfrage:** Was verrät `show ip rpf 10.1.1.10` auf R3?
6. **RPF-Weg umlenken.** Auf R3 `ip mroute 10.1.1.0 255.255.255.0 10.0.23.1`. Wiederhole den Ping.
   - **Prüfen:** RCV antwortet. `show ip rpf 10.1.1.10` auf R3 nennt jetzt Gi0/1 und die statische Mroute als Quelle. `show ip route 10.1.1.0` zeigt weiter den direkten Weg über Gi0/0.
   - **Denkfrage:** Warum ist eine statische Mroute hier besser als eine Änderung der OSPF-Kosten?
7. **Source-Specific Multicast.** Auf R1, R2 und R3 `ip pim ssm default`. Auf RCV `ip igmp join-group 232.1.1.1 source 10.1.1.10`. Auf SRC `ping 232.1.1.1 repeat 20`.
   - **Prüfen:** RCV antwortet. `show ip mroute 232.1.1.1` auf R3 zeigt nur einen (S,G)-Eintrag mit dem Flag `s`, kein (*,G).
   - **Denkfrage:** Warum funktioniert SSM auch dann, wenn beide RPs ausfallen?
8. **RP-Ausfall.** Starte auf SRC einen langen Ping an 239.1.1.1 und setze auf R2 Loopback1 auf `shutdown`. Danach `no shutdown`.
   - **Prüfen:** `traceroute 10.255.255.255` von R1 endet jetzt bei R3, neue Register landen dort. Die Pings an RCV laufen weiter.
   - **Denkfrage:** Wofür braucht das Netz den RP überhaupt noch, wenn der Baum zur Quelle steht?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** **Weil OSPF-Kosten je Richtung gelten.** R1 Gi0/2 hat Kosten 100, deshalb meidet R1 den direkten Link zu R3 und erreicht die RP-Adresse über R2. R3s Gi0/0 hat die normalen Kosten, deshalb nimmt R3 den direkten Weg zu R1. Genau diese Asymmetrie führt später zum RPF-Problem.
- **Zu 2:** **Das Interface mit der RP-Adresse sollte PIM sprechen, damit der Router die RP-Rolle sauber übernimmt** (Register annehmen, Ziel der Joins sein). Loopback0 ist nur die Quelle der MSDP-Sitzung über TCP, dafür braucht es kein PIM.
- **Zu 3:** **Die beiden RPs wissen nichts voneinander.** Jeder Router nutzt den nächstgelegenen RP: R1 registriert die Quelle bei R2, RCV meldet sich bei R3 an. Jeder RP kennt nur seine Hälfte, und der Verkehr kommt nicht an. MSDP verbindet die beiden: R2 meldet die aktive Quelle per Source-Active (SA) an R3.
- **Zu 4:** **Damit jede SA-Nachricht eine eindeutige RP-Adresse trägt.** Ohne `originator-id` setzt der RP die gemeinsame Anycast-Adresse ein. Der andere RP hält die SA dann für seine eigene und verwirft sie. Mit `originator-id Loopback0` steht die eindeutige Loopback0 in der SA.
- **Zu 5:** **Die RPF-Prüfung zeigt auf die Firewall-Strecke.** `show ip rpf 10.1.1.10` nennt Gi0/0 mit dem RPF-Nachbarn 10.0.13.1. Dort läuft kein PIM, also gibt es keinen Nachbarn, an den R3 den (S,G)-Join schicken kann. Der Baum zur Quelle kommt nicht zustande.
- **Zu 6:** **Weil die Mroute nur die RPF-Prüfung ändert, nicht den Unicast-Verkehr.** Änderst du die OSPF-Kosten, verschiebst du auch den Unicast-Weg, der über die Firewall gewollt sein kann. Die Mroute gilt nur für Multicast. Eine Alternative wäre MP-BGP mit der Adressfamilie IPv4 Multicast.
- **Zu 7:** **Weil SSM keinen RP braucht.** Der Empfänger nennt die Quelle selbst (IGMPv3), der Last-Hop-Router schickt den (S,G)-Join direkt Richtung Quelle. Shared Tree, Register und MSDP entfallen.
- **Zu 8:** **Nur für neue Quellen und neue Empfänger.** Bestehende (S,G)-Bäume laufen unabhängig vom RP weiter, deshalb merkt RCV vom Ausfall nichts. Eine neue Quelle registriert sich beim nächstgelegenen RP, sobald OSPF die Anycast-Adresse neu berechnet hat. Die Umschaltung dauert also so lange wie die Unicast-Konvergenz.

</details>

## Teil B – Reparieren

Importiere `topology-repair.yaml`. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** R3 hat keinen einzigen PIM-Nachbarn.

**Ticket 2:** `show ip msdp summary` auf R2 und R3 zeigt keine Sitzung im Zustand Up.

**Ticket 3:** Die Rendezvous Points bekommen von der Quelle nichts mit: `show ip mroute 239.1.1.1` auf R2 zeigt keinen Eintrag mit 10.1.1.10, auch während SRC an 239.1.1.1 sendet.

**Ticket 4:** RCV empfängt die Multicast-Pings von SRC weiterhin nicht, obwohl R3 die Quelle 10.1.1.10 kennt (`show ip msdp sa-cache`).

**Ticket 5:** Die SSM-Gruppe 232.1.1.1 fehlt in `show ip igmp groups` auf R3, obwohl RCV sie mit der Quelle 10.1.1.10 abonniert hat.

## Verifikation
```
show ip pim neighbor
show ip pim rp mapping
show ip msdp summary
show ip msdp sa-cache
show ip rpf 10.1.1.10
show ip mroute 239.1.1.1
show ip mroute 232.1.1.1
show ip igmp groups
ping 239.1.1.1 repeat 20   ! auf SRC
ping 232.1.1.1 repeat 20   ! auf SRC
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ip msdp summary` auf R2 | Peer 10.0.0.3 im Zustand Up |
| `show ip msdp sa-cache` auf R3 | (10.1.1.10, 239.1.1.1) mit RP 10.0.0.2 |
| `show ip rpf 10.1.1.10` auf R3 | RPF-Interface Gi0/1, RPF-Nachbar 10.0.23.1, Quelle: statische Mroute |
| `show ip mroute 232.1.1.1` auf R3 | nur (10.1.1.10, 232.1.1.1) mit Flag `s` |
| Pings von SRC | RCV antwortet auf 239.1.1.1 und auf 232.1.1.1 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Auto-RP läuft in einem reinen Sparse-Mode-Netz nicht an. Woran liegt das, und welche Lösungen gibt es?
<details><summary>Antwort</summary>

**Die Auto-RP-Gruppen 224.0.1.39 und 224.0.1.40 werden im Dense Mode verteilt, und im Sparse Mode gibt es für sie keinen RP.** Lösungen: `ip pim autorp listener` (nur diese beiden Gruppen dicht fluten) oder `ip pim sparse-dense-mode` an den Interfaces. Oder gleich BSR, das ohne Dense Mode auskommt.

</details>

2. Ein Standort soll nur Gruppen aus 239.192.0.0/16 erhalten. Welche Funktion setzt du am Übergabe-Interface ein?
<details><summary>Antwort</summary>

**Eine Multicast-Boundary: `ip multicast boundary <ACL>`.** Sie filtert Joins und Daten für Gruppen außerhalb der ACL. Mit `filter-autorp` filtert sie zusätzlich die passenden Auto-RP-Ankündigungen.

</details>

3. Warum gewinnt die statische Mroute die RPF-Prüfung gegen OSPF?
<details><summary>Antwort</summary>

**Weil IOS für die RPF-Prüfung die Quellen nach Administrativer Distanz vergleicht** und eine statische Mroute standardmäßig die Distanz 0 hat. Gibt man ihr eine höhere Distanz, dient sie nur als Rückfall, wenn der Unicast-Weg fehlt.

</details>

4. Was unterscheidet Anycast RP mit MSDP von PIM Anycast RP nach RFC 4610?
<details><summary>Antwort</summary>

**Bei MSDP tauschen die RPs aktive Quellen über eine eigene TCP-Sitzung aus, bei RFC 4610 leiten sie die Register-Nachrichten selbst an die anderen RPs weiter.** RFC 4610 braucht kein zweites Protokoll und funktioniert auch für IPv6, wo es kein MSDP gibt.

</details>

## Prüfungsbezug
- Anycast RP: dieselbe RP-Adresse auf mehreren RPs, jeder Router nutzt den nächsten. MSDP synchronisiert die aktiven Quellen (SA), `ip msdp originator-id` macht die SAs eindeutig.
- RPF: Multicast wird nur auf dem Interface angenommen, über das die Quelle per Unicast erreichbar ist. `ip mroute` ändert nur die RPF-Prüfung.
- SSM (232.0.0.0/8, `ip pim ssm default`) braucht IGMPv3 am Empfänger-Interface, aber keinen RP.
- Fehlersuche: `show ip pim neighbor`, `show ip pim rp mapping`, `show ip msdp summary`, `show ip msdp sa-cache`, `show ip rpf <Quelle>`, `show ip mroute`, `show ip igmp groups`.

## Hinweis zum Image

IOSv leitet Multicast in Software weiter, das reicht für Pings. Die Ausgaben von `show ip mroute` unterscheiden sich je nach Version in Details. Akzeptiert dein Image `ip igmp join-group … source` auf RCV nicht, prüfe, ob dort `ip igmp version 3` am Interface steht.

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-Konfiguration)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
