# FactoryOS – Fertigungsaufträge vollständig abschließen

Stand: 16.11.2026. Basis: GitHub main `681ccae76c2064fb9752e70353638c7df675d190`.
ZIP mit vollständigen geänderten/neuen Dateien; kein Diff.

## An der Maschine

In der Maschinenbedienung auf **Vorgang stoppen** klicken. Die nächste Seite
unterscheidet ausdrücklich:

- **Nur stoppen – Auftrag bleibt offen**: Produktionsbuchung beenden, Auftrag
  später weiterbearbeiten. Wie bisher mit Stoppbegründung.
- **Auftrag abschließen · Stückzahl bestätigen**: Endmengen prüfen, ausdrücklich
  bestätigen und den Fertigungsauftrag endgültig schließen.

Beim Abschluss die **Gesamtgutmenge** und **Gesamtausschussmenge seit Auftragsbeginn**
eingeben, keine zusätzlichen Mengen. Die Sollmenge wird nicht automatisch als Istmenge
vorgegeben; auch die Laufzeitschätzung gilt nicht als Mengenmeldung.
Bereits tatsächlich gemeldete Mengen werden als Orientierung angezeigt.

Die Endmeldung zählt nicht zusätzlich zu früheren Meldungen: Sie ist der bestätigte
Gesamtstand für die Auftragsstatistik. Eine Unterschreitung schon gemeldeter Mengen
ist gesperrt und muss vorher fachlich korrigiert werden. Überproduktion ist erlaubt.
Bei Untermenge sind eine eigene Bestätigung und mindestens fünf Zeichen Begründung nötig.

Der Abschluss beendet die zugehörige Produktions-/Pausenbuchung und hebt ihre
Auftragsreservierung auf. Die Maschine erhält eine freie Zustandsbuchung. Ein Werkzeug
wird dadurch nicht als abgerüstet behandelt. Kein Folgeauftrag startet automatisch.
Störungen, Rüstvorgänge und Wartungen werden nicht stillschweigend beendet oder quittiert:
Solche Fälle sind vorher regulär zu klären.

## Im Büro

Unter **Auftrag bearbeiten** gibt es einen eigenen Abschnitt **Auftrag abschließen**.
Zusätzlich ist die Funktion direkt in der Auftragsdetailansicht erreichbar.
Sie funktioniert auch bei einem nie gestarteten oder bereits gestoppten Auftrag.
Ein Büroabschluss ohne aktive Maschine erzeugt keine erfundenen Produktionszeiten.
Nicht gespeicherte Änderungen am Bearbeitungsformular bitte vorher speichern.

Offene oder gestartete Planpositionen dieses Auftrags werden beim Abschluss aus der
weiteren Planung genommen (Status `completed`). Andere Aufträge bleiben unverändert.
Musterungsaufträge behalten ihren vorhandenen Prüf-/Freigabeablauf; Projekte werden
nicht als stückbezogene Fertigungsaufträge abgeschlossen. Gesperrte, stornierte oder
bereits abgeschlossene Aufträge werden nicht erneut abgeschlossen.

## Nachvollziehbarkeit und Schutz

- Abschlussdatensatz mit Benutzer, Zeitpunkt, Quelle (Maschine/Büro), Sollmenge,
  vorherigem Meldestand, bestätigten Endmengen und Begründung.
- Auftragsstatus `finished`; Anzeige der Endmeldung im Auftrag und Verwendung in
  den Statistiken. Keine weitere Endzeitprognose für abgeschlossene Aufträge.
- Laufende Maschinenbuchung, Reservierung, Status, Planung und Protokoll werden
  in einer Transaktion geändert.
- Gleiche Befehlskennung erzeugt bei einer Wiederholung keinen zweiten Abschluss.
- Veraltete Auftrags-/Mengen-/Maschinenstände werden abgewiesen. Nach einem
  Konflikt ausdrücklich neu laden; Endmengen werden nicht automatisch bestätigt.
- Kein Wiederöffnen durch den normalen Status-Dropdown. Abgeschlossene Aufträge
  bleiben schreibgeschützt und gegen Löschen im normalen Auftragsworkflow geschützt.
- Keine elektrische Maschinensteuerung, kein Not-Halt und keine Sicherheitsfreigabe.

## Rechte

Die beiden neuen Rechte werden angelegt, aber keiner normalen Rolle automatisch zugewiesen:

- **Aufträge an der Maschine abschließen** (`production.complete_order`): für Einrichter,
  zusammen mit **Produktion ansehen**. Abschluss nur des zugeordneten Maschinenauftrags.
- **Aufträge im Büro abschließen** (`orders.complete`): für das Büro/Fertigungsleitung.
  Einrichtungsrechte und Büroabschluss sind voneinander getrennt.

Der Administrator hat Zugriff. Rollenrechte nach der Installation in der Rechteverwaltung
bewusst zuweisen. Ein reines Bearbeitungs- oder Stopp-Recht genügt nicht zum endgültigen Abschluss.

## Installation am Raspberry

ZIP entpacken und Dateien mit gleicher Ordnerstruktur in das bestehende GitHub-Repository
hochladen. Danach im Handy-Terminal diese eine Zeile ausführen:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_order_completion.sh
```

Das Installationsskript prüft die Voraussetzungen, stoppt den Dienst, sichert die
SQLite-Datenbank unter `/home/factoryos/backups/order_completion_...`, ergänzt ausschließlich
die neue Tabelle `order_completions` und die beiden Rechte und startet den Dienst wieder.
Bestehende Aufträge, Mengenmeldungen und Zeitbuchungen werden nicht umgeschrieben.
Bei fehlgeschlagenem Upgrade bleibt der Dienst zur Prüfung gestoppt; Fehlerausgabe weitergeben.
Groq-Schlüssel, DuckDNS und Tailscale werden nicht verändert. Anschließend Seiten neu laden.

## Geprüft

Automatisierte Tests auf isolierten Datenbanken: normaler Abschluss, Pausen-/Büroabschluss,
nie gestartete und geplante Aufträge, tatsächliche Gesamtmengen ohne Doppelzählung,
Mengenfehler/Untermenge/Bestätigung, Störungsblockade, unveränderte Buchung bei Fehlern,
CSRF und getrennte Rechte, Menü und Formularseiten, Abschlussnachweis, Wiederholschutz,
keine automatischen Folgestarts, Schreib-/Löschschutz und Upgrade-Wiederholung.
Parallele Abschlüsse und Start gegen Büroabschluss wurden mit unabhängigen SQLite-Sitzungen
getestet: nur ein Vorgang gewinnt, kein Deadlock oder verlorener Auftragsstand.
Vorhandene Maschinenbedienungs-, Formular-, Planungs- und Berechtigungstests laufen ebenfalls durch.
Keine Prüfung an echter Maschine oder auf einem echten Android-Gerät.
