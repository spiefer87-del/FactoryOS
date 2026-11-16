#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
setup_fix_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then setup_fix_python="$candidate"; break; fi
done
if [ -z "$setup_fix_python" ]; then echo "Python-Umgebung fehlt. Dienstkonfiguration prüfen: sudo systemctl cat factoryos"; exit 1; fi
"$setup_fix_python" -m compileall -q factoryos scripts
# Checks the existing report tables only; no schema or data migration.
"$setup_fix_python" scripts/upgrade_setup_reports.py --check
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
