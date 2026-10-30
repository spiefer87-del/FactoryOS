# Musterung: Stammdatenvorschläge und bewusste Rohstoffauswahl

Basis: GitHub main 2c7c98f. Vollständige Ersatzdateien dieser Erweiterung.
Bestehender Musterungs- und PDF-Bereich vorausgesetzt.
Keine neue Datenbankspalte, keine Migration und keine neue Paketabhängigkeit.

## Vorausfüllung

Bei einem Artikelwechsel werden Kunde und Rohstoff aus dem Artikel vorgeschlagen.
Genau ein zugeordnetes Werkzeug wird vorausgewählt. Bei mehreren Werkzeugen
bleibt das Werkzeug offen und die zugeordneten Nummern werden als Hinweis gezeigt.
Farbe wird aus dem gewählten Material vorgeschlagen; bei Farbänderung wird die
Artikel-/Materialfarbe nicht automatisch als gewünschte Versuchsfarbe übernommen.
Fehlende Stammdaten werden nicht erfunden.

Automatisch vorgeschlagene Werte dürfen bei einem weiteren Artikelwechsel
aktualisiert werden. Manuell geänderte Werte und beim Öffnen bereits vorhandene
Formularwerte bleiben erhalten. Gespeicherte oder nach Validierungsfehlern
wieder angezeigte Formulare werden nicht beim Laden neu befüllt.

Referenzbereich zeigt Zeichnung/Index, Zykluszeit, Schussgewicht, Verpackungseinheit,
Werkzeuglagerort, Kavitäten sowie Trocknungstemperatur/-dauer aus den Stammdaten.
Diese Werte werden ausdrücklich NICHT als gemessene Ist-Werte eingetragen.
Maschinen ohne Artikelzuordnung, Prüfergebnisse, Trocknungsentscheidung,
Zeichnungsvorlage und Freigaben werden nicht automatisch angenommen.

Referenzwerte werden beim Speichern im vorhandenen JSON-Snapshot gesichert.
Bei gleicher Zuordnung bleibt dieser Referenzstand bei späteren Bearbeitungen
erhalten. Ältere Aufträge ohne Referenzbereich bekommen ihn beim nächsten Speichern.
Die Artikel-, Werkzeug- und Materialstammdaten werden nicht verändert.

## Werkstoffänderung

Formular-Rohstoffzeile und Warnhinweis sind gelb.
Der bisherige Artikelrohstoff bleibt zur Orientierung sichtbar und ist keine
automatische Freigabe des Versuchsmaterials. Die Qualitätssicherung muss den
gewählten Rohstoff mit einer separaten Checkbox ausdrücklich bestätigen.
Dies gilt auch dann, wenn bewusst das bestehende Material verwendet werden soll.
Bei Artikel-, Material- oder Anlasswechsel wird die Checkbox zurückgesetzt.

Server prüft die Bestätigung beim Speichern eines ausgewählten Materials und
erneut beim Abschluss. Unausgewähltes Material ist im Entwurf weiter möglich.
Die Bestätigung speichert Artikel-ID, Material-ID, Benutzer-ID und UTC-Zeit im
vorhandenen Auftrags-JSON. Änderungen sind Teil des bestehenden Änderungsverlaufs.
Bereits abgeschlossene Altaufträge werden nicht nachträglich wieder geöffnet.
Auf der Detailseite ist der Werkstoffänderungs-Hinweis ebenfalls sichtbar.
PDF-/Drucklayout wird durch diesen Patch nicht verändert.

## Installation

ZIP mit vollständigen Pfaden hochladen und auf GitHub committen:

    cd /home/factoryos/FactoryOS
    git status --short
    git pull --ff-only origin main
    bash scripts/install_sampling_autofill.sh

Bei Konflikten stoppen. Installationsskript prüft Python-Code und startet den
Dienst neu. Danach Browser vollständig neu laden (Strg+F5).

## Prüfungen

Bestehende Musterungsregression, neue Python-Tests mit SQLite-Testdatenbank,
Formularrendering, Bestätigungssperre und Referenz-Snapshot erfolgreich.
JavaScript-Ereignistests mit simuliertem DOM für native Selects und TomSelect:
eindeutige/mehrere Werkzeuge, Artikelwechsel, Leeren, manuelle Werte,
vorhandene Werte, Materialwarnung, Bestätigungsreset und Farbänderung.
Keine visuelle Browserprüfung oder physischer Raspberry-Zugriff.
