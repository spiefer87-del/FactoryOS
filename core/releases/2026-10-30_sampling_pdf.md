# Musterung: PDF und manueller Druck

Basis: GitHub main a0ce4b3. Vollständige Ersatzdateien dieser Erweiterung.
Der bereits installierte Musterungsbereich wird vorausgesetzt.
Keine Datenbankänderung und kein erneutes Musterungs-Upgrade erforderlich.

## Bedienung

Nach dem Speichern einen Musterungsauftrag öffnen:

- PDF herunterladen: erzeugt einen aktuellen PDF-Ausdruck des gespeicherten Standes.
- Druckansicht öffnen: separate A4-Ansicht ohne Navigation oder Bearbeitungselemente.
- In der Druckansicht Jetzt drucken anklicken und den lokalen Drucker auswählen.

PDFs sind auch für Entwürfe verfügbar, dann ausdrücklich als Bearbeitungsstand
gekennzeichnet. Nicht gespeicherte Formularänderungen sind nicht enthalten.
Version und Erstellzeit der Ausgabe sind sichtbar. Intern abgeschlossene
Folgemusterungen und externe Kundenfreigabe werden weiterhin getrennt ausgewiesen.
Die Ausgabe verändert weder Auftrag noch Freigabe- oder Abschlussstatus.

PDF und Druckansicht nutzen dieselbe read-only Aufbereitung:
Auftragskopf, Stammdaten-Snapshots, Materialvorgaben, Durchführung, Ergebnisse,
Erstbemusterungsnachweise, Prüfpunkte, Bearbeiter, Prüfnotizen und Abschluss.
Leere Felder sind als fehlend erkennbar; 0 bleibt 0.
Gesamtaufwand wird nur bei zwei erfassten Zeitwerten addiert.
Lange Texte werden nicht abgeschnitten, sondern auf zusätzliche Seiten umbrochen.
Kopf/Fußzeile und Seitennummern im PDF. A4, gut lesbare deutsche Schrift,
zurückhaltende blaue Akzente und hellgraue Feldflächen.
Kein automatischer Druckauftrag, kein Excel-Zugriff, keine automatische
PDF-Archivierung auf dem Raspberry. PDF wird beim Abruf neu erzeugt.
PDF und Browserdruck können wegen der jeweiligen Druckengine anders umbrechen.
Browserseitige Kopf-/Fußzeilen bei Bedarf im Druckdialog ausschalten.

## Technik

Neue PDF- und Druckrouten sind wie die Musterungsansicht durch Anmeldung geschützt.
Dateinamen werden bereinigt; Cache-Control ist private/no-store.
Texte sind für ReportLab und HTML korrekt maskiert.
ReportLab >=4.0,<5 ist als Abhängigkeit ergänzt.
DejaVu-Schriften und zugehöriger Lizenztext liegen im Patch, damit die PDF-Ausgabe
nicht von auf dem Raspberry installierten Systemschriften abhängt.

## Installation

ZIP-Inhalte mit unveränderten Pfaden hochladen und auf GitHub committen:

    cd /home/factoryos/FactoryOS
    git status --short
    git pull --ff-only origin main
    bash scripts/install_sampling_pdf.sh

Bei Git-Konflikten stoppen und Ausgabe weitergeben.
Das Skript erkennt übliche Python-Umgebungen, installiert bei Bedarf nur
die neue PDF-Abhängigkeit, prüft Schriftdateien und startet FactoryOS neu.
Bei Fehler vor Neustart bleibt der laufende Dienst unverändert.

## Tests

Bestehende Musterungs-Regressionstests erfolgreich.
PDF-/Druckrouten, Login-Schutz, fehlender Auftrag (404), Download-Header,
Cache-Regel, unveränderte Datensatzversion, gespeicherte Snapshots,
Entwurfskennzeichnung, interne Freigabe, Umlaute, echte Nullwerte und
maskierte Sonderzeichen mit isolierter SQLite-Testdatenbank geprüft.
Normale und sehr lange Textfälle erzeugt, PDF-Seiten mit Poppler gerendert
und visuell auf Umbruch, Lesbarkeit und Kopf-/Fußzeilen geprüft.
Kein physischer Druckertest auf eurem Firmendrucker möglich.
