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


# =====================================================
# FINAL PDF / EXPORT RENDER ENGINE
# =====================================================

# factoryos/modules/quality/inspection_plan/services/marker_service.py

from io import BytesIO
from PIL import Image as PILImage
from PIL import ImageDraw
from PIL import ImageFont


# ==========================================================
# FINAL PDF / APP MARKER ENGINE
# ==========================================================

def render_qm_markers_scaled_for_pdf(
    image_path,
    characteristics,
    target_width_px
):
    """
    FINAL ENGINE

    - Bild wird zuerst skaliert
    - Marker danach NEU auf Zielgröße gerendert
    - exakt wie Builder
    - perfekte Position
    - perfekte Größe
    """

    # ------------------------------------------------------
    # ORIGINAL LADEN
    # ------------------------------------------------------
    img = PILImage.open(image_path).convert("RGB")

    orig_w, orig_h = img.size

    scale = target_width_px / orig_w
    target_height = int(orig_h * scale)

    # ------------------------------------------------------
    # BILD SKALIEREN
    # ------------------------------------------------------
    img = img.resize(
        (target_width_px, target_height),
        PILImage.LANCZOS
    )

    draw = ImageDraw.Draw(img)

    # ------------------------------------------------------
    # MARKER
    # ------------------------------------------------------
    for c in characteristics:

        if c.pos_x is None or c.pos_y is None:
            continue

        # ===============================================
        # SKALIERTE POSITION
        # ===============================================
        x = int(c.pos_x * scale)
        y = int(c.pos_y * scale)

        # ===============================================
        # FINAL DESIGN
        # ===============================================
        r = max(int(12 * scale), 10)

        arrow_len = int(r * 1.35)
        arrow_h = int(r * 0.95)

        border = max(int(r * 0.16), 2)

        font_size = int(r * 1.05)

        try:
            font = ImageFont.truetype(
                "DejaVuSans-Bold.ttf",
                font_size
            )
        except:
            font = ImageFont.load_default()

        # ===============================================
        # Builder Style:
        # Kreis links / Spitze rechts
        # ===============================================
        cx = x
        cy = y

        tip_x = x + r + arrow_len
        tip_y = y

        # -----------------------------------------------
        # Spitze
        # -----------------------------------------------
        draw.polygon(
            [
                (cx + r - 1, cy - arrow_h / 2),
                (tip_x, tip_y),
                (cx + r - 1, cy + arrow_h / 2)
            ],
            fill="#c80000"
        )

        # -----------------------------------------------
        # Kreis
        # -----------------------------------------------
        draw.ellipse(
            (
                cx - r,
                cy - r,
                cx + r,
                cy + r
            ),
            fill="white",
            outline="#c80000",
            width=border
        )

        # -----------------------------------------------
        # Zahl
        # -----------------------------------------------
        txt = str(c.sort_order)

        bbox = draw.textbbox((0, 0), txt, font=font)

        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        draw.text(
            (
                cx - tw / 2,
                cy - th / 2 - 1
            ),
            txt,
            fill="#c80000",
            font=font
        )

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    return output
