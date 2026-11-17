#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
warehouse_intake_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
 if [ -x "$candidate" ]; then warehouse_intake_python="$candidate"; break; fi
done
if [ -z "$warehouse_intake_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$warehouse_intake_python" -m compileall -q factoryos/modules/inventory
"$warehouse_intake_python" scripts/upgrade_inventory.py --check
sudo systemctl restart factoryos.service
sudo systemctl is-active factoryos.service
echo "Wareneingang vollständig neu laden. Keine Migration und keine Bestandsänderung durch Installation."
