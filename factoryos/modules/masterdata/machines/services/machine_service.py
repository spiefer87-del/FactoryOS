from datetime import datetime

from factoryos.extensions import db

from factoryos.modules.masterdata.machines.models import (
    Machine,
    InjectionMoldingData
)

from factoryos.core.services.change_log_service import (
    log_change
)


MACHINE_FIELDS = [
    "machine_no",
    "external_machine_no",
    "name",
    "description",
    "machine_type",
    "manufacturer",
    "model",
    "serial_no",
    "build_year",
    "controller_type",
    "automation_type",
    "operating_hours",
    "last_service_at",
    "next_service_at",
    "location",
    "machine_status",
]


INJECTION_FIELDS = [
    "clamping_force_kn",
    "tie_bar_width_mm",
    "tie_bar_height_mm",
    "min_mold_height_mm",
    "max_mold_height_mm",
    "opening_stroke_mm",
    "ejector_stroke_mm",
    "max_tool_weight_kg",
    "screw_diameter_mm",
    "max_shot_weight_g",
    "max_injection_pressure_bar",
    "heating_zones",
    "nozzle_radius_mm",
    "nozzle_diameter_mm",
]


INTEGER_FIELDS = {
    "build_year",
    "operating_hours",
    "heating_zones",
}


DATE_FIELDS = {
    "last_service_at",
    "next_service_at",
}


def _to_integer(value):

    if value in (None, ""):
        return None

    return int(value)


def _to_float(value):

    if value in (None, ""):
        return None

    return float(
        str(value).replace(",", ".")
    )


def _to_datetime(value):

    if not value:
        return None

    return datetime.strptime(
        value,
        "%Y-%m-%d"
    )


def _serialize_log_value(value):

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    return value


def _machine_data_from_form(data):

    result = {}

    for field in MACHINE_FIELDS:

        value = data.get(field)

        if field in INTEGER_FIELDS:
            value = _to_integer(value)

        elif field in DATE_FIELDS:
            value = _to_datetime(value)

        result[field] = None if value == "" else value

    result["machine_type"] = (
        result.get("machine_type")
        or "injection_molding"
    )

    result["machine_status"] = (
        result.get("machine_status")
        or "aktiv"
    )

    return result


def _injection_data_from_form(data):

    result = {}

    for field in INJECTION_FIELDS:

        value = data.get(field)

        if field in INTEGER_FIELDS:
            result[field] = _to_integer(value)
        else:
            result[field] = _to_float(value)

    return result


def _build_changes(instance, new_data, prefix=""):

    changes = {}

    for field, new_value in new_data.items():

        old_value = getattr(
            instance,
            field,
            None
        )

        if old_value == new_value:
            continue

        changes[f"{prefix}{field}"] = {
            "old": _serialize_log_value(old_value),
            "new": _serialize_log_value(new_value)
        }

    return changes


def create_machine(data, user_id):

    machine_data = _machine_data_from_form(
        data
    )

    machine = Machine(
        **machine_data,
        created_by_id=user_id
    )

    db.session.add(machine)
    db.session.flush()

    if machine.machine_type == "injection_molding":

        injection_data = _injection_data_from_form(
            data
        )

        injection = InjectionMoldingData(
            machine_id=machine.id,
            **injection_data
        )

        db.session.add(injection)

    log_change(
        entity_type="machine",
        entity_id=machine.id,
        entity_name=machine.machine_no,
        action="create",
        changes={
            "machine_no": {
                "old": None,
                "new": machine.machine_no
            }
        },
        category="masterdata"
    )

    db.session.commit()

    return machine


def update_machine(machine, data):

    machine_data = _machine_data_from_form(
        data
    )

    changes = _build_changes(
        machine,
        machine_data
    )

    for field, value in machine_data.items():
        setattr(machine, field, value)

    if machine.machine_type == "injection_molding":

        injection_data = _injection_data_from_form(
            data
        )

        injection = machine.injection_molding_data

        if injection is None:

            injection = InjectionMoldingData(
                machine=machine
            )

            db.session.add(injection)

        injection_changes = _build_changes(
            injection,
            injection_data,
            prefix="injection."
        )

        changes.update(
            injection_changes
        )

        for field, value in injection_data.items():
            setattr(injection, field, value)

    elif machine.injection_molding_data:

        changes["machine_type_data"] = {
            "old": "Spritzgießdaten vorhanden",
            "new": "Spritzgießdaten entfernt"
        }

        db.session.delete(
            machine.injection_molding_data
        )

    if changes:

        log_change(
            entity_type="machine",
            entity_id=machine.id,
            entity_name=machine.machine_no,
            action="update",
            changes=changes,
            category="masterdata"
        )

    db.session.commit()

    return machine


def delete_machine(machine):

    machine_no = machine.machine_no
    machine_id = machine.id

    log_change(
        entity_type="machine",
        entity_id=machine_id,
        entity_name=machine_no,
        action="delete",
        changes={},
        category="masterdata"
    )

    db.session.delete(machine)
    db.session.commit()
