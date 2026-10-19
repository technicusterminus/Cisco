#!/usr/bin/env python3
"""Spielt Konfigurationsdateien eines Labs per Telnet-Konsole in EVE-NG-Nodes ein.

EVE-NG kann Startkonfigurationen nicht per Datei importieren. Dieses Skript tippt sie
stellvertretend für dich in die Konsole jedes Nodes (wie Copy and Paste), mit kleinen Pausen.

Beispiele:
  python3 eve_push_configs.py 192.168.1.50 ../05-VLANs-Trunks-EtherChannel --mode build \\
      --ports R1=32769 SW1=32770 SW2=32771
  python3 eve_push_configs.py 192.168.1.50 ../05-VLANs-Trunks-EtherChannel --mode repair \\
      --ports R1=32769 SW1=32770 --dry-run

Die Telnet-Ports stehen in EVE-NG im Lab (Rechtsklick auf den Node bzw. Liste *Nodes*).
Voraussetzungen: Der Node ist gestartet, durchgebootet und zeigt einen Prompt (`Router>`/`Switch>`).
Fragt ein Image beim ersten Start nach dem Initial-Dialog, vorher manuell mit `no` beantworten.
Nur Standardbibliothek; getestet gegen einen lokalen Dummy-Telnet-Server, nicht gegen echtes EVE-NG.
"""
import argparse, os, socket, sys, time

def drain(sock, wait=0.2):
    sock.settimeout(wait); data = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk: break
            data += chunk
    except (socket.timeout, BlockingIOError):
        pass
    return data

def send_lines(sock, lines, delay):
    for i, line in enumerate(lines, 1):
        sock.sendall(line.encode() + b"\r\n"); time.sleep(delay)
        if i % 20 == 0: drain(sock, 0.1)

def load(path):
    with open(path) as f:
        return [l.rstrip("\n") for l in f if l.strip() and not l.lstrip().startswith("!")]

def push(host, port, lines, nxos, delay, dry):
    pre = ["", ""] if not nxos else [""]
    body = (["configure terminal"] if True else []) + lines + ["end"]
    post = ["copy running-config startup-config", ""] if nxos else ["write memory"]
    if not nxos: pre += ["enable"]
    seq = pre + body + post
    if dry:
        print(f"--- {host}:{port} ({len(seq)} Zeilen)"); print("\n".join(seq[:6]) + "\n..."); return
    s = socket.create_connection((host, port), timeout=10)
    try:
        time.sleep(0.5); drain(s, 0.5)
        send_lines(s, seq, delay)
        time.sleep(1.0); out = drain(s, 1.0)
        tail = out.decode(errors="replace").strip().splitlines()[-3:]
        print(f"{host}:{port}: {len(seq)} Zeilen gesendet. Letzte Ausgabe: {' | '.join(tail)}")
    finally:
        s.close()

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host"); ap.add_argument("lab", help="Lab-Ordner mit build/, repair/, solutions/")
    ap.add_argument("--mode", choices=["build", "repair", "solutions"], default="build")
    ap.add_argument("--ports", nargs="+", required=True, metavar="NODE=PORT", help="Telnet-Port je Node (Router/Switch)")
    ap.add_argument("--vpcs", nargs="*", default=[], metavar="HOST=PORT", help="VPCS-Hosts, Dateien aus vpcs/")
    ap.add_argument("--delay", type=float, default=0.08, help="Pause je Zeile in Sekunden (Standard 0.08)")
    ap.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nichts senden")
    a = ap.parse_args(argv)
    ok = True
    for item in a.ports:
        node, port = item.split("="); path = os.path.join(a.lab, a.mode, node + ".cfg")
        if not os.path.exists(path): print(f"{node}: keine Datei {path}, übersprungen"); continue
        lines = load(path); nxos = any(l.startswith("feature ") for l in lines)
        push(a.host, int(port), lines, nxos, a.delay, a.dry_run)
    for item in a.vpcs:
        node, port = item.split("="); path = os.path.join(a.lab, "vpcs", node + ".vpc")
        if not os.path.exists(path): print(f"{node}: keine VPCS-Datei {path}"); continue
        lines = [l.rstrip("\n") for l in open(path) if l.strip()]
        if a.dry_run: print(f"--- {a.host}:{port} (VPCS)\n" + "\n".join(lines)); continue
        s = socket.create_connection((a.host, int(port)), timeout=10)
        try: time.sleep(0.5); drain(s, 0.5); send_lines(s, [""] + lines, a.delay); time.sleep(0.5)
        finally: s.close()
        print(f"{a.host}:{port}: VPCS {node} gesetzt")
if __name__ == "__main__":
    main()
