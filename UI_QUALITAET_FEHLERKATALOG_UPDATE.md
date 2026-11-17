# Einheitliche Bedienelemente, Qualitätsdashboard und Fehlerkatalog

Basis: `spiefer87-del/FactoryOS`, Branch `main`, Commit `a9278159f2fb10e0d8c16bf5a6a9b73f7de6a142` vom 17.11.2026.

## Installation

ZIP entpacken und alle enthaltenen vollständigen Dateien mit ihrer Ordnerstruktur in das Stammverzeichnis des GitHub-Repositories hochladen und auf `main` committen. Keine zusätzliche äußere ZIP-Ordnerstufe übernehmen. Die neuen CSS- und JavaScript-Dateien gehören mit zum Patch.

Danach auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos
```

Prüfen:

```bash
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Keine Datenbankmigration und keine neuen Laufzeit-Abhängigkeiten erforderlich. Geänderte Formatvorlagen haben neue Versionsparameter, damit der Browser die aktualisierten Dateien lädt.

## Änderungen

| Bereich | Anpassung |
| --- | --- |
| Gemeinsames App-Layout | Bisher ungestaltete Textlinks innerhalb des Inhalts erhalten einen abgerundeten Link-Button. Ungestaltete Aktionsbuttons erhalten denselben Stil wie primäre Aktionen. Bereits gestaltete Komponenten behalten ihre eigene Funktion und Farbrolle. |
| Vorhandene Buttons | Primäre, sekundäre und kleine Schaltflächen erhalten einheitliche Rundungen, Ausrichtung, Textumbruch und Fokusmarkierungen. Löschaktionen bleiben rot. Die persönliche Akzentfarbe wird bei neuen Link-Buttons und Standardaktionen berücksichtigt. |
| Qualitätsdashboard | Verwendet jetzt dieselben Symbol-, Titel- und Beschreibungsklassen wie Produktion und Stammdaten. Dadurch stimmen Symbolgröße, Titelgewicht und Abstände überein. Die noch nicht verfügbare Auswertung ist als inaktive Kachel statt als scheinbar anklickbarer Link dargestellt. |
| Zurück-Navigation | Qualität, Fehlerkatalog, artikelspezifische Fehler und Abbrechen erscheinen als abgerundete sekundäre Buttons. |
| Projekte | Projektnummer direkt als Link-Button; die Suche verwendet einen primären Button statt des Browser-Standardbuttons. Weitere bisher ungestaltete Projektlinks werden durch den gemeinsamen Stil abgedeckt. |
| Fehlerkatalog: Einstieg | Schon die erste Spalte enthält eine zusammenhängende klickbare Fläche aus Artikelnummer, Fehlerbezeichnung und Artikelname. Sie führt zum konkreten Fehlerkatalogeintrag, nicht zum Artikelstamm. Die redundante separate Fehlerspalte entfällt. |
| Fehlerkatalog: Handy | Unter 700 Pixeln wird jeder Tabelleneintrag als kompakte Karte mit beschrifteten Angaben angezeigt. Der Detailaufruf steht oben und benötigt kein seitliches Scrollen. |
| Fehlerkatalog: Bedienung | Suche, Sortierung und Seitenwechsel verwenden weiterhin die bestehende Tabellenlogik. Eine zusätzliche Sortierauswahl bleibt auch in der mobilen Kartenansicht bedienbar. |
| Fotoansichten / Spezialkomponenten | Bildvorschauen, Dashboardkacheln und bereits speziell gestaltete Links werden nicht pauschal in kleine Link-Buttons umgewandelt. Druckseiten verwenden weiterhin ihre eigenen Formatvorlagen. |

Es werden keine Daten, Zuordnungen, Rechte oder Speicherabläufe geändert. Die Detailseiten und Formularaktionen behalten ihre bisherigen Zieladressen und Berechtigungsprüfungen.

## Verifikation

11 unterschiedliche Python-Regressionstestskripte erfolgreich: Fehlerkatalog, Bearbeitung, Löschung/PDF, Fotos, Projekte/Projektgründe, Prüfplanliste, Prüfpläne, Stammdatenansichten, Zugriffsrechte, Aktivitäten und die neue UI-Prüfung.

Zusätzliche Prüfungen an den tatsächlich gerenderten HTML-Seiten und DOM-Ereignissen: übereinstimmende berechnete Dashboard-Typografie, Rundungen für Projekt-/Zurück-/Standardbuttons, richtige Detailziele in der ersten Katalogspalte, echte Tabellensortierung, Suche und Seitenwechsel sowie ausgenommene Fotolinks. Die JavaScript-Syntax wurde ebenfalls geprüft.

Eine grafische Prüfung in einem echten Browser bzw. auf dem Android-Gerät war in dieser Umgebung nicht möglich. Die mobile Anordnung ist über ihre Formatvorlagen und die gerenderte Struktur geprüft.

Optionaler isolierter Funktionstest:

```bash
./venv/bin/python scripts/test_ui_consistency.py
```

Bei einer Umgebung namens `.venv` entsprechend `./.venv/bin/python` verwenden. Der Test nutzt synthetische Daten und keine Produktionsdatenbank.
