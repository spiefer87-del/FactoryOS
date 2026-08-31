from datetime import datetime

from flask import send_file
from flask_login import login_required

from factoryos.core.auth import permission_required

from . import bp
from ..services.machine_export_service import export_machines_to_excel


@bp.route("/export/excel")
@login_required
@permission_required("machines.excel_export")
def export_machines_excel():

    output = export_machines_to_excel()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Maschinen_Export_{timestamp}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )
