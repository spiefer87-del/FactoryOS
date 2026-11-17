# Überschneidungen direkt prüfen und korrigieren

Vollständige Dateien mit Ordnerstruktur nach GitHub übernehmen. Anschließend:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_booking_review.sh
```

Kein Reset, keine automatische Änderung bestehender Buchungen. Der Installer sichert vorher die Datenbank. nginx, OCR, Lager und Werkzeugbestand bleiben unverändert.

Die Überschneidungsmeldung der Startzeitkorrektur verlinkt für Nutzer mit `production.view` direkt auf die betroffene Buchung. Ohne Leserecht bleibt die Meldung ohne Link. Benutzertexte werden escaped.

Die Buchungsprüfung zeigt Auftrag, Maschine, Werkzeug, Zeiten und Ersteller. Laufende Produktions-/Musterungsbuchungen verweisen auf die bereits vorhandene Startzeitkorrektur. Abgeschlossene PROD-, MUSTER- und FREI-Zeitbuchungen ohne Mengenmeldungen, Abschluss, Sperrstatus oder Fremdschlüsselverknüpfungen können mit `production.edit_booking_time` verschoben werden. Start und Ende werden in Europe/Berlin eingegeben; Überlappung und Sommer-/Winterzeit werden geprüft. Andere Fachvorgänge bleiben geschützt.

Das neue Recht **Falsche Zeitbuchungen stornieren** (`production.cancel_booking`) muss Fachrollen bewusst zugewiesen werden. Stornieren ist kein spurloses Löschen: Eine falsche Buchung bekommt Nullzeit und Typ STORNO, behält ihre ID und zählt nicht mehr zur Timeline oder Laufzeit. Originaldaten, Benutzer und Begründung stehen im allgemeinen Änderungsprotokoll. Ein Auftragsabschluss wird dadurch nicht aufgehoben, Mengen und Lagerbuchungen werden nie mitgelöscht. Es gibt kein automatisches Wiederherstellen; eine Gegenkorrektur ist fachlich zu klären.

Jede Änderung erfordert Begründung, Vorschau und Bestätigung. CSRF, serverseitige Rechteprüfung, Maschinensteuerungssperre und erneute Abhängigkeits-/Versionsprüfung schützen vor konkurrierenden Änderungen. Laufende Buchungen müssen regulär gestoppt werden. Buchungen mit Mengenmeldungen oder Rüst-/Planverknüpfungen müssen zuerst im jeweiligen Fachablauf geklärt werden; dieser Patch umgeht diese Schutzregeln nicht.

Automatisierte Prüfungen erfolgen mit synthetischen Daten. Nach Installation bitte den konkreten Konflikt im Browser erneut prüfen. Die bisher eingegebene Startzeit muss nach Änderungen anderer Buchungen gegebenenfalls neu geprüft werden.
