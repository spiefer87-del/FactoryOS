# Direktbuchung aus der Wareneingangsliste

Basis main e88274e. Vollständige geänderte/neue Dateien. Keine Schemaänderung,
keine automatische Änderung vorhandener Bestände durch die Installation.

Dateien mit Verzeichnisstruktur nach GitHub übernehmen, anschließend:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_warehouse_intake.sh
```

Danach Wareneingang vollständig neu laden, damit die neuen JavaScript- und
CSS-Dateien geladen werden.

## Bedienung

In „Noch übergebbare bestätigte Produktion“ auf einen Auftrag bzw. seine Zeile
klicken oder die fokussierte Zeile mit Enter/Leertaste öffnen. Es erscheint ein
scrollbares Dialogfenster mit Auftrag, zugehörigem Stammdatenartikel und der
aktuell noch übergebbaren Gutmenge. Die Menge ist als Vorschlag vorausgefüllt
und kann auf eine tatsächlich übergebene Teilmenge reduziert werden.

Los-/Chargen-/Behälterkennung und Beleg ergänzen. Wer Produktionsübergabe und
Lagerannahme buchen darf, kann im selben Fenster einen Lagerplatz auswählen
und beides zusammen bestätigen. Andernfalls bleibt „nur Produktionsübergabe“
verfügbar. Der Dialog bietet keine zusätzliche Bestandsfreigabe an.

Die endgültige Checkbox bestätigt die tatsächliche Übergabe und gegebenenfalls
den tatsächlichen Empfang am Lagerplatz. Erst „Verbindlich buchen“ speichert.
Die Zuordnung zu Auftrag/Artikel ist serverseitig festgelegt, keine frei
änderbare Artikelwahl. Fehlende Stammdaten werden benannt und nicht erfunden.
Nach Erfolg lädt sich die Eingangsliste mit den neuen Restmengen neu.

## Buchungssicherheit

Kombinierte Übergabe und Lagerannahme erzeugen zwei separate Journalbuchungen
in einer einzigen Transaktion. Eine fehlerhafte Annahme hinterlässt weder eine
halbe Übergabe noch einen neuen Losursprung. Kennungen und Inhaltsprüfung
schützen beide Teilbuchungen vor Wiederholung. Restmenge und Lagerrevision
werden bei der Speicherung erneut geprüft. Lagerannahme erzeugt ausschließlich
Sperrbestand; Qualitätsfreigabe bleibt separat. Produktionsausschuss darf nicht
als Gutmenge übernommen werden. Rollenrechte und CSRF gelten unverändert.

Ohne Dialog-/JavaScript-Unterstützung öffnet der Auftragslink dieselbe Maske
als normale Seite. Auf Lesebenutzer wirken die Zeilen nicht als Buchungslinks.
Schließen/Escape, Tastaturfokus, begrenzte Dialoghöhe und mobile Breite sind
berücksichtigt. Verspätete Ladeantworten dürfen keinen neu geöffneten Auftrag
überschreiben.

Lokal geprüft: bestehende Lagerregression, Konkurrenztest unabhängiger SQLite-
Sitzungen und neue Direktbuchungstests: Teilmenge, zwei atomare Journalbuchungen,
Wiederholung, vollständiger Rollback bei fehlerhaftem Ziellagerplatz, Obergrenze,
Rechte, CSRF, reine GET-Lesezugriffe, aktualisierte Restmenge, nur Übergabe und
normale Seite ohne JavaScript. Endgültige Dialogdarstellung bitte auf eurem
Handy bzw. Arbeitsplatzbrowser prüfen.
