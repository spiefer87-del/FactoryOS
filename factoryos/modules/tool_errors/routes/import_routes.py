from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file
)

from flask_login import login_required, current_user

from factoryos.core.auth import permission_required

from . import bp

from ..services.error_import_service import (
    import_errors_from_excel
)
from ..services.error_export_service import (
    tool_error_workbook_bytes
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

        if not file.filename.lower().endswith(".xlsx"):

            flash(
                "Bitte eine XLSX-Datei auswählen.",
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
                updated=result["updated"],
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
    return send_file(
        tool_error_workbook_bytes(),
        as_attachment=True,
        download_name="ToolError_Import_Vorlage.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )
