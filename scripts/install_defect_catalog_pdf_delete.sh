#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
defect_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python"; do
 if [ -x "$candidate" ]; then defect_python="$candidate"; break; fi
done
test -n "$defect_python"
"$defect_python" scripts/upgrade_defect_catalog.py --check
"$defect_python" -c "import reportlab; from pathlib import Path; assert (Path(reportlab.__file__).parent / 'fonts/Vera.ttf').is_file()"
test -f instance/factoryos.db
sudo systemctl stop factoryos.service
defect_backup="/home/factoryos/backups/defect_catalog_pdf_delete_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$defect_backup"
cp -a instance/factoryos.db "$defect_backup/factoryos.db"
for suffix in -wal -shm; do
 if [ -f "instance/factoryos.db$suffix" ]; then cp -a "instance/factoryos.db$suffix" "$defect_backup/factoryos.db$suffix"; fi
done
echo "Sicherung: $defect_backup"
if [ -d instance/article_defect_photos ]; then tar -czf "$defect_backup/article_defect_photos.tar.gz" -C instance article_defect_photos; fi
"$defect_python" scripts/upgrade_defect_catalog.py
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "PDF-Export und Eintragslöschung eingerichtet. Fachrollen bewusst berechtigen. Kein Reset."
