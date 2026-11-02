# Störung erst auswählen, dann buchen

Basis: main 197debd. Geänderte/neue Dateien vollständig in Originalpfaden.

- Auf der Maschinen-Hauptseite gibt es keine Störgrundauswahl mehr.
- „Störung melden“ ist ein Navigationsbutton und öffnet die eigene Auswahlseite
  innerhalb desselben Pop-ups; auf der Touchscreen-Seite entsprechend direkt.
- Aktive Störgründe werden als große auswählbare Touch-Felder angezeigt.
- „Sonstige Störung / eigene Beschreibung“ bleibt möglich (mindestens 5 Zeichen).
- Erst „Störung speichern“ bestätigt die Meldung und beginnt die Störzeit.
  Das Öffnen oder Abbrechen der Seite verändert keine Buchungen.
- Laufender Zustand, Maschine, Auftrag und Werkzeug bleiben zur Kontrolle sichtbar.
- Alte Hauptseiten-POSTs für Störung öffnen nur die neue Auswahl; sie buchen nicht.
- Rechte, CSRF, UUID-Doppelbuchungsschutz, Versionsprüfung und Entstörlogik bleiben
  erhalten. Veraltete Auswahlseiten dürfen keine neueren Vorgänge überschreiben.
- Kein Datenbank-Schemawechsel und keine neue APK erforderlich.

Nach Übernahme der Dateien in GitHub:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_fault_selection.sh
```

Der Installer verwendet den bisherigen Maschinenbedienungs-Installer mit
Strukturprüfung, Dienststopp, Datenbanksicherung und Wiederanlauf. Danach App
neu laden. Voraussetzung ist der bereits installierte Maschinenbedienungs-Patch.

Isolierte SQLite-Integrationstests: Hauptseite ohne Störgründe, separate Seite,
Öffnen/Abbrechen ohne Schreibzugriff, Pflichtbeschreibung bei Sonstiges, aktiver
Störgrund, ungültiger/inaktiver Grund, CSRF, Rechte, veralteter Stand, Replay,
Weiterleitung im eingebetteten Pop-up und bisherige Maschinensteuerungsabläufe.
Python-/JavaScript-/Shell-Syntax und ZIP werden geprüft. Kein Zugriff auf die
produktive Datenbank; visuelle Touchscreen-Abnahme bleibt vor Ort erforderlich.
