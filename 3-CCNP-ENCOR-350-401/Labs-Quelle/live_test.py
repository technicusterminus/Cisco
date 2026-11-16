#!/usr/bin/env python3
"""Spielt die Labs ab Nummer 32 in einer laufenden CML- oder EVE-NG-Instanz durch und prüft sie.

Je Lab:
  1. Musterlösung einspielen (Basis + solutions) und jede Zeile auf Parser-Fehler prüfen („% Invalid input“ …).
  2. Warten, dann die Prüfungen des Labs ausführen (Befehl, erwartetes Muster).
  3. Jeden Fehler aus Teil B einzeln einbauen: Die Probe muss jetzt fehlschlagen (das Ticket-Symptom ist da).
     Danach zurücknehmen: Die Probe muss wieder passen (der Fix aus FAULTS.md wirkt).
Am Ende steht ein Bericht (Markdown) mit allen Abweichungen und der echten Geräteausgabe dazu.

CML (legt das Lab selbst an, startet es und räumt es wieder ab):
  pip install virl2_client "pyats[full]"
  export CML_PASSWORD=…
  python3 live_test.py cml https://cml.example.net --user admin [--insecure] [--lab 32 36] [--keep]

EVE-NG (Lab „Bauen“ aus EVE-Import.zip öffnen, alle Nodes starten, Telnet-Ports aus EVE-NG ablesen):
  python3 live_test.py eve 192.168.1.50 --lab 36 --ports R1=32769 R2=32770

Syntaxprüfung für ALLE Labs (auch 01 bis 31): spielt die vollständige Reparatur-Konfiguration jedes Geräts ein
und meldet jede Zeile, die das Image ablehnt. Das belegt nicht die Symptome, aber dass jede Zeile gültig ist.
  python3 live_test.py cml https://cml.example.net --user admin --syntax [--lab 05 12]
  python3 live_test.py eve 192.168.1.50 --syntax --lab 05 --ports SW1=32769 SW2=32770 …

Ablauf nur prüfen, ohne Geräte:
  python3 live_test.py selftest

Die Muster in den Lab-Definitionen (checks, probe) stammen aus der IOS-Dokumentation. Weicht die Ausgabe
deines Images ab, zeigt der Bericht Befehl, Muster und Ausgabe: Dann ist das Muster zu korrigieren, nicht das Lab.
"""
import argparse, datetime, glob, importlib, os, re, socket, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lablib

ROOT = os.path.dirname(HERE)
PARSER_ERR = re.compile(r"^\s*%\s?(Invalid|Incomplete|Ambiguous|Unrecognized|Error|.*not allowed|.*failed)", re.I)
PROMPT = re.compile(rb"[\r\n][\w.\-/]+(\([\w.\-/ ]+\))?[>#] ?$")


def load_labs(only):
    labs = [importlib.import_module(os.path.basename(f)[:-3]).LAB
            for f in sorted(glob.glob(os.path.join(HERE, "lab_[0-9]*.py")))]
    return [l for l in labs if not only or l["num"] in only]


def parser_errors(output):
    """(Zeile, Meldung) für jede vom Parser abgelehnte Konfigurationszeile."""
    out, last = [], ""
    for line in output.replace("\r", "").split("\n"):
        if ")#" in line:
            last = line.split(")#", 1)[1].strip()
        elif PARSER_ERR.match(line):
            out.append((last, line.strip()))
    return out


# ---------------------------------------------------------------- Zugänge

class Telnet:
    """Konsolenzugang über die Telnet-Ports von EVE-NG. Nur Standardbibliothek."""

    def __init__(self, host, ports, timeout=120):
        self.host, self.ports, self.timeout, self.socks = host, ports, timeout, {}

    def _sock(self, node):
        if node not in self.socks:
            if node not in self.ports:
                raise SystemExit(f"Kein Telnet-Port für {node} angegeben (--ports {node}=<Port>)")
            s = socket.create_connection((self.host, self.ports[node]), timeout=10)
            self.socks[node] = s
            self._send(node, "")
            if self._read(node, 15).rstrip().endswith(">"):
                self._send(node, "enable")
                self._read(node, 10)
            for c in ("terminal length 0", "terminal width 200"):
                self._send(node, c)
                self._read(node, 10)
        return self.socks[node]

    def _send(self, node, text):
        self.socks[node].sendall(text.encode() + b"\r")

    def _read(self, node, timeout=None):
        s, buf, end = self.socks[node], b"", time.time() + (timeout or self.timeout)
        s.settimeout(0.5)
        while time.time() < end:
            try:
                chunk = s.recv(65535)
                if not chunk:
                    break
                buf += re.sub(rb"\xff[\xfb-\xfe].", b"", chunk)
            except socket.timeout:
                if re.search(rb"\[confirm\]\s*$|\]\?\s*$", buf):
                    s.sendall(b"\r")
                elif PROMPT.search(b"\n" + buf):
                    break
        return buf.decode(errors="replace")

    def run(self, node, cmd):
        self._sock(node)
        self._send(node, cmd)
        return self._read(node)

    def config(self, node, lines):
        self._sock(node)
        out = ""
        for l in ["configure terminal"] + list(lines) + ["end"]:
            self._send(node, l)
            out += self._read(node, 20)
        return out

    def close(self):
        for s in self.socks.values():
            s.close()


class Cml:
    """CML über virl2_client und pyATS. Legt das Lab an, startet es und räumt am Ende ab."""

    def __init__(self, url, user, password, insecure, keep):
        from virl2_client import ClientLibrary
        self.client = ClientLibrary(url, user, password, ssl_verify=not insecure)
        self.user, self.password, self.keep, self.lab = user, password, keep, None

    def open(self, lab):
        path = os.path.join(ROOT, "CML-Labs", lab["slug"], "topology.yaml")
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.lab = self.client.import_lab_from_path(path, title=f"LIVE-TEST {lab['slug']}")
        self.lab.start()
        self.lab.wait_until_lab_converged()
        self.lab.pyats.sync_testbed(self.user, self.password)

    def run(self, node, cmd):
        return self.lab.pyats.run_command(node, cmd, timeout=180)

    def config(self, node, lines):
        try:
            return self.lab.pyats.run_config_command(node, "\n".join(lines), timeout=180)
        except Exception as e:  # unicon meldet abgelehnte Zeilen als Ausnahme
            return str(e)

    def close(self):
        if self.lab and not self.keep:
            self.lab.pyats.cleanup()
            self.lab.stop()
            self.lab.wipe()
            self.lab.remove()
        self.lab = None


class Stub:
    """Für `selftest`: kennt keinen IOS-Befehl, merkt sich nur, welcher Fehler gerade eingebaut ist."""

    def __init__(self, lab):
        self.lab, self.broken = lab, set()

    def config(self, node, lines):
        for k, f in enumerate(self.lab["faults"]):
            if node != f["node"]:
                continue
            if list(lines) == list(as_dict(f["inject"], node)[node]):
                self.broken.add(k)
            elif list(lines) == list(as_dict(f["revert"], node)[node]):
                self.broken.discard(k)
        return ""

    def run(self, node, cmd):
        for k in self.broken:
            if self.lab["faults"][k]["probe"][:2] == (node, cmd):
                return "STUB-BROKEN"
        return "STUB-OK"

    def close(self):
        pass


# ---------------------------------------------------------------- Ablauf

def as_dict(x, node):
    return x if isinstance(x, dict) else {node: x}


def healthy(probe, output, stub=False):
    node, cmd, pattern = probe[:3]
    want = probe[3] if len(probe) > 3 else True
    found = (output == "STUB-OK") == want if stub else bool(re.search(pattern, output))
    return found == want


def test_lab(lab, dev, wait, log, stub=False):
    """Gibt die Liste der Abweichungen zurück."""
    bad = []

    def note(kind, text, output=""):
        bad.append((kind, text, output))
        log(f"   FEHLER {kind}: {text}")

    log(f"\n== Lab {lab['num']} – {lab['title']}")
    log(" 1. Musterlösung einspielen")
    for n in lab["nodes"]:
        if n["type"] == "switch":
            continue
        out = dev.config(n["name"], [l for l in lablib.full_config(n, True) if not l.startswith("hostname ")])
        for line, msg in parser_errors(out):
            note("Parser", f"{n['name']}: `{line}` → {msg}")
    wait(lab.get("settle", 60))
    log(" 2. Prüfungen im gesunden Zustand")
    for probe in lab.get("checks", []):
        out = dev.run(probe[0], probe[1])
        if not healthy(probe, out, stub):
            note("Prüfung", f"{probe[0]}: `{probe[1]}` passt nicht auf `{probe[2]}`", out)
    for k, f in enumerate(lab["faults"], 1):
        log(f" 3.{k} Ticket {k} ({f['node']})")
        p = f["probe"]

        def step(lines_by_node, expect_healthy, phase):
            for node, lines in as_dict(lines_by_node, f["node"]).items():
                for line, msg in parser_errors(dev.config(node, lines)):
                    note("Parser", f"Ticket {k} {phase}, {node}: `{line}` → {msg}")
            wait(f.get("settle", 15))
            for node, cmd in f.get("kick", []):
                dev.run(node, cmd)
            out = dev.run(p[0], p[1])
            if healthy(p, out, stub) != expect_healthy:
                what = "Symptom tritt nicht auf" if not expect_healthy else "nach dem Fix nicht wieder in Ordnung"
                note("Ticket", f"Ticket {k} {phase}: {what} ({p[0]}: `{p[1]}`, Muster `{p[2]}`)", out)

        step(f["inject"], False, "eingebaut")
        step(f["revert"], True, "behoben")
    return bad


def syntax_labs(only):
    """Alle Labs mit Reparatur-Topologie: [(Lab-Dict, {Node: Konfigurationszeilen})]."""
    import yaml
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "CML-Labs", "*", "topology-repair.yaml"))):
        slug = os.path.basename(os.path.dirname(path))
        if only and slug[:2] not in only:
            continue
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        cfg = {n["label"]: [l for l in (n.get("configuration") or "").split("\n")
                            if l.strip() and not l.startswith(("hostname ", "!")) and l.strip() != "end"]
               for n in doc["nodes"] if n.get("configuration")}
        out.append(({"num": slug[:2], "slug": slug, "title": doc["lab"]["title"].replace(" (Repair)", "")}, cfg))
    return out


def test_syntax(lab, cfg, dev, log):
    bad = []
    log(f"\n== Lab {lab['num']} – Syntaxprüfung, {len(cfg)} Geräte")
    for node, lines in cfg.items():
        for line, msg in parser_errors(dev.config(node, lines)):
            bad.append(("Parser", f"{node}: `{line}` → {msg}", ""))
            log(f"   FEHLER Parser: {node}: `{line}` → {msg}")
    return bad


def report(results, target, path):
    lines = [f"# Live-Test ENCOR-Labs – {datetime.date.today().isoformat()}", "", f"Ziel: {target}", "",
             "| Lab | Ergebnis | Abweichungen |", "|---|---|---|"]
    for lab, bad in results:
        lines.append(f"| {lab['num']} {lab['title']} | {'in Ordnung' if not bad else 'Abweichungen'} | {len(bad)} |")
    for lab, bad in results:
        if bad:
            lines += ["", f"## Lab {lab['num']}"]
            for kind, text, output in bad:
                lines += ["", f"- **{kind}:** {text}"]
                if output:
                    lines += ["", "  ```", *("  " + l for l in output.replace("\r", "").strip().split("\n")[-40:]), "  ```"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["cml", "eve", "selftest"])
    ap.add_argument("target", nargs="?", help="CML-URL bzw. EVE-NG-Adresse")
    ap.add_argument("--lab", nargs="*", default=[], help="Lab-Nummern, z. B. 32 36 (Standard: alle)")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--insecure", action="store_true", help="CML: Zertifikat nicht prüfen")
    ap.add_argument("--keep", action="store_true", help="CML: Lab am Ende nicht löschen")
    ap.add_argument("--ports", nargs="*", default=[], help="EVE-NG: Node=Telnet-Port …")
    ap.add_argument("--report", default="live-test-bericht.md")
    ap.add_argument("--syntax", action="store_true", help="nur Syntaxprüfung, dafür für alle Labs")
    a = ap.parse_args(argv)
    if a.syntax:
        todo = syntax_labs(a.lab)
        labs = [l for l, _ in todo]
        run = {l["slug"]: (lambda dev, l=l, c=c: test_syntax(l, c, dev, print)) for l, c in todo}
    else:
        labs = load_labs(a.lab)
        run = {l["slug"]: (lambda dev, l=l: test_lab(l, dev, time.sleep, print)) for l in labs}
    if not labs:
        sys.exit("Keine passenden Labs gefunden")
    results = []
    if a.mode == "selftest":
        for lab in labs:
            if a.syntax:
                results.append((lab, run[lab["slug"]](type("Null", (), {"config": lambda self, n, l: ""})())))
            else:
                results.append((lab, test_lab(lab, Stub(lab), lambda s: None, print, stub=True)))
    elif a.mode == "eve":
        if len(labs) != 1:
            sys.exit("EVE-NG: genau ein Lab angeben (--lab NN), dazu die Ports seiner Nodes")
        dev = Telnet(a.target, {k: int(v) for k, v in (p.split("=") for p in a.ports)})
        try:
            results.append((labs[0], run[labs[0]["slug"]](dev)))
        finally:
            dev.close()
    else:
        pw = os.environ.get("CML_PASSWORD") or sys.exit("Bitte CML_PASSWORD setzen")
        dev = Cml(a.target, a.user, pw, a.insecure, a.keep)
        for lab in labs:
            try:
                dev.open(lab)
                results.append((lab, run[lab["slug"]](dev)))
            finally:
                dev.close()
    if a.mode != "selftest":
        report(results, f"{a.mode} {a.target}", a.report)
        print(f"\nBericht: {a.report}")
    total = sum(len(b) for _, b in results)
    print(f"\n{len(results)} Labs geprüft, {total} Abweichungen")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
