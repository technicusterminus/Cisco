#!/usr/bin/env python3
"""Prueft playbook_broken.yml (oder eine Datei als Argument). pip install pyyaml"""
import sys, yaml
path = sys.argv[1] if len(sys.argv) > 1 else "playbook_broken.yml"
errors = []
try: pb = yaml.safe_load(open(path))
except yaml.YAMLError as e:
    print("YAML-Syntaxfehler:", e); sys.exit(1)
if not isinstance(pb, list) or not pb: errors.append("Playbook muss eine Liste von Plays sein")
else:
    for play in pb:
        if "hosts" not in play: errors.append("Play ohne `hosts`")
        if play.get("connection") != "ansible.netcommon.network_cli": errors.append("`connection` muss ansible.netcommon.network_cli sein")
        if play.get("gather_facts") is not False: errors.append("`gather_facts: false` setzen")
        for t in play.get("tasks", []):
            mod = next((k for k in t if k not in ("name", "notify", "when", "tags", "register")), None)
            if mod is None: errors.append(f"Task {t.get('name')} ohne Modul"); continue
            if not mod.startswith("cisco.ios."): errors.append(f"Task '{t.get('name')}': Modul '{mod}' sollte voll qualifiziert sein (cisco.ios.ios_config)")
            a = t.get(mod) or {}
            if not isinstance(a.get("lines"), list): errors.append(f"Task '{t.get('name')}': `lines` muss eine Liste sein")
            if "parents" in a and not isinstance(a["parents"], list): errors.append(f"Task '{t.get('name')}': `parents` muss eine Liste sein")
            if "notify" in t and not any(h.get("name") == t["notify"] for h in play.get("handlers", [])):
                errors.append(f"Task '{t.get('name')}': notify '{t['notify']}' hat keinen Handler")
print("OK" if not errors else "\n".join("FEHLER: " + e for e in errors))
sys.exit(1 if errors else 0)
