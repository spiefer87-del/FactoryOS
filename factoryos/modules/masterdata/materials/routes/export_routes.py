from datetime import datetime

from flask import send_file
from flask_login import login_required

from factoryos.core.auth import permission_required

from ..services.material_excel_service import export_materials_to_excel
from . import bp


@bp.route("/export/excel")
@login_required
@permission_required("materials.excel_export")
def export_materials_excel():
    return send_file(
        export_materials_to_excel(),
        as_attachment=True,
        download_name=f"Materialien_Export_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
