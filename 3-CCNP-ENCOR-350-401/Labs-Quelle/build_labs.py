#!/usr/bin/env python3
"""Erzeugt die ENCOR-Labs ab Nummer 32 (CML und EVE-NG) aus den Definitionen lab_*.py.

Aufruf:  python3 build_labs.py          (benötigt: pip install pyyaml)
Schreibt in ../CML-Labs und ../EVE-NG-Labs. Geprüft wird dabei, dass jeder Fehler auf eine vorhandene
Konfigurationszeile trifft, dass die Links auf freie, vorhandene Interfaces zeigen, dass die Adressen
an jedem Link im selben Subnetz liegen und dass die Tickets zur Fehlerliste passen.

Danach die EVE-NG-Importdateien neu bauen (aus dem Paketordner):
  python3 EVE-NG-Labs/tools/build_eve_import.py --paket ENCOR

Die Labs 01 bis 31 sind älter und liegen nur als fertige Dateien vor. Die Übersichtstabellen in den
READMEs und ZIELE.md werden von Hand gepflegt; dieses Skript gibt die Zeilen dafür aus.
"""
import glob, importlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lablib

ROOT = os.path.dirname(HERE)


def main():
    labs = [importlib.import_module(os.path.basename(f)[:-3]).LAB
            for f in sorted(glob.glob(os.path.join(HERE, "lab_[0-9]*.py")))]
    for lab in labs:
        lablib.render(lab, ROOT)
    for plat in ("cml", "eve"):
        print(f"\n{plat}:")
        for l in labs:
            ram = sum(lablib.EVE_TPL[n["type"]][1] for n in l["nodes"]) / 1000
            ziele = ", ".join(t for t, _, _ in l["tags"])
            print(f"| [{l['num']}]({l['slug']}/) | {l['title']} | {ziele} | {len(l['nodes'])} | {len(l['faults'])} | "
                  + (f"{ram:.1f} GB | " if plat == "eve" else "") + f"{l['minutes']} min |")
    print(f"\n{len(labs)} Labs, {sum(len(l['faults']) for l in labs)} Fehler")
    return labs


if __name__ == "__main__":
    main()
