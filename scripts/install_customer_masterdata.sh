#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
booking_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then
        booking_python="$candidate"
        break
    fi
done
if [ -z "$booking_python" ]; then
    echo "Python-Umgebung nicht gefunden. Bitte folgende Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$booking_python" -m compileall -q factoryos scripts
"$booking_python" scripts/upgrade_customer_masterdata.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
backup_dir="/home/factoryos/backups/customers_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$backup_dir"
cp -a instance/factoryos.db "$backup_dir/factoryos.db"
echo "Backup: $backup_dir"
if ! "$booking_python" scripts/upgrade_customer_masterdata.py; then
    echo "Upgrade fehlgeschlagen. Dienst bleibt gestoppt; bitte Fehlerausgabe weitergeben."
    exit 1
fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
