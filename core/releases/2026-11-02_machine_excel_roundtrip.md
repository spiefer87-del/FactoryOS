# Maschinen: ein Excel-Format für Import, Export und Vorlage

Basis: main 8c341ba. Vollständige Ersatzdateien, kein Datenbankumbau.

## Korrekturen

- Ursache: Der bisherige Export hatte ein deutsches erstes Blatt und ein zweites technisches Importblatt. Der Import las nur das erste Blatt und erwartete machine_no.
- Export und leere Vorlage verwenden jetzt dieselbe zentrale Definition mit 30 deutschen Spalten im Blatt Maschinen. Hinweise stehen getrennt.
- Die Vorlage enthält keine Beispielmaschine, die versehentlich angelegt werden könnte.
- Vorhandene deutsche Exportdateien und die bisherigen internen Spaltennamen werden erkannt. Das Blatt Maschinen hat Vorrang vor dem alten Importformat; System-/Auditspalten bleiben unverändert.
- Alle Maschinen- und Spritzgießdaten sowie Wartungsdatum mit Uhrzeit bleiben beim Roundtrip erhalten. Führende Nullen bleiben als Text erhalten; Texte werden nicht als Excel-Formeln exportiert.
- Maschinennummer dient als Schlüssel: bestehende Datensätze aktualisieren, neue Nummern anlegen. Entfernte Spalten bleiben unverändert; leere Zellen vorhandener Spalten löschen optionale Angaben.
- Doppelte Nummern werden für alle betroffenen Zeilen abgelehnt. Doppelte Datenspalten und Formeln führen zum Abbruch vor der Datenübernahme. Fehlerhafte Zahlen, Datumswerte, Typen, Status und zu lange Texte werden gemeldet. Gültige Zeilen werden weiterhin übernommen, fehlerhafte Zeilen zurückgerollt.
- Berechtigungen für Import/Export bleiben unverändert.

## Installation

ZIP im GitHub-Repository mit denselben relativen Pfaden einspielen und committen.
Auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_machine_excel.sh
```

Keine Datenbankmigration erforderlich. Der Installer sucht .venv und venv sowie die bisher verwendeten externen Python-Umgebungen, kompiliert und startet FactoryOS neu. Bei abweichender Umgebung meldet er dies ohne Installation neuer Pakete.

## Prüfung

Isolierte SQLite-Tests in scripts/test_machine_excel.py: Export und Reimport aller technischen Felder, deutsche/alte Überschriften, gemeinsame Export-/Vorlagenstruktur, Datum/Uhrzeit, führende Nullen, Nullwerte, Teiländerungen, Zahlenprüfung, Zeilenrollback, doppelte Nummern/Spalten, Formeln, Download-Routen.

Zusätzlich scripts/test_access_control.py als Sicherheitsregression. Nicht gegen die produktive Raspberry-Datenbank getestet.
