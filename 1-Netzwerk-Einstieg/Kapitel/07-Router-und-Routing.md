# 7. Router und Routing

> **Darum geht's:** Ein Router ist wie ein Wegweiser an einer Kreuzung: Er schaut auf die Zieladresse und schickt das Paket in die passende Richtung. Welche Richtung das ist, steht in seiner Routing-Tabelle.
>
> **Danach kannst du:** erklären, woher ein Router seine Routen kennt · mit Longest Prefix Match vorhersagen, welche Route gewinnt · eine Zeile der Cisco-Routing-Tabelle lesen.

Ein Router verbindet **verschiedene Netze**. Er schaut auf die Ziel-IP eines Pakets und entscheidet anhand seiner **Routing-Tabelle**, wohin es als Nächstes geht.

## Wie ein Router entscheidet

```
Paket für 10.2.5.9 kommt an
    ↓
Routing-Tabelle:
   10.0.0.0/8      → via 192.168.1.2
   10.2.0.0/16     → via 192.168.1.3
   10.2.5.0/24     → via 192.168.1.4   ← längster passender Präfix
   0.0.0.0/0       → via 192.168.1.9   (Default Route)
```

**Longest Prefix Match:** Die Route mit der längsten passenden Präfixlänge gewinnt. Gibt es nichts Passendes und auch keine Default Route, wird das Paket verworfen.

## Woher kommen die Routen?

1. **Direkt verbunden** (Connected): Netze an den eigenen Interfaces.
2. **Statisch**: Du trägst sie von Hand ein. Einfach, aber ohne automatische Anpassung.
3. **Dynamisch**: Routingprotokolle (z. B. **OSPF**, EIGRP, BGP) tauschen Routen aus und passen sich Ausfällen an.

## Default Route

`0.0.0.0/0` heißt: „Alles, was ich nicht kenne, schicke dorthin“. Dein Heimrouter hat eine Default Route zum Provider.

## Was ein Router am Paket ändert

- TTL um 1 verringern (Schutz gegen Schleifen).
- Neue MAC-Adressen (nächster Hop) einsetzen.
- IP-Adressen bleiben unverändert (außer bei NAT).

## Wenn zwei Routen konkurrieren

Erst zählt der **längste Präfix**. Bei gleichem Präfix gewinnt die Quelle mit der niedrigeren **Administrative Distance** (AD):

| Quelle | AD |
|---|---|
| Direkt verbunden | 0 |
| Statisch | 1 |
| EIGRP (intern) | 90 |
| OSPF | 110 |
| RIP | 120 |

## Routing-Tabelle lesen (Cisco)

```
O    10.2.0.0/16 [110/20] via 10.0.0.2, 00:05:12, GigabitEthernet0/1
```

OSPF-Route (`O`), AD 110, Metrik 20, Next-Hop 10.0.0.2, vor 5:12 gelernt, Ausgang Gi0/1.

## Das Wichtigste in Kürze

- Routen kommen von direkt verbundenen Netzen, von Hand (statisch) oder von Routing-Protokollen (dynamisch).
- Erst gewinnt das längste passende Präfix, bei Gleichstand die kleinere Administrative Distanz.
- Die Default-Route 0.0.0.0/0 fängt alles auf, was sonst nicht passt.

## Selbsttest

1. Was ist ein Default Gateway im Verhältnis zur Default Route?
2. Welche Route gewinnt bei 10.1.1.5: `10.1.0.0/16` oder `10.1.1.0/24`?
3. Wozu dient die TTL?

<details><summary>Antworten</summary>

1. **Beide meinen „wohin mit unbekannten Zielen“, nur auf verschiedenen Geräten.** Das Default Gateway steht auf dem Host, die Default-Route auf dem Router.
2. **10.1.1.0/24.** Beide passen, aber /24 ist länger und damit genauer. Die längere Route gewinnt immer.
3. **Sie verhindert, dass Pakete endlos im Kreis laufen.** Jeder Router zieht 1 ab. Bei 0 wird das Paket verworfen.

</details>

Zurück: [6. Subnetting](06-Subnetting.md) · Weiter: [8. Transport und Anwendung](08-TCP-UDP-DNS-DHCP-NAT.md)
