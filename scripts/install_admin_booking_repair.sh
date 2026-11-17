#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
defect_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python"; do
 if [ -x "$candidate" ]; then defect_python="$candidate"; break; fi
done
test -n "$defect_python"
"$defect_python" -m compileall -q factoryos/modules/booking_review scripts/upgrade_booking_review.py
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
defect_backup="/home/factoryos/backups/admin_booking_repair_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$defect_backup"
cp -a instance/factoryos.db "$defect_backup/factoryos.db"
for suffix in -wal -shm; do
 if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$defect_backup/factoryos.db$suffix"; fi
done
echo "Sicherung: $defect_backup"
"$defect_python" scripts/upgrade_booking_review.py
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Buchungsübersicht und Administrator-Reparatur ergänzt. Kein Prüfplan-Reset."
