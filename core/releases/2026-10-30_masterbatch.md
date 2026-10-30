# Materialstamm: Masterbatch, Artikelrezeptur und Musterungsauftrag

Basis: FactoryOS main 471ea2e. Dieses ZIP enthält vollständige Ersatzdateien
und neue Dateien mit ihren Repository-Pfaden, keinen Git-Diff und keine Datenbank.

## Aufteilung

- Materialart `masterbatch`: Farbbatch mit eigener Materialnummer, Bezeichnung,
  Hersteller, Farbe, Farbnummer und RAL / Wunschfarbton. Dokumente, Lagerdaten,
  Lieferantenvorbereitung und Berechtigungen bleiben die des Materialmoduls.
- Eigenes Masterbatch-Feld im Artikel, optionaler FK auf `materials.id`.
  Farbe und RAL werden dort aus dem Materialstamm angezeigt, nicht doppelt gepflegt.
- Artikelabhängige Zugabe `masterbatch_percent`, optional. Bezugsbasis ausdrücklich
  Hauptrohstoffgewicht: 2 % = 2 kg Farbbatch je 100 kg Hauptrohstoff.
  Keine automatische Dosierung. Die betriebliche Bezugsbasis vor Einsatz prüfen.
- Hauptrohstoff und Farbbatch sind getrennte Zuordnungen. Verwendete Materialien
  können nicht zwischen Hauptrohstoff und Masterbatch umkategorisiert werden.
  Dafür bei Bedarf einen separaten Materialstamm anlegen.
- Materialübersicht kann nach Masterbatch filtern, zusätzlicher Einstieg im Dashboard.
  RAL und Farbnummer werden bei der Suche berücksichtigt.
- Material-Excel-Export und -Vorlage enthalten `ral_color` und die neue Materialart;
  Import akzeptiert `masterbatch`, `Farbbatch` und `Masterbatch / Farbbatch`.
  Alte Imports ohne RAL-Spalte erhalten bereits gespeicherte RAL-Angaben.

## Musterung

Farbbatch-Auswahl, Farbe, Prozentzugabe und Wunschfarbton / RAL stehen im
Auftragskopf, der Detailansicht sowie im PDF und in der Druckansicht.
Artikelwahl schlägt eindeutige vorhandene Zuordnungen und die Rezeptur vor.
Manuelle oder bereits gespeicherte Angaben werden nicht überschrieben.
Andere Batch-Auswahl übernimmt keine Dosierung des vorherigen Batch automatisch.
Nicht hinterlegte Angaben werden nicht erfunden. Messwerte bleiben getrennt.

Bei Anlass Farbänderung werden alle Farbfelder gelb markiert. Automatische
Alt-Farbvorschläge werden nicht als neuer Versuch übernommen; manuelle Angaben
bleiben erhalten. Neue eingegebene Farbangaben verlangen ausdrückliche Bestätigung.
Artikel-, Rohstoff-, Batch-, Farbton- oder Prozentänderungen setzen die Bestätigung
zurück. Die Abschlussprüfung prüft serverseitig den Bezug auf exakt diese Werte und
verlangt Farbe oder RAL. Ein leerer Entwurf darf weiterhin gespeichert werden.
Eine Bestätigung ersetzt keine Qualitätsfreigabe. Erstbemusterungsregeln bleiben.

Auftragsbezogene Angaben bleiben gespeichert, auch wenn später Materialfarbe oder
Bezeichnung geändert werden. Frühere abgeschlossene Aufträge werden nicht geändert.
Referenzierte Masterbatches sind gegen Löschung geschützt.

## Installation

1. ZIP entpacken und enthaltene Pfade unverändert in GitHub übernehmen/committen.
2. Auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_masterbatch.sh
```

Bei Pull-Konflikten oder Fehlern stoppen und Ausgabe weitergeben, nichts zurücksetzen.
Der Installer sucht die bisher verwendeten Python-Umgebungen, prüft das Schema,
stoppt den Dienst, sichert `instance/factoryos.db` inklusive eventuell vorhandener
WAL/SHM-Dateien nach `/home/factoryos/backups/masterbatch_<Zeitstempel>`, ergänzt
die drei optionalen Spalten plus Index und startet danach FactoryOS.
Bei Upgrade-Fehler bleibt der Dienst gestoppt. Sicherungspfad wird ausgegeben.
Es werden weder Artikel noch Materialien automatisch umklassifiziert oder gefüllt.
Keine neuen Python-Abhängigkeiten. Anschließend Browser vollständig neu laden.

## Prüfung

Isolierte SQLite-Testdatenbank; kein Zugriff auf die Raspberry-Datenbank.
Workflow-, Artikel-, Material-, Autofill-, Bestätigungs-, Snapshot- und Drucktests.
ADD COLUMN an alten Tabellen mit Bestandssatz sowie wiederholtes Upgrade getestet.
Material-Export/Import-Feldmapping einschließlich Masterbatch und RAL geprüft.
Native und TomSelect-Interaktionen per Node-DOM-Test, kein echter Browser-Lauftest.
Die bestehende, fachfremde OpenCV-Zeichnungserkennung wird nur im Test gestubbt.
PDF-Regressionstests einschließlich langer Texte; Masterbatch-PDF gerendert und
alle drei Seiten visuell geprüft. Python-Kompilierung, Shell-Syntax, Diff-Prüfung.

```bash
python scripts/test_masterbatch.py
python scripts/test_sampling_autofill.py
python scripts/test_sampling_pdf.py
node scripts/test_sampling_autofill.js
```
