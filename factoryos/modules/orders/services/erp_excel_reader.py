"""Read the ERP browse export without executing formulas or modifying the source."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from zipfile import ZipFile, BadZipFile
import re
import math
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 500
MAX_COLUMNS = 100
ALIASES = {
    "FA-Nummer": "order_no", "Auftragsnummer": "order_no", "order_no": "order_no",
    "Artikelnummer": "article_no", "article": "article_no",
    "Bezeichnung": "article_name", "Artikelname": "article_name",
    "Fertigungsmenge": "quantity", "Menge": "quantity", "target_qty": "quantity",
    "Kundennummer": "customer_no", "Kundenkurzname": "customer_name",
    "Werkzeug": "tool", "Werkzeugnummer": "tool",
    "Material": "material", "Rohstoff": "material", "Maschine": "machine",
    "Liefertermin": "delivery_date", "Liefer-KW": "delivery_week",
    "Mengeneinheit": "unit", "Status": "erp_status", "Auftragsart": "erp_type",
    "Startdatum": "planned_start", "Enddatum": "planned_end",
    "Zykluszeit": "cycle_time_s", "Zykluszeit (s)": "cycle_time_s",
    "Soll-Zykluszeit": "cycle_time_s", "Soll-Zykluszeit (s)": "cycle_time_s",
    "cycle_time_s": "cycle_time_s",
}

def clean(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, (int, float)) and value == int(value):
        return str(int(value))
    return str(value).replace("_x000D_", "").replace("\r\n", "\n").strip()

def normalized(value):
    return " ".join(clean(value).replace("\ufeff", "").split()).casefold()

def quantity(value):
    text = clean(value).replace(" ", "")
    # German grouped notation is accepted only when its grouping is unambiguous.
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", text):
        text = text.replace(".", "")
    try:
        number = Decimal(text.replace(",", "."))
        if not number.is_finite() or number != number.to_integral_value() or not 0 < number <= 2147483647:
            raise ValueError()
        return int(number)
    except (InvalidOperation, ValueError):
        raise ValueError("Fertigungsmenge muss eine positive ganze Stückzahl sein.")

def split_reference(value):
    text = clean(value)
    first = text.split("\n")[0].strip()
    parts = re.split(r"\s+[–—-]\s+", first, maxsplit=1)
    return (parts[0], parts[1] if len(parts) == 2 else "")

def iso_date(value):
    text = clean(value)
    if not text:
        return ""
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], pattern).date().isoformat()
        except ValueError:
            pass
    raise ValueError("Datum bitte als JJJJ-MM-TT oder TT.MM.JJJJ eingeben.")

def identifier(cell):
    value = cell.value
    text = clean(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value) or value != int(value) or abs(value) >= 10 ** 15:
            raise ValueError(f"Zeile {cell.row}: Nummer in {cell.column_letter} bitte als Text speichern.")
        if re.fullmatch(r"0{2,}", cell.number_format):
            text = str(int(value)).zfill(len(cell.number_format))
    return text

def read_erp_excel(file, sheet_name=""):
    raw = file.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Datei zu groß. Maximal 5 MB erlaubt.")
    try:
        with ZipFile(BytesIO(raw)) as archive:
            if len(archive.infolist()) > 1000 or sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
                raise ValueError("Die entpackte Excel-Datei ist zu groß.")
        workbook = load_workbook(BytesIO(raw), read_only=True, data_only=False, keep_links=False)
    except (BadZipFile, KeyError, OSError) as error:
        raise ValueError("Die Datei ist keine lesbare XLSX-Datei.") from error
    try:
        mapping = {normalized(label): key for label, key in ALIASES.items()}
        candidates = []
        for sheet in workbook.worksheets:
            if sheet_name and sheet.title != sheet_name:
                continue
            if sheet.max_column > MAX_COLUMNS or sheet.max_row > MAX_ROWS + 20:
                continue
            for index, row in enumerate(sheet.iter_rows(max_row=min(sheet.max_row, 20)), 1):
                keys = [mapping.get(normalized(cell.value), "") for cell in row]
                if {"order_no", "article_no", "quantity"}.issubset(keys):
                    candidates.append((sheet, index, keys, [clean(cell.value) for cell in row]))
                    break
        if len(candidates) != 1:
            raise ValueError("Kein eindeutiges Auftragsblatt erkannt. Erwartet: FA-Nummer, Artikelnummer, Fertigungsmenge. Bei mehreren Blättern bitte den Blattnamen angeben.")
        sheet, header_row, keys, labels = candidates[0]
        recognized = [key for key in keys if key]
        if len(recognized) != len(set(recognized)):
            raise ValueError("Eine erkannte Datenspalte ist doppelt vorhanden.")
        rows = []
        for excel_row, cells in enumerate(sheet.iter_rows(min_row=header_row + 1), header_row + 1):
            if not any(cell.value is not None and clean(cell.value) for cell in cells):
                continue
            if len(rows) >= MAX_ROWS:
                raise ValueError("Pro Import sind maximal 500 Auftragszeilen erlaubt.")
            if any(cell.data_type in ("f", "e") for cell in cells):
                raise ValueError(f"Zeile {excel_row}: Formeln/Excel-Fehler bitte durch geprüfte Werte ersetzen.")
            source, data = [], {}
            for index, cell in enumerate(cells):
                value = identifier(cell) if keys[index] in ("order_no", "article_no", "customer_no", "tool", "material", "machine") else clean(cell.value)
                if len(value) > 10000:
                    raise ValueError(f"Zeile {excel_row}: Einzelwert zu lang (maximal 10.000 Zeichen).")
                column = get_column_letter(index + 1)
                source.append({"column": column, "label": labels[index] or column, "value": value})
                if keys[index]: data[keys[index]] = value
            tool_no, tool_name = split_reference(data.get("tool"))
            material_no, material_name = split_reference(data.get("material"))
            machine_no, _ = split_reference(data.get("machine"))
            fields = {
                "order_no": data.get("order_no", ""), "article_no": data.get("article_no", ""),
                "article_name": data.get("article_name", "").split("\n")[0],
                "quantity": data.get("quantity", ""), "customer_no": data.get("customer_no", ""),
                "cycle_time_s": data.get("cycle_time_s", ""),
                "customer_name": data.get("customer_name", ""), "tool_no": tool_no,
                "tool_name": tool_name, "material_no": material_no, "material_name": material_name,
                "machine_no": machine_no, "delivery_date": data.get("delivery_date", ""),
                "delivery_week": data.get("delivery_week", ""), "unit": data.get("unit", ""),
                "material_type": "plastic",
            }
            rows.append({"excel_row": excel_row, "source": source, "fields": fields,
                         "choices": {}, "state": "pending", "acknowledged": False})
        if not rows:
            raise ValueError("Die Datei enthält keine Auftragszeilen.")
        return sheet.title, rows
    finally:
        workbook.close()
