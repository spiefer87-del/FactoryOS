#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
quality_list_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then quality_list_python="$candidate"; break; fi
done
if [ -z "$quality_list_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$quality_list_python" -m compileall -q factoryos
"$quality_list_python" scripts/upgrade_quality_plan.py --check
"$quality_list_python" -c 'from factoryos import create_app; from factoryos.extensions import db; from sqlalchemy import inspect; app=create_app(); ctx=app.app_context(); ctx.push(); inspector=inspect(db.engine); assert inspector.has_table("qm_checks") and "inspection_settings" in {c["name"] for c in inspector.get_columns("qm_sections")}, "Bitte zuerst das Prüfplan-Modul-Update installieren."'
sudo systemctl restart factoryos.service
sudo systemctl is-active factoryos.service
echo "Keine Datenbankänderung erforderlich. Prüfplanübersicht im Browser vollständig neu laden."
