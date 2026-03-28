from factoryos.extensions import db
from datetime import datetime

from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.tool_errors.models import ToolError

from factoryos.core.services.change_log_service import log_change, build_changes


# =========================
# CREATE
# =========================
def create_tool_error(form, user_id):

    error = ToolError(
        tool_id=form.get("tool_id"),
        order_id=form.get("order_id"),
        machine_id=form.get("machine_id"),
        error_type=form.get("error_type"),
        description=form.get("description"),
        reported_by_id=user_id,
        created_at=datetime.utcnow()
    )

    db.session.add(error)
    db.session.flush()  # 🔥 wichtig für ID

    # 🔧 Tool laden für Name
    tool = Tool.query.get(error.tool_id)

    # =========================
    # 📝 CHANGELOG
    # =========================
    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=tool.tool_no if tool else f"Tool {error.tool_id}",
        action="create",
        changes={
            "tool_id": {"old": None, "new": error.tool_id},
            "error_type": {"old": None, "new": error.error_type},
        },
        category="production"
    )

    db.session.commit()

    return error


# =========================
# UPDATE (optional, aber vorbereitet)
# =========================
def update_tool_error(error, data):

    new_data = {
        "tool_id": data.get("tool_id"),
        "error_type": data.get("error_type"),
        "description": data.get("description"),
        "order_id": data.get("order_id"),
        "machine_id": data.get("machine_id"),
    }

    changes = build_changes(error, new_data, new_data.keys())

    for key, value in new_data.items():
        setattr(error, key, value)

    if changes:
        tool = Tool.query.get(error.tool_id)

        log_change(
            entity_type="tool_error",
            entity_id=error.id,
            entity_name=tool.tool_no if tool else f"Tool {error.tool_id}",
            action="update",
            changes=changes,
            category="production"
        )

    db.session.commit()

    return error


# =========================
# DELETE
# =========================
def delete_tool_error(error):

    tool = Tool.query.get(error.tool_id)

    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=tool.tool_no if tool else f"Tool {error.tool_id}",
        action="delete",
        category="production"
    )

    db.session.delete(error)
    db.session.commit()