from factoryos.extensions import db

from ..models import QualityInspectionSection
from ..models import QualityInspectionCharacteristic

from PIL import Image as PILImage, ImageDraw, ImageFont
from io import BytesIO

import cairosvg
from io import BytesIO

import base64

from factoryos.modules.quality.inspection_plan.services.change_log_service import log_change


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

    name = data.get("name")
    target_value = data.get("target_value")
    tol_minus = data.get("tolerance_minus")
    tol_plus = data.get("tolerance_plus")
    unit = data.get("unit")

    pos_x = data.get("pos_x")
    pos_y = data.get("pos_y")

    last = (
        QualityInspectionCharacteristic.query
        .filter_by(section_id=section_id)
        .order_by(QualityInspectionCharacteristic.sort_order.desc())
        .first()
    )

    order = 1

    if last:
        order = last.sort_order + 1

    characteristic = QualityInspectionCharacteristic(

        section_id=section_id,
        name=name,
        target_value=target_value,
        tolerance_minus=tol_minus,
        tolerance_plus=tol_plus,
        unit=unit,

        pos_x=pos_x,
        pos_y=pos_y,

        sort_order=order
    )

    db.session.add(characteristic)

    section = QualityInspectionSection.query.get(section_id)

    log_change(
        section.version,
        "ADD_MARKER",
        f"Merkmal '{name}' auf Zeichnung gesetzt"
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

    characteristics = (
        QualityInspectionCharacteristic.query
        .filter_by(section_id=section_id)
        .order_by(QualityInspectionCharacteristic.sort_order.asc())
        .all()
    )

    for i, c in enumerate(characteristics, start=1):
        c.sort_order = i


    db.session.commit()

    
def render_svg_to_png(svg_string):

    png_output = BytesIO()

    cairosvg.svg2png(
        bytestring=svg_string.encode("utf-8"),
        write_to=png_output
    )

    png_output.seek(0)

    return png_output




def generate_svg_with_markers(image_path, characteristics):

    from PIL import Image as PILImage
    import base64

    img = PILImage.open(image_path)
    width, height = img.width, img.height

    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    svg = []

    svg.append(f'''
    <svg xmlns="http://www.w3.org/2000/svg"
         viewBox="0 0 {width} {height}"
         width="{width}"
         height="{height}">

        <image href="data:image/png;base64,{base64_image}"
               x="0"
               y="0"
               width="{width}"
               height="{height}" />
    ''')

    for c in characteristics:

        if c.pos_x is None or c.pos_y is None:
            continue

        # =====================================
        # CSS translate(-50%, -50%) berücksichtigen
        # =====================================

        pos_x = float(c.pos_x)
        pos_y = float(c.pos_y)

        marker_width = 28
        marker_height = 22

        x = pos_x - marker_width / 2
        y = pos_y - marker_height / 2

        # Kreis rechts
        cx = x + 18
        cy = y + 11

        svg.append(f'''
        <g>

            <!-- große Pfeilspitze -->
            <polygon points="
                {x+1},{y+11}
                {x+12},{y+4}
                {x+12},{y+18}
            "
            fill="#c40000"/>

            <!-- Kreis -->
            <circle cx="{cx}"
                    cy="{cy}"
                    r="11"
                    fill="white"
                    stroke="#c40000"
                    stroke-width="3"/>

            <!-- Zahl -->
            <text x="{cx}"
                  y="{cy+4}"
                  text-anchor="middle"
                  font-size="12"
                  font-weight="bold"
                  fill="#c40000"
                  font-family="Arial">
                {c.sort_order}
            </text>

        </g>
        ''')

    svg.append("</svg>")

    return "".join(svg)
