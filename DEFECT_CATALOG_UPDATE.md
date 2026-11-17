# FactoryOS: Prüfplan-Testreset und Artikel-Fehlerkatalog

Dieses Paket enthält vollständige neue/geänderte Dateien, auf Basis von `main` (`a3d5736`). Die Ordnerstruktur beim Hochladen nach GitHub beibehalten; keine Datenbankdatei hochladen oder ersetzen.

## Installation auf dem Raspberry Pi

Nach Übernahme aller Dateien in GitHub im bestehenden Terminal ausführen:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_defect_catalog.sh
```

**Achtung: Der erste erfolgreiche Lauf entfernt ALLE aktuell vorhandenen Prüfpläne einschließlich freigegebener Pläne, früherer Revisionen, Module, Prüfmerkmale und Prüfplanhistorie.** Das ist ausschließlich der angeforderte Abschluss der Testphase. Nicht auf einer anderen Installation mit produktiven Prüfplänen verwenden.

Vor der Löschung stoppt der Installer FactoryOS und sichert die SQLite-Datenbank einschließlich vorhandener WAL-Dateien unter `/home/factoryos/backups/defect_catalog_DATUM_UHRZEIT`. Er prüft die Integrität und vergleicht die gesicherten Prüfplaninhalte mit dem aktuellen Bestand. Bei Abweichungen oder unbekannten externen Prüfplanbezügen wird nicht gelöscht. Ein Fehler nach dem Stoppen lässt den Dienst zur Prüfung gestoppt; dann bitte die Fehlermeldung weitergeben, nicht wiederholt andere Upgrades starten.

Artikel, Werkzeuge, Maschinen, Einstellberichte, Aufträge, Lagerbuchungen und bisherige Werkzeug-Fehlermeldungen werden nicht zurückgesetzt. Medien alter Prüfpläne bleiben für eine mögliche Wiederherstellung auf dem Server; die zugehörigen Verknüpfungen liegen in der Sicherung. Der Reset wird im allgemeinen Änderungsprotokoll vermerkt. Ein einmaliger Reset-Vermerk verhindert, dass ein erneuter Installerlauf später neu angelegte Prüfpläne löscht.

Eine Wiederherstellung ist aus der Sicherung möglich. Nach weiteren produktiven Buchungen darf nicht einfach eine alte Gesamtdatenbank zurückkopiert werden: Prüfplandaten müssen dann gezielt wiederhergestellt werden, damit spätere Fachdaten nicht verloren gehen.

## Neue Bereiche unter Qualität

- **Fehlerkatalog:** Produktionsfehler gehören fest zu einem vorhandenen Artikel. Suche nach Artikelnummer/Bezeichnung ab zwei Zeichen, typische Fehlerarten wie Grat, Schlieren oder Dieseleffekt, Kurzbeschreibung und ausführliche Beobachtung; erprobte Abhilfe optional. Keine automatische Ursache, Maschinenfreigabe oder Änderung von Einstellparametern.
- Kameraaufnahme auf unterstützten Mobilgeräten oder Fotoauswahl. Bis zu fünf Fotos pro Eintrag, jeweils JPEG/PNG/WebP, maximal 10 MB und 24 MP. Fotos bleiben auf eurem Server; kein externer Erkennungsdienst. Vor Speicherung werden sie ausgerichtet, verkleinert und ohne EXIF/GPS-Metadaten neu kodiert.
- Suchbare Tabellenübersicht, Artikel-Direktzugang, Bearbeitung mit Versionskontrolle, Archivierung statt endgültiger Löschung. Fotos sind nur über die geschützte Anwendungsroute verfügbar.
- **Reklamationen:** eigener vorbereiteter Bereich. Noch keine vollständige Reklamations- oder 8D-Abwicklung; diesen Ablauf bauen wir getrennt auf.

## Rechte und Oberfläche

Administratoren haben Zugriff. Für andere Rollen unter Administration die neuen Rechte bewusst vergeben: `defects.view`, `defects.create`, `defects.edit` und `complaints.view`. Ohne passende Rechte werden die jeweiligen Kacheln nicht angeboten. Die Bereiche stehen auch in der persönlichen Dashboard-Konfiguration zur Auswahl; bestehende persönliche Dashboards werden nicht verändert.

Nach Installation die App neu laden. Unter Qualität müssen die Prüfplanzähler auf null stehen und der Fehlerkatalog zunächst leer sein. Danach einen Testeintrag mit Artikel und Foto anlegen. Die tatsächliche Kameraauswahl hängt vom Android-Browser und dessen Berechtigungen ab.

## Prüfung dieses Pakets

Automatisierter Test mit synthetischer SQLite-Datenbank: Upgrade wiederholbar; Reset nur mit passender Sicherung; Zurückweisung gleicher Zeilenzahl mit abweichendem Inhalt; freigegebene Revisionen und Module entfernt; andere Fachdaten erhalten; spätere Prüfpläne bei Wiederholung erhalten; Foto-Upload und ungültige Bilder; Artikelbindung; Archivierung; konkurrierende Bearbeitung; CSRF und private Fotozugriffe; Kategorien und Artikel-Link.

Die Tests laufen isoliert. Die Installation und Löschung auf eurem Raspberry Pi erfolgen erst durch den oben genannten Befehl.
