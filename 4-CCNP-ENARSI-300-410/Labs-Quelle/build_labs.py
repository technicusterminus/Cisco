#!/usr/bin/env python3
"""Erzeugt alle ENARSI-Labs (CML und EVE-NG) aus den Definitionen lab_*.py.

Aufruf:  python3 build_labs.py          (benötigt: pip install pyyaml)
Schreibt in ../CML-Labs und ../EVE-NG-Labs. Prüft dabei, dass jeder Fehler auf eine vorhandene
Konfigurationszeile trifft, dass die Links auf freie, vorhandene Interfaces zeigen und dass die
Tickets zur Fehlerliste passen.
"""
import glob, importlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lablib

ROOT = os.path.dirname(HERE)

ZIEL_NAMEN = {"1.8": "BFD", "2.1": "MPLS", "2.2": "MPLS L3VPN", "2.3": "DMVPN", "3.2.c": "uRPF", "3.4": "IPv6 First Hop Security",
              "4.4": "DHCP"}


def ram(lab):
    return sum(lablib.EVE_TPL[n["type"]][1] for n in lab["nodes"]) / 1000


def nodes(lab):
    return sum(1 for n in lab["nodes"] if n["type"] != "switch")


def goals_of(lab):
    return ", ".join(t for t, _, _ in lab["tags"])


def overview(labs, plat):
    out = ["| Lab | Thema | Ziele | Geräte | Fehler | " + ("RAM (Richtwert) | " if plat == "eve" else "") + "Dauer |",
           "|---|---|---|---|---|" + ("---|" if plat == "eve" else "") + "---|"]
    for l in labs:
        out.append(f"| [{l['num']}]({l['slug']}/) | {l['title']} | {goals_of(l)} | {len(l['nodes'])} | {len(l['faults'])} | "
                   + (f"{ram(l):.1f} GB | " if plat == "eve" else "") + f"{l['minutes']} min |")
    return "\n".join(out)


def coverage(labs):
    rows = ["| Ziel | Thema | Karten | Lab |", "|---|---|---|---|"]
    items = [(t, th, c, l) for l in labs for t, th, c in l["tags"]]
    items.sort(key=lambda x: [int(p) if p.isdigit() else ord(p[0]) for p in x[0].split(".")])
    for t, th, c, l in items:
        rows.append(f"| `{t}` | {th} | {c} | [{l['num']}]({l['slug']}/) |")
    return "\n".join(rows)


CML_README = """# CCNP ENARSI 300-410 – Labs (CML)

Diese Labs ergänzen das [Anki-Deck](../Anki/) zum Thema **VPN, Security und Services**, für die es im ENCOR-Paket keine eigenen Labs gibt: DMVPN Phase 3, MPLS L3VPN, BFD, uRPF, DHCP-Relay und IPv6 First Hop Security. Alle anderen ENARSI-Themen (EIGRP, OSPF, BGP, Redistribution, PBR, VRF-Lite, AAA, ACL, CoPP, SNMP, Syslog, NetFlow …) übst du mit den [ENCOR-Labs](../README.md#passende-labs-aus-dem-encor-paket).

**Inhalt:** {n} Labs mit zusammen {f} eingebauten Fehlern zum Reparieren. **Andere Plattform:** dieselben Labs für [EVE-NG](../EVE-NG-Labs/). Packet Tracer ist hier nicht dabei, weil es DMVPN, MPLS, BFD und uRPF nicht ausreichend abbildet.

## So ist jedes Lab aufgebaut

| Datei | Zweck |
|---|---|
| `topology.yaml` | **Bauen:** Topologie mit Basis-Konfiguration (Hostnamen, IP-Adressen). Das Routing und die Funktion baust du selbst. |
| `topology-repair.yaml` | **Reparieren:** komplett gebaute Topologie mit eingebauten Fehlern. Die Tickets stehen im README, die Auflösung in `solutions/FAULTS.md`. |
| `README.md` | Teil A Aufgaben, Teil B Tickets, Verifikation, Teil C Transferfragen mit Antworten, Prüfungsbezug |
| `solutions/*.cfg` | Musterlösung je Gerät (ohne Basis-IP-Adressen) |

## So arbeitest du ein Lab durch

1. **Teil A: Bauen.** Importiere `topology.yaml`, arbeite die Schritte ab und prüfe jeden Schritt mit den Befehlen aus „Prüfen“. Erst am Ende vergleichst du mit `solutions/`.
2. **Teil B: Reparieren.** Am besten an einem anderen Tag. Importiere `topology-repair.yaml`, lies das Ticket und gehe vor wie im Betrieb: Symptom nachstellen, eingrenzen, beheben, verifizieren. Erst nach 20 Minuten ohne Fortschritt in `solutions/FAULTS.md` schauen. Dort steht pro Ticket zuerst, mit welchem Befehl du den Fehler gefunden hättest, dann Ursache und Lösung.
3. **Teil C: Üben.** Beantworte die Transferfragen erst selbst, dann klappst du die Antwort auf.
4. **Nacharbeiten.** Wiederhole im Anki-Deck die Karten zum Ziel des Labs (`tag:Ziel::…`), besonders zu den Fehlern, die du nicht gefunden hast.

## Übersicht

{overview}

## Abdeckung nach Prüfungsziel

{coverage}

## Voraussetzungen und Stand

- **Images:** IOSv (15.x) für alle Labs, zusätzlich IOSvL2 für Lab E6. Die Images sind lizenzpflichtig und kommen nicht mit.
- **Geprüft per Skript:** Das YAML lädt, alle Links zeigen auf vorhandene und freie Interfaces, jeder eingebaute Fehler trifft genau eine Konfigurationszeile, die Tickets passen zur Fehlerliste, und die Adressen an jedem Link liegen im selben Subnetz. **In einer laufenden CML-Instanz sind die Labs noch nicht durchgespielt.** Die Befehle folgen der IOS-15-Dokumentation; die Ausgaben in „Prüfen“ und „So findest du es“ sind aus der Funktionsweise abgeleitet und können in Details abweichen.
- **Wenn ein Befehl nicht durchgeht:** Image-Versionen unterscheiden sich. Prüfe die Syntax in der Cisco-Dokumentation. Das ist gleich eine gute Übung. Eine Korrektur per Issue hilft allen.
- **Sonderfälle:** E3 (BFD) bleibt bei 300 ms, weil virtuelle Router keine kürzeren Timer stabil schaffen. E6 (IPv6 FHS) hängt am Switch-Image: Kennt dein IOSvL2 RA Guard oder DHCPv6 Guard nicht, lies das Lab als Konfigurations- und Denkaufgabe.

## Selbst ändern oder neu erzeugen

Die Labs entstehen aus den Definitionen in [`../Labs-Quelle`](../Labs-Quelle/). Eine Änderung an einer Definition und `python3 build_labs.py` erzeugen CML-Dateien, EVE-NG-Dateien, Fehlerliste und Diff neu, sie bleiben also immer konsistent.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter sind reine Lab-Werte.

> Kein offizielles Cisco-Material. Cisco, CCNP und ENARSI sind Marken von Cisco Systems, Inc.
"""

EVE_README = """# CCNP ENARSI 300-410 – Labs (EVE-NG)

Parallelzweig zu den [CML-Labs](../CML-Labs/) für **EVE-NG**: dieselben {n} Labs mit denselben Aufgaben (Bauen, Reparieren, Üben), Fehlerlisten und Lösungen. Die Geräte (vIOS, vIOS-L2) tragen dieselben Interface-Namen wie in CML, deshalb gelten Aufgabentexte und Konfigurationen unverändert. Dazu kommen Node- und Kabeltabellen mit EVE-Templates, der RAM-Bedarf und Konfigurationsdateien zum Einspielen.

**Inhalt:** {n} Labs, {f} eingebaute Fehler. Welche ENARSI-Themen die ENCOR-Labs abdecken, steht in der [ENARSI-Übersicht](../README.md#passende-labs-aus-dem-encor-paket).

## Voraussetzungen

- EVE-NG (Community oder Pro) mit den Images **vIOS** und für Lab E6 **vIOS-L2** (aus Ciscos IOSv-/IOSvL2-Paketen). Die Images sind lizenzpflichtig und kommen nicht mit; Installation nach der EVE-NG-Anleitung.
- RAM: Die Tabelle unten zeigt den Bedarf je Lab als Richtwert, er liegt bei 1.5 bis 3 GB.

## Arbeiten mit den Dateien

EVE-NG kann Startkonfigurationen nicht als Datei importieren. Pro Lab geht es so:

1. **Lab anlegen.** Neues Lab in EVE-NG, Nodes laut Tabelle „Nodes“ platzieren (Template wie angegeben), Kabel laut Tabelle „Verkabelung“ ziehen. Das Network-Objekt (*Bridge*) steht für den unmanaged Switch aus CML.
2. **Nodes starten**, bis ein Prompt (`Router>`/`Switch>`) erscheint.
3. **Ausgangszustand einspielen.** Entweder per Hand: Konsole öffnen, `enable`, `configure terminal`, Inhalt von `build/<Node>.cfg` einfügen, `end`, `write memory`. Oder mit dem Hilfsskript [`tools/eve_push_configs.py`](tools/eve_push_configs.py), das die Dateien per Telnet-Konsole tippt:
   `python3 tools/eve_push_configs.py <EVE-IP> <Lab-Ordner> --mode build --ports R1=32769 R2=32770 …`
   Die Telnet-Ports zeigt EVE-NG je Node an. `--dry-run` zeigt nur an, was gesendet würde.
4. **Teil A** selbst bauen und jeden Schritt mit den Befehlen aus „Prüfen“ kontrollieren. Erst am Ende mit `solutions/<Node>.cfg` vergleichen.
5. **Teil B (Reparieren).** Nodes per Rechtsklick *Wipe* zurücksetzen und `repair/<Node>.cfg` einspielen (`--mode repair`). Tickets wie im Betrieb abarbeiten. Erst nach 20 Minuten ohne Fortschritt in `solutions/FAULTS.md` schauen.
6. **Stand sichern.** Wenn dein Image es unterstützt, speichert *Export CFG* den Zustand als Startkonfiguration im Lab.
7. **Hosts.** Standardmäßig vIOS wie in CML. Alternative VPCS (spart RAM) nur dort, wo das Lab es erlaubt: Zeile aus `vpcs/<Host>.vpc` in der VPCS-Konsole eingeben.

## Übersicht

{overview}

## Abdeckung nach Prüfungsziel

{coverage}

## Stand

- **Geprüft per Skript:** Die Labs entstehen aus derselben Definition wie die CML-Labs, mit denselben Geräten, Kabeln, Konfigurationen und Fehlern. Das Skript prüft, dass alle Links auf vorhandene Interfaces zeigen, kein Port doppelt belegt ist und jeder Fehler in der Konfiguration steckt. In einer laufenden EVE-NG-Instanz sind die Labs noch nicht durchgespielt.
- **Templates und RAM** sind Richtwerte.
- **Das Hilfsskript** stammt aus dem ENCOR-Paket und ist gegen simulierte Telnet-Konsolen getestet. Klappt es bei dir nicht, füge die Dateien per Copy and Paste ein.
- **Sonderfälle:** Lab E3 bleibt bei BFD-Timern ab 300 ms; Lab E6 braucht vIOS-L2 mit RA Guard und DHCPv6 Guard und vIOS-Hosts (kein VPCS).

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter sind reine Lab-Werte.

> Kein offizielles Cisco-Material. Cisco, CCNP und ENARSI sind Marken von Cisco Systems, Inc.
"""


def main():
    labs = []
    for f in sorted(glob.glob(os.path.join(HERE, "lab_e*.py"))):
        labs.append(importlib.import_module(os.path.basename(f)[:-3]).LAB)
    for lab in labs:
        lablib.render(lab, ROOT)
        print(f"{lab['num']:3} {lab['slug']:34} {len(lab['nodes'])} Nodes, {len(lab['faults'])} Fehler")
    n, f = len(labs), sum(len(l["faults"]) for l in labs)
    lablib.write(os.path.join(ROOT, "CML-Labs", "README.md"),
                 CML_README.format(n=n, f=f, overview=overview(labs, "cml"), coverage=coverage(labs)))
    lablib.write(os.path.join(ROOT, "EVE-NG-Labs", "README.md"),
                 EVE_README.format(n=n, f=f, overview=overview(labs, "eve"), coverage=coverage(labs)))
    return labs

if __name__ == "__main__":
    main()
