# Materialstammdaten: Materialsack fotografieren und Vorschläge prüfen

Basis: main e3c33d4. Vollständige geänderte/neue Dateien in Originalpfaden.

## Ablauf

Stammdaten → Materialien → „Materialsack erkennen“ oder „Material anlegen“.
Oben „Foto aufnehmen“ (Rückkamera angefragt) oder vorhandenes Foto auswählen.
Etikett nah, gerade, scharf und ohne Spiegelung fotografieren.

1. Foto wird lokal auf dem FactoryOS-Server mit Tesseract ausgelesen.
2. Erkannten Text und Feldvorschläge prüfen/korrigieren.
3. Gewünschte Felder markieren und ausdrücklich ins normale Formular übernehmen.
4. Interne Materialnummer und fehlende Pflichtangaben selbst ergänzen.
5. Erst „Material anlegen“ speichert den Materialstamm über den bestehenden Weg.

Kein automatischer Stammdatensatz und keine Aktualisierung bestehender Materialien.
Unsichere Vermutungen sind gelb und nicht vorausgewählt. Das OCR-Lesbarkeitsmaß
ist keine fachliche Konfidenz über ein Material. Bei niedriger Lesbarkeit sind
alle Vorschläge zunächst abzuwählen bzw. bewusst neu zu wählen. Fehlende oder
widersprüchliche Angaben bleiben offen. Text kann manuell korrigiert und erneut
regelbasiert ausgewertet werden, ohne ein weiteres Foto hochzuladen.

## Erkannte Angaben

Konservative Regeln für explizite Etikettfelder: Handelsname/Produkt/Grade,
Hersteller, externe Materialnummer, Kunststoffart, Materialkategorie, Farbe,
Farbnummer, RAL und Lieferform. Ein Herstellername ohne ausdrückliche Beschriftung
wird nur als unbestätigter Vorschlag aus dem sichtbaren Aufdruck angeboten.
Es gibt keinen Online-Produktkatalog und keine Ableitung technischer Daten aus
Markennamen. PC/ABS und PA 6.6 werden gesondert behandelt; mehrere Kunststoffarten
oder Kategorien werden nicht still auf eine reduziert. Masterbatch wird nicht
als Hauptkunststoff eingeordnet, nur weil eine Trägerpolymer-Angabe aufgedruckt ist.

Charge/Los, Sackgewicht, Dosierraten, interne Materialnummer, Bestände,
Verarbeitungstemperaturen, Sicherheits-/Gefahrstoffbewertung und feste
Lieferantenverknüpfungen werden nicht automatisch gesetzt. Insbesondere bedeutet
„25 kg“ nicht Mindestbestand oder Materialidentität. Sicherheitsdatenblatt und
Gefahrstoffstatus bleiben manuell zu prüfen. Vorhandene Materialien mit gleichem
externem Code oder gleicher Bezeichnung werden als mögliche Dubletten angezeigt;
keine automatische Zusammenführung. Details nur mit materials.view.

OCR ist keine Garantie: zerknitterte, spiegelnde, schräg/seitlich fotografierte,
unbeschriftete oder schlecht gedruckte Säcke können Nacharbeit erfordern.
Für zuverlässige Stammdaten müssen Menschen Etikett und Vorschläge abgleichen.

## Kamera / Datenschutz / Technik

- Kamera-Dateieingabe mit capture=environment; alternative Fotoauswahl.
- Kamera hängt von Browser-/Android-/WebView-Berechtigung und dessen Datei-/
  Kameraunterstützung ab. Die vorhandene APK wird hier nicht verändert. Falls
  sie keine Kamera freigibt: Foto auswählen oder dieselbe FactoryOS-Seite im
  Smartphone-Browser verwenden; eine APK-Anpassung wäre ein separater Schritt.
- Kein Cloud-KI-Dienst, API-Schlüssel, externes Bild-Upload oder laufende OCR-Kosten.
- JPEG/PNG/WebP, maximal 10 MB und 24 MP. HEIC/PDF/SVG/Animationen werden abgewiesen.
- Foto wird im Speicher geprüft, EXIF-orientiert, auf maximal 2400 Pixel Kantenlänge
  reduziert und ohne EXIF/GPS als temporäres OCR-Bild verarbeitet.
- Temporäre Dateien werden bei normaler Abwicklung und abgefangenen Fehlern entfernt;
  bei abruptem Prozess-/Systemabbruch können Betriebssystem-Tempdateien bis zu dessen
  Bereinigung verbleiben. Kein Bild-/Textarchiv und
  keine Rohtext-Protokollierung. Das Browser-Vorschaubild bleibt nur bis Seitenwechsel.
- Eine serverweite OCR-Sperre begrenzt parallele Arbeit über Gunicorn-Worker hinweg.
  Zeitlimits, Größenlimits und ein begrenzter zweiter Erkennungsversuch verhindern
  unbeschränkte Verarbeitung. Bei belegter Erkennung: 429 und manuell erneut versuchen.
- Alle Erkennungs-/Text-Endpunkte benötigen materials.create und CSRF.
- Kein Shell-Aufruf aus OCR-Text, keine Bild-URLs/Downloads und kein Prompt-/Tool-Aufruf.
- Materialanlage prüft jetzt ebenfalls CSRF und erhält vorausgefüllte Angaben bei
  Validierungsfehlern. Dokumentenfelder bleiben bei einer fehlgeschlagenen Anlage sichtbar.

## Installation

Nach Übernahme der ZIP-Dateien in GitHub:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_material_scan.sh
```

Installer erkennt die vorhandene Python-venv und prüft das bereits in requirements.txt
vorhandene Pillow. Er installiert bei Bedarf ausschließlich die lokalen Debian-
Pakete tesseract-ocr, tesseract-ocr-deu und tesseract-ocr-eng (Internet und sudo für
die erstmalige Paketinstallation erforderlich). Kein allgemeines System-Upgrade.
Anschließend Syntaxprüfung/Dienstneustart. Kein Datenbank-Schemawechsel und keine
Änderung bestehender Stammdaten durch den Installer.

Erster Gerätetest: Materialanlage neu laden, Kamera-/Dateiberechtigung erteilen,
ein gut lesbares reales Sacketikett fotografieren, Vorschläge mit Aufdruck
vergleichen, mögliche Dublette prüfen und erst dann einen neuen Stamm speichern.
Es wurde keine echte Kamera/WebView oder ein produktiver Materialsack getestet.

## Prüfung und Referenzen

Isolierte SQLite-Tests mit tatsächlichem lokalem Tesseract auf einem synthetisch
erzeugten Etikett: Texterkennung, Feldzuordnung, Polymer-/Kategorie-Konflikte,
Masterbatch, Charge/Gewicht-Abgrenzung, explizite Übernahme, keine DB-Schreibzugriffe
durch Erkennung, Dubletten, CSRF/Rechte, Größen-/Formatlimits, Sperre, Timeouts,
Dateibereinigung und Formularerhalt. Keine produktive Datenbank verwendet.
JavaScript-/Python-/Shell-Syntax und ZIP-Integrität geprüft; keine visuelle
Browser-/Handy-Abnahme behauptet.

Primärdokumentation:
- https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html (TSV-Ausgabe)
- https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html (Bildqualität/PSM)
- https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/file (capture/Kamera)
