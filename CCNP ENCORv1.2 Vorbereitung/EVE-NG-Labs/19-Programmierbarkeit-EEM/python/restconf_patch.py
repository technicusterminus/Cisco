#!/usr/bin/env python3
"""Aufgabe 5/6: Description von GigabitEthernet2 per RESTCONF-PATCH setzen.
Aufruf: python3 restconf_patch.py <ip> <user> <pass> "Text"
TODO: Body, Content-Type und URL (…/interface=GigabitEthernet2) ergänzen; Statuscode auswerten (204 = ok)."""
import sys, requests, urllib3
urllib3.disable_warnings()
host, user, pw, text = sys.argv[1:5]
url = f"https://{host}/restconf/data/ietf-interfaces:interfaces/interface=GigabitEthernet2"
headers = {"Content-Type": "application/yang-data+json", "Accept": "application/yang-data+json"}
body = {"ietf-interfaces:interface": {"name": "GigabitEthernet2", "description": text}}
r = requests.patch(url, json=body, headers=headers, auth=(user, pw), verify=False, timeout=10)
print("HTTP", r.status_code)
