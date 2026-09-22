# Maschinen Booking – Timeline

## Inhalt

- responsive Timeline mit allen Maschinen und ihren vorhandenen Buchungen
- Kennzeichnung von Produktion, Rüsten, Störungen und freien Zeiten
- aktuelle Zeitmarke und auswählbarer Zeitraum (24 Stunden, 3 Tage, 7 Tage)
- Fertigstellungsprognose für laufende Produktionsaufträge
- mobile Detailkarten je Maschine
- direkte Verknüpfung zum Auftrag

## Berechnung der Prognose

Die Prognose nutzt ausschließlich vorhandene FactoryOS-Daten:

`(Sollmenge - gemeldete Gutmenge) × Zykluszeit des Artikels`

Fehlen Artikelzuordnung, Zykluszeit oder Auftragsdaten, zeigt FactoryOS bewusst
keine erfundene Fertigstellungszeit an. Für diesen Patch ist keine
Datenbankmigration erforderlich.

## Raspberry Pi aktualisieren

Nach dem Hochladen und Committen der Dateien auf GitHub:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
./.venv/bin/python -m compileall -q factoryos
sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
```

Falls der Dienst nicht als `active (running)` angezeigt wird:

```bash
sudo journalctl -u factoryos -n 80 --no-pager
```
