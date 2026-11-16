# FactoryOS – Werkzeugbestand und nachvollziehbare Rüstvorgänge

Stand 16.11.2026. Basis: GitHub main `aef97b6ed2c70c91634a9d72327141a832a1223d`.
Vollständige geänderte/neue Dateien, kein Diff.

## Der Widerspruch ist getrennt abgebildet

**Tätigkeit** und **Werkzeugbestand** sind zwei unterschiedliche Angaben:

- Produktion, Rüsten, Abrüsten, Pause, Störung, Wartung usw. beschreiben die Tätigkeit.
- „Gerüstet · Werkzeug … montiert“, „Abgerüstet · ohne Werkzeug bestätigt“ oder
  „Werkzeugbestand ungeklärt“ beschreiben den gespeicherten physischen Bestand.

Die interne Buchungskennung `FREI` bleibt zur Kompatibilität erhalten, heißt in der
Oberfläche aber **Keine aktive Tätigkeit**. Eine graue Zeitbuchung und der Abschluss
eines Auftrags sind deshalb keine Behauptung, dass die Maschine ohne Werkzeug ist.
Stoppen, Pausieren, Wartung und Auftragsabschluss entfernen keinen bestätigten Bestand.

Der aktuelle Bestand ist in Maschinenbedienung, Timeline und Auftragsplanung sichtbar.
Bei historischen Timeline-Zeiträumen ist der Bestandszusatz ausdrücklich mit „Aktuell“
gekennzeichnet: Er ist kein rückwirkend erfundener Werkzeugbestand.

## Normaler Ablauf für die Einrichter

1. **Rüsten starten** mit Werkzeug, optional mit offenem Auftrag.
2. Tatsächlichen Rüstvorgang durchführen; bei Bedarf **Rüstvorgang pausieren** oder
   Störung melden. Fortsetzen ist immer ein separater Befehl.
3. **Rüstende bestätigen**: dieses Werkzeug ist nun als montiert bestätigt.
4. Produktion separat starten, später stoppen oder Auftrag abschließen.
   Das Werkzeug bleibt dabei montiert.
5. **Abrüsten starten**: es zählt das montierte Werkzeug, nicht der ausgewählte Folgeauftrag.
6. **Abrüstende bestätigen**: erst jetzt ist „ohne Werkzeug“ bestätigt.

Ein anderes Werkzeug kann nicht einfach über einen bestätigten montierten Bestand
hinweg aufgerüstet werden. Erst regulär abrüsten. Einrichten desselben montierten
Werkzeugs bleibt als Rüstvorgang möglich. Während Auf-/Abrüsten ist der endgültige
physische Zustand noch nicht bestätigt; der offene Vorgang und sein Werkzeug bleiben sichtbar.

„Vorgang stoppen“ während eines offenen Rüstvorgangs ist ausdrücklich ein **Abbruch**,
kein erfolgreicher Abschluss. Der Bestand wird ungeklärt und der nächste neue
Produktions-/Rüststart bleibt bis zur tatsächlichen Bestandsprüfung gesperrt.

## Rüsthistorie und Zeiten

In der Maschinenbedienung unter **Rüsthistorie · Auf- und Abrüsten**:

- Werkzeugnummer und, soweit zugeordnet, Auftrag;
- Beginn und Startbenutzer;
- Ende und Endbenutzer;
- offen/unterbrochen, erfolgreich abgeschlossen oder abgebrochen;
- Abschluss-/Abbruchnotiz;
- Summe der gebuchten aktiven Rüst-/Abrüstzeiten, Unterbrechungszeit und Gesamtzeit.

Eine Störung oder Pause beendet nicht den gesamten Rüstvorgang. Seine Zeitabschnitte
bleiben über die vorhandenen Zeitbuchungen nachvollziehbar und werden für die Anzeige
zusammengeführt. Es handelt sich um gebuchte Zustandszeiten, nicht automatisch erfasste
Arbeitsstunden einer Person. Die letzten 30 Vorgänge werden angezeigt; ältere bleiben
gespeichert. Die bisherigen Buchungen und Befehlsprotokolle bleiben unverändert erhalten.

## Bestehende Maschinen einmal prüfen

Nach Installation bitte **je Maschine den tatsächlichen Bestand vor Ort bestätigen**.
Die neue Funktion **Bestand vor Ort bestätigen / korrigieren** erfordert einen bewussten
Zustand, ein vorhandenes Werkzeug bei „montiert“ und eine Begründung. Sie erzeugt
keine erfundenen Rüstzeiten. Während laufender Produktion kann nur das zugehörige
montierte Werkzeug bestätigt werden, niemals eine leere Maschine oder ein anderes Werkzeug.
Laufende Rüstvorgänge müssen zuerst beendet oder abgebrochen werden.

Es werden keine alten Werkzeugnummern ungeprüft zu bestätigten Beständen umgewandelt.
Als schonender Übergang bleibt ein bisheriger Start bei noch nie bestätigtem Altbestand
möglich, aber deutlich als **ungeprüft** gekennzeichnet; aus der Buchung entsteht keine
Montagebestätigung. Sobald Bestand bestätigt wurde, gelten die Prüfungen gegen leer,
falsches Werkzeug und fremde Belegung. Nach einem neu dokumentierten Rüstabbruch ist
die Prüfung zwingend. Bitte Erstbestände zeitnah bestätigen.

## Planung und Schutz

Ein bestätigtes montiertes Werkzeug bleibt auch ohne laufenden Auftrag auf dieser
Maschine gebunden. Dasselbe Werkzeug kann nicht gleichzeitig auf einer zweiten Maschine
bestätigt oder zum Rüsten reserviert werden. Die Planung warnt vor fremder Belegung und
vor Werkzeugwechseln an einer bereits gerüsteten Maschine. Planzeiten sind weiter
Annahmen; weder Abrüsten noch Folgestarts werden automatisch ausgelöst. Eventuelle
Abrüst-/Wechselzeiten müssen in der Planung fachlich berücksichtigt werden, statt sie
ungefragt aus historischen Mittelwerten zu erfinden.

Bestand und Rüstvorgänge werden mit demselben maschinenübergreifenden Datenbank-Lock
wie Produktionsbefehle verarbeitet. UUID-Wiederholschutz, Versionsprüfung, CSRF und
Rollenrechte bleiben wirksam. Ein Fehler rollt Buchung, Bestand, Vorgang und Audit zusammen
zurück. Werkzeugnummern mit Bestand/Rüsthistorie dürfen nicht geändert oder gelöscht
werden; Bezeichnung und Status sind weiterhin pflegbar.

Die Bestandsprüfung verwendet die vorhandenen Rechte **Produktion ansehen** und
**Rüstvorgänge erfassen** (`production.view` / `production.setup`). Für Pausieren und
Abbrechen ist weiterhin das Stopp-Recht nötig, für Entstören das bestehende Entstörrecht.
Es werden keine neuen Rechte automatisch vergeben. Keine elektrische Maschinensteuerung,
kein Not-Halt und keine Sicherheitsfreigabe.

## Installation

ZIP entpacken, Dateien mit gleicher Ordnerstruktur in das bestehende GitHub-Repository
hochladen. Im Handy-Terminal diese eine Zeile ausführen:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_tool_mount.sh
```

Das Skript prüft die Struktur, stoppt den Dienst, sichert die SQLite-Datenbank unter
`/home/factoryos/backups/tool_mount_...`, legt nur die beiden neuen Tabellen
`machine_tool_states` und `setup_operations` an und startet den Dienst wieder.
Keine Altbuchungen, Aufträge, Werkzeugbestände oder Rollen werden automatisch geändert.
Bei einem Upgradefehler bleibt der Dienst zur Prüfung gestoppt; Fehlerausgabe weitergeben.
Groq-Schlüssel, DuckDNS und Tailscale bleiben unverändert. Danach Seiten neu laden und
den Erstbestand je Maschine vor Ort bestätigen.

## Tests

Isolierte Datenbanktests für Rüsten/Abrüsten, Stoppen/Auftragsabschluss mit montiertem
Werkzeug, Pausen und Störungsunterbrechungen, Abbruch/Bestandsprüfung, konkrete Zeitrechnung,
unpassendes Werkzeug, doppelte Belegung, historische Daten, Formular/CSRF/Rechte,
Wiederholschutz, Werkzeugidentität sowie Timeline/Planhinweise. Parallele Bestätigungen
und Rüststarts für dasselbe Werkzeug mit unabhängigen SQLite-Sitzungen: ein Gewinner,
keine Doppelbelegung und kein Deadlock. Vorhandene Maschinen-, Abschluss-, Planungs-,
Störungs- und Berechtigungstests wurden erneut ausgeführt. Kein Test an echter Maschine
und keine Prüfung auf einem echten Android-Gerät.
