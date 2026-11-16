#!/usr/bin/env python3
"""Trägt die Tickets der Labs aus lab_NN.py in ../Trainer/ticket-trainer.html ein (wiederholbar)."""
import glob, importlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PATH = os.path.join(os.path.dirname(HERE), "Trainer", "ticket-trainer.html")


def const(src, name):
    m = re.search(r"const " + name + r"=(\[.*?\]);\n", src, re.S)
    return m, json.loads(m.group(1))


def main():
    labs = [importlib.import_module(os.path.basename(f)[:-3]).LAB
            for f in sorted(glob.glob(os.path.join(HERE, "lab_[0-9]*.py")))]
    src = open(PATH, encoding="utf-8").read()
    nums = {l["num"] for l in labs}
    for name in ("LABS", "T"):
        m, data = const(src, name)
        if name == "LABS":
            data = [x for x in data if x["n"] not in nums] + [{"n": l["num"], "t": l["title"]} for l in labs]
        else:
            data = [x for x in data if x["l"] not in nums]
            for l in labs:
                for k, f in enumerate(l["faults"], 1):
                    d = "\n".join(p + v for p, v in (("-", f.get("old")), ("+", f.get("new"))) if v is not None)
                    data.append({"l": l["num"], "n": k, "dev": f["node"], "s": l["tickets"][k - 1], "h": f["find"],
                                 "u": f["cause"], "f": f["fix"], "d": d})
            total = len(data)
        src = src[:m.start(1)] + json.dumps(data, ensure_ascii=False) + src[m.end(1):]
    open(PATH, "w", encoding="utf-8").write(src)
    print(f"{total} Tickets im Trainer")


if __name__ == "__main__":
    main()
