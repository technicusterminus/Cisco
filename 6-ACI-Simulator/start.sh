#!/bin/sh
# ACI Simulator starten (Linux/macOS). Weitere Optionen: ./start.sh --help
cd "$(dirname "$0")" && exec python3 -m aci_sim "$@"
