# Projektgründe und passende Projektbereiche

Basis: `spiefer87-del/FactoryOS`, Branch `main`, Commit `0426fba4c05613e4069b7c3134c1d6a690fd0b25`.

## Installation

Die ZIP enthält die vollständigen geänderten und neuen Dateien sowie den benötigten bestehenden Projektinstaller. ZIP lokal entpacken und den Inhalt mit der enthaltenen Ordnerstruktur in das Stammverzeichnis des GitHub-Repositories hochladen. Die Dateien müssen die bisherigen Dateien ersetzen, beispielsweise `factoryos/modules/projects/workspace_models.py`. Keine zusätzliche äußere ZIP-Ordnerstufe in das Repository übernehmen. Den Upload auf `main` committen.

Danach auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_project_types.sh
```

Status und letzte Meldungen:

```bash
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Der Installer findet die vorhandene Python-Umgebung, prüft die Voraussetzungen, stoppt den Dienst, sichert die tatsächlich verwendete SQLite-Datenbank und ergänzt das Feld `project_workspaces.project_kind`. Die Sicherung liegt im Unterordner `backups` neben der verwendeten Datenbank, normalerweise `instance/backups/before_project_workspace_*.db`. Danach wird der Dienst wieder gestartet. Das Upgrade ist wiederholbar; bereits ausgewählte Projektgründe bleiben erhalten. Es werden keine neuen Python-Abhängigkeiten benötigt. Bei einem Migrationsfehler bleibt der Dienst zur Prüfung gestoppt; die Fehlerausgabe prüfen bzw. weitergeben.

## Verhalten

Beim Anlegen werden zuerst Projektgrund und Bezug ausgewählt. Der Bezug ist ein Werkzeug, eine bestehende Musterung oder bei allgemeinen Anfragen ein Projekt ohne festen Bezug. Bei einer Musterung werden das Werkzeug aus dem Auftrag bzw. dem Werkzeugbezug und die Vorgangsverknüpfung automatisch übernommen. Die Auswahl benötigt das bestehende Leserecht `sampling.view`.

| Projektgrund | Benötigter Bezug | Neue Teilewechsel | Neue Vorgangsverknüpfungen |
| --- | --- | --- | --- |
| Kundenanfrage | Optional | Nein | Musterung |
| Werkzeugreparatur | Werkzeug, auch über Musterung möglich | Ja | Fehlermeldung, Musterung |
| Werkzeugwartung | Werkzeug, auch über Musterung möglich | Ja | Fehlermeldung, Musterung |
| Werkzeugänderung | Werkzeug, auch über Musterung möglich | Ja | Fehlermeldung, Musterung |
| Musterungsvorbereitung | Werkzeug, auch über Musterung möglich | Nein | Musterung |
| Musterung bearbeiten / begleiten | Bestehende Musterung | Nein | Musterung |
| Werkzeugverlagerung | Werkzeug, auch über Musterung möglich | Nein | Musterung |
| Werkzeugabnahme | Werkzeug, auch über Musterung möglich | Nein | Musterung |
| Sonstiges | Optional | Nein | Musterung, Fehlermeldung |

Aufgaben, Team, Arbeitszeiten und Arbeitsberichte bleiben für alle Projektgründe verfügbar. Bei Projekten ohne Teileerfassung heißt der Aufgabenstatus „Wartet auf Klärung“. Teilewechsel und Vorgangsarten werden zusätzlich auf dem Server geprüft; das Ausblenden allein kann nicht umgangen werden.

Bestehende Projekte werden bewusst als „Noch nicht eingeordnet“ übernommen und behalten zunächst ihre bisherigen Bereiche. Unter „Projektverwaltung → Projektgrund / Beschreibung / Projektleitung“ können berechtigte Benutzer die Einordnung nachtragen oder ändern. Bei bisherigen Projekten ohne Werkzeug kann dort gleichzeitig ein Werkzeug ergänzt werden. Vor „Musterung bearbeiten / begleiten“ muss eine Musterung verknüpft sein.

Ein Wechsel des Projektgrunds löscht keine Zeiten, Berichte, Aufgaben, Vorgangsbezüge oder Teileeinträge. Vorhandene Teileeinträge erscheinen bei Projektgründen ohne Teileerfassung in einer aufklappbaren bisherigen Teilehistorie. Fehleinträge bleiben nachvollziehbar stornierbar. Projektgrund und Änderungen werden protokolliert. Musterungsfreigaben und Werkzeugzustände werden durch das Projekt nicht automatisch verändert.

## Prüfung

Mit isolierten Testdaten geprüft: bisherige Projektabläufe einschließlich Zeiterfassung, Rechte, Fotos und Teilehistorie; alle neuen Projektgründe; Pflichtbezüge; Übernahme von Musterungswerkzeugen; Anzeige und serverseitige Sperren; Änderung des Projektgrunds ohne Datenverlust; wiederholtes Upgrade der bisherigen Tabellenstruktur; tatsächliche Sicherung einer temporären SQLite-Datei vor der Änderung. Zusätzlich wurden die gerenderte Formularseite, die JavaScript-Umschaltung mit DOM-Ereignissen und das Absenden eines Musterungsprojekts geprüft. Eine grafische Browserprüfung war in der Testumgebung nicht möglich.

Optionaler Regressionstest mit der vorhandenen FactoryOS-Python-Umgebung:

```bash
./venv/bin/python scripts/test_project_types.py
```

Bei einer Umgebung namens `.venv` entsprechend `./.venv/bin/python` verwenden. Die Tests verwenden eigene synthetische Datenbanken und keine Produktionsdaten.
