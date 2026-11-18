# Laufzeitüberschreitung in Timeline und Auftragsstatistik

Basis: spiefer87-del/FactoryOS, main,
Commit b2e0646138d57f085de74a44a1bc742d95c44a2b.

Das ZIP enthält die vollständigen geänderten und neuen Dateien mit ihren
Repository-Pfaden. ZIP entpacken und die enthaltenen Dateien im Stammverzeichnis
des GitHub-Repositorys übernehmen (Ordnerstruktur beibehalten), dann committen.
Die bestehenden Dateien werden ersetzt. Keine Datenbankmigration erforderlich.

## Verhalten

- Die Timeline laufender Aufträge trennt den gebuchten Abschnitt innerhalb der
  Soll-Laufzeit vom rot schraffierten Abschnitt danach. Eine gestrichelte
  Soll-Grenze kennzeichnet den Zeitpunkt, zu dem das gesamte Laufzeitbudget
  innerhalb der Produktionsbuchungen aufgebraucht wurde.
- Die Maschinenzeile zeigt die aktuelle absolute Überschreitungsdauer und die
  Sollzeit einschließlich Datum/Uhrzeit der Grenze. Liegt diese außerhalb des
  sichtbaren Zeitfensters, steht dort ein Hinweis statt einer falschen Randmarkierung.
- Die Auftragsstatistik zeigt unter „Laufzeiten“ zuerst die Sollzeit, bei einer
  Abweichung direkt danach deren Dauer und Prozentwert. Es folgen Arbeitskalender-
  Produktionszeit und rechnerische Restlaufzeit. Brutto steht als letzte Karte
  in einer eigenen Zeile darunter, auch auf kleinen Bildschirmen.
- Laufende Aufträge erhalten keine vermeintliche Minderlaufzeit, solange sie
  noch nicht fertig sind. Bestehende schnellere/langsamere Abschlussvergleiche
  verwenden weiterhin die bestätigte Gut- und Ausschussmenge als Bezugsgröße.
- Bereits begründete Abweichungen behalten die aktuelle Daueranzeige.
- Berechnung aus gebuchter Produktionszeit im Arbeitskalender; Wochenenden,
  Kalenderausnahmen und Lücken zwischen Produktionsbuchungen zählen nicht dazu.
  Das ist keine gemessene Maschinenzykluszeit. Fehlende Kavitäten werden als
  vorläufige Berechnung kenntlich gemacht. Kein Erfinden von Mengenmeldungen,
  keine Änderung von Buchungen, Terminprognosen oder Begründungstoleranzen.
- Beispiel: 53 Std 48 Min Arbeitskalender-Produktion minus 43 Std 20 Min Soll
  ergibt +10 Std 28 Min; die Bruttolaufzeit ist dafür keine Berechnungsbasis.

## Raspberry Pi

Nach dem Hochladen und Committen auf GitHub:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Anschließend Timeline bzw. Auftragsseite neu laden. Die geänderten Stylesheets
werden dort mit einer neuen Versionskennung angefordert.

## Prüfung

Mit isolierten SQLite-Testdatenbanken geprüft:

```bash
python scripts/test_runtime_overrun.py
python scripts/test_order_statistics.py
python scripts/test_production_deviations.py
python scripts/test_timeline_ranges.py
python scripts/test_order_planning.py
python scripts/test_planning_chain.py
python scripts/test_order_planning_concurrency.py
```

Der neue Test prüft Wochenend-/Feiertagsgrenzen, Buchungslücken und Überlappungen,
die Screenshot-Beispielrechnung, Gleichstand/Überschreitung/Minderlaufzeit,
begründete Abweichungen, fehlende Sollwerte und vorläufige Kavitäten,
Timeline-Aufteilung und Begrenzung sowie HTTP-Ausgabe und Kartenreihenfolge.
Zusätzlich wurde auf unveränderte Mengen-, Buchungs- und Auditdaten beim Lesen
geprüft. Ein grafischer Android-Browsertest war in dieser Umgebung nicht möglich.
