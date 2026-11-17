# Einmaliger Abschluss der Produktions-/Lagertestphase

**Nur für den ausdrücklich angeforderten Testreset verwenden. Kein normaler Installations-/Update-Schritt.** Vollständige Dateien mit Ordnerstruktur nach GitHub übernehmen. Danach:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_reset_production_warehouse_tests.sh
```

Dieser Befehl zeigt zuerst eine Vorschau, stoppt FactoryOS, erstellt eine geprüfte Datenbanksicherung und führt den Reset in einer Transaktion aus. Das verwendete App-Konto `admin` muss aktiv und Systemadministrator sein. Der Benutzer hat ausdrücklich bestätigt, dass alle Maschinen tatsächlich ohne Werkzeug starten sollen.

## Entfernt

- Alle bisherigen Zeitbuchungen und Rüst-/Abrüstvorgänge; alte Timeline-Aktivitäten und Maschinenplanungen.
- Alle Gut-/Ausschussmeldungen und Abschlussmengen, auch von erhaltenen offenen Aufträgen.
- Alle Lagerlose/-bestände, Übergaben, Reservierungen, Kommissionierungen und Lagerbewegungen einschließlich Test-Lagerjournal.
- Geschlossene Aufträge: Status finished/fertig/closed/geschlossen/abgeschlossen/completed/cancelled/canceled/storniert/beendet, Aufträge mit bestätigtem Abschluss sowie abgeschlossene Musterungsaufträge. Deren Musterungsprüfungen und ERP-Auftragssnapshots werden mit entfernt.
- Alte Maschinenbefehlsquittungen und Fortsetzungsreservierungen, damit Testbefehle keine alten Buchungen wiedergeben.

## Erhalten / neu begonnen

Offene Aufträge bleiben mit ihren Auftragsdaten unverändert, ebenso ihre ERP-Snapshots und Musterungsprüfungen. Ein Verweis einer offenen Nachmusterung auf eine entfernte abgeschlossene Vorgängermusterung wird gelöst und im Reset-Bericht vermerkt. Gesperrte, aber nicht abgeschlossene Aufträge werden nicht allein wegen einer Sperre gelöscht.

Artikel, Werkzeuge, Maschinen, Materialien, Kunden, Benutzer, Rollen/Rechte, persönliche Dashboards, Lagerplätze, Kalender, Prüfpläne, Einstellberichte, Fehlerkatalog und Fotos bleiben bestehen. Allgemeine Änderungsprotokolle bleiben erhalten. Es werden keine Mediendateien gelöscht.

Alle Maschinen erhalten einen bestätigten Bestand **abgerüstet / ohne Werkzeug**. Ab dem Reset-Zeitpunkt beginnt pro Maschine eine neue laufende FREI-Buchung. Die Timeline wird also nicht rückwirkend aufgefüllt. Bedien-/Planungs-/Lagersperrversionen werden erhöht, nicht auf null gesetzt. Vor der nächsten Produktion muss regulär gerüstet werden. Aktive/inaktive Maschinenstammdaten werden nicht umgestellt.

## Sicherung und Schutz

Die Sicherung liegt unter `/home/factoryos/backups/production_warehouse_test_reset_DATUM_UHRZEIT/factoryos.db`. SQLite-Backup berücksichtigt auch WAL-Inhalte; Integrität und vollständiger Inhalt werden vor der Löschung geprüft. Unbekannte Fremdbezüge, unerwartete Datenänderungen oder Fremdschlüsselprobleme stoppen den Reset. Die bekannten Unveränderlichkeitstrigger des Test-Lagerjournals werden ausschließlich innerhalb dieser Transaktion vorübergehend entfernt und exakt wiederhergestellt. Im normalen Lagerbetrieb bleiben sie aktiv.

Bei einem Fehler nach Dienststopp bleibt FactoryOS gestoppt und die Transaktion wird zurückgerollt. Fehlermeldung weitergeben, nicht unkontrolliert andere Reset-Befehle ausführen. Bei Erfolg protokolliert die Datenbank den Umfang und Sicherungspfad. Ein einmaliger Reset-Vermerk verhindert, dass eine Wiederholung später neu angelegte Daten erneut löscht.

Der Vorgang ist aus der vorherigen Datenbanksicherung wiederherstellbar, aber es gibt keinen automatischen Rückgängig-Button. Sobald neue produktive Buchungen vorliegen, darf eine alte Gesamtdatenbank nicht einfach darüberkopiert werden; eine Wiederherstellung muss dann gezielt erfolgen.

Nach dem Reset alle Browser/App-Seiten auf allen Geräten neu laden. Prüfen: Lagerbestände und Mengen null, geschlossene Aufträge verschwunden, offene Aufträge erhalten, Maschinen abgerüstet, neue Frei-Timeline ab Reset-Zeitpunkt. Das Paket selbst und ein bloßer Git-Pull führen keinen Reset aus; erst der oben genannte Installer startet ihn.
