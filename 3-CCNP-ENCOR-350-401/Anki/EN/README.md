# Anki-Deck EN: CCNP ENCOR 350-401 v1.2

**Stand:** 25.10.2026 · **1.981 Karten**
**Datei:** [`ENCOR_v1.2_Kompendium_EN.apkg`](ENCOR_v1.2_Kompendium_EN.apkg) (Quelle als Textimport: [`ENCOR_v1.2_Kompendium_EN.txt`](Quelle/ENCOR_v1.2_Kompendium_EN.txt))

Fragen, Antwortoptionen und Fachbegriffe stehen auf Englisch, so wie in der Prüfung. Die Erklärungen bleiben auf Deutsch. Grundlage ist das deutsche Kompendium 5.2: Doppelte Karten sind gestrichen, Listen mit mehr als vier Punkten sind geteilt, und Zusatzdetails von gestrichenen Karten stehen jetzt auf der behaltenen Karte. Was gestrichen und geteilt wurde, steht in der [Streichliste](Streichliste.md).

## Kartentypen

| Typ | Karten | Zweck |
|---|---:|---|
| Recall | 1.416 | Frage vorne, fetter englischer Kern und deutsche Erklärung hinten |
| MC | 429 | Prüfungsstil mit vier oder fünf Optionen, teils „Choose two“; hinten steht zu jeder falschen Option, warum sie falsch ist |
| Show | 136 | Echte Ausgaben lesen: BGP-Tabelle, OSPF-Nachbarn und LSDB, Routing-Tabelle, IPsec-SAs, Spanning Tree, Trunks, HSRP/VRRP, NAT |

Die MC-Karten haben mindestens zwei Varianten pro Kernthema. Die richtige Antwort ist gleichmäßig auf A bis D verteilt und fällt weder durch ihre Länge noch durch ihre Formulierung auf. Schwerpunkt sind Tie-Breaker, Defaults, Timer und typische Fallen. Alle MC- und Show-Karten wurden unabhängig gegengeprüft.

## Import

1. `.apkg` herunterladen und in Anki öffnen (Datei → Importieren).
2. Das Deck heißt „ENCOR::Kompendium“ und hat sechs Unterdecks pro Domäne, darunter ein Deck pro Prüfungsziel.
3. Updates einfach drüber importieren. Jede Karte hat eine feste Kennung, der Lernstand bleibt erhalten.

Das EN-Deck ersetzt das deutsche Deck inhaltlich. Wer beide importiert, lernt die meisten Inhalte doppelt.

## Verteilung

| Domäne | Karten | Anteil | Blueprint |
|---|---:|---:|---:|
| 1 Architecture | 248 | 12,5 % | 15 % |
| 2 Virtualization | 166 | 8,4 % | 10 % |
| 3 Infrastructure | 725 | 36,6 % | 30 % |
| 4 Network Assurance | 222 | 11,2 % | 10 % |
| 5 Security | 371 | 18,7 % | 20 % |
| 6 Automation | 249 | 12,6 % | 15 % |

## Gezielt lernen

| Suche | Was du bekommst |
|---|---|
| `tag:mc` | alle MC-Karten |
| `tag:show` | alle Show-Karten |
| `tag:recall` | alle Recall-Karten |
| `tag:security` usw. | eine Domäne (`architecture`, `virtualization`, `infrastructure`, `assurance`, `security`, `automation`) |
| `tag:ziel_3_2_b` usw. | ein einzelnes Prüfungsziel |
| `tag:ospf tag:mc` | MC-Karten zu einem Thema |

Die Tags `Stufe::…`, `Fokus::…`, `Modus::…` und `Befehlsart::…` aus dem deutschen Deck sind auf den Recall-Karten erhalten.

## Fehler gefunden?

Bitte als Issue melden, mit Karten-ID (steht klein unten auf jeder Karte) und Begründung. Im Zweifel gilt die Cisco-Dokumentation.
