# Auftragsstatistiken und protokollierte Startzeitkorrektur

Basis: main cdb30b0. Vollständige Ersatzdateien und neue Dateien.
Voraussetzung: bisheriger ERP-Import- und Soll-Zykluszeit-Patch sind installiert.

## Direkt beim Öffnen eines Auftrags

- Voraussichtliches Produktionsende, klar als Schätzung gekennzeichnet.
- Frühester Produktionsstart und Liste der Produktions-/Musterungsbuchungen.
- Sollmenge, gemeldete Gutmenge, gemeldeter Ausschuss, gemeldeter Fortschritt und Restmenge.
- Reine Soll-Gesamtlaufzeit, gebuchte Brutto-Produktionszeit und kalenderbereinigte Zeit.
- Gebuchte Pausendauer und rechnerische Restlaufzeit.
- Rechnerischer Material-Gesamt-/Restbedarf, Verbrauchsschätzung aus Mengenmeldungen,
  Hauptrohstoff- und Farbbatchbedarf sowie verwendetes Schussgewicht.
- ERP-Angaben sind weiterhin vorhanden, aber für mehr Platz standardmäßig eingeklappt.
- Aktivitäten und Startzeitkorrekturen bleiben aufklappbar.
- Dieselben Statistiken sind auch auf Musterungsdetails eingebunden.

## Wichtige Unterscheidung: Meldung und Schätzung

Gemeldete Gut-/Ausschussmengen kommen ausschließlich aus bestehenden Mengenbuchungen.
Es werden weder Stückzahlen noch Materialverbrauch automatisch gebucht.

Ohne Mengenmeldung wird die Endprognose nach Solltempo seit erfasstem Produktionsstart
berechnet. Nach einer Mengenmeldung beginnt die zusätzliche Zeitschätzung erst ab
deren Zeitstempel. Bereits gemeldete Produktion wird so nicht doppelt gezählt.
Zeitlich werden nur die zum Auftrag gebuchten Produktionsintervalle innerhalb des
bestehenden Arbeitskalenders angerechnet. Gebuchte Pausen und Wochenendschließungen
sowie hinterlegte Feiertage/Brückentage zählen nicht als verfügbare Produktionszeit.

Damit ändert eine rückdatierte Startzeit bei fehlenden Mengenmeldungen auch die
Laufzeit und Endprognose. Nach einer neueren Mengenmeldung bleibt diese der
maßgebliche Fortschrittsanker. Die Prognose unterstellt Solltempo ohne zusätzlichen
künftigen Ausschuss. Sie misst keine Maschine und kann ungebuchte Unterbrechungen,
deaktivierte Nester oder zusätzliche QS-/Rüstzeiten nicht erkennen.

Ein rechnerisch erreichtes Sollende bedeutet NICHT, dass die reale Menge fertig ist.
Ein Auftrag wird dadurch niemals automatisch abgeschlossen.
Pausierte/nicht gestartete Aufträge zeigen keinen verbindlichen Endtermin; ein
gesonderter Hinweis nennt die Prognose bei sofortigem Start/Fortsetzen.

## Materialrechnung

Gesamtbedarf = aufgerundete Sollstückzahl / Teile je Zyklus × Schussgewicht / 1000.
Das Schussgewicht gilt für den gesamten Schuss einschließlich Anguss.
Restbedarf aus Gutmeldungen und bisheriger Verbrauch aus Gut-/Ausschussmeldungen
werden ausdrücklich als rechnerische Werte beschriftet.

Die App hat noch keine echten Materialverbrauchsbuchungen. Deshalb wird kein
gemessener Ist-Verbrauch behauptet. Fehlt ein Schussgewicht, erscheint „nicht
berechenbar“ statt einer erfundenen Menge. Anfahr-/Reinigungsschüsse und zukünftiger
Ausschuss sind nicht geplant.

Bei normalen Aufträgen dient der aktuelle Artikelstamm als Schätzgrundlage.
Bei Musterungen werden vorhandene Schussgewichtsangaben bzw. gespeicherte
Artikelreferenzen verwendet. Abweichende ERP-/Artikelrohstoffe werden angezeigt.
Die Artikelrezeptur ist keine eingefrorene Auftragsrezeptur.

Bei Batchzugabe bezogen auf Hauptrohstoffgewicht:
Hauptrohstoff = Gesamtmischung / (1 + Prozent / 100).
Batch = Gesamtmischung minus Hauptrohstoff.
Bei unvollständigen Batchangaben bleibt die Aufteilung unbekannt.

## Startzeit ändern

Admin oder eine Rolle mit dem neuen Recht „Startzeiten korrigieren“
(production.edit_booking_time) sieht den Button direkt in der Auftragsübersicht
der Detailseite und an der entsprechenden Buchung in der Timeline.

1. Startzeit korrigieren öffnen.
2. Tatsächliche Zeit in Europe/Berlin und eine Begründung eingeben.
3. Vorschau prüfen.
4. Änderung verbindlich bestätigen.

- Speicherung intern in UTC; lokale Ein-/Ausgabe berücksichtigt Sommer-/Winterzeit.
- Nicht existierende Uhrzeiten bei Zeitumstellung werden abgelehnt.
- Bei der doppelten Herbststunde ist eine ausdrückliche Auswahl erforderlich.
- Zukunftsstart, Start nach Buchungsende und Überschneidungen mit realen Produktions-,
  Rüst-, Pausen- oder Störungsbuchungen werden abgelehnt.
- Bereits beendete automatisch erfasste FREI-Intervalle können beim Rückdatieren
  gekürzt werden. Vollständig überdeckte Frei-Phasen bleiben als Nullzeit-Datensatz
  erhalten und werden nicht als Timeline-Balken angezeigt. Nichts wird gelöscht.
- Bei späterem Start werden keine neuen Frei-Zeiten erfunden.
- Begründung, Bearbeiter, Änderungszeitpunkt, alter/neuer UTC-Start und Anpassungen
  an Frei-Intervallen werden protokolliert.
- Start-/Endstatus, Gut-/Ausschussmengen, ERP-Daten und andere reale Buchungen bleiben unverändert.
- Abgeschlossene Musterungen bleiben auch für Admin schreibgeschützt.
- CSRF, serverseitige Vorschauprüfung, Revision und Schreibsperre schützen die Bestätigung.

Die Timeline-Achse bleibt wie bisher in UTC. Endprognosen und neue Detail-/Korrekturzeiten
werden ausdrücklich in Europe/Berlin beschriftet. Der bestehende Kalender wird
nicht still in eine andere Zeitzone migriert.

## Installation

Dateien unter denselben relativen Pfaden in GitHub übernehmen und committen.

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_order_statistics.sh
```

Das Skript prüft die vorhandene Struktur, stoppt FactoryOS, sichert die SQLite-Datenbank
einschließlich vorhandener WAL-/SHM-Dateien und registriert nur das neue Recht.
Keine neuen Tabellen/Spalten und keine automatischen Rechtezuweisungen an Fachrollen.
Bei Fehlern bleibt der Dienst gestoppt, damit die Ursache geprüft werden kann.

Admin hat den bestehenden Vollzugriff. Für andere Benutzer unter Rechteverwaltung >
Produktion das Recht Startzeiten korrigieren bewusst zuweisen. Die normalen Lese-
rechte für Aufträge bzw. Produktion gelten zusätzlich für die jeweiligen Übersichtsseiten.
Keine neue APK nötig; in der App Neu laden wählen.
DuckDNS und Tailscale bleiben unverändert.

## Tests

scripts/test_order_statistics.py:
Rechte/CSRF/Vorschau, explizite Rollenzuweisung, zwei Stunden Rückdatierung mit
verändertem Endtermin, Auditlog, Frei-Zeitkürzung und Nullzeit-Erhaltung,
Überschneidungs-/Zukunftsschutz, gesperrte abgeschlossene Musterung, veraltete
Bestätigung, Zeitumstellungen, Wochenende/Feiertag, Verbrauchs-/Batchrechnung,
fehlendes Schussgewicht und keine erfundenen Mengenbuchungen.

Zusätzlich vorhandene Soll-Zykluszeit-, Musterungs- und Sicherheitsregressionen.
Tests gegen isolierte SQLite-Datenbank, nicht gegen die produktive Raspberry-Datenbank.
Keine echte Android-/Browser-Layoutprüfung in dieser Umgebung.
