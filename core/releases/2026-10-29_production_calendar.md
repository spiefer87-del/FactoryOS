# Maschinen Booking – Produktionskalender

## Inhalt

- konfigurierbares wöchentliches Produktionsfenster
- Standard: Montag 04:30 Uhr bis Samstag 06:00 Uhr
- Samstage nach 06:00 Uhr und Sonntage werden in Prognosen übersprungen
- Pflege von Feiertagen, Brückentagen und Betriebsruhen
- ganztägige und zeitlich begrenzte Kalenderausnahmen
- graue Kennzeichnung produktionsfreier Zeiten in der Timeline
- Fertigstellungsprognose berücksichtigt Wochenplan und Ausnahmen
- Setup-Seite ist auf Administratoren beschränkt

## Datenbank

Das idempotente Upgrade-Skript legt folgende Tabellen an:

- `production_calendar_settings`
- `production_calendar_exceptions`

Es kann gefahrlos erneut ausgeführt werden und legt beim ersten Lauf den
Standard-Wochenplan Montag 04:30 Uhr bis Samstag 06:00 Uhr an.

## Raspberry Pi

```bash
cd /home/factoryos/FactoryOS
sudo systemctl stop factoryos
./.venv/bin/python scripts/upgrade_production_calendar.py
./.venv/bin/python -m compileall -q factoryos scripts
sudo systemctl start factoryos
sudo systemctl status factoryos --no-pager
```
