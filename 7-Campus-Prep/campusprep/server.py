"""HTTP-Server: Catalyst-Center-API (Pfade wie im Original) und eine WLC-CLI unter /wlc/cli."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .catc import CatalystCenter
from .wlc import Cli, Wlc
from .world import new_world


class Sim:
    def __init__(self):
        self.world = new_world()
        self.wlc = Wlc(self.world)
        self.cli = Cli(self.wlc)
        self.catc = CatalystCenter(self.world)
        self.lock = threading.Lock()


def make_handler(sim):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, status, obj):
            data = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _go(self, method):
            u = urlparse(self.path)
            n = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(n) if n else b''
            with sim.lock:
                if u.path == '/wlc/cli' and method == 'POST':
                    try:
                        line = json.loads(raw or b'{}').get('command', '')
                    except ValueError:
                        return self._send(400, {'error': 'JSON erwartet: {"command": "..."}'})
                    out = sim.cli.run(line)
                    return self._send(200, {'output': out, 'prompt': sim.cli.prompt})
                status, obj = sim.catc.handle(method, u.path, parse_qs(u.query), dict(self.headers), raw)
            self._send(status, obj)

        def do_GET(self):
            self._go('GET')

        def do_POST(self):
            self._go('POST')

    return H


def serve(port=8090, host='127.0.0.1'):
    sim = Sim()
    srv = ThreadingHTTPServer((host, port), make_handler(sim))
    return srv, sim


if __name__ == '__main__':
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    srv, _ = serve(p)
    print('Campus Prep: http://127.0.0.1:%d  (Catalyst Center API, WLC-CLI unter POST /wlc/cli)' % p)
    srv.serve_forever()
