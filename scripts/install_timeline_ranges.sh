#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
timeline_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then timeline_python="$candidate"; break; fi
done
if [ -z "$timeline_python" ]; then
    echo "Python-Umgebung fehlt. Bitte Ausgabe weitergeben:"
    sudo systemctl cat factoryos | grep -E 'WorkingDirectory|ExecStart'
    exit 1
fi
"$timeline_python" -m compileall -q factoryos scripts
# Display-only update: no schema changes, no database writes or migration.
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
