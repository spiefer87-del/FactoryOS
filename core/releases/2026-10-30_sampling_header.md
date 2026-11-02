# Material-Einstieg und übersichtlicher Musterungsauftrag

Basis: main a6a7bed. Vollständige Ersatzdateien mit Repository-Pfaden plus
Installationsskript und Test; keine Datenbank im ZIP.

## Änderungen

- Zusätzliche Masterbatch-/Farbbatch-Kachel entfernt. Sie öffnete bereits dieselbe
  Materialtabelle wie die Materialübersicht, nur mit einem Materialart-Filter.
  Materialübersicht, Filter und Kategorie Masterbatch bleiben vollständig erhalten.
- Anlegen/Bearbeiten: eigener erster Abschnitt „Warum wird gemustert?“ mit deutlich
  hervorgehobenem Anlass und konkreter Erläuterung. Das vorhandene Feld
  `other_reason` wird weiterverwendet, nicht dupliziert. Bei Sonstiges weiter Pflicht,
  sonst optional. Genau ein Anlass, nach Anlage unveränderlich.
- Werkzeug und Artikel sind im Zuordnungsformular visuell hervorgehoben.
- Detailansicht: großer Anlassbereich und eigene Karten für Werkzeugnummer,
  Artikel, Maschine und Kunde vor den weiteren Daten. Anzeige aus dem gespeicherten
  Auftragsstand, nicht aus zwischenzeitlich geänderten Stammdaten.
- PDF und Druckansicht: deutlicher Anlassblock, Erläuterung und großer Werkzeug-/
  Artikelbereich. PDF-Folgeblätter nennen den Anlass zusätzlich in der Kopfzeile.
  Lange Erläuterungen können umbrechen; Eingaben werden weiterhin escaped.
- Freigaben, Erstbemusterungsregeln, gelbe Prüfhinweise, Vorausfüllung und
  Bestätigungen für Material/Farbänderungen bleiben unverändert.

## Installation

Dateien aus dem ZIP mit unveränderten Pfaden in GitHub übernehmen und committen.
Danach auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_sampling_header.sh
```

Bei Pull-Konflikten oder Fehlermeldungen stoppen und Ausgabe weitergeben.
Kein Datenbank-Upgrade, keine neuen Abhängigkeiten und keine Datenlöschung.
Das Skript prüft Python-Syntax und vorhandenes ReportLab vor dem Neustart.
Danach Browser vollständig neu laden (Strg+F5).

## Prüfung

Isolierte SQLite-Testdatenbank, nicht die Live-Datenbank des Raspberry.
Bestehende Workflow-, PDF- und Vorausfülltests plus `test_sampling_header.py`.
Geprüft: entfernter zusätzlicher Einstieg bei erhaltener Kategorie, eindeutige
Formularfelder, Reihenfolge der Inhalte, gespeicherte Snapshots, reine Lesezugriffe,
HTML-Escaping, lange Erläuterungen sowie PDF-Erzeugung. PDF-Seiten gerendert und
visuell geprüft. Python-Kompilierung, Shell-Syntax, Git-Diff-Prüfung.
Kein echter Browser-/Druckertest. Fachfremde OpenCV-Erkennung ist nur im Test gestubbt.
