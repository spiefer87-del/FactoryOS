# Artikelübersicht: lesbare Spalten auf Handy und Desktop

Basis: main 62bc6c1.

- Fachliche Mindestbreiten pro Spalte verhindern das Zusammenquetschen.
- Artikelnummern, Kunden-/Materiallinks und Werkzeugnummern bleiben lesbar und werden nicht zeichenweise umgebrochen.
- Breite Tabellen werden innerhalb der Karte horizontal scrollbar; die gesamte Seite muss nicht seitlich verschoben werden.
- Scrollbereich ist per Tastatur erreichbar und beschriftet.
- Hinweis zum seitlichen Wischen erscheint nur bei tatsächlichem Überlauf und aktualisiert sich bei Spaltenauswahl, Fenstergröße und Tabellenänderungen.
- Mobile Spaltenauswahl klappt innerhalb der Karte auf, statt vom Kartenrand abgeschnitten zu werden.
- Suche, Sortierung, Seitennavigation und persönliche Spaltenauswahl bleiben unverändert.
- Änderungen sind auf die Artikelübersicht begrenzt. Keine Datenbankänderung und keine neue APK notwendig.

## Installation

Dateien aus der ZIP mit ihren relativen Pfaden in GitHub übernehmen und committen.

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_article_mobile.sh
```

Anschließend in der Android-App im Menü Neu laden wählen. Im Browser gegebenenfalls mit geleertem Seitencache neu laden.

## Tests

- scripts/test_article_columns.py: Tabellen-/Vorlagenstruktur, unveränderte Spaltenauswahl, Historienlinks, Escape-Schutz, zugänglicher Scrollbereich und neue statische Datei.
- scripts/test_article_table_scroll.js: Überlauferkennung, Spaltenänderungen, Größenänderung und ResizeObserver-Fallback.
- Bestehender JavaScript-Test scripts/test_article_columns.js: unveränderte benutzerbezogene Speicherung, Konfliktbehandlung und Spaltenauswahl.
- Keine Live-Prüfung gegen Raspberry-Datenbank oder Android-Gerät. Der lokale Browserstart war in der Build-Umgebung nicht möglich; visuelle Darstellung bitte einmal auf dem Handy prüfen.
