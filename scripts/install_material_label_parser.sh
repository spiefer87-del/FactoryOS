#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
material_label_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then material_label_python="$candidate"; break; fi
done
if [ -z "$material_label_python" ]; then
    echo "Python-Umgebung fehlt. Bitte Dienstkonfiguration prüfen:"
    sudo systemctl cat factoryos
    exit 1
fi
"$material_label_python" -m compileall -q factoryos scripts
"$material_label_python" scripts/check_material_scan.py
# No package, database, systemd, DuckDNS or Tailscale configuration changes.
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
