#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
setup_report_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then setup_report_python="$candidate"; break; fi
done
if [ -z "$setup_report_python" ]; then echo "Python-Umgebung nicht gefunden. Dienstkonfiguration prüfen: sudo systemctl cat factoryos"; exit 1; fi
"$setup_report_python" -m compileall -q factoryos scripts
"$setup_report_python" scripts/upgrade_setup_reports.py --check
test -f instance/factoryos.db
sudo systemctl stop factoryos
setup_report_backup="/home/factoryos/backups/setup_reports_$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$setup_report_backup"
cp -a instance/factoryos.db "$setup_report_backup/factoryos.db"
for suffix in -wal -shm; do
    if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$setup_report_backup/factoryos.db$suffix"; fi
done
echo "Datenbank-Backup: $setup_report_backup"
if ! "$setup_report_python" scripts/upgrade_setup_reports.py; then echo "Upgrade fehlgeschlagen; Dienst bleibt für Prüfung gestoppt."; exit 1; fi
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
echo "Foto-Erkennung verwendet vorhandenes Tesseract. Ohne OCR bleibt die vollständige Handeingabe verfügbar."
