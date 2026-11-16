# Prüfplan erstellen: mobile Breite und Artikelsuche

Vollständige geänderte/neue Dateien; Basis main 6c7e892.
Keine Datenbankänderung, keine Änderung am Backend der Werkzeugzuordnung.

Dateien mit Ordnerstruktur nach GitHub übernehmen, anschließend:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos.service
```

Die Seite vollständig neu laden. Im Feld „Artikel suchen“ nach Artikelnummer
oder Bezeichnung suchen. Ab zwei Zeichen wird die Auswahl eingeschränkt.
Der passende Artikel wird anschließend ausdrücklich ausgewählt. Leeren der
Suche zeigt alle Artikel wieder an. Wenn der ausgewählte Artikel durch die
Suche entfällt, wird auch seine bisherige Werkzeugauswahl zurückgesetzt.

Die Werkzeuge stammen weiterhin ausschließlich aus dem bestehenden
Zuordnungs-Endpunkt des ausgewählten Artikels. Die vorhandene durchsuchbare
Werkzeugauswahl bleibt erhalten. Verspätete Antworten bei schnellem
Artikelwechsel können die neuere Werkzeugliste nicht mehr überschreiben.
Ladefehler bzw. fehlende Zuordnungen werden angezeigt.

Breitenbegrenzung und einspaltiges Formular gelten nur für diese Seite.
Lange Texte dürfen die Formularbreite nicht aufziehen; auf kleinen Geräten
stehen die Schaltflächen untereinander. Artikel-/Werkzeug-IDs und CSRF-Schutz
werden unverändert übermittelt. Kein neuer externer Dienst nötig.

Lokal geprüft: JavaScript mit 500 synthetischen Artikeln, Zwei-Zeichen-Suche,
Artikelnummer/Bezeichnung, leere Treffer, Zurücksetzen, Werkzeug-Anfragerennen,
unvollständiges Formular; Flask-Seite und unveränderte Werkzeug-API.
Die endgültige Darstellung auf eurem Android-Gerät bitte nach Neuladen prüfen.
