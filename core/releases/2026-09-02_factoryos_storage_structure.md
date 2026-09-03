# FactoryOS Release 2026-09-02 – strukturierte Dateiablage

## Ziel

Werkzeugbilder, Dokumente, Wartungsunterlagen, Historien sowie Bilder und PDFs
von Werkzeugfehlermeldungen werden außerhalb des Git-Quellcodes in einer
gemeinsamen, backup-fähigen Struktur gespeichert.

Standardpfad auf dem Raspberry Pi:

`/home/factoryos/FactoryOS/instance/storage`

Der Pfad kann bei Bedarf über die Umgebungsvariable
`FACTORYOS_STORAGE_ROOT` auf ein anderes Laufwerk oder einen eingehängten
Datenträger gelegt werden.

## Ordnerstruktur

```text
instance/storage/
└── Stammdaten/
    └── Werkzeuge/
        ├── WZ-10001/
        │   ├── Werkzeugbilder/
        │   ├── Dokumente/
        │   ├── Wartung/
        │   ├── Historie/
        │   └── Werkzeugfehlermeldungen/
        │       └── FM26-001/
        │           ├── Revision_01/
        │           │   ├── Bilder/
        │           │   └── PDF/
        │           └── Revision_02/
        │               ├── Bilder/
        │               └── PDF/
        ├── _Archiv/
        └── _Unzugeordnet/
```

## Funktionsumfang

- Neue Werkzeugbilder landen direkt im Werkzeugordner.
- PDFs und Dokumente können in `Dokumente`, `Wartung` oder `Historie`
  hochgeladen, angezeigt und heruntergeladen werden.
- Aus der aktiven Dokumentablage entfernte Dateien werden in die Historie
  verschoben und nicht sofort vernichtet.
- Jede Werkzeugfehlermeldung und jede Revision erhält einen eigenen Ordner.
- Temporäre Fehlerbilder werden nach dem Anlegen der Fehlermeldung automatisch
  in deren richtigen Werkzeug-/Revisionsordner verschoben.
- Beim Freigeben und beim manuellen PDF-Export wird das PDF dauerhaft im
  Revisionsordner archiviert.
- Neue Revisionen erhalten physisch getrennte Bildkopien.
- Beim Löschen eines Werkzeugs wird dessen kompletter Ordner unter `_Archiv`
  verschoben.
- Alte `static/uploads`-Pfade bleiben bis zur Migration lesbar.
- Dateien der neuen Ablage sind nur für angemeldete Benutzer abrufbar.

## Migration des Altbestands

Die Migration arbeitet zunächst als Vorschau. Erst `--apply` kopiert Dateien,
aktualisiert die Datenbankpfade und entfernt die verifizierten Altdateien nach
erfolgreichem Datenbank-Commit.

```bash
cd /home/factoryos/FactoryOS
./venv/bin/python scripts/migrate_factoryos_storage.py
./venv/bin/python scripts/migrate_factoryos_storage.py --apply
```

Nicht zuordenbare Dateien aus dem bisherigen gemeinsamen
`static/uploads/tool_errors`-Ordner werden unter `_Unzugeordnet` als
`_Altbestand` gesichert.

## Datenbank

Es werden keine neuen Tabellen oder Spalten benötigt. Ein SQL- oder
Alembic-Schritt ist für dieses Release nicht erforderlich.

## Backup

Für ein vollständiges FactoryOS-Datenbackup müssen mindestens diese beiden
Bestandteile gemeinsam gesichert werden:

- `instance/factoryos.db`
- `instance/storage/`

Die konkrete automatische Sicherung auf USB, NAS oder einen zweiten Rechner
kann als nächster, getrennt konfigurierbarer Schritt aufgebaut werden.
