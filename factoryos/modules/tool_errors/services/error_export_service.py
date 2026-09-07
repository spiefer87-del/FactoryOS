from io import BytesIO

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES
from factoryos.modules.tool_errors.constants import WORKFLOW_STATUSES
from factoryos.modules.tool_errors.models import ToolError


EXPECTED_HEADERS = [
    "error_no",
    "revision",
    "tool_no",
    "error_type",
    "description",
    "tool_status",
    "order_id",
    "machine_id",
]

HEADER_LABELS = {
    "error_no": "FM-Nummer",
    "revision": "Revision",
    "tool_no": "Werkzeugnummer",
    "error_type": "Fehlerart",
    "description": "Beschreibung",
    "tool_status": "Werkzeugstatus",
    "order_id": "Auftrag-ID",
    "machine_id": "Maschinen-ID",
}

HEADER_COMMENTS = {
    "error_no": (
        "Pflichtfeld. Zusammen mit revision bildet die FM-Nummer den "
        "eindeutigen Importschlüssel."
    ),
    "revision": "Positive ganze Zahl; bei leerem Feld wird Revision 1 verwendet.",
    "tool_no": "Pflichtfeld. Das Werkzeug muss in FactoryOS bereits vorhanden sein.",
    "tool_status": "Optional. Zulässige Werte stehen in der Dropdown-Liste.",
    "order_id": "Optional: numerische interne ID des Auftrags.",
    "machine_id": "Optional: numerische interne ID der Maschine.",
}

OVERVIEW_HEADERS = [
    "FM-Nr.",
    "Revision",
    "Aktuelle Revision",
    "Workflow",
    "Workflow intern",
    "Werkzeugnummer",
    "Externe Werkzeugnummer",
    "Werkzeugname",
    "Werkzeugstatus",
    "Fehlerart",
    "Beschreibung",
    "Auftrag",
    "Maschine",
    "Erstellt am",
    "Erstellt von",
    "Freigegeben am",
    "Freigegeben von",
]


def _format_datetime(value):
    return value.strftime("%d.%m.%Y %H:%M") if value else ""


def _bool_label(value):
    return "Ja" if value else "Nein"


def _workflow_label(status):
    return WORKFLOW_STATUSES.get(status, status or "")


def _tool_status_label(status):
    return TOOL_STATUSES.get(status, status or "")


def _autosize_columns(worksheet, labels, maximum=45):
    for index, label in enumerate(labels, start=1):
        maximum_length = len(str(label))
        for cells in worksheet.iter_cols(
            min_col=index,
            max_col=index,
            min_row=2,
            max_row=max(worksheet.max_row, 2),
        ):
            for cell in cells:
                if cell.value is not None:
                    maximum_length = max(maximum_length, len(str(cell.value)))
        worksheet.column_dimensions[get_column_letter(index)].width = min(
            max(maximum_length + 2, 12),
            maximum,
        )


def _style_sheet(worksheet, labels):
    header_fill = PatternFill(fill_type="solid", fgColor="1F2937")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="E5E7EB")
    border = Border(bottom=thin)

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = (
        f"A1:{get_column_letter(len(labels))}{max(worksheet.max_row, 2)}"
    )
    worksheet.row_dimensions[1].height = 30

    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

    for row in worksheet.iter_rows(
        min_row=2,
        max_row=max(worksheet.max_row, 2),
        max_col=len(labels),
    ):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    _autosize_columns(worksheet, labels)


def _get_tool_errors(include_history=False):
    query = ToolError.query.options(
        joinedload(ToolError.tool),
        joinedload(ToolError.reported_by),
        joinedload(ToolError.released_by),
    )

    if not include_history:
        query = query.filter(or_(
            ToolError.is_current.is_(True),
            ToolError.is_current.is_(None),
        ))

    return query.order_by(
        ToolError.error_no.asc(),
        ToolError.revision.asc(),
        ToolError.id.asc(),
    ).all()


def _append_import_export_sheet(workbook, errors):
    worksheet = workbook.active
    worksheet.title = "Tool Errors"
    worksheet.append(EXPECTED_HEADERS)

    for error in errors:
        tool = error.tool
        worksheet.append([
            error.error_no or "",
            error.revision or 1,
            tool.tool_no if tool else "",
            error.error_type or "",
            error.description or "",
            tool.tool_status if tool else "",
            error.order_id if error.order_id is not None else "",
            error.machine_id if error.machine_id is not None else "",
        ])

    _style_sheet(worksheet, EXPECTED_HEADERS)

    required_fill = PatternFill(fill_type="solid", fgColor="FFF2CC")
    for header in ("error_no", "tool_no"):
        cell = worksheet.cell(1, EXPECTED_HEADERS.index(header) + 1)
        cell.fill = required_fill
        cell.font = Font(color="111827", bold=True)

    for index, header in enumerate(EXPECTED_HEADERS, start=1):
        worksheet.cell(1, index).comment = Comment(
            HEADER_COMMENTS.get(header, HEADER_LABELS[header]),
            "FactoryOS",
        )

    revision_column = get_column_letter(EXPECTED_HEADERS.index("revision") + 1)
    revision_validation = DataValidation(
        type="whole",
        operator="between",
        formula1="1",
        formula2="999",
        allow_blank=True,
    )
    revision_validation.error = "Revision muss eine ganze Zahl zwischen 1 und 999 sein."
    revision_validation.showErrorMessage = True
    worksheet.add_data_validation(revision_validation)
    revision_validation.add(f"{revision_column}2:{revision_column}1001")

    status_column = get_column_letter(EXPECTED_HEADERS.index("tool_status") + 1)
    status_validation = DataValidation(
        type="list",
        formula1="=Werkzeugstatus",
        allow_blank=True,
    )
    status_validation.error = "Bitte einen Werkzeugstatus aus der Liste auswählen."
    status_validation.showErrorMessage = True
    worksheet.add_data_validation(status_validation)
    status_validation.add(f"{status_column}2:{status_column}1001")


def _append_overview_sheet(workbook, errors):
    worksheet = workbook.create_sheet("Übersicht")
    worksheet.append(OVERVIEW_HEADERS)

    for error in errors:
        tool = error.tool
        worksheet.append([
            error.error_no or "",
            error.revision or 1,
            _bool_label(error.is_current),
            _workflow_label(error.workflow_status),
            error.workflow_status or "",
            tool.tool_no if tool else "",
            tool.external_tool_no if tool else "",
            tool.name if tool else "",
            _tool_status_label(tool.tool_status) if tool else "",
            error.error_type or "",
            error.description or "",
            error.order_id if error.order_id is not None else "",
            error.machine_id if error.machine_id is not None else "",
            _format_datetime(error.created_at),
            error.reported_by.username if error.reported_by else "",
            _format_datetime(error.released_at),
            error.released_by.username if error.released_by else "",
        ])

    _style_sheet(worksheet, OVERVIEW_HEADERS)

def _append_list_sheet(workbook):
    worksheet = workbook.create_sheet("Auswahllisten")
    worksheet.append(["Werkzeugstatus intern", "Bezeichnung"])

    for key, label in TOOL_STATUSES.items():
        worksheet.append([key, label])

    _style_sheet(
        worksheet,
        ["Werkzeugstatus intern", "Bezeichnung"],
    )

    workbook.defined_names.add(DefinedName(
        "Werkzeugstatus",
        attr_text=f"'Auswahllisten'!$A$2:$A${len(TOOL_STATUSES) + 1}",
    ))
    worksheet.sheet_state = "hidden"


def build_tool_error_workbook(errors=None):
    workbook = Workbook()
    errors = list(errors or [])
    _append_import_export_sheet(workbook, errors)
    _append_overview_sheet(workbook, errors)
    _append_list_sheet(workbook)
    workbook.active = 0
    return workbook


def tool_error_workbook_bytes(errors=None):
    output = BytesIO()
    build_tool_error_workbook(errors).save(output)
    output.seek(0)
    return output


def export_tool_errors_to_excel(include_history=False):
    return tool_error_workbook_bytes(
        _get_tool_errors(include_history=include_history)
    )
