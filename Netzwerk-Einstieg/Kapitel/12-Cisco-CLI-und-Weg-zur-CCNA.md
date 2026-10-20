# 12. Cisco-CLI und der Weg zur CCNA

## Die Befehlszeile (CLI)

Router und Switches von Cisco bedient man über eine Textkonsole.

| Modus | Prompt | Wie hinein |
|---|---|---|
| Benutzermodus | `Switch>` | Beim Login |
| Privilegierter Modus | `Switch#` | `enable` |
| Globaler Konfigurationsmodus | `Switch(config)#` | `configure terminal` |
| Interface-Konfiguration | `Switch(config-if)#` | `interface gigabitEthernet 0/1` |

Zurück: `exit` (eine Ebene) oder `end` (direkt in den privilegierten Modus).

## Die ersten Befehle

```
enable
configure terminal
hostname SW1
interface vlan 1
 ip address 192.168.1.2 255.255.255.0
 no shutdown
 exit
enable secret MeinGeheim!
end
copy running-config startup-config
```

- **running-config** = aktuelle Konfiguration (im RAM).
- **startup-config** = gespeicherte (beim Start geladen).
- Ohne `copy running-config startup-config` ist nach dem Neustart alles weg.

## Hilfe in der CLI

- `?` zeigt die möglichen Befehle.
- `Tab` ergänzt Befehle.
- Abkürzungen gehen: `sh ip int br`.
- Fehlermeldung `% Invalid input detected` heißt: Tippfehler oder falscher Modus.

## Die wichtigsten Show-Befehle

| Befehl | Zeigt |
|---|---|
| `show running-config` | Aktuelle Konfiguration |
| `show ip interface brief` | Interfaces, IPs, Status |
| `show interfaces status` | Ports, VLAN, Speed, Duplex |
| `show vlan brief` | VLANs und Access-Ports |
| `show mac address-table` | MAC-Adresstabelle |
| `show ip route` | Routing-Tabelle |

## Wie es weitergeht

```
Dieses Einsteigerpaket
        ↓
CCNA 200-301  (Netzwerkgrundlagen, Switching, Routing, Dienste, Security, Automation)
        ↓
CCNP ENCOR 350-401  (Enterprise-Core)
```

- Für die CCNA findest du im Repo: [Anki-Deck, Packet-Tracer-Labs, Subnetting-Trainer, Prüfungssimulation und Lernplan](../../CCNA%20200-301%20Vorbereitung/).
- Danach geht es mit dem [CCNP-ENCOR-Paket](../../CCNP%20ENCORv1.2%20Vorbereitung/) weiter.

## Selbsttest

1. Was ist der Unterschied zwischen running-config und startup-config?
2. Wie wechselst du vom Benutzermodus in den privilegierten Modus?
3. Welcher Befehl zeigt alle Interfaces mit IP und Status?

<details><summary>Antworten</summary>

1. Running-Config läuft im RAM, Startup-Config ist gespeichert und wird beim Start geladen.
2. `enable`.
3. `show ip interface brief`.
</details>

Zurück: [11. Fehlersuche](11-Fehlersuche.md) · [Zur Übersicht](../README.md)
