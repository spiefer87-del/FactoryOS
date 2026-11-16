#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
selection_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then selection_python="$candidate"; break; fi
done
if [ -z "$selection_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$selection_python" -m compileall -q factoryos scripts
"$selection_python" scripts/upgrade_tool_mount.py --check
sudo systemctl restart factoryos.service
sudo systemctl is-active factoryos.service
echo "Auswahl aktualisiert. Keine Datenmigration oder automatische Musterungsänderung. Maschinenbedienung neu laden."
