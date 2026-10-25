"""Aufgabe 3: REST-Client gegen die Mock-API (Ziele 6.4 und 6.5). `pip install requests`.
Mock starten (eigenes Terminal): python3 ../mock_api/server.py 8080  -- oder einfach die Tests laufen lassen (sie starten den Mock selbst).
Tests: python3 -m unittest -v test_ex03   (im Ordner ex03_rest)"""
import time
import requests

BASE_PATH = "/dna/intent/api/v1"


def get_token(base, user, password):
    """POST {base}/dna/system/api/v1/auth/token mit HTTP Basic Auth. Rueckgabe: Token (str).
    Bei Statuscode 401 -> PermissionError("Anmeldung fehlgeschlagen")."""
    raise NotImplementedError


def get_all_devices(base, token, limit=10):
    """GET {base}/dna/intent/api/v1/network-device?offset=<1-basiert>&limit=<limit> bis alle Seiten gelesen sind
    (Header X-Auth-Token). Rueckgabe: Liste aller Geraete (dicts) aus dem Schluessel 'response'.
    Der Server liefert maximal 10 pro Seite: Pagination beachten!"""
    raise NotImplementedError


def get_device(base, token, dev_id):
    """GET .../network-device/<id>. Rueckgabe: dict des Geraets (Schluessel 'response'); bei 404 -> None."""
    raise NotImplementedError


def set_description(base, token, dev_id, text):
    """PATCH .../network-device/<id> mit JSON {"description": text} (Content-Type application/json).
    Erfolg: 202 -> Rueckgabe taskId (str) aus response.taskId.
    403 -> PermissionError, 404 -> LookupError, 400 -> ValueError, 415 -> TypeError."""
    raise NotImplementedError


def get_with_retry(url, retries=5):
    """GET auf url (ohne Token). Bei 503 oder 429 bis zu `retries` Versuche, dazwischen Retry-After (Sekunden) abwarten.
    Rueckgabe: das dekodierte JSON bei 200. Nach Ausschoepfen aller Versuche RuntimeError."""
    raise NotImplementedError
