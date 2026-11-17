#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
inventory_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
 if [ -x "$candidate" ]; then inventory_python="$candidate"; break; fi
done
if [ -z "$inventory_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$inventory_python" -m compileall -q factoryos
"$inventory_python" scripts/upgrade_inventory.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
inventory_backup="/home/factoryos/backups/inventory_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$inventory_backup"
cp -a instance/factoryos.db "$inventory_backup/factoryos.db"
for suffix in -wal -shm; do
 if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$inventory_backup/factoryos.db$suffix"; fi
done
echo "Sicherung: $inventory_backup"
if ! "$inventory_python" scripts/upgrade_inventory.py; then echo "Upgrade fehlgeschlagen. Dienst bleibt zur Prüfung gestoppt. Fehlerausgabe weitergeben."; exit 1; fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Lager neu laden. Fachrollen im Adminbereich bewusst berechtigen. Zuerst Lagerplätze anlegen."
