#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Reuse the existing stopped-service, backup-first, idempotent migration.
bash scripts/install_project_workspace.sh
echo "Projektgründe und passende Projektbereiche eingerichtet. Bestehende Projekte bei Bedarf in der Projektverwaltung einordnen."
