# Einheitliches Stammdaten-Design

Basis: GitHub main 56b3043. Vollständige Ersatzdateien dieses Patches.
Keine Datenbankänderung und kein Upgrade der Datenbank erforderlich.

Zentrale masterdata_theme.css, ausschließlich auf die Stammdaten-Blueprints
begrenzt. Wird nach den bisherigen Stylesheets geladen. Vereinheitlicht
Karten, Formularraster, Detailfelder, Buttons, Abstände, Tabellencontainer
und mobile Umbrüche für Artikel, Kunden, Werkzeuge, Maschinen und Materialien.
Andere App-Bereiche bleiben unverändert.

Die bestehenden Felder, Uploads, Bedingungen und Berechtigungen bleiben erhalten.
Kundendetailseite wird in Kontakt, Anschrift, Notizen und Artikel gegliedert.
Aktivitäten bei Werkzeugen, Maschinen und Materialien standardmäßig geschlossen;
per Pfeil oder Tastatur aufklappbar. Artikel verwenden bereits dasselbe Prinzip.

Getestet: 15 Detail-/Anlage-/Bearbeitungsseiten mit isolierter SQLite-Testdatenbank;
korrektes Rendering und geklappte Aktivitäten; Theme außerhalb der Stammdaten
nicht eingebunden. Renderingtest klammert lediglich die fremde Bildanalyse aus.
Visuelle Browserprüfung hier nicht möglich, da der Testbrowser nicht verfügbar war.

Nach Upload und Commit auf GitHub:

    cd /home/factoryos/FactoryOS
    git status --short
    git pull --ff-only origin main
    bash scripts/install_masterdata_theme.sh

Bei Konflikten stoppen und Ausgabe weitergeben.
Danach Browser vollständig neu laden (Desktop Strg+F5).
