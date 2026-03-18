from factoryos.extensions import db

from ..models import (
    QualityInspectionSection,
    QualityInspectionCharacteristic
)

from factoryos.modules.quality.inspection_plan.services.change_log_service import log_change

def add_section(version, section_type):

    titles = {
        "identification": "Identification",
        "dimension": "Dimension",
        "gauge": "Gauge Check",
        "visual": "Visual Inspection",
        "text": "Text Check"
    }

    section = QualityInspectionSection(
        section_type=section_type,
        title=title
    )

    version.sections.append(section)

    db.session.add(section)

    version.is_dirty = True

    log_change(
        version,
        "ADD_SECTION",
        f"Modul '{section.title}' hinzugefügt"
    )

    db.session.commit()

    return section

def delete_section(section):

    version = section.version

    log_change(
        version,
        "DELETE_SECTION",
        f"Modul '{section.title}' gelöscht"
    )

    db.session.delete(section)

    version.is_dirty = True

    db.session.commit()

def add_characteristic(section, data):

    sort_order = len(section.characteristics) + 1

    char = QualityInspectionCharacteristic(

        section_id=section.id,

        name=data.get("name"),
        target_value=data.get("target_value"),
        tolerance_minus=data.get("tolerance_minus"),
        tolerance_plus=data.get("tolerance_plus"),
        unit=data.get("unit"),

        pos_x=data.get("pos_x"),
        pos_y=data.get("pos_y"),

        sort_order=sort_order

    )

    db.session.add(char)

    section.version.is_dirty = True

    log_change(
        section.version,
        "ADD_CHARACTERISTIC",
        f"Merkmal '{char.name}' hinzugefügt"
    )

    db.session.commit()

    return char

def update_characteristic_position(char_id, x, y):

    char = QualityInspectionCharacteristic.query.get_or_404(char_id)

    char.pos_x = x
    char.pos_y = y

    db.session.commit()

    return char

def delete_characteristic(char_id):

    char = QualityInspectionCharacteristic.query.get_or_404(char_id)

    version = char.section.version

    log_change(
        version,
        "DELETE_CHARACTERISTIC",
        f"Merkmal '{char.name}' gelöscht"
    )

    db.session.delete(char)

    version.is_dirty = True

    db.session.commit()


