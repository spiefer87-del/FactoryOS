from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file
)

from flask_login import (
    login_required,
    current_user
)

from ..services.machine_excel_schema import machine_workbook

from factoryos.core.auth import permission_required

from . import bp

from ..services.machine_import_service import (
    import_machines_from_excel
)


# =====================================================
# IMPORT
# =====================================================

@bp.route("/import", methods=["GET", "POST"])
@login_required
@permission_required("machines.excel_import")
def import_machines():

    if request.method == "POST":

        file = request.files.get("file")

        if not file or not file.filename:

            flash(
                "Keine Datei ausgewählt.",
                "danger"
            )

            return redirect(
                url_for("machines.import_machines")
            )

        if not file.filename.lower().endswith(".xlsx"):

            flash(
                "Bitte eine XLSX-Datei auswählen.",
                "danger"
            )

            return redirect(
                url_for("machines.import_machines")
            )

        try:

            result = import_machines_from_excel(
                file,
                current_user.id
            )

            return render_template(
                "masterdata/machines/import_result.html",
                created=result["created"],
                updated=result["updated"],
                errors=result["errors"]
            )

        except Exception as error:

            flash(
                f"Importfehler: {error}",
                "danger"
            )

            return redirect(
                url_for("machines.import_machines")
            )

    return render_template(
        "masterdata/machines/import.html"
    )


# =====================================================
# TEMPLATE DOWNLOAD
# =====================================================

@bp.route("/import/template")
@login_required
@permission_required("machines.excel_import")
def download_import_template():

    output = machine_workbook()

    return send_file(
        output,
        as_attachment=True,
        download_name="Maschinen_Import_Vorlage.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )
