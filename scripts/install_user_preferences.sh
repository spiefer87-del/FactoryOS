#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
preferences_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then preferences_python="$candidate"; break; fi
done
if [ -z "$preferences_python" ]; then
    echo "Python-Umgebung nicht gefunden. Bitte folgende Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$preferences_python" -m compileall -q factoryos scripts
"$preferences_python" scripts/upgrade_user_preferences.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
preferences_backup="/home/factoryos/backups/user_preferences_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$preferences_backup"
cp -a instance/factoryos.db "$preferences_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$preferences_backup/factoryos.db$suffix"; fi
done
echo "Backup: $preferences_backup"
if ! "$preferences_python" scripts/upgrade_user_preferences.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt. Bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
