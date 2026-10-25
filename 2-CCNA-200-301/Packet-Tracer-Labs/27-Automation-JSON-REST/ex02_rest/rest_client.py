"""Aufgabe 2: REST-Client fuer die VLAN-Mock-API. Nur die Standardbibliothek (urllib), kein requests noetig."""
import json
import urllib.request, urllib.error

def _call(method, url, key, body=None):
    """Hilfsfunktion: sendet die Anfrage und gibt (status, json_oder_None, headers) zurueck.
    Bei HTTP-Fehlern ebenfalls (status, json, headers) zurueckgeben, nicht abstuerzen."""
    raise NotImplementedError

def list_vlans(base, key):
    """GET /api/v1/vlans -> Liste von Dicts {id, name}. 401 -> PermissionError."""
    raise NotImplementedError

def get_vlan(base, key, vid):
    """GET /api/v1/vlans/<id> -> Dict, bei 404 -> None."""
    raise NotImplementedError

def create_vlan(base, key, vid, name):
    """POST -> erzeugtes Dict. 409 -> FileExistsError, 403 -> PermissionError, 400 -> ValueError."""
    raise NotImplementedError

def replace_vlan(base, key, vid, name):
    """PUT -> Dict. 404 -> LookupError."""
    raise NotImplementedError

def rename_vlan(base, key, vid, name):
    """PATCH mit {"name": ...} -> Dict. 404 -> LookupError."""
    raise NotImplementedError

def delete_vlan(base, key, vid):
    """DELETE -> True bei 204, False bei 404, 403 -> PermissionError."""
    raise NotImplementedError
