# Auftragsplanung für die Fertigungsleitung

Basis: main f68e442. Vollständige geänderte/neue Dateien in Originalpfaden.

## Bedienung

Produktion → Auftragsplanung oder Button oben in der Maschinen-Timeline.
Je Maschine eine gespeicherte Reihenfolge offener Fertigungsaufträge bzw.
freigegebener, dieser Maschine zugeordneter Musterungsaufträge.

- Ungeplanten Auftrag per Suche/Auswahl hinten anhängen.
- Zusätzliche Rüstzeit in Minuten, frühesten Planbeginn und Notiz pflegen.
- Mit ↑ / ↓ oder am Desktop per Drag-and-drop innerhalb der Maschine umsortieren.
- Auf andere aktive Maschine verschieben; dort wird hinten angehängt.
- Aus Planung nehmen archiviert den Eintrag und löscht keinen Auftrag.
- Bei unbekanntem Vorgangsende manuelle zukünftige Verfügbarkeit mit Begründung.
- Leseansicht für Produktion; Änderungen nur mit neuem Recht „Aufträge planen“.
- Änderungsprotokoll mit Benutzer und Zeitpunkt.

## Berechnung und Grenzen

Rollierende, nicht eingefrorene Vorschau: Anfang ist jetzt bzw. eine spätere
Zeitvorgabe. Laufende Produktion belegt ihre Maschine bis zur aktuellen
kalenderbereinigten Endprognose. Danach folgt die gespeicherte Reihenfolge.
Zusätzliche Rüstzeit und Produktion überspringen den vorhandenen Arbeitskalender
einschließlich Wochenenden, Feiertagen und Brückentagen. Zeitberechnungen des
Kalenders bleiben unverändert; keine Migration seiner bestehenden Zeitzonen.
Eingaben und Anzeige verwenden Europe/Berlin, Speicherung UTC.

Geplante Produktionsdauer = aufgerundete Restzyklen (gemeldete Restmenge geteilt
durch Kavitäten, auf ganze Zyklen aufgerundet) × Soll-Zykluszeit des Auftrags. Nur bestätigte Gutmeldungen reduzieren die
Restmenge eines Warteschlangenauftrags; vergangene unbestätigte Zykluszeit wird
dort nicht als produzierte Stückzahl abgezogen. Fehlende Kavitäten führen zu
sichtbar vorläufiger Annahme 1 Teil/Zyklus. Fehlender Sollzyklus/Sollmenge wird
beim Einplanen abgewiesen. Keine zusätzliche Rüstzeit wird automatisch geraten;
0 Minuten ist eine ausdrückliche Planungsannahme.

Bei Störung/Pause/Wartung/Rüsten oder unbrauchbarer Endprognose bleibt die
nachfolgende Reihe ohne Termin, bis eine begründete zukünftige
Verfügbarkeitsannahme vorliegt. Diese beendet keinen realen Vorgang. Abgelaufene
Annahmen geben eine noch blockierte Maschine nicht automatisch frei. Laufendes
Rüsten desselben ersten Planauftrags wird nicht nochmals vollständig addiert;
die Verfügbarkeitsannahme umfasst in diesem Fall dessen restliches Rüsten.
Mehrfach aktive Altbuchungen und inaktive Maschinen bleiben gesperrt.

Ungültige Einträge blockieren nachfolgende Termine, statt scheinbar präzise
Termine zu erfinden. Vorschauhorizont maximal 366 Tage. Werkzeugüberschneidungen
zwischen geplanten Maschinen und mit bekannten laufenden Werkzeugbelegungen
werden gewarnt, nicht automatisch gelöst. Fehlt eine eindeutige Werkzeugbindung,
ist keine vollständige Ressourcenprüfung möglich. Maschineneignung, Personal,
Materialverfügbarkeit, QS-/Kundenfreigaben und Ausschuss sind nicht automatisch
optimiert. Keine Lieferterminzusage oder fertige Feinplanung/APS.

## Timeline und Maschinenbedienung

Geplante Produktion blau gestrichelt, geplantes Rüsten gelb gestrichelt; klar
von Ist-Buchungen und Prognosen laufender Aufträge getrennt. Kalenderfreie
Zeitabschnitte erhalten keine geplanten Arbeitsbalken. Klick öffnet die Planung.
Zeitfenster/Datumswahl und aktuelle Maschinenbedienung bleiben erhalten.

Kein automatischer Start. „Manuellen Start öffnen“ führt ins vorhandene Bedienfeld.
Der erste Planauftrag wird vorausgewählt. Die App prüft beim Produktionsstart
Maschine und Reihenfolge. Abweichungen zuerst durch die Fertigungsleitung
umplanen; bei einer vorhandenen Warteschlange kann kein anderer Auftrag still
dazwischengestartet werden. Geplante Uhrzeiten sind Vorschau, keine automatische
Sperr-/Freigabeuhr. Andere Fach-/Musterungsprüfungen bleiben unverändert.

Beim tatsächlichen Start werden Planeintrag (started), echte Startbuchung,
Versionszähler, Befehlsquittung und Protokoll atomar gespeichert. Der Auftrag
selbst wird dadurch nicht fertiggemeldet. Wird er später vorzeitig gestoppt,
kann die verbleibende Menge nach Beenden aller aktiven Reservierungen erneut
eingeplant werden. Archivierte Planeinträge bleiben erhalten.

## Konsistenz / Rechte / Datenbank

Neu: production_planning_state, machine_planning_settings, production_plan_entries.
Ein partieller Unique-Index verhindert denselben Auftrag mehrfach in offenen
Warteschlangen. Planung und Maschinenbefehle verwenden dieselbe Schreibsperre.
Planversion verhindert Überschreiben veralteter Fenster; konkurrierendes Planen
und Starten auf anderen Maschinen wird geprüft. CSRF und aktionsbezogene Rechte
werden serverseitig geprüft. Änderungen an Rollenrechten sind nicht automatisch.

Neues Recht `production.plan` für die Rolle der Fertigungsleitung bewusst
aktivieren, zusätzlich `production.view`. Admin hat Zugriff. Produktion kann
lesen und mit ihrem Startrecht den vorgesehenen Auftrag starten, aber nicht
eigenmächtig die Reihenfolge ändern. Stammdaten mit Planungshistorie werden
nicht gelöscht. Geplante Musterungen müssen vor erfolgreichem Abschluss
gestartet oder aus der Planung genommen werden.

## Installation

Voraussetzung: Maschinenbedienung, Störungsauswahl und Timeline-Zeitfenster
vollständig installiert. Dateien mit Originalpfaden in GitHub übernehmen, dann:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_order_planning.sh
```

Installer prüft Struktur, stoppt den Dienst, sichert instance/factoryos.db
einschließlich WAL/SHM und legt neue Tabellen/Recht an. Bei Fehler bleibt der
Dienst gestoppt. Vorhandene Aufträge, Buchungen, Mengen und Rollenzuweisungen
bleiben unverändert. Abweichende DB-Pfade müssen vor Installation berücksichtigt
werden. Keine neue APK; nach Installation App neu laden.

Erste Abnahme: Zwei Testaufträge an eine Testmaschine hängen, Rüstzeit eintragen,
Reihenfolge tauschen, 30-Tage-Timeline prüfen, ersten Auftrag manuell starten und
kontrollieren, dass nur dessen Eintrag die Warteschlange verlässt. Danach
Störung/Verfügbarkeitsannahme und Werkzeugkonflikt auf Testdaten durchspielen.

## Prüfung

Isolierte synthetische SQLite-Integrationstests: Upgrade aus altem Schema und
Wiederholung, Reihenfolge/Drag-Protokoll/Transfer/Archiv, kalenderbereinigte Rüst-
und Produktionszeiten, Restmengen, Brückentage, unbekannte Enden, manuelle
Verfügbarkeit, Werkzeugwarnungen, atomarer manueller Start, veraltete Versionen,
vollständiger Rollback bei Protokollfehlern, CSRF/Rechte, Löschschutz und
schreibfreie Vorschau. Konkurrenztests mit unabhängigen SQLite-Sitzungen für
Plan/Plan und Plan/manueller Start. Bestehende Maschinenbedienungs-, Timeline-,
Störungs- und Rechte-Regressionsprüfungen sowie Syntax/Whitespace/ZIP-Integrität.
Keine produktive Datenbank oder Hardware und kein Browser-/Touchscreen-Render-Test.
