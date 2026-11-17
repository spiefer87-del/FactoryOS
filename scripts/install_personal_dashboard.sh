#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
dashboard_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
 if [ -x "$candidate" ]; then dashboard_python="$candidate"; break; fi
done
if [ -z "$dashboard_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$dashboard_python" -m compileall -q factoryos
"$dashboard_python" scripts/upgrade_user_preferences.py --check
"$dashboard_python" -c 'from factoryos import create_app; from factoryos.extensions import db; from sqlalchemy import inspect; app=create_app(); ctx=app.app_context(); ctx.push(); assert inspect(db.engine).has_table("user_preferences"), "Bitte zuerst die vorhandene Profilverwaltung installieren."'
sudo systemctl restart factoryos.service
sudo systemctl is-active factoryos.service
echo "Dashboard vollständig neu laden. Keine Datenbankmigration und keine zusätzlichen Rechte erforderlich."
