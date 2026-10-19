# CCNP ENCOR 350-401 v1.2 – Anki-Kompendium (Deutsch)

Ein deutschsprachiges Anki-Deck für die Prüfung **Cisco 350-401 ENCOR v1.2**. Es deckt die Blueprint-Themen vollständig ab und ist darauf ausgelegt, Verständnis aufzubauen, nicht nur Fakten abzufragen. Zum Lernen unterwegs gibt es kurze Karten ohne Code, zum Prüfungstraining Exhibits und Fallen.

**Aktuelle Version:** 4.3 (Stand 19.10.2026) · **1.431 Karten**
**Datei:** [`ENCOR_v1.2_Kompendium_4.3_DE.apkg`](ENCOR_v1.2_Kompendium_4.3_DE.apkg)

## Schnellstart

1. `.apkg` herunterladen und in Anki öffnen (Datei → Importieren).
2. Das Deck `ENCOR v1.2 · Kompendium` erscheint mit sechs Unterdecks, eines pro Blueprint-Domäne.
3. Ein Update-Import über eine ältere Version behält deinen Lernfortschritt (gleiche Karten-IDs).

## Inhalt nach Blueprint

| Domäne | Karten | Anteil | Blueprint |
|---|---:|---:|---:|
| 1 Architektur (QoS, SD-WAN, SD-Access, Redundanz) | 185 | 12,9 % | 15 % |
| 2 Virtualisierung (Hypervisor, VRF, GRE/IPsec, LISP, VXLAN) | 147 | 10,3 % | 10 % |
| 3 Infrastruktur (Layer 2, OSPF, EIGRP, BGP, NAT, HSRP, Multicast) | 475 | 33,2 % | 30 % |
| 4 Network Assurance (Syslog, SNMP, NetFlow, SPAN, IP SLA, Catalyst Center) | 170 | 11,9 % | 10 % |
| 5 Security (AAA, ACL, CoPP, 802.1X, TrustSec, MACsec, Firewall) | 272 | 19,0 % | 20 % |
| 6 Automation und KI (Python, JSON, YANG, NETCONF/RESTCONF, EEM, Ansible/Terraform) | 182 | 12,7 % | 15 % |

Wireless gehört in v1.2 nicht mehr zu 350-401 (es liegt bei ENWLSI) und ist bewusst nicht enthalten.

## Kartentypen

| Typ | Anzahl | Zweck |
|---|---:|---|
| Wissen | 445 | Definitionen und Fakten |
| Szenario | 233 | Fehlersuche und Designentscheidungen |
| CLI | 213 | Konfiguration und Befehle |
| Interpretation | 169 | Ausgaben und Code lesen |
| Vergleich | 168 | Protokolle und Verfahren gegenüberstellen |
| Exhibit | 81 | `show`-Ausgaben und Konfigurationen wie in der Prüfung |
| Vertiefung | 54 | Warum funktioniert etwas so? |
| Prüfungsfalle | 43 | Typische Stolpersteine |
| Rechnen | 25 | Subnetze, Wildcards, Overhead, Metriken |

## Gefilterte Decks mit Tags

In Anki unter **Karteikarten durchsuchen** oder als gefiltertes Deck:

| Tag | Karten | Wofür |
|---|---:|---|
| `tag:Modus::Zug` | 1.022 | Kurze Karten ohne Codeblöcke, gut für unterwegs |
| `tag:Fokus::Exhibit` | 127 | Ausgaben und Konfigurationen interpretieren |
| `tag:Fokus::Falle` | 68 | Prüfungsfallen |
| `tag:Fokus::HighYield` | 203 | Klassische Prüfungsfakten |
| `tag:Domaene::3` usw. | – | Eine Blueprint-Domäne |
| `tag:Ziel::3.2.b` usw. | – | Ein einzelner Blueprint-Punkt |
| `tag:Korrektur::2026_10_19` | – | Nachträglich fachlich geschärfte Karten |

## Aufbau einer Karte

Jede Karte hat eine stabile ID (`E12-<Blueprint-Punkt>-<Nr>`), den Themenbezug, Typ und Stufe (Leicht, Mittel, Schwer), Frage, Antwort, einen optionalen Hinweis und Quellenlinks. Die Karten-IDs bleiben über Versionen hinweg gleich, deshalb funktioniert der Update-Import.

## Lernempfehlung

1. **Aufbauphase (4 bis 6 Wochen):** Gesamtes Deck oder `tag:Modus::Zug` täglich, parallel Labs (EVE-NG, CML oder echte Geräte).
2. **Vertiefung:** Schwache Domänen gezielt über `tag:Domaene::N` oder `tag:Ziel::…` nacharbeiten.
3. **Prüfungsphase (die letzten 2 bis 3 Wochen):** Umstellen auf `tag:Fokus::Exhibit`, `tag:Fokus::Falle` und `tag:Fokus::HighYield`.

## Qualität und Grenzen

- Die Karten sind eigene Formulierungen, keine Kopien von Cisco-Material. Die Quellenlinks verweisen auf Cisco-Dokumentation und RFCs.
- Sie sind nicht Karte für Karte gegen die Cisco-Dokumentation geprüft. **Im Zweifel gilt die offizielle Cisco-Dokumentation.**
- Die Exhibits sind gekürzt, Werte teilweise frei gewählt. Sie trainieren das Lesen, ersetzen aber keine echten Geräteausgaben.
- Aussagen zu Defaults und Grenzwerten hängen oft von Plattform und Release ab. Wo das relevant ist, steht es im Hinweisfeld.
- Du hast einen Fehler gefunden? Bitte als Issue melden, mit Karten-ID und Begründung.

## Versionen

| Version | Änderung |
|---|---|
| 4.3 | Syntax- und Fachkorrekturen (u. a. Flexible NetFlow `match ipv4 protocol`, `ip sla schedule`, IKEv2-Begriffe, EEM-Label-Reihenfolge, NETCONF `discard-changes`), neue Virtualisierungs-, LISP-/VXLAN- und PBR-Karten |
| 4.0 | +115 Karten: Vertiefung, weitere Exhibits, Security auf Blueprint-Niveau, Duplikate entfernt |
| 3.0 | Schwache Karten entfernt, Exhibits mit `show`-Ausgaben, Prüfungsfallen, Lücken geschlossen (Security-Produkte, 802.1X, Automation) |
| 1.0 | Ausgangsdeck (972 Karten) |

## Rechtliches

Kein offizielles Cisco-Material, nicht von Cisco geprüft oder freigegeben. Cisco, CCNP und ENCOR sind Marken von Cisco Systems, Inc. Das Deck dient der privaten Prüfungsvorbereitung.

## CML-Labs

Im Ordner [`CML-Labs/`](CML-Labs/) liegt zu jedem der 47 Ziele des Kompendiums Übungsmaterial: 19 Labs für Cisco Modeling Labs 2.x, je mit Bau-Topologie, Reparatur-Topologie mit eingebauten Fehlern (insgesamt 78), Tickets, Musterlösungen und Transferfragen. Dazu Python-/API-Drills mit automatischen Tests (lokal, ohne CML) und zwei Fallstudien-Pakete für Design, SD-WAN, SD-Access, Virtualisierung, Catalyst Center und Security. Die Python-Drills sind getestet, die CML-Labs nicht in einer echten CML-Instanz; Details in der README dort.
