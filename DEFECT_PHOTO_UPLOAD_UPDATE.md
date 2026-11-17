# Kamera-Upload und einzelne Fotos entfernen

Ergänzung zum bestehenden Fehlerkatalog mit Werkzeugsuche. Vollständige Dateien mit Ordnerstruktur nach GitHub übernehmen.

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_defect_photo_upload.sh
```

Der Installer sichert die Datenbank und ergänzt das neue Recht. Kein Prüfplan-Reset und keine automatische Löschung vorhandener Bilder. nginx-Konfiguration, DuckDNS, Tailscale und OCR bleiben unverändert. Bei Fehlern nach Dienststopp bleibt der Dienst zur Prüfung gestoppt.

## Große Kamerafotos

Die bisherigen 413-Meldungen stammen von nginx, noch vor der serverseitigen Bildverarbeitung. Die neue Oberfläche verkleinert Kamera- und Galerieaufnahmen deshalb im Browser vor dem Upload: maximal 1.600 Pixel und 150.000 Byte pro Bild; bei detailreichen Bildern wird weiter verkleinert. Fünf Bilder benötigen zusammen höchstens 750 KB zuzüglich Formulartext und Multipart-Overhead. Das liegt unter der üblichen nginx-Grenze von 1 MB. Eine individuell niedrigere Grenze kann weiterhin blockieren; dann erscheint eine Erklärung direkt im Formular, Texte und Auswahl bleiben erhalten. Kein unbegrenztes Anheben der Uploadgrenze.

Die Verarbeitung benötigt JavaScript und ein vom Browser lesbares Foto (typischerweise JPEG/PNG/WebP); lokale Quelldateien über 50 MB werden mit Hinweis abgewiesen. Das Original bleibt auf dem Handy und wird nicht hochgeladen. Die serverseitige Prüfung und Kompression bleiben zusätzlich aktiv. HEIC oder besondere Kameramodi können je nach Browser eine Umstellung auf JPEG erfordern.

Neu ausgewählte Fotos haben eine Vorschau mit Größe und einen Button „Foto entfernen“. Das entfernt nur die noch nicht gespeicherte Auswahl und benötigt kein Löschrecht. Während der Verarbeitung wird der Speichern-Button gesperrt. Mehrere Kameraaufnahmen können nacheinander ergänzt werden.

## Bereits gespeicherte Fotos

In Detailansicht und Bearbeitung gibt es pro Bild „Foto löschen“, mit Rückfrage. Dafür muss unter Administration ausdrücklich **Gespeicherte Fehlerfotos löschen** (`defects.delete_photos`) vergeben werden. Bearbeitungsrechte allein reichen nicht aus. Administratoren haben Zugriff. POST, CSRF und Versionsprüfung schützen die Aktion; Benutzer und Foto-ID werden protokolliert. Der Fehlereintrag und andere Fotos bleiben erhalten.

Das Löschen entfernt den Datenbankbezug und anschließend die Bilddatei. Scheitert die physische Entfernung ausnahmsweise, bleibt das Bild über die Anwendung gesperrt und der Fehler wird serverseitig protokolliert. Vorhandene Sicherungskopien werden nicht geändert. Es gibt keinen Papierkorb; eine Wiederherstellung ist gegebenenfalls nur aus einer vorherigen Sicherung möglich.

Nach Installation die App neu laden, Kameraaufnahme testen und ein entbehrliches Testbild löschen. Die automatisierten Tests ersetzen keinen abschließenden Test auf eurem Android-Gerät und eurem nginx-Server.
