#!/usr/bin/env python3
"""RESTCONF GET auf CSR1 (IOS XE). Aufruf: python3 restconf_get.py <ip> <user> <pass>"""
import sys, json, requests, urllib3
urllib3.disable_warnings()  # nur Lab: selbstsigniertes Zertifikat
host, user, pw = sys.argv[1:4]
url = f"https://{host}/restconf/data/ietf-interfaces:interfaces"
h = {"Accept": "application/yang-data+json"}
r = requests.get(url, headers=h, auth=(user, pw), verify=False, timeout=10)
r.raise_for_status()
for i in r.json()["ietf-interfaces:interfaces"]["interface"]:
    print(i["name"], i.get("description", ""), i.get("enabled"))
# TODO Aufgabe 4: PATCH auf .../interface=GigabitEthernet2 mit Content-Type application/yang-data+json
