# Aktivitäten: bereinigte Darstellung und ergänzte Protokolle

Basis: `spiefer87-del/FactoryOS`, Branch `main`, Commit `143a7c9cc2d816de139d282aacf362553b954ae5` vom 17.11.2026. Dieser Stand enthält bereits Projektgründe und die Projektaktivitäten aus den vorherigen ZIPs.

## Installation auf GitHub und Raspberry

Die ZIP enthält alle vollständigen geänderten und neuen Dateien. Lokal entpacken und den Inhalt mit der enthaltenen Ordnerstruktur ins Stammverzeichnis des GitHub-Repositories hochladen und auf `main` committen. Keine zusätzliche äußere ZIP-Ordnerstufe übernehmen. Alle enthaltenen Dateien gehören zusammen, insbesondere die neuen Python-Helfer, das gemeinsame Template und die CSS-Datei.

Danach auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos
```

Prüfen:

```bash
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Keine Datenbankmigration und keine neuen Laufzeit-Abhängigkeiten erforderlich.

## Ergebnisse der Prüfung

| Bereich | Gefundener Fehler / fehlende Aktivität | Änderung |
| --- | --- | --- |
| Gemeinsame Anzeige | Einzelwerte wurden wie Vorher-/Nachher-Paare behandelt; Bestätigungen teilweise leer angezeigt | Einzelwerte, direkte Ereignisdaten, Paare, Listen und verschachtelte Daten werden einheitlich aufbereitet |
| Fehlerkatalog | „Artikel gelöscht/erstellt“ bei Löschung/Anlage eines Fehlereintrags; Rohdaten und Foto-Dateinamen | Eigene Überschriften für Fehlereintrag und Foto; beschriftete Angaben statt Wörterbuch-Ausgabe; Fotos als Anzahl |
| Produktionsabweichung | Bestätigter Grund und Berechnungsstand erschienen als leere Änderung | Begründung und gespeicherte Bewertungsdaten werden lesbar angezeigt |
| Leere Werte | Beispielsweise Beschreibung und Werkzeugbauer als „– → –“ | Gleichwertige Leerwerte werden ausgeblendet; 0 und Nein bleiben erhalten |
| Stammdaten | Technische Feldnamen und gespeicherte Zuordnungs-IDs | Gemeinsame deutsche Feldbezeichnungen und Auflösung verfügbarer Namen/Nummern |
| Musterungen, Planung, Zeitkorrekturen, Werkzeugbestand | Verschachtelte Schnappschüsse und Listen wurden roh ausgegeben | Beschriftete Detailzeilen, lesbare Statuswerte und passende Ereignisüberschriften |
| Separate Artikelhistorie | Eigene Rohdatenanzeige blieb neben dem allgemeinen Protokoll bestehen | Verwendet ebenfalls die gemeinsame Aufbereitung |
| Hauptliste | Lagerjournal und Prüfplanjournal fehlten | Vorhandene Einträge werden direkt mit angezeigt, ohne Kopien oder Nachmigration |
| Messmittel | Kalibrierungen, Anlage und Statusänderungen fehlten im allgemeinen Protokoll | Neue Vorgänge werden protokolliert; ältere gespeicherte Kalibrierungen werden ergänzend gelesen und nicht doppelt angezeigt |
| Verwaltung | Benutzer- und Rollenänderungen sowie der alternative Rechteeditor hatten Lücken | Anlage, Änderungen, Löschung und Rechteänderungen werden in derselben Transaktion protokolliert; Passwortänderungen ausschließlich als Ereignis |
| Werkzeug-Excel-Import | Importierte Werkzeugänderungen fehlten | Erfolgreiche Zeilen erhalten einen Protokolleintrag; fehlerhafte zurückgerollte Zeilen nicht |
| Dateien / Bilder | Separate Werkzeug-/Materialdokumente und Hauptbildänderungen waren nicht protokolliert | Erfolgreiche Uploads, Archivierungen und Hauptbildwechsel erscheinen; reine Dateiänderungen beim Werkzeugbearbeiten werden ebenfalls erfasst |
| Aufträge / Kalender | Erfolgreiche Auftragslöschung und Kalenderänderungen hatten keine allgemeinen Aktivitäten | Protokollierung ergänzt |
| Ältere Prüfplan-Editoraktionen | Einzelne Merkmals-, Zeichnungs- und Ausschnittaktionen fehlten | Einträge im vorhandenen Prüfplanjournal ergänzt; dadurch auch in der Hauptliste sichtbar |
| Detailansichten / Filter | Einige fest begrenzte Abfragen ignorierten die Auswahl 5/15/25/50/Alle | Auswahl in den betroffenen Detail- und Planungsansichten berücksichtigt |
| Uhrzeiten / Handyansicht | Unterschiedliche Zeitdarstellung; lange Rohdatenblöcke | Aktivitätszeiten in Europe/Berlin mit CET/CEST; umbrechende Detailzeilen, auf schmalen Bildschirmen untereinander |

Die gespeicherten alten Protokolle bleiben unverändert. Die Anzeige bereitet sie neu auf. Historische Lager-, Prüfplan- und Kalibrierungseinträge werden direkt aus ihren bestehenden Journalen gelesen. Bei älteren Kalibrierungen wurde kein Benutzer gespeichert; die Anzeige benennt das ausdrücklich. Für frühere Aktionen ohne gespeicherten Protokolleintrag lassen sich Zeitpunkt, Benutzer und vorherige Werte nicht zuverlässig rekonstruieren. Ergänzte Schreiber erfassen diese Änderungen ab Installation des Patches.

Lesende Aufrufe erzeugen keine neuen Einträge. Die bestehenden Projektberechtigungen bleiben erhalten; Lagerjournal und Qualitätsjournale benötigen zusätzlich die entsprechenden Leserechte. Es werden keine Passwörter, Passwort-Hashes oder Zugangstoken im Aktivitätsprotokoll ausgegeben.

## Verifikation

24 unterschiedliche isolierte Regressionstestskripte erfolgreich ausgeführt. Dazu gehören Projekte und Projektgründe, Fehlerkatalog inklusive Bearbeitung/Löschung, Musterungen, Artikelhistorie, Kunden, Stammdatenansichten und Excel, Planung, Zeitkorrekturen, Auftragsabschluss, Einstellberichte, Prüfpläne, Lager und Zugriffsrechte.

Der neue Test `scripts/test_activity_review.py` prüft zusätzlich die Datenformate aus den Screenshots, lesbare Überschriften, verschachtelte und einzelne Werte, 0/Nein/Leerwerte, HTML-Escaping, geschützte Angaben, historische Journale, Kalibrierungs-Deduplizierung, Dateiaktionen, Auftragslöschung, Kalender-, Benutzer-, Rollen- und Importprotokolle sowie Transaktions-Rollback. Die HTML-Ausgabe wird durch echte Flask-Anfragen geprüft. Eine grafische Prüfung auf dem konkreten Android-Gerät wurde nicht durchgeführt.

Zwei veraltete Test-Fixtures wurden an den bestehenden Zugriffsschutz angepasst: Maschinenbuchungen werden vom Projekt-Stopp-Endpunkt abgewiesen; Kundentests verwenden eine aktive Adminrolle, Sitzungsschlüssel und Formular-Token. Der Zugriffsschutz der Anwendung wird dabei nicht abgeschwächt.

Optionaler gezielter Test mit der FactoryOS-Python-Umgebung:

```bash
./venv/bin/python scripts/test_activity_review.py
```

Falls die Umgebung `.venv` heißt, entsprechend `./.venv/bin/python` verwenden. Der Test nutzt synthetische Datenbanken und keine Produktionsdaten.
