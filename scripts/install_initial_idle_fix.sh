#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
idle_fix_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then idle_fix_python="$candidate"; break; fi
done
if [ -z "$idle_fix_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$idle_fix_python" -m compileall -q factoryos scripts
"$idle_fix_python" scripts/upgrade_tool_mount.py --check
"$idle_fix_python" scripts/repair_initial_idle.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
idle_fix_backup="/home/factoryos/backups/initial_idle_fix_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$idle_fix_backup"
cp -a instance/factoryos.db "$idle_fix_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$idle_fix_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $idle_fix_backup"
if ! "$idle_fix_python" scripts/repair_initial_idle.py; then echo "Nachtrag fehlgeschlagen. Dienst bleibt zur Prüfung gestoppt; Fehlerausgabe weitergeben."; exit 1; fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Timeline neu laden. Neue Bestandsmeldungen starten fehlende Zeitaufzeichnungen automatisch."
