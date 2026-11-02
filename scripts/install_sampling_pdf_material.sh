#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pdf_material_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then pdf_material_python="$candidate"; break; fi
done
if [ -z "$pdf_material_python" ]; then
    echo "Python-Umgebung nicht gefunden. Bitte folgende Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$pdf_material_python" -m compileall -q factoryos scripts
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
