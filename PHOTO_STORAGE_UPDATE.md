# Ergänzung: Speicherarme Fotos im Artikel-Fehlerkatalog

Voraussetzung ist das vorherige Paket `FactoryOS_Pruefplan_Reset_Fehlerkatalog.zip`. Dieses Zusatzpaket enthält vollständige neue/geänderte Dateien für die Foto-Speicherung. Ordnerstruktur beim Hochladen nach GitHub beibehalten.

## Verhalten für neue Fehlerkatalog-Fotos

- Kameraaufnahme und Galerie-Upload verwenden dieselbe serverseitige Verarbeitung.
- Höchstens 1.600 Pixel an der langen Seite, Seitenverhältnis bleibt erhalten; kleine Bilder werden nicht hochskaliert.
- Optimiertes JPEG, höchstens 500.000 Byte (500 KB) pro gespeichertem Bild. Zuerst wird die Kompression angepasst, bei besonders komplexen Bildern anschließend auch die Auflösung weiter reduziert.
- EXIF-Ausrichtung wird angewandt; Metadaten wie EXIF/GPS werden nicht mitgespeichert. Transparente Bilder bekommen einen weißen Hintergrund.
- Nur das verarbeitete Foto wird dauerhaft geschrieben, keine zusätzliche Originaldatei. Der Upload wird zur Verarbeitung im Arbeitsspeicher gelesen; mögliche temporäre Upload-Dateien des Webservers sind davon getrennt.
- Bis zu fünf Fotos ergeben maximal 2,5 MB Bilddateien pro Eintrag, zuzüglich Datenbank-/Dateisystemaufwand und Sicherungskopien.
- Uploadgrenzen bleiben 10 MB und 24 Megapixel. Bei ungültigen Bildern oder Überschreitung wird mit verständlicher Fehlermeldung abgebrochen.

Bestehende Fotos werden nicht verändert, überschrieben oder gelöscht. Andere Fotobereiche, technische Zeichnungen, PDFs und OCR-Verarbeitung sind nicht Teil dieser Ergänzung. Bereits vorhandene Fotos können größer sein als die neuen Grenzen.

## Installation

Nach Übernahme der Dateien in GitHub:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos.service
```

Keine Datenbankmigration und **kein weiterer Prüfplan-Reset** notwendig. Anschließend die App neu laden. Dieses Zusatzpaket enthält absichtlich keinen Reset-Installer.

## Geprüft

`scripts/test_defect_photos.py` prüft speicherintensive Bilder, feste Dateigröße, Größenbegrenzung, kein Hochskalieren, EXIF-Ausrichtung, Metadatenentfernung, Transparenz und ungültige Uploads. Der aktualisierte Integrationstest prüft zusätzlich die tatsächlich gespeicherte JPEG-Datei und dass kein Original daneben abgelegt wird. Die Prüfungen verwenden ausschließlich künstliche Testdaten.
