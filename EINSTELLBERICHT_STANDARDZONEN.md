# FactoryOS – Standard-Heizzonen und PDF-Dateinamen

Stand: 16.11.2026. Basis: GitHub main `61812c005d2a01f973d4237f5c9d401131a85a25`.
Vollständige geänderte/neue Dateien, kein Diff.

## Standardvorlage Zylindertemperaturen

Neue Einstellberichte enthalten automatisch folgende Zonen in dieser Reihenfolge:

1. DH
2. MH 3
3. MH 2
4. MH 1
5. Einzug

Die Zonen sind als „Aktiv: Ja“ vorgeschlagen. Das Profil bleibt offen und muss
an der tatsächlichen Maschine geprüft und bestätigt werden. Soll-/Istwerte und
beide Toleranzen bleiben bewusst leer. Die Temperaturen und Toleranzen aus dem
Beispielfoto sind keine allgemeingültigen Maschinenparameter und werden nicht übernommen.

Alle bisherigen Funktionen bleiben verfügbar: Zonen umbenennen, deaktivieren,
entfernen, zusätzliche Zonen hinzufügen und Reihenfolge anpassen. Zusätzlich
zum bisherigen Pfeil nach oben gibt es nun einen Pfeil nach unten.

Bestehende Berichte werden nicht verändert. Ältere leere Entwürfe bieten im
Zylinderprofil den Button **Standardzonen einfügen**. Sind bereits Zonen vorhanden,
erscheint kein überschreibender Vorlagenbutton. Absichtlich gelöschte Zonen werden
beim Schrittwechsel oder erneuten Öffnen nicht ungefragt wieder angelegt.
Neue Fassungen aus bestehenden Berichten behalten deren Profil und Reihenfolge;
die vorhandene erneute Prüfpflicht bleibt erhalten. Abgeschlossene Berichte bleiben schreibgeschützt.

## PDF-Zuordnung

Der Downloadname beginnt mit der Werkzeugnummer, zum Beispiel:

`COR249_Einstellbericht_7_Stand_15.pdf`

Berichts-ID und Stand verhindern Verwechslungen zwischen Fassungen. Auch der
Dokumenttitel in den PDF-Metadaten enthält jetzt die Werkzeugnummer. Die Nummer
stammt aus dem gespeicherten Zuordnungsstand des Berichts; fehlt sie dort, wird
die zugehörige Werkzeugnummer verwendet. Für Dateinamen ungeeignete Zeichen
werden sicher bereinigt. FB-18-Layout und Berichtsinhalte bleiben unverändert.

## Installation am Raspberry

ZIP entpacken und Dateien mit unveränderter Ordnerstruktur in das bestehende
GitHub-Repository hochladen. Anschließend im Handy-Terminal diese eine Zeile ausführen:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_setup_report_fix.sh
```

Wizard danach neu laden. Es sind keine Datenbankmigration, Änderungen an
Stammdaten, Groq-Schlüssel, DuckDNS oder Tailscale notwendig.

## Prüfungen

Automatisierte Tests: frische unabhängige Vorlagen, Reihenfolge und leere Werte,
Ergänzen/Umbenennen/Löschen/Verschieben, keine Überschreibung vorhandener oder
abgeschlossener Berichte, keine Wiederanlage gelöschter Zonen, unveränderte
Handeingabe-/Fotoübernahme-/Feldhinweise, geschützter PDF-Download, sicherer
werkzeugbezogener Dateiname und PDF-Dokumenttitel. Die Tests nutzen isolierte
Datenbanken und simulierte Groq-Antworten, keine echten externen Anfragen.
Keine Prüfung auf einem echten Android-Gerät.
