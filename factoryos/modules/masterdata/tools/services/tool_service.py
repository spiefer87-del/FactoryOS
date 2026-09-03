from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.tool_errors.models import ToolError

from factoryos.modules.masterdata.tools.services.tool_storage_service import (
    create_tool_folders,
    save_tool_images,
    save_tool_documents,
    validate_tool_documents,
    delete_tool_images_by_ids,
    delete_tool_folder,
    rename_tool_folder
)

from factoryos.core.services.change_log_service import (
    log_change,
    build_changes
)


# =====================================================
# CREATE
# =====================================================

def create_tool(
        data,
        image_files,
        document_files=None,
        document_category="documents"
    ):

    validate_tool_documents(
        document_files,
        document_category
    )

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

    create_tool_folders(tool.tool_no)
    save_tool_images(tool, image_files)
    save_tool_documents(
        tool,
        document_files,
        category=document_category
    )
    

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

def update_tool(
        tool,
        data,
        image_files,
        delete_ids,
        document_files=None,
        document_category="documents"
    ):

    validate_tool_documents(
        document_files,
        document_category
    )

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

    
    old_tool_no = tool.tool_no

    changes = build_changes(tool, new_data, new_data.keys())

    for key, value in new_data.items():
        setattr(tool, key, value)

    rename_tool_folder(old_tool_no, tool.tool_no)
    delete_tool_images_by_ids(delete_ids)
    save_tool_images(tool, image_files)
    save_tool_documents(
        tool,
        document_files,
        category=document_category
    )

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

    errors = ToolError.query.filter_by(tool_id=tool.id).all()

    for error in errors:
        db.session.delete(error)

    delete_tool_folder(tool.tool_no)

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
