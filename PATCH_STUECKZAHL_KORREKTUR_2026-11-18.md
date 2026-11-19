# Stückzahl direkt aus der Laufzeitabweichung korrigieren

GitHub-Basis: spiefer87-del/FactoryOS, main,
Commit 0cd15bdd5a7467b7e5968f1357da3c4371c5287c.

Das ZIP enthält vollständige geänderte und neue Dateien mit ihren Repository-
Pfaden. ZIP entpacken und die enthaltenen Dateien mit Ordnerstruktur in das
Stammverzeichnis des GitHub-Repositorys übernehmen, bestehende Dateien ersetzen
und committen. Keine Datenbankmigration und keine neuen Rollenrechte nötig.

## Bedienung

1. Bei „Laufzeitabweichung prüfen“ steht direkt nach „Bitte auswählen“ als
   erster Eintrag **Stückzahl korrigieren**.
2. Die Auswahl öffnet sofort die vorhandene Auftragsbearbeitung beim Feld
   „Stückzahl“. Das Eingabefeld erhält den Fokus.
3. Die neue gesamte Fertigungsmenge eingeben, beispielsweise **15000** statt
   **10000**, und „Änderungen speichern“ wählen. Nicht nur die Differenz 5000
   eingeben: Das Feld enthält wie bisher die vollständige Sollmenge.
4. Der bestehende Speichervorgang übernimmt die Menge in den Auftrag und
   protokolliert den alten und neuen Wert. Endprognose, Sollzeit und Folgeplanung
   werden auf Grundlage der neuen Sollmenge berechnet.

Ohne JavaScript steht auf der Abweichungsseite ein direkter Ersatzlink bereit.
Der neue Auswahleintrag ist eine Bearbeitungsaktion und wird nicht als bloße
Abweichungsbegründung gespeichert. Seine Auswahl allein verändert noch keine
Auftragsdaten und bestätigt keine Abweichung.

## Hinweis in der Timeline

Bei laufenden Fertigungsaufträgen mit erreichter/überschrittener Sollzeit bzw.
gemeldeter Sollmenge und fehlendem Abschluss erscheint „Auftragsmenge noch
aktuell?“. Er steht direkt an der Maschine sowie im Bereich „Aktueller Stand“.
Der abgerundete Button „Auftrag bearbeiten“ öffnet ebenfalls direkt die Menge.

Der Hinweis erklärt eine mögliche Mengenänderung als Prüfmöglichkeit und
unterstellt keine Ursache. Er bleibt auch bei bereits begründeter Überschreitung
sichtbar. Ist nach einer Korrektur tatsächlich keine Abweichung mehr vorhanden,
entfällt er beim Neuladen. Eine weiterhin bestehende Überschreitung bleibt
sichtbar und wird nicht pauschal bestätigt oder ausgeblendet.

## Berechtigungen und Grenzen

- Eintrag und Bearbeitungsbutton erscheinen nur mit dem bestehenden Recht
  orders.edit. Benutzer ohne dieses Recht sehen in der Timeline nur den Hinweis,
  eine berechtigte Person hinzuzuziehen.
- Die vorhandenen serverseitigen Prüfungen der Auftragsbearbeitung gelten für
  GET und POST weiter. Auch eine manuell eingesendete Auswahl der neuen Aktion
  auf der Abweichungsseite wird ohne Bearbeitungsrecht verweigert.
- Abgeschlossene, gesperrte oder stornierte Aufträge werden nicht über diesen
  Einstieg bearbeitet. Musterungen und Projekte behalten ihre eigenen Abläufe.
- Die Mengenänderung bucht keine gefertigten Gut-/Ausschussstücke, verändert
  keine Zeitbuchungen und löscht keine früheren Abweichungsbestätigungen.
  Die Endzeit bleibt eine Solltempo-Schätzung unter Berücksichtigung des
  Produktionskalenders und der vorhandenen Mengenmeldungen.

## Raspberry Pi

Nach Upload und Commit auf GitHub:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Danach Timeline und Abweichungsseite neu laden.

## Prüfung

Mit isolierten SQLite-Testdatenbanken geprüft:

```bash
python scripts/test_quantity_edit_navigation.py
node scripts/test_deviation_actions.cjs
python scripts/test_production_deviations.py
python scripts/test_order_forms.py
python scripts/test_timeline_ranges.py
python scripts/test_runtime_overrun.py
```

Der neue Integrationstest prüft den ersten Menüeintrag, unmittelbare Navigation,
gezielte Mengenfokussierung, Lese-/Bearbeitungsrechte, manipulierte POSTs und
CSRF, die tatsächliche bestehende Speicherung von 10000 auf 15000 Stück,
aktualisierte End- und Folgetermine sowie unveränderte Mengen-/Zeitbuchungen
und erhaltene Bestätigungshistorie. Der JavaScript-Test prüft den sofortigen
Seitenwechsel und unverändertes Verhalten der normalen Begründungsoptionen.
Ein grafischer Android-Browsertest war in dieser Umgebung nicht möglich.
