from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool

# 🔥 NEU
from factoryos.core.services.change_log_service import log_change, build_changes
from factoryos.modules.tool_errors.models import ToolError


def create_tool(data):

    tool = Tool(
        tool_no=data.get("tool_no"),
        name=data.get("name"),
        description=data.get("description"),
        location=data.get("location"),
        tool_status=data.get("tool_status"),
        cavities=data.get("cavities") or None,
    )

    db.session.add(tool)
    db.session.flush()  # 🔥 wichtig für ID

    # 📝 CHANGELOG
    log_change(
        entity_type="tool",
        entity_id=tool.id,
        entity_name=tool.tool_no,
        action="create",
        changes={
            "tool_no": {"old": None, "new": tool.tool_no}
        },
        category="masterdata"
    )

    db.session.commit()

    return tool


def update_tool(tool, data):

    # =========================
    # 🔍 Neue Werte vorbereiten
    # =========================

    new_data = {
        "tool_no": data.get("tool_no"),
        "name": data.get("name"),
        "description": data.get("description"),
        "location": data.get("location"),
        "tool_status": data.get("tool_status"),
        "cavities": data.get("cavities") or None,
    }

    # 🔍 Änderungen erkennen
    changes = build_changes(tool, new_data, new_data.keys())

    # Werte setzen
    for key, value in new_data.items():
        setattr(tool, key, value)

    # =========================
    # 📝 CHANGELOG
    # =========================

    if changes:
        log_change(
            entity_type="tool",
            entity_id=tool.id,
            entity_name=tool.tool_no,
            action="update",
            changes=changes,
            category="masterdata"
        )

    db.session.commit()

    return tool



def delete_tool(tool):

    tool_name = tool.tool_no  # 🔥 für Log sichern

    # 🔥 abhängige Fehler löschen
    ToolError.query.filter_by(tool_id=tool.id).delete()

    # 🔥 ChangeLog schreiben
    log_change(
        entity_type="tool",
        entity_id=tool.id,
        entity_name=tool_name,
        action="delete",
        category="masterdata"
    )

    db.session.delete(tool)
    db.session.commit()
