import os
import uuid
from datetime import datetime
from flask import current_app
from sqlalchemy import func

from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.core.services.change_log_service import log_change, build_changes

from ..models import ToolError, ToolErrorImage


# =========================
# CREATE TOOL ERROR (OHNE BILDER)
# =========================
def create_tool_error(form, user_id):

    year = datetime.utcnow().year % 100  # 26

    # 🔍 höchste Nummer dieses Jahres holen
    last = db.session.query(ToolError)\
        .filter(func.strftime('%Y', ToolError.created_at) == str(datetime.utcnow().year))\
        .order_by(ToolError.id.desc())\
        .first()

    if last and last.error_no:
        last_number = int(last.error_no.split("-")[1])
        new_number = last_number + 1
    else:
        new_number = 1

    error_no = f"FM{year:02d}-{new_number:03d}"

    tool_id_raw = form.get("tool_id")

    if not tool_id_raw:
        raise ValueError("❌ tool_id fehlt")

    tool_id = int(tool_id_raw)

    # 🔥 NEU: Status aus Form holen
    new_status = form.get("tool_status")

    new_data = {
        "tool_id": tool_id,
        "order_id": form.get("order_id"),
        "machine_id": form.get("machine_id"),
        "error_type": form.get("error_type"),
        "description": form.get("description"),
    }

    temp_obj = ToolError()
    changes = build_changes(temp_obj, new_data, new_data.keys())

    error = ToolError(
        **new_data,
        error_no=error_no,
        reported_by_id=user_id,
        created_at=datetime.utcnow()
    )

    db.session.add(error)
    db.session.flush()

    # 🔥 Bilder zuweisen
    temp_id = form.get("temp_id")

    images = ToolErrorImage.query.filter_by(temp_id=temp_id).all()

    for img in images:
        img.tool_error_id = error.id
        img.temp_id = None

    # =========================
    # 🔧 TOOL + STATUS HANDLING
    # =========================

    tool = Tool.query.get(tool_id)

    if tool:
        # Werkzeug ins Log schöner darstellen
        changes["Werkzeug"] = {
            "old": None,
            "new": tool.tool_no
        }
        changes.pop("tool_id", None)

        # 🔥 STATUS ÄNDERUNG
        if new_status:
            old_status = tool.tool_status

            # nur ändern wenn wirklich unterschiedlich
            if old_status != new_status:
                tool.tool_status = new_status

                # 🔥 ChangeLog ergänzen
                changes["Werkzeug Status"] = {
                    "old": old_status,
                    "new": new_status
                }

    # =========================
    # 🧾 CHANGELOG
    # =========================

    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=f"{error.error_no} ({tool.tool_no if tool else tool_id})",
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

    return image


# =========================
# ASSIGN TEMP IMAGES → ERROR
# =========================
def assign_images_to_error(temp_id, error_id):

    if not temp_id:
        print("❌ Kein temp_id")
        return

    images = ToolErrorImage.query.filter_by(temp_id=temp_id).all()

    for img in images:
        img.tool_error_id = error_id
        img.temp_id = None  # optional cleanup

    db.session.commit()

    print(f"✅ {len(images)} Bilder zugeordnet")


def set_tool_status(error_id, status):

    error = ToolError.query.get_or_404(error_id)

    tool = Tool.query.get(error.tool_id)

    if not tool:
        return False

    old_status = tool.tool_status

    tool.tool_status = status

    log_change(
        entity_type="tool",
        entity_id=tool.id,
        entity_name=tool.tool_no,
        action="status_update",
        changes={
            "Status": {
                "old": old_status,
                "new": status
            }
        },
        category="masterdata"
    )

    db.session.commit()

    return True

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
