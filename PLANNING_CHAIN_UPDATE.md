# Auftragsplanung: abgelaufene Schätzungen und automatische Folgezeiten

Basis: `spiefer87-del/FactoryOS`, Branch `main`, Commit `fcde18060fec32592a80013b0736cd293ac87371` vom 17.11.2026.

## Installation

ZIP entpacken. Alle enthaltenen vollständigen Dateien mit ihrer Ordnerstruktur ins Stammverzeichnis des GitHub-Repositories hochladen und auf `main` committen. Keine zusätzliche äußere ZIP-Ordnerstufe übernehmen.

Danach auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos
```

Prüfen:

```bash
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Keine Datenbankmigration und keine neuen Laufzeit-Abhängigkeiten erforderlich.

## Verständlicher Hinweis auf eine abgelaufene Schätzung

Wenn die bisherige Verfügbarkeitsschätzung erreicht oder überschritten ist und der laufende Vorgang weiterhin kein belastbares Ende hat, nennt der rote Hinweis jetzt:

- den konkreten bisherigen Termin, beispielsweise 17.11.2026 um 16:00 Uhr;
- den weiterhin laufenden Auftrag bzw. Vorgang;
- den Zusammenhang: Die Schätzung wurde überschritten, deshalb ist die Planung wieder rot und eine neue zukünftige Schätzung mit Begründung nötig.

Der Bereich zum Aktualisieren der Maschinenverfügbarkeit ist in diesem Fall bereits aufgeklappt. Der frühere Zeitpunkt bleibt als frühere, abgelaufene Annahme erkennbar. Neue Schätzungen in der Vergangenheit oder genau zum aktuellen Zeitpunkt werden beim Speichern abgewiesen.

Die Bewertung erfolgt wie bisher beim Aufrufen bzw. Neuberechnen der Planung. Eine bereits länger geöffnete Seite bei Bedarf neu laden. Ist die Maschine inzwischen frei oder liegt eine aktuelle belastbare Endprognose vor, erzwingt eine alte abgelaufene Annahme keine unnötige neue Schätzung. Eine spätere belastbare Endprognose bleibt maßgeblich.

## Eine Zeitkette für die Folgeaufträge

Die Planung verwendet durchgehend:

1. Maschinenverfügbarkeit bzw. Ende des vorherigen Auftrags.
2. Zusätzliche Rüstzeit für den nächsten Auftrag.
3. Produktion dieses Auftrags.
4. Dessen Ende als Grundlage für den folgenden Auftrag.

Beispiel innerhalb der Arbeitszeit: Maschine voraussichtlich frei ab 21:00 Uhr, zusätzliche Rüstzeit 30 Minuten → Rüsten ab 21:00 Uhr, Produktion ab 21:30 Uhr.

Das Eingabefeld „Frühester Planbeginn“ entfällt sowohl beim Anhängen als auch beim Bearbeiten eines Folgeauftrags. Stattdessen erscheint der automatisch übernommene Beginn als nicht editierbare Anzeige mit seiner Herkunft. Rüstminuten und Notiz bleiben bearbeitbar. Bei einer geänderten Maschinenverfügbarkeit, Reihenfolge oder Rüstzeit werden die weiteren Termine beim Neuberechnen entsprechend abgeleitet.

Arbeitsfreie Zeiträume werden weiterhin für Rüsten und Produktion berücksichtigt. Deshalb kann der tatsächlich angezeigte Rüstbeginn später als die reine Verfügbarkeit liegen. Für einen bereits laufenden Rüstvorgang desselben Auftrags gilt weiterhin der vorhandene Hinweis, dass dessen restliches Rüsten in der Verfügbarkeitsschätzung enthalten ist.

Bereits gespeicherte separate Planbeginne aus der bisherigen Oberfläche werden bei der neuen Berechnung nicht mehr als unabhängige Verzögerung berücksichtigt. Die Datenbankspalte bleibt ohne Schemaänderung erhalten. Beim nächsten ausdrücklichen Speichern eines Planeintrags wird sein alter separater Termin aufgehoben und im Änderungsprotokoll berücksichtigt. Ein lesender Aufruf verändert diese alten Datensätze nicht. Noch geöffnete alte Formulare mit einem separaten Starttermin werden mit einem verständlichen Hinweis zum Neuladen abgewiesen.

Bei eindeutigen Uhrzeiten ist die Zeitumstellungs-Auswahl jetzt „automatisch“. Im November wird dadurch nicht mehr irreführend „Erste Stunde (Sommerzeit)“ vorausgewählt. Tatsächlich doppelte Uhrzeiten im Herbst bleiben unterscheidbar.

## Prüfung

Erfolgreich geprüft: `test_planning_chain.py`, die darin ausgeführte bestehende Planungsregression, `test_order_planning_concurrency.py`, `test_order_statistics.py` und `test_tool_mount.py` einschließlich ihrer bestehenden Test-Fixtures.

Die neuen Fälle umfassen den Ablauf 16:00 → 21:00 → erneut überschritten, die Grenze genau zum geschätzten Termin, Verkettung mehrerer Aufträge mit Rüstzeiten, alte unabhängige Termine, Umordnen, Arbeitskalender, Ablehnung vergangener Schätzungen, Transaktions-Rollback, Formulare ohne zweites Startfeld, Winter-/Sommerzeit sowie freie, inaktive oder widersprüchlich mehrfach belegte Maschinen. Weiterhin getestet: keine Ist-Buchungen durch die Vorschau, konkurrierende Planänderungen und Konkurrenz mit einem echten manuellen Start.

Optionaler isolierter Test:

```bash
./venv/bin/python scripts/test_planning_chain.py
```

Bei einer Umgebung namens `.venv` entsprechend `./.venv/bin/python` verwenden. Die Tests verwenden synthetische Daten und keine Produktionsdatenbank.
