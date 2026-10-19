#!/usr/bin/env python3
"""Mock einer Controller-REST-API (angelehnt an Catalyst Center) fuer die Uebungen.
Nur Standardbibliothek. Start: python3 server.py [port]   (Standard 8080)
Zugangsdaten: admin / Lab#2026!  (Rolle SUPER-ADMIN)   viewer / View#2026!  (Rolle OBSERVER, nur lesen)
"""
import base64, json, sys, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

USERS = {"admin": ("Lab#2026!", "SUPER-ADMIN-ROLE"), "viewer": ("View#2026!", "OBSERVER-ROLE")}
DEVICES = [{"id": f"dev-{i:03d}", "hostname": f"sw{i:02d}.lab.local", "managementIpAddress": f"10.0.0.{i}",
            "platformId": "C9300-24P" if i % 2 else "C9200L-24P", "role": "ACCESS",
            "reachabilityStatus": "Reachable" if i % 7 else "Unreachable", "description": ""} for i in range(1, 26)]
LOCK = threading.Lock()
STATE = {"tokens": {}, "flaky": 0, "limited": 0}

def reset():
    with LOCK:
        STATE.update(tokens={}, flaky=0, limited=0)
        for d in DEVICES: d["description"] = ""

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _send(self, code, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items(): self.send_header(k, v)
        self.end_headers()
        if data: self.wfile.write(data)
    def _role(self):
        t = self.headers.get("X-Auth-Token")
        return STATE["tokens"].get(t) if t else None
    def _auth(self):
        role = self._role()
        if role is None:
            self._send(401, {"response": {"message": "Token fehlt oder ungueltig"}}); return None
        return role
    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0); self.rfile.read(n)
        if u.path == "/dna/system/api/v1/auth/token":
            h = self.headers.get("Authorization", "")
            try:
                user, pw = base64.b64decode(h.split()[1]).decode().split(":", 1)
            except Exception:
                return self._send(401, {"error": "Basic-Auth erwartet"})
            if user in USERS and USERS[user][0] == pw:
                tok = uuid.uuid4().hex
                with LOCK: STATE["tokens"][tok] = USERS[user][1]
                return self._send(200, {"Token": tok})
            return self._send(401, {"error": "Anmeldung fehlgeschlagen"})
        if u.path == "/__reset": reset(); return self._send(200, {"ok": True})
        self._send(405, {"error": "Methode nicht erlaubt"})
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/api/v1/flaky":
            with LOCK: STATE["flaky"] += 1; c = STATE["flaky"]
            if c <= 2: return self._send(503, {"error": "Dienst kurz nicht verfuegbar"}, {"Retry-After": "0"})
            return self._send(200, {"response": "ok nach %d Versuchen" % c})
        if u.path == "/api/v1/limited":
            with LOCK: STATE["limited"] += 1; c = STATE["limited"]
            if c % 2 == 1: return self._send(429, {"error": "zu viele Anfragen"}, {"Retry-After": "0"})
            return self._send(200, {"response": "ok"})
        role = self._auth()
        if role is None: return
        if u.path == "/dna/intent/api/v1/network-device/count":
            return self._send(200, {"response": len(DEVICES), "version": "1.0"})
        if u.path == "/dna/intent/api/v1/network-device":
            off = int(q.get("offset", ["1"])[0]); lim = int(q.get("limit", ["500"])[0])
            if off < 1 or lim < 1: return self._send(400, {"response": {"message": "offset >= 1, limit >= 1"}})
            return self._send(200, {"response": DEVICES[off - 1: off - 1 + min(lim, 10)], "version": "1.0"})
        if u.path.startswith("/dna/intent/api/v1/network-device/"):
            did = u.path.rsplit("/", 1)[1]
            for d in DEVICES:
                if d["id"] == did: return self._send(200, {"response": d, "version": "1.0"})
            return self._send(404, {"response": {"message": "Geraet nicht gefunden"}})
        self._send(404, {"error": "Pfad unbekannt"})
    def do_PATCH(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n)
        role = self._auth()
        if role is None: return
        if role == "OBSERVER-ROLE": return self._send(403, {"response": {"message": "Rolle darf nicht schreiben"}})
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._send(415, {"error": "Content-Type application/json erforderlich"})
        try: body = json.loads(raw or b"{}")
        except ValueError: return self._send(400, {"error": "Ungueltiges JSON"})
        did = u.path.rsplit("/", 1)[1]
        for d in DEVICES:
            if d["id"] == did:
                if "description" not in body: return self._send(400, {"error": "Feld description fehlt"})
                d["description"] = str(body["description"])
                return self._send(202, {"response": {"taskId": uuid.uuid4().hex, "url": "/api/v1/task/x"}, "version": "1.0"})
        self._send(404, {"response": {"message": "Geraet nicht gefunden"}})
    def do_DELETE(self): self._send(405, {"error": "Methode nicht erlaubt"})

def make_server(port=0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"Mock-API auf http://127.0.0.1:{port}  (Strg+C beendet)")
    srv.serve_forever()
