#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
order_forms_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then order_forms_python="$candidate"; break; fi
done
if [ -z "$order_forms_python" ]; then
    echo "Python-Umgebung fehlt. Bitte Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$order_forms_python" -m compileall -q factoryos scripts
# No schema change and no historical backfill.
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
