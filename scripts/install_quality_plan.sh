#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
quality_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then quality_python="$candidate"; break; fi
done
if [ -z "$quality_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$quality_python" -m compileall -q factoryos scripts
"$quality_python" scripts/upgrade_quality_plan.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
quality_backup="/home/factoryos/backups/quality_plan_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$quality_backup"
cp -a instance/factoryos.db "$quality_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$quality_backup/factoryos.db$suffix"; fi
done
echo "Datenbanksicherung: $quality_backup"
if ! "$quality_python" scripts/upgrade_quality_plan.py; then echo "Upgrade fehlgeschlagen; Dienst bleibt zur Prüfung gestoppt. Fehlerausgabe weitergeben."; exit 1; fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Prüfplan neu laden. Bestehende Freigaben bleiben erhalten; neue Module werden im Entwurf bearbeitet."
