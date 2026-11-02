#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
password_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then password_python="$candidate"; break; fi
done
if [ -z "$password_python" ]; then
    echo "Python-Umgebung nicht gefunden. Bitte folgende Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$password_python" -m compileall -q factoryos scripts
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
