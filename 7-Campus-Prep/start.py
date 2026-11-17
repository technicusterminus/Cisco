#!/usr/bin/env python3
"""Campus Prep starten.

    python3 start.py                  Port 8090, Zustand in ./data (nur localhost)
    python3 start.py 8095             anderer Port
    python3 start.py --data DIR       anderes Datenverzeichnis
    python3 start.py --ephemeral      ohne dauerhaften Zustand (temporaeres Verzeichnis, fuer Tests)
"""
import argparse
import atexit
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campusprep.server import serve  # noqa: E402

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Campus Prep: simulierter C9800 WLC und Catalyst Center')
    ap.add_argument('port', nargs='?', type=int, default=8090)
    ap.add_argument('--data', default=os.path.join(HERE, 'data'), help='Datenverzeichnis (Standard: ./data)')
    ap.add_argument('--ephemeral', action='store_true', help='Zustand nur fuer diesen Lauf (temporaeres Verzeichnis)')
    a = ap.parse_args()
    data = a.data
    if a.ephemeral:
        data = tempfile.mkdtemp(prefix='campusprep-')
        atexit.register(shutil.rmtree, data, True)
    srv, _ = serve(a.port, data_dir=data)
    print('Campus Prep laeuft auf http://127.0.0.1:%d  (Daten: %s; Strg+C beendet)' % (srv.server_address[1], data))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
