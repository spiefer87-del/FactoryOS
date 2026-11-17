#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
project_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
 if [ -x "$candidate" ]; then project_python="$candidate"; break; fi
done
if [ -z "$project_python" ]; then echo "FactoryOS-Python-Umgebung fehlt."; exit 1; fi
"$project_python" -m compileall -q factoryos/modules/projects scripts/upgrade_project_workspace.py
"$project_python" scripts/upgrade_project_workspace.py --check
sudo systemctl stop factoryos.service
if ! "$project_python" scripts/upgrade_project_workspace.py --backup; then
 echo "Migration fehlgeschlagen. Dienst bleibt zur Prüfung gestoppt; Fehlerausgabe weitergeben. Sicherung liegt, falls erstellt, unter instance/backups."
 exit 1
fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Projektbereich eingerichtet. Neue Projektrechte in der Berechtigungsmatrix bewusst vergeben."
