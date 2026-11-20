#!/usr/bin/env python3
"""Catalyst-Center-Antworten aus DEINEM Lab aufnehmen, damit der Simulator belegte Formate nachbauen kann.

Nur lesend: ein POST fuer das Token (wie die Oberflaeche), danach ausschliesslich GET auf eine feste Liste von Pfaden.
Nichts wird geaendert, nichts provisioniert. Das Skript laeuft nur, wenn du es selbst startest; der Simulator und diese
Sitzung verbinden sich nie mit einem echten Catalyst Center.

Zugangsdaten stehen nur in Umgebungsvariablen (nie im Repository, nie auf der Kommandozeile):

    export CATC_URL=https://catc.example.lab      # Basisadresse, mit https://
    export CATC_USER=...                          # Benutzer
    export CATC_PASS=...                          # Passwort
    python3 tools/catc_capture.py --out catc-beispiele --anonymize

Die Ausgabe sind JSON-Dateien je Pfad plus index.json (Status je Pfad). Das Token wird nie gespeichert. Mit --anonymize
werden IP-Adressen, MAC-Adressen, Seriennummern, UUIDs, Hostnamen und Benutzernamen durch stabile Platzhalter ersetzt
(gleicher Wert, gleicher Platzhalter), die Struktur bleibt. Pruefe die Dateien trotzdem, bevor du sie weitergibst.

Zertifikate werden geprueft. Hat dein Lab ein selbst signiertes Zertifikat, gib mit --cafile die Zertifikatsdatei an;
die Pruefung auszuschalten ist absichtlich nicht vorgesehen.
"""
import argparse
import base64
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

# Feste Liste, nur GET. Nicht jede Version kennt jeden Pfad: 404 und 403 werden im Index vermerkt und sind kein Fehler.
PATHS = [
    '/dna/intent/api/v1/network-device',
    '/dna/intent/api/v1/network-device/count',
    '/dna/intent/api/v1/site',
    '/dna/intent/api/v1/site/count',
    '/dna/intent/api/v1/site-health',
    '/dna/intent/api/v1/network-health',
    '/dna/intent/api/v1/client-health',
    '/dna/intent/api/v1/device-health',
    '/dna/intent/api/v1/interface',
    '/dna/intent/api/v1/wireless/profile',
    '/dna/intent/api/v1/template-programmer/template',
    '/dna/intent/api/v1/task',
    '/dna/intent/api/v1/dnacaap/management/execution-status',
    '/dna/system/api/v1/health',
]

IPV4 = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
MAC = re.compile(r'\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b|\b(?:[0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}\b')
UUID = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
SERIAL_KEYS = {'serialnumber', 'serial', 'apserialnumber'}
NAME_KEYS = {'hostname', 'name', 'devicename', 'username', 'user', 'managementipaddress', 'lastupdatedby', 'createdby'}
SECRET_KEYS = {'password', 'token', 'x-auth-token', 'secret', 'key', 'authorization', 'snmpauthpassphrase', 'snmpprivpassphrase', 'cliPassword'.lower(),
               'enablePassword'.lower(), 'snmpv2cread'.lower(), 'snmpv2cwrite'.lower()}


class Anonymizer:
    """Ersetzt Werte durch stabile Platzhalter: gleicher Wert, gleicher Platzhalter, damit Verweise erhalten bleiben."""

    def __init__(self):
        self.seen = {}

    def _alias(self, kind, value):
        key = (kind, value)
        if key not in self.seen:
            self.seen[key] = '%s-%d' % (kind, 1 + sum(1 for k in self.seen if k[0] == kind))
        return self.seen[key]

    def text(self, s):
        s = UUID.sub(lambda m: self._alias('uuid', m.group(0).lower()), s)
        s = MAC.sub(lambda m: self._alias('mac', m.group(0).lower()), s)
        return IPV4.sub(lambda m: m.group(0) if m.group(0).startswith(('0.', '255.')) else self._alias('ip', m.group(0)), s)

    def value(self, obj, key=''):
        k = key.lower()
        if isinstance(obj, dict):
            return {kk: self.value(v, kk) for kk, v in obj.items()}
        if isinstance(obj, list):
            return [self.value(v, key) for v in obj]
        if isinstance(obj, str):
            if k in SECRET_KEYS:
                return '<geschwaerzt>'
            if k in SERIAL_KEYS and obj:
                return self._alias('serial', obj)
            if k in NAME_KEYS and obj and not IPV4.fullmatch(obj):
                return self._alias('name', obj)
            return self.text(obj)
        return obj


def get_token(base, user, password, ctx):
    req = urllib.request.Request(base + '/dna/system/api/v1/auth/token', method='POST', data=b'')
    req.add_header('Authorization', 'Basic ' + base64.b64encode(('%s:%s' % (user, password)).encode()).decode())
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        return json.loads(r.read())['Token']


def fetch(base, path, token, ctx):
    req = urllib.request.Request(base + path, method='GET')
    req.add_header('X-Auth-Token', token)
    req.add_header('Accept', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def with_limit(path, limit):
    """Haengt limit an Listenpfade an (nicht an Zaehler und nicht, wenn schon ein limit steht)."""
    if not limit or path.endswith('/count') or 'limit=' in path:
        return path
    return path + ('&' if '?' in path else '?') + 'limit=%d' % limit


def file_name(path):
    return re.sub(r'[^A-Za-z0-9]+', '_', path.strip('/')) + '.json'


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', default='catc-beispiele', help='Zielverzeichnis (wird angelegt)')
    ap.add_argument('--anonymize', action='store_true', help='IP, MAC, Seriennummern, UUIDs, Namen und Geheimnisse ersetzen')
    ap.add_argument('--cafile', help='Zertifikatsdatei (PEM) fuer ein selbst signiertes Lab-Zertifikat')
    ap.add_argument('--path', action='append', default=[], help='zusaetzlicher GET-Pfad (mehrfach moeglich), z. B. /dna/intent/api/v1/site')
    ap.add_argument('--limit', type=int, default=5, help='Eintraege je Liste (Parameter limit), Standard 5; 0 = ohne')
    a = ap.parse_args(argv)
    base, user, password = os.environ.get('CATC_URL', ''), os.environ.get('CATC_USER', ''), os.environ.get('CATC_PASS', '')
    if not (base.startswith('https://') and user and password):
        sys.exit('CATC_URL (mit https://), CATC_USER und CATC_PASS muessen gesetzt sein.')
    base = base.rstrip('/')
    for p in a.path:
        if not p.startswith('/dna/'):
            sys.exit('Pfade muessen mit /dna/ beginnen: %s' % p)
    ctx = ssl.create_default_context(cafile=a.cafile)
    token = get_token(base, user, password, ctx)
    os.makedirs(a.out, exist_ok=True)
    anon = Anonymizer() if a.anonymize else None
    index = []
    for path in PATHS + a.path:
        full = with_limit(path, a.limit)
        status, body = fetch(base, full, token, ctx)
        try:
            data = json.loads(body) if body else None
        except ValueError:
            data = {'nicht-json': body[:200].decode('utf-8', 'replace')}
        if anon:
            data = anon.value(data)
        with open(os.path.join(a.out, file_name(path)), 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write('\n')
        index.append({'path': path, 'status': status, 'file': file_name(path)})
        print('%s %s' % (status, path))
    with open(os.path.join(a.out, 'index.json'), 'w', encoding='utf-8') as fh:
        json.dump({'anonymized': bool(a.anonymize), 'paths': index}, fh, indent=1)
        fh.write('\n')
    print('Fertig: %s (Token nicht gespeichert). Dateien vor dem Weitergeben pruefen.' % a.out)


if __name__ == '__main__':
    run()
