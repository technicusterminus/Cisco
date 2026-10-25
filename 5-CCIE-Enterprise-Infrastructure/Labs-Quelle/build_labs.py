#!/usr/bin/env python3
"""Erzeugt alle CCIE-Labs (CML und EVE-NG) aus den Definitionen lab_c*.py.

Aufruf:  python3 build_labs.py          (benötigt: pip install pyyaml)
Schreibt in ../CML-Labs und ../EVE-NG-Labs. Prüft dabei, dass jeder Fehler auf eine vorhandene
Konfigurationszeile trifft, dass die Links auf freie, vorhandene Interfaces zeigen, dass die Adressen
an jedem Link im selben Netz liegen, dass keine Adresse doppelt vorkommt, dass Nachbar- und Peer-Adressen
im Lab existieren und dass die Tickets zur Fehlerliste passen.
"""
import glob, importlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lablib

ROOT = os.path.dirname(HERE)


def ram(lab):
    return sum(lablib.EVE_TPL[n["type"]][1] for n in lab["nodes"]) / 1000


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
    items = {}
    for l in labs:
        for t, th, c in l["tags"]:
            items.setdefault(t, [th, c, []])[2].append(f"[{l['num']}]({l['slug']}/)")
    for t in sorted(items, key=lambda x: [int(p) if p.isdigit() else ord(p[0]) for p in x.split(".")]):
        th, c, ls = items[t]
        rows.append(f"| `{t}` | {th} | {c} | {', '.join(ls)} |")
    return "\n".join(rows)


INTRO = ("Diese Labs gehen über ENCOR und ENARSI hinaus. Sie behandeln, was im CCIE-Blueprint dazukommt: BGP mit "
         "AS-Pfad-Manipulation und bedingter Ankündigung, Multicast mit Anycast RP und MSDP, OSPF mit Virtual Link und NSSA, "
         "MPLS L3VPN mit Shared Services, DMVPN mit IKEv2 und BGP sowie EIGRP im Named Mode. Die Grundlagen übst du mit den "
         "Labs aus ENCOR und ENARSI, die Zuordnung steht im [CCIE-README](../README.md#passende-labs-aus-encor-und-enarsi).")

CML_README = """# CCIE Enterprise Infrastructure – Labs (CML)

{intro}

**Inhalt:** {n} Labs mit zusammen {f} eingebauten Fehlern zum Reparieren, jedes mit höchstens fünf Geräten. **Andere Plattform:** dieselben Labs für [EVE-NG](../EVE-NG-Labs/).

## So ist jedes Lab aufgebaut

| Datei | Zweck |
|---|---|
| `topology.yaml` | **Bauen:** Topologie mit Basis-Konfiguration (Hostnamen, IP-Adressen, teils das Underlay). Die Funktion des Labs baust du selbst. |
| `topology-repair.yaml` | **Reparieren:** komplett gebaute Topologie mit eingebauten Fehlern. Die Tickets stehen im README, die Auflösung in `solutions/FAULTS.md`. |
| `README.md` | Teil A Aufgaben, Teil B Tickets, Verifikation, Teil C Transferfragen mit Antworten, Prüfungsbezug |
| `solutions/*.cfg` | Musterlösung je Gerät (ohne Basis-Konfiguration) |

## So arbeitest du ein Lab durch

1. **Teil A: Bauen.** Importiere `topology.yaml`, arbeite die Schritte ab und prüfe jeden Schritt mit den Befehlen aus „Prüfen“. Erst am Ende vergleichst du mit `solutions/`.
2. **Teil B: Reparieren.** Am besten an einem anderen Tag. Importiere `topology-repair.yaml` und arbeite die Tickets ab wie im Betrieb: Symptom nachstellen, eingrenzen, beheben, verifizieren. In der Labprüfung zählt Tempo, deshalb mit Zeitlimit: **höchstens 10 Minuten pro Ticket**, dann in `solutions/FAULTS.md` nachsehen. Dort steht pro Ticket zuerst, mit welchem Befehl du den Fehler gefunden hättest, dann Ursache und Lösung.
3. **Teil C: Üben.** Beantworte die Transferfragen erst selbst, dann klappst du die Antwort auf.
4. **Nacharbeiten.** Wiederhole im [Anki-Deck](../Anki/) die Karten zum Ziel des Labs (`tag:Ziel::…`), besonders zu den Fehlern, die du nicht gefunden hast.

## Übersicht

{overview}

## Abdeckung nach Prüfungsziel

{coverage}

## Voraussetzungen und Stand

- **Images:** IOSv (15.x) für alle Geräte, auch für die Hosts im Multicast-Lab. Die Images sind lizenzpflichtig und kommen nicht mit.
- **Geprüft per Skript:** Das YAML lädt, alle Links zeigen auf vorhandene und freie Interfaces, die Adressen an jedem Link liegen im selben Netz, keine Adresse ist doppelt vergeben (außer der gewollten Anycast-Adresse), jede Nachbar-, Peer- und RP-Adresse existiert im Lab, jeder eingebaute Fehler trifft genau eine Konfigurationszeile, und die Tickets passen zur Fehlerliste. **In einer laufenden CML-Instanz sind die Labs noch nicht durchgespielt.** Die Befehle folgen der IOS-15-Dokumentation; die Ausgaben in „Prüfen“ und „So findest du es“ sind aus der Funktionsweise abgeleitet und können in Details abweichen.
- **Wenn ein Befehl nicht durchgeht:** Image-Versionen unterscheiden sich. Prüfe die Syntax in der Cisco-Dokumentation. Das ist gleich eine gute Übung. Eine Korrektur per Issue hilft allen.
- **Nicht dabei:** SD-Access und SD-WAN (Domäne 2) brauchen Controller, die sich mit IOSv nicht nachbauen lassen. Dafür gibt es Karten im Deck und Fragen in der [Prüfungssimulation](../Pruefungssimulation/).

## Selbst ändern oder neu erzeugen

Die Labs entstehen aus den Definitionen in [`../Labs-Quelle`](../Labs-Quelle/). Eine Änderung an einer Definition und `python3 build_labs.py` erzeugen CML-Dateien, EVE-NG-Dateien, Fehlerliste und Diff neu, sie bleiben also immer konsistent.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter und Schlüssel sind reine Lab-Werte.

> Kein offizielles Cisco-Material. Cisco und CCIE sind Marken von Cisco Systems, Inc.
"""

EVE_README = """# CCIE Enterprise Infrastructure – Labs (EVE-NG)

Parallelzweig zu den [CML-Labs](../CML-Labs/) für **EVE-NG**: dieselben {n} Labs mit denselben Aufgaben (Bauen, Reparieren, Üben), Fehlerlisten und Lösungen. Die Geräte (vIOS) tragen dieselben Interface-Namen wie in CML, deshalb gelten Aufgabentexte und Konfigurationen unverändert. Dazu kommen Node- und Kabeltabellen mit EVE-Templates, der RAM-Bedarf und Konfigurationsdateien zum Einspielen.

{intro}

**Inhalt:** {n} Labs, {f} eingebaute Fehler.

## Voraussetzungen

- EVE-NG (Community oder Pro) mit dem Image **vIOS** (aus Ciscos IOSv-Paket). Das Image ist lizenzpflichtig und kommt nicht mit; Installation nach der EVE-NG-Anleitung.
- RAM: Die Tabelle unten zeigt den Bedarf je Lab als Richtwert, er liegt bei 2 bis 2.6 GB.

## Arbeiten mit den Dateien

EVE-NG kann Startkonfigurationen nicht als Datei importieren. Pro Lab geht es so:

1. **Lab anlegen.** Neues Lab in EVE-NG, Nodes laut Tabelle „Nodes“ platzieren (Template wie angegeben), Kabel laut Tabelle „Verkabelung“ ziehen.
2. **Nodes starten**, bis ein Prompt (`Router>`) erscheint.
3. **Ausgangszustand einspielen.** Entweder per Hand: Konsole öffnen, `enable`, `configure terminal`, Inhalt von `build/<Node>.cfg` einfügen, `end`, `write memory`. Oder mit dem Hilfsskript [`tools/eve_push_configs.py`](tools/eve_push_configs.py), das die Dateien per Telnet-Konsole tippt:
   `python3 tools/eve_push_configs.py <EVE-IP> <Lab-Ordner> --mode build --ports R1=32769 R2=32770 …`
   Die Telnet-Ports zeigt EVE-NG je Node an. `--dry-run` zeigt nur an, was gesendet würde.
4. **Teil A** selbst bauen und jeden Schritt mit den Befehlen aus „Prüfen“ kontrollieren. Erst am Ende mit `solutions/<Node>.cfg` vergleichen.
5. **Teil B (Reparieren).** Nodes per Rechtsklick *Wipe* zurücksetzen und `repair/<Node>.cfg` einspielen (`--mode repair`). Tickets wie im Betrieb abarbeiten, mit Zeitlimit: höchstens 10 Minuten pro Ticket, dann in `solutions/FAULTS.md` nachsehen.
6. **Stand sichern.** Wenn dein Image es unterstützt, speichert *Export CFG* den Zustand als Startkonfiguration im Lab.

## Übersicht

{overview}

## Abdeckung nach Prüfungsziel

{coverage}

## Stand

- **Geprüft per Skript:** Die Labs entstehen aus derselben Definition wie die CML-Labs, mit denselben Geräten, Kabeln, Konfigurationen und Fehlern. Das Skript prüft Verkabelung, Adressen und Fehlermuster. In einer laufenden EVE-NG-Instanz sind die Labs noch nicht durchgespielt.
- **Templates und RAM** sind Richtwerte.
- **Das Hilfsskript** stammt aus dem ENCOR-Paket und ist gegen simulierte Telnet-Konsolen getestet. Klappt es bei dir nicht, füge die Dateien per Copy and Paste ein.
- **Hosts:** SRC und RCV im Multicast-Lab C2 bleiben vIOS, weil VPCS keinen Multicast-Gruppen beitreten kann.

Alle Adressen stammen aus Privat- oder Dokumentationsbereichen, Passwörter und Schlüssel sind reine Lab-Werte.

> Kein offizielles Cisco-Material. Cisco und CCIE sind Marken von Cisco Systems, Inc.
"""


def main():
    labs = []
    for f in sorted(glob.glob(os.path.join(HERE, "lab_c*.py"))):
        labs.append(importlib.import_module(os.path.basename(f)[:-3]).LAB)
    for lab in labs:
        lablib.render(lab, ROOT)
        print(f"{lab['num']:3} {lab['slug']:34} {len(lab['nodes'])} Nodes, {len(lab['faults'])} Fehler")
    n, f = len(labs), sum(len(l["faults"]) for l in labs)
    lablib.write(os.path.join(ROOT, "CML-Labs", "README.md"),
                 CML_README.format(intro=INTRO, n=n, f=f, overview=overview(labs, "cml"), coverage=coverage(labs)))
    lablib.write(os.path.join(ROOT, "EVE-NG-Labs", "README.md"),
                 EVE_README.format(intro=INTRO, n=n, f=f, overview=overview(labs, "eve"), coverage=coverage(labs)))
    return labs


if __name__ == "__main__":
    main()
