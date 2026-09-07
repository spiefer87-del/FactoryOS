from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from factoryos.core.auth import permission_required

from ..services.material_excel_service import (
    import_materials_from_excel,
    material_workbook_bytes,
)
from . import bp


@bp.route("/import", methods=["GET", "POST"])
@login_required
@permission_required("materials.excel_import")
def import_materials():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Keine Datei ausgewählt.", "danger")
            return redirect(url_for("materials.import_materials"))
        if not file.filename.lower().endswith(".xlsx"):
            flash("Bitte eine XLSX-Datei auswählen.", "danger")
            return redirect(url_for("materials.import_materials"))
        try:
            result = import_materials_from_excel(file, current_user.id)
            return render_template("masterdata/materials/import_result.html", **result)
        except Exception as error:
            flash(f"Importfehler: {error}", "danger")
            return redirect(url_for("materials.import_materials"))
    return render_template("masterdata/materials/import.html")


@bp.route("/import/template")
@login_required
@permission_required("materials.excel_import")
def download_import_template():
    return send_file(
        material_workbook_bytes(template=True),
        as_attachment=True,
        download_name="Materialien_Import_Vorlage.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
