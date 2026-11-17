# Laufzeitabweichungen in Timeline und Auftrag

Dateien mit Ordnerstruktur nach GitHub übernehmen, danach:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_production_deviations.sh
```

Der Installer sichert die vorhandene Datenbank, ergänzt eine Tabelle für bestätigte Abweichungen und ein Recht. Keine Rücksetzung von Aufträgen, Lager oder Buchungen. Bei Fehler nach Dienststopp bleibt FactoryOS zur Prüfung gestoppt.

## Erkennung und Darstellung

Bereits beim Erreichen der Sollzeit erscheint orange „Rechnerisches Sollende erreicht – Mengen und Abschluss prüfen“. Erst jenseits der unten beschriebenen Toleranz wird daraus der rote Überlaufhinweis. Ist die Gut-Sollmenge bereits gemeldet, läuft die Buchung aber weiter, wird dies unabhängig von der Toleranz rot als fehlender Abschluss markiert – nicht als bewiesene langsamere Zykluszeit.

- **Rot:** Der Auftrag läuft noch und seine gebuchte Produktionszeit im Arbeitskalender überschreitet die reine Soll-Laufzeit der Gesamtmenge um mehr als 5 %, mindestens 60 Sekunden. Meldung: „Soll-Laufzeit überschritten – Auftrag läuft weiter“. Ohne Mengenmeldungen beweist dies keine tatsächliche langsamere Zykluszeit. Fehlende Meldungen, falsche Zeiten, Unterbrechungen oder Sollvorgaben kommen ebenfalls in Betracht.
- Nach Abschluss mit gemeldeter Gut-/Ausschussmenge werden Sollzyklen für die tatsächlich gemeldete Gesamtmenge mit der gebuchten Zeit verglichen. **Rot** bei mehr als 5 % / mindestens 60 Sekunden längerer Zeit; **Orange** bei entsprechend kürzerer Zeit. Schnellere Produktion wird nicht aus einer laufenden Buchung ohne belastbare Abschlussmengen behauptet.
- Fehlende Kavitäten sind ausdrücklich als Annahme gekennzeichnet. Der aktive Überlaufhinweis kann dann vorläufig sein; ein schnellerer/langsamerer Abschlussvergleich wird ohne gültige Kavitäten nicht erzeugt. Fehlende Soll-Zykluszeit/Sollmenge oder Projektaufträge bekommen keine solche Bewertung.
- Die Timeline zeigt betroffene Balken farbig mit Warnsymbol und „prüfen“ bzw. „begründet“. Bei laufender Produktion steht die Warnung zusätzlich an der Maschinenzeile. Im Fertigungs-/Musterungsauftrag erscheint eine farbige Kennzahlenkarte. Die Legende erklärt die Farben.
- Sobald die rechnerische Restlaufzeit null ist, wird nicht ständig „jetzt“ als neuer Fertigstellungstermin angezeigt. Stattdessen bleibt der tatsächliche Endtermin offen. Der Auftrag wird nie automatisch beendet und die Maschine nicht gestoppt.

Berechnet wird aus **Buchungen, Produktionskalender, Sollwerten und gemeldeten Mengen**, nicht aus Maschinensignalen. Es gibt keinen Sensor für Ist-Zykluszeit. Die Anzeige ist ein Prüfhinweis, keine automatisch festgestellte Ursache. Künftiger Ausschuss, produktionsfreie Zeit, fehlende Störungsbuchungen oder veränderte aktive Nester können das Ergebnis beeinflussen.

## Bestätigung und Auftragsdokumentation

Das neue Recht **Laufzeitabweichungen begründen** (`production.confirm_deviation`) unter Administration vergeben. Zusätzlich braucht der Nutzer Leserecht für den jeweiligen Fertigungs-/Musterungsauftrag. Administratoren haben Zugriff.

„Abweichung prüfen und begründen“ öffnet eine Auswahl typischer Gründe: bewusst erhöhte/reduzierte Zykluszeit, Qualitätsprobleme, fehlende Störungsbuchung, abweichende Nester, Ausschuss, verspätete Mengenmeldung, fehlerhafte Zeit-/Sollvorgaben oder Sonstiges. Eine konkrete Erläuterung mit 10–2000 Zeichen und eine ausdrückliche Prüfbestätigung sind erforderlich.

Die Bestätigung wird als neuer Datensatz am Auftrag und im Änderungsprotokoll gespeichert: Benutzer, Zeitpunkt, Grund und Kennzahlenstand einschließlich der zugrunde liegenden Buchungen, Mengen, Sollwerte und Kalenderbasis. Frühere Bestätigungen bleiben erhalten, auch wenn sich die Werte später ändern. Die letzten zehn stehen in der Auftragsansicht. Neue bestätigte Daten werden durch weitere Bestätigungen nicht überschrieben.

Ändern sich Sollwert, Stückzahlen, Kavitäten, Kalender oder Buchungszeiten, gilt die alte Bestätigung nicht automatisch für die neue Grundlage. Die laufende Zeit darf weiterwachsen, ohne jede Sekunde eine neue Bestätigung anzufordern: Die Begründung gilt für die gleiche Datengrundlage und zeigt ihren gespeicherten Zeitstand. Die Farbe bleibt sichtbar; eine Begründung beseitigt die Abweichung nicht.

Hinweise werden beim Laden/Neuladen der Timeline und des Auftrags berechnet. Erst die ausdrückliche Bestätigung schreibt einen dauerhaften Abweichungsdatensatz. Lesen erzeugt keine Buchung. Die Bestätigung ist ein eigener fachlicher Arbeitsschritt; sie blockiert keinen notwendigen Maschinenstopp oder Auftragsabschluss. Unbestätigte Gründe erscheinen als offen. Soll-Zykluszeit, Maschinenparameter, Gut-/Ausschussmengen und Auftragsstatus werden nicht verändert.

CSRF, aktuelle Rechte, gesperrte konkurrierende Maschinenänderungen und ein Vergleich der Datengrundlage schützen die Bestätigung. Ein Auftrag mit bestätigter Abweichung bleibt beim normalen Löschen zur Nachverfolgung erhalten. Kein neuer externer Dienst und keine Zusatzkosten für Erkennung.

Automatisiert geprüft: Überlauf ohne erfundene Stückzahlen, keine rollierende Jetzt-Prognose bei Nullrestzeit, Timeline-Farben und Warntext, Gründe/Bestätigung/Rechte/CSRF, neue Datengrundlage macht Bestätigung erneut prüfpflichtig, schnellerer/langsamerer Abschlussvergleich, erhaltene Historie und wiederholbares Upgrade. Zusätzlich laufen die bisherigen Statistik-/Zeitkorrekturtests weiter durch. Nach Installation App neu laden und einen betroffenen Auftrag öffnen.
