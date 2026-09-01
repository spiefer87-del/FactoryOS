from io import BytesIO

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file
)

from flask_login import login_required
from openpyxl import Workbook
from openpyxl.styles import Font
from factoryos.core.auth import permission_required

from . import bp

from ..services.tool_import_service import (
    EXPECTED_HEADERS,
    import_tools_from_excel,
)


# =====================================================
# IMPORT
# =====================================================
@bp.route("/import", methods=["GET", "POST"])
@login_required
@permission_required("tools.excel_import")
def import_tools():

    if request.method == "POST":

        file = request.files.get("file")

        if not file or not file.filename:

            flash(
                "Keine Datei ausgewählt.",
                "danger"
            )

            return redirect(
                url_for("tools.import_tools")
            )

        if not file.filename.lower().endswith(".xlsx"):

            flash(
                "Bitte eine XLSX-Datei auswählen.",
                "danger"
            )

            return redirect(
                url_for("tools.import_tools")
            )

        try:

            result = import_tools_from_excel(file)

            return render_template(
                "masterdata/tools/import_result.html",
                created=result["created"],
                updated=result["updated"],
                errors=result["errors"]
            )

        except Exception as e:

            flash(
                f"Importfehler: {str(e)}",
                "danger"
            )

            return redirect(
                url_for("tools.import_tools")
            )

    return render_template(
        "masterdata/tools/import.html"
    )


# =====================================================
# TEMPLATE DOWNLOAD
# =====================================================

@bp.route("/import/template")
@login_required
@permission_required("tools.excel_import")
def download_import_template():

    wb = Workbook()

    ws = wb.active
    ws.title = "Werkzeuge"

    ws.append(EXPECTED_HEADERS)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    # ==========================================
    # BEISPIELDATENSATZ
    # ==========================================

    ws.append([

        "WZ-10001",
        "EXT-001",
        "Spritzgusswerkzeug Deckel",
        "8-fach Werkzeug",

        "Muster Werkzeugbau",
        2024,

        125000,
        "01.06.2026",

        "Regal A1",
        "aktiv",

        8,
        2,
        12,

        850,
        600,
        450,
        500,

        "Ø100",
        "Ø100",

        "Hydraulisch",
        "Auswerfer",

        "Linearroboter",
        "Ja"
    ])

    for column in ws.columns:
        letter = column[0].column_letter
        ws.column_dimensions[letter].width = 22

    output = BytesIO()

    wb.save(output)

    output.seek(0)

    return send_file(

        output,

        as_attachment=True,

        download_name="Werkzeug_Import_Vorlage.xlsx",

        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )
