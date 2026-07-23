from datetime import datetime

from flask import (
    send_file,
    request
)

from flask_login import login_required

from factoryos.core.auth import permission_required

from . import bp

from ..services.error_export_service import (
    export_tool_errors_to_excel
)


@bp.route("/export/excel")
@login_required
@permission_required("tool_error.excel_export")
def export_errors_excel():

    include_history = request.args.get("history") == "1"

    output = export_tool_errors_to_excel(
        include_history=include_history
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if include_history:

        filename = f"ToolErrors_Export_mit_Historie_{timestamp}.xlsx"

    else:

        filename = f"ToolErrors_Export_{timestamp}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
