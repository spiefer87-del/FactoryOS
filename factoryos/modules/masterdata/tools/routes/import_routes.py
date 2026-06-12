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

from . import bp

from ..services.tool_import_service import (
import_tools_from_excel
)



@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_tools():

if request.method == "POST":

    file = request.files.get("file")

    if not file:

        flash(
            "Keine Datei ausgewählt.",
            "danger"
        )

        return redirect(
            url_for("tools.import_tools")
        )

    try:

        created, updated = (
            import_tools_from_excel(file)
        )

        flash(
            f"{created} Werkzeuge importiert, "
            f"{updated} aktualisiert.",
            "success"
        )

    except Exception as e:

        flash(
            f"Importfehler: {str(e)}",
            "danger"
        )

    return redirect(
        url_for("tools.dashboard")
    )

return render_template(
    "masterdata/tools/import.html"
)



@bp.route("/import/template")
@login_required
def download_import_template():

wb = Workbook()

ws = wb.active

ws.title = "Werkzeuge"

headers = [

    "tool_no",
    "external_tool_no",
    "name",
    "description",

    "built_by",
    "build_year",

    "location",
    "tool_status",

    "cavities",
    "core_pulls",
    "hotrunner_zones",

    "tool_weight_kg",
    "tool_length_mm",
    "tool_width_mm",
    "tool_height_mm",

    "centering_nozzle_side",
    "centering_ejector_side",

    "ejector_connection",
    "demolding_type",

    "automation_type"
]

ws.append(headers)

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

    "Linearroboter"
])

# ==========================================
# DATEI IN SPEICHER ERZEUGEN
# ==========================================

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
