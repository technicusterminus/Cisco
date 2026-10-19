#!/usr/bin/env python3
"""NETCONF get-config per ncclient. pip install ncclient. Aufruf: python3 netconf_get.py <ip> <user> <pass>"""
import sys
from ncclient import manager
host, user, pw = sys.argv[1:4]
flt = """<filter><interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/></filter>"""
with manager.connect(host=host, port=830, username=user, password=pw, hostkey_verify=False) as m:
    print(m.get_config(source="running", filter=flt).xml)
