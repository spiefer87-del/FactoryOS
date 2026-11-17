#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
echo "ACHTUNG: TESTRESET entfernt Zeitbuchungen, Lagerbewegungen/-bestände, Mengenmeldungen und geschlossene Aufträge."
echo "Offene Aufträge und Stammdaten bleiben; alle Maschinen werden bestätigt abgerüstet."
python3 scripts/reset_production_warehouse_tests.py --actor admin
sudo systemctl stop factoryos.service
reset_backup="/home/factoryos/backups/production_warehouse_test_reset_$(date +%Y%m%d_%H%M%S)"
if ! python3 scripts/reset_production_warehouse_tests.py --actor admin --apply --offline --confirm RESET-TESTDATEN --backup-directory "$reset_backup"; then
 echo "Reset nicht erfolgreich. Transaktion zurückgerollt; Dienst bleibt zur Prüfung gestoppt. Fehlermeldung weitergeben."
 exit 1
fi
sudo systemctl start factoryos.service
sudo systemctl is-active factoryos.service
echo "Fertig. App auf allen Geräten neu laden. Ein erneuter Aufruf löscht keine neu erfassten Daten."
