"""Annotate the ENCOR CML canvases with role groups and a short task brief."""
import argparse
from pathlib import Path
import re
import textwrap

import yaml


# Objective and roles describe the intended topology in both variants.
# Pass/fail conditions and ticket causes stay in the learner guide and solutions.
CANVAS = {
    "01": ("Multi-Area-OSPFv2 aufbauen und Nachbarschaften sowie Summaries prüfen.",
           ("Area 0", "R1 R2"), ("Area 1", "SW R3 R4")),
    "02": ("IPv4 mit EIGRP und IPv6 mit OSPFv3 auf demselben Netz vergleichen.",
           ("Dual-Stack-Transit", "R1 R2 R3")),
    "03": ("Direkte eBGP-Sitzungen aufbauen und die Pfadwahl gezielt beeinflussen.",
           ("Standort", "R1"), ("Provider", "R2 R3"), ("Gegenstelle", "R4")),
    "04": ("Den ausgewählten Provider mit IP SLA und Tracking überwachen.",
           ("Client-LAN", "H1 H2 SW"), ("Provider", "R2 R3"), ("Messziele", "R4")),
    "05": ("VLAN-Pfade über 802.1Q, LACP und PAgP aufbauen und prüfen.",
           ("Access-Hosts", "H1 H2 H3"), ("Switching", "SW1 SW2 SW3"), ("Gateway", "R1")),
    "06": ("Mit dem bereitstehenden Trunk-Netz Root-Wahl, MST und Schutzfunktionen üben.",
           ("Distribution", "SW1 SW2"), ("Access", "SW3 SW4"), ("Test-Switch", "SW5")),
    "07": ("Die Gateway-Redundanz der drei VLANs prüfen und Ausfälle beobachten.",
           ("Upstream", "R3"), ("Gateway-Paar", "R1 R2"), ("Client-VLANs", "H1 H2 H3 H4")),
    "08": ("Zeit, Syslog und SNMP vom Quellgerät bis zum Empfänger verifizieren.",
           ("Zeitquelle", "R1"), ("Zwischenstation", "R2"), ("Endpunkt", "R3")),
    "09": ("Inside- und Outside-Verkehr verfolgen und NAT-Übersetzungen nachweisen.",
           ("Client-LAN", "PC1 PC2 SW"), ("Edge", "R1"), ("Außen", "ISP"), ("DMZ", "SRV")),
    "10": ("Datenverkehr und Routerzugriff mit ACL und CoPP unterschiedlich behandeln.",
           ("Client-LAN", "PC1 PC2 SW"), ("Edge", "R1"), ("Außen", "ISP"), ("DMZ", "SRV")),
    "11": ("Lokale Anmeldung, Autorisierung und AAA-Fallback getrennt überprüfen.",
           ("Zielrouter", "R1"), ("Admin-Client", "R2")),
    "12": ("Über dem OSPF-Underlay PIM, IGMP und RPF mit zwei Empfängern untersuchen.",
           ("Quelle", "SRC"), ("PIM-Netz", "R1 R2 R3 R4"), ("Empfänger", "REC1 REC2")),
    "13": ("Überlappende Adressen durch getrennte VRFs transportieren und vergleichen.",
           ("Kunden Site 1", "CR1 CB1"), ("Provider", "R1 R2"), ("Kunden Site 2", "CR2 CB2")),
    "14": ("Underlay zuerst prüfen, dann GRE und IPsec anhand von Routing und SAs belegen.",
           ("Site 1", "CE1"), ("Transport", "ISP"), ("Site 2", "CE2")),
    "15": ("EIDs, RLOCs und den Map-Cache anhand von Verkehr zwischen den Sites erklären.",
           ("Site 1", "H1 xTR1"), ("Transport", "CORE"), ("Site 2", "xTR2 H2"), ("Mapping", "MSMR")),
    "16": ("VTEP-Erreichbarkeit prüfen, danach VLAN, VNI und NVE zusammenführen.",
           ("Site 1", "H1 LEAF1"), ("Site 2", "LEAF2 H2")),
    "17": ("DSCP und MQC-Zähler vor und nach der Policy vergleichen.",
           ("Traffic-Quellen", "H1 H2 H3 SW"), ("Policy-Router", "R1"), ("WAN-Ziel", "R2 SRV")),
    "18": ("NetFlow im Cache und per Link-Capture nachweisen. SPAN im Guide bearbeiten.",
           ("Traffic-Quellen", "H1 H2 SW1"), ("Exporter", "R1"), ("Exportziel", "SRV")),
    "19": ("Vom Linux-Client RESTCONF und NETCONF prüfen. Ereignisse auf CSR1 beobachten.",
           ("API-Client", "API-CLIENT"), ("IOS XE", "CSR1"), ("IP-SLA-Ziel", "R2")),
    "23": ("Campus bis Internet prüfen. Für jedes Ticket einen Vorher-Nachher-Beleg sichern.",
           ("Internet", "ISP"), ("Edge", "EDGE"), ("Gateways", "R1 R2"), ("Access", "SW1 SW2 H10 H20")),
    "24": ("Transport, verschlüsseltes Overlay und die Standortpfade schichtweise prüfen.",
           ("Transport", "ISP"), ("Site 1", "R1 H1 H3"), ("Site 2", "R2 H2")),
    "25": ("EIGRP-Nachbarn, Pfadauswahl und Stub-Verhalten gegenüberstellen.",
           ("EIGRP-Domäne", "R1 R2 R3 R4")),
    "26": ("Loopback-Erreichbarkeit prüfen und iBGP-Routen über die internen Peers verfolgen.",
           ("Internes AS", "R1 R2 R3"), ("Provider", "ISP1 ISP2")),
    "27": ("Routen zwischen OSPF und EIGRP übernehmen und Rückverteilung verhindern.",
           ("OSPF-Seite", "R1"), ("Grenzrouter", "R2 R3"), ("EIGRP-Seite", "R4")),
    "28": ("Area-Typen, LSA-Ausgaben und Summaries Schritt für Schritt vergleichen.",
           ("Backbone", "R1 R2"), ("Area 1", "R3"), ("Area 2", "R4")),
    "29": ("Referenzpfade ohne PBR messen und danach Quelle und Anwendung vergleichen.",
           ("Client-LAN", "H1 H2 SW"), ("Branch", "R1"), ("Provider", "R2 R3"), ("Dienst", "R4")),
    "30": ("Routing-Fehler von den Nachbarschaften bis zur Ende-zu-Ende-Route eingrenzen.",
           ("Provider", "ISP"), ("Edge", "R1"), ("Interne Router", "R2 R3 R4")),
    "31": ("MST-Regionen und PVST-Übergang anhand von Root- und Boundary-Port-Ausgaben prüfen.",
           ("Distribution", "DS1 DS2"), ("Access", "AS1 AS2 H1 H2"), ("PVST-Seite", "LEG1 H3")),
    "32": ("SSM, Bidir und Anycast-RP getrennt aufbauen und Multicast-Zustände vergleichen.",
           ("Quelle", "SRC"), ("Multicast-Netz", "R1 R2 R3 R4"), ("Empfänger", "REC")),
    "33": ("Vom Client zum Dienst messen und ICMP-Befunde mit Debug-Ausgaben abgleichen.",
           ("Start", "H1"), ("Transit", "R1 R2 R3"), ("Dienst", "SRV")),
    "34": ("Nachbarschaften, LSDB und Routing-Tabelle beim Filtern getrennt beurteilen.",
           ("Area 1", "R3"), ("ABRs", "R2 R1"), ("Area 2", "R4")),
    "35": ("IP-SLA-Messungen und die Umschaltung zwischen zwei Provider-Pfaden belegen.",
           ("Client", "H1"), ("Messrouter", "R1"), ("Provider", "R2 R3"), ("Messziele", "R4")),
    "36": ("EEM-Applets auslösen und an Konsole, Syslog und Dateisystem verifizieren.",
           ("Applet-Router", "R1"), ("Testpartner", "R2")),
}

PALETTE = (
    ("#2563EBFF", "#60A5FA28"),
    ("#0F766EFF", "#2DD4BF28"),
    ("#A05C10FF", "#FBBF2428"),
    ("#7E22CEFF", "#C084FC28"),
)


def rectangle(left, top, right, bottom, border, fill):
    return {
        "type": "rectangle", "x1": left, "y1": top, "x2": right, "y2": bottom,
        "color": fill, "border_color": border, "border_style": "", "border_radius": 12,
        "thickness": 2, "rotation": 0, "z_index": 0,
    }


def label(text, x, y, size, *, bold=False, color="#203653FF"):
    return {
        "type": "text", "text_content": text, "x1": x, "y1": y, "color": color,
        "border_color": "#00000000", "border_style": "", "thickness": 1,
        "rotation": 0, "text_bold": bold, "text_italic": False, "text_font": "sans-serif",
        "text_size": size, "text_unit": "pt", "z_index": 1,
    }


def build_annotations(doc, number, repair):
    objective, *groups = CANVAS[number]
    positions = {node["label"]: (node["x"], node["y"]) for node in doc["nodes"]}
    left = min(x for x, _ in positions.values()) - 54
    top = min(y for _, y in positions.values()) - 190
    right = max(max(x for x, _ in positions.values()) + 54, left + 800)
    mode = "Teil B · Reparieren" if repair else "Teil A · Bauen"
    tip = ("Ticket im Guide lesen → Symptom reproduzieren → Fix verifizieren"
           if repair else "Guide öffnen → Ausgangslage prüfen → Aufgabe lösen")
    accent = ("#A05C10FF", "#FFF4DEFA") if repair else ("#2563EBFF", "#EAF2FFFA")
    title_lines = textwrap.wrap(doc["lab"]["title"].removesuffix(" (Repair)"), width=69)
    extra_height = 20 * (len(title_lines) - 1)
    top -= extra_height
    annotations = [
        rectangle(left, top, right, top + 120 + extra_height, *accent),
        label(mode, left + 16, top + 9, 10, bold=True),
        label("\n".join(title_lines), left + 16, top + 30, 14, bold=True),
        label(objective, left + 16, top + 62 + extra_height, 11),
        label(tip, left + 16, top + 89 + extra_height, 10),
    ]
    for (name, members), (border, fill) in zip(groups, PALETTE):
        xs, ys = zip(*(positions[node] for node in members.split()))
        x1, y1, x2, y2 = min(xs) - 46, min(ys) - 56, max(xs) + 46, max(ys) + 42
        x2 = max(x2, x1 + 18 + len(name) * 7)
        annotations.extend([
            rectangle(x1, y1, x2, y2, border, fill),
            label(name, x1 + 9, y1 + 7, 10, bold=True),
        ])
    return annotations


CURRICULUM = Path(__file__).resolve().parents[1] / "CML-Labs" / "AUFGABEN.md"


def learner_guide(readme, number, repair):
    curriculum = CURRICULUM.read_text(encoding="utf-8")
    task = re.search(rf"^## Lab {number} — [^\n]+\n[\s\S]*?(?=^## Lab |\Z)", curriculum, re.M)
    if not task:
        raise ValueError(f"Keine Curriculum-Aufgabe für Lab {number}")
    if repair:
        tickets = re.findall(r"^\*\*Ticket \d+(?: \(Papier\))?:\*\* .+$", readme, re.M)
        if number == "36":
            tickets = [
                "**Ticket 1:** Nach dem Speichern wird die Sicherung gemeldet. Die Sicherungsdatei fehlt.",
                "**Ticket 2:** Nach dem dritten Ausfall des Testpfads wird der Eingriff gemeldet. Der Testpfad bleibt aktiv.",
                "**Ticket 3:** Beim Abbruch einer OSPF-Nachbarschaft läuft die vorgesehene Diagnose nicht.",
                "**Ticket 4:** Der Router meldet die Sperre eines Debug-Befehls. Trotzdem werden die Debugs aktiviert.",
            ]
        brief = task.group().strip() + "\n\n" if number in {"23", "24", "30"} else ""
        bootstrap = ("Bei Lab 19 zuerst den dokumentierten Client- und SSH-Bootstrap ausführen.\n\n"
                     if number == "19" else "")
        return (brief + "## Reparieren\n\n" + bootstrap + "Importiere diese Datei als separates Lab. Reproduziere pro "
                "Ticket das Symptom, dokumentiere den Befund und belege die Wirkung der Korrektur. "
                "Stelle den Testzustand nach jedem Versuch wieder her.\n\n"
                + "\n\n".join(tickets)
                + "\n\nDie Topologiedaten, gestufte Hinweise und Lösungen findest du in den Lab-Unterlagen.")
    return task.group().strip()


def annotate(path):
    original = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(original)
    repair = path.name == "topology-repair.yaml"
    number = path.parent.name[:2]
    guide = learner_guide((path.parent / "README.md").read_text(encoding="utf-8"), number, repair)
    notes = "  notes: |-\n" + "\n".join("    " + line if line else "" for line in guide.splitlines())
    # Preserve existing CLI and link formatting when adding notes and visual annotations.
    changed, count = re.subn(r"^  notes:[^\n]*\n(?:    [^\n]*\n|\n)*",
                             lambda _: notes + "\n", original, count=1, flags=re.M)
    if not count:
        raise ValueError(f"Kein lab.notes-Feld in {path}")
    # Remove the previous generated block on repeat runs.
    changed = re.split(r"^annotations:\s*$", changed, maxsplit=1, flags=re.M)[0].rstrip()
    data = {"annotations": build_annotations(doc, path.parent.name[:2], repair)}
    changed += "\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10000)
    result = yaml.safe_load(changed)
    if result["lab"]["notes"].strip() != guide or result["nodes"] != doc["nodes"] or result["links"] != doc["links"]:
        raise ValueError(f"Anmerkungen oder Topologie stimmen nicht: {path}")
    if changed != original:
        path.write_text(changed, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labs", nargs="*", help="Optionale Lab-Nummern, z. B. 06 18")
    args = parser.parse_args()
    cml = Path(__file__).resolve().parents[1] / "CML-Labs"
    for name in ("topology.yaml", "topology-repair.yaml"):
        for path in sorted(cml.glob(f"*/{name}")):
            if not args.labs or path.parent.name[:2] in args.labs:
                annotate(path)


if __name__ == "__main__":
    main()
