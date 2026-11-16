#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
groq_setup_python=""
for candidate in "$PWD/.venv/bin/python" "$PWD/venv/bin/python" /home/factoryos/.venv/bin/python /home/factoryos/venv/bin/python; do
    if [ -x "$candidate" ]; then groq_setup_python="$candidate"; break; fi
done
if [ -z "$groq_setup_python" ]; then echo "Python-Umgebung des FactoryOS-Diensts nicht gefunden."; exit 1; fi
"$groq_setup_python" -m compileall -q factoryos scripts
"$groq_setup_python" scripts/upgrade_setup_reports.py --check
# Does not read/print the key in the terminal, alter nginx, DuckDNS or Tailscale.
sudo /usr/bin/python3 scripts/configure_groq_vision.py
# Upgrade seeds the new permission but grants it to no normal role. Existing tables unchanged.
"$groq_setup_python" scripts/upgrade_setup_reports.py
sudo systemctl daemon-reload
sudo systemctl restart factoryos.service
sudo systemctl is-active factoryos.service
echo "Dienst neu gestartet. Wizard neu laden, Foto-Erkennung öffnen, Extern mit Groq wählen."
echo "Im Parameter-Schritt Übertragung pro Foto bestätigen. API/Erkennung erst mit einem Foto getestet."
echo "DuckDNS und Tailscale wurden nicht verändert. Kein Schlüssel muss erneut eingegeben werden."
