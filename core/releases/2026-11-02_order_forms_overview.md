# Auftragserstellung, Werkzeugzuordnung und Übersicht

Basis: main e1c8918. Vollständige geänderte/neue Dateien in Originalpfaden.

## Formular

- Artikelnummer aus vorhandenen Stammdaten wählen, führende Nullen bleiben erhalten.
- Artikelname wird direkt angezeigt, ist readonly und wird serverseitig aus dem
  Artikelstamm übernommen. Ein manipulierter Formularwert überschreibt ihn nicht.
- Fehlender Artikelname im Stammsatz muss dort ergänzt werden.
- Stückzahl Pflicht: ganze Zahl von 1 bis 2.147.483.647. Leer, 0, negative Werte,
  Dezimalzahlen und ungültige Zahlen werden auch serverseitig abgewiesen.
- Werkzeugfeld: bei genau einer Zuordnung automatische Übernahme; mehrere
  zugeordnete Werkzeuge erfordern eine bewusste Auswahl. Bei fehlender Zuordnung
  erst Artikelstammdaten ergänzen. Keine willkürliche Auswahl fremder Werkzeuge.
- Soll-Zykluszeit bleibt Pflicht und auftragsbezogen änderbar. Artikelwert ist nur
  ein Vorschlag; Artikelstammdaten werden nicht verändert.
- Moderne, responsive Karten für Auftrag/Zuordnungen und Produktionsvorgaben.
- „Artikeldaten laden“ unterstützt die Übernahme auch ohne JavaScript, ohne
  einen Auftrag anzulegen. Fehler erhalten die eingegebenen editierbaren Werte.
- Erstellen/Bearbeiten prüfen CSRF. Erfolgreiche Anlage öffnet direkt den Auftrag.

Beim Bearbeiten gilt derselbe Stammdatenbezug. Ein bereits ausdrücklich gespeichertes
ERP-/Altwerkzeug darf bei unveränderter Artikelnummer beibehalten werden, auch wenn
die aktuelle Artikelzuordnung abweicht. Es wird im Formular als gespeicherte
Auftragszuordnung markiert. Keine nachträgliche automatische Änderung der ERP-
Originalangaben. Ein neues Auftragswerkzeug wird nur aus der Artikelzuordnung gewählt.
Das bestehende Werkzeugnummernfeld am Auftrag ist 50 Zeichen lang; längere Nummern
werden mit Hinweis abgewiesen statt abgeschnitten. Kein Schemawechsel.

Artikel-/Werkzeugwechsel und Abschluss bleiben bei laufenden/reservierten oder
eingeplanten Aufträgen gesperrt. Projektaufträge behalten ihren separaten
nicht-stückbezogenen Ablauf und ihre bisherigen Zuordnungen. Musterungen bleiben
im eigenen Modul. ERP-Importvalidierung wird nicht umgestellt.

## Übersicht und Detail

- Neuer Kopf mit Kennzahlen, Suche, sortierbarer Tabelle und bestehender Pagination.
- Auftrags- und Artikelnummer als kompakte Links/Buttons. Artikel öffnet den exakt
  passenden Artikeldatensatz; unbekannte Altartikel erhalten keinen falschen Link.
- Werkzeug ebenfalls sichtbar und, bei Leserecht, direkt verlinkt.
- Aktueller Artikelname aus dem Stamm in Übersicht/Detail sichtbar. Alte gespeicherte
  Namen und ERP-Snapshots werden beim Anzeigen nicht überschrieben.
- Fehlt das Auftragswerkzeug, kann eine eindeutige Artikelzuordnung als ausdrücklich
  ungespeicherter Vorschlag erscheinen. Zur echten Übernahme Auftrag bearbeiten/speichern.
- Fehlende Pflichtangaben alter Aufträge werden als „Angaben prüfen“ markiert.
- Lesbare Mindestbreiten und horizontaler Scrollbereich auf kleinen Geräten; keine
  auf einzelne Zeichen zusammengedrückten Spalten. Lange Artikelnamen dürfen umbrechen.
- Status deutsch beschriftet; Aktionen und Stammdatenlinks entsprechend Berechtigung.

## Installation

Nach Übernahme der Dateien in GitHub:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_order_forms.sh
```

Installer prüft Python-Syntax und startet den Dienst neu. Keine Datenbankmigration,
kein historischer Daten-Backfill, keine neue APK. Nach Installation App neu laden.
Bestehende Tabellen/Felder, Benutzerrechte und Importformate bleiben erhalten.

## Prüfung

Isolierte SQLite-Tests: Stammdatenname gegen manipulierte Werte, Pflichtstückzahl,
eindeutige/mehrfache/fehlende/fremde Werkzeugzuordnung, Duplikate, CSRF, Werte bei
Validierungsfehlern, Vorschau ohne Schreibzugriff, ERP-/Projekt-Erhalt, Schutz
laufender/eingeplanter Zuordnungen, korrekte Links, unveränderte historische Daten,
Autoescaping und Rechte. Bestehende Sollzyklus-, ERP- und Planungsregressionen.
Syntax und ZIP geprüft. Kein Zugriff auf produktive Datenbank und kein echter
Browser-/Handy-Render-Test; visuelle Abnahme auf dem Gerät erforderlich.
