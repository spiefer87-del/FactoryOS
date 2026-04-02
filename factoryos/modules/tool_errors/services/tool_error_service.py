import os
import uuid
from datetime import datetime
from flask import current_app

from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.core.services.change_log_service import log_change, build_changes

from ..models import ToolError, ToolErrorImage


# =========================
# CREATE TOOL ERROR (OHNE BILDER)
# =========================
def create_tool_error(form, user_id):

    new_data = {
        "tool_id": form.get("tool_id"),
        "order_id": form.get("order_id"),
        "machine_id": form.get("machine_id"),
        "error_type": form.get("error_type"),
        "description": form.get("description"),
    }

    temp_obj = ToolError()
    changes = build_changes(temp_obj, new_data, new_data.keys())

    error = ToolError(
        **new_data,
        reported_by_id=user_id,
        created_at=datetime.utcnow()
    )

    db.session.add(error)
    db.session.flush()

    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=f"Tool {error.tool_id} - {error.error_type}",
        action="create",
        changes=changes,
        category="production"
    )

    db.session.commit()

    return error


# =========================
# TEMP IMAGE UPLOAD
# =========================
def upload_temp_image(file, marker_x, marker_y, description, temp_id):

    if not file:
        print("❌ Kein File")
        return None
        

    upload_folder = os.path.join(
        current_app.static_folder,
        "uploads/tool_errors"
    )

    os.makedirs(upload_folder, exist_ok=True)

    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(upload_folder, filename)

    file.save(filepath)

    image = ToolErrorImage(
        tool_error_id=None,
        temp_id=temp_id,  # 🔥 HIER!
        image_path=f"uploads/tool_errors/{filename}",
        marker_x=float(marker_x) if marker_x else None,
        marker_y=float(marker_y) if marker_y else None,
        description=description
    )

    db.session.add(image)
    db.session.commit()

    return {"success": True}


# =========================
# ASSIGN TEMP IMAGES → ERROR
# =========================
def assign_images_to_error(temp_id, error_id):

    temp_id = form.get("temp_id")

    images = ToolErrorImage.query.filter_by(temp_id=temp_id).all()

    for img in images:
        img.tool_error_id = error.id
        img.temp_id = None  # optional cleanup 

    db.session.commit()


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

    for image in error.images:
        db.session.delete(image)

    db.session.delete(error)
    db.session.commit()
