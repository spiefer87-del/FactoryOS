#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
planning_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then planning_python="$candidate"; break; fi
done
if [ -z "$planning_python" ]; then
    echo "Python-Umgebung fehlt. Bitte Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$planning_python" -m compileall -q factoryos scripts
"$planning_python" scripts/upgrade_order_planning.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
mkdir -p /home/factoryos/backups
planning_backup=$(mktemp -d /home/factoryos/backups/order_planning_XXXXXXXX)
cp -a instance/factoryos.db "$planning_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$planning_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $planning_backup"
if ! "$planning_python" scripts/upgrade_order_planning.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt. Bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
