# Fehlerkatalog: PDF / Drucken und vollständige Eintragslöschung

Alle Dateien mit Ordnerstruktur nach GitHub übernehmen. Anschließend:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_defect_catalog_pdf_delete.sh
```

Der Installer prüft Datenmodell und PDF-Bibliothek, stoppt FactoryOS und sichert die Datenbank sowie den vorhandenen Fehlerfoto-Ordner. Er ergänzt Rechte, ohne Fachrollen automatisch zu berechtigen. Kein Reset und keine automatische Löschung bestehender Einträge. Bei Fehler nach Dienststopp bleibt FactoryOS zur Prüfung gestoppt.

## PDF

Auf der Detailansicht gibt es **PDF / Drucken**. Die Übersicht bietet den gesamten Katalog oder, nach Artikel gefiltert, dessen Artikelkatalog als PDF. Der lokale Freitext-Suchfilter der Tabelle ist kein zusätzlicher PDF-Filter. Archivierte Einträge werden mit Status gekennzeichnet mitexportiert.

Das A4-Dokument enthält FactoryOS-Kopf, Artikelnummer und Bezeichnung, optionale Werkzeugnummer, Fehlerart, Status, Version, Ersteller und Zeitangaben in Europe/Berlin, Beschreibung, Abhilfe und alle Fotos mit unverzerrtem Seitenverhältnis. Lange Texte und mehrere Fotos laufen auf weitere Seiten weiter. Fußzeile mit Exportdatum und Seitenzahl. Fehlende/nicht lesbare Bilder bekommen einen ausdrücklichen Hinweis statt eines stillschweigenden Weglassens. PDF wird geschützt auf Anfrage erzeugt und nicht öffentlich gespeichert. Nach Download im PDF-Betrachter drucken.

Rechte: `defects.view` und neu **Fehlerkatalog als PDF drucken** (`defects.pdf_export`). ReportLab ist bereits für andere FactoryOS-Exporte vorgesehen; keine neue Cloud-Anbindung und keine Zusatzkosten. Die vorhandene Foto-Kompression bleibt unverändert.

## Eintrag vollständig löschen

Im Bearbeitungsbereich unterhalb der Fotos steht **Gesamten Eintrag löschen**. Erforderlich sind Ansicht, Bearbeiten und das separate neue Recht **Fehlereinträge vollständig löschen** (`defects.delete`). Eine Bestätigungsseite zeigt den Eintrag und die Anzahl zugehöriger Fotos. Löschgrund (10–1000 Zeichen), Checkbox, CSRF und aktuelle Version sind Pflicht. GET löscht nichts. Unbekannte Fachverknüpfungen verhindern die Löschung.

Die Aktion entfernt den Eintrag, seine Foto-Datensätze und danach die Foto-Dateien. Andere Fehler, Artikel und Werkzeuge bleiben erhalten. Benutzer, Löschgrund und Originaltext/-metadaten einschließlich Foto-IDs stehen im allgemeinen Artikel-Änderungsprotokoll. Bei einer seltenen Dateisystemstörung bleibt ein Restbild nicht mehr über die App zugänglich; dies wird serverseitig protokolliert.

Kein Papierkorb oder automatischer Rückgängig-Button. Eine Wiederherstellung der Bilder benötigt eine vorherige Foto-Dateisicherung, nicht nur eine Datenbanksicherung. Der Installer legt bei vorhandenem Foto-Ordner ein separates `article_defect_photos.tar.gz` zur Datenbanksicherung ab. Später hinzugefügte Fotos sind darin noch nicht enthalten. Bereits heruntergeladene PDFs und andere Sicherungen werden durch Löschen nicht entfernt.

Unter Administration die neuen Rechte bewusst vergeben; Administratoren haben Zugriff. Nach Installation die App neu laden. Automatisierte Tests prüfen PDF-Erzeugung, Fotos, lange/escaped Texte, Rechte, Version/CSRF/Bestätigung, vollständige Foto-/Eintragslöschung und das erhaltene Änderungsprotokoll. PDF-Testseiten werden zusätzlich visuell geprüft.
