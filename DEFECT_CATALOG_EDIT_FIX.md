# Fehlerkatalog: abgestimmter Dateistand und Bearbeitungsfehler

Das Serverprotokoll zeigt eindeutig `AttributeError: 'ArticleDefect' object has no attribute 'tool_no'` in der Bearbeitungsroute. Die Route erwartete die optionale Werkzeugnummer, das geladene Datenmodell enthielt sie jedoch nicht. Das lässt sich nicht durch Kameraberechtigungen oder einen bloßen Datenbankbefehl beheben: Python-Datenmodell, Routen und Datenbank müssen zusammenpassen.

Dieses Paket enthält deshalb den vollständigen aktuellen Fehlerkatalog-Dateisatz einschließlich **factoryos/modules/article_defects/models.py**. Alle Dateien mit ihrer Ordnerstruktur nach GitHub übernehmen, nicht nur die HTML-Dateien. Danach:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_defect_catalog_edit_fix.sh
```

Der Installer prüft das tatsächlich geladene Datenmodell vor Änderungen, stoppt den Dienst, sichert die Datenbank und ergänzt eine gegebenenfalls fehlende optionale Werkzeugnummer-Spalte ohne Zurücksetzen der Einträge. Er prüft anschließend die Spalte, Beispielabfragen und Vorlagen. Falls Dateien fehlen oder das Modell nicht passt, wird ausdrücklich abgebrochen. Bei einem Fehler nach Dienststopp bleibt der Dienst zur Prüfung gestoppt. Bestehende Einträge und Foto-Dateien werden nicht gelöscht oder neu angelegt.

## Oberfläche und Rechte

- Detailansicht zeigt Fotos nur an. Kein „Foto löschen“-Button und kein Löschformular in dieser Ansicht.
- Nach „Bearbeiten“ stehen gespeicherte Fotos unterhalb des Eingabeformulars. Löschen benötigt sowohl `defects.edit` als auch `defects.delete_photos`; reine Ansichts-/Bearbeitungsrechte oder ein isoliertes Löschrecht reichen nicht aus. Dies wird serverseitig geprüft.
- Löschen ist eine separate Aktion mit Rückfrage, CSRF- und Versionsprüfung. Die Seite weist darauf hin, zuerst Textänderungen zu speichern. Nicht gespeicherte Textänderungen und neu ausgewählte Fotos gehen beim Neuladen durch Löschen verloren; dies steht ausdrücklich in der Rückfrage.
- Nach Löschen geht es wieder in die Bearbeitung, nicht zurück in die reine Detailansicht. Die anderen Fotos und der Fehlereintrag bleiben erhalten. Sicherungskopien werden nicht mitgelöscht.
- Kamera-/Galerie-Verkleinerung vor Upload, Vorschauen, Entfernen noch nicht gespeicherter Fotos, serverseitige Kompression und Artikelsuche über Werkzeugnummern bleiben enthalten. Die Skripte haben eine neue Versionskennung gegen alte Browser-Caches.

Kein Produktions-, Lager-, Auftrags- oder Prüfplan-Reset. Keine neue externe Erkennung oder kostenpflichtiger Dienst. Nach Installation die App neu laden und zunächst einen bestehenden archivierten Eintrag mit Foto öffnen und bearbeiten.

## Prüfungen

Automatisierte Regression mit bestehenden Einträgen und fehlender Datenbankspalte; gemapptes Werkzeugfeld; Bearbeiten von archivierten Einträgen mit Foto ohne Werkzeugnummer; gültige/historische Werkzeugnummern; ungültige Formulare; reine Detailansicht; Löschbereich nur im Editor; getrennte Ansichts-/Bearbeitungs-/Löschrechte; GET-/CSRF-/Versionsschutz; Entfernung der tatsächlichen Datei; Rückkehr in funktionierenden Editor. Die Prüfungen verwenden künstliche Daten, keine Kopie eurer Produktivdaten. Zusätzlich werden die vorhandenen Fehlerkatalog-, Kompressions- und Browser-Uploadtests ausgeführt.
