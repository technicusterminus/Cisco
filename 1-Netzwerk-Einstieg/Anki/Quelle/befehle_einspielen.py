#!/usr/bin/env python3
"""Spielt die Befehlskarten aus befehle*.txt in ein bestehendes Deck (.apkg) ein.

Aufruf:  python3 befehle_einspielen.py <bisher.apkg> <neu.apkg> <version>
Beispiel: python3 befehle_einspielen.py ../Deck_5.1_DE.apkg ../Deck_5.2_DE.apkg 5.2

Das Skript ändert weder den Notiztyp noch die bestehenden Karten. Es entfernt nur
Karten mit dem Tag Fokus::Befehle (aus einem früheren Lauf) und legt sie aus
den befehle*.txt-Dateien neu an. Die GUIDs hängen nur an der Frage, deshalb behält ein
Update-Import in Anki den Lernstand, solange die Frage gleich bleibt.

Kartenformat (wie bei ENARSI und CCIE):

    # 3.1.c | Thema des Abschnitts
    S: https://... | Titel der Quelle      (gilt für alle Karten des Abschnitts)

    Q: Aufgabe als Frage, endet mit ?
    A:
    ```
    befehl <platzhalter> [optional] {a | b}
    ```
    **Modus:** global. Ein, zwei Sätze, was der Befehl bewirkt.
    H: optionaler Hinweis (Merke:, Falle:)
    T: Befehl Stufe [Befehlsart]   z. B. "Befehl Leicht" oder "Befehl Mittel Pruefen"

Leerzeilen trennen Karten, im Codeblock stehen keine Leerzeilen.
"""
import glob, hashlib, html, json, os, re, shutil, sqlite3, sys, tempfile, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
STUFEN = {"Leicht", "Mittel", "Schwer"}
ARTEN = {"Pruefen", "Konfigurieren", "Betrieb"}

# Farben direkt im HTML, damit Code auch im Dunkelmodus lesbar ist (der CCNA- und
# der Einstieg-Notiztyp haben dafür keine eigenen Regeln).
PRE = ('<pre style="background:#102b3f;color:#e8f5ff;padding:12px 14px;border-radius:9px;overflow-x:auto;'
       'white-space:pre;text-align:left;font:14px/1.45 Menlo,Consolas,monospace;margin:12px 0">'
       '<code style="background:none;color:inherit;padding:0;font-size:inherit">')
CODE = '<code style="background:#dfe8ef;color:#183047;padding:1px 5px;border-radius:4px">'

DECKS = {
    "ENCOR_v1_2": dict(prefix="E12", ns="ENCOR-v1.2-Befehle", styled=False, kapitel=False),
    "CCNA_200_301": dict(prefix="C11", ns="CCNA-200-301-Befehle", styled=True, kapitel=False),
    "Netzwerk_Einstieg": dict(prefix="EIN", ns="Netzwerk-Einstieg-Befehle", styled=True, kapitel=True),
}

PRUEFEN = ("show", "debug", "undebug", "ping", "traceroute", "tracert", "test", "mtrace", "ipconfig", "ifconfig",
           "ip addr show", "ip route show", "nslookup", "arp", "netstat", "route print", "dig", "monitor capture")
BETRIEB = ("clear", "copy", "reload", "write", "erase", "dir", "delete", "ssh", "telnet", "terminal", "more",
           "event manager run", "guestshell run", "verify")


def inline(s, styled):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", (CODE if styled else "<code>") + r"\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s


def md(text, styled):
    out, parts = [], re.split(r"```\n?(.*?)\n?```", text, flags=re.S)
    for i, p in enumerate(parts):
        if i % 2:
            out.append((PRE if styled else "<pre><code>") + html.escape(p, quote=False) + "</code></pre>")
        elif p.strip():
            out.append(inline(p.strip(), styled).replace("\n", "<br>"))
    return "".join(out)


def sources_html(srcs):
    if not srcs:
        return ""
    return "<ul>" + "".join(f'<li><a href="{html.escape(u)}">{html.escape(t)}</a></li>' for u, t in srcs) + "</ul>"


def parse(path):
    cards, ziel, thema, sec_src, cur, key, errors = [], None, None, [], None, None, []

    def close():
        nonlocal cur
        if cur:
            cards.append(cur)
        cur = None

    for ln, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if cur is not None and key and cur[key].count("```") % 2 == 1:
            cur[key] += "\n" + line
            continue
        if not line.strip():
            close(); key = None
            continue
        if line.startswith("# "):
            close()
            ziel, thema = [x.strip() for x in line[2:].split("|", 1)]
            sec_src = []
            continue
        m = re.match(r"^([QAHTS]):\s?(.*)$", line)
        if m:
            k, v = m.groups()
            if k == "S":
                u, t = [x.strip() for x in v.split("|", 1)]
                (cur["S"] if cur else sec_src).append((u, t))
                continue
            if k == "Q":
                close()
                cur = {"Q": "", "A": "", "H": "", "T": "", "S": [], "ziel": ziel, "thema": thema,
                       "sec": list(sec_src), "loc": f"{os.path.basename(path)}:{ln}"}
            if cur is None:
                errors.append(f"{path}:{ln}: {k} ohne Q")
                continue
            cur[k] = v
            key = k
        elif cur is not None and key:
            cur[key] += "\n" + line
        else:
            errors.append(f"{path}:{ln}: unerwartete Zeile: {line[:60]}")
    close()
    return cards, errors


def befehlsart(c):
    t = c["T"].split()
    if len(t) == 3:
        return t[2]
    m = re.search(r"```\n?(.*?)\n", c["A"] + "\n", flags=re.S)
    first = (m.group(1) if m else "").strip().lower()
    if first.startswith(PRUEFEN):
        return "Pruefen"
    if first.startswith(BETRIEB):
        return "Betrieb"
    return "Konfigurieren"


def check(c):
    p = []
    if not c["Q"].strip().endswith("?"):
        p.append("Frage endet nicht mit ?")
    t = c["T"].split()
    if not (2 <= len(t) <= 3) or t[0] != "Befehl" or t[1] not in STUFEN or (len(t) == 3 and t[2] not in ARTEN):
        p.append(f"T ungültig: {c['T']!r}")
    a = c["A"].lstrip()
    if not (a.startswith("```") or a.startswith("**")):
        p.append("Antwort beginnt weder mit Code noch fett")
    if a.count("```") % 2:
        p.append("Codeblock nicht geschlossen")
    if "**Modus:**" not in c["A"]:
        p.append("Modus fehlt")
    return p


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def guid_for(ns, frage):
    # wie genanki.guid_for: base91 aus sha256
    h = hashlib.sha256(("__".join([ns, frage])).encode()).hexdigest()
    n = int(h[:16], 16)
    table = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&()*+,-./:;<=>?@[]^_`{|}~")
    out = []
    while n:
        n, r = divmod(n, len(table))
        out.append(table[r])
    return "".join(reversed(out))


def main():
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(2)
    src, dst, version = sys.argv[1:]
    cards, errors = [], []
    for f in sorted(glob.glob(os.path.join(HERE, "befehle*.txt"))):
        cs, es = parse(f)
        cards += cs; errors += es
    seen = set()
    for c in cards:
        errors += [f"{c['loc']}: {p}" for p in check(c)]
        k = re.sub(r"\W+", "", c["Q"].lower())
        if k in seen:
            errors.append(f"{c['loc']}: doppelte Frage")
        seen.add(k)
    if errors:
        print("\n".join(errors)); sys.exit(1)

    work = tempfile.mkdtemp()
    with zipfile.ZipFile(src) as z:
        z.extractall(work)
    db = sqlite3.connect(os.path.join(work, "collection.anki2"))
    models = json.loads(db.execute("select models from col").fetchone()[0])
    decks = json.loads(db.execute("select decks from col").fetchone()[0])
    if len(models) != 1:
        sys.exit("Erwartet genau einen Notiztyp")
    mid, model = next(iter(models.items()))
    names = [f["name"] for f in model["flds"]]
    base = db.execute("select tags from notes limit 1").fetchone()[0].split()[0]
    cfg = DECKS[base]

    # alte Befehlskarten entfernen (frühere Läufe)
    old = [r[0] for r in db.execute("select id from notes where tags like '% Fokus::Befehle %'")]
    for nid in old:
        db.execute("delete from cards where nid=?", (nid,))
        db.execute("delete from notes where id=?", (nid,))

    # bestehende IDs je Ziel/Kapitel, um weiterzuzählen
    idx = names.index("ID")
    maxn = {}
    for (flds,) in db.execute("select flds from notes"):
        m = re.match(rf"{cfg['prefix']}-(.+)-(\d+)$", flds.split("\x1f")[idx])
        if m:
            maxn[m.group(1)] = max(maxn.get(m.group(1), 0), int(m.group(2)))

    real = {did: d["name"] for did, d in decks.items() if d["name"] != "Default"}
    def deck_for(dom):
        if len(real) == 1:
            return int(next(iter(real)))
        for did, name in real.items():
            leaf = name.split("::")[-1]
            if re.match(rf"^{dom}[ ·]", leaf):
                return int(did)
        sys.exit(f"Kein Unterdeck für Domäne {dom}")

    now = int(time.time())
    nid = int(time.time() * 1000)
    due = (db.execute("select max(due) from cards where type=0").fetchone()[0] or 0) + 1
    vtag = version.replace(".", "_")
    per = {}
    for c in cards:
        stufe = c["T"].split()[1]
        ziel = c["ziel"]
        if cfg["kapitel"]:
            key = f"{int(ziel):02d}"
            tags = [base, f"Kapitel::{key}"]
            dom = None
        else:
            key = ziel
            dom = ziel.split(".")[0]
            tags = [base, f"Ziel::{ziel}", f"Domaene::{dom}"]
        maxn[key] = maxn.get(key, 0) + 1
        tags += ["Typ::Befehl", f"Stufe::{stufe}", "Fokus::Befehle", f"Befehlsart::{befehlsart(c)}",
                 f"Befehle::{vtag}"]
        werte = {
            "Frage": md(c["Q"], cfg["styled"]), "Antwort": md(c["A"], cfg["styled"]),
            "Hinweis": md(c["H"], cfg["styled"]), "Quellen": sources_html(c["sec"] + c["S"]),
            "ID": f"{cfg['prefix']}-{key}-{maxn[key]:03d}", "Ziel": ziel, "Kapitel": str(int(ziel)) if cfg["kapitel"] else ziel,
            "Thema": c["thema"], "Typ": f"Befehl · {stufe}",
        }
        flds = [werte.get(n, "") for n in names]
        sfld = strip_html(flds[model.get("sortf", 0)])
        csum = int(hashlib.sha1(sfld.encode()).hexdigest()[:8], 16)
        nid += 1
        db.execute("insert into notes values (?,?,?,?,?,?,?,?,?,?,?)",
                   (nid, guid_for(cfg["ns"], c["Q"].strip()), int(mid), now, -1, " " + " ".join(tags) + " ",
                    "\x1f".join(flds), sfld, csum, 0, ""))
        did = deck_for(dom)
        db.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (nid + 500000000, nid, did, 0, now, -1, 0, 0, due, 0, 0, 0, 0, 0, 0, 0, 0, ""))
        due += 1
        per[real[str(did)]] = per.get(real[str(did)], 0) + 1
    db.execute("update col set mod=?", (now * 1000,))
    db.commit()
    total = db.execute("select count(*) from notes").fetchone()[0]
    db.execute("vacuum")
    db.close()

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(work)):
            z.write(os.path.join(work, f), f)
    shutil.rmtree(work)
    print(f"{len(cards)} Befehlskarten, {len(old)} alte ersetzt, {total} Karten gesamt -> {dst}")
    for k, v in per.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
