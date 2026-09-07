# FactoryOS Release 2026-09-07 – Werkzeugfehlermeldungen Excel-Rundlauf

## Ziel

Export, Import und leere Vorlage verwenden dasselbe Excel-Format. Eine aus
FactoryOS exportierte Werkzeugfehlermeldungsliste kann damit direkt wieder
importiert werden.

## Gemeinsames Tabellenblatt `Tool Errors`

Das verbindliche Import- und Exportformat enthält diese Spalten:

1. `error_no`
2. `revision`
3. `tool_no`
4. `error_type`
5. `description`
6. `tool_status`
7. `order_id`
8. `machine_id`

Die Kombination aus `error_no` und `revision` ist der Importschlüssel.
Bestehende Datensätze werden aktualisiert; neue Datensätze werden als Entwurf
angelegt. Das zugeordnete Werkzeug muss bereits in FactoryOS existieren.

## Weitere Tabellenblätter

- `Übersicht` enthält zusätzliche lesbare System- und Workflowinformationen.
- `Auswahllisten` enthält die Werte für Excel-Dropdowns und ist ausgeblendet.

Die leere Vorlage wird mit demselben Workbook-Generator wie der Export erzeugt
und enthält keine erfundenen Beispieldaten.

## Kompatibilität

Der Import erkennt weiterhin die deutschen Überschriften älterer Exporte sowie
das bisherige technische Importformat.

Zusätzlich wurde der direkte Aufruf von
`scripts/upgrade_material_masterdata.py` repariert, sodass das Skript den
FactoryOS-Projektordner selbstständig in den Python-Suchpfad aufnimmt.
