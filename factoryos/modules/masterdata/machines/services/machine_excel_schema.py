"""One column contract shared by export, import and blank template."""
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from factoryos.modules.masterdata.shared.constants import MACHINE_TYPES, MACHINE_STATUSES

KEYS = """machine_no external_machine_no name description machine_type manufacturer model serial_no build_year controller_type automation_type operating_hours last_service_at next_service_at location machine_status clamping_force_kn tie_bar_width_mm tie_bar_height_mm min_mold_height_mm max_mold_height_mm opening_stroke_mm ejector_stroke_mm max_tool_weight_kg screw_diameter_mm max_shot_weight_g max_injection_pressure_bar heating_zones nozzle_radius_mm nozzle_diameter_mm""".split()
HEADERS = [
    "Maschinennummer", "Externe Maschinennummer", "Maschinenname", "Beschreibung",
    "Maschinentyp", "Hersteller", "Modell", "Seriennummer", "Baujahr", "Steuerung",
    "Automation", "Betriebsstunden", "Letzte Wartung", "Nächste Wartung", "Standort",
    "Status", "Schließkraft kN", "Holmabstand Breite mm", "Holmabstand Höhe mm",
    "Min. Werkzeughöhe mm", "Max. Werkzeughöhe mm", "Öffnungshub mm", "Auswerferhub mm",
    "Max. Werkzeuggewicht kg", "Schneckendurchmesser mm", "Max. Schussgewicht g",
    "Max. Einspritzdruck bar", "Heizzonen", "Düsenradius mm", "Düsendurchmesser mm",
]

def normalize(value):
    return " ".join(str(value or "").replace("\ufeff", "").replace("\xa0", " ").split()).lower()

HEADER_KEYS = {normalize(alias): key for key, label in zip(KEYS, HEADERS) for alias in (key, label)}

def machine_workbook(machines=()):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Maschinen"
    sheet.append(HEADERS)
    for machine in machines:
        values = []
        for index, key in enumerate(KEYS):
            source = machine if index < 16 else machine.injection_molding_data
            value = getattr(source, key, None)
            if key == "machine_type": value = MACHINE_TYPES.get(value, value)
            if key == "machine_status": value = MACHINE_STATUSES.get(value, value)
            values.append(value)
        sheet.append(values)
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str): cell.data_type = "s"
            if cell.column in (1, 2, 8): cell.number_format = "@"
            if cell.column in (13, 14): cell.number_format = "DD.MM.YYYY HH:MM:SS"
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F2937")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for index, label in enumerate(HEADERS, 1):
        sheet.column_dimensions[get_column_letter(index)].width = min(max(len(label)+2, 20), 38)
    notes = workbook.create_sheet("Hinweise")
    for message in (
        "Export und Importvorlage haben identische Spalten. Datenblatt: Maschinen.",
        "Maschinennummer ist Pflicht; vorhandene Nummern werden aktualisiert.",
        "Die leere Vorlage enthält absichtlich keine importierbare Beispielmaschine.",
        "Leere Zellen löschen optionale Werte. Nicht vorhandene Spalten bleiben unverändert.",
        "Nummern mit führenden Nullen als Text eingeben. Keine Excel-Formeln verwenden.",
        "Datum: Excel-Datum oder TT.MM.JJJJ HH:MM:SS; Zahlen auch mit Dezimalkomma.",
        "Spritzgießdaten gelten nur für Spritzgießmaschinen.",
        "Maschinentypen: " + ", ".join(MACHINE_TYPES.values()),
        "Status: " + ", ".join(MACHINE_STATUSES.values()),
        "Bisherige deutsche Exporte und interne Spaltennamen bleiben importierbar.",
    ): notes.append([message])
    notes.column_dimensions["A"].width = 120
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output
