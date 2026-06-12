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

        tool_no = str(row[0]).strip()

        tool = Tool.query.filter_by(
            tool_no=tool_no
        ).first()

        if not tool:
            continue

        error_type = row[1]
        description = row[2]
        tool_status = row[3]

        # ==========================================
        # FM NUMMER ERZEUGEN
        # ==========================================

        year = datetime.utcnow().year

        last = ToolError.query\
            .order_by(ToolError.id.desc())\
            .first()

        if last and last.error_no:

            try:

                last_number = int(
                    last.error_no.split("-")[1]
                )

            except Exception:

                last_number = 0

        else:

            last_number = 0

        error_no = (
            f"FM{year % 100:02d}-"
            f"{last_number + 1:03d}"
        )

        # ==========================================
        # FEHLER ANLEGEN
        # ==========================================

        error = ToolError(

            error_no=error_no,

            tool_id=tool.id,

            error_type=error_type,

            description=description,

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
