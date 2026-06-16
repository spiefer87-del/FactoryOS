from datetime import datetime

from openpyxl import load_workbook

from factoryos.extensions import db

from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.tool_errors.models import ToolError


def import_errors_from_excel(file):

    wb = load_workbook(file)

    ws = wb.active

    created = 0
    errors = []

    for row_index, row in enumerate(
        ws.iter_rows(min_row=2, values_only=True),
        start=2
    ):

        # ==========================================
        # LEERE ZEILE
        # ==========================================

        if not row:
            continue

        # ==========================================
        # FM NUMMER
        # ==========================================

        error_no = str(row[0]).strip() if row[0] else ""

        if not error_no:

            errors.append({
                "row": row_index,
                "reason": "Fehlernummer fehlt"
            })

            continue

        # ==========================================
        # WERKZEUGNUMMER
        # ==========================================

        tool_no = str(row[1]).strip() if row[1] else ""

        if not tool_no:

            errors.append({
                "row": row_index,
                "error_no": error_no,
                "reason": "Werkzeugnummer fehlt"
            })

            continue

        tool = Tool.query.filter_by(
            tool_no=tool_no
        ).first()

        if not tool:

            errors.append({
                "row": row_index,
                "error_no": error_no,
                "tool_no": tool_no,
                "reason": "Werkzeug nicht gefunden"
            })

            continue

        # ==========================================
        # FEHLERART
        # ==========================================

        error_type = str(row[2]).strip() if row[2] else ""

        

        # ==========================================
        # BESCHREIBUNG
        # ==========================================

        description = (
            str(row[3]).strip()
            if len(row) > 3 and row[3]
            else ""
        )

        # ==========================================
        # STATUS
        # ==========================================

        tool_status = (
            str(row[4]).strip()
            if len(row) > 4 and row[4]
            else None
        )

        # ==========================================
        # DOPPELTE FM NUMMER
        # ==========================================

        existing = ToolError.query.filter_by(
            error_no=error_no
        ).first()

        if existing:

            errors.append({
                "row": row_index,
                "error_no": error_no,
                "tool_no": tool_no,
                "reason": "FM-Nummer existiert bereits"
            })

            continue

        # ==========================================
        # TOOL ERROR ANLEGEN
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
        # TOOL STATUS AKTUALISIEREN
        # ==========================================
        STATUS_MAPPING = {
            "aktiv": "aktiv",
            "wartung": "wartung",
            "defekt": "defekt",
        
            "beim kunden": "external",
            "external": "external",
        
            "verschrottet": "scrapped",
            "scrapped": "scrapped"
        }
        
        if tool_status:

            status = str(tool_status).strip().lower()
        
            tool.tool_status = STATUS_MAPPING.get(
                status,
                "aktiv"
            )

        created += 1

    # ==========================================
    # SPEICHERN
    # ==========================================

    db.session.commit()

    return {
        "created": created,
        "errors": errors
    }

