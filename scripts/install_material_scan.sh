#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
material_scan_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then material_scan_python="$candidate"; break; fi
done
if [ -z "$material_scan_python" ]; then
    echo "Python-Umgebung fehlt. Bitte Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$material_scan_python" -c 'from PIL import Image, ImageOps, ImageFilter'
"$material_scan_python" -m compileall -q factoryos scripts
if ! command -v tesseract >/dev/null 2>&1 || ! tesseract --list-langs 2>/dev/null | grep -qx deu || ! tesseract --list-langs 2>/dev/null | grep -qx eng; then
    sudo apt-get update
    sudo apt-get install -y tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng
fi
tesseract --list-langs
tesseract --list-langs 2>/dev/null | grep -qx deu
tesseract --list-langs 2>/dev/null | grep -qx eng
# No DB schema changes, no credentials or external AI account needed.
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
