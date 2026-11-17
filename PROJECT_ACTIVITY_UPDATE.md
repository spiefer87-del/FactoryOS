# Verständliche Projektaktivitäten und zentrale Übersicht

Basis: `spiefer87-del/FactoryOS`, Branch `main`, Commit `2f80ec159c7144cb61617ccf9112473ec1ef465b` vom 17.11.2026. Der bereits installierte Patch für Projektgründe ist enthaltene Voraussetzung.

## Hochladen und installieren

ZIP entpacken. Alle enthaltenen Dateien mit ihrer Ordnerstruktur in das Stammverzeichnis des GitHub-Repositories hochladen und auf `main` committen. Beispielsweise muss `factoryos/templates/projects/workspace_detail.html` die bestehende Datei an genau diesem Pfad ersetzen. Keine zusätzliche äußere ZIP-Ordnerstufe hochladen.

Danach auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos
```

Prüfen:

```bash
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Für diesen Patch sind weder eine Datenbankmigration noch neue Python-Abhängigkeiten erforderlich.

## Änderung

- Das Projektprotokoll zeigt fachliche Einträge anstelle von JSON. Beispiel: „Projektleitung: admin → Mitarbeitername“ und „Projektgrund: Noch nicht eingeordnet → Sonstiges“. Unveränderte Einstellungsfelder werden weggelassen.
- Projektanlage, Einstellungen, Teamzuordnungen, Aufgaben, Vorgangsverknüpfungen, Arbeitsberichte, Zeitbuchungen einschließlich Korrektur/Storno, Teilevorgänge und Archivierung/Wiederöffnung erhalten lesbare Bezeichnungen.
- Dieselben Einträge erscheinen gemeinsam mit den bisherigen allgemeinen Aktivitäten in der zentralen Aktivitätenliste, nach Zeitpunkt sortiert und mit einem Link zum Projekt.
- Die Hauptliste kann nach Bereich, insbesondere „Projekte“, gefiltert werden. Die Anzahl-Auswahl 5/15/25/50/Alle berücksichtigt beide Protokollquellen. Standard sind 50 Einträge.
- Zeitangaben in der Hauptliste und im Projektprotokoll verwenden Europe/Berlin mit CET/CEST.

Die Anzeige liest die vorhandenen Projektprotokolle direkt. Deshalb erscheinen auch bereits gespeicherte Projektänderungen ohne Nachmigration. Es werden keine Protokolle kopiert oder doppelte Einträge angelegt und keine Bestandsdaten verändert. Ältere Einträge mit weniger gespeicherten Angaben zeigen die noch vorhandenen Informationen; nicht gespeicherte Details werden nicht nachträglich erfunden.

Die vorhandenen Projektberechtigungen gelten auch in der Hauptliste: `activity.view` öffnet die Aktivitätenübersicht; Projektaktivitäten benötigen zusätzlich `projects.view` und eine Projektzuordnung als Mitglied/Leitung oder `projects.view_all`. Geschützte Musterungs- und Fehlermeldungsbezüge erhalten ohne Quell-Leserecht keine zusätzlichen Detailangaben.

## Prüfung

Geprüft mit isolierten synthetischen Datenbanken: bisherige Musterungs- und Projektabläufe, Aufbereitung älterer Einträge im Format des Screenshots, Namen und Projektgrund-Bezeichnungen, gemischte zeitliche Reihenfolge, Bereichs- und Anzahlfilter, persönliche Projektsicht, berechtigte Gesamtsicht, geschützte Quellbezüge, unveränderte Datensätze und keine Duplikate nach wiederholtem Lesen. Die Hauptliste bleibt auch vor Installation optionaler Projekttabellen verfügbar. HTML-Templates werden über echte Flask-Anfragen gerendert.

Optionaler Regressionstest mit der vorhandenen Python-Umgebung:

```bash
./venv/bin/python scripts/test_project_activity.py
```

Bei einer Umgebung namens `.venv` stattdessen `./.venv/bin/python` verwenden. Der Test nutzt eigene Testdatenbanken und keine Produktionsdaten.
