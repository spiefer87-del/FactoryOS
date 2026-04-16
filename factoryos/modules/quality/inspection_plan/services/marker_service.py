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

def render_qm_markers_to_image(image_path, characteristics):
    """
    Rendert Marker direkt per PIL auf Zeichnung.
    1:1 Pixelpositionen aus DB.
    Output: BytesIO PNG
    """

    img = PILImage.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    width, height = img.size
    base = min(width, height)

    for c in characteristics:

        if c.pos_x is None or c.pos_y is None:
            continue

        x = int(c.pos_x)
        y = int(c.pos_y)

        # =================================================
        # MARKER SCALE
        # =================================================
        r = max(int(base * 0.016), 10)         # Kreisradius
        arrow_len = int(r * 1.45)             # Spitzenlänge
        arrow_h = int(r * 1.15)               # Spitzenhöhe
        border = max(int(r * 0.16), 2)

        font_size = int(r * 1.10)

        try:
            font = ImageFont.truetype(
                "DejaVuSans-Bold.ttf",
                font_size
            )
        except:
            font = ImageFont.load_default()

        # =================================================
        # POSITION
        # Spitze = Messpunkt
        # Kreis rechts daneben
        # =================================================
        tip_x = x
        tip_y = y

        cx = x + arrow_len + r - 1
        cy = y

        # =================================================
        # SPITZE
        # =================================================
        draw.polygon(
            [
                (tip_x, tip_y),
                (cx - r + 2, cy - arrow_h / 2),
                (cx - r + 2, cy + arrow_h / 2)
            ],
            fill="#c80000"
        )

        # =================================================
        # KREIS
        # =================================================
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

        # =================================================
        # TEXT
        # =================================================
        txt = str(c.sort_order)

        bbox = draw.textbbox((0, 0), txt, font=font)

        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        draw.text(
            (
                cx - tw / 2,
                cy - th / 2 - 2
            ),
            txt,
            fill="#c80000",
            font=font
        )

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    return output
