#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
completion_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then completion_python="$candidate"; break; fi
done
if [ -z "$completion_python" ]; then echo "Python-Umgebung des FactoryOS-Diensts fehlt."; exit 1; fi
"$completion_python" -m compileall -q factoryos scripts
"$completion_python" scripts/upgrade_order_completion.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
completion_backup="/home/factoryos/backups/order_completion_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$completion_backup"
cp -a instance/factoryos.db "$completion_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$completion_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $completion_backup"
if ! "$completion_python" scripts/upgrade_order_completion.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt zur Prüfung gestoppt. Bitte Fehlerausgabe weitergeben."; exit 1
fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Neue Rechte für Büro und Einrichter in der Rechteverwaltung zuweisen. Seiten neu laden."
