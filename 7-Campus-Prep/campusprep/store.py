"""Persistenz: automatischer Zustand, benannte Staende und Lab-Fortschritt als JSON im Datenverzeichnis.

Atomar (Temp-Datei + Umbenennen), mit kind/version, deterministisch (sortierte Schluessel, keine Zeitstempel). Ein defekter
oder fremder Zustand wird beim Start nicht geladen; die Datei bleibt als *.bad liegen. Das Datenverzeichnis gehoert nicht
ins Repository (siehe .gitignore); es enthaelt die Uebungs-Schluessel der Labs.
"""
import json
import os
import re

KIND = 'campusprep-state'
VERSION = 6          # 2: Flex Profiles und Site Tags, 3: AAA-Objekte und RADIUS-Gegenseite, 4: Web-Auth (lokale Benutzer, Login-Listen, Parameter Maps), 5: Mobility (Gruppe, Peers), 6: RF-Profile und RF Tags
ACCEPTED = (1, 2, 3, 4, 5, 6) # Staende der Version 1 bleiben ladbar; fehlende Felder werden mit Standardwerten gefuellt
NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$')


class StoreError(Exception):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.status = status


def check_name(name):
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise StoreError('Name: 1-40 Zeichen (Buchstaben, Ziffern, . _ -), beginnt mit Buchstabe oder Ziffer')
    return name


def validate_state(d):
    """Pruefen, ob ein Zustand dieser Version vorliegt und die Pflichtfelder hat. Wirft StoreError."""
    if not isinstance(d, dict) or d.get('kind') != KIND:
        raise StoreError('Kein Campus-Prep-Stand')
    if d.get('version') not in ACCEPTED:
        raise StoreError('Stand hat Version %s, erwartet wird %s' % (d.get('version'), ' oder '.join(map(str, ACCEPTED))))
    w, c = d.get('world'), d.get('wlc')
    if not isinstance(w, dict) or not isinstance(w.get('wlc'), dict) or not isinstance(w.get('aps'), list) \
            or not isinstance(w.get('clients'), list) or not isinstance(c, dict):
        raise StoreError('Stand ist unvollstaendig')
    for a in w['aps']:
        if not isinstance(a, dict) or not {'name', 'ethMac', 'radioMac', 'ip', 'model', 'joined'} <= set(a):
            raise StoreError('Stand: AP-Eintrag unvollstaendig')
    for cl in w['clients']:
        if not isinstance(cl, dict) or not {'mac', 'ssid', 'ap', 'protocol'} <= set(cl):
            raise StoreError('Stand: Client-Eintrag unvollstaendig')
    for k, t in (('wlans', dict), ('policies', dict), ('policyTags', dict), ('apCfg', dict)):
        if not isinstance(c.get(k), t):
            raise StoreError('Stand: %s fehlt' % k)
    return d


class Store:
    def __init__(self, directory):
        self.dir = directory
        self.saves = os.path.join(directory, 'saves')
        os.makedirs(self.saves, exist_ok=True)
        self._last = {}

    # ------------------------------------------------------------------ Dateien
    def _write(self, path, obj):
        text = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + '\n'
        if self._last.get(path) == text:
            return
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(text)
        os.replace(tmp, path)
        self._last[path] = text

    def _read(self, path):
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)

    def _quarantine(self, path):
        try:
            os.replace(path, path + '.bad')
        except OSError:
            pass

    # ------------------------------------------------------------------ Zustand und Fortschritt
    def write_state(self, d):
        self._write(os.path.join(self.dir, 'state.json'), d)

    def read_state(self):
        """Gespeicherter Zustand oder None (fehlt oder defekt; defekte Dateien werden zu *.bad)."""
        path = os.path.join(self.dir, 'state.json')
        if not os.path.exists(path):
            return None
        try:
            return validate_state(self._read(path))
        except (ValueError, StoreError, OSError):
            self._quarantine(path)
            return None

    def write_progress(self, p):
        self._write(os.path.join(self.dir, 'progress.json'), {'kind': 'campusprep-progress', 'version': VERSION, 'labs': p})

    def read_progress(self):
        path = os.path.join(self.dir, 'progress.json')
        if not os.path.exists(path):
            return {}
        try:
            d = self._read(path)
            assert d.get('kind') == 'campusprep-progress' and d.get('version') in ACCEPTED and isinstance(d.get('labs'), dict)
            return d['labs']
        except (ValueError, AssertionError, OSError, AttributeError):
            self._quarantine(path)
            return {}

    # ------------------------------------------------------------------ benannte Staende
    def _save_path(self, name):
        return os.path.join(self.saves, check_name(name) + '.json')

    def save_named(self, name, d):
        self._write(self._save_path(name), d)

    def load_named(self, name):
        path = self._save_path(name)
        if not os.path.exists(path):
            raise StoreError('Stand %s gibt es nicht' % name, 404)
        try:
            return validate_state(self._read(path))
        except (ValueError, OSError):
            raise StoreError('Stand %s ist nicht lesbar' % name)

    def named_exists(self, name):
        return os.path.exists(self._save_path(name))

    def delete_named(self, name):
        path = self._save_path(name)
        if not os.path.exists(path):
            raise StoreError('Stand %s gibt es nicht' % name, 404)
        os.remove(path)
        self._last.pop(path, None)

    def list_named(self):
        out = []
        for f in sorted(os.listdir(self.saves)):
            if not f.endswith('.json'):
                continue
            name = f[:-5]
            try:
                d = validate_state(self._read(os.path.join(self.saves, f)))
                lab = (d.get('lab') or {}).get('id')
                out.append({'name': name, 'lab': lab, 'wlans': len(d['wlc']['wlans'])})
            except (ValueError, StoreError, OSError):
                out.append({'name': name, 'lab': None, 'wlans': 0, 'broken': True})
        return out
