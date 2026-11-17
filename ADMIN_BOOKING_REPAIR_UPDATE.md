# Zentrale Buchungsübersicht und Administrator-Reparatur

Dieses Paket ergänzt die installierte Buchungsprüfung. Dateien mit unveränderter Ordnerstruktur nach GitHub übernehmen. Danach:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_admin_booking_repair.sh
```

Kein Reset, keine automatische Korrektur oder Löschung vorhandener Buchungen. Vor dem Neustart wird die Datenbank unter `/home/factoryos/backups/admin_booking_repair_DATUM_UHRZEIT` gesichert. Bei Installationsfehlern nach dem Stoppen bleibt der Dienst zur Prüfung gestoppt.

## Konkrete Ursache bei #25

Die Buchung war abgeschlossen, ebenso der Rüstnachweis. Ihre Endzeiten unterschieden sich jedoch um rund 19 Sekunden. Die bisherige Prüfung verlangte identische Grenzen und meldete deshalb irreführend „offen oder mehrteilig“. Der normale Prüfmodus bleibt bewusst restriktiv. Der neue ausdrücklich bezeichnete Administrator-Reparaturmodus kann solche widersprüchlichen Alt-/Testdaten bearbeiten.

## Bedienung

Unter Produktion gibt es die Kachel **Buchungsübersicht**. Diese ist auch als persönliche Dashboard-Kachel auswählbar. Die Tabelle sucht nach Buchungs-ID, Maschine, Auftrag, Werkzeug und Vorgang, ist serverseitig paginiert und auf Mobilgeräten horizontal verschiebbar. Pfad: `/production/booking/journal`.

Auf „Buchung prüfen“ erscheint für Systemadministratoren immer **Administrator-Reparatur / vollständig löschen**, auch wenn der normale Modus gesperrt ist. Bei #25 führt der Button auf `/production/booking/25/repair`.

Der Sondermodus ist ausschließlich für aktive Benutzer mit aktiver Rolle `admin` verfügbar. Das bloße Zuweisen eines normalen Bearbeitungs-/Löschrechts an andere Rollen reicht nicht aus. Die Durchsetzung erfolgt sowohl zentral als auch in der Route und vor der tatsächlichen Änderung.

## Reparaturumfang und Schutz

- Start und Ende aller Buchungstypen lassen sich korrigieren; leeres Ende bedeutet laufend. Maschine, Auftrag, Werkzeug und Vorgangsart werden nicht stillschweigend umgehängt. Zeiten in Europe/Berlin mit gesonderter Behandlung der doppelten Stunde, intern UTC.
- Auch abgeschlossene Aufträge, vorhandene Mengen und widersprüchliche Rüstzeitgrenzen sperren den Systemadministrator nicht pauschal. Ihre Auswirkungen erscheinen in der Vorschau. Bestätigte Mengen, Lagerbuchungen, Auftragsstatus und Freigaben bleiben unverändert und müssen separat fachlich kontrolliert werden.
- Bereits bestehende Überschneidungen dürfen ausdrücklich bestätigt werden, damit eine mehrstufige Bereinigung überhaupt möglich ist. Die Warnung nennt die betroffenen Buchungs-IDs. Es darf keine zusätzliche zweite laufende Buchung angelegt werden. Ungültige Zeitbereiche und Zukunftszeiten bleiben abgewiesen.
- Zugehörige Rüstnachweise erhalten aus den verbleibenden passenden Rüst-Teilbuchungen neue Zeitgrenzen und gegebenenfalls eine neue erste Teilbuchung. Abweichende ursprüngliche Grenzen werden protokolliert. Andere Teilbuchungen werden nicht verschoben. Bei einem offenen Nachweis ohne verbleibende laufende Teilbuchung wird der Nachweis administrativ als **abgebrochen**, nicht als erfolgreich abgeschlossen, geschlossen.
- Vollständiges Löschen entfernt den Datensatz tatsächlich aus den Zeitbuchungen. Ein dann leerer Rüstnachweis wird mitgelöscht, ein Nachweis mit verbleibenden Teilbuchungen neu begrenzt. Eine bekannte Planreferenz wird entfernt und mit ihrem ursprünglichen Wert protokolliert; der Planstatus wird nicht erfunden oder automatisch zurückgesetzt.
- Unbekannte Fremdschlüsselabhängigkeiten und widersprüchliche Werkzeug-/Auftragszuordnungen bleiben Stop-Bedingungen. Sie können nicht sicher durch pauschales Löschen behoben werden. Es wird keine unbekannte Tabelle oder Fremdbuchung mitgelöscht.
- Beim Eingriff in laufende Buchungen wird die Bedienversion erhöht; eine dazugehörige Fortsetzungsreservierung wird bei Beendigung/Löschung entfernt. Bei einem administrativ beendeten/gelöschten offenen Rüstvorgang ist eine erneute Werkzeugbestätigung erforderlich. Der tatsächliche Status montiert/leer wird nicht automatisch geändert. Kein elektrischer Maschinenstopp, keine neu erfundene Frei-Zeit.
- Nullzeit wird als STORNO gewertet. Wird eine STORNO-Buchung ausdrücklich auf eine positive oder laufende Zeit gesetzt, wird sie als START reaktiviert; dies steht in der Vorschau.

Jede Reparatur braucht eine Begründung, eine unveränderte Vorschau und eine ausdrückliche Bestätigung. CSRF-Prüfung, Versionsvergleich und die gemeinsame Maschinensteuerungssperre schützen vor konkurrierenden Änderungen. Änderungen werden atomar gespeichert; bei einem Fehler wird zurückgerollt. Die ursprüngliche Buchung, Rüstnachweise, gelöste Referenzen, Bedienzustand und Warnungen stehen im allgemeinen Änderungsprotokoll unter `booking_admin_repair` mit dem ausführenden Benutzer.

**Keine automatische Rückgängig-Funktion:** Es gibt keinen Papierkorb. Eine Wiederherstellung muss gezielt aus den protokollierten Originaldaten oder der Sicherung erfolgen. Nicht einfach eine alte Gesamtdatenbank über spätere produktive Buchungen kopieren. Eine Zeitreparatur ersetzt keine Korrektur bestätigter Mengen oder des tatsächlichen Werkzeugbestands.

Automatisierte Tests verwenden künstliche Daten, darunter den konkreten Fall unterschiedlicher Endzeiten. Nach Installation bitte #25 über den neuen Admin-Button prüfen, die richtige Zeit oder Löschen auswählen, Auswirkungen lesen und erst dann verbindlich bestätigen.
