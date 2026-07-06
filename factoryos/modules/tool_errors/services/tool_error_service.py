import os
import uuid
from datetime import datetime
from flask import current_app
from sqlalchemy import func
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from io import BytesIO
from PIL import Image as PILImage, ImageDraw, ImageFont, ImageOps



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
# UPDATE TOOL ERROR
# =========================
def update_tool_error(error, form):

    tool = Tool.query.get(error.tool_id)

    old_data = {
        "tool_id": error.tool_id,
        "order_id": error.order_id,
        "machine_id": error.machine_id,
        "error_type": error.error_type,
        "description": error.description,
    }

    new_data = {
        "tool_id": int(form.get("tool_id")),
        "order_id": form.get("order_id"),
        "machine_id": form.get("machine_id"),
        "error_type": form.get("error_type"),
        "description": form.get("description"),
    }

    changes = build_changes(
        error,
        new_data,
        new_data.keys()
    )

    # ---------------------------------------
    # Werkzeug geändert?
    # ---------------------------------------

    if new_data["tool_id"] != error.tool_id:

        new_tool = Tool.query.get(new_data["tool_id"])

        changes["Werkzeug"] = {
            "old": tool.tool_no if tool else error.tool_id,
            "new": new_tool.tool_no if new_tool else new_data["tool_id"]
        }

        tool = new_tool

    changes.pop("tool_id", None)

    # ---------------------------------------
    # Daten übernehmen
    # ---------------------------------------

    error.tool_id = new_data["tool_id"]
    error.order_id = new_data["order_id"]
    error.machine_id = new_data["machine_id"]
    error.error_type = new_data["error_type"]
    error.description = new_data["description"]

    # ---------------------------------------
    # Werkzeugstatus
    # ---------------------------------------

    new_status = form.get("tool_status")

    if tool and new_status:

        if tool.tool_status != new_status:

            changes["Werkzeug Status"] = {
                "old": tool.tool_status,
                "new": new_status
            }

            tool.tool_status = new_status

    # ---------------------------------------
    # Changelog
    # ---------------------------------------

    if changes:

        log_change(
            entity_type="tool_error",
            entity_id=error.id,
            entity_name=f"{error.error_no} ({tool.tool_no if tool else error.tool_id})",
            action="update",
            changes=changes,
            category="production"
        )

    db.session.commit()

    return error
    
# =========================
# TEMP IMAGE UPLOAD
# =========================
def upload_image(
        file,
        marker_x,
        marker_y,
        marker_px,
        marker_py,
        description,
        temp_id=None,
        tool_error_id=None
    ):

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

    img = PILImage.open(file)
    img = ImageOps.exif_transpose(img)
    img.save(filepath)

    image = ToolErrorImage(
        tool_error_id=tool_error_id,
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
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()
    content = []

    # =====================================================
    # DECKBLATT
    # =====================================================

    content.append(
        Paragraph(
            f"Fehlermeldung {error.error_no}",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 10 * mm))

    info_data = [
        ["Fehlermeldung", error.error_no],
        ["Fehlerart", error.error_type or "-"],
        ["Werkzeug", error.tool.tool_no if error.tool else "-"],
        ["Werkzeugstatus", TOOL_STATUSES.get(error.tool.tool_status, error.tool.tool_status) if error.tool else "-"],
        ["Revision", f"Revision {error.revision}"],
        ["Workflow", error.workflow_status or "-"],
        ["Erstellt am", error.created_at.strftime("%d.%m.%Y %H:%M") if error.created_at else "-"],
        ["Erstellt von", error.reported_by.username if error.reported_by else "-"],
    ]

    if error.released_at:
        info_data.append(
            [
                "Freigegeben am",
                error.released_at.strftime("%d.%m.%Y %H:%M")
            ]
        )

    if error.released_by:
        info_data.append(
            [
                "Freigegeben von",
                error.released_by.username
            ]
        )

    info_table = Table(
        info_data,
        colWidths=[
            45 * mm,
            190 * mm
        ]
    )

    info_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ])
    )

    content.append(info_table)
    content.append(Spacer(1, 10 * mm))

    content.append(
        Paragraph(
            "<b>Beschreibung</b>",
            styles["Heading2"]
        )
    )

    content.append(
        Paragraph(
            error.description or "-",
            styles["Normal"]
        )
    )

    content.append(PageBreak())

    # =====================================================
    # HELPER: MARKER INS BILD ZEICHNEN
    # =====================================================

    def build_marked_image(image, marker_number):

        image_path = os.path.join(
            current_app.static_folder,
            image.image_path
        )

        if not os.path.exists(image_path):
            return None

        # Wichtig bei Handyfotos:
        # EXIF-Orientierung anwenden
        pil_img = ImageOps.exif_transpose(
            PILImage.open(image_path)
        ).convert("RGB")

        draw = ImageDraw.Draw(pil_img)

        width, height = pil_img.size
        base = min(width, height)

        # =================================================
        # POSITION
        # Relative Werte bevorzugen!
        # Funktioniert auch nach Verkleinerung / Kamera-Fotos.
        # =================================================

        if image.marker_x is not None and image.marker_y is not None:

            x = int(float(image.marker_x) * width)
            y = int(float(image.marker_y) * height)

        elif image.marker_px is not None and image.marker_py is not None:

            x = int(image.marker_px)
            y = int(image.marker_py)

        else:

            x = y = None

        if x is not None and y is not None:

            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))

            r = max(int(base * 0.020), 11)
            arrow_len = int(r * 1.85)
            arrow_h = int(r * 1.20)
            border = max(int(r * 0.13), 2)

            font_size = int(r * 1.05)

            try:
                font = ImageFont.truetype(
                    "DejaVuSans-Bold.ttf",
                    font_size
                )
            except:
                font = ImageFont.load_default()

            tip_x = x
            tip_y = y

            cx = x - arrow_len - r + 2
            cy = y

            # Falls Marker zu weit links liegt,
            # Kreis nach rechts setzen und Pfeil nach links zeigen
            if cx - r < 0:

                cx = x + arrow_len + r - 2

                draw.ellipse(
                    (cx - r, cy - r, cx + r, cy + r),
                    fill="white",
                    outline="red",
                    width=border
                )

                draw.polygon([
                    (cx - r + 1, cy - arrow_h / 2),
                    (tip_x, tip_y),
                    (cx - r + 1, cy + arrow_h / 2)
                ], fill="red")

            else:

                draw.ellipse(
                    (cx - r, cy - r, cx + r, cy + r),
                    fill="white",
                    outline="red",
                    width=border
                )

                draw.polygon([
                    (cx + r - 1, cy - arrow_h / 2),
                    (tip_x, tip_y),
                    (cx + r - 1, cy + arrow_h / 2)
                ], fill="red")

            txt = str(marker_number)

            bbox = draw.textbbox((0, 0), txt, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            draw.text(
                (cx - tw / 2, cy - th / 2 - 3),
                txt,
                fill="red",
                font=font
            )

        img_buffer = BytesIO()
        pil_img.save(
            img_buffer,
            format="JPEG",
            quality=90
        )
        img_buffer.seek(0)

        return img_buffer, width, height

    # =====================================================
    # BILDERSEITEN
    # 2 Bilder pro Seite
    # =====================================================

    valid_images = []

    for index, image in enumerate(error.images, start=1):

        built = build_marked_image(
            image,
            index
        )

        if not built:
            continue

        valid_images.append(
            {
                "image": image,
                "number": index,
                "buffer": built[0],
                "width": built[1],
                "height": built[2]
            }
        )

    if not valid_images:

        content.append(
            Paragraph(
                "Keine Bilder vorhanden.",
                styles["Normal"]
            )
        )

    max_img_width = 125 * mm
    max_img_height = 120 * mm

    for page_start in range(0, len(valid_images), 2):

        pair = valid_images[page_start:page_start + 2]

        row_images = []
        row_descriptions = []

        for item in pair:

            width = item["width"]
            height = item["height"]

            aspect = width / height

            display_width = max_img_width
            display_height = display_width / aspect

            if display_height > max_img_height:
                display_height = max_img_height
                display_width = display_height * aspect

            pdf_img = Image(
                item["buffer"],
                width=display_width,
                height=display_height
            )

            row_images.append(pdf_img)

            description = item["image"].description or "-"

            row_descriptions.append(
                Paragraph(
                    f"<b>Bild {item['number']}</b><br/>{description}",
                    styles["Normal"]
                )
            )

        # Wenn nur ein Bild auf der letzten Seite ist,
        # zweite Spalte leer auffüllen
        while len(row_images) < 2:
            row_images.append("")
            row_descriptions.append("")

        table = Table(
            [
                row_images,
                row_descriptions
            ],
            colWidths=[
                130 * mm,
                130 * mm
            ],
            rowHeights=[
                125 * mm,
                30 * mm
            ]
        )

        table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ])
        )

        content.append(table)

        if page_start + 2 < len(valid_images):
            content.append(PageBreak())

    doc.build(content)

    buffer.seek(0)

    return buffer
