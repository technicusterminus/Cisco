#!/bin/sh
# Tenant per REST-API anlegen (Lab 08). Aufruf: sh curl-tenant.sh [http://localhost:8080]
APIC=${1:-http://localhost:8080}
COOKIE=$(mktemp)

echo "== Login"
curl -s -c "$COOKIE" -X POST "$APIC/api/aaaLogin.json" \
  -d '{"aaaUser":{"attributes":{"name":"admin","pwd":"admin"}}}' | head -c 120; echo

echo "== Tenant Automation mit VRF, BD, AP und EPG in einem POST"
curl -s -b "$COOKIE" -X POST "$APIC/api/mo/uni.json" -d '{
  "fvTenant": {"attributes": {"name": "Automation"}, "children": [
    {"fvCtx": {"attributes": {"name": "v1"}}},
    {"fvBD": {"attributes": {"name": "bd1"}, "children": [
      {"fvRsCtx": {"attributes": {"tnFvCtxName": "v1"}}},
      {"fvSubnet": {"attributes": {"ip": "192.168.1.1/24"}}}]}},
    {"fvAp": {"attributes": {"name": "app"}, "children": [
      {"fvAEPg": {"attributes": {"name": "epg1"}, "children": [
        {"fvRsBd": {"attributes": {"tnFvBDName": "bd1"}}}]}}]}}]}}'; echo

echo "== Alle BDs mit Unicast Routing"
curl -s -b "$COOKIE" -G "$APIC/api/class/fvBD.json" \
  --data-urlencode 'query-target-filter=eq(fvBD.unicastRoute,"yes")' \
  --data-urlencode 'rsp-prop-include=naming-only'; echo

echo "== Fehler provozieren: ungueltiger Wert"
curl -s -b "$COOKIE" -X POST "$APIC/api/mo/uni/tn-Automation.json" \
  -d '{"fvBD":{"attributes":{"name":"bd2","arpFlood":"vielleicht"}}}'; echo

rm -f "$COOKIE"
