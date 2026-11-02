# Persönliches Profil und kontobezogene Ansichten

Basis: main 88cc699. Vollständige Ersatzdateien mit Repository-Pfaden und neue
Dateien, Installationsskript und Tests. Keine Datenbank im ZIP.

## Was sich ändert

Der Benutzername rechts oben ist ein Link zu „Mein Profil“ (`/profile/`).
Jeder aktive angemeldete Nutzer kann seine eigenen UI-Einstellungen speichern,
ohne Administrationsrechte. Benutzername, Rolle, Passwort und Berechtigungen
werden nicht verändert.

Aktuell einstellbar:

- Artikelspalten, einschließlich Musterung. Artikelnummer bleibt sichtbar.
- Werkzeugspalten. Werkzeugnummer und Aktionen bleiben sichtbar.
- Tabellendichte komfortabel / kompakt für die Tabellen der Haupt-App.
- Akzentfarbe blau / petrol / violett für primäre Aktionen, Artikel-Verknüpfungen,
  Checkboxen und aktive Seitenauswahl. Fachliche Warn-/Statusfarben bleiben erhalten.
- Gespeicherte Artikel- und Werkzeugansicht separat auf Standard zurücksetzen.

Die Daten liegen in der neuen Tabelle `user_preferences`, pro Benutzer-ID und
Einstellungsbereich. Sie werden nach erneutem Login auch in einem anderen
Browser/Gerät aus der Datenbank geladen. Browserdaten löschen löscht diese
Kontoeinstellungen nicht. Änderungen bereits geöffneter Seiten werden nach
Neuladen sichtbar, kein Live-Push zwischen Fenstern. Abwarten, bis die Oberfläche
„im Benutzerkonto gespeichert“ bestätigt, bevor man die Seite verlässt.
Bei Netzwerk-/Sitzungsfehlern wird ausdrücklich „Nicht gespeichert“ angezeigt.
Dies ist die Grundlage für weitere persönliche Optionen; noch nicht jede
App-Seite hat eine eigene Spaltenauswahl. Sortierung, Suchbegriffe, Pagination,
Sidebar-Zustand und freie Layout-/Darkmode-Konfiguration sind nicht Bestandteil.
Druckansichten und PDFs erhalten kein persönliches Farbschema/Dichte-Override.

## Übernahme bisheriger Browserwerte

Die bisherige Artikel-Spaltenauswahl hatte bereits einen benutzerspezifischen
LocalStorage-Schlüssel. Beim ersten Öffnen wird sie übernommen, sofern für dieses
Konto noch keine Artikelansicht auf dem Server gespeichert wurde. Sobald eine
Serveransicht existiert, hat sie Vorrang. Reset speichert explizite Standardwerte.

Der alte Werkzeugschlüssel war browserweit, nicht benutzerbezogen. Deshalb keine
stille Übernahme: In der Werkzeugübersicht wird bei fehlender Serveransicht eine
Schaltfläche „Bisherige Browseransicht übernehmen“ angeboten. Übernahme erfordert
eine ausdrückliche Bestätigung. Alte lokale Daten werden nicht gelöscht; die neue
Speicherung schreibt ausschließlich ins angemeldete Benutzerkonto.

## Sicherheits- und Datenmodell

Neue Tabelle mit zusammengesetztem Primärschlüssel `(user_id, section)`, JSON-Wert,
Versionszähler und Änderungszeit. Alte Tabellen werden nicht umgebaut.
Gespeichert werden nur erlaubte UI-Optionen, keine beliebigen CSS-/HTML-Werte,
keine Passwörter und keine fachlichen Stammdaten. Whitelist-Validierung je Bereich.

API `/profile/preferences/<section>` liest/schreibt ausschließlich für die
aktuelle Anmeldung, nicht für eine vom Client wählbare Ziel-ID. Änderungen brauchen
CSRF-Token und übereinstimmende aktuelle Benutzer-ID, damit alte Tabs nach einem
Kontowechsel nicht versehentlich das andere Konto ändern. Deaktivierte Nutzer
können nicht speichern. Persönliche Antworten und authentifiziertes HTML sind
private/no-store. User-Löschung entfernt die persönlichen Einstellungszeilen.

Versionierung schützt vor veralteten parallelen Updates. Der JavaScript-Client
serialisiert Schreibvorgänge je Bereich; bei Versionskonflikt wird die aktuelle
Version geladen und nur die angefragten Optionen einmal erneut angewandt.
Fehlgeschlagene lokale Änderungen werden beim nächsten Speicherversuch mitgesendet.
Bei gleichzeitiger Änderung derselben Option gewinnt der zuletzt erfolgreiche
Schreibvorgang. Keine unbegrenzten Wiederholungen oder Hintergrundschreibschleifen.

## Installation auf dem Raspberry

ZIP entpacken, enthaltene Pfade unverändert nach GitHub übernehmen und committen.
Danach:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_user_preferences.sh
```

Bei Konflikten oder Fehlern stoppen und Ausgabe weitergeben. Skript sucht die
bekannte Python-Umgebung, prüft Syntax und Schema, stoppt FactoryOS und sichert
`instance/factoryos.db` plus vorhandene WAL/SHM-Dateien nach
`/home/factoryos/backups/user_preferences_<Zeitstempel>`. Danach legt es ausschließlich
die neue Tabelle an und startet den Dienst neu. Upgrade wiederholbar.
Bei Upgrade-Fehler bleibt der Dienst gestoppt. Sicherungspfad wird ausgegeben.
Keine neuen Python-Abhängigkeiten. Nach Abschluss Browser vollständig neu laden
(Strg+F5), dann rechts oben den Benutzernamen anklicken.

## Verifikation

Isolierte SQLite-Testdatenbank, kein Zugriff auf die Raspberry-Livedatenbank.
Migration/Check zweimal mit erhaltener Benutzertabelle, zwei Benutzerkonten,
echter Login/Logout und neuer Testclient als anderes Gerät, Kontentrennung,
CSRF/Kontowechsel, Schema-/Wertevalidierung, Versionierung, Reset und User-Cascade.
Profilseite, Navbar-Link, Darstellung im gerenderten HTML sowie Artikel- und
Werkzeugseiten geprüft. Bestehende Musterungs-/Artikelhistorientests bleiben aktiv.
Node-Tests: serialisierte API-Aufrufe, Konflikt-Merge, Offline/Recovery,
Artikelmigration, serverseitige Vorgaben, stabile Zellen, Reset und ausdrücklich
bestätigte Werkzeugmigration. Syntax-/Shell-/Git-Diff- und ZIP-Prüfungen.
Kein echter Browser-/Mobilgerät-Layouttest; fachfremde OpenCV-Erkennung nur im Test
gestubbt. Manuell danach zwei Benutzer und einen zweiten Browser gegenprüfen.

```bash
python scripts/test_user_preferences.py
python scripts/test_article_columns.py
node scripts/test_user_preferences.js
```
