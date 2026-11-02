# Artikelübersicht: Spaltenauswahl und kompakte Verknüpfungen

Basis: main 416f792. ZIP mit vollständigen geänderten/neuen Dateien und
Installationsskript, kein Git-Diff und keine Datenbank enthalten.

## Bedienung

Oben rechts in der Artikelübersicht „Spalten auswählen“ öffnen. Artikelname,
Kunde, Rohstoff, Werkzeuge, Status, Musterung und Aktionen können einzeln ein-/
ausgeblendet werden. Die Artikelnummer bleibt zur Identifizierung sichtbar.
„Alle Spalten anzeigen“ stellt die Standardansicht wieder her. Beim ersten
Aufruf sind alle Spalten sichtbar. Zum Beispiel Haken bei „Musterung“ entfernen.
Die Historie in der Artikeldetailseite bleibt unabhängig davon erreichbar.

Auswahl wird in localStorage pro angemeldetem Benutzer und Browser gespeichert.
Keine Synchronisierung auf andere Browser/Geräte. Browserdaten löschen setzt die
Auswahl zurück. Gesperrter Speicher verhindert das Umschalten nicht, die Auswahl
gilt dann nur auf der aktuellen Seite; ein Hinweis zeigt dies an. Es werden nur
Spaltenkennungen und Sichtbarkeitswerte gespeichert, keine Artikeldaten.
Escape schließt die Auswahl und gibt den Fokus an den Auslöser zurück.

Artikel-, Kunden- und Rohstoffverknüpfungen sind kompakte beschriftete Link-Buttons.
Werkzeugverknüpfungen erhalten dieselbe Gestaltung. Echte Links bleiben erhalten,
auch für Tastatur und „In neuem Tab öffnen“. Responsives Layout, sichtbarer
Tastaturfokus und reduzierte Bewegung bei entsprechender Systemeinstellung.

Nur die Artikelübersicht wird geändert. Keine neue Schreibaktion, keine Änderung
an Zuordnungen, Musterungsstatus, Freigaben, PDF oder Datenbankschema.
Kopf- und Datenzellen werden gemeinsam ausgeblendet, nicht aus dem DOM entfernt.
Ihre Reihenfolge/Indizes bleiben für die vorhandene Suche, Sortierung und
Seitennavigation erhalten; globale Tabellenfunktionen werden nicht verändert.

## Installation

ZIP entpacken, Dateien mit ihren unveränderten Pfaden in GitHub übernehmen und
committen. Danach auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_article_columns.sh
```

Bei Pull-Konflikten oder Fehlern stoppen und Ausgabe weitergeben.
Kein DB-Upgrade und keine neuen Abhängigkeiten. Skript sucht die bekannte
Python-Umgebung, prüft Syntax und startet FactoryOS neu. Danach Browser vollständig
neu laden (Strg+F5), damit die neue JavaScript-/CSS-Version geladen wird.

## Verifikation

`node scripts/test_article_columns.js`: Standardsicht, Ausblenden aller 26
Testzeilen inklusive Kopf, konstante Zellreihenfolge, Speicherung/Wiederherstellung,
Benutzertrennung, obligatorische Artikelnummer, Reset, gesperrter/defekter Speicher,
ungültige Speicherdaten, Escape/Fokus.
`python scripts/test_article_columns.py`: isolierte SQLite-Testdatenbank und
HTML-Parser prüfen exakt acht zusammenpassende Spalten pro Zeile, Steuerelemente,
Button-Verknüpfungen, Escaping und vorhandene Historienfunktionen. Führt auch
bestehende Artikelhistorien-/Musterungsworkflowtests aus.
Python-Kompilierung, Shell-Syntax, Diff-Prüfung und ZIP-Integritätsprüfung.
Kein Live-Datenbankzugriff und kein echter Browser-/Mobilgeräte-Layouttest.
Die fachfremde OpenCV-Erkennung wird nur in der Testumgebung gestubbt.
