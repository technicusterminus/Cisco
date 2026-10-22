"""Hilfsbibliothek: erzeugt aus einer Lab-Definition die CML- und EVE-NG-Dateien.

Eine Lab-Definition ist ein dict (siehe lab_*.py). Aus ihr entstehen
  CML-Labs/<slug>/{topology.yaml, topology-repair.yaml, README.md, solutions/*.cfg, solutions/FAULTS.md}
  EVE-NG-Labs/<slug>/{README.md, build/*.cfg, repair/*.cfg, solutions/*.cfg, solutions/FAULTS.md, vpcs/*.vpc}

Fehler werden nicht von Hand in zwei Konfigurationen gepflegt, sondern als Änderung an der
fertigen Konfiguration beschrieben (ersetzen, entfernen, einfügen). So stimmen Reparatur-Topologie,
Fehlerliste und Diff immer überein.
"""
import os, re
import yaml

HEADER = ["no ip domain-lookup", "service timestamps log datetime msec",
          "line con 0", " exec-timeout 0 0", " logging synchronous"]

NODE_DEF = {"router": "iosv", "host": "iosv", "l2": "iosvl2", "switch": "unmanaged_switch"}
EVE_TPL = {"router": ("Cisco vIOS Router", 512, ""),
           "host": ("Cisco vIOS Router", 512, "Host (vIOS, wie in CML; alternativ VPCS)"),
           "l2": ("Cisco vIOS Switch (vIOS-L2)", 768, "Der erste Start dauert einige Minuten."),
           "switch": ("Network (Bridge)", 0,
                      "Kein Gerät, sondern ein **Network**-Objekt (Linux-Bridge) mit Typ *Bridge*.")}


def lines(text):
    return [l.rstrip() for l in text.strip("\n").split("\n")] if text and text.strip() else []


def long_if(n):
    return n if n.startswith("port") else re.sub(r"^Gi", "GigabitEthernet", n)


def full_config(node, with_sol, faults=()):
    """Gesamtkonfiguration eines Nodes. with_sol=False: Ausgangslage zum Bauen."""
    body = ["hostname " + node["name"]] + HEADER + lines(node.get("base", ""))
    if with_sol:
        body += lines(node.get("sol", ""))
        for f in faults:
            if f["node"] == node["name"]:
                body = apply_fault(body, f)
    return body


def apply_fault(body, f):
    nth = f.get("nth", 0)
    if f.get("old") is None:  # einfügen nach der nth-ten Zeile ctx
        hits = [i for i, l in enumerate(body) if l == f["ctx"]]
        if len(hits) <= nth:
            raise SystemExit(f"Fehler {f['node']}: ctx {f['ctx']!r} nicht gefunden (nth {nth})")
        idx = hits[nth]
        return body[:idx + 1] + [f["new"]] + body[idx + 1:]
    start = 0
    if f.get("ctx"):
        hits = [i for i, l in enumerate(body) if l == f["ctx"]]
        if len(hits) != 1:
            raise SystemExit(f"Fehler {f['node']}: ctx {f['ctx']!r} kommt {len(hits)}x vor")
        start = hits[0]
    hits = [i for i in range(start, len(body)) if body[i] == f["old"]]
    if len(hits) <= nth:
        raise SystemExit(f"Fehler {f['node']}: Zeile {f['old']!r} nicht gefunden (ctx {f.get('ctx')!r}, nth {nth})")
    idx = hits[nth]
    if f.get("new") is None:
        return body[:idx] + body[idx + 1:]
    return body[:idx] + [f["new"]] + body[idx + 1:]


def diff_block(f):
    out = []
    if f.get("old") is not None:
        out.append("-" + f["old"])
    if f.get("new") is not None:
        out.append("+" + f["new"])
    return "```diff\n" + "\n".join(out) + "\n```"


# ---------------------------------------------------------------- YAML

class Lit(str):
    pass


yaml.add_representer(Lit, lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", str(v), style="|"))


def cml_yaml(lab, repair):
    nodes, nid = [], {}
    for k, n in enumerate(lab["nodes"]):
        nid[n["name"]] = f"n{k}"
        d = {"id": f"n{k}", "label": n["name"], "node_definition": NODE_DEF[n["type"]],
             "x": n["x"], "y": n["y"]}
        if n["type"] != "switch":
            cfg = "\n".join(full_config(n, repair, lab["faults"] if repair else ())) + "\n"
            d["configuration"] = Lit(cfg)
        d["tags"] = []
        d["interfaces"] = interfaces(n["type"])
        nodes.append(d)
    links = []
    for k, (a, ia, b, ib) in enumerate(lab["links"]):
        links.append({"id": f"l{k}", "n1": nid[a], "n2": nid[b], "i1": ifid(ia), "i2": ifid(ib),
                      "label": f"{a}-{long_if(ia)}<->{b}-{long_if(ib)}"})
    title = f"Lab {lab['num']} – {lab['title']}" + (" (Repair)" if repair else "")
    doc = {"lab": {"title": title, "description": lab["summary"], "notes": "Aufgaben: siehe README.md",
                   "version": "0.2.0"}, "nodes": nodes, "links": links}
    return yaml.dump(doc, sort_keys=False, allow_unicode=True, width=10000)


def interfaces(t):
    if t == "switch":
        return [{"id": f"i{k}", "label": f"port{k}", "slot": k, "type": "physical"} for k in range(8)]
    out = [{"id": "i0", "label": "Loopback0", "type": "loopback"}]
    labels = ([f"GigabitEthernet0/{k}" for k in range(4)] if t != "l2" else
              [f"GigabitEthernet{a}/{b}" for a in range(4) for b in range(4)])
    for k, l in enumerate(labels):
        out.append({"id": f"i{k + 1}", "label": l, "slot": k, "type": "physical"})
    return out


def ifid(name):
    """Interface-Id wie in der Topologie: Loopback0 = i0, Gi0/0 = i1, ..."""
    if name.startswith("port"):
        return "i" + name[4:]
    m = re.match(r"Gi(\d)/(\d)$", name)
    a, b = int(m.group(1)), int(m.group(2))
    return f"i{a * 4 + b + 1}"


# ---------------------------------------------------------------- Prüfungen

def validate(lab):
    names = {n["name"] for n in lab["nodes"]}
    types = {n["name"]: n["type"] for n in lab["nodes"]}
    for a, ia, b, ib in lab["links"]:
        assert a in names and b in names, (a, b)
    used = set()
    for a, ia, b, ib in lab["links"]:
        for n, i in ((a, ia), (b, ib)):
            assert (n, i) not in used, f"{n} {i} doppelt belegt"
            used.add((n, i))
            if types[n] == "switch":
                assert i.startswith("port") and int(i[4:]) < 8
            elif types[n] == "l2":
                assert re.match(r"Gi[0-3]/[0-3]$", i), (n, i)
            else:
                assert re.match(r"Gi0/[0-3]$", i), (n, i)
    for k, f in enumerate(lab["faults"], 1):
        node = next(n for n in lab["nodes"] if n["name"] == f["node"])
        good = full_config(node, True)
        bad = full_config(node, True, [f])
        assert good != bad, f"Fehler {k} ändert nichts"
        if f.get("new") is not None:
            assert f["new"] in bad
    assert len(lab["tickets"]) == len(lab["faults"]), "Tickets und Fehler passen nicht zusammen"
    for r in (False, True):
        d = yaml.safe_load(cml_yaml(lab, r))
        ids = {n["id"]: {i["id"] for i in n["interfaces"]} for n in d["nodes"]}
        for l in d["links"]:
            assert l["i1"] in ids[l["n1"]] and l["i2"] in ids[l["n2"]]


# ---------------------------------------------------------------- Texte

def part_a(lab):
    out = ["## Teil A – Bauen",
           "Arbeite die Schritte der Reihe nach ab. Jeder Schritt sagt dir, was du tust, woran du den Erfolg erkennst "
           "(**Prüfen**) und worüber du nachdenken sollst (**Denkfrage**). Die Antworten auf die Denkfragen stehen am "
           "Ende von Teil A.", ""]
    for k, s in enumerate(lab["steps"], 1):
        out.append(f"{k}. **{s['t']}** {s['body']}")
        if s.get("check"):
            out.append(f"   - **Prüfen:** {s['check']}")
        if s.get("think"):
            out.append(f"   - **Denkfrage:** {s['think']}")
    out += ["", "<details><summary>Antworten zu den Denkfragen</summary>", ""]
    for ref, text in lab["answers"]:
        out.append(f"- **Zu {ref}:** {text}")
    out += ["", "</details>"]
    return "\n".join(out)


def part_b(lab, plat):
    n = len(lab["faults"])
    if plat == "cml":
        intro = "Importiere `topology-repair.yaml`."
    else:
        intro = "Setze alle Nodes zurück (Rechtsklick → *Wipe*) und spiele `repair/<Node>.cfg` ein."
    out = ["## Teil B – Reparieren", "",
           f"{intro} Alle Geräte sind vollständig konfiguriert, aber es stecken **{n} Fehler** drin. Behandle jede "
           "Meldung als Ticket: erst Symptom nachstellen, dann die Ursache eingrenzen (Layer für Layer), dann beheben "
           "und das Ergebnis beweisen. Ändere nur, was kaputt ist."]
    if lab.get("staggered"):
        out.append("")
        out.append("Manche Symptome zeigen sich erst, wenn ein anderer Fehler behoben ist. Das ist gewollt: Arbeite von "
                   "unten nach oben (Underlay, Control Plane, Daten).")
    for k, t in enumerate(lab["tickets"], 1):
        out += ["", f"**Ticket {k}:** {t}"]
    return "\n".join(out)


def part_c(lab):
    out = ["## Teil C – Üben", "", "Beantworte zuerst selbst, dann klappe die Antwort auf.", ""]
    for k, (q, a) in enumerate(lab["teilc"], 1):
        out += [f"{k}. {q}", "<details><summary>Antwort</summary>", "", a, "", "</details>", ""]
    return "\n".join(out).rstrip()


def verification(lab):
    out = ["## Verifikation", "```"] + lab["verify"] + ["```", "",
           "| Befehl | Das solltest du sehen |", "|---|---|"]
    out += [f"| {c} | {s} |" for c, s in lab["verify_table"]]
    return "\n".join(out)


def exam(lab):
    return "## Prüfungsbezug\n" + "\n".join("- " + e for e in lab["exam"])


def head(lab, plat):
    nodes = {}
    for n in lab["nodes"]:
        nodes[n["type"]] = nodes.get(n["type"], 0) + 1
    names = {"router": "iosv", "host": "iosv", "l2": "iosvl2", "switch": "unmanaged_switch"}
    cnt = {}
    for n in lab["nodes"]:
        cnt[names[n["type"]]] = cnt.get(names[n["type"]], 0) + 1
    ns = ", ".join(f"{v}× {k}" for k, v in sorted(cnt.items(), key=lambda x: -x[1]))
    if plat == "cml":
        first = f"# Lab {lab['num']} – {lab['title']}\n\n**Dauer:** {lab['minutes']} min · **Niveau:** {lab['level']} · **Nodes:** {ns}"
    else:
        first = f"# Lab {lab['num']} – {lab['title']}\n\n**Plattform:** EVE-NG · **Dauer:** {lab['minutes']} min · **Niveau:** {lab['level']}"
    goals = "\n".join("- " + g for g in lab["goals"])
    tags = "\n".join(f"| `Ziel::{t}` | {th} | {c} |" for t, th, c in lab["tags"])
    how = ("**So arbeitest du:** Teil A = Bauen (importiere `topology.yaml`), Teil B = Reparieren (importiere "
           "`topology-repair.yaml`, dort ist alles gebaut, aber mit Fehlern), Teil C = Üben (Transferfragen zum "
           "Selbsttest). Lösungen und Fehlerursachen liegen in `solutions/`, erst nach eigenem Versuch öffnen."
           if plat == "cml" else
           "**So arbeitest du:** Teil A = Bauen (Ausgangszustand aus `build/` einspielen), Teil B = Reparieren (Nodes "
           "zurücksetzen, `repair/` einspielen), Teil C = Üben. Konfigurationen liegen als Textdateien vor (`build/`, "
           "`repair/`, `solutions/`), die du per Konsole einfügst (siehe [Arbeiten mit den Dateien](../README.md#arbeiten-mit-den-dateien)). "
           "Die Interface-Namen sind **identisch zu CML**; die Aufgabentexte und Konfigurationen gelten unverändert.")
    return (f"{first}\n\n{lab['summary']}\n\n**Lernziele:** Nach diesem Lab kannst du …\n\n{goals}\n\n"
            f"| Deck-Tag | Thema | Karten im Kompendium |\n|---|---|---|\n{tags}\n\n{how}")


def eve_build(lab):
    rows, ram = [], 0
    host_ram = 0
    for n in lab["nodes"]:
        tpl, mb, note = EVE_TPL[n["type"]]
        ram += mb
        if n["type"] == "host":
            host_ram += mb
        rows.append(f"| {n['name']} | {tpl} | {note} | {mb if mb else '–'} |")
    out = ["## Aufbau in EVE-NG", "", "### Nodes", "",
           "| Node | EVE-Template | Hinweis | RAM (Richtwert, MB) |", "|---|---|---|---|"] + rows
    hosts = any(n["type"] == "host" for n in lab["nodes"])
    s = f"\nSumme (alle Nodes als vIOS/…): ca. **{ram / 1000:.1f} GB RAM**."
    if hosts and lab.get("vpcs"):
        s += f" Mit VPCS statt vIOS-Hosts: ca. **{(ram - host_ram) / 1000:.1f} GB**."
    out.append(s)
    out += ["", "### Verkabelung", "", "| Von | Interface | Nach | Interface |", "|---|---|---|---|"]
    types = {n["name"]: n["type"] for n in lab["nodes"]}
    for a, ia, b, ib in lab["links"]:
        f = lambda n, i: "–" if types[n] == "switch" else i
        out.append(f"| {a} | {f(a, ia)} | {b} | {f(b, ib)} |")
    if hosts:
        out += ["", "### Hosts: vIOS oder VPCS", ""]
        if lab.get("vpcs"):
            out.append("Die Hosts sind in den Aufgaben IOS-Geräte (Dateien `build/<Host>.cfg`). Willst du RAM sparen, "
                       "nimm **VPCS**: Konsole öffnen und die Zeile aus `vpcs/<Host>.vpc` eingeben, danach `save`. "
                       + lab["vpcs_note"])
        else:
            out.append(lab["vpcs_note"])
    return "\n".join(out)


def topology_section(lab):
    return ("## Topologie\n\n```\n" + lab["diagram"].strip("\n") + "\n```\n\n"
            "| Link | Netz |\n|---|---|\n" + "\n".join(f"| {a} | {b} |" for a, b in lab["nets"]) + "\n\n" + lab["topo_text"])


def faults_md(lab):
    out = [f"# Fehlerliste – Lab {lab['num']} – {lab['title']}", "", "**Spoiler.** Erst nach eigener Fehlersuche lesen."]
    for k, f in enumerate(lab["faults"], 1):
        out += ["", f"## Ticket {k} ({f['node']})", "", f"- **Symptom:** {lab['tickets'][k - 1]}",
                f"- **So findest du es:** {f['find']}", f"- **Ursache:** {f['cause']}", f"- **Fix:** {f['fix']}",
                "- **Eingebaut:**", "", diff_block(f)]
    return "\n".join(out) + "\n"


def readme(lab, plat):
    sol = ("## Lösungen\n\n- `solutions/<Gerät>.cfg`: Konfiguration zu Teil A (ohne Basis-IP-Adressen)\n"
           "- `solutions/FAULTS.md`: Fehlerliste zu Teil B (Spoiler!)")
    parts = [head(lab, plat)]
    if plat == "eve":
        parts.append(eve_build(lab))
    parts += [topology_section(lab), part_a(lab), part_b(lab, plat), verification(lab), part_c(lab), exam(lab), sol]
    if lab.get("caveat"):
        parts.insert(-1, "## Hinweis zum Image\n\n" + lab["caveat"])
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------- Schreiben

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def render(lab, root):
    validate(lab)
    cml = os.path.join(root, "CML-Labs", lab["slug"])
    eve = os.path.join(root, "EVE-NG-Labs", lab["slug"])
    write(os.path.join(cml, "topology.yaml"), cml_yaml(lab, False))
    write(os.path.join(cml, "topology-repair.yaml"), cml_yaml(lab, True))
    write(os.path.join(cml, "README.md"), readme(lab, "cml"))
    write(os.path.join(cml, "solutions", "FAULTS.md"), faults_md(lab))
    write(os.path.join(eve, "README.md"), readme(lab, "eve"))
    write(os.path.join(eve, "solutions", "FAULTS.md"), faults_md(lab))
    for n in lab["nodes"]:
        if n["type"] == "switch":
            continue
        build = "\n".join(full_config(n, False)) + "\n"
        rep = "\n".join(full_config(n, True, lab["faults"])) + "\n"
        write(os.path.join(eve, "build", n["name"] + ".cfg"), build)
        write(os.path.join(eve, "repair", n["name"] + ".cfg"), rep)
        if n["type"] != "host" and n.get("sol", "").strip():
            sol = "\n".join(lines(n["sol"])) + "\n"
            write(os.path.join(cml, "solutions", n["name"] + ".cfg"), sol)
            write(os.path.join(eve, "solutions", n["name"] + ".cfg"), sol)
        if n["type"] == "host" and n.get("vpcs"):
            write(os.path.join(eve, "vpcs", n["name"] + ".vpc"), n["vpcs"].strip() + "\nsave\n")
