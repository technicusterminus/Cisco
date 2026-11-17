#!/usr/bin/env python3
"""Campus Prep starten:  python3 start.py [port]   (Standard 8090, nur localhost)"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campusprep.server import serve  # noqa: E402

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    srv, _ = serve(port)
    print('Campus Prep laeuft auf http://127.0.0.1:%d  (Strg+C beendet)' % port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
