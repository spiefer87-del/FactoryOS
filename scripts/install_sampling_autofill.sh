#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
autofill_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then
        autofill_python="$candidate"
        break
    fi
done
if [ -z "$autofill_python" ]; then
    echo "Python-Umgebung nicht gefunden. Bitte diese Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$autofill_python" -m compileall -q factoryos
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager

