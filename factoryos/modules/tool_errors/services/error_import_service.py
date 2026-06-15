# factoryos/modules/tool_errors/services/error_import_service.py

from datetime import datetime

from openpyxl import load_workbook

from factoryos.extensions import db

from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.tool_errors.models import ToolError


def import_errors_from_excel(file):

    wb = load_workbook(file)

    ws = wb.active

    created = 0

    for row in ws.iter_rows(min_row=2, values_only=True):

        if not row or not row[0]:
            continue
            
        error_no = str(row[0]).strip() if row[0] else None

        if not error_no:
            continue
        
        tool_no = str(row[1]).strip()

        tool = Tool.query.filter_by(
            tool_no=tool_no
        ).first()

        if not tool:
            print(f"Werkzeug nicht gefunden: {tool_no}")
            continue

        error_type = str(row[2]).strip() if row[2] else ""
        description = str(row[3]).strip() if row[3] else ""
        tool_status = row[4]

        existing = ToolError.query.filter_by(
            error_no=error_no
        ).first()
        
        if existing:
            continue

        # ==========================================
        # FEHLER ANLEGEN
        # ==========================================

        error = ToolError(

            error_no=error_no,

            tool_id=tool.id,

            error_type=error_type,

            description=description,
            reported_by_id=1,

            created_at=datetime.utcnow()
        )

        db.session.add(error)

        # ==========================================
        # OPTIONAL STATUS SETZEN
        # ==========================================

        if tool_status:

            tool.tool_status = str(
                tool_status
            ).strip()

        created += 1

    db.session.commit()

    return created
