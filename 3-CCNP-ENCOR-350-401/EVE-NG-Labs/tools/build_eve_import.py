#!/usr/bin/env python3
"""Erzeugt importierbare EVE-NG-Labs (.unl in .zip) aus den CML-Topologien.

Quelle je Lab:
  - Topologie (Nodes, Verkabelung, Positionen): CML-Labs/<Lab>/topology.yaml
  - Startkonfigurationen: EVE-NG-Labs/<Lab>/build/*.cfg und repair/*.cfg

Ergebnis je Lab zwei EVE-Labs, „Bauen“ und „Reparieren“, mit eingebetteter
Startkonfiguration. Abgelegt werden:
  - EVE-NG-Labs/<Lab>/EVE-Import.zip      (nur dieses Lab)
  - EVE-NG-Labs/<Paket>-EVE-NG-Labs.zip   (alle Labs des Pakets)

Aufruf (aus dem Paketordner, z. B. „3-CCNP-ENCOR-350-401“):
  python3 EVE-NG-Labs/tools/build_eve_import.py --paket ENCOR

Die Images werden bewusst nicht eingetragen. Ohne Image-Angabe nimmt EVE-NG
beim Laden das neueste installierte Image des Templates, damit passt das Lab
zu jeder Installation.
"""
import argparse
import base64
import glob
import os
import re
import sys
import uuid
import zipfile
from xml.sax.saxutils import quoteattr, escape

import yaml

NS = uuid.UUID("6f1c2b8e-3d4a-4f5b-9c7d-1e2f3a4b5c6d")

# CML-Node-Typ -> EVE-Template, RAM (MB), CPU, Mindestzahl Interfaces, Icon
TEMPLATES = {
    "iosv": ("vios", 512, 1, 4, "Router.png"),
    "iosvl2": ("viosl2", 768, 1, 8, "Switch L3.png"),
    "csr1000v": ("csr1000vng", 4096, 1, 4, "Router.png"),
    "nxosv9000": ("nxosv9k", 8192, 2, 8, "Switch L3.png"),
}
HOST_RE = re.compile(r"^(H|PC|HOST|SRV|CLIENT)\d*$", re.I)


def eve_if(node_def, label):
    """CML-Interfacename -> (EVE-Interface-Index, EVE-Anzeigename)."""
    if node_def == "iosv":
        m = re.fullmatch(r"GigabitEthernet0/(\d+)", label)
        if m:
            i = int(m.group(1))
            return i, f"Gi0/{i}"
    elif node_def == "iosvl2":
        m = re.fullmatch(r"GigabitEthernet(\d+)/(\d+)", label)
        if m and int(m.group(2)) < 4:
            a, b = int(m.group(1)), int(m.group(2))
            return a * 4 + b, f"Gi{a}/{b}"
    elif node_def == "csr1000v":
        m = re.fullmatch(r"GigabitEthernet(\d+)", label)
        if m and int(m.group(1)) >= 1:
            i = int(m.group(1))
            return i - 1, f"Gi{i}"
    elif node_def == "nxosv9000":
        if label.lower() == "mgmt0":
            return 0, "Mgmt0"
        m = re.fullmatch(r"Ethernet1/(\d+)", label)
        if m:
            i = int(m.group(1))
            return i, f"e1/{i}"
    raise ValueError(f"Interface {label} auf {node_def} nicht abbildbar")


def read_cfg(lab_dir, mode, label):
    p = os.path.join(lab_dir, mode, f"{label}.cfg")
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    with open(p, encoding="utf-8") as f:
        text = f.read()
    if not text.endswith("\n"):
        text += "\n"
    if not re.search(r"^end\s*$", text, re.M):
        text += "end\n"
    return text


def build_unl(cml, eve_lab_dir, mode, lab_name, desc, body):
    nodes = cml["nodes"]
    by_id = {n["id"]: n for n in nodes}

    devices = [n for n in nodes if n["node_definition"] in TEMPLATES]
    bridges = [n for n in nodes if n["node_definition"] == "unmanaged_switch"]
    clouds = [n for n in nodes if n["node_definition"] == "external_connector"]
    unknown = [n for n in nodes if n["node_definition"] not in TEMPLATES
               and n["node_definition"] not in ("unmanaged_switch", "external_connector")]
    if unknown:
        raise ValueError(f"Unbekannte Node-Typen: {[n['node_definition'] for n in unknown]}")

    xs = [n.get("x", 0) for n in nodes]
    ys = [n.get("y", 0) for n in nodes]
    minx, miny = min(xs), min(ys)

    def pos(n):
        return int(n.get("x", 0) - minx) + 120, int(n.get("y", 0) - miny) + 120

    eve_id = {n["id"]: i + 1 for i, n in enumerate(devices)}

    # Netze: jeder Switch/Cloud ein sichtbares Netz, jede Punkt-zu-Punkt-Verbindung ein verstecktes
    networks = []  # dict(id, type, name, left, top, visibility, icon)
    net_of_node = {}
    for n in bridges + clouds:
        nid = len(networks) + 1
        left, top = pos(n)
        if n["node_definition"] == "unmanaged_switch":
            networks.append(dict(id=nid, type="bridge", name=n["label"], left=left, top=top,
                                 visibility=1, icon="lan.png"))
        else:
            networks.append(dict(id=nid, type="pnet0", name=n["label"], left=left, top=top,
                                 visibility=1, icon="cloud.png"))
        net_of_node[n["id"]] = nid

    attach = {n["id"]: {} for n in devices}  # node -> {if_index: (name, net_id)}

    def iface(node, iid):
        for i in node["interfaces"]:
            if i["id"] == iid:
                return i
        raise KeyError(iid)

    def add(node, iid, net):
        i = iface(node, iid)
        idx, name = eve_if(node["node_definition"], i["label"])
        if idx in attach[node["id"]]:
            raise ValueError(f"{node['label']} {name} doppelt belegt")
        attach[node["id"]][idx] = (name, net)

    for link in cml["links"]:
        a, b = by_id[link["n1"]], by_id[link["n2"]]
        a_dev, b_dev = a["id"] in eve_id, b["id"] in eve_id
        if a_dev and b_dev:
            nid = len(networks) + 1
            (l1, t1), (l2, t2) = pos(a), pos(b)
            networks.append(dict(id=nid, type="bridge", name=f"Net-{a['label']}-{b['label']}",
                                 left=(l1 + l2) // 2, top=(t1 + t2) // 2, visibility=0, icon=None))
            add(a, link["i1"], nid)
            add(b, link["i2"], nid)
        elif a_dev and b["id"] in net_of_node:
            add(a, link["i1"], net_of_node[b["id"]])
        elif b_dev and a["id"] in net_of_node:
            add(b, link["i2"], net_of_node[a["id"]])
        else:
            raise ValueError(f"Verbindung zwischen zwei Netzobjekten nicht unterstützt: {link['label']}")

    lab_uuid = uuid.uuid5(NS, lab_name)
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           f'<lab name={quoteattr(lab_name)} id="{lab_uuid}" version="1" scripttimeout="300" lock="0">',
           f"  <description>{escape(desc)}</description>",
           f"  <body>{escape(body)}</body>",
           "  <topology>", "    <nodes>"]
    configs = []
    for n in devices:
        tpl, ram, cpu, min_eth, icon = TEMPLATES[n["node_definition"]]
        if n["node_definition"] == "iosv" and HOST_RE.match(n["label"]):
            icon = "Desktop.png"
        ifs = attach[n["id"]]
        eth = max([min_eth] + [i + 1 for i in ifs])
        left, top = pos(n)
        nid = eve_id[n["id"]]
        node_uuid = uuid.uuid5(NS, f"{lab_name}/{n['label']}")
        out.append(
            f'      <node id="{nid}" name={quoteattr(n["label"])} type="qemu" template="{tpl}" '
            f'console="telnet" cpu="{cpu}" cpulimit="0" ram="{ram}" ethernet="{eth}" '
            f'uuid="{node_uuid}" delay="0" icon={quoteattr(icon)} config="1" left="{left}" top="{top}">')
        for idx in sorted(ifs):
            name, net = ifs[idx]
            out.append(f'        <interface id="{idx}" name={quoteattr(name)} type="ethernet" network_id="{net}"/>')
        out.append("      </node>")
        configs.append((nid, read_cfg(eve_lab_dir, mode, n["label"])))
    out += ["    </nodes>", "    <networks>"]
    for net in networks:
        icon = f" icon={quoteattr(net['icon'])}" if net["icon"] else ""
        out.append(f'      <network id="{net["id"]}" type="{net["type"]}" name={quoteattr(net["name"])} '
                   f'left="{net["left"]}" top="{net["top"]}" visibility="{net["visibility"]}"{icon}/>')
    out += ["    </networks>", "  </topology>", "  <objects>", "    <configs>"]
    for nid, text in configs:
        b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        out.append(f'      <config id="{nid}">{b64}</config>')
    out += ["    </configs>", "  </objects>", "</lab>", ""]
    return "\n".join(out)


def write_zip(path, members):
    """Reproduzierbares ZIP (feste Zeitstempel), members = [(name, text)]."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in members:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, text.encode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paket", required=True, help="Kurzname für Dateinamen, z. B. ENCOR")
    ap.add_argument("--root", default=".", help="Paketordner mit CML-Labs/ und EVE-NG-Labs/")
    args = ap.parse_args()

    cml_root = os.path.join(args.root, "CML-Labs")
    eve_root = os.path.join(args.root, "EVE-NG-Labs")
    all_members = []
    for topo in sorted(glob.glob(os.path.join(cml_root, "*", "topology.yaml"))):
        lab = os.path.basename(os.path.dirname(topo))
        eve_lab_dir = os.path.join(eve_root, lab)
        if not os.path.isdir(eve_lab_dir):
            continue
        lab_members = []
        for mode, fname, suffix in (("build", "topology.yaml", "Bauen"),
                                    ("repair", "topology-repair.yaml", "Reparieren")):
            src = os.path.join(os.path.dirname(topo), fname)
            if not os.path.exists(src):
                continue
            with open(src, encoding="utf-8") as f:
                cml = yaml.safe_load(f)
            title = cml["lab"]["title"]
            lab_name = f"{args.paket} {lab} {suffix}"
            if mode == "build":
                body = ("Teil A (Bauen): Ausgangszustand ist geladen. "
                        "Aufgaben, Prüfschritte und Denkfragen stehen in der README des Labs.")
            else:
                body = ("Teil B (Reparieren): Alle Geräte sind konfiguriert, aber es stecken Fehler drin. "
                        "Tickets stehen in der README des Labs, die Auflösung in solutions/FAULTS.md.")
            unl = build_unl(cml, eve_lab_dir, mode, lab_name, f"{title} – {suffix}", body)
            member = f"{args.paket}-{lab}-{suffix}.unl"
            lab_members.append((member, unl))
        write_zip(os.path.join(eve_lab_dir, "EVE-Import.zip"), lab_members)
        all_members += lab_members
        print(f"{lab}: {len(lab_members)} Labs")
    if not all_members:
        sys.exit("Keine Labs gefunden")
    write_zip(os.path.join(eve_root, f"{args.paket}-EVE-NG-Labs.zip"), all_members)
    print(f"{args.paket}: {len(all_members)} .unl-Dateien")


if __name__ == "__main__":
    main()
