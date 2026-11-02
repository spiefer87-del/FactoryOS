# Artikelübersicht: offene Musterungen und Historienfenster

Basis main 12c563d. Das ZIP enthält vollständige geänderte/neue Dateien mit
Repository-Pfaden und das Installationsskript. Keine Datenbank enthalten.

## Funktionen

- Neue Spalte „Musterung“ in der Artikelübersicht. Anzahl offener Musterungen,
  Anzahl insgesamt und Statusverteilung im Tooltip. Anklicken öffnet den Verlauf.
- Offen = jeder Auftrag, der nicht `completed` ist, insbesondere Entwurf,
  In Bearbeitung, In Prüfung, Nachbemusterung erforderlich. Unbekannte zukünftige
  Status werden vorsichtshalber ebenfalls als offen gezählt.
- Intern abgeschlossene reguläre Musterungen sind nicht mehr als offen markiert,
  auch wenn die Kundenfreigabe aussteht. Der separate Kundenstatus steht im Verlauf.
- Artikeldetailseite erhält einen Bereich „Musterungen und Artikelhistorie“ mit
  Statusübersicht und Button für ein separates Popup-Fenster. Je nach Browser
  kann ein neuer Tab erscheinen. Ohne JavaScript bzw. bei Popup-Blockade bleibt
  der normale Link verwendbar. Bereits vorhandene Aktivitäten bleiben erhalten.
- Fenster mit Musterungsverlauf (Anlass, Status, Freigaben, Termine, gespeichertes
  Werkzeug/Material, Grund/Ergebnis, PDF und Druckansicht) und Artikeländerungen
  (Zeit, Benutzer und Vorher-/Nachher-Werte, soweit protokolliert).
- Neueste Einträge zuerst, getrennte Seitennavigation mit je 20 Aufträgen bzw.
  Artikelereignissen. Es werden keine älteren Einträge abgeschnitten.
- Artikelbezug ausschließlich über vorhandenen FK `sampling_orders.article_id`,
  nicht über Namens-/Artikelnummern-Vermutungen. Ohne Zuordnung bleibt eine
  Musterung außerhalb des artikelbezogenen Verlaufs. Nachträglich zu einem anderen
  Artikel umgehängte Musterungen erscheinen beim aktuell zugeordneten Artikel.
- Es wird keine rückwirkende Historie erfunden. Nicht protokollierte frühere
  Änderungen sind nicht rekonstruierbar. Gespeicherte Referenz-IDs werden als IDs
  benannt; die Oberfläche zeigt keine heutigen Namen als angebliche frühere Werte.

## Technik und Sicherheit

Nur Lesezugriffe. Keine Schemaänderung, Migration oder neue Python-Abhängigkeit.
Der Anmeldeschutz entspricht den bestehenden Artikel-/Musterungsseiten.
Historienseite liefert private/no-store. Eingaben werden HTML-escaped; geöffneten
Popup-Fenstern wird der Opener entzogen. Keine neuen Schreib-/Freigabeaktionen.
Eine aggregierte Datenbankabfrage für die komplette angezeigte Artikelliste statt
Einzelabfragen je Artikel. Verknüpfungen und Historienseiten laden benötigte Daten
vorab. Datums-/Zeitstempel des bestehenden Systems werden ausdrücklich als UTC
bezeichnet; reine Datumsfelder bleiben reine Datumswerte.

## Installation

Dateien mit unveränderten Ordnerpfaden in GitHub übernehmen und committen.
Auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_article_sampling_history.sh
```

Bei Konflikten oder Fehlern stoppen und Ausgabe weitergeben. Das Skript findet
die bekannte Python-Umgebung, prüft Syntax und startet den Dienst neu. Danach
Browser vollständig neu laden (Strg+F5). Keine Datenlöschung, kein DB-Upgrade.

## Tests

`scripts/test_article_sampling_history.py` mit isolierter SQLite-Testdatenbank:
alle offenen Status, abgeschlossen/intern vs. Kundenfreigabe, getrennte Artikel,
gespeicherter Werkzeugstand, leere Historie, Such-/Übersichts- und Detaillinks,
Login/404, HTML-Escaping, Seitennavigation, unveränderte Auftragsdaten/Versionen
bei Lesezugriffen, genau eine aggregierte Statusabfrage für mehrere Artikel.
Bestehende Musterungsworkflow-Tests werden dabei ebenfalls ausgeführt.
`scripts/test_article_sampling_history.js`: Popup-Aufruf, Opener-Isolation,
blockiertes Popup, Fehlerfall und Strg-/modifizierte Klicks.
Python-Kompilierung, Shell-Syntax und Diff-Prüfung. Kein Live-Zugriff auf die
Raspberry-Datenbank und kein echter Browserfenster-/Mobilgerätetest.
Die fachfremde OpenCV-Zeichnungserkennung wird nur im Test gestubbt.
