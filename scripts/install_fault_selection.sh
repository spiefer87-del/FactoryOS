#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# No schema change. Reuse the established checked installer and DB backup.
bash scripts/install_machine_control.sh
