from factoryos.extensions import db

from factoryos.modules.quality.inspection_plan.models.characteristic_models import (
    QualityInspectionCharacteristic
)


def add_characteristic(section, form):

    # nächste Merkmalnummer bestimmen
    next_order = (
        db.session.query(db.func.max(QualityInspectionCharacteristic.sort_order))
        .filter_by(section_id=section.id)
        .scalar()
    )

    next_order = (next_order or 0) + 1

    characteristic = QualityInspectionCharacteristic(
        section_id=section.id,
        name=form.get("name"),
        target_value=form.get("target_value"),
        tolerance_minus=form.get("tolerance_minus"),
        tolerance_plus=form.get("tolerance_plus"),
        unit=form.get("unit"),
        sort_order=next_order
    )

    db.session.add(characteristic)
    db.session.commit()

    return characteristic
