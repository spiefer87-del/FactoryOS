# Maschinen: Vorwärts und rückwärts durch die Detailansicht blättern

Basis: main 62f9dba. Die ZIP enthält vollständige Ersatzdateien und neue Dateien.

- Oben in der Detailansicht: Vorherige Maschine, Nächste Maschine und Zur Übersicht.
- Anzeige der aktuellen Position, beispielsweise Maschine 2 von 12.
- Reihenfolge: Maschinennummer aufsteigend, wie die Standard-Maschinenübersicht. Keine Übernahme einer nur im Browser geänderten Tabellenfilterung oder Sortierung.
- Am Anfang/Ende ist der betreffende Button deaktiviert, ohne automatischen Sprung zum anderen Ende.
- Alle Maschinen einschließlich stillgelegter Maschinen bleiben erreichbar.
- Bestehende Anzeige-, Bearbeitungs- und Löschrechte bleiben unverändert.
- Mobil umbrechende Navigation und Tastaturfokus; keine JavaScript-Abhängigkeit.
- Keine Datenbankänderung oder zusätzliche Abhängigkeit erforderlich.

## Installation

Die Dateien unter den enthaltenen relativen Pfaden in GitHub übernehmen und committen.

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_machine_navigation.sh
```

## Prüfung

scripts/test_machine_navigation.py prüft mit isolierter SQLite-Datenbank die Navigation, Randfälle mit einer Maschine/gelöschten Maschinen, lesenden Zugriff ohne Bearbeitungsrecht, verweigerten Zugriff, HTML-Escaping und 404-Antworten.
Keine Prüfung gegen die produktive Raspberry-Datenbank, keine visuelle Browserprüfung.
