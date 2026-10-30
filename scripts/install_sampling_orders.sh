#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
sampling_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then
        sampling_python="$candidate"
        break
    fi
done
if [ -z "$sampling_python" ]; then
    echo "Python-Umgebung nicht gefunden. Bitte diese Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$sampling_python" -m compileall -q factoryos scripts
"$sampling_python" scripts/upgrade_sampling_orders.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
backup_dir="/home/factoryos/backups/sampling_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$backup_dir"
cp -a instance/factoryos.db "$backup_dir/factoryos.db"
for sidecar in instance/factoryos.db-wal instance/factoryos.db-shm; do
    if [ -f "$sidecar" ]; then cp -a "$sidecar" "$backup_dir/"; fi
done
echo "Backup: $backup_dir"
if ! "$sampling_python" scripts/upgrade_sampling_orders.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt; bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager

