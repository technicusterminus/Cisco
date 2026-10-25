import time
import requests

BASE_PATH = "/dna/intent/api/v1"


def get_token(base, user, password):
    r = requests.post(f"{base}/dna/system/api/v1/auth/token", auth=(user, password), timeout=10)
    if r.status_code == 401:
        raise PermissionError("Anmeldung fehlgeschlagen")
    r.raise_for_status()
    return r.json()["Token"]


def get_all_devices(base, token, limit=10):
    out, offset = [], 1
    while True:
        r = requests.get(f"{base}{BASE_PATH}/network-device", params={"offset": offset, "limit": limit},
                         headers={"X-Auth-Token": token}, timeout=10)
        r.raise_for_status()
        page = r.json()["response"]
        out.extend(page)
        if len(page) < limit:
            return out
        offset += len(page)


def get_device(base, token, dev_id):
    r = requests.get(f"{base}{BASE_PATH}/network-device/{dev_id}", headers={"X-Auth-Token": token}, timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()["response"]


def set_description(base, token, dev_id, text):
    r = requests.patch(f"{base}{BASE_PATH}/network-device/{dev_id}", json={"description": text},
                       headers={"X-Auth-Token": token}, timeout=10)
    errs = {403: PermissionError, 404: LookupError, 400: ValueError, 415: TypeError}
    if r.status_code in errs:
        raise errs[r.status_code](r.text)
    r.raise_for_status()
    return r.json()["response"]["taskId"]


def get_with_retry(url, retries=5):
    for _ in range(retries):
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (503, 429):
            time.sleep(float(r.headers.get("Retry-After", "0")))
            continue
        r.raise_for_status()
    raise RuntimeError("Zu viele Fehlversuche")
