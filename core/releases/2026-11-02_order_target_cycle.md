# Soll-Zykluszeit am Auftrag und geordnete Artikelformulare

Basis: main 4bf2ad7. Vollständige Ersatzdateien und neue Dateien.

## Fachliche Änderungen

- Neue Fertigungsaufträge brauchen eine positive, endliche Soll-Zykluszeit in Sekunden pro Maschinenzyklus. Die Prüfung erfolgt im Formular UND auf dem Server.
- Beim Bearbeiten eines Fertigungsauftrags ist der Sollwert ebenfalls erforderlich. Ein fehlerhafter Wert speichert keine Teiländerung.
- Der Auftrag erhält einen eigenen gespeicherten Sollwert (orders.cycle_time_s). Spätere Artikeländerungen ändern den Auftrag nicht automatisch.
- Ein Artikelwert kann bei Artikelauswahl vorgeschlagen werden. Manuelle oder bereits gespeicherte Auftragswerte bleiben erhalten. Artikelstammdaten werden dadurch nicht geändert.
- Im ERP-Import wird eine vorhandene Zykluszeitspalte erkannt. Fehlt sie, dient ein gültiger, eindeutig zugeordneter Artikelwert als Vorschlag. Ohne gültigen Sollwert keine verbindliche Übernahme.
- Musterungsaufträge haben ein Pflichtfeld Soll-Zykluszeit im Auftragskopf. Die gemessene Ist-Zykluszeit bleibt separat und wird nicht aus dem Sollwert ausgefüllt.
- Die Soll-Zykluszeit ist in Musterungsdetail, PDF und Druckansicht sichtbar. Für den Abschluss offener Musterungen muss sie vorhanden sein.
- Der Projektbereich (nicht stückbezogene Projektarbeit) wird nicht künstlich zu einer Zykluszeit gezwungen.

## Laufzeit und Produktionskalender

Die Timeline verwendet zuerst den gespeicherten Auftragssollwert.
Restmenge ist Sollstückzahl minus gebuchte Gutteile.

Restzyklen = aufrunden(Reststückzahl / Werkzeugkavitäten).
Reine Restlaufzeit = Restzyklen × Soll-Zykluszeit.

Vorhandene Werkzeugkavitäten werden berücksichtigt. Fehlen sie oder sind sie ungültig,
wird 1 Teil je Zyklus angenommen und diese Annahme ausdrücklich angezeigt.
Fehlt am Auftrag eine Werkzeugnummer, kann eine eindeutige Artikel-Werkzeugzuordnung
verwendet werden; diese Quelle wird ebenfalls angezeigt. Bei mehreren zugeordneten
Werkzeugen wird keines still ausgewählt.
Die Werkzeugkavitäten stammen aus dem Werkzeugstamm und sind keine gesondert
gespeicherte Vorgabe für aktivierte/deaktivierte Nester.

Wochenenden, Feiertage und Brückentage berücksichtigt weiterhin der bestehende
Produktionskalender. Rüst-, Störungs-, Prüfzeiten, zukünftiger Ausschuss oder
abweichende aktive Nester sind nicht vorweggenommen. Bei Musterungen ist dies nur
eine Prognose der reinen Zykluslaufzeit, nicht der gesamten QS-Bearbeitungsdauer.

Altaufträge ohne eigenen Sollwert werden nicht rückwirkend mit erfundenen Werten
gefüllt. Für sie kann ein gültiger Artikelwert als ausdrücklich gekennzeichnete
Ersatzprognose dienen. Den Auftrag bitte bearbeiten und einen geprüften Sollwert
hinterlegen. Ohne beide Angaben gibt es keine Prognose. Bereits abgeschlossene
Musterungen bleiben unverändert und schreibgeschützt.

## Artikelformulare

Nur die Anordnung wurde verändert, keine Artikel-Pflichtfelder oder Fachlogik:

1. Artikelnummer und Artikelname.
2. Werkzeuge.
3. Rohstoff und Kunde.
4. Farbbatch und Prozentzugabe.
5. Zeichnungsdaten sowie weitere bestehende Angaben.

IDs, Feldnamen, optionale Zuordnungen, Mehrfach-Werkzeugauswahl und Suchhilfen bleiben erhalten.

## Datenbank und Installation

Nur eine zusätzliche nullable FLOAT-Spalte in orders. Kein Umbau bestehender
Tabellen und kein automatisches Umschreiben historischer Aufträge/Artikel.
Die technische NULL-Zulässigkeit erhält Altaufträge und Projektaufträge; neue
Fertigungs-/Musterungsaufträge sind serverseitig pflichtgeprüft.

Die Dateien aus der ZIP unter denselben relativen Pfaden in GitHub übernehmen und committen.
Danach:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_cycle_time.sh
```

Der Installer sucht die bekannte Python-Umgebung, prüft die Struktur, stoppt
FactoryOS, sichert instance/factoryos.db einschließlich vorhandener WAL-/SHM-Dateien
und ergänzt die Spalte. Bei Fehlern bleibt der Dienst gestoppt, damit die Ursache
zuerst geprüft werden kann. Das Upgrade ist wiederholbar.

Keine neue APK nötig. Danach in der App Neu laden wählen.
Keine Rechte- oder DuckDNS-/Tailscale-Änderung.

## Prüfung

- scripts/test_cycle_time.py: leere/ungültige/positive Werte, reguläre Formulare, unabhängige Soll-/Ist-Werte, ERP-Pflichtprüfung, historische DB-Erhaltung, Feldreihenfolge sowie Kavitäten/Rundung und Kalenderausnahmen.
- scripts/test_order_cycle.js und scripts/test_sampling_autofill.js: Vorschläge ohne Überschreiben manueller oder gespeicherter Werte.
- scripts/test_order_import.py: ERP-Assistent einschließlich Pflichtzykluszeit.
- scripts/test_sampling_orders.py / test_sampling_autofill.py / test_sampling_pdf.py: vorhandene Musterungsregressionen mit gültigen Sollvorgaben.
- scripts/test_access_control.py: bestehende Berechtigungsregressionen.
- Musterungs-PDFs wurden erstellt und die geänderte Kopfsektion visuell geprüft.

Alle Datenbanktests mit isoliertem SQLite-Testbestand, nicht mit der Raspberry-Datenbank.
Keine echte Android-/Browser-Layoutprüfung möglich.
