"""Benutzerverwaltung von Datacenter Prep.

Jeder Benutzer hat eine eigene, vollstaendig getrennte Uebungswelt: eigene
Fabric-Konfiguration, eigene Labs, Speicherstaende, Snapshots und eigenen
Fortschritt (Verzeichnis data/users/<name>/). Das ist unabhaengig von den
simulierten APIC-Benutzern (admin, TACACS+ usw.), mit denen man sich danach
am APIC anmeldet.

Rollen: Der erste Benutzer ist Verwalter. Ein Verwalter darf andere Benutzer
anlegen, loeschen, zuruecksetzen und ihr Passwort neu setzen. Jeder Benutzer
darf sein eigenes Passwort aendern, seine Welt zuruecksetzen und sich loeschen.
"""
import hashlib
import json
import os
import re
import secrets
import shutil
import threading
import time

from .model import AciError

NAME_RE = re.compile(r'^[\w .-]{1,32}$', re.UNICODE)
SESSION_DAYS = 30
COOKIE = 'DCP-session'


def _hash(pwd, salt):
    return hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), bytes.fromhex(salt), 120000).hex()


class Hub:
    """Alle Benutzer und ihre Simulationen (eine Sim pro Benutzer, erst bei Bedarf geladen)."""

    def __init__(self, data_dir, admin_pwd='admin', discovery=20):
        self.root = data_dir
        self.admin_pwd = admin_pwd
        self.discovery = discovery
        self.lock = threading.RLock()
        self.udir = os.path.join(data_dir, 'users')
        os.makedirs(self.udir, exist_ok=True)
        self.file = os.path.join(data_dir, 'users.json')
        self.sims = {}
        self.data = {'users': {}, 'sessions': {}, 'last': None}
        if os.path.exists(self.file):
            with open(self.file, encoding='utf-8') as f:
                self.data = json.load(f)
            self.data.setdefault('sessions', {})
        if not self.data['users']:
            self._first_start()

    # ------------------------------------------------------------ Persistenz
    def _save(self):
        tmp = self.file + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=1)
        os.replace(tmp, self.file)

    def _first_start(self):
        """Erster Start: Benutzer 'standard' anlegen und eine Welt aus einer aelteren Version uebernehmen."""
        self.data['users']['standard'] = self._record('standard', '', 'verwalter')
        d = self.dir_of('standard')
        os.makedirs(d, exist_ok=True)
        for item in ('state.json', 'saves', 'snapshots'):
            src = os.path.join(self.root, item)
            if os.path.exists(src) and not os.path.exists(os.path.join(d, item)):
                shutil.move(src, os.path.join(d, item))
        self.data['last'] = 'standard'
        self._save()

    def _record(self, name, pwd, role):
        salt = secrets.token_hex(16)
        return {'name': name, 'role': role, 'salt': salt, 'hash': _hash(pwd, salt) if pwd else '',
                'created': time.strftime('%Y-%m-%dT%H:%M:%S'), 'lastSeen': None, 'dir': self._slug(name)}

    def _slug(self, name):
        base = re.sub(r'[^a-z0-9_.-]', '_', name.lower()).strip('.') or 'user'
        used = {u['dir'] for u in self.data['users'].values()}
        slug, n = base, 2
        while slug in used:
            slug, n = '%s-%d' % (base, n), n + 1
        return slug

    def dir_of(self, name):
        return os.path.join(self.udir, self.data['users'][name]['dir'])

    # ------------------------------------------------------------ Abfragen
    def find(self, name):
        name = (name or '').strip()
        for n in self.data['users']:
            if n.lower() == name.lower():
                return n
        return None

    def is_admin(self, name):
        u = self.data['users'].get(name)
        return bool(u) and u['role'] == 'verwalter'

    def listing(self):
        out = []
        for n, u in sorted(self.data['users'].items(), key=lambda x: x[0].lower()):
            prog = self._progress(n)
            out.append({'name': n, 'role': u['role'], 'password': bool(u['hash']), 'created': u['created'], 'lastSeen': u['lastSeen'],
                        'labsDone': sum(1 for p in prog.values() if p.get('done')), 'labsStarted': len(prog),
                        'lab': self._current_lab(n)})
        return out

    def _progress(self, name):
        fp = os.path.join(self.dir_of(name), 'progress.json')
        try:
            with open(fp, encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _current_lab(self, name):
        s = self.sims.get(name)
        if s:
            return s.sim.get('lab')
        fp = os.path.join(self.dir_of(name), 'state.json')
        try:
            with open(fp, encoding='utf-8') as f:
                return json.load(f)['sim'].get('lab')
        except (OSError, ValueError, KeyError):
            return None

    # ------------------------------------------------------------ Simulationen
    def sim(self, name):
        from .server import Sim
        with self.lock:
            if name not in self.data['users']:
                raise AciError('DCP-NOUSER', 'Benutzer %s gibt es nicht' % name, 401)
            if name not in self.sims:
                self.sims[name] = Sim(self.dir_of(name), self.admin_pwd, self.discovery)
            return self.sims[name]

    def save_all(self):
        for s in list(self.sims.values()):
            with s.lock:
                s.save()

    def user_of_apic_token(self, tok):
        for n, s in list(self.sims.items()):
            if tok in s.tokens:
                return n
        return None

    # ------------------------------------------------------------ Sitzungen
    def login(self, name, pwd):
        with self.lock:
            n = self.find(name)
            if not n:
                raise AciError(401, 'Unbekannter Benutzer', 401)
            u = self.data['users'][n]
            if u['hash'] and _hash(pwd or '', u['salt']) != u['hash']:
                raise AciError(401, 'Passwort falsch', 401)
            tok = secrets.token_urlsafe(24)
            now = time.time()
            self.data['sessions'] = {k: v for k, v in self.data['sessions'].items() if v[1] > now}
            self.data['sessions'][tok] = [n, now + SESSION_DAYS * 86400]
            u['lastSeen'] = time.strftime('%Y-%m-%dT%H:%M:%S')
            self.data['last'] = n
            self._save()
            return tok, n

    def logout(self, tok):
        with self.lock:
            if self.data['sessions'].pop(tok, None):
                self._save()

    def session_user(self, tok):
        v = self.data['sessions'].get(tok or '')
        if v and v[1] > time.time() and v[0] in self.data['users']:
            return v[0]
        return None

    def check_password(self, name, pwd):
        u = self.data['users'].get(name)
        return bool(u) and (not u['hash'] or _hash(pwd or '', u['salt']) == u['hash'])

    def resolve(self, cookies, headers, remote_ip):
        """Welcher Benutzer stellt diese Anfrage? Reihenfolge: Sitzungs-Cookie, Header, APIC-Token,
        zuletzt aktiver Benutzer (nur lokal oder wenn er kein Passwort hat)."""
        n = self.session_user(cookies.get(COOKIE))
        if n:
            return n
        h = headers.get('X-DCPrep-User')
        if h:
            n = self.find(h)
            if not n or not self.check_password(n, headers.get('X-DCPrep-Password', '')):
                raise AciError(401, 'X-DCPrep-User: Benutzer unbekannt oder Passwort (X-DCPrep-Password) falsch', 401)
            return n
        tok = cookies.get('APIC-cookie') or headers.get('APIC-challenge')
        if tok:
            n = self.user_of_apic_token(tok)
            if n:
                return n
        last = self.data.get('last')
        if last in self.data['users'] and (remote_ip in ('127.0.0.1', '::1') or not self.data['users'][last]['hash']):
            return last
        if len(self.data['users']) == 1:
            only = next(iter(self.data['users']))
            if not self.data['users'][only]['hash']:
                return only
        raise AciError('DCP-NOUSER', 'Kein Datacenter-Prep-Benutzer angemeldet', 401)

    # ------------------------------------------------------------ Verwaltung
    def op(self, actor, b):
        """Aktionen der Benutzerverwaltung. actor = angemeldeter Benutzer oder None (Startseite)."""
        op = b.get('op')
        with self.lock:
            if op == 'create':
                if actor is None and not self.data.get('openSignup', True):
                    raise AciError(403, 'Neue Benutzer legt nur ein Verwalter an', 403)
                name = (b.get('name') or '').strip()
                if not NAME_RE.match(name):
                    raise AciError(400, 'Name: 1-32 Zeichen (Buchstaben, Ziffern, Leerzeichen, . _ -)')
                if self.find(name):
                    raise AciError(400, 'Benutzer %s gibt es schon' % name)
                role = b.get('role') if actor and self.is_admin(actor) and b.get('role') in ('verwalter', 'benutzer') else 'benutzer'
                self.data['users'][name] = self._record(name, b.get('password') or '', role)
                os.makedirs(self.dir_of(name), exist_ok=True)
                self._save()
                return {'ok': True, 'name': name}
            target = self.find(b.get('name')) if b.get('name') else actor
            if b.get('name') and not target:
                raise AciError(404, 'Benutzer %s gibt es nicht' % b.get('name'), 404)
            if not actor:
                raise AciError(401, 'Bitte zuerst anmelden', 401)
            if target != actor and not self.is_admin(actor):
                raise AciError(403, 'Das darf nur ein Verwalter', 403)
            u = self.data['users'][target]
            if op == 'password':
                if target == actor and u['hash'] and not self.check_password(target, b.get('old', '')):
                    raise AciError(403, 'Bisheriges Passwort falsch', 403)
                u['salt'] = secrets.token_hex(16)
                u['hash'] = _hash(b['password'], u['salt']) if b.get('password') else ''
                self._save()
                return {'ok': True}
            if op == 'role':
                if not self.is_admin(actor):
                    raise AciError(403, 'Das darf nur ein Verwalter', 403)
                if b.get('role') not in ('verwalter', 'benutzer'):
                    raise AciError(400, 'Rolle verwalter oder benutzer')
                if u['role'] == 'verwalter' and b['role'] != 'verwalter' and self._admins() == 1:
                    raise AciError(400, 'Es muss mindestens einen Verwalter geben')
                u['role'] = b['role']
                self._save()
                return {'ok': True}
            if op == 'reset':
                self._wipe(target)
                return {'ok': True}
            if op == 'delete':
                if u['role'] == 'verwalter' and self._admins() == 1 and len(self.data['users']) > 1:
                    raise AciError(400, 'Der letzte Verwalter kann sich nicht loeschen, solange es andere Benutzer gibt')
                self._wipe(target, remove=True)
                del self.data['users'][target]
                self.data['sessions'] = {k: v for k, v in self.data['sessions'].items() if v[0] != target}
                if self.data.get('last') == target:
                    self.data['last'] = None
                if not self.data['users']:
                    self._first_start()
                self._save()
                return {'ok': True}
            if op == 'signup':
                if not self.is_admin(actor):
                    raise AciError(403, 'Das darf nur ein Verwalter', 403)
                self.data['openSignup'] = bool(b.get('open'))
                self._save()
                return {'ok': True}
        raise AciError(400, 'Unbekannte Aktion')

    def _admins(self):
        return sum(1 for u in self.data['users'].values() if u['role'] == 'verwalter')

    def _wipe(self, name, remove=False):
        """Welt eines Benutzers loeschen: Zustand, Speicherstaende, Snapshots, Fortschritt."""
        s = self.sims.pop(name, None)
        if s:
            with s.lock:
                s.tokens.clear()
        d = self.dir_of(name)
        if os.path.isdir(d):
            shutil.rmtree(d)
        if not remove:
            os.makedirs(d, exist_ok=True)


class SimProxy:
    """Steht im Request-Handler fuer 'die Sim des anfragenden Benutzers' (pro Thread gebunden)."""

    def __init__(self):
        object.__setattr__(self, '_tl', threading.local())

    def bind(self, sim):
        self._tl.sim = sim

    def __getattr__(self, k):
        s = self._tl.__dict__.get('sim')
        if s is None:
            raise AciError('DCP-NOUSER', 'Kein Datacenter-Prep-Benutzer angemeldet', 401)
        return getattr(s, k)

    def __setattr__(self, k, v):
        setattr(self._tl.sim, k, v)
