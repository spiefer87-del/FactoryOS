from flask import render_template
from flask_login import login_required
from io import BytesIO
from flask import send_file
from openpyxl import Workbook

from . import bp


@bp.route("/import")
@login_required
def import_errors():

    return render_template(
        "tool_errors/import.html"
    )


@bp.route("/import/template")
@login_required
def download_error_import_template():

    wb = Workbook()

    ws = wb.active
    ws.title = "Tool Errors"

    ws.append([
        "error_no",
        "tool_no",
        "error_type",
        "description",
        "tool_status"
    ])

    ws.append([
        "FM26-001",
        "WZ-10001",
        "Gratbildung",
        "Grat an der Trennebene",
        "wartung"
    ])

    output = BytesIO()

    wb.save(output)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="ToolError_Import_Vorlage.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
