#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
control_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then control_python="$candidate"; break; fi
done
if [ -z "$control_python" ]; then
    echo "Python-Umgebung fehlt. Bitte Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$control_python" -m compileall -q factoryos scripts
"$control_python" scripts/upgrade_machine_control.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
control_backup="/home/factoryos/backups/machine_control_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$control_backup"
cp -a instance/factoryos.db "$control_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$control_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $control_backup"
if ! "$control_python" scripts/upgrade_machine_control.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt. Bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
