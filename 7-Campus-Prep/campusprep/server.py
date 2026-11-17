"""HTTP-Server: Catalyst-Center-API (Pfade wie im Original) und eine WLC-CLI unter /wlc/cli."""
import copy
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .catc import CatalystCenter
from .labs import LabEngine, LabError
from .store import KIND, VERSION, Store, StoreError, validate_state
from .wlc import Cli, Wlc, apply_commands
from .world import new_world


STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
         '.svg': 'image/svg+xml'}


class Sim:
    def __init__(self, labs_dir=None, data_dir=None):
        self.lock = threading.Lock()
        self.reset_world()
        self.labs = LabEngine(self, labs_dir) if labs_dir else LabEngine(self)
        self.store = Store(data_dir) if data_dir else None
        if self.store:
            self.labs.progress = self.store.read_progress()
            st = self.store.read_state()
            if st is not None:
                try:
                    self.restore_all(st)
                except StoreError:
                    self.store._quarantine(os.path.join(self.store.dir, 'state.json'))

    # ------------------------------------------------------------------ Staende
    def snapshot_all(self):
        return {'kind': KIND, 'version': VERSION, 'world': copy.deepcopy(self.world), 'wlc': self.wlc.dump(),
                'lab': copy.deepcopy(self.labs.session)}

    def restore_all(self, d):
        """Zustand ersetzen. Wirft StoreError und laesst die laufende Sim unveraendert, wenn der Stand nicht passt."""
        validate_state(d)
        world = copy.deepcopy(d['world'])
        wlc = Wlc(world)
        try:
            wlc.load(d['wlc'])
            wlc.state()
        except (KeyError, TypeError, ValueError, AttributeError):
            raise StoreError('Stand ist beschaedigt')
        self.world, self.wlc = world, wlc
        self.cli = Cli(self.wlc)
        self.catc = CatalystCenter(self.world)
        self.labs.restore_session(d.get('lab'))

    def persist(self):
        if self.store:
            self.store.write_state(self.snapshot_all())
            self.store.write_progress(self.labs.progress)

    def reset_world(self, clients=None):
        """Neue Welt (Standard oder mit Lab-Clients) und unkonfigurierter Controller."""
        self.world = new_world()
        if clients is not None:
            self.world['clients'] = copy.deepcopy(clients)
        self.wlc = Wlc(self.world)
        self.cli = Cli(self.wlc)
        self.catc = CatalystCenter(self.world)

    def apply(self, commands):
        return apply_commands(self.wlc, commands)

    def ui_state(self):
        """Zustand fuer die Oberflaeche. Im Pruefungsmodus gibt es keine Begruendungen der Client-Diagnose."""
        st = self.wlc.state()
        sess = self.labs.session
        exam = bool(sess and sess['mode'] == 'exam')
        if exam:
            for c in st['clients']:
                c['reasons'] = []
        st['diagAvailable'] = not exam
        st['lab'] = {'id': sess['id'], 'mode': sess['mode']} if sess else None
        st['persistent'] = self.store is not None
        return st


def make_handler(sim):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, status, obj):
            if self.command == 'POST':
                sim.persist()   # vor der Antwort: nach der Antwort darf der Client sofort neu starten
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

        def _saves(self, method, path, raw):
            if sim.store is None:
                return self._send(409, {'error': 'Persistenz ist ausgeschaltet'})
            try:
                body = json.loads(raw) if raw else {}
                assert isinstance(body, dict)
            except (ValueError, AssertionError):
                return self._send(400, {'error': 'JSON-Objekt erwartet'})
            try:
                if (method, path) == ('GET', '/wlc/api/saves'):
                    return self._send(200, {'saves': sim.store.list_named()})
                if (method, path) == ('POST', '/wlc/api/saves'):
                    sim.store.save_named(body.get('name'), sim.snapshot_all())
                    return self._send(200, {'saves': sim.store.list_named()})
                if (method, path) == ('POST', '/wlc/api/saves/load'):
                    sim.restore_all(sim.store.load_named(body.get('name')))
                    return self._send(200, {'ok': True})
                if (method, path) == ('POST', '/wlc/api/saves/delete'):
                    sim.store.delete_named(body.get('name'))
                    return self._send(200, {'saves': sim.store.list_named()})
                if (method, path) == ('POST', '/wlc/api/progress/reset'):
                    sim.labs.reset_progress()
                    return self._send(200, {'labs': sim.labs.list()})
            except StoreError as e:
                return self._send(e.status, {'error': str(e)})
            return self._send(404, {'error': 'Endpunkt nicht umgesetzt'})

        def _lab(self, method, path, raw):
            L = sim.labs
            try:
                body = json.loads(raw) if raw else {}
                assert isinstance(body, dict)
            except (ValueError, AssertionError):
                return self._send(400, {'error': 'JSON-Objekt erwartet'})
            try:
                if (method, path) == ('GET', '/wlc/api/labs'):
                    return self._send(200, {'labs': L.list(), 'current': L.public()})
                if (method, path) == ('GET', '/wlc/api/lab'):
                    return self._send(200, {'current': L.public()})
                if (method, path) == ('POST', '/wlc/api/lab/start'):
                    return self._send(200, {'current': L.start(body.get('id', ''), body.get('mode', 'guided'))})
                if (method, path) == ('POST', '/wlc/api/lab/reset'):
                    return self._send(200, {'current': L.reset()})
                if (method, path) == ('POST', '/wlc/api/lab/stop'):
                    L.stop()
                    return self._send(200, {'current': None})
                if (method, path) == ('POST', '/wlc/api/lab/hint'):
                    return self._send(200, {'current': L.hint()})
                if (method, path) == ('GET', '/wlc/api/lab/solution'):
                    return self._send(200, L.solution())
                if (method, path) == ('POST', '/wlc/api/lab/answer'):
                    return self._send(200, L.answer(body.get('id', ''), body.get('answer')))
                if (method, path) == ('POST', '/wlc/api/lab/check'):
                    return self._send(200, L.check())
            except LabError as e:
                return self._send(e.status, {'error': str(e)})
            return self._send(404, {'error': 'Endpunkt nicht umgesetzt'})

        def _go(self, method):
            u = urlparse(self.path)
            if method == 'GET' and (u.path in ('/', '') or u.path.startswith('/static/')):
                return self._static(u.path)
            n = int(self.headers.get('Content-Length') or 0)
            raw = self.rfile.read(n) if n else b''
            with sim.lock:
                if u.path == '/wlc/api/state' and method == 'GET':
                    return self._send(200, sim.ui_state())
                if u.path.startswith('/wlc/api/saves') or u.path == '/wlc/api/progress/reset':
                    return self._saves(method, u.path, raw)
                if u.path.startswith('/wlc/api/lab'):
                    return self._lab(method, u.path, raw)
                if u.path == '/wlc/api/apply' and method == 'POST':
                    try:
                        cmds = json.loads(raw or b'{}').get('commands')
                        assert isinstance(cmds, list) and all(isinstance(x, str) for x in cmds)
                    except (ValueError, AssertionError):
                        return self._send(400, {'error': 'JSON erwartet: {"commands": ["..."]}'})
                    ok, results, err = apply_commands(sim.wlc, cmds)
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


def serve(port=8090, host='127.0.0.1', data_dir=None):
    sim = Sim(data_dir=data_dir)
    srv = ThreadingHTTPServer((host, port), make_handler(sim))
    return srv, sim


if __name__ == '__main__':
    import sys
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    srv, _ = serve(p)
    print('Campus Prep: http://127.0.0.1:%d  (Catalyst Center API, WLC-CLI unter POST /wlc/cli)' % p)
    srv.serve_forever()
