from io import BytesIO

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

from openpyxl import Workbook
from openpyxl.styles import Font

from factoryos.core.auth import permission_required

from . import bp

from ..services.machine_import_service import (
    import_machines_from_excel,
    EXPECTED_HEADERS
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

    workbook = Workbook()

    worksheet = workbook.active
    worksheet.title = "Maschinen"

    worksheet.append(
        EXPECTED_HEADERS
    )

    for cell in worksheet[1]:
        cell.font = Font(bold=True)

    worksheet.append([
        "SGM-001",
        "EXT-SGM-001",
        "Spritzgießmaschine 1",
        "Produktionsmaschine Halle 1",
        "injection_molding",
        "ARBURG",
        "Allrounder",
        "SN-123456",
        2020,
        "SELOGICA",
        "Linearroboter",
        25000,
        "01.06.2026",
        "01.12.2026",
        "Halle 1",
        "aktiv",
        1300,
        570,
        570,
        250,
        600,
        500,
        180,
        2500,
        40,
        220,
        2500,
        5,
        15.5,
        4
    ])

    for column in worksheet.columns:
        letter = column[0].column_letter
        worksheet.column_dimensions[letter].width = 22

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="Maschinen_Import_Vorlage.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )
