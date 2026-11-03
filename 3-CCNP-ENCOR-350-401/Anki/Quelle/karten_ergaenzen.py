#!/usr/bin/env python3
"""Ergänzt neue Wissens- und Übungskarten aus ergaenzung*.txt in ein bestehendes Deck (.apkg).

Aufruf:  python3 karten_ergaenzen.py <bisher.apkg> <neu.apkg> <version>
Beispiel: python3 karten_ergaenzen.py ../ENCOR_v1.2_Kompendium_5.3_DE.apkg ../ENCOR_v1.2_Kompendium_5.4_DE.apkg 5.4

Bestehende Karten bleiben unverändert. Eine Karte, deren GUID schon im Deck steht,
wird nicht noch einmal angelegt, der Aufruf lässt sich also wiederholen. Die GUID hängt
nur an der Frage: Wer eine Frage später umformuliert, bekommt eine neue Karte.

Kartenformat wie bei den Befehlskarten (siehe befehle_einspielen.py), nur T anders:

    T: <Typ> <Stufe>      z. B. "Szenario Mittel" oder "Pruefungsfalle Schwer"

Typen: Wissen, Szenario, CLI, Interpretation, Vergleich, Exhibit, Vertiefung,
Pruefungsfalle, Rechnen. Karten ohne Codeblock bekommen Modus::Zug, Exhibits und
Interpretationen mit Codeblock Fokus::Exhibit, Prüfungsfallen Fokus::Falle.
"""
import glob, hashlib, json, os, re, shutil, sqlite3, sys, tempfile, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from befehle_einspielen import parse, md, sources_html, strip_html, guid_for  # noqa: E402

NS = "ENCOR-v1.2-Ergaenzung"
TYPEN = {"Wissen": "Wissen", "Szenario": "Szenario", "CLI": "CLI", "Interpretation": "Interpretation",
         "Vergleich": "Vergleich", "Exhibit": "Exhibit", "Vertiefung": "Vertiefung",
         "Pruefungsfalle": "Prüfungsfalle", "Rechnen": "Rechnen"}
STUFEN = {"Leicht", "Mittel", "Schwer"}


def check(c):
    p = []
    if not c["Q"].split("```")[0].strip().endswith("?"):
        p.append("Frage endet nicht mit ?")
    t = c["T"].split()
    if len(t) != 2 or t[0] not in TYPEN or t[1] not in STUFEN:
        p.append(f"T ungültig: {c['T']!r}")
    a = c["A"].lstrip()
    if not (a.startswith("**") or a.startswith("```")):
        p.append("Antwort beginnt nicht fett")
    if "**" not in a:
        p.append("Antwort ohne fetten Kern")
    for k in ("Q", "A", "H"):
        if c[k].count("```") % 2:
            p.append(f"Codeblock in {k} nicht geschlossen")
    return p


def norm(s):
    return re.sub(r"\W+", "", strip_html(s).lower())


def main():
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(2)
    src, dst, version = sys.argv[1:]
    cards, errors = [], []
    for f in sorted(glob.glob(os.path.join(HERE, "ergaenzung*.txt"))):
        cs, es = parse(f)
        cards += cs; errors += es
    seen = set()
    for c in cards:
        errors += [f"{c['loc']}: {p}" for p in check(c)]
        k = norm(c["Q"])
        if k in seen:
            errors.append(f"{c['loc']}: doppelte Frage")
        seen.add(k)

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
    if base != "ENCOR_v1_2":
        sys.exit(f"Unerwartetes Deck: {base}")

    guids = {g for (g,) in db.execute("select guid from notes")}
    fragen = {norm(f.split("\x1f")[names.index("Frage")]) for (f,) in db.execute("select flds from notes")}
    for c in cards:
        if guid_for(NS, c["Q"].strip()) not in guids and norm(md(c["Q"], False)) in fragen:
            errors.append(f"{c['loc']}: Frage steht schon im Deck")
    if errors:
        print("\n".join(errors)); sys.exit(1)

    idx = names.index("ID")
    maxn = {}
    for (flds,) in db.execute("select flds from notes"):
        m = re.match(r"E12-(.+)-(\d+)[a-z]?$", flds.split("\x1f")[idx])
        if m:
            maxn[m.group(1)] = max(maxn.get(m.group(1), 0), int(m.group(2)))

    real = {did: d["name"] for did, d in decks.items() if d["name"] != "Default"}

    def deck_for(dom):
        for did, name in real.items():
            if re.match(rf"^{dom}[ ·]", name.split("::")[-1]):
                return int(did)
        sys.exit(f"Kein Unterdeck für Domäne {dom}")

    now = int(time.time())
    nid = max(int(time.time() * 1000), db.execute("select max(id) from notes").fetchone()[0])
    cid = db.execute("select max(id) from cards").fetchone()[0]
    due = (db.execute("select max(due) from cards where type=0").fetchone()[0] or 0) + 1
    vtag = version.replace(".", "_")
    neu, per = 0, {}
    for c in cards:
        guid = guid_for(NS, c["Q"].strip())
        if guid in guids:
            continue
        typ, stufe = c["T"].split()
        ziel = c["ziel"]
        dom = ziel.split(".")[0]
        maxn[ziel] = maxn.get(ziel, 0) + 1
        code = "```" in c["Q"] + c["A"] + c["H"]
        tags = [base, f"Ziel::{ziel}", f"Domaene::{dom}", f"Typ::{typ}", f"Stufe::{stufe}",
                "Didaktik::4_4", f"Ergaenzung::{vtag}"]
        if not code:
            tags.append("Modus::Zug")
        if typ == "Exhibit" or (typ == "Interpretation" and code):
            tags.append("Fokus::Exhibit")
        if typ == "Pruefungsfalle":
            tags.append("Fokus::Falle")
        werte = {
            "Frage": md(c["Q"], False), "Antwort": md(c["A"], False), "Hinweis": md(c["H"], False),
            "Quellen": sources_html(c["sec"] + c["S"]), "ID": f"E12-{ziel}-{maxn[ziel]:03d}",
            "Ziel": ziel, "Thema": c["thema"], "Typ": f"{TYPEN[typ]} · {stufe}",
        }
        flds = [werte.get(n, "") for n in names]
        sfld = strip_html(flds[model.get("sortf", 0)])
        csum = int(hashlib.sha1(sfld.encode()).hexdigest()[:8], 16)
        nid += 1; cid += 1
        db.execute("insert into notes values (?,?,?,?,?,?,?,?,?,?,?)",
                   (nid, guid, int(mid), now, -1, " " + " ".join(tags) + " ",
                    "\x1f".join(flds), sfld, csum, 0, ""))
        did = deck_for(dom)
        db.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (cid, nid, did, 0, now, -1, 0, 0, due, 0, 0, 0, 0, 0, 0, 0, 0, ""))
        due += 1; neu += 1
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
    print(f"{neu} neue Karten, {len(cards) - neu} schon vorhanden, {total} Karten gesamt -> {dst}")
    for k, v in sorted(per.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
