#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
statistics_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then statistics_python="$candidate"; break; fi
done
if [ -z "$statistics_python" ]; then
    echo "Python-Umgebung fehlt. Bitte diese Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$statistics_python" -m compileall -q factoryos scripts
"$statistics_python" scripts/upgrade_order_statistics.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
statistics_backup="/home/factoryos/backups/order_statistics_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$statistics_backup"
cp -a instance/factoryos.db "$statistics_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$statistics_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $statistics_backup"
if ! "$statistics_python" scripts/upgrade_order_statistics.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt. Bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
