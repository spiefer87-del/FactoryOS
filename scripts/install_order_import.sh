#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
erp_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then erp_python="$candidate"; break; fi
done
if [ -z "$erp_python" ]; then
    echo "Python-Umgebung fehlt. Bitte diese Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$erp_python" -m compileall -q factoryos scripts
"$erp_python" scripts/upgrade_order_import.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
erp_backup="/home/factoryos/backups/erp_order_import_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$erp_backup"
cp -a instance/factoryos.db "$erp_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$erp_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $erp_backup"
if ! "$erp_python" scripts/upgrade_order_import.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt. Bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
