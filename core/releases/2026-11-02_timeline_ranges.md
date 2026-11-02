# Timeline: kurze/lange Zeitfenster und freie Datumswahl

Basis: main 7ad8b3e. Vollständige geänderte/neue Dateien in Originalpfaden.

- Neu: 1 Stunde (15 Minuten zurück / 45 voraus), 8 Stunden (2 zurück / 6 voraus),
  30 Tage (7 zurück / 23 voraus). 24 Stunden, 3 Tage und 7 Tage bleiben erhalten.
- Eigener Zeitraum mit Von/Bis einschließlich Uhrzeit für Vergangenheit/Zukunft.
  Mindestspanne 1 Minute, Höchstspanne 366 Tage pro Anzeige (Jahre 1970–2100).
- Eingaben, Zeitachse und Beschriftungen in Europe/Berlin. Speicherung bleibt UTC.
  Doppelte Herbststunde erfordert bewusste Auswahl der ersten/zweiten Stunde;
  nicht existierende Frühlingszeiten werden abgewiesen.
- Ungültige Eingaben bleiben zur Korrektur erhalten; klar beschriftete vorläufige
  24-Stunden-Ansicht und HTTP 400 statt stiller Übernahme eines falschen Zeitfensters.
- „Zurück zu jetzt“ öffnet wieder die normale 24-Stunden-Ansicht.
- Adaptive Achsenskalierung und horizontal scrollbar bleibende Mindestbreite.
- Jetzt-Markierung nur, wenn jetzt tatsächlich im ausgewählten Zeitfenster liegt.
- Aktuelle Statuskarten, Kennzahlen und Maschinenbedienung bleiben IMMER aktuell,
  auch beim Betrachten der Vergangenheit. Historische Buchungen beeinflussen
  nicht die Auswahl des laufenden Vorgangs.
- Zukunft zeigt ausschließlich aktuelle Endprognosen laufender Aufträge.
  Keine erfundenen zukünftigen Ist-Zeiten und keine Balken nach Prognoseende.
  Auftragsreihenfolgen/Planungsbuchungen werden in diesem Patch noch nicht angelegt.
- Bestehende Produktionskalender-Berechnung bleibt unverändert; keine Umstellung
  gespeicherter Kalenderzeiten, Buchungen oder Mengen.

Nach Übernahme in GitHub:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_timeline_ranges.sh
```

Reines Anzeigeupdate: kein Datenbank-Upgrade und keine neue APK. Installer prüft
Python-Syntax und startet den Dienst neu; er schreibt nicht in die Datenbank.
App anschließend neu laden. Vorhandene Maschinenbedienung bleibt verfügbar.

Prüfung mit synthetischer SQLite-Datenbank: alle festen Fenster, freie lokale
Datumswahl, ungültige/zu große Zeiträume, Zeitumstellung, historische Buchungen,
Live-Zustände außerhalb des Fensters, Zukunftsprognosen und Balkengrenzen,
bedingte Jetzt-Markierung, Achsendichte sowie fehlende Schreibeffekte auf
Buchungen/Mengen/Protokolle. Maschinenbedienungs-Regressionssuite mit ausgeführt.
Keine produktive Datenbank und kein echter Touchscreen verwendet; visuelle
Geräteabnahme nach Installation erforderlich.
