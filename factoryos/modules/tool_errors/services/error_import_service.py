from datetime import datetime

from openpyxl import load_workbook

from factoryos.core.services.change_log_service import log_change
from factoryos.extensions import db
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.tool_errors.models import ToolError
from factoryos.modules.tool_errors.services.error_export_service import (
    EXPECTED_HEADERS,
)
from factoryos.modules.tool_errors.services.tool_error_storage_service import (
    create_tool_error_folders,
    move_tool_error_revision,
)


HEADER_ALIASES = {
    "fm-nr.": "error_no",
    "fm-nr": "error_no",
    "fehlernummer": "error_no",
    "revision": "revision",
    "werkzeugnummer": "tool_no",
    "werkzeug-nr.": "tool_no",
    "fehlerart": "error_type",
    "beschreibung": "description",
    "werkzeugstatus": "tool_status",
    "auftrag": "order_id",
    "auftrag-id": "order_id",
    "maschine": "machine_id",
    "maschinen-id": "machine_id",
}

STATUS_MAPPING = {
    **{key.lower(): key for key in TOOL_STATUSES},
    **{label.lower(): key for key, label in TOOL_STATUSES.items()},
    "beim kunden": "external",
}


def _normalize(value):
    return (
        str(value or "")
        .replace("\xa0", " ")
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
        .lower()
    )


def _header(value):
    normalized = _normalize(value)
    if normalized in EXPECTED_HEADERS:
        return normalized
    return HEADER_ALIASES.get(normalized, "")


def _identifier(value):
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _integer(value, field_label, default=None):
    if value in (None, ""):
        return default
    try:
        number = float(str(value).strip().replace(",", "."))
    except ValueError as error:
        raise ValueError(f"{field_label} muss eine ganze Zahl sein.") from error
    if not number.is_integer():
        raise ValueError(f"{field_label} muss eine ganze Zahl sein.")
    return int(number)


def _text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _tool_status(value):
    if value in (None, ""):
        return None
    status = STATUS_MAPPING.get(_normalize(value))
    if not status:
        raise ValueError(f"Ungültiger Werkzeugstatus: {value}")
    return status


def _find_import_sheet(workbook):
    for worksheet in workbook.worksheets:
        headers = [_header(cell.value) for cell in worksheet[1]]
        if "error_no" in headers and "tool_no" in headers:
            return worksheet, headers
    raise ValueError(
        "Keine Tabelle mit den Spalten 'error_no' und 'tool_no' gefunden."
    )


def _row_dict(headers, row):
    return {
        header: row[index] if index < len(row) else None
        for index, header in enumerate(headers)
        if header
    }


def _changes(instance, values):
    return {
        field: {"old": getattr(instance, field, None), "new": value}
        for field, value in values.items()
        if getattr(instance, field, None) != value
    }


def import_errors_from_excel(file, user_id):
    workbook = load_workbook(file, data_only=True)
    worksheet, headers = _find_import_sheet(workbook)
    created = 0
    updated = 0
    errors = []
    seen = set()

    for row_index, row in enumerate(
        worksheet.iter_rows(min_row=2, values_only=True),
        start=2,
    ):
        if not any(value is not None and str(value).strip() for value in row):
            continue

        data = _row_dict(headers, row)
        error_no = _identifier(data.get("error_no"))
        tool_no = _identifier(data.get("tool_no"))

        try:
            if not error_no:
                raise ValueError("Fehlernummer fehlt")
            if len(error_no) > 20:
                raise ValueError("Fehlernummer darf höchstens 20 Zeichen haben")
            if not tool_no:
                raise ValueError("Werkzeugnummer fehlt")

            revision = _integer(data.get("revision"), "Revision", default=1)
            if revision < 1:
                raise ValueError("Revision muss mindestens 1 sein")

            identity = (error_no, revision)
            if identity in seen:
                raise ValueError("FM-Nummer und Revision sind in der Datei doppelt")
            seen.add(identity)

            tool = Tool.query.filter_by(tool_no=tool_no).first()
            if not tool:
                raise ValueError("Werkzeug nicht gefunden")

            mapped_status = _tool_status(data.get("tool_status"))
            values = {
                "tool_id": tool.id,
                "error_type": _text(data.get("error_type")),
                "description": _text(data.get("description")),
                "order_id": _integer(data.get("order_id"), "Auftrag-ID"),
                "machine_id": _integer(data.get("machine_id"), "Maschinen-ID"),
            }

            with db.session.begin_nested():
                error = ToolError.query.filter_by(
                    error_no=error_no,
                    revision=revision,
                ).first()
                is_new = error is None

                if is_new:
                    parent = None
                    if revision > 1:
                        parent = (
                            ToolError.query
                            .filter_by(error_no=error_no)
                            .order_by(ToolError.revision.asc())
                            .first()
                        )
                    error = ToolError(
                        error_no=error_no,
                        revision=revision,
                        parent_error_id=parent.id if parent else None,
                        reported_by_id=user_id,
                        created_at=datetime.utcnow(),
                        workflow_status="draft",
                        is_current=True,
                        **values,
                    )
                    db.session.add(error)
                    db.session.flush()
                    changes = {
                        "error_no": {"old": None, "new": error_no},
                        "revision": {"old": None, "new": revision},
                        **{
                            field: {"old": None, "new": value}
                            for field, value in values.items()
                        },
                    }
                else:
                    changes = _changes(error, values)

                old_tool = error.tool
                old_tool_no = old_tool.tool_no if old_tool else None

                for field, value in values.items():
                    setattr(error, field, value)
                error.tool = tool

                if old_tool_no and old_tool_no != tool.tool_no:
                    move_tool_error_revision(error, old_tool_no, tool.tool_no)

                if is_new:
                    newer_revision = (
                        ToolError.query
                        .filter(ToolError.error_no == error_no)
                        .filter(ToolError.id != error.id)
                        .filter(ToolError.revision > revision)
                        .first()
                    )
                    if newer_revision:
                        error.is_current = False
                    else:
                        (
                            ToolError.query
                            .filter(ToolError.error_no == error_no)
                            .filter(ToolError.id != error.id)
                            .update({"is_current": False}, synchronize_session=False)
                        )

                if mapped_status and tool.tool_status != mapped_status:
                    changes["tool_status"] = {
                        "old": tool.tool_status,
                        "new": mapped_status,
                    }
                    tool.tool_status = mapped_status

                db.session.flush()
                create_tool_error_folders(error)
                log_change(
                    entity_type="tool_error",
                    entity_id=error.id,
                    entity_name=(
                        f"{error.error_no} Rev. {error.revision} ({tool.tool_no})"
                    ),
                    action="import" if is_new else "update",
                    changes=changes,
                    category="production",
                )

            if is_new:
                created += 1
            else:
                updated += 1

        except Exception as error:
            errors.append({
                "row": row_index,
                "error_no": error_no or "-",
                "tool_no": tool_no or "-",
                "reason": str(error),
            })

    db.session.commit()
    return {"created": created, "updated": updated, "errors": errors}
