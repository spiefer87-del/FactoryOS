#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ocr_fix_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then ocr_fix_python="$candidate"; break; fi
done
if [ -z "$ocr_fix_python" ]; then
    echo "Python-Umgebung fehlt. Bitte Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$ocr_fix_python" -m compileall -q factoryos scripts
"$ocr_fix_python" scripts/check_material_scan.py
# Does not modify systemd PATH, permissions, DB or package installations.
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
