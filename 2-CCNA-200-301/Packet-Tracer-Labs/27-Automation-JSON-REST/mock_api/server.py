#!/usr/bin/env python3
"""Mock-REST-API fuer VLANs (CCNA 6.5). Nur Standardbibliothek.
Start: python3 server.py [port]   (Standard 8080)
API-Schluessel: lab-key-123 (lesen+schreiben), lab-ro-key (nur lesen). Header: X-API-Key
Basic-Auth (admin / Lab#2026!) wird zusaetzlich akzeptiert."""
import base64, json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

KEYS = {"lab-key-123": "rw", "lab-ro-key": "ro"}
LOCK = threading.Lock()
VLANS = {}
def reset():
    with LOCK:
        VLANS.clear(); VLANS.update({1: "default", 10: "USERS", 20: "SERVER"})
reset()

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
        k = self.headers.get("X-API-Key")
        if k: return KEYS.get(k)
        a = self.headers.get("Authorization", "")
        if a.startswith("Basic "):
            try:
                u, p = base64.b64decode(a.split()[1]).decode().split(":", 1)
                if (u, p) == ("admin", "Lab#2026!"): return "rw"
            except Exception: pass
        return None
    def _check(self, write):
        role = self._role()
        if role is None:
            self._send(401, {"error": "Authentisierung fehlt oder ungueltig"}); return False
        if write and role != "rw":
            self._send(403, {"error": "Schluessel darf nicht schreiben"}); return False
        return True
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n)
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            self._send(415, {"error": "Content-Type application/json erforderlich"}); return None
        try: d = json.loads(raw or b"{}")
        except ValueError:
            self._send(400, {"error": "Ungueltiges JSON"}); return None
        if not isinstance(d, dict):
            self._send(400, {"error": "JSON-Objekt erwartet"}); return None
        return d
    def _vid(self):
        p = urlparse(self.path).path.rstrip("/").split("/")
        try: return int(p[-1])
        except ValueError: return None
    def _is_collection(self): return urlparse(self.path).path.rstrip("/") == "/api/v1/vlans"
    def do_GET(self):
        if not self._check(False): return
        u = urlparse(self.path)
        if self._is_collection():
            q = parse_qs(u.query)
            items = [{"id": k, "name": v} for k, v in sorted(VLANS.items())]
            if "name" in q: items = [i for i in items if i["name"] == q["name"][0]]
            return self._send(200, {"count": len(items), "vlans": items})
        vid = self._vid()
        if vid in VLANS: return self._send(200, {"id": vid, "name": VLANS[vid]})
        self._send(404, {"error": "VLAN nicht gefunden"})
    def do_POST(self):
        if not self._check(True): return
        if not self._is_collection(): return self._send(405, {"error": "POST nur auf /api/v1/vlans"})
        d = self._body()
        if d is None: return
        vid, name = d.get("id"), d.get("name")
        if not isinstance(vid, int) or isinstance(vid, bool) or not 1 <= vid <= 4094 or not isinstance(name, str) or not name:
            return self._send(400, {"error": "id (1-4094) und name erforderlich"})
        with LOCK:
            if vid in VLANS: return self._send(409, {"error": "VLAN existiert bereits"})
            VLANS[vid] = name
        self._send(201, {"id": vid, "name": name}, {"Location": f"/api/v1/vlans/{vid}"})
    def do_PUT(self):
        if not self._check(True): return
        d = self._body()
        if d is None: return
        vid = self._vid()
        if vid not in VLANS: return self._send(404, {"error": "VLAN nicht gefunden"})
        if not isinstance(d.get("name"), str) or not d["name"]: return self._send(400, {"error": "name erforderlich (PUT ersetzt die ganze Ressource)"})
        with LOCK: VLANS[vid] = d["name"]
        self._send(200, {"id": vid, "name": d["name"]})
    def do_PATCH(self):
        if not self._check(True): return
        d = self._body()
        if d is None: return
        vid = self._vid()
        if vid not in VLANS: return self._send(404, {"error": "VLAN nicht gefunden"})
        if "name" in d:
            if not isinstance(d["name"], str) or not d["name"]: return self._send(400, {"error": "name ungueltig"})
            with LOCK: VLANS[vid] = d["name"]
        self._send(200, {"id": vid, "name": VLANS[vid]})
    def do_DELETE(self):
        if not self._check(True): return
        vid = self._vid()
        if vid not in VLANS: return self._send(404, {"error": "VLAN nicht gefunden"})
        with LOCK: del VLANS[vid]
        self._send(204)

def make_server(port=0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"Mock-API auf http://127.0.0.1:{port}  (Strg+C beendet)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
