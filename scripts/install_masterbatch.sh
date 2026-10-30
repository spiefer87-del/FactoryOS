#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
batch_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then batch_python="$candidate"; break; fi
done
if [ -z "$batch_python" ]; then
    echo "Python-Umgebung nicht gefunden. Bitte folgende Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$batch_python" -m compileall -q factoryos scripts
"$batch_python" scripts/upgrade_masterbatch.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
batch_backup="/home/factoryos/backups/masterbatch_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$batch_backup"
cp -a instance/factoryos.db "$batch_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then
        cp -a "instance/factoryos.db$suffix" "$batch_backup/factoryos.db$suffix"
    fi
done
echo "Backup: $batch_backup"
if ! "$batch_python" scripts/upgrade_masterbatch.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt. Bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
