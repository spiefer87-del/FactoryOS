# ERP-Auftragsimport mit Prüf- und Zuordnungsassistent

Basis: main 62bc6c1. Die ZIP enthält vollständige Ersatzdateien und neue Dateien.

## Geprüfte Vorlage

Browse_02112026142814.xlsx enthält einen Auftrag in Tabelle1, 36 Spalten:
FA-Nummer 261742, Artikel 103010227, Menge 2000 Stück, Kunde 10301,
Werkzeug COR150 und Material 00000004. Liefertermin fehlt; Liefer-KW ist 44/26.
ERP-Auftragsart ist 0, ERP-Status 1. Diese Codes sind fachlich nicht dokumentiert
und werden deshalb nicht automatisch in FactoryOS-Status übersetzt.

Die Datei wird nur gelesen. Alle 36 Spalten bleiben als auftragsbezogene Quellangaben erhalten.
Das Excel-Escape _x000D_ wird für die Anzeige bereinigt; Textabsätze bleiben erhalten.
Die Originaldatei wird weder verändert noch im Repository mitgeliefert.

## Ablauf

1. Aufträge > ERP-Aufträge importieren: XLSX hochladen.
2. Eigene Vorschau öffnen und eine Auftragszeile prüfen.
3. Erkannte Nummern werden exakt zugeordnet. Ähnliche Treffer bleiben Vorschläge.
4. Fehlende Kunden, Artikel, Werkzeuge, Materialien oder Maschinen können mit Nummer
   und Bezeichnung nach ausdrücklicher Auswahl neu angelegt werden.
5. Fehler korrigieren und Vorschau prüfen. Erst danach die einzelne Zeile verbindlich übernehmen.
6. Der Assistent führt zur nächsten offenen Zeile. Zeilen können ohne Änderungen übersprungen werden.

Der Upload selbst erzeugt nur einen eigenen Importentwurf, keine Aufträge/Stammdaten.
Entwürfe sind sieben Tage bearbeitbar; ältere Entwürfe werden nicht automatisch gelöscht.
Es gibt in dieser ersten Version keine ungeprüfte Sammelübernahme.

## Zuordnung und Schutzregeln

| ERP-Angabe | Behandlung |
| --- | --- |
| FA-Nummer | Eindeutige FactoryOS-Auftragsnummer, kein stilles Überschreiben |
| Artikelnummer/Bezeichnung | Artikelstamm prüfen; für den Auftrag Nummer und Stammdatenbezeichnung übernehmen |
| Fertigungsmenge/Mengeneinheit | Positive ganze Stückzahl; keine kg-/Stück-Umrechnung |
| Kunde/Werkzeug/Material/Maschine | Exakte Nummer oder bewusste Auswahl; historische Zuordnung am Auftrag speichern |
| Materialtext und Lieferhinweise | Vollständig in ERP-Originalangaben am Auftrag erhalten |
| Liefertermin/Liefer-KW | Getrennte Angaben; keine Erfindung eines Tagesdatums oder einer Maschinenbuchung |
| Auftragsart/Status | Originalcodes erhalten, manuelle Bestätigung als Fertigungsauftrag erforderlich |
| Lieferanten, Abschnitt/Position, Start/Ende, Produktionsreihenfolge usw. | Als Quellangaben erhalten, nicht still in andere Felder umdeuten |

Bei fehlenden Quellangaben zu Kunde, Material oder eindeutigem Werkzeug können
vorhandene Artikelstammdaten vorausgefüllt werden. ERP-Werte werden dabei nicht überschrieben.

Bestehende Stammdaten bleiben immer unverändert. Nur ein NEU angelegter Artikel
erhält die gewählten Kunden-, Material- und Werkzeugbezüge. Eine abweichende
Zuordnung zu einem vorhandenen Artikel gilt nur für den Auftrag und wird angezeigt.
Neuanlagen enthalten nur die geprüften Nummern/Bezeichnungen plus gewählte
Material-/Maschinenkategorie; weitere technische Daten müssen anschließend gepflegt werden.

Vorhandene Aufträge benötigen eine ausdrückliche Aktualisierungsentscheidung.
Nur offene, ungebuchte Fertigungsaufträge dürfen geändert werden.
Musterungs-/Projektaufträge, laufende/abgeschlossene/gesperrte Aufträge sowie
Aufträge mit Zeit- oder Mengenbuchungen bleiben geschützt.
Mehrere Positionen mit derselben FA-Nummer werden NICHT automatisch zusammengefasst.
Die doppelten Zeilen müssen fachlich geklärt oder bewusst übersprungen werden.

Keine automatische Material- oder Werkzeugfreigabe aus ERP-Statuscodes.
Keine automatische Produktionsbuchung. Neue Aufträge erhalten FactoryOS-Status open.
Vorhandene Status-, Beschreibungs- und Standortfelder werden beim Importupdate nicht zurückgesetzt.

## Datenbank und Rechte

- Zwei neue Tabellen: erp_order_import_batches und erp_order_data.
- Keine bestehenden Auftrags- oder Stammdatentabellen werden umgebaut.
- Bestehende Auftragsfelder article, article_name, tool_no und target_qty bleiben kompatibel.
- Ergänzende Zuordnungen sind historische auftragsbezogene Referenzen/Snapshots,
  keine neue globale Stammdaten-Fremdschlüsselstruktur.
- Neuer Import und frühere ERP-Importstände bleiben am Auftrag lesbar.
- Neues Recht orders.excel_import: in der Rechteverwaltung bei Bedarf zuweisen.
- Zusätzlich gelten orders.create bzw. orders.edit und die jeweiligen Stammdaten-Lese-/Anlagerechte.
- Bestehende Rollenzuweisungen bleiben unverändert. Systemadministration hat den vorhandenen Vollzugriff.
- Entwürfe sind nur für ihren Besitzer sichtbar, nicht global freigegeben.
- Alle Import-POSTs sind CSRF-geschützt. Versionierung verhindert veraltete
  Bestätigungen aus einem zweiten Fenster.
- Änderungen an Stammdaten oder Rechten nach der Vorschau erzwingen eine neue Prüfung.
- Jede bestätigte Zeile ist eine Transaktion: bei Fehlern keine halben Stammdaten-/Auftragsanlagen.
- Upload maximal 5 MB, 500 Zeilen, 100 Spalten, 50 MB entpackt.
- Formeln/Excel-Fehler werden abgelehnt, nicht ausgeführt.
- Auftragsübersicht verwendet jetzt direktes HTML-Autoescaping statt ungeprüfter safe-Zellen.

## Installation auf dem Raspberry

Dateien mit denselben relativen Pfaden in GitHub übernehmen und committen.
Dann:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_order_import.sh
```

Der Installer sucht die bekannte Python-Umgebung, prüft die DB-Struktur,
stoppt FactoryOS, sichert instance/factoryos.db einschließlich vorhandener
WAL-/SHM-Dateien und ergänzt nur die beiden neuen Tabellen/das Importrecht.
Bei Fehlern bleibt der Dienst gestoppt, damit der Fehler zuerst geprüft werden kann.
Kein Zurückspielen der Sicherung ohne Prüfung der konkreten Ursache.

Anschließend Aufträge > ERP-Aufträge importieren öffnen.
Keine neue APK erforderlich. Die neue Funktion erscheint nach Neu laden.
Bei Fachrollen das neue Importrecht und erforderliche Stammdatenrechte bewusst zuweisen.

## Prüfung

scripts/test_order_import.py prüft den Parser, die Upload-/Prüf-/Übernahme-Routen,
leere/fehlerhafte Werte, CSRF, Benutzertrennung, Rechte, explizite Neuanlagen/Updates,
Transaktionsrollback, parallele Stammdatenänderungen, doppelte FA-Nummern, Mengen/
Einheiten, ungültige Termine, ERP-Snapshots, Historie und HTML-Escaping.
Der Test kann optional den Pfad einer Originaldatei erhalten.

Zusätzlich Sicherheitsregression scripts/test_access_control.py.
Prüfung auf isolierter SQLite-Datenbank, nicht gegen eure Raspberry-Datenbank.
Keine echte Android-/Browser-Layoutprüfung in dieser Umgebung.
