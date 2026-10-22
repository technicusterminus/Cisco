#!/usr/bin/env python3
"""Baut das ENARSI-Anki-Deck aus den Kartendateien in diesem Ordner.

Aufruf:  python3 build_deck.py [ausgabe.apkg]
Benötigt: pip install genanki

Kartenformat (eine Datei pro Domäne, *.txt):

    # 1.9.c | EIGRP: Loop-freie Pfadwahl
    S: https://... | Titel der Quelle        (gilt für alle Karten des Abschnitts)

    Q: Frage, konkret und mit Situation
    A: **Kern der Antwort.** Danach Mechanismus in ein, zwei Sätzen.
    H: optionaler Hinweis (Merke:, Falle:, nächster Prüfschritt)
    T: Typ Stufe          z. B. "Szenario Mittel"
    S: https://... | zusätzliche Quelle nur für diese Karte

Leerzeilen trennen Karten. Code steht zwischen ``` und ``` (ohne Leerzeilen darin).
Inline: **fett**, `code`.
"""
import glob, hashlib, html, os, re, sys

import genanki

VERSION = "1.0"
STAND = "22.10.2026"
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = 1842041000
DECK_ROOT = "ENARSI 300-410 · Kompendium"
DOMAINS = {
    "1": ("1 Layer-3-Technologien", 1842041101),
    "2": ("2 VPN-Technologien", 1842041102),
    "3": ("3 Infrastruktur-Security", 1842041103),
    "4": ("4 Infrastruktur-Services", 1842041104),
}
TYPEN = {"Wissen": "Wissen", "Szenario": "Szenario", "Vergleich": "Vergleich", "CLI": "CLI",
         "Exhibit": "Exhibit", "Rechnen": "Rechnen", "Falle": "Prüfungsfalle"}
STUFEN = {"Leicht", "Mittel", "Schwer"}

CSS = open(os.path.join(HERE, "karte.css"), encoding="utf-8").read()
HEAD = ('<div class="sheet"><div class="eyebrow">ENARSI 300-410</div><div class="meta">'
        '<span class="badge">{{Ziel}}</span><span class="badge">{{Typ}}</span><span>{{Thema}}</span></div>'
        '<div class="prompt">{{Frage}}</div>')
MODEL = genanki.Model(
    MODEL_ID, "ENARSI 300-410 · Frage–Antwort",
    fields=[{"name": n} for n in ["Frage", "Antwort", "Hinweis", "Quellen", "ID", "Ziel", "Thema", "Typ"]],
    templates=[{
        "name": "Karte",
        "qfmt": HEAD + "</div>",
        "afmt": HEAD + '<hr id="answer"><div class="label">Kernantwort</div><div class="answer">{{Antwort}}</div>'
                '{{#Hinweis}}<div class="hint">{{Hinweis}}</div>{{/Hinweis}}'
                f'<div class="sources"><div>{{{{ID}}}} · Kompendium {VERSION} · Stand {STAND}</div>{{{{Quellen}}}}</div></div>',
    }],
    css=CSS, sort_field_index=0)


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s


def md(text):
    out, parts = [], re.split(r"```\n?(.*?)\n?```", text, flags=re.S)
    for i, p in enumerate(parts):
        if i % 2:
            out.append("<pre><code>" + html.escape(p, quote=False) + "</code></pre>")
        elif p.strip():
            out.append(inline(p.strip()))
    return "".join(out)


def sources_html(srcs):
    if not srcs:
        return ""
    return "<ul>" + "".join(f'<li><a href="{html.escape(u)}">{html.escape(t)}</a></li>' for u, t in srcs) + "</ul>"


def parse(path):
    cards, ziel, thema, sec_src, cur, key = [], None, None, [], None, None
    errors = []

    def close():
        nonlocal cur
        if cur:
            cards.append(cur)
        cur = None

    for ln, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        in_code = cur is not None and key and cur[key].count("```") % 2 == 1
        if in_code:
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


def check(c):
    p = []
    if not c["Q"].strip().endswith("?"):
        p.append("Frage endet nicht mit ?")
    typ_stufe = c["T"].split()
    if len(typ_stufe) != 2 or typ_stufe[0] not in TYPEN or typ_stufe[1] not in STUFEN:
        p.append(f"T ungültig: {c['T']!r}")
    a = c["A"].lstrip()
    if not (a.startswith("**") or (typ_stufe and typ_stufe[0] == "CLI" and a.startswith("```"))):
        p.append("Antwort beginnt nicht fett")
    if a.count("```") % 2:
        p.append("Codeblock nicht geschlossen")
    for w in ("konzeptionell", "plattformabhängig", "im üblichen", "Lehrbeispiel"):
        if w in c["Q"] + c["A"] + c["H"]:
            p.append(f"Floskel: {w}")
    return p


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), f"ENARSI_300-410_Kompendium_{VERSION}_DE.apkg")
    cards, errors = [], []
    for f in sorted(glob.glob(os.path.join(HERE, "*.txt"))):
        cs, es = parse(f)
        cards += cs; errors += es
    counter, seen = {}, set()
    decks = {d: genanki.Deck(did, f"{DECK_ROOT}::{name}") for d, (name, did) in DOMAINS.items()}
    for c in cards:
        for p in check(c):
            errors.append(f"{c['loc']}: {p}")
        key = re.sub(r"\W+", "", c["Q"].lower())
        if key in seen:
            errors.append(f"{c['loc']}: doppelte Frage")
        seen.add(key)
    if errors:
        print("\n".join(errors)); sys.exit(1)
    for c in cards:
        counter[c["ziel"]] = counter.get(c["ziel"], 0) + 1
        cid = f"N11-{c['ziel']}-{counter[c['ziel']]:03d}"
        typ, stufe = c["T"].split()
        dom = c["ziel"].split(".")[0]
        frage, antwort = md(c["Q"]), md(c["A"])
        tags = ["ENARSI_300_410", f"Ziel::{c['ziel']}", f"Domaene::{dom}", f"Typ::{typ}", f"Stufe::{stufe}",
                f"Kompendium::{VERSION.replace('.', '_')}"]
        if "<pre>" not in frage + antwort and typ != "CLI" and len(c["Q"]) + len(c["A"]) < 360:
            tags.append("Modus::Zug")
        if typ == "Falle":
            tags.append("Fokus::Falle")
        if typ == "Exhibit":
            tags.append("Fokus::Exhibit")
        note = genanki.Note(
            model=MODEL,
            fields=[frage, antwort, md(c["H"]), sources_html(c["sec"] + c["S"]), cid, c["ziel"], c["thema"],
                    f"{TYPEN[typ]} · {stufe}"],
            tags=tags,
            guid=genanki.guid_for("ENARSI-300-410", hashlib.sha1(c["Q"].strip().encode()).hexdigest()[:16]))
        decks[dom].add_note(note)
    genanki.Package(list(decks.values())).write_to_file(out)
    per = {d: len(decks[d].notes) for d in decks}
    print(f"{len(cards)} Karten -> {out}  {per}")


if __name__ == "__main__":
    main()
