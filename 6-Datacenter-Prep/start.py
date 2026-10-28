#!/usr/bin/env python3
"""Datacenter Prep starten.

    python3 start.py              (Windows: Doppelklick auf start.bat oder: py start.py)

Danach oeffnet sich der Browser mit der Startseite. Optionen: python3 start.py --help
"""
import os
import sys

if sys.version_info < (3, 8):
    print('Datacenter Prep braucht Python 3.8 oder neuer (gefunden: %s).' % sys.version.split()[0])
    print('Download: https://www.python.org/downloads/')
    if os.name == 'nt':
        input('Enter zum Schliessen ...')
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from dcprep.__main__ import main  # noqa: E402

if __name__ == '__main__':
    try:
        main()
    except SystemExit as ex:
        if ex.code not in (None, 0) and os.name == 'nt' and sys.stdin.isatty():
            print(ex.code)
            input('Enter zum Schliessen ...')
        raise
