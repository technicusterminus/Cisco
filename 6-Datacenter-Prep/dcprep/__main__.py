"""Start von Datacenter Prep. Normalerweise ueber start.py (bzw. start.bat unter Windows)."""
import argparse
import errno
import getpass
import os
import threading
import webbrowser

from .server import serve, BASE

DEFAULT_PORT = 8080


def parser():
    ap = argparse.ArgumentParser(prog='start.py', description='Datacenter Prep - ACI-Trainingsumgebung im Browser')
    ap.add_argument('--port', type=int, default=None, help='Port (Standard 8080, mit --https 8443; ist er belegt, wird der naechste freie genommen)')
    ap.add_argument('--host', default='127.0.0.1',
                    help='Listen-Adresse (Standard 127.0.0.1 = nur dieser Rechner; 0.0.0.0 = aus dem Netz erreichbar, z. B. Schulungsraum)')
    ap.add_argument('--no-browser', action='store_true', help='Browser nicht automatisch oeffnen')
    ap.add_argument('--https', action='store_true', help='HTTPS mit selbstsigniertem Zertifikat (braucht openssl)')
    ap.add_argument('--data', default=os.path.join(BASE, 'data'), help='Datenverzeichnis (Benutzer, Uebungswelten, Speicherstaende)')
    ap.add_argument('--password', default=os.environ.get('DCPREP_PASSWORD', 'admin'),
                    help='APIC-Passwort fuer admin in neuen Uebungswelten (Standard: admin)')
    ap.add_argument('--discovery', type=float, default=20, help='Sekunden pro Discovery-Schritt in neuen Welten (Standard 20)')
    ap.add_argument('--strict', action='store_true', help='Unbekannte Attribute ablehnen wie ein APIC (Standard: annehmen, fuer Ansible/Terraform)')
    ap.add_argument('--users', action='store_true', help='Benutzer auflisten und beenden')
    ap.add_argument('--set-password', metavar='BENUTZER', help='Passwort eines Benutzers neu setzen (z. B. vergessenes Verwalter-Passwort) und beenden')
    return ap


def admin_tasks(a):
    from .users import Hub, _hash
    import secrets
    hub = Hub(a.data, a.password, a.discovery)
    if a.users:
        for u in hub.listing():
            print('%-24s %-10s %s  %d Labs bestanden' % (u['name'], u['role'], 'Passwort' if u['password'] else 'ohne Passwort', u['labsDone']))
        return
    n = hub.find(a.set_password)
    if not n:
        raise SystemExit('Benutzer %s gibt es nicht. Vorhanden: %s' % (a.set_password, ', '.join(hub.data['users'])))
    p1 = getpass.getpass('Neues Passwort fuer %s (leer = ohne Passwort): ' % n)
    if p1 and getpass.getpass('Wiederholen: ') != p1:
        raise SystemExit('Die Passwoerter stimmen nicht ueberein.')
    u = hub.data['users'][n]
    u['salt'] = secrets.token_hex(16)
    u['hash'] = _hash(p1, u['salt']) if p1 else ''
    hub._save()
    print('Passwort von %s %s.' % (n, 'gesetzt' if p1 else 'entfernt'))


def main(argv=None, open_browser=True):
    a = parser().parse_args(argv)
    if a.users or a.set_password:
        return admin_tasks(a)
    if a.strict:
        from . import model
        model.STRICT = True
    want = a.port or (8443 if a.https else DEFAULT_PORT)
    hub = httpd = None
    for port in ([want] if a.port else range(want, want + 20)):
        try:
            hub, httpd = serve(a.host, port, a.data, a.password, a.https, a.discovery)
            break
        except FileNotFoundError:
            raise SystemExit('Fuer --https wird openssl benoetigt. Ohne --https laeuft Datacenter Prep per HTTP.')
        except OSError as ex:
            if ex.errno not in (errno.EADDRINUSE, getattr(errno, 'WSAEADDRINUSE', -1), 10048) or a.port:
                raise SystemExit('Port %d ist nicht verfuegbar: %s' % (port, ex))
    if not httpd:
        raise SystemExit('Kein freier Port zwischen %d und %d gefunden. Mit --port einen anderen waehlen.' % (want, want + 19))
    url = '%s://%s:%d/' % ('https' if a.https else 'http', 'localhost' if a.host in ('0.0.0.0', '127.0.0.1') else a.host, port)
    users = ', '.join(hub.data['users'])
    print('')
    print('  Datacenter Prep laeuft')
    print('  -----------------------------------------------------------')
    print('  Im Browser oeffnen:  %s' % url)
    if port != want:
        print('  (Port %d war belegt, deshalb Port %d)' % (want, port))
    print('  Benutzer:            %s  (auf der Startseite waehlen oder neu anlegen)' % users)
    print('  APIC-Login danach:   admin / %s' % ('admin' if a.password == 'admin' else '(--password)'))
    if a.host == '0.0.0.0':
        print('  Aus dem Netz:        %s://<IP dieses Rechners>:%d/  - Benutzern ein Passwort geben!' % ('https' if a.https else 'http', port))
    print('  Daten:               %s' % a.data)
    print('  Beenden:             Strg+C')
    print('')
    if open_browser and not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nBeendet - alle Uebungswelten sind gespeichert.')
        hub.save_all()


if __name__ == '__main__':
    main(open_browser=False)
