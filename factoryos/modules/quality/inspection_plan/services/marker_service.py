# factoryos/modules/quality/inspection_plan/services/marker_service.py

import os
from io import BytesIO

from PIL import Image as PILImage
from PIL import ImageDraw
from PIL import ImageFont

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

# ==========================================================
# FACTORYOS - ULTIMATE PDF ENGINE FINAL
# QM MARKER 1:1 APP → PDF PIXEL PERFECT
# ==========================================================

import os
from io import BytesIO
from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.platypus import Image
from reportlab.lib.units import mm


# ==========================================================
# FINAL ENGINE
# ==========================================================

def render_qm_markers(
    image_path,
    markers,
    pdf_max_width_mm=170,
    pdf_max_height_mm=250
):
    """
    markers = [
        {"x":1234,"y":888,"number":1},
        ...
    ]

    returns ReportLab Image()
    """

    img = PILImage.open(image_path).convert("RGB")
    orig_w, orig_h = img.size

    # ------------------------------------------------------
    # 1. ZIELGRÖSE FÜR PDF FESTLEGEN
    # ------------------------------------------------------
    aspect = orig_w / orig_h

    if aspect >= 1:
        target_w_mm = pdf_max_width_mm
        target_h_mm = pdf_max_width_mm / aspect
    else:
        target_h_mm = pdf_max_height_mm
        target_w_mm = pdf_max_height_mm * aspect

    MAX_RENDER_PX = 4200

    target_w_px = int(target_w_mm * 11.811)
    target_h_px = int(target_h_mm * 11.811)

    # Begrenzen
    if target_w_px > MAX_RENDER_PX:
        scale = MAX_RENDER_PX / target_w_px
        target_w_px = int(target_w_px * scale)
        target_h_px = int(target_h_px * scale)

    if target_h_px > MAX_RENDER_PX:
        scale = MAX_RENDER_PX / target_h_px
        target_w_px = int(target_w_px * scale)
        target_h_px = int(target_h_px * scale)
    

    # ------------------------------------------------------
    # 2. BILD EXAKT AUF ENDFORMAT SKALIEREN
    # ------------------------------------------------------
    img = img.resize((target_w_px, target_h_px), PILImage.LANCZOS)

    draw = ImageDraw.Draw(img)

    scale_x = target_w_px / orig_w
    scale_y = target_h_px / orig_h

    # ------------------------------------------------------
    # 3. FONT
    # ------------------------------------------------------
    try:
        font_size = int(circle_r * 1.05)

        font = ImageFont.truetype(
            "DejaVuSans-Bold.ttf",
            font_size
        )
    except:
        font = ImageFont.load_default()

    # ------------------------------------------------------
    # 4. MARKER ZEICHNEN (1:1 APP STYLE)
    # ------------------------------------------------------
    for m in markers:

        # ORM oder Dict kompatibel
        raw_x = getattr(m, "pos_x", None)
        raw_y = getattr(m, "pos_y", None)
        raw_no = getattr(m, "sort_order", None)

        if raw_x is None:
            raw_x = m["x"]

        if raw_y is None:
            raw_y = m["y"]

        if raw_no is None:
            raw_no = m["number"]

        x = int(float(raw_x) * scale_x)
        y = int(float(raw_y) * scale_y)

        number = str(raw_no)

        # App Maße exakt
        base = min(target_w_px, target_h_px)

        circle_r = max(int(base * 0.022), 14)
        border = max(int(circle_r * 0.18), 3)

        arrow_len = int(circle_r * 1.45)
        arrow_half_h = int(circle_r * 0.58)

        cx = x - arrow_len - circle_r + 1
        cy = y

        # ---------- Spitze ----------
        draw.polygon(
            [
                (x, y),
                (cx + circle_r - 1, y - arrow_half_h),
                (cx + circle_r - 1, y + arrow_half_h)
            ],
            fill="#c80000"
        )

        # ---------- Kreis ----------
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

        # ---------- Zahl ----------
        bbox = draw.textbbox((0, 0), number, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        draw.text(
            (cx - tw / 2, cy - th / 2 - 1),
            number,
            fill="#c80000",
            font=font
        )

    # ------------------------------------------------------
    # 5. RETURN REPORTLAB IMAGE
    # ------------------------------------------------------
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    return Image(
        output,
        width=target_w_mm * mm,
        height=target_h_mm * mm
    )



        
