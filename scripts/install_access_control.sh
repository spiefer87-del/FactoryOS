#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
access_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then access_python="$candidate"; break; fi
done
if [ -z "$access_python" ]; then
    echo "Python-Umgebung fehlt. Bitte folgende Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$access_python" -m compileall -q factoryos scripts
"$access_python" scripts/configure_session_secret.py
"$access_python" scripts/upgrade_access_control.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
access_backup="/home/factoryos/backups/access_control_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$access_backup"
cp -a instance/factoryos.db "$access_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$access_backup/factoryos.db$suffix"; fi
done
echo "Backup: $access_backup"
if ! "$access_python" scripts/upgrade_access_control.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt. Bitte Ausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
