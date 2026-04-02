uploaded_files = files.getlist("images")

for i, file in enumerate(uploaded_files):

    if not file or not file.filename:
        continue

    marker_x = form.get(f"marker_x_{i}")
    marker_y = form.get(f"marker_y_{i}")
    description = form.get(f"image_description_{i}")

    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(upload_folder, filename)

    file.save(filepath)

    image = ToolErrorImage(
        tool_error_id=error.id,
        image_path=f"uploads/tool_errors/{filename}",
        marker_x=float(marker_x) if marker_x else None,
        marker_y=float(marker_y) if marker_y else None,
        description=description
    )

    db.session.add(image)

import os
import uuid
from datetime import datetime
from flask import current_app

from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.core.services.change_log_service import log_change, build_changes

from ..models import ToolError, ToolErrorImage


# =========================
# CREATE (OHNE BILDER!)
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
    db.session.commit()

    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=f"Tool {error.tool_id} - {error.error_type}",
        action="create",
        changes=changes,
        category="production"
    )

    return error


# =========================
# IMAGE UPLOAD (NEU!)
# =========================
def upload_tool_error_image(error_id, file, marker_x, marker_y, description, user_id):

    if not file or not file.filename:
        print("❌ Kein File erhalten")
        return None

    upload_folder = os.path.join(
        current_app.static_folder,
        "uploads/tool_errors"
    )

    os.makedirs(upload_folder, exist_ok=True)

    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(upload_folder, filename)

    file.save(filepath)

    print("✅ Bild gespeichert:", filename)

    image = ToolErrorImage(
        tool_error_id=error_id,
        image_path=f"uploads/tool_errors/{filename}",
        marker_x=float(marker_x) if marker_x else None,
        marker_y=float(marker_y) if marker_y else None,
        description=description
    )

    db.session.add(image)
    db.session.commit()

    return image


# =========================
# UPDATE
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

    for image in error.images:
        db.session.delete(image)

    db.session.delete(error)
    db.session.commit()
