#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
warehouse_ui_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
 if [ -x "$candidate" ]; then warehouse_ui_python="$candidate"; break; fi
done
if [ -z "$warehouse_ui_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$warehouse_ui_python" -m compileall -q factoryos/modules/inventory
"$warehouse_ui_python" scripts/upgrade_inventory.py --check
sudo systemctl restart factoryos.service
sudo systemctl is-active factoryos.service
echo "Lager vollständig neu laden. Keine Lagerbuchung und keine Datenbankmigration durchgeführt."
