# Lab E6 – IPv6 First Hop Security: RA Guard und DHCPv6 Guard

**Plattform:** EVE-NG · **Dauer:** 90 min · **Niveau:** mittel

Im IPv6-Zugangsnetz kann jeder Host Router Advertisements und DHCPv6-Antworten senden. Du richtest auf dem Switch RA Guard und DHCPv6 Guard ein, sodass nur der Router-Port als Router und DHCPv6-Server gilt, und siehst, wie sich der Zustand am Host ändert. Dazu die Einordnung von IPv6 Snooping, ND Inspection und Source Guard.

**Lernziele:** Nach diesem Lab kannst du …

- Die Wirkung eines Rogue-Routers und eines Rogue-DHCPv6-Servers am Host nachweisen.
- RA-Guard-Policies (`device-role host` und `router`) anlegen und an Ports binden.
- DHCPv6-Guard-Policies (`device-role client` und `server`) anlegen und binden.
- Die Rolle der Ports prüfen und die Ergänzungen (Snooping, ND Inspection, Source Guard) einordnen.

| Deck-Tag | Thema | Karten im Kompendium |
|---|---|---|
| `Ziel::3.4` | IPv6 First Hop Security: Feinheiten | 13 |

**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, `repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.

## Aufbau in EVE-NG

### Nodes

| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |
|---|---|---|---|
| SW | Cisco vIOS Switch (vIOS-L2) | Der erste Start dauert einige Minuten. | 768 |
| R1 | Cisco vIOS Router |  | 512 |
| H1 | Cisco vIOS Router | Host (vIOS, wie in CML; alternativ VPCS) | 512 |
| ATK | Cisco vIOS Router |  | 512 |

Summe (alle Nodes als vIOS/…): ca. **2.3 GB RAM**.

### Verkabelung

| Von | Interface | Nach | Interface |
|---|---|---|---|
| SW | Gi0/0 | R1 | Gi0/0 |
| SW | Gi0/1 | H1 | Gi0/0 |
| SW | Gi0/2 | ATK | Gi0/0 |

### Hosts: vIOS oder VPCS

Für dieses Lab brauchst du **vIOS-Hosts**: VPCS kann kein DHCPv6 und keine ND-Auswertung wie ein IOS-Host.

## Topologie

```
              ┌── R1 (legitimer Router, DHCPv6-Server, 2001:db8:1::/64)
   SW (L2) ───┤── H1 (Host, SLAAC + DHCPv6)
              └── ATK (Rogue-Router und Rogue-DHCPv6, 2001:db8:bad::/64)
```

| Link | Netz |
|---|---|
| SW Gi0/0 – R1 Gi0/0 | 2001:db8:1::/64 (R1 ::1) – legitimer Router, Router-Port |
| SW Gi0/1 – H1 Gi0/0 | Hostport |
| SW Gi0/2 – ATK Gi0/0 | 2001:db8:bad::/64 (ATK ::1) – Angreifer-Port, gleiches VLAN |

Alle drei Geräte hängen im selben VLAN am Switch. R1 sendet Router Advertisements für 2001:db8:1::/64 mit gesetztem M-Flag und bietet per DHCPv6 Adressen und einen DNS-Server (2001:db8:1::53). ATK macht genau dasselbe für 2001:db8:bad::/64. H1 nimmt SLAAC-Adressen aus Router Advertisements und fordert zusätzlich eine Adresse per DHCPv6 an. Konfigurieren musst du nur den Switch; R1 und ATK sind in der Ausgangslage fertig.

## Teil A – Bauen
Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst (**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am Ende von Teil A.

1. **Angriff sichtbar machen.** Auf H1: `show ipv6 routers`, `show ipv6 interface brief`, `show ipv6 route ::/0` und `show ipv6 dhcp interface`.
   - **Prüfen:** H1 sieht zwei Router (R1 und ATK), hat Adressen aus beiden Präfixen und zwei Default-Routen. Die DHCPv6-Adresse stammt von einem der beiden Server.
   - **Denkfrage:** Was kann der Angreifer damit erreichen, und welche zwei Mechanismen nutzt er?
2. **RA-Guard-Policies anlegen.** Auf SW: `ipv6 nd raguard policy HOST-POLICY` mit `device-role host`, `ipv6 nd raguard policy ROUTER-POLICY` mit `device-role router`.
   - **Prüfen:** `show ipv6 nd raguard policy` listet beide Policies mit der Rolle.
   - **Denkfrage:** Warum schaltet RA Guard auf Hostports nur Router Advertisements ab und nicht allen ICMPv6-Verkehr?
3. **RA Guard an die Ports binden.** Gi0/0 (R1): `ipv6 nd raguard attach-policy ROUTER-POLICY`. Gi0/1 (H1) und Gi0/2 (ATK): `ipv6 nd raguard attach-policy HOST-POLICY`. Setze danach auf H1 das Interface zurück (`shutdown`, `no shutdown`).
   - **Prüfen:** `show ipv6 routers` auf H1 nennt nur noch R1. Die Adresse aus dem ATK-Präfix und die zweite Default-Route sind weg.
   - **Denkfrage:** Warum hätte H1 den Eintrag von ATK auch ohne das Zurücksetzen noch eine Weile behalten?
4. **DHCPv6 Guard.** Auf SW: `ipv6 dhcp guard policy SERVER-POLICY` mit `device-role server` und `ipv6 dhcp guard policy CLIENT-POLICY` mit `device-role client`. Binde Gi0/0 an SERVER-POLICY, Gi0/1 und Gi0/2 an CLIENT-POLICY (`ipv6 dhcp guard attach-policy …`). Auf H1 die DHCPv6-Anfrage erneuern.
   - **Prüfen:** `show ipv6 interface brief` auf H1 zeigt nur noch Adressen aus 2001:DB8:1::/64. `show ipv6 dhcp guard policy` listet die Policies mit den Zielen.
   - **Denkfrage:** Welche Nachrichten blockiert `device-role client`, und warum reicht RA Guard allein nicht?
5. **Ergänzungen einordnen.** Mehr ist in diesem Lab nicht konfiguriert.
   - **Denkfrage:** Was leisten IPv6 Snooping, ND Inspection und Source Guard zusätzlich, und was nützt RA Guard nichts gegen fragmentierte Router Advertisements?

<details><summary>Antworten zu den Denkfragen</summary>

- **Zu 1:** Mit einem **Rogue-RA** wird der Angreifer zum Default-Gateway des Hosts und kann den Verkehr mitlesen oder umleiten (Man in the Middle). Mit einem **Rogue-DHCPv6-Server** liefert er Adressen und einen eigenen DNS-Server und lenkt Namensauflösungen um.
- **Zu 2:** RA Guard filtert nur **Router Advertisements** (ICMPv6 Typ 134), weil nur die Quelle der RAs ein Router sein darf. Neighbor Solicitation, Echo und alle anderen ICMPv6-Typen müssen weiter fließen, sonst funktioniert IPv6 nicht.
- **Zu 3:** Die Adresse und die Default-Route aus dem alten RA bleiben, bis ihre Lebenszeit (Router Lifetime und Valid/Preferred Lifetime) abläuft. RA Guard wirkt nur auf neue Pakete. Für den Test sofort: Interface zurücksetzen oder die Einträge löschen.
- **Zu 4:** `device-role client` blockiert DHCPv6-Antworten, die nur Server senden (Advertise, Reply, Reconfigure). RA Guard schützt nur gegen RAs. Ein Rogue-DHCPv6-Server braucht aber keinen RA, er antwortet direkt auf die Anfrage des Hosts.
- **Zu 5:** **IPv6 Snooping** baut eine Bindungstabelle (Adresse, MAC, Port) aus ND und DHCPv6 auf. **ND Inspection** prüft ND-Nachrichten gegen diese Tabelle (verhindert Spoofing von Neighbor Advertisements). **Source Guard** filtert Pakete, deren Absenderadresse nicht zur Bindung passt. RA Guard lässt sich mit fragmentierten RAs oder Extension Headern umgehen, wenn der Switch die Header nicht vollständig lesen kann (RFC 7113). Abhilfe: Fragmente auf Hostports verwerfen oder Extension-Header-Filter.

</details>

## Teil B – Reparieren

Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein. Alle Geräte sind vollständig konfiguriert, aber es stecken **5 Fehler** drin. Behandle jede Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben und das Ergebnis beweisen. Ändere nur, was kaputt ist.

Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von unten nach oben (Underlay, Control Plane, Daten).

**Ticket 1:** H1 sieht weiterhin die Router Advertisements von ATK (`show ipv6 routers` listet zwei Router), obwohl RA Guard eingerichtet ist.

**Ticket 2:** H1 bekommt keinen Default-Router und keine Adresse aus 2001:DB8:1::/64; `show ipv6 routers` ist leer.

**Ticket 3:** ATK schickt RAs, und sie erreichen H1, obwohl am Port Gi0/2 die Host-Policy hängt.

**Ticket 4:** H1 bekommt per DHCPv6 eine Adresse aus 2001:DB8:BAD::/64, obwohl der Port von ATK eine Client-Policy trägt.

**Ticket 5:** H1 bekommt gar keine DHCPv6-Adresse mehr, auch nicht von R1; SLAAC funktioniert.

## Verifikation
```
show ipv6 nd raguard policy
show ipv6 dhcp guard policy
show ipv6 routers               ! auf H1
show ipv6 interface brief         ! auf H1
show ipv6 route ::/0               ! auf H1
show ipv6 dhcp interface         ! auf H1
```

| Befehl | Das solltest du sehen |
|---|---|
| `show ipv6 routers` auf H1 | nur R1 (Link-Local von R1) |
| `show ipv6 interface brief` auf H1 | nur Adressen aus 2001:DB8:1::/64 |
| `show ipv6 nd raguard policy` auf SW | ROUTER-POLICY an Gi0/0, HOST-POLICY an Gi0/1 und Gi0/2 |
| `show ipv6 dhcp guard policy` auf SW | SERVER-POLICY an Gi0/0, CLIENT-POLICY an Gi0/1 und Gi0/2 |

## Teil C – Üben

Beantworte zuerst selbst, dann klappe die Antwort auf.

1. Ein Host bekommt über SLAAC keinen Default-Router, obwohl der Router RAs sendet. Was prüfst du auf dem Switch?
<details><summary>Antwort</summary>

**Rolle und Bindung des Router-Ports.** Hängt am Router-Port eine Policy mit `device-role router` (nicht host)? Sind Policy und Port richtig gebunden (`show ipv6 nd raguard policy`)? Gibt es eine zweite Filterung (VACL, PACL, ND Inspection) auf dem Pfad?

</details>

2. Warum braucht man DHCPv6 Guard zusätzlich zu RA Guard?
<details><summary>Antwort</summary>

**Weil ein Rogue-DHCPv6-Server keinen RA braucht.** Der Host fragt per Multicast (ff02::1:2) nach einem Server, der Angreifer antwortet mit Adresse und DNS-Server. RA Guard schaut nur auf RAs, nicht auf DHCPv6-Nachrichten.

</details>

3. Was bewirkt ein Preference-Limit oder `match ipv6 access-list` in einer RA-Guard-Policy?
<details><summary>Antwort</summary>

**Es erlaubt nur RAs, deren Absender und Inhalt zur Vorgabe passen.** Mit `match ipv6 access-list` prüfst du die Absenderadresse, mit `match ra prefix-list` die angekündigten Präfixe, mit `router-preference maximum` begrenzt du die angekündigte Priorität. So kann auch auf dem Router-Port nur der erwartete Router mit den erwarteten Präfixen senden.

</details>

## Prüfungsbezug
- RA Guard: `ipv6 nd raguard policy … / device-role host|router`, Bindung mit `ipv6 nd raguard attach-policy`.
- DHCPv6 Guard: `ipv6 dhcp guard policy … / device-role client|server`, optional Match auf Server-Adresse und Präfix.
- Hostport = Rolle host/client, Router-/Serverport = Rolle router/server. Eine falsch gesetzte Rolle ist der häufigste Fehler.
- Ergänzungen: IPv6 Snooping (Bindungstabelle), ND Inspection (prüft ND gegen die Tabelle), Source Guard (prüft die Absenderadresse).
- RA Guard kann durch fragmentierte RAs oder Extension Header umgangen werden (RFC 7113).

## Hinweis zum Image

RA Guard und DHCPv6 Guard hängen vom Switch-Image ab. Das IOSvL2-Image kennt die Befehle womöglich nur eingeschränkt oder gar nicht; dann lies das Lab als Konfigurations- und Denkaufgabe (Teil A, Teil C, die Tickets mit den Lösungen). Die Syntax folgt der Cisco-IOS-15-Dokumentation und ist hier nicht in einer laufenden Simulation getestet. Auf Catalyst-Switches mit IOS XE heißen einige Befehle anders (SISF).

## Lösungen

- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)
- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)
