# factoryos/modules/quality/inspection_plan/services/marker_service.py

import os
from io import BytesIO

from PIL import Image as PILImage
from PIL import ImageDraw
from PIL import ImageFont

from reportlab.platypus import Image
from reportlab.lib.units import mm

from factoryos.extensions import db

from ..models import (
    QualityInspectionSection,
    QualityInspectionCharacteristic
)

from factoryos.modules.quality.inspection_plan.services.change_log_service import log_change


# =====================================================
# CRUD MARKER
# =====================================================

def create_marker(section_id, pos_x, pos_y):

    section = QualityInspectionSection.query.get_or_404(section_id)

    characteristic = QualityInspectionCharacteristic(
        section_id=section.id,
        name="Neues Merkmal",
        pos_x=pos_x,
        pos_y=pos_y
    )

    db.session.add(characteristic)
    db.session.commit()

    return characteristic


def create_characteristic_with_marker(data):

    section_id = data.get("section_id")

    last = (
        QualityInspectionCharacteristic.query
        .filter_by(section_id=section_id)
        .order_by(QualityInspectionCharacteristic.sort_order.desc())
        .first()
    )

    order = 1 if not last else last.sort_order + 1

    characteristic = QualityInspectionCharacteristic(
        section_id=section_id,
        name=data.get("name"),
        target_value=data.get("target_value"),
        tolerance_minus=data.get("tolerance_minus"),
        tolerance_plus=data.get("tolerance_plus"),
        unit=data.get("unit"),
        pos_x=data.get("pos_x"),
        pos_y=data.get("pos_y"),
        sort_order=order
    )

    db.session.add(characteristic)

    section = QualityInspectionSection.query.get(section_id)

    log_change(
        section.version,
        "ADD_MARKER",
        f"Merkmal '{characteristic.name}' auf Zeichnung gesetzt"
    )

    db.session.commit()

    return characteristic


def update_marker_position(char_id, pos_x, pos_y):

    char = QualityInspectionCharacteristic.query.get_or_404(char_id)

    char.pos_x = pos_x
    char.pos_y = pos_y

    log_change(
        char.section.version,
        "MOVE_MARKER",
        f"Marker '{char.name}' verschoben"
    )

    db.session.commit()


def delete_marker(char_id):

    char = QualityInspectionCharacteristic.query.get_or_404(char_id)

    section = char.section
    section_id = char.section_id

    log_change(
        section.version,
        "DELETE_MARKER",
        f"Marker '{char.name}' gelöscht"
    )

    db.session.delete(char)
    db.session.commit()

    reorder_characteristics(section_id)


def reorder_characteristics(section_id):

    chars = (
        QualityInspectionCharacteristic.query
        .filter_by(section_id=section_id)
        .order_by(QualityInspectionCharacteristic.sort_order.asc())
        .all()
    )

    for i, c in enumerate(chars, start=1):
        c.sort_order = i

    db.session.commit()


# =====================================================
# FACTORYOS FINAL PDF MARKER ENGINE
# 1:1 App Marker Export
# =====================================================

def render_qm_markers(
    image_path,
    markers,
    pdf_max_width_mm=170,
    pdf_max_height_mm=250
):
    """
    Gibt ReportLab Image zurück.
    Nutzt exakt dieselben Marker-Proportionen wie Frontend.
    """

    img = PILImage.open(image_path).convert("RGB")
    orig_w, orig_h = img.size

    # -----------------------------------------
    # PDF Zielgröße
    # -----------------------------------------
    aspect = orig_w / orig_h

    if aspect >= 1:
        target_w_mm = pdf_max_width_mm
        target_h_mm = pdf_max_width_mm / aspect
    else:
        target_h_mm = pdf_max_height_mm
        target_w_mm = pdf_max_height_mm * aspect

    # 300 DPI ungefähr
    PX_PER_MM = 11.811

    target_w_px = int(target_w_mm * PX_PER_MM)
    target_h_px = int(target_h_mm * PX_PER_MM)

    MAX_RENDER = 4200

    if target_w_px > MAX_RENDER:
        factor = MAX_RENDER / target_w_px
        target_w_px = int(target_w_px * factor)
        target_h_px = int(target_h_px * factor)

    if target_h_px > MAX_RENDER:
        factor = MAX_RENDER / target_h_px
        target_w_px = int(target_w_px * factor)
        target_h_px = int(target_h_px * factor)

    # -----------------------------------------
    # Bild skalieren
    # -----------------------------------------
    img = img.resize((target_w_px, target_h_px), PILImage.LANCZOS)

    draw = ImageDraw.Draw(img)

    scale_x = target_w_px / orig_w
    scale_y = target_h_px / orig_h

    # -----------------------------------------
    # Marker zeichnen
    # -----------------------------------------
    for m in markers:

        # ORM oder Dict kompatibel
        raw_x = getattr(m, "pos_x", None)
        raw_y = getattr(m, "pos_y", None)
        raw_no = getattr(m, "sort_order", None)
        raw_rotation = getattr(m, "rotation", 0)

        if raw_x is None:
            raw_x = m["x"]

        if raw_y is None:
            raw_y = m["y"]

        if raw_no is None:
            raw_no = m["number"]

        if raw_rotation is None:
            raw_rotation = m.get("rotation", 0)

        # gespeicherte Pixelkoordinaten
        x = float(raw_x) * scale_x
        y = float(raw_y) * scale_y

        number = str(raw_no)
        rotation = float(raw_rotation)

        # ---------------------------------
        # 1:1 Frontend CSS Maße
        # marker width:44 height:24
        # circle:24
        # arrow left:22
        # ---------------------------------

        ui_scale = target_w_px / orig_w

        circle_r = max(int(12 * ui_scale), 8)
        border = max(int(2 * ui_scale), 1)

        arrow_len = max(int(18 * ui_scale), 12)
        arrow_half_h = max(int(7 * ui_scale), 3)

        # gespeicherter Punkt = MITTE marker-box
        # circle sitzt links
        cx = int(x - (10 * ui_scale))
        cy = int(y)

        tip_x = int(x + (12 * ui_scale))
        tip_y = cy

        # Font
        try:
            font = ImageFont.truetype(
                "DejaVuSans-Bold.ttf",
                max(int(circle_r * 1.15), 10)
            )
        except:
            font = ImageFont.load_default()

        # Spitze
        draw.polygon(
            [
                (tip_x, tip_y),
                (cx + circle_r - 2, cy - arrow_half_h),
                (cx + circle_r - 2, cy + arrow_half_h)
            ],
            fill="#c80000"
        )

        # Kreis
        draw.ellipse(
            (
                cx - circle_r,
                cy - circle_r,
                cx + circle_r,
                cy + circle_r
            ),
            fill="white",
            outline="#c80000",
            width=border
        )

        # Zahl zentrieren
        bbox = draw.textbbox((0, 0), number, font=font)
        
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        tx = cx - tw / 2 - bbox[0]
        ty = cy - th / 2 - bbox[1]
        
        draw.text(
            (tx, ty),
            number,
            fill="#c80000",
            font=font
        )

    # -----------------------------------------
    # ReportLab Image zurück
    # -----------------------------------------
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    return output

def update_marker_rotation(char_id, rotation):

    char = QualityInspectionCharacteristic.query.get_or_404(char_id)

    char.rotation = rotation

    log_change(
        char.section.version,
        "ROTATE_MARKER",
        f"Marker '{char.name}' gedreht"
    )

    db.session.commit()
