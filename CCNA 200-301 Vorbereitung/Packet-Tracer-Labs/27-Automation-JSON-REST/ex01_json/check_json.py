#!/usr/bin/env python3
"""Prueft broken.json (oder eine als Argument uebergebene Datei) auf gueltiges JSON."""
import json, sys
p = sys.argv[1] if len(sys.argv) > 1 else "broken.json"
try:
    d = json.load(open(p))
except json.JSONDecodeError as e:
    print(f"FEHLER in Zeile {e.lineno}, Spalte {e.colno}: {e.msg}"); sys.exit(1)
ports = d.get("device", {}).get("ports")
if not isinstance(ports, list) or len(ports) != 3:
    print("FEHLER: device.ports soll eine Liste mit 3 Eintraegen sein"); sys.exit(1)
print("OK: gueltiges JSON, 3 Ports")
