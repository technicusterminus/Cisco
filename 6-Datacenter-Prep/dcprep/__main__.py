"""Start: python3 -m dcprep [--port 8443 --https] [--password admin]"""
import argparse
import os

from .server import serve, BASE


def main():
    ap = argparse.ArgumentParser(prog='dcprep', description='Datacenter Prep - ACI-Trainingsumgebung')
    ap.add_argument('--host', default='127.0.0.1',
                    help='Listen-Adresse (Standard 127.0.0.1; 0.0.0.0 = aus dem Netz erreichbar, z. B. in einer VM)')
    ap.add_argument('--port', type=int, default=None, help='Port (Standard 8080, mit --https 8443)')
    ap.add_argument('--https', action='store_true', help='HTTPS mit selbstsigniertem Zertifikat (braucht openssl)')
    ap.add_argument('--data', default=os.path.join(BASE, 'data'), help='Datenverzeichnis fuer Zustand und Snapshots')
    ap.add_argument('--password', default=os.environ.get('DCPREP_PASSWORD', 'admin'),
                    help='Passwort fuer admin bei einer frischen Installation (Standard: admin)')
    ap.add_argument('--discovery', type=float, default=20, help='Sekunden pro Discovery-Schritt (Standard 20)')
    ap.add_argument('--strict', action='store_true',
                    help='Unbekannte Attribute ablehnen (Standard: annehmen, fuer Ansible/Terraform)')
    a = ap.parse_args()
    if a.strict:
        from . import model
        model.STRICT = True
    port = a.port or (8443 if a.https else 8080)
    try:
        S, httpd = serve(a.host, port, a.data, a.password, a.https, a.discovery)
    except FileNotFoundError:
        raise SystemExit('Fuer --https wird openssl benoetigt. Ohne --https laeuft der Simulator per HTTP.')
    except OSError as ex:
        raise SystemExit('Port %d ist nicht verfuegbar: %s' % (port, ex))
    url = '%s://%s:%d/' % ('https' if a.https else 'http', 'localhost' if a.host == '0.0.0.0' else a.host, port)
    print('Datacenter Prep laeuft: %s  (Login: admin)' % url)
    print('REST-API wie beim APIC: %sapi/aaaLogin.json, %sapi/mo/uni.json' % (url, url))
    print('Daten: %s  - Beenden mit Strg+C' % a.data)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nBeendet.')
        with S.lock:
            S.save()


if __name__ == '__main__':
    main()
