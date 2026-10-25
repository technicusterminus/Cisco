import json
import urllib.request, urllib.error

def _call(method, url, key, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-API-Key", key)
    if data is not None: req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw) if raw else None), dict(e.headers)

def list_vlans(base, key):
    st, js, _ = _call("GET", base + "/api/v1/vlans", key)
    if st == 401: raise PermissionError("401")
    return js["vlans"]

def get_vlan(base, key, vid):
    st, js, _ = _call("GET", f"{base}/api/v1/vlans/{vid}", key)
    if st == 404: return None
    if st == 401: raise PermissionError("401")
    return js

def create_vlan(base, key, vid, name):
    st, js, _ = _call("POST", base + "/api/v1/vlans", key, {"id": vid, "name": name})
    if st == 201: return js
    if st == 409: raise FileExistsError(js["error"])
    if st in (401, 403): raise PermissionError(js["error"])
    if st == 400: raise ValueError(js["error"])
    raise RuntimeError(st)

def replace_vlan(base, key, vid, name):
    st, js, _ = _call("PUT", f"{base}/api/v1/vlans/{vid}", key, {"name": name})
    if st == 200: return js
    if st == 404: raise LookupError(js["error"])
    if st in (401, 403): raise PermissionError(js["error"])
    raise RuntimeError(st)

def rename_vlan(base, key, vid, name):
    st, js, _ = _call("PATCH", f"{base}/api/v1/vlans/{vid}", key, {"name": name})
    if st == 200: return js
    if st == 404: raise LookupError(js["error"])
    if st in (401, 403): raise PermissionError(js["error"])
    raise RuntimeError(st)

def delete_vlan(base, key, vid):
    st, js, _ = _call("DELETE", f"{base}/api/v1/vlans/{vid}", key)
    if st == 204: return True
    if st == 404: return False
    if st in (401, 403): raise PermissionError(js["error"])
    raise RuntimeError(st)
