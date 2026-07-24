from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from sqlalchemy.orm import joinedload

from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES


def _format_datetime(value):

    if not value:
        return ""

    return value.strftime("%d.%m.%Y %H:%M")


def _bool_label(value):

    return "Ja" if value else "Nein"


def _tool_status_label(status):

    return TOOL_STATUSES.get(status, status or "")


def _join_article_numbers(tool):

    if not tool.articles:
        return ""

    return ", ".join(
        article.article_no
        for article in tool.articles
        if article.article_no
    )


def _join_article_names(tool):

    if not tool.articles:
        return ""

    return ", ".join(
        article.article_name
        for article in tool.articles
        if article.article_name
    )


def _dimensions(tool):

    if not tool.tool_length_mm and not tool.tool_width_mm and not tool.tool_height_mm:
        return ""

    return (
        f"{tool.tool_length_mm or '-'} × "
        f"{tool.tool_width_mm or '-'} × "
        f"{tool.tool_height_mm or '-'} mm"
    )


def _autosize_columns(ws):

    for column_cells in ws.columns:

        max_length = 0
        column_letter = get_column_letter(column_cells[0].column)

        for cell in column_cells:

            if cell.value is None:
                continue

            max_length = max(
                max_length,
                len(str(cell.value))
            )

        ws.column_dimensions[column_letter].width = min(
            max(max_length + 2, 12),
            50
        )


def _style_sheet(ws):

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="1F2937"
    )

    header_font = Font(
        color="FFFFFF",
        bold=True
    )

    thin = Side(
        style="thin",
        color="E5E7EB"
    )

    border = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin
    )

    for cell in ws[1]:

        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )
        cell.border = border

    for row in ws.iter_rows(min_row=2):

        for cell in row:

            cell.border = border
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True
            )

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    _autosize_columns(ws)


def _get_tools():

    return (
        Tool.query
        .options(
            joinedload(Tool.articles),
            joinedload(Tool.created_by),
            joinedload(Tool.images)
        )
        .order_by(
            Tool.tool_no.asc()
        )
        .all()
    )


def export_tools_to_excel():

    tools = _get_tools()

    wb = Workbook()

    # =====================================================
    # SHEET 1: WERKZEUGE
    # =====================================================

    ws = wb.active
    ws.title = "Werkzeuge"

    ws.append([
        "Werkzeugnummer",
        "Externe Werkzeugnummer",
        "Werkzeugname",
        "Beschreibung",

        "Status",
        "Status intern",
        "Standort",

        "Artikelnummern",
        "Artikelnamen",

        "Hersteller",
        "Baujahr",
        "Schusszähler",
        "Letzte Wartung",

        "Kavitäten",
        "Kernzüge",
        "Heißkanalzonen",

        "Gewicht kg",
        "Länge mm",
        "Breite mm",
        "Höhe mm",
        "Abmessungen",

        "Zentrierung Düsenseite",
        "Zentrierung Auswerferseite",
        "Auswerferanschluss",
        "Entformung",
        "Automation",
        "Umbausatz",

        "Bilder Anzahl",

        "Erstellt am",
        "Erstellt von",
    ])

    for tool in tools:

        ws.append([
            tool.tool_no or "",
            tool.external_tool_no or "",
            tool.name or "",
            tool.description or "",

            _tool_status_label(tool.tool_status),
            tool.tool_status or "",
            tool.location or "",

            _join_article_numbers(tool),
            _join_article_names(tool),

            tool.built_by or "",
            tool.build_year or "",
            tool.shot_counter or "",
            _format_datetime(tool.last_service_at),

            tool.cavities or "",
            tool.core_pulls or "",
            tool.hotrunner_zones or "",

            tool.tool_weight_kg or "",
            tool.tool_length_mm or "",
            tool.tool_width_mm or "",
            tool.tool_height_mm or "",
            _dimensions(tool),

            tool.centering_nozzle_side or "",
            tool.centering_ejector_side or "",
            tool.ejector_connection or "",
            tool.demolding_type or "",
            tool.automation_type or "",
            _bool_label(tool.has_conversion_kit),

            len(tool.images) if tool.images else 0,

            _format_datetime(tool.created_at),
            tool.created_by.username if tool.created_by else "",
        ])

    _style_sheet(ws)


    # =====================================================
    # SHEET 2: ARTIKELZUORDNUNG
    # =====================================================

    ws_articles = wb.create_sheet("Artikelzuordnung")

    ws_articles.append([
        "Werkzeugnummer",
        "Externe Werkzeugnummer",
        "Werkzeugname",
        "Artikelnummer",
        "Artikelname",
    ])

    for tool in tools:

        if not tool.articles:

            ws_articles.append([
                tool.tool_no or "",
                tool.external_tool_no or "",
                tool.name or "",
                "",
                "",
            ])

            continue

        for article in tool.articles:

            ws_articles.append([
                tool.tool_no or "",
                tool.external_tool_no or "",
                tool.name or "",
                article.article_no or "",
                article.article_name or "",
            ])

    _style_sheet(ws_articles)


    output = BytesIO()

    wb.save(output)
    output.seek(0)

    return output
