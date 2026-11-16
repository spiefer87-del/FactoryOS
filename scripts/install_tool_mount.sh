#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
mount_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then mount_python="$candidate"; break; fi
done
if [ -z "$mount_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$mount_python" -m compileall -q factoryos scripts
"$mount_python" scripts/upgrade_tool_mount.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
mount_backup="/home/factoryos/backups/tool_mount_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$mount_backup"
cp -a instance/factoryos.db "$mount_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$mount_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $mount_backup"
if ! "$mount_python" scripts/upgrade_tool_mount.py; then echo "Upgrade fehlgeschlagen; Dienst bleibt zur Prüfung gestoppt. Fehlerausgabe weitergeben."; exit 1; fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Seiten neu laden und den tatsächlichen Werkzeugbestand je Maschine prüfen/bestätigen. Recht: Rüstvorgänge erfassen."
