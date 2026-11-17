# Lageroberfläche kompakt

Basis main 5075c23. Vollständige geänderte/neue Dateien. Keine Migration,
keine Änderung an Buchungslogik, Mengen, Reservierungen, Rechten oder Journal.

Dateien mit Verzeichnisstruktur nach GitHub übernehmen, dann auf dem Pi:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_inventory_ui.sh
```

Anschließend die Seite vollständig neu laden, damit die neue CSS-Datei geladen
wird. Voraussetzung ist das bereits installierte Lager-Grundmodul.

## Neue Aufteilung

Die Lagerstartseite enthält vier große Kacheln wie die Produktionsübersicht:
Wareneingang, Lagerbestände, Warenausgang sowie Verwaltung & Historie.
Darunter steht direkt die Bestandsliste mit Suche, Sortierung und Seitenwechsel.
Die bisherige obere Navigationsleiste und die lange Liste aller Buchungsaktionen
entfallen. Auf kleinen Bildschirmen stehen die Kacheln untereinander.

- Wareneingang: Produktionsübergabe und Lagerannahme direkt; Übergabeausschuss
  und Storno unter „Weitere Aktionen“. Bestätigte Produktion und offene
  Übergaben stehen nur noch hier, nicht zusätzlich auf der Startseite.
- Bestände: Umlagern, Freigeben und Reservieren direkt; Sperren, Lagerausschuss
  und Erstbestand unter „Weitere Aktionen“.
- Warenausgang: Kommissionieren und Versand direkt; Freigabe einer Reservierung
  und Rücknahme unter „Weitere Aktionen“.
- Verwaltung & Historie: zwei weitere Kacheln für Lagerplätze und Journal.
  Lagerplätze werden dort angelegt, Gegenbuchungen aus dem Journal geöffnet.

Alle vorhandenen Aktionen bleiben erhalten und werden weiterhin nach den
bestehenden Rechten angezeigt. Auf Unterseiten führt „Lagerübersicht“ zurück;
Formulare führen zurück zu ihrem fachlich passenden Bereich. Die bisherigen
URLs für Bestände, Wareneingang, Versand, Lagerplätze und Journal bleiben gültig.
Tabellen scrollen innerhalb ihres Bereichs, nicht über die ganze Seite.

Lokal geprüft: komplette vorhandene Lager-Funktionsregression und zusätzlicher
Navigationstest (vier Startkacheln, nur eine Bestandsliste, vollständige Verteilung
aller Aktionen, Rückwege, reine Lesezugriffe und ausgeblendete Aktionen für
Lesebenutzer). Die endgültige Darstellung auf eurem Android-Gerät bitte prüfen.
