from factoryos.extensions import db

from ..models import QualityInspectionSection
from ..models import QualityInspectionCharacteristic

from PIL import Image as PILImage, ImageDraw, ImageFont
from io import BytesIO

import cairosvg
from io import BytesIO

import base64
import html


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






def generate_svg_with_markers(image_path, characteristics):

    from PIL import Image as PILImage
    import base64

    # Bildgröße holen
    img = PILImage.open(image_path)
    width, height = img.width, img.height

    # Base64
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("ascii").replace("\n", "").replace("\r", "")

    svg = []

    svg.append(f'''
    <svg xmlns="http://www.w3.org/2000/svg"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        viewBox="0 0 {width} {height}"
        preserveAspectRatio="xMidYMid meet">

        <image xlink:href="data:image/png;base64,{base64_image}"
               x="0" y="0"
               width="{width}" height="{height}" />
    ''')

    for c in characteristics:

        if c.pos_x is None or c.pos_y is None:
            continue

        x = c.pos_x * width
        y = c.pos_y * height

        # 🔥 HIER FIX 3
        text = html.escape(str(c.sort_order))

        svg.append(f'''
        <g transform="translate({x} {y})">
            <circle r="12"
                    cx="0"
                    cy="0"
                    fill="red"
                    stroke="black"
                    stroke-width="2"/>

            <text text-anchor="middle"
                dominant-baseline="middle"
                x="0"
                y="0"
                fill="white"
                font-size="20">
                {text}
            </text>

        </g>
        ''')
    
    svg.append("</svg>")
    print(svg[:500])
    return "".join(svg)
    
def render_svg_to_png(svg_string):

    png_output = BytesIO()

    cairosvg.svg2png(
        bytestring=svg_string.encode("utf-8"),
        write_to=png_output,
        output_width=2000  # 🔥 wichtig für Qualität
    )

    png_output.seek(0)

    return png_output
