from openpyxl import load_workbook

from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool


STATUS_MAPPING = {
    "aktiv": "aktiv",
    "wartung": "wartung",
    "defekt": "defekt",

    "beim kunden": "external",
    "external": "external",

    "verschrottet": "scrapped",
    "scrapped": "scrapped"
}


def import_tools_from_excel(file):

    wb = load_workbook(file)
    ws = wb.active

    created = 0
    updated = 0
    errors = []

    for row_index, row in enumerate(
        ws.iter_rows(
            min_row=2,
            values_only=True
        ),
        start=2
    ):

        # ==========================================
        # LEERE ZEILE
        # ==========================================

        if not row:
            continue

        # ==========================================
        # WERKZEUGNUMMER
        # ==========================================

        tool_no = str(row[0]).strip() if row[0] else ""

        if not tool_no:

            errors.append({
                "row": row_index,
                "tool_no": "-",
                "reason": "Werkzeugnummer fehlt"
            })

            continue

        # ==========================================
        # WERKZEUG SUCHEN / ANLEGEN
        # ==========================================

        tool = Tool.query.filter_by(
            tool_no=tool_no
        ).first()

        if not tool:

            tool = Tool(
                tool_no=tool_no
            )

            db.session.add(tool)

            created += 1

        else:

            updated += 1

        # ==========================================
        # STATUS MAPPING
        # ==========================================

        raw_status = (
            str(row[7]).strip()
            if len(row) > 7 and row[7]
            else None
        )

        mapped_status = None

        if raw_status:

            normalized_status = (
                str(raw_status)
                .replace("\xa0", "")
                .replace("\n", "")
                .replace("\r", "")
                .strip()
                .lower()
            )

            mapped_status = STATUS_MAPPING.get(
                normalized_status
            )

            if not mapped_status:

                errors.append({
                    "row": row_index,
                    "tool_no": tool_no,
                    "reason": (
                        f"Unbekannter Status: "
                        f"'{raw_status}'"
                    )
                })

        # ==========================================
        # FELDER
        # ==========================================

        tool.external_tool_no = row[1]
        tool.name = row[2]
        tool.description = row[3]

        tool.built_by = row[4]
        tool.build_year = row[5]

        tool.location = row[6]

        if mapped_status:
            tool.tool_status = mapped_status

        tool.cavities = row[8]
        tool.core_pulls = row[9]
        tool.hotrunner_zones = row[10]

        tool.tool_weight_kg = row[11]
        tool.tool_length_mm = row[12]
        tool.tool_width_mm = row[13]
        tool.tool_height_mm = row[14]

        tool.centering_nozzle_side = row[15]
        tool.centering_ejector_side = row[16]

        tool.ejector_connection = row[17]
        tool.demolding_type = row[18]

        tool.automation_type = row[19]

    db.session.commit()

    return {
        "created": created,
        "updated": updated,
        "errors": errors
        
    }from openpyxl import load_workbook

from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool


def import_tools_from_excel(file):

    wb = load_workbook(file)

    ws = wb.active

    created = 0
    updated = 0
    errors = []

    for row in ws.iter_rows(
        min_row=2,
        values_only=True
    ):

        tool_no = row[0]

        if not tool_no:
            continue

        tool_no = str(tool_no).strip()

        tool = Tool.query.filter_by(
            tool_no=tool_no
        ).first()

        if not tool:

            tool = Tool(
                tool_no=tool_no
            )

            db.session.add(tool)

            created += 1

        else:

            updated += 1

        tool.external_tool_no = row[1]
        tool.name = row[2]
        tool.description = row[3]

        tool.built_by = row[4]
        tool.build_year = row[5]

        tool.location = row[6]
        tool.tool_status = row[7]

        tool.cavities = row[8]
        tool.core_pulls = row[9]
        tool.hotrunner_zones = row[10]

        tool.tool_weight_kg = row[11]
        tool.tool_length_mm = row[12]
        tool.tool_width_mm = row[13]
        tool.tool_height_mm = row[14]

        tool.centering_nozzle_side = row[15]
        tool.centering_ejector_side = row[16]

        tool.ejector_connection = row[17]
        tool.demolding_type = row[18]

        tool.automation_type = row[19]

    errors.append({
        "row": row_index,
        "tool_no": tool_no,
        "reason": f"Status '{tool_status}' wurde zu '{mapped_status}' gemappt"
    })

    db.session.commit()
    
    return {
        "created": created,
        "updated": updated,
        "errors": errors
    }
