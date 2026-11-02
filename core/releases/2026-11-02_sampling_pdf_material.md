# PDF und Druckansicht: Farbbatch-Angaben unter Material

Basis main c134366. ZIP mit vollständigen geänderten Dateien, keinen Diff anwenden.

Farbe / Farbton, Farbbatch-Bezeichnung und -Nummer, prozentuale Zugabe sowie
RAL / Wunschfarbton stehen jetzt ausschließlich unter „02 Material und Vorgaben“
zusammen mit dem Rohstoff und den weiteren Zusätzen. Sie wurden aus
„01 Auftrag und Zuordnungen“ entfernt. PDF und HTML-Druckansicht verwenden
dieselbe Dokumentstruktur. Die Eingabeformulare, gespeicherte Daten,
Bestätigungen und Freigaberegeln bleiben unverändert.

Keine Datenbankmigration und keine neuen Abhängigkeiten erforderlich.
ZIP mit unveränderten Pfaden in GitHub übernehmen und committen. Auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_sampling_pdf_material.sh
```

Bei Konflikten oder Fehlermeldungen stoppen und Ausgabe weitergeben.
Danach Druckansicht neu laden bzw. PDF neu herunterladen; ältere heruntergeladene
PDF-Dateien werden nicht nachträglich verändert.

Prüfung: isolierte SQLite-Testdatenbank, Masterbatch- und PDF-Regressionstests,
richtige Gruppierung/HTML-Reihenfolge, PDF-Erzeugung und visuelle Prüfung,
Python-Kompilierung, Shell-Syntax und Diff-Prüfung. Kein Live-Datenbankzugriff.
Fachfremde OpenCV-Zeichnungserkennung nur in Testumgebung gestubbt.
