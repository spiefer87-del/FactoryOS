import os
import uuid
from datetime import datetime
from flask import current_app

from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.core.services.change_log_service import log_change, build_changes

from ..models import ToolError, ToolErrorImage


def create_tool_error(form, files, user_id):

    # =========================
    # 🔧 Daten vorbereiten
    # =========================

    new_data = {
        "tool_id": form.get("tool_id"),
        "order_id": form.get("order_id"),
        "machine_id": form.get("machine_id"),
        "error_type": form.get("error_type"),
        "description": form.get("description"),
    }

    # Dummy Objekt für Vergleich (create → alles ist "neu")
    temp_obj = ToolError()

    changes = build_changes(temp_obj, new_data, new_data.keys())

    # =========================
    # 🆕 Objekt erstellen
    # =========================

    error = ToolError(
        **new_data,
        reported_by_id=user_id,
        created_at=datetime.utcnow()
    )

    db.session.add(error)
    db.session.flush()  # 🔥 ID verfügbar

    # =========================
    # 📸 Bilder speichern
    # =========================

    upload_folder = os.path.join(
        current_app.static_folder,
        "uploads/tool_errors"
    )

    os.makedirs(upload_folder, exist_ok=True)

    uploaded_files = files.getlist("images")

    for i, file in enumerate(uploaded_files):

        if file and file.filename:

            filename = f"{uuid.uuid4()}_{file.filename}"
            filepath = os.path.join(upload_folder, filename)

            file.save(filepath)

            marker_x = form.get(f"marker_x_{i}")
            marker_y = form.get(f"marker_y_{i}")

            marker_px = form.get(f"marker_px_{i}")
            marker_py = form.get(f"marker_py_{i}")

            image = ToolErrorImage(
                tool_error_id=error.id,
                image_path=f"uploads/tool_errors/{filename}",image_path=...,
                marker_x=float(marker_x),
                marker_y=float(marker_y),
                marker_px=int(marker_px),
                marker_py=int(marker_py)
            )

            db.session.add(image)
        

    # =========================
    # 📝 CHANGELOG
    # =========================

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
