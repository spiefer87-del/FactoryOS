# Einstellbericht: Übernahme, Prüfhaken, FB-18 und direkter Einstieg

Basis: main 30e4634. Voraussetzung: bereits installierter Einstellbericht-Wizard.
ZIP enthält vollständige neue/geänderte Dateien, keinen Git-Diff. Keine
Datenbankmigration, kein Cloud-Dienst, keine neuen Pakete oder API-Schlüssel.

## Korrektur der Übernahme

Foto-Vorschläge änderten bisher nur das JavaScript-Datenmodell; die sichtbaren
Felder und deren Eingabe-Listener blieben an einem alten Objekt hängen. Daher
fehlte die unmittelbare Anzeige und eine anschließende manuelle Eingabe konnte
am veralteten Objekt landen.

Jetzt werden Werte und Profile sofort sichtbar aktualisiert. Die Vorschlagskarte
meldet „Übernommen - noch unbestätigt“. Ein zusätzlicher Button führt direkt zum
betroffenen Feld bzw. Profil-Schritt. Scanner und andere Eingaben bleiben erhalten.
Handkorrekturen nach der Übernahme werden richtig gespeichert. Übernahme ist
weiterhin kein Speichern und keine fachliche Bestätigung; anschließend Entwurf
speichern. Vorhandene Werte werden nur nach ausdrücklicher Rückfrage ersetzt.

## Zahlenerkennung

Die frühere Filterung nach Wortmitte konnte bei einer zerlegten Zahl wie
„130.“ + „00“ nur den Suffix „00“ auswählen. Das ist keine gültige Grundlage
für einen Dosierpositions-Vorschlag.

- Ganzen Feld-Nachbarbereich prüfen, nicht nur das Wort unter der Spaltenmitte.
- Mehrere Zahlenfragmente bzw. ein unsicher gelesener Teil führen zur Ablehnung,
  nicht zum Zusammenkleben oder Raten fehlender Dezimalstellen/Ziffern.
- „00“, führend mit Nullen gepolsterte Fragmente und unvollständige Zahlen
  werden nicht übernommen. Dezimalkomma und vollständige Dezimalzahlen bleiben
  zulässig. Dosierposition 0 bzw. negativ wird nicht automatisch vorgeschlagen.
  Gültige Nullen bei anderen Parametern, etwa Pausenzeit, bleiben möglich.
- Einzelwerte müssen in beiden vorhandenen OCR-Layoutversuchen übereinstimmen.
  Bei Abweichung, nur einem verwertbaren Versuch oder unterschiedlichen Seiten
  erscheinen keine Einzelwert-Vorschläge. Keine Auswahl mehr nach „mehr Werte“.
- Auch gespeicherte alte unsichere Foto-Vorschläge werden bei der Übernahme
  serverseitig zurückgewiesen und bei der Abschluss-Prüfliste als offen angezeigt.

Dadurch können weniger Vorschläge erscheinen. Das verbessert die Rückhaltung
falscher Werte, ist aber keine Garantie für vollständige oder richtige OCR.
Auf dem ursprünglichen NC5-Prozessfoto blieb der Zahlenausschnitt auch nach
lokaler Auswertung uneindeutig; es wurde kein Ersatzwert erfunden. Temperaturen
und Profile bleiben im bisherigen konservativen Assistenzumfang. Das ist keine
automatische Prozessoptimierung und keine Maschinensteuerung.

**Schon gespeicherte falsche Werte werden nicht automatisch umgeschrieben.**
Alte Dosierposition „00“ im Entwurf bitte am Maschinenbild prüfen und manuell
korrigieren oder entfernen; danach speichern. Fotos und alte Stände bleiben
nachvollziehbar. Für neue Vorschläge Foto nach Installation erneut auslesen.

## Bestätigung ohne Status-Dropdown

Einzelwerte und ganze Profile erhalten die Haken „Geprüft“ und „Nicht zutreffend“
rechts unter dem Feld. Beide schließen sich gegenseitig aus. Nicht zutreffend
benötigt weiterhin eine Begründung. Leere Felder/Profile lassen sich nicht als
geprüft bestätigen. Änderungen an Wert, Einheit oder Profil setzen den Haken
wieder zurück. Die schnelle Sammelbestätigung ausgefüllter Werte bleibt erhalten.
Die für Zuordnungen, Einheiten und Stufenaktivierung benötigten Auswahlfelder
bleiben bestehen; der Prüfstatus selbst ist kein Dropdown mehr.

## PDF wie das bisherige FB-18

Erste Seite wieder A4 quer mit tabellarischem FB-18-Aufbau: Kunde/Artikel,
Maschinen- und Werkzeugdaten links, Werkstoff/Farbe/Trocknung/Kühlung mittig,
Zeichnung, Temperaturen, Zeiten, Drücke und Spritz-/Nachdruckprofile rechts.
Bemerkungsbereich mit Schreiblinien, Verpackung, Datum und Name sind unten links.
Es wird nur der Aufbau nachempfunden; Excel-Makros, veraltete Excel-Bezüge und
Logos werden nicht ausgeführt oder ausgedacht. Die Vorlage selbst bleibt unverändert.

Das kompakte Formblatt zeigt Solltemperaturen, nicht versehentlich deren Istwerte.
Offene Werte sind mit * markiert, begründete Ausnahmen mit n.z. Vollständige Texte,
weitere Zonen und mehr als vier Profilstufen sowie Quellen/Prüfstatus stehen in der
anschließenden ungekürzten Anlage (A4 hoch). Auf dem Deckblatt nötige Kürzungen
werden mit ... gekennzeichnet. Für das Formblatt allein Seite 1 drucken; für die
vollständige Dokumentation alle Seiten. Keine Daten werden durch Kürzung gelöscht.

## Neue Kachel

Stammdaten -> Werkzeuge -> **Einstellbericht starten**. Der Einstieg liegt unter
/masterdata/setup-reports/start. Erst Werkzeugnummer eingeben/auswählen, dann
startet direkt der vorhandene Wizard ohne Besuch der Werkzeug-Detailseite.
Der Bericht bleibt zwingend dem ausgewählten Werkzeug zugeordnet. Fehlende oder
mehrdeutige Werkzeugnummern legen keinen Bericht an. Bei Berechtigung ist auch
die Neuanlage eines Werkzeugs separat verlinkt.

Es gelten die bisherigen Rechte: setup_reports.create und tools.view für den
direkten Einstieg; weitere Bearbeitungs-/Lese-/Abschluss-/PDF-Rechte wie bisher.
Keine automatische Vergabe von Rechten. CSRF gilt auch am neuen Einstieg.

## Installation

Alle Dateien mit ihren Originalpfaden nach GitHub übernehmen. Auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_setup_report_fix.sh
```

Prüft die vorhandene Struktur und startet FactoryOS neu. Kein Umbau von DB,
DuckDNS, Tailscale oder APK. Danach Wizard-Seite neu öffnen; Skript-/CSS-URLs sind
versioniert, damit die Oberfläche nicht die alte Übernahme-Logik aus dem Cache lädt.

## Prüfung

- Isolierte SQLite-Tests des Wizards inklusive Rechte, Abschluss, Historie,
  Sperren, PDF, unveränderte Stammdaten und lokale OCR erfolgreich.
- Gezielt geprüft: „130.“ + „00“ (auch mit unsicherem Präfix), einzelne „00“,
  falsche Null-Dosierung, blaue Messwerte, abweichende OCR-Leseversuche, gültige
  Dezimalkomma-Zahl, alte gespeicherte Foto-Vorschläge und Handkorrektur.
- JavaScript mit DOM-Stubs: sichtbare Feld-/Profilübernahme VOR Speichern,
  nachfolgende Handkorrektur, Quellfoto, Rücksetzen des Prüfhakens, keine
  Status-Dropdowns, kein automatisches Überschreiben, Scanner bleibt sichtbar.
- Direkter Einstieg: neue Kachel, Werkzeugauswahl, CSRF, keine Anlage bei
  ungültigem Werkzeug, richtige Zuordnung und fehlende Rechte getestet.
- Bestehende Rechte-/Beschriftungstests erfolgreich (214 gesperrte Aufrufkombinationen).
- Deckblatt und Anlage erzeugt, gerendert und optisch geprüft; zusätzlich
  Belastungstest mit langen Texten, Sonderzeichen und 32 Zeilen je Profil.
  Seitenausrichtung überprüft: erste Seite quer, Anlage hoch.
- Keine Prüfung auf dem tatsächlichen Smartphone und keine Browser-/Kamera-
  Freigabeprüfung. Diese bitte vor Ort nachholen. Lokale OCR-Testumgebung hat
  nur Englisch; Ergebnisse auf dem Raspberry können abweichen.
