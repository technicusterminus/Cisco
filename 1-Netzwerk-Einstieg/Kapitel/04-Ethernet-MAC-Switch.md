# 4. Ethernet, MAC-Adressen und der Switch

> **Darum geht's:** Im lokalen Netz zählt nicht die IP-Adresse, sondern die MAC-Adresse. Der Switch merkt sich, welches Gerät an welchem Port hängt, wie ein Hausmeister, der weiß, wer in welcher Wohnung wohnt.
>
> **Danach kannst du:** eine MAC-Adresse lesen und ihren Zweck erklären · beschreiben, wie ein Switch lernt und weiterleitet · erklären, wozu ARP gebraucht wird.

## Ethernet

Ethernet ist der Standard in fast jedem kabelgebundenen LAN. Daten reisen in **Frames**.

## Die MAC-Adresse

- 48 Bit, in Hex geschrieben: `00:1A:2B:3C:4D:5E`.
- Fest in der Netzwerkkarte eingebaut (heute oft änderbar).
- Die erste Hälfte (OUI) verrät den Hersteller.
- Gilt **nur im lokalen Netz**. Über Router hinweg zählt die IP-Adresse.

## Wie ein Frame aussieht (vereinfacht)

```
| Ziel-MAC | Quell-MAC | Typ | Daten (Paket) | Prüfsumme |
```

## Der Switch: Wie er denkt

Ein Switch hat eine **MAC-Adresstabelle**:

| Port | MAC |
|---|---|
| 1 | AAAA |
| 2 | BBBB |

1. Frame kommt an Port 1 an, Quelle ist AAAA → Switch merkt: *AAAA liegt an Port 1*.
2. Ziel BBBB bekannt → Frame nur an Port 2.
3. Ziel unbekannt → Frame an alle Ports außer dem Eingangsport (**Flooding**).
4. Broadcast (`FF:FF:FF:FF:FF:FF`) → an alle.

## Kollisionsdomäne und Broadcast-Domäne

- **Kollisionsdomäne**: Bereich, in dem Frames kollidieren können. Jeder Switch-Port ist eine eigene.
- **Broadcast-Domäne**: alle Geräte, die einen Broadcast erhalten. Ein Switch trennt sie *nicht*; ein Router oder VLAN schon.

## ARP: Von der IP zur MAC

Dein PC kennt die IP des Ziels, braucht aber die MAC. Er fragt per Broadcast: *„Wer hat 192.168.1.1?“* Der Besitzer antwortet mit seiner MAC. Die Antworten merkt sich der PC in der **ARP-Tabelle** (`arp -a`).

## VLANs (Vorschau)

Ein Switch kann in mehrere logische Netze getrennt werden, **VLANs**. Geräte in verschiedenen VLANs sehen sich nicht (nur über einen Router). Mehr dazu in der CCNA.

## Das Wichtigste in Kürze

- Die MAC-Adresse gilt nur im lokalen Netz. Über Router hinweg zählt die IP-Adresse.
- Der Switch lernt aus der Absender-MAC und schickt Frames gezielt weiter. Unbekannte Ziele und Broadcasts flutet er.
- ARP findet zu einer IP-Adresse die passende MAC-Adresse.

## Selbsttest

1. Was macht ein Switch mit einem Frame an eine unbekannte MAC?
2. Wozu dient ARP?
3. Wie viele Kollisionsdomänen hat ein Switch mit 8 Ports?

<details><summary>Antworten</summary>

1. **Er schickt ihn an alle Ports außer dem, an dem er ankam (Flooding).** Antwortet das Ziel, lernt der Switch dessen Port und schickt ab dann gezielt.
2. **Um zu einer IP-Adresse die MAC-Adresse zu finden.** Der PC fragt per Broadcast „Wer hat diese IP?“, der Besitzer antwortet mit seiner MAC.
3. **Acht.** Jeder Switch-Port ist eine eigene Kollisionsdomäne.

</details>

Zurück: [3. Schichtenmodell](03-Schichtenmodell-OSI-TCPIP.md) · Weiter: [5. IP-Adressen](05-IP-Adressen.md)
