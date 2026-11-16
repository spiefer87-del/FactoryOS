# Erstbestand und durchgehende Zeitaufzeichnung

Ursache: Die Bestandsmeldung speicherte den Werkzeugbestand, aber bei einer
Maschine ohne vorherige Buchung noch keinen laufenden Zeitabschnitt.

Eine bestätigte Bestandsmeldung startet jetzt bei fehlender aktiver Buchung
einen Abschnitt FREI / Keine aktive Tätigkeit. Ein Auftrag ist nicht nötig.
Die Timeline und die Maschinenauswahl verwenden dadurch denselben laufenden
Status. Werkzeugbestand und Tätigkeit bleiben unabhängig: Auch mit montiertem
Werkzeug kann keine aktive Tätigkeit vorliegen. Laufende Buchungen werden
nicht beendet, geteilt oder neu gestartet. Bestätigungen bleiben atomar,
berechtigungsgeprüft und wiederholungssicher.

## Installation auf dem Raspberry Pi

Alle Dateien dieses Pakets mit ihren Verzeichnissen nach GitHub übernehmen,
dann im Terminal eine Zeile ausführen:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_initial_idle_fix.sh
```

Der Installer prüft die bestehende Struktur, stoppt den Dienst, sichert die
SQLite-Datenbank einschließlich vorhandener WAL-Dateien und ergänzt die
fehlenden Abschnitte. Anschließend startet er den Dienst wieder. Bei einem
Reparaturfehler wird die Transaktion zurückgerollt und der Dienst bleibt zur
Prüfung gestoppt. Danach Timeline bzw. Maschinenauswahl neu laden.

## Nachtrag vorhandener Meldungen

Nur Maschinen mit bestätigtem Werkzeugbestand und ohne aktive Buchung kommen
infrage. Wenn das unveränderte Befehlsprotokoll die Bestandsmeldung ohne
aktive Buchung belegt und danach keine Buchung liegt, beginnt der Abschnitt
zum Zeitpunkt dieser Meldung. Es wird keine Zeit vor der Meldung erfunden.
Bei unvollständigem Nachweis oder zwischenzeitlicher Tätigkeit beginnt der
Abschnitt erst zum Reparaturzeitpunkt. Ungeklärte Reservierungen, offene
Rüstvorgänge und Zukunftskonflikte werden mit einem Hinweis übersprungen.
Unbekannte oder erneut prüfpflichtige Werkzeugbestände werden nicht geändert.

Der Systemnachtrag wird separat protokolliert; vorhandene Bestandsmeldungen
und Befehlsprotokolle bleiben unverändert. Er erzeugt keine Produktionsmenge,
keinen Auftrag und keinen Rüstnachweis. Wiederholte Installation erzeugt keine
doppelten aktiven Abschnitte. Die Timeline selbst bleibt rein lesend.

Lokale Regressionen: scripts/test_initial_idle.py sowie die bestehenden Tests
für Werkzeugbestand, Maschinenbedienung, Auftragsabschluss und Zeiträume.
Keine Änderungen an DuckDNS, Tailscale oder externen Erkennungsdiensten.
