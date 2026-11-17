# Rüstzeitkorrektur und vollständiges Löschen direkt in der Buchungsprüfung

Voraussetzung ist das vorherige Paket zur Buchungsprüfung. Dateien mit Ordnerstruktur nach GitHub übernehmen, danach:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_setup_booking_review.sh
```

Kein Reset und keine automatische Änderung vorhandener Buchungen. Der Installer sichert zuerst die Datenbank und registriert zusätzliche Rechte, ohne sie Fachrollen automatisch zuzuweisen. Bei Fehlern nach Dienststopp bleibt der Dienst zur Prüfung gestoppt.

## Rüst-/Abrüstzeiten

Auf „Buchung prüfen“ lassen sich jetzt auch abgeschlossene RUEST-/ABRUEST-Zeiten korrigieren. Dies gilt für alte Einzelbuchungen ohne separaten Rüstnachweis sowie konsistente, abgeschlossene einfache Rüstnachweise. Ein eindeutig verknüpfter Nachweis wird atomar mit den neuen Start-/Endzeiten aktualisiert. Er erhält keine andere Werkzeug-, Maschinen- oder Auftragszuordnung. Der aktuelle montierte Werkzeugbestand und ursprüngliche Maschinen-Befehlsprotokolle bleiben unverändert.

Neues Recht: **Rüst- und Abrüstzeiten korrigieren** (`production.edit_setup_time`). Zusätzlich ist Lesezugriff `production.view` nötig. Das allgemeine Startzeitrecht allein berechtigt nicht zur Rüstzeitkorrektur.

Mehrteilige oder unterbrochene Rüstvorgänge werden nicht als einzelne Buchung verändert: Alle Teilzeiten müssten gemeinsam korrigiert werden. Offene, inkonsistente oder mit weiteren Fachvorgängen verbundene Nachweise bleiben mit Erklärung gesperrt. Ebenso bleiben abgeschlossene/gesperrte Aufträge und Aufträge mit bestätigten Mengen geschützt. Vorschau, Begründung, Sommer-/Winterzeit, Überschneidung und konkurrierende Änderungen werden geprüft.

## Vollständiges Löschen

Neues separates Recht: **Zeitbuchungen vollständig löschen** (`production.delete_booking`). In der Buchungsprüfung erscheint die Aktion nur bei passendem Recht und zulässiger Buchung. Sie benötigt Begründung, Vorschau und eine zusätzliche ausdrückliche Bestätigung. Das ist wirklich ein Löschen der Zeitbuchung, nicht bloß Nullzeit/Storno. Ein eindeutig zugehöriger einfacher abgeschlossener Rüstnachweis wird in derselben Transaktion mitgelöscht. Fremdverweise und Mengen-/Abschlussdaten verhindern die Löschung. Bereits stornierte, ansonsten ungeschützte Buchungen können ebenfalls vollständig entfernt werden.

Die ursprünglichen Buchungs- und gegebenenfalls Rüstnachweisdaten bleiben mit Benutzer und Grund im allgemeinen Änderungsprotokoll erhalten; Sicherungskopien bleiben unverändert. Es gibt keinen Papierkorb oder automatischen Wiederherstellen-Button. Die Wiederherstellung muss fachlich aus Protokoll/Sicherung erfolgen, ohne spätere Daten zu überschreiben. Die Buchung ist danach nicht mehr in den Zeitbuchungen oder der Timeline vorhanden.

**Wichtig:** Löschen oder Verschieben einer historischen Rüstzeit rüstet kein Werkzeug physisch ab und setzt die Maschine nicht automatisch frei. Ein falscher tatsächlicher Werkzeugbestand muss separat bestätigt/korrigiert werden. Mengen, Lagerbuchungen und Aufträge werden nicht mitgelöscht. An bisher vorhandenen Benutzerrechten ändert sich nichts.

Automatisiert mit künstlichen Daten geprüft: Einzel-/Legacy-Rüstzeiten, atomare Nachweis-Korrektur, Versionskonflikt bei Nachweisänderung, gesondertes Löschrecht, Vorschau und Bestätigung, physische Löschung mit Audit, unveränderter Werkzeugbestand und bestehende Buchungsprüfung. Abschließend bitte den konkreten Fall #25 auf eurem Server prüfen.
