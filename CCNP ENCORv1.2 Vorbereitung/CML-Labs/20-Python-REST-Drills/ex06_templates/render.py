#!/usr/bin/env python3
"""Rendert interfaces.j2 (oder eine als Argument uebergebene Vorlage) mit data.yml und vergleicht mit expected.txt.
pip install jinja2 pyyaml"""
import difflib, os, sys, yaml
from jinja2 import Environment, FileSystemLoader
here = os.path.dirname(os.path.abspath(__file__))
tpl = sys.argv[1] if len(sys.argv) > 1 else "interfaces.j2"
env = Environment(loader=FileSystemLoader(here), trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
out = env.get_template(tpl).render(**yaml.safe_load(open(os.path.join(here, "data.yml"))))
exp = open(os.path.join(here, "expected.txt")).read()
if out == exp:
    print("OK: Template erzeugt die erwartete Konfiguration")
else:
    print("ABWEICHUNG:")
    sys.stdout.writelines(difflib.unified_diff(exp.splitlines(True), out.splitlines(True), "erwartet", "erzeugt"))
    sys.exit(1)
