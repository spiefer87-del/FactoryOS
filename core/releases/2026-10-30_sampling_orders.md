# Musterungsaufträge

Basis: GitHub main b78885afcaf8984ef726ebdc1422797fc223726b.
Vollständige Ersatzdateien für diesen Patch. Kein kompletter Repository-Snapshot.

## Datenstruktur

Neue Tabellen sampling_orders und sampling_checks. Ein Musterungsauftrag
verweist eindeutig auf einen vorhandenen Auftragskopf (orders).
Die Struktur von orders und vorhandene Aufträge werden nicht verändert.
Musterungen erscheinen getrennt in Aufträge > Musterungsaufträge.
Die bisherige Auftragsübersicht enthält weiterhin die bisherigen Aufträge,
nicht die neu angelegten Musterungen. is_project bleibt unverändert.

Ein Anlass pro Musterung: Erstbemusterung/Neuwerkzeug, Werkzeugreparatur,
Werkzeugänderung, Artikeländerung, Werkstoffänderung, Farbänderung, Sonstiges.
Der Anlass bleibt nach Anlage unveränderlich.
Nachbemusterungen sind eigene Aufträge mit unveränderlichem Vorgängerbezug.

Stammdaten werden bewusst ausgewählt und als Auftragsstand gespeichert.
Änderungen an Vorgaben und Ist-Werten schreiben keine Stammdaten zurück.
Artikel, Kunden, Materialien, Werkzeuge und Maschinen mit Musterungsbezug
können über die bestehenden Löschrouten nicht mehr gelöscht werden.

## Bearbeitung

Entwurf > In Bearbeitung > In Prüfung > erfolgreicher Abschluss.
Zusätzlicher Status: Nachbemusterung erforderlich.
Entwurf und Nachbemusterung sind im Maschinen Booking gesperrt.
Zuordnung der Maschine vor Booking erforderlich. Musterungsbuchungen
verwenden den Prozess MUSTER und sind in der Timeline gekennzeichnet.
Auf der Musterungsdetailseite kann die Buchung beendet werden.
Die Zykluszeit-Prognose regulärer Produktion wird nicht ungeprüft für
Musterungen verwendet. Musterungsdauer und Rüstzeit werden separat dokumentiert.

Vorgaben, Änderungen, Ergebnisse, Abweichungen, Trocknung, Farbe, Zusätze,
Gewichte, Zykluszeit, Nester, Verpackung, Zählerstände und Dokumentencheckliste
orientieren sich an der bereitgestellten Vorlage. Kein Excel-Import/-Export,
keine Änderung der Excel-Dateien und noch kein Druck-/Etikettenexport.
Dokumentnachweise werden zunächst als Referenz/Notiz erfasst, nicht als Upload.

## Abschlussregeln dieser ersten Umsetzung

Für alle erfolgreichen Abschlüsse: Status In Prüfung, keine laufende Buchung,
Artikel/Werkzeug/Rohstoff/Maschine zugeordnet, durchführende Person, Datum und
Ergebnis dokumentiert. Interne Freigabe muss erteilt sein. Alle internen
Prüf-/Dokumentenpunkte müssen erledigt oder begründet nicht erforderlich sein.
Erledigte, erteilte und abgelehnte Prüfpunkte benötigen ein Datum.
Nicht erforderliche und abgelehnte Punkte benötigen eine Begründung.

Folgemusterung: Kundenentscheidung darf offen bleiben. Anzeige lautet dann
Intern erfolgreich abgeschlossen; externe Freigabe bleibt separat sichtbar.
Die Kundenentscheidung kann danach separat nachgetragen werden, ohne den
internen Abschluss zu verändern.

Erstbemusterung: Zusätzlich Kunde, Prüfumfang, kavitätenbezogene Ergebnisse
und Prüfbericht-/EMPB-Referenz erforderlich. Maßprüfung, Funktion, EMPB,
Musterversand und Zeichnungsprüfung dürfen nicht auf nicht erforderlich
gesetzt sein. Interne UND externe Freigabe müssen erteilt sein.
Ein bloßer interner Abschluss ist ausgeschlossen.

Nach Abschluss ist der Auftragsinhalt schreibgeschützt; neue Versuche werden
über Nachbemusterung angelegt. Keine Löschfunktion für Musterungen.
Der bestehende globale Auftragseditor darf die Abschlussprüfung nicht umgehen.

## Zugriff und Nachvollziehbarkeit

Wie bisherige Aufträge für angemeldete Nutzer zugänglich.
Es wird keine zusätzliche Freigabe-Rollenmatrix eingeführt.
Prüfpunktänderungen erfassen Datum und angemeldeten Bearbeiter.
Änderungen/Abschlüsse werden im vorhandenen ChangeLog protokolliert.
Neue Mutationen sind mit Sitzungstoken abgesichert.
Versionsprüfung verhindert versehentliches Überschreiben durch ältere Formulare.

## Installation

ZIP entpacken, Dateien mit Pfaden ins Repository hochladen und committen:

    cd /home/factoryos/FactoryOS
    git status --short
    git pull --ff-only origin main
    bash scripts/install_sampling_orders.sh

Das Skript erkennt übliche Python-Umgebungen und prüft die vorhandene
SQLite-Struktur. Danach stoppt es den Dienst, sichert instance/factoryos.db
samt gegebenenfalls vorhandenen WAL/SHM-Dateien und legt die neuen Tabellen an.
Upgrade ist wiederholbar. Bei Fehler bleibt der Dienst gestoppt.
Bei Git-Konflikten nicht überschreiben, sondern die Ausgabe weitergeben.

Erfolgsmeldung: Musterungsauftrags-Upgrade erfolgreich abgeschlossen.
Danach muss factoryos.service active (running) sein.

## Tests

Isolierte SQLite-Testdatenbank, reale Flask-Routen und Services:
Upgrade zweimal, bestehender Auftrag erhalten, alle Anlässe, Formular-/Detail-
und Listenrendering, ungültige Referenzen/Status/Nummern, Sitzungstoken,
Anlasssperre, Versionsschutz, Erstbemusterung ohne/mit Kundenfreigabe,
intern abgeschlossene Folgemusterung, spätere Kundenentscheidung, Booking
Start/Stop, Stammdaten-Snapshots und Löschschutz.
Die fremde Bildanalyse wird im Test ausgeklammert.
Keine reale Raspberry-Datenbank eingesehen. Visuelle Browserprüfung
hier nicht ausgeführt; HTML-Rendering technisch geprüft.
