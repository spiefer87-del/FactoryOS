# Produktions-Endzeit korrigieren

GitHub-Basis: spiefer87-del/FactoryOS, main,
Commit 18e5b18ab435e0c50a915df6e610493f92d799d2.

Das ZIP enthält vollständige geänderte und neue Dateien mit ihren
Repository-Pfaden, keinen einzelnen Diff. ZIP entpacken und die enthaltenen
Dateien mit Ordnerstruktur in das Stammverzeichnis des GitHub-Repositorys
übernehmen, bestehende Dateien ersetzen und committen.

## Bedienung

1. Auftrag öffnen. In der Statistik auf „Endzeit der letzten Produktionsbuchung
   korrigieren“ klicken, oder bei einer einzelnen beendeten Produktionsbuchung
   „Endzeit korrigieren“ wählen.
2. Auf der bisherigen Startzeit-Seite lässt sich bei beendeten Buchungen direkt
   zur Endzeit wechseln. Auch die Buchungsprüfung enthält einen Einstieg.
3. Tatsächliches Ende in Europe/Berlin eingeben und begründen.
4. „Änderung prüfen“ zeigt die alte und neue Endzeit sowie gegebenenfalls die
   Anpassung der anschließenden Frei-Zeit. Erst danach verbindlich bestätigen.

Startzeit und Endzeit werden getrennt korrigiert. Die Endzeitkorrektur gilt für
beendete Produktions-/Musterungs-Startbuchungen und funktioniert auch bei
abgeschlossenen Fertigungsaufträgen. Abgeschlossene Musterungen bleiben über
ihren Freigabeablauf schreibgeschützt. Eine laufende Buchung muss weiterhin
regulär beendet werden, bevor ihre Endzeit korrigiert werden kann.

## Berechnung und Protokoll

- Eine unmittelbar anschließende Frei-Buchung wird in derselben Transaktion
  auf den neuen Beginn angepasst. Bei späterem Produktionsende wird sie
  verkürzt; bei früherem Ende beginnt sie früher. Vollständig verdrängte,
  beendete Frei-Intervalle bleiben mit Nullzeit und Änderungsnachweis erhalten.
- Echte Folgebuchungen und andere Maschinenaktivitäten werden nicht verschoben.
  Überschneidungen, einschließlich paralleler Produktion desselben Auftrags auf
  anderen Maschinen, sind gesperrt. Ohne anschließende Frei-Buchung wird keine
  zusätzliche Aktivität erzeugt; eine Lücke kann bestehen bleiben.
- Produktionsende, Timeline, gebuchte Laufzeiten und Sollabweichung verwenden
  die korrigierte Buchung. Vorhandene Abweichungsbestätigungen werden wie bisher
  anhand ihrer Zeitbasis geprüft, ihre Historie bleibt erhalten.
- Gut-/Ausschussmengen, Auftragsstatus und Abschlussbestätigung werden nicht
  verändert. Der ursprüngliche Bestätigungszeitpunkt bleibt als Erfassungszeit
  erhalten; die Auftragsseite bezeichnet ihn deshalb als „Abschluss erfasst am“.
- Die Aktivitäten von Auftrag und Maschine sowie bei offenen Musterungen deren
  Protokoll enthalten Begründung, Benutzer, alte/neue Endzeit und die betroffene
  Frei-Zeit. Uhrzeiten dieser Korrekturen werden sekundengenau lesbar dargestellt.
- Die Korrektur nutzt das vorhandene Recht production.edit_booking_time;
  dessen angezeigter Name lautet jetzt „Start- und Endzeiten korrigieren“.
  Vorhandene Rollenzuordnungen bleiben erhalten. Keine neue Datenbankstruktur
  und kein Migrationsbefehl erforderlich.

## Raspberry Pi

Nach Upload und Commit auf GitHub:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Danach die Auftrags- bzw. Korrekturseite neu laden.

## Prüfung

Mit isolierten SQLite-Testdatenbanken erfolgreich geprüft:

```bash
python scripts/test_booking_end_time.py
python scripts/test_order_statistics.py
python scripts/test_order_completion.py
python scripts/test_booking_review.py
python scripts/test_activity_review.py
python scripts/test_production_deviations.py
python scripts/test_runtime_overrun.py
python scripts/test_permission_labels.py
python scripts/test_access_control.py
```

Der neue Test umfasst frühere/spätere Endzeiten, offene und geschlossene
Frei-Intervalle bis Nullzeit, echte Folgebuchungen und parallele Produktion,
unveränderte Abschlussmengen und Bestätigungszeitpunkte, korrigierte Laufzeit
und Timeline, lesbare Aktivitäten einschließlich Sekunden, Vorschau-Bindung,
CSRF, explizite Benutzerrechte, veraltete Revisionen, offene Buchungen,
abgeschlossene Musterungen und Sommer-/Winterzeit-Eingaben. Die Tests ändern
keine produktive Datenbank. HTTP-Ausgabe und Formulare sind geprüft; ein
grafischer Android-Browsertest war in dieser Umgebung nicht möglich.
