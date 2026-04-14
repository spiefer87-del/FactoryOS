from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool, ToolImage
from factoryos.modules.tool_errors.models import ToolError

from factoryos.core.services.change_log_service import (
    log_change,
    build_changes
)


# =====================================================
# CREATE
# =====================================================

def create_tool(data):

    tool = Tool(
        # 🔹 Identifikation
        tool_no=data.get("tool_no"),
        external_tool_no=data.get("external_tool_no"),
        name=data.get("name"),
        description=data.get("description"),

        # 🔹 Hersteller / Historie
        built_by=data.get("built_by"),
        build_year=data.get("build_year") or None,
        shot_counter=data.get("shot_counter") or None,

        # 🔹 Organisation
        location=data.get("location"),
        tool_status=data.get("tool_status"),

        # 🔹 Technische Daten
        cavities=data.get("cavities") or None,
        core_pulls=data.get("core_pulls") or None,
        hotrunner_zones=data.get("hotrunner_zones") or None,

        # 🔹 Maße
        tool_weight_kg=data.get("tool_weight_kg") or None,
        tool_length_mm=data.get("tool_length_mm") or None,
        tool_width_mm=data.get("tool_width_mm") or None,
        tool_height_mm=data.get("tool_height_mm") or None,

        # 🔹 Ausstattung
        centering_nozzle_side=data.get("centering_nozzle_side"),
        centering_ejector_side=data.get("centering_ejector_side"),
        ejector_connection=data.get("ejector_connection"),
        demolding_type=data.get("demolding_type"),
        automation_type=data.get("automation_type"),

        has_conversion_kit=True if data.get("has_conversion_kit") else False,
    )

    db.session.add(tool)
    db.session.flush()

    files = request.files.getlist("images")

    for file in files:
        if file and file.filename:
    
            filename = secure_filename(file.filename)
    
            folder = os.path.join(
                current_app.static_folder,
                "uploads/tools"
            )
    
            os.makedirs(folder, exist_ok=True)
    
            filepath = os.path.join(folder, filename)
            file.save(filepath)
    
            img = ToolImage(
                tool_id=tool.id,
                image_path=f"uploads/tools/{filename}"
            )
    
            db.session.add(img)
    

    # ==========================================
    # CHANGELOG
    # ==========================================
    log_change(
        entity_type="tool",
        entity_id=tool.id,
        entity_name=tool.tool_no,
        action="create",
        changes={
            "tool_no": {
                "old": None,
                "new": tool.tool_no
            }
        },
        category="masterdata"
    )

    db.session.commit()
    return tool


# =====================================================
# UPDATE
# =====================================================

def update_tool(tool, data):

    new_data = {

        # 🔹 Identifikation
        "tool_no": data.get("tool_no"),
        "external_tool_no": data.get("external_tool_no"),
        "name": data.get("name"),
        "description": data.get("description"),

        # 🔹 Historie
        "built_by": data.get("built_by"),
        "build_year": data.get("build_year") or None,
        "shot_counter": data.get("shot_counter") or None,

        # 🔹 Organisation
        "location": data.get("location"),
        "tool_status": data.get("tool_status"),

        # 🔹 Technische Daten
        "cavities": data.get("cavities") or None,
        "core_pulls": data.get("core_pulls") or None,
        "hotrunner_zones": data.get("hotrunner_zones") or None,

        # 🔹 Maße
        "tool_weight_kg": data.get("tool_weight_kg") or None,
        "tool_length_mm": data.get("tool_length_mm") or None,
        "tool_width_mm": data.get("tool_width_mm") or None,
        "tool_height_mm": data.get("tool_height_mm") or None,

        # 🔹 Ausstattung
        "centering_nozzle_side": data.get("centering_nozzle_side"),
        "centering_ejector_side": data.get("centering_ejector_side"),
        "ejector_connection": data.get("ejector_connection"),
        "demolding_type": data.get("demolding_type"),
        "automation_type": data.get("automation_type"),

        "has_conversion_kit": True if data.get("has_conversion_kit") else False,
    }

    # Bilder löschen
    delete_ids = request.form.getlist("delete_images")
    
    for image_id in delete_ids:
        img = ToolImage.query.get(image_id)
        if img:
            db.session.delete(img)
    
    
    # Neue Bilder
    files = request.files.getlist("images")
    
    for file in files:
        if file and file.filename:
    
            filename = secure_filename(file.filename)
    
            folder = os.path.join(
                current_app.static_folder,
                "uploads/tools"
            )
    
            os.makedirs(folder, exist_ok=True)
    
            filepath = os.path.join(folder, filename)
            file.save(filepath)
    
            img = ToolImage(
                tool_id=tool.id,
                image_path=f"uploads/tools/{filename}"
            )
    
            db.session.add(img)


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


# =====================================================
# DELETE
# =====================================================

def delete_tool(tool):

    tool_name = tool.tool_no

    # 🔥 abhängige Fehlermeldungen löschen
    ToolError.query.filter_by(tool_id=tool.id).delete()

    # 🔥 Bilder löschen
    ToolImage.query.filter_by(tool_id=tool.id).delete()

    # 🔥 ChangeLog
    log_change(
        entity_type="tool",
        entity_id=tool.id,
        entity_name=tool_name,
        action="delete",
        category="masterdata"
    )

    db.session.delete(tool)
    db.session.commit()
