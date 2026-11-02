#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
machine_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then machine_python="$candidate"; break; fi
done
if [ -z "$machine_python" ]; then
    echo "Python-Umgebung fehlt. Bitte diese Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$machine_python" -m compileall -q factoryos scripts
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
