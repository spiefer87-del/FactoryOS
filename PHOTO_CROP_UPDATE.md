# Fehlerfotos zuschneiden und zoomen

Dateien mit Ordnerstruktur ins Repository übernehmen. Anschließend auf dem Raspberry Pi:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos.service
```

Im Fehlerkatalog ein Foto aufnehmen oder auswählen. Neben der Vorschau erscheint „Zuschneiden / Zoomen“. Im Fenster Format, Zoom und Ausschnitt über die Regler einstellen, dann „Übernehmen“. Mit „Abbrechen“ bleibt das Bild unverändert. „Zurücksetzen“ zeigt wieder das ursprüngliche Bild der aktuellen Auswahl. Die Bearbeitung bleibt lokal und wird erst beim Speichern des Fehlereintrags hochgeladen. Die automatische Komprimierung bleibt aktiv.

Dies betrifft neue Fotos vor dem Speichern, nicht bereits gespeicherte Fotos. Keine Datenbankänderung erforderlich. Moderne Browser mit Dialog-Unterstützung erforderlich.
