import os
import uuid
from datetime import datetime
from flask import current_app
from sqlalchemy import func
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from io import BytesIO
from PIL import Image as PILImage, ImageDraw, ImageFont



from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.core.services.change_log_service import log_change, build_changes
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES

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
def upload_temp_image(file, marker_x, marker_y, marker_px, marker_py, description, temp_id):

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
        temp_id=temp_id,
        image_path=f"uploads/tool_errors/{filename}",

        marker_x=float(marker_x) if marker_x else None,
        marker_y=float(marker_y) if marker_y else None,

        marker_px=int(marker_px) if marker_px else None,
        marker_py=int(marker_py) if marker_py else None,

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



# =========================
# PDF Export
# =========================



def generate_tool_error_pdf(error):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()
    content = []

    # HEADER
    content.append(Paragraph(f"Fehlermeldung {error.error_no}", styles["Title"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"<b>Werkzeug:</b> {error.tool.tool_no}", styles["Normal"]))
    content.append(Paragraph(f"<b>Fehler:</b> {error.error_type}", styles["Normal"]))
    content.append(Paragraph(f"<b>Datum:</b> {error.created_at.strftime('%d.%m.%Y %H:%M')}", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("<b>Beschreibung:</b>", styles["Heading3"]))
    content.append(Paragraph(error.description or "-", styles["Normal"]))
    content.append(Spacer(1, 20))

    if error.images:
        content.append(Paragraph("Bilder:", styles["Heading2"]))
        content.append(Spacer(1, 10))

    for i, image in enumerate(error.images):

        image_path = os.path.join(current_app.static_folder, image.image_path)

        if not os.path.exists(image_path):
            continue

        pil_img = PILImage.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(pil_img)

        width, height = pil_img.size
        base = min(width, height)

        # =========================
        # 📍 POSITION
        # =========================
        if image.marker_px is not None and image.marker_py is not None:
            x = image.marker_px
            y = image.marker_py
        elif image.marker_x is not None and image.marker_y is not None:
            x = int(image.marker_x * width)
            y = int(image.marker_y * height)
        else:
            x = y = None

        if x and y:

            # Größen dynamisch
            circle_radius = max(int(base * 0.025), 12)
            arrow_length = max(int(base * 0.05), 20)
            font_size = max(int(base * 0.03), 14)

            try:
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()

            marker_x = x - arrow_length
            marker_y = y

            # Kreis
            draw.ellipse(
                (
                    marker_x - circle_radius,
                    marker_y - circle_radius,
                    marker_x + circle_radius,
                    marker_y + circle_radius
                ),
                fill="red"
            )

            # Pfeil
            draw.polygon([
                (marker_x + circle_radius, marker_y),
                (x, y),
                (marker_x + circle_radius, marker_y + circle_radius * 0.8)
            ], fill="red")

            # Nummer
            number = str(i + 1)

            bbox = draw.textbbox((0, 0), number, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            draw.text(
                (marker_x - text_w / 2, marker_y - text_h / 2),
                number,
                fill="white",
                font=font
            )

        # =========================
        # 📐 SKALIERUNG
        # =========================
        max_width_mm = 170
        max_height_mm = 120

        aspect = width / height

        if width > height:
            display_width = max_width_mm * mm
            display_height = (max_width_mm / aspect) * mm
        else:
            display_height = max_height_mm * mm
            display_width = (max_height_mm * aspect) * mm

        img_buffer = BytesIO()
        pil_img.save(img_buffer, format="JPEG")
        img_buffer.seek(0)

        pdf_img = Image(img_buffer, width=display_width, height=display_height)

        content.append(pdf_img)
        content.append(Spacer(1, 5))

        if image.description:
            content.append(Paragraph(image.description, styles["Italic"]))
            content.append(Spacer(1, 10))

    doc.build(content)
    buffer.seek(0)

    return buffer
