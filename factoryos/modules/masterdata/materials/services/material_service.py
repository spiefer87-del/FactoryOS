from factoryos.core.services.change_log_service import log_change
from factoryos.extensions import db
from factoryos.modules.masterdata.shared.constants import (
    MATERIAL_BASE_UNITS,
    MATERIAL_DELIVERY_FORMS,
    MATERIAL_STATUSES,
    MATERIAL_TYPES,
    POLYMER_TYPES,
)

from ..models import Material
from .material_storage_service import (
    create_material_folders,
    delete_material_folder,
    rename_material_folder,
)


TEXT_FIELDS = (
    "material_no",
    "external_material_no",
    "name",
    "description",
    "material_type",
    "polymer_type",
    "manufacturer",
    "color",
    "color_no",
    "delivery_form",
    "base_unit",
    "melt_flow_rate",
    "storage_location",
    "material_status",
    "preferred_supplier_name",
    "supplier_material_no",
)

FLOAT_FIELDS = (
    "density_g_cm3",
    "drying_temperature_c",
    "drying_time_h",
    "processing_temperature_min_c",
    "processing_temperature_max_c",
    "mold_temperature_min_c",
    "mold_temperature_max_c",
    "minimum_stock",
    "reorder_point",
)

PLASTIC_ONLY_FIELDS = (
    "polymer_type",
    "density_g_cm3",
    "melt_flow_rate",
    "drying_temperature_c",
    "drying_time_h",
    "processing_temperature_min_c",
    "processing_temperature_max_c",
    "mold_temperature_min_c",
    "mold_temperature_max_c",
)


def _text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _float(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).strip().replace(",", "."))


def _boolean(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {
        "1", "true", "yes", "ja", "j", "x",
    }


def material_data_from_input(data):
    values = {field: _text(data.get(field)) for field in TEXT_FIELDS}
    values.update({field: _float(data.get(field)) for field in FLOAT_FIELDS})
    values["hazardous_material"] = _boolean(data.get("hazardous_material"))

    values["material_type"] = values.get("material_type") or "plastic"
    values["material_status"] = values.get("material_status") or "aktiv"
    values["base_unit"] = values.get("base_unit") or "kg"

    if not values.get("material_no"):
        raise ValueError("Die Materialnummer ist erforderlich.")
    if not values.get("name"):
        raise ValueError("Die genaue Bezeichnung ist erforderlich.")
    if values["material_type"] not in MATERIAL_TYPES:
        raise ValueError("Die Materialart ist ungültig.")
    if values["material_status"] not in MATERIAL_STATUSES:
        raise ValueError("Der Materialstatus ist ungültig.")
    if values["base_unit"] not in MATERIAL_BASE_UNITS:
        raise ValueError("Die Basiseinheit ist ungültig.")
    if (
        values.get("delivery_form")
        and values["delivery_form"] not in MATERIAL_DELIVERY_FORMS
    ):
        raise ValueError("Die Lieferform ist ungültig.")

    if values["material_type"] == "plastic":
        if not values.get("polymer_type"):
            raise ValueError("Bei Kunststoffmaterial ist die Kunststoffart erforderlich.")
        if values["polymer_type"] not in POLYMER_TYPES:
            raise ValueError("Die Kunststoffart ist ungültig.")
    else:
        for field in PLASTIC_ONLY_FIELDS:
            values[field] = None

    for minimum, maximum, label in (
        ("processing_temperature_min_c", "processing_temperature_max_c", "Verarbeitungstemperatur"),
        ("mold_temperature_min_c", "mold_temperature_max_c", "Werkzeugtemperatur"),
    ):
        if (
            values[minimum] is not None
            and values[maximum] is not None
            and values[minimum] > values[maximum]
        ):
            raise ValueError(f"Bei {label} ist der Minimalwert größer als der Maximalwert.")

    return values


def _build_changes(instance, values):
    return {
        field: {"old": getattr(instance, field, None), "new": value}
        for field, value in values.items()
        if getattr(instance, field, None) != value
    }


def create_material(data, user_id):
    material = Material(
        **material_data_from_input(data),
        created_by_id=user_id,
    )
    db.session.add(material)
    db.session.flush()

    try:
        create_material_folders(material.material_no)
    except OSError:
        db.session.rollback()
        raise

    log_change(
        entity_type="material",
        entity_id=material.id,
        entity_name=material.material_no,
        action="create",
        changes={"material_no": {"old": None, "new": material.material_no}},
        category="masterdata",
    )
    db.session.commit()
    return material


def update_material(material, data):
    values = material_data_from_input(data)
    changes = _build_changes(material, values)
    old_material_no = material.material_no

    if old_material_no != values["material_no"]:
        duplicate = (
            Material.query
            .filter(Material.material_no == values["material_no"])
            .filter(Material.id != material.id)
            .first()
        )
        if duplicate:
            raise ValueError("Die Materialnummer existiert bereits.")
        rename_material_folder(old_material_no, values["material_no"])

    for field, value in values.items():
        setattr(material, field, value)

    if changes:
        log_change(
            entity_type="material",
            entity_id=material.id,
            entity_name=material.material_no,
            action="update",
            changes=changes,
            category="masterdata",
        )

    db.session.commit()
    create_material_folders(material.material_no)
    return material


def delete_material(material):
    material_id = material.id
    material_no = material.material_no
    delete_material_folder(material_no)

    log_change(
        entity_type="material",
        entity_id=material_id,
        entity_name=material_no,
        action="delete",
        changes={},
        category="masterdata",
    )
    db.session.delete(material)
    db.session.commit()
