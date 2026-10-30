#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pdf_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then
        pdf_python="$candidate"
        break
    fi
done
if [ -z "$pdf_python" ]; then
    echo "Python-Umgebung nicht gefunden. Bitte diese Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
if ! "$pdf_python" -c 'import reportlab; assert int(reportlab.Version.split(".")[0]) >= 4'; then
    "$pdf_python" -m pip install 'reportlab>=4.0,<5'
fi
"$pdf_python" -c 'from reportlab.pdfbase.ttfonts import TTFont; TTFont("Check", "factoryos/static/fonts/sampling/DejaVuSans.ttf"); TTFont("CheckBold", "factoryos/static/fonts/sampling/DejaVuSans-Bold.ttf"); print("PDF-Schriften und Abhängigkeit geprüft.")'
"$pdf_python" -m compileall -q factoryos
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
