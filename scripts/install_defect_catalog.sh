#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
defect_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
 if [ -x "$candidate" ]; then defect_python="$candidate"; break; fi
done
if [ -z "$defect_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$defect_python" -m compileall -q factoryos scripts/reset_test_inspection_plans.py
"$defect_python" scripts/upgrade_defect_catalog.py --check
"$defect_python" scripts/reset_test_inspection_plans.py
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
defect_backup="/home/factoryos/backups/defect_catalog_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$defect_backup"
cp -a instance/factoryos.db "$defect_backup/factoryos.db"
for suffix in -wal -shm; do
 if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$defect_backup/factoryos.db$suffix"; fi
done
echo "Sicherung: $defect_backup"
if ! "$defect_python" scripts/upgrade_defect_catalog.py; then echo "Upgrade fehlgeschlagen. Dienst bleibt zur Prüfung gestoppt."; exit 1; fi
if ! "$defect_python" scripts/reset_test_inspection_plans.py --apply --backup "$defect_backup/factoryos.db"; then echo "Prüfplan-Reset fehlgeschlagen. Dienst bleibt zur Prüfung gestoppt; Fehlerausgabe weitergeben."; exit 1; fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Prüfpläne zurückgesetzt; Fehlerkatalog und Reklamationen unter Qualität. Fachrollen bewusst berechtigen."
