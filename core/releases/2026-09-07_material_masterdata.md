# FactoryOS Release 2026-09-07 – Materialstammdaten

## Funktionsumfang

- Neues Stammdatenmodul mit Übersicht, Anlage, Bearbeitung, Detailansicht und Archivierung.
- Saubere Trennung in Kunststoffmaterial, Betriebsstoff und Hilfsstoff.
- Kunststoffauswahl mit gebräuchlichen Kurzzeichen und ausgeschriebenen Werkstoffnamen.
- Kunststoffabhängige Felder für Dichte, MFR, Trocknung sowie Verarbeitungs- und Werkzeugtemperatur.
- Lager-, Bestands- und Gefahrstoffangaben.
- Vorbereitung des späteren Lieferantenmoduls durch Lieferantenname, Lieferanten-Materialnummer und ein noch unverknüpftes `supplier_id`-Feld.
- Dokumentablage je Materialnummer für Datenblätter, Sicherheitsdatenblätter, Zertifikate, sonstige Dokumente und Historie.
- Excel-Export und -Import verwenden dasselbe technische Tabellenblatt `Materialien`. Ein Export kann direkt wieder importiert werden.
- Die leere Excel-Vorlage enthält Dropdown-Listen und Feldhinweise, aber keine erfundenen Betriebsdaten.

## Ablagestruktur

```text
instance/storage/
└── Stammdaten/
    └── Materialien/
        ├── <Materialnummer>/
        │   ├── Datenblaetter/
        │   ├── Sicherheitsdatenblaetter/
        │   ├── Zertifikate/
        │   ├── Sonstige_Dokumente/
        │   └── Historie/
        └── _Archiv/
            └── Geloeschte_Materialien/
```

## Datenbank-Upgrade

Das Upgrade ist absichtlich unabhängig von der vorhandenen Alembic-Historie und kann gefahrlos mehrfach ausgeführt werden:

```bash
./venv/bin/python scripts/upgrade_material_masterdata.py
```

Es legt die Tabelle `materials` an, ergänzt die Materialberechtigungen und weist sie der Rolle `admin` zu.
