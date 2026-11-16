# Werkzeug-Einstellberichte: Wizard, Handeingabe und lokale Foto-Ausfüllhilfe

Basis: main d34c8fe. Das ZIP enthält vollständige neue/geänderte Dateien mit
Originalpfaden, keinen Git-Diff. Die Excel-Vorlage wird nicht verändert und es
werden keine Excel-Makros ausgeführt. Keine Änderung an DuckDNS, Tailscale oder APK.

## Einstieg und Ablauf

Werkzeug-Detailseite -> **Einstellberichte / Wizard** -> **Einstellbericht beginnen**.

1. Werkzeug, Maschine, Artikel und Rohstoff/Farbbatch zuordnen.
2. Spritzparameter und Spritz-/Nachdruckprofile erfassen.
3. Werkzeugbewegungen, Werkzeugschutz, Auswerfer und Kernzüge erfassen.
4. Zylindertemperaturen, Heißkanal und Werkzeugtemperierung/Kühlanschlüsse erfassen.
5. Rohstoff, Farbe, Batchanteil, Trocknung und Gewichte prüfen.
6. Betriebsart, Entnahme, Verpackung, Bemerkungen, Datum und Einrichter ergänzen.
7. Offene Punkte gezielt anspringen, prüfen und abschließen.

Jeder Parameterbereich bietet Handeingabe und Foto-Erkennung. Fotos sind niemals
Pflicht. Zahlen werden ohne Einheit eingegeben; Dezimalkomma wird akzeptiert.
Profile besitzen explizite Reihenfolge, Stufen-/Zonenbezeichnungen, Einheiten und
Aktivierung. Auch nicht erkannte Steuerungen sind vollständig manuell erfassbar.
Auf kleinen Bildschirmen bleiben Profilspalten breit und sind seitlich scrollbar.

**Schnell erfassen:** Ausgefüllte Einzelwerte eines Schritts können nach bewusster
Prüfung gemeinsam bestätigt werden. Leere optionale Felder und leere Profile
können mit gemeinsamer ausdrücklicher Begründung als nicht zutreffend markiert
werden. Kernangaben (Werkzeug, Maschine, Artikel, Rohstoff, Sollzyklus, Datum,
Einrichter) bleiben erforderlich. Profile müssen zusätzlich ausdrücklich geprüft
werden. Leer ist nicht null; ausgegraute Stufen sind nicht automatisch aktiv.

## Stammdaten und Bestätigung

- Genau ein am Werkzeug hinterlegter Artikel wird, bei Leserecht, vorgeschlagen;
  mehrere Artikel werden nicht automatisch ausgewählt. Maschine bewusst auswählen.
- Artikelname/-nummer, Kunde, Zeichnung/Index, Rohstoff, Hersteller,
  Werkstoffgruppe, Farbe, Farbbatch/RAL/Anteil, Schussgewicht, Sollzyklus sowie
  Werkzeug-/Maschinendaten werden aus vorhandenen Stammdaten vorgeschlagen.
- Sämtliche Vorschläge bleiben unbestätigt. Trocknung ist als Materialvorgabe
  gekennzeichnet und kein Nachweis der tatsächlichen Verwendung. Maschinen-
  Kapazitätsdaten werden nicht als tatsächliche Schließkraft/Spritzdruck übernommen.
- Zuordnung ändern -> Vorschläge laden -> erneut bestätigen. Ein signierter
  Zuordnungsstand bindet die Vorschau an Benutzer, Werkzeug-Bericht und ausgewählte
  Datensatz-IDs. Geänderte Zuordnungen ohne neuen Abgleich werden nicht gespeichert.
  Ein Wechsel setzt in der Oberfläche sämtliche Prüfbestätigungen zurück.
- Bei fehlenden Stammdaten führen berechtigungsabhängige Links zu den normalen
  Anlageformularen für Maschine, Artikel, Kunde, Rohstoff/Farbbatch oder Werkzeug-
  Bearbeitung. Entwurf vorher speichern; Formulare öffnen sich separat. Neue
  Artikel müssen dem Werkzeug zugeordnet werden. Anschließend Vorschläge laden,
  neue Zuordnung auswählen und nochmals abgleichen. Keine automatische Neuanlage.
- Ohne Stammdaten-Leserecht stehen keine kompletten Auswahllisten zur Verfügung.
  Berechtigte Person hinzuziehen. Die Einstellungen schreiben keine Stammdaten um.

## Foto-Erkennung: bewusst begrenzter erster Stand

Lokales Tesseract mit positionsbezogenen OCR-Wörtern und zwei Layoutversuchen.
Die bestehende Engine-Auflösung, Bildvalidierung und Cross-Worker-Sperre werden
wiederverwendet. OpenCV (bereits in requirements.txt) kann den hellen Bildschirm
erkennen und den Bildausschnitt verbessern; ohne OpenCV bleibt die OCR verfügbar.
Es gibt keinen neuen Cloud-Dienst und keinen API-Schlüssel.

Das erste Zuordnungsprofil ist **Sumitomo Demag NC5**:

- Temperaturansicht: nur eindeutig beschriftete Zonen und unterscheidbare
  Soll-/Ist-Zeilen werden zugeordnet. Fehlende Zonen, Toleranzen und Aktivierungen
  müssen manuell ergänzt werden. Eine erkannte Teilmenge ist kein vollständiger
  Zylinderplan. Unbekannte oder widersprüchliche Temperaturblöcke werden verworfen.
- Prozessoptimierung: einzelne eindeutig lokalisierte Einstellfelder können als
  Vorschlag erscheinen. Nicht sämtliche Werte und Profile werden bereits erkannt.
- Werkzeug- und Auswerferseiten werden erkannt, ihre Stufen werden in diesem
  ersten Stand manuell zugeordnet. Vollautomatische Erkennung inaktiver Felder,
  Kernzugabläufe und vollständiger Bewegungsprofile ist nicht enthalten.
- PDE-Statistik wird nicht in Sollwerte umgedeutet. Messzyklen ersetzen keine
  Soll-Zykluszeit. Blaue Messfelder werden nicht als graue Einstellfelder zugeordnet.
- Unbekannte Steuerungen: erkannter Text und Foto dienen als Eingabehilfe;
  keine Anwendung der NC5-Regeln und keine erfundene automatische Zuordnung.

Pro Bericht maximal 12 Fotos, maximal 10 MB / 24 MP je Eingangsfoto. Einzelne
Aufnahmen nacheinander auslesen (jeweils zuvor Entwurf speichern). OCR-Läufe
maximal 10 + 8 Sekunden, Engine-Prüfung maximal 3 Sekunden, ein OCR-Thread.
Vorschläge werden angezeigt, aber überschreiben weder Werte noch Profile.
Erst die bewusste Übernahme ersetzt vorhandene Daten mit zusätzlicher Rückfrage.
Danach sind diese Werte erneut zu prüfen. Quellfotos bleiben nachvollziehbar.

Auf den bereitgestellten echten NC5-Fotos wurden die Seiten und teilweise Werte
erkannt; **keine zuverlässige vollständige Zahlenextraktion**. Kleine Schrift,
Moiré, Glanz und Tabellenlinien begrenzen lokale OCR. Fehlende Zahlen bleiben
offen. Für weitere Steuerungen sind zusätzliche Profile und reale Testfotos
erforderlich. Nicht als bereits vollautomatischen Einstellbericht verwenden.

## Datenhaltung und Historie

Drei zusätzliche Tabellen: setup_reports, setup_report_revisions und
setup_report_photos. Hauptzuordnung ist die Werkzeug-ID, zusätzlich werden die
Maschinen-/Artikel-/Materialzuordnungen und der jeweilige Stammdatenstand als
Snapshot gespeichert. Umbenennen des Werkzeugs löst die Historie nicht ab.
Werkzeuge mit Berichten können nicht mehr über die Werkzeug-Löschroute entfernt
werden. Stattdessen Status ändern.

Normalisierte JPEG-Bildschirmfotos ohne Metadaten werden privat in der SQLite-
Datenbank gespeichert, nicht unter einer öffentlichen Static-/Storage-URL.
Damit umfasst das Datenbank-Backup auch die Fotos. Bis zu 3 MB je gespeichertes
Foto; Datenbankgröße und Backupkapazität entsprechend einplanen. Lokale OCR-
Zwischendateien werden entfernt. Es erfolgt kein Cloud-Upload.

Jeder gespeicherte Stand erzeugt einen unveränderlichen Snapshot und einen
Werkzeug-Protokolleintrag. Optimistische Versionssperre schützt vor Überschreiben
gleichzeitiger Änderungen. Entwürfe dürfen Lücken haben. Abschluss benötigt
Prüfstatus aller Felder/Profile, Pflichtangaben und widerspruchsfreie Zuordnungen.
Abgeschlossene Berichte bleiben gesperrt. „Neue Fassung als Vorlage“ erstellt
einen neuen Bericht und setzt alle Bestätigungen zurück; alte Stände bleiben
lesbar. Neue Fassung kopiert keine Fotos, verweist aber auf den Vorgänger.

Der Abschluss ist eine Dokumentationsprüfung, keine elektrische Maschinen-
Freigabe, Sicherheitsfreigabe oder automatische Prozessoptimierung.

PDF-Ausgabe ist ein neu aufgebauter moderner FB-18-Bericht, keine pixelgenaue
Excel-Kopie. Quellen, Einheiten, Prüfstatus, begründete Ausnahmen und Entwurfsstatus
bleiben sichtbar. Das PDF kann über den PDF-Viewer manuell gedruckt werden.

## Rechte

Neue Rechte unter „Werkzeug-Einstellberichte“: Ansehen, Anlegen, Bearbeiten,
Geprüft abschließen, PDF/Export. Systemadministration hat wie bisher Zugriff.
Andere Rollen erhalten **keine** zusätzlichen Rechte automatisch.

Für normale Nutzer im Adminbereich bewusst vergeben:

- setup_reports.view + create + edit für den Wizard;
- setup_reports.release zusätzlich für geprüften Abschluss;
- setup_reports.pdf_export für PDF und Ausdruck;
- tools.view, articles.view, machines.view, materials.view für zugehörige
  Stammdatenseiten und verfügbare Auswahllisten;
- zusätzliche create/edit-Rechte nur soweit Stammdatenpflege gewünscht ist.

Serverseitige Rechteprüfung, CSRF und signierter Zuordnungsstand gelten auch für
direkte Aufrufe. Foto- und Historien-IDs werden immer zum Werkzeug und Bericht
aufgelöst. Fotos/PDFs werden privat und ohne Browsercache ausgeliefert.

## Installation

Nach Übernahme aller ZIP-Dateien mit unveränderten Ordnerpfaden nach GitHub:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_setup_reports.sh
```

Der Installer prüft zuerst die Struktur, stoppt den Dienst, sichert die vorhandene
SQLite-Datei einschließlich WAL/SHM unter /home/factoryos/backups, legt nur neue
Tabellen/Rechte an und startet den Dienst wieder. Bei Upgradefehler bleibt der
Dienst zur Prüfung gestoppt. Bestehende Stammdaten und Rollenrechte unverändert.
Die Foto-Auswertung braucht die bereits installierte Tesseract-Umgebung; fehlt
sie, bleibt die vollständige Handeingabe nutzbar. Kein zusätzliches APK nötig.

## Tests und Grenzen

- Isolierte SQLite-Tests: Upgrade doppelt, Stammdaten nur Vorschläge, ungültige
  Zahlen, Entwurf/Abschluss, Konflikte, unveränderliche Historie, Vorlagen ohne
  Bestätigungen, Foto-Quellen, kein automatisches Überschreiben, Querverweise,
  Leserechte, PDF-Rechte, CSRF, gesperrte Abschlüsse und Werkzeug-Löschschutz.
- NC5-Parser mit synthetischen Positionsdaten: Soll/Ist getrennt (EF 65/66),
  unbekannte Steuerung und Statistik ohne erfundene Sollwerte.
- Echte lokale OCR auf generiertem Foto und Probeauswertung der fünf gelieferten
  Maschinenfotos. Testumgebung hat nur englisches OCR-Sprachpaket; Raspberry-
  Lauf und deutsche OCR müssen vor Ort geprüft werden.
- JavaScript-Logik mit DOM-Stubs: Schrittwechsel, schnelle Handeingabe,
  Speichern/Weiterbearbeiten, Foto-Vorschläge ohne automatische Übernahme,
  bewusste Übernahme und offene Stufenaktivierung.
- Bestehende Rechte- und Beschriftungstests erfolgreich. PDF erstellt, gerendert
  und optisch geprüft. Keine Browser-/Android-Kamerafreigabeprüfung: lokaler
  Chromium-Start wurde durch die Ausführungsumgebung blockiert. Vor Ort auf
  Smartphone und Desktop testen, besonders Tastatur, Profilscrollen und Kamera.

Testbefehle (nur mit isolierter Testumgebung; niemals auf die Produktiv-DB zeigen):

```bash
python scripts/test_setup_reports.py
node scripts/test_setup_reports_ui.cjs
```
