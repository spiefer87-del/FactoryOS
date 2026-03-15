from factoryos.extensions import db

from factoryos.modules.quality.inspection_plan.models import (
    QualityInspectionCharacteristic,
    QualityInspectionSection
)

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
