#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
wait_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then wait_python="$candidate"; break; fi
done
if [ -z "$wait_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$wait_python" -m compileall -q factoryos scripts
"$wait_python" scripts/upgrade_setup_wait.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
wait_backup="/home/factoryos/backups/setup_wait_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$wait_backup"
cp -a instance/factoryos.db "$wait_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$wait_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $wait_backup"
if ! "$wait_python" scripts/upgrade_setup_wait.py; then echo "Upgrade fehlgeschlagen; Dienst bleibt zur Prüfung gestoppt. Fehlerausgabe weitergeben."; exit 1; fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Rüstende-Auswahl und gerüstete Wartezeiten sind eingerichtet. Seiten neu laden."
