#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cycle_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then cycle_python="$candidate"; break; fi
done
if [ -z "$cycle_python" ]; then
    echo "Python-Umgebung fehlt. Bitte diese Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$cycle_python" -m compileall -q factoryos scripts
"$cycle_python" scripts/upgrade_cycle_time.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
cycle_backup="/home/factoryos/backups/cycle_time_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$cycle_backup"
cp -a instance/factoryos.db "$cycle_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$cycle_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $cycle_backup"
if ! "$cycle_python" scripts/upgrade_cycle_time.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt. Bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
