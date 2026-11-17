"""HTTP-Server: Catalyst-Center-API (Pfade wie im Original) und eine WLC-CLI unter /wlc/cli."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .catc import CatalystCenter
from .wlc import Cli, Wlc
from .world import new_world


STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
         '.svg': 'image/svg+xml'}


def apply_commands(sim, commands):
    """Befehle atomar anwenden: Bei einem Fehler wird die Konfiguration auf den Stand davor zurueckgesetzt.
    Die Oberflaeche geht damit durch dieselbe CLI wie ein Benutzer (eine Wahrheit)."""
    snap = sim.wlc.snapshot()
    cli = Cli(sim.wlc)
    results = []
    for line in ['configure terminal'] + list(commands) + ['end']:
        out = cli.run(line)
        results.append({'command': line, 'output': out})
        if out.startswith('% '):
            sim.wlc.restore(snap)
            return False, results, {'command': line, 'message': out[2:]}
    return True, results, None


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

        def _static(self, path):
            rel = 'index.html' if path in ('/', '') else path[len('/static/'):] if path.startswith('/static/') else None
            full = os.path.realpath(os.path.join(STATIC, rel)) if rel else None
            root = os.path.realpath(STATIC)
            if not full or not full.startswith(root + os.sep) or not os.path.isfile(full):
                return self._send(404, {'error': 'nicht gefunden'})
            with open(full, 'rb') as fh:
                data = fh.read()
            self.send_response(200)
            self.send_header('Content-Type', TYPES.get(os.path.splitext(full)[1], 'application/octet-stream'))
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _go(self, method):
            u = urlparse(self.path)
            if method == 'GET' and (u.path in ('/', '') or u.path.startswith('/static/')):
                return self._static(u.path)
            n = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(n) if n else b''
            with sim.lock:
                if u.path == '/wlc/api/state' and method == 'GET':
                    return self._send(200, sim.wlc.state())
                if u.path == '/wlc/api/apply' and method == 'POST':
                    try:
                        cmds = json.loads(raw or b'{}').get('commands')
                        assert isinstance(cmds, list) and all(isinstance(x, str) for x in cmds)
                    except (ValueError, AssertionError):
                        return self._send(400, {'error': 'JSON erwartet: {"commands": ["..."]}'})
                    ok, results, err = apply_commands(sim, cmds)
                    return self._send(200 if ok else 400, {'ok': ok, 'results': results, 'error': err})
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
