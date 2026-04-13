from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool

# 🔥 NEU
from factoryos.core.services.change_log_service import log_change, build_changes
from factoryos.modules.tool_errors.models import ToolError


def create_tool(data):

    tool = Tool(
        tool_no=data.get("tool_no"),
        external_tool_no=data.get("external_tool_no"),
        name=data.get("name"),
        description=data.get("description"),
        location=data.get("location"),
        tool_status=data.get("tool_status"),

        cavities=data.get("cavities") or None,

        tool_weight_kg=data.get("tool_weight_kg") or None,
        tool_length_mm=data.get("tool_length_mm") or None,
        tool_width_mm=data.get("tool_width_mm") or None,
        tool_height_mm=data.get("tool_height_mm") or None,

        centering_type=data.get("centering_type"),
        ejector_connection=data.get("ejector_connection"),
        demolding_type=data.get("demolding_type"),
        hotrunner_zones=data.get("hotrunner_zones") or None,
        automation_type=data.get("automation_type"),

        has_conversion_kit=True if data.get("has_conversion_kit") else False,
        core_pulls=data.get("core_pulls") or None,
    )

    db.session.add(tool)
    db.session.flush()

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

    new_data = {
        "tool_no": data.get("tool_no"),
        "external_tool_no": data.get("external_tool_no"),
        "name": data.get("name"),
        "description": data.get("description"),
        "location": data.get("location"),
        "tool_status": data.get("tool_status"),

        "cavities": data.get("cavities") or None,

        "tool_weight_kg": data.get("tool_weight_kg") or None,
        "tool_length_mm": data.get("tool_length_mm") or None,
        "tool_width_mm": data.get("tool_width_mm") or None,
        "tool_height_mm": data.get("tool_height_mm") or None,

        "centering_type": data.get("centering_type"),
        "ejector_connection": data.get("ejector_connection"),
        "demolding_type": data.get("demolding_type"),
        "hotrunner_zones": data.get("hotrunner_zones") or None,
        "automation_type": data.get("automation_type"),

        "has_conversion_kit": True if data.get("has_conversion_kit") else False,
        "core_pulls": data.get("core_pulls") or None,
    }

    changes = build_changes(tool, new_data, new_data.keys())

    for key, value in new_data.items():
        setattr(tool, key, value)

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
