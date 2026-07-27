from io import BytesIO

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file
)

from flask_login import login_required, current_user
from openpyxl import Workbook

from factoryos.core.auth import permission_required

from . import bp

from ..services.error_import_service import (
    import_errors_from_excel
)


# =====================================================
# TOOL ERROR EXCEL IMPORT
# =====================================================

@bp.route("/import", methods=["GET", "POST"])
@login_required
@permission_required("tool_error.excel_import")
def import_errors():

    if request.method == "POST":

        file = request.files.get("file")

        if not file or not file.filename:

            flash(
                "Keine Datei ausgewählt.",
                "danger"
            )

            return redirect(
                url_for("tool_error.import_errors")
            )

        try:

            result = import_errors_from_excel(
                file,
                current_user.id
            )

            return render_template(
                "tool_errors/import_result.html",
                created=result["created"],
                errors=result["errors"]
            )

        except Exception as error:

            flash(
                f"Importfehler: {str(error)}",
                "danger"
            )

            return redirect(
                url_for("tool_error.import_errors")
            )

    return render_template(
        "tool_errors/import.html"
    )


# =====================================================
# IMPORT-VORLAGE HERUNTERLADEN
# =====================================================

@bp.route("/import/template")
@login_required
@permission_required("tool_error.excel_import")
def download_error_import_template():

    workbook = Workbook()

    worksheet = workbook.active
    worksheet.title = "Tool Errors"

    worksheet.append([
        "error_no",
        "tool_no",
        "error_type",
        "description",
        "tool_status"
    ])

    worksheet.append([
        "FM26-001",
        "WZ-10001",
        "Gratbildung",
        "Grat an der Trennebene",
        "wartung"
    ])

    output = BytesIO()

    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="ToolError_Import_Vorlage.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )
